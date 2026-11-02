import httpx

from conftest import PROJECT, REVIEW, TYPE, accept_elicitation, call


def _review_routes(fake, status="Draft", items=2):
    review = {"id": REVIEW, "number": 3, "cipher": "R-3", "name": "Stage P", "status": status,
              "topVersion": {"id": "rv1", "number": 1, "itemsCount": items}}
    fake.routes[("POST", "/reviews")] = lambda req, body: [review]
    fake.routes[("POST", "/reviews/count")] = lambda req, body: {"data": 1}
    fake.routes[("GET", "/reviews/types/names")] = lambda req, body: [
        {"id": TYPE, "name": "Expertise", "topVersionId": "t1", "topVersionNumber": 1}]
    fake.routes[("POST", "/reviews/versions/item-versions")] = lambda req, body: {"rv1": ["iv-in-review"]}
    fake.routes[("POST", "/reviews/create")] = lambda req, body: "new-review"
    fake.routes[("POST", "/reviews/items/add")] = lambda req, body: httpx.Response(200)

    def start(req, body):
        review["status"] = "InProgress"
        return httpx.Response(200)
    fake.routes[("POST", "/reviews/process/start")] = start
    return review


async def test_list_reviews(connect, fake):
    _review_routes(fake)
    async with connect() as c:
        r = await call(c, "list_reviews", project_id=PROJECT)
    assert r["data"][0]["top_version"]["items_count"] == 2 and r["page"]["total"] == 1


async def test_create_review_uses_configured_actor(connect, fake):
    _review_routes(fake)
    async with connect("write") as c:
        p = await call(c, "create_review", project_id=PROJECT, review_type_id=TYPE, name="Stage P", cipher="R-3")
        done = await call(c, "create_review", project_id=PROJECT, review_type_id=TYPE, name="Stage P", cipher="R-3",
                          confirmation_token=p["confirmation_token"])
    assert done["data"]["review_id"] == "new-review"
    body = fake.sent("POST", "/reviews/create")[0][2]
    assert body["behalfUserId"] == "55555555-5555-5555-5555-555555555555"


async def test_add_documents_to_review_reports_per_item(connect, fake):
    _review_routes(fake)
    ids = ["00000000-0000-0000-0000-0000000000d1", "00000000-0000-0000-0000-0000000000d2"]
    async with connect("write") as c:
        p = await call(c, "add_documents_to_review", project_id=PROJECT, review_id=REVIEW, item_version_ids=ids)
        done = await call(c, "add_documents_to_review", project_id=PROJECT, review_id=REVIEW, item_version_ids=ids,
                          confirmation_token=p["confirmation_token"])
    assert [i["result"] for i in done["data"]["items"]] == ["added", "added"]


async def test_start_review_with_confirmation(connect, fake):
    _review_routes(fake)
    async with connect("workflow", elicitation=accept_elicitation()) as c:
        p = await call(c, "prepare_start_review", project_id=PROJECT, review_id=REVIEW)
        done = await call(c, "start_review", project_id=PROJECT, review_id=REVIEW,
                          confirmation_token=p["confirmation_token"])
    assert done["data"]["status_after"] == "InProgress"


async def test_only_draft_review_can_start(connect, fake):
    _review_routes(fake, status="InProgress")
    async with connect("workflow", elicitation=accept_elicitation()) as c:
        r = await call(c, "prepare_start_review", project_id=PROJECT, review_id=REVIEW)
    assert r["error"]["code"] == "INVALID_STATE"


async def test_create_transfer_checks_type_belongs_to_project(connect, fake):
    fake.routes[("POST", "/documents-transfers/types")] = lambda req, body: [{"id": TYPE, "name": "Main"}]
    fake.routes[("POST", "/documents-transfers/create")] = lambda req, body: "new-transfer"
    async with connect("write") as c:
        wrong = await call(c, "create_document_transfer", project_id=PROJECT,
                           documents_transfer_type_id="00000000-0000-0000-0000-0000000000e1", cipher="T", name="N")
        p = await call(c, "create_document_transfer", project_id=PROJECT, documents_transfer_type_id=TYPE,
                       cipher="T-13", name="Set 13")
        done = await call(c, "create_document_transfer", project_id=PROJECT, documents_transfer_type_id=TYPE,
                          cipher="T-13", name="Set 13", confirmation_token=p["confirmation_token"])
    assert wrong["error"]["code"] == "NOT_FOUND"
    assert done["data"]["transfer_id"] == "new-transfer"
