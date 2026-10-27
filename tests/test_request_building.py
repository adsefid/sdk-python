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


@pytest.mark.parametrize(("count", "accepted"), [(210, True), (230, False), (2000, False)])
async def test_a_status_lookup_that_cannot_fit_in_a_url_is_refused_locally(
    make_client, count: int, accepted: bool
) -> None:
    client, recorder = make_client(content=b'{"status":"success","data":{"receptors":[]}}')

    if accepted:
        await unwrap(client.sms.get_status(message_ids=_ids(count)))
        assert "%2C" not in str(recorder.only.url)
        return
    with pytest.raises(AdsefidValidationError, match="characters long"):
        await unwrap(client.sms.get_status(message_ids=_ids(count)))
    assert not recorder.requests
