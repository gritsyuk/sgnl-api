import json
import re
from pathlib import Path

import httpx
import pytest
import yaml
from mcp.shared.exceptions import MCPError

from conftest import TRANSFER, accept_elicitation, call, decline_elicitation
from sgnl_mcp.errors import PolicyDenied
from sgnl_mcp.guard import ROUTES, GuardedTransport
from sgnl_mcp.profiles import Profile, Risk, READ_SCOPES, scopes_for

SPEC = Path(__file__).resolve().parents[2] / "openapi" / "schema.yml"
SEND = dict(transfer_id=TRANSFER, recipient_type="User", recipient_identifier="user-42")


# ---- workflow: send a transfer --------------------------------------------------------------------

async def test_send_requires_prepare_and_user_confirmation(connect, fake):
    accept_elicitation.messages.clear()
    async with connect("workflow", elicitation=accept_elicitation()) as c:
        prepared = await call(c, "prepare_send_document_transfer", **SEND)
        assert prepared["status"] == "confirmation_required" and not fake.sent("POST", "/documents-transfer-acceptances/send")
        sent = await call(c, "send_document_transfer", **SEND, confirmation_token=prepared["confirmation_token"])
    assert sent["status"] == "done" and sent["data"]["status_after"] == "Sent"
    assert "SEND" in accept_elicitation.messages[0] and "Set 12" in accept_elicitation.messages[0]
    assert fake.sent("POST", "/documents-transfer-acceptances/send")[0][2]["authorId"] == "55555555-5555-5555-5555-555555555555"


async def test_declined_confirmation_sends_nothing(connect, fake):
    async with connect("workflow", elicitation=decline_elicitation) as c:
        prepared = await call(c, "prepare_send_document_transfer", **SEND)
        r = await call(c, "send_document_transfer", **SEND, confirmation_token=prepared["confirmation_token"])
        again = await call(c, "send_document_transfer", **SEND, confirmation_token=prepared["confirmation_token"])
    assert r["error"]["code"] == "CONFIRMATION_DECLINED"
    assert again["success"] is False  # the declined token is spent
    assert not fake.sent("POST", "/documents-transfer-acceptances/send")


async def test_unchecked_box_counts_as_decline(connect, fake):
    async with connect("workflow", elicitation=accept_elicitation(confirm=False)) as c:
        prepared = await call(c, "prepare_send_document_transfer", **SEND)
        r = await call(c, "send_document_transfer", **SEND, confirmation_token=prepared["confirmation_token"])
    assert r["error"]["code"] == "CONFIRMATION_DECLINED"
    assert not fake.sent("POST", "/documents-transfer-acceptances/send")


async def test_client_without_elicitation_cannot_send(connect, fake):
    async with connect("workflow") as c:
        prepared = await call(c, "prepare_send_document_transfer", **SEND)
        with pytest.raises(MCPError, match="elicitation"):
            await c.call_tool("send_document_transfer", {**SEND, "confirmation_token": prepared["confirmation_token"]})
    assert not fake.sent("POST", "/documents-transfer-acceptances/send")


async def test_sent_transfer_cannot_be_sent_again(connect, fake):
    fake.transfer["status"] = "Sent"
    async with connect("workflow", elicitation=accept_elicitation()) as c:
        r = await call(c, "prepare_send_document_transfer", **SEND)
    assert r["error"]["code"] == "INVALID_STATE"


async def test_email_recipient_is_flagged(connect):
    async with connect("workflow", elicitation=accept_elicitation()) as c:
        r = await call(c, "prepare_send_document_transfer", transfer_id=TRANSFER, recipient_type="Email",
                       recipient_identifier="someone@outside.example")
    assert any("e-mail" in w for w in r["preview"]["warnings"])


async def test_add_documents_skips_existing(connect, fake):
    fake.routes[("POST", "/documents-transfer-items/add")] = lambda req, body: httpx.Response(200)
    async with connect("write") as c:
        p = await call(c, "add_documents_to_transfer", transfer_id=TRANSFER,
                       item_version_ids=["00000000-0000-0000-0000-0000000000c1"])
        assert p["preview"]["to_add"] == ["00000000-0000-0000-0000-0000000000c1"]
        done = await call(c, "add_documents_to_transfer", transfer_id=TRANSFER,
                          item_version_ids=["00000000-0000-0000-0000-0000000000c1"],
                          confirmation_token=p["confirmation_token"])
    assert done["data"]["added"] == ["00000000-0000-0000-0000-0000000000c1"]


# ---- profiles and registration -------------------------------------------------------------------

async def test_tools_registered_per_profile(connect):
    names = {}
    for profile in ("read", "write", "workflow"):
        async with connect(profile) as c:
            names[profile] = {t.name: t for t in (await c.list_tools()).tools}
    assert len(names["read"]) == 18 and len(names["write"]) == 26 and len(names["workflow"]) == 30
    assert "update_issues" not in names["read"] and "send_document_transfer" not in names["write"]
    forbidden = re.compile(r"delete|remove|move|rename|permission", re.I)
    assert not [n for n in names["workflow"] if forbidden.search(n)]
    for name, tool in names["workflow"].items():
        if name in names["read"]:
            assert tool.annotations.read_only_hint, name
    assert not names["workflow"]["send_document_transfer"].annotations.read_only_hint


