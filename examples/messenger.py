"""The Messenger resource end to end: upload an attachment, send it, check status.

Messenger sends go through a "profile" configured in your adsefid.com panel
rather than an SMS line, and allow a longer body (4000 characters against SMS's
900). File upload is the only multipart endpoint in the API.

Usage:
    ADSEFID_API_KEY=... python examples/messenger.py
"""

from __future__ import annotations

import os
import sys

from adsefid import AdsefidClient, SendSingleMessengerRequest


def main() -> int:
    api_key = os.environ.get("ADSEFID_API_KEY")
    if not api_key:
        print("set ADSEFID_API_KEY", file=sys.stderr)
        return 1

    with AdsefidClient(api_key=api_key) as client:
        profiles = client.user.get_profiles()
        if not profiles:
            print(
                "no messenger profiles on this account — add one in the adsefid.com panel first",
                file=sys.stderr,
            )
            return 1

        print(f"{len(profiles)} messenger profile(s):")
        for profile in profiles:
            print(f"  {profile.id:<40} {profile.name:<20} {profile.messenger}")

        # upload_file takes a path, raw bytes, or an open binary file. A path or
        # file object is streamed rather than buffered whole.
        uploaded = client.messenger.upload_file(
            b"Statement for September 2026\nTotal: 1,250,000 IRR\n",
            filename="statement.txt",
            content_type="text/plain",
        )
        print(f"\nuploaded attachment as file_id {uploaded.file_id}")

        sent = client.messenger.send_single(
            SendSingleMessengerRequest(
                message="Your statement is attached.",
                receptor="09120000000",
                profile=profiles[0].id,
                file_id=uploaded.file_id,
                local_id="statement-2026-09",
            )
        )
        print(f"\nsent {sent.message_id} via {sent.messenger}: {sent.status} (cost {sent.cost})")

        status = client.messenger.get_status(message_ids=[sent.message_id])
        for item in status.receptors:
            print(f"  {item.message_id} -> {item.status}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
