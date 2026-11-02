from typing import Optional


class SgnlApiError(Exception):
    """Base exception for all SGNL API errors."""

    def __init__(self, message: str, *, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class SgnlRequestError(SgnlApiError):
    """Raised on network/transport-level failures (timeouts, connection errors)."""


class SgnlAuthenticationError(SgnlApiError):
    """Raised on 401 - invalid, missing or expired credentials."""


class SgnlBadRequestError(SgnlApiError):
    """Raised on 400 - malformed request."""


class SgnlForbiddenError(SgnlApiError):
    """Raised on 403 - insufficient scopes/permissions."""


class SgnlNotFoundError(SgnlApiError):
    """Raised on 404 - resource not found."""


class SgnlQuotaExceededError(SgnlApiError):
    """Raised on 450 - maximum resource quota reached."""


class SgnlRateLimitError(SgnlApiError):
    """Raised on 429 - too many requests, after automatic retries are exhausted.

    ``retry_after`` holds the number of seconds the server asked to wait (from the
    ``Retry-After`` header), or ``None`` if the header was missing or unparsable.
    """

    def __init__(self, message: str, *, status_code: Optional[int] = 429, retry_after: Optional[float] = None):
        super().__init__(message, status_code=status_code)
        self.retry_after = retry_after


class SgnlServerError(SgnlApiError):
    """Raised on 5xx - API server error."""
