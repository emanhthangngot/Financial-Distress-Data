---
title: "Docs Style Contract — reviewer-facing narrative format"
date: 2026-08-14
status: active
scope: "docs/submission/**, README.md, docs/architecture/**, docs/pngs/**"
---

# Docs Style Contract

House style for every reviewer-facing narrative doc built under this plan
(`plans/260814-1223-recsys-format-docs-overhaul/`). Format ported from
`itsmekhoathekid/RecSys-MLops` (structure only, no content copied). Any doc
matching this contract should be structurally indistinguishable from the rest
of the set.

## 1. Non-negotiable gates

Two hard rules enforced by `scripts/check_documentation.py`
(`check_documentation` function, `scripts/check_documentation.py:20`):

- **Line cap:** every `docs/**.md` file must be ≤ 800 lines
  (`--max-lines` default at `scripts/check_documentation.py:59`), except the
  two spec files in `SOURCE_SPEC_EXCEPTIONS` (`coursework.md`,
  `mini_coursework.md`). Split a long narrative into `-part2.md` rather than
  raising the cap.
- **Link rule:** every relative Markdown link — image or reference — must resolve
  to a file that exists, checked from every `docs/**.md` and from `README.md`.
  Absolute URLs (`://`) and in-page anchors (`#...`) are exempt.

One invariant enforced by `scripts/audit_phase2_evidence.py`: every
`evidence_path` cell in the rubric matrix must start with
`docs/phase2/evidence/` (checked at `scripts/audit_phase2_evidence.py:319`;
the same prefix is asserted again in the diff-scope check around
`scripts/audit_phase2_evidence.py:655` and the secret-scan sweep around
`scripts/audit_phase2_evidence.py:790`). Narrative docs never move or rename
files under that prefix — they link into it.

## 2. Three-layer model

```text
Layer 1 — canonical evidence (immutable location)
  docs/phase2/evidence/llm/*.md        60 rows, audit-gate pinned prefix
  docs/evidence/**                     Phase 1 generated artifacts
      ^ never moved, never hand-edited

Layer 2 — narrative (reviewer-facing)
  docs/submission/rubric-(mini-coursework)/*.md
  docs/submission/rubric-final-coursework-(final-llm)/*.md
  docs/submission/ml-track-deferred.md
      ^ tells the story, quotes real code, links DOWN into Layer 1

Layer 3 — entry point
  README.md                            rubric index tables link into Layer 2
```

## 3. Narrative doc skeleton

```text
# <Area>: <what it actually delivers>
<one-paragraph scope statement — what this doc proves and what it does not>
<active-deployment fact list: project, namespace, runtime, versions, replicas>

## Part I — <deploy / build>
### 1. <imperative step title>
<quoted code from a repo-relative linked file>
#### Image proof
Markdown image tag: `alt` text, target path under `docs/pngs/&lt;name&gt;.png`.
*Image note:* <what is visible> <what it proves> <what it does not prove>
### 2. ...

## Part II — <baseline / behavior>
## Part III — <optimization / result>
<before/after metric table>
<honest limitation paragraph>

## References
<internet links used>
```

Every code quote is copied verbatim from the file at its current working-tree
state, never paraphrased, and linked repo-relative.

## 4. Image note rule

Every `#### Image proof` is followed by an `*Image note:*` paragraph stating,
in order:

1. what is visibly in the capture (resource name, status column,
   version/digest, namespace),
2. what that capture proves,
3. what it does **not** prove.

Discipline copied from the reference's `llm_inference_platform.md` §6 note,
which states a Gateway capture "is used only as Gateway infrastructure
evidence; it predates the runtime migration" — narrow, honest scope, not a
blanket claim.

## 5. Screenshot naming

`<subsystem>_<subject>_<state>.png` — lowercase, underscores, no dates in the
filename (dates go in `docs/pngs/manifest.csv`). Examples:
`argocd_applications_synced.png`, `kagent_agent_ready.png`,
`flink_checkpoints_optimized.png`.

## 6. Link rule

- Repo-relative links only.
- No absolute local filesystem paths.
- No bare `http(s)` links to internal/cluster-only hosts (those are not
  reachable by a reviewer).
- Every link is checked by `scripts/check_documentation.py`; run it after
  every 3–4 docs written, not only at the end.

## 7. Diagram rule

Every subsystem gets one small Mermaid diagram, embedded inline in its owning
narrative doc where the subsystem is first introduced. The composed system
view is one rendered PNG (`docs/pngs/system_architecture_overview.png`) with
a tracked `.mmd`/DOT source and a documented regeneration command, used as the
README hero image.

### Color legend (fixed, reused identically across all diagrams)

| Class | Meaning | Example nodes |
|---|---|---|
| `edge` | client/ingress boundary | browser, NGINX ingress, API gateway |
| `service` | a running deployable unit | coordinator agent, MCP tool server, Airflow scheduler |
| `store` | persisted state | Kafka topic, MinIO bucket, Postgres table, DuckDB view |
| `model` | ML/LLM artifact or serving endpoint | KServe InferenceService, model gateway route |
| `result` | observability/output surface | Grafana dashboard, Jaeger trace, drift alert |

## 8. Honesty rule

Any design-only or deferred item is named as such in the same sentence as its
claim — never a bare "Work in progress" placeholder. `docs/submission/
ml-track-deferred.md` is the canonical place for scope decisions; narrative
docs state limitations in their own closing paragraph.

## 9. Image policy (hybrid layout, accepted decision)

- New captures land **directly** in `docs/pngs/`.
- An existing screenshot needed by a narrative doc is **copied** into
  `docs/pngs/` under a contract-conformant name; the original stays at its
  audit-pinned path. The copy gets a manifest row recording the source path.
- No narrative doc reaches sideways into `docs/evidence/screenshots/` or
  `docs/phase2/evidence/**/screenshots/` — it reads from `docs/pngs/` only.

## 10. Worked example (structure, not content)

```text
### 4. Deploy the model gateway route

\`\`\`yaml
# gateway-route.yaml (repo-relative link)
kind: HTTPRoute
...
\`\`\`

#### Image proof
Markdown image tag: alt text "Gateway route programmed", target
`docs/pngs/gateway_route_programmed.png`.

*Image note:* Gateway UI shows route `llm-router` in namespace `llm-platform`
with status `Programmed=True` and target `model-gateway-svc:8080`. This proves
the route is live and accepted by the control plane. It does not prove any
request actually completed successfully — see §6 for the round-trip capture.
```
</content>
