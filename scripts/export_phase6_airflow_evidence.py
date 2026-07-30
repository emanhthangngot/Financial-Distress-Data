#!/usr/bin/env python3
"""Export DP1/DP2/DP3 run and task states from the Airflow metadata database."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DAG_IDS = (
    "ingest_source_to_bronze",
    "build_silver_gold",
    "build_offline_features",
)


def export(dsn: str) -> dict:
    """Return latest successful run and task states for each rubric DAG."""
    import psycopg2

    pipelines = {}
    with psycopg2.connect(dsn) as connection, connection.cursor() as cursor:
        for dag_id in DAG_IDS:
            cursor.execute(
                """
                SELECT run_id, state, execution_date, start_date, end_date
                FROM dag_run
                WHERE dag_id = %s AND state = 'success'
                ORDER BY execution_date DESC
                LIMIT 1
                """,
                (dag_id,),
            )
            run = cursor.fetchone()
            if not run:
                raise RuntimeError(f"no successful Airflow run found for {dag_id}")
            cursor.execute(
                """
                SELECT task_id, state, try_number
                FROM task_instance
                WHERE dag_id = %s AND run_id = %s
                ORDER BY task_id
                """,
                (dag_id, run[0]),
            )
            pipelines[dag_id] = {
                "run_id": run[0],
                "state": run[1],
                "execution_date": run[2].isoformat(),
                "start_date": run[3].isoformat() if run[3] else None,
                "end_date": run[4].isoformat() if run[4] else None,
                "tasks": [
                    {"task_id": task_id, "state": state, "try_number": try_number}
                    for task_id, state, try_number in cursor.fetchall()
                ],
            }
    all_success = all(
        pipeline["state"] == "success"
        and pipeline["tasks"]
        and all(task["state"] == "success" for task in pipeline["tasks"])
        for pipeline in pipelines.values()
    )
    return {
        "schema_version": 1,
        "status": "pass" if all_success else "fail",
        "pipelines": pipelines,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = export(args.dsn)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
