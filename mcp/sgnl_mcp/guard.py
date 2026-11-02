"""Guarded httpx transport: every request the SDK sends passes through here before the network.

It enforces, in order:
1. an allowlist of (method, path) for the active profile; everything else, including any DELETE,
   is refused before it leaves the process;
2. no "deleted" field anywhere in the body of a write request (soft delete through an update);
3. external hosts only for the S3 upload PUT, and only while an upload service has opened that window;
4. the REST request budget of the current tool call;
5. a process-wide rate limit (token bucket) and a cap on parallel requests.
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

from .errors import BudgetExceeded, PolicyDenied
from .profiles import Profile, Risk

ID = r"[^/]+"

# (method, path regex relative to the API base, risk). The risk decides the minimal profile.
ROUTES: tuple[tuple[str, str, Risk], ...] = (
    ("POST", r"/auth/token", Risk.READ),
    # projects and folders
    ("GET", r"/projects", Risk.READ),
    ("GET", rf"/projects/{ID}", Risk.READ),
    ("GET", rf"/docs/projects/{ID}", Risk.READ),
    ("GET", rf"/projects/{ID}/folders/tree", Risk.READ),
    # documents and versions
    ("POST", r"/items/search", Risk.READ),
    ("GET", r"/items", Risk.READ),
    ("GET", r"/items/count", Risk.READ),
    ("GET", r"/items/item-version", Risk.READ),
    ("GET", r"/items/download", Risk.READ),
    ("GET", r"/versions", Risk.READ),
    # document context
    ("POST", r"/attributes/types", Risk.READ),
    ("POST", r"/attributes/values/items", Risk.READ),
    ("GET", r"/cades/signatures", Risk.READ),
    ("GET", r"/embedded/signatures", Risk.READ),
    # transfers
    ("POST", r"/documents-transfers", Risk.READ),
    ("GET", r"/documents-transfers", Risk.READ),
    ("POST", r"/documents-transfers/count", Risk.READ),
    ("POST", r"/documents-transfers/types", Risk.READ),
    ("POST", r"/documents-transfer-items", Risk.READ),
    ("POST", r"/documents-transfer-items/count", Risk.READ),
    # issues
    ("POST", r"/issues", Risk.READ),
    ("POST", r"/issues/count", Risk.READ),
    ("POST", r"/issues/types", Risk.READ),
    # reviews
    ("POST", r"/reviews", Risk.READ),
    ("POST", r"/reviews/count", Risk.READ),
    ("POST", r"/reviews/versions", Risk.READ),
    ("POST", r"/reviews/versions/item-versions", Risk.READ),
    ("POST", r"/reviews/items", Risk.READ),
    ("GET", r"/reviews/types/names", Risk.READ),
    # write profile: checks
    ("GET", r"/company/users", Risk.WRITE),
    ("GET", r"/naming-patterns/folder-items/find", Risk.WRITE),
    # write profile: changes
    ("PUT", r"/objects", Risk.WRITE),
    ("POST", rf"/objects/{ID}/uploading/commit", Risk.WRITE),
    ("POST", r"/versions", Risk.WRITE),
    ("PUT", r"/items/file", Risk.WRITE),
    ("PUT", r"/items/versions", Risk.WRITE),
    ("PATCH", r"/items/versions/update", Risk.WRITE),
    ("POST", r"/documents-transfers/create", Risk.WRITE),
    ("POST", r"/documents-transfer-items/add", Risk.WRITE),
    ("PATCH", r"/issues", Risk.WRITE),
    ("POST", r"/reviews/create", Risk.WRITE),
    ("POST", r"/reviews/items/add", Risk.WRITE),
    # workflow profile
    ("POST", r"/documents-transfer-acceptances/send", Risk.WORKFLOW),
    ("POST", r"/reviews/process/start", Risk.WORKFLOW),
)

_COMPILED = tuple((method, re.compile(pattern + r"/?"), risk) for method, pattern, risk in ROUTES)


def route_risk(method: str, path: str) -> Optional[Risk]:
    for allowed_method, pattern, risk in _COMPILED:
        if method == allowed_method and pattern.fullmatch(path):
            return risk
    return None


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
            inner: Optional[httpx.AsyncBaseTransport] = None):
        parts = urlsplit(base_url)
        self.api_host = parts.netloc
        self.api_prefix = parts.path.rstrip("/")
        self.profile = profile
        self.inner = inner or httpx.AsyncHTTPTransport()
        self.bucket = TokenBucket(rate_per_sec, burst)
        self.semaphore = asyncio.Semaphore(max_concurrency)

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
        risk = route_risk(method, relative)
        if risk is None:
            raise PolicyDenied(f"{method} {relative} is not on the allowlist")
        if not self.profile.allows(risk):
            raise PolicyDenied(f"{method} {relative} needs the {risk.name.lower()} profile")
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
