from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

from .._base import expect_object
from .._serialization import (
    MESSENGER_MESSAGE_MAX_LENGTH,
    join_csv,
    validate_ids_count,
    validate_local_id,
    validate_max_length,
    validate_non_empty,
)
from ..exceptions import AdsefidValidationError
from ..models.common import CancelResult, StatusResult
from ..models.messenger import (
    CancelMessengerRequest,
    SendBulkMessengerRequest,
    SendBulkMessengerResult,
    SendP2pMessengerRequest,
    SendP2pMessengerResult,
    SendSingleMessengerRequest,
    SendSingleMessengerResult,
    SendTemplateMessengerRequest,
    SendTemplateMessengerResult,
    UploadMessengerFileResult,
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


def _validate_send_p2p(request: SendP2pMessengerRequest) -> None:
    validate_non_empty(request.profile, field_name="profile")
    if not request.receptors:
        raise AdsefidValidationError("'receptors' must contain at least 1 item")


def _validate_send_template(request: SendTemplateMessengerRequest) -> None:
    validate_non_empty(request.template_id, field_name="template_id")
    validate_non_empty(request.receptor, field_name="receptor")
    validate_non_empty(request.profile, field_name="profile")
    validate_local_id(request.local_id)


def _validate_cancel(request: CancelMessengerRequest) -> None:
    if not request.message_ids and not request.local_ids:
        raise AdsefidValidationError("At least one of 'message_ids'/'local_ids' must be non-empty")


def _build_files_payload(
    file: FileSource,
    filename: str | None,
    content_type: str | None,
) -> dict[str, tuple[str, bytes | BinaryIO, str | None]]:
    if isinstance(file, (str, Path)):
        path = Path(file)
        resolved_filename = filename or path.name
        return {"file": (resolved_filename, path.read_bytes(), content_type)}
    if isinstance(file, (bytes, bytearray)):
        resolved_filename = filename or "file"
        return {"file": (resolved_filename, bytes(file), content_type)}
    resolved_filename = filename or os.path.basename(str(getattr(file, "name", "") or "")) or "file"
    return {"file": (resolved_filename, file, content_type)}


class MessengerResource:
    """Synchronous messenger (Rubika/Bale/etc.) operations, available as
    `AdsefidClient(...).messenger`.
    """

    def __init__(self, client: AdsefidClient) -> None:
        self._client = client

    def send_single(self, request: SendSingleMessengerRequest) -> SendSingleMessengerResult:
        """Send one messenger message to one receptor (`POST /v1/messenger/single`).

        Raises AdsefidValidationError if `message`/`receptor`/`profile` is empty,
        `message` exceeds `MESSENGER_MESSAGE_MAX_LENGTH`, or `local_id` doesn't match
        the required shape.
        """
        _validate_send_single(request)
        data = self._client.request("POST", "/v1/messenger/single", json_body=request.to_dict())
        return SendSingleMessengerResult.from_dict(expect_object(data))

    def send_bulk(self, request: SendBulkMessengerRequest) -> SendBulkMessengerResult:
        """Send the same message body to many receptors (`POST /v1/messenger/bulk`).

        A per-receptor delivery failure does not raise: it is reported as a normal
        typed result via each item's `status`/`raw_status` field. Raises
        AdsefidValidationError for empty `receptors` or empty/too-long request-level
        fields. Item errors are returned in the partial API response.
        """
        _validate_send_bulk(request)
        data = self._client.request("POST", "/v1/messenger/bulk", json_body=request.to_dict())
        return SendBulkMessengerResult.from_dict(expect_object(data))

    def send_p2p(self, request: SendP2pMessengerRequest) -> SendP2pMessengerResult:
        """Send a distinct message per receptor in one call (`POST /v1/messenger/p2p`).

        Like `send_bulk`, a per-message delivery failure is a normal typed result,
        not an exception. Raises AdsefidValidationError for empty `receptors` or
        `profile`. Item errors are returned in the partial API response.
        """
        _validate_send_p2p(request)
        data = self._client.request("POST", "/v1/messenger/p2p", json_body=request.to_dict())
        return SendP2pMessengerResult.from_dict(expect_object(data))

    def upload_file(
        self,
        file: FileSource,
        *,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> UploadMessengerFileResult:
        """Upload an attachment for later use as a message `file_id`
        (`POST /v1/messenger/file`).

        `file` accepts a path (`str`/`Path`), raw `bytes`/`bytearray`, or an
        already-open binary file object. `filename` defaults to the source path's
        name (or `"file"` for bytes/an unnamed stream) if not given.
        """
        files = _build_files_payload(file, filename, content_type)
        data = self._client.request("POST", "/v1/messenger/file", files=files)
        return UploadMessengerFileResult.from_dict(expect_object(data))

    def cancel(self, request: CancelMessengerRequest) -> CancelResult:
        """Cancel scheduled/pending messages (`POST /v1/messenger/cancel`).

        Raises AdsefidValidationError if both `message_ids` and `local_ids` are empty.
        """
        _validate_cancel(request)
        data = self._client.request("POST", "/v1/messenger/cancel", json_body=request.to_dict())
        return CancelResult.from_dict(expect_object(data))

    def send_template(self, request: SendTemplateMessengerRequest) -> SendTemplateMessengerResult:
        """Send a pre-approved template message (`POST /v1/messenger/template`).

        Raises AdsefidValidationError if `template_id`/`receptor`/`profile` is empty
        or `local_id` doesn't match the required shape.
        """
        _validate_send_template(request)
        data = self._client.request("POST", "/v1/messenger/template", json_body=request.to_dict())
        return SendTemplateMessengerResult.from_dict(expect_object(data))

    def get_status(
        self,
        *,
        message_ids: Sequence[str] | None = None,
        local_ids: Sequence[str] | None = None,
    ) -> StatusResult:
        """Look up delivery status for previously sent messages
        (`GET /v1/messenger/status`).

        At least one of `message_ids`/`local_ids` is required; their combined
        distinct count must not exceed `MAX_STATUS_IDS`. Raises
        AdsefidValidationError otherwise.
        """
        validate_ids_count(message_ids, local_ids)
        params = {"message_ids": join_csv(message_ids), "local_ids": join_csv(local_ids)}
        data = self._client.request("GET", "/v1/messenger/status", query_params=params)
        return StatusResult.from_dict(expect_object(data))


class AsyncMessengerResource:
    """Asynchronous messenger operations, available as
    `AdsefidAsyncClient(...).messenger`.

    Same operations, validation, and error behavior as `MessengerResource`; see its
    method docstrings for details.
    """

    def __init__(self, client: AdsefidAsyncClient) -> None:
        self._client = client

    async def send_single(self, request: SendSingleMessengerRequest) -> SendSingleMessengerResult:
        _validate_send_single(request)
        data = await self._client.request(
            "POST", "/v1/messenger/single", json_body=request.to_dict()
        )
        return SendSingleMessengerResult.from_dict(expect_object(data))

    async def send_bulk(self, request: SendBulkMessengerRequest) -> SendBulkMessengerResult:
        _validate_send_bulk(request)
        data = await self._client.request("POST", "/v1/messenger/bulk", json_body=request.to_dict())
        return SendBulkMessengerResult.from_dict(expect_object(data))

    async def send_p2p(self, request: SendP2pMessengerRequest) -> SendP2pMessengerResult:
        _validate_send_p2p(request)
        data = await self._client.request("POST", "/v1/messenger/p2p", json_body=request.to_dict())
        return SendP2pMessengerResult.from_dict(expect_object(data))

    async def upload_file(
        self,
        file: FileSource,
        *,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> UploadMessengerFileResult:
        files = _build_files_payload(file, filename, content_type)
        data = await self._client.request("POST", "/v1/messenger/file", files=files)
        return UploadMessengerFileResult.from_dict(expect_object(data))

    async def cancel(self, request: CancelMessengerRequest) -> CancelResult:
        _validate_cancel(request)
        data = await self._client.request(
            "POST", "/v1/messenger/cancel", json_body=request.to_dict()
        )
        return CancelResult.from_dict(expect_object(data))

    async def send_template(
        self, request: SendTemplateMessengerRequest
    ) -> SendTemplateMessengerResult:
        _validate_send_template(request)
        data = await self._client.request(
            "POST", "/v1/messenger/template", json_body=request.to_dict()
        )
        return SendTemplateMessengerResult.from_dict(expect_object(data))

    async def get_status(
        self,
        *,
        message_ids: Sequence[str] | None = None,
        local_ids: Sequence[str] | None = None,
    ) -> StatusResult:
        validate_ids_count(message_ids, local_ids)
        params = {"message_ids": join_csv(message_ids), "local_ids": join_csv(local_ids)}
        data = await self._client.request("GET", "/v1/messenger/status", query_params=params)
        return StatusResult.from_dict(expect_object(data))
