from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

from .._base import parse_object
from .._serialization import (
    MAX_CANCEL_IDS,
    MAX_MESSENGER_FILE_BYTES,
    MESSENGER_MESSAGE_MAX_LENGTH,
    validate_file_size,
    validate_ids_count,
    validate_local_id,
    validate_max_length,
    validate_non_empty,
)
from ..exceptions import AdsefidValidationError
from ..models.common import CancelResponse, StatusResponse
from ..models.messenger import (
    CancelMessengerRequest,
    SendBulkMessengerRequest,
    SendBulkMessengerResponse,
    SendP2PMessengerRequest,
    SendP2PMessengerResponse,
    SendSingleMessengerRequest,
    SendSingleMessengerResponse,
    SendTemplateMessengerRequest,
    SendTemplateMessengerResponse,
    UploadMessengerFileResponse,
)

if TYPE_CHECKING:
    from ..async_client import AdsefidAsyncClient
    from ..client import AdsefidClient

FileSource = str | Path | bytes | bytearray | BinaryIO


def _validate_send_single(request: SendSingleMessengerRequest) -> None:
    validate_non_empty(request.message, field_name="message")
    validate_max_length(
        request.message, field_name="message", max_length=MESSENGER_MESSAGE_MAX_LENGTH
    )
    validate_non_empty(request.receptor, field_name="receptor")
    validate_non_empty(request.profile, field_name="profile")
    validate_local_id(request.local_id)


def _validate_send_bulk(request: SendBulkMessengerRequest) -> None:
    validate_non_empty(request.message, field_name="message")
    validate_max_length(
        request.message, field_name="message", max_length=MESSENGER_MESSAGE_MAX_LENGTH
    )
    validate_non_empty(request.profile, field_name="profile")
    if not request.receptors:
        raise AdsefidValidationError("'receptors' must contain at least 1 item")


def _validate_send_p2p(request: SendP2PMessengerRequest) -> None:
    validate_non_empty(request.profile, field_name="profile")
    if not request.receptors:
        raise AdsefidValidationError("'receptors' must contain at least 1 item")


def _validate_send_template(request: SendTemplateMessengerRequest) -> None:
    validate_non_empty(request.template_id, field_name="template_id")
    validate_non_empty(request.receptor, field_name="receptor")
    validate_non_empty(request.profile, field_name="profile")
    validate_local_id(request.local_id)


def _validate_cancel(request: CancelMessengerRequest) -> None:
    validate_ids_count(request.message_ids, request.local_ids, max_total=MAX_CANCEL_IDS)


def _build_files_payload(
    file: FileSource,
    filename: str | None,
    content_type: str,
) -> dict[str, tuple[str, bytes | BinaryIO, str]]:
    validate_non_empty(content_type, field_name="content_type")
    if isinstance(file, str | Path):
        path = Path(file)
        validate_file_size(path.stat().st_size)
        return {"file": (filename or path.name, path.read_bytes(), content_type)}
    if isinstance(file, bytes | bytearray):
        validate_file_size(len(file))
        return {"file": (filename or "file", bytes(file), content_type)}
    resolved_filename = filename or os.path.basename(str(getattr(file, "name", "") or "")) or "file"
    if file.seekable():
        position = file.tell()
        validate_file_size(file.seek(0, os.SEEK_END) - position)
        file.seek(position)
        return {"file": (resolved_filename, file, content_type)}
    content = file.read(MAX_MESSENGER_FILE_BYTES + 1)
    validate_file_size(len(content))
    return {"file": (resolved_filename, content, content_type)}


