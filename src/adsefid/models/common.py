from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .._serialization import format_datetime, parse_datetime
from ..enums import WebServiceMessageStatus, parse_message_status


@dataclass(frozen=True, slots=True)
class CancelledMessageItem:
    message_id: str
    local_id: str | None
    status: WebServiceMessageStatus | None
    raw_status: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "local_id": self.local_id,
            "status": self.raw_status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CancelledMessageItem:
        status, raw_status = parse_message_status(data["status"])
        return cls(
            message_id=data["message_id"],
            local_id=data.get("local_id"),
            status=status,
            raw_status=raw_status,
        )


@dataclass(frozen=True, slots=True)
class CancelResult:
    cancelled_messages: list[CancelledMessageItem]
    failed_to_cancel: list[CancelledMessageItem]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cancelled_messages": [item.to_dict() for item in self.cancelled_messages],
            "failed_to_cancel": [item.to_dict() for item in self.failed_to_cancel],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CancelResult:
        return cls(
            cancelled_messages=[
                CancelledMessageItem.from_dict(item) for item in data.get("cancelled_messages", [])
            ],
            failed_to_cancel=[
                CancelledMessageItem.from_dict(item) for item in data.get("failed_to_cancel", [])
            ],
        )


@dataclass(frozen=True, slots=True)
class StatusReceptor:
    message_id: str
    local_id: str | None
    status: WebServiceMessageStatus | None
    raw_status: int
    receptor: str
    send_time: datetime | None
    delivery_time: datetime | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "local_id": self.local_id,
            "status": self.raw_status,
            "receptor": self.receptor,
            "send_time": format_datetime(self.send_time),
            "delivery_time": format_datetime(self.delivery_time),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StatusReceptor:
        status, raw_status = parse_message_status(data["status"])
        return cls(
            message_id=data["message_id"],
            local_id=data.get("local_id"),
            status=status,
            raw_status=raw_status,
            receptor=data["receptor"],
            send_time=parse_datetime(data.get("send_time")),
            delivery_time=parse_datetime(data.get("delivery_time")),
        )


@dataclass(frozen=True, slots=True)
class StatusResult:
    receptors: list[StatusReceptor]

    def to_dict(self) -> dict[str, Any]:
        return {"receptors": [item.to_dict() for item in self.receptors]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StatusResult:
        return cls(receptors=[StatusReceptor.from_dict(item) for item in data.get("receptors", [])])
