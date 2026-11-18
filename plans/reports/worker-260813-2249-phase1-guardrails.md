# platform .uardrails report

Status: DONE

## Summary

- Extended `scripts/audit_phase2_evidence.py` platform .rotection coverage for
  `src/security`, `src/evidence`, `src/lakehouse`, `src/jobs`,
  `src/orchestration`, `src/io`, and `src/governance`.
- Added shared-package carve-outs for `src/io/paths.py` and
  `src/governance/phase2_lineage.py`.
- Added `--check-artifacts`; source paths resolve from this checkout and GitOps
  paths require `--gitops-root`. Executed gaps fail; design-only/stretch gaps
  warn.
- Added focused artifact contract tests covering executed missing artifacts,
  design-only warnings, and GitOps root resolution.

## Verification

- `pytest tests/platform/test_artifact_path_contract.py tests/platform/pipelines/test_audit_protected_paths.py -q`: 6 passed
- `pytest tests/platform/test_rubric_matrix.py -q`: 64 passed, 1 skipped
- `scripts/audit_phase2_evidence.py --matrix-only --strict`: pass
- Ruff, Black, and `git diff --check`: pass

Concerns/Blockers: none.
