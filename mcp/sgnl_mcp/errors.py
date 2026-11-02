from typing import Any, Optional

from sgnl_api import (
    SgnlApiError,
    SgnlAuthenticationError,
    SgnlBadRequestError,
    SgnlForbiddenError,
    SgnlNotFoundError,
    SgnlQuotaExceededError,
    SgnlRateLimitError,
    SgnlRequestError,
    SgnlServerError,
)


class ToolFailure(Exception):
    """An error returned to the agent as a structured result, not raised to the client."""

    def __init__(self, code: str, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class PolicyDenied(Exception):
    """Raised by the guarded transport before a forbidden request reaches the network."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class BudgetExceeded(Exception):
    """Raised by the guarded transport when a tool call used up its REST request budget."""


def describe_api_error(error: Exception, *, writing: bool) -> ToolFailure:
    """Maps an SDK exception to a tool error code (spec section 6.1)."""
    if isinstance(error, ToolFailure):
        return error
    if isinstance(error, PolicyDenied):
        return ToolFailure("POLICY_DENIED", error.message)
    if isinstance(error, BudgetExceeded):
        return ToolFailure("BUDGET_EXCEEDED", "Request budget for this tool call is used up")
    if isinstance(error, SgnlBadRequestError):
        return ToolFailure("INVALID_REQUEST", "SIGNAL rejected the request parameters", {"api_message": _short(error)})
    if isinstance(error, SgnlAuthenticationError):
        return ToolFailure("AUTH_FAILED", "Authentication with SIGNAL failed")
    if isinstance(error, SgnlForbiddenError):
        return ToolFailure("FORBIDDEN", "Not allowed: the token lacks a scope or the account has no rights on this object")
    if isinstance(error, SgnlNotFoundError):
        return ToolFailure("NOT_FOUND", "Object not found or not visible to this account")
    if isinstance(error, SgnlQuotaExceededError):
        return ToolFailure("QUOTA_EXCEEDED", "SIGNAL resource quota reached; contact SIGNAL support")
    if isinstance(error, SgnlRateLimitError):
        return ToolFailure("RATE_LIMITED", "SIGNAL rate limit hit", {"retry_after": error.retry_after})
    if isinstance(error, (SgnlServerError, SgnlRequestError)):
        if writing:
            return ToolFailure(
                "OUTCOME_UNKNOWN",
                "The write request failed without a clear answer; it may or may not have been applied",
            )
        code = "SERVER_ERROR" if isinstance(error, SgnlServerError) else "NETWORK_ERROR"
        return ToolFailure(code, "SIGNAL did not answer correctly; try again later")
    if isinstance(error, SgnlApiError):
        return ToolFailure("API_ERROR", "SIGNAL returned an unexpected error", {"status": error.status_code})
    return ToolFailure("INTERNAL_ERROR", f"Unexpected error: {type(error).__name__}")


def _short(error: SgnlApiError, limit: int = 500) -> Any:
    return error.message[:limit]
