---
title: "Close LLM Rubric To 100"
description: "Close the last 21 LLM rubric points (7 Routing & Gateway rows, 6 Observability rows) with real live-cluster evidence, then freeze the submission: frozen PHASE1_BASE_SHA, SHA stamp, strict audit with zero cuts, row-by-row mock grade, finalized cost ledger, hibernation."
status: in_progress (phases 1-5 complete; 100/100 LLM points; phase 6 freeze pending)
priority: P1
effort: "4.5 focused days (1 cluster window ≈ 6-8h), re-budgeted after the 2026-08-11 red team"
branch: codex/phase06-llm-submission
tags: [phase2, llm, evidence, gitops, gke, submission]
blockedBy: [260813-1846-production-hardening-overlay]
blocks: []
created: 2026-08-11
---

# Close LLM Rubric To 100

## Overview

Active phase: **explicit Phase 2**, LLM track only.

Measured today (2026-08-11, HEAD `d72f15f`, both worktrees clean): the LLM track
is **79 / 100 points executed** and the strictest available gate passes on those
rows —

```bash
PATH="$PWD/.venv-phase2/bin:$PATH" .venv-phase2/bin/python scripts/audit_phase2_evidence.py \
  --strict --require-executed --run-validations --track LLM --ml 100 --llm 100 \
  --phase1-base ddbcbe7bd41ae4883954b8a247efdc67c7329078 \
  --gitops-root ~/Studying/FSDS/financial-distress-gitops \
  --accept-design-only "<the 13 rows below>"
# → "platform .ubric matrix is complete and consistent."
```

That run requires a **clean worktree**: an uncommitted sibling plan or an
untracked plan directory alone makes it exit with
`source checkout is not clean`. The 79 points are real; the "passes today" claim
is true only against a clean tree.

The remaining **21 points sit in 13 rows** that are still `design_only`, all of
them Phase 04 rows whose manifests exist but were never reconciled onto a live
cluster. This plan closes exactly those rows and then freezes the submission.

This plan owns **sequencing and the closeout gates only**. Architecture,
manifests, and the evidence contract stay owned by
`plans/260809-2039-complete-phase2-llm-submission/` (its `phase-04` and
`phase-06`) and `plans/260802-1037-unified-phase2-ml-llm-gitops/`. Nothing here
redesigns the gateway or the observability stack — both are already built and
Argo-wired; they have never run.

Read before starting: `AGENTS.md`, `docs/platform/evidence-contract.md`,
`plans/260809-2039-complete-phase2-llm-submission/phase-04-complete-gateway-uis-and-observability.md`.

## The Evidence Rule (non-negotiable)

Every row closed by this plan must carry proof from a **running system**:
a live HTTPS request through the F5 NGINX edge, a real PromQL query result, a
real Loki query result, a real Jaeger trace ID. Static manifests, `helm template`
output, local unit tests, and port-forwarded services are **not** evidence for
these 13 rows — the rubric text says `Capture màn hình thể hiện từng setup đã
thành công` and `có thể coi trên các dashboard`, i.e. the routed, deployed thing.

- Screenshots supplement machine-readable output; they never replace it
  (`docs/platform/evidence-contract.md`). Each of the 13 evidence files carries the
  8 contract fields plus the raw command output that backs the screenshot.
- A row that cannot be captured stays `design_only` and gets named in
  `--accept-design-only` **and** in `docs/submission/README.md`. Never flip a row
  because the manifest looks right.
- Never edit an evidence claim to match reality — fix the system, re-run,
  replace the evidence file atomically.

## Measured Starting State (2026-08-11)

