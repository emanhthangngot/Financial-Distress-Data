"""DAG 09 - Data governance lite (W21).

Runs ``src.quality.contract_checker`` for each DP and writes lineage +
validation evidence JSONs to ``docs/evidence/governance/``. The DAG is the
terminal task of each DP so the evidence is regenerated on every run.
"""

from __future__ import annotations

from pathlib import Path

from dags.utils.dag_utils import DEFAULT_ARGS, airflow_imports
from src.quality.contract_checker import load_contracts, write_dp_evidence

DAG, PythonOperator = airflow_imports()

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DOC = REPO_ROOT / "docs" / "07_data_contracts.md"
EVIDENCE_DIR = REPO_ROOT / "docs" / "evidence" / "governance"


def _make_check_callable(dp: str):
    """Bind ``dp`` into a closure for the PythonOperator."""

    def _check_contracts() -> dict:
        contracts = load_contracts(CONTRACTS_DOC)
        write_dp_evidence(contracts, dp, EVIDENCE_DIR)
        return {"dp": dp, "evidence_dir": str(EVIDENCE_DIR)}

    _check_contracts.__name__ = f"check_{dp}_contracts"
    return _check_contracts


if DAG is not None:
    with DAG(
        dag_id="09_data_governance",
        default_args=DEFAULT_ARGS,
        schedule=None,
        catchup=False,
        tags=["financial-distress", "stage-1", "governance"],
    ) as dag:
        check_dp1_contracts = PythonOperator(
            task_id="check_dp1_contracts",
            python_callable=_make_check_callable("dp1"),
        )
        check_dp2_contracts = PythonOperator(
            task_id="check_dp2_contracts",
            python_callable=_make_check_callable("dp2"),
        )
        check_dp3_contracts = PythonOperator(
            task_id="check_dp3_contracts",
            python_callable=_make_check_callable("dp3"),
        )
        check_dp1_contracts >> check_dp2_contracts >> check_dp3_contracts
