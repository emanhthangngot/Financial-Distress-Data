# Locust Web API SLA

- Host: `https://distresslens.duckdns.org` (F5 NGINX Ingress, basic-auth
  protected), target `POST /v1/features/by-id` on `feature-mcp`
- Requests: 1352
- Failures: 0
- Failure rate: 0.00%
- Throughput: 15.06 req/s
- p95 latency: 140.00 ms
- SLA: failure rate 0%, p95 < 500 ms, throughput >= 10 req/s
- Result: PASS
- Command: `locust -f tests/load/locustfile.py --headless --users 20 --spawn-rate 5 --run-time 90s --host https://distresslens.duckdns.org --html docs/platform/evidence/llm/locust-report.html --csv docs/platform/evidence/llm/locust`
- Captured: 2026-08-10T23:19:36+07:00 (live gateway run; not re-run today —
  requires the connected cluster's public gateway, which this session did not
  bring up)
- Screenshot: [`screenshots/locust-sla-report.jpg`](screenshots/locust-sla-report.jpg)
  — real capture of the tool-generated
  [`../locust-report.html`](../locust-report.html), opened in Chrome and
  photographed via `mcp__claude-in-chrome`, not a rendering built for this
  document.
