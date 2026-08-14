# Live capacity check — 2026-08-13

Commands:

```text
gcloud compute regions describe asia-southeast1 --format=json
kubectl get nodes -o wide
kubectl get applications.argoproj.io -A -o wide
```

Observed:

| Resource | Limit | Usage | Result |
|---|---:|---:|---|
| Regional CPUS | 32 | 8 | headroom exists at the aggregate quota |
| Regional E2_CPUS | 8 | 0 reported by quota API | the current node pool is `e2-standard-8`; no safe scale-up headroom is assumed |
| External network LB forwarding rules | 50 | 3 | billing-leak cleanup remains outstanding |
| GKE nodes | 1 Ready | — | existing platform is healthy |

The cluster is reachable and current Argo applications report `Synced /
Healthy`, but the target 24-vCPU concurrent soak cannot be honestly claimed:
the E2 quota is 8 and the plan requires an external quota increase before
scaling. No quota mutation was attempted.
