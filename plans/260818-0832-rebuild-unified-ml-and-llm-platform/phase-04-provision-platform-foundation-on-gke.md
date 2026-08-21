---
title: "Phase 4: Provision The Platform Foundation On GKE"
status: todo
priority: P1
effort: "1.5 weeks"
dependencies: [1]
---

# Phase 4: Provision The Platform Foundation On GKE

## Overview

Rebuild the cluster to hold both tracks at once: resize the node pools against the
approved quota, install Istio in sidecar mode with Kiali, Vault + External Secrets, Jenkins, NGINX
Ingress + cert-manager, and the observability stack, all reconciled by Argo CD from
the GitOps repo. Un-archive the ML platform manifests and restructure the GitOps
repo around namespaces rather than tracks.

Runs in parallel with phases 2-3 from the moment the quota increase lands.

## Requirements

Functional:
- [ ] Terraform provisions the GKE cluster as an on-demand pool (~12 vCPU) plus a tainted **spot** pool (~36 vCPU), plus the GCE VM for the Ansible row
- [ ] Exactly **one** external load balancer exists; Kourier and agentgateway are `ClusterIP` behind NGINX
- [ ] Ansible configures the VM through roles, converging to `changed=0` on re-run
- [ ] Argo CD reconciles every platform component; no `kubectl apply` is a deployment path
- [ ] **Istio installed in sidecar mode with mesh-wide injection**, mTLS enforced, and at least one `AuthorizationPolicy` denying an unauthorized service-to-service call
- [ ] **Kiali** installed and rendering the platform service graph
- [ ] **Native sidecar (`restartPolicy: Always` init container) verified for every Job-producing workload** — Kubeflow steps, Ray, Spark, Airflow `KubernetesPodOperator`, model-loader — each proven to reach `Completed`
- [ ] Vault deployed, unsealed, with External Secrets Operator syncing secrets into namespaces
- [ ] Jenkins controller + dynamic agents running in-cluster, with credentials sourced from Vault
- [ ] NGINX Ingress + cert-manager serving HTTPS on the registered domain via a **wildcard certificate** issued through the Cloudflare DNS-01 solver
- [ ] Subdomain routing live for every externally reachable service; **exactly one** `LoadBalancer` Service exists cluster-wide
- [ ] Prometheus, Grafana, Loki, Jaeger, PushGateway and an **OpenTelemetry Collector** installed and receiving
- [ ] Knative **Serving and Eventing** + **KServe 0.18+** installed, with both the core controller and the `llmisvc` controller, serving one track-neutral smoke `InferenceService`
- [ ] **Gateway API CRDs + Gateway API Inference Extension (GIE) + LeaderWorkerSet** installed, with **Istio as the gateway provider** (`GatewayClass: istio`); GIE CRDs applied **before** the provider, since the provider decides extension support at startup
- [ ] The llmisvc `Gateway` is a `ClusterIP` reached through the NGINX Ingress — it does not create a second `LoadBalancer`
- [ ] vLLM CPU throughput measured with explicit thread configuration, and the **serving branch (A: llm-d / B: llama.cpp) decided and recorded** before phase 6 starts
- [ ] **Argo Rollouts** controller installed, providing progressive delivery for the API and web Deployments; the model A/B rows use `canaryTrafficPercent` (ML) and `HTTPRoute` weights (LLM) instead — see the Architecture section
- [ ] `archive/ml-track/` restored into the live GitOps tree, restructured by namespace

Non-functional:
- [ ] `make gcp-up` / `gcp-down` hibernate node pools to zero with PVCs preserved
- [ ] Always-on floor measured after install and recorded; must sit at or below ~16 vCPU, leaving ~32 for scheduled work
- [ ] Every windowed component (DataHub, Trino, Superset, Flink, Jenkins, Kubeflow, Ray, Spark) has a verified scale-to-zero path

## Architecture

The GitOps repo is reorganized from `platform/<track-ish>` into namespace-aligned
directories matching the target architecture in `plan.md`, with one Argo CD
`Application` per namespace and an `ApplicationSet` generating the per-app
overlays. Track labels remain on workloads for cost attribution and for the
time-slicing fallback, but nothing is gated on them.

Istio runs in **sidecar mode with mesh-wide injection** — the user's decision, taken
for reference fidelity and evidence quality over footprint. Every workload pod gets
an Envoy sidecar, so mTLS, L7 `AuthorizationPolicy` and Kiali's service graph cover
the whole platform rather than two namespaces.

