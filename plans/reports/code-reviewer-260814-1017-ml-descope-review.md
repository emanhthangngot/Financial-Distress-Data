# Code Review — ML-track descope + LLM evidence gate repair

Date: 2026-08-14
Reviewer: code-reviewer
Scope: `620975d..40c56dd` (source) + `32483a1..1d0ebb6` (gitops)

## Scope

- Source: 152 files, +7574/-129. GitOps: 57 files, +1522/-1.
- Focus: ML-vs-LLM classification correctness, workflow/config deletions,
  gitops archive path integrity, SHA-stamp commit integrity.
- Verification method: diff reading + path cross-referencing. Test suites not
  re-run (already verified by requester).

## Verified claims (all confirmed)

| Claim | Result |
| --- | --- |
| Commit #6 touches only `source_sha`/`gitops_sha` lines | **CONFIRMED.** Exactly 60 files, all `2 2` numstat, zero non-SHA `+`/`-` lines. |
| No LLM rubric row lost its artifact | **CONFIRMED.** All 60 LLM rows resolve (31 `source`, 29 `gitops`). Only 9 ML rows dangle. |
| The 9 dangling ML rows are non-fatal | **CONFIRMED.** All 9 are `evidence_type: design_only` → warnings in `_audit_artifacts`, never errors. |
| GitOps archive broke no surviving reference | **CONFIRMED.** No `argocd/` or `platform/` file references any archived path. `charts/` ↔ `apps/dev/` remains 1:1 (`drift-mcp`, `feature-mcp`, `web`). The `gateway-feature-api` Ingress in `platform/ingress/routes-ui.yaml:88` backs service `feature-mcp`, not the archived chart — name collision only. |
| `benchmark-client` revert restored the working role | **CONFIRMED.** `ansible/roles/benchmark-client/tasks/main.yml` contains the Locust venv install; tree clean; `ansible/playbooks/vast-evidence-worker.yml:22` still lists the role. |
| Catalog ↔ caller workflows consistent after ML removal | **CONFIRMED.** 8 catalog entries ↔ 8 caller workflows, matching `name`/`dockerfile`/`gitops_path`/`gitops_target_type`. |
| Login guard is safe | **CONFIRMED.** `if: github.event_name != 'pull_request'` on `docker/login-action` matches the pre-existing `push: ${{ github.event_name != 'pull_request' }}`. Cosign/upload steps carry the same guard. Net cosign diff is zero. |
| No stale `infra/phase2` references | **CONFIRMED** in executable surfaces. Remaining hits are only in `plans/` narrative records. |

## Critical

None.

## High

### H1 — `.githooks/pre-commit` blocks files the audit script explicitly permits

`.githooks/pre-commit` `protected[]` adds `src/lakehouse/`, `src/io/`,
`src/governance/`, `src/security/`, `src/evidence/`, `src/jobs/`,
`src/orchestration/`, mirroring the new `PHASE1_PROTECTED` in
`scripts/audit_phase2_evidence.py`. But the hook's `exceptions[]` is only:

```bash
exceptions=("src/streaming/flink/jobs/" "sql/init_ml.sql")
```

while the auditor carves out five more:

```python
"src/io/paths.py", "src/governance/phase2_lineage.py",
"src/lakehouse/catalog.py", "src/lakehouse/tables.py", "src/lakehouse/snapshots.py",
```

Impact: anyone with `core.hooksPath=.githooks` cannot commit an edit to
`src/lakehouse/catalog.py`, `tables.py`, `snapshots.py`, `src/io/paths.py`, or
`src/governance/phase2_lineage.py` — the exact files this branch just added.
The hook rejects what the gate accepts.

Fix: extract the protected/exception lists to one machine-readable file
(e.g. `configs/phase1-protected.yaml`) consumed by both, or at minimum copy the
five carve-outs into the hook. Two hand-maintained copies of one policy will
drift again.

Aggravating detail: the hook diffs `git diff --cached --name-only -z "${base_sha}"`
against `origin/dev`, not against `HEAD`. It therefore evaluates *every* file
that differs from `origin/dev`, not just the files in the current commit. On a
long-lived branch that has legitimately touched a protected path once, every
subsequent commit is blocked permanently.

### H2 — `build_digest_bump_patch` does not enforce the uniqueness its error message claims

`scripts/phase2_ci/gitops_paths.py`:

```python
updated, repo_count = re.subn(r"(?m)^(\s*repository:\s*).*$", ..., text, count=1)
updated, digest_count = re.subn(r"(?m)^(\s*digest:\s*).*$", ..., updated, count=1)
if repo_count != 1 or digest_count != 1:
    raise GitOpsPathError("values target must contain one image.repository and one image.digest")
```

`re.subn(..., count=1)` returns at most 1, so `!= 1` detects only *zero*
matches. A values file with a second `repository:`/`digest:` (sidecar,
initContainer, chart dependency block) silently gets its **first** occurrence
patched, which may be the wrong image. The regex is also not YAML-path aware —
it matches any `repository:` at any nesting depth, not specifically
`image.repository`.

