import asyncio
import contextlib
import json
import re
from typing import Callable, Optional

import httpx
import pytest
from mcp import Client
from mcp.types import ElicitResult

from sgnl_mcp.config import Settings
from sgnl_mcp.runtime import App
from sgnl_mcp.server import build_server

PROJECT = "11111111-1111-1111-1111-111111111111"
ROOT = "22222222-2222-2222-2222-222222222222"
FOLDER = "33333333-3333-3333-3333-333333333333"
DOC = "44444444-4444-4444-4444-444444444444"
ACTOR = "55555555-5555-5555-5555-555555555555"
TRANSFER = "66666666-6666-6666-6666-666666666666"
ISSUE = "77777777-7777-7777-7777-777777777777"
TYPE = "88888888-8888-8888-8888-888888888888"
REVIEW = "99999999-9999-9999-9999-999999999999"


class FakeSignal:
    """A small in-memory SIGNAL API. Handlers get (request, body) and return a Response or JSON-able value."""

    def __init__(self):
        self.calls: list[tuple[str, str, Optional[object]]] = []
        self.routes: dict[tuple[str, str], Callable] = {}
        self.in_flight = 0
        self.max_in_flight = 0
        self.delay = 0.0
        self.issue = {"id": ISSUE, "number": 7, "name": "Crack in wall", "status": "Open",
                      "issueTypeId": TYPE, "modified": "2026-10-01T10:00:00Z", "eliminationDate": "2026-11-30",
                      "responsible": {"id": ACTOR, "type": "User"}, "observers": [], "markupData": {"big": True}}
        self.transfer = {"id": TRANSFER, "name": "Set 12", "cipher": "T-12", "number": 12, "status": "Draft",
                         "deleted": False, "documentsTransferType": {"id": TYPE, "name": "Main", "settings": {}}}
        self.transfer_items = [{"id": "ti1", "itemVersionId": "iv-old", "itemName": "Old.pdf"}]
        self.items_created = []
        self.fail_item_create = False
        self._defaults()

    def route(self, method: str, path: str):
        def deco(fn):
            self.routes[(method, path)] = fn
            return fn
        return deco

    def _defaults(self):
        r = self.route
        r("GET", "/projects")(lambda req, body: [{"id": PROJECT, "name": "Tower", "code": "TW"}])
        r("GET", f"/projects/{PROJECT}")(lambda req, body: {"id": PROJECT, "name": "Tower", "code": "TW",
                                                           "email": "", "address": "Main st", "latitude": 1, "longitude": 2})
        r("GET", f"/docs/projects/{PROJECT}")(lambda req, body: {"rootFolderId": ROOT, "isStorageConfigured": True})
        r("GET", f"/projects/{PROJECT}/folders/tree")(lambda req, body: {
            "id": ROOT, "name": "Root", "permissions": "Update", "children": [
                {"id": FOLDER, "name": "Drawings", "permissions": "Update", "children": [
                    {"id": "deep", "name": "Deep", "children": []}]}]})
        r("POST", "/items/search")(self._search)
        r("GET", "/versions")(lambda req, body: [
            {"id": "v1", "itemVersionId": "iv1", "itemVersionNumber": 1, "name": "A.pdf", "size": 10, "comment": "old",
             "signaturesCount": 1},
            {"id": "v2", "itemVersionId": "iv2", "itemVersionNumber": 2, "name": "A.pdf", "size": 12, "comment": None,
             "signaturesCount": 0}])
        r("POST", "/attributes/values/items")(lambda req, body: [
            {"attributeId": "a1", "attributeTypeId": "at1", "itemId": DOC, "data": {"type": "Text", "deleted": False, "text": "КЖ"}}])
        r("POST", "/attributes/types")(lambda req, body: [{"id": "at1", "name": "Раздел", "type": "Text"}])
        r("POST", "/issues")(self._issues)
        r("POST", "/issues/count")(lambda req, body: {"data": 1})
        r("POST", "/issues/types")(lambda req, body: [{"id": TYPE, "name": "Defect"}])
        r("PATCH", "/issues")(self._update_issues)
        r("POST", "/reviews/items")(lambda req, body: [{"itemVersionId": "iv2", "status": "InReview", "reviewId": REVIEW}])
        r("GET", "/embedded/signatures")(lambda req, body: [])
        r("GET", "/cades/signatures")(lambda req, body: [{"id": "s1", "subject": "Ivanov", "certificateId": "c1"}])
        r("GET", "/company/users")(lambda req, body: [{"id": ACTOR, "email": "agent@x"}])
        r("GET", "/naming-patterns/folder-items/find")(lambda req, body: {"value": None})
        r("PUT", "/objects")(lambda req, body: {"objectId": "obj1", "signedUrl": "https://s3.example/put/obj1?X-Amz-Signature=abc", "ttlSec": 600})
        r("PUT", "/put/obj1")(lambda req, body: httpx.Response(200))
        r("POST", "/objects/obj1/uploading/commit")(lambda req, body: httpx.Response(200))
        r("POST", "/versions")(lambda req, body: {"data": "ver1"})
        r("PUT", "/items/file")(self._create_item)
        r("GET", "/documents-transfers")(lambda req, body: self.transfer)
        r("POST", "/documents-transfer-items")(lambda req, body: self.transfer_items)
        r("POST", "/documents-transfer-items/count")(lambda req, body: {"data": len(self.transfer_items)})
        r("POST", "/documents-transfer-acceptances/send")(self._send)

    def _search(self, req, body):
        docs = [{"id": DOC, "name": "A.pdf", "type": "File", "folderId": FOLDER, "topVersionId": "v2",
                 "topItemVersionId": "iv2", "topVersionNumber": 2, "deleted": False}]
        docs += self.items_created
        if body.get("ids"):
            docs = [d for d in docs if d["id"] in body["ids"]]
        if body.get("name"):
            docs = [d for d in docs if d["name"] == body["name"]]
        return docs

    def _issues(self, req, body):
        return [dict(self.issue)]

    def _update_issues(self, req, body):
        for change in body:
            if change["id"] == ISSUE:
                for k, v in change.items():
                    if k == "eliminationDate":
                        self.issue["eliminationDate"] = v["value"]
                    elif k != "comment":
                        self.issue[k] = v
                self.issue["modified"] = "2026-10-02T10:00:00Z"
        return httpx.Response(200)

    def _create_item(self, req, body):
        if self.fail_item_create:
            return httpx.Response(503, text="unavailable")
        self.items_created.append({"id": "new-item", "name": body["name"], "type": "File", "folderId": body["folderId"]})
        return {"data": "new-item"}

    def _send(self, req, body):
        self.transfer["status"] = "Sent"
        return httpx.Response(200)

    async def handler(self, request: httpx.Request) -> httpx.Response:
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            path = request.url.path.replace("/public/v1", "")
            if path == "/auth/token":
                return httpx.Response(200, json={"token": "jwt-secret-token", "expiresIn": 3600})
            body = None
            if request.headers.get("content-type") == "application/json" and request.content:
                body = json.loads(request.content)
            self.calls.append((request.method, path, body))
            fn = self.routes.get((request.method, path))
            if fn is None:
                return httpx.Response(404, text=f"no fake route {request.method} {path}")
            result = fn(request, body)
            return result if isinstance(result, httpx.Response) else httpx.Response(200, json=result)
        finally:
            self.in_flight -= 1

    def sent(self, method: str, path: str) -> list:
        return [c for c in self.calls if c[0] == method and c[1] == path]


