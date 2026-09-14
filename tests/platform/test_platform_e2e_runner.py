from __future__ import annotations

from contextlib import contextmanager

import pytest

from scripts import run_platform_e2e
from scripts.run_platform_e2e import (
    coordinator_payload,
    model_payload,
    validate_coordinator_response,
)


def valid_response() -> dict[str, object]:
    return {
        "answer": "[feature] last_price=1.0\n\n[drift] count=1 passed=True",
        "specialists": [
            {"specialist": "feature", "answer": "last_price=1.0", "citations": []},
            {"specialist": "drift", "answer": "count=1 passed=True", "citations": []},
        ],
        "citations": [
            {"source_uri": "feature://user/PHASE3_CONTRACT_PROBE", "label": "features"},
            {"source_uri": "drift://scenario/market_stress", "label": "drift report"},
        ],
        "hops_used": 1,
    }


def test_coordinator_payload_contains_real_numeric_drift_observation() -> None:
    payload = coordinator_payload()
    rows = payload["drift_request"]["rows"]

    assert rows == [{"ticker": "PHASE3_CONTRACT_PROBE", "close_price": 100.0}]
    assert payload["drift_request"]["scenario"]["target_metric"] == "close_price"


def test_model_payload_uses_the_live_gateway_model() -> None:
    payload = model_payload()

    assert payload["model"] == "qwen2.5-0.5b-instruct"
    assert payload["stream"] is False
    assert payload["messages"]


def test_validate_coordinator_response_requires_both_specialists_and_citations() -> None:
    result = validate_coordinator_response(valid_response())

    assert result["specialists"] == ["drift", "feature"]
    assert result["drift_rows_sent"] == 1
    assert result["hops_used"] == 1


def test_warm_model_leaves_hibernated_revision_running_for_followup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []
    responses = iter(
        [
            (503, {"error": "starting"}),
            (200, {"choices": [{"message": {"content": "ready"}}]}),
        ]
    )

    @contextmanager
    def fake_port_forward(*_: object, **__: object):
        yield "http://127.0.0.1:1"

    monkeypatch.setattr(run_platform_e2e, "port_forward", fake_port_forward)
    monkeypatch.setattr(
        run_platform_e2e,
        "http_json",
        lambda *_args, **_kwargs: next(responses),
    )
    monkeypatch.setattr(run_platform_e2e, "_active_model_deployment", lambda: "model-revision")
    monkeypatch.setattr(
        run_platform_e2e,
        "_kubectl_json",
        lambda *_args, **_kwargs: {"spec": {"replicas": 0}},
    )
    monkeypatch.setattr(run_platform_e2e, "_kubectl", lambda *args, **_kwargs: calls.append(args))
    monkeypatch.setattr(run_platform_e2e.time, "sleep", lambda *_args: None)
    monkeypatch.setattr(run_platform_e2e.time, "monotonic", iter([0.0, 0.0, 0.0]).__next__)

    result = run_platform_e2e.warm_model(timeout=5)

    assert result["scaled_revision"] == "model-revision"
    assert calls == [
        ("scale", "deployment", "model-revision", "-n", "default", "--replicas=1"),
    ]


def test_warm_model_restores_hibernated_revision_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    @contextmanager
    def fake_port_forward(*_: object, **__: object):
        yield "http://127.0.0.1:1"

    monkeypatch.setattr(run_platform_e2e, "port_forward", fake_port_forward)
    monkeypatch.setattr(
        run_platform_e2e,
        "http_json",
        lambda *_args, **_kwargs: (503, {"error": "starting"}),
    )
    monkeypatch.setattr(run_platform_e2e, "_active_model_deployment", lambda: "model-revision")
    monkeypatch.setattr(
        run_platform_e2e,
        "_kubectl_json",
        lambda *_args, **_kwargs: {"spec": {"replicas": 0}},
    )
    monkeypatch.setattr(run_platform_e2e, "_kubectl", lambda *args, **_kwargs: calls.append(args))
    monkeypatch.setattr(run_platform_e2e.time, "monotonic", iter([0.0, 0.0, 6.0]).__next__)
    monkeypatch.setattr(run_platform_e2e.time, "sleep", lambda *_args: None)

    with pytest.raises(RuntimeError, match="model warm-up failed"):
        run_platform_e2e.warm_model(timeout=5)

    assert calls == [
        ("scale", "deployment", "model-revision", "-n", "default", "--replicas=1"),
        ("scale", "deployment", "model-revision", "-n", "default", "--replicas=0"),
    ]


@pytest.mark.parametrize(
    "patch",
    [
        {"specialists": [{"specialist": "feature"}]},
        {"citations": [{"source_uri": "feature://only", "label": "features"}]},
        {"answer": ""},
    ],
)
def test_validate_coordinator_response_rejects_incomplete_evidence(
    patch: dict[str, object],
) -> None:
    response = valid_response()
    response.update(patch)

    with pytest.raises(RuntimeError):
        validate_coordinator_response(response)
