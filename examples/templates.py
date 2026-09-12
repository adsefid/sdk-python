"""Listing templates and sending one, with exact numeric parameter values.

A parameter the template declares as `number` may be sent either as a JSON
number or as a JSON string, and the service substitutes a numeric string
verbatim. That is the only way to keep a value's exact digits: "001234" keeps
its leading zeros and Decimal("1.50") its trailing zero, where the numbers 1234
and 1.5 would not.

Usage:
    ADSEFID_API_KEY=... ADSEFID_LINE_NUMBER=983000XXX python examples/templates.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from adsefid import (
    AdsefidClient,
    SendTemplateSmsRequest,
    TemplateParameterType,
    TemplateState,
    UserTemplate,
)
from adsefid.models.common import serialize_template_parameters


def show_value_choices() -> None:
    """Which representation to reach for, without sending anything."""
    choices: list[tuple[str, object]] = [
        ("an ordinary count", 2),
        ("a price where float rounding is fine", 19.99),
        ("an invoice number whose leading zeros matter", "001234"),
        ("an amount that must render as exactly 1.50", Decimal("1.50")),
    ]
    print("\nchoosing a parameter value:")
    for why, value in choices:
        wire = serialize_template_parameters({"v": value})["v"]  # type: ignore[dict-item]
        print(f"  {why:<48} -> {json.dumps(wire)}")


def pick_approved_template(client: AdsefidClient) -> UserTemplate:
    page = client.user.get_templates(state=TemplateState.APPROVED, take=100)
    if not page.items:
        print(
            "no approved templates on this account — create one in the adsefid.com panel first",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print(f"{page.total} approved template(s):")
    for item in page.items:
        print(f"  {item.template_id:<24} {len(item.parameters)} parameter(s)")
    return page.items[0]


def main() -> int:
    api_key = os.environ.get("ADSEFID_API_KEY")
    line_number = os.environ.get("ADSEFID_LINE_NUMBER")
    if not api_key or not line_number:
        print("set ADSEFID_API_KEY and ADSEFID_LINE_NUMBER", file=sys.stderr)
        return 1

    with AdsefidClient(api_key=api_key) as client:
        template = pick_approved_template(client)
        print(f"\nusing template {template.template_id!r}\n  content: {template.content}")

        # Build one value per declared parameter. A `number` parameter gets a
        # Decimal here so its exact form survives.
        parameters: dict[str, object] = {}
        for name, kind in template.parameters.items():
            print(f"  parameter {name:<14} {kind.value}")
            if kind is TemplateParameterType.STRING:
                parameters[name] = "Ali"
            else:
                parameters[name] = Decimal("1.50")

        result = client.sms.send_template(
            SendTemplateSmsRequest(
                template_id=template.template_id,
                parameters=parameters,  # type: ignore[arg-type]
                receptor="09120000000",
                line_number=line_number,
                expiry_date=datetime.now(timezone.utc) + timedelta(minutes=10),
            )
        )

        print(f"\nsent {result.message_id}: {result.status}")
        print(f"  rendered: {result.message}")
        print("  parameters echoed back:")
        for name, value in result.parameters.items():
            print(f"    {name:<14} {type(value).__name__:<6} {value!r}")

    show_value_choices()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
