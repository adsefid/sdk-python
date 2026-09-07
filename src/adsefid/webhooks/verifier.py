from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Callable
from typing import Any

from ..exceptions import AdsefidWebhookVerificationError
from .events import (
    MessengerStatusWebhookEvent,
    ReceiveWebhookEvent,
    StatusWebhookEvent,
    WebhookEvent,
)
from .headers import WebhookEventType

_SIGNATURE_PREFIX = "v1="

_EVENT_PARSERS: dict[str, Callable[[dict[str, Any]], WebhookEvent]] = {
    WebhookEventType.RECEIVE: ReceiveWebhookEvent.from_dict,
    WebhookEventType.STATUS: StatusWebhookEvent.from_dict,
    WebhookEventType.MESSENGER_STATUS: MessengerStatusWebhookEvent.from_dict,
}


def verify_and_parse_webhook(
    raw_body: bytes | str,
    signature_header: str,
    timestamp_header: str,
    secret: str,
    max_age_seconds: int = 300,
) -> WebhookEvent:
    """Verify an inbound webhook's HMAC signature and timestamp, then parse its body.

    Raises AdsefidWebhookVerificationError on bad signature, a stale timestamp,
    or a malformed/unrecognized JSON payload.
    """
    body_bytes = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body

    if not signature_header.startswith(_SIGNATURE_PREFIX):
        raise AdsefidWebhookVerificationError(
            f"Signature header must start with {_SIGNATURE_PREFIX!r}"
        )
    provided_signature = signature_header[len(_SIGNATURE_PREFIX) :]

    try:
        timestamp = int(timestamp_header)
    except (TypeError, ValueError) as exc:
        raise AdsefidWebhookVerificationError("Timestamp header is not a valid integer") from exc

    now = int(time.time())
    age = abs(now - timestamp)
    if age > max_age_seconds:
        raise AdsefidWebhookVerificationError(
            f"Webhook timestamp is stale: age={age}s exceeds max_age_seconds={max_age_seconds}"
        )

    # Signing input is the literal string f"{timestamp}.{raw_body}"; built here as
    # bytes concatenation to avoid a decode/re-encode round trip of the raw body.
    signing_input = f"{timestamp}.".encode() + body_bytes
    expected_digest = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    expected_signature = base64.b64encode(expected_digest).decode("ascii")

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise AdsefidWebhookVerificationError("Webhook signature mismatch")

    try:
        payload: Any = json.loads(body_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AdsefidWebhookVerificationError("Webhook body is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise AdsefidWebhookVerificationError("Webhook body must be a JSON object")

    event_type = payload.get("type")
    if not isinstance(event_type, str):
        raise AdsefidWebhookVerificationError(f"Unknown webhook event type: {event_type!r}")
    parser = _EVENT_PARSERS.get(event_type)
    if parser is None:
        raise AdsefidWebhookVerificationError(f"Unknown webhook event type: {event_type!r}")

    try:
        return parser(payload)
    except KeyError as exc:
        raise AdsefidWebhookVerificationError(
            f"Webhook payload is missing required field: {exc}"
        ) from exc
    except (AttributeError, TypeError, ValueError) as exc:
        raise AdsefidWebhookVerificationError("Webhook payload has an invalid field value") from exc
