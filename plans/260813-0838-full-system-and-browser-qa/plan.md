---
title: "Full system and browser QA"
description: "Run the repository's full Phase 1/Phase 2 test contracts plus detailed Chrome DevTools and Playwright QA for user-facing flows."
status: completed
priority: P1
effort: ""
tags: []
created: 2026-08-13
---

# Full system and browser QA

## Overview

Validate the implemented coursework surface without changing product code: backend contracts, web unit/integration tests, build/type/lint gates, existing Playwright suites, live Phase 2 service readiness, and detailed browser behavior.

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | Validate Phase 1 and Phase 2 automated contracts and coverage | P1 |
| 2 | Validate all documented web pages, role boundaries, assistant flows, accessibility, responsive behavior, and error states | P1 |
| 3 | Record reproducible evidence, failures, skips, and unresolved questions | P1 |

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Phase 1: Scope and preflight](./phase-01-start.md) | Completed |
| 2 | [Phase 2: Code and contract suite](./phase-02-code-and-contract-suite.md) | Completed |
| 3 | [Phase 3: Live service and browser QA](./phase-03-live-service-and-browser-qa.md) | Completed |
| 4 | [Phase 4: Coverage and report](./phase-04-coverage-and-report.md) | Completed |

## Success Criteria

- [x] Phase 1/2 pytest contracts pass or every failure is recorded with cause.
- [x] Web typecheck, lint, build, Vitest and Playwright suites complete with no unexplained failures.
- [x] Chrome DevTools MCP was attempted; Playwright/Chrome equivalent verified console, network, accessibility, responsive, and performance signals when MCP could not start without X.
- [x] Report is saved under `plans/reports/test-report-260813-0836-full-system-browser-qa.md`.

## Acceptance criteria

- Repository test suite -> executes Phase 1 and Phase 2 contracts -> results include pass/fail/skip counts and failure diagnostics.
- Web package -> runs typecheck, lint, build, Vitest, and Playwright -> all completed results are recorded without suppressing failures.
- Browser QA -> visits documented analyst, company, assistant, operations, registry, and error routes -> each route has functional, console, network, and responsive evidence.
- Accessibility/performance checks -> run against critical pages -> violations and budgets are recorded with severity.
- QA report -> summarizes evidence and unresolved questions -> another operator can reproduce the commands and browser checks.

<!-- slug: full-system-and-browser-qa -->
