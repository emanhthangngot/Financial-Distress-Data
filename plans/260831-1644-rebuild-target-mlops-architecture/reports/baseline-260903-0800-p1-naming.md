# Phase 1 Naming Cutover Baseline

**Captured:** 2026-09-03 08:00
**Tool:** `scripts/verify_naming_cutover.py`
**Repo:** `/home/pearspringmind/Studying/FSDS/Financial-Distress-Data`

## Result

```
path-name matches:  115
content matches:    724
total matches:      839
exit code:          1
```

839 hits before the cutover, across 639 scannable files (after exclusions).
Excluded paths (intentionally not scanned) per ADR-019 and P1 step 1:
`supabase/`, `plans/`, `.git/`, `__pycache__/`, `.venv*/`, `node_modules/`,
`mutants/`, `.next/`, `dist/`, `build/`, `out/`, `coverage/`, `.pnpm-store/`,
`.ruff_cache/`, `.pytest_cache/`, `.hypothesis/`,
`financial_distress_data.egg-info/`, `warehouse.db`, `.codex/`, `.agents/`,
`.claude/`, `images/`, `docs/` (whole tree — P1 class D handles docs).

## Highest-blast-radius surfaces

| Surface | Approx. hits | Cutover class |
|---|---:|---|
| `docker-compose.yml` | 22 | C |
| `AGENTS.md` | 38+ | AGENTS.md rewrite |
| `requirements-phase2.txt` | 4 (file + content) | C |
| `pyproject.toml` | ≥1 | C |
| `tests/phase2/**` | path + content | A |
| `dags/phase2/**`, `dags/stage1_*.py` | path + content | A |
| `scripts/*phase2*`, `scripts/*stage1*` | path + content | A |
| `sql/init_project_metadata.sql`, `sql/init_ml_metadata.sql` | file + content | D |
| `infra/phase1-cluster/**` | path | E (or D) |
| `apps/web/scripts/phase2/**` | path | A |
| `outputs/phase2/**` | path | A |

## Next step

P1 implementation step 2 — Rename class A: Python modules and packages.
Use `git mv` then a single project-wide identifier update; atomic commit;
`pytest tests -m "not slow"` must pass before commit.
