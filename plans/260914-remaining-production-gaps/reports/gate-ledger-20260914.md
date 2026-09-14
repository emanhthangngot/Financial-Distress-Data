# Remaining Production Gaps — Gate Ledger

**Captured:** 2026-09-15T04:02:03+07:00
**Phase:** Gap 01 — Reconfirm gates and inventory
**Source revision:** `ffe7c91` (last source change; all subsequent commits contain ledger-only documentation edits; unrelated user changes preserved)
**Evidence baseline:** `evidence-baseline-pre-rebuild` resolves locally

## Status

| Gate | Status | Evidence | Owner / next action |
|---|---|---|---|
| Baseline tag | PASS | `git tag -l evidence-baseline-pre-rebuild` resolved | Evidence owner: retain tag and existing evidence |
| Billing/spend controls | BLOCKED | Billing enabled for `project-60655616-d84a-4883-867`, currency VND, user holds `roles/billing.admin`. Cloud Billing report for the last 90 days shows net subtotal/total `₫0` after savings with gross usage about `₫6,089,726`. A monthly budget `fsds-evidence-guardrail` now exists (`last-period` amount, alert thresholds 50/90/100%), but an alert is not a hard cap and no approved window, teardown deadline, residual credit or backup/export destination is recorded | Operator: record the approved window, teardown deadline and backup/export destination; decide whether a fixed ceiling replaces the last-period amount |
| Project-wide CPU capacity | BLOCKED | `CPUS_ALL_REGIONS=12`, usage `9`; `GPUS_ALL_REGIONS=0`, usage `0`; forwarding-rule usage includes external network LBs | Platform owner: obtain approved quota/no-spend window before capacity-backed phases |
| Regional CPU capacity | BLOCKED | `asia-southeast1`: `CPUS=32`, usage `8` after stopping the evidence VM; `E2_CPUS=8`, usage `0`; `PREEMPTIBLE_CPUS=0`, usage `0`; `INSTANCES=8`, usage `2` | Platform owner: obtain approved quota/no-spend window before capacity-backed phases |
| Kubernetes capacity | BLOCKED | One Ready `e2-standard-8` node remains running; `fsds-evidence-worker` is now `TERMINATED`, with its 30-GB persistent disk `READY` and still attached; node remains billable and violates the documented between-session hibernation invariant | Platform owner: record authorization/window and teardown deadline; hibernate the node pool in a controlled operator action if no approved window exists |
| External load balancers | PASS | GitOps commit `ae79945` set `kourier-system/kourier` to `ClusterIP`; Argo synced revision `ae79945` and the live Service type is `ClusterIP`. Cluster now reports exactly one external `LoadBalancer` (`ingress-nginx` at `34.21.242.110`) and exactly one external forwarding rule | Platform owner: keep NGINX as the sole external entry point |
| Jenkins host/controller | UNVERIFIED | `fsds-evidence-worker` is `TERMINATED` and one GKE node remains Ready; no Jenkins health/controller inspection was performed; no root `Jenkinsfile` exists | Platform owner: identify or provision the approved controller, JCasC, backup and ephemeral-agent proof |
| Provider access/limits | UNVERIFIED | No fresh Groq/Gemini/provider capability or quota check was performed | ML/agent owner: measure allowed free providers before pinning or evaluating models |
| LangGraph runtime | UNVERIFIED | No current `src/agents/langgraph_runtime.py` or declaration in `requirements.txt`, `requirements-platform.txt`, `pyproject.toml` or `uv.lock`. `.venv-platform` has undeclared `langgraph 0.6.11`, `langgraph_checkpoint 3.0.1` and `langchain_core 1.6.2`; an ignored CPython bytecode file references a prior uncommitted pilot source path. `git log --all --diff-filter=D -- src/agents/langgraph_runtime.py` is empty and the preserved stash contains no LangGraph files | ML/agent owner: pin the dependency and recover or reimplement the runtime in Phase 04 from an attributable source revision, then measure parity before cutover |
| Domain/HTTPS | UNVERIFIED | No fresh domain certificate/edge exercise was run in this local gate refresh | Serving owner: capture trusted HTTPS and auth/rate-limit evidence |
| Kaggle/GPU capacity | UNVERIFIED | No Kaggle job or GPU capacity exercise was run in this refresh | ML owner: run only after access and spend controls are verified |

## Current runtime evidence

