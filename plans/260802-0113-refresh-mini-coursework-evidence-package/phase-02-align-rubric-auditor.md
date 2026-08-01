---
title: "Phase 2: Align rubric auditor"
status: completed
---

# Phase 2: Align rubric auditor

## Overview

Update the rubric requirements, mapping, and tests so the current CSV weights drive audit results.

## Requirements

- [x] Keep README/deployment evidence mandatory but non-scored, matching the CSV.
- [x] Preserve all 100 current rubric points and proof-type contracts.

## Implementation Steps

1. Update requirements and evidence IDs/points.
2. Add a test that derives scored criteria and point total from the CSV.

## Todo

- [x] Update auditor config and mappings.
- [x] Run focused tests.

## Success Criteria

Rubric audit -> evaluates 44 scored criteria -> totals exactly 100 points from the current CSV.
