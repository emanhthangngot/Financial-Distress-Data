---
title: "Reviewer-Facing Docs Overhaul in RecSys-MLops Format (LLM Track)"
description: "Rebuild README, docs/ IA, architecture diagrams, and screenshot evidence in the itsmekhoathekid/RecSys-MLops presentation format, adapted to this repo's LLM track and improved beyond it."
status: pending
priority: P1
effort: "5-7d"
tags: [docs, evidence, phase2, llm, readme]
created: 2026-08-14
---

# Reviewer-Facing Docs Overhaul in RecSys-MLops Format (LLM Track)

## Overview

Reference repo `itsmekhoathekid/RecSys-MLops` (69 stars, ML track) presents its
coursework in a format this repo does not currently match. This plan ports that
**presentation format** — not its content — onto this repo's LLM track, then
improves on it in four places the reference is weak.

Reference format, decoded from the downloaded tarball
(`/tmp/.../scratchpad/recsys`, `main` @ 2026-08-13):

1. **Root README** (374 lines): emoji section headers, `## 🛍️ Business Domain`,
   a five-bullet `## 📝 System Overview` where each bullet is one dense
   paragraph per subsystem, a demo GIF linking to MP4, a numbered TOC, an
   `## 🏗️ Architecture` section with **one big rendered PNG for the whole system
   plus four small per-subsystem Mermaid diagrams**, a `txt`-fenced repository
   folder tree with inline comments, and per-rubric-tab index tables mapping
   every rubric area to its narrative doc.
2. **`docs/submission/<rubric-tab-name>/*.md`**: one narrative doc per rubric
   area, 200–1200 lines, structured as numbered steps that tell a story
   (`### 1. Select the active deployment profile` → `### 8. Download and serve
   the model`). Every step quotes **real code from a repo-relative linked file**,
   then proves the runtime with `#### Image proof` → screenshot →
   `*Image note:*` paragraph stating exactly what the capture proves and what it
   does **not** prove. Ends with metric tables, an honest limitations paragraph,
   and an `Internet references` list.
3. **`docs/pngs/`**: 405 screenshots in one flat directory, descriptively named
   (`agentgateway_controller_gatewayclass_ready.png`).

Current repo gap: README has no visual story and no per-subsystem diagram set;
`docs/submission/` holds 7 thin files (17–167 lines) with no image proofs; the
60 canonical LLM evidence rows sit in `docs/phase2/evidence/llm/` under
machine-generated slug filenames that are reviewer-hostile; ~100 real
screenshots are scattered across 5 directories with no Image notes.

