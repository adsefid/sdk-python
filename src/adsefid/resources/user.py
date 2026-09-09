from __future__ import annotations

from typing import TYPE_CHECKING

from .._base import expect_list, expect_object
from .._serialization import validate_skip, validate_take
from ..enums import TemplateState
from ..models.user import (
    AccountInfo,
    GetTemplatesRequest,
    GetUserTemplatesResult,
    UserLine,
    UserProfile,
)

if TYPE_CHECKING:
    from ..async_client import AdsefidAsyncClient
    from ..client import AdsefidClient


def _templates_request(
    state: TemplateState | None, skip: int | None, take: int | None
) -> GetTemplatesRequest:
    validate_skip(skip)
    validate_take(take)
    return GetTemplatesRequest(state=state, skip=skip, take=take)


class UserResource:
    """Synchronous account/user operations, available as `AdsefidClient(...).user`."""

    def __init__(self, client: AdsefidClient) -> None:
        self._client = client

    def get_info(self) -> AccountInfo:
        """Fetch the authenticated account's profile and credit balance
        (`GET /v1/user/info`).
        """
        data = self._client.request("GET", "/v1/user/info")
        return AccountInfo.from_dict(expect_object(data))

    def get_lines(self) -> list[UserLine]:
        """List the SMS lines assigned to the account (`GET /v1/user/lines`)."""
        data = self._client.request("GET", "/v1/user/lines")
        return [UserLine.from_dict(item) for item in expect_list(data)]

    def get_profiles(self) -> list[UserProfile]:
        """List the messenger profiles assigned to the account
        (`GET /v1/user/profiles`).
        """
        data = self._client.request("GET", "/v1/user/profiles")
        return [UserProfile.from_dict(item) for item in expect_list(data)]

    def get_templates(
        self,
        *,
        state: TemplateState | None = None,
        skip: int | None = None,
        take: int | None = None,
    ) -> GetUserTemplatesResult:
        """List message templates, optionally filtered and paginated
        (`GET /v1/user/templates`).

        Raises AdsefidValidationError if `skip` is negative or `take` is outside
        `[MIN_TEMPLATE_TAKE, MAX_TEMPLATE_TAKE]`.
        """
        request = _templates_request(state, skip, take)
        data = self._client.request(
            "GET", "/v1/user/templates", query_params=request.to_query_params()
        )
        return GetUserTemplatesResult.from_dict(expect_object(data))


class AsyncUserResource:
    """Asynchronous account/user operations, available as
    `AdsefidAsyncClient(...).user`.

    Same operations, validation, and error behavior as `UserResource`; see its
    method docstrings for details.
    """

    def __init__(self, client: AdsefidAsyncClient) -> None:
        self._client = client

    async def get_info(self) -> AccountInfo:
        data = await self._client.request("GET", "/v1/user/info")
        return AccountInfo.from_dict(expect_object(data))

    async def get_lines(self) -> list[UserLine]:
        data = await self._client.request("GET", "/v1/user/lines")
        return [UserLine.from_dict(item) for item in expect_list(data)]

    async def get_profiles(self) -> list[UserProfile]:
        data = await self._client.request("GET", "/v1/user/profiles")
        return [UserProfile.from_dict(item) for item in expect_list(data)]

    async def get_templates(
        self,
        *,
        state: TemplateState | None = None,
        skip: int | None = None,
        take: int | None = None,
    ) -> GetUserTemplatesResult:
        request = _templates_request(state, skip, take)
        data = await self._client.request(
            "GET", "/v1/user/templates", query_params=request.to_query_params()
        )
        return GetUserTemplatesResult.from_dict(expect_object(data))
