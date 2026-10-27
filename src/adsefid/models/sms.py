from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from .._serialization import format_datetime, parse_datetime, to_decimal
from ..enums import (
    ERROR_CODE_MIN,
    LineSelector,
    WebServiceMessageStatus,
    WebServiceResponseCode,
    coerce_enum,
    parse_message_status,
    parse_response_code,
)
from .common import TemplateParameterValue, serialize_template_parameters

# --------------------------------------------------------------------------
# 4.1 POST /v1/sms/single
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SendSingleSmsRequest:
    receptor: str
    line_number: str
    message: str
    line_selector: LineSelector | int | None = None
    send_time: datetime | None = None
    local_id: str | None = None
    hide: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "receptor": self.receptor,
            "line_number": self.line_number,
            "message": self.message,
        }
        if self.line_selector is not None:
            data["line_selector"] = int(self.line_selector)
        if self.send_time is not None:
            data["send_time"] = format_datetime(self.send_time)
        if self.local_id is not None:
            data["local_id"] = self.local_id
        if self.hide is not None:
            data["hide"] = self.hide
        return data


@dataclass(frozen=True, slots=True)
class SendSingleSmsResponse:
    group_id: str
    local_id: str | None
    status: WebServiceMessageStatus | None
    raw_status: int
    line_number: str
    line_selector: LineSelector | int
    cost: Decimal
    receptor: str
    send_time: datetime | None
    message_id: str
    segment_count: int
    hide: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SendSingleSmsResponse:
        status, raw_status = parse_message_status(data["status"])
        return cls(
            group_id=data["group_id"],
            local_id=data.get("local_id"),
            status=status,
            raw_status=raw_status,
            line_number=data["line_number"],
            line_selector=coerce_enum(LineSelector, data["line_selector"]),
            cost=to_decimal(data["cost"]),
            receptor=data["receptor"],
            send_time=parse_datetime(data.get("send_time")),
            message_id=data["message_id"],
            segment_count=data["segment_count"],
            hide=data["hide"],
        )


# --------------------------------------------------------------------------
# 4.2 POST /v1/sms/bulk
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BulkReceptor:
    receptor: str
    local_id: str | None = None
    hide: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"receptor": self.receptor}
        if self.local_id is not None:
            data["local_id"] = self.local_id
        if self.hide is not None:
            data["hide"] = self.hide
        return data


@dataclass(frozen=True, slots=True)
class SendBulkSmsRequest:
    receptors: list[BulkReceptor]
    message: str
    line_number: str
    line_selector: LineSelector | int | None = None
    send_time: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "receptors": [r.to_dict() for r in self.receptors],
            "message": self.message,
            "line_number": self.line_number,
        }
        if self.line_selector is not None:
            data["line_selector"] = int(self.line_selector)
        if self.send_time is not None:
            data["send_time"] = format_datetime(self.send_time)
        return data


@dataclass(frozen=True, slots=True)
class BulkReceptorResult:
    message_id: str | None
    receptor: str
    local_id: str | None
    status: WebServiceMessageStatus | None
    raw_status: int
    hide: bool
    cost: Decimal

    @property
    def error_code(self) -> WebServiceResponseCode | None:
        """The named error code when this one item was rejected (``raw_status`` >= 2000).

        ``None`` when the item was accepted (``status`` is then set) or when the
        service reported a code this SDK does not know yet.
        """
        if self.raw_status < ERROR_CODE_MIN:
            return None
        code, _ = parse_response_code(self.raw_status)
        return code

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BulkReceptorResult:
        status, raw_status = parse_message_status(data["status"])
        return cls(
            message_id=data.get("message_id"),
            receptor=data["receptor"],
            local_id=data.get("local_id"),
            status=status,
            raw_status=raw_status,
            hide=data["hide"],
            cost=to_decimal(data["cost"]),
        )


@dataclass(frozen=True, slots=True)
class SendBulkSmsResponse:
    group_id: str
    receptors: list[BulkReceptorResult]
    message: str
    segment_count: int
    send_time: datetime | None
    line_number: str
    line_selector: LineSelector | int
    counts: dict[str, int]
    total_count: int
    total_cost: Decimal

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SendBulkSmsResponse:
        return cls(
            group_id=data["group_id"],
            receptors=[BulkReceptorResult.from_dict(item) for item in data["receptors"]],
            message=data["message"],
            segment_count=data["segment_count"],
            send_time=parse_datetime(data.get("send_time")),
            line_number=data["line_number"],
            line_selector=coerce_enum(LineSelector, data["line_selector"]),
            counts=dict(data.get("counts", {})),
            total_count=data["total_count"],
            total_cost=to_decimal(data["total_cost"]),
        )


# --------------------------------------------------------------------------
# 4.3 POST /v1/sms/p2p
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class P2PMessage:
    receptor: str
    message: str
    local_id: str | None = None
    hide: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"receptor": self.receptor, "message": self.message}
        if self.local_id is not None:
            data["local_id"] = self.local_id
        if self.hide is not None:
            data["hide"] = self.hide
        return data


