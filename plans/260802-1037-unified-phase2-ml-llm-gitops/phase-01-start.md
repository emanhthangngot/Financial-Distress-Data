---
title: "Phase 1: Lock specification and rubric contract"
status: in_review
estimate: "3-4 days"
---

# Phase 1: Lock specification and rubric contract

## Context

Phase 2 is explicit, but `docs/coursework.md` still describes LLM/Kubernetes/AWS as optional or excluded. This phase replaces that stale boundary with one accepted architecture and a machine-checkable, 200-point evidence contract before implementation begins.

Start checklist:

- Active phase: explicit Phase 2 final coursework.
- Specs read: `AGENTS.md`, `docs/spec.md`, `docs/mini_coursework.md`, `docs/coursework.md`, ML rubric CSV, LLM rubric CSV.
- Skills: `ak:plan`, then `ak:devops`; `financial-distress-sdd` was requested by repo law but is not installed in this checkout.
- Verification target: rubric linter returns no unmapped scored row, no unowned evidence, and no Phase 1 contract mutation.

## Requirements

- [x] Convert every ML and LLM CSV row into a stable rubric ID with source row/digest, points, requirement, Proof, Deliverables, acceptance ID, implementation owner/repo/file, contract test, behavior-validation command, and evidence path.
- [x] Write acceptance criteria only as `WHO -> ACTION -> RESULT`.
- [x] Separate executed proof, design-only claims, and optional stretch work.
- [x] Make the two-plane architecture, two-repository boundary, four traffic layers, and cost envelope normative.
- [x] Record the two custom ideas and five low-level classes for each track before code begins.

## Files

- Modify: `docs/coursework.md`, `docs/system-architecture.md`, `README.md`.
- Create: `docs/phase2/requirements.md`, `docs/phase2/acceptance-criteria.md`, `docs/phase2/rubric-matrix.{md,csv}`, `docs/phase2/architecture.md`, `docs/phase2/evidence-contract.md`, `docs/phase2/adr/`.
- Create tests/scripts: `tests/phase2/test_rubric_matrix.py`, `scripts/audit_phase2_evidence.py`.
- Do not modify Phase 1 data contracts, collectors, transforms, or evidence outputs.

## Implementation Steps

1. Give every non-header rubric row a semantic ID; do not rely on spreadsheet line numbers, which shift with multiline cells and headers.
2. Rewrite `docs/coursework.md` as the accepted Phase 2 source of truth while linking to, not duplicating, Phase 1 contracts.
3. Add numbered data flows for analyst, training, inference, agent, platform operator, CI/GitOps, observability, and teardown. Diagram nodes must be deployable units.
4. Add ADRs for two gateways, one source monorepo plus GitOps control repo, ephemeral EKS, KServe 0.18 pin, Feast stores, MLflow promotion, mixed Helm/Kustomize ownership, product-plane degradation, and active F5 NGINX OSS.
5. Seed failing rubric-matrix tests before implementing the linter; fail on a deleted/substituted source row even if totals remain 100, altered digest, unresolved acceptance ID, missing Proof/Deliverables, synthetic artifact directory, wrong repo, or absent behavior-validation command.
6. Define the named class contracts:
   - ML: `TrainingDataService`, `PointInTimeSplitService`, `FeatureMaterializationService`, `ModelTrainingService`, `ModelPromotionService`.
   - LLM: `RagIngestionService`, `EmbeddingRegistryService`, `McpToolService`, `AgentOrchestrationService`, `AgentReleaseService`.
7. Define novel ideas and proof:
   - ML: point-in-time leakage guard; cost-governed reproducibility manifest tied to data delta and model digest.
   - LLM: embedding-version hot swap; citation/PII guard whose decisions link to traces and evidence.

## Validation

- `python scripts/audit_phase2_evidence.py --matrix-only --strict`
- `pytest tests/phase2/test_rubric_matrix.py tests/test_stage1_quality_gates.py`
- Markdown link and Mermaid syntax checks.
- Canonical source audit asserts exactly 57 ML + 60 LLM rows and 100 points per track.

