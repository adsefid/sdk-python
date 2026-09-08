from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version

from .exceptions import AdsefidValidationError

try:
    SDK_VERSION = version("adsefid")
except PackageNotFoundError:
    SDK_VERSION = "0+unknown"

DEFAULT_BASE_URL = "https://api.adsefid.com"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_USER_AGENT = f"adsefid-python/{SDK_VERSION}"


@dataclass(frozen=True, slots=True)
class ClientConfig:
    """Resolved client configuration shared by all resource requests."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    user_agent: str = DEFAULT_USER_AGENT

    def __post_init__(self) -> None:
        if not self.user_agent.strip() or "\r" in self.user_agent or "\n" in self.user_agent:
            raise AdsefidValidationError("user_agent must be non-blank and contain no line breaks")
