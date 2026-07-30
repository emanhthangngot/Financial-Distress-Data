"""W9 — DAG 06 / compute_distress_label must document the staging→fact→label
dependency chain.

W9 AC: ``compute_distress_label`` reads source-of-truth columns from a
typed dim/fact intermediate (or staging view) and documents the
dependency in its docstring. The current implementation accepts a
flattened fact row; the docstring must at minimum spell out the
column-source contract so the staging→fact→label chain is explicit.
"""

from __future__ import annotations

import inspect

from src.transforms.compute_distress_labels import compute_distress_label


def test_compute_distress_label_docstring_documents_column_sources():
    """Function docstring must list the required columns and the data-flow stage."""
    doc = inspect.getdoc(compute_distress_label) or ""
    assert doc.strip(), "compute_distress_label must have a docstring (W9 AC)."
    lower = doc.lower()
    # Must mention the dependency chain: staging → fact → label, or at least
    # the source-of-truth column set.
    chain_mentioned = any(
        token in lower
        for token in ("staging", "fact", "intermediate", "source-of-truth", "source of truth")
    )
    assert chain_mentioned, (
        "compute_distress_label docstring must document the staging→fact→label "
        "dependency chain or the source-of-truth column set (W9 AC)."
    )


def test_compute_distress_label_docstring_lists_required_columns():
    """The docstring must enumerate the columns the labeler reads (at least ticker)."""
    doc = inspect.getdoc(compute_distress_label) or ""
    for col in ("ticker", "report_period", "total_assets", "total_liabilities"):
        assert col in doc, (
            f"compute_distress_label docstring must mention column '{col}' "
            f"so the staging→fact contract is explicit (W9 AC). Found doc:\n{doc}"
        )
