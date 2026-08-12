# Evidence — per-request LLM token, latency, and PII safety metrics

- rubric_id: LLM-observability-m-b-o-t-nh-t-c-c-metrics
- execution_timestamp: 2026-08-12T08:34:08+00:00
- source_sha: 6ee3175073333df7ed3ed6737bc6c2ac65e6a0a8
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: coordinator/feature-agent/drift-agent and MCP images from the Phase 2 Artifact Registry digests; model=qwen2.5-0.5b-instruct; data=stream_market_features:last_price with synthetic market_stress rows AAA/BBB; embedding=not-used-by-this-runtime-path
- command: start `kubectl -n agents-sandbox port-forward svc/coordinator 18080:80` and `kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 19090:9090`; POST the nested `feature_request`/`drift_request` payload below to `http://127.0.0.1:18080/v1/run`, then query the listed PromQL expressions at `http://127.0.0.1:19090/api/v1/query`
- expected_result: a real coordinator request reaches both specialists and emits non-zero input/output/total token counts, generation round-trip duration, TTFT, and a PII-safety catch counter for the synthetic email prompt
- actual_result: the live request returned HTTP 200 with a non-empty answer, two citations, and specialists `drift` and `feature`; both model services emitted non-zero input/output/total token counts, generation duration, TTFT, and an `email` PII catch in the same Prometheus capture window
- redaction_status: synthetic email `analyst@example.test` only; response text, credentials, bearer tokens, pod names, IP addresses, and infrastructure labels were omitted from the artifact

## Live request

The request used `X-Request-ID: phase3-live-metrics-961e550808c8`. The request
body was:

```json
{
  "question": "Assess the market signal and explain the result. Contact: analyst@example.test",
  "feature_request": {
    "user_id": "PHASE3_CONTRACT_PROBE",
    "feature_names": ["stream_market_features:last_price"],
    "scope": "financial-distress:read"
  },
  "drift_request": {
    "rows": [
      {"ticker": "AAA", "close_price": 10.0},
      {"ticker": "BBB", "close_price": 20.0}
    ],
    "scenario": {
      "name": "market_stress",
      "seed": 7,
      "start_quarter": 1,
      "affected_fraction": 1.0,
      "feature_shifts": {
        "close_price": {"mode": "multiplicative", "magnitude": 0.5}
      },
      "target_metric": "close_price",
      "observed_stat": "mean",
      "expected_direction": "increase",
      "threshold": 0.1
    },
    "scope": "financial-distress:drift"
  }
}
```

```text
request={"answer_present":true,"citation_count":2,"elapsed_seconds":3.13,"error":null,"request_id":"phase3-live-metrics-961e550808c8","specialists":["drift","feature"],"status":200}
```

## Prometheus output

The following are the aggregate results returned by the live Prometheus API.
The `increase(...[5m])` values are the scrape-window values, so Prometheus
extrapolates them between scrapes; the important contract property is that all
three token directions and both timing families are emitted for both model
services.

```text
query=sum by (service, model, direction) (increase(fd_llm_tokens_total[5m]))
[
  {"metric":{"direction":"input","model":"qwen2.5-0.5b-instruct","service":"feature-agent"},"value":[1786523648.014,"53.68421052631579"]},
  {"metric":{"direction":"output","model":"qwen2.5-0.5b-instruct","service":"feature-agent"},"value":[1786523648.014,"84.21052631578947"]},
  {"metric":{"direction":"total","model":"qwen2.5-0.5b-instruct","service":"feature-agent"},"value":[1786523648.014,"137.89473684210526"]},
  {"metric":{"direction":"input","model":"qwen2.5-0.5b-instruct","service":"drift-agent"},"value":[1786523648.014,"242.1052631578947"]},
  {"metric":{"direction":"output","model":"qwen2.5-0.5b-instruct","service":"drift-agent"},"value":[1786523648.014,"101.05263157894737"]},
  {"metric":{"direction":"total","model":"qwen2.5-0.5b-instruct","service":"drift-agent"},"value":[1786523648.014,"343.1578947368421"]}
]

query=sum by (service, model) (increase(fd_llm_generation_round_trip_seconds_sum[5m]))
[
  {"metric":{"model":"qwen2.5-0.5b-instruct","service":"feature-agent"},"value":[1786523648.129,"2.64551986210551"]},
  {"metric":{"model":"qwen2.5-0.5b-instruct","service":"drift-agent"},"value":[1786523648.129,"2.9747105957894266"]}
]

query=sum by (service, model) (increase(fd_llm_generation_round_trip_seconds_count[5m]))
[
  {"metric":{"model":"qwen2.5-0.5b-instruct","service":"feature-agent"},"value":[1786523648.245,"1.0526315789473684"]},
  {"metric":{"model":"qwen2.5-0.5b-instruct","service":"drift-agent"},"value":[1786523648.245,"1.0526315789473684"]}
]

query=sum by (service, model) (increase(fd_llm_ttft_seconds_sum[5m]))
[
  {"metric":{"model":"qwen2.5-0.5b-instruct","service":"feature-agent"},"value":[1786523648.362,"0.0694757999999159"]},
  {"metric":{"model":"qwen2.5-0.5b-instruct","service":"drift-agent"},"value":[1786523648.362,"0.05453043157869711"]}
]

query=sum by (service, model) (increase(fd_llm_ttft_seconds_count[5m]))
[
  {"metric":{"model":"qwen2.5-0.5b-instruct","service":"feature-agent"},"value":[1786523648.479,"1.0526315789473684"]},
  {"metric":{"model":"qwen2.5-0.5b-instruct","service":"drift-agent"},"value":[1786523648.479,"1.0526315789473684"]}
]

query=sum by (service, finding_type) (increase(fd_llm_pii_safety_catches_total[5m]))
[
  {"metric":{"finding_type":"email","service":"feature-agent"},"value":[1786523648.594,"1.0526315789473684"]},
  {"metric":{"finding_type":"email","service":"drift-agent"},"value":[1786523648.594,"1.0526315789473684"]}
]
```

The recording rule `phase2:llm_safety_pii_prompt_catches_total:rate5m` was also
present for both model services; the raw counter increase above is retained as
the primary proof because it is the directly queried per-request family.
