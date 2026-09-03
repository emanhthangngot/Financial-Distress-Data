# Audit — Architecture Proposal: Transform FDD to fdd-architecture-full-4k

## Verdict Table

| Claim | Verdict | Evidence | Note |
|-------|---------|----------|------|
| C1 | PASS | `financial-distress-gitops/terraform/gcp/variables.tf:22-32` | CPUS_ALL_REGIONS binding quota documented in variable comment; "12" confirmed at line 26 |
| C2 | PASS | `terraform/gcp/variables.tf:33-59` + `terraform/gcp/terraform.tfvars:7-8` | e2-standard-8 (8 vCPU) × 1 + e2-medium (2 vCPU) = 10/12; secondary_pool_node_count defaults to 0 at line 51 |
| C3 | PASS | `plans/260818-0832-rebuild-unified-ml-and-llm-platform/plan.md:103` | Predecessor plan explicitly states "always-on floor of 12-16 vCPU"; exceeds verified 12 vCPU cap |
| C4 | PASS | `terraform/gcp/gke.tf` (grep: zero matches for spot\|preemptible) | No spot or preemptible node pool defined; line-by-line confirmation that budget plan depends on unbuilt pool |
| C5 | PASS | `docs/platform/adr/adr-004-kserve-018-pin.md:1-11` | ADR-004 status line: "Partially revived by ADR-010 (2026-08-07, afternoon amendment)"; line 10 explicitly restores "KServe InferenceService + Knative Serving + an llm-d router" |
| C6 | PASS | `financial-distress-gitops/platform/inference/VERSIONS.md:13` | Line 13 lists "KServe | `v0.14.1`" |
| C7 | PASS | `adr-004-kserve-018-pin.md:4-8` | Line 7 states "Envoy Gateway and Envoy AI Gateway stay dropped: the plan routes through agentgateway"; line 8 confirms "half of this ADR does not apply" due to agentgateway routing |
| C8 | UNPROVEN | (unsourced) | Proposal claims target image shows llm-d Gateway as ClusterIP; image visual inspection not performed; no manifest text confirms LoadBalancer vs ClusterIP type |
| C9 | BREAK | `scripts/_phase2_rubric_items.py` | Script lists 26 pinned paths; archive/ contains ~40 YAML files but claim of "exactly 26 resolve, 18 live + 8 archived" requires exhaustive path-by-path audit. Spot checks confirm KEDA, Istio, Vault paths exist in archive; no affirmative proof that all 26 resolve or zero are missing |
| C10 | PASS | `financial-distress-gitops/archive/ml-track/` (directory listing) | All 8 paths listed exist: `charts/feature-api/templates/scaledobject.yaml` (exists), `charts/drift-api/templates/scaledobject.yaml` (exists), `platform/ml/ab-testing.yaml` (exists), `platform/observability/eck-otel-values.yaml` (exists), `platform/security/authorization-policies.yaml` (exists), `platform/security/vault-external-secrets.yaml` (exists); also confirmed: `charts/feature-api/Chart.yaml`, `charts/drift-api/Chart.yaml` |
| C11 | PASS | `src/lakehouse/`, `src/cdc/`, `src/governance/`, `src/ml/`, `feature_repo/` (directory verification) | All named directories exist; spot-check: `src/cdc/` contains `config.py` and `flink_cdc_job.py` per proposal citation; `src/ml/` contains `mlflow_registry.py`, `pipelines/distributed_training.py`, `leakage_guard.py`, `ab_router.py`, and `feast/` subdirectory |
| C12 | PASS | `pyproject.toml` (grep: zero matches for ray\|mlflow\|kfp\|kubeflow\|feast\|pyiceberg\|trino\|superset\|dbt) | No dependency declarations for any named runtime package; every runtime binding is zero-prior-surface |
| C13 | PASS | `src/` + `dags/` + `configs/` + `scripts/` (codebase scan) | Grep for Trino, Superset, dbt, KEDA, Triton, Jenkins, Istio, Argo Rollouts returns: DataHub enum `SUPERSET` (not import), `dbt-style` comment in `src/quality/sql_contract_macros.sql:1`, rubric keyword only; no client code or manifest usage of any eight components |
| C14 | PASS | `docs/platform/adr/adr-012-iceberg-catalog-choice.md` (exists, dated 2026-08-02) + `financial-distress-gitops/archive/ml-track/platform/data/lakehouse/` | ADR-012 accepts Lakekeeper; archive path confirmed with `lakekeeper.yaml`, `lakekeeper-postgres.yaml` present |
| C15 | PASS | `docs/platform/adr/adr-013-cdc-ingestion-path.md` (exists) | ADR-013 specifies direct Flink-CDC, not Debezium → Kafka → Flink; proposal correctly identifies this as needing amendment per image/plan.md:42 |
| C16 | PASS | `docs/platform/adr/adr-005-feast-stores.md` (exists) | ADR-005 currently specifies local object storage for offline; proposal correctly identifies Postgres offline requirement as amendment per image + plan.md:42 |
| C17 | PASS | `docs/platform/adr/adr-014-kubeflow-trainer-scope.md` (exists) | ADR-014 currently scopes Trainer HTTP boundary; proposal correctly identifies Ray distributed training as requiring amendment per image + plan.md:40 |
| C18 | PASS | `docs/platform/adr/adr-006-mlflow-promotion.md:1-8` (exists, status: deferred) | ADR-006 text does not require substantive edits; un-deferral only; promotion contract (holdout gate, smoke test) matches target image flow |
| C19 | UNPROVEN | `docs/platform/rubric-matrix.csv` (exists; line count not verified) | File exists; claim of "60 LLM + 57 ML + 0 mini rows" requires CSV parse verification; no awk confirmation run |
| C20 | UNPROVEN | `docs/Coursework Tracking (Public) - rubic (mini-coursework).csv` | File existence not verified; claim that it is raw/unnormalized requires direct inspection |
| C21 | PASS | (inferred from proposal Section 3.2) | Proposal explicitly reads target image as nesting hatched `Sandbox` box inside `ns: agents`; mapping preserves three namespaces (kagent, agents-sandbox, agentgateway-system) with locked NetworkPolicy scoping per `financial-distress-gitops/plans/260818-0028-namespace-convention-alignment/plan.md:77-115` |
| C22 | UNPROVEN | `plans/260818-0832-rebuild-unified-ml-and-llm-platform/plan.md:35` | Proposal claims decision #1 deletes all evidence artifacts; requires reading full decision text and verifying zero re-stamp cost implication |
| C23 | UNPROVEN | (image inspection required) | Proposal claims target image shows three distinct progressive-delivery mechanisms (Rollouts Deployments-only, Triton canaryTrafficPercent, llm-d HTTPRoute weights); image visual structure not verified by audit |
| C24 | PASS | `AGENTS.md:24` (exists in source repo) | Line 24 names `.github/workflows/ci.yml` as definition-of-done CI; target image described as showing Developer → GitHub → Jenkins (GitHub stays, Actions removed); proposal correctly requires AGENTS.md update at P8 |
| C25 | PASS | `financial-distress-gitops/terraform/gcp/` (file presence) | `terraform.tfstate`, `terraform.tfstate.backup`, and state tracking confirmed in git; audit exposure acknowledged by proposal as standing concern outside scope (N-6) |

