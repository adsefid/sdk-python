from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

import httpx

from ._base import QueryValue, build_request_kwargs, parse_success_data, wrap_transport_error
from .config import DEFAULT_BASE_URL, DEFAULT_TIMEOUT_SECONDS, DEFAULT_USER_AGENT, ClientConfig
from .resources.messenger import MessengerResource
from .resources.sms import SmsResource
from .resources.user import UserResource


class AdsefidClient:
    """Synchronous client for the adsefid.com SMS Web Service API.

    Exposes the API surface through three resources: `.sms`, `.messenger`, and
    `.user`. Supports the `with` statement, which calls `close()` on exit.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
        http_client: httpx.Client | None = None,
    ) -> None:
        """Create a client.

        Args:
            api_key: Sent as the `X-API-KEY` header on every request.
            base_url: API origin, an absolute http(s) URL; override only to target a
                non-production environment.
            timeout: Per-request timeout in seconds, a positive finite number,
                passed to `httpx.Client`. Ignored if `http_client` is given.
            user_agent: Value sent in the `User-Agent` header. Defaults to
                `adsefid-python/<SDK_VERSION>`.
            http_client: A pre-configured `httpx.Client` to use instead of constructing
                one from `timeout`. Requests always carry the absolute URL built from
                `base_url`, so the supplied client needs no `base_url` of its own. When
                supplied, this SDK does not close it on `close()`/`__exit__` — the
                caller owns its lifecycle.
        """
        self._config = ClientConfig(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            user_agent=user_agent,
        )
        self._http_client = http_client or httpx.Client(timeout=timeout)
        self._owns_http_client = http_client is None
        self._request_timeout: float | None = None
        self._bind_resources()

    def _bind_resources(self) -> None:
        self.sms = SmsResource(self)
        self.messenger = MessengerResource(self)
        self.user = UserResource(self)

    def with_options(self, *, timeout: float) -> AdsefidClient:
        """Return a client that shares this one's connection pool but uses `timeout` seconds.

        Use it to bound a single call (`client.with_options(timeout=5).sms.send_single(...)`).
        Closing the returned client never closes the shared `httpx.Client`.
        """
        config = replace(self._config, timeout=timeout)
        clone = object.__new__(AdsefidClient)
        clone._config = config
        clone._http_client = self._http_client
        clone._owns_http_client = False
        clone._request_timeout = timeout
        clone._bind_resources()
        return clone

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        query_params: Mapping[str, QueryValue] | None = None,
        files: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        kwargs = build_request_kwargs(
            method=method,
            base_url=self._config.base_url,
            path=path,
            api_key=self._config.api_key,
            user_agent=self._config.user_agent,
            json_body=json_body,
            query_params=query_params,
            files=files,
        )
        if self._request_timeout is not None:
            kwargs["timeout"] = self._request_timeout
        try:
            response = self._http_client.request(**kwargs)
        except httpx.RequestError as exc:
            raise wrap_transport_error(exc) from exc
        return parse_success_data(response.status_code, response.content)

    def close(self) -> None:
        """Close the underlying `httpx.Client`, unless it was supplied by the caller."""
        if self._owns_http_client:
            self._http_client.close()

    def __enter__(self) -> AdsefidClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
