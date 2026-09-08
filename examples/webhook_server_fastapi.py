"""FastAPI app receiving and verifying adsefid.com webhooks.

Usage:
    pip install "adsefid[examples]"
    ADSEFID_WEBHOOK_SECRET=... uvicorn examples.webhook_server_fastapi:app --port 8080

The one thing to get right in an ASGI framework is the body. Signature
verification runs over the exact bytes the service signed, so read them with
`await request.body()` — never re-serialize a parsed model, and never declare a
Pydantic body parameter for this route, because the bytes FastAPI would hand
back are not guaranteed to be byte-identical to what arrived.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Request, Response, status

from adsefid import AdsefidWebhookVerificationError, verify_and_parse_webhook
from adsefid.webhooks import (
    MessengerStatusWebhookEvent,
    ReceiveWebhookEvent,
    StatusWebhookEvent,
    WebhookHeaders,
)

app = FastAPI()

# The secret is shown in your adsefid.com panel as Base64; pass it through
# verbatim and the SDK decodes it to the raw HMAC key.
WEBHOOK_SECRET = os.environ["ADSEFID_WEBHOOK_SECRET"]


@app.post("/webhooks/adsefid")
async def handle_webhook(request: Request) -> Response:
    try:
        event = verify_and_parse_webhook(
            raw_body=await request.body(),
            signature_header=request.headers[WebhookHeaders.SIGNATURE],
            timestamp_header=request.headers[WebhookHeaders.TIMESTAMP],
            secret=WEBHOOK_SECRET,
        )
    except KeyError:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
    except AdsefidWebhookVerificationError:
        # Say nothing about why: an attacker probing signatures learns nothing
        # from a bare 401.
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    # Use the delivery id as an idempotency key. The service retries with
    # backoff until it sees a 2xx, so the same event can arrive more than once.
    delivery_id = request.headers.get(WebhookHeaders.ID)
    print(f"delivery {delivery_id} attempt {event.attempt}: {event.type}")

    # Only the event types this endpoint is subscribed to (configured per
    # endpoint in your adsefid.com panel) ever arrive here.
    match event:
        case ReceiveWebhookEvent():
            for item in event.data:
                print(
                    f"  inbound SMS #{item.id} from {item.sender} "
                    f"on {item.line_number}: {item.message}"
                )
        case StatusWebhookEvent():
            for item in event.data:
                print(f"  SMS {item.id} (local_id={item.local_id}) -> {item.status_delivery}")
        case MessengerStatusWebhookEvent():
            for item in event.data:
                print(
                    f"  messenger message {item.id} (local_id={item.local_id}) "
                    f"-> {item.status_delivery}"
                )

    # Answer quickly and do the real work elsewhere: the service gives each
    # delivery 10 seconds before it counts as failed.
    return Response(status_code=status.HTTP_204_NO_CONTENT)
