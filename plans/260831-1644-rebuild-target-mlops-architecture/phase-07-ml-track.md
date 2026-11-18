---
phase: 7
title: "Phase 7: ML pipeline, Kaggle experiments and conditional LoRA"
status: pending
priority: P1
effort: "Re-estimate from unfinished ACs after P0 gates; historical baseline 14-20 d graded core + 2-3 d Kaggle lane + 1 d LoRA gate (+1-2 d only on PROCEED)"
dependencies: ["phase-04-data-plane.md", "phase-05-cdc-streaming.md", "phase-06-platform.md"]
owns: ["src/ml/pipelines/", "src/ml/mlflow*", "src/ml/promotion_gate.py", "src/ml/data_versioning.py", "src/ml/experiments/", "scripts/kaggle/", "notebooks/ml-*.ipynb", "platform/kubeflow/", "platform/tracking/", "platform/serving/model-canary-isvc.yaml", "dags/drift_check.py", "dags/retrain_trigger.py"]
---

# Phase 7: ML pipeline, Kaggle experiments and conditional LoRA

## Revision 2026-09-10 — no-additional-spend compute, bounded Kaggle lane, conditional LoRA gate

Three accepted session decisions land in this phase. Where an older sentence in this file disagreed
with them it was **rewritten in place**; there is no override appendix, and no acceptance criterion
was deleted.

1. **Zero additional monetary spend.** No paid SKU, no rented GPU, no paid inference route, no paid
   Kaggle tier, and no cloud apply that is not bounded to zero spend. Free credit is *not*
   permission to spend it: P0's `G1-spend` and `G2-window` gates own the ledger
   (`phase-00-gates.md:29-30`), and `reports/gate-decisions.md` is a **dated historical
   observation, not authority to spend** (`plan.md:169-170`). Where capacity is unverified the
   affected live AC records `blocked/unverified`; local ML work continues
   (`plan.md:105-107`). A step that can only be executed by spending money is **BLOCKED and
   escalated**, never quietly downgraded to something cheaper that proves less.
2. **GPU-class experiments run as bounded Kaggle kernels through the Kaggle MCP tools.** GCP
   `GPUS_ALL_REGIONS` is limit **0**, usage 0 (`reports/gate-decisions.md:38`), and all five quota
   preferences this project filed returned `NOT_ENOUGH_USAGE_HISTORY`
   (`reports/gate-decisions.md:224-233`) — a free cloud GPU does not exist for this project. Kaggle
   is therefore the only zero-spend accelerator available. It is an **experiment lane and nothing
   else**: see §Bounded Kaggle GPU experiment lane for the explicit non-substitution list.
3. **Fine-tuning is a decision gate, not a scheduled task.** This plan schedules **no** training
   run beyond the graded training pipeline. A LoRA attempt requires six preconditions to hold, and a
   documented **STOP** is a successful outcome of that gate. See §Conditional LoRA decision gate.

**What did not change.** Every graded surface is retained verbatim: Feast-mediated training-data
retrieval (ML 22), notebook↔pipeline step parity (ML 23), genuine distributed training (ML 24),
incremental data versioning (ML 26), the MLflow Model Registry (ML 25), the canary A/B rollout and
the two-version dashboard (ML 51-52), the drift DAG plus Kubeflow retrain trigger (ML 49-50) and
the KNative Eventing drift path (ML 34). All 19 rubric rows this phase owns keep their `rubric_id`s,
their points and their `AC-P7-RUBRIC-*` citations. Architecture-image fidelity is **not** an
acceptance criterion: the 83-component image is a historical reference, rubric rows are the
requirement (`plan.md:33`, `plan.md:138`), and non-rubric components — Triton included — are reused
only when already working and no-spend, otherwise they need a capability-specific justification
(`plan.md:45-52`).

**Measured 2026-09-10** against `docs/rubric-matrix-unified.csv`: of the 19 rows whose
`owning_phase` is `P7`, **zero** name a GPU, fine-tuning, LoRA or any training beyond the training
pipeline itself (queried across `requirement`, `deliverables` and `proof`). The Kaggle lane and the
LoRA gate therefore cannot put a rubric point at risk — and cannot be used to claim one either.

### Master alignment (2026-09-10 master rewrite)

| Master contract | How this phase satisfies it |
|---|---|
| `EXT-KAGGLE` (`plan.md:147`) — accept a `COMPLETE` job, validate downloaded outputs, manifest/hashes/per-case metrics/replay inputs, no secret disclosure | AC-P7-16…21 |
| `EXT-FT` (`plan.md:148`) — eligibility gate, documented defer or paired narrow experiment, no trained-adapter/Groq compatibility assumed | AC-P7-23, AC-P7-24 |
| `EXT-COST` (`plan.md:146`) — zero paid routes, depleted resources fail closed | AC-P7-25 |
| Kaggle ledger row (`plan.md:40`) — bounded GPU batch, not hosting, not a cloud-IaC substitute, not a replacement for graded KFP/distributed training | §Bounded Kaggle GPU experiment lane, AC-P7-22 |
| Fine-tuning ledger row (`plan.md:41`) — conditional, after baseline and licensed dataset; defer is honest; no automatic LoRA/QLoRA/full training/RLHF/DPO | §Conditional LoRA decision gate |
| Scheduling boundary (`plan.md:98-99`) — local notebooks and Kaggle preparation may run before P6 live evidence | steps 3, 6, 12 and 13 are local-capable; steps 1, 4, 5, 7-9 and 11 require an approved window |
| Verification surface (`plan.md:152-155`) | code changes in this phase run `.venv/bin/python scripts/run_lakehouse_quality_gates.py`; every command this file introduces is authored here before it is ever reported as run |
| P0 `G6-Kaggle` / `AC-P0-KAGGLE` (`phase-00-gates.md:34,68`) — MCP access, GPU quota, private dataset and export policy verified **without pushing an unreviewed notebook** (`phase-00-gates.md:56`) | this phase owns compilation and artifact checks; §Pre-push audit is the mechanism |

## Overview

Largest phase, and the one that closes the biggest gap: **all 57 ML rubric rows are currently
`design_only`** — none has ever executed. This phase turns the ML track from a design document into
a running system. **Cost: +3-4 vCPU inside an explicit P0 `G2-window`, no always-on floor, and 0
additional monetary spend.** Where the window cannot be opened at zero spend, the cluster-bound ACs
record `blocked/unverified` and the local ACs still land.

ADR-006 (MLflow promotion) and ADR-014 (distributed training) must **match the implementation
actually selected for their graded capability**, reconciled by content and ID rather than newly
invented (`phase-03-contracts-rubric.md:38-40`). P3 also carries the new decisions for the Kaggle
artifact bridge and conditional fine-tuning (`phase-03-contracts-rubric.md:45-46`), which this file
is the implementation contract for.

## Requirements

