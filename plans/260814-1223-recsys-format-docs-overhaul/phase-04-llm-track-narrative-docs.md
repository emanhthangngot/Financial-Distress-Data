---
phase: 4
title: "LLM-track narrative submission docs"
status: done
priority: P1
effort: "2d"
dependencies: [1, 2, 3]
---

# Phase 4: LLM-track narrative submission docs

## Overview

The heart of the overhaul. Build
`docs/submission/rubric-final-coursework-(final-llm)/` — one narrative doc per
LLM rubric area, in the reference's numbered-step + quoted-code + Image proof +
Image note format, covering **all 21 areas** where the reference itself ships
only 3 and marks 18 "Work in progress".

## Requirements

- Functional: 21 rubric areas covered. The 60 canonical evidence rows in
  `docs/platform/evidence/llm/` are the source of truth; each narrative doc links
  to the rows it explains.
- Functional: every technical claim quotes real code from a repo-relative
  linked file, at the version in the working tree — not paraphrased.
- Functional: every screenshot is `#### Image proof` + image + `*Image note:*`
  stating what is visible, what it proves, and what it does not.
- Functional: before/after metric tables wherever an optimization is claimed
  (routing, warm-up, retrieval quality, drift latency).
- Non-functional: each doc ≤ 800 lines; split into `-part2` files rather than
  raising the gate.
- Non-functional: no evidence file moved out of `docs/platform/evidence/`.

## Architecture

Directory named after the rubric CSV tab, matching the reference convention:

```text
docs/submission/rubric-final-coursework-(final-llm)/
  README.md                        index table: area -> doc -> rows -> points
  llm_inference_platform.md        inference platform + custom model + benchmark
  global_model_config.md           shared model config, secret ref, agent use
  agent_registry.md                registry deploy + UI
  rag.md                           RAG pipeline + data governance for it
  web_api_user_data.md             feature-pull Web API (MCP tool + agent)
  web_api_drift_detection.md       real-time drift Web API (MCP tool + agent)
  agent_understanding.md           the two demonstration notebooks
  coordinator_agent.md             coordinator orchestrating 2+ agents
  agent_warm_up.md                 warm-up mode + measurement
  validation_verification.md       coverage, equivalence partitioning, boundary,
                                   mutation, property-based, load
  improve_data_generator.md        drift simulation, label table, config
  ci_cd.md                         the six CI/CD jobs
  routing_gateway.md               NGINX ingress, hidden services, auth, UIs
  iac.md                           Terraform + Ansible
  observability.md                 metrics, logs, traces, per-agent/tool metrics
  ab_testing.md                    model/prompt A/B + per-version monitoring
  security.md                      centralized secret management
  repository_design.md             clean repo, clean code, design patterns
  low_level_design.md              key service classes -> implementation map
  novel_ideas.md                   embedding registry + citation guard
  cost.md                          cost deliverable (already exists, rewritten)
```

Per-doc skeleton (from `docs/docs-style-contract.md`):

```text
# <Area>: <what it actually delivers>
<scope paragraph — what this doc proves and what it does not>
<active deployment fact list: project, namespace, runtime, versions, replicas>
## Part I — <deploy / build>
### 1. <imperative step>      code quote + repo-relative link
#### Image proof              image + *Image note:*
### 2. ...
## Part II — <baseline / behavior>
## Part III — <optimization / result>
<metric comparison table>
<honest limitation paragraph>
## References                 internet links used
```

## Related Code Files

- Create: `docs/submission/rubric-final-coursework-(final-llm)/*.md` (~21 docs)
- Modify: `docs/submission/README.md` — becomes the two-tab reviewer index
- Retire (Phase 7): the current flat `docs/submission/{ci_cd,iac,observability,
  routing_gateway,security,validation_verification,cost}.md` after their content
  is absorbed and links are rewired
