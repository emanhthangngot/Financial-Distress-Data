---
phase: 3
title: "Phase 3: Rubric ownership, ADRs and contract reconciliation"
status: pending
priority: P1
effort: "Re-estimate from the measured baseline below; most artifacts exist and need reconciliation, not authoring"
dependencies: ["phase-01-naming-cutover.md", "phase-02-data-model.md"]
owns: ["docs/platform/adr/", "docs/rubric-matrix-unified.csv", "docs/architecture/low-level-design.md", "scripts/verify_rubric_coverage.py", "scripts/verify_target_architecture.py", "scripts/_rubric_items.py"]
---

# Phase 3: Rubric ownership, ADRs and contract reconciliation

## Overview

Preserve and reconcile the existing `docs/rubric-matrix-unified.csv`: 161 rows / 300 points.
Do not append 44 mini rows to an already unified matrix. Historical reports of missing ACs are
baseline findings, not current measurements. This phase gates consumer integration, not local
resource-free investigation. No target-image component count is an acceptance requirement.

## Measured baseline (2026-09-10)

Verified this session — do not re-derive from the 2026-09-01/02 audit prose:

- `docs/rubric-matrix-unified.csv` already holds 161 rows / 300 points: mini 44/100, ML 57/100,
  LLM 60/100, 20 columns including `owning_phase`. Every mini row is already owned by P2, P4, P5
  or P11. `evidence_type` is 60 `executed`, 57 `design_only`, 44 `pending`.
- Owner distribution: P2 7, P3 2, P4 32, P5 10, P6 4, P7 19, P8 27, P9 19, P10 15, P11 14, P12 12.
- ADR-001 through ADR-021 exist as files. ADR-016, ADR-017 and ADR-021 are already `Accepted`,
  with ADR-017 and ADR-021 recorded as implemented and merged to `dev` on 2026-09-05.
- `scripts/verify_rubric_coverage.py`, `scripts/verify_target_architecture.py`,
  `scripts/verify_naming_cutover.py` and `scripts/lint_naming_convention.py` exist.
- `docs/architecture/low-level-design.md` (310 lines) and `docs/architecture/data-model.md`
  (717 lines) exist.

So the remaining work is reconciliation against the 2026-09-10 decisions, executed-evidence
conversion and negative-case coverage — not authoring a matrix, an ADR stack or these scripts from
scratch. New session decisions take fresh IDs from **ADR-022 onward**; never reuse 016-021.

## Requirements and architecture

Three raw rubric CSVs -> unique canonical row IDs -> one owning phase and WHO -> ACTION -> RESULT
assertion -> executable validation -> attributable evidence. Keep the matrix's existing schema unless
an explicitly validated field is needed. Terminal `executed` means successful real behavior, not a
citation, screenshot of source, or a generated manifest. All 44 mini, 57 ML and 60 LLM rows remain.

The selected architecture inventory records capability, resource, owner, validation and rubric IDs.
`verify_target_architecture.py` verifies that inventory, not 83 logos. Record why omitted image-only
components are unnecessary. `verify_rubric_coverage.py` must support both design completeness
(owners/ACs) and final executed-evidence checks without calling the first a 300-point score.

Keep existing rubric ownership and exact IDs in phase citation blocks. P2/P4/P5/P11 own mini rows;
P6 cloud/Ansible, P8 custom inference/agents, P9 gateway/HTTPS/deployments, P10 per-artifact delivery,
P12 telemetry/final evidence. Shared evidence records the primary owner and supporting producer.

## ADR and data dictionary work

- Reconcile existing ADRs by content/ID before creating files. ADR-005 Feast Postgres offline,
  ADR-006 MLflow promotion, ADR-013 Debezium/Kafka/Flink and ADR-014 distributed training must match
  the implementation selected for their graded capability.
- ADR-022 supersedes ADR-016's O-1 with rubric-first, session-windowed deployment; no mandatory
  Jenkins/llm-d/Kiali restore. The shipped ADR-016 still states O-1 as binding until P3 executes
  this amendment (§Measured baseline, AC-P3-3) — do not cite ADR-016 alone as settling this. ADR-017
  records P2 temporal keys/grains and selection precedence; ADR-018 metadata unification; ADR-019
  residual naming/exceptions; ADR-020 measured source units, tier caps and explicit synthetic
  provenance; ADR-021 enforced type/naming contracts.
- Add uniquely numbered decisions for free-provider routing, LangChain/LangGraph boundary,
  session memory, Kaggle artifact bridge and conditional fine-tuning after checking current ADR IDs.
  They record accepted session choices; no second interview is needed for settled choices.
- Reconcile `docs/07_data_contracts.md`, ERD/schema documentation, Feast definitions and actual DDL:
  full grain, required vs optional fields, nullability, date roles, unit normalization, label
  availability, vintage selection, historical OBT and event IDs. P2 owns the definition; P3 records
  it; P4/P5 must demonstrate parity in executable paths.
- Produce the rubric-required low-level design for five meaningful classes per ML and LLM track,
  with signatures and request/data flow. Do not invent classes solely to fill the count.

## Related files

Own unified matrix, ADRs, canonical contract docs, `scripts/verify_*.py`, merged rubric definitions.
Inspect existing scripts first; update rather than recreate functioning verifiers. Coordinate
`scripts/lint_naming_convention.py` with P2 and P1's naming verifier; P12 later updates final docs,
not these definitions concurrently. No evidence purge is needed to author an ADR.

