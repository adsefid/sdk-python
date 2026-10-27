"""Fixtures shaped like real gateway responses.

They carry 7-digit fractional seconds (which `datetime.fromisoformat` rejects on 3.10 as
is), an empty-string description, null account fields, long decimal money and "+98" receptors.
"""

from __future__ import annotations

from decimal import Decimal

from adsefid import SendTemplateSmsRequest, WebServiceMessageStatus
from tests.conftest import unwrap
from tests.helpers.fixtures import fixture_bytes


async def test_account_info_keeps_null_fields_and_the_exact_credit(make_client) -> None:
    client, _ = make_client(content=fixture_bytes("envelopes/user.get_info.live.json"))

    info = await unwrap(client.user.get_info())

    assert info.company_name is None
    assert info.email is None
    assert info.credit_left == Decimal("5877471300.00000")
    assert str(info.credit_left) == "5877471300.00000"


async def test_templates_parse_seven_digit_timestamps_and_an_empty_description(make_client) -> None:
    client, _ = make_client(content=fixture_bytes("envelopes/user.get_templates.live.json"))

    item = (await unwrap(client.user.get_templates())).items[0]

    assert item.description == ""
    assert item.created_at is not None
    assert item.created_at.microsecond == 403029


async def test_template_send_keeps_long_decimal_cost_and_normalized_receptor(make_client) -> None:
    client, _ = make_client(content=fixture_bytes("envelopes/sms.send_template.live.json"))

    response = await unwrap(
        client.sms.send_template(
            SendTemplateSmsRequest(
                template_id="otp",
                parameters={"otp_code": "001234"},
                receptor="989120000000",
                line_number="983000",
            )
        )
    )

    assert str(response.cost) == "1129.0000000000000000"
    assert response.receptor == "+989120000000"
    assert response.expiry_date is None
    assert response.send_time is not None


async def test_status_parses_a_seven_digit_delivery_time(make_client) -> None:
    client, _ = make_client(content=fixture_bytes("envelopes/sms.get_status.live.json"))

    item = (await unwrap(client.sms.get_status(local_ids=["order-10001"]))).receptors[0]

    assert item.status == WebServiceMessageStatus.UNDELIVERED
    assert item.delivery_time is not None
    assert item.delivery_time.microsecond == 953820
