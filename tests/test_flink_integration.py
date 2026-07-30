"""Flink opt-in integration tests (W26).

These tests pin the Flink client + DAG 04 opt-in behaviour. The HTTP
client uses only the standard library (``urllib.request``) on purpose
so this test file does not need ``requests`` installed in the venv.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from src.streaming.flink import client as flink_client

REPO_ROOT = Path(__file__).resolve().parents[1]
DAG_04_PATH = REPO_ROOT / "dags" / "dag_04_stream_market_events_to_kafka.py"


def _load_dag04():
    spec = importlib.util.spec_from_file_location(
        "dag_04_stream_market_events_to_kafka", DAG_04_PATH
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load DAG 04 module from {DAG_04_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fake_urlopen_response(status: int = 200, body: dict | str | None = None):
    """Build a context-manager-compatible object mimicking urllib's response."""
    if isinstance(body, dict):
        raw = json.dumps(body).encode("utf-8")
    elif isinstance(body, str):
        raw = body.encode("utf-8")
    else:
        raw = b""

    class _Resp:
        def __init__(self):
            self.status = status

        def read(self_inner):
            return raw

        def __enter__(self_inner):
            return self_inner

        def __exit__(self_inner, exc_type, exc, tb):
            return False

    return _Resp()


def test_flink_submit_returns_job_id_on_success(monkeypatch):
    """Submit a Flink job to a mocked jobmanager REST endpoint and assert
    the helper returns a job_id string.

    WHO: data engineer running stage1 streaming DAG.
    ACTION: call flink_client.submit_job with a dummy jar_id and program args.
    RESULT: returns a job_id (non-empty string) and POSTs to the right URL.
    """
    monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink-jobmanager:8081")
    monkeypatch.setenv("FLINK_PARALLELISM", "1")

    captured: dict = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["method"] = request.method
        captured["body"] = json.loads(request.data.decode("utf-8")) if request.data else None
        captured["timeout"] = timeout
        return _fake_urlopen_response(200, {"jobid": "abcd1234"})

    with patch.object(flink_client.urllib.request, "urlopen", side_effect=fake_urlopen):
        job_id = flink_client.submit_job(
            jar_id="stage1-burst-handler",
            program_args=["--bootstrap", "kafka:9092", "--bucket", "lake"],
        )

    assert isinstance(job_id, str)
    assert job_id == "abcd1234"
    assert captured["url"].endswith("/jars/stage1-burst-handler/run")
    assert captured["method"] == "POST"
    assert captured["body"]["programArgs"] == "--bootstrap kafka:9092 --bucket lake"
    assert captured["body"]["parallelism"] == 1
    assert captured["timeout"] == flink_client.DEFAULT_TIMEOUT_SECONDS


def test_flink_submit_raises_when_jobmanager_unreachable(monkeypatch):
    """When the jobmanager URL is unreachable, submit_job must fail fast
    with a clear error rather than silently returning None.

    WHO: CI runner executing streaming DAG.
    ACTION: call flink_client.submit_job with FLINK_JOBMANAGER_URL unset.
    RESULT: raises RuntimeError with a descriptive message; never returns None.
    """
    monkeypatch.delenv("FLINK_JOBMANAGER_URL", raising=False)

    with pytest.raises(RuntimeError, match="FLINK_JOBMANAGER_URL"):
        flink_client.submit_job(jar_id="stage1-burst-handler", program_args=[])


def test_flink_submit_raises_on_http_error(monkeypatch):
    """A non-2xx response from the jobmanager must surface as RuntimeError
    with the HTTP status in the message so DAG tasks fail loudly.

    WHO: CI runner executing streaming DAG.
    ACTION: call submit_job against a jobmanager that returns 404.
    RESULT: RuntimeError mentioning HTTP 404.
    """
    import urllib.error

    monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink-jobmanager:8081")

    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url, 404, "Not Found", {}, io.BytesIO(b"jar not found")
        )

    with patch.object(flink_client.urllib.request, "urlopen", side_effect=fake_urlopen):
        with pytest.raises(RuntimeError, match="HTTP 404"):
            flink_client.submit_job(jar_id="missing-jar", program_args=[])


