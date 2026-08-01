---
title: "Phase 3: Refresh browser evidence"
status: blocked
---

# Phase 3: Refresh browser evidence

## Overview

Use Chrome to capture valid Flink restart/checkpoint evidence and Airflow graph views that visibly demonstrate stage ordering.

## Requirements

- [x] Do not substitute generated images for live UI captures.
- [x] Retain existing checked-in screenshots only when they are non-blank and visibly tied to the linked UI evidence.

## Implementation Steps

1. Open local Airflow and Flink in Chrome.
2. Capture graph/checkpoint pages and verify output is non-blank.

## Todo

- [x] Remove the blank Flink restart/checkpoint capture from the sealed package.
- [x] Use the newest checked-in Airflow captures in the sealed package.
- [ ] Capture fresh graph/checkpoint pages: blocked because the Chrome extension is absent and Docker bridge networking cannot create veth interfaces in this environment.

## Success Criteria

Reviewer -> opens each screenshot -> can see non-blank runtime UI evidence; fresh graph/checkpoint proof requires rerunning in an environment with Chrome extension and Docker networking.
