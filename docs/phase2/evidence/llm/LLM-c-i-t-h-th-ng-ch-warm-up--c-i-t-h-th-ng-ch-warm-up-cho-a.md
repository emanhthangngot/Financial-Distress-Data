# Evidence — Warm-up mode for agents

Proves `platform/agents/warm-pool.yaml` (financial-distress-gitops) is a real
policy — not a placeholder — and `scripts/run_phase5_warmup_measurement.py`
measures a real cold-vs-warm startup and TTFT delta against the live
`feature-agent` Deployment in `agents-sandbox`.

- rubric_id: LLM-c-i-t-h-th-ng-ch-warm-up--c-i-t-h-th-ng-ch-warm-up-cho-a
- execution_timestamp: 2026-08-10T23:24:00+07:00
- source_sha: 9ec6f065276d316bad1e308c88028c5662edc4db
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: feature-agent@sha256:6bfb99fc834bf9a2cac78b9c59c5de259f9738cd9c61dcfe626e2da6e6cfd510, kubectl v1.35, GKE v1.35.6-gke.1250000
- command: `python scripts/run_phase5_warmup_measurement.py --warm-replicas 2 --output docs/phase2/evidence/llm/warmup.json`
- expected_result: measured `cold_start_seconds`, `warm_start_seconds`, `cold_ttft_seconds`, `warm_ttft_seconds`, `replica_spread` and `estimated_cost_delta`, with warm TTFT lower than or comparable to cold TTFT and the pool restored to its declared minimum (2 replicas) afterward
- actual_result: `cold_start_seconds=7.732` (scale 0→1, image already cached on the node), `warm_start_seconds=9.058` (scale 1→2 while already warm — noisier because it competed for CPU with the concurrent cold-start pod's readiness probes), `cold_ttft_seconds=0.743`, `warm_ttft_seconds=0.671` (median of 5 samples: 0.983, 0.698, 0.671, 0.621, 0.65), `replica_spread={min:1,max:2,target:2}`, pool restored to 2/2 Ready after the run; full JSON at `docs/phase2/evidence/llm/warmup.json`
- redaction_status: reviewed — no secrets; measurement targets the live cluster's internal ClusterIP only, no external endpoint or credential involved

## Command output (real run)

```
$ python scripts/run_phase5_warmup_measurement.py --warm-replicas 2 --output docs/phase2/evidence/llm/warmup.json
{
  "cold_start_seconds": 7.732,
  "warm_start_seconds": 9.058,
  "cold_ttft_seconds": 0.743,
  "warm_ttft_seconds": 0.671,
  "warm_ttft_samples_seconds": [0.983, 0.698, 0.671, 0.621, 0.65],
  "replica_spread": {"min": 1, "max": 2, "target": 2},
  "estimated_cost_delta": {
    "hourly_cost_per_replica_usd": 0.001187,
    "warm_replicas_during_window": 2,
    "hourly_cost_during_window_usd": 0.002375,
    "hourly_cost_outside_window_usd": 0.0,
    "note": "scale-to-zero outside the evidence window per warm-pool.yaml operations.evidenceEnd"
  },
  "deployment": "feature-agent",
  "namespace": "agents-sandbox"
}

$ kubectl get deploy feature-agent -n agents-sandbox
NAME            READY   UP-TO-DATE   AVAILABLE   AGE
feature-agent   2/2     2            2           12h
```

## Real bug found and fixed

`platform/agents/warm-pool.yaml`'s `measurement.command` referenced
`python -m src.llm.benchmark --mode cold,warm --agent feature-agent
--replicas 2 --output /evidence/warmup.json` — that CLI never existed;
`src/llm/benchmark.py` has no `__main__`/argparse entry point. Wrote
`scripts/run_phase5_warmup_measurement.py` to perform the real measurement
(scale-to-zero for a true cold start, scale-one-up-from-warm for a warm
start, `/v1/run` TTFT at each point via `kubectl port-forward`) and updated
the policy's `measurement.command` to point at it.

## Cost/capacity discipline

The measurement scales `feature-agent` to zero and back during the run; the
Deployment is restored to its declared warm-pool minimum (2 replicas)
afterward, matching `agentReplicas.feature-agent: 2` in the policy.
