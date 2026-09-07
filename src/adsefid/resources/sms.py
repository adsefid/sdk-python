from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING

from .._serialization import (
    SMS_MESSAGE_MAX_LENGTH,
    format_datetime,
    join_csv,
    validate_ids_count,
    validate_local_id,
    validate_max_length,
    validate_non_empty,
    validate_receive_count,
)
from ..exceptions import AdsefidValidationError
from ..models.common import CancelResult, StatusResult
from ..models.sms import (
    CancelSmsRequest,
    GetReceivedSmsResult,
    SendBulkSmsRequest,
    SendBulkSmsResult,
    SendP2pSmsRequest,
    SendP2pSmsResult,
    SendSingleSmsRequest,
    SendSingleSmsResult,
    SendSmsTemplateRequest,
    SendSmsTemplateResult,
)

if TYPE_CHECKING:
    from ..async_client import AdsefidAsyncClient
    from ..client import AdsefidClient


def _validate_send_single(request: SendSingleSmsRequest) -> None:
    validate_non_empty(request.receptor, field_name="receptor")
    validate_non_empty(request.line_number, field_name="line_number")
    validate_non_empty(request.message, field_name="message")
    validate_max_length(request.message, field_name="message", max_length=SMS_MESSAGE_MAX_LENGTH)
    validate_local_id(request.local_id)


def _validate_send_bulk(request: SendBulkSmsRequest) -> None:
    validate_non_empty(request.message, field_name="message")
    validate_max_length(request.message, field_name="message", max_length=SMS_MESSAGE_MAX_LENGTH)
    validate_non_empty(request.line_number, field_name="line_number")
    if not request.receptors:
        raise AdsefidValidationError("'receptors' must contain at least 1 item")
    for receptor in request.receptors:
        validate_non_empty(receptor.receptor, field_name="receptors[].receptor")
        validate_local_id(receptor.local_id, field_name="receptors[].local_id")


def _validate_send_p2p(request: SendP2pSmsRequest) -> None:
    validate_non_empty(request.line_number, field_name="line_number")
    if not request.messages:
        raise AdsefidValidationError("'messages' must contain at least 1 item")
    for message in request.messages:
        validate_non_empty(message.receptor, field_name="messages[].receptor")
        validate_non_empty(message.message, field_name="messages[].message")
        validate_max_length(
            message.message, field_name="messages[].message", max_length=SMS_MESSAGE_MAX_LENGTH
        )
        validate_local_id(message.local_id, field_name="messages[].local_id")


def _validate_send_template(request: SendSmsTemplateRequest) -> None:
    validate_non_empty(request.template_id, field_name="template_id")
    validate_non_empty(request.receptor, field_name="receptor")
    validate_non_empty(request.line_number, field_name="line_number")
    validate_local_id(request.local_id)


def _validate_cancel(request: CancelSmsRequest) -> None:
    if not request.message_ids and not request.local_ids:
        raise AdsefidValidationError("At least one of 'message_ids'/'local_ids' must be non-empty")


def _receive_query_params(
    line_number: str, count: int | None, since: datetime | None
) -> dict[str, str | int]:
    validate_non_empty(line_number, field_name="line_number")
    validate_receive_count(count)
    params: dict[str, str | int] = {"line_number": line_number}
    if count is not None:
        params["count"] = count
    if since is not None:
        formatted = format_datetime(since)
        if formatted is not None:
            params["since"] = formatted
    return params


