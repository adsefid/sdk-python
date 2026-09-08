"""A recording httpx.MockTransport and the client factories built on it."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from adsefid import AdsefidAsyncClient, AdsefidClient

BASE_URL = "https://api.test"
API_KEY = "test-api-key"


@dataclass
class Recorded:
    """One request as the mock transport saw it."""

    method: str
    url: httpx.URL
    headers: httpx.Headers
    content: bytes

    @property
    def path(self) -> str:
        return self.url.path

    @property
    def params(self) -> httpx.QueryParams:
        return self.url.params

    @property
    def json(self) -> Any:
        import json as _json

        return _json.loads(self.content)


@dataclass
class Recorder:
    """Collects every request that reached the transport."""

    requests: list[Recorded] = field(default_factory=list)

    @property
    def only(self) -> Recorded:
        assert len(self.requests) == 1, f"expected exactly 1 request, got {len(self.requests)}"
        return self.requests[0]


def mock_transport(
    *,
    status_code: int = 200,
    content: bytes = b"{}",
    raises: Exception | None = None,
) -> tuple[httpx.MockTransport, Recorder]:
    recorder = Recorder()

    def handler(request: httpx.Request) -> httpx.Response:
        recorder.requests.append(
            Recorded(
                method=request.method,
                url=request.url,
                headers=request.headers,
                content=request.content,
            )
        )
        if raises is not None:
            raise raises
        return httpx.Response(status_code, content=content)

    return httpx.MockTransport(handler), recorder


def sync_client(**kwargs: Any) -> tuple[AdsefidClient, Recorder]:
    transport, recorder = mock_transport(**kwargs)
    # base_url has to live on the mock client itself: when http_client is
    # supplied, AdsefidClient's own base_url/timeout arguments are ignored.
    http = httpx.Client(transport=transport, base_url=BASE_URL)
    return AdsefidClient(API_KEY, http_client=http), recorder


def async_client(**kwargs: Any) -> tuple[AdsefidAsyncClient, Recorder]:
    transport, recorder = mock_transport(**kwargs)
    http = httpx.AsyncClient(transport=transport, base_url=BASE_URL)
    return AdsefidAsyncClient(API_KEY, http_client=http), recorder
