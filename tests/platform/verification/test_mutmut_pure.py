"""Mutation harness that imports ``src`` modules under non-``src`` aliases.

mutmut 3.7 rejects its own trampoline statistics when a module name starts
with ``src.``. The application package stays unchanged; this harness only
gives the mutation runner an import name it can instrument.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from src.drift.generator_config import DriftScenario, ShiftSpec

REPO_ROOT = Path(__file__).resolve().parents[3]


def load_alias(alias: str, relative_path: str) -> ModuleType:
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(alias, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


def test_mutmut_drift_pure_paths_are_behaviorally_pinned() -> None:
    module = load_alias("drift.generator", "src/drift/generator.py")
    scenario = DriftScenario(
        name="mutation",
        seed=41,
        start_quarter=1,
        affected_fraction=0.5,
        feature_shifts={"close_price": ShiftSpec(mode="multiplicative", magnitude=0.25)},
        target_metric="close_price",
        observed_stat="mean",
        expected_direction="increase",
        threshold=0.01,
    )
    rows = [
        {"ticker": "AAA", "close_price": 10.0},
        {"ticker": "BBB", "close_price": 20.0},
        {"ticker": "CCC", "close_price": 30.0},
    ]
    first = module.apply_drift(rows, scenario)
    assert first == module.apply_drift(rows, scenario)
    assert module._apply_shift(10.0, ShiftSpec("multiplicative", 0.5), 1.0) == 15.0
    assert module._apply_shift(10.0, ShiftSpec("additive", 2.0), 0.5) == 11.0
    assert module._distribution_stats([])["count"] == 0
    assert module._distribution_stats([1.0, 2.0])["count"] == 2


def test_mutmut_chunking_pure_paths_are_behaviorally_pinned() -> None:
    module = load_alias("llm.rag.chunking", "src/llm/rag/chunking.py")
    assert module.normalize_text(" Café\n  report ") == "Café report"
    document_hash = module.compute_document_hash(b"report")
    assert len(document_hash) == 64
    content_hash = module.compute_content_hash("report")
    assert len(content_hash) == 64
    assert module.chunk_text("") == []
    assert module.chunk_text("short", target_chars=10) == ["short"]
    chunks = module.chunk_text("One. Two. Three. Four.", target_chars=10, overlap_chars=2)
    assert len(chunks) >= 2
    assert all(chunk for chunk in chunks)

    assert module._find_sentence_boundary("A. B. C", 5, 7) is None
    assert module._find_sentence_boundary("A. B. C. D", 0, 5) == 3
    assert module._find_sentence_boundary("A. B. C. D", 0, 6) == 6
    assert module._find_sentence_boundary("A. B. C. D", 0, 9) == 9

    long_text = "".join(chr(65 + index % 26) for index in range(1000))
    default_chunks = module.chunk_text(long_text)
    assert len(default_chunks) == 2
    assert default_chunks[1] == long_text[680:]

    exact_chunks = module.chunk_text("abcdefghij", target_chars=6, overlap_chars=2)
    assert exact_chunks == ["abcdef", "efghij"]
    overlap_guard = module.chunk_text("abcdefghij", target_chars=3, overlap_chars=3)
    assert overlap_guard == ["abc", "bcd", "cde", "def", "efg", "fgh", "ghi", "hij"]
