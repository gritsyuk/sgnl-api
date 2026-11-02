import asyncio
from typing import Optional

from ..errors import ToolFailure
from ..profiles import Risk
from .common import UNCERTAIN, page, pick

TRANSFER_FIELDS = (
    "id", "number", "name", "cipher", "status", "deleted", "documents_transfer_type_id",
    "documents_transfer_type_name", "contract_number", "company_sender", "company_recipient",
    "sender_id", "sent_at", "received_by", "received_at", "added", "added_by",
)
ITEM_FIELDS = ("id", "item_id", "item_name", "item_folder_id", "item_version_id", "version_id",
               "version_number", "virtual_version_number", "version_size", "version_modified")
# Once a transfer has left, its content and recipient must not change.
CLOSED_STATUSES = {"Sent", "Viewed", "Received", "Rejected"}
ITEMS_PAGE = 200
MAX_ITEM_PAGES = 4


async def list_document_transfers(app, project_id, *, take: int, skip: int, **filters) -> dict:
    flt = {"projectId": project_id, **{k: v for k, v in filters.items() if v is not None}}
    items, total = await asyncio.gather(
        app.api.documents_transfer.get_list(flt, take=take, skip=skip),
        app.api.documents_transfer.count(flt),
    )
    return {"data": [pick(t, TRANSFER_FIELDS) for t in items], "page": page(items, take, skip, total)}


async def get_document_transfer(app, transfer_id) -> dict:
    return {"data": await app.api.documents_transfer.get(transfer_id)}


async def list_transfer_documents(app, transfer_id, take: int, skip: int) -> dict:
    flt = {"documentsTransferId": transfer_id}
    items, total = await asyncio.gather(
        app.api.documents_transfer_item.get_list(flt, take=take, skip=skip),
        app.api.documents_transfer_item.count(flt),
    )
    return {"data": [pick(i, ITEM_FIELDS) for i in items], "page": page(items, take, skip, total)}


async def transfer_types(app, project_id) -> list:
    return await app.cached(
        ("transfer_types", str(project_id)),
        lambda: app.api.documents_transfer_type.get_list({"projectId": project_id, "deleted": False}),
    )


async def list_document_transfer_types(app, project_id) -> dict:
    types = await transfer_types(app, project_id)
    return {"data": [pick(t, ("id", "name", "settings", "default_recipient", "acceptance_certificate_folder_id"))
                     for t in types]}


async def _open_transfer(app, transfer_id) -> dict:
    transfer = await app.api.documents_transfer.get(transfer_id)
    if transfer.get("deleted"):
        raise ToolFailure("INVALID_STATE", "The transfer is deleted")
    if transfer.get("status") in CLOSED_STATUSES:
        raise ToolFailure("INVALID_STATE", f"The transfer is already {transfer.get('status')}; it cannot be changed")
    return transfer


async def _included_versions(app, transfer_id) -> set[str]:
    included = set()
    for n in range(MAX_ITEM_PAGES):
        items = await app.api.documents_transfer_item.get_list(
            {"documentsTransferId": transfer_id}, take=ITEMS_PAGE, skip=n * ITEMS_PAGE)
        included |= {str(i.get("item_version_id")) for i in items}
        if len(items) < ITEMS_PAGE:
            return included
    raise ToolFailure("INVALID_STATE", f"The transfer has more than {ITEMS_PAGE * MAX_ITEM_PAGES} documents; "
                      "duplicates cannot be checked")


async def create_document_transfer(app, *, project_id, documents_transfer_type_id, cipher: str, name: str,
                                   confirmation_token=None) -> dict:
    args = {"project_id": project_id, "documents_transfer_type_id": documents_transfer_type_id,
            "cipher": cipher, "name": name}

    async def prepare():
        types = await transfer_types(app, project_id)
        chosen = next((t for t in types if str(t["id"]) == str(documents_transfer_type_id)), None)
        if chosen is None:
            raise ToolFailure("NOT_FOUND", "This transfer type does not belong to the project or is deleted")
        preview = {"action": "create a transfer (draft)", "project_id": str(project_id),
                   "type": pick(chosen, ("id", "name", "settings", "default_recipient")),
                   "cipher": cipher, "name": name, "author_user_id": str(app.settings.actor_user_id)}
        return preview, {"type_id": str(chosen["id"])}

    async def execute(snapshot):
        transfer_id = await app.api.documents_transfer.create(
            documents_transfer_type_id=documents_transfer_type_id, cipher=cipher, name=name,
            author_id=app.settings.actor_user_id)
        return {"transfer_id": transfer_id}

    return await app.two_phase("create_document_transfer", args, confirmation_token, prepare, execute,
                               objects={"project_id": project_id})


