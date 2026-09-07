from __future__ import annotations

from dataclasses import dataclass

DEFAULT_BASE_URL = "https://api.adsefid.com"
DEFAULT_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class ClientConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_TIMEOUT_SECONDS
