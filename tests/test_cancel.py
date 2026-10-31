"""Cancellation bounds and request preservation for both resources and clients."""

from __future__ import annotations

import pytest

from adsefid import (
    AdsefidValidationError,
    CancelMessengerRequest,
    CancelSmsRequest,
    WebServiceMessageStatus,
    WebServiceResponseCode,
)
from tests.conftest import unwrap
from tests.helpers.fixtures import fixture_bytes


@pytest.mark.parametrize("area", ["sms", "messenger"])
@pytest.mark.parametrize(
    ("message_count", "local_count", "repetitions", "rejected"),
    [
        (0, 0, 1, True),
        (2000, 0, 1, False),
        (2001, 0, 1, True),
        (0, 2000, 1, False),
        (0, 2001, 1, True),
        (1000, 1000, 1, False),
        (1000, 1001, 1, True),
        (1000, 1000, 3, False),
    ],
)
async def test_cancel_counts_distinct_ids_and_preserves_body(
    make_client, area: str, message_count: int, local_count: int, repetitions: int, rejected: bool
) -> None:
    message_ids = [f"00000000-0000-0000-0000-{i:012}" for i in range(message_count)] * repetitions
    local_ids = [f"00000000-0000-0000-0000-{i:012}" for i in range(local_count)] * repetitions
    client, recorder = make_client(content=fixture_bytes(f"envelopes/{area}.cancel.success.json"))
    request = (
        CancelSmsRequest(message_ids, local_ids)
        if area == "sms"
        else CancelMessengerRequest(message_ids, local_ids)
    )
    resource = client.sms if area == "sms" else client.messenger

    if rejected:
        with pytest.raises(AdsefidValidationError):
            await unwrap(resource.cancel(request))
        assert recorder.requests == []
    else:
        await unwrap(resource.cancel(request))
        assert recorder.only.method == "POST"
        assert recorder.only.path == f"/v1/{area}/cancel"
        assert recorder.only.json == {
            key: value
            for key, value in (("message_ids", message_ids), ("local_ids", local_ids))
            if value
        }


@pytest.mark.parametrize("area", ["sms", "messenger"])
async def test_cancel_preserves_nullable_ids_and_item_errors(make_client, area: str) -> None:
    client, recorder = make_client(content=fixture_bytes("envelopes/cancel.partial_success.json"))
    request = (
        CancelSmsRequest(local_ids=["missing-local"])
        if area == "sms"
        else CancelMessengerRequest(local_ids=["missing-local"])
    )
    result = await unwrap(getattr(client, area).cancel(request))
    assert result.cancelled_messages[0].status is WebServiceMessageStatus.CANCELED
    assert [item.raw_status for item in result.failed_to_cancel] == [1001, 2046, 2029, 2999]
    assert result.failed_to_cancel[1].local_id is None
    assert result.failed_to_cancel[2].message_id is None
    assert result.failed_to_cancel[1].error_code is WebServiceResponseCode.INVALID_MESSAGE_IDS
    assert result.failed_to_cancel[2].error_code is WebServiceResponseCode.INVALID_LOCAL_IDS
    assert result.failed_to_cancel[3].error_code is None
    assert result.failed_to_cancel[2].to_dict()["message_id"] is None
    assert len(recorder.requests) == 1