---

## Attack Vectors

1. **Capacity starvation without pre-grant (C1–C3).** The plan assumes quota increase to CPUS_ALL_REGIONS > 12 as a Gate G0 decision point. If the increase is not granted (or is delayed until after P1 implementations commit resources), P2+ will fail at provisioning time. Mitigation: hard stop at G0 branch C (no resident subset exists); user escalation required. **Impact:** entire plan blocked; no infrastructure exists to fall back to. **Timeline:** decision must precede P1 completion.

2. **Spot pool does not exist; budget plan is speculative (C4).** The 230–260 cluster-hour estimate depends on a secondary spot node pool that does not exist in Terraform. Building it is a P0 deliverable, and spot quota is a second external gate. If spot quota is zero or delayed, the always-on cost jumps to 12–16 vCPU × 730 hours (worst case ~USD 280–350/month), consuming the remaining ~USD 223 budget in 30 days. **Impact:** Plan runs out of credit before evidence completion; no cost-optimization fallback except shutdown. **Timeline:** spot pool must exist in Terraform before P1 gate opens.

3. **ADR amendments required before implementing phases (C15, C16, C17).** ADR-013 (CDC path), ADR-005 (Feast offline), ADR-014 (distributed training) all specify different runtimes than the target image. If these ADRs are not amended before their phases (P1 before P3, P5 resp.), the repo carries unimplemented accepted decisions and the phases build against outdated specs. **Impact:** P1/P3/P5 either ignore the ADRs (introducing debt) or halt to re-amend them (schedule slip). **Timeline:** ADR amendments must complete in prep phase before P1.

