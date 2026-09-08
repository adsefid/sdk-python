"""Webhook signature verification and event parsing."""

from __future__ import annotations

import base64

import pytest

from adsefid import (
    AdsefidWebhookVerificationError,
    MessengerStatusWebhookEvent,
    ReceiveWebhookEvent,
    StatusWebhookEvent,
    WebhookEventType,
    WebhookHeaders,
    WebServiceMessageStatus,
    verify_and_parse_webhook,
)
from tests.helpers.fixtures import fixture_bytes, fixture_json
from tests.helpers.webhook_sign import now_timestamp, sign

VECTOR = fixture_json("webhooks/signature_vector.json")
A_CENTURY = 100 * 365 * 24 * 60 * 60


def golden_body() -> bytes:
    return fixture_bytes(VECTOR["body_file"])


def test_the_golden_vector_verifies() -> None:
    """The cross-SDK vector.

    It is what proves the HMAC key is the Base64-DECODED secret bytes rather
    than the UTF-8 bytes of the Base64 string the panel shows. Its timestamp is
    fixed, so the staleness window has to be opened wide.
    """
    event = verify_and_parse_webhook(
        raw_body=golden_body(),
        signature_header=VECTOR["signature"],
        timestamp_header=VECTOR["timestamp"],
        secret=VECTOR["secret"],
        max_age_seconds=A_CENTURY,
    )

    assert isinstance(event, ReceiveWebhookEvent)
    assert event.type == WebhookEventType.RECEIVE
    assert event.attempt == 1
    assert event.version == "1"
    assert event.occurred_at is not None
    assert len(event.data) == 1
    assert event.data[0].sender
    assert event.data[0].message


def test_a_utf8_keyed_signature_is_rejected() -> None:
    """Regression guard for the key-derivation fix.

    Keying the HMAC with the text of the Base64 secret is what this SDK used to
    do, and it never matched a real delivery.
    """
    import hashlib
    import hmac

    signing_input = f"{VECTOR['timestamp']}.".encode() + golden_body()
    digest = hmac.new(VECTOR["secret"].encode("utf-8"), signing_input, hashlib.sha256).digest()
    wrong_signature = "v1=" + base64.b64encode(digest).decode("ascii")

    assert wrong_signature != VECTOR["signature"], "the vector is degenerate"

    with pytest.raises(AdsefidWebhookVerificationError):
        verify_and_parse_webhook(
            raw_body=golden_body(),
            signature_header=wrong_signature,
            timestamp_header=VECTOR["timestamp"],
            secret=VECTOR["secret"],
            max_age_seconds=A_CENTURY,
        )


def test_the_decoded_key_may_be_passed_as_bytes() -> None:
    key = base64.b64decode(VECTOR["secret"], validate=True)

    event = verify_and_parse_webhook(
        raw_body=golden_body(),
        signature_header=VECTOR["signature"],
        timestamp_header=VECTOR["timestamp"],
        secret=key,
        max_age_seconds=A_CENTURY,
    )

    assert isinstance(event, ReceiveWebhookEvent)


def test_a_str_body_is_accepted_as_well_as_bytes() -> None:
    event = verify_and_parse_webhook(
        raw_body=golden_body().decode("utf-8"),
        signature_header=VECTOR["signature"],
        timestamp_header=VECTOR["timestamp"],
        secret=VECTOR["secret"],
        max_age_seconds=A_CENTURY,
    )

    assert isinstance(event, ReceiveWebhookEvent)


@pytest.mark.parametrize(
    ("fixture", "expected_type", "expected_event"),
    [
        pytest.param(
            "webhooks/receive.body.json",
            ReceiveWebhookEvent,
            WebhookEventType.RECEIVE,
            id="receive",
        ),
        pytest.param(
            "webhooks/status.body.json",
            StatusWebhookEvent,
            WebhookEventType.STATUS,
            id="status",
        ),
        pytest.param(
            "webhooks/messenger_status.body.json",
            MessengerStatusWebhookEvent,
            WebhookEventType.MESSENGER_STATUS,
            id="messenger status",
        ),
    ],
)
def test_each_event_type_parses_to_its_own_class(fixture, expected_type, expected_event) -> None:
    body = fixture_bytes(fixture)
    timestamp = now_timestamp()

    event = verify_and_parse_webhook(
        raw_body=body,
        signature_header=sign(VECTOR["secret"], timestamp, body),
        timestamp_header=timestamp,
        secret=VECTOR["secret"],
    )

    assert isinstance(event, expected_type)
    assert event.type == expected_event
    assert event.data


def test_status_items_carry_a_typed_delivery_status() -> None:
    body = fixture_bytes("webhooks/status.body.json")
    timestamp = now_timestamp()

    event = verify_and_parse_webhook(
        raw_body=body,
        signature_header=sign(VECTOR["secret"], timestamp, body),
        timestamp_header=timestamp,
        secret=VECTOR["secret"],
    )

    assert isinstance(event, StatusWebhookEvent)
    item = event.data[0]
    assert item.status_delivery is WebServiceMessageStatus.DELIVERED
    assert item.local_id == "order-10001"
    assert item.delivery_time is not None


