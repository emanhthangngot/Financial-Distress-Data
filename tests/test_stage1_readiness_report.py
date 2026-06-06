from __future__ import annotations

import importlib


def test_readiness_report_uses_evidence_only_by_default(monkeypatch):
    module = importlib.import_module("scripts.stage1_readiness_report")
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
    assert service_calls == []


def test_readiness_report_can_include_service_checks(monkeypatch):
    module = importlib.import_module("scripts.stage1_readiness_report")
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
    module = importlib.import_module("scripts.stage1_readiness_report")

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
