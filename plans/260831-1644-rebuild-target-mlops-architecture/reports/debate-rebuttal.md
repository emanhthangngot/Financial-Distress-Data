# Rebuttal — Architecture Proposal: Transform FDD to `fdd-architecture-full-4k`

**Seat:** ArchitectureProposerRebuttal · **Round:** 3 (proposer rebuttal) · **Date:** 2026-08-31
**Answers:** `reports/debate-audit.md` · **Defends:** `reports/debate-proposal.md`
**Locks:** all preserved. **No `BREAKS-LOCK` declared in this rebuttal.**

---

## 0. Method and what this round actually ran

Round 2 left six claims disputed and seven evidence gaps open, five of which the auditor
declared unsettleable without inspecting the target image or executing the rubric script.
Both were done in this round rather than argued around:

| Check | Command / action | Where the result lands |
|---|---|---|
| Exhaustive 26-path audit | imported `scripts/_phase2_rubric_items.py`, resolved every `artifact_repo == "gitops"` path against `../financial-distress-gitops/` then `archive/ml-track/` | C9, C10, gap 2 |
| Rubric matrix parse | `csv.DictReader` over `docs/phase2/rubric-matrix.csv`, counted `track` / `evidence_type` | C19, gap 3 |
| Mini rubric parse | `csv.reader` over `docs/Coursework Tracking (Public) - rubic (mini-coursework).csv` | C20, gap 3 |
| Namespace-literal grep | scanned every `evidence_path`, `artifact_path`, `validation_command`, `behavioral_assertion` cell for `phase2-data` / `monitoring` | C22, invariant 2, gap 4 |
| Target image OCR + region crops | `magick` crop of `images/architecture/fdd-architecture-full-4k.png` (4000×4088) + `tesseract`, then direct visual read of two crops | C8, C23, invariant 3, gaps 1 and 5 |
| Terraform re-read | `terraform/gcp/variables.tf:24-53`, `gke.tf:96-131`, `terraform.tfvars:6-8` | C1, C2, C4, vector 2 |
| Knative net layer | `platform/inference/VERSIONS.md`, `06-config-network-patch.yaml`, vendored `04-kserve.yaml` | gap 7 |

**One defect in the audit is recorded first, because it affects how Round 4 reads the record.**
The audit's Final Summary states *"16 PASS, 1 BREAK, 8 UNPROVEN"* (`debate-audit.md:131`). Its own
verdict table (`debate-audit.md:7-31`) contains **19 PASS, 1 BREAK (C9), 5 UNPROVEN (C8, C19, C20,
C22, C23)**. The table is authoritative — 19 + 1 + 5 = 25 claims, and every claim C1–C25 has
exactly one row. This rebuttal answers the **table**. The summary line is a counting error, not a
sixth disputed claim.

---

## 1. Response to every verdict

`ACK` = PASS accepted. `ACK+` = PASS accepted with additional corroboration supplied.
`REBUT` = finding contested with new evidence. `ACCEPT` = finding taken; design changes.

| Claim | Audit verdict | Response | One-line basis |
|---|---|---|---|
| C1 | PASS | `ACK+` | `terraform/gcp/variables.tf:26-29` re-read: `CPUS_ALL_REGIONS` "is 12"; regional `CPUS` = 32 named non-binding at line 25 |
| C2 | PASS | `ACK+` | `variables.tf:36,41,47,52,58` — `e2-standard-8` × 1 + `e2-medium`, `secondary_pool_node_count = 0`; comment at :29 states "= 10/12, a 2-vCPU buffer" |
| C3 | PASS | `ACK` | `plan.md:103` always-on floor 12-16 vCPU; sharpened in §3.1 below (it is worse than the audit computed) |
| C4 | PASS | `REBUT (narrow)` | Pool absence conceded; **the pool resource already exists** — `gke.tf:96-131`. Only the `spot` attribute is missing. See §2.2 |
| C5 | PASS | `ACK` | ADR-004 revival by ADR-010 afternoon amendment |
| C6 | PASS | `ACK+` | `platform/inference/VERSIONS.md:13` `KServe v0.14.1`; :11-12 pin Knative Serving and net-kourier at `knative-v1.16.0` |
| C7 | PASS | `ACK` | Envoy chain stays dropped; agentgateway is the router |
| C8 | UNPROVEN | `REBUT` | Image read. Text in the drawing: `Gateway / GatewayClass: istio / ClusterIP`. Zero `LoadBalancer` tokens in the whole image. See §2.1 |
| C9 | **BREAK** | `REBUT` | Exhaustive audit executed: **26 paths, 18 live, 8 archived, 0 missing**. See §2.3 |
| C10 | PASS | `ACK+` | The same run returns exactly the 8 paths C10 names — no more, no fewer |
| C11 | PASS | `ACK` | — |
| C12 | PASS | `ACK` | — |
| C13 | PASS | `ACK` | — |
| C14 | PASS | `ACK` | — |
| C15 | PASS | `ACK` | ADR-013 amendment is a P1 deliverable ahead of P3, as written |
| C16 | PASS | `ACK` | ADR-005 amendment is a P1 deliverable ahead of P3 |
| C17 | PASS | `ACK` | ADR-014 amendment is a P1 deliverable ahead of P5 |
| C18 | PASS | `ACK` | Un-defer only |
| C19 | UNPROVEN | `REBUT` | Parsed: **60 LLM + 57 ML = 117 rows, 0 mini rows**; `evidence_type` = 60 `executed` / 57 `design_only`. See §2.4 |
| C20 | UNPROVEN | `REBUT + revise` | File exists, raw form confirmed; **44 scored rows / 100 points**, not merely "84 lines". C20 revised to carry the row and point count. See §2.5 |
| C21 | PASS | `ACK+` | Image crop confirms the hatched sandbox tier is drawn separately; NetworkPolicy lock untouched |
| C22 | UNPROVEN | `REBUT (with a residual)` | `plan.md:35` read verbatim; **zero** `phase2-data` and **zero** namespace-valued `monitoring` references in any evidence field. See §2.6 |
| C23 | UNPROVEN | `REBUT` | Image crop shows all three mechanisms with their annotations, including `canaryTrafficPercent 10 → 25 → 50`. See §2.7 |
| C24 | PASS | `ACK` | `AGENTS.md:24` update scheduled at the P8 flip |
| C25 | PASS | `ACK` | Standing exposure, N-6, unchanged |

