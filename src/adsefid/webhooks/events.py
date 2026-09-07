from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from .._serialization import parse_datetime
from ..enums import WebServiceMessageStatus, parse_message_status


def _parse_required_datetime(value: Any) -> datetime:
    if not isinstance(value, str):
        raise TypeError("required datetime field must be a string")
    parsed = parse_datetime(value)
    if parsed is None:
        raise ValueError("required datetime field is missing")
    return parsed


@dataclass(frozen=True, slots=True)
class ReceiveWebhookItem:
    id: int
    line_number: str
    sender: str
    message: str
    receive_date: datetime | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReceiveWebhookItem:
        return cls(
            id=data["id"],
            line_number=data["line_number"],
            sender=data["sender"],
            message=data["message"],
            receive_date=parse_datetime(data.get("receive_date")),
        )


@dataclass(frozen=True, slots=True)
class ReceiveWebhookEvent:
    id: str
    type: Literal["receive"]
    occurred_at: datetime
    attempt: int
    version: str
    data: list[ReceiveWebhookItem]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ReceiveWebhookEvent:
        return cls(
            id=payload["id"],
            type="receive",
            occurred_at=_parse_required_datetime(payload["occurred_at"]),
            attempt=payload["attempt"],
            version=payload["version"],
            data=[ReceiveWebhookItem.from_dict(item) for item in payload["data"]],
        )


@dataclass(frozen=True, slots=True)
class StatusWebhookItem:
    id: str
    local_id: str | None
    status_delivery: WebServiceMessageStatus | None
    raw_status_delivery: int
    delivery_time: datetime | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StatusWebhookItem:
        status_delivery, raw_status_delivery = parse_message_status(data["status_delivery"])
        return cls(
            id=data["id"],
            local_id=data.get("local_id"),
            status_delivery=status_delivery,
            raw_status_delivery=raw_status_delivery,
            delivery_time=parse_datetime(data.get("delivery_time")),
        )


@dataclass(frozen=True, slots=True)
class StatusWebhookEvent:
    id: str
    type: Literal["status"]
    occurred_at: datetime
    attempt: int
    version: str
    data: list[StatusWebhookItem]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> StatusWebhookEvent:
        return cls(
            id=payload["id"],
            type="status",
            occurred_at=_parse_required_datetime(payload["occurred_at"]),
            attempt=payload["attempt"],
            version=payload["version"],
            data=[StatusWebhookItem.from_dict(item) for item in payload["data"]],
        )


@dataclass(frozen=True, slots=True)
class MessengerStatusWebhookEvent:
    id: str
    type: Literal["messenger.status"]
    occurred_at: datetime
    attempt: int
    version: str
    data: list[StatusWebhookItem]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> MessengerStatusWebhookEvent:
        return cls(
            id=payload["id"],
            type="messenger.status",
            occurred_at=_parse_required_datetime(payload["occurred_at"]),
            attempt=payload["attempt"],
            version=payload["version"],
            data=[StatusWebhookItem.from_dict(item) for item in payload["data"]],
        )


WebhookEvent = ReceiveWebhookEvent | StatusWebhookEvent | MessengerStatusWebhookEvent
