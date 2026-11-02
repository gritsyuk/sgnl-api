import asyncio

import httpx

from conftest import DOC, FOLDER, PROJECT, ROOT, call


async def test_list_projects(connect, fake):
    async with connect() as c:
        r = await call(c, "list_projects")
    assert r["success"] and r["data"] == [{"id": PROJECT, "name": "Tower", "code": "TW"}]
    assert r["page"]["returned"] == 1


async def test_get_project_merges_root_folder_and_drops_email(connect):
    async with connect() as c:
        r = await call(c, "get_project", project_id=PROJECT)
    assert r["data"]["root_folder_id"] == ROOT and "email" not in r["data"]


async def test_search_uses_project_root_and_caches_it(connect, fake):
    async with connect() as c:
        await call(c, "search_documents", project_id=PROJECT, name="A.pdf")
        await call(c, "search_documents", project_id=PROJECT, suffixes=["pdf"])
    assert len(fake.sent("GET", f"/docs/projects/{PROJECT}")) == 1
    bodies = [b for m, p, b in fake.calls if p == "/items/search"]
    assert bodies[0]["folderId"] == ROOT and bodies[1]["suffixes"] == ["pdf"]


async def test_folder_tree_is_pruned(connect):
    async with connect() as c:
        r = await call(c, "get_project_folder_tree", project_id=PROJECT, max_depth=1)
    drawings = r["data"]["children"][0]
    assert drawings["id"] == FOLDER and drawings["children_not_shown"] == 1


async def test_download_url_has_expiry(connect, fake):
    fake.routes[("GET", "/items/download")] = lambda req, body: {"signedUrl": "https://s3/x?X-Amz-Signature=1", "ttlSec": 300}
    async with connect() as c:
        r = await call(c, "get_document_download_url", item_id=DOC, version_id="00000000-0000-0000-0000-000000000002")
    assert r["data"]["ttl_sec"] == 300 and r["data"]["expires_at"]


async def test_list_issues_hides_markup_and_names_type(connect):
    async with connect() as c:
        r = await call(c, "list_issues", project_id=PROJECT)
    issue = r["data"][0]
    assert "markup_data" not in issue and issue["issue_type_name"] == "Defect"
    assert r["page"]["total"] == 1


async def test_document_context_keeps_other_blocks_when_one_fails(connect, fake):
    fake.routes[("POST", "/issues")] = lambda req, body: httpx.Response(500, text="boom")
    async with connect() as c:
        r = await call(c, "get_document_context", project_id=PROJECT, document_id=DOC, include_all=True, mode="full")
    availability = r["data"]["data_availability"]
    assert r["success"]
    assert availability["issues"] == "error"
    assert availability["versions"] == "success" and availability["reviews"] == "success"
    assert availability["transfers"] == "not_supported"
    assert r["data"]["attributes"] == {"Раздел": "КЖ"}
    assert any(w.startswith("issues:") for w in r["warnings"])


async def test_document_context_summary_and_not_requested(connect, fake):
    async with connect() as c:
        r = await call(c, "get_document_context", project_id=PROJECT, document_id=DOC, include_versions=True)
    availability = r["data"]["data_availability"]
    assert availability["versions"] == "success" and availability["issues"] == "not_requested"
    assert r["data"]["summary"]["versions"]["latest"]["item_version_number"] == 2
    assert not fake.sent("POST", "/issues")


async def test_document_not_found(connect):
    async with connect() as c:
        r = await call(c, "get_document_context", project_id=PROJECT,
                       document_id="00000000-0000-0000-0000-00000000dead", include_all=True)
    assert not r["success"] and r["error"]["code"] == "NOT_FOUND"


async def test_api_error_codes(connect, fake):
    fake.routes[("GET", "/projects")] = lambda req, body: httpx.Response(403, text="nope")
    async with connect() as c:
        r = await call(c, "list_projects")
    assert r["error"]["code"] == "FORBIDDEN" and r["request_id"]


async def test_rate_limit_and_concurrency(connect, fake):
    fake.delay = 0.02
    async with connect(max_concurrency=2) as c:
        await asyncio.gather(*[call(c, "list_projects") for _ in range(12)])
    assert fake.max_in_flight <= 2


async def test_rate_limit_spaces_requests(connect, fake):
    async with connect(rate_per_sec=10, burst=1) as c:
        started = asyncio.get_running_loop().time()
        await asyncio.gather(*[call(c, "list_projects") for _ in range(6)])
        elapsed = asyncio.get_running_loop().time() - started
    assert elapsed >= 0.45  # 5 waits of 1/10 s after the first request
