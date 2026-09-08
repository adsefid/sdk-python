# adsefid

[![CI](https://github.com/adsefid/sdk-python/actions/workflows/ci.yml/badge.svg)](https://github.com/adsefid/sdk-python/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/adsefid.svg)](https://pypi.org/project/adsefid/)

Python client SDK for the [adsefid.com](https://adsefid.com) SMS Web Service API — SMS, Messenger (Rubika/Bale/etc.), and account/user endpoints, plus outgoing webhook signature verification.

## Requirements

- Python 3.10+
- [`httpx`](https://www.python-httpx.org/) (the only runtime dependency)

## Install

```bash
pip install adsefid
```

## Quickstart

### Sync

```python
import os

from adsefid import AdsefidClient
from adsefid.models.sms import SendSingleSmsRequest

client = AdsefidClient(api_key=os.environ["ADSEFID_API_KEY"])

result = client.sms.send_single(
    SendSingleSmsRequest(
        receptor="98912xxxxxxx",
        line_number="3000xxxx",
        message="Hello from adsefid",
    )
)
print(result.message_id, result.status)

client.close()
```

### Async

```python
import asyncio
import os

from adsefid import AdsefidAsyncClient
from adsefid.models.sms import SendSingleSmsRequest


async def main() -> None:
    async with AdsefidAsyncClient(api_key=os.environ["ADSEFID_API_KEY"]) as client:
        result = await client.sms.send_single(
            SendSingleSmsRequest(
                receptor="98912xxxxxxx",
                line_number="3000xxxx",
                message="Hello from adsefid",
            )
        )
        print(result.message_id, result.status)


asyncio.run(main())
```

`AdsefidClient` also supports the `with` statement (shown above via explicit `close()`); `AdsefidAsyncClient` supports `async with`.

## Authentication

The SDK never reads environment variables itself — pass the API key explicitly:

```python
import os
from adsefid import AdsefidClient

client = AdsefidClient(api_key=os.environ["ADSEFID_API_KEY"])
```

## Configuration

```python
from adsefid import AdsefidClient
import httpx

client = AdsefidClient(
    api_key="...",
    base_url="https://api.adsefid.com",  # override for a different environment
    timeout=30.0,  # seconds, passed to httpx
    user_agent="my-service/1.0.0",  # defaults to adsefid-python/<SDK_VERSION>
    http_client=httpx.Client(...),  # optional: inject your own configured httpx.Client
)
```

If you pass your own `http_client`/`AdsefidAsyncClient(http_client=...)`, the SDK will not close it for you when `.close()`/`.aclose()` is called — you own its lifecycle.

Monetary response fields (`cost`, `total_cost`, and `credit_left`) use `float` and may contain fractional values.

## Resource reference

| Resource | SDK method | HTTP endpoint | Notes |
|---|---|---|---|
| `client.sms` | `send_single(request)` | `POST /v1/sms/single` | |
| `client.sms` | `send_bulk(request)` | `POST /v1/sms/bulk` | Partial success is a normal typed return, not an exception |
| `client.sms` | `send_p2p(request)` | `POST /v1/sms/p2p` | Partial success is a normal typed return, not an exception |
| `client.sms` | `send_template(request)` | `POST /v1/sms/template` | |
| `client.sms` | `get_status(message_ids=..., local_ids=...)` | `GET /v1/sms/status` | |
| `client.sms` | `cancel(request)` | `POST /v1/sms/cancel` | |
| `client.sms` | `get_received(line_number=..., count=..., since=...)` | `GET /v1/sms/receive` | |
| `client.messenger` | `send_single(request)` | `POST /v1/messenger/single` | |
| `client.messenger` | `send_bulk(request)` | `POST /v1/messenger/bulk` | Partial success is a normal typed return, not an exception |
| `client.messenger` | `send_p2p(request)` | `POST /v1/messenger/p2p` | Partial success is a normal typed return, not an exception |
| `client.messenger` | `upload_file(file, filename=..., content_type=...)` | `POST /v1/messenger/file` | Accepts a path, bytes, or an open file object |
| `client.messenger` | `cancel(request)` | `POST /v1/messenger/cancel` | |
| `client.messenger` | `send_template(request)` | `POST /v1/messenger/template` | |
| `client.messenger` | `get_status(message_ids=..., local_ids=...)` | `GET /v1/messenger/status` | |
| `client.user` | `get_info()` | `GET /v1/user/info` | |
| `client.user` | `get_lines()` | `GET /v1/user/lines` | |
| `client.user` | `get_profiles()` | `GET /v1/user/profiles` | |
| `client.user` | `get_templates(state=..., skip=..., take=...)` | `GET /v1/user/templates` | |

`AdsefidAsyncClient` exposes the identical surface with `await`-able methods (`client.sms.send_single(...)`, etc.).

Every method takes/returns hand-written `@dataclass(frozen=True, slots=True)` request/response types from `adsefid.models.*` whose fields mirror the API's snake_case JSON exactly.

## Error handling

Every resource method **raises** on a non-success API response or a non-2xx HTTP status — it never returns a Result/Either type. Bulk and P2P responses with mixed per-item outcomes are still normal successful returns (HTTP 200, `status: "success"`); check each item's own `status`/`raw_status` field.

```python
from adsefid import AdsefidApiError, AdsefidRateLimitError, AdsefidValidationError

try:
    result = client.sms.send_single(request)
except AdsefidValidationError as e:
    # Failed a client-side pre-flight check (e.g. bad local_id, message too long) — no network call was made.
    print("invalid request:", e)
except AdsefidRateLimitError as e:
    # WebServiceResponseCode 2035 (MESSAGE_LIMIT_REACHED) or 2036 (REQUEST_LIMIT_REACHED),
    # or a bare HTTP 429 with an unparseable body.
    print("rate limited:", e.code, e.name)
except AdsefidApiError as e:
    print("API error:", e.code, e.name, e.http_status_code, e.details)
```

`details` is not one shape — the service picks one per endpoint:

| When | Shape | Example |
|---|---|---|
| Request validation (`2024 INVALID_PARAMETER`) | `{"errors": {field: message}}` — snake_case field paths, **string** values | `{"errors":{"take":"invalid value for take"}}` |
| Single send | `{field: message}` — flat, no wrapper | `{"receptor":"invalid value for receptor"}` |
| Bulk / P2P | `{"errors": {...}, "messages": [{"index": n, "errors": {...}}]}` — `index` is the position in *your* array, so gaps are normal | `{"errors":{},"messages":[{"index":2,"errors":{"local_id":"invalid value for local_id"}}]}` |
| Cancel | `{field: [value, ...]}` — the one shape whose values are **arrays** | `{"local_ids":["order-10001"]}` |
| Anything else | absent or `null` | |

Decode it defensively for the endpoint you called rather than assuming a single shape.

### Rate limits

The default sending limit is 500 units/second shared across SMS and Messenger traffic (SMS counts by segment). Codes `2035`, `2036`, and bare HTTP `429` responses surface as `AdsefidRateLimitError`.

## Enums

All enums live in `adsefid.enums` and are exported from the top-level package:

- `LineSelector` (`IntEnum`, 0-5) — see doc §3.1
- `WebServiceMessageStatus` (`IntEnum`, 1000-1999) — see doc §3.2. Parsed **permissively**: response dataclasses expose both a `status: WebServiceMessageStatus | None` field and a `raw_status: int` field, so an unrecognized future status code never crashes parsing.
- `WebServiceResponseCode` (`IntEnum`, 2000-2045) — see doc §3.4. `AdsefidApiError.code` is the enum member when recognized, otherwise the raw `int`.
- `TemplateState` (`str, Enum`: `pendingapproval` / `approved` / `rejected`) — see doc §3.5
- `TemplateParameterType` (`str, Enum`: `string` / `number`) — see doc §3.6. This is the doc's complete *documented* public set; the live server has been observed to also emit an undocumented `url` value which is intentionally not exposed here (such a parameter is dropped from `UserTemplate.parameters` rather than surfaced as a value you cannot match on).

## Template parameters, leading zeros and decimals

`TemplateParameterValue` is `str | int | float | Decimal`. A parameter the template declares as
`number` may be sent **either** as a JSON number or as a JSON string, and the platform substitutes
a numeric string verbatim — so a string is the only way to keep a value's exact digits:

```python
from decimal import Decimal

client.sms.send_template(
    SendTemplateSmsRequest(
        template_id="invoice_notice",
        parameters={
            "invoice": "001234",  # renders as 001234, not 1234
            "amount": Decimal("1.50"),  # renders as 1.50, not 1.5
            "count": 2,  # an ordinary integer
            "rate": 19.99,  # a float, where rounding is acceptable
        },
        receptor="09120000000",
        line_number="3000xxxx",
    )
)
```

A `Decimal` is serialized as its exact decimal string for exactly this reason; plain `int` and
`float` travel as JSON numbers. Reach for a `str` or a `Decimal` whenever the rendered text must
match the digits you supplied — invoice and account numbers, zero-padded codes, and money amounts
with a fixed number of decimal places.

Free-form server strings with no complete documented enum (`messenger`, e.g. `"rubika"`/`"bale"`; `account_status`, e.g. `"active"`) are plain `str` fields, not enums.

## File upload example

```python
from adsefid.resources.messenger import MessengerResource  # via client.messenger

file_result = client.messenger.upload_file("./brochure.pdf", content_type="application/pdf")
print(file_result.file_id)

# Also accepts raw bytes or an already-open binary file object:
with open("./brochure.pdf", "rb") as f:
    file_result = client.messenger.upload_file(
        f, filename="brochure.pdf", content_type="application/pdf"
    )
```

## Webhook verification

The platform signs outgoing webhooks as `X-Atlas-Webhook-Signature: v1=<base64_hmac_sha256>` over `f"{timestamp}.{raw_body}"`, keyed with your per-endpoint webhook secret. Always verify on the **raw** request body bytes, before any JSON parsing your framework might have already done.

```python
from flask import Flask, request

from adsefid import AdsefidWebhookVerificationError, verify_and_parse_webhook
from adsefid.webhooks import WebhookEventType, WebhookHeaders

app = Flask(__name__)
WEBHOOK_SECRET = os.environ["ADSEFID_WEBHOOK_SECRET"]


@app.post("/webhooks/adsefid")
def handle_webhook():
    try:
        event = verify_and_parse_webhook(
            raw_body=request.get_data(),  # raw bytes, not request.json
            signature_header=request.headers[WebhookHeaders.SIGNATURE],
            timestamp_header=request.headers[WebhookHeaders.TIMESTAMP],
            secret=WEBHOOK_SECRET,
        )
    except AdsefidWebhookVerificationError:
        # Say nothing about why: an attacker probing signatures learns nothing
        # from a bare 401.
        return "", 401

    # Only event types this webhook endpoint is subscribed to (in your adsefid.com panel) ever
    # arrive here — an endpoint subscribed to just "receive" never sees a "status" event.
    match event.type:
        case WebhookEventType.RECEIVE:
            for item in event.data:
                print("inbound SMS from", item.sender, ":", item.message)
        case WebhookEventType.STATUS:
            for item in event.data:
                print("SMS", item.id, "->", item.status_delivery)
        case WebhookEventType.MESSENGER_STATUS:
            for item in event.data:
                print("messenger message", item.id, "->", item.status_delivery)

    return {"ok": True}, 200
```

`WebhookHeaders` exposes every header name as a constant so you never have to type
`"X-Atlas-Webhook-Signature"` yourself; `WebhookEventType` does the same for the `type` values.

### The signing secret is Base64

Your endpoint's signing secret is shown in the adsefid.com panel as the Base64 encoding of 32
random bytes, and the platform signs with **those raw bytes** — not with the text of the Base64
string. Pass the secret exactly as the panel shows it and `verify_and_parse_webhook` decodes it for
you; a secret that is not valid Base64 raises `AdsefidWebhookVerificationError`. If you already
hold the decoded key, pass it as `bytes` instead.

See [`examples/webhook_server.py`](examples/webhook_server.py) for a Flask receiver and
[`examples/webhook_server_fastapi.py`](examples/webhook_server_fastapi.py) for a FastAPI one. In an
ASGI framework, read the body with `await request.body()` — verification runs over the exact bytes
that were signed, so never re-serialize a parsed model.

Return a `2xx` quickly and process asynchronously where possible — the platform treats any `2xx` as delivered and otherwise retries with backoff (`5s, 60s, 120s, 360s, 600s, 900s`) until it gives up. Handlers should be idempotent using `WebhookHeaders.ID` plus each event item's own id.

## Versioning

This SDK follows Semantic Versioning independently of the API documentation.

- SDK version: **`0.3.0`** (`version` in `pyproject.toml`; `adsefid.__version__` reads package metadata)
- Verified API documentation: **`v1.12.0`**

SDK releases use `v<SDK_VERSION>` tags. The two version numbers move independently.

## Development

```bash
make deps    # pip install -e ".[dev]" (ruff, mypy, build, pytest)
make fmt     # ruff format .
make lint    # ruff check . && ruff format --check . && mypy src/adsefid
make build   # python -m build
make test    # python -m pytest
```

The suite runs every endpoint test against both `AdsefidClient` and `AdsefidAsyncClient` from a
single test body, so pytest reports each one twice (`[sync]` / `[async]`). Golden fixtures under
`tests/fixtures/` are byte-identical to the same tree in the sibling SDK repositories, and
`tests/test_fixtures_integrity.py` verifies them against `CHECKSUMS.txt`.

### Examples

```bash
pip install -e ".[examples]"
export ADSEFID_API_KEY=...
export ADSEFID_LINE_NUMBER=3000xxxx

python examples/account.py             # account info, lines, profiles, templates; client config
python examples/quickstart.py          # send one SMS, with full error triage
python examples/quickstart_async.py    # the same, on the async client
python examples/bulk_and_p2p.py        # bulk + P2P sends, and reading a partial success
python examples/templates.py           # list templates and send one, incl. exact numeric values
python examples/status_and_cancel.py   # delivery status, cancelling, inbound messages
python examples/messenger.py           # upload an attachment and send it via a messenger profile

ADSEFID_WEBHOOK_SECRET=... flask --app examples/webhook_server.py run --port 8080
ADSEFID_WEBHOOK_SECRET=... uvicorn examples.webhook_server_fastapi:app --port 8080
```

`examples/account.py` sends nothing, so it is the safest one to try first.

## License

MIT — see [LICENSE](LICENSE).
