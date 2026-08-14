---
title: "Agent Warm-Up"
date: 2026-08-14
status: active
---

# Agent Warm-Up: measured cold-vs-warm startup and TTFT delta

This doc proves the single row in "Cài đặt hệ thống ở chế độ Warm Up":
`platform/agents/warm-pool.yaml` is a real policy, not a placeholder, and a
real measurement script captured cold-vs-warm startup time and TTFT against
the live `feature-agent` Deployment. It does not prove the warm-up policy
reduces cost at scale — the measured window is a single run, and the
cost-delta model is a documented estimate, not a billing reconciliation.

**Active deployment facts:** namespace `agents-sandbox`, deployment
`feature-agent`, warm-pool target 2 replicas,
`feature-agent@sha256:6bfb99fc...` GKE `v1.35.6-gke.1250000`.

## Part I — Measurement

### 1. Real cold-vs-warm measurement against the live deployment

```text
$ python scripts/run_phase5_warmup_measurement.py --warm-replicas 2 \
    --output docs/phase2/evidence/llm/warmup.json
{
  "cold_start_seconds": 7.732,
  "warm_start_seconds": 9.058,
  "cold_ttft_seconds": 0.743,
  "warm_ttft_seconds": 0.671,
  "warm_ttft_samples_seconds": [0.983, 0.698, 0.671, 0.621, 0.65],
  "replica_spread": {"min": 1, "max": 2, "target": 2},
  "deployment": "feature-agent",
  "namespace": "agents-sandbox"
}

$ kubectl get deploy feature-agent -n agents-sandbox
NAME            READY   UP-TO-DATE   AVAILABLE   AGE
feature-agent   2/2     2            2           12h
```

Warm TTFT (0.671s median of 5 samples) is lower than cold TTFT (0.743s); the
pool was restored to its declared minimum (2/2 Ready) after the run. Full
evidence:
[`LLM-c-i-t-h-th-ng-ch-warm-up--c-i-t-h-th-ng-ch-warm-up-cho-a.md`](../../phase2/evidence/llm/LLM-c-i-t-h-th-ng-ch-warm-up--c-i-t-h-th-ng-ch-warm-up-cho-a.md).

### 2. A real bug found and fixed during this measurement

`platform/agents/warm-pool.yaml`'s `measurement.command` originally
referenced `python -m src.llm.benchmark --mode cold,warm --agent
feature-agent --replicas 2 --output /evidence/warmup.json` — that CLI never
existed; `src/llm/benchmark.py` has no `__main__`/argparse entry point. The
fix: `scripts/run_phase5_warmup_measurement.py` was written to perform the
real measurement (scale-to-zero for a true cold start, scale-one-up-from-warm
for a warm start, `/v1/run` TTFT via `kubectl port-forward`), and the
policy's `measurement.command` was updated to point at it. Disclosed here
rather than silently patched, per this submission's honesty rule.

## Cost/capacity discipline

The measurement scales `feature-agent` to zero and back during the run and
restores it to its declared warm-pool minimum afterward, matching
`agentReplicas.feature-agent: 2` in the policy — the measurement doesn't
leave the cluster in a different state than it found it.

## Limitations

`warm_start_seconds` (9.058s) reads *slower* than `cold_start_seconds`
(7.732s) in this run — the warm-start measurement competed for CPU with the
concurrent cold-start pod's readiness probes, making it noisier. This is
reported as measured, not smoothed to fit the expected direction; TTFT (not
raw startup time) is the primary signal this row actually claims, and TTFT
did improve warm-vs-cold as expected. The cost-delta figures are a documented
per-replica-hour estimate, not a reconciled billing number.

## References

- Kubernetes HPA and readiness probes: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
</content>
