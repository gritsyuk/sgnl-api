from typing import Any, Iterable, Optional

from sgnl_api import SgnlRequestError, SgnlServerError

# Failures after which a write may or may not have been applied.
UNCERTAIN = (SgnlServerError, SgnlRequestError)


def pick(obj: dict, keys: Iterable[str]) -> dict:
    return {k: obj.get(k) for k in keys if k in obj}


def page(items: list, take: int, skip: int, total: Optional[int] = None) -> dict:
    info: dict[str, Any] = {"take": take, "skip": skip, "returned": len(items)}
    if total is not None:
        info["total"] = total
        info["has_more"] = skip + len(items) < total
    else:
        info["has_more"] = len(items) == take
    return info


def find_path(node: dict, folder_id: str, trail: tuple = ()) -> Optional[list[str]]:
    """Names from the project root down to folder_id in a folder tree, or None if it is not in the tree."""
    trail = trail + (node.get("name"),)
    if str(node.get("id")) == str(folder_id):
        return list(trail)
    for child in node.get("children") or []:
        found = find_path(child, folder_id, trail)
        if found:
            return found
    return None