## Success Criteria

- [x] Coursework reviewer -> selects any scored row in either CSV -> finds an exact implementation, validation command, and planned artifact without inference.
- [x] Phase 1 maintainer -> compares the accepted Phase 2 spec to `docs/mini_coursework.md` -> finds additive boundaries and no silent change to Phase 1 semantics.
- [x] Developer -> runs the rubric linter on a deliberately incomplete fixture -> receives a failing result naming the missing contract field.
- [x] Auditor -> deletes one canonical rubric row and transfers its points to another -> rejects the altered matrix by source digest/count, even though the point total remains 100.

## AK Re-audit Closure (2026-08-02)

- Every row resolves to a section-level WHO -> ACTION -> RESULT ID in
  `docs/phase2/acceptance-criteria.md`; no 117-row prose duplication.
- `test` remains the mapping-contract test; `validation_command` is explicitly
  the future feature-specific behavior gate and must execute before Phase 8.
- `artifact_repo` distinguishes source from GitOps, and `artifact_path` is a
  concrete planned file rather than a rubric-ID directory.
- `EXPLICIT_IMPLEMENTATION` is an exhaustive reviewed map keyed by all 117
  rubric IDs; generated rows fail closed if an ID is missing or its owner/path
  diverges. No keyword fallback selects implementation files.
- Each behavior command is checked as the exact `acceptance_id` test file plus
  that row's `-k <rubric_id>` selector, so a substituted generic test cannot
  satisfy another row.
- Promotion requires a frozen 40-hex `PHASE1_BASE_SHA`; evidence source and
  GitOps SHAs must resolve to commits and equal the checked-out repository
  HEADs before a 100/100 claim is accepted.
- Canonical CSV row digest/count checks make point-transfer or omitted-row
  attacks fail closed.
- The CSV-export hyperlink loss is disclosed; official upstream URLs and
  exact version/digest pins are normative until original Sheet links exist.

## Risks and Rollback

- Risk: chasing all 200 points expands scope. Mitigation: use the cut policy in `plan.md`; never cut a scored item.
- Rollback: revert only Phase 2 documentation/linter commits; Phase 1 runtime stays untouched.

## Validation Decisions (Session 1)

<!-- Updated: Validation Session 1 - semantic slug IDs, role-based owner, stub contracts, per-deliverable AC, feature branch + PR, full coursework.md replacement, planned evidence paths -->

Locked by `/ak:plan validate` 2026-08-02 before implementation:

- Semantic IDs are slugs derived from requirement text (never spreadsheet line numbers).
- Class contracts ship as Python signature stubs in `src/ml/contracts.py` and `src/llm/contracts.py` plus `docs/phase2/low-level-design.md`.
- `owner` is role-based: `ml_engineer`, `llm_engineer`, `data_engineer`, `platform_operator`.
- Acceptance criteria are written per deliverable and per class (~20-30 total), not one per scored row.
- Work happens on branch `codex/phase2-spec-lock` off `dev`, merged via PR.
- `docs/coursework.md` is replaced wholesale; no archive copy kept.
- The linter's `--matrix-only --strict` validates a planned `docs/phase2/evidence/...` path per row (file need not exist); `--require-executed` is deferred to phase-08.

## Review Findings & Resolutions (Session 1 — 2026-08-02)

Spec-compliance review flagged 8 findings (3 P1, 3 P2, 2 P3). Resolutions:

- [P1] Validation command: every row's `test` field now holds a reproducible
  `pytest tests/phase2 -k '<rubric_id>'` command; generator + linter enforce it.
- [P1] Incomplete-fixture AC: `test_incomplete_fixture_fails_with_named_field`
  runs a real fixture CSV through the CLI with `--matrix` and asserts exit 1 +
  `missing 'owner'`; `test_audit_script_executable` now requires `--strict`.
- [P1] `--require-executed` enforces the full evidence contract (rubric_id,
  execution_timestamp, source_sha, gitops_sha, versions, command,
  expected/actual result, redaction_status); a near-empty executed file fails.
