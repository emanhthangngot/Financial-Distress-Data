---
title: "Phase 3: Live service and browser QA"
status: completed
---

# Phase 3: Live service and browser QA

## Overview

Validate live service readiness and browser behavior through Playwright plus Chrome DevTools MCP, including console/network, accessibility, responsive, and performance checks.

## Requirements

- [x] Live platform .unner confirms required workloads, model gateway, coordinator, Prometheus, and Jaeger.
- [x] Critical web routes render expected content; the observed `/sign-out` 404 is recorded as a P1 finding.
- [x] Assistant happy path and timeout/policy/malformed-response states behave as documented.
- [x] Desktop and mobile layouts have no material horizontal overflow.

## Implementation Steps

1. Start the minimum reproducible web runtime and confirm fixture/live environment variables.
2. Execute the live platform .2E runner.
3. Run existing Playwright role, assistant, surface, a11y, and live suites.
4. Attempt Chrome DevTools MCP; use Playwright/Chrome equivalent for snapshots, network requests, console messages, performance, and mobile emulation if the MCP cannot start in the environment.
5. Save screenshots and traces under the report directory or Playwright artifact directory.

## Todo

- [x] Analyst overview/company/compare/report routes.
- [x] Operations and agent registry role boundaries.
- [x] Assistant submit, streaming, cancellation, quota, plane-off, policy, malformed response.
- [x] Responsive widths and keyboard/focus flow.
- [x] Network/API and secret-leak checks.

## Success Criteria

Browser and live-service outcomes are reproducible and every observed failure is recorded with URL, action, evidence, and severity.
