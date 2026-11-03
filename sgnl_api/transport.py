import asyncio
import json as jsonlib
from datetime import date, datetime, timedelta
from uuid import UUID
from typing import List, Optional, Union

import httpx

from .exceptions import (
    SgnlApiError,
    SgnlAuthenticationError,
    SgnlBadRequestError,
    SgnlCredentialError,
    SgnlForbiddenError,
    SgnlLicenseError,
    SgnlNotFoundError,
    SgnlQuotaExceededError,
    SgnlRateLimitError,
    SgnlRequestError,
    SgnlScopeError,
    SgnlServerError,
)
from .scopes import SCOPES_HELP
from .utils import keys_to_snake_case

DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3
# Upper bound for a single wait on 429, so a misbehaving Retry-After cannot stall the caller for minutes.
MAX_RETRY_AFTER = 30.0
# Wait used when a 429 response has no usable Retry-After header.
DEFAULT_RETRY_AFTER = 1.0

_ERROR_CLASSES = {
    400: SgnlBadRequestError,
    401: SgnlAuthenticationError,
    403: SgnlForbiddenError,
    404: SgnlNotFoundError,
    429: SgnlRateLimitError,
    450: SgnlQuotaExceededError,
}

_STATUS_REASONS = {
    400: "Bad request",
    401: "The request did not have the correct authorization header credentials",
    403: "Forbidden",
    404: "Not found",
    429: "Too many requests",
    450: "Maximum resource quota reached. To increase the quota, contact support",
}


def _error_class_for(status_code: int) -> type:
    if status_code in _ERROR_CLASSES:
        return _ERROR_CLASSES[status_code]
    if status_code >= 500:
        return SgnlServerError
    return SgnlApiError


def _json_default(value):
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _encode_json(payload) -> bytes:
    """Serializes a request body, accepting UUID, datetime and date values as the API's string formats."""
    return jsonlib.dumps(payload, default=_json_default, ensure_ascii=False).encode("utf-8")


def _parse_retry_after(response: httpx.Response) -> Optional[float]:
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return max(float(value), 0.0)
    except ValueError:
        return None


class Transport:
    """Owns the HTTP connection pool, auth token lifecycle and rate-limit retries for the SGNL API."""

    def __init__(
            self,
            *,
            client_id: str,
            client_secret: str,
            scopes: List[str],
            base_url: str,
            timeout: float = DEFAULT_TIMEOUT,
            max_retries: int = DEFAULT_MAX_RETRIES,
            http_client: Optional[httpx.AsyncClient] = None) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes
        self.base_url = base_url
        self.max_retries = max_retries
        self._jwt = None
        self._jwt_expires_at = None
        self._token_lock = asyncio.Lock()
        # A caller-supplied client (e.g. one with its own httpx transport that filters or
        # throttles requests) is used as is and stays owned by the caller.
        self._owns_client = http_client is None
        self._client = http_client if http_client is not None else httpx.AsyncClient(timeout=timeout)

    @property
    def client(self) -> httpx.AsyncClient:
        return self._client

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _send(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Sends a request, retrying on 429 up to ``max_retries`` times, honoring Retry-After.

        Returns the last response, which may still be a 429 if retries were exhausted.
        Network-level failures are raised as SgnlRequestError.
        """
        attempt = 0
        while True:
            try:
                response = await self._client.request(method=method, url=url, **kwargs)
            except httpx.HTTPError as e:
                raise SgnlRequestError(f"{method} {url} failed: {e}") from e

            if response.status_code != 429 or attempt >= self.max_retries:
                return response

            retry_after = _parse_retry_after(response)
            delay = DEFAULT_RETRY_AFTER if retry_after is None else retry_after
            await asyncio.sleep(min(delay, MAX_RETRY_AFTER))
            attempt += 1

    async def _invalidate_token(self, rejected_jwt: Optional[str]) -> None:
        async with self._token_lock:
            # Only drop the token the server rejected; a concurrent request may already have refreshed it.
            if self._jwt == rejected_jwt:
                self._jwt = None
                self._jwt_expires_at = None

    def _auth_error(self, response: httpx.Response) -> SgnlAuthenticationError:
        """Turns a refused token request into an exception that says what to fix."""
        try:
            code = response.json()
        except ValueError:
            code = None
        status = response.status_code
        requested = ", ".join(self.scopes)
        if code == "ScopeError":
            return SgnlScopeError(
                f"SIGNAL refused the token: the integration does not have every requested scope. "
                f"Requested: {requested}. {SCOPES_HELP}",
                status_code=status, requested_scopes=tuple(self.scopes)
            )
        if code == "CredentialError":
            return SgnlCredentialError(
                "SIGNAL refused the token: invalid client id or client secret "
                "(after \"Обновить ключ доступа\" the old secret stops working).",
                status_code=status
            )
        if code == "LicenseError":
            return SgnlLicenseError(
                f"SIGNAL refused the token: the company has no license for a module of one of the "
                f"requested scopes. Requested: {requested}.",
                status_code=status
            )
        return SgnlAuthenticationError(
            f"Authentication failed with status {status}: {response.text}",
            status_code=status
        )

    async def _ensure_token(self) -> None:
        async with self._token_lock:
            if self._jwt is not None and self._jwt_expires_at and datetime.now() < self._jwt_expires_at:
                return
            try:
                response = await self._send(
                    'POST',
                    f'{self.base_url}/auth/token',
                    json={
                        "clientId": self.client_id,
                        "clientSecret": self.client_secret,
                        "scopes": self.scopes
                    },
                    headers={'Content-Type': 'application/json'}
                )
            except SgnlRequestError as e:
                raise SgnlAuthenticationError(f"Authentication failed: {e}") from e

            if response.status_code == 429:
                raise SgnlRateLimitError(
                    f"Authentication failed: too many requests: {response.text}",
                    retry_after=_parse_retry_after(response)
                )
            if not response.is_success:
                raise self._auth_error(response)

            data = response.json()
            self._jwt = data.get('token')
            expires_in = data.get('expiresIn', 3600)
            self._jwt_expires_at = datetime.now() + timedelta(seconds=expires_in)

    async def request(
            self,
            method: str,
            path: str,
            *,
            params: Optional[dict] = None,
            json: Union[dict, list, None] = None) -> Union[dict, list, str, int, None]:
        content = _encode_json(json) if json is not None else None

        response = None
        for attempt in range(2):
            await self._ensure_token()
            jwt = self._jwt
            headers = {
                "accept": "application/json",
                "Authorization": f"Bearer {jwt}"
            }
            if content is not None:
                headers["Content-Type"] = "application/json"

            response = await self._send(
                method,
                f'{self.base_url}{path}',
                params=params,
                content=content,
                headers=headers
            )
            # A token revoked before its expiresIn: refresh once and resend. 401 means the request
            # was rejected before processing, so resending is safe for writes too.
            if response.status_code == 401 and attempt == 0:
                await self._invalidate_token(jwt)
                continue
            break

        if response.is_success:
            if not response.content:
                return None
            return keys_to_snake_case(response.json())

        reason = _STATUS_REASONS.get(response.status_code, "Unexpected error")
        message = f"{method} {path} -> {response.status_code} {reason}: {response.text}"
        if response.status_code == 429:
            raise SgnlRateLimitError(message, retry_after=_parse_retry_after(response))
        if response.status_code == 403:
            message += (f" [403 is either a missing scope or no access for the user. The token was issued "
                        f"for: {', '.join(self.scopes)}; the method's docstring names the scope it needs.]")
        raise _error_class_for(response.status_code)(message, status_code=response.status_code)
