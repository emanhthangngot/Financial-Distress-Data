# ADR-010: LLM-Only Submission Scope and Platform Simplification

- Status: Accepted, amended 2026-08-07 (afternoon)
- Date: 2026-08-07
- Deciders: the platform architecture review, cost owner, platform operator
- Supersedes: ADR-001 (in part), ADR-003; amends ADR-004, ADR-005, ADR-007 (in
  part); defers ADR-006
- Related: `plans/260802-1037-unified-platform-ml-llm-gitops/plan.md` Session 2
  and Session 3 validation logs, `phase-03`, `phase-04`, `phase-05`, `phase-06`

## Context

The coursework accepts delivery of one of the two tracks. Seven days remain to
the deadline. Verified state at decision time:

- Zero of the 117 rubric rows had an executed evidence artifact. Only 59
  phase-02 product UI artifacts existed.
- The remaining plan estimated 46-67 workdays — roughly seven times the
  available budget.
- The local development machine had ~5 GB free RAM, insufficient to host the
  planned platform stack.
- No the platform Python dependency was installed; `.venv` held only `pytest`,
  `ruff`, `black`, `duckdb` and `pyspark`.
- `terraform`, `ansible`, `aws`, `k3d`, `mutmut` and `locust` were not
  installed.
- No LLM rubric row names EKS, Kubernetes, Argo CD, Istio, mesh, mTLS or TLS.
  The rows do require an agent sandbox, a reachable log-viewer service and a
  reachable trace-viewer service.

Under those constraints the previously accepted platform could not be built,
and building a smaller share of it would have forfeited scored rows to
unscored infrastructure.

## Decision

### 1. Submission scope

The submission delivers the **LLM track only**: 60 rows, 100 points. The 57 ML
rows remain in `docs/platform/rubric-matrix.csv` unchanged, and
`phase-05-deliver-ml-track.md` remains in place as the retrofit backlog. The ML
track is deferred, not cancelled; ADR-006 (MLflow promotion) is deferred with
it.

Track selection is enforced by a new `--track` filter on
`scripts/audit_phase2_evidence.py` that narrows **only** the executed-evidence
and behavior-validation gates. `_audit_matrix`, `_audit_canonical_coverage` and
the per-track 100/100 totals continue to require all 117 rows. Deleting rows or
zeroing expected totals is explicitly rejected: it hides the deferral and breaks
the canonical-coverage check.

### 2. Evidence plane — supersedes ADR-003 (amended 2026-08-07 afternoon)

**Original (morning) decision, since superseded:** a single rented CPU VM
(16-32 GB RAM, root access, hourly billing) running `k3d`, with AWS reduced to
one timeboxed three-hour session for Terraform, TLS and cost evidence.

**Current decision:** a **Terraform-provisioned GKE Standard zonal cluster**
(`asia-southeast1-b`) plus a Terraform-provisioned GCE VM for the Ansible row,
paid entirely from an untouched GCP free-trial credit (USD 300 / 90 days). Two
facts drove the change: the user will not spend out of pocket, only unused
trial credit; and the canonical LLM CSV's IaC row reads `Dùng Terraform để
setup GKE hoặc các cloud services` — GKE named first, which a k3d VM satisfies
only by analogy. Node pool size is decided day 0 from the real vCPU quota, not
assumed. Target spend is under USD 100 of the 300, kept low by hibernating node
pools overnight (`make gcp-up`/`gcp-down`, PVCs preserved) rather than by a
teardown-and-rebuild cycle.

Terraform authenticates via `gcloud auth application-default login`. **No
service-account key JSON is ever created** — the equivalent boundary to the
original "no long-lived AWS credential" rule, now expressed as ADC + Workload
Identity instead of OIDC-scoped tokens on a rented box. The trial billing
account is never upgraded to paid: an exhausted trial stops, an upgraded
account does not.

ADR-003's teardown discipline, cost tagging and "product plane must stay useful
when the evidence cluster is off" consequence (ADR-008) survive unchanged —
`make gcp-down` is the mechanism now, `terraform destroy`/EventBridge teardown
before.

### 3. Model chain — amends ADR-001, partially revives ADR-004 (2026-08-07 afternoon)

**Original (morning) decision, since amended:** KServe `LLMInferenceService`,
llm-d, Envoy Gateway and Envoy AI Gateway all dropped; the chain was `kagent
Agent -> kagent ModelConfig -> agentgateway AI backend -> OpenAI-compatible
small model server (CPU)`, direct on the model server.

**Current decision:** the evidence-plane move to GKE (section 2) removes the
reason KServe/Knative/llm-d were cut — "a full day of CRD wrangling on k3d" no
longer applies on a cluster with ~43 GB allocatable. The chain becomes:

```
kagent Agent -> kagent ModelConfig -> agentgateway AI backend
             -> llm-d router -> KServe InferenceService (Knative Serving)
             -> OpenAI-compatible small model server (CPU)
