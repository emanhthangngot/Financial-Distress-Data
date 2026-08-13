---
title: "Phase 4: Coverage and report"
status: completed
---

# Phase 4: Coverage and report

## Overview

Consolidate automated, live, and browser evidence into a concise QA report following `ak:test` format.

## Requirements

- [x] Coverage percentages and thresholds are reported.
- [x] Failed/skipped tests list exact causes and impact.
- [x] UI screenshots, console, responsive, accessibility, and performance evidence are linked.
- [x] Unresolved questions and follow-up recommendations are explicit.

## Implementation Steps

1. Inspect test artifacts and coverage outputs.
2. Summarize results by test layer and feature.
3. Write the report under `plans/reports/` using the timestamped naming rule.
4. Update this plan status using the plan CLI after verification.

## Todo

- [x] QA report under 200 lines where practical.
- [x] Report links only safe, local evidence paths and does not expose secrets.

## Success Criteria

Report is complete, reproducible, and honest about blockers; no test result is omitted.
