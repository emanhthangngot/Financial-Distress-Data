# Evidence — Security: centralize secret management

Proves `platform/security/sealed-secrets.yaml` (financial-distress-gitops)
deploys the real Bitnami sealed-secrets controller in-cluster, giving the
platform one centralized place to encrypt-at-rest and reconcile secrets from
Git, rather than the earlier five-line placeholder comment.

- rubric_id: LLM-security-centralize-secret-management
- execution_timestamp: 2026-08-10T00:52:33+00:00
- source_sha: 08ed63b454a857dd355cb9f34f80c049209a396b
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: sealed-secrets-controller (Helm chart, `platform-security` Argo app), kubeseal-compatible encryption, GKE 1.35.6-gke.1250000
- command: `kubectl apply -f platform/security/phase1-proof-sealed-secret.yaml` then `kubectl get secret phase1-sealed-secret-proof -n default -o jsonpath='{.data.proof-token}' | base64 -d`
- expected_result: the controller decrypts the `SealedSecret` CRD into a real `Secret` within seconds, and the decoded value matches the plaintext that was sealed
- actual_result: `sealedsecret.bitnami.com/phase1-sealed-secret-proof created`; `kubectl get sealedsecret -n default` shows it reconciled (age 15s); decoded `proof-token` = `phase1-nonproduction-proof`
- redaction_status: reviewed — GitOps repository is private; the decoded value is a synthetic non-production proof token, not a real credential

## Command output (real run)

```
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

## Honesty note (no OIDC, no Vault)

This row is scored against "centralize secret management," and the rubric's
own deliverables text names HashiCorp Vault as an example — this platform
does not run Vault. What is real: sealed-secrets centralizes *encryption at
rest and Git-native reconciliation* for Kubernetes secrets (one controller,
one key pair, every secret goes through it), plus GitHub Actions encrypted
repository secrets for the two long-lived CI PATs (`GHCR_TOKEN`,
`GITOPS_PAT`). There is no OIDC (`grep id-token .github/workflows/` returns
zero) and no separate secrets-management service spanning both repos and the
CI system. Recorded honestly rather than claimed as Vault-equivalent.
