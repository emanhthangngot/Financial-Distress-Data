"""Hypothesis properties for deterministic retrieval and repeated tools."""

from __future__ import annotations

from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from src.drift.generator import apply_drift
from src.drift.generator_config import DriftScenario, ShiftSpec
from src.llm.contracts import BoundedMcpToolService


@settings(max_examples=40, deadline=None)
@given(
    st.lists(
        st.fixed_dictionaries(
            {
                "ticker": st.sampled_from(["AAA", "BBB", "CCC"]),
                "close_price": st.floats(min_value=0.01, max_value=10_000, allow_nan=False),
            }
        ),
        min_size=1,
        max_size=12,
    )
)
def test_drift_retrieval_is_idempotent(rows: list[dict[str, Any]]) -> None:
    scenario = DriftScenario(
        name="property-stress",
        seed=41,
        start_quarter=1,
        affected_fraction=0.5,
        feature_shifts={"close_price": ShiftSpec(mode="multiplicative", magnitude=0.25)},
        target_metric="close_price",
        observed_stat="mean",
        expected_direction="increase",
        threshold=0.01,
    )
    first = apply_drift(rows, scenario)
    second = apply_drift(rows, scenario)
    assert first == second


@settings(max_examples=40, deadline=None)
@given(st.integers(min_value=-10_000, max_value=10_000))
def test_repeated_tool_invocation_returns_the_same_value(value: int) -> None:
    service = BoundedMcpToolService(
        handlers={"echo": lambda payload: {"value": payload["value"]}},
        validators={"echo": lambda payload: payload},
        grants={"echo": {("verification-agent", "verification")}},
        max_calls=2,
    )
    request = {
        "value": value,
        "agent_identity": "verification-agent",
        "scope": "verification",
    }
    first = service.invoke("echo", request)
    second = service.invoke("echo", request)
    assert first.ok and second.ok
    assert first.value == second.value == {"value": value}
