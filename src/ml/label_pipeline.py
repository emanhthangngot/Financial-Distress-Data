"""Phase 2 label table build.

Wraps ``src.transforms.compute_distress_labels.compute_labels`` (Phase 1,
read-only import — AGENTS.md forbids editing Phase 1) and reshapes its
output to the ``ml_metadata.label_table`` contract. Registered as offline
parquet + a Postgres row, never as a Feast FeatureView — see
``plans/260802-1037-unified-phase2-ml-llm-gitops/phase-04-implementation-notes.md``,
section 5, for why: a training-time label must never be reachable through
the online feature-serving path.
"""

from __future__ import annotations

from typing import Any

from src.transforms.compute_distress_labels import RULE_VERSION, compute_labels

LABEL_VERSION = f"altman-z-{RULE_VERSION}"
LABEL_SOURCE = "proxy_not_ground_truth"
PROXY_LABEL_NOTICE = (
    "label is a rule-based Altman Z''-Score proxy, not a ground-truth "
    "financial-distress outcome. Never present it to an end user as verified."
)


def build_labels(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute distress labels and project them to the label_table schema
    (ticker, event_timestamp, label, label_version, created_ts,
    training_eligible, label_source). Deterministic: identical input yields
    identical output on every call."""
    computed = compute_labels(rows)
    return [
        {
            "ticker": row["ticker"],
            "event_timestamp": row["event_timestamp"],
            "label": row["distress_label"],
            "label_version": LABEL_VERSION,
            "created_ts": row["created_ts"],
            "training_eligible": row["training_eligible"],
            "label_source": LABEL_SOURCE,
        }
        for row in computed
    ]


# write_labels_parquet / write_labels_postgres are deferred (YAGNI) to
# whichever slice first calls build_labels from a DAG — sql/init_ml_metadata.sql
# already defines the target ml_metadata.label_table schema (ticker,
# event_timestamp, label, label_version, created_ts, training_eligible,
# label_source; PK (ticker, event_timestamp, label_version); upsert keeping
# the latest created_ts per AGENTS.md's dedupe rule), and the psycopg import
# there must stay lazy per D4 (phase-04-implementation-notes.md section 0).
