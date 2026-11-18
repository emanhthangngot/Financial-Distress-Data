---
phase: 1
title: "Format contract and docs information architecture"
status: done
priority: P1
effort: "0.5d"
dependencies: []
---

# Phase 1: Format contract and docs information architecture

## Overview

Write down the house presentation style once, so Phases 4–6 are mechanical
instead of improvised, and lay out the target `docs/` tree without moving any
audit-pinned file yet.

## Requirements

- Functional: a single style contract doc that any later phase (or another
  agent) can follow to produce a doc indistinguishable in structure from the
  rest of the set.
- Functional: a target-IA table naming every new directory/file and, for each,
  whether it is new, rewritten, kept, or retired.
- Non-functional: the contract itself obeys the ≤ 800 line doc gate and links
  only to paths that exist.

## Architecture

Three layers, with an explicit rule about which layer owns what:

```text
Layer 1 — canonical evidence (immutable location)
  docs/platform/evidence/llm/*.md        60 rows, audit-gate pinned prefix
  docs/evidence/**                     platform .enerated artifacts
      ^ never moved, never hand-edited

Layer 2 — narrative (new, reviewer-facing)
  docs/submission/rubric-(mini-coursework)/*.md
  docs/submission/rubric-final-coursework-(final-llm)/*.md
  docs/submission/ml-track-deferred.md
      ^ tells the story, quotes real code, links DOWN into Layer 1

Layer 3 — entry point
  README.md                            rubric index tables link into Layer 2
```

Image policy under the accepted hybrid decision:

- New captures taken in platform .re written **directly** to `docs/pngs/`.
- An existing screenshot needed by a narrative doc is **copied** to `docs/pngs/`
  under a descriptive name; the original stays at its audit-pinned path. The
  copy is recorded in the manifest with its source path so the duplication is
  traceable, not accidental.
- No narrative doc reaches sideways into `docs/evidence/screenshots/` or
  `docs/platform/evidence/**/screenshots/`; it reads from `docs/pngs/` only.

## Related Code Files

- Create: `docs/docs-style-contract.md` — the house style, below
- Create: `docs/pngs/.gitkeep`
- Create: `docs/pngs/manifest.csv` — header row only in this phase
- Modify: `docs/project-file-map.md` — add the three-layer model
- Read only: `scripts/check_documentation.py` (line cap + link rule),
  `scripts/audit_phase2_evidence.py` (pinned prefix at `:319`, `:655`, `:790`)

## Implementation Steps

1. Read `scripts/check_documentation.py` and record the two hard rules
   (≤ 800 lines per `docs/**.md`, every relative link must resolve) in the
   contract as non-negotiable.
2. Read `scripts/audit_phase2_evidence.py` around lines 300–330, 640–700, and
   780–800 and record the pinned `docs/platform/evidence/` prefix as invariant.
3. Write `docs/docs-style-contract.md` containing:
   - **Narrative doc skeleton**: `# <Area>: <what it delivers>` → 1-paragraph
     scope statement → active-deployment fact list → `## Part I/II/III` →
     `### N. <imperative step title>` → quoted code from a repo-relative linked
     file → `#### Image proof` → `![alt](../../pngs/<name>.png)` →
     `*Image note:*` paragraph → metric table where applicable →
     honest-limitation paragraph → `## References`.
   - **Image note rule**: must state (a) what is visibly in the capture,
     (b) what that proves, (c) what it does *not* prove. Copy the discipline
     from the reference's llm_inference_platform.md §6 note, which explicitly
     says a Gateway capture "is used only as Gateway infrastructure evidence;
     it predates the runtime migration".
   - **Screenshot naming**: `<subsystem>_<subject>_<state>.png`, lowercase,
     underscores, no dates in the name (dates go in the manifest).
   - **Link rule**: repo-relative only, no absolute local paths, no bare
     `http` to internal hosts.
   - **Diagram rule**: every subsystem gets a small Mermaid diagram inline in
     its narrative doc; the composed system diagram is a rendered PNG with a
     tracked source.
   - **Honesty rule**: any design-only or deferred item is named as such in the
     same sentence as its claim; no "Work in progress" placeholders.
4. Create `docs/pngs/` with `manifest.csv` header:
   `image,subsystem,rubric_area,capture_command_or_source,captured_at,proves`.
5. Write the target-IA table into `docs/project-file-map.md`: for each planned
   path, one of `new | rewrite | keep | retire`, plus its owning phase.
6. List every current `docs/*.md` top-level file against the target IA and mark
   the ones that become redundant once Layer 2 exists (candidates:
   `evidence-index.md`, `11_rubric_completion_spec.md`, the numbered
   `0N_*.md` duplicates of kebab-case siblings). Mark only — retirement happens
   in Phase 7 after the links move.

## Success Criteria

- [ ] `docs/docs-style-contract.md` exists and covers skeleton, Image note rule,
      naming, link rule, diagram rule, honesty rule
- [ ] `docs/pngs/manifest.csv` exists with the agreed header
- [ ] `docs/project-file-map.md` carries the three-layer model and the target-IA
      table with a disposition for every planned path
- [ ] Redundant-doc candidates are listed but not deleted
- [ ] `.venv/bin/python scripts/check_documentation.py` exits 0

## Risk Assessment

- **Risk:** contract too abstract to constrain later phases → docs drift apart.
  **Mitigation:** the contract embeds one full worked example section copied in
  *structure* (not text) from the reference, so later phases pattern-match.
- **Risk:** premature deletion of a doc still linked by the audit matrix.
  **Mitigation:** platform .nly marks; Phase 7 deletes after link rewiring and a
  green audit run.
