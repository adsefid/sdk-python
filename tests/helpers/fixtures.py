"""Access to the golden fixtures shared byte-for-byte with the sibling SDKs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def fixture_bytes(name: str) -> bytes:
    """Read one fixture as raw bytes.

    Webhook verification signs the exact bytes on the wire, so anything that
    feeds a signature must go through here rather than re-serializing JSON.
    """
    return (FIXTURES_DIR / name).read_bytes()


def fixture_text(name: str) -> str:
    return fixture_bytes(name).decode("utf-8")


def fixture_json(name: str) -> Any:
    return json.loads(fixture_bytes(name))


def envelope_data(name: str) -> Any:
    """The `data` payload of a success envelope fixture."""
    return fixture_json(name)["data"]


def manifest_entries() -> list[tuple[str, str]]:
    """(sha256, path) pairs from CHECKSUMS.txt."""
    manifest = fixture_text("CHECKSUMS.txt").strip().splitlines()
    return [tuple(line.split("  ", 1)) for line in manifest]  # type: ignore[misc]


def sha256_of(name: str) -> str:
    return hashlib.sha256(fixture_bytes(name)).hexdigest()
