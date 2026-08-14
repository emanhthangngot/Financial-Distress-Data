---
phase: 2
title: "Live screenshot capture campaign"
status: pending
priority: P1
effort: "1.5d"
dependencies: [1]
---

# Phase 2: Live screenshot capture campaign

## Overview

The reference repo's persuasive power is 405 clear captures of real tool UIs,
each explained. This phase produces this repo's equivalent set from the live
GKE evidence plane, the local Docker stack, and the product web app — while the
cluster is still up.

## Requirements

- Functional: one capture per claim that a narrative doc will make, taken from
  the real running system, showing the tool's own UI or its CLI output with the
  identifying context visible (namespace, resource name, status column, version).
- Functional: `docs/pngs/manifest.csv` gets one row per image recording the
  capture command or source, timestamp, and what it proves.
- Non-functional: no secrets, tokens, cookies, JWTs, private IPs beyond what is
  already public in the repo, or personal data visible in any capture. Redact
  before committing.
- Non-functional: readable at 100% zoom; terminal captures use a font size that
  survives GitHub's image scaling.

## Architecture

Capture is organized by subsystem so each narrative doc in Phase 4/5 has its
image set ready before writing starts.

```text
GKE evidence plane (live now — capture first, it is the perishable one)
  Argo CD        13 applications Synced/Healthy, one app detail view
  kagent         10 agents Ready, one agent spec + one agent run
  Model gateway  gateway programmed, route, model config resolution
  KServe         inference service ready, a real prediction round-trip
  MCP services   tool list, a tool call with its response
  Coordinator    a full round-trip with feature + drift citations
  Prometheus     targets up, agent/tool call metrics, token+latency+PII metrics
  Grafana        dashboards per rubric claim
  Jaeger         discoverable services, one end-to-end trace
  Ingress/NGINX  routing, auth challenge, hidden-service proof

Local Phase 1 stack
  Airflow        DAG graph + task tree + a successful run per DAG
  Kafka          topic offsets
  MinIO          Bronze/Silver/Gold object paths
  DuckDB/DBeaver Gold views, schema, row counts
  Flink          job overview, checkpoints, baseline vs optimized
  Spark UI       baseline vs optimized stage timings

Product plane
  Web app        login, analyst surfaces, agent registry UI, agent chat
  Supabase       RLS policies, auth users table (redacted)
```

## Related Code Files

- Modify: `scripts/capture_ui_screenshots.py` — add/extend targets so browser
  captures land in `docs/pngs/` with contract-conformant names
- Modify: `scripts/capture_phase2_evidence.py` — only if it already owns a
  capture this phase needs; do not duplicate its responsibilities
- Create: `docs/pngs/*.png` (the capture set)
- Modify: `docs/pngs/manifest.csv` (one row per image)
- Modify: `docs/ui-screenshot-runbook.md` — record the exact reproduction steps
  for this campaign
- Read only: `docs/phase2/evidence-contract.md` (what counts as proof)

## Implementation Steps

1. Inventory first: derive the required-capture list from the 21 LLM rubric
   areas + 9 mini-coursework areas. Write it into
   `docs/ui-screenshot-runbook.md` as a checklist before capturing anything, so
   the cluster is visited once, not five times.
2. Cross-check the inventory against the ~100 existing screenshots
   (`docs/evidence/screenshots/`, `docs/phase2/evidence/product/`,
   `docs/evidence/reviewer_screenshots/`,
   `docs/phase2/evidence/llm/validation-verification/screenshots/`). Mark each
   required capture as `re-capture` or `reuse-copy`.
3. **Capture the GKE plane first** — it is the perishable resource. Work down
   the checklist namespace by namespace. For each capture, make the proof
   self-evident in-frame: resource name, status column, version/digest, and the
   command that produced it.
4. Capture the local Phase 1 stack: bring up the Docker stack, run the DAGs, and
   capture Airflow/Kafka/MinIO/DuckDB/Flink/Spark. Follow `AGENTS.md` — Flink
   needs `--profile flink` and `ENABLE_FLINK=1`.
5. Capture the product plane via `scripts/capture_ui_screenshots.py`, extended
   to emit contract-conformant filenames into `docs/pngs/`.
6. Copy the `reuse-copy` images into `docs/pngs/` under contract names; record
   the source path in the manifest's `capture_command_or_source` column.
7. Redaction pass: open every new PNG, confirm no secret/token/credential/PII is
   visible; blur or re-take otherwise. This is a blocking gate before commit.
8. Fill `docs/pngs/manifest.csv` completely. An image with no manifest row is
   not allowed to be referenced by a later phase.
9. Commit as `docs(evidence): capture live tool screenshots for narrative docs`.

## Success Criteria

- [ ] Every required capture in the runbook checklist is either taken or
      explicitly marked reused, with a reason
- [ ] Every GKE capture shows namespace + resource + status in-frame
- [ ] Baseline/optimized pairs exist for Flink, Spark, and the LLM routing
      benchmark so Phase 4 can build before/after metric tables
- [ ] `docs/pngs/manifest.csv` has one row per image, no empty `proves` cell
- [ ] Redaction pass completed; no credential visible in any committed image
- [ ] `docs/ui-screenshot-runbook.md` reproduces the campaign step by step

## Risk Assessment

- **Risk:** cluster torn down or drifts mid-campaign, leaving a half set.
  **Mitigation:** capture GKE before local; checklist-driven single pass;
  any missed shot is recorded as a gap in the runbook, never invented.
- **Risk:** a capture leaks a token or demo credential.
  **Mitigation:** blocking redaction pass in step 7; `AGENTS.md` already
  forbids committing secrets; the submission index already routes credentials
  out of band.
- **Risk:** image bloat in git history.
  **Mitigation:** capture at the smallest resolution that stays legible; prefer
  a cropped panel over a full 4K desktop.
- **Risk:** duplication between `docs/pngs/` copies and canonical evidence
  images drifts over time.
  **Mitigation:** manifest records the source path for every copy; Phase 7
  verifies the copies still match their sources.
