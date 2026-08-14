# ADR-011: Keyless supply-chain provenance

## Status

Accepted — 2026-08-13.

## Decision

Phase 2 images are signed with keyless Sigstore Cosign in GitHub Actions. The
workflow obtains a short-lived Fulcio certificate from the GitHub Actions OIDC
identity, records the signature in Rekor, and attaches both an SPDX-JSON SBOM
and SLSA provenance attestation to the same immutable image digest. No
long-lived signing key is stored in the source or GitOps repositories.

The source catalog and GitOps gate reject tag-only image references. A deployed
reference must therefore be `repository@sha256:<64 lowercase hex>`, which makes
the signed subject unambiguous and lets Kyverno enforce the same invariant at
admission time.

## Evidence mapping

| Evidence contract | Supply-chain counterpart |
| --- | --- |
| `source_sha` | SLSA `invocation.configSource.digest` |
| `gitops_sha` | digest-bump commit in the GitOps checkout |
| `versions` | signed subject image digest |
| `command` | SLSA build definition and parameters |
| `redaction_status` | reviewed SBOM component list |

The `verify_supply_chain.py` developer tool verifies all three objects and
prints the registry responses, including provenance fields when the registry
returns them.

## Consequences and disclosure

Keyless signing avoids key rotation and secret leakage, but verification relies
on the public Fulcio and Rekor services and exposes the image digest and OIDC
identity to Rekor. It does not publish source files, credentials, or SBOM values
outside the registry's attestation payload. A registry or cosign outage blocks
the build's signing step; local catalog and digest checks remain offline.