- The first bounded producer Job `lakehouse-gold-producer-live-1789416417` exposed a nullable-timestamp defect and is not used as clean evidence. After preserving `None` in the Parquet timestamp writer, the final Job `lakehouse-gold-producer-live-1789416418` completed successfully on the existing GKE node using the checked-in **cluster fixture profile** (`generator.enabled=true`, seed `42`, stressed ticker `NVL`) with `gold_rows=843`, `risk_rows=16`, `risk_tickers=[HPG,NVL]`; Feast `company_risk_features` materialization for `NVL` completed with registry revision `8da8a16e6d4fbbf9`. This is bounded generated-fixture proof, not live-source proof.
- Feature MCP direct read for `NVL` returned non-null materialized values: `current_ratio=0.4`, `debt_to_asset=0.9`, `roa=-0.03`, `z_score=-1.3011`, `distress_label=1`, `training_eligible=true`, with the generated distress reason retained.
- `.venv-platform/bin/python scripts/run_platform_e2e.py --timeout 30 --json` returned `status=PASS`: all required workloads/services, model warm-up through AgentGateway, coordinator round-trip, five Prometheus application targets, and five Jaeger services passed. The runner now leaves a hibernated model revision available through the coordinator round-trip and restores it on warm-up failure, normal follow-up completion, or SIGINT/SIGTERM.
- Prometheus target API independently reported `up=1` for `coordinator`, `feature-agent`, `drift-agent`, `feature-mcp`, and `drift-mcp` after the monitoring namespace NetworkPolicy correction.
- The producer CronJob is suspended after the bounded run; the temporary source-override ConfigMap was deleted. No PersistentVolume/PersistentDisk or cloud data was deleted.
- Local source fixes are committed as `45db6f1`, `4bd9474`, `0b7c025`, `b5096f7`, `f29e18d`, `5dd81b2`, and `ffe7c91`. GitOps producer promotion `55611f1`, producer suspension `34030fb`, timestamp-safe image promotion `94b1d5d`, and nullable-timestamp image promotion `d6d7c59` are pushed over SSH. The final Artifact Registry digest is `sha256:0460ccf3ee0257f5e9de5b18f6242add8de6a6f342c18f5a24d6bbe454fb5c55`; the final bounded Job ran with that digest and no source override against the checked-in generated-fixture profile, not an external live-source adapter.
- Argo `platform-data` is now `Synced/Healthy` at GitOps revision `b6d1448`; the active-key resealed `dataflow-credentials` is managed by SealedSecrets, and the idempotent schema migration Job completed successfully after its credentials were aligned to the Secret's database/user keys.
- Current Argo reconciliation is mixed: `platform-data` is `Synced/Healthy` at `b6d1448`, `platform-agents` is `Synced/Healthy`, `platform-security` is `Synced/Degraded` with no non-Synced resource listed and a stale health transition (`2026-09-12T03:13:23Z`), `platform-observability` is `OutOfSync/Degraded` waiting for healthy `Certificate/distresslens-duckdns-tls`, and `platform-llm` is `OutOfSync/Healthy` because Knative rejects an in-place `fd.dev/experiment` label change without a revision-name change. These are external platform blockers, not reasons to start unbounded local rebuild work.
- The earlier bounded producer Job `lakehouse-gold-producer-live-1789416417` completed successfully on the existing GKE node, but its artifacts were superseded because the writer converted nullable timestamps to the Unix epoch; its fixed-key MinIO objects were overwritten by the final run and are not retained as evidence.

## Inventory reconciliation

