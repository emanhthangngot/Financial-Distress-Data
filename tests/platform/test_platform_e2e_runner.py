from __future__ import annotations

import pytest

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