- Functional:
  - KFP, KubeRay, RayCluster and MLflow all `Healthy`.
  - A **Jupyter notebook** pulls features from the offline store through Feast and trains a model
    (ML 22).
  - A training **pipeline** reproduces the notebook with **the same number of steps** (ML 23).
  - The train step uses **distributed training** (ML 24); the MLflow `run_id` exists before the Ray
    job is submitted, and Ray reports per-epoch and per-worker metrics into that run.
  - Model weights and hyper-parameters land in the MLflow **Model Registry** (ML 25).
  - Each training pull **versions the data incrementally** (ML 26).
  - The promotion gate hard-fails when champion and candidate were scored on different snapshots.
  - A canary A/B rollout steps 10 % → 25 % → 50 % on the **existing serving runtime** (ML 51) with
    a **two-version monitoring dashboard** (ML 52). The graded capability is canary A/B plus the
    dual-version dashboard, not a specific server product; Triton is used only if an existing
    instance is reused at no spend.
  - An Airflow drift DAG pulls from the offline store, compares against ground truth, pushes through
    PushGateway (ML 49) and **triggers retrain by calling the Kubeflow API** (ML 50).
  - The real-time drift-detection Web API uses **KNative Eventing with KServe** (ML 34).
  - Every GPU-class experiment runs as a **bounded Kaggle kernel** driven through the Kaggle MCP
    tools, is self-contained and resumable, and returns results as a **downloaded artifact bundle
    with a SHA-256 manifest** — never as an inbound connection to this project.
  - A Kaggle result is accepted only when `kaggle_kernel_status` reports `COMPLETE` **and** the
    downloaded output passes artifact validation: expected filenames present, per-file SHA-256
    match, per-example metric rows present, and every in-kernel invariant logged as passed.
  - Fine-tuning is gated, not scheduled: `src/ml/experiments/lora_gate.py` emits
    `PROCEED` / `DEFER` / `STOP` from six predeclared preconditions, and **`STOP` is a pass**.
- Non-functional: `holdout-v1` (frozen in P4, pinned to a knowledge-time cutoff) is the only allowed
  evaluation snapshot; all training is windowed.
- Constraints (2026-09-10 decisions, binding on every step below):
  - **No additional monetary spend.** No paid GPU, no paid inference route, no paid tier, no new
    billable SKU. A step that needs money is recorded `BLOCKED` with its escalation, not softened.
  - **No assumed free capacity and no assumed credentials.** Kaggle MCP authentication, remaining
    GPU quota and internet-enabled-kernel availability are **measured** in a preflight step and
    recorded with timestamps. If any is absent, the lane is skipped and the phase still exits on its
    graded criteria.
  - **No inbound network path into a Kaggle kernel**, and **no Kaggle API credential inside a
    kernel** — a running kernel has none (rule §2), so `kaggle kernels output …` from inside a
    kernel is not a fallback.
  - Kaggle is **not** a substitute for KFP orchestration, for the cluster, or for serving. Full
    fine-tuning, RLHF and DPO are out of scope for this phase at any budget.

## Architecture

```
Iceberg Gold @ knowledge-time cutoff
        │
        ▼
 Jupyter notebook  ──(same step count)──►  KFP pipeline
        │                                       │
        │                            step 1: log MLflow run_id
        │                            step 2: version the data pull (incremental)
        │                            step 3: submit Ray distributed training → that run_id
        │                                       │
        │                              MLflow artifact store (MinIO)
        │                              MLflow Model Registry
        │                                       │
        │                            promotion_gate.py — holdout-v1 equality
        │                                       │
        ▼                                       ▼
   drift DAG (Airflow)         InferenceService, existing runtime (ns: kserve)
   offline store vs ground truth    canary 10 → 25 → 50 %
        │  PushGateway                          │
        └──► Kubeflow API ──► retrain run       └──► two-version Grafana dashboard

   drift-api (real-time)  ──  KNative Eventing trigger ──► KServe

   ── no-additional-spend experiment side-lane (never on the serving path) ──

   src/ml/experiments/kaggle_job.py ──build──► self-contained kernel script + metadata
        │                                            │ prepush_audit.py (blocking)
        │                                            ▼
        │                                     kaggle_kernel_push (MCP; stdout scanned)
        │                                            ▼
        │                          Kaggle GPU kernel — no credentials, no inbound port
        │                          /kaggle/working/<arm>/ + _DONE_<arm> + sha256
        │                                            │ kaggle_kernel_status → COMPLETE
        │                                            │ kaggle_kernel_output (retry on 30 s timeout)
        ▼                                            ▼
   run-bundle validator  ◄────────── downloaded bundle (metrics.jsonl, manifest.json, log)
        │ checksums + invariants + per-example rows + redaction
        ▼
   MLflow run tagged compute_source=kaggle, serving=blocked  (imported locally; MLflow stays
   in-cluster and is never exposed to the internet)
```

### Novel ideas (ML 57, ML 58)

- **Idea 1 — measured restatement leakage.** Using the P4 multi-vintage generator and the P2
  knowledge-time guard, report holdout AUC on latest-vintage features minus AUC on as-known
  features. The gap is the quantified proof that the naive pipeline leaks. The guard **fails** on
  the seeded restatement and passes with the vintage filter.
- **Idea 2 — cost-governed reproducibility manifest.** `src/ml/reproducibility_manifest.py` already
  exists and carries exactly five fields — `snapshot_id`, `source_sha`, `image_digest`,
  `environment_digest`, `data_version` (`src/ml/reproducibility_manifest.py:62-66`). Bind it to the
  live run **and** extend it with the compute-attribution fields the cost claim actually needs:
  `compute_source` (`gke` | `kaggle` | `local`), `compute_seconds`, `accelerator` and
  `marginal_cost_usd` — which is `0.00` for the Kaggle lane and for work inside an approved
  zero-spend window, and must be *justified per run* rather than assumed. Every promotion then
  carries the data snapshot tag, the code SHA, the container digest, the measured cluster-hour cost
  **and** the measured zero-spend GPU seconds. `build_manifest` must fail closed when a field is
  absent (`src/ml/reproducibility_manifest.py:78-96` currently validates only `snapshot_id`).

## Bounded Kaggle GPU experiment lane (no additional spend)

