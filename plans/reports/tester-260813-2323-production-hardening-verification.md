# Production-hardening verification

Environment: `feat/production-hardening-overlay`, Linux, 2026-08-13.
No source or test files were modified.

## Results

| Check | Result |
|---|---|
| `.venv/bin/python -m pytest tests` | PASS — 311 passed in 1.89s |
| `.venv/bin/ruff check src dags tests scripts` | PASS |
| `.venv/bin/black --check src dags tests scripts` | PASS — 326 files unchanged |
| `docker compose config` | PASS |
| `audit_phase2_evidence.py --matrix-only --strict` | PASS |
| `audit_phase2_evidence.py --require-executed --track LLM --gitops-root ../financial-distress-gitops` | PASS |
| `audit_phase2_evidence.py --check-artifacts --track ML --track LLM --gitops-root ../financial-distress-gitops` | PASS |
| `scripts/run_phase2_quality_gates.py` | PASS — 72 passed, 1 skipped; shell syntax passed |
| sibling `make validate` | PASS — kubeconform unavailable (explicit non-fatal SKIP) |
| Ansible syntax (`ansible/`, both playbooks) | PASS — deprecation warnings only |
| `tests/phase2/test_rollout_evidence.py -q` | PASS — 2 passed |

The live rollout capture command exits `2` with `required cluster tools are missing: kubectl-argo-rollouts`; this is the expected fail-closed behavior when cluster tooling is unavailable.

Status: DONE