Two consequences follow and both are handled here rather than downstream:

1. **Job completion.** Envoy does not exit when a job container finishes, so without
   care every Kubernetes Job hangs in `Running` forever. Istio is therefore
   configured to use Kubernetes **native sidecars** (`restartPolicy: Always` init
   containers, stable since 1.33; the cluster runs GKE 1.35.6). Any workload that
   cannot be made to terminate this way is annotated
   `sidecar.istio.io/inject: "false"` and documented as an explicit exception — a
   hung Kubeflow or Spark job discovered in phase 5 costs a cluster window.
2. **Knative networking.** With Istio present mesh-wide, Knative uses `net-istio`
   rather than the `net-kourier` the old install pinned, removing a redundant
   ingress layer and matching the reference topology.

Three traffic-splitting mechanisms are installed here, one per surface, as settled
in `plan.md`'s routing section: **Argo Rollouts with `trafficRouting.nginx`** for the
API and web Deployments, **KServe `canaryTrafficPercent`** for the Triton
champion/candidate pair, and the **`LLMInferenceService` router's Gateway API
`HTTPRoute` weights** for the LLM A/B pair. Rollouts cannot own a Knative-backed
`InferenceService`, so pointing it at the models is not an option; conversely
`canaryTrafficPercent` exists only in serverless mode, which is why KServe stays on
Knative Serving for the ML track.

That makes **Gateway API a hard dependency**, not a rejected alternative:
`LLMInferenceService` requires Gateway API, the Gateway API Inference Extension
(GIE), LeaderWorkerSet and a gateway provider, and creates its own `Gateway` and
`HTTPRoute`. The provider is **Istio** (`GatewayClass: istio`) rather than the
default Envoy Gateway, because Istio is already installed mesh-wide and a second
Envoy data plane would split TLS, auth and rate limiting. The `Gateway` is a
`ClusterIP` behind the single NGINX Ingress, so the one-load-balancer rule holds.

Vault replaces sealed-secrets wholesale. Sealed-secrets is removed, not left
alongside — two secret mechanisms would undermine the "centralized across the whole
organization" claim the rubric row asks for. Vault's Kubernetes auth backend issues
short-lived credentials; ESO materializes them as Secrets; Jenkins reads its own
credentials from Vault through the Vault plugin.

## DataHub backing stores — decided

DataHub needs four dependencies. Three are satisfied by what the cluster already
runs; one is not:

| Dependency | Decision | Why |
|---|---|---|
| Kafka | **Reuse** the existing cluster, separate topic prefix and consumer groups | Saves ~2-3 vCPU, and see the emitter note below — this is the decision that makes DataHub's scale-to-zero safe |
| Database | **Reuse** the existing PostgreSQL, in its own `datahub` database | DataHub supports Postgres, not only MySQL. A separate database (not merely a schema) keeps it clear of `project_metadata` and `ml_metadata`, consistent with the existing no-cross-write rule |
| Search index | **Deploy fresh Elasticsearch**, single node, replicas 0, small heap | Unavoidable. Loki is log aggregation with its own index and no Elasticsearch API — it cannot serve as DataHub's search backend, despite both being "the logging/search stack" |
| Graph index | **Elasticsearch**, `graph_service_impl` set away from Neo4j | DataHub's own recommendation for lighter deployments; removes a whole database |

Footprint drops from ~4-6 vCPU to **~2-3 vCPU**: GMS, frontend, single-node
Elasticsearch and the system-update job.

**Do not reuse the GraphRAG Neo4j as DataHub's graph index.** Phase 8's novel idea
deploys Neo4j, so sharing it looks like a free saving. It is not: Elasticsearch is
still mandatory for search either way, so the reuse saves nothing and couples
governance to an experiment whose pod gets restarted while its retrieval strategy is
being tuned.

**Use the Kafka emitter, not the REST emitter, for lineage.** This is the
non-obvious part. DataHub is a windowed component that scales to zero outside the
governance window. With a REST emitter, any pipeline that emits lineage while GMS is
down loses that lineage silently — and the loss surfaces in phase 8 as a gap in the
graph, long after the run that should have populated it. With the Kafka emitter the
events sit in the topic and GMS consumes them when it comes up. This is what makes
the residency schedule safe, and it matters more than the vCPU saving.

## Related Code Files

