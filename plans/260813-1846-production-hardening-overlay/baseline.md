# Production hardening baseline

Captured on 2026-08-13 before source changes on branch
`feat/production-hardening-overlay`.

| Check | Result | Command |
|---|---|---|
| platform .atrix | PASS — ML 100/100 (57 rows), LLM 100/100 (60 rows) | `python scripts/audit_phase2_evidence.py --matrix-only --strict` |
| Fast loop | PASS — 311 passed | `uv run --offline python -m pytest tests -q` |
| Compose config | PASS | `docker compose config` |
| Stage 1 evidence audit | PASS | `uv run --offline python scripts/audit_stage1_evidence.py docs/evidence --check` |
| Ruff | PASS before this overlay | `uv run --offline ruff check src dags tests scripts` |
| Black | PASS before this overlay | `uv run --offline black --check src dags tests scripts` |

The repository wrapper `scripts/run_stage1_quality_gates.py` was not used for
the baseline because invoking it with the system interpreter resolves a Python
without pytest; the equivalent gates above run in the project uv environment.
This is an environment issue, not a relaxed quality gate.

Source HEAD: `620975d1e070703f7744e759f57f26ef27443a98` (`docs(phase2): record rag ci fix evidence`)

GitOps HEAD: `32483a1bb9775c95047836864e6b2dbef6adb9bf` (sibling checkout `financial-distress-gitops`)

The frozen evidence revision used by the current LLM submission remains
`6ee3175073333df7ed3ed6737bc6c2ac65e6a0a8`; the final promotion gate must keep
that SHA ancestry/frozen-revision contract intact until evidence is re-stamped.
