# Remaining Production Gaps — Gate Ledger

**Captured:** 2026-09-15T09:40:50+07:00
**Phase:** Gap 01 — Reconfirm gates and inventory
**Source revision:** `working tree` (post-`ffe7c91`; runtime slices are uncommitted and user changes remain preserved)
**Evidence baseline:** `evidence-baseline-pre-rebuild` resolves locally

## Status

| Gate | Status | Evidence | Owner / next action |
|---|---|---|---|
| Baseline tag | PASS | `git tag -l evidence-baseline-pre-rebuild` resolved | Evidence owner: retain tag and existing evidence |
| Billing/spend controls | BLOCKED | Billing enabled for `project-60655616-d84a-4883-867`, currency VND, user holds `roles/billing.admin`. Cloud Billing report for the last 90 days shows net subtotal/total `₫0` after savings with gross usage about `₫6,089,726`. A monthly budget `fsds-evidence-guardrail` now exists (`last-period` amount, alert thresholds 50/90/100%). A draft control block below proposes a fixed ceiling and teardown/export path, but no operator sign-off is recorded and an alert is not a hard cap | Operator: sign off or revise the proposed window, ceiling, teardown list and export destination |
| Project-wide CPU capacity | BLOCKED | `CPUS_ALL_REGIONS=12`, usage `9`; `GPUS_ALL_REGIONS=0`, usage `0`; forwarding-rule usage includes external network LBs | Platform owner: obtain approved quota/no-spend window before capacity-backed phases |
| Regional CPU capacity | BLOCKED | `asia-southeast1`: `CPUS=32`, usage `8` after stopping the evidence VM; `E2_CPUS=8`, usage `0`; `PREEMPTIBLE_CPUS=0`, usage `0`; `INSTANCES=8`, usage `2` | Platform owner: obtain approved quota/no-spend window before capacity-backed phases |
| Kubernetes capacity | BLOCKED | One Ready `e2-standard-8` node remains running; `fsds-evidence-worker` is now `TERMINATED`, with its 30-GB persistent disk `READY` and still attached; node remains billable and violates the documented between-session hibernation invariant | Platform owner: record authorization/window and teardown deadline; hibernate the node pool in a controlled operator action if no approved window exists |
| External load balancers | PASS | GitOps commit `ae79945` set `kourier-system/kourier` to `ClusterIP`; Argo synced revision `ae79945` and the live Service type is `ClusterIP`. Cluster now reports exactly one external `LoadBalancer` (`ingress-nginx` at `34.21.242.110`) and exactly one external forwarding rule | Platform owner: keep NGINX as the sole external entry point |
| Jenkins host/controller | UNVERIFIED | `fsds-evidence-worker` is `TERMINATED` and one GKE node remains Ready; no Jenkins health/controller inspection was performed. A root `Jenkinsfile` now exists with explicit source checkout/stash and clean-agent unstash steps, but no live controller/agent run was captured | Platform owner: identify or provision the approved controller, JCasC, backup and ephemeral-agent proof |
| Provider access/limits | PARTIAL | A real bounded VCI/KBS call for `VNM` using isolated `vnstock==4.0.7` succeeded. The community financial response exposed four quarter columns; the adapter emitted four `vnstock_vci`/`VND`/`is_synthetic=false` rows and 171 normalized KBS daily rows. Evidence: `docs/evidence/live/real-source-vci-vnm-20260915.json`. No Groq/Gemini capability or quota check was performed | ML/agent owner: measure allowed free providers before evaluation |
| LangGraph runtime | PARTIAL | `src/agents/langgraph_runtime.py` is implemented and dependency pins are declared. Local graph execution passed the coordinator success/error/citation contract and bounded specialist timeout contract; persistent PostgreSQL checkpointer restart and authenticated thread-boundary proof remain unverified | ML/agent owner: provide approved provider/runtime credentials, then measure parity and authenticate persistent thread IDs before cutover |
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
- Gap-02 local verification covers both the checked-in fixture and a bounded real VCI/KBS `VNM` run through local Docker Compose; the real run produced 4 live financial periods, 6 explicitly synthetic tier-cap backfill periods, 499 live market rows, Gold outputs in local MinIO, and `docs/evidence/live/real-source-cluster-vnm-20260915.json`.
- Gap-02 AC3 is **CLOSED locally**. `tests/test_vnstock_live_adapter.py` covers the four-period cap, records one exact `tier_period_cap` failure with requested/available/missing periods, routes only capped periods to the configured generator, records stable `generator_fallback_failed` failures, and asserts live rows remain `is_synthetic=false`; the focused gate passed `13`.
- Gap-02 AC4 is **CLOSED locally**. The disposable real-Feast test materializes two `known_from_ts` vintages, compares offline and online values with numeric tolerance/NaN-safe missing checks, verifies the selected source timestamp is not after cutoff, and excludes the newer vintage; the combined Feast gate passed `5` under `.venv-platform`. A fresh real-source local run also materialized `company_risk_features` for `VNM` into Redis and verified the offline/online identity at `known_from_ts=2026-09-15T03:16:44+00:00`; fresh cluster materialization remains an operator/runtime check while services are stopped.
- Gap-02 AC2 is **CLOSED locally**. `tests/platform/test_spark_gold_value_parity.py` runs real local PySpark 4.2.0 against the same fixture rows for financial, market and news facts and compares grain, keys, timestamps, provenance and values; the focused gate passed `7`. Spark runtime coordinates now derive from bundled Hadoop and support Hadoop 3.3.4's AWS SDK v1 coordinate and Hadoop 3.5.0's AWS SDK v2 coordinate.

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
- Workflow path reconciliation is complete: the 13 rubric rows now point to the existing `.github/workflows/phase2-ci.yaml` family. The six executed LLM rows retain their evidence; the seven ML rows remain design-only and genuinely unbuilt. Four additional ML design-only rows still reference absent GitOps `charts/feature-api`/`charts/drift-api`; the current chart inventory is `fastapi-service`, `feature-mcp`, `drift-mcp` and `web`, so those API deliverables remain unbuilt.
- The corrected row set is `LLM-ci-cd-agent-drift-detection`, `LLM-ci-cd-agent-k-o-d-li-u`, `LLM-ci-cd-agent-l-m-coordinator`, `LLM-ci-cd-ci-cd-cho-rag-data-pipeline`, `LLM-ci-cd-job-1`, `LLM-ci-cd-job-2`, plus the seven design-only ML CI rows; all now resolve to `phase2-ci.yaml`. Chart mappings remain `ML-autoscale-autoscale-web-api-k-o-d-li-u-v`, `ML-web-api-k-o-d-li-u-to-k8s-with-helm-rollingupdate`, `ML-autoscale-web-api-cho-drift-detection`, `ML-web-api-cho-real-time-dri-to-k8s-with-helm-rollingupdate`.
- Phase 01 AC3 result: retained executed evidence is accounted for, no stale executed artifact is scheduled for recapture, and every identified stale mapping has an explicit correction action under its existing rubric owner. Mini pending rows and ML design-only rows stay deferred to their owning phases.
- Architecture obligation audit: the master contract enumerates `O-1` through `O-8` plus `EXT-AGENT`, `EXT-EVAL`, `EXT-COST`, `EXT-KAGGLE` and `EXT-FT`; ownership is assigned across the target phases. The 161-row index and owning-phase citations are present, but no end-to-end production obligation is promoted to PASS here: data/model parity, LangGraph parity and cutover, Jenkins-only delivery, failure/rollback, protected serving and external-provider/Kaggle evidence remain pending or unverified.