**Score after this round, by the proposer's accounting:** 19 PASS stand, the 1 BREAK is rebutted
with an executed check, all 5 UNPROVEN are settled with new evidence, and **1 claim (C20) is
revised** because the new evidence is more specific than the claim was.

---

## 2. The six disputed claims, in full

### 2.1 C8 — llm-d Gateway is ClusterIP · `REBUT`

The audit's requirement was exact and fair: *"visual confirmation of llm-d Gateway type
(ClusterIP vs LoadBalancer)"* (`debate-audit.md:113`). It was performed.

`images/architecture/fdd-architecture-full-4k.png` is 4000×4088. Crop
`1150x300+2270+2030` (the `ns: kserve` box) renders, verbatim as drawn:

```
Gateway / GatewayClass: istio / ClusterIP
```

Full-image OCR (`--psm 11`, 481 lines) returns that same string as a single label and returns
**zero** occurrences of `LoadBalancer` anywhere in the drawing — `grep -ic loadbalancer` = `0`.

This settles C8 affirmatively and preserves the two consequences the claim was load-bearing for:
ADR-009's sole-external-entry rule survives, and no third idle load balancer is created
(USD 54/month/LB, packet §IX). Acceptance criterion **AC-P6-2** (`debate-proposal.md:758`) already
encodes the runtime re-check — *the cluster's external LoadBalancer count is unchanged from before
P6* — so the image reading is a design input, not the final proof.

**Evidence gap 1: closed.**

### 2.2 C4 — no spot pool · `REBUT (narrow)`, and it changes the P0 estimate

