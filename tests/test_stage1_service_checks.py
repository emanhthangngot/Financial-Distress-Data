from __future__ import annotations

import importlib
import subprocess
from pathlib import Path


def _completed(command, *, stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)


def test_service_check_passes_when_all_local_services_are_ready():
    module = importlib.import_module("scripts.check_stage1_services")
    responses = {
        ("docker", "compose", "ps", "--status", "running", "--services"): _completed(
            (),
            stdout="postgres\nminio\nkafka\nairflow-webserver\nairflow-scheduler\n",
        ),
        (
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "pg_isready",
            "-U",
            "airflow",
            "-d",
            "financial_distress",
        ): _completed((), stdout="/var/run/postgresql:5432 - accepting connections\n"),
        (
            "docker",
            "compose",
            "exec",
            "-T",
            "kafka",
            "/opt/kafka/bin/kafka-topics.sh",
            "--bootstrap-server",
            "kafka:9092",
            "--list",
        ): _completed(
            (),
            stdout="financial.price_events\nfinancial.news_events\nfinancial.alert_events\n",
        ),
        (
            "docker",
            "compose",
            "exec",
            "-T",
            "minio",
            "sh",
            "-c",
            "test -d /data/financial-distress-lake",
        ): _completed(()),
        (
            "docker",
            "compose",
            "exec",
            "-T",
            "airflow-scheduler",
            "airflow",
            "dags",
            "list-import-errors",
        ): _completed((), stdout="No data found\n"),
    }

    def fake_runner(command, *, cwd, capture_output, text, check):
        assert cwd == module.PROJECT_ROOT
        assert capture_output is True
        assert text is True
        assert check is False
        return responses[tuple(command)]

    summary = module.check_services(runner=fake_runner, cwd=module.PROJECT_ROOT)

    assert summary["status"] == "pass"
    assert summary["failed_checks"] == []


def test_service_check_reports_missing_running_services_before_e2e():
    module = importlib.import_module("scripts.check_stage1_services")

    def fake_runner(command, *, cwd, capture_output, text, check):
        if tuple(command) == ("docker", "compose", "ps", "--status", "running", "--services"):
            return _completed(command, stdout="postgres\nminio\n")
        return _completed(command)

    summary = module.check_services(runner=fake_runner, cwd=Path("/tmp"))

    assert summary["status"] == "fail"
    assert "docker-compose-running-services" in summary["failed_checks"]
    assert "airflow-scheduler" in summary["checks"][0]["detail"]


def test_service_check_reports_missing_kafka_topics():
    module = importlib.import_module("scripts.check_stage1_services")

    def fake_runner(command, *, cwd, capture_output, text, check):
        command = tuple(command)
        if command == ("docker", "compose", "ps", "--status", "running", "--services"):
            return _completed(
                command,
                stdout="postgres\nminio\nkafka\nairflow-webserver\nairflow-scheduler\n",
            )
        if "kafka-topics.sh" in command:
            return _completed(command, stdout="financial.price_events\n")
        if "airflow" in command:
            return _completed(command, stdout="No data found\n")
        return _completed(command)

    summary = module.check_services(runner=fake_runner, cwd=Path("/tmp"))

    assert summary["status"] == "fail"
    assert "kafka-topics" in summary["failed_checks"]
    kafka_check = next(check for check in summary["checks"] if check["name"] == "kafka-topics")
    assert "financial.alert_events" in kafka_check["detail"]
    assert "financial.news_events" in kafka_check["detail"]