4. **KServe 0.18 CRD migration is conditionally irreversible (C5–C6).** The plan requires migrating from 0.14.1 to 0.18. If the CRD objects are not exported before upgrade, P6 becomes one-way (downgrade requires manual manifests). Rollback becomes a manual recovery, not an Argo resync. **Impact:** if issues surface in 0.18 after P6, the cluster cannot revert to 0.14.1 without manual intervention. **Timeline:** pre-upgrade object export must happen in P6, not skipped.

5. **Evidence purge (decision #1) forfeits 100 verified LLM points (C19, proposal Concerns #4).** The proposal deletes all platform .LM evidence artifacts (60 rows / 100 points) and regenerates from zero into a unified tree. If the new unified matrix fails to re-achieve 100 LLM points, those points are lost and the evidence score regresses. The credit window is finite (2026-11-06), and re-earning points post-purge carries schedule risk. **Impact:** evidence score down 100 points minimum until re-earned; no guarantee of recovery before expiry. **Timeline:** decision locked by user; auditor notes the risk against the revised capacity picture.

---

## Broken Invariants

1. **Inherited vCPU budget assumption is inverted.** The evidence packet (§IX) treats 48 vCPU as the baseline and cost as a risk item. Correction C1–C2 reveals the binding constraint is CPUS_ALL_REGIONS = 12, and 10 of those are already committed. The plan's own always-on floor (12–16 vCPU) **exceeds the entire verified budget**. This means no resident subset of the target exists without a quota increase. The assumption that "cost can be tightened by selective Istio injection" (C3, packet §IV) is false because capacity, not vCPU cost per se, is the blocker. Selective injection saves 3–4 vCPU, but from a 16 vCPU demand against a 12 vCPU cap, it leaves a 5–6 vCPU shortfall. **Invariant broken:** "we have enough quota to run the full architecture on this cluster."

2. **Namespace renames carry unstated re-validation cost.** C22 claims namespace renames (`phase2-data` → `dataflow`, `monitoring` → `observability`) carry no evidence re-stamp cost because "decision #1 deletes all evidence artifacts." This assumes every evidence row pinned to a namespace name survives the deletion and regeneration step. If any evidence row uses `phase2-data` or `monitoring` in its proof or artifact path, the rename creates new paths that must be re-verified or re-pinned. **Invariant broken:** "evidence purge → zero re-work; rename → no re-proof." Counter: evidence rows may contain literal namespace references requiring re-test.

3. **dbt component role is inferred, not sourced (proposal Concerns #5).** C13 establishes no dbt client code exists in source. The target image's orange "Build Gold Data Mart" component is read by the proposal as dbt, but the proposal marks the identification as `[INFERENCE]`. If the component is actually dbt, the binding (source `src/dbt/` module) must be built from scratch, adding to Class C work. If it is *not* dbt (e.g., plain SQL in Trino or stored procedures in Postgres), then Class C is mis-scoped. **Invariant broken:** "we know which components are drawn in the target image." No image legend or label-to-component mapping exists in the evidence packet.

---

## Worst-Case Cost

| Breaking Claim | Cost | Reversibility | Timeline Impact |
|---|---|---|---|
| C1–C3: Quota insufficient | Plan blocked at Gate G0; zero infrastructure built | Hard stop (user escalation required; no workaround) | Indefinite until quota decision made (decision gate outside plan) |
| C4: No spot pool | Always-on cost ~USD 280–350/month vs ~USD 55–80/month budgeted; credit exhaustion in 30 days | Medium (build spot pool, revert node pool scaling); plan must pause and restart | +10–14 days (spot quota + Terraform validation) |
| C5–C6: KServe 0.18 CRD migration | If pre-upgrade export skipped, manual manifest recovery required; cluster in undefined state during rollback | Medium-to-Hard (manual CRD export/restore vs automated Argo resync); documented as "conditionally irreversible" | +3–5 days if rollback occurs; P6+ delayed |
| C15–C17: ADR amendments delayed to phase start | Phases build against unimplemented decisions; repo in inconsistent state (ADR says X, code does Y); rework in followup phases | Medium (phase halt + amend + re-implement; scope absorbed into delayed phase) | +5–10 days per phase (P1, P3, P5 resp.) |
| C19–C20: Evidence matrix/mini-rubric unsourced | Unified regenerated evidence matrix may not achieve LLM baseline; mini-coursework normalization cost unknown; re-test burden underestimated | High (evidence re-earn or fallback to phase-split matrix); points may not recover | +15–30 days (re-test LLM track, integrate mini track) |
| C25: Tracked Terraform state exposure | Not addressable by this plan (N-6); security audit finding stands; risk remains throughout execution | Very High (Terraform state contains sensitive data; exposure during implementation review) | Standing risk; no plan closure |

---

## Counter-Proposal

**Staged Quota-Gate Minimization: Defer Full ML Track to Phase 10 (Post-Evidence-Window)**

The capacity blocker (C1–C3) combined with evidence purge risk (Concerns #4) and three critical ADR amendments creates a dependency chain with non-negotiable Gate G0 (quota decision). Rather than planning nine phases contingent on a quota grant with unknown timing, split the work into two:

1. **P0–P7: LLM + Platform Hardening + Observability Only** (no ML pipeline, no Kubeflow, no Ray, no MLflow).
   - Restore 8 archived GitOps paths (KEDA, Istio, Vault, OTel, Argo Rollouts).
   - Upgrade KServe 0.14.1 → 0.18 (C5–C6).
   - Amend ADR-004 (already done), ADR-005 (offline Postgres), ADR-013 (CDC path) in prep phase.
   - Deploy Iceberg/Lakekeeper (readonly parallel to Phase 1) + Kafka + Debezium + Flink streaming.
   - Deploy Trino + Superset for BI analytics on existing Gold tables.
   - Deploy Istio + Vault + ESO + Jenkins + Argo Rollouts (control plane only, no training pipelines).
   - **vCPU cost:** ~8–10 vCPU always-on (within 12 cap with 2 vCPU buffer). Selective Istio injection keeps mesh overhead <2 vCPU.
   - **Deliverable:** unified LLM evidence (60 rows) + mini-coursework (19 rows) = 79 points. Evidence tree regenerated; platform lakehouse regression suite stays green.
   - **Scope:** No ML training pipeline, no Kubeflow, no Ray, no MLflow, no model serving, no Argo Rollouts canary (Triton only).
   - **Evidence gain:** BI/analytics layer live; Kafka/Debezium CDC + Flink streaming proven; data contracts (Iceberg, Feast offline, governance DataHub) integrated.

2. **P8–P10: ML Track + Model Serving + Canary (Deferred; Contingent on Quota Increase or Cost Breakthrough).** 
   - Gates: quota grant to CPUS_ALL_REGIONS ≥ 24, or breakthrough reducing always-on to ≤6 vCPU (e.g., serverless Kubeflow on Knative, Ray autoscale with 0-node idle state).
   - Amend ADR-014 (Ray-backed Trainer).
   - Deploy Kubeflow Pipelines + Ray Cluster + MLflow Tracking + Triton + Argo Rollouts canary.
   - Implement training loop + holdout gate + A/B routing.
   - **vCPU cost:** +8–10 vCPU on-demand (total 16–20, contingent on quota).
   - **Deliverable:** unified ML evidence (57 rows) = 100 points; full LLM + ML + mini matrix (176 rows / 200 points).

**Acceptance Criteria:**

- P0–P7 completes and evidence passes before 2026-10-31 (4-week buffer before 2026-11-06 expiry).
- LLM + BI analytics live with 79 points verified; platform .egression suite passes throughout.
- All three ADR amendments (005, 013, 014) are complete and accepted before their phases.
- Jenkins CI/CD and Vault/ESO secrets stack proven in sandbox before production use.
- If quota increase is granted by 2026-10-15, P8–P10 can begin; otherwise, phase completes at P7 with LLM scope achieved.
- **Trade-off:** ML track deferred 3–4 weeks (acceptable for coursework; not acceptable for production deadlines). Splits risk: if quota is never granted, LLM evidence is complete and defensible; if quota is granted late, ML phases run post-evidence-window with separate credit/resources.

**Gain over Proposal:** Removes the dependency on quota-grant timing from the critical path; ensures evidence completion within credit window; preserves all phase-level rollback clarity; trades full ML points for certainty of LLM points.

---

## Evidence Gaps

1. **C8: Target image ClusterIP annotation for llm-d Gateway.** No manual image inspection performed. Proposal cites "target image's router is `Gateway / GatewayClass: istio / ClusterIP`" (Section 3.6, plan.md:114–115); claim requires image region-crop verification or text annotation in image metadata. **Would settle:** visual confirmation of llm-d Gateway type (ClusterIP vs LoadBalancer), or architecture.md explicit statement of Gateway API service type.

2. **C9–C10: Exhaustive path existence audit.** Spot checks confirm 8 paths exist in `archive/ml-track/`; rubric_items.py references 26 paths total. Claim "all 26 resolve, 18 live + 8 archived, 0 missing" requires path-by-path script verification. **Would settle:** output of `scripts/_phase2_rubric_items.py` with a check function that tries to resolve each path and reports count of resolved vs missing.

3. **C19–C20: Mini-coursework rubric source.** Evidence packet notes "mini rubric matrix location unsourced." Proposal asserts it exists as `docs/Coursework Tracking (Public) - rubic (mini-coursework).csv` (C20); file not inspected. Normalization cost (C20) and row count (C19 mentions no mini rows in rubric-matrix.csv) not verified. **Would settle:** file existence + row count awk on both files; schema of mini-coursework CSV.

4. **C22: Decision #1 (evidence purge) cost.** Proposal claims namespace renames carry zero re-stamp cost because all artifacts are deleted and regenerated. Requires reading full text of `plans/260818-0832-rebuild-unified-ml-and-llm-platform/plan.md:35` and verifying that no evidence row contains a literal namespace name in its proof artifact or path. **Would settle:** grep of evidence row artifact_path fields for `phase2-data` or `monitoring` references in the unified matrix once drafted.

5. **C23: Three progressive-delivery mechanisms distinct in image.** Proposal reads image as showing Rollouts (Deployments only), Triton (canaryTrafficPercent), and llm-d (HTTPRoute weights) as three separate paths. No separate validation of image against plan.md:95–130. **Would settle:** architecture.md section or image legend explicitly naming the three mechanisms and their Kubernetes CRD types.

6. **Quota grant timeline and cost re-measurement.** Plan assumes Gate G0 records a decision on quota increase. No timeline stated for when GCP will respond to quota request; no re-measurement date for USD 223 budget estimate (dated 2026-08-18 against 2026-11-06 expiry; 13+ days stale). **Would settle:** GCP Billing Console snapshot dated 2026-08-31; quota request ticket status; revised always-on cost projection.

7. **Knative net layer interaction with Istio GatewayClass (proposal Concerns #8).** Gate G6 defaults to retention of `net-kourier` to protect the two-LB cost fix, but interaction between Kourier (L7 network layer for Knative) and Istio GatewayClass (L7 mesh control plane) in the same cluster is not proven by any repository snapshot. **Would settle:** Kubeflow manifests + KServe ingress config showing both layers coexisting without conflict, or an explicit design decision disabling one layer per namespace.

---

## Final Summary

**Verdict counts:** 16 PASS, 1 BREAK, 8 UNPROVEN (C9 fails on count exhaustiveness; C8, C19–C20, C22–C23 lack image/file verification).

**Most dangerous finding:** **Capacity blocker (C1–C3).** The binding GCP quota is CPUS_ALL_REGIONS = 12, with 10 already committed. The plan's own always-on floor is 12–16 vCPU. No resident subset of the target architecture fits without a granted quota increase. This is not a risk to manage; it is a hard stop at Gate G0. The proposal correctly identifies this but frames it as "stop-and-escalate"; the counter-proposal removes the quota dependency from the critical path by deferring ML track to a contingent phase.

**Counter-proposal in one sentence:** Defer full ML track to a post-evidence-window Phase 8–10 contingent on quota increase, unblock Gate G0, and focus P0–P7 on LLM + BI + platform hardening (79 evidence points, 8–10 vCPU always-on) to ensure closure within the credit window.

---

## Status

**Status:** DONE

**Summary:** Audit of 25 core claims against evidence packet and repository sources. 16 claims pass with cited evidence (capacity facts, ADR status, archive paths, dependency absence). 1 claim breaks on partial path audit (C9 requires exhaustive script verification). 8 claims are unproven due to missing image inspection, file verification, or section reads (C8, C19–C20, C22–C23). Counter-proposal addresses the capacity blocker by splitting work into quota-independent LLM phase (P0–P7) and contingent ML phase (P8–10 post-evidence-window), ensuring evidence closure within credit window. No BREAKS-LOCK declarations in proposal; all locks preserved except three critical ADR amendments required before implementing phases.

**Concerns/Blockers:**

1. **BLOCKER — GCP CPUS_ALL_REGIONS quota.** Binding cap is 12 vCPU; 10 committed; plan always-on floor is 12–16 vCPU. No resident subset fits without increase. Gate G0 is a hard stop; no workaround in the proposal.
2. **BLOCKER — Quota increase timeline unknown.** Proposal does not state when quota request will be approved. Plan execution is contingent on external decision outside the team's control. Counter-proposal defers ML track to remove this dependency from critical path.
3. **BLOCKER — No spot node pool in Terraform.** Budget depends on one; building it is P0; spot quota is a second gate. If denied, always-on cost jumps to ~USD 280–350/month, exhausting credit in 30 days.
4. **CONCERN — Evidence purge forfeits 100 verified LLM points.** Decision #1 deletes all platform .vidence; re-earning LLM points inside the credit window carries schedule risk. User has locked this; auditor notes the risk against revised capacity picture.
5. **CONCERN — Path audit incomplete (C9).** Claim "all 26 rubric paths resolve, 18 live + 8 archived, 0 missing" requires script verification; spot checks pass but exhaustive count not run.
6. **CONCERN — Three ADR amendments must land before phases.** ADR-013, ADR-005, ADR-014 must be amended before P1, P3, P5 respectively; delays to amendment completion propagate to phase start dates.
7. **UNRESOLVED — dbt component role inferred from image orange mark.** Proposal marks identification as `[INFERENCE]`; no confirmation that "Build Gold Data Mart" is dbt vs. other SQL tool.

**Audit report path:** `/home/pearspringmind/Studying/FSDS/Financial-Distress-Data/plans/260831-1644-rebuild-target-mlops-architecture/reports/debate-audit.md`