```

Envoy Gateway and Envoy AI Gateway **stay dropped** — agentgateway remains the
gateway the rubric's agent rows name, and it fronts the llm-d router rather
than Envoy fronting KServe. The model server itself is unchanged: a small
instruction-tuned model served on CPU by vLLM-CPU or llama.cpp. The rubric
asks for a custom model server that is benchmarked and optimized, not for
GPU-class throughput; the chain keeps a real benchmark (TTFT, inter-token
latency, throughput, memory) and a real optimization with a before/after
table, now against the restored `InferenceService`.

ADR-001's surviving normative rule: agentgateway remains the only path agents
use to reach models or tools, enforced by negative tests. ADR-004's pin is back
in effect for KServe/Knative/llm-d only — see its status header.

**Changed cost:** canonical row 2 (2 pts, links a KServe/llm-d deployment guide
verbatim) moves from *at risk* to *satisfied as written*, since KServe/llm-d is
now the literal stack deployed. Expected outcome revised from 85-95/100 to
**95-99/100**; see `phase-06`'s Honest Point Budget for the four rows that
remain at risk (benchmark quality, coverage, domain/HTTPS, Terraform apply).

### 4. Render tooling — supersedes ADR-007

Helm is the only render tool. Kustomize is dropped, so one resource has exactly
one owner by construction. `resource-ownership.yaml` and the duplicate-owner CI
check are removed as unnecessary rather than as a relaxation. CI validates
`helm lint/template` and `kubeconform`; `kustomize build` is removed.

### 5. Platform components dropped or restored

Restored 2026-08-07 afternoon (see section 3):

| Restored | Why it was cut | Why it is back |
|---|---|---|
| KServe `InferenceService`, Knative Serving, llm-d router | k3d on a 16 GB rented VM made CRD install a full-day risk | GKE has ~43 GB allocatable; this is the literal stack canonical row 2's guide describes |

Still dropped:

| Dropped | Replaced by | Rubric cost |
|---|---|---:|
| Istio (mesh, mTLS, authorization) | NGINX Ingress edge, `ClusterIP`-only backends, default-deny NetworkPolicy, proven by a negative direct-to-backend call | 0 |
| ECK / Elasticsearch / Kibana | Loki + Grafana Explore, exposed through the gateway | 0 |
| Vault / external-secrets operator | GitHub Actions secrets + OIDC + sealed-secrets | 0 |
| Envoy Gateway / Envoy AI Gateway | agentgateway | 0 |
| Jenkins in-cluster | GitHub Actions + Argo CD | 0 |
| GPU node pool | CPU host | 0 (free-trial GPU quota is 0; row 4 asks for benchmark + optimization, not throughput) |
| Agent Sandbox as a product install | `agents-sandbox` namespace: restricted PSS, tokenless ServiceAccount, default-deny egress, read-only root filesystem, proven by three negative demonstrations | 0 |
| Compatibility spike across 18 components | Version pinning; replace anything that fails to install | 0 |
| GKE Cloud Logging / Cloud Monitoring | Loki + Grafana (scored); Cloud Logging bills per GB | 0 |

ADR-009 (active F5 NGINX Ingress Controller OSS, never the retired community
`ingress-nginx`) and ADR-002 (two repositories) are unaffected.

### 6. Feature stores — amends ADR-005

Store backends move in-cluster: Redis for the structured online store (not
ElastiCache Valkey), PGVector in-cluster (not RDS), and in-cluster MinIO for
offline data and version manifests (not S3). The rest of ADR-005 stands.

**The structured Feast project still defines an offline store with correct
`event_timestamp` semantics**, even though only the online store is read during
the LLM-only week. This is load-bearing: retrofitting point-in-time correctness
onto an online-only key-value design is a schema redesign, not an addition, and
it is what keeps the ML retrofit at 4-5 days.

### 7. Retired self-imposed gates

The ">90% test coverage and >80% changed-code mutation score" bar is not a
rubric row. The rubric asks that mutation testing be used. The real numbers are
recorded; the submission is not failed against a threshold the coursework never
set.

## Consequences

- The submission scores at most 100 (one track) instead of 200 (two tracks).
  This is what the coursework permits and what the calendar allows.
- Four points remain at risk, none from the model-chain substitution (restored
  2026-08-07 afternoon — see section 3): benchmark quality (row 4), coverage
  >90% (row 26), domain/HTTPS (row 46), and a successful `terraform apply` (row
  47). See `phase-06`'s Honest Point Budget.
- Evidence is produced on Terraform-provisioned GKE, paid from GCP free-trial
  credit — not on EKS, and not on a rented third-party VM. This must be stated
  plainly in `docs/platform/` and the README. "Designed", "configured",
  "executed" and "passed" remain distinct statuses; nothing is labelled as
  running on infrastructure it did not run on.
- Nine load-bearing decisions listed in `phase-05-deliver-ml-track.md` must be
  honoured by the LLM track, or the ML retrofit degrades from additive work into
  rework.
- Three declared GitOps artifact paths are retargeted in both
  `docs/platform/rubric-matrix.csv` and
  `scripts/_phase2_rubric_items.py::EXPLICIT_IMPLEMENTATION`; they must stay in
  parity or `--matrix-only --strict` fails.
- Days 3-4 in `phase-06` absorb ~13h of restored KServe/Knative/llm-d/KEDA work
  without dropping any row (user-confirmed 2026-08-07); if either slips, warm-up
  (row 25) and A/B (row 16) are cut first.

## Alternatives Considered

- **Deliver both tracks anyway** (rejected: 46-67 workdays of remaining scope
  against 7 days; would have produced two incomplete tracks instead of one
  complete one).
- **Deliver the ML track instead of the LLM track** (rejected: ML-only residual
  work is 32 points against LLM's 42, but the LLM track was the user's
  objective and its shared platform is the same either way).
- **Keep EKS and cut rubric work to afford it** (rejected: EKS appears in zero
  rubric rows; spending scored-row time on unscored infrastructure inverts the
  objective).
- **Rent a third-party CPU VM and run k3d** (rejected 2026-08-07 afternoon,
  reversing the morning's own decision: the user holds unused GCP free-trial
  credit and will not spend out of pocket, and canonical row 67 names GKE
  first, which a k3d VM satisfies only by analogy).
- **Keep KServe/llm-d dropped and accept the ~2-point risk on row 2** (rejected
  once the evidence plane moved to GKE: the constraint that motivated the cut —
  CRD install risk on a 16 GB k3d box — no longer holds, so restoring the
  literal guide's stack is strictly better than the substitute).