**Four improvements over the reference** (this is the "phát triển lên tốt hơn"
requirement — the reference's own LLM tab is 18/21 rows "Work in progress"):

- **Every rubric row lands, none marked WIP.** The reference LLM tab ships 3 of
  21 areas. This plan ships all 21 LLM areas plus 9 mini-coursework areas plus a
  19-row ML-deferred index that states scope honestly instead of "Work in
  progress".
- **Machine-verified links.** The reference has no link gate. This repo has
  `scripts/check_documentation.py`, which fails on any broken relative link and
  on any `docs/**.md` over 800 lines. Every doc written here passes it.
- **Two-level architecture per subsystem, not per repo.** The reference draws
  one big picture plus four diagrams total. This plan draws a small diagram for
  *each* of the seven subsystems and one composed system diagram, with the
  Mermaid/DOT sources tracked so they stay regenerable.
- **Traceable evidence provenance.** Every narrative image carries an Image note
  *and* a manifest row mapping it back to the canonical
  `docs/phase2/evidence/**` row or the capture command that produced it.

## Non-Goals

- No copying of RecSys-MLops prose, diagrams, or ML-track content. Format only.
- No change to Phase 1 pipeline behavior, DAGs, or data contracts.
- No relocation of `docs/phase2/evidence/**`. The audit gate hard-pins that
  prefix (`scripts/audit_phase2_evidence.py:319`, `:655`, `:790`); moving those
  files breaks the submission gate. The new narrative layer links *into* them.
- No new AWS/K8s code in this repo (`AGENTS.md` → Don't Touch).
- No fabricated screenshots or metrics. Every capture comes from a real run.

## Accepted Decisions

| Decision | Choice | Consequence |
|---|---|---|
| Live capture | GKE evidence plane is alive | Phase 2 re-captures Argo/kagent/Grafana/Jaeger/gateway fresh instead of reusing stale shots |
| Image layout | Hybrid | Narrative images live in `docs/pngs/`; canonical evidence images stay at their audit-pinned paths |
| Docs scope | Full + ML deferred index | Both rubric tabs get narrative doc sets; ML rows get an explicit deferred table |

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | A reviewer opening the README understands the business domain, the whole system, and where every rubric point is proven, without opening a second tab | P1 |
| 2 | Every rubric area has one narrative doc with numbered steps, quoted real code, repo-relative source links, and Image proof + Image note per screenshot | P1 |
| 3 | Every subsystem has a small architecture diagram; the system has one composed large diagram; all sources are tracked and regenerable | P1 |
| 4 | Screenshots show the actual tool UI clearly, are descriptively named, and each states what it proves and what it does not | P1 |
| 5 | The whole docs tree passes `check_documentation.py` (no broken links, no doc over 800 lines) and the Phase 2 evidence audit stays green | P1 |
| 6 | ML-track rows are presented as an explicit deferred/design-only table, never as unexplained gaps | P2 |

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Phase 1: Format contract and docs information architecture](./phase-01-format-contract-and-docs-ia.md) | Done |
| 2 | [Phase 2: Live screenshot capture campaign](./phase-02-live-screenshot-capture.md) | Done (8 gaps, see runbook) |
| 3 | [Phase 3: Two-level architecture diagram set](./phase-03-architecture-diagram-set.md) | Done |
| 4 | [Phase 4: LLM-track narrative submission docs](./phase-04-llm-track-narrative-docs.md) | Done |
| 5 | [Phase 5: Mini-coursework narrative docs and ML deferred index](./phase-05-mini-coursework-and-ml-index.md) | Done |
| 6 | [Phase 6: Root README rebuild](./phase-06-root-readme-rebuild.md) | Done |
| 7 | [Phase 7: Integrity gates, cleanup, and freeze](./phase-07-integrity-gates-and-cleanup.md) | Pending |

Dependencies: 1 blocks all. 2 and 3 run in parallel after 1. 4 and 5 need 2+3.
6 needs 3 (diagrams) and 4+5 (index tables it links). 7 needs everything.

## Key Invariants

- `docs/phase2/evidence/**` paths are canonical and immutable. Audit gate pins
  the prefix; narrative docs link in, never out.
- Generated artifacts (`docs/evidence/**`, `outputs/**`, `warehouse.db`) are
  never hand-edited. Regenerate via the producing script.
- Every `docs/**.md` stays ≤ 800 lines (`check_documentation.py --max-lines`
  default). Split long narratives into part files rather than raising the cap.
- Every relative link resolves. The doc gate fails the build otherwise.
- Commit format: Conventional Commits, no AI-attribution trailer.

## Verify Commands

```bash
.venv/bin/python scripts/check_documentation.py            # links + size gate
.venv/bin/python scripts/audit_phase2_evidence.py --track LLM
.venv/bin/python scripts/run_stage1_quality_gates.py       # pytest+ruff+black+compose
```

## Success Criteria

- [ ] Root README follows the reference skeleton (business domain → system
      overview → demo → TOC → architecture → repo tree → rubric index tables),
      adapted to LLM track, with zero RecSys content copied
- [ ] `docs/submission/rubric-final-coursework-(final-llm)/` covers all 21 LLM
      rubric areas; no area reads "Work in progress"
- [ ] `docs/submission/rubric-(mini-coursework)/` covers all 9 Phase 1 areas
- [ ] `docs/submission/ml-track-deferred.md` lists all 19 ML areas with an
      explicit deferred/design-only reason each
- [ ] Seven small subsystem diagrams + one composed system diagram exist, with
      tracked Mermaid/DOT sources
- [ ] Every screenshot referenced from a narrative doc has an `*Image note:*`
      paragraph and a manifest row naming its source or capture command
- [ ] `check_documentation.py` exits 0
- [ ] `audit_phase2_evidence.py --track LLM` reports no new findings vs. the
      pre-change baseline
- [ ] `run_stage1_quality_gates.py` exits 0

<!-- slug: recsys-format-docs-overhaul -->
