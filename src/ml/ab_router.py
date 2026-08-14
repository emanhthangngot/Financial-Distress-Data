"""Deterministic weighted A/B model routing."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class RouteDecision:
    key: str
    variant: str
    bucket: float


class ABRouter:
    """Route a stable key to a weighted model variant without mutable RNG state."""

    def __init__(self, variants: Mapping[str, float], *, salt: str = "financial-distress"):
        if not variants:
            raise ValueError("at least one model variant is required")
        if any(float(weight) < 0 for weight in variants.values()):
            raise ValueError("variant weights cannot be negative")
        total = sum(float(weight) for weight in variants.values())
        if total <= 0:
            raise ValueError("variant weights must have a positive sum")
        self._variants = tuple(
            (str(name), float(weight) / total) for name, weight in variants.items()
        )
        self.salt = salt

    def decide(self, key: str | int) -> RouteDecision:
        raw = hashlib.sha256(f"{self.salt}:{key}".encode()).digest()
        bucket = int.from_bytes(raw[:8], "big") / 2**64
        cumulative = 0.0
        for name, weight in self._variants:
            cumulative += weight
            if bucket < cumulative:
                return RouteDecision(str(key), name, bucket)
        return RouteDecision(str(key), self._variants[-1][0], bucket)

    def route(self, key: str | int) -> str:
        return self.decide(key).variant

    @property
    def weights(self) -> dict[str, float]:
        return dict(self._variants)


def route_model(
    key: str | int, variants: Mapping[str, float], *, salt: str = "financial-distress"
) -> str:
    """Functional wrapper for DAG/API callers."""

    return ABRouter(variants, salt=salt).route(key)
