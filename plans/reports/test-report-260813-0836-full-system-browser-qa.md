---
title: "Full system and browser QA"
date: 2026-08-13
scope: "Phase 1, Phase 2 LLM track, web UI, live service path"
status: "PASS; UI FINDING RESOLVED IN PR #75"
---

# Test Report — 2026-08-13 — Full system and browser QA

## Test Results Overview

| Layer | Result |
|---|---|
| Stage 1 Python gate | **311 passed**; Ruff, Black, Compose config, evidence audit passed |
| Phase 2 Python suite | **510 passed, 35 skipped**; skips are dependency/infra-marked |
| Web Vitest | **183 passed**; 92.91% statements, 90.10% branches, 90.99% functions |
| `@distresslens/contracts` | **86 passed**; 100% statements, 97.7% branches, 100% functions |
| Web typecheck/lint/build | **PASS** |
| Playwright fixture + role + assistant + a11y | **102 passed** |
| Playwright live Supabase smoke | **3 passed** |
| Live Phase 2 service runner | **PASS** |
| LLM evidence matrix audit | **PASS** (non-promotion mode) |

## Playwright/UI Results

- Default analyst suite: **60/60** across desktop 1440, tablet 1024, mobile 390.
- Operator/plane-off suite: **16/16** across desktop and mobile.
- Assistant streaming/error suite: **6/6** — streaming, timeout, refusal, malformed response, cancel, secret redaction.
- Assistant quota: **1/1**.
- Assistant plane-off: **1/1**.
- Accessibility analyst: **9/9**.
- Accessibility operator/degraded plane: **9/9**.
- Live Supabase: **3/3** — real AAL1 operator boundary, signed-out denial, secret redaction.
- Responsive checks: no horizontal overflow at 1440, 1024, or 390 widths.
- Direct production Playwright probe: critical routes returned HTTP 200 and expected content; no console errors on the clean routes.
- Assistant quick action in fixture mode correctly showed `CHƯA KẾT NỐI DỊCH VỤ` when no inference endpoint was configured.

Screenshots:

- [overview-production.png](test-report-260813-0836-full-system-browser-qa/overview-production.png)
- [company-nvl-production.png](test-report-260813-0836-full-system-browser-qa/company-nvl-production.png)
- [company-nvl-mobile-production.png](test-report-260813-0836-full-system-browser-qa/company-nvl-mobile-production.png)

## Live Service E2E

Command:

```bash
.venv/bin/python scripts/run_phase2_e2e.py --json --timeout 120
```

Result: **PASS**.

- 14 required workloads ready; 10 service endpoints resolved.
- Model warm-up through AgentGateway: HTTP 200, `qwen2.5-0.5b-instruct`.
- Coordinator: HTTP 200, 1,046-character answer, feature + drift specialists, 2 citations, 1 hop, 1 numeric drift row.
- Prometheus: coordinator, feature-agent, drift-agent, feature-MCP, drift-MCP all `1.0`.
- Jaeger: coordinator-agent, feature-agent, drift-agent, feature-MCP, drift-MCP traces present.

## Finding

### [P1] `/sign-out` link is a 404

- **Observed:** production browser probe recorded `404 GET /sign-out?_rsc=...` and a console resource error on `/companies`, `/companies/ZZZ`, `/compare?ticker=NVL`, and `/reports`.
- **Source:** `apps/web/src/components/shell/user-menu.tsx:82` and `apps/web/src/components/shell/analyst-shell.tsx:62` both link to `/sign-out`, but no `apps/web/src/app/sign-out/` route exists.
- **Impact:** navigation prefetch emits errors and clicking “Đăng xuất” cannot reliably complete the sign-out flow.
- **Suggested fix:** implement the intended sign-out server action/route, or replace the link with the existing logout action and add a regression test for click + session clearance.
- **Not fixed in this QA run:** user requested testing; no product source was changed.

## Environment / Execution Notes

- First Playwright attempt was blocked because the Playwright Chromium headless shell was absent. Installed the declared Playwright Chromium runtime; rerun passed.
- Chrome DevTools MCP calls (`new_page`, `lighthouse_audit`) were blocked by the environment with `Missing X server to start the headful browser`; equivalent detailed checks ran through Playwright using the installed Chrome/Chromium runtime.
- Next production server prints a warning that `next start` does not support the configured standalone output; it still served all tested routes and all tests passed. Prefer the standalone server command in a future test-config cleanup.
- Direct dev-server probe showed expected HMR WebSocket errors; production probe was used for console conclusions.
- Strict LLM promotion audit could not run to completion because both source and GitOps worktrees are intentionally dirty from the uncommitted implementation. The non-promotion matrix/evidence audit passed. The command and required frozen baseline are recorded below for a clean checkout:

```bash
.venv-phase2/bin/python scripts/audit_phase2_evidence.py \
  --strict --require-executed --run-validations --track LLM \
  --ml 100 --llm 100 \
  --phase1-base ddbcbe7bd41ae4883954b8a247efdc67c7329078 \
  --gitops-root ../financial-distress-gitops
```

## Resolution note

The `/sign-out` finding above was resolved after this QA capture by PR #75:
`apps/web/src/app/sign-out/route.ts` now clears `sb-access-token` and redirects
to `/sign-in`, with live login/logout Playwright coverage. The original finding
is retained as historical evidence from the pre-fix run.

## Recommendations

1. **Resolved in PR #75:** `/sign-out` now has a cookie-clearing route and a
   Playwright assertion covering the real click path.
2. **P2:** run the strict LLM promotion audit after committing/staging the intended source and GitOps changes in a clean verification checkout.
3. **P3:** configure Playwright/Next to launch the standalone server directly and run Chrome DevTools MCP under an X-capable/headless configuration.

## Unresolved Questions

- Should the live smoke test delete the disposable `smoke.operator@example.com` user after the run? The current test provisions or updates it but does not clean it up.
