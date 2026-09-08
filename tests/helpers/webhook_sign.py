"""Reproduces the service's webhook signing, for tests that need a fresh one."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time

SIGNATURE_PREFIX = "v1="


def sign(secret_base64: str, timestamp: str, raw_body: bytes) -> str:
    """HMAC-SHA256 over "{timestamp}.{raw_body}", keyed with the DECODED secret.

    The endpoint secret is 32 random bytes shown Base64-encoded in the panel;
    the service keys the HMAC with those raw bytes.
    """
    key = base64.b64decode(secret_base64, validate=True)
    signing_input = f"{timestamp}.".encode() + raw_body
    digest = hmac.new(key, signing_input, hashlib.sha256).digest()
    return SIGNATURE_PREFIX + base64.b64encode(digest).decode("ascii")


def now_timestamp(offset_seconds: int = 0) -> str:
    return str(int(time.time()) + offset_seconds)