GitOps repo (`financial-distress-gitops`):
- Create: `platform/gateway-api/` (Gateway API CRDs, GIE, LeaderWorkerSet, `GatewayClass: istio`, the llmisvc `Gateway`), `platform/argo-rollouts/`, `platform/istio/`, `platform/kiali/`, `platform/datahub/` (GMS + frontend + single-node Elasticsearch; Kafka and Postgres referenced, not deployed), `platform/vault/`, `platform/external-secrets/`, `platform/ci-jenkins/`, `platform/kubeflow/`, `platform/mlflow/`, `platform/ray/`, `platform/trino/`, `platform/superset/`, `platform/datahub/`, `platform/redis/`, `platform/debezium/`, `argocd/applicationset-platform.yaml`
- Modify: `terraform/gcp/gke.tf` (node pool sizing), `terraform/gcp/vm.tf`, `ansible/roles/**`, `Makefile`, `argocd/applications/**`, `platform/observability/**`, `platform/ingress/**`
- Move: `archive/ml-track/**` → live `platform/` and `charts/` trees
- Delete: `platform/security/sealed-secrets*`, all `SealedSecret` manifests

## Implementation Steps

1. Confirm the approved quota against the **48 vCPU** baseline. At 48, proceed as planned. Below 48, stop and re-decide before provisioning — the first lever is selective sidecar injection (`api-serving`, `agents`, `kserve` only, recovering ~3-4 vCPU), the second is time-slicing the two tracks. Do not size optimistically and discover the ceiling at install time.
2. Update `terraform/gcp/gke.tf` to **two pools split by preemption tolerance**: an on-demand pool of ~12 vCPU for the always-on floor (Postgres, MinIO, Istio control plane, Argo CD, observability) and a **spot** pool of ~36 vCPU for everything restartable (Spark, Ray, Kubeflow, Trino, DataHub, serving). Taint the spot pool and set tolerations per workload so nothing lands there by accident. `terraform plan` and review the vCPU total against quota before applying.
3. **Cut the two redundant load balancers before anything else runs.** Set `kourier-system/kourier` and `agentgateway-system/agentgateway-proxy` to `ClusterIP` in the GitOps manifests and route both behind NGINX Ingress. Do not delete the forwarding rules directly — GKE recreates a rule deleted underneath a `LoadBalancer` Service. This is ~USD 94 of the remaining credit and it also fixes the rubric row requiring services to sit behind the gateway. With `net-istio` replacing Kourier in step 10, the first of the two disappears anyway.
4. Restructure the GitOps repo by namespace; restore `archive/ml-track/` into the live tree; delete the archive directory once nothing references it.
5. Install Istio in **sidecar mode** via Argo CD with mesh-wide injection and native sidecars enabled, plus **Kiali**. Enable `PeerAuthentication` STRICT mTLS. Write one `AuthorizationPolicy` that denies a specific unauthorized caller; keep the denied-call evidence as the proof for that row, and capture the Kiali service graph as supporting evidence.
6. **Prove Job completion under the mesh before anything depends on it.** Run one throwaway Kubernetes Job, one Spark submit, one Ray job and one Airflow `KubernetesPodOperator` task in an injected namespace; each must reach `Completed`, not hang in `Running`. Any that cannot are annotated `sidecar.istio.io/inject: "false"` and recorded as documented exceptions. This gate exists because discovering a hung Kubeflow step in phase 5 costs a whole cluster window.
7. Deploy Vault (single-node with persistent storage; auto-unseal via GCP KMS) and External Secrets Operator. Migrate every existing secret into Vault, then delete all sealed-secret material and the controller.
8. Deploy Jenkins with the Kubernetes plugin for dynamic agents and the Vault plugin for credentials. Verify no credential is stored in Jenkins' own config.
9. Reinstall NGINX Ingress + cert-manager. Configure a `ClusterIssuer` using the **ACME DNS-01 challenge with the Cloudflare solver**, credential sourced from Vault, and issue a **wildcard certificate** for `*.<domain>` plus the apex. HTTP-01 cannot issue wildcards — if the issuer is left on HTTP-01, every subdomain needs its own certificate and the Let's Encrypt rate limit becomes a real constraint. Verify HTTPS end to end on the apex and one subdomain before proceeding.
   Keep `distresslens.duckdns.org` resolving until the wildcard issues successfully; retire it only afterwards.
