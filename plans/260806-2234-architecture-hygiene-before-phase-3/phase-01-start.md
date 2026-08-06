---
phase: 1
title: "Capture the green baseline"
status: pending
priority: P1
effort: "0.5h"
dependencies: []
---

# Phase 1: Capture the green baseline

## Overview

Record the exact pass/fail state of every quality gate before any file moves, so
phases 2-6 can prove they changed structure without changing behavior. A refactor
without a baseline is a guess.

## Requirements

- Functional: a committed baseline artifact holding the current gate output and
  the current structural inventory.
- Non-functional: the capture is reproducible by re-running one command; no
  hand-typed numbers.

## Architecture

Baseline lives in the plan directory, not in `docs/` — it is a stateful record of
one refactor, not evergreen product documentation
(`documentation-management.md`: plans and reports are stateful records).

Two captures:

1. **Gate baseline** — stdout of `scripts/run_stage1_quality_gates.py`, plus the
   pytest collected-test count.
2. **Structural inventory** — the tracked-file facts each later phase changes, so
   a later phase can diff instead of re-deriving: tracked top-level directories,
   the Flink file/mount facts, the generator symbol collision, `pyproject.toml`
   packaging fields.

## Related Code Files

- Create: `plans/260806-2234-architecture-hygiene-before-phase-3/baseline.md`
- Modify: none
- Delete: none

## Implementation Steps

1. Run the gate and capture verbatim:
   ```bash
   .venv/bin/python scripts/run_stage1_quality_gates.py 2>&1 | tee /tmp/gate-baseline.txt
   .venv/bin/python -m pytest tests --collect-only -q | tail -3
   ```
   Do **not** pass `--include-services`; it needs the Docker stack up (AGENTS.md
   time-costly list) and this baseline must be cheap enough to re-run per phase.
2. Capture the structural inventory:
   ```bash
   git ls-files | awk -F/ '{print $1}' | sort -u
   git ls-files 'flink/**' 'src/streaming/flink/**'
   git grep -n "flink/jobs" -- ':!plans'
   git grep -n "src\.generators" -- ':!plans'
   git grep -nE "^  (packages|pythonpath|testpaths)" pyproject.toml
   ```
3. Write `baseline.md` with: date, git SHA (`git rev-parse HEAD`), gate result
   per gate, collected test count, and the inventory output.
4. If the gate is **not** green at baseline, stop. Fix the pre-existing failure
   as its own change first; do not start a refactor on a red tree.

## Success Criteria

- [ ] Maintainer -> opens `baseline.md` -> finds the git SHA, per-gate result,
      and collected test count for the pre-refactor tree.
- [ ] `scripts/run_stage1_quality_gates.py` -> exits 0 at the recorded SHA.
- [ ] Every later phase -> re-runs the same command -> compares against this file
      rather than against memory.

## Risk Assessment

- Risk: the tree is already red and the refactor gets blamed for it.
  Mitigation: step 4 hard-stops on a red baseline.
- Risk: baseline goes stale if phases land days apart. Mitigation: the capture is
  one command; re-run and note the new SHA if more than one phase's work
  intervenes.