| Fact | Value | Source |
|---|---|---|
| LLM points executed | **79 / 100**, 47 rows | `docs/platform/rubric-matrix.csv` |
| Rows still `design_only` | 13 (Routing & Gateway 7 rows / 13 pts, Observability 6 rows / 8 pts) | same |
| Full strict gate on the 79 | **passes**, 47 `validation_command` subprocesses included | audit run above |
| platform .o-regression gate | `.venv/bin/python scripts/run_stage1_quality_gates.py` → exit 0, `status: pass` | run 2026-08-11 |
| Source HEAD / GitOps HEAD | `d72f15f` / `921bdc1`, both worktrees clean; evidence `source_sha` `6dc70ba` is an ancestor with only SHA lines since | `git`, auditor ancestor rule |
| `PHASE1_BASE_SHA` | **never recorded anywhere**; only `ddbcbe7bd41ae4883954b8a247efdc67c7329078` passes the protected-path diff | `grep`, empirical audit runs |
| GitOps gateway assets | `platform/ingress/{f5-nginx-values,routes-ui,routes-viewers,duckdns-certificate,basic-auth-sealed-secret}.yaml` all present | gitops worktree |
| GitOps observability assets | `platform/observability/{prometheus-values,loki-otel-values,otel-collector,jaeger,dashboards}.yaml` + `grafana-dashboards/llm-observability.yaml` | gitops worktree |
| Argo wiring | `platform-observability` Application syncs kube-prometheus-stack 88.2.0 + loki 7.2.0 + `platform/observability` + **`platform/ingress`** | `argocd/applications/platform-observability.yaml` |
| **Blocker 0** | GitOps checkout is on `feat/phase5-ab-pvc-clones`; every Argo source pins `targetRevision: master`; `921bdc1` is **not** an ancestor of `origin/master` | `git merge-base --is-ancestor` → false; `argocd/applications/platform-observability.yaml:26,29,39` |
| Blocker 1 | `platform/ingress/basic-auth-sealed-secret.yaml` holds **5** `REPLACE_WITH_KUBESEAL_OUTPUT` markers across **3** SealedSecrets in **2** namespaces — `gateway-basic-auth` in `phase2-data` and `monitoring`, plus `grafana-admin-credentials` (Grafana has `existingSecret` + anonymous auth disabled) | grep; `platform/observability/prometheus-values.yaml:4-11` |
| **Blocker 1b** | `apps/dev/web/values.yaml:25-26` mounts Secret `web-runtime-config`, which is produced nowhere; the chart's `secretKeyRef` is not optional | grep across the GitOps repo |
| **Blocker 1c** | `apps/web` has **no sign-in flow** (nothing sets `sb-access-token`); the registry page is only "live" in Supabase mode; `/api/assistant/stream` needs `consume_ai_quota`/`record_audit_event` RPCs and a `profiles` row | `src/lib/server/session.ts`, `src/lib/data/supabase-adapter.ts:186-191`, `src/lib/server/ai-budget.ts:62,126` |
| Blocker 2 | `apps/dev/web/values.yaml` has `tag: phase4`, `digest: ""`, and points at Artifact Registry while CI publishes to **GHCR** | file + `.github/workflows/phase2-ci.yaml` |
| Blocker 3 | no `phase2-web.yaml` caller workflow — `apps/web/Dockerfile` exists but no pipeline builds it; and `gitops-pr` only runs on `main`/`dev`, so a feature branch produces no digest PR | `.github/workflows/phase2-ci.yaml:161` |
| **Blocker 3b** | `charts/web` has no `imagePullSecrets` and no `serviceAccountName` — a private GHCR package cannot be pulled declaratively | `charts/web/templates/deployment.yaml` |
| **Blocker 3c** | `letsencrypt-prod` uses an `http01.ingress` solver, but `gateway-ui-master` already owns `distresslens.duckdns.org` with `ssl-redirect` and host-wide basic auth — the solver Ingress cannot own the same host | `platform/security/letsencrypt-clusterissuer.yaml:18-21`, `platform/ingress/routes-ui.yaml:6-13` |
| **Blocker 3d** | `/loki` is routed as a "viewer" but Loki runs `auth_enabled: false` with the gateway disabled — the route publishes push and delete APIs | `platform/observability/loki-otel-values.yaml:4,43-44`, `platform/ingress/routes-viewers.yaml:29-36` |
| Blocker 4 | cluster `fsds-evidence` at 0 nodes; last live state showed only `hello-web` and `platform-observability` `OutOfSync/Healthy` | phase-04 record |
| CI digest rewrite | `gitops_target_type: values` rewrites `image.repository` + `image.digest` in a Helm values file — exactly what `apps/dev/web/values.yaml` needs | `phase2-ci.yaml` gitops-pr job |
| Cost ledger | `docs/submission/cost.md` still says credit deltas / final balance "TBD phase-08" | file |
| Mock grade | no row-by-row grade report exists | `plans/**/reports/` |
| Flip mechanism | `behavioral_assertion` is matched against the **artifact file**, and all 7 gateway rows declare the same `f5-nginx-values.yaml` while the traces row declares a Loki values file with no Jaeger content — 8 rows cannot carry a distinct assertion as declared | `tests/platform/requirements/conftest.py:143-187`, `scripts/_phase2_rubric_items.py:725-758` |
| Frozen-revision rule | any GitOps commit invalidates the check for all 47 existing rows (the rule only allows SHA lines under `docs/platform/evidence/`, which the GitOps repo does not have) | `scripts/audit_phase2_evidence.py:609-638` |
| Denylist vs capture | the auditor rejects `Authorization:`, the ingress IP `34.21.242.110`, and the project ID in **any** evidence body — exactly what a gateway capture prints | `scripts/audit_phase2_evidence.py:712-741,753-770` |
| Quota figure | the predecessor plan says `CPUS_ALL_REGIONS = 12`; `terraform/gcp/terraform.tfvars:5-6` records a measured regional `CPUS = 32` — unreconciled | both files |
| `make gcp-up` | starts the evidence VM unconditionally and resizes `primary-pool` only; no target raises `secondary-pool` | gitops `Makefile:34-72` |

