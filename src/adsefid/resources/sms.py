from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING

from .._base import parse_object
from .._serialization import (
    MAX_CANCEL_IDS,
    SMS_MESSAGE_MAX_LENGTH,
    format_datetime,
    validate_ids_count,
    validate_local_id,
    validate_max_length,
    validate_non_empty,
    validate_receive_count,
)
from ..exceptions import AdsefidValidationError
from ..models.common import CancelResponse, StatusResponse
from ..models.sms import (
    CancelSmsRequest,
    GetReceivedSmsResponse,
    SendBulkSmsRequest,
    SendBulkSmsResponse,
    SendP2PSmsRequest,
    SendP2PSmsResponse,
    SendSingleSmsRequest,
    SendSingleSmsResponse,
    SendTemplateSmsRequest,
    SendTemplateSmsResponse,
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


def _validate_send_p2p(request: SendP2PSmsRequest) -> None:
    validate_non_empty(request.line_number, field_name="line_number")
    if not request.messages:
        raise AdsefidValidationError("'messages' must contain at least 1 item")


def _validate_send_template(request: SendTemplateSmsRequest) -> None:
    validate_non_empty(request.template_id, field_name="template_id")
    validate_non_empty(request.receptor, field_name="receptor")
    validate_non_empty(request.line_number, field_name="line_number")
    validate_local_id(request.local_id)


def _validate_cancel(request: CancelSmsRequest) -> None:
    validate_ids_count(request.message_ids, request.local_ids, max_total=MAX_CANCEL_IDS)


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

    def send_single(self, request: SendSingleSmsRequest) -> SendSingleSmsResponse:
        """Send one SMS to one receptor (`POST /v1/sms/single`).

        Raises AdsefidValidationError if `receptor`/`line_number`/`message` is empty,
        `message` exceeds `SMS_MESSAGE_MAX_LENGTH`, or `local_id` doesn't match the
        required shape.
        """
        _validate_send_single(request)
        data = self._client._request("POST", "/v1/sms/single", json_body=request.to_dict())
        return parse_object(SendSingleSmsResponse.from_dict, data)

    def send_bulk(self, request: SendBulkSmsRequest) -> SendBulkSmsResponse:
        """Send the same SMS body to many receptors (`POST /v1/sms/bulk`).

        A per-receptor delivery failure does not raise: it is reported as a normal
        typed result via each item's `status`/`raw_status` field. Raises
        AdsefidValidationError for empty `receptors` or empty/too-long request-level
        fields. Item errors are returned in the partial API response.
        """
        _validate_send_bulk(request)
        data = self._client._request("POST", "/v1/sms/bulk", json_body=request.to_dict())
        return parse_object(SendBulkSmsResponse.from_dict, data)

    def send_p2p(self, request: SendP2PSmsRequest) -> SendP2PSmsResponse:
        """Send a distinct message per receptor in one call (`POST /v1/sms/p2p`).

        Like `send_bulk`, a per-message delivery failure is a normal typed result,
        not an exception. Raises AdsefidValidationError for empty `messages` or
        `line_number`. Item errors are returned in the partial API response.
        """
        _validate_send_p2p(request)
        data = self._client._request("POST", "/v1/sms/p2p", json_body=request.to_dict())
        return parse_object(SendP2PSmsResponse.from_dict, data)

    def send_template(self, request: SendTemplateSmsRequest) -> SendTemplateSmsResponse:
        """Send a pre-approved template message (`POST /v1/sms/template`).

        Raises AdsefidValidationError if `template_id`/`receptor`/`line_number` is
        empty or `local_id` doesn't match the required shape.
        """
        _validate_send_template(request)
        data = self._client._request("POST", "/v1/sms/template", json_body=request.to_dict())
        return parse_object(SendTemplateSmsResponse.from_dict, data)

    def get_status(
        self,
        *,
        message_ids: Sequence[str] | None = None,
        local_ids: Sequence[str] | None = None,
    ) -> StatusResponse:
        """Look up delivery status for previously sent messages (`QUERY /v1/sms/status`).

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
        data = self._client._request("QUERY", "/v1/sms/status", json_body=params)
        return parse_object(StatusResponse.from_dict, data)

    def cancel(self, request: CancelSmsRequest) -> CancelResponse:
        """Cancel eligible SMS messages (`POST /v1/sms/cancel`).

        Raises AdsefidValidationError for empty IDs or over 2,000 distinct IDs combined.
        """
        _validate_cancel(request)
        data = self._client._request("POST", "/v1/sms/cancel", json_body=request.to_dict())
        return parse_object(CancelResponse.from_dict, data)

    def get_received(
        self,
        *,
        line_number: str,
        count: int | None = None,
        since: datetime | None = None,
    ) -> GetReceivedSmsResponse:
        """Fetch inbound SMS received on a line (`GET /v1/sms/receive`).

        Raises AdsefidValidationError if `line_number` is empty or `count` is not in
        `(0, MAX_RECEIVE_COUNT)`.
        """
        params = _receive_query_params(line_number, count, since)
        data = self._client._request("GET", "/v1/sms/receive", query_params=params)
        return parse_object(GetReceivedSmsResponse.from_dict, data)


class AsyncSmsResource:
    """Asynchronous SMS operations, available as `AdsefidAsyncClient(...).sms`.

    Same operations, validation, and error behavior as `SmsResource`; see its
    method docstrings for details.
    """

    def __init__(self, client: AdsefidAsyncClient) -> None:
        self._client = client

    async def send_single(self, request: SendSingleSmsRequest) -> SendSingleSmsResponse:
        _validate_send_single(request)
        data = await self._client._request("POST", "/v1/sms/single", json_body=request.to_dict())
        return parse_object(SendSingleSmsResponse.from_dict, data)

    async def send_bulk(self, request: SendBulkSmsRequest) -> SendBulkSmsResponse:
        _validate_send_bulk(request)
        data = await self._client._request("POST", "/v1/sms/bulk", json_body=request.to_dict())
        return parse_object(SendBulkSmsResponse.from_dict, data)

    async def send_p2p(self, request: SendP2PSmsRequest) -> SendP2PSmsResponse:
        _validate_send_p2p(request)
        data = await self._client._request("POST", "/v1/sms/p2p", json_body=request.to_dict())
        return parse_object(SendP2PSmsResponse.from_dict, data)

    async def send_template(self, request: SendTemplateSmsRequest) -> SendTemplateSmsResponse:
        _validate_send_template(request)
        data = await self._client._request("POST", "/v1/sms/template", json_body=request.to_dict())
        return parse_object(SendTemplateSmsResponse.from_dict, data)

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
        data = await self._client._request("QUERY", "/v1/sms/status", json_body=params)
        return parse_object(StatusResponse.from_dict, data)

    async def cancel(self, request: CancelSmsRequest) -> CancelResponse:
        _validate_cancel(request)
        data = await self._client._request("POST", "/v1/sms/cancel", json_body=request.to_dict())
        return parse_object(CancelResponse.from_dict, data)

    async def get_received(
        self,
        *,
        line_number: str,
        count: int | None = None,
        since: datetime | None = None,
    ) -> GetReceivedSmsResponse:
        params = _receive_query_params(line_number, count, since)
        data = await self._client._request("GET", "/v1/sms/receive", query_params=params)
        return parse_object(GetReceivedSmsResponse.from_dict, data)