def test_write_profile_requires_actor_and_upload_root(make_settings):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        make_settings("write", actor_user_id=None)


def test_auto_confirm_cannot_cover_workflow(make_settings):
    settings = make_settings("workflow", auto_confirm="send_document_transfer,update_issues")
    assert "send_document_transfer" in settings.auto_confirm  # listed, but two_phase ignores it for WORKFLOW


# ---- guarded transport ---------------------------------------------------------------------------

def _guard(profile=Profile.WORKFLOW):
    return GuardedTransport(base_url="https://api.sgnl.pro/public/v1", profile=profile,
                            rate_per_sec=10, burst=10, max_concurrency=4)


@pytest.mark.parametrize("method,path,body", [
    ("DELETE", "/items/abc", None),
    ("DELETE", "/folders/abc", None),
    ("DELETE", "/shares", {"id": "x", "deleted": True}),
    ("PATCH", "/items/move", {"id": "x", "newFolderId": "y"}),
    ("PATCH", "/items/update", {"id": "x", "name": "y"}),
    ("PATCH", "/folders", {"id": "x", "name": "y"}),
    ("POST", "/permissions/folders/upsert", {"folderId": "x", "items": []}),
    ("PATCH", "/issues", [{"id": "x", "deleted": True}]),
    ("PATCH", "/issues", [{"id": "x", "observers": [{"id": "y", "type": "User", "deleted": True}]}]),
    ("PUT", "/company-users", {"users": []}),
])
def test_guard_denies_critical_requests(method, path, body):
    request = httpx.Request(method, "https://api.sgnl.pro/public/v1" + path,
                            content=json.dumps(body).encode() if body is not None else None)
    with pytest.raises(PolicyDenied):
        _guard().check(request)


def test_guard_denies_write_in_read_profile_and_external_hosts():
    with pytest.raises(PolicyDenied):
        _guard(Profile.READ).check(httpx.Request("PATCH", "https://api.sgnl.pro/public/v1/issues", content=b"[]"))
    with pytest.raises(PolicyDenied):
        _guard().check(httpx.Request("PUT", "https://attacker.example/upload", content=b"x"))
    # a read filter may carry "deleted": it selects, it does not delete
    _guard(Profile.READ).check(httpx.Request("POST", "https://api.sgnl.pro/public/v1/issues",
                                             content=json.dumps({"projectId": "p", "deleted": False}).encode()))


def test_allowlist_has_no_delete_and_matches_spec():
    assert not [r for r in ROUTES if r[0] == "DELETE"]
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    operations = {}
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            pattern = re.sub(r"\{[^}]+\}", "[^/]+", path.replace("/public/v1", ""))
            scopes = re.findall(r"`([a-z_:]+)`", op.get("description") or "")
            operations[(method.upper(), pattern)] = (op, scopes)

    for method, route, risk in ROUTES:
        matches = [v for (m, p), v in operations.items() if m == method and p == route]
        assert matches, f"{method} {route} is not in the API spec"
        _, required = matches[0]
        if route == "/auth/token":
            continue
        profile = Profile(int(risk))
        assert set(required) <= set(scopes_for(profile)), f"{method} {route} needs {required}"
        if risk == Risk.READ:
            assert set(required) <= set(READ_SCOPES), f"read route {method} {route} needs a write scope"


def test_no_profile_requests_delete_scopes():
    for profile in Profile:
        assert not [s for s in scopes_for(profile) if s.endswith(":delete")]


def test_settings_errors_name_the_variables(monkeypatch):
    import pytest
    from pydantic import ValidationError

    from sgnl_mcp.config import Settings
    from sgnl_mcp.server import describe_settings_error

    for name in ("SGNL_CLIENT_ID", "SGNL_CLIENT_SECRET", "SGNL_MCP_PROFILE", "SGNL_MCP_ACTOR_USER_ID",
                 "SGNL_MCP_UPLOAD_ROOT", "SGNL_MCP_RATE_PER_SEC"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValidationError) as missing:
        Settings(_env_file=None)
    text = describe_settings_error(missing.value)
    assert "SGNL_CLIENT_ID is not set" in text and "SGNL_CLIENT_SECRET is not set" in text

    monkeypatch.setenv("SGNL_CLIENT_ID", "x")
    monkeypatch.setenv("SGNL_CLIENT_SECRET", "y")
    monkeypatch.setenv("SGNL_MCP_RATE_PER_SEC", "50")
    with pytest.raises(ValidationError) as too_fast:
        Settings(_env_file=None)
    assert "SGNL_MCP_RATE_PER_SEC" in describe_settings_error(too_fast.value)

    monkeypatch.delenv("SGNL_MCP_RATE_PER_SEC")
    monkeypatch.setenv("SGNL_MCP_PROFILE", "write")
    with pytest.raises(ValidationError) as no_actor:
        Settings(_env_file=None)
    assert "SGNL_MCP_ACTOR_USER_ID is required" in describe_settings_error(no_actor.value)
