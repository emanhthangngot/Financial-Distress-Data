---
phase: 3
title: "Two-level architecture diagram set"
status: pending
priority: P1
effort: "1d"
dependencies: [1]
---

# Phase 3: Two-level architecture diagram set

## Overview

The user's explicit requirement: *"ở mỗi kiến trúc đều vẽ architecture nhỏ rồi
architecture lớn"*. Deliver a small diagram for every subsystem plus one
composed system diagram — and go past the reference, which draws four diagrams
total for the whole repo.

## Requirements

- Functional: seven small subsystem diagrams, each inline Mermaid in its
  narrative doc, each showing that subsystem's real components and data flow —
  not a generic box chart.
- Functional: one composed large system diagram rendered to PNG for the README,
  with a tracked source file so it can be regenerated.
- Functional: every diagram node names a real deployable unit or table that
  exists in this repo; a reviewer can grep the name and find it.
- Non-functional: Mermaid renders on GitHub without plugins; colors carry
  meaning (edge / service / store / model / result), consistent across all
  diagrams.

## Architecture

Level split, matching the reference's small-then-large pattern:

```text
SMALL (Mermaid, inline in the owning narrative doc)
  1. Phase 1 lakehouse       collectors -> Kafka -> Bronze/Silver/Gold -> DuckDB
  2. LLM inference platform  gateway -> model config -> model serving -> response
  3. RAG pipeline            source -> chunk -> embed -> index -> retrieve -> cite
  4. Agent plane             registry -> coordinator -> sub-agents -> MCP tools
  5. Product plane           Next.js -> Supabase auth/RLS -> data port -> outbox
  6. GitOps/CI-CD            source repo -> CI -> image -> gitops repo -> Argo -> GKE
  7. Observability + drift   metrics/logs/traces -> Prometheus/Loki/Jaeger ->
                             Grafana -> drift detector -> retrain/alert path

LARGE (rendered PNG, README hero image)
  Composed view: the seven subsystems as subgraphs, with the cross-boundary
  contracts drawn explicitly — Gold tables into RAG/feature APIs, evidence
  plane as disposable, product plane as persistent.
```

Color legend fixed once in the style contract and reused in all seven:
edge/client, service, store, model, result/observability.

## Related Code Files

- Create: `docs/architecture/subsystem-*.mmd` (7 sources, one per small diagram)
- Create: `docs/architecture/system-overview.mmd` or extend
  `docs/architecture/deployment.mmd` for the composed view
- Create: `docs/pngs/system_architecture_overview.png` (rendered large diagram)
- Modify: `docs/system-architecture.md` — becomes the diagram home with the
  legend and the regeneration command
- Modify: `images/architecture/` — retire or supersede
  `architecture-stage-1.png` if the composed diagram replaces it; decide, do
  not leave two competing hero images
- Read only: `docs/phase1_architecture.md`, `docs/phase2/architecture.md`,
  `docs/architecture/repository-map.md`

## Implementation Steps

1. Extract the real component list per subsystem from
   `docs/phase2/architecture.md`, `docs/phase1_architecture.md`, and
   `docs/architecture/repository-map.md`. Every node name must be traceable to a
   file, service, or table in this repo.
2. Fix the color legend in `docs/docs-style-contract.md` (five classes) and
   apply it identically in all seven diagrams.
3. Draw the seven small Mermaid diagrams as `.mmd` sources under
   `docs/architecture/`. Keep each under ~40 nodes; a diagram nobody can read
   proves nothing.
4. Compose the large diagram from the seven subgraphs, showing cross-boundary
   contracts: Gold → RAG/feature API, evidence plane disposability, product
   plane persistence, GitOps as the only path to cluster state.
5. Render the large diagram to `docs/pngs/system_architecture_overview.png`.
   Record the exact render command in `docs/system-architecture.md` so it is
   regenerable, not a hand-drawn one-off.
6. Verify each small diagram renders on GitHub (Mermaid dialect, no unsupported
   syntax) by previewing the containing doc.
7. Resolve the competing hero images: either regenerate
   `images/architecture/architecture-stage-1.png` as the Phase 1 subsystem view
   or retire it and point everything at the new set. Record the decision in
   `docs/system-architecture.md`.

## Success Criteria

- [ ] Seven `.mmd` sources exist under `docs/architecture/`, one per subsystem
- [ ] Each small diagram's nodes are greppable to real repo artifacts
- [ ] One composed large diagram is rendered to `docs/pngs/` with its source and
      render command tracked
- [ ] The five-class color legend is identical across all diagrams and is
      documented once
- [ ] `docs/system-architecture.md` is the single diagram index; no orphaned
      competing hero image remains
- [ ] `.venv/bin/python scripts/check_documentation.py` exits 0

## Risk Assessment

- **Risk:** diagrams describe an idealized system rather than the deployed one.
  **Mitigation:** node-name greppability rule in step 1; anything not present in
  the repo is either removed or explicitly labelled design-only.
- **Risk:** Mermaid syntax that renders locally but breaks on GitHub.
  **Mitigation:** step 6 preview check; keep to the same constructs the
  reference uses successfully (`flowchart LR/TD`, `subgraph`, `classDef`).
- **Risk:** the composed diagram becomes unreadable.
  **Mitigation:** subgraph-level composition only — the large diagram shows
  subsystem boxes and their contracts, not every internal node.
