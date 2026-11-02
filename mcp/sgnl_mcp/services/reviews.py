import asyncio

from ..errors import ToolFailure, describe_api_error
from ..profiles import Risk
from .common import UNCERTAIN, page, pick

REVIEW_FIELDS = ("id", "number", "cipher", "name", "status", "plan_date", "contract_date", "plan_days_diff",
                 "first_version_started", "top_version_started", "added", "added_by", "modified")
MAX_ADD = 20


async def list_reviews(app, project_id, *, order, is_order_asc, take: int, skip: int) -> dict:
    find = {"projectId": project_id}
    reviews, total = await asyncio.gather(
        app.api.review.get_list(find, order=order, is_order_asc=is_order_asc, take=take, skip=skip),
        app.api.review.count(find),
    )
    data = []
    for r in reviews:
        row = pick(r, REVIEW_FIELDS)
        top = r.get("top_version") or {}
        row["top_version"] = pick(top, ("id", "number", "items_count", "rejected_items_count", "stages_status"))
        data.append(row)
    return {"data": data, "page": page(reviews, take, skip, total)}


async def get_review_details(app, review_version_ids: list) -> dict:
    versions, item_versions = await asyncio.gather(
        app.api.review.get_versions(review_version_ids),
        app.api.review.find_item_version_ids_by_review_version_ids(review_version_ids),
    )
    return {"data": {"versions": versions, "item_version_ids": item_versions}}


async def get_document_review_status(app, project_id, item_version_ids: list, review_id=None) -> dict:
    return {"data": await app.api.review_item.get_statuses(project_id, item_version_ids, review_id)}


async def review_types(app, project_id) -> list:
    return await app.cached(("review_types", str(project_id)), lambda: app.api.review_type.get_names(project_id))


async def list_review_types(app, project_id) -> dict:
    return {"data": await review_types(app, project_id)}


async def _review(app, project_id, review_id) -> dict:
    found = await app.api.review.get_list({"projectId": project_id, "ids": [review_id]}, take=1)
    if not found:
        raise ToolFailure("NOT_FOUND", "Review not found in this project")
    return found[0]


async def create_review(app, *, project_id, review_type_id, name: str, cipher: str, plan_date=None,
                        contract_date=None, comment=None, confirmation_token=None) -> dict:
    args = {"project_id": project_id, "review_type_id": review_type_id, "name": name, "cipher": cipher,
            "plan_date": plan_date.isoformat() if plan_date else None,
            "contract_date": contract_date.isoformat() if contract_date else None, "comment": comment}

    async def prepare():
        types = await review_types(app, project_id)
        chosen = next((t for t in types if str(t["id"]) == str(review_type_id)), None)
        if chosen is None:
            raise ToolFailure("NOT_FOUND", "This review type does not belong to the project")
        preview = {"action": "create a review (draft, not started)", "type": chosen, "name": name,
                   "cipher": cipher, "plan_date": args["plan_date"], "contract_date": args["contract_date"],
                   "comment": comment, "on_behalf_of_user_id": str(app.settings.actor_user_id)}
        return preview, {"type_id": str(chosen["id"])}

    async def execute(snapshot):
        review_id = await app.api.review.create(
            project_id=project_id, review_type_id=review_type_id, name=name, cipher=cipher,
            behalf_user_id=app.settings.actor_user_id, plan_date=args["plan_date"],
            contract_date=args["contract_date"], comment=comment)
        return {"review_id": review_id}

    return await app.two_phase("create_review", args, confirmation_token, prepare, execute,
                               objects={"project_id": project_id})


