---
title: "Phase 2: Code and contract suite"
status: completed
---

# Phase 2: Code and contract suite

## Overview

Run all deterministic Python and TypeScript validation available in the repository, including platform .ubric requirement tests, web coverage, static checks, and production build.

## Requirements

- [x] Full Python pytest and Stage 1 quality gate pass.
- [x] platform .pp/agent/product/requirement suites pass in `.venv-phase2` where required.
- [x] Web Vitest, typecheck, lint, and build pass.
- [x] Existing Playwright configurations complete.

## Implementation Steps

1. Run preflight commands and package dependency checks.
2. Run Python full suite, platform .uites, and rubric-specific tests.
3. Run web Vitest with coverage, typecheck, lint, and production build.
4. Run Playwright configs by fixture/live mode and preserve artifacts.

## Todo

- [x] Capture exact totals and skipped-test reasons.
- [x] Investigate every failure enough to classify product bug, test bug, or environment blocker.

## Success Criteria

All deterministic suites have a recorded exit status; no failing test is hidden or reclassified as pass.
