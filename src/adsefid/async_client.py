from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from ._base import build_request_kwargs, parse_success_data, wrap_transport_error
from .config import DEFAULT_BASE_URL, DEFAULT_TIMEOUT_SECONDS, DEFAULT_USER_AGENT, ClientConfig
from .resources.messenger import AsyncMessengerResource
from .resources.sms import AsyncSmsResource
from .resources.user import AsyncUserResource


class AdsefidAsyncClient:
    """Asynchronous client for the adsefid.com SMS Web Service API.

    Exposes the API surface through three resources: `.sms`, `.messenger`, and
    `.user`. Supports the `async with` statement, which calls `aclose()` on exit.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Create a client.

        Args:
            api_key: Sent as the `X-API-KEY` header on every request.
            base_url: API origin; override only to target a non-production environment.
            timeout: Per-request timeout in seconds, passed to `httpx.AsyncClient`.
                Ignored if `http_client` is given.
            user_agent: Value sent in the `User-Agent` header. Defaults to
                `adsefid-python/<SDK_VERSION>`.
            http_client: A pre-configured `httpx.AsyncClient` to use instead of
                constructing one from `base_url`/`timeout`. When supplied, this SDK
                does not close it on `aclose()`/`__aexit__` — the caller owns its
                lifecycle.
        """
        self._config = ClientConfig(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            user_agent=user_agent,
        )
        self._http_client = http_client or httpx.AsyncClient(base_url=base_url, timeout=timeout)
        self._owns_http_client = http_client is None

        self.sms = AsyncSmsResource(self)
        self.messenger = AsyncMessengerResource(self)
        self.user = AsyncUserResource(self)

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        query_params: Mapping[str, str | int | None] | None = None,
        files: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Send a raw request against the API and return the parsed `data` payload.

        Used internally by the resource classes (`.sms`, `.messenger`, `.user`);
        exposed publicly so callers can reach an endpoint not yet wrapped by a
        resource method. Raises `AdsefidTransportError` on a network-level failure,
        or an `AdsefidApiError`/`AdsefidRateLimitError` subclass on a non-success
        response.
        """
        kwargs = build_request_kwargs(
            method=method,
            path=path,
            api_key=self._config.api_key,
            user_agent=self._config.user_agent,
            json_body=json_body,
            query_params=query_params,
            files=files,
        )
        try:
            response = await self._http_client.request(**kwargs)
        except httpx.TransportError as exc:
            raise wrap_transport_error(exc) from exc
        return parse_success_data(response.status_code, response.content)

    async def aclose(self) -> None:
        """Close the underlying `httpx.AsyncClient`, unless it was supplied by the caller."""
        if self._owns_http_client:
            await self._http_client.aclose()

    async def __aenter__(self) -> AdsefidAsyncClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