## The 13 Rows (copied verbatim from the CSV — never hand-type these)

Routing & Gateway — 13 points, all `artifact_repo: gitops`,
`acceptance_id: LLM-AC-13-ROUTING`. All 7 currently declare the same
`artifact_path: platform/ingress/f5-nginx-values.yaml`, which cannot carry seven
distinct behavioral assertions — phase 1 re-points them to the manifest that
actually implements each row:

```text
LLM-routing-gateway-c-c-service-c-n-c-hide-ng-sau-      2   services hidden behind the gateway
LLM-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-      1   same for the feature Web API
LLM-routing-gateway-ui-test-agent                       2   UI to test an agent
LLM-routing-gateway-ui-cho-agent-registry               2   UI for the agent registry
LLM-routing-gateway-authentication-cho-ui-test-age      2   authentication for that UI
LLM-routing-gateway-service-coi-log                     2   log viewer service
LLM-routing-gateway-service-coi-trace                   2   trace viewer service
```

Observability — 8 points, `acceptance_id: LLM-AC-15-OBSERVABILITY`:

```text
LLM-observability-collect-v-visualize-metrics-v-        1   Prometheus + Grafana   (prometheus-values.yaml)
LLM-observability-m-b-o-t-nh-t-c-c-metrics              2   token in/out/total per request + generation round-trip time + TTFT + PII-catch frequency (full CSV requirement)
LLM-observability-agent-tool-call-metrics               2   per-agent call count, per-MCP-tool call count, failures (prometheus-values.yaml)
LLM-observability-web-api-metrics                       1   Web API metrics        (prometheus-values.yaml)
LLM-observability-t-ng-t-cho-logs                       1   logs                   (loki-otel-values.yaml)
LLM-observability-t-ng-t-cho-traces                     1   traces                 (loki-otel-values.yaml)
```

Evidence filenames are contractually `docs/platform/evidence/llm/<rubric_id>.md`.
Copy each ID from `docs/platform/rubric-matrix.csv`; they truncate silently.

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | 13 rows → `executed` with live-cluster proof, each at an `artifact_path` that can carry its own behavioral assertion | P0 |
| 2 | Strict two-repo audit exits 0 with **no** `--accept-design-only` for the LLM track | P0 |
| 3 | Freeze the submission: `PHASE1_BASE_SHA` recorded, SHAs stamped, docs truthful, mock grade written | P0 |
| 4 | platform .ate stays green; `.venv` never mutated; no platform .AG or pipeline touched | P0 |
| 5 | One cluster window; end at the exact hibernation invariant; cost ledger finalized | P1 |

## Phases

| # | Phase | Points | Effort | Status |
|---|-------|-------:|--------|--------|
| 1 | [Align the contract, the repos and the audit mechanics](./phase-01-align-contract-and-audit-mechanics.md) | 0 | 0.75d (no cluster) | Complete |
| 2 | [Release inputs and platform preflight](./phase-02-release-inputs-and-platform-preflight.md) | 0 | 0.75d (no cluster) | Complete |
| 3 | [Build the web auth plane so the UI rows are real](./phase-03-build-web-auth-plane.md) | 0 | 1d (no cluster) | Pending |
| 4 | [Deploy the edge, data and observability planes live via GitOps](./phase-04-deploy-live-via-gitops.md) | 0 | 0.5d (cluster up) | Pending |
| 5 | [Capture the 13 live evidence artifacts](./phase-05-capture-live-evidence.md) | 21 | 0.75d (cluster up) | Pending |
| 6 | [Freeze the submission — docs first, stamp last, mock-grade, hibernate](./phase-06-freeze-submission.md) | 0 | 0.75d (no cluster) | Pending |

