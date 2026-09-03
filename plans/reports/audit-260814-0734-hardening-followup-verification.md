# Audit — hardening follow-up + plan sync reports

Scope: independently re-run every claim in
`debugger-260814-0052-hardening-followup.md` and `pm-260814-0058-plan-sync.md`
on branch `feat/production-hardening-overlay`, working tree as found (61
uncommitted paths in source repo, 29 in `../financial-distress-gitops`).

## Verdict

Reports are **numerically accurate but overstate one P0 invariant**. 12 of 13
claimed checks reproduce exactly. One claim (`LLM executed gate: pass`) does not
reproduce with the canonical strict invocation, and two failure modes are
under-reported.

## Reproduced as claimed

| Claim | Re-run result |
|---|---|
| Full tests 311 passed | `.venv/bin/python -m pytest tests` -> 311 passed, 1.46s |
| Ruff / Black | ruff PASS; black 328 files unchanged |
| Docker Compose config | PASS |
| platform .ate + GitOps | 72 passed, 1 skipped; kubeconform 302 resources, 190 valid, 0 invalid/errors; Helm lint 6 charts, terraform fmt/validate PASS |
| Strict real-digest gate fails on 4 API values | exact: `apps/dev/{drift,feature}-api/values.yaml`, `charts/{drift,feature}-api/values.yaml`, all `sha256:0000…` |
| ML gate 57 `design_only` | confirmed (59 findings = 57 design_only + 2 missing-arg) |
| Matrix strict | `--matrix-only --strict` PASS |
| `--check-artifacts` with `--gitops-root` | PASS, zero missing artifacts |
| API `/healthz` `/readyz` `/metrics` | present in `apps/feature-api/app/main.py:45-51`, `apps/drift-api/app/main.py:63-69` |
| Kyverno digest + signature Enforce | `require-signed-images.yaml:10`, `require-digest-pinned.yaml:9`, `disallow-latest-tag.yaml:9` = Enforce (non-root, resource-limits still Audit — correct, not claimed) |
| cosign empty/non-JSON rejection | `scripts/verify_supply_chain.py:63-73` raises on empty payload and `JSONDecodeError` |
| Evidence capture fail-closed | `scripts/capture_phase2_evidence.py:95-110` marks missing command / screenshot-without-command as `fail` |
| Plan sync row counts (3/16, 3/3, 2/3, 0/61; 8 checked) | exact match against phase-file checkbox counts |

## Discrepancies

### 1. `LLM executed gate: pass` does not reproduce — P0 invariant currently RED

Canonical command from `scripts/audit_phase2_evidence.py:6-9`:

```
audit_phase2_evidence.py --require-executed --run-validations --track LLM \
  --phase1-base ddbcbe7bd41ae4883954b8a247efdc67c7329078 \
  --gitops-root ../financial-distress-gitops --ml 100 --llm 100
```

Result: **122 findings — FAIL**. Breakdown:

- 60x `changes after source_sha=6ee3175… are not limited to SHA lines in evidence files`
- 60x `changes after gitops_sha=a9491d1… are not limited to SHA lines in evidence files`
- 1x `source checkout is not clean; commit evidence and implementation files before promotion`
- 1x `GitOps checkout is not clean; commit all declared manifests before promotion`

Reduced invocations fail too (`--require-executed --track LLM` -> 29 findings;
without `--phase1-base`/`--gitops-root` -> 31). There is no flag combination
found that yields the reported PASS.

Cause is not a code defect: the whole hardening slice is **uncommitted** (61
paths here, 29 in the GitOps repo), so evidence rows' recorded `source_sha` /
`gitops_sha` are stale against a dirty tree. Plan acceptance criterion 1 ("gate
runs after every phase -> PASS 100/100, protected diff clean") is therefore not
currently satisfiable. Fix is mechanical — commit both repos, re-stamp evidence
SHAs, re-run — but until then the reports' green LLM line is not defensible.

### 2. ML gate has a hard error the report omits

Beyond the 57 `design_only` rows, 2 rows fail with:

```
behavior validation failed with exit 4 — ERROR: file or directory not found: tests/platform/requirements/test_ml_ac_01_web_api.py
```

3 rows in `docs/platform/rubric-matrix.csv` reference that file; it does not exist
(`tests/platform/requirements/` holds only `test_llm_ac_*`). This is an in-repo
gap fixable now, not an external blocker — the report frames the ML failure as
entirely `design_only`-driven.

### 3. "Full tests: 311 passed" is mislabeled

`tests/phase2` collects **zero** tests under `.venv` (platform .eps live in
`.venv-phase2`). Real platform .overage: `.venv-phase2 -m pytest tests/phase2` ->
**557 passed, 35 skipped in 55s**. The 311 figure is the platform .uite only, and
the 72-passed gate figure is a gate subset, not the phase-2 suite. Neither is
wrong; the label "Full tests" is.

## External blockers — confirmed as stated

GHCR `write:packages` scope, absent cluster CRDs (Kyverno/ESO/Linkerd/KEDA/Argo
Rollouts/Lakekeeper), `E2_CPUS=8` vs 24-vCPU soak target: all consistent with
the 4 zero-digest failures and with zero live-evidence rows checked. No sign of
fabricated evidence, cluster mutation, or inflated checkbox counts — the
"deliberately not marked complete" list is honest.

## Recommended next actions

1. Commit source + GitOps working trees on their branches, re-stamp evidence
   `source_sha`/`gitops_sha`, re-run the strict LLM gate. Until this is green,
   do not report the LLM invariant as held.
2. Add `tests/platform/requirements/test_ml_ac_01_web_api.py` or repoint those 3
   matrix rows — removes 2 ML findings without any external dependency.
3. Relabel verification tables: state the venv and the selection for each
   pytest number.

## Unresolved questions

- Which exact command produced the reported `LLM executed gate: pass`? If it
  was run pre-dirty-tree, the report should timestamp it.
- "API container smoke: PASS" was not re-verified here (requires container
  build); not disputed, just unchecked.
