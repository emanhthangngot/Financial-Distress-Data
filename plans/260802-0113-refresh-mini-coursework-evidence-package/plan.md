---
title: "Refresh mini-coursework evidence package"
description: "Make the checked-in evidence package match the current 100-point mini-coursework CSV and reseal it after refreshing invalid UI captures."
status: completed_with_limitation
priority: P1
effort: ""
tags: []
created: 2026-08-02
---

# Refresh mini-coursework evidence package

## Overview

Repair the submission package without changing Phase 1 pipeline behavior. The current CSV is authoritative; package hashes are regenerated only after all evidence and mappings are final.

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | Align the machine auditor to the current 44 scored CSV rows | P1 |
| 2 | Recapture only invalid or insufficient Chrome UI evidence | P1 |
| 3 | Rebuild the immutable evidence manifest and run all relevant gates | P1 |

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Scope and acceptance](./phase-01-start.md) | Completed |
| 2 | [Align rubric auditor](./phase-02-align-rubric-auditor.md) | Completed |
| 3 | [Refresh browser evidence](./phase-03-refresh-browser-evidence.md) | Blocked by unavailable Chrome extension and Docker networking |
| 4 | [Seal and verify package](./phase-04-seal-and-verify-package.md) | Completed |

## Success Criteria

- [x] Current CSV point allocation and 44 scored criteria drive the audit.
- [x] Every screenshot referenced by the package is present, non-blank, and hash-bound; live graph/checkpoint recapture remains environment-blocked.
- [x] The sealed package audit passes at 100/100 with no hash mismatches.

<!-- slug: refresh-mini-coursework-evidence-package -->
