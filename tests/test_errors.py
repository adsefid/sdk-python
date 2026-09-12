"""HTTP status × error envelope mapping, and the transport/success edges."""

from __future__ import annotations

import httpx
import pytest

from adsefid import (
    AdsefidApiError,
    AdsefidError,
    AdsefidRateLimitError,
    AdsefidTransportError,
    ApiErrorDetails,
    ApiFieldError,
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


async def test_validation_details_are_strongly_typed(make_client) -> None:
    client, _ = make_client(
        status_code=400, content=fixture_bytes("errors/error.invalid_parameter.json")
    )

    with pytest.raises(AdsefidApiError) as caught:
        await unwrap(client.user.get_templates())

    details = caught.value.details
    assert details is not None
    assert details.errors is not None
    assert details.errors["take"].code is WebServiceResponseCode.INVALID_PARAMETER
    assert details.errors["state"].name == "INVALID_PARAMETER"


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        pytest.param(
            "errors/error.details_single.json",
            {"errors": {"receptor": {"code": 2014, "name": "INVALID_RECEPTOR"}}},
            id="single send field errors",
        ),
        pytest.param(
            "errors/error.details_bulk.json",
            {
                "items": [
                    {
                        "index": 0,
                        "errors": {"receptor": {"code": 2014, "name": "INVALID_RECEPTOR"}},
                    },
                    {
                        "index": 2,
                        "errors": {"local_id": {"code": 2007, "name": "DUPLICATE_LOCAL_ID"}},
                    },
                ],
            },
            id="bulk item errors",
        ),
        pytest.param(
            "errors/error.details_cancel.json",
            {
                "errors": {
                    "order-10001": {"code": 2029, "name": "INVALID_LOCAL_IDS"},
                    "order-10002": {"code": 2029, "name": "INVALID_LOCAL_IDS"},
                }
            },
            id="cancel errors keyed by rejected id",
        ),
    ],
)
async def test_every_details_shape_maps_to_the_shared_model(make_client, fixture, expected) -> None:
    client, _ = make_client(status_code=400, content=fixture_bytes(fixture))

    with pytest.raises(AdsefidApiError) as caught:
        await unwrap(client.user.get_info())

    assert caught.value.details is not None
    assert caught.value.details.to_dict() == expected


async def test_an_unknown_nested_code_keeps_its_raw_integer(make_client) -> None:
    body = (
        b'{"status":"error","error":{"code":2024,"name":"INVALID_PARAMETER",'
        b'"details":{"errors":{"future":{"code":2999,"name":"FUTURE_CODE"}}}}}'
    )
    client, _ = make_client(status_code=400, content=body)

    with pytest.raises(AdsefidApiError) as caught:
        await unwrap(client.user.get_info())

    details = caught.value.details
    assert details is not None and details.errors is not None
    assert details.errors["future"].code == 2999


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
        "boom",
        code=2024,
        name="INVALID_PARAMETER",
        http_status_code=400,
        details=ApiErrorDetails(errors={"a": ApiFieldError(code=2024, name="INVALID_PARAMETER")}),
    )
    rendered = repr(error)
    assert "2024" in rendered
    assert "INVALID_PARAMETER" in rendered
    assert "400" in rendered


@pytest.mark.parametrize(
    ("call", "content"),
    [
        (lambda client: client.user.get_info(), b'{"status":"success","data":[]}'),
        (lambda client: client.user.get_lines(), b'{"status":"success","data":{}}'),
        (
            lambda client: client.sms.get_status(message_ids=["a"]),
            b'{"status":"success","data":[]}',
        ),
    ],
    ids=["object expected, array sent", "array expected, object sent", "status list as array"],
)
async def test_a_success_payload_of_the_wrong_shape_is_a_transport_error(
    make_client, call, content
) -> None:
    client, _ = make_client(content=content)

    with pytest.raises(AdsefidTransportError):
        await unwrap(call(client))
