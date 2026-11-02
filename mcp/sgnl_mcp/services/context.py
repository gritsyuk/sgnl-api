"""get_document_context: one call that gathers what is known about a document (spec section 5.4)."""
import asyncio
from collections import Counter

from ..errors import ToolFailure, describe_api_error
from .common import pick
from .documents import DOC_FIELDS, VERSION_FIELDS, find_document

BLOCKS = ("versions", "attributes", "issues", "reviews", "signatures", "transfers")
MAX_VERSIONS = 50
SIGNED_VERSIONS = 5
ISSUE_FIELDS = ("id", "number", "name", "status", "issue_type_id", "responsible", "elimination_date",
                "item_version", "added", "modified")


class Block:
    def __init__(self, requested: bool):
        self.status = "not_requested" if not requested else "success"
        self.data = None
        self.warnings: list[str] = []

    def fail(self, error: Exception) -> None:
        failure = describe_api_error(error, writing=False)
        self.status = "error"
        self.warnings.append(f"{failure.code}: {failure.message}")


async def _versions(app, document_id, block: Block):
    versions = await app.api.version.get_list(document_id, take=MAX_VERSIONS)
    block.data = [pick(v, VERSION_FIELDS) for v in versions]
    if len(versions) == MAX_VERSIONS:
        block.status = "partial"
        block.warnings.append(f"Only the first {MAX_VERSIONS} versions are shown")
    return versions


async def _attributes(app, project_id, document_id, block: Block):
    values = await app.api.attribute_value.list_items({"projectId": project_id, "itemIds": [document_id]})
    names = {}
    try:
        types = await app.cached(("attr_types", str(project_id)),
                                 lambda: app.api.attribute_type.get_list({"projectId": project_id}))
        names = {str(t["id"]): t for t in types}
    except Exception as e:  # names are a nicety; values are still useful without them
        block.warnings.append(f"Attribute names unavailable: {type(e).__name__}")
    result = {}
    for v in values:
        data = v.get("data") or {}
        if data.get("deleted"):
            continue
        attr_type = names.get(str(v.get("attribute_type_id")), {})
        value = data.get(str(data.get("type", "")).lower())
        if data.get("type") == "List" and attr_type.get("list"):
            value = next((i["name"] for i in attr_type["list"] if str(i["id"]) == str(value)), value)
        result[attr_type.get("name") or str(v.get("attribute_type_id"))] = value
    block.data = result


async def _issues(app, project_id, document_id, block: Block):
    flt = {"projectId": project_id, "itemIds": [document_id], "deleted": False}
    issues, total = await asyncio.gather(app.api.issue.get_list(flt, take=100), app.api.issue.count(flt))
    block.data = {"total": total, "by_status": dict(Counter(i.get("status") for i in issues)),
                  "items": [pick(i, ISSUE_FIELDS) for i in issues]}
    if total > len(issues):
        block.status = "partial"
        block.warnings.append(f"{len(issues)} of {total} issues shown; use list_issues for the rest")


async def _reviews(app, project_id, versions, block: Block):
    ids = [v["item_version_id"] for v in versions if v.get("item_version_id")][:50]
    if not ids:
        block.data = []
        return
    block.data = await app.api.review_item.get_statuses(project_id, ids)


async def _signatures(app, document_id, versions, block: Block):
    embedded = await app.api.embedded_signature.get_list(document_id)
    recent = sorted(versions, key=lambda v: v.get("item_version_number") or 0, reverse=True)[:SIGNED_VERSIONS]
    cades = []
    for v in recent:
        if not v.get("signatures_count"):
            continue
        for s in await app.api.cades_signature.get_list(v["id"]):
            cades.append({"version_id": v["id"], **pick(s, ("id", "subject", "certificate_id"))})
    block.data = {"embedded": [pick(s, ("id", "version_id", "certificate_id", "company_name", "owner_name"))
                               for s in embedded],
                  "cades": cades}
    if len(versions) > SIGNED_VERSIONS:
        block.status = "partial"
        block.warnings.append(f"CAdES signatures checked for the latest {SIGNED_VERSIONS} versions only")


async def get_document_context(app, project_id, document_id, include: set[str], mode: str) -> dict:
    blocks = {name: Block(name in include) for name in BLOCKS}
    document = await find_document(app, project_id, document_id)
    if document is None:
        raise ToolFailure("NOT_FOUND", "Document not found in this project")

    if "transfers" in include:
        blocks["transfers"].status = "not_supported"
        blocks["transfers"].warnings.append(
            "SIGNAL API has no lookup from a document to the transfers that include it"
        )

    async def guarded(block: Block, coro):
        try:
            return await coro
        except Exception as e:  # one block failing must not lose the others
            block.fail(e)
            return None

    versions = []
    need_versions = include & {"versions", "reviews", "signatures"}
    if need_versions:
        vb = blocks["versions"] if "versions" in include else Block(True)
        versions = await guarded(vb, _versions(app, document_id, vb)) or []
        if "versions" not in include and vb.status == "error":
            for name in ("reviews", "signatures"):
                if name in include:
                    blocks[name].fail(Exception("versions unavailable"))

    tasks = []
    if "attributes" in include:
        tasks.append(guarded(blocks["attributes"], _attributes(app, project_id, document_id, blocks["attributes"])))
    if "issues" in include:
        tasks.append(guarded(blocks["issues"], _issues(app, project_id, document_id, blocks["issues"])))
    if "reviews" in include and blocks["reviews"].status != "error":
        tasks.append(guarded(blocks["reviews"], _reviews(app, project_id, versions, blocks["reviews"])))
    if "signatures" in include and blocks["signatures"].status != "error":
        tasks.append(guarded(blocks["signatures"], _signatures(app, document_id, versions, blocks["signatures"])))
    await asyncio.gather(*tasks)

    doc = pick(document, DOC_FIELDS)
    doc["project_id"] = str(project_id)
    data = {"document": doc}
    if mode == "full":
        for name, block in blocks.items():
            data[name] = block.data
    else:
        data["summary"] = _summary(blocks)
    data["data_availability"] = {"document": "success", **{n: b.status for n, b in blocks.items()}}
    warnings = [f"{n}: {w}" for n, b in blocks.items() for w in b.warnings]
    return {"data": data, "warnings": warnings}


def _summary(blocks: dict) -> dict:
    out = {}
    versions = blocks["versions"].data
    if versions:
        top = max(versions, key=lambda v: v.get("item_version_number") or 0)
        out["versions"] = {"count": len(versions), "latest": pick(top, ("item_version_number", "name", "comment"))}
    if blocks["attributes"].data is not None:
        out["attributes"] = blocks["attributes"].data
    if blocks["issues"].data is not None:
        out["issues"] = {k: blocks["issues"].data[k] for k in ("total", "by_status")}
    if blocks["reviews"].data is not None:
        out["reviews"] = [pick(r, ("item_version_id", "status", "review_id", "review_cipher")) for r in blocks["reviews"].data]
    if blocks["signatures"].data is not None:
        out["signatures"] = {"embedded": len(blocks["signatures"].data["embedded"]),
                             "cades": len(blocks["signatures"].data["cades"])}
    return out
