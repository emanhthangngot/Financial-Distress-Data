from __future__ import annotations

import importlib
import subprocess
import sys

import pytest


def test_quality_gate_runner_executes_default_gates_in_order():
    module = importlib.import_module("scripts.run_lakehouse_quality_gates")
    calls = []

    def fake_runner(command, *, cwd, check):
        calls.append((tuple(command), cwd, check))

    module.run_quality_gates(module.DEFAULT_GATES, runner=fake_runner)

    assert [command[0] for command, _, _ in calls] == [
        sys.executable,
        sys.executable,
        sys.executable,
        "docker",
        sys.executable,
        sys.executable,
    ]
    assert [command for command, _, _ in calls] == [gate.command for gate in module.DEFAULT_GATES]
    assert all(check is True for _, _, check in calls)
    assert all(cwd == module.PROJECT_ROOT for _, cwd, _ in calls)
    assert "lakehouse-service-readiness" not in [gate.name for gate in module.DEFAULT_GATES]


def test_quality_gate_selection_preserves_default_order():
    module = importlib.import_module("scripts.run_lakehouse_quality_gates")

    selected = module._selected_gates({"lakehouse-evidence-audit", "pytest"})

    assert [gate.name for gate in selected] == ["pytest", "lakehouse-evidence-audit"]


def test_quality_gate_selection_can_run_service_readiness_gate_explicitly():
    module = importlib.import_module("scripts.run_lakehouse_quality_gates")

    selected = module._selected_gates({"lakehouse-service-readiness"})

    assert [gate.name for gate in selected] == ["lakehouse-service-readiness"]
    assert selected[0].command == (
        sys.executable,
        "scripts/check_lakehouse_services.py",
    )


def test_quality_gate_selection_rejects_unknown_gate():
    module = importlib.import_module("scripts.run_lakehouse_quality_gates")

    with pytest.raises(ValueError, match="Unknown quality gate"):
        module._selected_gates({"not-a-gate"})


def test_quality_gate_runner_stops_on_first_failed_gate():
    module = importlib.import_module("scripts.run_lakehouse_quality_gates")
    calls = []

    def fake_runner(command, *, cwd, check):
        calls.append(tuple(command))
        if len(calls) == 2:
            raise subprocess.CalledProcessError(returncode=7, cmd=command)

    with pytest.raises(subprocess.CalledProcessError) as exc:
        module.run_quality_gates(module.DEFAULT_GATES, runner=fake_runner)

    assert exc.value.returncode == 7
    assert calls == [module.DEFAULT_GATES[0].command, module.DEFAULT_GATES[1].command]