async def add_documents_to_transfer(app, *, transfer_id, item_version_ids: list, confirmation_token=None) -> dict:
    unique = list(dict.fromkeys(str(i) for i in item_version_ids))
    args = {"transfer_id": transfer_id, "item_version_ids": unique}

    async def prepare():
        transfer = await _open_transfer(app, transfer_id)
        included = await _included_versions(app, transfer_id)
        to_add = [i for i in unique if i not in included]
        already = [i for i in unique if i in included]
        if not to_add:
            raise ToolFailure("NOTHING_TO_DO", "All these document versions are already in the transfer")
        preview = {"action": "add document versions to the transfer",
                   "transfer": pick(transfer, ("id", "name", "cipher", "number", "status")),
                   "to_add": to_add, "already_included": already, "documents_after": len(included) + len(to_add)}
        return preview, {"status": transfer.get("status"), "included": sorted(included), "to_add": to_add}

    async def execute(snapshot):
        await app.api.documents_transfer_item.add(transfer_id, snapshot["to_add"])
        return {"transfer_id": str(transfer_id), "added": snapshot["to_add"]}

    return await app.two_phase("add_documents_to_transfer", args, confirmation_token, prepare, execute,
                               objects={"transfer_id": transfer_id})


def _send_args(transfer_id, recipient_type, recipient_identifier, share_expiry_date) -> dict:
    return {"transfer_id": transfer_id, "recipient_type": recipient_type,
            "recipient_identifier": recipient_identifier,
            "share_expiry_date": share_expiry_date.isoformat() if share_expiry_date else None}


def _send_flow(app, transfer_id, recipient_type, recipient_identifier, share_expiry_date):
    async def prepare():
        transfer = await _open_transfer(app, transfer_id)
        count = await app.api.documents_transfer_item.count({"documentsTransferId": transfer_id})
        if not count:
            raise ToolFailure("INVALID_STATE", "The transfer has no documents")
        warnings = []
        if recipient_type == "Email":
            warnings.append("The recipient is an e-mail address: the documents leave the company")
        settings = (transfer.get("documents_transfer_type") or {}).get("settings") or {}
        if settings.get("acceptance_certificate_object_required") and not transfer.get("acceptance_certificate"):
            warnings.append("This transfer type requires an acceptance certificate and none is attached")
        preview = {"action": "SEND the transfer to the recipient",
                   "transfer": pick(transfer, ("id", "name", "cipher", "number", "status")),
                   "documents": count,
                   "recipient": {"type": recipient_type, "identifier": recipient_identifier},
                   "share_expiry_date": share_expiry_date.isoformat() if share_expiry_date else None,
                   "sender_user_id": str(app.settings.actor_user_id), "warnings": warnings}
        return preview, {"status": transfer.get("status"), "documents": count}

    async def execute(snapshot):
        try:
            await app.api.documents_transfer_acceptance.send(
                documents_transfer_id=transfer_id,
                recipient={"type": recipient_type, "identifier": recipient_identifier},
                author_id=app.settings.actor_user_id,
                share_expiry_date=share_expiry_date.isoformat() if share_expiry_date else None)
        except UNCERTAIN as e:
            observed = await _status_or_none(app, transfer_id)
            raise ToolFailure("OUTCOME_UNKNOWN", "Sending failed without a clear answer; it was NOT retried. "
                              "Check the transfer status before doing anything else.",
                              {"observed_status": observed}) from e
        status = await _status_or_none(app, transfer_id)
        return {"transfer_id": str(transfer_id), "status_after": status,
                "note": "Sent is not accepted: the recipient still has to receive or reject the transfer"}

    return prepare, execute


async def _status_or_none(app, transfer_id) -> Optional[str]:
    try:
        return (await app.api.documents_transfer.get(transfer_id)).get("status")
    except Exception:
        return None


async def prepare_send_document_transfer(app, *, transfer_id, recipient_type, recipient_identifier,
                                         share_expiry_date=None) -> dict:
    args = _send_args(transfer_id, recipient_type, recipient_identifier, share_expiry_date)
    prepare, execute = _send_flow(app, transfer_id, recipient_type, recipient_identifier, share_expiry_date)
    return await app.two_phase("send_document_transfer", args, None, prepare, execute, risk=Risk.WORKFLOW,
                               objects={"transfer_id": transfer_id})


async def send_document_transfer(app, *, transfer_id, recipient_type, recipient_identifier, share_expiry_date,
                                 confirmation_token: str) -> dict:
    args = _send_args(transfer_id, recipient_type, recipient_identifier, share_expiry_date)
    prepare, execute = _send_flow(app, transfer_id, recipient_type, recipient_identifier, share_expiry_date)
    return await app.two_phase("send_document_transfer", args, confirmation_token, prepare, execute,
                               risk=Risk.WORKFLOW, objects={"transfer_id": transfer_id},
                               confirmed_by="elicitation")
