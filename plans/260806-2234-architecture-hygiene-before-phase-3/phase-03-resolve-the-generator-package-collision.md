---
phase: 3
title: "Resolve the generator package collision"
status: pending
priority: P1
effort: "2-3h"
dependencies: [1]
---

# Phase 3: Resolve the generator package collision

## Overview

`src/generator/` and `src/generators/` are one letter apart and both export
`GeneratorConfig`, `load_generator_config`, and `StreamingConfig` with different
schemas. Split them by what they actually are, so no import can silently pick the
wrong one.

## Requirements

- Functional: no two importable modules export the same public name with a
  different shape.
- Functional: every existing caller keeps working, with updated imports.
- Non-functional: no change to generated data, config file formats, or the YAML
  files under `configs/`.
- Non-functional: no test expected-value edits (AGENTS.md).

## Architecture

**What each package actually is** (verified 2026-08-06):

| | `src/generator/` (585 lines) | `src/generators/` (391 lines) |
|---|---|---|
| Purpose | deterministic offline + streaming data generation | fixture-adapter tuning knobs + streaming problem events |
| Modules | `config.py`, `offline.py`, `streaming.py`, `storage.py`, `profile.py` | `config_loader.py`, `streaming_problem_factory.py` |
| Config source | `configs/generator-config.yaml`, profile-aware (`load_generator_config(path, profile="evidence")`) | `configs/collector_config.yaml` (`DEFAULT_CONFIG_PATH`) |
| Config shape | `OfflineConfig`, `StreamingConfig`, `OutputConfig` | `SkewConfig`, `CardinalityConfig`, `EvolutionConfig`, `DuplicationConfig`, `BurstConfig`, `LateArrivalConfig`, `StreamingConfig` |
| Callers | `scripts/run_generator_and_profile.py`, `scripts/run_flink_benchmark.py` | `src/collectors/source_adapters/vnstock_fixture_adapter.py`, `src/jobs/stage1_evidence_job.py`, 3 test files |

Colliding names: `GeneratorConfig`, `load_generator_config`, `StreamingConfig`.

**Target split.** The two modules in `src/generators/` do not belong together and
neither belongs beside `src/generator/`:

```
src/generator/                         unchanged — keeps GeneratorConfig, load_generator_config
src/collectors/fixture_config.py       <- src/generators/config_loader.py
                                          renamed symbols: FixtureGeneratorConfig,
                                          load_fixture_config; sibling dataclasses
                                          (SkewConfig, CardinalityConfig, ...) keep
                                          their names — they never collided
                                          StreamingConfig -> FixtureStreamingConfig
src/streaming/problem_factory.py       <- src/generators/streaming_problem_factory.py
                                          no symbol renames; it already imports
                                          src.streaming.events.StreamEvent, so this
                                          is where it belonged
src/generators/                        deleted
```

Rationale for each destination:

- `config_loader.py` reads `configs/collector_config.yaml` and its only two
  non-test callers are the vnstock fixture adapter and the stage-1 evidence job.
  It configures how the **collector fixture** behaves. `src/collectors/` owns it.
- `streaming_problem_factory.py` builds `StreamEvent`s from
  `src.streaming.events`. `src/streaming/` owns it. Dropping the redundant
  `streaming_` prefix once it lives under `src/streaming/` is DRY, not churn.

**A rubric evidence check depends on the moved file.** `scripts/_rubric_items.py:130-133`
scores rubric row 7 ("Generator is driven by configuration", 2 points) with:

```python
evidence_check=lambda: _exists_any(
    "src/generators/config_loader.py", "src/generator/config.yaml"
),
```

`src/generator/config.yaml` does not exist. The check therefore passes on the
first path alone — the exact file this phase moves. Moving it without updating
this line silently drops 2 rubric points. Validation session 1 decided to repoint
it at both real files, which also retires the dead second path:

```python
evidence_check=lambda: _exists_any(
    "src/collectors/fixture_config.py", "configs/generator-config.yaml"
),
```

**Rejected alternative:** merge the two `GeneratorConfig` classes into one. They
read different YAML files with disjoint schemas for different consumers. Merging
would invent a union type nothing wants (YAGNI) and would change the config
contract for both callers.

## Related Code Files

- Create: `src/collectors/fixture_config.py` (moved from `src/generators/config_loader.py`)
- Create: `src/streaming/problem_factory.py` (moved from `src/generators/streaming_problem_factory.py`)
- Modify: `src/collectors/source_adapters/vnstock_fixture_adapter.py:16`
- Modify: `src/jobs/stage1_evidence_job.py:23-24`
- Modify: `tests/test_fixture_adapter_knobs.py:6`
- Modify: `tests/test_generator_config.py:9`
- Modify: `tests/test_streaming_problem_factory.py:9`
- Modify: `scripts/_rubric_items.py:130-133` — **load-bearing**, see below
- Delete: `src/generators/` (`__init__.py`, `config_loader.py`, `streaming_problem_factory.py`)