class MessengerResource:
    """Synchronous messenger (Rubika/Bale/etc.) operations, available as
    `AdsefidClient(...).messenger`.
    """

    def __init__(self, client: AdsefidClient) -> None:
        self._client = client

    def send_single(self, request: SendSingleMessengerRequest) -> SendSingleMessengerResponse:
        """Send one messenger message to one receptor (`POST /v1/messenger/single`).

        Raises AdsefidValidationError if `message`/`receptor`/`profile` is empty,
        `message` exceeds `MESSENGER_MESSAGE_MAX_LENGTH`, or `local_id` doesn't match
        the required shape.
        """
        _validate_send_single(request)
        data = self._client._request("POST", "/v1/messenger/single", json_body=request.to_dict())
        return parse_object(SendSingleMessengerResponse.from_dict, data)

    def send_bulk(self, request: SendBulkMessengerRequest) -> SendBulkMessengerResponse:
        """Send the same message body to many receptors (`POST /v1/messenger/bulk`).

        A per-receptor delivery failure does not raise: it is reported as a normal
        typed result via each item's `status`/`raw_status` field. Raises
        AdsefidValidationError for empty `receptors` or empty/too-long request-level
        fields. Item errors are returned in the partial API response.
        """
        _validate_send_bulk(request)
        data = self._client._request("POST", "/v1/messenger/bulk", json_body=request.to_dict())
        return parse_object(SendBulkMessengerResponse.from_dict, data)

    def send_p2p(self, request: SendP2PMessengerRequest) -> SendP2PMessengerResponse:
        """Send a distinct message per receptor in one call (`POST /v1/messenger/p2p`).

        Like `send_bulk`, a per-message delivery failure is a normal typed result,
        not an exception. Raises AdsefidValidationError for empty `receptors` or
        `profile`. Item errors are returned in the partial API response.
        """
        _validate_send_p2p(request)
        data = self._client._request("POST", "/v1/messenger/p2p", json_body=request.to_dict())
        return parse_object(SendP2PMessengerResponse.from_dict, data)

    def upload_file(
        self,
        file: FileSource,
        *,
        filename: str | None = None,
        content_type: str,
    ) -> UploadMessengerFileResponse:
        """Upload an attachment for later use as a message `file_id`
        (`POST /v1/messenger/file`).

        `file` accepts a path (`str`/`Path`), raw `bytes`/`bytearray`, or an
        already-open binary file object. `filename` defaults to the source path's
        name (or `"file"` for bytes/an unnamed stream) if not given. `content_type` is
        required. Content above `MAX_MESSENGER_FILE_BYTES` (15 MiB) raises
        AdsefidValidationError before any request is sent.
        """
        files = _build_files_payload(file, filename, content_type)
        data = self._client._request("POST", "/v1/messenger/file", files=files)
        return parse_object(UploadMessengerFileResponse.from_dict, data)

    def cancel(self, request: CancelMessengerRequest) -> CancelResponse:
        """Cancel eligible Messenger messages (`POST /v1/messenger/cancel`).

        Raises AdsefidValidationError for empty IDs or over 2,000 distinct IDs combined.
        """
        _validate_cancel(request)
        data = self._client._request("POST", "/v1/messenger/cancel", json_body=request.to_dict())
        return parse_object(CancelResponse.from_dict, data)

    def send_template(self, request: SendTemplateMessengerRequest) -> SendTemplateMessengerResponse:
        """Send a pre-approved template message (`POST /v1/messenger/template`).

        Raises AdsefidValidationError if `template_id`/`receptor`/`profile` is empty
        or `local_id` doesn't match the required shape.
        """
        _validate_send_template(request)
        data = self._client._request("POST", "/v1/messenger/template", json_body=request.to_dict())
        return parse_object(SendTemplateMessengerResponse.from_dict, data)

    def get_status(
        self,
        *,
        message_ids: Sequence[str] | None = None,
        local_ids: Sequence[str] | None = None,
    ) -> StatusResponse:
        """Look up delivery status for previously sent messages
        (`QUERY /v1/messenger/status`).

        At least one of `message_ids`/`local_ids` is required; their combined
        distinct count must not exceed `MAX_STATUS_IDS`. Raises
        AdsefidValidationError otherwise.
        """
        validate_ids_count(message_ids, local_ids)
        params = {
            key: list(dict.fromkeys(ids))
            for key, ids in (("message_ids", message_ids), ("local_ids", local_ids))
            if ids
        }
        data = self._client._request("QUERY", "/v1/messenger/status", json_body=params)
        return parse_object(StatusResponse.from_dict, data)


class AsyncMessengerResource:
    """Asynchronous messenger operations, available as
    `AdsefidAsyncClient(...).messenger`.

    Same operations, validation, and error behavior as `MessengerResource`; see its
    method docstrings for details.
    """

    def __init__(self, client: AdsefidAsyncClient) -> None:
        self._client = client

    async def send_single(self, request: SendSingleMessengerRequest) -> SendSingleMessengerResponse:
        _validate_send_single(request)
        data = await self._client._request(
            "POST", "/v1/messenger/single", json_body=request.to_dict()
        )
        return parse_object(SendSingleMessengerResponse.from_dict, data)

    async def send_bulk(self, request: SendBulkMessengerRequest) -> SendBulkMessengerResponse:
        _validate_send_bulk(request)
        data = await self._client._request(
            "POST", "/v1/messenger/bulk", json_body=request.to_dict()
        )
        return parse_object(SendBulkMessengerResponse.from_dict, data)

    async def send_p2p(self, request: SendP2PMessengerRequest) -> SendP2PMessengerResponse:
        _validate_send_p2p(request)
        data = await self._client._request("POST", "/v1/messenger/p2p", json_body=request.to_dict())
        return parse_object(SendP2PMessengerResponse.from_dict, data)

    async def upload_file(
        self,
        file: FileSource,
        *,
        filename: str | None = None,
        content_type: str,
    ) -> UploadMessengerFileResponse:
        files = _build_files_payload(file, filename, content_type)
        data = await self._client._request("POST", "/v1/messenger/file", files=files)
        return parse_object(UploadMessengerFileResponse.from_dict, data)

    async def cancel(self, request: CancelMessengerRequest) -> CancelResponse:
        _validate_cancel(request)
        data = await self._client._request(
            "POST", "/v1/messenger/cancel", json_body=request.to_dict()
        )
        return parse_object(CancelResponse.from_dict, data)

    async def send_template(
        self, request: SendTemplateMessengerRequest
    ) -> SendTemplateMessengerResponse:
        _validate_send_template(request)
        data = await self._client._request(
            "POST", "/v1/messenger/template", json_body=request.to_dict()
        )
        return parse_object(SendTemplateMessengerResponse.from_dict, data)

    async def get_status(
        self,
        *,
        message_ids: Sequence[str] | None = None,
        local_ids: Sequence[str] | None = None,
    ) -> StatusResponse:
        validate_ids_count(message_ids, local_ids)
        params = {
            key: list(dict.fromkeys(ids))
            for key, ids in (("message_ids", message_ids), ("local_ids", local_ids))
            if ids
        }
        data = await self._client._request("QUERY", "/v1/messenger/status", json_body=params)
        return parse_object(StatusResponse.from_dict, data)
