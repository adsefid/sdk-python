"""SMS endpoints, run against both the sync and async clients."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from adsefid import AdsefidValidationError, WebServiceMessageStatus, WebServiceResponseCode
from adsefid.models.sms import (
    BulkReceptor,
    CancelSmsRequest,
    P2pMessage,
    SendBulkSmsRequest,
    SendP2pSmsRequest,
    SendSingleSmsRequest,
    SendTemplateSmsRequest,
)
from tests.conftest import unwrap
from tests.helpers.fixtures import fixture_bytes
from tests.helpers.transport import API_KEY


async def test_send_single_builds_the_request(make_client) -> None:
    client, recorder = make_client(content=fixture_bytes("envelopes/sms.send_single.success.json"))

    await unwrap(
        client.sms.send_single(
            SendSingleSmsRequest(receptor="98912xxxxxxx", line_number="3000xxxx", message="hello")
        )
    )

    request = recorder.only
    assert request.method == "POST"
    assert request.path == "/v1/sms/single"
    assert request.headers["X-API-KEY"] == API_KEY
    assert request.headers["User-Agent"].startswith("adsefid-python/")
    assert request.json == {
        "receptor": "98912xxxxxxx",
        "line_number": "3000xxxx",
        "message": "hello",
    }
    # Omitted optionals must be absent, not null.
    for absent in ("send_time", "local_id", "hide", "line_selector"):
        assert absent not in request.json


async def test_send_single_includes_supplied_optionals(make_client) -> None:
    client, recorder = make_client(content=fixture_bytes("envelopes/sms.send_single.success.json"))
    send_at = datetime(2026, 4, 4, 11, 0, tzinfo=timezone.utc)

    await unwrap(
        client.sms.send_single(
            SendSingleSmsRequest(
                receptor="98912xxxxxxx",
                line_number="3000xxxx",
                message="hello",
                send_time=send_at,
                local_id="order-1",
                hide=True,
                line_selector=2,
            )
        )
    )

    body = recorder.only.json
    assert body["local_id"] == "order-1"
    assert body["hide"] is True
    assert body["line_selector"] == 2
    assert body["send_time"].startswith("2026-04-04T11:00:00")


async def test_send_single_parses_the_response(make_client) -> None:
    client, _ = make_client(content=fixture_bytes("envelopes/sms.send_single.success.json"))

    result = await unwrap(
        client.sms.send_single(
            SendSingleSmsRequest(receptor="98912xxxxxxx", line_number="3000xxxx", message="hi")
        )
    )

    assert result.status is WebServiceMessageStatus.SCHEDULED
    assert result.raw_status == 1000
    assert result.segment_count == 1
    assert result.cost == 120
    assert result.send_time is not None


async def test_send_bulk_partial_success_is_not_an_error(make_client) -> None:
    """HTTP 200 with per-receptor failures is a normal typed response."""
    client, _ = make_client(content=fixture_bytes("envelopes/sms.send_bulk.partial_success.json"))

    result = await unwrap(
        client.sms.send_bulk(
            SendBulkSmsRequest(
                receptors=[BulkReceptor(receptor="a"), BulkReceptor(receptor="b")],
                message="m",
                line_number="3000xxxx",
            )
        )
    )

    assert len(result.receptors) == 2
    assert result.receptors[0].raw_status == 1000
    # 2025 RECEPTOR_BLACKLISTED is a response code, not a message status, which
    # is why the raw int is kept alongside the optional enum.
    assert result.receptors[1].raw_status == 2025
    assert result.receptors[1].message_id is None
    assert result.total_count == 2
    assert result.counts["2025"] == 1
    # The typed views split the WebServiceCode by range, so a caller never compares raw ints.
    assert result.receptors[0].status is WebServiceMessageStatus.SCHEDULED
    assert result.receptors[0].error_code is None
    assert result.receptors[1].status is None
    assert result.receptors[1].error_code is WebServiceResponseCode.RECEPTOR_BLACKLISTED


async def test_send_p2p_partial_success_is_not_an_error(make_client) -> None:
    client, _ = make_client(content=fixture_bytes("envelopes/sms.send_p2p.partial_success.json"))

    result = await unwrap(
        client.sms.send_p2p(
            SendP2pSmsRequest(
                messages=[P2pMessage(receptor="a", message="x")], line_number="3000xxxx"
            )
        )
    )

    assert [item.raw_status for item in result.messages] == [1000, 2014]
    assert [item.error_code for item in result.messages] == [
        None,
        WebServiceResponseCode.INVALID_RECEPTOR,
    ]


async def test_send_template_keeps_exact_numeric_values(make_client) -> None:
    """A number-typed parameter sent as a string keeps its exact digits.

    The service substitutes a numeric string verbatim, so "001234" renders with
    its leading zeros and "1.50" with its trailing zero.
    """
    client, recorder = make_client(
        content=fixture_bytes("envelopes/sms.send_template.success.json")
    )

    await unwrap(
        client.sms.send_template(
            SendTemplateSmsRequest(
                template_id="otp_login",
                parameters={
                    "code": "459122",
                    "invoice": "001234",
                    "exact_amount": Decimal("1.50"),
                    "quantity": 2,
                    "rate": 19.99,
                },
                receptor="98912xxxxxxx",
                line_number="3000xxxx",
            )
        )
    )

    parameters = recorder.only.json["parameters"]
    assert parameters["invoice"] == "001234"
    assert parameters["exact_amount"] == "1.50"
    assert parameters["quantity"] == 2
    assert parameters["rate"] == 19.99


async def test_send_template_echoes_parameters_back(make_client) -> None:
    client, _ = make_client(content=fixture_bytes("envelopes/sms.send_template.success.json"))

    result = await unwrap(
        client.sms.send_template(
            SendTemplateSmsRequest(
                template_id="otp_login",
                parameters={"code": "459122"},
                receptor="98912xxxxxxx",
                line_number="3000xxxx",
            )
        )
    )

    assert result.parameters["code"] == "459122"
    assert result.parameters["minutes"] == 2
    assert result.expiry_date is not None


async def test_get_status_joins_ids_into_csv_query_params(make_client) -> None:
    client, recorder = make_client(content=fixture_bytes("envelopes/sms.get_status.success.json"))

    await unwrap(client.sms.get_status(message_ids=["m1", "m2"], local_ids=["l1"]))

    request = recorder.only
    assert request.method == "GET"
    assert request.path == "/v1/sms/status"
    assert request.params["message_ids"] == "m1,m2"
    assert request.params["local_ids"] == "l1"


async def test_cancel(make_client) -> None:
    client, recorder = make_client(content=fixture_bytes("envelopes/sms.cancel.success.json"))

    result = await unwrap(client.sms.cancel(CancelSmsRequest(message_ids=["m1"])))

    assert recorder.only.path == "/v1/sms/cancel"
    assert "local_ids" not in recorder.only.json
    assert result.cancelled_messages or result.failed_to_cancel


async def test_get_received(make_client) -> None:
    client, recorder = make_client(content=fixture_bytes("envelopes/sms.get_received.success.json"))

    result = await unwrap(client.sms.get_received(line_number="3000xxxx", count=10))

    request = recorder.only
    assert request.path == "/v1/sms/receive"
    assert request.params["line_number"] == "3000xxxx"
    assert request.params["count"] == "10"
    assert result.messages
    assert result.messages[0].receive_date is not None


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(
            lambda c: c.sms.send_single(
                SendSingleSmsRequest(receptor="", line_number="3000", message="m")
            ),
            id="empty receptor",
        ),
        pytest.param(
            lambda c: c.sms.send_single(
                SendSingleSmsRequest(receptor="a", line_number="", message="m")
            ),
            id="empty line number",
        ),
        pytest.param(
            lambda c: c.sms.send_single(
                SendSingleSmsRequest(receptor="a", line_number="3000", message="")
            ),
            id="empty message",
        ),
        pytest.param(
            lambda c: c.sms.send_single(
                SendSingleSmsRequest(receptor="a", line_number="3000", message="x" * 901)
            ),
            id="message over the limit",
        ),
        pytest.param(
            lambda c: c.sms.send_single(
                SendSingleSmsRequest(receptor="a", line_number="3000", message="m", local_id="-bad")
            ),
            id="invalid local id",
        ),
        pytest.param(
            lambda c: c.sms.send_bulk(
                SendBulkSmsRequest(receptors=[], message="m", line_number="3000")
            ),
            id="no receptors",
        ),
        pytest.param(
            lambda c: c.sms.send_p2p(SendP2pSmsRequest(messages=[], line_number="3000")),
            id="no messages",
        ),
        pytest.param(lambda c: c.sms.get_status(), id="status with neither id list"),
        pytest.param(lambda c: c.sms.cancel(CancelSmsRequest()), id="cancel with neither id list"),
        pytest.param(
            lambda c: c.sms.get_received(line_number="3000", count=500),
            id="received count over the limit",
        ),
        pytest.param(
            lambda c: c.sms.get_received(line_number=""), id="received with empty line number"
        ),
    ],
)
async def test_validation_rejects_before_any_request_is_sent(make_client, build) -> None:
    client, recorder = make_client(content=fixture_bytes("envelopes/sms.send_single.success.json"))

    with pytest.raises(AdsefidValidationError):
        await unwrap(build(client))

    assert recorder.requests == [], "validation must reject before reaching the network"