Dependencies are linear: 1 → 2 → 3 → 4 → 5 → 6. Phases 4 and 5 run in **one**
cluster window; everything else runs with the cluster at zero nodes.

**Deliberate split of deploy (phase 4) from capture (phase 5).** Deploying and
capturing in one step is how "configured" gets recorded as "executed". Phase 4
ends with a healthy, routed, authenticated stack and **zero** rubric claims.

**Three phases of preflight, not one.** The 2026-08-11 red team found that the
premise "the gateway and observability surfaces are already built and Argo-wired,
they have just never run" is false in three separate ways: the audit mechanics
cannot accept the flip (phase 1), the release inputs and issuance path do not
exist (phase 2), and the web app has no sign-in flow at all (phase 3). Each was
verified against the repositories, not argued.

## Non-Goals

- ML track. The 57 ML rows stay `design_only`; `--track LLM` excludes them and
  `--ml 100 --llm 100` keeps the deferral visible.
- Any change to platform .`src/collectors`, `src/generator`, `src/streaming`,
  `dags/*.py` outside `phase2/`, `docs/evidence/`). The auditor fails the run if
  a protected path moves.
- New gateway or observability design. Those manifests exist; this plan deploys
  and proves them. (The web **auth plane** is the exception — phase 3 builds it,
  because it does not exist.)
- Publishing the GitOps repo itself. It stays private (committed
  `terraform.tfstate`, `ansible/inventory.ini`); the grader gets a **scrubbed
  read-only mirror** of `platform/`, `apps/`, `charts/`, `argocd/` instead
  (user decision, 2026-08-11).
- Product auth features beyond one sign-in path and one demo account: no sign-up,
  no password reset, no account management — none of those is a rubric row.
- Re-capturing any of the 47 already-executed rows unless a change here
  invalidates one. Note they are all re-stamped in phase 6 regardless, because
  any GitOps commit moves their `gitops_sha` baseline.

## Cut Ladder — keyed to the failure, not to a running clock

The target is 100. The previous draft keyed every cut to elapsed time, which
produced a wrong instruction: "if certificate issuance is not green, cut Jaeger
and Loki" concedes 6 points for nothing, because without HTTPS all 7 gateway rows
(13 pts) are already dead. Cuts are also not free — removing a manifest from
`platform/observability` is a `master` commit reconciled with `prune: true`, so
budget the round-trip.

Name every cut row in both `--accept-design-only` and `docs/submission/README.md`.

| Failure observed | Correct response | Points conceded |
|---|---|---:|
| Certificate never reaches `Ready=True` | **Abort branch**, not a cut: either capture HTTP-only and say so in every affected evidence file, or end the window and re-plan issuance. Cutting Jaeger/Loki here changes nothing | 0 or 13 |
| Node pressure / pods `Pending` after the phase-2 disables and scale-to-zero list | Cut the trace viewer + traces row (Jaeger is the least shared dependency), then the log viewer + logs row | 3, then 3 |
| Model plane or data plane cannot run alongside the agents | Cut the agent/tool-call and token metric rows — they require a real generation through a real MCP tool | 4 |
| Phase 3's auth plane not finished before the window | Cut the two UI rows; **do not** capture fixture mode and call it live | 4 |

Never cut: hide-services, the authentication row, or the Prometheus+Grafana row —
they are the highest points-per-node-hour and everything else at the edge depends
on the same ingress being up.

## Success Criteria

