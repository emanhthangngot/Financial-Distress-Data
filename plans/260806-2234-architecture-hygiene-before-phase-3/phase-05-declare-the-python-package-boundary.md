---
phase: 5
title: "Declare the Python package boundary"
status: pending
priority: P2
effort: "2h"
dependencies: [1]
---

# Phase 5: Declare the Python package boundary

## Overview

`pyproject.toml` has no `[build-system]` and declares no packages; the whole
Python tree only imports because `[tool.pytest.ini_options] pythonpath = ["."]`
injects the repo root. Nothing outside pytest run from the repo root can import
this code — including a future model or agent container image. Make the tree
installable.

## Requirements

- Functional: `pip install -e .` succeeds and `import src.ml.contracts` works
  from a working directory other than the repo root.
- Functional: `pytest` keeps passing with no test edits.
- Non-functional: no module is renamed and no import statement in `src/`,
  `dags/`, `tests/`, or `scripts/` changes.
- Non-functional: the Airflow image build is not slowed or altered.

## Architecture

Current state:

```toml
[project]
name = "financial-distress-data"
version = "0.1.0"
dependencies = ["pandas>=2.2", "pyyaml>=6.0"]
[project.optional-dependencies]
dev = [...]         # pytest, ruff, black, playwright
runtime = [...]     # duckdb, kafka-python, minio, pyarrow, psycopg, pyspark
[tool.pytest.ini_options]
pythonpath = ["."]  # <- the only reason imports resolve
```

No `[build-system]`. No `[tool.setuptools]`. `pip install -e .` has no backend to
call.

Target: add a build backend and declare `src` (plus its subpackages) as the
distributed package.

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]
```

**On the package being literally named `src`:** this is a known wart — `src` is
conventionally a layout directory, not an importable name, and a proper fix
renames it to `financial_distress` with a repo-wide import rewrite. That rewrite
touches every file in `src/`, `dags/`, `tests/`, and `scripts/`, and would churn
the platform .pec's file tables in `docs/mini_coursework.md`. Rejected for now
(YAGNI): declaring `src` as the package name buys full installability at ~5 lines
of config. Record the wart in `docs/architecture/repository-map.md` (phase 4) so
the decision is visible rather than accidental.

**`dags/` is deliberately excluded** from the distribution. Airflow discovers
DAGs by filesystem path via the compose bind mount, not by import; packaging them
would create a second, competing discovery path.

**Observed, not fixed here:** runtime dependency versions are declared in three
places that can drift —

| Manifest | Content |
|---|---|
| `pyproject.toml` `[project.optional-dependencies] runtime` | `duckdb>=1.1`, `kafka-python>=2.0`, `minio>=7.2`, `pyarrow>=17.0`, `psycopg[binary]>=3.2`, `pyspark>=3.5` (floors) |
| `requirements.txt` | overlapping floors, plus dev tools, minus `pyspark`/`kafka-python`/`minio` |
| `infra/airflow/Dockerfile:27-33` | exact pins (`duckdb==1.1.3`, `pyspark==3.5.6`, …) |

Consolidating them is a separate change with its own blast radius (CI installs
from `requirements.txt`; the image rebuild is expensive). This phase only
**documents** which manifest is authoritative for which consumer, in the
repository map. Do not rewrite the three manifests here.

## Related Code Files

- Modify: `pyproject.toml` (add `[build-system]`, `[tool.setuptools.packages.find]`)
- Modify: `.github/workflows/ci.yml` (add the installability check to the `test`
  job; leave the `contracts` job alone)
- Modify: `docs/architecture/repository-map.md` (dependency-manifest ownership +
  the `src`-as-package-name note) — created in phase 4; if phase 4 has not
  landed, put the note in `README.md` instead and move it later
- Modify: `.gitignore` if `*.egg-info/` is not already ignored

## Implementation Steps

1. Add `[build-system]` and `[tool.setuptools.packages.find]` to
   `pyproject.toml` exactly as shown above. Leave `[project]`,
   `[project.optional-dependencies]`, `[tool.black]`, `[tool.ruff]`, and
   `[tool.pytest.ini_options]` untouched.
2. Keep `pythonpath = ["."]` in the pytest config. It is redundant once the
   package is installed, but removing it would break a contributor who runs
   pytest without installing. Redundant and harmless beats a new setup step.
3. `.gitignore:12` already has `*.egg-info/`, so the editable install's
   `financial_distress_data.egg-info/` is covered. `build/` is **not** ignored —
   add it, since a non-editable `pip install .` or `python -m build` writes there.
4. Verify installability from outside the repo root — the whole point:
   ```bash
   .venv/bin/pip install -e .
   cd /tmp && /home/pearspringmind/Studying/FSDS/Financial-Distress-Data/.venv/bin/python \
     -c "import src.ml.contracts, src.llm.contracts, src.streaming.events; print('ok')"
   ```
5. Confirm nothing regressed:
   ```bash
   .venv/bin/python -m pytest tests
   .venv/bin/python scripts/run_stage1_quality_gates.py
   ```
6. Add the check to CI so it cannot silently rot. The target is the **`test`**
   job in `.github/workflows/ci.yml` (the workflow is *named* "Stage 1 CI"; the
   job id is `test`, and there is a second job `contracts` for the pnpm
   workspace — do not touch that one). Insert after the `Install dependencies`
   step and before `Stage 1 quality gates`, so a packaging break is attributed
   correctly:
   ```yaml
   - name: Package installability
     run: |
       pip install -e .
       cd /tmp && python -c "import src.ml.contracts; print('ok')"
   ```
   Note that `Install dependencies` installs from `requirements.txt` only, which
   is why the `[build-system] requires` isolated-build-env behavior in the risk
   section matters here.
7. Record in the repository map: which dependency manifest each consumer reads
   (CI -> `requirements.txt`; Airflow image -> `infra/airflow/Dockerfile` pins;
   local dev -> `pyproject.toml` extras), and the `src`-as-package-name decision.

## Success Criteria

- [ ] Developer -> runs `pip install -e .` -> exits 0 with a wheel-less editable
      install, no build backend error.
- [ ] Developer -> runs `python -c "import src.ml.contracts"` from `/tmp` ->
      prints ok.
- [ ] CI -> runs the `test` job in `.github/workflows/ci.yml` -> the packaging
      step passes on a clean runner.
- [ ] `pytest tests` -> same collected count and same pass result as the phase-1
      baseline, with zero test edits.
- [ ] Reader -> opens the repository map -> learns which dependency manifest is
      authoritative for CI, for the Airflow image, and for local dev.

## Risk Assessment

- Risk: `packages.find` with `include = ["src*"]` also sweeps up stray
  directories that happen to start with `src`. Mitigation: none exist today;
  verify with `python -c "from setuptools import find_packages; print(find_packages(include=['src*']))"`
  before committing, and confirm `dags`, `tests`, `scripts` are absent from the
  result.
- Risk: an editable install shadows the repo-root path and changes which copy of
  a module is imported during tests. Mitigation: editable installs resolve to the
  same on-disk files; step 5's full pytest run is the check.
- Risk: CI runners install from `requirements.txt`, which lacks `setuptools>=68`.
  Mitigation: `[build-system] requires` is fetched by pip in an isolated build
  env, independent of `requirements.txt`. If the runner is offline-restricted,
  add `setuptools>=68` to `requirements.txt`.
- Rollback: `git revert`; deleting the `[build-system]` table returns the repo to
  pytest-only importability. No code depends on the install.