Law of record: [`rule://kaggle-mcp-experiments`](rule://kaggle-mcp-experiments). Its governing
principle — *one push per fully audited script; never use Kaggle as a syntax checker* — is adopted
as an acceptance criterion here (AC-P7-17, AC-P7-18), not as advice.

### What the lane is, and the five things it is not

| Kaggle **may** | Kaggle **may not** |
|---|---|
| Run a bounded GPU batch experiment (hyper-parameter arm sweep, embedding extraction, a single LoRA arm if the gate returns `PROCEED`) | **Substitute for KFP.** Pipeline definition, step parity (ML 23) and the retrain trigger (ML 50) are cluster-side and stay there |
| Produce artifacts that are downloaded, validated and imported into MLflow | **Substitute for cloud evidence.** GKE/Argo/Istio/Terraform evidence remains a cluster artifact; a Kaggle log never stands in for it |
| Report metrics that inform a decision | **Substitute for serving.** No `InferenceService`, no drift API, no endpoint of any kind lives on Kaggle |
| Hold private inputs as a **private Kaggle dataset** or a declared `kernel_sources` mount | **Substitute for distributed training evidence (ML 24).** Ray-on-cluster per-worker metrics in the MLflow run are the proof; a Kaggle kernel is not |
| Be skipped entirely with no graded consequence | **Hold any credential, secret, tunnel, reverse proxy or public URL.** There is no 24/7 public URL anywhere in this project |

### Preflight — measured, never assumed

Before any kernel is designed, `docs/evidence/ml/kaggle-preflight.md` records, with timestamps:
MCP tool reachability and authentication status; remaining GPU quota for the account; whether
internet-enabled kernels are permitted (needed whenever the kernel pip-installs pinned versions —
rule §2); and the resolved versions of every pinned dependency. `pyproject.toml:10-64` declares no
`torch`, `transformers`, `peft`, `mlflow` or `ray` at all, so **every version used is resolved and
recorded at execution time, never guessed**, and a pinned API is verified against the pinned version
rather than against memory (rule §3).

If preflight fails on any line, the file records the negative result, the lane is skipped, and
AC-P7-1…14 remain the phase's exit condition. Nothing graded regresses.

### Kernel contract

| Rule | Why (rule §2/§3) |
|---|---|
| Self-contained script; helpers **copied in**, never imported from another kernel | `kernel_sources` mount *output files only*, never source code |
| Locate every mounted input by filename (`Path("/kaggle/input").rglob("<name>")`) | Kernel slugs change on rename; filenames survive |
| Every reused artifact pinned by expected SHA-256, fail-closed on mismatch | Makes cross-run comparisons exact instead of approximately equal |
| Work partitioned into arms; each arm writes `_DONE_<arm>`; completed arms are skipped on re-push | A monolithic kernel hits the duration cap and is killed with exit 137 |
| Output directories created before any `np.save`/`open` write | A missing directory otherwise surfaces only after the expensive stage |
| `json.dump(..., default=<numpy converter>)`; integer accumulations cast to `int` | NumPy scalars are not JSON-serialisable; `uint8` accumulation overflows |
| Invariants asserted **inside** the kernel (row counts, artifact hashes, parity at the null point, liveness of trained parameters) | A `COMPLETE` kernel proves execution, never correctness (rule §4) |
| `enable_internet: true` whenever the kernel installs pinned versions or fetches an upstream archive | Otherwise the install fails at runtime |
| Zero credentials in source, metadata or logs; private inputs arrive as a private dataset or a declared `kernel_sources` slug; logs pass a redaction check before storage | A kernel has no Kaggle API credentials, and evidence is published |

### Pre-push audit — blocking, and it must actually run

`scripts/kaggle/prepush_audit.py` exits non-zero unless all of the following pass, and it is the
only sanctioned path to `kaggle_kernel_push`:

1. `python -m py_compile <kernel>.py`.
2. AST check: no duplicated, orphaned or misindented top-level `def`/`class`.
3. AST check: every call site of a copied helper matches that helper's arity in *this* file — the
   copy/paste arity drift that cost a whole run (rule §3).
4. AST check: every name used at runtime is imported at module top level (`subprocess`, `zipfile`,
   `time` are the usual omissions).
5. AST check: every write path's parent directory is created before the write; every `json.dump`
   has a `default=` converter.
6. Metadata check: `id` slug is consistent with the slug Kaggle derives from `title`; every
   `kernel_sources` slug resolves; `keywords` is `[]`; `enable_internet` matches whether the script
   installs anything.
7. **Executed** CPU smoke run of the kernel's `--smoke` path on a tiny fixture. If `numpy`/`torch`
   are missing locally the smoke run **fails closed**; it may never report `OK (skipped=N)` as a
   pass, because a skip-heavy local run is not verification (rule §4).

`kaggle_kernel_push` returns `returncode: 0` while silently dropping invalid metadata, so its stdout
is captured and scanned; `not valid kernel sources`, `not valid tags` or
`kernel title does not resolve to the specified id` fails the push record. A later `id`-vs-slug
disagreement returns `409 Conflict … SaveKernel`, so the fix is always to set `id` to the slug
Kaggle really created — before the next run, never after.

### Acceptance of a result

`kaggle_kernel_status` is the only completion signal; results are read only at `COMPLETE`. On
`ERROR`, the output is downloaded and `<kernel>.log` holds the traceback — the public code URL
returns HTTP 404 without authentication and is never fetched as a substitute. A
`kaggle_kernel_output` call that exceeds the 30 s MCP timeout is **re-issued identically** and is
never recorded as "the run produced nothing".

`scripts/kaggle/validate_bundle.py` then requires: every expected filename present in the
*downloaded* listing (a kernel's output does not reliably contain everything written under
`/kaggle/working`); every per-file SHA-256 equal to `manifest.json`; `metrics.jsonl` carrying
per-example rows plus their hashes so paired statistics and bootstrap intervals can be computed
later without re-running; every in-kernel invariant logged as passed; and the recorded resolved
dependency versions matching the pinned ones. Only then is the bundle imported as an MLflow run
tagged `compute_source=kaggle`, `serving=blocked`. `DataVersion.source`
(`src/ml/data_versioning.py:50-76`) carries `kaggle` for any input the kernel produced, so the
incremental-versioning chain (ML 26) stays intact across the lane boundary.

### Why a bundle bridge and not the obvious alternatives

| Rejected | Reason |
|---|---|
| Kernel logs metrics directly to MLflow over the internet | Requires a persistent public MLflow endpoint — a 24/7 public URL, which is excluded, and an inbound path into the cluster |
| Reverse tunnel / ngrok / port-forward into the kernel | Same exclusion, plus it makes the experiment irreproducible |
| Kernel shells out to the `kaggle` CLI to fetch a prior run's artifacts | A running kernel has no Kaggle API credentials (rule §2); declare `kernel_sources` instead |
| Kernel pushes to the model registry | Registry writes are promotion events and stay cluster-side behind `promotion_gate.py` |
| Paid GPU or paid object storage to simplify the handoff | Violates decision 1 (zero additional spend) |

## Conditional LoRA decision gate

`src/ml/experiments/lora_gate.py` is a **decision procedure, not a training job**. It runs, emits
`PROCEED` / `DEFER` / `STOP`, writes `docs/evidence/ml/lora-gate-decision.md`, and exits 0 in all
three cases. A negative decision with published evidence is the *expected* outcome and a passing
one; a fabricated "fine-tuning completed" is not available at any budget.

### The six preconditions — all must hold for `PROCEED`

| # | Precondition | Evidence required | Owner of the evidence |
|---|---|---|---|
| 1 | A **prompt/RAG baseline** for the same task exists and is published | the `split: "holdout"` block of `docs/evidence/llm/baseline-<dataset_revision>.json` — `metric_name`, `value`, `ci_low`/`ci_high` (bootstrap 95 %), `n`, `dataset_revision`, `provider_id`, `model_id`, `prompt_revision`, `corpus_revision`, `harness_revision`, `captured_ts`; read-only, never regenerated here | **P8** publishes (`src/llm`, `src/agents`); P11 owns the harness/corpus behind it |
| 2 | A **curated dataset** exists whose licence permits this use | dataset revision id, row count, licence identifier and its source, curation procedure | P7, from P2/P4 grain |
| 3 | A **leakage-free holdout** exists | disjoint from training data **by record id and by knowledge-time cutoff**, proved by an executed check, not asserted | **P11** harness + P4 vintage data |
| 4 | The target behaviour is **narrow and named** (e.g. one output format or one refusal behaviour), not "better answers" | one-sentence behaviour statement plus the failing baseline examples that motivate it | P7 |
| 5 | Metric and **minimum gain are predeclared before the run** | metric id, threshold, decision rule, timestamp preceding the push record | P7 |
| 6 | A **zero-spend serve path for the adapter is verified** against P8's real self-hosted custom model server — not against an assumption | (a) the adapter's base model **equals** that server's base model, (b) the adapter **converts** to the server's weight format, (c) the converted weights fit a **no-spend serving window** on already-granted resources | **P8** (`src/llm/model_server.py:3-9`) |

Precondition 6 is the binding one, and it is decided against a **named real server**. Groq is a
hosted API and cannot accept a custom adapter, so *adapter-on-Groq is serve-compat `FAIL` by
construction* — but that is not a blanket `STOP`, because P8 retains a **self-hosted
OpenAI-compatible custom model server** (`src/llm/model_server.py:3-9`, llama.cpp behind KServe)
because rubric LLM-3 grades a custom model server, and that lane can load local weights.
Serve-compat **PASSES only if** 6(a), 6(b) and 6(c) all hold; any one failing returns `STOP`, which
remains a valid pass with prompt/RAG as the delivered behaviour. P7 **cites** that lane and does
not define its manifests, runtime or weights — P8 owns them.

Preconditions 1, 3 and 6 are **subgates of `lora_gate.py`, not whole-phase dependencies** (parent
ruling, 2026-09-10). They block the gate only. Steps 1-12 and AC-P7-1…22 never wait on them, so no
cycle enters the phase graph. When a subgate's artifact does not exist yet the gate returns
`DEFER`, which is a pass.

### If and only if `PROCEED`: the bounded arm

One Kaggle arm, LoRA only, through the same lane and the same validation. Grounded in the official
PEFT documentation (`https://huggingface.co/docs/peft/main/en/package_reference/lora`,
`https://huggingface.co/docs/peft/main/en/quicktour`), read 2026-09-10:

- `LoraConfig(r=…, lora_alpha=…, target_modules=[…], lora_dropout=…, bias="none", modules_to_save=[…])`
  then `get_peft_model(model, config)`; `print_trainable_parameters()` is logged as the
  parameter-efficiency record. Default initialisation is a no-op (Kaiming-uniform `A`, zeros `B`),
  so **step-0 output parity with the base model is an in-kernel invariant** (rule §4) and
  `init_lora_weights=False` is debug-only and forbidden here.
- `target_modules` is declared explicitly (attention projections) or as `"all-linear"` for
  QLoRA-style coverage; the choice is recorded, not defaulted silently.
- `peft_model.save_pretrained(dir)` writes **only** `adapter_config.json` and
  `adapter_model.safetensors` — megabytes, not gigabytes — which is exactly why the artifact bundle
  can cross the Kaggle boundary at zero cost. Both files are hashed into `manifest.json`.
- Serving loads the adapter through **P8's self-hosted custom model server**, never through a hosted
  API: `PeftModel.from_pretrained(base_model, dir)` where the runtime is PEFT-aware, or the merged
  weights where the server consumes a converted single-file format — merging removes the extra
  inference latency but produces full-size weights, which is precisely what precondition 6(b) and
  6(c) decide. Which of the two applies is recorded, never assumed.
- No `push_to_hub`: nothing is published to a third party from this project.

**Explicitly excluded, at any budget:** full fine-tuning, RLHF, DPO, any preference-optimisation
run, multi-arm training sweeps, and continued pretraining. Only one narrow LoRA arm is reachable
from this gate.

### Outcomes

| Outcome | When | Required artifact | Effect on the phase |
|---|---|---|---|
| `STOP` | A precondition is *false* — serve-compat fails 6(a)/(b)/(c) (adapter-on-Groq always does), the licence forbids the use, the holdout leaks | decision record naming the failing precondition and its evidence | **Pass.** No training job created |
| `DEFER` | A precondition's evidence does not exist yet (P8 baseline or P11 holdout absent) | decision record naming the missing artifact and its owner | **Pass.** Re-evaluated if the artifact lands |
| `PROCEED` | All six hold | predeclaration record, then one validated bundle | Adapter registered in MLflow marked `serving=blocked` until precondition 6's path is live; **promoted only if the measured holdout gain meets the predeclared threshold** — otherwise the negative result is published and nothing is promoted |

## Related Code Files

- Restore from archive: `platform/kubeflow/` (KFP standalone, KubeRay, RayCluster),
  `platform/tracking/` (MLflow + Postgres + MinIO bucket)
- Modify: `src/ml/mlflow_registry.py` — bind to live MLflow; `mlflow` is **proposed** to
  `pyproject.toml` through the shared-dependency integration boundary (`plan.md:124-126`), not
  edited unilaterally
- Modify: `src/ml/pipelines/distributed_training.py` — bind to the selected distributed backend
  (Ray unless P3's ADR-014 reconciliation selects another); `ray[train]` proposed through the same
  dependency boundary
- Modify: `src/ml/data_versioning.py` — incremental version per training pull (ML 26)
- Modify: `src/ml/reproducibility_manifest.py`, `src/ml/ab_router.py`
- Create: `src/ml/promotion_gate.py` — holdout equality assertion
- Create: `notebooks/ml-training.ipynb` (replaces the current stub), `notebooks/ml-eda.ipynb`
- Create: `platform/serving/model-canary-isvc.yaml` with `canaryTrafficPercent` — renamed from
  `triton-isvc.yaml` on 2026-09-10 because the graded capability is canary A/B on the existing
  serving runtime, not a Triton deployment (`plan.md:45-52`)
- Create: `platform/serving/knative-eventing-drift-trigger.yaml` (ML 34)
- Create: `dags/drift_check.py`, `dags/retrain_trigger.py`
- Create: `docs/evidence/ml/leakage-delta.md` (novel idea 1 write-up)
- Create: `src/ml/experiments/kaggle_job.py` — build a self-contained kernel script plus metadata
  (slug-consistent `id`, `enable_internet`, resolved `kernel_sources`) from a job spec
- Create: `src/ml/experiments/run_bundle.py` — write and read the run bundle (`manifest.json` with
  per-file SHA-256, `metrics.jsonl` per-example rows, `_DONE_<arm>` markers) and import it into
  MLflow as a run tagged `compute_source=kaggle`, `serving=blocked`
- Create: `src/ml/experiments/lora_gate.py` — the six preconditions and the
  `PROCEED`/`DEFER`/`STOP` decision record
- Create: `src/ml/experiments/jobs/*.yaml` — job specs (arms, expected artifacts and their hashes,
  pinned dependency versions); kept inside the module so no other phase's `configs/` is touched
- Create: `scripts/kaggle/prepush_audit.py` — the blocking pre-push audit (compile + AST checks +
  executed CPU smoke), the only sanctioned path to `kaggle_kernel_push`
- Create: `scripts/kaggle/validate_bundle.py` — `COMPLETE`-plus-artifact acceptance and redaction
  check
- Create: `docs/evidence/ml/kaggle-preflight.md` (measured capacity/credential state),
  `docs/evidence/ml/lora-gate-decision.md` (the gate outcome, including a `STOP`)
- Modify: `src/ml/reproducibility_manifest.py` — add `compute_source`, `compute_seconds`,
  `accelerator`, `marginal_cost_usd`; fail closed when any is absent

## Implementation Steps

1. **Restore `platform-kubeflow` and `platform-tracking`** (2-3 d) — KFP standalone, KubeRay,
   RayCluster; MLflow with its Postgres and MinIO bucket.
2. **Bind MLflow** (1 d) — `src/ml/mlflow_registry.py` against the live server; verify experiment
   and run creation, and Model Registry write.
3. **Author the notebook** (1-2 d) — pull features through Feast from the offline store at a named
   knowledge-time cutoff; train; evaluate on `holdout-v1`. **Record its step count** — the pipeline
   must match it.
4. **Bind Ray** (2 d) — `src/ml/pipelines/distributed_training.py` to the live cluster; run a toy
   distributed job; confirm per-worker metrics.
5. **KFP pipeline with step parity** (2-3 d) — step 1 logs the MLflow `run_id`; step 2 versions the
   data pull incrementally; step 3 submits the Ray job referencing that `run_id`. Assert the step
   count equals the notebook's.
6. **Promotion gate** (1 d) — hard equality assertion that champion and candidate are both scored at
   `holdout-v1`; `PromotionError` when snapshots differ; promote only when candidate ≥ champion.
7. **Canary + dual dashboard** (1-2 d) — deploy the `InferenceService` on the existing serving
   runtime in `ns: kserve` (reuse a working Triton instance only if it costs nothing to run; do not
   introduce a new server for its logo); step canary traffic 10 → 25 → 50 %; build the Grafana
   dashboard comparing both versions without ground truth (ML 52 explicitly assumes no ground
   truth — monitor drift and traffic).
8. **Drift DAG + Kubeflow retrain trigger** (2-3 d) — Airflow DAG reads the offline store,
   compares against ground truth, pushes metrics through PushGateway, and on breach **calls the
   Kubeflow API** to start a retrain run. Verify a new KFP run appears.
9. **KNative Eventing drift path** (1 d) — a `Trigger` routes drift events to the KServe-backed
   drift API; verify an emitted event produces an invocation.
10. **Novel idea 1 measurement** (1-2 d) — train twice, once on latest-vintage features and once on
    as-known features at the same cutoff; report the holdout AUC delta; confirm the guard fails and
    then passes.
11. **End-to-end** (2 d) — full KFP run; `run_id` before Ray; gate rejects a snapshot mismatch;
    canary steps; drift DAG fires retrain.
12. **Kaggle lane preflight, contract and bridge** (2-3 d) — *measure, never assume*: MCP
    reachability and auth, remaining GPU quota, internet-enabled-kernel availability, resolved
    dependency versions → `docs/evidence/ml/kaggle-preflight.md`. Then implement `kaggle_job.py`,
    `run_bundle.py`, `prepush_audit.py`, `validate_bundle.py`, and take **one deliberately cheap
    single-arm canary kernel** all the way through: prepush audit → push (stdout scanned) → status
    `COMPLETE` → output download (retry on timeout) → bundle validation → MLflow import. Re-push it
    once with one arm already `_DONE_` to prove resume. If preflight fails, publish the negative
    result and skip the lane — no graded criterion depends on it.
13. **Conditional LoRA gate evaluation** (1 d; +1-2 d only on `PROCEED`) — run `lora_gate.py`,
    publish the decision record with per-precondition evidence, and stop there unless all six hold.
    A `PROCEED` authorizes exactly one bounded LoRA arm through step 12's lane, whose adapter is
    registered `serving=blocked` and promoted only if the measured holdout gain meets the gain
    predeclared before the push.

## Success Criteria

- [ ] AC-P7-1: Argo CD → syncs `platform-kubeflow` and `platform-tracking` inside an approved P0
      `G2-window` → KFP, KubeRay, RayCluster and MLflow report `Healthy`; if no zero-spend window
      exists the AC records `blocked/unverified` and is never satisfied by a local-only stand-in
- [ ] AC-P7-2 **(ML 22)**: Data scientist → runs `notebooks/ml-training.ipynb` → pulls features from
      the offline store through Feast and produces a trained model
- [ ] AC-P7-3 **(ML 23)**: Engineer → compares the notebook and the KFP pipeline → **step counts are
      equal** and each step performs the same operation
- [ ] AC-P7-4 **(ML 24)**: KFP pipeline → reaches the train step → training runs distributed across
      more than one Ray worker; per-worker metrics appear in the MLflow run
- [ ] AC-P7-5: KFP pipeline → starts a training run → the MLflow `run_id` exists **before** the Ray
      job is submitted
- [ ] AC-P7-6 **(ML 25)**: Training pipeline → completes → model weights and hyper-parameters are
      retrievable from the MLflow Model Registry by version
- [ ] AC-P7-7 **(ML 26)**: Training pipeline → pulls from Feast twice → the second pull records an
      incremented data version referencing only the delta
- [ ] AC-P7-8: `src/ml/promotion_gate.py` → candidate scored on a different snapshot than champion →
      fails with a hard equality error; promotion blocked
- [ ] AC-P7-9: `src/ml/promotion_gate.py` → both scored at `holdout-v1` → promotes only when
      candidate accuracy ≥ champion
- [ ] AC-P7-10 **(ML 51)**: `InferenceService` on the existing serving runtime → receives a canary
      revision → serves N−1 at 90 % and N at 10 %; the operator steps to 25 % then 50 %. The
      assertion is on canary traffic behaviour, not on which server product answers
- [ ] AC-P7-11 **(ML 52)**: Analyst → opens the Grafana dashboard → sees both model versions
      monitored side by side without ground truth (drift + traffic + latency)
- [ ] AC-P7-12 **(ML 49-50)**: Drift DAG → detects a threshold breach → pushes through PushGateway
      **and calls the Kubeflow API**; a new KFP retrain run is observable
- [ ] AC-P7-13 **(ML 34)**: Event source → emits a drift event → a KNative Eventing `Trigger`
      invokes the KServe-backed drift API; the invocation appears in the trace
- [ ] AC-P7-14 **(ML 57, novel idea 1)**: Engineer → trains on latest-vintage and on as-known
      features at the same cutoff → reports a non-trivial holdout AUC delta; the leakage guard
      **fails** on the seeded restatement and passes with the vintage filter
- [ ] AC-P7-15 **(ML 58, novel idea 2 — amended 2026-09-10)**: Promotion → completes → the
      reproducibility manifest carries the data snapshot tag, code SHA, image digest,
      `environment_digest` **and** the compute-attribution fields `compute_source`,
      `compute_seconds`, `accelerator`, `marginal_cost_usd` — measured cluster-hour cost for cluster
      runs, `0.00` **with its per-run justification** for Kaggle and zero-spend-window runs; the
      manifest build **fails closed** when any field is absent
- [ ] AC-P7-16 **(preflight, no assumed capacity)**: Engineer → runs the Kaggle lane preflight →
      `docs/evidence/ml/kaggle-preflight.md` records measured MCP auth, remaining GPU quota,
      internet-enabled-kernel availability and resolved dependency versions with timestamps; when
      any is unavailable it records the negative result and the phase still exits on AC-P7-1…14
- [ ] AC-P7-17 **(pre-push audit is blocking)**: `scripts/kaggle/prepush_audit.py` → is given a
      kernel with (a) a syntax error, (b) a duplicated top-level `def`, (c) a helper call whose
      arity differs from the copied definition, (d) an `np.save` into a directory never created,
      (e) a `json.dump` of a NumPy scalar with no `default=`, (f) an unresolvable `kernel_sources`
      slug → **exits non-zero on every one, naming the defect**; and when its CPU smoke run skips a
      numeric assertion because `numpy`/`torch` is missing it **fails instead of reporting success**
- [ ] AC-P7-18 **(one push per audited script)**: Engineer → pushes a kernel → the bundle's push
      record proves `prepush_audit` passed **before** `kaggle_kernel_push`, and the captured push
      stdout is scanned: `not valid kernel sources`, `not valid tags` or
      `title does not resolve to the specified id` **fails the push record even though the tool
      returned `returncode: 0`**
- [ ] AC-P7-19 **(`COMPLETE` is not acceptance)**: `scripts/kaggle/validate_bundle.py` → is given a
      `COMPLETE` run whose output is missing an expected artifact / has one SHA-256 mismatch / has
      zero per-example metric rows / logs a failed in-kernel invariant → **rejects each case**;
      accepts only when status is `COMPLETE` and all four hold. A `kaggle_kernel_output` 30 s
      timeout is retried on the identical call and never recorded as an empty result
- [ ] AC-P7-20 **(resume, not restart)**: Operator → re-pushes a partitioned job whose arm 1 already
      wrote `_DONE_arm1` → the kernel skips arm 1, runs only the unfinished arms, and the merged
      bundle covers every arm exactly once
- [ ] AC-P7-21 **(no credentials, no inbound path)**: Auditor → inspects the generated kernel script,
      its metadata and its stored logs → zero API tokens, zero `kaggle` CLI invocations, zero
      tunnel/reverse-proxy/public-URL references, zero tracking URI outside the cluster; every
      non-public input is a private Kaggle dataset or a declared `kernel_sources` mount; the
      redaction check passes before any log is stored as evidence
- [ ] AC-P7-22 **(Kaggle is not a substitute)**: Reviewer → reads the evidence tree → the KFP
      pipeline (AC-P7-3…5), the Ray distributed train step (AC-P7-4), the registry entry (AC-P7-6)
      and the deployed canary (AC-P7-10) are each produced **on the cluster**; no Kaggle
      bundle is the source of any of them, and every Kaggle-derived MLflow run carries
      `compute_source=kaggle` and `serving=blocked`
- [ ] AC-P7-23 **(the gate decides, and STOP passes)**: `src/ml/experiments/lora_gate.py` → runs with
      one precondition unmet → emits `STOP` or `DEFER` naming the failing or missing precondition,
      writes `docs/evidence/ml/lora-gate-decision.md`, **exits 0**, and creates no training job; the
      phase is not failed by a negative decision and no run is reported as trained
- [ ] AC-P7-24 **(a `PROCEED` is narrow and provable)**: gate → emits `PROCEED` only when all six
      preconditions hold with evidence — the **`split: "holdout"`** block of
      `docs/evidence/llm/baseline-<dataset_revision>.json` read read-only from P8; a curated dataset
      with a recorded permitting licence; a holdout disjoint by record id **and** knowledge-time
      cutoff, proved by an executed check against **P11's frozen eval contract**; a named narrow
      behaviour; metric and minimum gain predeclared before the push; and serve-compat verified
      against **P8's self-hosted custom model server** — base model equal, weight format
      convertible, fits a no-spend serving window (**adapter-on-Groq is a `FAIL`, never a `PASS`**).
      On `PROCEED`, the adapter is promoted **only** if the measured holdout gain meets the
      predeclared threshold; otherwise the negative result is published and nothing is promoted
- [ ] AC-P7-25 **(zero additional spend)**: Auditor → reviews every P7 step's evidence → each names
      the free tier or already-granted resource it used, the phase enables **no new billable SKU**,
      and any step that would require payment is recorded `BLOCKED` with its escalation rather than
      silently replaced

## Risk Assessment

**Risk:** Ray cannot allocate enough CPU. Signal: RayCluster pods `Pending`. Mitigation: the
P0 `G0-cloud`/`G2-window` gates size the window before P7 opens; windowed clusters only, no
always-on floor. Response: reduce parallelism to two workers — AC-P7-4 needs *more than one*
worker, not many — and if no zero-spend window exists, record `blocked/unverified` rather than
relabelling a local run as distributed cluster evidence.

**Risk:** distributed training is unjustifiable at real scale (~64 000 statement rows) and a
reviewer notices. Signal: the training set is tiny. Mitigation: train on the **generated** 10-50M-row
corpus, not the 64 000 real rows, and say so explicitly in the write-up. Response: state the scale
honestly; the rubric grades that the mechanism works, and the generator is what makes it meaningful.

**Risk:** the notebook and the pipeline drift apart in step count. Signal: AC-P7-3 fails after a
later edit. Mitigation: assert step parity in a test, not by inspection. Response: fix whichever
side drifted.

**Risk:** MLflow's registry schema conflicts with existing contracts. Signal: registry write fails on
migration. Mitigation: run `mlflow_registry.py` unit tests against the live server before extending.
Response: reset the MLflow database and re-migrate.

**Risk:** the promotion gate rejects valid candidates because the holdout drifted. Signal:
`PromotionError` on an identical snapshot. Mitigation: `holdout-v1` is an immutable Iceberg tag
pinned to a knowledge-time cutoff. Response: restore from the P4 snapshot; by Iceberg semantics this
should be impossible.

**Risk:** the measured leakage delta is near zero and novel idea 1 has no evidence. Signal:
AC-P7-14's AUC gap is within noise. Mitigation: P4 calibrates restatement magnitude and cohort
correlation before this phase. Response: regenerate with stronger magnitudes; a near-zero delta
means the fixture was too mild, not that the leakage is unreal.

**Risk:** no free Kaggle GPU quota when the lane opens. Signal: preflight reports zero remaining GPU
hours or an auth failure. Mitigation: preflight runs **before** any kernel is designed, and the lane
is optional by construction. Response: publish the negative preflight and skip the lane — all 19
graded rows are GPU-free (measured 2026-09-10), so nothing regresses.

**Risk:** a long kernel is killed at Kaggle's duration cap (exit 137) and the run is lost. Signal:
`ERROR` with 137 in `<kernel>.log`. Mitigation: work is partitioned into arms with `_DONE_<arm>`
markers and completed arms are skipped on re-push (rule §2). Response: re-push; the run resumes
instead of restarting.

**Risk:** `kaggle_kernel_push` silently drops invalid metadata and the run fails minutes later on a
missing mount. Signal: `not valid kernel sources` in stdout that nobody read. Mitigation: AC-P7-18
scans the captured stdout and fails the push record. Response: fix the slug or set `id` to the slug
Kaggle really created — a mismatch later returns `409 Conflict … SaveKernel`.

**Risk:** `kaggle_kernel_output` exceeds the 30 s MCP timeout and the result is misread as "no
output". Signal: `Request timeout after 30000ms`. Mitigation: re-issue the identical call; it
typically succeeds. Response: never conclude a run produced nothing from a timeout.

**Risk:** an artifact written under `/kaggle/working` is absent from the downloaded output. Signal:
validation reports a missing expected filename. Mitigation: the downloaded bundle is **listed and
validated before** any cross-run dependency is designed on it; inputs are located by filename via
`rglob`, never by kernel slug directory. Response: re-declare the artifact and re-push once.

**Risk:** a `COMPLETE` kernel is confidently wrong — stale constant, diagnostic statistic used as a
gate, a registered gate omitted (rule §4). Signal: numbers that pass validation but contradict this
file. Mitigation: in-kernel invariant assertions plus a re-audit of the kernel's logic against this
phase file before any number is accepted (AC-P7-19). Response: fix the kernel, re-push once.

**Risk:** dependency versions are guessed rather than verified — `pyproject.toml:10-64` declares no
`torch`, `transformers`, `peft`, `mlflow` or `ray`. Signal: a pinned API behaves differently than
remembered. Mitigation: pins are declared in the job spec, installed with `enable_internet: true`,
verified against the pinned version, and the resolved versions are recorded in the bundle manifest.
Response: fix the call site, not the pin.

**Risk:** the LoRA adapter has nowhere to serve at zero spend, so the whole exercise is unusable.
Signal: precondition 6 fails — base model mismatch, no weight-format conversion, or no no-spend
serving window; adapter-on-Groq fails by construction. Mitigation: precondition 6 is evaluated
against P8's self-hosted custom model server **before** any training, and `STOP` is a pass.
Response: publish the `STOP`; prompt/RAG remains the delivered behaviour.

**Risk:** an attractive but unusable curated dataset (licence unknown or non-permitting), or a
holdout that leaks through restatements. Signal: preconditions 2 or 3 fail. Mitigation: both are
gate preconditions with executed checks, not review items. Response: `STOP`; the negative result is
the artifact.

**Risk:** a `PROCEED` arm's measured gain lands within noise. Signal: gain below the predeclared
threshold. Mitigation: the threshold and decision rule are predeclared before the push, so the
outcome is a decision rather than a negotiation. Response: do not promote; publish the negative
result. This is a valid completion of the gate, not a phase failure.

## Ownership, subgates and shared paths (2026-09-10)

**Ownership added to this phase's frontmatter:** `src/ml/experiments/` and `scripts/kaggle/`. Both
are new paths — a repository-wide grep for `kaggle` on 2026-09-10 returned **no match anywhere**, in
source or in this plan — and P8 confirmed on 2026-09-10 that no P8 file references
`src/ml/experiments/` or `docs/evidence/ml/`. `notebooks/` was **narrowed to
`notebooks/ml-*.ipynb`** in the same revision: master assigns ML notebooks to P7 and LLM notebooks
to P8 (`plan.md:117-118`), and the directory already holds two P8-owned agent notebooks, so
directory-level ownership would have collided.

This phase does **not** touch `src/llm/`, `src/agents/` or the inference/gateway deployment (P8),
`tests/` (P11), or `configs/` (job specs live inside `src/ml/experiments/jobs/`). `pyproject.toml`,
shared tests and docs are **integration boundaries, not P7 property** (`plan.md:124-126`): every
dependency this phase needs (`mlflow`, the distributed backend, and — only on a `PROCEED` — the
kernel-side `torch`/`transformers`/`peft` pins, which live in the kernel and the job spec, not in
the repo's runtime extras) is *proposed* to the owning integrator rather than written directly.

**Subgates, not dependency edges.** The `dependencies:` frontmatter is unchanged (`P4, P5, P6`).
Per the parent's 2026-09-10 ruling, the LoRA gate's cross-phase needs are recorded as **subgates of
`lora_gate.py`** rather than whole-phase edges: the graph stays acyclic and the graded critical path
is untouched.

| Subgate | Consumed artifact (read-only) | Owner | If absent |
|---|---|---|---|
| Precondition 1 | `docs/evidence/llm/baseline-<dataset_revision>.json`, **`split: "holdout"`** block only | **P8** publishes; P11 owns the harness/corpus behind it | `DEFER` |
| Precondition 3 | P11's **frozen eval contract** — dataset revision id plus per-example scoring output | **P11** | `DEFER` |
| Precondition 6 | P8's self-hosted OpenAI-compatible custom model server (`src/llm/model_server.py:3-9`): its base model and weight format | **P8** | `STOP` if verified incompatible, `DEFER` if not yet published |

The holdout block is written once per frozen candidate and is **the only number this gate may
read**; the re-runnable development split is P8/P11 territory and is never read by this gate.

**Shared evidence paths.** `docs/evidence/llm/` is **read-only** to P7. P7 writes only
`docs/evidence/ml/` and is the contributing owner there; **P12 owns the final evidence tree and the
capture runner** (`plan.md:122`), so P7 produces artifacts for capture and never edits P12's final
docs or the runner. P8 confirmed the llm/ml split on 2026-09-10, so no file is co-owned.

**Contracts consumed** (owned elsewhere, referenced here): P2 data/feature grain; P4 multi-vintage
generator, `holdout-v1` Iceberg tag and knowledge-time cutoff; P5 Feast offline snapshot contract;
P8 baseline metrics and any adapter-capable serving runtime; P11 eval datasets and harness.
**Contracts produced here** for others: the run-bundle format (`manifest.json`, `metrics.jsonl`,
`_DONE_<arm>`), the MLflow tags `compute_source` / `serving`, the extended reproducibility-manifest
fields, and the LoRA gate decision record — P12 captures the last two as evidence.

## Source references (read 2026-09-10)

| Source | What it grounds |
|---|---|
| [`rule://kaggle-mcp-experiments`](rule://kaggle-mcp-experiments) §1-§4 | MCP tool behaviour (`kernel_output` timeout, silent metadata drop, `409` slug conflict, `status` as the only completion signal), the execution model (no credentials, output-only `kernel_sources`, filename lookup, exit-137 partitioning), the pre-push checklist, and "`COMPLETE` proves execution, never correctness" |
| `https://huggingface.co/docs/peft/main/en/package_reference/lora` | `LoraConfig` parameters (`r`, `lora_alpha`, `target_modules`, `lora_dropout`, `bias`, `modules_to_save`), default no-op initialisation (Kaiming `A`, zero `B`), `init_lora_weights=False` as debug-only, `target_modules="all-linear"` for QLoRA-style coverage, merging to remove inference latency |
| `https://huggingface.co/docs/peft/main/en/quicktour` | `get_peft_model`, `print_trainable_parameters`, and that `save_pretrained` writes only `adapter_config.json` + `adapter_model.safetensors` (megabytes), loaded back with `PeftModel.from_pretrained(base, dir)` |
| `reports/gate-decisions.md:38`, `:224-233` (dated historical observation, **not** spend authority — `plan.md:169-170`) | `GPUS_ALL_REGIONS` limit 0 and all five quota preferences refused as `NOT_ENOUGH_USAGE_HISTORY`, i.e. no free cloud GPU has ever been granted to this project; P0's new dated ledger supersedes it |
| `docs/rubric-matrix-unified.csv` (queried) | 19 rows own `owning_phase = P7`; none names a GPU, fine-tuning or LoRA |
| `src/ml/reproducibility_manifest.py:62-66`, `:78-96` | the five existing manifest fields and that only `snapshot_id` is validated today |
| `src/ml/data_versioning.py:50-76` | `DataVersion.source` already exists, so `source="kaggle"` needs no schema change |
| `src/ml/mlflow_registry.py:1-34` | MLflow is optional with a JSON fallback, so bundle import must work against either backend |
| `src/ml/pipelines/distributed_training.py:34-71` | `train_local` shard semantics and `submit_kubeflow`'s HTTP payload — the cluster-side path the Kaggle lane must not replace |
| `pyproject.toml:10-64` | no `torch`/`transformers`/`peft`/`mlflow`/`ray` declared → versions are resolved and recorded at execution time, never guessed |
| P8 interface reply (`AgentEvalPlanUpgrade`, 2026-09-10) | the baseline artifact path and field list, that the holdout block is the only gate-readable number, that adapter-on-Groq is serve-compat `FAIL`, and that P8's self-hosted custom model server (`src/llm/model_server.py:3-9`, llama.cpp behind KServe, retained for rubric LLM-3) is the one lane that can load local weights |
| Parent ruling (2026-09-10) | preconditions 1/3/6 are **subgates**, not cyclic whole-phase edges; serve-compat must be verified against P8's chosen real local/custom model serving; Groq Free is not assumed adapter-compatible |

## Rubric Citations (phase-03 R-12 closure, appended 2026-09-05)

Every rubric row this phase owns per `docs/rubric-matrix-unified.csv`'s `owning_phase` column, cited so `scripts/verify_rubric_coverage.py` can resolve ownership to an assertion (R-12). Each line names the row's real `rubric_id`, its stated requirement, and its proof artifact/deliverable — the row's own matrix columns, not invented text. Rows whose capability is not yet implemented are forward specs, matching this file's other `AC-P7-*` entries.

- AC-P7-RUBRIC-1: `ML-a-b-testing-monitoring-dashboard-to-monito` — ml_engineer -> delivers "Setup monitoring dashboard to monitor 2 versions.; Assumption: we also don't have groundtruth to monitor drift here!" -> Capture màn hình thể hiện cách mọi người thực hiện A/B test và dashboard để đánh giá kết quả A/B test (evidence: `docs/platform/evidence/ml/ML-a-b-testing-monitoring-dashboard-to-monito.md`)
- AC-P7-RUBRIC-2: `ML-a-b-testing-when-you-deploy-a-new-model` — ml_engineer -> delivers "A/B Testing — When you deploy a new model, don't replace the old one directly, you should do A/B test, monitor it, and deploy. It's simple,..." -> Capture màn hình thể hiện cách mọi người thực hiện A/B test và dashboard để đánh giá kết quả A/B test (evidence: `docs/platform/evidence/ml/ML-a-b-testing-when-you-deploy-a-new-model.md`)
- AC-P7-RUBRIC-3: `ML-autoscale-autoscale-web-api-k-o-d-li-u-v` — platform_operator -> delivers "Autoscale — Autoscale Web API kéo dữ liệu và drift detection (ví dụ dùng với KEDA để scale theo req)" -> Capture màn hình cách mọi người handle autoscale và demonstrate it worked! (evidence: `docs/platform/evidence/ml/ML-autoscale-autoscale-web-api-k-o-d-li-u-v.md`)
- AC-P7-RUBRIC-4: `ML-autoscale-web-api-cho-drift-detection` — platform_operator -> delivers "Web API cho drift detection" -> Capture màn hình cách mọi người handle autoscale và demonstrate it worked! (evidence: `docs/platform/evidence/ml/ML-autoscale-web-api-cho-drift-detection.md`)
- AC-P7-RUBRIC-5: `ML-ci-cd-cho-real-time-drift-detection-` — platform_operator -> delivers "Cho real-time drift detection Web API (sử dụng KNative Eventing kết hợp với KServe)" -> Capture màn hình từng CI/CD pipeline đã run thành công (evidence: `docs/platform/evidence/ml/ML-ci-cd-cho-real-time-drift-detection-.md`)
- AC-P7-RUBRIC-6: `ML-feature-store-job-ch-u-tr-ch-nhi-m-push-stre` — data_engineer -> delivers "Deploy job chịu trách nhiệm push streaming feature (ở mini-coursework) vào OFFLINE store" -> + Capture màn hình thể hiện các data pipeline và thứ tự các stage trên Airflow; + Capture màn hình thể hiện 2 job đang chạy, và thể hiện out... (evidence: `docs/platform/evidence/ml/ML-feature-store-job-ch-u-tr-ch-nhi-m-push-stre.md`)
- AC-P7-RUBRIC-7: `ML-feature-store-job-online-store-push` — data_engineer -> delivers "Deploy job chịu trách nhiệm push streaming feature (ở mini-coursework) vào ONLINE store" -> + Capture màn hình thể hiện các data pipeline và thứ tự các stage trên Airflow; + Capture màn hình thể hiện 2 job đang chạy, và thể hiện out... (evidence: `docs/platform/evidence/ml/ML-feature-store-job-online-store-push.md`)
- AC-P7-RUBRIC-8: `ML-feature-store-materialize-pipeline-jobs-for-` — data_engineer -> delivers "Feature Store — Build materialize pipeline & jobs for push streaming data into feature stores" -> + Capture màn hình thể hiện các data pipeline và thứ tự các stage trên Airflow; + Capture màn hình thể hiện 2 job đang chạy, và thể hiện out... (evidence: `docs/platform/evidence/ml/ML-feature-store-materialize-pipeline-jobs-for-.md`)
- AC-P7-RUBRIC-9: `ML-ml-jupyter-notebook-to-demonstrat` — ml_engineer -> delivers "ML — Jupyter notebook to demonstrate basic understanding of ML/DL" -> Document các step chính đã làm trong Jupyter notebook (evidence: `docs/platform/evidence/ml/ML-ml-jupyter-notebook-to-demonstrat.md`)
- AC-P7-RUBRIC-10: `ML-ml-pipelines-training-pipeline` — ml_engineer -> delivers "ML Pipelines — Training Pipeline" -> Capture training pipeline đã run thành công + Capture màn hình thể hiện có sử dụng distributed training (evidence: `docs/platform/evidence/ml/ML-ml-pipelines-training-pipeline.md`)
- AC-P7-RUBRIC-11: `ML-ml-pipelines-trong-training-pipeline` — ml_engineer -> delivers "Trong training pipeline, ở step train, thay bằng distributed training, ví dụ nếu mọi người dùng model XGBoost thì có thể coi tutorial này." -> Capture training pipeline đã run thành công + Capture màn hình thể hiện có sử dụng distributed training (evidence: `docs/platform/evidence/ml/ML-ml-pipelines-trong-training-pipeline.md`)
- AC-P7-RUBRIC-12: `ML-novel-ideas-idea-1` — ml_engineer -> delivers "Novel ideas ; (không nhất thiết tự sáng tạo ra cái gì, có thể nghiên cứu dùng thêm các công cụ, hoặc kỹ thuật gì đó không được dạy ở EDAI) —..." -> Document idea + proof it worked! (evidence: `docs/platform/evidence/ml/ML-novel-ideas-idea-1.md`)
- AC-P7-RUBRIC-13: `ML-novel-ideas-idea-2` — ml_engineer -> delivers "Idea 2" -> Document idea + proof it worked! (evidence: `docs/platform/evidence/ml/ML-novel-ideas-idea-2.md`)
- AC-P7-RUBRIC-14: `ML-versioning-m-i-l-n-k-o-d-li-u-t-feast-v-t` — data_engineer -> delivers "Mỗi lần kéo dữ liệu từ Feast về để training, cần version lại DATA theo cơ chế incremental (ví dụ lần train thứ 2 data chỉ có 1 chút thay đổi..." -> Model đã được version và lưu trữ lại + Data tương ứng cũng được version theo cơ chế incremental (evidence: `docs/platform/evidence/ml/ML-versioning-m-i-l-n-k-o-d-li-u-t-feast-v-t.md`)
- AC-P7-RUBRIC-15: `ML-versioning-model-versioning` — ml_engineer -> delivers "Versioning — Model Versioning" -> Model đã được version và lưu trữ lại + Data tương ứng cũng được version theo cơ chế incremental (evidence: `docs/platform/evidence/ml/ML-versioning-model-versioning.md`)
- AC-P7-RUBRIC-16: `ML-web-api-cho-real-time-dri-c-s-d-ng-fastapi-data-validati` — data_engineer -> delivers "Web API cho Real-time Drift Detection — Có sử dụng FastAPI + data validation (với pydantic)" -> Capture màn hình cách mọi người handle rolling update và fall back (evidence: `docs/platform/evidence/ml/ML-web-api-cho-real-time-dri-c-s-d-ng-fastapi-data-validati.md`)
- AC-P7-RUBRIC-17: `ML-web-api-cho-real-time-dri-s-d-ng-async` — data_engineer -> delivers "Sử dụng async" -> Capture màn hình cách mọi người handle rolling update và fall back (evidence: `docs/platform/evidence/ml/ML-web-api-cho-real-time-dri-s-d-ng-async.md`)
- AC-P7-RUBRIC-18: `ML-web-api-k-o-d-li-u-c-s-d-ng-fastapi-data-validati` — data_engineer -> delivers "Web API kéo dữ liệu; (Web API này sẽ dùng để kéo dữ liệu từ Online Feature store dựa trên ID (user_id, hoặc customer_id, etc.), sau đó gửi t..." -> Capture màn hình cách mọi người handle rolling update và fall back (evidence: `docs/platform/evidence/ml/ML-web-api-k-o-d-li-u-c-s-d-ng-fastapi-data-validati.md`)
- AC-P7-RUBRIC-19: `ML-web-api-k-o-d-li-u-s-d-ng-async` — data_engineer -> delivers "Sử dụng async" -> Capture màn hình cách mọi người handle rolling update và fall back (evidence: `docs/platform/evidence/ml/ML-web-api-k-o-d-li-u-s-d-ng-async.md`)

**Rubric-scope note (2026-09-10):** none of the 19 rows above names a GPU, fine-tuning, LoRA or any
training beyond the training pipeline itself. The Kaggle lane (AC-P7-16…22) and the LoRA gate
(AC-P7-23, AC-P7-24) therefore add optional evidence and carry **zero** rubric points; every one of
these 19 rows is earned by AC-P7-1…14 on cluster artifacts, exactly as before this revision.
