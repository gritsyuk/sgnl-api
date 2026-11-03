"""Guarded httpx transport: every request the SDK sends passes through here before the network.

It enforces, in order:
1. an allowlist of (method, path) for the active profile; everything else, including any DELETE,
   is refused before it leaves the process;
2. no "deleted" field anywhere in the body of a write request (soft delete through an update);
3. external hosts only for the S3 upload PUT, and only while an upload service has opened that window;
4. the REST request budget of the current tool call;
5. a process-wide rate limit (token bucket) and a cap on parallel requests;
6. scopes the integration refused at startup: a request that needs one is answered with
   SCOPE_MISSING and a message for the SIGNAL administrator, without calling the API.
"""
import asyncio
import contextvars
import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlsplit

import httpx

from .errors import BudgetExceeded, PolicyDenied, ScopeMissing
from .profiles import Profile, Risk

ID = r"[^/]+"

# (method, path regex relative to the API base, risk, scope). The risk decides the minimal profile;
# the scope is the one the API spec names for the route ("Required scopes"), and the profile's token
# is requested with exactly the scopes of its routes.
ROUTES: tuple[tuple[str, str, Risk, Optional[str]], ...] = (
    ("POST", r"/auth/token", Risk.READ, None),
    # projects and folders
    ("GET", r"/projects", Risk.READ, "project:list"),
    ("GET", rf"/projects/{ID}", Risk.READ, "project:read"),
    ("GET", rf"/docs/projects/{ID}", Risk.READ, "project:read"),
    ("GET", rf"/projects/{ID}/folders/tree", Risk.READ, "docs:folder:read"),
    # documents and versions
    ("POST", r"/items/search", Risk.READ, "docs:item:list"),
    ("GET", r"/items", Risk.READ, "docs:item:list"),
    ("GET", r"/items/count", Risk.READ, "docs:item:list"),
    ("GET", r"/items/item-version", Risk.READ, "docs:item:read"),
    ("GET", r"/items/download", Risk.READ, "docs:item:read"),
    ("GET", r"/versions", Risk.READ, "docs:version:list"),
    # document context
    ("POST", r"/attributes/types", Risk.READ, "docs:attribute:list"),
    ("POST", r"/attributes/values/items", Risk.READ, "docs:attribute:list"),
    ("GET", r"/cades/signatures", Risk.READ, "docs:signing:list"),
    ("GET", r"/embedded/signatures", Risk.READ, "docs:signing:list"),
    # transfers
    ("POST", r"/documents-transfers", Risk.READ, "docs:docs_transfer:list"),
    ("GET", r"/documents-transfers", Risk.READ, "docs:docs_transfer:read"),
    ("POST", r"/documents-transfers/count", Risk.READ, "docs:docs_transfer:list"),
    ("POST", r"/documents-transfers/types", Risk.READ, "docs:docs_transfer:list"),
    ("POST", r"/documents-transfer-items", Risk.READ, "docs:docs_transfer:list"),
    ("POST", r"/documents-transfer-items/count", Risk.READ, "docs:docs_transfer:list"),
    # issues
    ("POST", r"/issues", Risk.READ, "docs:issue:list"),
    ("POST", r"/issues/count", Risk.READ, "docs:issue:list"),
    ("POST", r"/issues/types", Risk.READ, "docs:issue:list"),
    # reviews
    ("POST", r"/reviews", Risk.READ, "docs:review:list"),
    ("POST", r"/reviews/count", Risk.READ, "docs:review:list"),
    ("POST", r"/reviews/versions", Risk.READ, "docs:review:list"),
    ("POST", r"/reviews/versions/item-versions", Risk.READ, "docs:review:list"),
    ("POST", r"/reviews/items", Risk.READ, "docs:review:list"),
    ("GET", r"/reviews/types/names", Risk.READ, "docs:review:list"),
    # write profile: checks
    ("GET", r"/company/users", Risk.WRITE, "company:user:list"),
    ("GET", r"/naming-patterns/folder-items/find", Risk.WRITE, "docs:item:create"),
    # write profile: changes
    ("PUT", r"/objects", Risk.WRITE, "docs:object:create"),
    ("POST", rf"/objects/{ID}/uploading/commit", Risk.WRITE, "docs:object:create"),
    ("POST", r"/versions", Risk.WRITE, "docs:version:create"),
    ("PUT", r"/items/file", Risk.WRITE, "docs:item:create"),
    ("PUT", r"/items/versions", Risk.WRITE, "docs:version:create"),
    ("PATCH", r"/items/versions/update", Risk.WRITE, "docs:version:update"),
    ("POST", r"/documents-transfers/create", Risk.WRITE, "docs:docs_transfer:create"),
    ("POST", r"/documents-transfer-items/add", Risk.WRITE, "docs:docs_transfer:update"),
    ("PATCH", r"/issues", Risk.WRITE, "docs:issue:update"),
    ("POST", r"/reviews/create", Risk.WRITE, "docs:review:create"),
    ("POST", r"/reviews/items/add", Risk.WRITE, "docs:review:update"),
    # workflow profile
    ("POST", r"/documents-transfer-acceptances/send", Risk.WORKFLOW, "docs:docs_transfer:update"),
    ("POST", r"/reviews/process/start", Risk.WORKFLOW, "docs:review:update"),
)

