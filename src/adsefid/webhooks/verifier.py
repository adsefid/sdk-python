from __future__ import annotations

import base64
import binascii
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


def _decode_secret(secret: str | bytes) -> bytes:
    """Turn the panel's secret into the raw HMAC key.

    A webhook endpoint's secret is 32 random bytes, and the adsefid.com panel
    shows it Base64-encoded. The service signs with those *decoded* bytes, so
    the Base64 must be undone before it is used as an HMAC key. Callers holding
    the decoded key already may pass `bytes` straight through.
    """
    if isinstance(secret, bytes | bytearray):
        return bytes(secret)
    try:
        return base64.b64decode(secret.strip(), validate=True)
    except (ValueError, binascii.Error) as exc:
        raise AdsefidWebhookVerificationError(
            "Webhook secret is not valid Base64; use the secret exactly as shown "
            "in your adsefid.com panel, or pass the decoded key as bytes"
        ) from exc


def verify_and_parse_webhook(
    raw_body: bytes | str,
    signature_header: str,
    timestamp_header: str,
    secret: str | bytes,
    max_age_seconds: int = 300,
) -> WebhookEvent:
    """Verify an inbound webhook's HMAC signature and timestamp, then parse its body.

    Args:
        raw_body: The exact request body as received. Re-serializing or
            reformatting it first breaks verification.
        signature_header: The `X-Atlas-Webhook-Signature` header value.
        timestamp_header: The `X-Atlas-Webhook-Timestamp` header value.
        secret: The endpoint's signing secret as shown in your adsefid.com
            panel, which is Base64 and is decoded here, or the already-decoded
            key as `bytes`.
        max_age_seconds: How stale a timestamp may be. Defaults to 5 minutes.

    Raises AdsefidWebhookVerificationError on a non-Base64 secret, a bad
    signature, a stale timestamp, or a malformed/unrecognized JSON payload.
    """
    body_bytes = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body
    key = _decode_secret(secret)

    if not signature_header.startswith(_SIGNATURE_PREFIX):
        raise AdsefidWebhookVerificationError(
            f"Signature header must start with {_SIGNATURE_PREFIX!r}"
        )
    provided_signature = signature_header[len(_SIGNATURE_PREFIX) :]

    try:
        timestamp = int(timestamp_header)
    except (TypeError, ValueError) as exc:
        raise AdsefidWebhookVerificationError("Timestamp header is not a valid integer") from exc

    # Signing input is the literal string f"{timestamp}.{raw_body}"; built here as
    # bytes concatenation to avoid a decode/re-encode round trip of the raw body.
    signing_input = f"{timestamp}.".encode() + body_bytes
    expected_digest = hmac.new(key, signing_input, hashlib.sha256).digest()
    expected_signature = base64.b64encode(expected_digest).decode("ascii")

    # Signature first, then freshness — the sibling SDKs check in this order, so
    # the same request reports the same failure everywhere.
    if not hmac.compare_digest(expected_signature, provided_signature):
        raise AdsefidWebhookVerificationError("Webhook signature mismatch")

    age = abs(int(time.time()) - timestamp)
    if age > max_age_seconds:
        raise AdsefidWebhookVerificationError(
            f"Webhook timestamp is stale: age={age}s exceeds max_age_seconds={max_age_seconds}"
        )

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
