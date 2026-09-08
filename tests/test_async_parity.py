"""Structural guard on the hand-maintained sync/async twin surface.

Every resource has an asynchronous twin whose methods must match one for one.
The actual failure mode is somebody adding a method to the sync class and
forgetting the async one, which no behavioural test would catch — so compare
the surfaces directly.
"""

from __future__ import annotations

import inspect

import pytest

from adsefid import AdsefidAsyncClient, AdsefidClient
from adsefid.resources.messenger import AsyncMessengerResource, MessengerResource
from adsefid.resources.sms import AsyncSmsResource, SmsResource
from adsefid.resources.user import AsyncUserResource, UserResource

PAIRS = [
    pytest.param(SmsResource, AsyncSmsResource, id="sms"),
    pytest.param(MessengerResource, AsyncMessengerResource, id="messenger"),
    pytest.param(UserResource, AsyncUserResource, id="user"),
]


def public_names(cls: type) -> set[str]:
    return {name for name in dir(cls) if not name.startswith("_")}


@pytest.mark.parametrize(("sync_cls", "async_cls"), PAIRS)
def test_the_twins_expose_the_same_methods(sync_cls: type, async_cls: type) -> None:
    assert public_names(sync_cls) == public_names(async_cls)


@pytest.mark.parametrize(("sync_cls", "async_cls"), PAIRS)
def test_the_twins_share_each_method_signature(sync_cls: type, async_cls: type) -> None:
    for name in sorted(public_names(sync_cls)):
        sync_signature = inspect.signature(getattr(sync_cls, name))
        async_signature = inspect.signature(getattr(async_cls, name))
        assert sync_signature == async_signature, f"{name} has drifted between the twins"


@pytest.mark.parametrize(("sync_cls", "async_cls"), PAIRS)
def test_every_async_method_is_a_coroutine(sync_cls: type, async_cls: type) -> None:
    for name in sorted(public_names(async_cls)):
        assert inspect.iscoroutinefunction(getattr(async_cls, name)), f"{name} is not async"
        assert not inspect.iscoroutinefunction(getattr(sync_cls, name)), f"{name} should be sync"


def test_the_clients_expose_the_same_surface_apart_from_close() -> None:
    """`close` / `aclose` is the one deliberate difference, mirroring httpx."""
    sync_names = public_names(AdsefidClient) - {"close"}
    async_names = public_names(AdsefidAsyncClient) - {"aclose"}
    assert sync_names == async_names
    assert "close" in public_names(AdsefidClient)
    assert "aclose" in public_names(AdsefidAsyncClient)


@pytest.mark.parametrize("resource", ["sms", "messenger", "user"])
def test_both_clients_expose_every_resource(resource: str) -> None:
    assert hasattr(AdsefidClient("k"), resource)
    assert hasattr(AdsefidAsyncClient("k"), resource)
