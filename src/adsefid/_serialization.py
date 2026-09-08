from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from .exceptions import AdsefidValidationError

LOCAL_ID_PATTERN = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9\-_.:]{0,34}[A-Za-z0-9])?$")

SMS_MESSAGE_MAX_LENGTH = 900
MESSENGER_MESSAGE_MAX_LENGTH = 4000
MAX_STATUS_IDS = 2000
MIN_RECEIVE_COUNT = 1
MAX_RECEIVE_COUNT = 499
MIN_TEMPLATE_TAKE = 1
MAX_TEMPLATE_TAKE = 100


def parse_datetime(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp, tolerating a trailing 'Z' (not accepted by
    datetime.fromisoformat on the Python 3.10 floor)."""
    if value is None:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


def format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def join_csv(values: Sequence[str] | None) -> str | None:
    if not values:
        return None
    return ",".join(values)


def validate_local_id(local_id: str | None, *, field_name: str = "local_id") -> None:
    """Validate an optional local_id.

    The service normalizes a blank value to "not supplied" before validating,
    so `None`, `""` and whitespace-only are all accepted and simply omitted.
    """
    if local_id is None or not local_id.strip():
        return
    if not LOCAL_ID_PATTERN.match(local_id):
        raise AdsefidValidationError(
            f"{field_name!r} must be 1-36 ASCII letters/digits, with '- _ . :' "
            f"allowed only inside (not as first/last character); got {local_id!r}"
        )


def validate_non_empty(value: str | None, *, field_name: str) -> None:
    if value is None or value == "":
        raise AdsefidValidationError(f"{field_name!r} is required and must be non-empty")


def utf16_length(value: str) -> int:
    """Length of `value` in UTF-16 code units.

    The service counts its length limits in UTF-16 code units, so a character
    outside the Basic Multilingual Plane (an emoji, say) costs two. Python's
    `len()` counts code points and would accept a message the service rejects.
    """
    return len(value.encode("utf-16-le")) // 2


def validate_max_length(value: str, *, field_name: str, max_length: int) -> None:
    length = utf16_length(value)
    if length > max_length:
        raise AdsefidValidationError(
            f"{field_name!r} must be at most {max_length} characters; got {length}"
        )


def validate_ids_count(
    message_ids: Sequence[str] | None,
    local_ids: Sequence[str] | None,
    *,
    max_total: int = MAX_STATUS_IDS,
    require_at_least_one: bool = True,
) -> None:
    message_id_count = len(message_ids) if message_ids else 0
    local_id_count = len(local_ids) if local_ids else 0
    if require_at_least_one and message_id_count == 0 and local_id_count == 0:
        raise AdsefidValidationError("At least one of 'message_ids'/'local_ids' is required")
    combined = len(set(message_ids or ())) + len(set(local_ids or ()))
    if combined > max_total:
        raise AdsefidValidationError(
            "Combined count of distinct 'message_ids'+'local_ids' must be "
            f"<= {max_total}; got {combined}"
        )


def validate_take(take: int | None) -> None:
    if take is None:
        return
    if not (MIN_TEMPLATE_TAKE <= take <= MAX_TEMPLATE_TAKE):
        raise AdsefidValidationError(
            f"'take' must be between {MIN_TEMPLATE_TAKE} and {MAX_TEMPLATE_TAKE}; got {take}"
        )


def validate_skip(skip: int | None) -> None:
    if skip is None:
        return
    if skip < 0:
        raise AdsefidValidationError(f"'skip' must be non-negative; got {skip}")


def validate_receive_count(count: int | None) -> None:
    if count is None:
        return
    if not (MIN_RECEIVE_COUNT <= count <= MAX_RECEIVE_COUNT):
        raise AdsefidValidationError(
            f"'count' must be between {MIN_RECEIVE_COUNT} and {MAX_RECEIVE_COUNT}; got {count}"
        )


def optional(data: dict[str, Any], key: str) -> Any | None:
    return data.get(key)


def require(data: dict[str, Any], key: str) -> Any:
    if key not in data:
        raise AdsefidValidationError(f"Response payload is missing required field {key!r}")
    return data[key]