The claim as written is correct and the audit's PASS stands: `grep -c 'spot\|preemptible'
terraform/gcp/gke.tf` = 0. **But the audit's attack vector 2 draws a cost from it that the
Terraform does not support.** Vector 2 says *"Building it is a P0 deliverable"* and prices the
consequence at *"+10–14 days (spot quota + Terraform validation)"* (`debate-audit.md:64`).

Re-reading the file: a **second node pool already exists as a Terraform resource** —
`gke.tf:96-131`, with `node_count = var.secondary_pool_node_count` (:106) and
`machine_type = var.secondary_pool_machine_type` (:109), defaulting to `e2-standard-4` / `0` nodes
(`variables.tf:44-53`, `terraform.tfvars:8`). `variables.tf:30-32` states the intent explicitly:

> `secondary_pool_node_count` defaults to 0 (pool exists, no nodes, zero quota use) so it can be
> scaled up later without a new `terraform apply` plan diff if a quota increase is granted.

So the P0 deliverable is **adding `spot = true` to an existing `node_config` block and raising one
integer**, not authoring and validating a new pool. The external gate — spot quota — is real and
survives; the internal build cost does not. Vector 2's Terraform-validation component of the
"+10–14 days" is overstated by roughly the whole Terraform half.

**Revision R-2 (below) rewrites the P0 spot item to match.**

### 2.3 C9 — all 26 pinned GitOps paths resolve · `REBUT` (the BREAK falls)

The audit's objection was well-formed: spot checks are not an exhaustive audit, and it named the
settling artifact — *"output of `scripts/_phase2_rubric_items.py` with a check function that tries
to resolve each path and reports count of resolved vs missing"* (`debate-audit.md:115`). Run:

```
import _phase2_rubric_items as R
paths = sorted({it.artifact_path for it in R.ITEMS if it.artifact_repo == 'gitops'})
# resolve each against ../financial-distress-gitops/ then archive/ml-track/
→ TOTAL 26  LIVE 18  ARCHIVED 8  MISSING 0
```

Archived, exactly and only:

```
charts/drift-api/Chart.yaml
charts/drift-api/templates/scaledobject.yaml
charts/feature-api/Chart.yaml
charts/feature-api/templates/scaledobject.yaml
platform/ml/ab-testing.yaml
platform/observability/eck-otel-values.yaml
platform/security/authorization-policies.yaml
platform/security/vault-external-secrets.yaml
```

That list is identical to C10's, so C9 and C10 close together. Two secondary corrections to the
audit's reasoning at `debate-audit.md:15`:

- *"archive/ contains ~40 YAML files"* is not a counter-fact. The pinned set is 26; whatever else
  the archive holds is unpinned and outside both claims.
- The GitOps-root heuristic over-counts. `SOURCE_ARTIFACT_ROOTS` / `GITOPS_ARTIFACT_ROOTS`
  (`_phase2_rubric_items.py:305-324`) place `.github/workflows/` under the GitOps roots tuple while
  `artifact_repo` assigns those two rows to `source`. Filtering by prefix yields 28; filtering by
  `artifact_repo` — the field the rows are actually keyed on — yields 26. The claim says 26 and is
  right.

**C9's BREAK is withdrawn on evidence. Evidence gap 2: closed.**

### 2.4 C19 — rubric matrix composition · `REBUT`

The audit asked for the awk (`debate-audit.md:25,117`). Equivalent CSV parse of
`docs/phase2/rubric-matrix.csv` (118 physical lines, 19 columns, 117 data rows):

```
track:         {'LLM': 60, 'ML': 57}          → 0 mini rows
evidence_type: {'executed': 60, 'design_only': 57}
total_points:  LLM 100, ML 100
```

Every element of C19 holds exactly as stated: 60 LLM, 57 ML, 57 `design_only`, no mini rows.

### 2.5 C20 — mini-coursework rubric source · `REBUT`, and C20 is revised upward in precision

`docs/Coursework Tracking (Public) - rubic (mini-coursework).csv` exists. Raw-export form
confirmed on every point the claim asserted:

| Property | Measured |
|---|---|
| Physical lines | 84 (`wc -l`; file's last line is unterminated, so 85 text lines) |
| Logical CSV records | 47 |
| Columns | 5 — header is `['', '', '', 'Proof', 'Point']`: **three unnamed leading columns** |
| Cells containing an embedded newline | 16 |
| Rows carrying a numeric `Point` | 45 |
| Of those, section-total rows | 1 (record 47: empty requirement, `Point = 100`) |
| **Scored rows** | **44** |
| **Scored points** | **100** (200 raw sum − the 100-point total row) |

This is stronger than C20 claimed, and it cross-validates a locked decision. Locked decision **1b**
(`plan.md:36`) fixes the unified scope at *"161 rows / 300 points"*. Measured:
`117 (ML+LLM) + 44 (mini) = 161 rows`, and `100 (ML) + 100 (LLM) + 100 (mini) = 300 points`. The
lock's arithmetic is exact against the two source files.

**C20 is revised** from "84 physical lines" to the row/point statement above, because the
normalization task P1 owns is sized in rows, not lines. The claim's *conclusion* — that the
packet's "mini rubric matrix location unsourced" gap reduces to a normalization task into the
19-column schema — is unchanged and now quantified: **44 rows into 19 columns.**

**Evidence gap 3: closed.**

### 2.6 C22 — namespace renames carry no evidence re-stamp cost · `REBUT`, with one residual

`plan.md:35`, read in full, is the decision the claim rests on:

> | 1 | Additive retrofit of code and platform; **delete all existing evidence and regenerate** |
> The 100 LLM points already executed must be re-earned. No evidence artifact survives. |

"No evidence artifact survives" is categorical, so the premise holds. The audit's real objection is
sharper than the premise, and it is the one worth answering — Broken Invariant 2
(`debate-audit.md:53`): *"evidence rows may contain literal namespace references requiring
re-test."* Tested directly, across all 117 rows and all four evidence-bearing fields:

| Field | `phase2-data` | `monitoring` |
|---|---|---|
| `evidence_path` | 0 | 1 |
| `artifact_path` | 0 | 2 |
| `validation_command` | 0 | 1 |
| `behavioral_assertion` | 0 | 2 |

**Zero `phase2-data` references exist anywhere in the matrix.** All five `monitoring` hits are the
English word, never the Kubernetes namespace:

- `ML-a-b-testing-monitoring-dashboard-to-monito` — a rubric-id slug derived from the requirement
  text "monitoring dashboard"; its `evidence_path` and `validation_command` inherit the slug.
- `dags/phase2/phase2_drift_monitoring.py` (2 rows) — a Python module filename in the **source**
  repo, unaffected by a Kubernetes namespace rename.
- `python_ast_contains:monitoring` (2 rows) — an AST-token assertion against that same module.

Renaming the `monitoring` namespace to `observability` touches none of them. C22 stands.

**Residual, stated rather than argued away.** This grep runs against the *current* matrix, which
decision #1 deletes. It proves the rename is free *today*; it cannot prove the regenerated matrix
will stay free. That is a one-command guard, and it becomes a P1 acceptance criterion —
**revision R-4** below. **Evidence gap 4: closed for the current tree, guarded for the new one.**

### 2.7 C23 — three distinct progressive-delivery mechanisms · `REBUT`

The audit asked for image-structure verification (`debate-audit.md:29,121`). Crop
`1150x300+2270+2030` of the target image renders, in one frame:

| Mechanism | As drawn | CRD surface |
|---|---|---|
| Triton canary | `NVIDIA Triton InferenceService` → `revision N-1 \| stable 90%` and `revision N \| canary 10%`, joined by the label **`canaryTrafficPercent 10 → 25 → 50`** | KServe `InferenceService` |
| llm-d A/B | `HTTPRoute` / `group: llm-ab` → `llm-d isvc-a model w =9` and `llm-d isvc-b model w =1` | Gateway API `HTTPRoute` |
| Argo Rollouts | separate `ns: rollouts` box: `Argo Rollouts`, annotated **`Rollouts: Deployments only`**, `canary + AnalysisTemplate` | Argo `Rollout` |

Three mechanisms, three CRD families, drawn in two different namespace boxes, with the Rollouts box
explicitly fenced off from the CRDs by its own annotation. The image is unambiguous and C23's
reading of it is literal. Unifying them under Argo Rollouts would contradict the drawing, so the
proposal's refusal to unify stands. **Evidence gap 5: closed.**

---

## 3. Response to every attack vector

### Vector 1 — Capacity starvation without pre-grant (C1–C3) · `ACCEPT the risk`, mitigation restated and sharpened

Accepted without qualification, and **sharpened against the proposer's own interest**: it is worse
than the audit computed. `CPUS_ALL_REGIONS = 12` caps **VM** vCPU. Of the committed 10, the
`e2-medium` evidence VM (2 vCPU) is not a cluster node (`variables.tf:29,55-58`). **Schedulable
cluster capacity today is 8 vCPU**, one `e2-standard-8`. The always-on *workload* floor of 12-16
vCPU (`plan.md:103`) must fit inside that 8, minus GKE system overhead. The shortfall is not 5-6
vCPU; it is 4-8 vCPU after selective injection, against 8 total.

No design change follows, because the proposal already encodes exactly this as a blocking gate: P0
is *"a gate, not work"* and *"no phase after it is authorized until its branch is recorded"*
(`debate-proposal.md:456-457`). There is no resident subset to fall back to, and the proposal does
not pretend there is.

**Mitigation, all of it repo-sourced, none of it new scope:**

1. The quota request is not an open question — it is **locked decision #3** (`plan.md:38`):
   *"GCP quota target 48 vCPU, locked as the planning baseline | Submit on day 1 — approval takes
   1-3 days."* Gate G0's job is to submit and record, not to decide whether to ask.
2. The grant is absorbed without a Terraform redesign: `variables.tf:30-32` states the secondary
   pool exists at zero nodes precisely so it "can be scaled up later without a new `terraform
   apply` plan diff if a quota increase is granted."
3. Gate G0 gains two recorded artifacts the audit asked for (**revision R-3**).

### Vector 2 — Spot pool does not exist; budget is speculative (C4) · `ACCEPT the external gate`, `DISAGREE with the internal cost`

Two halves, answered separately.

**Accepted:** spot quota is a genuine second external gate, and if it is zero the always-on
arithmetic degrades. That belongs in the risk register and in G0.

**Disagreed:** the "+10–14 days (spot quota + Terraform validation)" figure prices a pool build
that is not needed. Per §2.2, `gke.tf:96-131` already declares the second pool; the change is
`spot = true` inside an existing `node_config` plus one variable default. Terraform validation of a
one-attribute diff on an existing resource is hours, not days. The residual timeline is **GCP's
spot-quota response**, which is the same external clock as vector 1 and does not add a second
serial wait.

**Disagreed, second premise:** vector 2 costs failure at *"12–16 vCPU × 730 hours"*
(`debate-audit.md:39`). That cannot happen, because 12-16 vCPU cannot be provisioned at all under
C1 — the cap is 12 VM vCPU and 10 are committed. The worst case at current quota is bounded by the
quota, not by the demand. If quota is granted *and* spot is denied, the on-demand figure applies;
that is a compound branch of G0, not the default failure mode.

### Vector 3 — ADR amendments required before implementing phases (C15–C17) · `AGREE; already the design`

No dispute. This vector describes the proposal rather than attacking it. ADR-013, ADR-005 and
ADR-014 amendments are **P1 deliverables**, and P1 is *"Contracts, ADR cutover, unified evidence
tree (source-only)"* (`debate-proposal.md:473`), gated ahead of P3 and P5 by the dependency graph
in §6. The audit's own timeline requirement — *"ADR amendments must complete in prep phase before
P1"* (`debate-audit.md:41`) — is satisfied one phase earlier than the phases that consume them.
P1 is source-only and cluster-free, so it runs while G0 is still waiting on GCP. No change.

### Vector 4 — KServe 0.18 CRD migration is conditionally irreversible (C5–C6) · `ACCEPT`; already gated, now with the rollback path named

Accepted as stated. The pre-upgrade export is already a hard acceptance criterion: **AC-P6-1**
requires *"the pre-upgrade object export exists as a P6 entry artifact"*
(`debate-proposal.md:757`) — an *entry* artifact, so P6 cannot begin without it. The vector's
failure mode ("if the pre-upgrade export is skipped") is therefore unreachable through the gate.

One thing the vector gets right that the proposal left implicit: the *rollback* is not an Argo
resync even with the export in hand, because CRD schema removal is not reversed by a git revert.
**Revision R-5** records that P6's rollback is the one documented exception to the universal
`git revert` + resync boundary (`debate-proposal.md:678-679`).

### Vector 5 — Evidence purge forfeits 100 verified LLM points · `ACCEPT the risk`, with a mitigation the audit did not have

Accepted, and the audit is right that this is user-locked (decision #1, `plan.md:35`) and therefore
not the proposer's to reopen. Two facts bound the exposure:

1. **Re-earning is a re-run, not a re-design.** All 117 rows — including all 60 LLM rows — carry a
   populated `validation_command`, `behavioral_assertion` and `evidence_path`
   (`docs/phase2/rubric-matrix.csv`, verified: 60/60 on each field, 117/117 across the matrix).
   The regeneration is executing 60 recorded commands against a rebuilt cluster and re-capturing
   output. What decision #1 destroys is the *captures*, not the *contracts*.
2. **The purge is not optional even if it were unlocked.** `plan.md:36` gives the reason: the data
   plane is rebuilt on Iceberg at 10-50M rows, so *"the mini evidence would be invalidated
   anyway — Spark skew, compaction and DataHub lineage all have to be recaptured."* The same
   applies to LLM rows pinned to cluster state.

The residual — that regeneration is gated on a cluster that is gated on quota — is real, and it is
already Concern #4. It does not change the design, because the alternative (keep stale captures
against a rebuilt platform) produces evidence that does not describe the running system.

---

## 4. Response to every broken invariant

### Invariant 1 — inherited vCPU budget assumption is inverted · `ACCEPT` (it is the proposal's own C3)

Fully accepted; see §3 vector 1, where the number is corrected further downward (8 schedulable
vCPU, not 12). One clarification for the record: this invariant breaks the **evidence packet**
(§IX, which inherited the 48-vCPU baseline), not the proposal. The proposal states the inversion
itself as C1-C3 and opens with it — *"the always-on floor exceeds nothing available today (§0.4)"*
(`debate-proposal.md:322`). The audit and the proposal agree; nothing is in dispute.

### Invariant 2 — namespace renames carry unstated re-validation cost · `REBUT`

Answered in full at §2.6. Zero `phase2-data` references, zero namespace-valued `monitoring`
references across all four evidence fields of all 117 rows. The invariant as stated —
*"evidence rows may contain literal namespace references"* — is falsifiable and was falsified.
The residual (the *regenerated* matrix must stay clean) is conceded and converted into a P1
acceptance criterion, **revision R-4**.

### Invariant 3 — dbt component role is inferred, not sourced · `REBUT (largely)`, with the residual bounded

The audit is right that the proposal marked this `[INFERENCE]` and right that no text label reads
"dbt". The image was inspected. Crop `620x200+1230+840` shows:

```
                    SQL ↘
