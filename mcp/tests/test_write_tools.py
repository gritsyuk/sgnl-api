import json

from conftest import DOC, FOLDER, ISSUE, PROJECT, call


async def test_update_issues_two_phase(connect, fake):
    change = [{"id": ISSUE, "status": "InProgress", "comment": "Взято в работу"}]
    async with connect("write") as c:
        preview = await call(c, "update_issues", project_id=PROJECT, changes=change)
        assert preview["status"] == "confirmation_required"
        assert not fake.sent("PATCH", "/issues")  # the preview changes nothing
        row = preview["preview"]["issues"][0]
        assert row["changes"]["status"] == {"before": "Open", "after": "InProgress"}
        assert row["significant"] == ["status"]

        done = await call(c, "update_issues", project_id=PROJECT, changes=change,
                          confirmation_token=preview["confirmation_token"])
    assert done["status"] == "done"
    assert done["data"]["issues"] == [{"id": ISSUE, "result": "applied", "fields_not_applied": [], "status": "InProgress"}]
    assert fake.sent("PATCH", "/issues")[0][2] == [{"id": ISSUE, "status": "InProgress", "comment": "Взято в работу"}]


async def test_token_is_bound_to_arguments(connect, fake):
    async with connect("write") as c:
        preview = await call(c, "update_issues", project_id=PROJECT, changes=[{"id": ISSUE, "status": "Closed"}])
        r = await call(c, "update_issues", project_id=PROJECT, changes=[{"id": ISSUE, "status": "Void"}],
                       confirmation_token=preview["confirmation_token"])
    assert r["error"]["code"] == "CONFIRMATION_INVALID"
    assert not fake.sent("PATCH", "/issues")


async def test_token_replay_does_not_repeat_the_write(connect, fake):
    change = [{"id": ISSUE, "status": "Closed"}]
    async with connect("write") as c:
        preview = await call(c, "update_issues", project_id=PROJECT, changes=change)
        token = preview["confirmation_token"]
        await call(c, "update_issues", project_id=PROJECT, changes=change, confirmation_token=token)
        again = await call(c, "update_issues", project_id=PROJECT, changes=change, confirmation_token=token)
    assert again["status"] == "already_done"
    assert len(fake.sent("PATCH", "/issues")) == 1


async def test_object_changed_after_preview(connect, fake):
    change = [{"id": ISSUE, "status": "Closed"}]
    async with connect("write") as c:
        preview = await call(c, "update_issues", project_id=PROJECT, changes=change)
        fake.issue["modified"] = "2026-10-05T00:00:00Z"  # someone else edited it
        r = await call(c, "update_issues", project_id=PROJECT, changes=change,
                       confirmation_token=preview["confirmation_token"])
    assert r["error"]["code"] == "CONFIRMATION_INVALID"
    assert not fake.sent("PATCH", "/issues")


async def test_issue_delete_field_is_rejected_by_schema(connect, fake):
    async with connect("write") as c:
        r = await c.call_tool("update_issues", {"project_id": PROJECT, "changes": [{"id": ISSUE, "deleted": True}]})
    assert r.is_error
    assert not fake.sent("PATCH", "/issues")


async def test_batch_limit(connect):
    changes = [{"id": f"00000000-0000-0000-0000-{n:012d}", "status": "Open"} for n in range(26)]
    async with connect("write") as c:
        r = await c.call_tool("update_issues", {"project_id": PROJECT, "changes": changes})
    assert r.is_error


async def test_upload_document_full_protocol(connect, fake):
    async with connect("write") as c:
        preview = await call(c, "upload_document", project_id=PROJECT, folder_id=FOLDER, file_path="A2.pdf")
        assert preview["preview"]["folder_path"] == "Root / Drawings"
        assert not fake.sent("PUT", "/objects")
        done = await call(c, "upload_document", project_id=PROJECT, folder_id=FOLDER, file_path="A2.pdf",
                          confirmation_token=preview["confirmation_token"])
    assert done["data"]["item_id"] == "new-item" and done["data"]["version_id"] == "ver1"
    writes = [(m, p) for m, p, _ in fake.calls if m in ("PUT", "POST") and p not in ("/items/search",)]
    assert writes == [("PUT", "/objects"), ("PUT", "/put/obj1"), ("POST", "/objects/obj1/uploading/commit"),
                      ("POST", "/versions"), ("PUT", "/items/file")]
    assert fake.sent("PUT", "/items/file")[0][2] == {"name": "A2.pdf", "folderId": FOLDER, "versionId": "ver1"}


