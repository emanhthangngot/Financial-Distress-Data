# platform .aming Cutover Baseline

**Captured:** 2026-09-03
**Tool:** `scripts/verify_naming_cutover.py`
**Repo:** `/home/pearspringmind/Studying/FSDS/Financial-Distress-Data`

## Initial baseline (2026-09-03 08:00)

```
path-name matches:  115
content matches:    724
total matches:      839
exit code:          1
scannable files:    639
```

839 hits before the cutover. Excluded paths (intentionally not scanned) per
ADR-019 and P1 step 1: `supabase/`, `plans/`, `.git/`, `__pycache__/`,
`.venv*/`, `node_modules/`, `mutants/`, `.next/`, `dist/`, `build/`, `out/`,
`coverage/`, `.pnpm-store/`, `.ruff_cache/`, `.pytest_cache/`, `.hypothesis/`,
`financial_distress_data.egg-info/`, `warehouse.db`, `.codex/`, `.agents/`,
`.claude/`, `images/`, `docs/` (whole tree — class D handles docs).

## After class A (`c88718a`, 2026-09-03)

```
path-name matches:  16
content matches:    616
total matches:      632
exit code:          1
```

Drop: 207 hits (-25%). All 17 scripts/ renames, dags/ flatten + stage1 rename,
`src/governance/phase2_lineage.py`, `tests/platform/`→`tests/platform/`,
`apps/web/scripts/phase2/`→`platform/`, `outputs/phase2/`→`evidence/` landed
with `git mv`. Identifier updates in scripts/dags/src/tests + authorized docs
hrefs. Fast pytest: 318 passed, 0 skipped, 1.52s.

## Highest-blast-radius surfaces (pre-class A estimate)

| Surface | Approx. hits | Cutover class |
|---|---:|---|
| `docker-compose.yml` | 22 | B |
| `AGENTS.md` | 38+ | AGENTS.md rewrite |
| `requirements-phase2.txt` | 4 (file + content) | B |
| `pyproject.toml` | ≥1 | B |
| `tests/platform/**` | path + content | A ✅ |
| `dags/phase2/**`, `dags/stage1_*.py` | path + content | A ✅ |
| `scripts/*phase2*`, `scripts/*stage1*` | path + content | A ✅ |
| `sql/init_ops.sql`, `sql/init_ml.sql` | file + content | C |
| `infra/phase1-cluster/**` | path | D |
| `apps/web/scripts/phase2/**` | path | A ✅ |
| `outputs/phase2/**` | path | A ✅ |

## Remaining after class A

| Surface | Class | Notes |
|---|---|---|
| `docker-compose.yml` | B | service names, env vars, image tags |
| `AGENTS.md` | rewrite | full prose rewrite, separate step |
| `requirements-phase2.txt` | B | rename to `requirements-platform.txt` + content |
| `pyproject.toml` | B | pytest markers, package paths, optional-deps |
| `sql/init_ops.sql` → `sql/init_ops.sql` | C | schema rename |
| `sql/init_ml.sql` → `sql/init_ml.sql` | C | schema rename |
| `infra/phase1-cluster/` → `infra/lakehouse-cluster/` | D | path rename |
| `.github/workflows/phase2-*.yaml` | rewrite | prefix drop |
| Postgres schema names referenced in Python (class C) | C | forward migration required |
| Env vars `PHASE2_*` | B | rename to `PLATFORM_*` |

## Next step

P1 step 3 — Rename class B: configs, venv, requirements, env-vars,
docker-compose. `pyproject.toml` carries `[project.optional-dependencies]`
after the requirements file is folded in. `docker-compose.yml` profile names,
service names, env-var names, and image tags all change. `.env*` files in
working tree must be updated to match. One atomic commit.
