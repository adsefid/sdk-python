"""Account endpoints, plus configuring the client beyond the defaults.

Nothing here sends a message, so it is the safest example to run first against
a real API key.

Usage:
    ADSEFID_API_KEY=... python examples/account.py
"""

from __future__ import annotations

import os
import sys

import httpx

from adsefid import AdsefidClient


def main() -> int:
    api_key = os.environ.get("ADSEFID_API_KEY")
    if not api_key:
        print("set ADSEFID_API_KEY", file=sys.stderr)
        return 1

    # The SDK never retries a request. If you want retries, connection pooling,
    # tracing or a proxy, hand over your own httpx.Client — the SDK then leaves
    # its lifecycle to you and ignores its own base_url/timeout arguments, so
    # configure both on the client you pass in.
    http_client = httpx.Client(
        base_url=os.environ.get("ADSEFID_BASE_URL", "https://api.adsefid.com"),
        timeout=httpx.Timeout(20.0, connect=5.0),
        limits=httpx.Limits(max_keepalive_connections=10),
        transport=httpx.HTTPTransport(retries=0),
    )

    with (
        http_client,
        AdsefidClient(
            api_key=api_key,
            http_client=http_client,
            # Identify your own application; the SDK's default is
            # "adsefid-python/<version>".
            user_agent="my-billing-service/1.4 (+https://example.com)",
        ) as client,
    ):
        info = client.user.get_info()
        print(f"account {info.name} ({info.account_status})")
        print(f"  credit left: {info.credit_left}")
        if info.email:
            print(f"  email: {info.email}")

        lines = client.user.get_lines()
        print(f"\n{len(lines)} SMS line(s):")
        for line in lines:
            state = "enabled" if line.enabled else "disabled"
            print(
                f"  {line.line_number:<14} {line.line_name:<24} {state:<9} "
                f"default selector: {line.line_selector.name}"
            )

        profiles = client.user.get_profiles()
        print(f"\n{len(profiles)} messenger profile(s):")
        for profile in profiles:
            print(f"  {profile.id:<40} {profile.name:<20} {profile.messenger}")

        # Templates are paged; take is capped at 100.
        page = client.user.get_templates(skip=0, take=100)
        print(f"\n{page.total} template(s) (showing {len(page.items)}):")
        for item in page.items:
            print(
                f"  {item.template_id:<24} {item.state.value:<16} "
                f"{len(item.parameters)} parameter(s)"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
