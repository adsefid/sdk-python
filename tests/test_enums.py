"""Enum wire values and the permissive parsing the service's growth requires."""

from __future__ import annotations

from decimal import Decimal

import pytest

from adsefid import (
    LineSelector,
    TemplateParameterType,
    TemplateState,
    WebServiceMessageStatus,
    WebServiceResponseCode,
)
from adsefid.enums import parse_message_status, parse_response_code
from adsefid.models.common import serialize_template_parameters
from tests.helpers.fixtures import fixture_json


class TestDocumentedWireValues:
    def test_template_states_are_lowercase(self) -> None:
        assert TemplateState.PENDING_APPROVAL.value == "pendingapproval"
        assert TemplateState.APPROVED.value == "approved"
        assert TemplateState.REJECTED.value == "rejected"

    def test_template_parameter_types_are_lowercase(self) -> None:
        assert TemplateParameterType.STRING.value == "string"
        assert TemplateParameterType.NUMBER.value == "number"

    def test_line_selector_values(self) -> None:
        assert LineSelector(2) is LineSelector.BULK_SERVICE_SEND_BASED

    def test_message_status_values(self) -> None:
        assert WebServiceMessageStatus(1000) is WebServiceMessageStatus.SCHEDULED
        assert WebServiceMessageStatus(1002) is WebServiceMessageStatus.DELIVERED

    def test_response_code_values(self) -> None:
        assert WebServiceResponseCode(2024) is WebServiceResponseCode.INVALID_PARAMETER
        assert WebServiceResponseCode(2035) is WebServiceResponseCode.MESSAGE_LIMIT_REACHED


class TestPermissiveParsing:
    """The service adds codes over time.

    Parsing must degrade to the raw int rather than raising, so an older SDK
    keeps working against a newer service.
    """

    def test_a_known_message_status_yields_the_member(self) -> None:
        assert parse_message_status(1002) == (WebServiceMessageStatus.DELIVERED, 1002)

    def test_an_unknown_message_status_yields_the_raw_int(self) -> None:
        assert parse_message_status(1998) == (None, 1998)

    def test_a_known_response_code_yields_the_member(self) -> None:
        assert parse_response_code(2024) == (WebServiceResponseCode.INVALID_PARAMETER, 2024)

    def test_an_unknown_response_code_yields_the_raw_int(self) -> None:
        assert parse_response_code(2999) == (None, 2999)


class TestUndocumentedParameterType:
    """The live service emits a third parameter type this SDK does not model."""

    def test_it_is_absent_from_the_enum(self) -> None:
        with pytest.raises(ValueError):
            TemplateParameterType("url")

    def test_the_fixture_still_carries_it(self) -> None:
        # If the service ever stops sending it, this fixture should be revisited
        # in all five SDKs at once.
        parameters = fixture_json("envelopes/user.get_templates.unknown_type.json")["data"][
            "items"
        ][0]["parameters"]
        assert parameters["link"] == "url"


class TestSerializeTemplateParameters:
    """A `number` parameter may travel as a JSON string, which is how exact
    digits survive: the service substitutes such a value verbatim."""

    def test_strings_pass_through_unchanged(self) -> None:
        assert serialize_template_parameters({"invoice": "001234"}) == {"invoice": "001234"}

    def test_ints_and_floats_stay_json_numbers(self) -> None:
        assert serialize_template_parameters({"n": 2, "f": 19.99}) == {"n": 2, "f": 19.99}

    def test_a_decimal_becomes_its_exact_decimal_string(self) -> None:
        assert serialize_template_parameters({"amount": Decimal("1.50")}) == {"amount": "1.50"}

    def test_a_decimal_with_many_places_is_not_rounded(self) -> None:
        assert serialize_template_parameters(
            {"rate": Decimal("0.123456789012345678901234567890")}
        ) == {"rate": "0.123456789012345678901234567890"}

    def test_an_empty_map_stays_empty(self) -> None:
        assert serialize_template_parameters({}) == {}

    def test_the_shared_example_serializes_as_the_other_sdks_do(self) -> None:
        import json

        example = fixture_json("validation/template_parameters.json")
        serialized = serialize_template_parameters(example["parameters"])
        assert (
            json.dumps(serialized, sort_keys=True, separators=(",", ":"))
            == (example["expected_json"])
        )