## Resource safety

No new billable resource was created. The approved evidence VM was stopped without deleting its persistent disk. The redundant external load balancer was removed through desired state, releasing one forwarding rule and its ephemeral address. A monthly budget guardrail with 50/90/100% alert thresholds was created. A concrete execution-control draft is recorded below; one GKE node remains running pending operator sign-off.

## Draft resource-window controls (awaiting operator sign-off)

- Proposed execution window: one bounded session with a maximum wall-clock duration of 2 hours; exact start/end must be entered by the operator before any capacity-backed work.
- Proposed fixed budget ceiling: `₫1,000,000` incremental net spend for the session, replacing the current `last-period` budget basis if the billing control supports an absolute threshold. The budget alert remains advisory; the operator must stop work before the ceiling because it is not an automatic hard cap.
- Teardown order: (1) stop/scale the GKE node pool to zero after evidence export; (2) keep `fsds-evidence-worker` VM `TERMINATED`; preserve its attached 30-GB persistent disk and do not delete it; (3) release the `ingress-nginx` `LoadBalancer` and its forwarding rule only after protected-edge evidence is exported and the operator confirms the cluster no longer needs the sole external entry point; (4) verify no unexpected nodes, forwarding rules or load balancers remain.
- Proposed evidence export destination: redacted archive plus `manifest.sha256` under `/home/pearspringmind/Studying/FSDS/phase1-evidence-exports/20260915T041429+0700/`; copy to a separately approved durable destination before teardown, with no credentials or raw secret payloads.
- Draft status: documented for approval only; no new node, load balancer, disk deletion, backup deletion or export operation was performed by this draft.


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
- `.venv/bin/python scripts/run_lakehouse_quality_gates.py` (latest final gate: `384 passed, 2 xfailed`; pytest, ruff, black, compose config, naming, rubric, target architecture and lakehouse evidence audit all passed)
- local Docker build/push of `lakehouse-pipeline` to Artifact Registry (`source-mapfix`, `source-timestampfix`, and final `source-timestamp-nullfix`; final digest `sha256:0460ccf3ee0257f5e9de5b18f6242add8de6a6f342c18f5a24d6bbe454fb5c55`)
- `kubectl apply -f platform/data/schema-migration.yaml` and successful `platform-schema-v1` Job logs
- GitOps commits pushed: `ae79945`, `8052af9`, `ec5a305`, `4d26f08`, `c213119`, `5b0cf4a`, `e9cec0c`, `55611f1`, `34030fb`, `94b1d5d`, `d6d7c59`, `be8e2a3`, `4c24600`, `b6d1448`.
- `docker compose up -d minio minio-init platform-redis platform-postgres` for local-only Gap-02 verification, followed by `docker compose stop minio minio-init platform-redis platform-postgres`; named volumes were retained and no volumes were deleted
- `.venv/bin/python scripts/run_cluster_pipeline.py produce-gold` with the checked-in fixture profile (`gold_rows=843`, `risk_rows=16`, `risk_tickers=[HPG,NVL]`)
- `.venv-platform/bin/python scripts/run_cluster_pipeline.py materialize-risk` against local MinIO/Redis/Postgres (`registry_revision=3d1682a492d66a2d`; all seven risk features non-null)
- `CLUSTER_SOURCE_MODE=online CLUSTER_TICKERS=VNM .venv/bin/python scripts/run_cluster_pipeline.py produce-gold` against live VCI/KBS and local MinIO (`gold_rows=2041`, `risk_rows=10`, `adapter_failed_records=1`; evidence `docs/evidence/live/real-source-cluster-vnm-20260915.json`)
- `PLATFORM_VERIFY_TICKER=VNM .venv-platform/bin/python scripts/run_cluster_pipeline.py materialize-risk` against the real-source Gold output and local Redis (`registry_revision=1f9f619f68c6fd3d`; offline/online vintage identity verified)
- checked-in Spark parity invocation against real local PySpark 4.2.0; the current package resolver derives the coordinate from bundled Hadoop and the value/key/grain/provenance parity gate passed `7`
- `.venv/bin/python -m pytest tests/test_restatement_leakage.py tests/test_generator_restatement.py tests/test_bitemporal_contract.py tests/test_vnstock_live_adapter.py tests/platform/test_lakehouse_cluster_parity.py -q` (`20 passed`; historical baseline)
- `.venv/bin/python -m pytest tests/platform/test_spark_gold_value_parity.py -q` (`7 passed`; actual local PySpark value/key/grain/provenance parity, including Hadoop 3.3.4 connector resolution)
- `.venv-platform/bin/python -m pytest tests/platform/pipelines/test_feast_known_from_ts_axis.py tests/platform/pipelines/test_feast_smoke.py -q` (`5 passed`; local Feast vintage selection and materialization)
- `.venv/bin/python -m pytest tests/test_vnstock_live_adapter.py -q` (`13 passed`; adapter-boundary tier-cap routing, stable fallback failure reason, and synthetic marker checks)
- `.venv-platform/bin/python -m pytest tests/platform/agents/test_langgraph_runtime.py tests/platform/agents/test_runtime.py tests/platform/verification/test_delivery_contract.py -q` (`17 passed`; LangGraph timeout/error contract, authenticated persistent-checkpointer guard, role wiring, lane validation, rollback digest and Jenkins handoff contracts)
- local Docker services stopped after verification; no additional cloud resource was created. A previously requested GKE node-pool scale-down remains operator-reconciling (`fsds-evidence` / `primary-pool`, observed node count `1`); no cluster deletion was attempted.

## Phase result

The dated inventory refresh is current and evidence-backed. The baseline tag and single-external-entry-point invariant are closed, and the final timestamp/null-safe producer completed a bounded generated-fixture run with Feast materialization; a later bounded local VCI/KBS `VNM` run completed Bronze-to-Silver-to-Gold plus Feast materialization against local MinIO/Redis, with six tier-cap backfill rows explicitly marked synthetic. The dataflow application is now `Synced/Healthy` and its schema migration completed. Current observability and LLM Argo apps are not converged, and the security app remains degraded, so the live platform is not a clean prerequisite set. Gap-02 AC1, AC2, AC3 and AC4 are **CLOSED locally**: schema provenance survives, live-source tier-cap routing is explicit, Spark parity is measured against real local PySpark, and Feast vintage selection is verified with tolerant numeric comparison. LangGraph, delivery, and runtime hardening are locally verified but provider parity, persistent PostgreSQL checkpointer restart, live Jenkins/controller execution, protected HTTPS, fresh cluster materialization, and real-source production-plane E2E remain unverified. Phase 01 AC2 remains **BLOCKED** pending operator sign-off on the drafted 2-hour window, proposed `₫1,000,000` ceiling, teardown list and evidence export destination. No production-ready claim is made.
