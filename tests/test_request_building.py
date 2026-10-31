"""Query-string building, URL length, and base URL handling."""

from __future__ import annotations

import pytest

from adsefid import AdsefidValidationError
from adsefid._base import encode_query
from tests.conftest import unwrap


class TestEncodeQuery:
    def test_a_list_is_deduplicated_and_joined_with_literal_commas(self) -> None:
        assert encode_query({"local_ids": ["a", "b", "a"]}) == "local_ids=a,b"

    def test_values_are_escaped_but_the_separator_is_not(self) -> None:
        assert encode_query({"local_ids": ["a b", "c&d"]}) == "local_ids=a%20b,c%26d"

    def test_empty_and_missing_values_are_omitted(self) -> None:
        assert encode_query({"message_ids": [], "local_ids": None, "count": 3}) == "count=3"
        assert encode_query(None) == ""


def _ids(count: int) -> list[str]:
    return [f"0195ff8c-55aa-7e74-a337-{i:012d}" for i in range(count)]


@pytest.mark.parametrize("area", ["sms", "messenger"])
@pytest.mark.parametrize("count", [0, 2000, 2001])
async def test_status_uses_a_query_body_with_the_combined_distinct_limit(
    make_client, area, count
) -> None:
    client, recorder = make_client(content=b'{"status":"success","data":{"receptors":[]}}')
    message_ids = _ids(count // 2)
    local_ids = _ids(count - count // 2)
    resource = getattr(client, area)

    def call():
        return resource.get_status(
            message_ids=tuple(message_ids + message_ids), local_ids=local_ids
        )

    if count == 0 or count > 2000:
        with pytest.raises(AdsefidValidationError):
            await unwrap(call())
        assert not recorder.requests
    else:
        assert (await unwrap(call())).receptors == []
        assert recorder.only.method == "QUERY"
        assert not recorder.only.params
        assert recorder.only.json == {"message_ids": message_ids, "local_ids": local_ids}
        assert recorder.only.headers["content-type"] == "application/json"
