# adsefid

[![CI](https://github.com/adsefid/sdk-python/actions/workflows/ci.yml/badge.svg)](https://github.com/adsefid/sdk-python/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/adsefid.svg)](https://pypi.org/project/adsefid/)

A Python client for the [adsefid.com](https://adsefid.com) SMS Web Service API. It sends SMS and
Messenger messages (single, bulk, P2P and template), checks delivery status, cancels unsent
messages, reads inbound SMS, looks up account data, and verifies signed webhooks. There is a sync
client and an async client with the same methods.

It needs Python 3.10 or later and [`httpx`](https://www.python-httpx.org/), its only dependency.
It is fully typed (`py.typed`) and verified against API documentation **v1.14.0**. Sibling SDKs
exist for .NET, Go, JavaScript and PHP with the same shape.

## Install

```bash
pip install adsefid
```

## Quickstart

```python
import os

from adsefid import AdsefidClient, LineSelector, SendSingleSmsRequest

with AdsefidClient(api_key=os.environ["ADSEFID_API_KEY"]) as client:
    result = client.sms.send_single(
        SendSingleSmsRequest(
            receptor="989120000000",
            line_number="983000",
            line_selector=LineSelector.BULK_SERVICE_SEND_BASED,
            message="Hello from adsefid",
        )
    )
    print(result.message_id, result.status)
```

The async client has the same surface with `await`:

```python
import asyncio
import os

from adsefid import AdsefidAsyncClient, LineSelector, SendSingleSmsRequest


async def main() -> None:
    async with AdsefidAsyncClient(api_key=os.environ["ADSEFID_API_KEY"]) as client:
        result = await client.sms.send_single(
            SendSingleSmsRequest(
                receptor="989120000000",
                line_number="983000",
                line_selector=LineSelector.BULK_SERVICE_SEND_BASED,
                message="Hello",
            )
        )
        print(result.message_id, result.status)


asyncio.run(main())
```

The SDK never reads environment variables. Pass the API key yourself. It goes out as the
`X-API-KEY` header on every request. Every request and response model is importable from the top
level `adsefid` package.

**Line selector.** An account can own several lines with the same number, each with its own
selector (see `client.user.get_lines()`). When it does, `line_selector` is required on every SMS
send; without it the service answers `LINE_NOT_FOUND`.

## Configuration

```python
client = AdsefidClient(
    api_key="...",
    base_url="https://api.adsefid.com",  # default; must be an absolute http(s) URL
    timeout=30.0,  # seconds; positive and finite
    user_agent="my-service/1.0.0",  # default: adsefid-python/<SDK_VERSION>
    http_client=httpx.Client(...),  # optional; you own its lifecycle
)
```

`ClientConfig` validation raises `AdsefidValidationError` for a blank key, a bad URL, a bad
timeout or a bad user agent. A client you pass in is never closed by the SDK.

To bound a single call, derive a client with its own timeout. It shares the connection pool, and
closing it never closes the shared `httpx` client:

```python
client.with_options(timeout=5).sms.send_single(request)
```

Money fields (`cost`, `total_cost`, `credit_left`) are `decimal.Decimal`, so you keep the exact
amount the service sent.

## Methods

| Resource | Methods | Endpoint |
|---|---|---|
| `client.sms` | `send_single`, `send_bulk`, `send_p2p`, `send_template` | `POST /v1/sms/{single,bulk,p2p,template}` |
| `client.sms` | `get_status(message_ids=, local_ids=)`, `cancel`, `get_received(line_number=, count=, since=)` | `GET /v1/sms/status`, `POST /v1/sms/cancel`, `GET /v1/sms/receive` |
| `client.messenger` | `send_single`, `send_bulk`, `send_p2p`, `send_template` | `POST /v1/messenger/{single,bulk,p2p,template}` |
| `client.messenger` | `upload_file(file, filename=, content_type=)` | `POST /v1/messenger/file` |
| `client.messenger` | `get_status(message_ids=, local_ids=)`, `cancel` | `GET /v1/messenger/status`, `POST /v1/messenger/cancel` |
| `client.user` | `get_info`, `get_lines`, `get_profiles`, `get_templates(state=, skip=, take=)` | `GET /v1/user/{info,lines,profiles,templates}` |

Request and response types are frozen dataclasses whose fields mirror the API's snake_case JSON.
Cancel accepts messages that are awaiting approval, queued or scheduled, with no refund, and at
most 2,000 distinct IDs across both lists. Status lookups are GET requests, so the URL caps them at about 200 IDs per call. The SDK raises a validation error past 8,000 URL characters instead of letting the gateway answer HTTP 414.

## Bulk and P2P: partial success is not an error

A bulk or P2P call returns normally even when some items are rejected. Each item has `raw_status`,
either a message status (1000 to 1999) or an error code (2000 and up). `status` is the typed
message status and `error_code` is the typed error code. Each is `None` for the other range or for
a code this SDK does not know yet:

```python
from adsefid import BulkReceptor, SendBulkSmsRequest

result = client.sms.send_bulk(
    SendBulkSmsRequest(
        receptors=[BulkReceptor(receptor="989120000000"), BulkReceptor(receptor="989130000000")],
        message="Hello",
        line_number="983000",
        line_selector=LineSelector.BULK_SERVICE_SEND_BASED,
    )
)
for item in result.receptors:
    if item.error_code is not None:
        print(item.receptor, "rejected:", item.error_code.name)
    else:
        print(item.receptor, "accepted as", item.message_id)
```

Item values reach the API unchanged, so valid items still go out. If every item is rejected, the
call raises `AdsefidApiError` with `details.items` listing each rejected index. Only request-level
fields are checked locally.

## Template parameters

A parameter the template declares as `number` can be sent as a number or a string. The service
substitutes a numeric string as written, so a string is the only way to keep exact digits. A
`Decimal` is sent as its exact decimal string:

```python
from decimal import Decimal

client.sms.send_template(
    SendTemplateSmsRequest(
        template_id="invoice_notice",
        parameters={
            "invoice": "001234",  # renders 001234, not 1234
            "amount": Decimal("1.50"),  # renders 1.50, not 1.5
            "count": 2,
            "rate": 19.99,  # a float, so rounding is possible
        },
        receptor="09120000000",
        line_number="983000",
        line_selector=LineSelector.BULK_SERVICE_SEND_BASED,
    )
)
```

## File upload

```python
uploaded = client.messenger.upload_file("./brochure.pdf", content_type="application/pdf")
print(uploaded.file_id)

with open("./brochure.pdf", "rb") as f:  # bytes and open files work too
    uploaded = client.messenger.upload_file(
        f, filename="brochure.pdf", content_type="application/pdf"
    )
```

`content_type` is required. Content is limited to 15 MiB inclusive (`MAX_MESSENGER_FILE_BYTES`).
A larger file raises `AdsefidValidationError` before any request is sent. The service also
enforces a MIME allowlist and answers `FILE_TOO_LARGE` (2047) if it still objects to the size.

## Errors

Every method raises on failure. All errors extend `AdsefidError`.

| Error | Meaning |
|---|---|
| `AdsefidValidationError` | A local check failed. No request was sent. |
| `AdsefidApiError` | The API returned an error envelope, or a non-2xx status without one. Has `code`, `name`, `http_status_code` and optional `details`. |
| `AdsefidRateLimitError` | Subclass of `AdsefidApiError`. Codes 2035 and 2036, or any HTTP 429. |
| `AdsefidTransportError` | Network failure, timeout, or a response that was not valid JSON or had a missing field. |
| `AdsefidWebhookVerificationError` | A webhook failed verification. |

```python
from adsefid import (
    AdsefidApiError,
    AdsefidRateLimitError,
    AdsefidTransportError,
    AdsefidValidationError,
)

try:
    result = client.sms.send_single(request)
except AdsefidValidationError as e:
    print("invalid request:", e)
except AdsefidRateLimitError as e:  # catch before AdsefidApiError
    print("rate limited:", e.name)
except AdsefidApiError as e:
    print("API error:", e.code, e.name, e.http_status_code, e.details)
except AdsefidTransportError as e:
    print("transport failure:", e)
```

`e.code` is a `WebServiceResponseCode` when known and a plain `int` otherwise. A non-2xx response
with no error envelope has code `-1` and name `UNKNOWN_ERROR`. A bare 429 has code 2036 and name
`RATE_LIMITED`. `details.errors` maps field names (or rejected cancel IDs) to field errors, and
`details.items` carries indexed bulk/P2P errors. The SDK sends each request once and never
retries. Pass an `httpx` client with a retrying transport if you want backoff.

## Enums and unknown values

`LineSelector`, `WebServiceMessageStatus`, `WebServiceResponseCode`, `TemplateState` and
`TemplateParameterType` live in `adsefid.enums` and the top-level package. A value the service
adds later never raises: an unknown line selector stays an `int`, an unknown template state or
parameter type stays a `str`, and an unknown status or error code is `None` next to its
`raw_status`.

## Webhooks

`verify_and_parse_webhook` checks the signature and timestamp, then returns a typed event. Give
it the exact raw request bytes. A body that a framework already parsed will not verify.

```python
import os

from flask import Flask, request

from adsefid import AdsefidWebhookVerificationError, verify_and_parse_webhook
from adsefid.webhooks import WebhookEventType, WebhookHeaders

app = Flask(__name__)


@app.post("/webhooks/adsefid")
def handle_webhook():
    try:
        event = verify_and_parse_webhook(
            raw_body=request.get_data(),  # raw bytes, not request.json
            signature_header=request.headers.get(WebhookHeaders.SIGNATURE, ""),
            timestamp_header=request.headers.get(WebhookHeaders.TIMESTAMP, ""),
            secret=os.environ["ADSEFID_WEBHOOK_SECRET"],
        )
    except AdsefidWebhookVerificationError:
        return "", 401  # do not say why

    match event.type:
        case WebhookEventType.RECEIVE:
            for item in event.data:
                print("SMS from", item.sender, item.message)
        case WebhookEventType.STATUS | WebhookEventType.MESSENGER_STATUS:
            for item in event.data:
                print("status", item.id, item.status_delivery)
    return {"ok": True}
```

The panel shows the signing secret Base64-encoded, and the service signs with the decoded bytes.
Pass the secret exactly as shown, or pass the decoded key as `bytes`. An empty secret or key is
always rejected. A stale timestamp (default 300 seconds, change it with `max_age_seconds`) or a bad
signature raises `AdsefidWebhookVerificationError`.

In an ASGI framework, read the body with `await request.body()`. See `examples/webhook_server.py`
(Flask) and `examples/webhook_server_fastapi.py` (FastAPI). Each endpoint only receives the event
types you subscribed it to in the panel. Deliveries can repeat, so key your handler on
`WebhookHeaders.ID` plus each item's id, and return a 2xx quickly.

## Using this SDK with coding agents

[AGENTS.md](AGENTS.md) holds the repository rules. These points prevent most wrong guesses:

- Pass the API key and webhook secret explicitly. The SDK reads no environment variables.
- Treat a bulk or P2P response as data, not an error. Check each item.
- Send exact numeric text (`"001234"`, `Decimal("1.50")`) as a string or `Decimal`.
- Give `verify_and_parse_webhook` raw bytes, never a re-serialized model.
- There are no retries and no automatic batching. Split large requests yourself.
- Catch `AdsefidRateLimitError` before `AdsefidApiError`, and branch on `e.code`.

## Examples and contributing

Runnable samples are in [`examples/`](examples): `account`, `quickstart`, `quickstart_async`,
`bulk_and_p2p`, `templates`, `status_and_cancel`, `messenger`, `webhook_server` and
`webhook_server_fastapi`. `account.py` sends nothing, so try it first.

```bash
pip install "adsefid[examples]"
export ADSEFID_API_KEY=...
export ADSEFID_LINE_NUMBER=983000
python examples/quickstart.py
```

To work on the SDK: `make deps` (uses `uv`), then `make lint`, `make test` and `make build`. See
[AGENTS.md](AGENTS.md).

## Versioning and license

Semantic Versioning, independent of the API documentation. SDK version **0.6.0**, verified
against API documentation **v1.14.0**. Releases use `v<version>` tags. See
[CHANGELOG.md](CHANGELOG.md). MIT licensed, see [LICENSE](LICENSE).
