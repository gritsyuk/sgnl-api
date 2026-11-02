import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from sgnl_api.file import file_info

from ..errors import ToolFailure
from ..guard import current_scope
from .common import UNCERTAIN, find_path, page, pick
from .projects import folder_tree

DOC_FIELDS = (
    "id", "name", "type", "folder_id", "top_version_id", "top_item_version_id", "top_version_number",
    "link", "deleted", "added", "added_by", "modified", "modified_by",
)
VERSION_FIELDS = ("id", "item_version_id", "item_version_number", "name", "size", "comment", "signatures_count")
MIN_SIZE = 10
MAX_SIZE = 5 * 1024 ** 3


# reading ---------------------------------------------------------------------------------------

async def search_documents(app, project_id, folder_id=None, *, take: int, skip: int, **filters) -> dict:
    root = folder_id or await app.root_folder_id(project_id)
    items = await app.api.item.search(root, take=take, skip=skip, **filters)
    return {"data": [pick(i, DOC_FIELDS) for i in items], "page": page(items, take, skip)}


async def find_document(app, project_id, document_id) -> Optional[dict]:
    root = await app.root_folder_id(project_id)
    found = await app.api.item.search(root, ids=[document_id], take=1)
    return found[0] if found else None


async def list_folder_documents(app, folder_id, deleted_only: bool, take: int, skip: int) -> dict:
    items, total = await asyncio.gather(
        app.api.item.get_list(folder_id, deleted=deleted_only, take=take, skip=skip),
        app.api.item.count(folder_id, deleted=deleted_only),
    )
    return {"data": [pick(i, DOC_FIELDS) for i in items], "page": page(items, take, skip, total)}


async def list_document_versions(app, item_id, take: int, skip: int) -> dict:
    items = await app.api.version.get_list(item_id, take=take, skip=skip)
    return {"data": [pick(v, VERSION_FIELDS) for v in items], "page": page(items, take, skip)}


async def get_document_version(app, item_version_id) -> dict:
    return {"data": await app.api.item.get_item_version(item_version_id)}


async def get_document_download_url(app, item_id, version_id) -> dict:
    ticket = await app.api.item.get_link(item_id, version_id)
    ttl = int(ticket.get("ttl_sec") or 0)
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat()
    return {
        "data": {"signed_url": ticket.get("signed_url"), "ttl_sec": ttl, "expires_at": expires_at},
        "warnings": ["The link grants access without authorization until it expires; do not share it further"],
    }


# uploading -------------------------------------------------------------------------------------

