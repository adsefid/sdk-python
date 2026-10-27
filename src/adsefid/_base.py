from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal
from typing import Any, NoReturn, TypeVar
from urllib.parse import quote, urlsplit

import httpx

from .enums import WebServiceResponseCode, parse_response_code
from .exceptions import (
    AdsefidApiError,
    AdsefidRateLimitError,
    AdsefidTransportError,
    AdsefidValidationError,
)
from .models.errors import ApiErrorDetails

API_KEY_HEADER = "X-API-KEY"
_RATE_LIMIT_RAW_CODES = {
    WebServiceResponseCode.MESSAGE_LIMIT_REACHED.value,
    WebServiceResponseCode.REQUEST_LIMIT_REACHED.value,
}
UNKNOWN_ERROR_CODE = -1
_HTTP_TOO_MANY_REQUESTS = 429
_SHAPE_ERRORS = (KeyError, TypeError, ValueError, AttributeError, ArithmeticError)
_T = TypeVar("_T")


def build_headers(api_key: str, user_agent: str) -> dict[str, str]:
    return {API_KEY_HEADER: api_key, "User-Agent": user_agent}


QueryValue = str | int | Sequence[str] | None

MAX_REQUEST_TARGET_LENGTH = 8000
"""Longest path-and-query the SDK sends.

The service sits behind a proxy that rejects request lines over 8 KiB with an HTML
414, so a GET with a very long id list is refused locally.
"""


def encode_query(params: Mapping[str, QueryValue] | None) -> str:
    """Build a query string. A sequence becomes a deduplicated list joined by a literal
    comma, which the service reads as the separator and which keeps the URL a third
    shorter than ``%2C`` would."""
    pairs: list[str] = []
    for key, value in (params or {}).items():
        if value is None:
            continue
        if isinstance(value, str | int):
            encoded = quote(str(value), safe="")
        else:
            encoded = ",".join(quote(item, safe="") for item in dict.fromkeys(value))
        if encoded:
            pairs.append(f"{key}={encoded}")
    return "&".join(pairs)


