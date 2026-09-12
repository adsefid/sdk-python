from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..enums import WebServiceResponseCode, parse_response_code


@dataclass(frozen=True, slots=True)
class ApiFieldError:
    """One field-level API error in an error envelope."""

    code: WebServiceResponseCode | int
    name: str

    def to_dict(self) -> dict[str, Any]:
        return {"code": int(self.code), "name": self.name}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApiFieldError:
        raw_code = data.get("code")
        raw_code = raw_code if isinstance(raw_code, int) else 0
        code, _ = parse_response_code(raw_code)
        return cls(code=code if code is not None else raw_code, name=str(data.get("name", "")))


@dataclass(frozen=True, slots=True)
class ApiItemError:
    """Errors for one rejected item in a bulk or P2P request."""

    index: int
    errors: dict[str, ApiFieldError]

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "errors": {field: error.to_dict() for field, error in self.errors.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApiItemError:
        raw_errors = data.get("errors")
        errors = (
            {
                field: ApiFieldError.from_dict(error)
                for field, error in raw_errors.items()
                if isinstance(field, str) and isinstance(error, dict)
            }
            if isinstance(raw_errors, dict)
            else {}
        )
        index = data.get("index")
        return cls(index=index if isinstance(index, int) else 0, errors=errors)


@dataclass(frozen=True, slots=True)
class ApiErrorDetails:
    """Structured ``error.details``, shared by all endpoint families."""

    errors: dict[str, ApiFieldError] | None = None
    items: list[ApiItemError] | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.errors is not None:
            data["errors"] = {field: error.to_dict() for field, error in self.errors.items()}
        if self.items is not None:
            data["items"] = [item.to_dict() for item in self.items]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApiErrorDetails:
        raw_errors = data.get("errors")
        errors = (
            {
                field: ApiFieldError.from_dict(error)
                for field, error in raw_errors.items()
                if isinstance(field, str) and isinstance(error, dict)
            }
            if isinstance(raw_errors, dict)
            else None
        )
        raw_items = data.get("items")
        items = (
            [ApiItemError.from_dict(item) for item in raw_items if isinstance(item, dict)]
            if isinstance(raw_items, list)
            else None
        )
        return cls(errors=errors, items=items)