def resolve_upload_path(app, file_path: str) -> Path:
    """The file must exist under SGNL_MCP_UPLOAD_ROOT after resolving symlinks; anything else is refused."""
    root = app.settings.upload_root.resolve(strict=True)
    candidate = Path(file_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        real = candidate.resolve(strict=True)
    except (FileNotFoundError, RuntimeError):
        raise ToolFailure("INVALID_REQUEST", f"File not found under the upload directory: {file_path}")
    if not real.is_relative_to(root):
        raise ToolFailure("POLICY_DENIED", "Only files inside the configured upload directory can be uploaded")
    if not real.is_file():
        raise ToolFailure("INVALID_REQUEST", f"Not a regular file: {file_path}")
    if real.suffix.lower() not in app.settings.allowed_extensions:
        raise ToolFailure("INVALID_REQUEST", f"File type {real.suffix or '(none)'} is not allowed for upload",
                          {"allowed": list(app.settings.allowed_extensions)})
    size = real.stat().st_size
    if not MIN_SIZE <= size <= MAX_SIZE:
        raise ToolFailure("INVALID_REQUEST", f"File size must be from {MIN_SIZE} bytes to 5 GiB, got {size}")
    return real


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def _file_snapshot(path: Path) -> dict:
    try:
        mime, size = file_info(str(path))
    except ValueError as e:
        raise ToolFailure("INVALID_REQUEST", str(e))
    return {"sha256": await asyncio.to_thread(_sha256, path), "size": size, "mime_type": mime}


async def _upload_object(app, project_id, path: Path, mime_type: str) -> str:
    """Steps 1-3. A failure here leaves no document behind, so the whole call can be repeated."""
    scope = current_scope.get()
    scope.upload_window = True
    try:
        uploaded = await app.api.file.upload(project_id, str(path), mime_type=mime_type)
    except Exception as e:
        raise ToolFailure("UPLOAD_FAILED",
                          "Transferring the file failed before any document was created; request a new preview "
                          "and try again", {"reason": type(e).__name__}) from e
    finally:
        scope.upload_window = False
    return uploaded["object_id"]


async def _create_version(app, object_id, project_id, name: str) -> str:
    """Step 4."""
    try:
        return await app.api.version.create(object_id=object_id, project_id=project_id, name=name)
    except UNCERTAIN as e:
        raise ToolFailure("OUTCOME_UNKNOWN", "Creating the version failed without a clear answer; nothing was "
                          "attached to a document", {"object_id": object_id, "step": "version_create"}) from e


async def upload_document(app, *, project_id, folder_id, file_path: str, name: Optional[str],
                          naming_pattern_id=None, resume_version_id=None, confirmation_token=None) -> dict:
    path = resolve_upload_path(app, file_path)
    doc_name = name or path.name
    if not 1 <= len(doc_name) <= 255:
        raise ToolFailure("INVALID_REQUEST", "Document name must be 1-255 characters")
    args = {"project_id": project_id, "folder_id": folder_id, "file_path": str(path), "name": doc_name,
            "naming_pattern_id": naming_pattern_id, "resume_version_id": resume_version_id}

    async def prepare():
        tree = await folder_tree(app, project_id)
        folder_path = find_path(tree, folder_id)
        if folder_path is None:
            raise ToolFailure("NOT_FOUND", "The folder is not in this project or not visible to this account")
        snapshot = await _file_snapshot(path)
        same_name = await app.api.item.search(folder_id, name=doc_name, take=5)
        existing = [pick(i, ("id", "name", "top_version_number")) for i in same_name
                    if i.get("name") == doc_name and not i.get("deleted")]
        patterns = await app.api.folder_items_naming_pattern.find(folder_id)
        preview = {
            "action": "create a new document with its first version",
            "folder_path": " / ".join(folder_path),
            "name": doc_name,
            "file": path.name,
            **snapshot,
            "documents_with_same_name": existing,
            "folder_naming_patterns": (patterns or {}).get("value"),
            "resume_version_id": resume_version_id,
        }
        warnings = []
        if existing:
            warnings.append("A document with this name already exists here; to add a version use add_document_version")
        if preview["folder_naming_patterns"] and not naming_pattern_id:
            warnings.append("The folder has naming patterns; pass naming_pattern_id if the name must follow one")
        preview["warnings"] = warnings
        return preview, {**snapshot, "folder_id": str(folder_id)}

    async def execute(snapshot):
        started = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
        object_id = None
        if resume_version_id:
            version_id = resume_version_id
        else:
            object_id = await _upload_object(app, project_id, path, snapshot["mime_type"])
            version_id = await _create_version(app, object_id, project_id, doc_name)
        try:
            item_id = await app.api.item.create_file(doc_name, folder_id, version_id, naming_pattern_id)
        except UNCERTAIN as e:
            found = await app.api.item.search(folder_id, name=doc_name, added_from=started, take=5)
            match = [i for i in found if i.get("name") == doc_name]
            if not match:
                raise ToolFailure(
                    "OUTCOME_UNKNOWN",
                    "Creating the document failed without a clear answer and it was not found in the folder. "
                    "Repeat with resume_version_id to finish without uploading the file again.",
                    {"version_id": version_id, "object_id": object_id, "step": "item_create"},
                ) from e
            item_id = match[0]["id"]
        app.invalidate("tree")
        return {"item_id": item_id, "version_id": version_id, "object_id": object_id,
                "name": doc_name, "folder_id": str(folder_id)}

    return await app.two_phase("upload_document", args, confirmation_token, prepare, execute,
                               objects={"project_id": project_id, "folder_id": folder_id})


async def add_document_version(app, *, project_id, item_id, file_path: str, resume_version_id=None,
                               confirmation_token=None) -> dict:
    path = resolve_upload_path(app, file_path)
    args = {"project_id": project_id, "item_id": item_id, "file_path": str(path),
            "resume_version_id": resume_version_id}

    async def prepare():
        doc = await find_document(app, project_id, item_id)
        if doc is None or doc.get("deleted"):
            raise ToolFailure("NOT_FOUND", "Document not found in this project")
        if doc.get("type") not in ("File", None):
            raise ToolFailure("INVALID_REQUEST", f"Versions can only be added to File documents, this is {doc.get('type')}")
        snapshot = await _file_snapshot(path)
        preview = {
            "action": "add a new version to an existing document",
            "document": pick(doc, ("id", "name", "folder_id", "top_version_number")),
            "file": path.name,
            **snapshot,
            "resume_version_id": resume_version_id,
        }
        return preview, {**snapshot, "top_version_id": doc.get("top_version_id")}

    async def execute(snapshot):
        object_id = None
        if resume_version_id:
            version_id = resume_version_id
        else:
            object_id = await _upload_object(app, project_id, path, snapshot["mime_type"])
            version_id = await _create_version(app, object_id, project_id, path.name)
        try:
            await app.api.item.add_version(item_id, version_id)
        except UNCERTAIN as e:
            versions = await app.api.version.get_list(item_id, take=50)
            if not any(str(v.get("id")) == str(version_id) for v in versions):
                raise ToolFailure(
                    "OUTCOME_UNKNOWN",
                    "Attaching the version failed without a clear answer and it is not on the document. "
                    "Repeat with resume_version_id to finish without uploading the file again.",
                    {"version_id": version_id, "object_id": object_id, "step": "attach_version"},
                ) from e
        return {"item_id": str(item_id), "version_id": version_id, "object_id": object_id}

    return await app.two_phase("add_document_version", args, confirmation_token, prepare, execute,
                               objects={"project_id": project_id, "item_id": item_id})


async def update_document_version_comment(app, *, item_version_id, comment: str, confirmation_token=None) -> dict:
    if len(comment) > 255:
        raise ToolFailure("INVALID_REQUEST", "Comment must be at most 255 characters")
    args = {"item_version_id": item_version_id, "comment": comment}

    async def prepare():
        record = await app.api.item.get_item_version(item_version_id)
        versions = await app.api.version.get_list(record["item_id"], take=200)
        current = next((v for v in versions if str(v.get("item_version_id")) == str(item_version_id)), None)
        if current is None:
            raise ToolFailure("NOT_FOUND", "Version not found on its document")
        old = current.get("comment")
        preview = {"action": "change the version comment", "item_id": record["item_id"],
                   "version_number": current.get("item_version_number"), "comment_before": old, "comment_after": comment}
        return preview, {"comment": old}

    async def execute(snapshot):
        await app.api.item.update_version(item_version_id, comment=comment)
        return {"item_version_id": str(item_version_id), "comment": comment}

    return await app.two_phase("update_document_version_comment", args, confirmation_token, prepare, execute,
                               objects={"item_version_id": item_version_id})
