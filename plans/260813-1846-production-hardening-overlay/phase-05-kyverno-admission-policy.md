---
phase: 5
title: "Kyverno admission and runtime policy"
status: cancelled
priority: P1
effort: "1d"
dependencies: [3, 4]
---

> **CANCELLED 2026-08-14 (user decision, ML track dropped).** Zero LLM rubric rows reference Kyverno (measured 2026-08-14). Closed only ML rows (~2 pts). The Kyverno manifests already written in the GitOps repo (Enforce mode) are committed as-is in the ML archive commit — not reverted, not extended.
> Body below is kept as the historical record of what was planned/built; nothing further is executed against it. See `plan.md` Overview.

# Phase 5: Kyverno admission and runtime policy

## Overview

Make phase 3's signatures load-bearing: the cluster refuses to run an image that
is not signature-verified and digest-pinned. This is the step that converts
provenance from a document claim into an enforced runtime property.

## Requirements

- Functional: unsigned images, images signed by an unexpected identity, and
  tag-based references are all rejected at admission; the rejection is observable.
- Non-functional: policies ship in `Audit` mode first and are promoted to
  `Enforce` in a separate, individually revertable commit.

## Architecture

Kyverno over OPA Gatekeeper: policies are Kubernetes-native YAML with no Rego to
learn, and Kyverno ships a first-class `verifyImages` rule that calls cosign
verification inline — exactly the primitive this plan needs. Gatekeeper would
require expressing signature verification through an external data provider.

Policy set:

| Policy | Rule | Mode progression |
|---|---|---|
| `require-signed-images` | `verifyImages` against the GitHub Actions OIDC issuer and this repo's identity | Audit -> Enforce |
| `require-digest-pinned` | reject any `image:` without `@sha256:` | Audit -> Enforce |
| `disallow-latest-tag` | reject `:latest` | Enforce immediately (nothing uses it) |
| `require-resource-limits` | every container declares CPU/memory requests and limits | Audit -> Enforce |
| `require-non-root` | `runAsNonRoot: true` | Audit -> Enforce |

The Audit-first progression matters: flipping straight to Enforce on a live
cluster with in-flight platform components would deadlock reconciliation for
upstream charts we do not control. Audit mode produces a `PolicyReport` naming
every violator, which is remediated before the flip.

Upstream platform charts (ingress, cert-manager, observability, Argo CD) are not
signed by our identity. They are exempted by namespace with an explicit,
documented exclusion list — an honest carve-out beats a policy so broad it proves
nothing.

## Related Code Files

GitOps repo:

- Create: `platform/security/kyverno-values.yaml`
- Create: `platform/security/policies/require-signed-images.yaml`
- Create: `platform/security/policies/require-digest-pinned.yaml`
- Create: `platform/security/policies/disallow-latest-tag.yaml`
- Create: `platform/security/policies/require-resource-limits.yaml`
- Create: `platform/security/policies/require-non-root.yaml`
- Create: `argocd/applications/platform-kyverno.yaml`
- Modify: `scripts/validate-gitops.sh` — kubeconform the new CRD kinds

Source repo:

- Create: `scripts/capture_admission_evidence.py`

## Implementation Steps

1. Add the Kyverno Argo CD Application with a pinned chart version and a sync
   wave earlier than the workloads it must guard.
2. Author the five policies in `Audit` mode. Scope `verifyImages` to our own
   registry path so upstream images are not silently matched.
3. Sync, then read the generated `PolicyReport` objects. Remediate every
   violation in our own workloads — most will be missing resource limits.
4. Add the documented namespace exclusion list for upstream platform components,
   with a one-line justification per entry.
5. Flip to `Enforce` in a **separate commit** so the flip is a one-line revert.
6. Write `scripts/capture_admission_evidence.py`: apply a deliberately unsigned
   image manifest and a deliberately tag-based manifest into a scratch namespace,
   capture the API server rejection messages and the `PolicyReport`, and write
   them as evidence artifacts. Negative-path evidence is the whole point — a
   policy that has never rejected anything proves nothing.
7. Re-run the GitOps gate and the strict LLM gate.

## Verification

```bash
kubectl get clusterpolicy
kubectl get policyreport -A
.venv/bin/python scripts/capture_admission_evidence.py
scripts/validate-gitops.sh   # in the gitops repo
```

## Success Criteria

- [ ] Kyverno -> receives a Pod with an unsigned image -> rejects it, message captured
- [ ] Kyverno -> receives a Pod with a tag-based reference -> rejects it, message captured
- [ ] Kyverno -> receives a correctly signed, digest-pinned Pod -> admits it
- [ ] `kubectl get policyreport -A` -> after remediation -> zero failures in our own namespaces
- [ ] Enforce flip -> reverted as a test -> cluster returns to Audit cleanly
- [ ] Strict `--track LLM` gate -> unchanged PASS 100/100

## ML rubric rows closed

- Security — service-to-service and workload authorization (partial; the mesh
  half lands in phase 6)
- CI/CD — deploy-gate credit, completing the section started in phase 2

Approximately 2 points, and it is what makes phase 3's ~5 points defensible
rather than decorative.

## Risk Assessment

- **Enforce mode can deadlock the cluster** if a platform component cannot satisfy
  a policy. Mitigated by Audit-first, the exclusion list, and the isolated flip
  commit.
- **`verifyImages` adds latency to every admission** and calls out to Rekor.
  Configure the Rekor URL explicitly and set a bounded timeout so a transparency
  log outage degrades to a clear failure rather than a hung API server.
- **Scratch-namespace test manifests must never reach a real namespace.** The
  capture script creates and deletes its own namespace.
