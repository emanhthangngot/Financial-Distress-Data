"""Phase 2 Flink CDC contracts.

The package contains pure configuration, event-normalisation and reconciliation
helpers.  Connector clients are intentionally optional so the fast test loop
does not require Flink, Kafka or Postgres binaries.
"""

from .config import CDCConfig, CDCConfigError
from .reconcile import ReconciliationReport, reconcile, reconcile_paths

__all__ = [
    "CDCConfig",
    "CDCConfigError",
    "ReconciliationReport",
    "reconcile",
    "reconcile_paths",
]
