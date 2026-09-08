from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from .._serialization import format_datetime, parse_datetime
from ..enums import WebServiceMessageStatus, parse_message_status

TemplateParameterValue = str | int | float | Decimal
"""A value bound to one named template parameter.

The API accepts a JSON string or a JSON number for any parameter. For a
parameter the template declares as ``number``, the service substitutes a
numeric *string* verbatim, so pass a string whenever the exact digits matter:
``"001234"`` keeps its leading zeros and ``"1.50"`` keeps its trailing zero,
where the numbers ``1234`` and ``1.5`` would not.

A `Decimal` is serialized as a numeric string for the same reason — that is the
only representation that survives the round trip exactly. Plain `int` and
`float` travel as JSON numbers.
"""


def serialize_template_parameters(
    parameters: dict[str, TemplateParameterValue],
) -> dict[str, str | int | float]:
    """Render a template parameter map into JSON-encodable values.

    `Decimal` becomes its exact decimal string rather than a lossy float.
    """
    return {
        name: str(value) if isinstance(value, Decimal) else value
        for name, value in parameters.items()
    }


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
