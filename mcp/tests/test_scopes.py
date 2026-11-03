"""The user only has a key: missing scopes must not stop the server, and must be explained."""
import json

import httpx
import pytest
from mcp import Client

from sgnl_mcp.errors import ScopeMissing
from sgnl_mcp.profiles import Profile, scopes_for
from sgnl_mcp.runtime import App
from sgnl_mcp.server import build_server

from conftest import call


def refusing(fake, enabled=None, unlicensed=()):
    """Wraps the fake SIGNAL so /auth/token refuses scopes like the real one: a bare 422 code."""
    inner = fake.handler

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/token"):
            asked = json.loads(request.content)["scopes"]
            handler.token_scopes.append(asked)
            if enabled is not None and any(s not in enabled for s in asked):
                return httpx.Response(422, json="ScopeError")
            if any(s in unlicensed for s in asked):
                return httpx.Response(422, json="LicenseError")
        return await inner(request)

    handler.token_scopes = []
    return handler


async def open_app(make_settings, handler, profile="read"):
    settings = make_settings(profile)
    app = App(settings, inner_transport=httpx.MockTransport(handler))
    server, _ = build_server(settings, app)
    return Client(server), app


def test_profiles_request_only_route_scopes():
    read = scopes_for(Profile.READ)
    assert "docs:issue:list" in read and "project:list" in read
    assert not [s for s in read if s.endswith((":create", ":update", ":delete"))]
    assert set(read) < set(scopes_for(Profile.WRITE)) <= set(scopes_for(Profile.WORKFLOW))
    assert "company:user:list" in scopes_for(Profile.WRITE)


async def test_server_starts_without_a_missing_scope_and_explains_it(fake, make_settings, capsys):
    enabled = set(scopes_for(Profile.READ)) - {"docs:issue:list"}
    handler = refusing(fake, enabled=enabled)
    fake.routes[("GET", "/projects")] = lambda req, body: [{"id": "p1", "name": "P", "code": "C"}]
    client, app = await open_app(make_settings, handler)
    async with client:
        assert handler.token_scopes[-1] == sorted(enabled)

        ok = await call(client, "list_projects")
        assert ok["success"] is True

        before = len(fake.calls)
        r = await call(client, "list_issues", project_id="00000000-0000-0000-0000-000000000001")
        assert r["success"] is False
        assert r["error"]["code"] == "SCOPE_MISSING"
        assert r["error"]["details"]["missing_scopes"] == ["docs:issue:list"]
        assert "администратору SIGNAL" in r["error"]["message"]
        assert "docs:issue:list" in r["error"]["message"] and "client_id client" in r["error"]["message"]
        assert len(fake.calls) == before  # nothing reached SIGNAL

        status = await call(client, "get_access_status")
        assert status["unavailable_scopes"] == {"docs:issue:list": "missing"}
        assert "docs:issue:list" in status["message_for_admin"]
    assert "limited rights" in capsys.readouterr().err


async def test_unlicensed_scope_gets_its_own_message(fake, make_settings):
    handler = refusing(fake, unlicensed={"docs:review:list"})
    client, app = await open_app(make_settings, handler)
    async with client:
        r = await call(client, "list_reviews", project_id="00000000-0000-0000-0000-000000000001")
        assert r["error"]["code"] == "SCOPE_MISSING"
        assert "нет лицензии" in r["error"]["message"]
        status = await call(client, "get_access_status")
        assert status["unavailable_scopes"] == {"docs:review:list": "unlicensed"}


async def test_full_key_reports_nothing_missing(connect):
    async with connect() as client:
        status = await call(client, "get_access_status")
        assert status["unavailable_scopes"] == {} and status["message_for_admin"] is None
        assert status["granted_scopes"] == scopes_for(Profile.READ)


async def test_key_without_any_profile_scope_does_not_start(fake, make_settings):
    app = App(make_settings("read"), inner_transport=httpx.MockTransport(refusing(fake, enabled=set())))
    with pytest.raises(RuntimeError, match="Cannot authenticate with SIGNAL for profile 'read' \\(client_id client\\)"):
        await app.start()
    await app.close()


async def test_writes_blocked_when_actor_cannot_be_checked(fake, make_settings):
    enabled = set(scopes_for(Profile.WRITE)) - {"company:user:list"}
    app = App(make_settings("write"), inner_transport=httpx.MockTransport(refusing(fake, enabled=enabled)))
    await app.start()
    assert not fake.sent("GET", "/company/users")
    with pytest.raises(ScopeMissing) as info:
        app.guard.check(httpx.Request("PATCH", "https://api.sgnl.pro/public/v1/issues", content=b"[]"))
    assert info.value.scopes == {"company:user:list": "missing"}
    # reads still work
    app.guard.check(httpx.Request("POST", "https://api.sgnl.pro/public/v1/issues", content=b"{}"))
    await app.close()