Fix: count matches first (`len(re.findall(...))`) and raise when `> 1`, or
parse with `ruamel.yaml` and address `image.repository` / `image.digest`
explicitly. This writes to the GitOps control repo, so a wrong bump deploys the
wrong image.

### H3 — `configs/evidence-checklist.yaml` still mandates capture for the 10 cancelled phases

Commit #1 cancelled phases 03–12. The checklist retains a section for each:

- `phase3-supply-chain` runs `scripts/verify_supply_chain.py --help`. A `--help`
  invocation proves argparse works and nothing else — this is phantom evidence,
  and commit #3 reverted the cosign SBOM/SLSA/attest steps it would attest to.
- `phase5-kyverno` → `kubectl get clusterpolicy -A`, but all Kyverno policies
  are now in `archive/ml-track/platform/security/policies/`.
- `phase6-secrets-mesh` → `kubectl get externalsecret -A`; ESO manifests archived.
- `phase7-lakehouse` → `kubectl get deployment lakekeeper`; lakehouse archived.
- `phase8-cdc`, `phase9-phase1-plane` → `-n phase1-data`; `platform/data-phase1/` archived.
- `phase10-ml` → `-n phase2-ml`; `platform/ml/` archived.
- `phase11-rollouts` → `kubectl get rollouts,analysisruns`; `platform/rollouts/`
  archived. Its `screenshot_command` targets `--rollout feature-api --namespace
  phase2-data` — a Rollout whose chart is archived.

Because `_run_section` records a non-zero return code as `status: fail` and the
driver docstring says a failed command "makes the process fail",
`scripts/capture_phase2_evidence.py` is now guaranteed to fail for the LLM
submission. `tests/platform/test_evidence_capture.py::test_evidence_checklist_covers_all_overlay_phases`
pins this by asserting `len(sections) >= 12` and the presence of
`phase11-rollouts` / `phase12-freeze` by name — so the test actively defends the
inconsistency.

Fix: reduce the checklist to phase1/phase2 sections (plus phase12-freeze if the
UI screenshot is still in LLM scope), and change the test to assert the LLM
section set rather than a `>= 12` count.

## Medium

### M1 — `--check-artifacts` is an unwired mode whose flag semantics contradict its docstring

`scripts/audit_phase2_evidence.py`:

```python
fail = args.strict or args.require_executed or args.run_validations or args.check_artifacts
```

The docstring calls this "a lightweight backlog/reporting mode that can be run
while rows are still design-only", but passing the flag promotes **every**
finding in the run — including unrelated non-strict matrix findings — to fatal.
Either drop `args.check_artifacts` from the `fail` expression, or fix the
docstring to say it is a strict mode.

Separately, grep finds no invocation of `--check-artifacts` in
`.github/workflows/`, `.githooks/`, or `scripts/run_phase2_quality_gates.py`.
It is exercised only by its own unit test. New gate, no consumer.

### M2 — `configs/phase2-deployables.yaml` is a second source of truth with no binding contract

The file header calls itself "Source-of-truth metadata for the Phase 2
deployables", but the caller workflows still carry inline `deployables:` JSON,
and nothing cross-validates the two. The catalog is read only by
`run_phase2_quality_gates.py` and `tests/platform/test_deployable_catalog.py`;
CI itself never reads it.

They happen to agree today (I verified all 8 entries against the 8 caller
workflows), but only because the same commit edited both by hand — exactly the
failure mode the ML descope just had to clean up.

Fix: add a test that parses each caller's `deployables` JSON and asserts it
equals the corresponding catalog entry. That test would have made the ML removal
self-verifying.

### M3 — `test_deployable_catalog.py` asserts a magic count, not a set

```python
assert len(entries) == 8
```

Replace with the explicit name set. A count assertion passes if someone removes
`web` and adds `foo`, and the accompanying comment (`feature-api/drift-api
removed 2026-08-14`) is the kind of dated note that rots.

### M4 — gitops CI: image-pin gate silently skips on branch-create and force-push

`.github/workflows/validate-gitops.yml`:

```yaml
GITOPS_VALIDATE_BASE: ${{ github.event_name == 'pull_request' && github.event.pull_request.base.sha || github.event.before }}
```

On a branch-creation push, `github.event.before` is the all-zero SHA.
`validate-gitops.sh` then fails `git rev-parse --verify`, falls back to
`git diff HEAD` (empty on a fresh CI checkout) plus untracked files (none), and
prints `SKIP: image pin policy` while exiting 0. The digest-pinning gate — the
repo's headline invariant per its own `AGENTS.md` — is bypassed on exactly the
push shape most likely to introduce a new manifest.

Fix: when the base is unresolvable on a `push`, fall back to scanning all
tracked YAML rather than nothing, or fail closed.

