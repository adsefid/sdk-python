"""Account endpoints, run against both the sync and async clients."""

from __future__ import annotations

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
    assert item.description is None


async def test_get_templates_drops_undocumented_parameter_types(make_client) -> None:
    """The live service emits a parameter type this SDK does not model.

    Dropping the entry keeps the typed map honest rather than surfacing a value
    callers cannot match on.
    """
    client, _ = make_client(content=fixture_bytes("envelopes/user.get_templates.unknown_type.json"))

    result = await unwrap(client.user.get_templates())

    parameters = result.items[0].parameters
    assert "link" not in parameters
    assert set(parameters) == {"OTPCode", "amount"}


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
