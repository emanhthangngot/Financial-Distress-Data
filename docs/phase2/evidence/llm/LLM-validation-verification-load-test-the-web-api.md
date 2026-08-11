# Evidence — Load test the Web API (Locust)

Proves `tests/load/locustfile.py` runs against the feature Web API through
the real public gateway (`https://distresslens.duckdns.org`, F5 NGINX
Ingress Controller, basic-auth-protected), producing an HTML SLA report with
p95 latency, throughput, error rate and concurrency.

- rubric_id: LLM-validation-verification-load-test-the-web-api
- execution_timestamp: 2026-08-10T23:19:36+07:00
- source_sha: 6dc70ba62f2a664aaeba484a34c23604246e0017
- gitops_sha: 921bdc1075ef8335e0f509747bd64db2d525f73e
- versions: locust 2.46.3, nginx/nginx-ingress:5.5.4, feature-mcp@sha256:6bfb99fc834bf9a2cac78b9c59c5de259f9738cd9c61dcfe626e2da6e6cfd510
- command: `locust -f tests/load/locustfile.py --headless --users 20 --spawn-rate 5 --run-time 90s --host https://distresslens.duckdns.org --html docs/phase2/evidence/llm/locust-report.html --csv docs/phase2/evidence/llm/locust`
- expected_result: HTML report with p95 latency, throughput (req/s), error rate and concurrency, generated from real requests through the gateway to the live `feature-mcp` service
- actual_result: 1352 requests, 0 failures, median 51ms, p95 140ms, p99 330ms, max 490ms, throughput 15.06 req/s at 20 concurrent users; report at `docs/phase2/evidence/llm/locust-report.html`, raw stats at `docs/phase2/evidence/llm/locust_stats.csv`
- redaction_status: reviewed — gateway basic-auth password generated for this run only, not committed; request payload is synthetic (`user_id: VNM`, a real seeded ticker in the online store)

## Command output (real run)

```
Type     Name                            # reqs      # fails |    Avg     Min     Max    Med |   req/s  failures/s
--------|--------------------------------|-------|-------------|-------|-------|-------|-------|--------|-----------
POST     POST /v1/features/by-id           1352     0(0.00%) |     63      42     487     51 |   15.06        0.00

Response time percentiles (approximated)
Type     Name                                   50%    66%    75%    80%    90%    95%    98%    99%  99.9% 99.99%   100% # reqs
--------|---------------------------------------|-----|------|------|------|------|------|------|------|------|------|------
POST     POST /v1/features/by-id                 51     55     58     60     66    140    260    330    450    490    490   1352
```

## Real bugs found and fixed to get a live run

1. Gateway route (`platform/ingress/routes-ui.yaml`) pointed at
   `/api/features/by-id`; `feature-mcp` actually exposes
   `POST /v1/features/by-id`. Every request 404'd until the route was fixed.
2. `locustfile.py` used `catch_response=True` without a `with`-block; Locust
   2.46.3 raises `LocustError` when `.success()`/`.failure()` is called on a
   request made outside a `with`-block, silently dropping every request from
   stats (0 reqs recorded despite real 200 responses upstream). Fixed to use
   `with self.client.post(...) as response: ...`.
3. Test payload requested `company_features:risk_score`, a feature view that
   does not exist in the `fd_structured` Feast project; the registered view
   is `company_risk_features` with a `z_score` field. Fixed the payload.
4. An orphaned `hello-web` Ingress (namespace `default`, no `mergeable-ingress-type`
   annotation, not tracked in git) claimed the gateway host outright,
   returning its own debug page for every request and blocking the F5
   `master`/`minion` Ingress set from being accepted at all
   (`NoIngressMasterFound` / `All hosts are taken by other resources`).
   Deleted; it predates the gateway work and had no owner.
5. `gateway-basic-auth` and the `distresslens-duckdns-tls` `Certificate`
   were referenced but never created — `platform/ingress/basic-auth-sealed-secret.yaml`
   is a template with `REPLACE_WITH_KUBESEAL_OUTPUT` markers. Created a real
   `gateway-basic-auth` Secret directly in-cluster for this evidence run and
   applied the existing (previously un-applied) `duckdns-certificate.yaml`,
   which cert-manager issued via the HTTP-01 solver in under two minutes.