- [ ] Auditor -> runs the strict two-repo gate with `--track LLM --require-executed --run-validations` and **no** `--accept-design-only` -> exits 0, and the 57 ML rows remain visibly `design_only`.
- [ ] Reviewer -> opens each of the 13 new evidence files -> finds rubric_id, ISO-8601 timestamp, 40-hex source + GitOps SHAs, versions/digests, a non-interactive reproduction command, expected vs actual result, accurate redaction status, and raw output backing every screenshot.
- [ ] Grader -> opens the public HTTPS gateway host with the out-of-band credential -> signs in, reaches the agent-test UI and the registry UI, and gets 401 without credentials on all five protected routes.
- [ ] Grader -> queries Grafana -> sees per-agent call counts, per-MCP-tool call counts, failures, per-request token counts, generation round-trip time, TTFT, PII-catch frequency, and Web API metrics from a real run, plus the matching Loki lines and Jaeger trace.
- [ ] Grader -> opens the scrubbed GitOps mirror at a referenced commit -> reaches the manifests, and finds no tfstate, tfvars, inventory or key material in it.
- [ ] Reviewer -> cross-checks the six correlated evidence files -> they cite one identical Jaeger trace ID, and the gateway files cite the served certificate's serial and `notBefore`.
- [ ] Maintainer -> reads `docs/platform/evidence-contract.md` -> finds the frozen 40-hex `PHASE1_BASE_SHA` recorded, not a placeholder.
- [ ] platform .aintainer -> runs `.venv/bin/python scripts/run_stage1_quality_gates.py` -> exit 0, `.venv` unmutated.
- [ ] Reviewer -> opens the mock-grade report -> finds a row-by-row grade against the canonical CSV (not against this plan) totalling the claimed score.
- [ ] Cost owner -> reads `docs/submission/cost.md` -> finds per-session credit deltas including the evidence VM, a final balance, and confirmation the trial billing account was never upgraded.
- [ ] Cost owner -> runs `make gcp-status` -> primary pool 0 nodes, secondary pool 0 nodes, evidence VM stopped.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Node capacity: the full transitive stack (observability + data plane + model plane + agents + MCP + web) does not fit the primary node | Observability and metric rows uncapturable | platform .erives the budget from `helm template` output, not hand sums, and names what to disable (Loki `chunksCache`/`resultsCache`) and what to scale to zero; the secondary pool is raised only after the evidence VM is stopped, using a target added in phase 2 |
| Certificate never issues (HTTP-01 solver cannot own a host already owned by the mergeable master) | All 7 gateway rows die | platform .ommits an issuance strategy that avoids the conflict (acme minion, DNS-01, or pre-issued) and phase 4 verifies `Ready=True` before any capture; staging-vs-prod is irrelevant to this failure |
| A ciphertext sealed for the wrong namespace or a missed placeholder | 503 instead of 401; Grafana never ready | Phase 4 gates on all six Secrets materializing before syncing routes |
| Web image never built, or built but unpullable | Both UI rows die on `ImagePullBackOff` | platform .erges the caller to `dev` (the only branch that opens a digest PR), verifies the job ran, and proves the pull path |
| The auth plane is not finished before the window | UI rows uncapturable | Phase 3 runs with the cluster down and gates on a local container round-trip; if it slips, the cut ladder cuts the UI rows rather than capturing fixtures as live |
| Late fix invalidates already-captured evidence | Silent staleness | Every evidence file records the SHAs/digests live at capture; any later system change forces atomic re-capture of that scenario |
| Any commit after stamping | All 60 rows fail the frozen-revision rule | Phase 6 order: write and commit everything → stamp → gate → stop |
| Jaeger memory storage loses the correlated trace | Six evidence files cite an unresolvable ID | Phase 5 persists the trace JSON in the same step that runs the scenario |
| Credit exhaustion mid-window | Window lost | Record balance at window open; never use `gcp-up` as a mid-window reset (it restarts the VM and zeroes the secondary pool); fall to the failure-keyed cut ladder |

## Red Team Review

### Session — 2026-08-11
**Findings:** 30 raw from 3 hostile reviewers (Security Adversary / Fact Checker,
Failure Mode Analyst / Flow Tracer, Assumption Destroyer / Scope Auditor),
deduplicated to 15. **15 accepted, 0 rejected** — every finding carried
`file:line` evidence, and the controller independently re-verified the branch
mismatch, the frozen-revision rule, the assertion mechanism, the sealed-secret
count, the missing `web-runtime-config`, the CI branch gate and the denylist
before adjudication.
**Severity breakdown:** 9 Critical, 5 High, 1 Medium.

