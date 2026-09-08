"""Minimal Flask app receiving and verifying adsefid.com webhooks.

Usage:
    ADSEFID_WEBHOOK_SECRET=... FLASK_APP=examples/webhook_server.py flask run
"""

from __future__ import annotations

import os

from flask import Flask, request

from adsefid import AdsefidWebhookVerificationError, verify_and_parse_webhook
from adsefid.webhooks import (
    MessengerStatusWebhookEvent,
    ReceiveWebhookEvent,
    StatusWebhookEvent,
    WebhookHeaders,
)

app = Flask(__name__)
WEBHOOK_SECRET = os.environ["ADSEFID_WEBHOOK_SECRET"]


@app.post("/webhooks/adsefid")
def handle_webhook():
    try:
        event = verify_and_parse_webhook(
            raw_body=request.get_data(),
            signature_header=request.headers[WebhookHeaders.SIGNATURE],
            timestamp_header=request.headers[WebhookHeaders.TIMESTAMP],
            secret=WEBHOOK_SECRET,
        )
    except AdsefidWebhookVerificationError:
        # Say nothing about why: an attacker probing signatures learns nothing
        # from a bare 401. See webhook_server_fastapi.py for the ASGI version.
        return "", 401

    # Only event types this webhook endpoint is subscribed to (in your adsefid.com panel) ever
    # arrive here — an endpoint subscribed to just "receive" never sees a StatusWebhookEvent.
    match event:
        case ReceiveWebhookEvent():
            for item in event.data:
                print(
                    f"inbound SMS #{item.id} from {item.sender} "
                    f"on {item.line_number}: {item.message}"
                )
        case StatusWebhookEvent():
            for item in event.data:
                print(f"SMS {item.id} (local_id={item.local_id}) -> {item.status_delivery}")
        case MessengerStatusWebhookEvent():
            for item in event.data:
                print(
                    f"messenger message {item.id} (local_id={item.local_id}) "
                    f"-> {item.status_delivery}"
                )

    return {"ok": True}, 200


if __name__ == "__main__":
    app.run()
