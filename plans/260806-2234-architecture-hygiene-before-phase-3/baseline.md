# Phase 1: Green baseline

- Date: 2026-08-06
- Git SHA: `315a6ec2aea0d151c429f4c072226e9214192b62`

## Gate results (`scripts/run_stage1_quality_gates.py`)

| Gate | Result |
|---|---|
| pytest (`tests`) | 514 passed in 6.32s |
| ruff (`src dags tests scripts`) | All checks passed! |
| black --check (`src dags tests scripts`) | pass (no output = clean) |
| docker compose config | valid (rendered without error) |
| stage1-evidence-audit | `"status": "pass"`, `"failed_checks": []` |

Overall: gate script exit 0 — full stdout captured in `/tmp/gate-baseline.txt`
(not committed, ephemeral; re-run the command below to reproduce).

Collected test count: `514 tests collected in 0.26s`
(`.venv/bin/python -m pytest tests --collect-only -q`)

## Structural inventory

### Tracked top-level directories/files

```
AGENTS.md
apps
.claude
CLAUDE.md
configs
dags
docker-compose.yml
docs
.env.example
flink
.github
.gitignore
images
infra
init
package.json
packages
plans
pnpm-lock.yaml
pnpm-workspace.yaml
pyproject.toml
README.md
requirements.txt
scripts
sql
src
supabase
tests
uv.lock
```

### Flink files (`flink/**`, `src/streaming/flink/**`)

```
flink/jobs/price_event_job.py
src/streaming/flink/__init__.py
src/streaming/flink/client.py
src/streaming/flink/jobs/README.md
```

### `flink/jobs` references (`git grep -n "flink/jobs" -- ':!plans'`)

```
docker-compose.yml:189:      - ./src/streaming/flink/jobs:/opt/flink/jobs:ro
docs/11_rubric_completion_spec.md:349:- `src/streaming/flink/jobs/README.md`
docs/evidence/final/coursework-final-20260731T0030/documents/flink.md:34,38
docs/evidence/final/coursework-final-20260802T0115/config/compose.yaml:189
docs/evidence/final/coursework-final-20260802T0115/documents/flink.md:34,38
docs/evidence/final/coursework-final-20260802T0130/config/compose.yaml:189
docs/evidence/final/coursework-final-20260802T0130/documents/flink.md:34,38
docs/evidence/rubric_coverage.json:211,222,232,242,252
docs/flink-stream-processing.md:34,38
scripts/_rubric_items.py:244,253,260,267,274
scripts/run_mini_coursework_submission.py:48
src/streaming/flink/jobs/README.md:4
```

Frozen `docs/evidence/final/coursework-final-*/` snapshots reference the old
mount path — those are historical evidence artifacts, not live wiring; phase 2
must not edit them (`documentation-management.md`: generated artifacts).

### `src.generators` import references (`git grep -n "src\.generators" -- ':!plans'`)

```
src/collectors/source_adapters/vnstock_fixture_adapter.py:16
src/jobs/stage1_evidence_job.py:23,24
tests/test_fixture_adapter_knobs.py:6
tests/test_generator_config.py:9
tests/test_streaming_problem_factory.py:9
```

### `pyproject.toml` packaging fields

```
pythonpath = ["."]
testpaths = ["tests"]
```

No `packages = [...]` declared — confirms plan claim (goal 4, phase 5) that the
tree is not currently installable as a package.

## Gate status

Green at this SHA. Refactor may proceed.

## Reproduce

```bash
.venv/bin/python scripts/run_stage1_quality_gates.py
.venv/bin/python -m pytest tests --collect-only -q | tail -3
```