_COMPILED = tuple((method, re.compile(pattern + r"/?"), risk, scope) for method, pattern, risk, scope in ROUTES)

# Every write first checks the action author in the company user list (App._check_actor).
ACTOR_CHECK_SCOPE = "company:user:list"


def route_for(method: str, path: str) -> Optional[tuple[Risk, Optional[str]]]:
    for allowed_method, pattern, risk, scope in _COMPILED:
        if method == allowed_method and pattern.fullmatch(path):
            return risk, scope
    return None


def route_risk(method: str, path: str) -> Optional[Risk]:
    route = route_for(method, path)
    return route[0] if route else None


def scopes_for(profile: Profile) -> list[str]:
    """The scopes a profile's token is requested with: those of the routes the profile may call."""
    return sorted({scope for _, _, risk, scope in ROUTES if scope and profile.allows(risk)})


def contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(contains_key(v, key) for v in value.values())
    if isinstance(value, list):
        return any(contains_key(v, key) for v in value)
    return False


@dataclass
class CallScope:
    """Per tool call: how many REST requests it may still send, and what it sent (for the audit)."""

    budget: int
    upload_window: bool = False
    calls: list = field(default_factory=list)

    def take(self) -> None:
        if self.budget <= 0:
            raise BudgetExceeded()
        self.budget -= 1


current_scope: contextvars.ContextVar[Optional[CallScope]] = contextvars.ContextVar("sgnl_call_scope", default=None)


class TokenBucket:
    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.capacity = burst
        self.tokens = float(burst)
        self.updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
                self.updated = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                await asyncio.sleep((1 - self.tokens) / self.rate)


class GuardedTransport(httpx.AsyncBaseTransport):
    def __init__(
            self,
            *,
            base_url: str,
            profile: Profile,
            rate_per_sec: float,
            burst: int,
            max_concurrency: int,
            inner: Optional[httpx.AsyncBaseTransport] = None,
            client_id: str = ""):
        parts = urlsplit(base_url)
        self.api_host = parts.netloc
        self.api_prefix = parts.path.rstrip("/")
        self.profile = profile
        self.inner = inner or httpx.AsyncHTTPTransport()
        self.bucket = TokenBucket(rate_per_sec, burst)
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.client_id = client_id
        # Scopes the integration refused at startup -> "missing" (not enabled) or "unlicensed".
        self.unavailable_scopes: dict[str, str] = {}

    def is_api(self, request: httpx.Request) -> bool:
        host = request.url.host if request.url.port is None else f"{request.url.host}:{request.url.port}"
        return host == self.api_host

    def check(self, request: httpx.Request) -> Optional[Risk]:
        """Raises PolicyDenied for a request the profile does not allow. Returns the route risk."""
        method = request.method.upper()
        if not self.is_api(request):
            scope = current_scope.get()
            if method == "PUT" and scope is not None and scope.upload_window:
                return None
            raise PolicyDenied(f"{method} to an external host is not allowed")

        path = request.url.path
        if not path.startswith(self.api_prefix + "/"):
            raise PolicyDenied(f"{method} {path} is outside the API")
        relative = path[len(self.api_prefix):]
        route = route_for(method, relative)
        if route is None:
            raise PolicyDenied(f"{method} {relative} is not on the allowlist")
        risk, scope = route
        if not self.profile.allows(risk):
            raise PolicyDenied(f"{method} {relative} needs the {risk.name.lower()} profile")
        needed = [scope] if scope else []
        if risk >= Risk.WRITE:
            needed.append(ACTOR_CHECK_SCOPE)
        refused = {s: self.unavailable_scopes[s] for s in needed if s in self.unavailable_scopes}
        if refused:
            raise ScopeMissing(refused, self.client_id)
        if risk >= Risk.WRITE and request.content:
            try:
                body = json.loads(request.content)
            except ValueError:
                raise PolicyDenied(f"{method} {relative}: write body is not JSON")
            if contains_key(body, "deleted"):
                raise PolicyDenied(f"{method} {relative}: the 'deleted' field is forbidden in write requests")
        return risk

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        # The body of an API request is already buffered by the SDK; read it so check() can inspect it.
        is_api = self.is_api(request)
        if is_api:
            await request.aread()
        self.check(request)
        scope = current_scope.get()
        is_auth = request.url.path.endswith("/auth/token")
        if scope is not None and not is_auth:
            scope.take()
        await self.bucket.acquire()
        started = time.monotonic()
        async with self.semaphore:
            response = await self.inner.handle_async_request(request)
        if scope is not None and not is_auth:
            relative = request.url.path[len(self.api_prefix):] if is_api else "<upload>"
            scope.calls.append({
                "method": request.method,
                "path": relative,
                "status": response.status_code,
                "ms": round((time.monotonic() - started) * 1000),
            })
        return response

    async def aclose(self) -> None:
        await self.inner.aclose()
