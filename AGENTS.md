# AGENTS.md — adsefid Python SDK

## Scope

This repository is the Python client SDK for the adsefid.com SMS Web Service API (package:
`adsefid`), independently versioned and published with its own `pyproject.toml`. Equivalent SDKs
exist for the same API in sibling repositories (`sdk-dotnet`, `sdk-js`, `sdk-php`, `sdk-go`); a
behavior change here should generally be considered for parity there.

## Source of truth

The API surface (endpoints, field names, types, validation rules, enums, example payloads,
webhook behavior) is defined by the published adsefid.com SMS Web Service API documentation.
This SDK is verified against doc version v1.12.0. Re-read the relevant documentation before
changing any endpoint, request/response model, or enum. The SDK follows independent Semantic
Versioning from `pyproject.toml`; never copy the API-document version into package metadata.
Record both versions in the README.

A small number of facts below are empirically observed behaviors of the live API that are easy
to get wrong from a literal reading of the documentation's prose or pseudo-code. Trust these
notes over an ambiguous doc reading:

- Webhook signatures are plain Base64, not hex-then-Base64. The signature is HMAC-SHA256 over
  the literal string `"{timestamp}.{raw_body}"`, and the raw digest bytes are Base64-encoded
  directly — there is no intermediate hex-encoding step, even though a literal reading of some
  spec pseudo-code can suggest one. See `src/adsefid/webhooks/verifier.py`.
- `TemplateParameterType` has an undocumented third value in the wild. The documented, supported
  public set is `{string, number}`. The live API has been observed to also emit a `url` value for
  some templates; this SDK intentionally models only the two documented values — do not add
  support for it without first confirming it against current, documented API behavior. See
  `src/adsefid/enums.py`.
- `error.details` shape varies per endpoint and is intentionally untyped. It may be a validation
  map, a bulk/P2P per-item list, a cancel-specific map, or absent entirely — never give it a
  strong type; decode it defensively per endpoint if you need it.

## Architecture map

```
src/adsefid/
├── __init__.py          public API re-exports
├── py.typed             PEP 561 marker — do not remove
├── client.py            AdsefidClient (sync, wraps httpx.Client)
├── async_client.py       AdsefidAsyncClient (async, wraps httpx.AsyncClient)
├── _base.py              shared request-building / envelope-parsing / error-raising (used by both clients)
├── config.py             ClientConfig
├── exceptions.py         full exception hierarchy
├── enums.py              LineSelector, WebServiceMessageStatus, WebServiceResponseCode, TemplateState, TemplateParameterType
├── _serialization.py     to_dict/from_dict helpers, ISO-8601 datetime parse/format, local_id regex + validators, CSV join
├── resources/
│   ├── sms.py            SmsResource (sync) + AsyncSmsResource (async) — 7 ops each
│   ├── messenger.py      MessengerResource + AsyncMessengerResource — 7 ops each (incl. upload_file)
│   └── user.py           UserResource + AsyncUserResource — 4 ops each
├── models/
│   ├── common.py         shared envelope/status/cancel dataclasses reused by sms + messenger
│   ├── sms.py            request/response dataclasses for the 7 SMS ops
│   ├── messenger.py       request/response dataclasses for the 7 messenger ops
│   └── user.py            request/response dataclasses for the 4 user ops
└── webhooks/
    ├── verifier.py        verify_and_parse_webhook
    ├── events.py          WebhookEvent union + 3 concrete dataclasses
    └── headers.py         WebhookHeaders/WebhookEventType constants — use instead of typing header/type strings
```

## Adding a new endpoint

