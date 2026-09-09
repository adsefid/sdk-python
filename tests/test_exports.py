"""The public surface is importable from the top-level package."""

from __future__ import annotations

import importlib

import adsefid


def test_every_public_name_is_exported_and_resolvable() -> None:
    for name in adsefid.__all__:
        assert hasattr(adsefid, name), name


def test_request_and_result_models_are_importable_from_the_top_level() -> None:
    # A caller should not have to know the models/ layout to build a request.
    for module_name, names in {
        "adsefid.models.sms": ("SendSingleSmsRequest", "BulkReceptor", "SendBulkSmsResult"),
        "adsefid.models.messenger": ("SendSingleMessengerRequest", "MessengerBulkReceptor"),
        "adsefid.models.user": ("AccountInfo", "UserLine", "UserTemplate"),
        "adsefid.models.common": ("CancelResult", "StatusResult"),
    }.items():
        module = importlib.import_module(module_name)
        for name in names:
            assert name in adsefid.__all__, name
            assert getattr(adsefid, name) is getattr(module, name), name
