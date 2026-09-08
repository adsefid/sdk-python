"""The golden fixtures are copied byte-for-byte into all five SDK repositories.

A fixture that drifts here silently weakens every test that reads it, so the
manifest is verified rather than trusted.
"""

from __future__ import annotations

from tests.helpers.fixtures import FIXTURES_DIR, manifest_entries, sha256_of


def test_every_listed_fixture_matches_its_checksum() -> None:
    entries = manifest_entries()
    assert entries, "the manifest is empty"

    for expected_sha, name in entries:
        assert (FIXTURES_DIR / name).is_file(), f"{name} is listed but missing"
        assert sha256_of(name) == expected_sha, f"{name} has drifted from the shared copy"


def test_no_fixture_is_missing_from_the_manifest() -> None:
    listed = {name for _, name in manifest_entries()}
    on_disk = {
        path.relative_to(FIXTURES_DIR).as_posix()
        for path in FIXTURES_DIR.rglob("*")
        if path.is_file() and path.name != "CHECKSUMS.txt"
    }
    assert on_disk == listed