class SmsResource:
    """Synchronous SMS operations, available as `AdsefidClient(...).sms`."""

    def __init__(self, client: AdsefidClient) -> None:
        self._client = client

    def send_single(self, request: SendSingleSmsRequest) -> SendSingleSmsResult:
        """Send one SMS to one receptor (`POST /v1/sms/single`).

        Raises AdsefidValidationError if `receptor`/`line_number`/`message` is empty,
        `message` exceeds `SMS_MESSAGE_MAX_LENGTH`, or `local_id` doesn't match the
        required shape.
        """
        _validate_send_single(request)
        data = self._client.request("POST", "/v1/sms/single", json_body=request.to_dict())
        return SendSingleSmsResult.from_dict(data)  # type: ignore[arg-type]

    def send_bulk(self, request: SendBulkSmsRequest) -> SendBulkSmsResult:
        """Send the same SMS body to many receptors (`POST /v1/sms/bulk`).

        A per-receptor delivery failure does not raise: it is reported as a normal
        typed result via each item's `status`/`raw_status` field. Raises
        AdsefidValidationError for empty `receptors`, empty/too-long `message`, or an
        invalid `local_id` on any receptor.
        """
        _validate_send_bulk(request)
        data = self._client.request("POST", "/v1/sms/bulk", json_body=request.to_dict())
        return SendBulkSmsResult.from_dict(data)  # type: ignore[arg-type]

    def send_p2p(self, request: SendP2pSmsRequest) -> SendP2pSmsResult:
        """Send a distinct message per receptor in one call (`POST /v1/sms/p2p`).

        Like `send_bulk`, a per-message delivery failure is a normal typed result,
        not an exception. Raises AdsefidValidationError for empty `messages`, or an
        empty/too-long message body or invalid `local_id` on any entry.
        """
        _validate_send_p2p(request)
        data = self._client.request("POST", "/v1/sms/p2p", json_body=request.to_dict())
        return SendP2pSmsResult.from_dict(data)  # type: ignore[arg-type]

    def send_template(self, request: SendSmsTemplateRequest) -> SendSmsTemplateResult:
        """Send a pre-approved template message (`POST /v1/sms/template`).

        Raises AdsefidValidationError if `template_id`/`receptor`/`line_number` is
        empty or `local_id` doesn't match the required shape.
        """
        _validate_send_template(request)
        data = self._client.request("POST", "/v1/sms/template", json_body=request.to_dict())
        return SendSmsTemplateResult.from_dict(data)  # type: ignore[arg-type]

    def get_status(
        self,
        *,
        message_ids: Sequence[str] | None = None,
        local_ids: Sequence[str] | None = None,
    ) -> StatusResult:
        """Look up delivery status for previously sent messages (`GET /v1/sms/status`).

        At least one of `message_ids`/`local_ids` is required; their combined
        distinct count must not exceed `MAX_STATUS_IDS`. Raises
        AdsefidValidationError otherwise.
        """
        validate_ids_count(message_ids, local_ids)
        params = {"message_ids": join_csv(message_ids), "local_ids": join_csv(local_ids)}
        data = self._client.request("GET", "/v1/sms/status", query_params=params)
        return StatusResult.from_dict(data)  # type: ignore[arg-type]

    def cancel(self, request: CancelSmsRequest) -> CancelResult:
        """Cancel scheduled/pending messages (`POST /v1/sms/cancel`).

        Raises AdsefidValidationError if both `message_ids` and `local_ids` are empty.
        """
        _validate_cancel(request)
        data = self._client.request("POST", "/v1/sms/cancel", json_body=request.to_dict())
        return CancelResult.from_dict(data)  # type: ignore[arg-type]

    def get_received(
        self,
        *,
        line_number: str,
        count: int | None = None,
        since: datetime | None = None,
    ) -> GetReceivedSmsResult:
        """Fetch inbound SMS received on a line (`GET /v1/sms/receive`).

        Raises AdsefidValidationError if `line_number` is empty or `count` is not in
        `(0, MAX_RECEIVE_COUNT)`.
        """
        params = _receive_query_params(line_number, count, since)
        data = self._client.request("GET", "/v1/sms/receive", query_params=params)
        return GetReceivedSmsResult.from_dict(data)  # type: ignore[arg-type]


class AsyncSmsResource:
    """Asynchronous SMS operations, available as `AdsefidAsyncClient(...).sms`.

    Same operations, validation, and error behavior as `SmsResource`; see its
    method docstrings for details.
    """

    def __init__(self, client: AdsefidAsyncClient) -> None:
        self._client = client

    async def send_single(self, request: SendSingleSmsRequest) -> SendSingleSmsResult:
        _validate_send_single(request)
        data = await self._client.request("POST", "/v1/sms/single", json_body=request.to_dict())
        return SendSingleSmsResult.from_dict(data)  # type: ignore[arg-type]

    async def send_bulk(self, request: SendBulkSmsRequest) -> SendBulkSmsResult:
        _validate_send_bulk(request)
        data = await self._client.request("POST", "/v1/sms/bulk", json_body=request.to_dict())
        return SendBulkSmsResult.from_dict(data)  # type: ignore[arg-type]

    async def send_p2p(self, request: SendP2pSmsRequest) -> SendP2pSmsResult:
        _validate_send_p2p(request)
        data = await self._client.request("POST", "/v1/sms/p2p", json_body=request.to_dict())
        return SendP2pSmsResult.from_dict(data)  # type: ignore[arg-type]

    async def send_template(self, request: SendSmsTemplateRequest) -> SendSmsTemplateResult:
        _validate_send_template(request)
        data = await self._client.request("POST", "/v1/sms/template", json_body=request.to_dict())
        return SendSmsTemplateResult.from_dict(data)  # type: ignore[arg-type]

    async def get_status(
        self,
        *,
        message_ids: Sequence[str] | None = None,
        local_ids: Sequence[str] | None = None,
    ) -> StatusResult:
        validate_ids_count(message_ids, local_ids)
        params = {"message_ids": join_csv(message_ids), "local_ids": join_csv(local_ids)}
        data = await self._client.request("GET", "/v1/sms/status", query_params=params)
        return StatusResult.from_dict(data)  # type: ignore[arg-type]

    async def cancel(self, request: CancelSmsRequest) -> CancelResult:
        _validate_cancel(request)
        data = await self._client.request("POST", "/v1/sms/cancel", json_body=request.to_dict())
        return CancelResult.from_dict(data)  # type: ignore[arg-type]

    async def get_received(
        self,
        *,
        line_number: str,
        count: int | None = None,
        since: datetime | None = None,
    ) -> GetReceivedSmsResult:
        params = _receive_query_params(line_number, count, since)
        data = await self._client.request("GET", "/v1/sms/receive", query_params=params)
        return GetReceivedSmsResult.from_dict(data)  # type: ignore[arg-type]