- Baseline tag still resolves; no evidence tree was deleted.
- Existing prior gate evidence remains historical and is not relabeled as current proof.
- Cleanup result: `fsds-evidence-worker` is `TERMINATED`; its persistent disk remains `READY` and attached.
- Durable Kourier cutover: the earlier direct Service deletion was reverted by Argo self-heal, so the desired state in `financial-distress-gitops` was changed to `ClusterIP` instead; Argo reconciled and the external rule was released.
- Current cluster has one Ready `e2-standard-8` node and a single external entry point `34.21.242.110`; `kourier-internal` remains `ClusterIP` for in-cluster Knative routing.
- Baseline/current evidence diff: `git diff --stat evidence-baseline-pre-rebuild..HEAD -- docs/platform/evidence` reports two modified files and no additions or deletions. Both changes update the retired `PHASE2_PG_DSN` name to `PLATFORM_PG_DSN`; no executed evidence artifact was removed.
- Unified rubric reconciliation from `docs/rubric-matrix-unified.csv`: 161 rows / 300 points = 60 LLM rows executed (100 points), 57 ML rows design-only (100 points), and 44 mini rows pending (100 points). All 60 executed rows have existing evidence files. The 57 missing ML evidence files are explicitly `design_only`, not stale executed artifacts.
- Mini recapture schedule — P2 owner, 7 rows / 17 points: `mini-26-data-storage-how-to-optimize-your-data-storage-dat`; `mini-39-documentation-schema-design-visualize-tables-on-al`; `mini-40-documentation-schema-design-dim-table-with-scd-2`; `mini-41-documentation-schema-design-feature-tables-feat_-t`; `mini-42-documentation-schema-design-relationship-between-d`; `mini-43-documentation-schema-design-naming-convention`; `mini-44-novel-ideas-idea-1-idea-1`.
- Mini recapture schedule — P4 owner, 26 rows / 59 points: `mini-04` through `mini-19` generator/processing rows; `mini-25`; `mini-27` through `mini-30`; `mini-33` through `mini-36`; `mini-45`. Exact row IDs and evidence paths remain in `docs/rubric-matrix-unified.csv`; all are `pending` and require fresh evidence, not stale-artifact replacement.
- Mini recapture schedule — P5 owner, 9 rows / 21 points: `mini-20` through `mini-24`; `mini-31`; `mini-32`; `mini-37`; `mini-38`. Exact row IDs and evidence paths remain in `docs/rubric-matrix-unified.csv`; all are `pending`.
- Mini recapture schedule — P11 owner, 2 rows / 3 points: `mini-02`; `mini-03`. Exact row IDs and evidence paths remain in `docs/rubric-matrix-unified.csv`; all are `pending`.
- The 44 mini rows are now explicitly scheduled by owning phase; they are not silently treated as missing ML evidence or as stale executed artifacts.
- Stale path mappings, not evidence recaptures: 13 rows reference absent `.github/workflows/platform-ci.yaml`; the active reusable workflow is `.github/workflows/phase2-ci.yaml`. Six executed LLM rows retain their evidence and need a matrix-path correction only; seven ML rows remain design-only and genuinely unbuilt. Four additional ML design-only rows reference absent GitOps `charts/feature-api`/`charts/drift-api`; the current chart inventory is `fastapi-service`, `feature-mcp`, `drift-mcp` and `web`. Those four rows need path reconciliation, while the underlying ML API deliverables remain unbuilt.
- Row-level stale/path inventory: executed rows requiring matrix-path correction = `LLM-ci-cd-agent-drift-detection`, `LLM-ci-cd-agent-k-o-d-li-u`, `LLM-ci-cd-agent-l-m-coordinator`, `LLM-ci-cd-ci-cd-cho-rag-data-pipeline`, `LLM-ci-cd-job-1`, `LLM-ci-cd-job-2`; design-only rows with the same workflow mapping = `ML-ci-cd-cho-real-time-drift-detection-`, `ML-ci-cd-ci-cd-cho-pipelines`, `ML-ci-cd-inference-engine`, `ML-ci-cd-job-1`, `ML-ci-cd-job-2`, `ML-ci-cd-training-pipeline`, `ML-ci-cd-web-api`; chart mappings = `ML-autoscale-autoscale-web-api-k-o-d-li-u-v`, `ML-web-api-k-o-d-li-u-to-k8s-with-helm-rollingupdate`, `ML-autoscale-web-api-cho-drift-detection`, `ML-web-api-cho-real-time-dri-to-k8s-with-helm-rollingupdate`.
- AC3 result: retained executed evidence is accounted for, no stale executed artifact is scheduled for recapture, and every identified stale mapping has an explicit correction action under its existing rubric owner. Mini pending rows and ML design-only rows stay deferred to their owning phases.

## Resource safety

No new billable resource was created. The approved evidence VM was stopped without deleting its persistent disk. The redundant external load balancer was removed through desired state, releasing one forwarding rule and its ephemeral address. A monthly budget guardrail with 50/90/100% alert thresholds was created. One GKE node remains running; approved window, teardown deadline and backup/export destination remain unrecorded.


## Commands exercised