- Read only (source of truth): `docs/platform/evidence/llm/*.md` (60 rows),
  `docs/platform/rubric-matrix.csv`, `docs/platform/evidence-contract.md`,
  `docs/coursework.md`, `docs/Coursework Tracking (Public) - rubic
  final-coursework (final - llm).csv`
- Read only (code to quote): `src/llm/`, `src/agents/`, `src/drift/`, `apps/`,
  `dags/phase2/`, `scripts/phase2_ci/`

## Implementation Steps

1. Build the area→rows→evidence-files map from
   `docs/platform/rubric-matrix.csv` and the LLM rubric CSV. Every one of the 60
   rows must be claimed by exactly one narrative doc. A row claimed twice or
   zero times is a mapping bug — fix before writing.
2. Write `docs/submission/rubric-final-coursework-(final-llm)/README.md` first:
   the index table (area | doc | rows | points | evidence). Writing the index
   first forces the mapping to be complete before prose starts.
3. Write the docs in dependency order so shared context accumulates:
   `llm_inference_platform` → `global_model_config` → `agent_registry` →
   `rag` → the two web APIs → `agent_understanding` → `coordinator_agent` →
   `agent_warm_up` → then the cross-cutting ones (`ci_cd`, `routing_gateway`,
   `iac`, `observability`, `ab_testing`, `security`) → then the meta ones
   (`validation_verification`, `improve_data_generator`, `repository_design`,
   `low_level_design`, `novel_ideas`, `cost`).
4. For each doc: quote code by reading the file at its current state and
   copying the exact lines; link the file repo-relative; never paraphrase a
   config value.
5. For each doc: embed its subsystem Mermaid diagram from Phase 3 where the
   subsystem is first introduced.
6. For each doc: pull its images from `docs/pngs/` (Phase 2) and write the
   `*Image note:*` paragraph per the contract — visible / proves / does not
   prove.
7. For each optimization claim: build the before/after metric table from real
   captured numbers. If a baseline was never measured, say so in the limitation
   paragraph instead of inventing one.
8. For each doc: close with the honest limitation paragraph. Follow the
   reference's own example — it states plainly that its baseline-vs-optimized
   run "is an infrastructure before/after comparison, not a strict router-policy
   A/B test". Match that candor.
9. Run `check_documentation.py` after every 3–4 docs, not at the end — the link
   gate is cheap and catching a broken path early beats a 21-doc sweep.
10. Commit per logical group: `docs(phase2): narrative submission docs for <group>`.

## Success Criteria

- [ ] All 21 LLM rubric areas have a narrative doc; none says "Work in progress"
- [ ] All 60 canonical rows are claimed by exactly one doc, per the index table
- [ ] Every doc follows the skeleton: scope → deployment facts → numbered
      Part/step structure → Image proof/Image note → limitations → references
- [ ] Every code quote matches the linked file's current content verbatim
- [ ] Every screenshot has an Image note covering visible / proves / not-proves
- [ ] Every optimization claim carries a real before/after table or an explicit
      statement that no baseline exists
- [ ] No doc exceeds 800 lines
- [ ] `.venv/bin/python scripts/check_documentation.py` exits 0
- [ ] `.venv/bin/python scripts/audit_phase2_evidence.py --track LLM` shows no
      new findings versus the pre-change baseline

## Risk Assessment

- **Risk:** the biggest one — narrative claims drift from what the evidence
  files actually prove, producing a prettier but less honest submission.
  **Mitigation:** step 1's exclusive row→doc mapping; the audit gate stays the
  arbiter; the limitation paragraph is mandatory, not optional.
- **Risk:** quoted code goes stale as the tree changes.
  **Mitigation:** quote-and-link discipline; Phase 7 re-verifies quotes against
  the final commit before freeze.
- **Risk:** 800-line gate hit mid-doc, tempting a cap raise.
  **Mitigation:** contract already mandates part-splitting; the cap is a
  reviewer-attention feature, not an obstacle.
- **Risk:** absorbing the old flat submission docs loses content.
  **Mitigation:** absorb first, retire in Phase 7 only after the new doc covers
  every claim the old one made.
