---
title: "Phase 4: Run full gates and record evidence"
status: complete
---

# Phase 4: Run full gates and record evidence

## Overview

Run the narrow-to-broad quality gates and leave a reproducible implementation
report without modifying generated evidence artifacts.

## Requirements

- [x] Web -> runs focused tests, typecheck, lint, build, and the relevant
  Playwright suites -> no unexplained failure remains.
- [x] Repository -> runs the applicable Phase 1/platform .ontract gate -> the
  auth route change causes no cross-module regression.
- [x] Report -> records commands, counts, screenshots/logs if produced, and
  the intentional no-sign-up decision.

## Implementation Steps

1. Run targeted auth Vitest and live Playwright first.
2. Run web typecheck/lint/build and the full web test suite.
3. Run the repository quality gate required by `AGENTS.md` and record any
   environment-only skips honestly.
4. Write the report under `plans/reports/`.

## Todo

- [x] Execute all applicable verification commands.
- [x] Resolve or explain every failure.
- [x] Save the final report and sync plan status.

## Success Criteria

All required evidence is reproducible, the implementation is reviewed by the
mandatory tester/debugger/code-reviewer workflow, and the plan has no stale
phase status.