- `date --iso-8601=seconds`
- `git tag -l evidence-baseline-pre-rebuild`
- `git rev-parse --short HEAD`
- `gcloud auth list --filter=status:ACTIVE`
- `gcloud billing projects describe project-60655616-d84a-4883-867`
- `gcloud compute project-info describe`
- `gcloud compute regions describe asia-southeast1`
- `gcloud beta billing accounts describe 01DCB8-DBCF3D-13358B`
- `gcloud billing budgets list --billing-account=01DCB8-DBCF3D-13358B` (budget exists: `fsds-evidence-guardrail`)
- `gcloud container clusters list`
- `gcloud compute instances list`
- `kubectl get nodes -o wide`
- `kubectl get svc -A --field-selector spec.type=LoadBalancer -o wide`
- repository inventory for `Jenkinsfile`, Jenkins, LangChain and LangGraph surfaces
- `gcloud billing budgets create --billing-account=01DCB8-DBCF3D-13358B --display-name=fsds-evidence-guardrail --last-period-amount --threshold-rule=percent=0.5/0.9/1.0`
- `gcloud compute forwarding-rules list`, `gcloud compute addresses list`
- GitOps edit + push: `platform/inference/vendored/03-net-kourier.yaml` → `ClusterIP` (`ae79945`)
- `kubectl -n dataflow get job lakehouse-gold-producer-live-1789416417` and job logs (superseded debugging run)
- `kubectl -n dataflow get job lakehouse-gold-producer-live-1789416418` and final job logs
- `kubectl -n dataflow get cronjob lakehouse-gold-producer` (final digest, `suspend=true`)
- `kubectl -n dataflow get configmap lakehouse-pipeline-source-fix --ignore-not-found`
- `curl POST http://127.0.0.1:18085/v1/features/by-id` for `NVL` risk features
- `kubectl -n argocd get app platform-data` (after active-key reseal and schema migration reconciliation: `Synced/Healthy`, revision `b6d1448`)
- `kubectl -n argocd get app platform-data platform-observability platform-security platform-agents platform-llm -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status,REV:.status.sync.revision`
- `kubectl -n argocd get app platform-observability platform-security platform-llm -o json` with filtered status/resource inspection
- `.venv-platform/bin/python scripts/run_platform_e2e.py --timeout 30 --json`
- Prometheus `/api/v1/targets` query for the five platform services
- `.venv/bin/python -m pytest tests/platform/test_platform_e2e_runner.py tests/test_cluster_pipeline.py -q`
- `.venv/bin/ruff check scripts/run_platform_e2e.py tests/platform/test_platform_e2e_runner.py src/io/minio_writer.py src/io/paths.py src/jobs/lakehouse_evidence_job.py`
- `.venv/bin/black --check scripts/run_platform_e2e.py tests/platform/test_platform_e2e_runner.py src/io/minio_writer.py src/io/paths.py src/jobs/lakehouse_evidence_job.py`
- `.venv/bin/python scripts/run_lakehouse_quality_gates.py` (`378 passed, 2 xfailed`; ruff, black, compose config, naming, rubric, target architecture and evidence audit all passed)
- local Docker build/push of `lakehouse-pipeline` to Artifact Registry (`source-mapfix`, `source-timestampfix`, and final `source-timestamp-nullfix`; final digest `sha256:0460ccf3ee0257f5e9de5b18f6242add8de6a6f342c18f5a24d6bbe454fb5c55`)
- `kubectl apply -f platform/data/schema-migration.yaml` and successful `platform-schema-v1` Job logs
- GitOps commits pushed: `ae79945`, `8052af9`, `ec5a305`, `4d26f08`, `c213119`, `5b0cf4a`, `e9cec0c`, `55611f1`, `34030fb`, `94b1d5d`, `d6d7c59`, `be8e2a3`, `4c24600`, `b6d1448`.

## Phase result

The dated inventory refresh is current and evidence-backed. The baseline tag and single-external-entry-point invariant are closed, and the final timestamp/null-safe producer completed a bounded generated-fixture run with Feast materialization; the dataflow application is now `Synced/Healthy` and its schema migration completed. Current observability and LLM Argo apps are not converged, and the security app remains degraded, so the live platform is not a clean prerequisite set. AC1 and AC3 are closed in this ledger; AC2 remains **BLOCKED** because an approved window, teardown deadline and backup/export destination are unrecorded and the GKE node is still running. Provider access, Jenkins host, domain/HTTPS, Kaggle capacity and Phase 04/05 implementation gates remain unverified or pending. Phase 01 remains **BLOCKED/PARTIAL**. No production-ready claim is made.
