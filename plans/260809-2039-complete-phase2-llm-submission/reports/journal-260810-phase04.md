---
phase: 04
date: 2026-08-10
status: working-tree-not-release-ready
---

# Phase 04 implementation journal

## Context

Phase 04 covers the F5 gateway, product UIs, protected viewer routes, and
metrics/logs/traces. This entry records the current working-tree state; it is
not a commit or deployment record.

- Source repo: `Financial-Distress-Data`, branch `dev`, dirty
  (`dev...origin/dev`).
- Private GitOps repo: `financial-distress-gitops`, branch `master`, dirty
  (`master...origin/master`).
- Existing source-repo edits to the Phase 04 plan/plan overview, onboarding
  material, research, and the Phase 03 report were preserved. No unrelated
  files were changed by this journal task.

## What happened

Source repo changes add the deployable web surface and live-plane wiring:

- `apps/web` now has standalone Next output and a non-root production
  Dockerfile; the registry adapter reads the cluster registry, stamps source
  and GitOps provenance, and fails closed instead of serving fixture entries.
- The assistant route can call the live coordinator, translate specialist/tool
  and citation results, and propagate request/correlation/trace metadata.
- Shared Python telemetry covers token input/output/total, generation
  round-trip time, TTFT, PII-safety catches, agent calls, MCP-tool calls,
  invocation failures, and Web API RED metrics. HTTP/MCP/agent code exposes
  `/metrics`, OTel spans, and redaction-safe metadata.

Private GitOps changes declare the deployment shape:

- A web chart and dev ApplicationSet input, ClusterIP services, F5 mergeable
  ingress routes for `/`, `/agents/registry`, `/grafana`, `/loki`, and
  `/jaeger`, plus DuckDNS Certificate resources.
- Basic-auth/rate-limit annotations, Prometheus/Grafana recording rules and
  dashboard, ServiceMonitors, Loki configuration, Jaeger redaction, and an
  OTel log collector.
- The auth manifest still contains sealing placeholders, and the web values
  reference a `web-runtime-config` secret that is not represented in this
  checkout. These are release blockers, not evidence of working credentials.

## Verification

Passed locally:

- Phase 04 Python tests: `.venv-phase2/bin/python -m pytest tests/phase2/apps tests/phase2/agents tests/phase2/test_observability.py -q` — **16 passed**.
- Full web suite: `pnpm --filter @distresslens/web test` — **20 files and 176 tests passed**; package coverage was 93.62% statements and 90.38% branches.
- Targeted web tests: 2 files, 19 tests passed with coverage disabled.
- Web typecheck and ESLint passed.
- Python syntax compilation for the touched agent/MCP/observability modules
  passed.
- `helm lint charts/web -f apps/dev/web/values.yaml` and the corresponding
  `helm template` render passed.
- `git diff --check` passed in both repositories.

Not passed or not performed:

- No Docker image build/push, Argo sync, cluster readiness, DNS update,
  cert-manager issuance, HTTPS route check, direct-backend denial, auth
  challenge, 429 burst test, viewer check, UI viewport evidence, or
  metric/log/trace correlation proof was run. No commit or push is claimed.

## Exact release prerequisites

1. Release engineer -> builds and publishes every changed runtime image -> the
   GitOps values use immutable image digests and inject valid source/GitOps
   SHAs required by the live registry provenance gate.
2. Platform owner -> creates the web runtime secret and replaces all four
   auth/Grafana ciphertext placeholders across the three SealedSecret objects
   with out-of-band SealedSecret output -> Argo can sync without plaintext
   credentials in Git.
3. DNS/platform owner -> points `distresslens.duckdns.org` at the reserved
   ingress address `34.21.242.110` and syncs cert-manager -> the ACME
   certificate is issued and the HTTPS chain is captured.
4. Platform owner -> syncs the observability Application/ApplicationSet and
   ingress resources -> web, Grafana, Loki, and Jaeger are Ready and answer
   through the protected gateway routes.
5. Evidence owner -> captures the required negative/positive gateway proofs,
   auth and 429 behavior, live registry/UI evidence at three viewports, and a
   correlation ID across redacted metrics, logs, and traces -> Phase 04 rows
   can be marked executed.
6. Maintainer -> regenerates the Phase 04 evidence/audit artifacts and runs
   the required final audit, including the `gcp-down` delta -> release
   readiness is documented from runtime evidence rather than manifests alone.

## Unresolved questions

- Which release job owns image digest publication and source/GitOps SHA
  injection?
- Where is the out-of-band owner/process for `web-runtime-config` and the
  sealed auth/Grafana secrets documented?

Status: DONE_WITH_CONCERNS
Summary: Concise Phase 04 journal created from the source and private GitOps working trees, with passed checks, failed/blocked checks, and release prerequisites recorded.
Concerns/Blockers: Runtime deployment evidence is still absent; auth material is not sealed, the web runtime secret is not represented here, and the focused Python test is blocked by the incomplete `.venv`.