### M5 — gitops CI installs helm/kubeconform/terraform without checksum verification

The workflow curls three tarballs/zips and `sudo install`s them, in a repo whose
`AGENTS.md` states "Every concrete container image reference must use
`@sha256:<64 hex>`". Versions are pinned but contents are not. Either add
`sha256sum -c` against pinned digests or use the maintained setup actions
(`azure/setup-helm`, `hashicorp/setup-terraform`) pinned to a commit SHA.

## Low

- **L1** — `tests/platform/pipelines/test_workflows_phase2.py::CALLERS` omits
  `phase2-drift-mcp.yaml` and `phase2-web.yaml`, both present on disk. The
  module docstring claims it pins "its list-driven callers". Pre-existing, but
  the same commit edited this list.
- **L2** — `test_catalog_gitops_paths_validate_when_checkout_is_available`
  depends on a sibling `../financial-distress-gitops` directory and skips in CI.
  Local-only coverage; acceptable, but do not count it as a CI gate.
- **L3** — `run_phase2_quality_gates.py` only passes `env=` when
  `require_real_digests` is true. A pre-existing `GITOPS_REQUIRE_REAL_DIGESTS=1`
  in the caller's environment leaks into the child regardless of the flag.
  Explicitly set the variable to `"0"` when the flag is off.
- **L4** — `capture_phase2_evidence.py` calls
  `screenshot_command.format(output_dir=...)` on a config-supplied string. Any
  literal `{` in a future command raises `KeyError`/`IndexError` mid-capture.
  Prefer `str.replace("{output_dir}", ...)`.
- **L5** — `validate-gitops.sh` writes `/tmp/gitops-secret-match.$$` with a
  predictable name; on a shared runner this is a symlink-clobber target. Use
  `mktemp`. Its secret regex `^(current-context|clusters|contexts|users):`
  will also false-positive on any manifest with a top-level `users:` key.
- **L6** — `_only_evidence_sha_lines_changed` tracks `current_path` from
  `+++ b/` only. For a whole-file deletion the header is `+++ /dev/null`, so
  `current_path` stays stale from the previous file. Exploitation requires the
  deleted file's every line to match `^[+-]\s*(?:[-*]\s*)?(?:\*\*)?(?:source_sha|gitops_sha)\s*:`,
  so impact is negligible — but reset `current_path` on `--- a/` for clarity.

## Operational note on the evidence gate (not a defect)

`source_sha` is stamped to `529fc06` (HEAD~1), not `40c56dd` (HEAD). This is
correct and unavoidable — `_revision_is_ancestor` + `_only_evidence_sha_lines_changed`
in `scripts/audit_phase2_evidence.py:614-657` were designed for exactly this
chicken-and-egg case.

The consequence to plan for: the gate holds only while every commit after
`529fc06` is SHA-line-only. **Merging this branch will itself invalidate all 60
evidence files** — the merge commit's diff against `529fc06` contains
non-evidence changes. Budget a re-stamp commit as the last commit on `main`
after the merge, or squash-merge and re-stamp.

Also note `platform/agents/agent-deployments.yaml` is the digest-bump target for
`feature-agent`/`drift-agent`/`coordinator`, so `apps/dev/feature-mcp/values.yaml`
has no catalog entry and its digest is never bumped by CI. Pre-existing, flagged
for awareness.

## Recommended actions

1. **H1** — sync `.githooks/pre-commit` exceptions with `PHASE1_PROTECTED_EXCEPTIONS`
   (ideally via one shared config). Blocking: the hook is unusable as shipped.
2. **H3** — trim `configs/evidence-checklist.yaml` to LLM-scope sections and
   relax the `>= 12` assertion in `test_evidence_capture.py`.
3. **H2** — enforce real uniqueness in `build_digest_bump_patch`.
4. **M2** — add a catalog ↔ caller-workflow equality test so the next descope
   is self-verifying.
5. **M4/M5** — fail-closed base resolution and checksum-verified tool installs
   in the gitops workflow.
6. **M1** — decide whether `--check-artifacts` is strict or advisory, then wire
   it into `run_phase2_quality_gates.py` or remove it.
7. Plan the post-merge SHA re-stamp commit.

## Unresolved questions

1. Is `.githooks/` intended to be activated (`core.hooksPath`)? Nothing in the
   diff sets it and no doc instructs it. If it is never activated, H1 is dead
   code rather than a blocker — but then the hook is unverified scope.
2. Is `verify_supply_chain.py` still in LLM scope? Phase 03 is cancelled and the
   cosign attest steps were reverted, yet the script and
   `tests/platform/test_supply_chain_verifier.py` remain, and the checklist calls
   it with `--help`.
3. Should the 9 ML rubric rows' `artifact_path` values be repointed at
   `archive/ml-track/...` in `docs/platform/rubric-matrix.csv`? They are harmless
   warnings today, but they are now factually wrong paths in a document that
   claims to be the rubric mapping.