## Implementation Steps

1. `git mv src/generators/config_loader.py src/collectors/fixture_config.py`
2. `git mv src/generators/streaming_problem_factory.py src/streaming/problem_factory.py`
3. `git rm src/generators/__init__.py` and remove the empty directory. Fold the
   useful half of its docstring (the rubric-row-2 note) into the two destination
   module docstrings — do not lose the rubric traceability.
4. In `src/collectors/fixture_config.py`, rename only the three colliding names:
   - `GeneratorConfig` -> `FixtureGeneratorConfig`
   - `load_generator_config` -> `load_fixture_config`
   - `StreamingConfig` -> `FixtureStreamingConfig` (and its `_build_streaming`
     return annotation)
   Leave `SkewConfig`, `CardinalityConfig`, `EvolutionConfig`,
   `DuplicationConfig`, `BurstConfig`, `LateArrivalConfig`, `DEFAULT_CONFIG_PATH`
   and every private helper unchanged.
5. Update the 5 caller files to the new module paths and symbol names. Exact
   current import sites:
   - `src/collectors/source_adapters/vnstock_fixture_adapter.py:16` —
     `from src.generators.config_loader import GeneratorConfig` (inside a
     `TYPE_CHECKING`/try block; keep that structure)
   - `src/jobs/stage1_evidence_job.py:23-24` — both `load_generator_config` and
     the `streaming_problem_factory` symbols
   - the 3 test files listed above
6. Update the `config_loader.py` docstring's stale reference to
   `configs/generator/*.yaml` — no such directory exists; the real default is
   `configs/collector_config.yaml`.
7. Repoint the rubric evidence check at `scripts/_rubric_items.py:130-133` to
   `_exists_any("src/collectors/fixture_config.py", "configs/generator-config.yaml")`.
   Do this in the **same commit** as the move — between the two, rubric row 7
   scores zero.
8. Verify no orphan references, no name exported twice, and no lost rubric points:
   ```bash
   git grep -n "src\.generators\|src/generators" -- ':!plans'   # must return nothing
   git grep -n "load_generator_config\|GeneratorConfig" -- ':!plans'
   .venv/bin/python -m pytest tests -k "generator or fixture_adapter or problem_factory"
   .venv/bin/python -m pytest tests -k "rubric"                 # rubric row 7 still scores
   .venv/bin/python scripts/run_stage1_quality_gates.py
   ```
   Note the grep now covers the **path** form `src/generators` as well as the
   import form — the rubric check referenced it as a path string, which an
   import-only grep would have missed.

## Success Criteria

- [ ] Developer -> `git grep "class GeneratorConfig"` -> exactly one hit,
      `src/generator/config.py`.
- [ ] Developer -> `git grep "src\.generators"` -> zero hits outside `plans/`.
- [ ] `pytest tests -k "generator or fixture_adapter or problem_factory"` ->
      same pass count as the phase-1 baseline, with zero expected-value edits.
- [ ] `ruff check src dags tests scripts` -> clean (catches every missed import).
- [ ] Rubric auditor -> runs the rubric coverage tests -> row 7 ("Generator is
      driven by configuration") still scores 2 points, now against two paths that
      both exist.
- [ ] `scripts/run_stage1_quality_gates.py` -> same result as the phase-1 baseline.

## Risk Assessment

- Risk: a dynamic import or a string-based module reference is missed by grep.
  Mitigation: `ruff` + the full pytest run in step 8; also grep for the bare
  strings `"generators"` and `'generators'` before declaring done.
- Risk: renaming `GeneratorConfig` in the fixture path breaks a type annotation
  in `vnstock_fixture_adapter.py` that is only evaluated under `TYPE_CHECKING`
  and therefore not caught at runtime. Mitigation: the annotation is a quoted
  forward reference — grep for `"GeneratorConfig"` as a string literal too.
- Risk: **confirmed, not hypothetical** — `scripts/_rubric_items.py:132` cites
  `src/generators/config_loader.py` as the evidence path for a scored rubric row,
  and its `_exists_any` fallback path does not exist. Mitigation: step 7 repoints
  it in the same commit; step 8 re-runs the rubric tests. This was found by
  path-string grep, not import grep — a plain `src\.generators` search misses it.
- Rollback: single commit, `git revert`. No data or config file format changed.