1. Add the request/response `@dataclass(frozen=True, slots=True)` types to the right `models/<area>.py` (or `models/common.py` if the shape is shared across SMS and messenger, e.g. cancel/status). Hand-write `to_dict`/`from_dict` — no metaprogramming.
2. Add one sync method to the resource class in `resources/<area>.py`, and the structurally identical `async def` method to the `Async<Area>Resource` class in the same file. The two classes must stay parallel: same method names, same parameter order, same validation calls, same shape of return.
3. Any client-side pre-flight rule (max length, required field, `local_id` shape, count limits) goes in `_serialization.py` as a small named validator function and is called from the resource method *before* the request is built — never inline `if` checks scattered across resource methods. Note `validate_max_length` counts **UTF-16 code units**, matching the service; Python's `len()` counts code points and would accept an over-long message containing non-BMP characters.
4. Add rows to the request-building, response-parsing and validation tests for the new endpoint.
5. Re-export anything new that belongs in the public surface from `adsefid/__init__.py`.

## Hard rules

- **Every change ships with tests.** `tests/` uses pytest with `asyncio_mode = "auto"`. Endpoint
  tests are written once and run against both clients via the `make_client` fixture in
  `conftest.py`, which parametrizes over `flavor` (`sync`/`async`); `unwrap()` awaits when needed.
  Do not write a second copy of a test for the async twin — `tests/test_async_parity.py` guards the
  twin surfaces structurally instead.
- **Golden fixtures are shared across all five SDKs.** `tests/fixtures/` is byte-identical to the
  same tree in the sibling repositories. Never edit one in isolation: change it in all five and
  regenerate every `CHECKSUMS.txt`, or `tests/test_fixtures_integrity.py` fails.
- **No pydantic, no reflection-based validation/serialization.** Every dataclass hand-writes its own `to_dict`/`from_dict`. If two models share shape, factor the shared dataclass into `models/common.py` — don't reach for a validation library.
- **No magic string/int literals.** Any code value that appears in the doc's enum tables belongs in `enums.py`. Any other repeated constant (max lengths, limits, header names) is a named module-level constant, not a literal repeated at call sites.
- **Docstrings on the public API, minimal comments elsewhere.** Every public class/function (clients, resources, exceptions, enums, `verify_and_parse_webhook`) needs a PEP 257 docstring with real content — not a restatement of its name. Internal/private (`_`-prefixed) code stays uncommented except where a genuinely non-obvious constraint requires a note (e.g. the webhook digest-vs-hex behavior, the permissive-enum-parsing rationale). Don't narrate what the code obviously does.
- **Raise on error, always — never introduce a Result/Either type.** Every resource method either returns a typed success dataclass or raises from the `exceptions.py` hierarchy. Partial-success bulk/P2P responses are still normal typed returns (they're HTTP 200 successes with per-item status), not exceptions.
- **Keep sync and async clients/resources behaviorally identical.** Same validation, same error mapping, same defaults. If you touch one, touch the other in the same change.
- **No retry logic anywhere in this SDK.** Every request is a single attempt.
- **Template parameter values.** `TemplateParameterValue` lives once in `models/common.py` and is
  `str | int | float | Decimal`. A `number` parameter may legitimately travel as a JSON *string* —
  that is how leading zeros (`"001234"`) and exact decimals reach the service intact, since it
  substitutes a numeric string verbatim. `serialize_template_parameters` renders a `Decimal` as its
  exact decimal string for the same reason; don't "fix" that into a float.
- **The webhook secret is Base64.** A webhook endpoint's secret is 32 random bytes shown
  Base64-encoded in the panel, and the service signs with the **decoded** bytes.
  `verify_and_parse_webhook` decodes before keying the HMAC, and also accepts raw `bytes`. Keying
  the HMAC with the UTF-8 bytes of the Base64 string does not verify against the live service.
- `WebServiceMessageStatus` and `WebServiceResponseCode` are the two enums most likely to grow ahead of doc updates — they're parsed permissively (unknown int falls back to a raw int field rather than raising). Don't "fix" this into a hard `IntEnum(value)` call that would crash on a new server-side code.

## Commands

```bash
pip install -e ".[dev]"   # ruff + mypy + build + pytest
make lint                 # ruff check + ruff format --check + mypy
make fmt                  # ruff format .
make build                # python -m build (sdist + wheel)
make test                 # python -m pytest
```
