# Operator Runbook

Use this guide for local lakehouse setup, platform configuration, source checks,
and the external deployment handoff. Coursework captures document their recorded
runs; they are not instructions to recreate a live deployment.

## Table of Contents

1. [Naming Convention](#naming-convention)
2. [Historical Lakehouse Evidence](#historical-lakehouse-evidence)
3. [Schema Evidence](#schema-evidence)
4. [API Surface](#api-surface)
5. [Local Setup](#local-setup)
6. [Running in Docker](#running-in-docker)
7. [Phase 2 Runtime Setup](#phase-2-runtime-setup)
8. [External Deployment Handoff](#external-deployment-handoff)
9. [Historical Phase 2 Evidence](#historical-phase-2-evidence)
10. [Service URLs](#service-urls)
11. [Run Lakehouse Evidence](#run-lakehouse-evidence)
12. [Validation Commands](#validation-commands)
13. [Useful Inspection Queries](#useful-inspection-queries)
14. [Stop Services](#stop-services)

## Naming Convention

Use the [naming rules](../AGENTS.md#naming-convention-graded--mini-rubric-row-43-both-clauses)
and [naming lint](../scripts/lint_naming_convention.py) for the repository-wide
convention. Inspect the [storage path builder](../src/io/paths.py) for `raw_`
Bronze feeds and `stg_` Silver feeds, and the [DuckDB view definitions](../sql/duckdb_create_views.sql)
for the `gold_` view names over `dim_`, `fact_`, `obt_`, and `feat_` paths.
`distress_labels` is an input alias in the path builder; the current Gold path
is `fact_distress_label`, not `distress_labels`.

## Historical Lakehouse Evidence

The [checked-in audit summary](evidence/lakehouse_runtime_audit_summary.json)
reports the recorded local E2E run. See the [evidence index](evidence/README.md)
for the Airflow, Kafka, MinIO, PostgreSQL, DuckDB, and DQ records. These files do
not report the health of a running local stack.

## Schema Evidence

The local schema follows a Medallion design: raw Bronze-style tables, Silver
staging tables, Gold dimensions/facts, distress labels, OBT, and feature tables.

![Schema evidence ERD](../images/schema/schema_evidence_erd.png)

DBeaver evidence can be reproduced by connecting to a local DuckDB file named
`warehouse.db` and opening the `schema_evidence` schema. `warehouse.db` is a
local generated artifact and is intentionally ignored by Git; regenerate it from
the local pipeline when needed. See `docs/submission/rubric-(mini-coursework)/schema_design.md`
for the narrative naming/SCD2/feature-contract proof.

## API Surface

The local lakehouse is a data pipeline, not a REST service. For the additive
platform, use the [web workspace](../apps/web/README.md), [feature MCP](../apps/feature-mcp/),
and [drift MCP](../apps/drift-mcp/) entrypoints.

## Local Setup

Create and activate the repository-local Python environment, then use
[requirements.txt](../requirements.txt) and the [package extras](../pyproject.toml)
for dependencies.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e ".[dev,runtime]"
```

Create local environment config.

```bash
cp .env.example .env
```

Continue with [Docker Compose](#running-in-docker).

## Running in Docker

Start the local data platform from [Docker Compose](../docker-compose.yml).
No provider account is needed; Flink stays disabled by default.

```bash
docker compose up -d
```

Check service status.

```bash
docker compose ps
.venv/bin/python scripts/check_lakehouse_services.py
```

Opt in to Apache Flink (jobmanager + taskmanager, profile `flink`):

```bash
ENABLE_FLINK=1 docker compose --profile flink up -d
```

DAG 04 (`dags/dag_04_stream_market_events_to_kafka.py`) automatically dispatches to the Flink REST endpoint when `ENABLE_FLINK=1`; otherwise it keeps the original `MicroBatchConsumer` smoke path so the default stack stays light.

Create Kafka topics manually if needed.

```bash
docker compose exec kafka bash /opt/financial-distress-init/kafka_init_topics.sh
```

## Phase 2 Runtime Setup

Use the [web workspace](../apps/web/README.md) for local product setup. The
[platform preflight](../scripts/run_platform_quality_gates.py) needs no external
checkout when run without `--gitops-root`. It is not the full platform suite:
in an environment with the platform dependencies, also run
`python -m pytest tests/platform -q`. Use the web package's checks separately.

Configure only the interfaces each service uses. For HTTP connections, supply
explicit, absolute `http://` or `https://` URLs that the caller can reach.
Loopback is only appropriate when the endpoint is in the caller's network
namespace. Do not infer live addresses from the coursework cluster.
Use HTTPS for live bearer-authenticated endpoints. The application accepts
cleartext bearer transmission only on loopback for local testing. Do not send
sensitive data over unencrypted connections between live services.

| Runtime boundary | Setup and executable owner |
|---|---|
| Product data and assistant | See [Supabase client setup](../apps/web/src/lib/server/supabase.ts), [server-only inference configuration](../apps/web/src/lib/server/inference-config.ts) and the [assistant route](../apps/web/src/app/api/assistant/stream/route.ts) for the coordinator endpoint and token. Use fixture mode only for local development or tests, not live verification. |
| Live agent registry | Enable [live registry reads](../apps/web/src/lib/data/supabase-adapter.ts) with `DISTRESSLENS_LIVE_PLANE=1`. Set `DISTRESSLENS_AGENT_REGISTRY_URL` to the full deployed `/v1/agents` URL, including any routing prefix. For the [bundled server](../src/agents/registry.py), provide the JSON registry at `AGENT_REGISTRY_PATH` (default `/registry/registry.json`). Supply `DISTRESSLENS_SOURCE_SHA` for the deployed source. Supply `DISTRESSLENS_GITOPS_SHA` only if a GitOps configuration commit applies; otherwise leave it unset. Never invent revisions or copy them from coursework receipts. |
| Specialist agents and coordinator | Set `MODEL_BASE_URL` to the OpenAI-compatible base, `FEATURE_MCP_URL` and `DRIFT_MCP_URL` to full MCP endpoints, and `FEATURE_AGENT_URL` and `DRIFT_AGENT_URL` to specialist service bases where each is needed. The [agent runtime](../src/agents/runtime.py) owns the per-role endpoint, token and readiness settings. |
| Feature MCP and stores | Set `FEATURE_API_BASE_URL` for the [MCP client](../apps/feature-mcp/app/mcp_server.py). The deployment owner supplies a pre-applied Feast repository via `FEAST_REPO_PATH`; its selected profile configures the actual online store and is used for readiness and reads. Set `RAG_DATABASE_URL` or explicit Postgres settings as applicable; see the [feature API](../apps/feature-mcp/app/main.py). |
| Drift MCP | Set `DRIFT_API_BASE_URL` to use an HTTP API, including on loopback. Leave it unset only when the local in-process implementation is intended. See the [drift MCP entrypoint](../apps/drift-mcp/app/mcp_server.py) for transport and allowed-host configuration. |

For coordinator chat, configure the full `/v1/run` URL as
`DISTRESSLENS_COORDINATOR_URL` and provide `DISTRESSLENS_COORDINATOR_DRIFT_SCENARIO`
in the format consumed by the [assistant route](../apps/web/src/app/api/assistant/stream/route.ts)
and [drift schema](../apps/drift-mcp/app/main.py). For a path-prefixed MCP route,
configure `FEATURE_MCP_HEALTH_URL` or `DRIFT_MCP_HEALTH_URL` if the default
origin-root `/mcp-readyz` is not the right route. MCP readiness verifies its
configured business API; REST `/readyz` for Feature API checks its stores.

Glossary-only inference requires `DISTRESSLENS_INFERENCE_URL`, a server-side
`DISTRESSLENS_INFERENCE_TOKEN`, and `DISTRESSLENS_INFERENCE_MODEL` set to the
provider's model or deployment ID. The full web URL can carry a date-based
`api-version` query; credentials belong in headers, not URLs. Do not configure
an environment proxy for web loopback bearer traffic. Python bypasses proxies
for plaintext HTTP; HTTPS retains environment TLS trust. Set
connection and command timeouts in external database and Feast profiles.

Set `MCP_ALLOWED_HOSTS` for the hosts used to reach MCP services and
`MCP_AUTH_GRANTS` to allow only the scopes each authenticated tool identity
needs. See the grant readers in [feature MCP](../apps/feature-mcp/app/mcp_server.py)
and [drift MCP](../apps/drift-mcp/app/mcp_server.py) for the configuration.
The receiving service or its edge must authenticate the caller and bind it
to the tool request's `agent_identity`; a client-supplied identity is not
proof of authentication. Deliver outbound bearer tokens via the deployment
secret mechanism; configuring them does not enable inbound authentication.

If a required service is unavailable or unconfigured, do not substitute
fixtures, historical receipts, or assumed health for a live result.
Fixture identities are for local development and tests. Local production-mode
tests must explicitly opt in through their Playwright configuration; the
published release image rejects fixture identities.

For coordinator and specialist roles, override the shared MCP image command
with `uvicorn src.agents.runtime:app --host 0.0.0.0 --port 8000` and set
`AGENT_ROLE` (`coordinator`, `feature`, or `drift`). The MCP applications keep
their [feature MCP](../apps/feature-mcp/Dockerfile) or [drift MCP](../apps/drift-mcp/Dockerfile)
image defaults.

### Optional Live Supabase Browser Check

Run the web manifest's `e2e:live` only against an explicitly approved,
disposable Supabase test project. The [Playwright configuration](../apps/web/playwright.live.config.ts)
uses a local web build against the configured Supabase project, not a deployed
URL. The [smoke suite](../apps/web/e2e/live-smoke.spec.ts) and
[auth lifecycle suite](../apps/web/e2e/auth-lifecycle.spec.ts) use service-role
access to create or update users and roles and delete test accounts. Do not
run it unattended or against production; it is not a deployment readiness check.

Use an unused `DISTRESSLENS_LIVE_E2E_PORT`; do not reuse a pre-existing server.
Confirm the local build and [test environment loader](../apps/web/e2e/live-env.ts)
target the same disposable project. Verify the [migrations](../supabase/migrations/)
and the [demo-account setup](../apps/web/scripts/seed-demo-accounts.ts) before running.

## External Deployment Handoff

Source CI verifies pull requests without publishing images. The [reusable
workflow](../.github/workflows/phase2-ci.yaml) owns the signed immutable image
handoff; the [source verification workflow](../.github/workflows/ci.yml) owns
the source gates. Source CI must not authenticate to a deployment provider,
provision infrastructure, promote a workload, or change an external
deployment repository.

The external deployment owner chooses a runtime only after checking:

- **Capabilities:** the target can pull and verify the signed image digest,
  provide the [configured service interfaces](#phase-2-runtime-setup), isolate
  workloads, and supply secrets and telemetry without exposing private services.
- **Data residency and access:** the chosen locations and access policies cover
  application data, replicas, backups, logs, and cross-boundary traffic.
  Deploying code is not approval to copy or move data.
- **Cost:** the approved ceiling covers compute, storage and egress, including
  idle resources and teardown.
- **Readiness:** verify the target identity and deployed image digest, then
  check the readiness handlers for the configured [agents](../src/agents/runtime.py),
  [registry](../src/agents/registry.py), and [feature API](../apps/feature-mcp/app/main.py),
  as applicable. A liveness response or the [web plane flag](../apps/web/src/lib/server/session.ts)
  is not proof of dependency readiness. Before accepting the release, verify
  an authenticated response with the expected value and provenance, an
  authorized request that degrades when a dependency is unavailable, and a
  separately denied request. Check SSE response states, not only HTTP status.
- **Rollback:** before promotion, record the previous known-good digest and
  compatible configuration, data recovery limits, and an owner-approved
  rollback procedure and trigger.

Use the external owner's approved release procedure and restricted secret
store. This repository does not select a target, grant access, or authorize
a rollout or data move.

## Historical Phase 2 Evidence

The [coursework verification snapshot](platform/architecture.md#6-verification-and-residuals)
records the GKE checks and their limitations. The [coursework CI/CD narrative](<submission/rubric-final-coursework-(final-llm)/ci_cd.md>)
links the pinned workflow that opened GitOps PRs for that submission. The
[Kubernetes smoke runner](../scripts/run_platform_e2e.py) targets that topology;
it is not a generic deployment readiness check.

To audit that submission, use the matching clean source and GitOps checkouts
with the dependencies for that revision installed. The
[evidence contract](platform/evidence-contract.md) owns the revision rules.
For a matching revision with the [current audit CLI](../scripts/audit_platform_evidence.py),
set `GITOPS_CHECKOUT` to the matching local checkout and run:

```bash
python scripts/audit_platform_evidence.py \
  --strict --require-executed --run-validations --track LLM --ml 100 --llm 100 \
  --platform-base ddbcbe7bd41ae4883954b8a247efdc67c7329078 \
  --gitops-root "${GITOPS_CHECKOUT:?Set GITOPS_CHECKOUT to the matching local checkout}"
```

Use the matching revision's registered CLI if its names differ. This is a
coursework audit, not a source-only gate or a live trust check. Do not restamp
historical receipts to make a current checkout pass it.

## Service URLs

| Service | URL / Connection | Notes |
|---|---|---|
| Airflow | `http://localhost:8085` | Default host port; override with `AIRFLOW_HOST_PORT` |
| MinIO Console | `http://localhost:9001` | Credentials come from local environment configuration |
| MinIO API | `http://localhost:9000` | Bucket: `financial-distress-lake` |
| PostgreSQL | `localhost:5432` | Default host port; override with `POSTGRES_HOST_PORT` |
| Kafka host listener | `localhost:9094` | Host-side access |
| Kafka Docker listener | `kafka:9092` | Container-side access |
| Flink jobmanager (opt-in) | `http://localhost:8081` | Start with `docker compose --profile flink up -d`; gated by `ENABLE_FLINK=1` |

## Run Lakehouse Evidence

Run the [fixture-backed evidence pipeline](../scripts/run_lakehouse_evidence.py)
from the host. Write new captures to a scratch directory, not the historical bundle.

```bash
.venv/bin/python scripts/run_lakehouse_evidence.py --evidence-dir /tmp/lakehouse-evidence
```

Run the connected local E2E path through Airflow, Kafka, Spark, MinIO,
PostgreSQL, and DuckDB.

```bash
.venv/bin/python scripts/run_lakehouse_real_e2e.py \
  --execution-date 2026-06-06T10:04:00+00:00 \
  --export-evidence /tmp/lakehouse-e2e
```

Generate a machine-readable audit summary for the E2E artifacts.

```bash
.venv/bin/python scripts/audit_lakehouse_evidence.py /tmp/lakehouse-e2e
```

Validate the checked-in submission evidence without regenerating files.

```bash
.venv/bin/python scripts/audit_lakehouse_evidence.py docs/evidence --check
```

Build a reviewer-facing readiness report from the checked-in evidence.

```bash
.venv/bin/python scripts/lakehouse_readiness_report.py
.venv/bin/python scripts/lakehouse_readiness_report.py --json --output /tmp/lakehouse-readiness-report.json
```

Prove critical DQ failures are persisted before the pipeline halts.

```bash
.venv/bin/python scripts/run_lakehouse_dq_failure_probe.py \
  --run-id lakehouse-dq-failure-probe \
  --export-evidence /tmp/lakehouse-dq-failure-probe
```

For a no-service payload check:

```bash
.venv/bin/python scripts/run_lakehouse_evidence.py --dry-run --evidence-dir /tmp/lakehouse-evidence
```

Run the primary Airflow evidence DAG once from the CLI.

```bash
docker compose exec airflow-scheduler airflow dags test lakehouse_local_evidence_pipeline 2026-06-06T02:00:00+00:00
```

Runtime evidence artifacts are written to MinIO:

```txt
financial-distress-lake/evidence/lakehouse/run_id=.../
```

See the [fixture evidence runner](../scripts/run_lakehouse_evidence.py) and
[connected E2E runner](../scripts/run_lakehouse_real_e2e.py) for their exported
artifacts.

## Validation Commands

Run local quality gates.

```bash
.venv/bin/python scripts/run_lakehouse_quality_gates.py
```

Run quality gates plus Docker service readiness after the stack is up.

```bash
.venv/bin/python scripts/run_lakehouse_quality_gates.py --include-services
```

Build a readiness report plus live service checks after the stack is up.

```bash
.venv/bin/python scripts/lakehouse_readiness_report.py --include-services
.venv/bin/python scripts/lakehouse_readiness_report.py --include-services --include-quality-gates
```

The [gate runner](../scripts/run_lakehouse_quality_gates.py) owns the check list,
including naming, rubric coverage, target architecture, and the evidence audit.
Use `--only` with a registered gate to narrow a local check.

While iterating, `.venv/bin/python -m pytest tests -m "not slow"` runs the fast
loop — no Docker stack, no Postgres binaries. Markers select tests; they never
skip, so `pytest tests` with no `-m` stays the definition of done.

List Kafka topics.

```bash
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --list
```

List Airflow DAGs.

```bash
docker compose exec airflow-scheduler airflow dags list
```

Inspect MinIO objects from inside the container.

```bash
docker compose exec minio sh -c 'ls -R /data/financial-distress-lake | head -120'
```

## Useful Inspection Queries

PostgreSQL metadata checks:

```bash
docker compose exec postgres psql -U airflow -d financial_distress -c \
"select dataset_name, status, count(*) from ops.pipeline_run_log group by dataset_name, status order by dataset_name, status;"
```

```bash
docker compose exec postgres psql -U airflow -d financial_distress -c \
"select dataset_name, check_name, status, severity, count(*) from ops.data_quality_result group by dataset_name, check_name, status, severity order by dataset_name, check_name;"
```

```bash
docker compose exec postgres psql -U airflow -d financial_distress -c \
"select dataset_name, status, freshness_lag_minutes, sla_minutes from ops.dataset_freshness;"
```

```bash
docker compose exec postgres psql -U airflow -d financial_distress -c \
"select dataset_name, start_date, end_date, status, requested_by from ops.backfill_request order by created_ts desc limit 20;"
```

See the [checked-in DuckDB validation output](evidence/lakehouse_duckdb_validation.json)
for the recorded local evidence.

## Stop Services

Stop containers but keep volumes/data.

```bash
docker compose stop
```

Stop and remove containers/network.

```bash
docker compose down
```