10. Install Knative **Serving and Eventing** plus **KServe 0.18+** — both the core controller (`InferenceService`, for the ML track's Triton serving) and the `llmisvc` controller (`LLMInferenceService`/`LLMInferenceServiceConfig`, for llm-d). Replace the old `v0.14.1` pin and its vendored manifests wholesale. Record the new pins in `platform/inference/VERSIONS.md`. Use **`net-istio`** as Knative's networking layer, replacing `net-kourier`, since Istio is now mesh-wide.
   **The `llmisvc` controller does not run on Knative.** Its documented dependencies are Gateway API, the Gateway API Inference Extension, LeaderWorkerSet and a gateway provider; it creates `Gateway` and `HTTPRoute` objects, and Knative is not in that chain. Install, in this order: Gateway API CRDs, **GIE CRDs**, then the provider — `GatewayClass: istio`, not the default Envoy Gateway, so the mesh's existing data plane serves it — then LeaderWorkerSet. The order matters: the provider inspects available CRDs at startup to decide whether it supports the inference extension, so installing GIE afterwards leaves it silently disabled. Pin the `Gateway` Service to `ClusterIP` and route it through NGINX; verify with `kubectl get svc -A --field-selector spec.type=LoadBalancer` that the count is still one.
   Knative **Eventing** is not optional and not implied by Serving: the ML rubric names it literally — *"Cho real-time drift detection Web API (sử dụng KNative Eventing kết hợp với KServe)"*. Install the Eventing CRDs and a **Kafka-backed** Broker here — not the in-memory one, since phase 5's real-time producer is a `KafkaSource` on `inference_log` and an in-memory Broker drops events whenever its pod restarts, which on the spot pool is routine. Phase 5 wires the drift service's Trigger to it.
11. Smoke-test four things on that install before any later phase depends on them: one `InferenceService`, one `InferenceService` with `canaryTrafficPercent` splitting traffic across two revisions, one `LLMInferenceService` reachable through its `HTTPRoute`, and one Eventing Broker→Trigger delivery.
12. **Decide the LLM serving branch here — this is an architecture fork, not a benchmark.** Run vLLM on CPU with explicit `OMP_NUM_THREADS` and thread pinning and measure TTFT and tokens/s against a fixed prompt set; vLLM's own docs state the CPU path is not an optimization target, so treat unusable throughput as the expected outcome, not the surprise.
    - **Branch A — usable.** Keep `LLMInferenceService` on llm-d. Phase 6 delivers the KV-cache-aware routing on/off comparison as planned.
    - **Branch B — unusable.** Serve an OpenAI-compatible llama.cpp server behind a plain `InferenceService` with a custom `ServingRuntime`. This is **not** a drop-in backend swap: there is no shipped llama.cpp `ServingRuntime` for KServe (kserve issue #5334 is still a proposal), and dropping llm-d drops KV-cache-aware routing with it. The optimization row is then earned by quantization sweeps plus the gateway semantic cache's hit-rate comparison, which phase 8 builds anyway.
    Record the branch, the measured numbers and the chosen evidence story in `docs/evidence/ml/` before phase 6 starts. The agent gateway and `ModelConfig` wiring are unchanged either way — that is what the `ModelRuntime` adapter interface is for — but the CRD, the router and one rubric row's evidence are not.
13. Deploy Prometheus, Grafana, Loki, Jaeger, PushGateway and an **OpenTelemetry Collector**; confirm scraping, log shipping and trace collection all work before any application depends on them. The Collector is what makes the trace rows real: Istio sidecars emit one span per proxy hop, so without application instrumentation a "trace" is a chain of network hops with no idea what happened inside each service — not one request walking API → service → Feast → inference. Services export OTLP to the Collector, which forwards to Jaeger.
14. Rebuild `make gcp-up` / `gcp-down` / `gcp-status` for the new node-pool layout; verify PVCs survive a full hibernate/wake cycle. Add per-group targets (`make up-training`, `up-streaming`, `up-analytic`, `up-governance`) so a window brings up only what it needs — the capacity budget in `plan.md` depends on this being one command, not a manual scaling exercise nobody does under time pressure.
15. Measure and record the real always-on idle vCPU with every windowed group scaled to zero. Compare against the ~16 vCPU floor in the budget. If it exceeds that, cut before phase 5 rather than discovering the ceiling mid-training.
16. Run the Ansible playbook against the VM twice; capture the second run's `changed=0` output.

## Success Criteria

- [ ] `terraform apply` converges; `terraform plan` afterwards reports no drift
- [ ] Ansible second run reports `changed=0`
- [ ] Argo CD shows every Application `Synced` and `Healthy`
- [ ] A call from an unauthorized service is denied by `AuthorizationPolicy`, with the denial captured from logs
- [ ] Kiali renders the service graph with mTLS indicated on the edges
- [ ] Every Job-producing workload class reaches `Completed` under injection, or is a documented `inject: false` exception
- [ ] `vault status` shows unsealed; ESO syncs a secret into a workload namespace; zero `SealedSecret` resources remain in the repo or cluster
- [ ] Jenkins runs a pipeline that reads a Vault credential without that credential existing in Jenkins config
- [ ] Wildcard certificate valid for `*.<domain>` and the apex; HTTP redirects to HTTPS
- [ ] `kubectl get svc -A --field-selector spec.type=LoadBalancer` returns exactly one row, with the Gateway API `Gateway` installed and serving
- [ ] An `LLMInferenceService` answers a completion through its `HTTPRoute` via NGINX, and an `InferenceService` splits traffic across two revisions at a set `canaryTrafficPercent`
- [ ] The LLM serving branch is recorded with its measured TTFT/tokens-per-second, and the evidence story for the optimization row names the mechanism that branch can actually demonstrate
- [ ] Grafana shows node and pod metrics; Loki returns pod logs; Jaeger shows a trace
- [ ] Hibernate/wake cycle preserves all PVC data
- [ ] Cluster vCPU at full load ≤ 85% of approved quota

## Risk Assessment

- **Quota denied or under-approved.** This is the phase's dominant risk and it is decided in step 1, not discovered later. Fallback: label-driven time-slicing, +1.5 weeks.
- **The always-on footprint may exhaust the quota before any workload runs.** Rough idle accounting: Kubeflow Pipelines ~8, DataHub (GMS + Elasticsearch + backing store) ~4-8, Kafka + Connect + Flink ~5-7, Trino ~2-4, Airflow ~2-3, Jenkins ~2, observability ~2-3, KServe/Triton/vLLM ~4-8, agents/MCP/gateway ~2-4, Istio/Vault/ingress ~2-3 — roughly **30-45 vCPU idling**, leaving little or nothing for the Spark jobs, Ray bursts and Locust run that also have to happen. Phase 5 already commits to hibernating Ray, Kubeflow and Spark between windows; that discipline is insufficient because it omits the always-on services. **Mitigation: extend scale-to-zero-between-windows to DataHub, Trino and Flink as well — none needs to be resident outside its own evidence-capture window. Measure the real idle total right after install and record it; if it exceeds 70% of quota, start the cut list immediately rather than at week 9.**
- **DataHub carries 8 points and cannot be substituted** — the mini rubric names the product literally ("Capture màn hình pipeline trên **DataHub UI**"). Its backing-store decision is settled in the section above rather than left open, because it changes both the footprint and whether the residency schedule works at all.
- **The stack does not fit resident at 48 vCPU.** The budget in `plan.md` puts everything-resident at 36-54 vCPU before any Spark or Ray burst. Mitigation: this is designed around, not mitigated — an always-on floor of ~12-16 vCPU plus scheduled per-group residency, with `make up-<group>` targets so bringing up a window is one command. The failure mode to guard against is not exceeding quota once; it is components silently staying up between windows and quietly eating the burst headroom. Step 13 measures the real floor rather than trusting this estimate.
- **A missed Job-completion case stalls a pipeline silently.** The symptom is not an error but a pod stuck `Running`, which reads as "still working" until a window is gone. Mitigation: step 6 is a hard gate covering all four job classes before phase 5 begins, and any exception is written down rather than left implicit.
- **Knative + Istio sidecar interaction.** Switching Knative from `net-kourier` to `net-istio` removes a layer but changes the request path for every `InferenceService`. Mitigation: the step-11 smoke test exercises `InferenceService`, `canaryTrafficPercent`, `LLMInferenceService` and an Eventing delivery after the switch, so a broken path surfaces immediately rather than in phase 6.
- **Vault migration can lock the cluster out of its own secrets.** Mitigation: migrate secrets into Vault and verify ESO sync **before** deleting sealed-secrets. Keep the sealed-secrets controller running until the last consumer is confirmed on ESO.
- **Jenkins in-cluster consumes more than budgeted.** Mitigation: controller with modest resources and ephemeral Kubernetes agents that scale to zero between builds; no static agent pool.
- **Restoring `archive/ml-track/` reintroduces stale manifests.** Mitigation: treat the archive as a reference to port from, not a directory to copy — every restored manifest is reviewed against the current namespace layout before it lands.
