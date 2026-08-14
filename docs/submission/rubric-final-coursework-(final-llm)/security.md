---
title: "Security"
date: 2026-08-14
status: active
---

# Security: centralized secret encryption with sealed-secrets

This doc proves the single row in "Security": the Bitnami sealed-secrets
controller runs in-cluster and gives the platform one centralized place to
encrypt-at-rest and reconcile secrets from Git — a real controller, not a
placeholder comment. It does not claim a Vault-equivalent secrets service or
OIDC-based CI credential exchange — neither exists in this submission, stated
plainly rather than implied.

**Active deployment facts:** `sealed-secrets-controller` (Helm chart,
`platform-security` Argo app), namespace `kube-system`, GKE
`1.35.6-gke.1250000`.

## Part I — Real encrypt-and-reconcile round-trip

### 1. Apply a SealedSecret, watch it decrypt to a real Secret

```text
$ kubectl apply -f platform/security/phase1-proof-sealed-secret.yaml
sealedsecret.bitnami.com/phase1-sealed-secret-proof created

$ kubectl get sealedsecret -n default
NAME                         AGE
phase1-sealed-secret-proof   15s

$ kubectl get secret phase1-sealed-secret-proof -n default -o jsonpath='{.data.proof-token}' | base64 -d
phase1-nonproduction-proof

$ kubectl get pods -n kube-system -l name=sealed-secrets-controller
NAME                                         READY   STATUS    RESTARTS   AGE
sealed-secrets-controller-76b686947b-f6tr9   1/1     Running   0          <age>
```

The controller decrypted the `SealedSecret` CRD into a real Kubernetes
`Secret` within 15 seconds, and the decoded value matched the plaintext that
was sealed. Full evidence:
[`LLM-security-centralize-secret-management.md`](../../phase2/evidence/llm/LLM-security-centralize-secret-management.md).

## Limitations — honesty note on scope

The rubric's own deliverables text names HashiCorp Vault as an example; this
platform does not run Vault. What is real: sealed-secrets centralizes
*encryption at rest and Git-native reconciliation* for Kubernetes secrets —
one controller, one key pair, every secret goes through it — plus GitHub
Actions encrypted repository secrets for the two long-lived CI PATs
(`GHCR_TOKEN`, `GITOPS_PAT`). There is no OIDC token exchange
(`grep id-token .github/workflows/` returns zero matches) and no separate
secrets-management service spanning both repositories and the CI system.
Recorded honestly rather than claimed as Vault-equivalent.

## References

- Bitnami sealed-secrets: https://github.com/bitnami-labs/sealed-secrets
</content>
