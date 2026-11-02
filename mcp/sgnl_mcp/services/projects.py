import asyncio

from .common import page, pick


async def list_projects(app, take: int, skip: int) -> dict:
    items = await app.api.project.get_list(take=take, skip=skip)
    return {"data": [pick(p, ("id", "name", "code")) for p in items], "page": page(items, take, skip)}


async def get_project(app, project_id) -> dict:
    info, docs = await asyncio.gather(app.api.project.info(project_id), app.api.project.root_folder(project_id))
    info.pop("email", None)  # deprecated, always empty
    return {"data": {**info, "root_folder_id": docs.get("root_folder_id"),
                     "is_storage_configured": docs.get("is_storage_configured")}}


async def folder_tree(app, project_id) -> dict:
    return await app.cached(("tree", str(project_id)), lambda: app.api.folder.get_project_tree(project_id))


def _prune(node: dict, depth: int) -> dict:
    out = pick(node, ("id", "name", "type", "permissions", "color", "modified"))
    children = node.get("children") or []
    if depth <= 0:
        out["children_not_shown"] = len(children)
    else:
        out["children"] = [_prune(c, depth - 1) for c in children]
    return out


async def get_project_folder_tree(app, project_id, max_depth: int) -> dict:
    tree = await folder_tree(app, project_id)
    return {"data": _prune(tree, max_depth)}
