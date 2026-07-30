#!/usr/bin/env python3
"""Audit or emit DP1/DP2/DP3 governance metadata to DataHub."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.governance.datahub_emitter import emit_governance  # noqa: E402
from src.governance.datahub_graphql import (  # noqa: E402
    upsert_data_contracts,
    verify_governance_entities,
)
from src.governance.datahub_model import (  # noqa: E402
    audit_governance_model,
    load_governance_model,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/datahub/governance.yaml"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--server", default="http://localhost:8080")
    parser.add_argument("--token")
    parser.add_argument("--emit", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    model = load_governance_model(args.config)
    report = audit_governance_model(model)
    report["run_id"] = args.run_id
    if args.emit:
        from datahub.sdk import DataHubClient

        client = DataHubClient(server=args.server, token=args.token)
        report = emit_governance(model, client, args.run_id)
        report["contract_urns"] = upsert_data_contracts(
            args.server, report["contracts"], token=args.token
        )
        report["verification"] = verify_governance_entities(
            args.server, report["contracts"], token=args.token
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
