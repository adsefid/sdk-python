"""Messenger endpoints, run against both the sync and async clients."""

from __future__ import annotations

import email
from pathlib import Path

import pytest

from adsefid import AdsefidValidationError, WebServiceResponseCode
from adsefid.models.messenger import (
    CancelMessengerRequest,
    MessengerBulkReceptor,
    MessengerP2pReceptor,
    SendBulkMessengerRequest,
    SendP2pMessengerRequest,
    SendSingleMessengerRequest,
    SendTemplateMessengerRequest,
)
from adsefid.resources.messenger import _build_files_payload
from tests.conftest import unwrap
from tests.helpers.fixtures import fixture_bytes


async def test_send_single(make_client) -> None:
    client, recorder = make_client(
        content=fixture_bytes("envelopes/messenger.send_single.success.json")
    )

    result = await unwrap(
        client.messenger.send_single(
            SendSingleMessengerRequest(message="hi", receptor="98912xxxxxxx", profile="profile-1")
        )
    )

    request = recorder.only
    assert request.method == "POST"
    assert request.path == "/v1/messenger/single"
    for absent in ("hide", "file_id", "send_time", "local_id"):
        assert absent not in request.json
    assert result.message_id


async def test_send_bulk_partial_success_is_not_an_error(make_client) -> None:
    """HTTP 200 with per-receptor failures is a normal typed response."""
    client, recorder = make_client(
        content=fixture_bytes("envelopes/messenger.send_bulk.partial_success.json")
    )

    result = await unwrap(
        client.messenger.send_bulk(
            SendBulkMessengerRequest(
                receptors=[
                    MessengerBulkReceptor(receptor="a"),
                    MessengerBulkReceptor(receptor="", local_id="-bad"),
                ],
                message="m",
                profile="p",
            )
        )
    )

    assert [item.raw_status for item in result.receptors] == [1000, 2025]
    assert [item.error_code for item in result.receptors] == [
        None,
        WebServiceResponseCode.RECEPTOR_BLACKLISTED,
    ]
    assert result.receptors[1].message_id is None
    assert result.counts["2025"] == 1
    assert result.total_count == 2
    assert len(recorder.only.json["receptors"]) == 2


async def test_send_p2p_partial_success_is_not_an_error(make_client) -> None:
    client, recorder = make_client(
        content=fixture_bytes("envelopes/messenger.send_p2p.partial_success.json")
    )

    result = await unwrap(
        client.messenger.send_p2p(
            SendP2pMessengerRequest(
                receptors=[
                    MessengerP2pReceptor(receptor="a", message="m"),
                    MessengerP2pReceptor(receptor="", message=""),
                ],
                profile="p",
            )
        )
    )

    assert [item.raw_status for item in result.receptors] == [1000, 2014]
    assert len(recorder.only.json["receptors"]) == 2


async def test_send_template_keeps_leading_zeros(make_client) -> None:
    client, recorder = make_client(
        content=fixture_bytes("envelopes/messenger.send_template.success.json")
    )

    await unwrap(
        client.messenger.send_template(
            SendTemplateMessengerRequest(
                template_id="invoice_notice",
                parameters={"invoice": "001234", "amount": 2},
                receptor="98912xxxxxxx",
                profile="p",
            )
        )
    )

    parameters = recorder.only.json["parameters"]
    assert parameters["invoice"] == "001234"
    assert parameters["amount"] == 2


async def test_cancel(make_client) -> None:
    client, recorder = make_client(content=fixture_bytes("envelopes/messenger.cancel.success.json"))

    await unwrap(client.messenger.cancel(CancelMessengerRequest(message_ids=["m1"])))

    assert recorder.only.path == "/v1/messenger/cancel"


async def test_get_status(make_client) -> None:
    client, recorder = make_client(
        content=fixture_bytes("envelopes/messenger.get_status.success.json")
    )

    await unwrap(client.messenger.get_status(message_ids=["m1"], local_ids=["l1"]))

    request = recorder.only
    assert request.path == "/v1/messenger/status"
    assert request.params["message_ids"] == "m1"
    assert request.params["local_ids"] == "l1"


async def test_upload_file_sends_multipart(make_client) -> None:
    client, recorder = make_client(
        content=fixture_bytes("envelopes/messenger.upload_file.success.json")
    )

    result = await unwrap(
        client.messenger.upload_file(
            b"file-contents-here", filename="invoice.pdf", content_type="application/pdf"
        )
    )

    request = recorder.only
    assert request.path == "/v1/messenger/file"
    content_type = request.headers["Content-Type"]
    assert content_type.startswith("multipart/form-data")

    # Parse the body rather than string-matching it: httpx generates a random
    # boundary, so a literal comparison would be meaningless.
    parsed = email.message_from_bytes(
        f"Content-Type: {content_type}\r\n\r\n".encode() + request.content
    )
    parts = [part for part in parsed.walk() if not part.is_multipart()]
    assert len(parts) == 1
    part = parts[0]
    assert 'name="file"' in part["Content-Disposition"]
    assert 'filename="invoice.pdf"' in part["Content-Disposition"]
    assert part.get_content_type() == "application/pdf"
    assert part.get_payload(decode=True) == b"file-contents-here"

    assert result.file_id


class TestBuildFilesPayload:
    """`upload_file` accepts a path, raw bytes, or an open binary file."""

    def test_bytes_default_to_a_generic_filename(self) -> None:
        payload = _build_files_payload(b"data", None, None)
        assert payload["file"] == ("file", b"data", None)

    def test_bytes_keep_an_explicit_filename(self) -> None:
        payload = _build_files_payload(b"data", "report.csv", "text/csv")
        assert payload["file"] == ("report.csv", b"data", "text/csv")

    def test_a_path_defaults_to_its_basename(self, tmp_path: Path) -> None:
        source = tmp_path / "statement.txt"
        source.write_bytes(b"hello")

        payload = _build_files_payload(source, None, "text/plain")

        assert payload["file"] == ("statement.txt", b"hello", "text/plain")

    def test_an_open_file_defaults_to_its_name(self, tmp_path: Path) -> None:
        source = tmp_path / "banner.png"
        source.write_bytes(b"\x89PNG")

        with source.open("rb") as handle:
            payload = _build_files_payload(handle, None, "image/png")
            assert payload["file"][0] == "banner.png"
            assert payload["file"][1] is handle


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(
            lambda c: c.messenger.send_single(
                SendSingleMessengerRequest(message="", receptor="a", profile="p")
            ),
            id="empty message",
        ),
        pytest.param(
            lambda c: c.messenger.send_single(
                SendSingleMessengerRequest(message="m", receptor="a", profile="")
            ),
            id="empty profile",
        ),
        pytest.param(
            lambda c: c.messenger.send_single(
                SendSingleMessengerRequest(message="x" * 4001, receptor="a", profile="p")
            ),
            id="message over the limit",
        ),
        pytest.param(
            lambda c: c.messenger.send_bulk(
                SendBulkMessengerRequest(receptors=[], message="m", profile="p")
            ),
            id="no receptors",
        ),
        pytest.param(
            lambda c: c.messenger.cancel(CancelMessengerRequest()),
            id="cancel with neither id list",
        ),
        pytest.param(lambda c: c.messenger.get_status(), id="status with neither id list"),
    ],
)
async def test_validation_rejects_before_any_request_is_sent(make_client, build) -> None:
    client, recorder = make_client(
        content=fixture_bytes("envelopes/messenger.send_single.success.json")
    )

    with pytest.raises(AdsefidValidationError):
        await unwrap(build(client))

    assert recorder.requests == []
