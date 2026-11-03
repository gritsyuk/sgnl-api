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
    """Raised on 401 - invalid, missing or expired credentials - and when a token cannot be issued."""


class _TokenRefusedError(SgnlAuthenticationError):
    """SIGNAL refused to issue a token for the requested scopes.

    ``requested_scopes`` is what was sent. When the client could work out which scopes were
    refused, ``missing_scopes`` lists those not enabled for the integration and
    ``unlicensed_scopes`` those the company has no license for; otherwise both are empty.
    """

    def __init__(self, message: str, *, status_code: Optional[int] = 422, requested_scopes: tuple = (),
                 missing_scopes: tuple = (), unlicensed_scopes: tuple = ()):
        super().__init__(message, status_code=status_code)
        self.requested_scopes = tuple(requested_scopes)
        self.missing_scopes = tuple(missing_scopes)
        self.unlicensed_scopes = tuple(unlicensed_scopes)


class SgnlScopeError(_TokenRefusedError):
    """A requested scope is not enabled for the integration in SIGNAL ("Редактировать интеграцию"),
    or the list was empty. See ``missing_scopes``."""


class SgnlCredentialError(SgnlAuthenticationError):
    """The client id or client secret is wrong (or the secret was rotated)."""


class SgnlLicenseError(_TokenRefusedError):
    """The company has no license for a module one of the requested scopes belongs to.
    See ``unlicensed_scopes``."""


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