- [P2] Ownership mapping: `_assign_owner` provides the role taxonomy, while
  the exhaustive `EXPLICIT_IMPLEMENTATION` map locks each row's reviewed
  owner/repository/file and fails on any missing or divergent entry; linter
  still fails if any role owns no scored row.
- [P2] Phase 1 no-mutation: linter now also runs `git diff --name-only` against
  the base ref (`--git-base`, default `origin/dev` since Session 2) and flags
  protected-path changes.
- [P2] Architecture flows: rewritten with deployable-unit nodes only, every
  edge numbered, coordinator agent orchestrates specialist agents + MCP tools
  + model (not the reverse).
- [P3] Plan status aligned: phase table shows "In Review" until PR opens;
  phase file status `in_review`; PR action item remains unchecked.
- [P3] README marks `src/drift/` and `src/agents/` as planned Phase 2 dirs,
  not yet existing.

## Review Findings & Resolutions (Session 2 — 2026-08-02, re-review)

Re-review still blocked merge with 4 P1 + 4 P2. Resolutions:

- [P1] Validation commands now run real tests: `tests/phase2/test_rubric_row_
  contracts.py` generates one parametrized contract test per rubric row keyed
  by rubric_id, so `pytest tests/phase2 -k '<rubric_id>'` collects ≥1 test
  (previously exit 5, "no tests ran"). A collection pass asserts every id is
  matched and the first row's command runs end-to-end. This also surfaced a
  generator bug: the dedup suffix (`-1`) left `test`/`evidence_path` pointing
  at the pre-dedup id — now regenerated after dedup.
- [P1] `--require-executed` now rejects rows still recorded as design_only or
  stretch (every row must carry executed evidence), instead of only checking
  metadata on executed rows; verified with the `design-only-matrix.csv` fixture.
- [P1] No-mutation gate is fail-closed: default `--git-base` is `origin/dev`;
  an unresolvable baseline now exits 1 (was "skipped", exit 0); untracked new
  files are included via `git ls-files --others` so a brand-new protected-path
  file is caught too.
- [P1] Architecture contradictions fixed: NGINX terminates public TLS (was
  "TLS passthrough"); Flow 4 routes the prompt to the coordinator agent first,
  specialist agents appear and call MCP tools, and the coordinator drives model
  generation through Envoy AI Gateway (not prompt-straight-to-LLM); Flow 6 CI
  pushes the image to ECR and the promotion bot opens the GitOps PR directly
  (no source-repo merge); the flow intro now allows actor/artifact/process
  nodes (digest, PR, outbox) alongside deployable units, and missing units
  (admin UI, promotion bot, EventBridge Scheduler, CodeBuild) were added to
  the table.
- [P2] Linter smoke test now requires exit 0 (was accepting exit 2/crash).
- [P2] `tests/phase2/test_rubric_matrix.py` reformatted with black.
- [P2] The placeholder evidence file moved out of `docs/phase2/evidence/` into
  `tests/phase2/fixtures/ML-evidence-empty.md` (fixture mode skips the
  evidence-path prefix rule).
- [P2] Class-contract tests now import `src/ml/contracts.py` and
  `src/llm/contracts.py` and verify all five classes per track, their exact
  abstract methods, parameter names, and docstrings — not just file existence.

## Review Findings & Resolutions (Session 3 — 2026-08-02, implementation audit)

- [P1] Replaced heuristic artifact selection with an explicit 117-row map and
  added exhaustive map-parity assertions and parametrized tests.
- [P1] Bound every behavior-validation command to its acceptance file and exact
  rubric selector; the auditor rejects command substitution.
- [P1] Extended the Phase 1 protected-path check to promotion mode with an
  immutable baseline SHA instead of a moving branch ref.
- [P2] Promotion now verifies every evidence SHA is an existing commit and
  equals the source/GitOps checkout `HEAD`, not merely 40-hex syntax; both
  checkouts must be clean so audited files are contained in those commits.
