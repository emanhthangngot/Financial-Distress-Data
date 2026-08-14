---
phase: 6
title: "Secrets: ESO + Secret Manager, and Linkerd"
status: cancelled
priority: P2
effort: "1.5d"
dependencies: [4]
---

> **CANCELLED 2026-08-14 (user decision, ML track dropped).** Zero LLM rubric rows reference External Secrets Operator or Linkerd (measured 2026-08-14). The LLM track's own 'Security — Centralize secret management' row is already `executed` via a different artifact_path; this phase's ESO/Vault/Linkerd manifests targeted the separate ML-track security rows. Archived, not deleted.
> Body below is kept as the historical record of what was planned/built; nothing further is executed against it. See `plan.md` Overview.

# Phase 6: Secrets (ESO + Secret Manager) and service mesh (Linkerd)

## Overview

Replace the non-rotatable Sealed Secrets mechanism with External Secrets Operator
backed by GCP Secret Manager, and add a service mesh so service-to-service calls
are mutually authenticated and authorized rather than merely network-policied.

## Requirements

- Functional: application secrets are sourced from Secret Manager at runtime and
  rotate without a Git commit; service-to-service traffic is mTLS with an explicit
  authorization policy; unauthorized service calls are denied and observable.
- Non-functional: no secret material, sealed or plain, remains in Git for the
  migrated secrets.

## Architecture

**Secrets.** Sealed Secrets works and is currently deployed, but its ciphertext
lives in Git and rotation means re-sealing and re-committing by hand. External
Secrets Operator reads from GCP Secret Manager via Workload Identity and
materializes a Kubernetes Secret; rotation happens in Secret Manager and ESO
re-syncs. Git holds only an `ExternalSecret` reference — a pointer, not a payload.
Vault was rejected in the plan contract: it would add a server, an injector, an
unseal procedure and HA storage for capability this project does not need.

Migration is incremental and reversible: ESO is installed alongside Sealed
Secrets, secrets move one at a time, and Sealed Secrets is only removed once every
consumer is verified. Do not attempt a big-bang cutover of the credentials the
cluster is currently running on.

**Mesh.** Linkerd over Istio, deliberately. The rubric row is worth one point
("using service mesh to authorize access from service to service") and Istio's
control plane plus sidecars would consume a meaningful fraction of the phase 4
capacity budget. Linkerd's Rust micro-proxy is substantially lighter and provides
exactly what the row asks: automatic mTLS plus `AuthorizationPolicy`.

The existing `default-deny` NetworkPolicy stays. Mesh authorization and network
policy are different layers — L7 identity versus L3/L4 reachability — and keeping
both is the correct production posture, not redundancy.

## Related Code Files

GitOps repo:

- Create: `platform/security/external-secrets-values.yaml`
- Create: `platform/security/secret-store.yaml` (`ClusterSecretStore`)
- Create: `platform/security/external-secrets/*.yaml` (one per migrated secret)
- Create: `platform/security/linkerd-values.yaml`
- Create: `platform/security/authorization-policies.yaml`
- Create: `argocd/applications/platform-eso.yaml`, `platform-linkerd.yaml`
- Modify: `terraform/gcp/` — Secret Manager secrets, service account, Workload Identity binding
- Delete (last step only): superseded `*-sealed-secret.yaml` files

Note: `platform/security/authorization-policies.yaml` and
`platform/security/vault-external-secrets.yaml` are already **declared** in the
rubric matrix but absent from disk — this phase creates the first and supersedes
the second (rename the matrix row's `artifact_path` to the ESO manifest).

## Implementation Steps

1. Terraform: create the Secret Manager secrets, a dedicated service account with
   `secretAccessor` on exactly those secrets, and the Workload Identity binding.
   Least privilege — not project-wide access.
2. Install ESO via Argo CD; create the `ClusterSecretStore` pointing at the
   project with Workload Identity auth.
3. Migrate secrets one at a time: create the `ExternalSecret`, confirm the
   materialized Secret matches, repoint the consuming workload, verify, then
   remove the corresponding Sealed Secret. Repeat.
4. Demonstrate rotation: change a value in Secret Manager, observe ESO re-sync
   and the consumer pick it up without any Git commit. Capture as evidence — the
   rotation demo is the whole justification for this phase.
5. Install Linkerd; annotate the application namespaces for proxy injection.
   Leave data-plane-heavy namespaces (Kafka, Flink) un-injected initially to
   limit blast radius and overhead.
6. Write `AuthorizationPolicy` objects: the web app may call the MCP services and
   the inference gateway; nothing else may. Then demonstrate a **denied** call
   from an unauthorized workload and capture it.
7. Update the rubric matrix `artifact_path` for the two affected security rows to
   point at the manifests that now exist. Re-run `--check-artifacts`.

## Verification

```bash
kubectl get externalsecret -A
kubectl get secret <migrated> -o jsonpath='{.metadata.annotations}'
linkerd check
linkerd viz stat deploy -n <ns>
.venv/bin/python scripts/audit_phase2_evidence.py --check-artifacts \
  --gitops-root ~/Studying/FSDS/financial-distress-gitops
```

## Success Criteria

- [ ] ESO -> value rotated in Secret Manager -> consuming pod sees the new value with zero Git commits, captured
- [ ] `kubectl get externalsecret -A` -> all report `SecretSynced`
- [ ] Git -> searched after migration -> contains no sealed or plain material for the migrated secrets
- [ ] Linkerd -> service-to-service call -> reported as mTLS in `linkerd viz`
- [ ] `AuthorizationPolicy` -> unauthorized workload calls a protected service -> denied, denial captured
- [ ] Strict `--track LLM` gate -> unchanged PASS 100/100

## ML rubric rows closed

- Security — centralize secret management (1 pt), completing what phase 3 started
- Security — service mesh authorization service-to-service (1 pt)

## Risk Assessment

- **A botched secret migration can take down running services**, including the
  ones serving already-captured LLM evidence. Step 3's one-at-a-time protocol with
  verification between each is mandatory; do not batch.
- **Workload Identity misconfiguration fails opaquely.** Verify the binding with a
  debug pod before migrating any real secret.
- **Mesh injection can break workloads** with unusual networking. Start with
  application namespaces only; data-plane namespaces are explicitly out of scope
  for injection in this phase.