Airflow daily DAG ──► [orange ✕ mark] ──"Buld Gold Data Mart"──► trino
                                                                   │
                                                              "Run SQL"
                                                                   ▼
                                                     gold.distress_holdout_v1
```

Three facts the audit did not have:

1. The orange mark is a **logo, not a labelled box** — it is the dbt Labs glyph. The image labels
   every other component with a wordmark or a vendor logo (NVIDIA, KServe, trino's rabbit, Argo's
   octopus), so a bare logo here is consistent with the drawing's convention, not an omission.
2. Its **topology is the dbt-on-Trino pattern exactly**: an orchestrator (`Airflow daily DAG`)
   triggers it, it emits `Build Gold Data Mart`, and the arrow terminates at `trino` — i.e. it
   compiles SQL and executes it through a query engine rather than owning storage.
3. Full-image OCR returns **no `Superset` token and no second SQL-tool label** anywhere near this
   region, so the audit's alternatives ("plain SQL in Trino or stored procedures in Postgres") have
   no drawn representation competing for this box.

**The residual is real but bounded, and it does not touch the phase plan.** Whichever tool the
glyph names, the P7 deliverable is identical in shape: *the Airflow daily DAG builds the Gold Data
Mart by running SQL against Trino*. If it is dbt, P7 builds `src/dbt/` and a dbt CronJob; if it is
not, the same CronJob runs the same SQL without the dbt layer — strictly less Class C work, never
more. So the identification cannot mis-scope the plan upward, and the invariant *"we know which
components are drawn"* is downgraded from unresolved to **logo-identified, with a
scope-non-increasing fallback**. **Revision R-1** records this. **Evidence gap 5: closed for the
delivery mechanisms; this one narrowed, not eliminated.**

---

## 5. Response to the remaining evidence gaps

| Gap | Status | Basis |
|---|---|---|
| 1 — C8 image ClusterIP | **Closed** | §2.1 — image text reads `ClusterIP`; zero `LoadBalancer` tokens image-wide |
| 2 — C9/C10 exhaustive path audit | **Closed** | §2.3 — 26 / 18 live / 8 archived / 0 missing, executed |
| 3 — C19/C20 rubric sources | **Closed** | §2.4, §2.5 — both files parsed; 117 + 44 = 161 rows, 300 points, matching lock 1b |
| 4 — C22 purge cost | **Closed for the current tree, guarded for the new one** | §2.6 + revision R-4 |
| 5 — C23 three mechanisms | **Closed** | §2.7 — all three visible in one crop with their annotations |
| 6 — quota timeline and cost re-measurement | **Partly closed; the rest becomes a G0 artifact** | Timeline is locked decision #3 (`plan.md:38`, "approval takes 1-3 days"). The USD 223 figure is dated 2026-08-18 (`plan.md:126-131`) and the audit is right that it is stale — revision R-3 |
| 7 — Kourier / Istio GatewayClass coexistence | **Narrowed from unproven to configured** | Below |

**Gap 7, answered from the repository.** The audit asked for *"Kubeflow manifests + KServe ingress
config showing both layers coexisting, or an explicit design decision disabling one layer per
namespace"* (`debate-audit.md:125`). The KServe ingress config is vendored in this repo and it
carries the flag that governs exactly this:

- `platform/inference/VERSIONS.md:15-19` — *"Networking layer is net-kourier, not Istio (dropped)
  … `06-config-network-patch.yaml` sets `config-network`'s `ingress-class` to route through
  Kourier."*
- `platform/inference/06-config-network-patch.yaml:11` — `ingress-class:
  "kourier.ingress.networking.knative.dev"`.
- `platform/inference/vendored/04-kserve.yaml:31765-31767` — KServe's own `inferenceservice-config`
  documents `disableIstioVirtualHost`: *"By setting this field to true, user can use other
  networking layers supported by knative"*, citing the upstream Kourier-networking admin guide.

The two layers occupy different surfaces: Kourier is Knative's **cluster-local** ingress for
`InferenceService` revisions (`networking.internal.knative.dev`), while Istio's GatewayClass is the
**Gateway API provider** for the llm-d `LLMInferenceService` router (`gateway.networking.k8s.io`).
Coexistence is a supported upstream configuration selected by one documented flag, not an unproven
interaction. Gate G6's default — retain `net-kourier` (`debate-proposal.md:547-550`) — is therefore
a configured decision rather than an open risk, and the two-LB cost fix is protected by
construction. Runtime confirmation still belongs to P6; the *design* question is closed.

---

## 6. Counter-proposal: **DEFEND the original. The counter-proposal is rejected.**

The audit proposes *Staged Quota-Gate Minimization: defer the full ML track to a contingent
Phase 8-10*, claiming it *"removes the dependency on quota-grant timing from the critical path"*
(`debate-audit.md:107`). It does not. It is rejected on four independent grounds, any one of which
is sufficient.

### 6.1 It does not remove the blocker, because the ML track is not what breaches the cap

This is decisive on its own. The residency table at `plan.md:86-101` marks each group's
*Resident when*. Every group the counter-proposal defers is **already windowed, never `Always`**:

| Deferred by the counter-proposal | Idle vCPU | Resident when (`plan.md`) |
|---|---:|---|
| Kubeflow Pipelines standalone | 3-4 | Training window (:96) |
| Spark job, Ray workers, Locust | +6-12 | *"Their own windows only"* (:101) |
| Triton (inside Serving) | — | Serving + LLM windows (:93) |
| MLflow | — | not a listed always-on group |

**Deferring the ML track removes 0 vCPU from the always-on floor.** The floor is set entirely by
groups the counter-proposal *retains* (`plan.md:88-92`):

| Retained by the counter-proposal | Idle vCPU | Resident when |
|---|---:|---|
| Istio + Kiali | 5-6 | **Always** |
| Core platform: Argo CD, Argo Rollouts, Vault, ESO, cert-manager, NGINX | 2-3 | **Always** |
| Gateway API stack for llm-d (GIE + LWS) | 1-2 | **Always** |
| Observability | 3-4 | **Always** |
| Stores: MinIO, Postgres, Redis | 2-3 | **Always** |
| **Sum** | **13-18** | — |

Against a schedulable capacity of 8 vCPU (§3 vector 1), the counter-proposal's P0-P7 is *further*
from fitting than the audit's own Broken Invariant 1 says the full plan is. Gate G0 is not
unblocked; it is unchanged.

### 6.2 Its own capacity number is unsourced and contradicted by the table it cites

`debate-audit.md:85` asserts *"~8–10 vCPU always-on (within 12 cap with 2 vCPU buffer). Selective
Istio injection keeps mesh overhead <2 vCPU."* Both figures fail against `plan.md`:

- The retained groups sum to **13-18**, not 8-10 (§6.1).
- Selective injection is sourced at *"roughly 3-4 vCPU"* recovered from a 5-6 vCPU Istio line
  (`plan.md:110-113`), landing Istio at **2-3**, not *"<2"*. Applying the audit's own best case
  still yields **10-15 always-on**.
- The "2 vCPU buffer against the 12 cap" double-counts the buffer that `variables.tf:29` already
  spent: the existing 10/12 commitment *is* the 2-vCPU buffer, and 8 of that 10 is the only node.

Per debate law §3, an argument without a source is `UNPROVEN`, and this one is contradicted by the
source it relies on.

### 6.3 It is internally inconsistent, and its own scope destroys the evidence it promises

The counter-proposal's headline deliverable is *"unified LLM evidence (60 rows)"*
(`debate-audit.md:86`). Its scope line for the same phases states *"no model serving"*
(`debate-audit.md:87`).

Those cannot both hold. **21 of the 60 LLM rows are pinned to model-serving, agent or llm-track
GitOps artifacts** — `platform/inference/model-server.yaml`, `platform/llm/ab-testing.yaml`,
`platform/agents/*` (counted from `_phase2_rubric_items.py`). The existing LLM evidence corpus is
built on live serving measurements: cold-start / warm-start / TTFT captures against a running
`InferenceService`
(`docs/phase2/evidence/llm/LLM-c-i-t-h-th-ng-ch-warm-up-…md:15`). Delivering 60 LLM rows without
model serving is not possible.

Two further inconsistencies in the same block: line 84 deploys Argo Rollouts in P0-P7 while line 87
excludes *"Argo Rollouts canary (Triton only)"* and line 93 places Triton in the deferred phase; and
line 80 upgrades KServe to 0.18 in P0-P7 while line 87 declares "no model serving" — an upgrade
with nothing to serve.

Its points arithmetic is also wrong in both directions: *"60 rows + 19 rows = 79 points"*
(`debate-audit.md:86`) conflates rows with points and uses a mini row count of 19. Measured (§2.4,
§2.5): LLM = 60 rows / **100 points**, mini = **44 rows / 100 points**. The counter-proposal's real
ceiling would be 200 of 300 — if it could serve a model, which per above it cannot.

### 6.4 It silently reopens three locked decisions without declaring `BREAKS-LOCK`

This is the procedural ground, and under debate law it is dispositive. `rule://arena-debate` §5
requires any seat needing to contradict a locked decision to say so explicitly; §6 states the
Arbiter *"may not lift a lock."* The counter-proposal contradicts three, and files no declaration:

| Lock | Text | How the counter-proposal contradicts it |
|---|---|---|
| **#3** (`plan.md:38`) | *"GCP quota target 48 vCPU, locked as the planning baseline … 48 is the requirement, not a stretch goal"* | Treats the grant as a contingency to route around and sets a *lower* contingent bar of ≥24 (`debate-audit.md:91`) |
| **#5** (`plan.md:40`) | *"Kubeflow Pipelines + Ray + MLflow + KServe/Triton for the ML track"* — matching rubric wording verbatim | Defers all four past the credit window (`debate-audit.md:90-93`) |
| **#1b** (`plan.md:36`) | *"Scope is all three rubrics … 161 rows / 300 points"* | Ships 2 of 3 tracks, explicitly accepting *"if quota is never granted, LLM evidence is complete"* (`debate-audit.md:105`) |

The context foundation states these are *"the planning baseline"*
(`debate-context-foundation.md:23`). A counter-proposal whose entire premise is that the quota
target may never be met is a proposal to lift lock #3. That is the human's decision, not a seat's,
and it was not requested.

### 6.5 What is adopted from the counter-proposal

Rejecting the restructuring does not mean rejecting everything in it. Three of its acceptance
criteria are compatible with the original and are adopted as G0/P1 tightenings, none of which
changes scope, phase order, or any lock:

- *"All three ADR amendments (005, 013, 014) are complete and accepted before their phases"*
  (`debate-audit.md:102`) — already P1; now stated as a P1 **exit** criterion rather than a
  deliverable (**R-6**).
- *"a GCP Billing Console snapshot dated 2026-08-31"* and the quota-ticket status (gap 6) — now
  required G0 artifacts (**R-3**).
- Vector 4's observation that CRD-schema rollback escapes the `git revert` + resync boundary
  (**R-5**).

**The original nine-phase proposal stands, unchanged in scope, phase order and gating.**

---

## 7. Changes to the original proposal

Six revisions. All are precision or gating changes. **None changes scope, phase count, phase order,
component coverage, or any locked decision.**

| # | Where | Change | Driver |
|---|---|---|---|
| **R-1** | §3.3 / §10 component row for the Gold Data Mart; Concerns #5 | Upgrade the dbt identification from bare `[INFERENCE]` to **logo-identified** (dbt Labs glyph, Airflow-triggered, terminating at `trino`), and record the explicit fallback: if the glyph is not dbt, P7 runs the same Airflow-daily CronJob issuing the same SQL against Trino without the dbt layer — strictly less Class C work | Invariant 3 |
| **R-2** | P0 spot-pool item | Restate as *"set `spot = true` on the existing secondary pool `node_config` (`gke.tf:108-112`) and raise `secondary_pool_node_count`"* — the pool resource already exists (`gke.tf:96-131`). The external spot-quota gate is unchanged; the internal build cost drops from a pool build to a one-attribute diff | Vector 2, C4 |
| **R-3** | Gate G0 | Add two required recorded artifacts before G0 can branch: (a) a GCP Billing Console snapshot dated at execution start, superseding the stale 2026-08-18 USD 223 figure (`plan.md:126-131`); (b) the quota-increase request ticket id and submission date, per locked decision #3's day-1 submission (`plan.md:38`) | Gap 6, vector 1 |
| **R-4** | P1 acceptance criteria | Add: *Planner -> greps the regenerated matrix's `evidence_path`, `artifact_path`, `validation_command` and `behavioral_assertion` fields for `phase2-data` and for namespace-valued `monitoring` -> returns zero matches.* Guards C22 forward across the purge | C22 residual, invariant 2 |
| **R-5** | §8 Rollback | Record P6 (KServe 0.14.1 → 0.18) as the **one documented exception** to the universal `git revert` + Argo-resync boundary: CRD schema removal is not reversed by a revert, so rollback is restore-from-export using the AC-P6-1 entry artifact. AC-P6-1 itself is unchanged | Vector 4 |
| **R-6** | P1 | Promote the three ADR amendments (005, 013, 014) from P1 deliverables to P1 **exit** criteria, so P3 and P5 cannot open against an unamended ADR | Vector 3; adopted from counter-proposal AC |

### Claim-set changes

- **C4** — narrowed: the *pool* exists (`gke.tf:96-131`); only the `spot` attribute is absent. The
  claim's conclusion (the cluster-hour budget rests on an unbuilt spot capability) is unchanged.
- **C9** — unchanged, now proven by execution: 26 / 18 / 8 / 0.
- **C19** — unchanged, now proven: 60 LLM, 57 ML, 57 `design_only`, 0 mini.
- **C20** — **revised**: the mini rubric is **44 scored rows / 100 points** (47 logical CSV records,
  5 columns with 3 unnamed leading columns, 16 multi-line quoted cells, 1 section-total row, 84
  `wc -l` lines). P1's normalization target is 44 rows into the 19-column schema. Cross-validates
  locked decision 1b: 117 + 44 = 161 rows, 100 + 100 + 100 = 300 points.
- **C8, C22, C23** — unchanged; evidence supplied.
- **C1-C3, C5-C7, C10-C18, C21, C24-C25** — unchanged.

### Locks

All locks in `debate-context-foundation.md:20-27` are preserved. No `BREAKS-LOCK` is declared in
this rebuttal. The rebuttal declines the counter-proposal in part *because* adopting it would
require lifting locks #1b, #3 and #5 without such a declaration.

---

## 8. Unresolved, carried to the Arbiter

1. **The capacity blocker is real and neither seat can clear it.** Gate G0 is a hard stop
   contingent on an external GCP decision. Both the proposal and the counter-proposal are blocked
   by it; the counter-proposal's claim to route around it does not survive §6.1. The Arbiter should
   record this as the plan's single external dependency, not as a dispute between seats.
2. **dbt glyph identification** (§4, invariant 3) remains logo-based, not text-labelled. Bounded by
   R-1's fallback so it cannot mis-scope the plan upward, but not eliminated.
3. **Stale cost baseline.** The USD 223 / 2026-11-06 figures date to 2026-08-18 (`plan.md:126-131`).
   R-3 makes re-measurement a G0 artifact; the number itself cannot be produced from the repository.
4. **Audit summary counting error** (§0): the Final Summary says 16/1/8; the verdict table says
   19/1/5. The table is authoritative and is what this rebuttal answers.

---

## Status

**Status:** DONE

**Summary:** Answered all 25 audit verdicts, 5 attack vectors, 3 broken invariants and 7 evidence
gaps. The single BREAK (C9) is rebutted by executing the path audit the auditor named as the
settling artifact — 26 pinned GitOps paths, 18 live, 8 archived, 0 missing. All 5 UNPROVEN claims
(C8, C19, C20, C22, C23) are settled with new evidence: the target image was cropped and read,
confirming `Gateway / GatewayClass: istio / ClusterIP` with zero `LoadBalancer` tokens image-wide
and all three progressive-delivery mechanisms with their annotations; both rubric CSVs were parsed
(60 LLM + 57 ML + 0 mini; mini = 44 scored rows / 100 points, cross-validating locked decision 1b's
161 rows / 300 points); and all 117 evidence rows were scanned for namespace literals, returning
zero `phase2-data` and zero namespace-valued `monitoring` references. Evidence gaps 1-5 closed,
gap 6 converted to a G0 artifact, gap 7 narrowed to a documented KServe configuration flag
(`disableIstioVirtualHost`). Vectors 1, 4 and 5 accepted with mitigations; vector 2 accepted on its
external gate and disputed on its internal cost (the second node pool already exists at
`gke.tf:96-131` — the change is `spot = true`, not a pool build); vector 3 agreed as already-design.
The counter-proposal is **rejected and the original defended**, on four independent grounds:
deferring the ML track removes 0 vCPU from the always-on floor because every ML group is already
windowed (`plan.md:96,101`); its "8-10 vCPU always-on" figure is contradicted by the table it cites
(retained groups sum to 13-18, `plan.md:88-92`); it is internally inconsistent and its own "no model
serving" scope forfeits the 21 of 60 LLM rows pinned to serving artifacts that it promises to
deliver; and it silently reopens locked decisions #1b, #3 and #5 without a `BREAKS-LOCK`
declaration, which `rule://arena-debate` §5-6 forbids. Six revisions issued (R-1 to R-6), all
precision or gating; one claim revised (C20), one narrowed (C4). Scope, phase count, phase order and
component coverage unchanged.

**Concerns/Blockers:**

1. **BLOCKER (external, unchanged) — GCP `CPUS_ALL_REGIONS` = 12.** Sharpened against the
   proposer's own interest: schedulable cluster capacity is **8 vCPU**, not 12, because the
   `e2-medium` evidence VM is not a node (`variables.tf:29,55-58`). The always-on floor is 12-16
   (`plan.md:103`). Gate G0 is a hard stop. Neither the proposal nor the counter-proposal clears it.
2. **BLOCKER (external) — spot quota.** Genuine second gate. Internal build cost is now hours, not
   days (R-2), but the GCP response time is outside the plan.
3. **CONCERN — evidence purge (locked decision #1).** Accepted; bounded by the fact that all 117
   rows retain populated `validation_command` / `behavioral_assertion` / `evidence_path`, making
   regeneration a re-run of recorded contracts rather than a re-design.
4. **CONCERN — dbt glyph is logo-identified, not text-labelled.** Bounded by R-1's
   scope-non-increasing fallback.
5. **CONCERN — cost baseline is 13 days stale.** Converted to a required G0 artifact (R-3); not
   derivable from the repository.
6. **NOTE for the Arbiter — the audit's Final Summary verdict counts (16/1/8) contradict its own
   verdict table (19 PASS / 1 BREAK / 5 UNPROVEN).** The table is authoritative and is what this
   rebuttal answers.

**Rebuttal report path:**
`/home/pearspringmind/Studying/FSDS/Financial-Distress-Data/plans/260831-1644-rebuild-target-mlops-architecture/reports/debate-rebuttal.md`
