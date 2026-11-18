from __future__ import annotations

import subprocess

import pytest

from scripts.verify_supply_chain import _cosign_json


def _runner(stdout: str):
    def run(*_args, **_kwargs):
        return subprocess.CompletedProcess((), 0, stdout, "")

    return run


def test_cosign_empty_output_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="no verification output"):
        _cosign_json(("verify", "image@sha256:" + "a" * 64), runner=_runner(""))


def test_cosign_non_json_output_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="non-JSON"):
        _cosign_json(("verify", "image@sha256:" + "a" * 64), runner=_runner("verified"))
