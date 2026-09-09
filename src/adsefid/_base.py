from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, NoReturn

import httpx

from .enums import parse_response_code
from .exceptions import AdsefidApiError, AdsefidRateLimitError, AdsefidTransportError

API_KEY_HEADER = "X-API-KEY"
_RATE_LIMIT_RAW_CODES = {2035, 2036}


def build_headers(api_key: str, user_agent: str) -> dict[str, str]:
    return {API_KEY_HEADER: api_key, "User-Agent": user_agent}


def build_query_params(
    params: Mapping[str, str | int | None] | None,
) -> dict[str, str | int] | None:
    if not params:
        return None
    return {key: value for key, value in params.items() if value is not None}


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
    query_params: Mapping[str, str | int | None] | None = None,
    files: dict[str, Any] | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "method": method,
        "url": build_url(base_url, path),
        "headers": build_headers(api_key, user_agent),
    }
    params = build_query_params(query_params)
    if params:
        kwargs["params"] = params
    if json_body is not None:
        kwargs["json"] = json_body
    if files is not None:
        kwargs["files"] = files
    return kwargs


def parse_success_data(http_status_code: int, raw_body: bytes) -> dict[str, Any] | list[Any]:
    parsed: Any = None
    if raw_body:
        try:
            parsed = json.loads(raw_body)
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

    _raise_api_error(http_status_code, parsed)


def _raise_api_error(http_status_code: int, parsed: Any) -> NoReturn:
    if isinstance(parsed, dict) and isinstance(parsed.get("error"), dict):
        error = parsed["error"]
        raw_code = error.get("code", http_status_code)
        name = error.get("name") or f"HTTP_{http_status_code}"
        details = error.get("details")
        if isinstance(raw_code, int):
            enum_code, raw_code_int = parse_response_code(raw_code)
            code: Any = enum_code if enum_code is not None else raw_code_int
        else:
            raw_code_int = http_status_code
            code = raw_code_int
        message = f"adsefid API error {name} (code={raw_code_int}, http={http_status_code})"
        if raw_code_int in _RATE_LIMIT_RAW_CODES:
            raise AdsefidRateLimitError(
                message, code=code, name=name, http_status_code=http_status_code, details=details
            )
        raise AdsefidApiError(
            message, code=code, name=name, http_status_code=http_status_code, details=details
        )

    if http_status_code == 429:
        raise AdsefidRateLimitError(
            "HTTP 429 rate limited (response body was empty or not a recognized error envelope)",
            code=http_status_code,
            name="RATE_LIMITED",
            http_status_code=http_status_code,
            details=None,
        )

    raise AdsefidApiError(
        f"HTTP {http_status_code} error with no parseable error envelope",
        code=http_status_code,
        name=f"HTTP_{http_status_code}",
        http_status_code=http_status_code,
        details=None,
    )


def wrap_transport_error(exc: httpx.TransportError) -> AdsefidTransportError:
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