| # | Finding | Severity | Disposition | Applied To |
|---|---------|----------|-------------|------------|
| 1 | GitOps checkout is on a branch Argo never deploys; `921bdc1` is not an ancestor of `origin/master` | Critical | Accept | platform .
| 2 | The frozen-revision rule makes a clean gate impossible before stamping — any GitOps commit fails all 47 rows | Critical | Accept | Phase 1, 5, 6 |
| 3 | The freeze order stamps first and then commits documents, invalidating its own stamp | Critical | Accept | Phase 6 |
| 4 | 8 of 13 rows cannot carry a row-specific behavioral assertion at their declared `artifact_path` | Critical | Accept | platform .
| 5 | The web pod cannot start: `web-runtime-config` is referenced but never produced; provenance SHAs unset; data-source mode unset | Critical | Accept | Phase 2, 3 |
| 6 | Five sealed-secret placeholders across three SealedSecrets and two namespaces, including Grafana's admin credentials | Critical | Accept | Phase 4 |
| 7 | CI cannot open a digest PR from a feature branch (`gitops-pr` gated to `main`/`dev`) | Critical | Accept | platform .
| 8 | HTTP-01 issuance collides with the mergeable-Ingress master owning the same host | Critical | Accept | Phase 2, 4 |
| 9 | The UI rows and the assistant round-trip need a sign-in flow that does not exist; "live registry" is fixture-backed without a session | Critical | Accept | Phase 3 |
| 10 | The auditor's denylist rejects exactly the captures the plan mandates | High | Accept | Phase 1, 5 |
| 11 | The automated gate cannot distinguish live evidence from prose | High | Accept | Phase 5 (liveness anchors) |
| 12 | The capacity budget method undercounts chart defaults and omits the data/model planes | High | Accept | platform .
| 13 | `gcp-up` restarts the evidence VM and never scales the secondary pool; the quota figure is unreconciled | High | Accept | Phase 2, 4 |
| 14 | The web CI caller lacks `secrets:` and would run a Python-only gate over a Next.js app; `charts/web` cannot express a pull secret | High | Accept | platform .
| 15 | `/loki` publishes a write-capable API as a "viewer"; the credential-delivery path is undefined and the denylist misses `curl -u`/htpasswd shapes | Medium | Accept | Phase 1, 2 |

#### User decisions taken during adjudication — 2026-08-11

1. **Apply all 15 findings.**
2. **Build the Supabase auth plane for real** rather than capturing the UI in
   fixture mode. This is new build work and became phase 3; the alternative
   (screenshotting fixtures as "live") was rejected as the exact failure the
   Evidence Rule exists to prevent.
3. **Grader access via a scrubbed read-only mirror** containing only `platform/`,
   `apps/`, `charts/`, `argocd/`. This revises the predecessor plan's 2026-08-09
   decision (keep private, grant read access) on new evidence: the control repo
   carries a committed `terraform.tfstate` and `ansible/inventory.ini`, and the
   auditor's own denylist treats two of those values as leaks. Rejected:
   granting access to the original, and rewriting history with `git filter-repo`
   on a live infrastructure repo.

#### Whole-Plan Consistency Sweep

- Files reread: `plan.md` and all six phase files.
- Decision deltas checked: 18 (15 findings + 3 user decisions).
- Reconciled: phase count 4 → 6 and effort 2.5d → 4.5d; the cut ladder re-keyed
  from elapsed time to observed failure; the "passes today" claim qualified with
  the clean-worktree requirement; the deploy phase's evidence-driving step changed
  from a UI click to a scripted gateway call; the token-metrics row's scope
  widened to the full CSV requirement (TTFT and PII-catch frequency); the
  "grant the grader read access" step replaced by the scrubbed mirror everywhere
  it appeared.
- Unresolved contradictions: 0.

## Open Questions

- Is another GCP window affordable, and what is the current credit balance? Phase 4 step 0 records it; if it is short, take the cut ladder deliberately at window open, not at hour six.
- Where does the scrubbed mirror live (same account, new repo name?), and who publishes it? Phase 6 step 3 needs that decided.
- Which channel delivers the gateway credential out of band to the grader? platform .ecides; the repo records only the fact of delivery.
- Does the grader accept DuckDNS as "domain + HTTPS", or is a real domain expected? DuckDNS is what the manifests use; if unacceptable, that is a phase-2 decision, not a phase-4 discovery.
- Which vCPU quota figure governs — the predecessor plan's `CPUS_ALL_REGIONS = 12` or the measured regional `CPUS = 32` in `terraform.tfvars`? platform .tep 5 resolves it against the project's actual quota.
- Which Supabase project hosts the auth plane, and are its migrations already applied there? Phase 3 step 1 verifies rather than assumes.

<!-- slug: close-llm-rubric-to-100 -->
