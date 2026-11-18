from __future__ import annotations

import importlib
import json
import subprocess


def test_readiness_report_uses_evidence_only_by_default(monkeypatch):
    module = importlib.import_module("scripts.lakehouse_readiness_report")
    service_calls = []

    monkeypatch.setattr(
        module,
        "audit_evidence",
        lambda evidence_dir: {
            "status": "pass",
            "failed_checks": [],
            "duckdb_metrics": {"total_financial_statement_rows": 16},
            "kafka_topics": ["financial.alert_events", "financial.news_events"],
            "minio_object_count": 100,
        },
    )
    monkeypatch.setattr(module, "check_services", lambda **kwargs: service_calls.append(kwargs))
    monkeypatch.setattr(
        module,
        "_git_summary",
        lambda **kwargs: {"branch": "dev", "commit": "abc1234", "status": "clean"},
    )

    report = module.build_readiness_report("docs/evidence")

    assert report["status"] == "pass"
    assert report["coursework_ready"] is True
    assert report["production_ready"] is False
    assert report["enterprise_ready"] is False
    assert report["services"] is None
    assert report["quality_gates"] is None
    assert service_calls == []


def test_readiness_report_can_include_service_checks(monkeypatch):
    module = importlib.import_module("scripts.lakehouse_readiness_report")
    service_calls = []

    monkeypatch.setattr(
        module,
        "audit_evidence",
        lambda evidence_dir: {
            "status": "pass",
            "failed_checks": [],
            "duckdb_metrics": {},
            "kafka_topics": [],
            "minio_object_count": 0,
        },
    )

    def fake_check_services(**kwargs):
        service_calls.append(kwargs)
        return {"status": "pass", "failed_checks": [], "checks": []}

    monkeypatch.setattr(module, "check_services", fake_check_services)
    monkeypatch.setattr(
        module,
        "_git_summary",
        lambda **kwargs: {"branch": "dev", "commit": "abc1234", "status": "clean"},
    )

    report = module.build_readiness_report("docs/evidence", include_services=True)

    assert report["status"] == "pass"
    assert report["services"]["status"] == "pass"
    assert len(service_calls) == 1


def test_readiness_report_fails_when_evidence_fails(monkeypatch):
    module = importlib.import_module("scripts.lakehouse_readiness_report")

    monkeypatch.setattr(
        module,
        "audit_evidence",
        lambda evidence_dir: {
            "status": "fail",
            "failed_checks": ["duckdb_total_news_feature_rows_ok"],
            "duckdb_metrics": {},
            "kafka_topics": [],
            "minio_object_count": 0,
        },
    )
    monkeypatch.setattr(
        module,
        "_git_summary",
        lambda **kwargs: {"branch": "dev", "commit": "abc1234", "status": "clean"},
    )

    report = module.build_readiness_report("docs/evidence")

    assert report["status"] == "fail"
    assert report["coursework_ready"] is False
    assert report["failed_sections"] == ["evidence"]


def test_readiness_report_can_include_quality_gates(monkeypatch):
    module = importlib.import_module("scripts.lakehouse_readiness_report")
    quality_gate_calls = []

    monkeypatch.setattr(
        module,
        "audit_evidence",
        lambda evidence_dir: {
            "status": "pass",
            "failed_checks": [],
            "duckdb_metrics": {},
            "kafka_topics": [],
            "minio_object_count": 0,
        },
    )

    def fake_run_quality_gates(**kwargs):
        quality_gate_calls.append(kwargs)
        return {"status": "pass", "returncode": 0, "command": ["quality"], "output_tail": "ok"}

    monkeypatch.setattr(module, "_run_quality_gates", fake_run_quality_gates)
    monkeypatch.setattr(
        module,
        "_git_summary",
        lambda **kwargs: {"branch": "dev", "commit": "abc1234", "status": "clean"},
    )

    report = module.build_readiness_report("docs/evidence", include_quality_gates=True)

    assert report["status"] == "pass"
    assert report["quality_gates"]["status"] == "pass"
    assert len(quality_gate_calls) == 1


def test_readiness_report_fails_when_quality_gates_fail(monkeypatch):
    module = importlib.import_module("scripts.lakehouse_readiness_report")

    monkeypatch.setattr(
        module,
        "audit_evidence",
        lambda evidence_dir: {
            "status": "pass",
            "failed_checks": [],
            "duckdb_metrics": {},
            "kafka_topics": [],
            "minio_object_count": 0,
        },
    )
    monkeypatch.setattr(
        module,
        "_run_quality_gates",
        lambda **kwargs: {
            "status": "fail",
            "returncode": 1,
            "command": ["quality"],
            "output_tail": "failed",
        },
    )
    monkeypatch.setattr(
        module,
        "_git_summary",
        lambda **kwargs: {"branch": "dev", "commit": "abc1234", "status": "clean"},
    )

    report = module.build_readiness_report("docs/evidence", include_quality_gates=True)

    assert report["status"] == "fail"
    assert report["failed_sections"] == ["quality_gates"]


def test_write_report_writes_json_artifact(tmp_path):
    module = importlib.import_module("scripts.lakehouse_readiness_report")
    output_path = tmp_path / "lakehouse_readiness_report.json"

    module._write_report({"status": "pass", "coursework_ready": True}, output_path)

    assert json.loads(output_path.read_text(encoding="utf-8")) == {
        "status": "pass",
        "coursework_ready": True,
    }


def test_git_summary_reports_clean_status_for_empty_git_status(monkeypatch):
    module = importlib.import_module("scripts.lakehouse_readiness_report")

    def fake_run(command, *, cwd, capture_output, text, check):
        outputs = {
            ("git", "branch", "--show-current"): "dev\n",
            ("git", "rev-parse", "--short", "HEAD"): "abc1234\n",
            ("git", "status", "--short"): "",
        }
        return subprocess.CompletedProcess(command, 0, stdout=outputs[tuple(command)], stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module._git_summary() == {"branch": "dev", "commit": "abc1234", "status": "clean"}
