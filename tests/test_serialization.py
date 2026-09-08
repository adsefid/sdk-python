"""Pre-flight validation and the small serialization helpers."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from adsefid import AdsefidValidationError
from adsefid._serialization import (
    MAX_RECEIVE_COUNT,
    MAX_STATUS_IDS,
    MAX_TEMPLATE_TAKE,
    MESSENGER_MESSAGE_MAX_LENGTH,
    MIN_RECEIVE_COUNT,
    MIN_TEMPLATE_TAKE,
    SMS_MESSAGE_MAX_LENGTH,
    format_datetime,
    join_csv,
    parse_datetime,
    utf16_length,
    validate_ids_count,
    validate_local_id,
    validate_max_length,
    validate_non_empty,
    validate_receive_count,
    validate_skip,
    validate_take,
)
from tests.helpers.fixtures import fixture_json


class TestLocalId:
    """The golden table is shared byte-for-byte with the sibling SDKs."""

    @pytest.mark.parametrize("case", fixture_json("validation/local_ids.json"))
    def test_golden_table(self, case: dict) -> None:
        if case["valid"]:
            validate_local_id(case["value"])
        else:
            with pytest.raises(AdsefidValidationError):
                validate_local_id(case["value"])

    def test_none_is_not_supplied(self) -> None:
        validate_local_id(None)

    def test_the_field_name_reaches_the_message(self) -> None:
        with pytest.raises(AdsefidValidationError, match="receptors\\[\\].local_id"):
            validate_local_id("-bad", field_name="receptors[].local_id")


class TestMaxLengthCountsUtf16CodeUnits:
    """The service counts its limits in UTF-16 code units.

    A character outside the Basic Multilingual Plane costs two, so counting
    Python code points would accept a message the service rejects.
    """

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("", 0),
            ("abc", 3),
            ("سلام", 4),
            ("😀", 2),
            ("a😀b", 4),
            ("é", 1),
        ],
    )
    def test_utf16_length(self, value: str, expected: int) -> None:
        assert utf16_length(value) == expected

    @pytest.mark.parametrize(
        ("value", "rejected"),
        [
            pytest.param("a" * 900, False, id="ascii at the limit"),
            pytest.param("a" * 901, True, id="ascii one over"),
            pytest.param("س" * 900, False, id="persian at the limit"),
            pytest.param("س" * 901, True, id="persian one over"),
            pytest.param("😀" * 450, False, id="450 emoji is exactly 900 units"),
            pytest.param("😀" * 451, True, id="451 emoji is 902 units"),
            pytest.param("😀" * 900, True, id="900 emoji is 1800 units"),
        ],
    )
    def test_sms_limit(self, value: str, rejected: bool) -> None:
        if rejected:
            with pytest.raises(AdsefidValidationError):
                validate_max_length(value, field_name="message", max_length=SMS_MESSAGE_MAX_LENGTH)
        else:
            validate_max_length(value, field_name="message", max_length=SMS_MESSAGE_MAX_LENGTH)


class TestLimitsMatchTheService:
    """The bounds are shared with the sibling SDKs via a golden fixture."""

    def test_the_constants_match_the_shared_table(self) -> None:
        limits = fixture_json("validation/limits.json")
        assert SMS_MESSAGE_MAX_LENGTH == limits["sms_message_max_length"]
        assert MESSENGER_MESSAGE_MAX_LENGTH == limits["messenger_message_max_length"]
        assert MAX_STATUS_IDS == limits["combined_status_ids_max"]
        assert MIN_RECEIVE_COUNT == limits["receive_count_min"]
        assert MAX_RECEIVE_COUNT == limits["receive_count_max"]
        assert MIN_TEMPLATE_TAKE == limits["templates_take_min"]
        assert MAX_TEMPLATE_TAKE == limits["templates_take_max"]


class TestValidateIdsCount:
    def test_requires_at_least_one_list(self) -> None:
        with pytest.raises(AdsefidValidationError):
            validate_ids_count(None, None)

    @pytest.mark.parametrize(
        ("message_ids", "local_ids"),
        [(["a"], None), (None, ["b"]), (["a"], ["b"])],
    )
    def test_accepts_either_or_both(self, message_ids, local_ids) -> None:
        validate_ids_count(message_ids, local_ids)

    def test_the_combined_ceiling_is_inclusive(self) -> None:
        validate_ids_count([f"m{i}" for i in range(MAX_STATUS_IDS)], None)

        with pytest.raises(AdsefidValidationError):
            validate_ids_count([f"m{i}" for i in range(MAX_STATUS_IDS + 1)], None)

    def test_duplicates_collapse_before_the_ceiling_is_applied(self) -> None:
        validate_ids_count(["same"] * (MAX_STATUS_IDS + 50), None)


class TestNumericBounds:
    @pytest.mark.parametrize("count", [MIN_RECEIVE_COUNT, 250, MAX_RECEIVE_COUNT])
    def test_receive_count_accepts_the_valid_range(self, count: int) -> None:
        validate_receive_count(count)

    @pytest.mark.parametrize("count", [0, -1, MAX_RECEIVE_COUNT + 1])
    def test_receive_count_rejects_out_of_range(self, count: int) -> None:
        with pytest.raises(AdsefidValidationError):
            validate_receive_count(count)

    def test_receive_count_is_optional(self) -> None:
        validate_receive_count(None)

    @pytest.mark.parametrize("take", [MIN_TEMPLATE_TAKE, MAX_TEMPLATE_TAKE])
    def test_take_accepts_the_boundaries(self, take: int) -> None:
        validate_take(take)

    @pytest.mark.parametrize("take", [0, MAX_TEMPLATE_TAKE + 1, -1])
    def test_take_rejects_out_of_range(self, take: int) -> None:
        with pytest.raises(AdsefidValidationError):
            validate_take(take)

    def test_skip_must_be_non_negative(self) -> None:
        validate_skip(0)
        validate_skip(10)
        with pytest.raises(AdsefidValidationError):
            validate_skip(-1)


class TestNonEmpty:
    @pytest.mark.parametrize("value", [None, ""])
    def test_rejects_blank(self, value) -> None:
        with pytest.raises(AdsefidValidationError):
            validate_non_empty(value, field_name="receptor")

    def test_accepts_a_value(self) -> None:
        validate_non_empty("x", field_name="receptor")


class TestJoinCsv:
    @pytest.mark.parametrize(
        ("values", "expected"),
        [
            (None, None),
            ([], None),
            (["a"], "a"),
            (["a", "b", "c"], "a,b,c"),
        ],
    )
    def test_join(self, values, expected) -> None:
        assert join_csv(values) == expected


class TestDatetimes:
    def test_round_trip(self) -> None:
        value = datetime(2026, 4, 4, 11, 0, tzinfo=timezone.utc)
        assert parse_datetime(format_datetime(value)) == value

    def test_none_passes_through(self) -> None:
        assert parse_datetime(None) is None
        assert format_datetime(None) is None

    def test_a_trailing_z_is_accepted(self) -> None:
        """`datetime.fromisoformat` on the 3.10 floor rejects 'Z' on its own."""
        parsed = parse_datetime("2026-04-04T11:00:00Z")
        assert parsed == datetime(2026, 4, 4, 11, 0, tzinfo=timezone.utc)

    def test_an_offset_is_preserved(self) -> None:
        parsed = parse_datetime("2026-04-04T11:40:00+03:30")
        assert parsed is not None
        assert parsed.utcoffset() is not None
