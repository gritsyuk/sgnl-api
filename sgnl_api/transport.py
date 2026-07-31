import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Union

import httpx

from .exceptions import (
    SgnlApiError,
    SgnlAuthenticationError,
    SgnlBadRequestError,
    SgnlForbiddenError,
    SgnlNotFoundError,
    SgnlQuotaExceededError,
    SgnlRequestError,
    SgnlServerError,
)
from .utils import keys_to_snake_case

DEFAULT_TIMEOUT = 30.0

_ERROR_CLASSES = {
    400: SgnlBadRequestError,
    401: SgnlAuthenticationError,
    403: SgnlForbiddenError,
    404: SgnlNotFoundError,
    450: SgnlQuotaExceededError,
}

_STATUS_REASONS = {
    400: "Bad request",
    401: "The request did not have the correct authorization header credentials",
    403: "Forbidden",
    404: "Not found",
    450: "Maximum resource quota reached. To increase the quota, contact support",
}


def _error_class_for(status_code: int) -> type:
    if status_code in _ERROR_CLASSES:
        return _ERROR_CLASSES[status_code]
    if status_code >= 500:
        return SgnlServerError
    return SgnlApiError


class Transport:
    """Owns the HTTP connection pool and auth token lifecycle for the SGNL API."""

    def __init__(
            self,
            *,
            client_id: str,
            client_secret: str,
            scopes: List[str],
            base_url: str,
            timeout: float = DEFAULT_TIMEOUT) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes
        self.base_url = base_url
        self._jwt = None
        self._jwt_expires_at = None
        self._token_lock = asyncio.Lock()
        self._client = httpx.AsyncClient(timeout=timeout)

    @property
    def client(self) -> httpx.AsyncClient:
        return self._client

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _ensure_token(self) -> None:
        async with self._token_lock:
            if self._jwt is not None and self._jwt_expires_at and datetime.now() < self._jwt_expires_at:
                return
            try:
                response = await self._client.post(
                    f'{self.base_url}/auth/token',
                    json={
                        "clientId": self.client_id,
                        "clientSecret": self.client_secret,
                        "scopes": self.scopes
                    },
                    headers={'Content-Type': 'application/json'}
                )
                response.raise_for_status()
            except httpx.HTTPError as e:
                raise SgnlAuthenticationError(f"Authentication failed: {e}") from e

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
            json: Optional[dict] = None) -> Union[dict, list, None]:
        await self._ensure_token()

        try:
            response = await self._client.request(
                method=method,
                url=f'{self.base_url}{path}',
                params=params,
                json=json,
                headers={
                    "accept": "application/json",
                    "Authorization": f"Bearer {self._jwt}"
                }
            )
        except httpx.HTTPError as e:
            raise SgnlRequestError(f"{method} {path} failed: {e}") from e

        if response.is_success:
            if not response.content:
                return None
            return keys_to_snake_case(response.json())

        reason = _STATUS_REASONS.get(response.status_code, "Unexpected error")
        error_class = _error_class_for(response.status_code)
        raise error_class(
            f"{method} {path} -> {response.status_code} {reason}: {response.text}",
            status_code=response.status_code
        )
