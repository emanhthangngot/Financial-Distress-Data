---
title: "Phase 4: Seal and verify package"
status: completed
---

# Phase 4: Seal and verify package

## Overview

Regenerate the signed evidence manifest and all derived reports after the final evidence state is complete.

## Requirements

- [x] Include every required package artifact and exclude stale references.
- [x] Verify tests, package audit, and quality checks.

## Implementation Steps

1. Rebuild the manifest and generated index/report.
2. Run the 100-point audit and focused/full tests.

## Todo

- [x] Seal after all screenshot/mapping changes.
- [x] Confirm zero hash mismatches.

## Success Criteria

Submission auditor -> runs with --require-score 100 -> exits zero with a verified 100/100 package.