## Implementation steps

1. Parse source CSVs with multiline-cell support; reconcile existing IDs and scores by source row.
2. Assert one owner per row, all owners valid, every row cited by an AC in its owning phase.
3. Bind generic rubric citation text to the phase's concrete behavioral AC and runtime artifact;
   screenshot requirements remain in addition to machine-readable output.
4. Accept/reconcile ADRs and data dictionary; resolve source/DDL/Spark/Feast differences explicitly.
5. Update architecture and rubric verifiers. Seed a missing required resource/owner/evidence entry
   and prove each fails in its appropriate mode. A non-required logo must not fail architecture.
6. Record all optional extensions separately, with proposed thresholds distinguished from rubric.
   No cut ladder automatically deletes capabilities or claims lower-point completion.
7. Preserve baseline evidence and link provenance; only remove obsolete artifacts after replacement,
   resolvable baseline tag, reference check and explicit ownership. Validate affected code normally.

## Success criteria

- [ ] AC-P3-1: Rubric auditor -> parses source CSVs and existing matrix -> 161 unique rows and 300 points, track counts 44/57/60; no duplicate append.
- [ ] AC-P3-2: Coverage verifier -> validates ownership -> every row has exactly one valid primary phase and evidence/validation/assertion contract.
- [ ] AC-P3-2b: Coverage verifier -> checks phase AC citations -> every canonical rubric ID appears in its owning phase.
- [ ] AC-P3-2c: Auditor -> groups mini ownership -> all 44 rows/100 points assigned among P2/P4/P5/P11 with no missing row.
- [ ] AC-P3-3: Architect -> writes ADR-022 (first ID after the 016-021 block, per §Measured
      baseline) recording "Rubric before image fidelity — 2026-09-10" -> ADR-022 explicitly
      supersedes ADR-016's O-1 ("every component and annotated edge in
      `images/architecture/fdd-architecture-full-4k.png` must be live"), demoting it to a
      historical reference inventory **without dropping any rubric capability**; ADR-016 itself is
      amended to point at ADR-022 in its own Status section once P3 executes — this planning
      update makes no edit to the shipped `docs/platform/adr/adr-016-full-platform-restore.md` file
- [ ] AC-P3-4: Data architect -> reconciles ADR-017 and dictionary -> surrogate fact joins, vintage PKs, known_from_ts, Feast timestamps and explicit unavailable history agree with P2.
- [ ] AC-P3-5: Architect -> reviews dependent ADRs -> accepted facts match selected runtime; no stale paid/free-tier or framework capability assertion remains load-bearing.
- [ ] AC-P3-6: Architecture verifier -> checks a missing required capability -> fails; unselected image-only component is not counted as a failure.
- [ ] AC-P3-7: Naming verifier -> follows current matrix paths and commands -> no dangling active legacy reference remains; historical evidence keeps provenance.
- [ ] AC-P3-8: Reviewer -> reads low-level design -> five real ML and five real LLM classes with signatures and sequence flows (rubric citations below).
- [ ] AC-P3-9: Planner -> checks all session extensions -> owner, gate, artifact and explicit non-rubric thresholds present; no automatic point cuts.
- [ ] AC-P3-10: Engineer -> exercises changed verifier negative cases and quality gate -> missing ownership/evidence/required resources are rejected.
- [ ] AC-P3-11: Evidence owner -> proposes deleting obsolete evidence -> deletion blocked unless baseline tag resolves, replacement exists and consumers updated.
- [ ] AC-P3-12: Naming/type verifier -> checks P2 contracts -> catches invalid units/names/types/grain without conflating Bronze append-only grain with enforced PKs.

## Risks

A citation is not proof: P12 runs the actual behavioral assertion. A complete matrix can contain
stale evidence; record revisions and validate against affected code/data. Temporal dictionary drift
must block P4/P5 exit, not be patched by renaming columns in documentation alone.

## Rubric Citations (phase-03 R-12 closure, appended 2026-09-05)

Every rubric row this phase owns per `docs/rubric-matrix-unified.csv`'s `owning_phase` column, cited so `scripts/verify_rubric_coverage.py` can resolve ownership to an assertion (R-12). Each line names the row's real `rubric_id`, its stated requirement, and its proof artifact/deliverable — the row's own matrix columns, not invented text. Rows whose capability is not yet implemented are forward specs, matching this file's other `AC-P3-*` entries.

- AC-P3-RUBRIC-1: `LLM-documentation-low-level-ml-design` — llm_engineer -> delivers "Documentation ; (tất cả documents để trong folder `docs/`, và ở README.md thì mọi người link tới mấy document này nhé. README.md chỉ summari..." -> Document 5 key classes (evidence: `docs/platform/evidence/llm/LLM-documentation-low-level-ml-design.md`)
- AC-P3-RUBRIC-2: `ML-documentation-low-level-ml-design` — ml_engineer -> delivers "Documentation ; (tất cả documents để trong folder `docs/`, và ở README.md thì mọi người link tới mấy document này nhé. README.md chỉ summari..." -> Document 5 key classes (evidence: `docs/platform/evidence/ml/ML-documentation-low-level-ml-design.md`)
