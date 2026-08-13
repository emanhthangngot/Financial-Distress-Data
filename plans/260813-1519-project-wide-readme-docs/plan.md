# Project-wide documentation refresh

Status: completed

## Objective

Refresh the project-facing documentation so a reviewer understands the complete
Phase 1 + Phase 2 system, its separate product/evidence planes, operational
boundaries, evidence contract, run commands, and current submission status.

## Expected output

- A project-wide root README that describes the complete system rather than
  Stage 1 only.
- Aligned coursework, architecture, repository-map, file-map, and the
  complete submission-page index with the implemented Phase 2 LLM/product/
  GitOps scope.
- A short documentation report recording changed files, validation results, and
  any intentionally unresolved submission residuals.

## Acceptance criteria

- Reviewer -> opens `README.md` -> sees project scope, architecture, deployment
  flow, run/verify commands, repository boundaries, and honest completion state.
- Maintainer -> opens the documentation map -> reaches Phase 1 code, Phase 2
  code, product web, evidence, plans, and the separate GitOps repo without stale
  Stage-1-only guidance.
- Submission reviewer -> opens the submission index -> reaches the canonical
  LLM evidence and sees 60/60 rows, 100/100 logical coverage, pending freeze
  requirements, and known residuals without credentials being added or exposed.
- Documentation checks -> validate Markdown links, tracked paths, and relevant
  rubric/evidence contracts -> pass without changing application behavior.

## Scope

In scope: `README.md`, `docs/coursework.md`, `docs/system-architecture.md`,
`docs/phase2/architecture.md`, `docs/architecture/repository-map.md`,
`docs/project-file-map.md`, `docs/submission/*.md`, and this plan/report.

Out of scope: Python/TypeScript code, tests, DAG behavior, Kubernetes/GitOps
manifests, generated evidence files, credentials, evidence SHA stamping, the
scrubbed mirror, and GCP hibernation.

## Constraints

- Describe only behavior supported by the repository and recorded live
  evidence; distinguish verified, submitted, deferred, and residual states.
- Keep Phase 1 local-first semantics and Phase 2 additive-only boundaries.
- Do not copy or add secrets, tokens, private keys, or personal credentials.
- Preserve existing public links and document paths where possible.

## Verification

- Markdown/link/path checks for changed documentation.
- `.venv/bin/python -m pytest tests/test_documentation.py tests/test_readme_polish.py -q`.
- `.venv/bin/python scripts/audit_phase2_evidence.py --strict ...` is not a
  documentation gate in this phase because evidence SHA stamping is explicitly
  out of scope; record its existing freeze status honestly.

## Implementation order

1. Rewrite the root README around the complete system and reviewer journey. ✓
2. Align coursework, architecture, repository map, file map, and submission
   pages without modifying canonical evidence artifacts. ✓
3. Run focused documentation tests and link/path checks. ✓
4. Review for stale claims, secrets, and Phase 1/Phase 2 boundary violations. ✓
5. Finalize the plan/report and prepare a focused documentation PR. ✓

See [reports/docs-closeout-260813-1519-project-wide-readme.md](reports/docs-closeout-260813-1519-project-wide-readme.md)
for the verification snapshot and the intentionally unresolved freeze steps.
