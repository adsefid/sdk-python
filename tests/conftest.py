"""Shared fixtures.

The SDK ships a synchronous client and a structurally identical asynchronous
twin. Rather than duplicating every endpoint test, the `flavor` fixture
parametrizes over both and `unwrap` awaits whatever the call returned, so one
test body covers `SmsResource` and `AsyncSmsResource` alike. pytest reports the
two runs separately (`[sync]` / `[async]`), so an async-only regression is
named precisely.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from tests.helpers.transport import Recorder, async_client, sync_client


async def unwrap(value: Any) -> Any:
    """Await `value` if it is awaitable, otherwise return it unchanged."""
    return await value if inspect.isawaitable(value) else value


@pytest.fixture(params=["sync", "async"])
def flavor(request: pytest.FixtureRequest) -> str:
    return str(request.param)


@pytest.fixture
def make_client(flavor: str):  # type: ignore[no-untyped-def]
    """Builds a client of the current flavor wired to a recording transport."""

    def factory(**kwargs: Any) -> tuple[Any, Recorder]:
        return sync_client(**kwargs) if flavor == "sync" else async_client(**kwargs)

    return factory
