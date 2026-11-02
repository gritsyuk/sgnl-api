import asyncio
from datetime import date
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..errors import ToolFailure
from .common import page

IssueStatus = Literal["Draft", "Open", "InProgress", "Closed", "Void", "Rejected", "InReview", "NotAccepted"]
HEAVY_FIELDS = ("markup_data", "bim_data")
SIGNIFICANT = {"status", "responsible", "issue_type_id", "elimination_date"}


class Identity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    type: Literal["User", "Role"]


class IssueChange(BaseModel):
    """Fields an agent may change. `deleted`, markup and BIM data are deliberately absent."""

    model_config = ConfigDict(extra="forbid")
    id: UUID
    status: Optional[IssueStatus] = None
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    placement: Optional[str] = Field(None, max_length=1000)
    comment: Optional[str] = Field(None, max_length=1000, description="Comment added with the change")
    issue_type_id: Optional[UUID] = None
    responsible: Optional[Identity] = None
    observers: Optional[list[Identity]] = Field(None, max_length=200)
    elimination_date: Optional[date] = None
    clear_elimination_date: bool = False

    def changes(self) -> dict:
        out = self.model_dump(exclude={"id", "clear_elimination_date"}, exclude_none=True, mode="json")
        if self.clear_elimination_date:
            out["elimination_date"] = None
        return out

    def to_api(self) -> dict:
        body = {"id": str(self.id)}
        names = {"issue_type_id": "issueTypeId"}
        for key, value in self.changes().items():
            if key == "elimination_date":
                body["eliminationDate"] = {"value": value}
            else:
                body[names.get(key, key)] = value
        return body


async def issue_types(app, project_id) -> dict:
    types = await app.cached(("issue_types", str(project_id)),
                             lambda: app.api.issue_type.get_list({"projectId": project_id}))
    return {str(t["id"]): t.get("name") for t in types}


async def list_issues(app, project_id, *, take: int, skip: int, include_markup: bool, **filters) -> dict:
    flt = {"projectId": project_id, "includeMarkup": include_markup, "includeBimData": include_markup,
           **{k: v for k, v in filters.items() if v is not None}}
    issues, total, names = await asyncio.gather(
        app.api.issue.get_list(flt, take=take, skip=skip),
        app.api.issue.count(flt),
        issue_types(app, project_id),
    )
    data = []
    for issue in issues:
        if not include_markup:
            for heavy in HEAVY_FIELDS:
                issue.pop(heavy, None)
        issue["issue_type_name"] = names.get(str(issue.get("issue_type_id")))
        data.append(issue)
    return {"data": data, "page": page(issues, take, skip, total)}


def _current(issue: dict, field: str):
    value = issue.get(field)
    if field == "responsible" and isinstance(value, dict):
        return {"id": str(value.get("id")), "type": value.get("type")}
    if field == "observers" and isinstance(value, list):
        return [{"id": str(o.get("id")), "type": o.get("type")} for o in value]
    return value


async def update_issues(app, *, project_id, changes: list[IssueChange], confirmation_token=None) -> dict:
    if not 1 <= len(changes) <= 25:
        raise ToolFailure("INVALID_REQUEST", "Send from 1 to 25 issues per call")
    ids = [str(c.id) for c in changes]
    if len(set(ids)) != len(ids):
        raise ToolFailure("INVALID_REQUEST", "Each issue may appear only once per call")
    if any(not c.changes() for c in changes):
        raise ToolFailure("INVALID_REQUEST", "Every issue needs at least one field to change")
    args = {"project_id": project_id, "changes": [c.model_dump(mode="json") for c in changes]}

    async def snapshot_issues() -> dict:
        found = await app.api.issue.get_list({"projectId": project_id, "ids": ids}, take=25)
        by_id = {str(i["id"]): i for i in found}
        missing = [i for i in ids if i not in by_id]
        if missing:
            raise ToolFailure("NOT_FOUND", "Some issues are not in this project or are not visible", {"ids": missing})
        return by_id

    async def prepare():
        current = await snapshot_issues()
        rows = []
        for change in changes:
            issue = current[str(change.id)]
            diff = {}
            for field, new in change.changes().items():
                old = None if field == "comment" else _current(issue, field)
                if old != new:
                    diff[field] = {"before": old, "after": new}
            rows.append({"id": str(change.id), "number": issue.get("number"), "name": issue.get("name"),
                         "changes": diff, "significant": sorted(SIGNIFICANT & diff.keys())})
        preview = {"action": f"update {len(rows)} issue(s)", "issues": rows}
        return preview, {i: current[i].get("modified") for i in ids}

    async def execute(snapshot):
        await app.api.issue.update([c.to_api() for c in changes])
        after = await snapshot_issues()
        results = []
        for change in changes:
            issue = after[str(change.id)]
            not_applied = [f for f, v in change.changes().items()
                           if f != "comment" and _current(issue, f) != v]
            results.append({"id": str(change.id), "result": "not_applied" if not_applied else "applied",
                            "fields_not_applied": not_applied, "status": issue.get("status")})
        return {"issues": results}

    return await app.two_phase("update_issues", args, confirmation_token, prepare, execute,
                               objects={"project_id": project_id, "issue_ids": ids})
