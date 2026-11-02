import json
import uuid

import httpx
import pytest

from sgnl_api import DocsApi, SgnlAuthenticationError, SgnlNotFoundError, SgnlRateLimitError

BASE = "https://api.sgnl.pro/public/v1"


class FakeApi:
    """Records requests and answers them from a route table: (method, path) -> callable or Response."""

    def __init__(self):
        self.calls = []
        self.tokens_issued = 0
        self.routes = {}

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path.replace("/public/v1", "")
        if path == "/auth/token":
            self.tokens_issued += 1
            return httpx.Response(200, json={"token": f"tok{self.tokens_issued}", "expiresIn": 3600})
        body = None
        if request.headers.get("content-type") == "application/json":
            body = json.loads(request.content)
        self.calls.append((request.method, path, dict(request.url.params), body, request.headers.get("authorization")))
        route = self.routes.get((request.method, path))
        if route is None:
            return httpx.Response(404, text="no route")
        return route(request) if callable(route) else route

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler))


@pytest.fixture
def fake():
    return FakeApi()


@pytest.fixture
async def api(fake):
    client = fake.client()
    api = DocsApi(client_id="id", client_secret="secret", http_client=client, max_retries=2)
    yield api
    await api.aclose()
    await client.aclose()


async def test_http_client_is_used_and_not_closed(fake, api):
    fake.routes[("GET", "/projects")] = httpx.Response(200, json=[{"id": "p1", "name": "P", "code": "C"}])
    assert await api.project.get_list() == [{"id": "p1", "name": "P", "code": "C"}]
    await api.aclose()
    assert not api._transport.client.is_closed


async def test_401_refreshes_token_once_and_retries(fake, api):
    seen = []

    def projects(request):
        seen.append(request.headers["authorization"])
        return httpx.Response(401) if len(seen) == 1 else httpx.Response(200, json=[])

    fake.routes[("GET", "/projects")] = projects
    assert await api.project.get_list() == []
    assert seen == ["Bearer tok1", "Bearer tok2"]


async def test_persistent_401_raises(fake, api):
    fake.routes[("GET", "/projects")] = httpx.Response(401, text="revoked")
    with pytest.raises(SgnlAuthenticationError):
        await api.project.get_list()
    assert fake.tokens_issued == 2


async def test_429_retries_then_raises(fake, api):
    fake.routes[("GET", "/projects")] = httpx.Response(429, headers={"Retry-After": "0"}, text="slow")
    with pytest.raises(SgnlRateLimitError) as e:
        await api.project.get_list()
    assert e.value.retry_after == 0
    assert len(fake.calls) == 3  # 1 + max_retries


async def test_uuid_in_json_body_is_serialized(fake, api):
    folder = uuid.UUID("12345678-1234-5678-1234-567812345678")
    fake.routes[("PUT", "/folders")] = httpx.Response(200, json={"data": "f2"})
    assert await api.folder.create(folder, "Docs") == "f2"
    assert fake.calls[-1][3] == {"parentId": str(folder), "name": "Docs"}


async def test_create_link_sends_link_field(fake, api):
    fake.routes[("PUT", "/items/link")] = httpx.Response(200, json={"data": "i1"})
    assert await api.item.create_link("Site", "f1", "https://example.com") == "i1"
    assert fake.calls[-1][3] == {"name": "Site", "folderId": "f1", "link": "https://example.com"}


async def test_not_found_maps_to_exception(fake, api):
    with pytest.raises(SgnlNotFoundError):
        await api.project.info("missing")


async def test_upload_streams_and_returns_object_id(fake, api, tmp_path):
    payload = b"%PDF-" + b"x" * 3_000_000
    path = tmp_path / "drawing.pdf"
    path.write_bytes(payload)
    received = {}

    def put_s3(request):
        received["length"] = request.headers.get("content-length")
        received["chunked"] = request.headers.get("transfer-encoding")
        return httpx.Response(200)

    fake.routes[("PUT", "/objects")] = httpx.Response(
        200, json={"objectId": "o1", "signedUrl": "https://s3.example/upload/o1", "ttlSec": 600}
    )
    fake.routes[("PUT", "/upload/o1")] = put_s3
    fake.routes[("POST", "/objects/o1/uploading/commit")] = httpx.Response(200)

    result = await api.file.upload("p1", str(path))

    assert result == {"object_id": "o1", "mime_type": "application/pdf", "size": len(payload)}
    assert received == {"length": str(len(payload)), "chunked": None}
    assert fake.calls[0][3] == {"projectId": "p1", "mimeType": "application/pdf", "size": len(payload)}
    assert [c[1] for c in fake.calls] == ["/objects", "/upload/o1", "/objects/o1/uploading/commit"]


async def test_upload_rejects_unknown_mime_and_empty_file(api, tmp_path):
    unknown = tmp_path / "data.zzz"
    unknown.write_bytes(b"0123456789")
    with pytest.raises(ValueError, match="MIME"):
        await api.file.upload("p1", str(unknown))
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")
    with pytest.raises(ValueError, match="empty"):
        await api.file.upload("p1", str(empty))
    with pytest.raises(FileNotFoundError):
        await api.file.upload("p1", str(tmp_path / "missing.pdf"))