async def test_upload_outside_root_is_refused(connect, fake, tmp_path):
    secret = tmp_path / "secret.pdf"
    secret.write_bytes(b"%PDF-" + b"s" * 50)
    async with connect("write") as c:
        absolute = await call(c, "upload_document", project_id=PROJECT, folder_id=FOLDER, file_path=str(secret))
        traversal = await call(c, "upload_document", project_id=PROJECT, folder_id=FOLDER, file_path="../secret.pdf")
    assert absolute["error"]["code"] == "POLICY_DENIED"
    assert traversal["error"]["code"] == "POLICY_DENIED"
    assert not fake.sent("PUT", "/objects")


async def test_upload_symlink_out_of_root_is_refused(connect, fake, tmp_path, upload_root):
    secret = tmp_path / "id_rsa.pdf"
    secret.write_bytes(b"%PDF-" + b"k" * 50)
    (upload_root / "innocent.pdf").symlink_to(secret)
    async with connect("write") as c:
        r = await call(c, "upload_document", project_id=PROJECT, folder_id=FOLDER, file_path="innocent.pdf")
    assert r["error"]["code"] == "POLICY_DENIED"


async def test_upload_unknown_outcome_then_resume(connect, fake):
    fake.fail_item_create = True
    async with connect("write") as c:
        preview = await call(c, "upload_document", project_id=PROJECT, folder_id=FOLDER, file_path="A2.pdf")
        failed = await call(c, "upload_document", project_id=PROJECT, folder_id=FOLDER, file_path="A2.pdf",
                            confirmation_token=preview["confirmation_token"])
        assert failed["error"]["code"] == "OUTCOME_UNKNOWN"
        assert failed["error"]["details"] == {"version_id": "ver1", "object_id": "obj1", "step": "item_create"}
        assert len(fake.sent("PUT", "/items/file")) == 1  # not retried automatically

        fake.fail_item_create = False
        uploads_before = len(fake.sent("PUT", "/objects"))
        preview = await call(c, "upload_document", project_id=PROJECT, folder_id=FOLDER, file_path="A2.pdf",
                             resume_version_id="00000000-0000-0000-0000-0000000000a1")
        done = await call(c, "upload_document", project_id=PROJECT, folder_id=FOLDER, file_path="A2.pdf",
                          resume_version_id="00000000-0000-0000-0000-0000000000a1",
                          confirmation_token=preview["confirmation_token"])
    assert done["status"] == "done"
    assert len(fake.sent("PUT", "/objects")) == uploads_before  # the file was not uploaded again


async def test_changed_file_invalidates_token(connect, fake, upload_root):
    async with connect("write") as c:
        preview = await call(c, "upload_document", project_id=PROJECT, folder_id=FOLDER, file_path="A2.pdf")
        (upload_root / "A2.pdf").write_bytes(b"%PDF-1.7 replaced content " + b"y" * 100)
        r = await call(c, "upload_document", project_id=PROJECT, folder_id=FOLDER, file_path="A2.pdf",
                       confirmation_token=preview["confirmation_token"])
    assert r["error"]["code"] == "CONFIRMATION_INVALID"
    assert not fake.sent("PUT", "/objects")


async def test_audit_records_without_secrets(connect, fake, tmp_path):
    change = [{"id": ISSUE, "status": "Closed"}]
    async with connect("write") as c:
        preview = await call(c, "update_issues", project_id=PROJECT, changes=change)
        await call(c, "update_issues", project_id=PROJECT, changes=change,
                   confirmation_token=preview["confirmation_token"])
        preview = await call(c, "upload_document", project_id=PROJECT, folder_id=FOLDER, file_path="A2.pdf")
        await call(c, "upload_document", project_id=PROJECT, folder_id=FOLDER, file_path="A2.pdf",
                   confirmation_token=preview["confirmation_token"])
    text = (tmp_path / "audit.jsonl").read_text()
    events = [json.loads(line) for line in text.splitlines()]
    stages = [(e["tool"], e["stage"], e.get("outcome")) for e in events]
    assert ("update_issues", "intent", None) in stages and ("update_issues", "result", "success") in stages
    assert all(e["actor_user_id"] for e in events)
    for secret in ("super-secret-value", "jwt-secret-token", "X-Amz-Signature=abc"):
        assert secret not in text


async def test_document_version_comment(connect, fake):
    fake.routes[("GET", "/items/item-version")] = lambda req, body: {"id": "iv1", "itemId": DOC, "versionId": "v1"}
    fake.routes[("PATCH", "/items/versions/update")] = lambda req, body: __import__("httpx").Response(204)
    async with connect("write") as c:
        preview = await call(c, "update_document_version_comment", item_version_id="00000000-0000-0000-0000-0000000000b1",
                             comment="new")
        assert preview["error"]["code"] == "NOT_FOUND"  # that item_version_id is not on the document
        fake.routes[("GET", "/items/item-version")] = lambda req, body: {"id": "iv1", "itemId": DOC, "versionId": "v1"}
    async with connect("write") as c:
        r = await call(c, "get_document_version", item_version_id="00000000-0000-0000-0000-0000000000b1")
    assert r["data"]["item_id"] == DOC
