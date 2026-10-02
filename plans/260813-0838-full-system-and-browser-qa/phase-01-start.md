---
title: "Phase 1: Scope and preflight"
status: completed
---

# Phase 1: Scope and preflight

## Overview

Read the active platform/platform specifications, final LLM rubric, existing test/config surfaces, and unfinished plans. Define the QA matrix without modifying product code.

## Requirements

- [x] platform scope is `docs/mini_coursework.md` plus repository quality gates.
- [x] platform scope is `docs/coursework.md`, `docs/phase2/rubric-matrix.md`, final LLM rubric, and existing platform tests.
- [x] Browser scope covers all routes represented by `apps/web/e2e/` and critical navigation/assistant/error flows.

## Implementation Steps

1. Inventory package scripts, Playwright configs, routes, fixtures, and test groups.
2. Separate deterministic fixture tests from live GKE/service tests.
3. Create the timestamped QA plan and report path.

## Todo

- [x] Read testing skill and browser testing references.
- [x] Confirm Chrome DevTools MCP and Playwright tooling are available.

## Success Criteria

Scope and reproducible commands are documented before execution.
