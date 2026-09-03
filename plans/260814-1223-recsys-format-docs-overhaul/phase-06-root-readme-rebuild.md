---
phase: 6
title: "Root README rebuild"
status: done
priority: P1
effort: "0.5d"
dependencies: [3, 4, 5]
---

# Phase 6: Root README rebuild

## Overview

Rebuild `README.md` in the reference's skeleton, adapted to the LLM track. The
current README is 653 lines but structured as an operator runbook — Local Setup,
Docker, Service URLs, Validation Commands, Stop Services — which buries the
story a grader needs in the first screen.

## Requirements

- Functional: the reference skeleton, LLM-adapted: business domain → system
  overview → demo → TOC → architecture (large PNG + small Mermaid set) →
  repository tree → rubric index tables.
- Functional: operator content (local setup, docker, service URLs, validation
  commands, inspection queries) moves to a dedicated runbook doc, linked from
  the README rather than inlined.
- Functional: three index tables — mini-coursework, LLM track, ML deferred —
  each row linking to its Phase 4/5 narrative doc.
- Non-functional: zero prose copied from the reference. Structure only.
- Non-functional: every relative link resolves (README is link-gated too).

## Architecture

Target section order, with what changes versus the current README:

```text
# Financial Distress Data + AI Engineering Platform     (retitled: LLM track)
<one-line positioning sentence>
## 🏦 Business Domain            keep current content, tighten
## 📝 System Overview            NEW: 5 dense bullets, one per subsystem
                                 (lakehouse / LLM+RAG / agents+MCP / product /
                                  platform+observability)
## 🎬 Demo                       NEW: product + agent round-trip GIF -> MP4
## 📚 Table of Contents          renumber to the new order
## 🏗️ Architecture               large PNG + the 7 small Mermaid diagrams
                                 (or links to their owning narrative docs)
## 📁 Repository Structure       txt-fenced tree with inline comments
## 🗂️ Coursework Documentation   3 index tables -> Phase 4/5 docs
## 🚀 Quickstart                 short; links to the runbook
## 📌 Project Status             keep the honest status table
MOVED OUT -> docs/operator-runbook.md:
  Local Setup, Running in Docker, Product and platform .hecks, Service URLs,
  Run Stage 1 Evidence, Validation Commands, Useful Inspection Queries,
  Stop Services, Naming Convention details
```

The Demo section is the one reference element that needs a decision: the
reference embeds a GIF linking to an MP4. Produce one only if the product +
coordinator round-trip can be recorded cleanly while the cluster is up
(platform .indow). If not recorded, omit the section — do not ship a placeholder.

## Related Code Files

- Modify: `README.md` (full rewrite)
- Create: `docs/operator-runbook.md` (absorbs the moved operator sections)
- Create (optional): `docs/pngs/product_demo.gif` + `.mp4`
- Read only: the Phase 4/5 index READMEs, `docs/coursework.md`,
  `docs/system-architecture.md`

## Implementation Steps

1. Draft the five System Overview bullets. Each is one dense paragraph naming
   the real components of that subsystem — the reference's bullets are the
   quality bar: they name every technology and its role in one breath.
2. Move the operator sections verbatim into `docs/operator-runbook.md`, verify
   every command in them still works, then delete them from the README and
   replace with a Quickstart plus a link.
3. Insert the architecture section: the composed PNG from Phase 3 as the hero,
   then the small diagrams (inline for the two most important subsystems,
   linked for the rest to keep the README scannable).
4. Regenerate the repository tree from the actual current layout with inline
   comments per top-level directory. A stale tree is worse than none.
5. Build the three index tables from the Phase 4/5 README index tables — same
   rows, so the two stay consistent by construction.
6. Record the demo: if captured, embed `[![alt](docs/pngs/product_demo.gif)](docs/pngs/product_demo.mp4)`;
   if not, drop the section and note the omission in the plan report.
7. Keep the Project Status table honest — it currently states the submission
   freeze is pending. Do not upgrade a status that this plan does not change.
8. Run `check_documentation.py` (it link-checks `README.md` explicitly) and
   preview the rendered README on GitHub before committing.
9. Commit as `docs(readme): rebuild reviewer-facing README`.

## Success Criteria

- [ ] README follows the target section order with emoji headers
- [ ] System Overview has one dense paragraph per subsystem, all five present
- [ ] Architecture section shows the composed diagram plus the small-diagram set
- [ ] Repository tree matches the actual current layout
- [ ] Three index tables link to every Phase 4/5 narrative doc, no dead rows
- [ ] Operator content lives in `docs/operator-runbook.md`, commands verified
- [ ] Demo section is either a real recording or absent — no placeholder
- [ ] Project Status table remains accurate about the pending freeze
- [ ] `.venv/bin/python scripts/check_documentation.py` exits 0

## Risk Assessment

- **Risk:** README becomes marketing and loses the operator utility people
  actually use daily.
  **Mitigation:** nothing is deleted — operator content moves to a linked
  runbook and its commands are re-verified during the move.
- **Risk:** index tables drift from the Phase 4/5 indexes.
  **Mitigation:** generate them from the same source rows; Phase 7 diffs them.
- **Risk:** overclaiming in the System Overview.
  **Mitigation:** every technology named must appear in a Phase 4/5 doc with
  evidence; the Project Status table stays as the honesty anchor.