async def add_documents_to_review(app, *, project_id, review_id, item_version_ids: list,
                                  confirmation_token=None) -> dict:
    unique = list(dict.fromkeys(str(i) for i in item_version_ids))
    if not 1 <= len(unique) <= MAX_ADD:
        raise ToolFailure("INVALID_REQUEST", f"Add from 1 to {MAX_ADD} document versions per call")
    args = {"project_id": project_id, "review_id": review_id, "item_version_ids": unique}

    async def prepare():
        review = await _review(app, project_id, review_id)
        if review.get("status") in ("Completed", "Deleted", "Cancelled"):
            raise ToolFailure("INVALID_STATE", f"The review is {review.get('status')}; documents cannot be added")
        top = review.get("top_version") or {}
        included = set()
        if top.get("id"):
            grouped = await app.api.review.find_item_version_ids_by_review_version_ids([top["id"]])
            included = {str(i) for ids in (grouped or {}).values() for i in ids}
        to_add = [i for i in unique if i not in included]
        if not to_add:
            raise ToolFailure("NOTHING_TO_DO", "All these document versions are already in the review")
        preview = {"action": "add document versions to the review",
                   "review": pick(review, ("id", "number", "cipher", "name", "status")),
                   "to_add": to_add, "already_included": [i for i in unique if i in included]}
        return preview, {"status": review.get("status"), "to_add": to_add}

    async def execute(snapshot):
        results = []
        for n, version_id in enumerate(snapshot["to_add"]):
            try:
                await app.api.review_item.add(review_id, version_id)
                results.append({"item_version_id": version_id, "result": "added"})
            except UNCERTAIN:
                results.append({"item_version_id": version_id, "result": "unknown"})
                results += [{"item_version_id": v, "result": "not_sent"} for v in snapshot["to_add"][n + 1:]]
                break
            except Exception as e:
                failure = describe_api_error(e, writing=True)
                results.append({"item_version_id": version_id, "result": "failed", "error": failure.code})
        return {"review_id": str(review_id), "items": results}

    return await app.two_phase("add_documents_to_review", args, confirmation_token, prepare, execute,
                               objects={"project_id": project_id, "review_id": review_id})


def _start_flow(app, project_id, review_id, comment):
    async def prepare():
        review = await _review(app, project_id, review_id)
        if review.get("status") != "Draft":
            raise ToolFailure("INVALID_STATE", f"Only a draft review can be started; this one is {review.get('status')}")
        top = review.get("top_version") or {}
        if not top.get("items_count"):
            raise ToolFailure("INVALID_STATE", "The review has no documents")
        preview = {"action": "START the review process",
                   "review": pick(review, ("id", "number", "cipher", "name", "status")),
                   "documents": top.get("items_count"), "comment": comment,
                   "on_behalf_of_user_id": str(app.settings.actor_user_id),
                   "note": "Starting is not approval: the documents still go through the review stages"}
        return preview, {"status": review.get("status"), "documents": top.get("items_count")}

    async def execute(snapshot):
        try:
            await app.api.review_process.start(review_id, behalf_user_id=app.settings.actor_user_id, comment=comment)
        except UNCERTAIN as e:
            raise ToolFailure("OUTCOME_UNKNOWN", "Starting failed without a clear answer; it was NOT retried. "
                              "Check the review status before doing anything else.") from e
        after = await _review(app, project_id, review_id)
        return {"review_id": str(review_id), "status_after": after.get("status")}

    return prepare, execute


async def prepare_start_review(app, *, project_id, review_id, comment=None) -> dict:
    args = {"project_id": project_id, "review_id": review_id, "comment": comment}
    prepare, execute = _start_flow(app, project_id, review_id, comment)
    return await app.two_phase("start_review", args, None, prepare, execute, risk=Risk.WORKFLOW,
                               objects={"review_id": review_id})


async def start_review(app, *, project_id, review_id, comment=None, confirmation_token: str) -> dict:
    args = {"project_id": project_id, "review_id": review_id, "comment": comment}
    prepare, execute = _start_flow(app, project_id, review_id, comment)
    return await app.two_phase("start_review", args, confirmation_token, prepare, execute, risk=Risk.WORKFLOW,
                               objects={"review_id": review_id}, confirmed_by="elicitation")
