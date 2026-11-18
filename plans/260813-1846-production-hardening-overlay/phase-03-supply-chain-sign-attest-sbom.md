---
phase: 3
title: "Supply chain: sign, attest, SBOM"
status: cancelled
priority: P1
effort: "2d"
dependencies: [2]
---

> **CANCELLED 2026-08-14 (user decision, ML track dropped).** Zero LLM rubric rows reference cosign/SBOM/SLSA attestation (measured against docs/platform/rubric-matrix.csv, 2026-08-14). This closed only ML rows (~5 pts). The fork-PR login guard fix this phase produced was kept (folded into the LLM-relevant CI commit); the cosign/SBOM/SLSA steps were reverted out of the shared `phase2-ci.yaml` because it also builds LLM deployables and the missing GHCR `write:packages` scope would have broken their CI runs too.
> Body below is kept as the historical record of what was planned/built; nothing further is executed against it. See `plan.md` Overview.

# Phase 3: Supply chain — sign, attest, SBOM

## Overview

Extend this project's strongest existing property — documentary provenance — down
to the artifact layer. Every image built by CI gets a keyless cosign signature
recorded in the Rekor transparency log, a SLSA build provenance attestation, and
an SBOM. Phase 5 then makes the cluster refuse anything lacking them.

Neither reference repo has this. It is the plan's principal novel contribution.

No cloud quota required — this is entirely build-side.

## Requirements

- Functional: every deployable image is signed keylessly, carries a provenance
  attestation naming the builder, source repo, commit SHA and build parameters,
  and ships an SBOM; all three are verifiable offline from the registry.
- Non-functional: no long-lived signing key exists anywhere; signing adds under a
  minute to each build.

## Architecture

Keyless signing is the point. Fulcio issues a short-lived certificate bound to the
GitHub Actions OIDC identity, cosign signs with it, and Rekor records the event in
a public append-only transparency log. There is no private key to store, rotate or
leak — which is exactly why it beats the alternative of a long-lived key in CI
secrets.

The provenance chain this creates maps one-to-one onto the existing evidence
contract, which is what makes it more than a checkbox:

| Evidence contract field | Supply-chain counterpart |
|---|---|
| `source_sha` (40-hex, ancestry-checked) | SLSA provenance `invocation.configSource.digest` |
| `gitops_sha` | digest-bump commit referenced by the deployed digest |
| `versions` (image digest) | the signed subject digest itself |
| `command` (reproduction) | SLSA `buildDefinition` parameters |
| `redaction_status` | SBOM component list, reviewed for leakage |

A rubric row can therefore be traced from its declared proof, to a commit, to a
build, to a signature, to the exact bytes admitted into the cluster. That is a
defensible novel-idea claim with machine-checkable evidence behind it.

`.github/workflows/phase2-ci.yaml` is the reusable job already used by eight
caller workflows, so signing is added once there and every deployable inherits it.

## Related Code Files

- Modify: `.github/workflows/phase2-ci.yaml` — signing, attestation, SBOM steps
- Create: `configs/phase2-deployables.yaml` — deployable catalog
- Create: `scripts/phase2_ci/__init__.py`, `catalog.py`, `gitops_paths.py`
- Create: `tests/platform/test_deployable_catalog.py`
- Create: `scripts/verify_supply_chain.py`
- Create: `docs/platform/adr/adr-011-supply-chain-provenance.md`
- Modify: `requirements-phase2.txt` — add `pyyaml`-based catalog deps if needed

## Implementation Steps

1. Create `configs/phase2-deployables.yaml` as the single catalog, consolidating
   the eight inline JSON deployable specs currently embedded in the caller
   workflows: `name`, `dockerfile`, `image_context`, `test_selector`,
   `lint_paths`, `gitops_chart`, `gitops_values_path`.
2. Create `scripts/phase2_ci/` as tested Python — the `RecSys-MLops` lesson that
   CI decisions belong in unit-tested code, not YAML. Provide catalog parsing,
   GitOps path resolution and digest-bump patch construction.
3. Add `tests/platform/test_deployable_catalog.py` asserting that every
   `gitops_values_path` and `gitops_chart` in the catalog resolves inside the
   GitOps checkout. **This is the unit test that would have caught the
   `platform/ml/` vs `platform/llm/` drift** at commit time rather than at
   phase 8.
4. Extend `phase2-ci.yaml`: after push, add `id-token: write` permission, run
   `cosign sign --yes <digest-ref>` keyless, generate the SBOM with Syft in
   SPDX-JSON, attach it with `cosign attest --type spdxjson`, and emit SLSA
   provenance via the GitHub Actions attestation action bound to the same digest.
5. Convert the eight caller workflows to read their deployable entry from the
   catalog rather than embedding JSON, one workflow per commit so a break is
   isolated.
6. Write `scripts/verify_supply_chain.py`: given an image reference, verify the
   cosign signature against the expected OIDC issuer and identity, verify the
   attestation predicate, and print the resolved provenance fields. This is both
   the developer tool and the evidence producer.
7. Write ADR-011 recording the keyless-over-keyed decision and the mapping table
   above.

## Verification

```bash
.venv/bin/python -m pytest tests/phase2 -k "deployable_catalog"
.venv/bin/python scripts/verify_supply_chain.py \
  ghcr.io/emanhthangngot/<deployable>@sha256:<digest>
cosign verify --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  --certificate-identity-regexp '.*' ghcr.io/.../<image>@sha256:<digest>
.venv/bin/python scripts/run_phase2_quality_gates.py --gitops-root ~/Studying/FSDS/financial-distress-gitops
```

## Success Criteria

- [ ] CI build -> completes -> image has a cosign signature, an SBOM attestation and a SLSA provenance attestation, all bound to the same digest
- [ ] `cosign verify` -> run offline against the registry -> succeeds and reports the GitHub Actions OIDC identity
- [ ] `verify_supply_chain.py` -> given a deployed digest -> prints the source commit SHA matching the rubric row's `source_sha`
- [x] `test_deployable_catalog.py` -> given a catalog entry with a wrong GitOps path -> fails
- [x] Strict `--track LLM` gate -> unchanged PASS 100/100

## ML rubric rows closed

- Security — centralize secret management (partial; completed in phase 6)
- CI/CD — "all secrets should be saved in Jenkins or similar" (keyless signing
  means there is no signing secret at all, which is the stronger answer)
- **Novel ideas x2** — the provenance chain from rubric row to admitted bytes is
  the strongest novel-idea candidate available and is genuinely absent from both
  reference implementations

Approximately 5 points, plus it is the precondition for phase 5's ~2.

## Risk Assessment

- **Rekor is a public transparency log.** Only image digests and OIDC identities
  are published, never source or secrets — but state this explicitly in ADR-011
  so the disclosure is a documented decision rather than an accident.
- **Converting eight workflows at once could break CI broadly.** Step 5
  deliberately converts one per commit.
- **GHCR registry permissions** must allow attestation push; verify the token
  scope early in the phase rather than discovering it at the end.
