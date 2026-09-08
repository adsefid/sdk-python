"""Bulk and P2P SMS sends, and how to read a partial success.

Both endpoints answer HTTP 200 even when some receptors failed, so a call that
did not raise still needs its per-item results inspected. `raw_status` is the
number the service sent: below 2000 it is a delivery status, 2000 and above it
is an error code explaining why that one receptor was rejected.

Usage:
    ADSEFID_API_KEY=... ADSEFID_LINE_NUMBER=3000xxxx python examples/bulk_and_p2p.py
"""

from __future__ import annotations

import os
import sys

from adsefid import (
    AdsefidApiError,
    AdsefidClient,
    WebServiceMessageStatus,
    WebServiceResponseCode,
)
from adsefid.models.sms import (
    BulkReceptor,
    P2pMessage,
    SendBulkSmsRequest,
    SendP2pSmsRequest,
)


def describe(receptor: str, local_id: str | None, raw_status: int, message_id: str | None) -> str:
    label = local_id or "-"
    if raw_status >= 2000:
        try:
            reason = WebServiceResponseCode(raw_status).name
        except ValueError:
            reason = "UNKNOWN"
        return f"  {receptor:<14} ({label}) FAILED {raw_status} {reason}"

    try:
        state = WebServiceMessageStatus(raw_status).name
    except ValueError:
        state = str(raw_status)
    return f"  {receptor:<14} ({label}) accepted as {message_id}: {state}"


def main() -> int:
    api_key = os.environ.get("ADSEFID_API_KEY")
    line_number = os.environ.get("ADSEFID_LINE_NUMBER")
    if not api_key or not line_number:
        print("set ADSEFID_API_KEY and ADSEFID_LINE_NUMBER", file=sys.stderr)
        return 1

    with AdsefidClient(api_key=api_key) as client:
        try:
            # One identical message to many receptors. local_id is your own
            # handle: it comes back here and on the status webhook, so you can
            # match a delivery report to your record without storing our IDs.
            bulk = client.sms.send_bulk(
                SendBulkSmsRequest(
                    line_number=line_number,
                    message="Scheduled maintenance tonight from 01:00 to 03:00.",
                    receptors=[
                        BulkReceptor(receptor="09120000000", local_id="maint-1"),
                        BulkReceptor(receptor="09120000001", local_id="maint-2"),
                    ],
                )
            )
        except AdsefidApiError as exc:
            print(f"bulk send failed outright: {exc.name} ({exc.code})", file=sys.stderr)
            return 1

        print(f"\nbulk group {bulk.group_id}: {bulk.total_count} receptors, cost {bulk.total_cost}")
        for item in bulk.receptors:
            print(describe(item.receptor, item.local_id, item.raw_status, item.message_id))
        print(f"  status histogram: {bulk.counts}")

        # A different message per receptor, in one request.
        p2p = client.sms.send_p2p(
            SendP2pSmsRequest(
                line_number=line_number,
                messages=[
                    P2pMessage(
                        receptor="09120000000",
                        message="Hi Ali, your order #1001 shipped.",
                        local_id="ship-1001",
                    ),
                    P2pMessage(
                        receptor="09120000001",
                        message="Hi Reza, your order #1002 shipped.",
                        local_id="ship-1002",
                    ),
                ],
            )
        )

        print(f"\np2p group {p2p.group_id}: cost {p2p.total_cost}")
        for message in p2p.messages:
            print(
                describe(message.receptor, message.local_id, message.raw_status, message.message_id)
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
