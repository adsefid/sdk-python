from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .._serialization import parse_datetime
from ..enums import LineSelector, TemplateParameterType, TemplateState

# --------------------------------------------------------------------------
# 6.1 GET /v1/user/info
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AccountInfo:
    name: str
    company_name: str
    credit_left: int
    email: str
    phone: str
    account_status: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AccountInfo:
        return cls(
            name=data["name"],
            company_name=data["company_name"],
            credit_left=data["credit_left"],
            email=data["email"],
            phone=data["phone"],
            account_status=data["account_status"],
        )


# --------------------------------------------------------------------------
# 6.2 GET /v1/user/lines
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UserLine:
    line_number: str
    line_selector: LineSelector
    line_name: str
    enabled: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserLine:
        return cls(
            line_number=data["line_number"],
            line_selector=LineSelector(data["line_selector"]),
            line_name=data["line_name"],
            enabled=data["enabled"],
        )


# --------------------------------------------------------------------------
# 6.3 GET /v1/user/profiles
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UserProfile:
    id: str
    name: str
    messenger: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserProfile:
        return cls(id=data["id"], name=data["name"], messenger=data["messenger"])


# --------------------------------------------------------------------------
# 6.4 GET /v1/user/templates
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GetTemplatesRequest:
    state: TemplateState | None = None
    skip: int | None = None
    take: int | None = None

    def to_query_params(self) -> dict[str, str]:
        params: dict[str, str] = {}
        if self.state is not None:
            params["state"] = self.state.value
        if self.skip is not None:
            params["skip"] = str(self.skip)
        if self.take is not None:
            params["take"] = str(self.take)
        return params


@dataclass(frozen=True, slots=True)
class TemplateItem:
    template_id: str
    content: str
    parameters: dict[str, TemplateParameterType]
    state: TemplateState
    description: str | None
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TemplateItem:
        raw_parameters: dict[str, str] = data.get("parameters", {})
        parameters: dict[str, TemplateParameterType] = {}
        for key, value in raw_parameters.items():
            try:
                parameters[key] = TemplateParameterType(value)
            except ValueError:
                # Server has been observed to emit an undocumented "url" type;
                # skip strong-typing values outside the documented public set.
                continue
        return cls(
            template_id=data["template_id"],
            content=data["content"],
            parameters=parameters,
            state=TemplateState(data["state"]),
            description=data.get("description"),
            created_at=parse_datetime(data.get("created_at")),
            updated_at=parse_datetime(data.get("updated_at")),
        )


@dataclass(frozen=True, slots=True)
class GetTemplatesResult:
    items: list[TemplateItem]
    total: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GetTemplatesResult:
        return cls(
            items=[TemplateItem.from_dict(item) for item in data.get("items", [])],
            total=data["total"],
        )