@pytest.fixture
def fake():
    return FakeSignal()


@pytest.fixture
def upload_root(tmp_path):
    root = tmp_path / "uploads"
    root.mkdir()
    (root / "A2.pdf").write_bytes(b"%PDF-1.7 " + b"x" * 100)
    return root


@pytest.fixture
def make_settings(tmp_path, upload_root):
    def make(profile="read", **extra) -> Settings:
        values = dict(client_id="client", client_secret="super-secret-value", profile=profile,
                      actor_user_id=ACTOR, upload_root=upload_root, audit_path=tmp_path / "audit.jsonl",
                      state_path=tmp_path / "state.sqlite", rate_per_sec=10, burst=50)
        values.update(extra)
        return Settings(**values)
    return make


def accept_elicitation(confirm=True):
    async def callback(context, params):
        accept_elicitation.messages.append(params.message)
        return ElicitResult(action="accept", content={"confirm": confirm})
    return callback


accept_elicitation.messages = []


async def decline_elicitation(context, params):
    return ElicitResult(action="decline")


@pytest.fixture
def connect(fake, make_settings):
    @contextlib.asynccontextmanager
    async def open_client(profile="read", elicitation=None, **extra):
        settings = make_settings(profile, **extra)
        app = App(settings, inner_transport=httpx.MockTransport(fake.handler))
        server, _ = build_server(settings, app)
        async with Client(server, elicitation_callback=elicitation) as client:
            client.app = app
            yield client
    return open_client


async def call(client, tool: str, /, **arguments) -> dict:
    result = await client.call_tool(tool, arguments)
    if result.structured_content is not None:
        return result.structured_content
    text = result.content[0].text if result.content else ""
    try:
        return json.loads(text)
    except ValueError:
        return {"success": False, "error": {"code": "CLIENT_ERROR", "message": text}, "is_error": result.is_error}
