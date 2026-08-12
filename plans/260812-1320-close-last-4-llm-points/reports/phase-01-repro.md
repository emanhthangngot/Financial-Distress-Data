# Phase 1 Reproduction Report — Drift MCP Loopback

## Result

Status: **environmental hypothesis; local reproduction did not reproduce the
cluster hang**.

The exact drift-MCP application topology succeeded both under bare uvicorn and
under the built image with the recorded Kubernetes CPU and memory limits. Both
runs emitted an access-log line for the self-call. The previous cluster window
record remains the contrary observation: the MCP call timed out after 5 seconds
and no `/v1/drift/report` access-log line appeared.

This is a go decision for phase 2: continue with the in-process client fix. A
service must not HTTP-call its own pure function, even though the local
reproduction did not hang.

## Recorded cluster configuration

Captured from the current `phase2-data/drift-mcp` Deployment and the checked-out
GitOps values file on 2026-08-12:

```text
DRIFT_API_BASE_URL=http://127.0.0.1:8000
MCP_AUTH_GRANTS={"drift-agent":["financial-distress:drift"]}
containerPort=8000
requests.cpu=25m
requests.memory=96Mi
limits.cpu=500m
limits.memory=512Mi
image=asia-southeast1-docker.pkg.dev/project-60655616-d84a-4883-867/fsds-images/drift-mcp@sha256:e8fe83deb8554ebcbb83617750025a367ea8e19f27e24a7d1c5d8706b0d2c7c9
serviceMonitor.enabled=true
serviceMonitor.interval=15s
```

The current cluster has no running drift-MCP pod: the namespace-wide pod list
shows workloads `Pending`, and `kubectl -n phase2-data get pods -l app=drift-mcp`
returns `No resources found`. Therefore no new live access-log sample was
possible in this phase. The missing access-log/5-second-timeout observation is
carried forward from `plans/260811-1627-close-llm-rubric-to-100/reports/phase-04-window-log.md`.

## Bare uvicorn run

Command:

```bash
env PYTHONPATH=. \
  DRIFT_API_BASE_URL=http://127.0.0.1:8000 \
  MCP_AUTH_GRANTS='{"drift-agent":["financial-distress:drift"]}' \
  .venv-phase2/bin/python -m uvicorn app.main:app \
  --app-dir apps/drift-mcp --host 0.0.0.0 --port 8000
```

Direct route checks:

```text
/healthz 200 {"status":"ok"}
/v1/drift/report 200
```

The separate MCP client process called `build_realtime_drift_report` with the
valid `drift-agent` / `financial-distress:drift` grant and the two-row
`market_stress` scenario.

```text
elapsed_seconds=0.058
structured_content.ok=True
structured_content.data.report.passed=True
structured_content.data.affected_tickers=["AAA", "BBB"]
```

The uvicorn log contained both the MCP request and the self-call:

```text
POST /mcp/ HTTP/1.1 200 OK
POST /v1/drift/report HTTP/1.1 200 OK
POST /mcp/ HTTP/1.1 200 OK
```

## Container-parity run

The existing `drift-mcp:rebuild-otel` image was run with the recorded resource
limits:

```bash
docker run --rm --cpus 0.5 --memory 512m \
  -e DRIFT_API_BASE_URL=http://127.0.0.1:8000 \
  -e MCP_AUTH_GRANTS='{"drift-agent":["financial-distress:drift"]}' \
  -p 8001:8000 \
  asia-southeast1-docker.pkg.dev/project-60655616-d84a-4883-867/fsds-images/drift-mcp:rebuild-otel
```

The same separate-process MCP probe returned:

```text
elapsed_seconds=0.067
structured_content.ok=True
structured_content.data.report.passed=True
structured_content.data.affected_tickers=["AAA", "BBB"]
```

The container log also contained the self-call access line:

```text
POST /mcp/ HTTP/1.1 200 OK
POST /v1/drift/report HTTP/1.1 200 OK
```

This rules out a deterministic pure-async deadlock and the recorded CPU limit
as sufficient causes in the local image environment.

## Feature-MCP comparison

The existing `feature-mcp:rebuild-otel` image was run with the same resource
limits and a loopback `FEATURE_API_BASE_URL`. A valid
`lookup_feature_context` request completed in 0.058s and returned
`{"ok":false,"error":"api_error"}` because no local Feast/Postgres
dependency was configured. Its access log showed the loopback business route:

```text
POST /v1/features/by-id HTTP/1.1 503 Service Unavailable
```

It did not hang. This comparison confirms the MCP transport and loopback shape
can complete under the local container conditions.

## Named cluster-side hypothesis and confirmation command

The remaining hypothesis is Kubernetes-runtime-specific handling of the
loopback connection (CNI/network policy or pod-level socket/listen behavior),
possibly amplified by the live node's resource pressure. The current evidence
does not distinguish those causes because the cluster has no running pod.

When the pod is running, execute this exact in-pod check before the phase-3
round-trip:

```bash
kubectl -n phase2-data exec deploy/drift-mcp -- \
  python -c 'import json,urllib.request; body=json.dumps({"rows":[{"ticker":"AAA","close_price":10.0}],"scenario":{"name":"market_stress","seed":7,"start_quarter":1,"affected_fraction":1.0,"feature_shifts":{"close_price":{"mode":"multiplicative","magnitude":0.5}},"target_metric":"close_price","observed_stat":"mean","expected_direction":"increase","threshold":0.1}}).encode(); print(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8000/v1/drift/report", data=body, headers={"content-type":"application/json"}), timeout=2).status, flush=True)'
```

Capture the command output together with the pod log. A timeout/connection
error without a corresponding `/v1/drift/report` access line confirms the
cluster loopback hypothesis; a `200` shifts the diagnosis to the MCP request
path or transient node pressure. Regardless, phase 2 removes this fragile hop.

## Scope check

No file under `src/` or `apps/` was modified by phase 1. Only this report was
created.
