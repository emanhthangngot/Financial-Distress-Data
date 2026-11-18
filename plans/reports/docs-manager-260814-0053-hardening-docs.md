# Documentation audit — production hardening overlay

## Scope

Reviewed `AGENTS.md`, the production-hardening overlay plan, and the debugger
follow-up report. Audited the platform .vidence-capture documentation against the
verified fixes.

## Change

Updated `docs/platform/evidence/README.md` to document three observable capture
contracts:

- failed commands make the run fail;
- screenshot-declared sections fail when the screenshot command fails or emits
  no files;
- omitted source/GitOps SHAs are resolved from checkout `HEAD`, with an explicit
  `unresolved` marker when the checkout cannot be inspected.

No other documentation required correction for the reported fixes.

## Verification

- `.venv/bin/python -m pytest tests/platform/test_evidence_capture.py -q` — 4 passed
- `git diff --check` — clean

Status: DONE

Summary: Added only the missing user-facing capture semantics; no source,
tests, plans, or GitOps files were modified.

Concerns/Blockers: None.
