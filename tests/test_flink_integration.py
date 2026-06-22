from __future__ import annotations

from unittest.mock import patch

import pytest

from src.streaming.flink import client as flink_client


def test_flink_submit_returns_job_id_on_success(monkeypatch):
    """Submit a Flink job to a mocked jobmanager REST endpoint and assert
    the helper returns a job_id string.

    WHO: data engineer running stage1 streaming DAG.
    ACTION: call flink_client.submit_job with a dummy jar_id and program args.
    RESULT: returns a job_id (non-empty string).
    """
    monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink-jobmanager:8081")
    monkeypatch.setenv("FLINK_PARALLELISM", "1")

    captured: dict = {}

    def fake_post(url, json=None, timeout=None):  # noqa: A002
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout

        class _Resp:
            status_code = 200
            text = ""

            def json(self_inner):
                return {"jobid": "abcd1234"}

        return _Resp()

    with patch.object(flink_client.requests, "post", side_effect=fake_post):
        job_id = flink_client.submit_job(
            jar_id="stage1-burst-handler",
            program_args=["--bootstrap", "kafka:9092", "--bucket", "lake"],
        )

    assert isinstance(job_id, str)
    assert job_id == "abcd1234"
    assert captured["url"].endswith("/jars/stage1-burst-handler/run")
    assert captured["json"]["programArgs"] == "--bootstrap kafka:9092 --bucket lake"
    assert captured["json"]["parallelism"] == 1


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
    ACTION: import dag_04 and call the task callable after toggling ENABLE_FLINK=1.
    RESULT: flink_client.submit_job called once with jar_id=stage1-burst-handler.
    """
    monkeypatch.setenv("ENABLE_FLINK", "1")
    monkeypatch.setenv("FLINK_JOBMANAGER_URL", "http://flink-jobmanager:8081")

    from dags import dag_04_stream_market_events_to_kafka as dag04

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
    ACTION: import dag_04 and call the task callable with ENABLE_FLINK unset.
    RESULT: flink_client.submit_job NOT called; result is the original
            microbatch flush list.
    """
    monkeypatch.delenv("ENABLE_FLINK", raising=False)

    from dags import dag_04_stream_market_events_to_kafka as dag04

    with patch.object(dag04.flink_client, "submit_job") as mock_submit:
        result = dag04._stream_smoke()

    mock_submit.assert_not_called()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["record_count"] == 2
