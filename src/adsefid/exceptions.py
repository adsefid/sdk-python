from __future__ import annotations

from .enums import WebServiceResponseCode
from .models.errors import ApiErrorDetails


class AdsefidError(Exception):
    """Base class for all errors raised by this SDK."""


class AdsefidValidationError(AdsefidError):
    """Raised by client-side pre-flight validation before any network call is made."""


class AdsefidApiError(AdsefidError):
    """Raised when the API responds with an error envelope or a non-2xx HTTP status.

    Attributes:
        code: The parsed `WebServiceResponseCode` member, or the raw `int` if the
            server returned a code not yet in that enum.
        name: The error name string from the response envelope (or a synthesized
            `HTTP_<status>` when the body had no error envelope).
        http_status_code: The HTTP status code of the response.
        details: Structured field/item error details, or `None` when absent.
    """

    def __init__(
        self,
        message: str,
        *,
        code: WebServiceResponseCode | int,
        name: str,
        http_status_code: int,
        details: ApiErrorDetails | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.name = name
        self.http_status_code = http_status_code
        self.details = details

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(code={self.code!r}, name={self.name!r}, "
            f"http_status_code={self.http_status_code!r}, details={self.details!r})"
        )


class AdsefidRateLimitError(AdsefidApiError):
    """Raised for WebServiceResponseCode 2035/2036, or a bare HTTP 429 with an unparseable body."""


class AdsefidTransportError(AdsefidError):
    """Wraps a network-level failure (connection error, timeout, etc.)."""


class AdsefidWebhookVerificationError(AdsefidError):
    """Raised when an inbound webhook fails signature verification, is stale, or is malformed."""
