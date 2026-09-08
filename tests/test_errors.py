"""HTTP status × error envelope mapping, and the transport/success edges."""

from __future__ import annotations

import httpx
import pytest

from adsefid import (
    AdsefidApiError,
    AdsefidError,
    AdsefidRateLimitError,
    AdsefidTransportError,
    WebServiceResponseCode,
)
from tests.conftest import unwrap
from tests.helpers.fixtures import fixture_bytes


@pytest.mark.parametrize(
    ("fixture", "http_status", "rate_limited", "code", "name"),
    [
        pytest.param(
            "errors/error.invalid_api_key.json",
            401,
            False,
            WebServiceResponseCode.UNAUTHORIZED,
            "UNAUTHORIZED",
            id="unauthorized",
        ),
        pytest.param(
            "errors/error.rate_limit_message.json",
            429,
            True,
            WebServiceResponseCode.MESSAGE_LIMIT_REACHED,
            "MESSAGE_LIMIT_REACHED",
            id="message rate limit",
        ),
        pytest.param(
            # The envelope wins over the HTTP status: a 200 carrying an error
            # envelope is still an error.
            "errors/error.rate_limit_request.json",
            200,
            True,
            WebServiceResponseCode.REQUEST_LIMIT_REACHED,
            "REQUEST_LIMIT_REACHED",
            id="request rate limit inside a 200",
        ),
        pytest.param(
            "errors/error.invalid_parameter.json",
            400,
            False,
            WebServiceResponseCode.INVALID_PARAMETER,
            "INVALID_PARAMETER",
            id="invalid parameter",
        ),
    ],
)
async def test_error_envelopes_map_to_typed_exceptions(
    make_client, fixture, http_status, rate_limited, code, name
) -> None:
    client, _ = make_client(status_code=http_status, content=fixture_bytes(fixture))

    with pytest.raises(AdsefidApiError) as caught:
        await unwrap(client.user.get_info())

    error = caught.value
    assert error.code is code
    assert error.name == name
    assert error.http_status_code == http_status
    assert isinstance(error, AdsefidRateLimitError) is rate_limited


async def test_validation_details_survive_intact(make_client) -> None:
    """The real shape of a validation failure: a field-to-message map under
    `errors`, with plain string values."""
    client, _ = make_client(
        status_code=400, content=fixture_bytes("errors/error.invalid_parameter.json")
    )

    with pytest.raises(AdsefidApiError) as caught:
        await unwrap(client.user.get_templates())

    assert caught.value.details == {
        "errors": {
            "take": "invalid value for take",
            "state": "invalid value for state",
        }
    }


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        pytest.param(
            "errors/error.details_single.json",
            {"receptor": "invalid value for receptor"},
            id="single send is a flat field to message map",
        ),
        pytest.param(
            "errors/error.details_bulk.json",
            {
                "errors": {"line_number": "invalid value for line_number"},
                "messages": [
                    {"index": 0, "errors": {"receptor": "invalid value for receptor"}},
                    {
                        "index": 2,
                        "errors": {
                            "local_id": "invalid value for local_id",
                            "message": "invalid value for message",
                        },
                    },
                ],
            },
            id="bulk carries per-item errors keyed by index",
        ),
        pytest.param(
            "errors/error.details_cancel.json",
            {"local_ids": ["order-10001", "order-10002"]},
            id="cancel is the one shape whose values are arrays",
        ),
    ],
)
async def test_every_details_shape_survives_unchanged(make_client, fixture, expected) -> None:
    """`details` is deliberately untyped because the service uses a different
    shape per endpoint. Each real shape must come through uncoerced."""
    client, _ = make_client(status_code=400, content=fixture_bytes(fixture))

    with pytest.raises(AdsefidApiError) as caught:
        await unwrap(client.user.get_info())

    assert caught.value.details == expected


async def test_an_unmapped_code_is_carried_through_not_rejected(make_client) -> None:
    """A code the enum does not know about must not break the response.

    The service adds codes over time; falling back to the raw int keeps an
    older SDK working against a newer service.
    """
    client, _ = make_client(
        status_code=400, content=fixture_bytes("errors/error.unknown_code.json")
    )

    with pytest.raises(AdsefidApiError) as caught:
        await unwrap(client.user.get_info())

    assert caught.value.code == 2999
    assert caught.value.name == "SOME_FUTURE_SERVER_ERROR"


async def test_a_500_with_an_html_body(make_client) -> None:
    client, _ = make_client(status_code=500, content=fixture_bytes("errors/error.not_json.txt"))

    with pytest.raises(AdsefidApiError) as caught:
        await unwrap(client.user.get_info())

    assert not isinstance(caught.value, AdsefidRateLimitError)
    assert caught.value.http_status_code == 500
    assert caught.value.name == "HTTP_500"


async def test_a_bare_429_is_still_a_rate_limit(make_client) -> None:
    client, _ = make_client(status_code=429, content=fixture_bytes("errors/error.not_json.txt"))

    with pytest.raises(AdsefidRateLimitError):
        await unwrap(client.user.get_info())


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(b"", id="empty body"),
        pytest.param(b"<html>nope</html>", id="not json"),
        pytest.param(b'{"status":"partial","data":{}}', id="unrecognized status word"),
    ],
)
async def test_a_body_that_is_not_an_envelope_is_an_api_error(make_client, body) -> None:
    client, _ = make_client(status_code=200, content=body)

    with pytest.raises(AdsefidApiError):
        await unwrap(client.user.get_info())


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(b'{"status":"success"}', id="no data field"),
        pytest.param(b'{"status":"success","data":null}', id="null data"),
        pytest.param(b'{"status":"success","data":"nope"}', id="data is a scalar"),
    ],
)
async def test_a_success_envelope_with_no_payload_is_a_transport_error(make_client, body) -> None:
    """Never let a malformed payload surface as a bare KeyError from a model."""
    client, _ = make_client(status_code=200, content=body)

    with pytest.raises(AdsefidTransportError):
        await unwrap(client.user.get_info())


async def test_a_network_failure_becomes_a_transport_error(make_client) -> None:
    client, _ = make_client(raises=httpx.ConnectError("connection refused"))

    with pytest.raises(AdsefidTransportError):
        await unwrap(client.user.get_info())


async def test_a_timeout_becomes_a_transport_error(make_client) -> None:
    client, _ = make_client(raises=httpx.ReadTimeout("timed out"))

    with pytest.raises(AdsefidTransportError):
        await unwrap(client.user.get_info())


def test_the_exception_hierarchy() -> None:
    """A rate limit is an API error, so `except AdsefidApiError` catches it too.

    Callers who want to treat rate limits specially must order their handlers
    accordingly — the narrower class first.
    """
    assert issubclass(AdsefidRateLimitError, AdsefidApiError)
    assert issubclass(AdsefidApiError, AdsefidError)
    assert issubclass(AdsefidTransportError, AdsefidError)


def test_the_repr_carries_the_diagnostic_fields() -> None:
    error = AdsefidApiError(
        "boom", code=2024, name="INVALID_PARAMETER", http_status_code=400, details={"a": 1}
    )
    rendered = repr(error)
    assert "2024" in rendered
    assert "INVALID_PARAMETER" in rendered
    assert "400" in rendered