def test_flink_disabled_by_default(monkeypatch):
    """Stage 1 keeps Flink opt-in. When ENABLE_FLINK is unset, is_enabled()
    must return False so the DAG falls back to MicroBatchConsumer.

    WHO: developer running local Docker stack without Flink.
    ACTION: query is_enabled() with ENABLE_FLINK unset.
    RESULT: returns False.
    """
    monkeypatch.delenv("ENABLE_FLINK", raising=False)
    assert flink_client.is_enabled() is False


def test_flink_opt_in_via_env(monkeypatch):
    """Setting ENABLE_FLINK=1 must flip is_enabled() to True so DAG 04
    dispatches to the Flink submit path.

    WHO: developer running with --profile flink or ENABLE_FLINK=1.
    ACTION: set ENABLE_FLINK=1 and query is_enabled().
    RESULT: returns True.
    """
    monkeypatch.setenv("ENABLE_FLINK", "1")
    assert flink_client.is_enabled() is True


def test_dag_04_uses_flink_when_enabled(monkeypatch):
    """When ENABLE_FLINK=1, the DAG 04 task callable must invoke
    flink_client.submit_job instead of the MicroBatchConsumer smoke path.

    WHO: reviewer verifying opt-in behavior.
    ACTION: load dag_04 and call the task callable after toggling ENABLE_FLINK=1.
    RESULT: flink_client.submit_job called once with jar_id=stage1-burst-handler.
    """
    monkeypatch.setenv("ENABLE_FLINK", "1")
    monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink-jobmanager:8081")

    dag04 = _load_dag04()

    with patch.object(
        dag04.flink_client,
        "submit_job",
        return_value="job-opt-in-test",
    ) as mock_submit:
        result = dag04._stream_smoke()

    mock_submit.assert_called_once()
    assert "stage1-burst-handler" in str(mock_submit.call_args)
    assert result == {"flink_job_id": "job-opt-in-test", "mode": "flink"}


def test_dag_04_falls_back_to_microbatch_when_disabled(monkeypatch):
    """When ENABLE_FLINK is unset, DAG 04 must keep the original
    MicroBatchConsumer behavior so the existing smoke test still passes.

    WHO: reviewer verifying backward compatibility.
    ACTION: load dag_04 and call the task callable with ENABLE_FLINK unset.
    RESULT: flink_client.submit_job NOT called; result is the original
            microbatch flush list.
    """
    monkeypatch.delenv("ENABLE_FLINK", raising=False)

    dag04 = _load_dag04()

    with patch.object(dag04.flink_client, "submit_job") as mock_submit:
        result = dag04._stream_smoke()

    mock_submit.assert_not_called()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["record_count"] == 2


def test_flink_submit_rejects_non_http_scheme(monkeypatch):
    """Submit must reject non-http(s) FLINK_JOBMANAGER_URL values so a
    misconfigured env cannot turn the client into a local-file fetcher.

    WHO: security review of the Flink opt-in path.
    ACTION: set FLINK_JOBMANAGER_URL to a non-http scheme and call submit_job.
    RESULT: RuntimeError mentioning the bad scheme; no HTTP request issued.
    """

    monkeypatch.setenv("FLINK_JOBMANAGER_URL", "file:///etc/passwd")
    monkeypatch.setenv("ENABLE_FLINK", "1")

    called = {"n": 0}

    def should_not_be_called(*a, **kw):
        called["n"] += 1
        raise AssertionError("urlopen must not be called for a non-http scheme")

    with patch.object(flink_client.urllib.request, "urlopen", side_effect=should_not_be_called):
        with pytest.raises(RuntimeError, match="scheme"):
            flink_client.submit_job(jar_id="stage1-burst-handler", program_args=[])
    assert called["n"] == 0


def test_flink_submit_rejects_jar_id_with_path_traversal(monkeypatch):
    """jar_id is interpolated into the URL path; a value containing
    slashes or `..` must be rejected so callers cannot pivot the
    request to an unexpected jobmanager endpoint.

    WHO: security review of the Flink opt-in path.
    ACTION: pass jar_id='../../etc/passwd' to submit_job.
    RESULT: RuntimeError; no HTTP request issued.
    """
    monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink-jobmanager:8081")
    monkeypatch.setenv("ENABLE_FLINK", "1")

    with patch.object(flink_client.urllib.request, "urlopen") as mock_urlopen:
        with pytest.raises(RuntimeError, match="jar_id"):
            flink_client.submit_job(jar_id="../../etc/passwd", program_args=[])
    mock_urlopen.assert_not_called()