@dataclass(frozen=True, slots=True)
class SendP2PSmsRequest:
    messages: list[P2PMessage]
    line_number: str
    line_selector: LineSelector | int | None = None
    send_time: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "messages": [m.to_dict() for m in self.messages],
            "line_number": self.line_number,
        }
        if self.line_selector is not None:
            data["line_selector"] = int(self.line_selector)
        if self.send_time is not None:
            data["send_time"] = format_datetime(self.send_time)
        return data


@dataclass(frozen=True, slots=True)
class P2PMessageResult:
    message_id: str | None
    receptor: str
    status: WebServiceMessageStatus | None
    raw_status: int
    local_id: str | None
    message: str
    hide: bool
    segment_count: int
    cost: Decimal

    @property
    def error_code(self) -> WebServiceResponseCode | None:
        """The named error code when this one item was rejected (``raw_status`` >= 2000).

        ``None`` when the item was accepted (``status`` is then set) or when the
        service reported a code this SDK does not know yet.
        """
        if self.raw_status < ERROR_CODE_MIN:
            return None
        code, _ = parse_response_code(self.raw_status)
        return code

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> P2PMessageResult:
        status, raw_status = parse_message_status(data["status"])
        return cls(
            message_id=data.get("message_id"),
            receptor=data["receptor"],
            status=status,
            raw_status=raw_status,
            local_id=data.get("local_id"),
            message=data["message"],
            hide=data["hide"],
            segment_count=data["segment_count"],
            cost=to_decimal(data["cost"]),
        )


@dataclass(frozen=True, slots=True)
class SendP2PSmsResponse:
    group_id: str
    messages: list[P2PMessageResult]
    send_time: datetime | None
    line_number: str
    line_selector: LineSelector | int
    total_cost: Decimal
    counts: dict[str, int]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SendP2PSmsResponse:
        return cls(
            group_id=data["group_id"],
            messages=[P2PMessageResult.from_dict(item) for item in data["messages"]],
            send_time=parse_datetime(data.get("send_time")),
            line_number=data["line_number"],
            line_selector=coerce_enum(LineSelector, data["line_selector"]),
            total_cost=to_decimal(data["total_cost"]),
            counts=dict(data.get("counts", {})),
        )


# --------------------------------------------------------------------------
# 4.4 POST /v1/sms/template
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SendTemplateSmsRequest:
    template_id: str
    parameters: dict[str, TemplateParameterValue]
    receptor: str
    line_number: str
    local_id: str | None = None
    line_selector: LineSelector | int | None = None
    expiry_date: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "template_id": self.template_id,
            "parameters": serialize_template_parameters(self.parameters),
            "receptor": self.receptor,
            "line_number": self.line_number,
        }
        if self.local_id is not None:
            data["local_id"] = self.local_id
        if self.line_selector is not None:
            data["line_selector"] = int(self.line_selector)
        if self.expiry_date is not None:
            data["expiry_date"] = format_datetime(self.expiry_date)
        return data


@dataclass(frozen=True, slots=True)
class SendTemplateSmsResponse:
    group_id: str
    message_id: str
    status: WebServiceMessageStatus | None
    raw_status: int
    local_id: str | None
    line_number: str
    template_id: str
    send_time: datetime | None
    expiry_date: datetime | None
    line_selector: LineSelector | int
    cost: Decimal
    receptor: str
    message: str
    segment_count: int
    parameters: dict[str, TemplateParameterValue]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SendTemplateSmsResponse:
        status, raw_status = parse_message_status(data["status"])
        return cls(
            group_id=data["group_id"],
            message_id=data["message_id"],
            status=status,
            raw_status=raw_status,
            local_id=data.get("local_id"),
            line_number=data["line_number"],
            template_id=data["template_id"],
            send_time=parse_datetime(data.get("send_time")),
            expiry_date=parse_datetime(data.get("expiry_date")),
            line_selector=coerce_enum(LineSelector, data["line_selector"]),
            cost=to_decimal(data["cost"]),
            receptor=data["receptor"],
            message=data["message"],
            segment_count=data["segment_count"],
            parameters=dict(data.get("parameters", {})),
        )


# --------------------------------------------------------------------------
# 4.6 POST /v1/sms/cancel
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CancelSmsRequest:
    message_ids: list[str] = field(default_factory=list)
    local_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.message_ids:
            data["message_ids"] = list(self.message_ids)
        if self.local_ids:
            data["local_ids"] = list(self.local_ids)
        return data


# --------------------------------------------------------------------------
# 4.7 GET /v1/sms/receive
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReceivedSmsMessage:
    message: str
    line_number: str
    receive_date: datetime | None
    sender: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReceivedSmsMessage:
        return cls(
            message=data["message"],
            line_number=data["line_number"],
            receive_date=parse_datetime(data.get("receive_date")),
            sender=data["sender"],
        )


@dataclass(frozen=True, slots=True)
class GetReceivedSmsResponse:
    messages: list[ReceivedSmsMessage]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GetReceivedSmsResponse:
        return cls(
            messages=[ReceivedSmsMessage.from_dict(item) for item in data.get("messages", [])]
        )
