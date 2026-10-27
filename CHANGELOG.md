# Changelog

## Unreleased

### Breaking
- Response models are named `*Response` instead of `*Result` (for example `SendSingleSmsResponse`,
  `CancelResponse`, `StatusResponse`); per-item types keep `*Result`. `P2p` is spelled `P2P`
  (`SendP2PSmsRequest`, `P2PMessage`).
- Monetary fields (`cost`, `total_cost`, `credit_left`) are `Decimal` instead of `float`.
- `LineSelector`, `TemplateState` and `TemplateParameterType` fields keep an unknown wire value as a
  raw `int`/`str`; an unrecognized template parameter type is no longer dropped.
- `AccountInfo.company_name`, `email` and `phone` are `str | None`.
- `content_type` is required by `upload_file`.
- `client.request()` is now private (`_request`).
- A non-2xx response without an error envelope raises `AdsefidApiError` with code `-1` and name
  `UNKNOWN_ERROR` (was the HTTP status and `HTTP_<status>`); a bare 429 has code `2036` and name
  `RATE_LIMITED`. Any 429 is an `AdsefidRateLimitError`.
- A 2xx body that is not a success envelope raises `AdsefidTransportError` (was `AdsefidApiError`).
- `base_url` must be an absolute http(s) URL and `timeout` positive and finite.

### Fixed
- Timestamps with 7 fractional digits, which the service sends, now parse on Python 3.10.
- Status lookups send ids joined by literal commas, and a GET whose path and query pass 8,000
  characters raises `AdsefidValidationError` instead of reaching the gateway's HTML 414.
- `verify_and_parse_webhook` rejects an empty key, and a non-ASCII or malformed signature raises
  `AdsefidWebhookVerificationError` instead of `TypeError`.
- A malformed model body raises `AdsefidTransportError` instead of `KeyError`/`ValueError`, and every
  `httpx.RequestError` is wrapped.

### Added
- `client.with_options(timeout=...)` on both clients.
- `MAX_MESSENGER_FILE_BYTES`; uploads above 15 MiB are rejected before sending.
- Python 3.14 in CI and classifiers; the Makefile runs through `uv`.