def build_url(base_url: str, path: str) -> str:
    """Join the configured base URL and an endpoint path into one absolute URL.

    The SDK always sends absolute URLs, so a caller-supplied `httpx.Client` needs
    no `base_url` of its own.
    """
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def build_request_kwargs(
    *,
    method: str,
    base_url: str,
    path: str,
    api_key: str,
    user_agent: str,
    json_body: dict[str, Any] | None = None,
    query_params: Mapping[str, QueryValue] | None = None,
    files: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = build_url(base_url, path)
    query = encode_query(query_params)
    if query:
        url = f"{url}?{query}"
    if method == "GET":
        parts = urlsplit(url)
        target_length = len(parts.path) + 1 + len(parts.query) if parts.query else len(parts.path)
        if target_length > MAX_REQUEST_TARGET_LENGTH:
            raise AdsefidValidationError(
                f"The request URL is {target_length} characters long, over the "
                f"{MAX_REQUEST_TARGET_LENGTH} the service accepts; send fewer ids per call."
            )
    kwargs: dict[str, Any] = {
        "method": method,
        "url": url,
        "headers": build_headers(api_key, user_agent),
    }
    if json_body is not None:
        kwargs["json"] = json_body
    if files is not None:
        kwargs["files"] = files
    return kwargs


def parse_success_data(http_status_code: int, raw_body: bytes) -> dict[str, Any] | list[Any]:
    parsed: Any = None
    if raw_body:
        try:
            parsed = json.loads(raw_body, parse_float=Decimal)
        except (json.JSONDecodeError, UnicodeDecodeError):
            parsed = None

    is_success = 200 <= http_status_code < 300
    if isinstance(parsed, dict) and parsed.get("status") == "success" and is_success:
        data = parsed.get("data")
        if not isinstance(data, dict | list):
            # A success envelope with no usable payload is a malformed response,
            # not a successful call. Returning {} here would push the failure
            # into a model's from_dict as a bare KeyError.
            raise AdsefidTransportError(
                "The API returned a success envelope with a missing or unusable 'data' payload"
            )
        return data

    has_error_envelope = isinstance(parsed, dict) and isinstance(parsed.get("error"), dict)
    if is_success and not has_error_envelope:
        raise AdsefidTransportError(
            f"The API returned HTTP {http_status_code} with a malformed success envelope"
        )
    _raise_api_error(http_status_code, parsed)


def _raise_api_error(http_status_code: int, parsed: Any) -> NoReturn:
    if isinstance(parsed, dict) and isinstance(parsed.get("error"), dict):
        error = parsed["error"]
        raw_code = error.get("code", http_status_code)
        name = error.get("name") or f"HTTP_{http_status_code}"
        raw_details = error.get("details")
        details: ApiErrorDetails | None = None
        if isinstance(raw_details, dict):
            try:
                details = ApiErrorDetails.from_dict(raw_details)
            except _SHAPE_ERRORS:
                details = None
        if isinstance(raw_code, int):
            enum_code, raw_code_int = parse_response_code(raw_code)
            code: Any = enum_code if enum_code is not None else raw_code_int
        else:
            raw_code_int = http_status_code
            code = raw_code_int
        message = f"adsefid API error {name} (code={raw_code_int}, http={http_status_code})"
        if raw_code_int in _RATE_LIMIT_RAW_CODES or http_status_code == _HTTP_TOO_MANY_REQUESTS:
            raise AdsefidRateLimitError(
                message, code=code, name=name, http_status_code=http_status_code, details=details
            )
        raise AdsefidApiError(
            message, code=code, name=name, http_status_code=http_status_code, details=details
        )

    if http_status_code == _HTTP_TOO_MANY_REQUESTS:
        raise AdsefidRateLimitError(
            "HTTP 429 rate limited (response body was empty or not a recognized error envelope)",
            code=WebServiceResponseCode.REQUEST_LIMIT_REACHED,
            name="RATE_LIMITED",
            http_status_code=http_status_code,
            details=None,
        )

    raise AdsefidApiError(
        f"HTTP {http_status_code} error with no parseable error envelope",
        code=UNKNOWN_ERROR_CODE,
        name="UNKNOWN_ERROR",
        http_status_code=http_status_code,
        details=None,
    )


def wrap_transport_error(exc: httpx.RequestError) -> AdsefidTransportError:
    return AdsefidTransportError(f"Transport error while calling adsefid API: {exc}")


def expect_object(data: dict[str, Any] | list[Any]) -> dict[str, Any]:
    """Narrow a success payload to the JSON object an endpoint documents.

    A list where an object was expected is a malformed response, surfaced as
    `AdsefidTransportError` rather than as a bare `TypeError`/`KeyError` from a
    model's `from_dict`.
    """
    if not isinstance(data, dict):
        raise AdsefidTransportError(
            "The API returned a JSON array where an object payload was expected"
        )
    return data


def expect_list(data: dict[str, Any] | list[Any]) -> list[Any]:
    """Narrow a success payload to the JSON array an endpoint documents."""
    if not isinstance(data, list):
        raise AdsefidTransportError(
            "The API returned a JSON object where an array payload was expected"
        )
    return data


def parse_object(factory: Callable[[dict[str, Any]], _T], data: dict[str, Any] | list[Any]) -> _T:
    """Build a model from an object payload; a malformed body becomes `AdsefidTransportError`."""
    obj = expect_object(data)
    try:
        return factory(obj)
    except _SHAPE_ERRORS as exc:
        raise AdsefidTransportError(f"The API response had an unexpected shape: {exc!r}") from exc


def parse_list(
    factory: Callable[[dict[str, Any]], _T], data: dict[str, Any] | list[Any]
) -> list[_T]:
    """Build models from an array payload; a malformed body becomes `AdsefidTransportError`."""
    items = expect_list(data)
    try:
        return [factory(item) for item in items]
    except _SHAPE_ERRORS as exc:
        raise AdsefidTransportError(f"The API response had an unexpected shape: {exc!r}") from exc
