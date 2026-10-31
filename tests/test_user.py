"""Account endpoints, run against both the sync and async clients."""

from __future__ import annotations

from decimal import Decimal

import pytest

from adsefid import AdsefidValidationError, TemplateParameterType, TemplateState
from tests.conftest import unwrap
from tests.helpers.fixtures import fixture_bytes


async def test_get_info(make_client) -> None:
    client, recorder = make_client(content=fixture_bytes("envelopes/user.get_info.success.json"))

    result = await unwrap(client.user.get_info())

    assert recorder.only.method == "GET"
    assert recorder.only.path == "/v1/user/info"
    assert result.name


async def test_get_lines(make_client) -> None:
    client, recorder = make_client(content=fixture_bytes("envelopes/user.get_lines.success.json"))

    result = await unwrap(client.user.get_lines())

    assert recorder.only.path == "/v1/user/lines"
    assert result
    assert result[0].line_number


async def test_get_profiles(make_client) -> None:
    client, recorder = make_client(
        content=fixture_bytes("envelopes/user.get_profiles.success.json")
    )

    result = await unwrap(client.user.get_profiles())

    assert recorder.only.path == "/v1/user/profiles"
    assert result


async def test_get_templates_parses_the_documented_shape(make_client) -> None:
    client, recorder = make_client(
        content=fixture_bytes("envelopes/user.get_templates.success.json")
    )

    result = await unwrap(client.user.get_templates(state=TemplateState.APPROVED, skip=0, take=50))

    request = recorder.only
    assert request.path == "/v1/user/templates"
    assert request.params["state"] == "approved"
    assert request.params["skip"] == "0"
    assert request.params["take"] == "50"

    assert result.total == 1
    item = result.items[0]
    assert item.state is TemplateState.APPROVED
    assert item.parameters["OTPCode"] is TemplateParameterType.STRING
    assert item.parameters["amount"] is TemplateParameterType.NUMBER
    assert item.description == ""


async def test_get_templates_preserves_unknown_parameter_types(make_client) -> None:
    """A parameter type this SDK has no member for.

    It stays a plain string so callers can see which parameters a template needs.
    """
    client, _ = make_client(content=fixture_bytes("envelopes/user.get_templates.unknown_type.json"))

    result = await unwrap(client.user.get_templates())

    assert result.items[0].parameters == {
        "OTPCode": "string",
        "link": "future_type",
        "amount": "number",
    }
    assert result.items[0].parameters["link"] == "future_type"
    assert result.items[0].description is None


async def test_get_templates_omits_absent_query_params(make_client) -> None:
    client, recorder = make_client(
        content=fixture_bytes("envelopes/user.get_templates.success.json")
    )

    await unwrap(client.user.get_templates())

    assert str(recorder.only.url.query, "ascii") == ""


@pytest.mark.parametrize("take", [1, 100])
async def test_get_templates_accepts_the_take_boundaries(make_client, take: int) -> None:
    client, _ = make_client(content=fixture_bytes("envelopes/user.get_templates.success.json"))

    await unwrap(client.user.get_templates(take=take))


@pytest.mark.parametrize(
    ("skip", "take"),
    [
        pytest.param(None, 0, id="take below the minimum"),
        pytest.param(None, 101, id="take above the maximum"),
        pytest.param(-1, None, id="negative skip"),
    ],
)
async def test_get_templates_rejects_out_of_range_paging(make_client, skip, take) -> None:
    client, recorder = make_client(
        content=fixture_bytes("envelopes/user.get_templates.success.json")
    )

    with pytest.raises(AdsefidValidationError):
        await unwrap(client.user.get_templates(skip=skip, take=take))

    assert recorder.requests == []


async def test_an_unknown_line_selector_and_template_state_are_preserved(make_client) -> None:
    lines = (
        b'{"status":"success","data":[{"line_number":"1","line_selector":9,'
        b'"line_name":"x","enabled":true}]}'
    )
    client, _ = make_client(content=lines)
    assert (await unwrap(client.user.get_lines()))[0].line_selector == 9

    body = (
        b'{"status":"success","data":{"items":[{"template_id":"t","content":"c","parameters":{},'
        b'"state":"archived","description":null,"created_at":"2026-09-02T10:30:00+03:30",'
        b'"updated_at":"2026-09-02T11:00:00+03:30"}],"total":1}}'
    )
    client, _ = make_client(content=body)
    assert (await unwrap(client.user.get_templates())).items[0].state == "archived"


async def test_money_is_an_exact_decimal(make_client) -> None:
    body = (
        b'{"status":"success","data":{"name":"n","company_name":null,"credit_left":1250000.10,'
        b'"email":null,"phone":null,"account_status":"active"}}'
    )
    client, _ = make_client(content=body)

    info = await unwrap(client.user.get_info())

    assert info.credit_left == Decimal("1250000.10")
    assert str(info.credit_left) == "1250000.10"
    assert info.company_name is None
