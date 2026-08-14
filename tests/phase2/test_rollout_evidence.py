from __future__ import annotations

import pytest

from scripts.capture_rollout_evidence import capture


def test_capture_fails_closed_when_cluster_tools_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("scripts.capture_rollout_evidence.shutil.which", lambda _: None)
    with pytest.raises(RuntimeError, match="required cluster tools are missing"):
        capture(rollout="feature-api")


def test_capture_records_failed_cluster_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scripts.capture_rollout_evidence.shutil.which", lambda _: "/usr/bin/tool")

    class Result:
        returncode = 1
        stdout = ""
        stderr = "not found"

    monkeypatch.setattr("scripts.capture_rollout_evidence.subprocess.run", lambda *a, **k: Result())
    payload = capture(rollout="feature-api")
    assert payload["status"] == "fail"
    assert len(payload["records"]) == 3
