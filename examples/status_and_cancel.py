"""Delivery status, cancelling scheduled messages, and reading inbound SMS.

Status and cancel both accept message IDs (ours) and local IDs (yours) in one
call; their combined distinct count may not exceed 2000, which the SDK checks
before making the request.

Usage:
    ADSEFID_API_KEY=... ADSEFID_LINE_NUMBER=3000xxxx python examples/status_and_cancel.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

from adsefid import AdsefidClient, CancelSmsRequest, SendSingleSmsRequest


def main() -> int:
    api_key = os.environ.get("ADSEFID_API_KEY")
    line_number = os.environ.get("ADSEFID_LINE_NUMBER")
    if not api_key or not line_number:
        print("set ADSEFID_API_KEY and ADSEFID_LINE_NUMBER", file=sys.stderr)
        return 1

    with AdsefidClient(api_key=api_key) as client:
        # Schedule far enough ahead that there is something to cancel.
        send_at = datetime.now(timezone.utc) + timedelta(hours=2)
        sent = client.sms.send_single(
            SendSingleSmsRequest(
                receptor="09120000000",
                line_number=line_number,
                message="This one is scheduled, and about to be cancelled.",
                send_time=send_at,
                local_id="demo-cancel-1",
            )
        )
        print(f"scheduled {sent.message_id} for {send_at.isoformat()}")

        # Look it up by our ID and by your own local_id at the same time.
        status = client.sms.get_status(message_ids=[sent.message_id], local_ids=["demo-cancel-1"])
        print(f"\nstatus for {len(status.receptors)} message(s):")
        for item in status.receptors:
            delivered = item.delivery_time.isoformat() if item.delivery_time else "not yet"
            print(f"  {item.message_id} -> {item.status} (delivered: {delivered})")

        # Cancelling reports each message separately: one already sent cannot
        # be recalled and comes back under failed_to_cancel.
        cancelled = client.sms.cancel(CancelSmsRequest(message_ids=[sent.message_id]))
        print(
            f"\ncancelled {len(cancelled.cancelled_messages)}, "
            f"failed to cancel {len(cancelled.failed_to_cancel)}"
        )
        for item in cancelled.failed_to_cancel:
            print(f"  {item.message_id} could not be cancelled: {item.status}")

        # Inbound messages. count must be 1..499; since filters by arrival time.
        received = client.sms.get_received(
            line_number=line_number,
            count=50,
            since=datetime.now(timezone.utc) - timedelta(days=1),
        )
        print(f"\n{len(received.messages)} inbound message(s) in the last 24h:")
        for message in received.messages:
            print(
                f"  {message.line_number} from {message.sender} "
                f"at {message.receive_date.isoformat()}: {message.message}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
