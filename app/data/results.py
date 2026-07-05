"""Step 2 — Safe result wrapper for external API calls.

Think of ApiResult as a sealed delivery box: it always arrives with either data or a
clean error string, never an uncaught exception reaching the caller.
"""

from dataclasses import dataclass
from typing import Generic, TypeVar

import httpx

T = TypeVar("T")


@dataclass
class ApiResult(Generic[T]):
    """Either ``data`` or ``error`` — never both, never an escaping exception."""

    data: T | None = None
    error: str | None = None
    # True if a retry might help (timeout / 429); False for permanent errors (403, 404)
    transient: bool = False

    @property
    def ok(self) -> bool:
        """Returns True if the API call was successful (no error)."""
        return self.error is None and self.data is not None


def is_transient(exc: Exception) -> bool:
    """Determine if an exception is transient (worth retrying) or permanent."""
    if isinstance(exc, httpx.TimeoutException):
        # Network-related errors are usually transient
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        # 429 rate limits and 5xx server errors may succeed on retry
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return False


def explain_error(exc: Exception) -> str:
    """Turn an exception into a short, human-readable error string for ApiResult."""
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
    if isinstance(exc, httpx.TimeoutException):
        return "Request timed out"
    return str(exc)