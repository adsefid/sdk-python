"""Client construction, configuration precedence, and lifecycle."""

from __future__ import annotations

import httpx
import pytest

from adsefid import AdsefidAsyncClient, AdsefidClient, AdsefidValidationError, ClientConfig
from adsefid.config import DEFAULT_BASE_URL, DEFAULT_TIMEOUT_SECONDS, DEFAULT_USER_AGENT
from tests.helpers.transport import BASE_URL, mock_transport


class TestClientConfig:
    def test_defaults(self) -> None:
        config = ClientConfig(api_key="k")
        assert config.base_url == DEFAULT_BASE_URL
        assert config.timeout == DEFAULT_TIMEOUT_SECONDS
        assert config.user_agent == DEFAULT_USER_AGENT

    def test_the_default_user_agent_is_prefixed_not_pinned(self) -> None:
        # The version comes from package metadata, so never assert it exactly.
        assert DEFAULT_USER_AGENT.startswith("adsefid-python/")

    @pytest.mark.parametrize("api_key", ["", "   "])
    def test_a_blank_api_key_is_rejected(self, api_key: str) -> None:
        with pytest.raises(AdsefidValidationError, match="api_key"):
            ClientConfig(api_key=api_key)

    def test_a_blank_base_url_is_rejected(self) -> None:
        with pytest.raises(AdsefidValidationError, match="base_url"):
            ClientConfig(api_key="k", base_url="  ")

    @pytest.mark.parametrize(
        "user_agent",
        ["", "   ", "bad\nagent", "bad\ragent"],
        ids=["empty", "blank", "newline", "carriage return"],
    )
    def test_an_unusable_user_agent_is_rejected(self, user_agent: str) -> None:
        with pytest.raises(AdsefidValidationError, match="user_agent"):
            ClientConfig(api_key="k", user_agent=user_agent)


class TestClientConstruction:
    @pytest.mark.parametrize("cls", [AdsefidClient, AdsefidAsyncClient])
    def test_a_blank_api_key_is_rejected(self, cls) -> None:
        with pytest.raises(AdsefidValidationError):
            cls("")

    @pytest.mark.parametrize("cls", [AdsefidClient, AdsefidAsyncClient])
    def test_all_three_resources_are_wired_up(self, cls) -> None:
        client = cls("k")
        assert client.sms is not None
        assert client.messenger is not None
        assert client.user is not None


class TestHttpClientOwnership:
    """A caller-supplied client is the caller's to close."""

    def test_a_supplied_client_is_not_closed(self) -> None:
        transport, _ = mock_transport()
        http = httpx.Client(transport=transport, base_url=BASE_URL)

        with AdsefidClient("k", http_client=http):
            pass

        assert not http.is_closed

    def test_an_owned_client_is_closed(self) -> None:
        client = AdsefidClient("k")
        client.close()
        assert client._http_client.is_closed

    async def test_a_supplied_async_client_is_not_closed(self) -> None:
        transport, _ = mock_transport()
        http = httpx.AsyncClient(transport=transport, base_url=BASE_URL)

        async with AdsefidAsyncClient("k", http_client=http):
            pass

        assert not http.is_closed


@pytest.mark.parametrize("base_url", [BASE_URL, BASE_URL + "/"], ids=["bare", "trailing slash"])
def test_a_supplied_client_without_a_base_url_still_hits_the_configured_origin(
    base_url: str,
) -> None:
    transport, recorder = mock_transport(content=b'{"status":"success","data":[]}')
    http = httpx.Client(transport=transport)
    client = AdsefidClient("k", base_url=base_url, http_client=http)

    client.user.get_lines()

    assert str(recorder.only.url) == BASE_URL + "/v1/user/lines"


async def test_a_custom_user_agent_reaches_the_wire() -> None:
    transport, recorder = mock_transport(content=b'{"status":"success","data":{}}')
    http = httpx.Client(transport=transport, base_url=BASE_URL)
    client = AdsefidClient("k", http_client=http, user_agent="my-app/2.1")

    try:
        client.request("GET", "/v1/user/lines")
    except Exception:  # noqa: BLE001 - the payload shape is irrelevant here
        pass

    assert recorder.only.headers["User-Agent"] == "my-app/2.1"
