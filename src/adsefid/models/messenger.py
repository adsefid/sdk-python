from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .._serialization import format_datetime, parse_datetime
from ..enums import (
    ERROR_CODE_MIN,
    WebServiceMessageStatus,
    WebServiceResponseCode,
    parse_message_status,
    parse_response_code,
)
from .common import TemplateParameterValue, serialize_template_parameters

# --------------------------------------------------------------------------
# 5.1 POST /v1/messenger/single
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SendSingleMessengerRequest:
    message: str
    receptor: str
    profile: str
    hide: bool | None = None
    file_id: str | None = None
    send_time: datetime | None = None
    local_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "message": self.message,
            "receptor": self.receptor,
            "profile": self.profile,
        }
        if self.hide is not None:
            data["hide"] = self.hide
        if self.file_id is not None:
            data["file_id"] = self.file_id
        if self.send_time is not None:
            data["send_time"] = format_datetime(self.send_time)
        if self.local_id is not None:
            data["local_id"] = self.local_id
        return data


@dataclass(frozen=True, slots=True)
class SendSingleMessengerResult:
    group_id: str
    message_id: str
    status: WebServiceMessageStatus | None
    raw_status: int
    receptor: str
    local_id: str | None
    hide: bool
    cost: float
    send_time: datetime | None
    profile: str
    messenger: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SendSingleMessengerResult:
        status, raw_status = parse_message_status(data["status"])
        return cls(
            group_id=data["group_id"],
            message_id=data["message_id"],
            status=status,
            raw_status=raw_status,
            receptor=data["receptor"],
            local_id=data.get("local_id"),
            hide=data["hide"],
            cost=float(data["cost"]),
            send_time=parse_datetime(data.get("send_time")),
            profile=data["profile"],
            messenger=data["messenger"],
        )


# --------------------------------------------------------------------------
# 5.2 POST /v1/messenger/bulk
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MessengerBulkReceptor:
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
class SendBulkMessengerRequest:
    receptors: list[MessengerBulkReceptor]
    message: str
    profile: str
    send_time: datetime | None = None
    file_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "receptors": [r.to_dict() for r in self.receptors],
            "message": self.message,
            "profile": self.profile,
        }
        if self.send_time is not None:
            data["send_time"] = format_datetime(self.send_time)
        if self.file_id is not None:
            data["file_id"] = self.file_id
        return data


@dataclass(frozen=True, slots=True)
class MessengerBulkReceptorResult:
    message_id: str | None
    receptor: str
    local_id: str | None
    hide: bool
    status: WebServiceMessageStatus | None
    raw_status: int
    cost: float

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
    def from_dict(cls, data: dict[str, Any]) -> MessengerBulkReceptorResult:
        status, raw_status = parse_message_status(data["status"])
        return cls(
            message_id=data.get("message_id"),
            receptor=data["receptor"],
            local_id=data.get("local_id"),
            hide=data["hide"],
            status=status,
            raw_status=raw_status,
            cost=float(data["cost"]),
        )


@dataclass(frozen=True, slots=True)
class SendBulkMessengerResult:
    group_id: str
    receptors: list[MessengerBulkReceptorResult]
    message: str
    send_time: datetime | None
    total_count: int
    total_cost: float
    counts: dict[str, int]
    profile: str
    messenger: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SendBulkMessengerResult:
        return cls(
            group_id=data["group_id"],
            receptors=[MessengerBulkReceptorResult.from_dict(item) for item in data["receptors"]],
            message=data["message"],
            send_time=parse_datetime(data.get("send_time")),
            total_count=data["total_count"],
            total_cost=float(data["total_cost"]),
            counts=dict(data.get("counts", {})),
            profile=data["profile"],
            messenger=data["messenger"],
        )


# --------------------------------------------------------------------------
# 5.3 POST /v1/messenger/p2p
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MessengerP2pReceptor:
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
class SendP2pMessengerRequest:
    receptors: list[MessengerP2pReceptor]
    profile: str
    send_time: datetime | None = None
    file_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "receptors": [r.to_dict() for r in self.receptors],
            "profile": self.profile,
        }
        if self.send_time is not None:
            data["send_time"] = format_datetime(self.send_time)
        if self.file_id is not None:
            data["file_id"] = self.file_id
        return data


@dataclass(frozen=True, slots=True)
class MessengerP2pReceptorResult:
    message_id: str | None
    receptor: str
    message: str
    local_id: str | None
    hide: bool
    status: WebServiceMessageStatus | None
    raw_status: int
    cost: float

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
    def from_dict(cls, data: dict[str, Any]) -> MessengerP2pReceptorResult:
        status, raw_status = parse_message_status(data["status"])
        return cls(
            message_id=data.get("message_id"),
            receptor=data["receptor"],
            message=data["message"],
            local_id=data.get("local_id"),
            hide=data["hide"],
            status=status,
            raw_status=raw_status,
            cost=float(data["cost"]),
        )


@dataclass(frozen=True, slots=True)
class SendP2pMessengerResult:
    group_id: str
    receptors: list[MessengerP2pReceptorResult]
    send_time: datetime | None
    total_count: int
    total_cost: float
    counts: dict[str, int]
    profile: str
    messenger: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SendP2pMessengerResult:
        return cls(
            group_id=data["group_id"],
            receptors=[MessengerP2pReceptorResult.from_dict(item) for item in data["receptors"]],
            send_time=parse_datetime(data.get("send_time")),
            total_count=data["total_count"],
            total_cost=float(data["total_cost"]),
            counts=dict(data.get("counts", {})),
            profile=data["profile"],
            messenger=data["messenger"],
        )


# --------------------------------------------------------------------------
# 5.4 POST /v1/messenger/file
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UploadMessengerFileResult:
    file_id: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UploadMessengerFileResult:
        return cls(file_id=data["file_id"])


# --------------------------------------------------------------------------
# 5.5 POST /v1/messenger/cancel
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CancelMessengerRequest:
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
# 5.6 POST /v1/messenger/template
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SendTemplateMessengerRequest:
    template_id: str
    parameters: dict[str, TemplateParameterValue]
    receptor: str
    profile: str
    local_id: str | None = None
    expiry_date: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "template_id": self.template_id,
            "parameters": serialize_template_parameters(self.parameters),
            "receptor": self.receptor,
            "profile": self.profile,
        }
        if self.local_id is not None:
            data["local_id"] = self.local_id
        if self.expiry_date is not None:
            data["expiry_date"] = format_datetime(self.expiry_date)
        return data


@dataclass(frozen=True, slots=True)
class SendTemplateMessengerResult:
    group_id: str
    message_id: str
    status: WebServiceMessageStatus | None
    raw_status: int
    local_id: str | None
    template_id: str
    send_time: datetime | None
    expiry_date: datetime | None
    cost: float
    receptor: str
    message: str
    profile: str
    messenger: str
    parameters: dict[str, TemplateParameterValue]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SendTemplateMessengerResult:
        status, raw_status = parse_message_status(data["status"])
        return cls(
            group_id=data["group_id"],
            message_id=data["message_id"],
            status=status,
            raw_status=raw_status,
            local_id=data.get("local_id"),
            template_id=data["template_id"],
            send_time=parse_datetime(data.get("send_time")),
            expiry_date=parse_datetime(data.get("expiry_date")),
            cost=float(data["cost"]),
            receptor=data["receptor"],
            message=data["message"],
            profile=data["profile"],
            messenger=data["messenger"],
            parameters=dict(data.get("parameters", {})),
        )
