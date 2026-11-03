"""Runtime shared by all tools: SDK client behind the guarded transport, audit, confirmations, cache."""
import asyncio
import json
import sys
import time
import uuid
from typing import Any, Awaitable, Callable, Optional

import httpx

from sgnl_api import DocsApi, SgnlApiError, SgnlLicenseError, SgnlScopeError

from .audit import AuditLog
from .config import Settings
from .confirm import ConfirmationStore, fingerprint
from .errors import ToolFailure, admin_message, describe_api_error
from .guard import ACTOR_CHECK_SCOPE, CallScope, GuardedTransport, current_scope
from .profiles import Profile, Risk, scopes_for

Prepare = Callable[[], Awaitable[tuple[Any, Any]]]
Execute = Callable[[Any], Awaitable[Any]]


class App:
    def __init__(self, settings: Settings, inner_transport: Optional[httpx.AsyncBaseTransport] = None):
        self.settings = settings
        self.profile: Profile = settings.profile
        self.guard = GuardedTransport(
            base_url=settings.base_url,
            profile=settings.profile,
            rate_per_sec=settings.rate_per_sec,
            burst=settings.burst,
            max_concurrency=settings.max_concurrency,
            inner=inner_transport,
            client_id=settings.client_id,
        )
        self.http = httpx.AsyncClient(transport=self.guard, timeout=settings.http_timeout)
        self.api = DocsApi(
            client_id=settings.client_id,
            client_secret=settings.client_secret.get_secret_value(),
            scopes=scopes_for(settings.profile),
            http_client=self.http,
            max_retries=3,
        )
        self.api._transport.base_url = settings.base_url
        self.audit = AuditLog(settings.audit_path)
        self.confirmations = ConfirmationStore(settings.confirmation_ttl_sec, settings.state_path)
        self._cache: dict[Any, tuple[float, Any]] = {}

    # lifecycle ---------------------------------------------------------------------------------

    async def start(self) -> None:
        """Gets a token and checks the action author. Fails loudly, never half-starts.

        The token is requested with every scope of the profile. If the integration lacks some, the
        server starts without them: requests that need them are answered with SCOPE_MISSING and a
        message for the SIGNAL administrator, and the gap is reported here on stderr.
        """
        try:
            await self.api._transport._ensure_token()
        except (SgnlScopeError, SgnlLicenseError) as e:
            refused = {s: "missing" for s in e.missing_scopes}
            refused.update({s: "unlicensed" for s in e.unlicensed_scopes})
            granted = [s for s in self.api._transport.scopes if s not in refused]
            if not refused or not granted:
                raise self._auth_failure(e) from e
            self.guard.unavailable_scopes = refused
            self.api._transport.scopes = granted
            try:
                await self.api._transport._ensure_token()
            except SgnlApiError as again:
                raise self._auth_failure(again) from again
            print(f"sgnl-mcp: started with limited rights. {admin_message(refused, self.settings.client_id)}",
                  file=sys.stderr)
        except SgnlApiError as e:
            raise self._auth_failure(e) from e
        if self.profile >= Profile.WRITE and ACTOR_CHECK_SCOPE not in self.guard.unavailable_scopes:
            await self._check_actor()

    def _auth_failure(self, error: SgnlApiError) -> RuntimeError:
        return RuntimeError(
            f"Cannot authenticate with SIGNAL for profile '{self.profile.name.lower()}' "
            f"(client_id {self.settings.client_id}): {error.message[:500]}"
        )

    def access_status(self) -> dict:
        """What this key can do: for the agent to explain gaps before the user hits them."""
        unavailable = dict(self.guard.unavailable_scopes)
        return {
            "profile": self.profile.name.lower(),
            "client_id": self.settings.client_id,
            "granted_scopes": list(self.api._transport.scopes),
            "unavailable_scopes": unavailable,
            "message_for_admin": admin_message(unavailable, self.settings.client_id) if unavailable else None,
        }

    async def _check_actor(self) -> None:
        actor = str(self.settings.actor_user_id)
        scope = CallScope(budget=10)
        token = current_scope.set(scope)
        try:
            for page in range(10):
                users = await self.api.company.users_list(take=200, skip=page * 200)
                if any(str(u.get("id")) == actor for u in users):
                    return
                if len(users) < 200:
                    break
        finally:
            current_scope.reset(token)
        raise RuntimeError(f"SGNL_MCP_ACTOR_USER_ID {actor} is not a user of this company")

    async def close(self) -> None:
        await self.api.aclose()
        await self.http.aclose()

    # helpers -----------------------------------------------------------------------------------

    async def cached(self, key: Any, load: Callable[[], Awaitable[Any]]) -> Any:
        now = time.monotonic()
        hit = self._cache.get(key)
        if hit and hit[0] > now:
            return hit[1]
        value = await load()
        self._cache[key] = (now + self.settings.cache_ttl_sec, value)
        return value

    def invalidate(self, *prefixes: str) -> None:
        for key in list(self._cache):
            if isinstance(key, tuple) and key and key[0] in prefixes:
                self._cache.pop(key, None)

    async def root_folder_id(self, project_id) -> str:
        async def load():
            info = await self.api.project.root_folder(project_id)
            return info["root_folder_id"]
        return await self.cached(("root", str(project_id)), load)

    # running tools -----------------------------------------------------------------------------

    async def run(
            self,
            tool: str,
            body: Callable[[], Awaitable[dict]],
            *,
            risk: Risk = Risk.READ,
            budget: int = 5,
            timeout: Optional[float] = None) -> dict:
        """Runs a tool body with its request budget and timeout; maps every failure to the error envelope."""
        request_id = uuid.uuid4().hex
        scope = CallScope(budget=budget)
        scope_token = current_scope.set(scope)
        writing = risk >= Risk.WRITE
        try:
            async with asyncio.timeout(timeout or self.settings.tool_timeout):
                result = await body()
            envelope = {"success": True, **result, "request_id": request_id}
        except TimeoutError:
            code = "OUTCOME_UNKNOWN" if writing and scope.calls else "TIMEOUT"
            envelope = self._error(request_id, ToolFailure(code, "The tool did not finish in time"))
        except Exception as error:  # noqa: BLE001 - every failure becomes a structured answer
            failure = describe_api_error(error, writing=writing)
            if failure.code in ("POLICY_DENIED", "SCOPE_MISSING"):
                self.audit.write({"tool": tool, "risk": risk.name.lower(), "profile": self.profile.name.lower(),
                                  "stage": "guard", "outcome": "denied", "error": failure.message,
                                  "request_id": request_id})
            envelope = self._error(request_id, failure)
        finally:
            current_scope.reset(scope_token)
        return self._fit(envelope)

    @staticmethod
    def _error(request_id: str, failure: ToolFailure) -> dict:
        return {
            "success": False,
            "error": {"code": failure.code, "message": failure.message, "details": failure.details},
            "request_id": request_id,
        }

    def _fit(self, envelope: dict) -> dict:
        """Keeps the answer under max_response_chars by cutting the data list, never by dropping the error."""
        limit = self.settings.max_response_chars
        data = envelope.get("data")
        if isinstance(data, list) and len(json.dumps(envelope, default=str, ensure_ascii=False)) > limit:
            keep = len(data)
            while keep > 0 and len(json.dumps({**envelope, "data": data[:keep]}, default=str, ensure_ascii=False)) > limit:
                keep = keep // 2
            envelope["data"] = data[:keep]
            envelope["truncated"] = True
            envelope.setdefault("warnings", []).append(
                f"Answer cut to {keep} of {len(data)} items to fit the size limit; narrow the filter or page with skip"
            )
        return envelope

    # confirmation ------------------------------------------------------------------------------

    async def two_phase(
            self,
            tool: str,
            args: dict,
            confirmation_token: Optional[str],
            prepare: Prepare,
            execute: Execute,
            *,
            risk: Risk = Risk.WRITE,
            objects: Optional[dict] = None,
            confirmed_by: str = "token") -> dict:
        """Preview → token → execute, with audit records for every stage.

        `prepare` returns (preview, snapshot); `execute` gets the fresh snapshot and returns the data.
        Workflow tools never run without a token; Write tools listed in auto_confirm skip the preview.
        """
        auto = risk == Risk.WRITE and tool in self.settings.auto_confirm
        base_event = {
            "tool": tool,
            "risk": risk.name.lower(),
            "profile": self.profile.name.lower(),
            "actor_user_id": str(self.settings.actor_user_id) if self.settings.actor_user_id else None,
            "args": args,
            "objects": objects or {},
        }

        if confirmation_token is None and not auto:
            preview, snapshot = await prepare()
            token = self.confirmations.issue(tool, args, snapshot, preview)
            self.audit.write({**base_event, "stage": "preview", "outcome": "success"})
            return {
                "status": "confirmation_required",
                "preview": preview,
                "confirmation_token": token,
                "expires_in_sec": self.settings.confirmation_ttl_sec,
                "next_step": (
                    "Show the preview to the user. Only after they agree, call this tool again with the same "
                    "arguments and confirmation_token."
                ),
            }

        if confirmation_token is not None:
            done = self.confirmations.completed(confirmation_token)
            if done is not None:
                return {"status": "already_done", "data": done,
                        "warnings": ["This confirmation was already executed; nothing was sent again"]}
            pending = self.confirmations.take(confirmation_token, tool, args)
            _, snapshot = await prepare()
            if fingerprint(snapshot) != fingerprint(pending.snapshot):
                self.audit.write({**base_event, "stage": "execute", "confirmation": confirmed_by,
                                  "outcome": "denied", "error": "object changed since preview"})
                raise ToolFailure(
                    "CONFIRMATION_INVALID",
                    "The objects changed after the preview; request a new preview and show it to the user",
                )
        else:
            _, snapshot = await prepare()

        confirmation = "auto" if auto else confirmed_by
        self.audit.write({**base_event, "stage": "intent", "confirmation": confirmation})
        try:
            data = await execute(snapshot)
        except Exception as error:
            failure = describe_api_error(error, writing=True)
            self.audit.write({**base_event, "stage": "result", "confirmation": confirmation,
                              "outcome": "unknown" if failure.code == "OUTCOME_UNKNOWN" else "failed",
                              "error": failure.code, "calls": current_scope.get().calls})
            raise failure from error
        if confirmation_token is not None:
            self.confirmations.record(confirmation_token, tool, data)
        self.audit.write({**base_event, "stage": "result", "confirmation": confirmation, "outcome": "success",
                          "result": data, "calls": current_scope.get().calls})
        return {"status": "done", "data": data}

    def audit_denied(self, tool: str, args: dict, reason: str, risk: Risk) -> None:
        self.audit.write({
            "tool": tool, "risk": risk.name.lower(), "profile": self.profile.name.lower(),
            "actor_user_id": str(self.settings.actor_user_id) if self.settings.actor_user_id else None,
            "args": args, "stage": "execute", "outcome": "denied", "error": reason,
        })