def _fresh_signature(body: bytes | None = None) -> tuple[bytes, str, str]:
    body = body or golden_body()
    timestamp = now_timestamp()
    return body, sign(VECTOR["secret"], timestamp, body), timestamp


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda body, sig, ts: (body, VECTOR["tampered_signature"], VECTOR["timestamp"]),
            id="tampered signature",
        ),
        pytest.param(lambda body, sig, ts: (body + b" ", sig, ts), id="tampered body"),
        pytest.param(
            lambda body, sig, ts: (body, sig.removeprefix("v1="), ts), id="missing v1= prefix"
        ),
        pytest.param(
            lambda body, sig, ts: (body, "v1=not-base-64-!!", ts), id="signature is not base64"
        ),
        pytest.param(
            lambda body, sig, ts: (body, sig, "not-a-number"), id="timestamp is not an int"
        ),
        pytest.param(lambda body, sig, ts: (body, sig, ""), id="timestamp is empty"),
    ],
)
def test_rejections(mutate) -> None:
    # Assert the exception type only, never the message: a doubly-invalid
    # request may report either failure depending on check order.
    body, signature, timestamp = mutate(*_fresh_signature())

    with pytest.raises(AdsefidWebhookVerificationError):
        verify_and_parse_webhook(
            raw_body=body,
            signature_header=signature,
            timestamp_header=timestamp,
            secret=VECTOR["secret"],
        )


def test_a_wrong_secret_is_rejected() -> None:
    body, signature, timestamp = _fresh_signature()
    other_secret = base64.b64encode(b"a-completely-different-32-byte!!!").decode("ascii")

    with pytest.raises(AdsefidWebhookVerificationError):
        verify_and_parse_webhook(
            raw_body=body,
            signature_header=signature,
            timestamp_header=timestamp,
            secret=other_secret,
        )


def test_a_secret_that_is_not_base64_is_rejected() -> None:
    body, signature, timestamp = _fresh_signature()

    with pytest.raises(AdsefidWebhookVerificationError, match="Base64"):
        verify_and_parse_webhook(
            raw_body=body,
            signature_header=signature,
            timestamp_header=timestamp,
            secret="not base64 !!",
        )


@pytest.mark.parametrize("offset", [-301, 301], ids=["stale", "in the future"])
def test_timestamps_outside_the_window_are_rejected(offset: int) -> None:
    body = golden_body()
    timestamp = now_timestamp(offset)

    with pytest.raises(AdsefidWebhookVerificationError, match="stale"):
        verify_and_parse_webhook(
            raw_body=body,
            signature_header=sign(VECTOR["secret"], timestamp, body),
            timestamp_header=timestamp,
            secret=VECTOR["secret"],
        )


def test_max_age_seconds_widens_the_window() -> None:
    body = golden_body()
    timestamp = now_timestamp(-600)
    signature = sign(VECTOR["secret"], timestamp, body)

    with pytest.raises(AdsefidWebhookVerificationError):
        verify_and_parse_webhook(
            raw_body=body,
            signature_header=signature,
            timestamp_header=timestamp,
            secret=VECTOR["secret"],
        )

    event = verify_and_parse_webhook(
        raw_body=body,
        signature_header=signature,
        timestamp_header=timestamp,
        secret=VECTOR["secret"],
        max_age_seconds=900,
    )
    assert isinstance(event, ReceiveWebhookEvent)


def test_the_signature_is_checked_before_freshness() -> None:
    """All five SDKs report the signature first for a doubly-invalid request."""
    timestamp = now_timestamp(-600)

    with pytest.raises(AdsefidWebhookVerificationError, match="signature"):
        verify_and_parse_webhook(
            raw_body=golden_body(),
            signature_header=VECTOR["tampered_signature"],
            timestamp_header=timestamp,
            secret=VECTOR["secret"],
        )


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(fixture_bytes("webhooks/unknown_type.body.json"), id="unknown event type"),
        pytest.param(b"<html>nope</html>", id="not json"),
        pytest.param(b"[1,2,3]", id="json but not an object"),
        pytest.param(b'{"type":"receive"}', id="missing required fields"),
    ],
)
def test_unparseable_payloads_are_rejected(body: bytes) -> None:
    timestamp = now_timestamp()

    with pytest.raises(AdsefidWebhookVerificationError):
        verify_and_parse_webhook(
            raw_body=body,
            signature_header=sign(VECTOR["secret"], timestamp, body),
            timestamp_header=timestamp,
            secret=VECTOR["secret"],
        )


def test_header_constants_are_the_wire_protocol() -> None:
    # These are the literal names the service sends; renaming any of them
    # breaks every deployed receiver.
    assert WebhookHeaders.ID == "X-Atlas-Webhook-Id"
    assert WebhookHeaders.SIGNATURE == "X-Atlas-Webhook-Signature"
    assert WebhookHeaders.TIMESTAMP == "X-Atlas-Webhook-Timestamp"
    assert WebhookHeaders.EVENT == "X-Atlas-Webhook-Event"
    assert WebhookHeaders.ATTEMPT == "X-Atlas-Webhook-Attempt"


def test_event_type_values() -> None:
    assert WebhookEventType.RECEIVE == "receive"
    assert WebhookEventType.STATUS == "status"
    assert WebhookEventType.MESSENGER_STATUS == "messenger.status"
