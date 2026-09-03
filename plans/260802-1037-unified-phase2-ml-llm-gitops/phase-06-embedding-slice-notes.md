---
title: "Phase 6 embedding slice: deploy a text-embedding server on GKE to unblock phase-04 RAG"
description: "Scoped supplement — one CPU embedding InferenceService on the existing Knative/KServe install, plus the HTTP EmbeddingBackend that calls it. No chat model, no kagent, no gateway."
status: pending
priority: P1
effort: 5h
branch: dev
tags: [phase2, llm-track, rag, embeddings, kserve, knative, gke, gitops, cost]
created: 2026-08-08
---

# Phase 6 — Embedding slice (supplement)

Scoped supplement to `phase-06-deliver-llm-mcp-and-agent-track.md`. That file
stays authoritative for the full phase-06 scope. This file covers **one sliver**:
a text-embedding model server on the already-provisioned GKE cluster, so
`src/llm/rag_pipeline.py::write_vectors` (`src/llm/contracts.py:38`) has a real
embeddings endpoint and phase-04 slice 4B stops being blocked on phase-06.

Verification basis (re-verified live 2026-08-08):

| Claim | Evidence |
|---|---|
| GitOps repo branch is **`master`**, not `main` | `git branch` in `financial-distress-gitops`; Argo apps all use `targetRevision: master` (`argocd/applications/platform-inference.yaml`) |
| Cluster has 0 nodes right now | `kubectl get nodes` → `No resources found`; both pools `RUNNING` at 0 |
| Node pools | `gcloud container node-pools list` → `primary-pool` e2-standard-8, `secondary-pool` e2-standard-4 |
| `make gcp-up` scales **primary-pool only**, to 1 node | `financial-distress-gitops/Makefile:32-36` |
| Installed KServe = **v0.14.1** | `platform/inference/VERSIONS.md:14`; `vendored/05-kserve-cluster-resources.yaml:12` image `kserve/huggingfaceserver:v0.14.1` |
| KServe v0.14.1 has **no `LLMInferenceService` CRD** | full CRD list in `vendored/04-kserve.yaml`: `inferenceservices`, `inferencegraphs`, `servingruntimes`, `clusterservingruntimes`, `trainedmodels`, `localmodelcache(s)`, `localmodelnodegroups`, `localmodelnodes`, `clusterstoragecontainers` — nothing llm-d-related |
| `platform/inference/model-server.yaml` is a rubric-pinned artifact | `docs/platform/rubric-matrix.csv:9`, rubric_id `LLM-a-llm-inference-platform--llm-inference-platform-setup-c`, `artifact_path=platform/inference/model-server.yaml` |
| Argo already reconciles `platform/inference/` recursively | `argocd/applications/platform-inference.yaml` — `path: platform/inference`, `directory.recurse: true`, `exclude: "*.md"`, `automated{prune,selfHeal}`, `ServerSideApply=true` |
| Knative routes through Kourier | `platform/inference/06-config-network-patch.yaml` sets `config-network.ingress-class=kourier...` |
| PGVector column is `vector(384)` | `phase-04-implementation-notes.md:343` |
| `.venv-phase2` has `tenacity 8.5.0` and `requests`, **no `httpx`** | `ls .venv-phase2/lib/python*/site-packages` |
| `src/llm/` contains only `contracts.py` | `ls src/llm/` |
| Public HTTPS already works at `distresslens.duckdns.org` | `phase-03-...md:352` (LE cert verified 2026-08-08) |
| vCPU quota is the binding constraint | `phase-03-...md:344` — project-wide `CPUS_ALL_REGIONS=12`, forced collapse to one e2-standard-8 pool |

---

## 0. Decisions this slice locks

### D-E1 — Serving stack is **HF Text Embeddings Inference (TEI) CPU**, not vLLM-CPU

The user's decision named "vLLM-CPU **or an equivalent OpenAI-compatible
embeddings server**". Taking the second branch, on evidence:

- TEI ships an official prebuilt CPU image (`ghcr.io/huggingface/text-embeddings-inference:cpu-<ver>`)
  and serves an OpenAI-compatible `/v1/embeddings` route natively. Nothing to build.
- vLLM's official published images are CUDA-targeted; the CPU path is a
  separate build (`docker/Dockerfile.cpu`, ECR gallery mirror), is AVX-512
  sensitive, is multi-GB, and its encoder/pooling path on CPU is not the
  combination vLLM tests first. On a single e2-standard-8 node that also hosts
  Argo CD + Knative + Kourier + KServe + ingress + cert-manager, that is a bad
  trade for a 470 MB encoder model.

**Consequence (a YAGNI win): no Dockerfile, no image build, no GHCR push, no CI
workflow for this slice.** The source repo's existing Dockerfiles
(`infra/airflow/Dockerfile`, `infra/flink/Dockerfile`) stay untouched, and no
new one is created.

Non-conflict with phase-06 proper: phase-06's chat model (Qwen2.5, vLLM-CPU or
llama.cpp) is a **different** InferenceService in a different file. Embedding
server = TEI, chat server = vLLM. Two runtimes is correct here, not duplication —
they solve different problems.

Caveat to state in the evidence file: **TEI is licensed HFOIL**, not Apache-2.0.
Fine for coursework; must not be described as OSS.

### D-E2 — New file `platform/inference/embedding-server.yaml`; do **not** touch `model-server.yaml`

`docs/platform/rubric-matrix.csv:9` pins `platform/inference/model-server.yaml` as
the gitops `artifact_path` for `LLM-AC-01-INFERENCE` ("Deploy a LLM inference
platform … + setup custom model", 2 pts). `phase-06-...md:165` also reserves it
for the chat model's `InferenceService`.

Filling `model-server.yaml` with an embedding server would make the row's
artifact assertion pass with an artifact that is not what the row asks for —
exactly the "designed vs executed" dishonesty phase-08's contract forbids
(`phase-06-...md:126-128`). **New path.** The placeholder comment in
`model-server.yaml` stays exactly as-is.

`platform/inference/llm-d-router.yaml` (also reserved, `phase-06-...md:166`) is
likewise not created here — see D-E3.

**This slice claims zero rubric rows.** Its output is an unblocking dependency
for phase-04's `LLM-rag-rag-data-pipeline` row, not evidence for any row itself.

### D-E3 — **No llm-d in this slice.** Expose the Knative Route directly.

Not a preference — a hard version fact. llm-d integrates with KServe through the
`LLMInferenceService` CRD introduced in KServe **0.18**. The cluster runs
**0.14.1**, which does not ship that CRD (verified above). There is no
llm-d-shaped surface to configure.

This also surfaces a **real ADR/reality conflict that must be recorded**:
`docs/platform/adr/adr-004-kserve-018-pin.md:24` pins KServe **0.18**;
`ADR-010:88-93` restores "llm-d router → KServe InferenceService" on that
assumption; phase-03 actually vendored **0.14.1**. See Open Question **QE-1** —
this belongs to phase-06 proper (it affects whether canonical row 2 lands "as
written"), but it is discovered here and must not be silently absorbed.

For a **single** model, llm-d's request-aware multi-model routing buys nothing
anyway. Knative's own Route gives a stable in-cluster host and scale-to-zero.
Adding llm-d later for the chat model does not require changing anything this
slice creates — the embedding ISVC is just another backend.

Trade-off accepted: this slice produces no llm-d evidence. That was never its job.

### D-E4 — `multilingual-e5-small` is 384-dim: **PGVector schema is unchanged**

`intfloat/multilingual-e5-small` outputs **384** dimensions, matching
`embedding vector(384)` at `phase-04-implementation-notes.md:343` and matching
D5's `all-MiniLM-L6-v2`. **No schema change, no migration.**

But same dimensionality ≠ same vector space. Vectors from
`all-MiniLM-L6-v2`, the `DeterministicHashEmbedder`, and `multilingual-e5-small`
are mutually **incomparable**. The existing `UNIQUE (content_hash,
embedding_version)` constraint plus the `embedding_model` column already handles
this correctly — a different backend produces a disjoint row set. **Requirement:
`embedding_version` must change when the backend changes.** Never reuse one.

### D-E5 — e5 prefix contract is mandatory and easy to get silently wrong

`multilingual-e5-*` models are trained with instruction prefixes. Retrieval
quality degrades badly (and silently — no error, just worse neighbours) without
them:

- ingestion / stored chunks → `"passage: " + text`
- retrieval / user queries → `"query: " + text`

The prefix scheme is part of the vector space's identity, so it goes into the
`embedding_version` string and into the registry digest (D-E7). A future change
of prefix scheme is a re-embed, not a config tweak.

Also: e5 outputs are meant to be **L2-normalized** and compared by cosine. TEI
normalizes by default; the HNSW index is already `vector_cosine_ops`
(`phase-04-implementation-notes.md:347`). Consistent — but the backend asserts
`abs(||v|| - 1.0) < 1e-3` on the first vector of each batch rather than trusting it.

### D-E6 — Evidence run reaches the endpoint by `kubectl port-forward`, not a public route

Airflow is platform .nd local (`AGENTS.md` boundary); it is not in GKE. So the
RAG pipeline is a client **outside** the cluster. Two concrete options:

| Option | Verdict |
|---|---|
| Public route on `distresslens.duckdns.org` via ingress-nginx → Kourier | **Rejected for this slice.** Puts an unauthenticated embeddings API on the public internet, and needs an Ingress + auth + a cert SAN — all of which is phase-06's gateway/auth work, which this slice explicitly excludes. |
| `kubectl port-forward -n knative-serving svc/kourier-internal 8080:80`, client sets `Host: <ksvc-host>` | **Chosen.** Zero extra manifests, zero exposure, zero cost, works from the local Airflow/pytest process. |

Client config: `EMBEDDING_ENDPOINT=http://127.0.0.1:8080/v1/embeddings` plus
`EMBEDDING_HOST_HEADER=fd-embeddings.default.svc.cluster.local` (exact value read
from `kubectl get ksvc fd-embeddings -o jsonpath='{.status.url}'`). Knative routes
by `Host`, so omitting the header yields a 404 from Kourier — a first-run trap;
name it in the runbook.

Documented-but-not-built: the public route is a one-Ingress addition later, and
nothing in this slice blocks it.

### D-E7 — Registry metadata is a **config file**, not an implementation

`EmbeddingRegistryService` (`src/llm/contracts.py:42-61`) is abstract-only; no
concrete class exists (`src/llm/` holds only `contracts.py`), and
`ml.rag_chunk` does not exist until phase-04 slice 4A. Implementing
`register_version` here would mean building the registry, the table, and the
hot-swap path — all phase-06/novel-idea scope.

Instead this slice pins the exact tuple that the future `register_version(
model_name, dims, digest)` call will consume, in `configs/embedding-backends.yaml`:

```yaml
backends:
  e5-small-tei:
    model_name: intfloat/multilingual-e5-small
    model_revision: <HF commit sha, pinned at deploy time>
    dims: 384
    prefix_scheme: {passage: "passage: ", query: "query: "}
    normalize: true
    server: {runtime: text-embeddings-inference, image_digest: sha256:<...>}
    embedding_version: e5s-tei-v1
    digest: <sha256 over the canonical JSON of the fields above>
```

`digest` is computed by a helper, not typed by hand, so it is reproducible. Both
the HTTP backend and the future registry impl read this one file — DRY, and the
registry gets its inputs for free when it lands.

---

## 1. Data flow

```
[local process: pytest / airflow task / smoke script]
  src/llm/rag/embedding.py :: TeiHttpEmbedder.embed(texts)
      -> prefix each text with "passage: "  (D-E5)
      -> POST http://127.0.0.1:8080/v1/embeddings
         Host: fd-embeddings.default.svc.cluster.local
         {"input": [...], "model": "intfloat/multilingual-e5-small"}
      |
  [kubectl port-forward] -> svc/kourier-internal (knative-serving)
      -> Knative Route/Ingress (host match)
      -> Knative Activator (if scaled to zero: hold request, scale 0->1)
      -> Revision Pod: TEI container :8080
           model loaded from HF hub into emptyDir cache on cold start
      <- {"data":[{"embedding":[384 floats]},...],"usage":{...}}
      |
  -> assert len == 384, assert ||v|| ~ 1.0
  -> rag_pipeline.write_vectors -> PGVector ml.rag_chunk (phase-04 4B)
```

Failure modes on this path, and where each is handled:

| Failure | Surfaces as | Handling |
|---|---|---|
| port-forward dropped | `ConnectionError` | `tenacity` retry; runbook says re-establish |
| missing `Host` header | Kourier 404 | backend sends it always; smoke test asserts non-404 |
| cold start exceeds client timeout | read timeout | client timeout 180s on first call (D-E9) |
| node evicted / pool at 0 | 503 from activator, or DNS fail | preflight `kubectl get nodes` gate |
| model download fails (HF rate limit / no egress) | pod `CrashLoopBackOff`, ISVC never Ready | preflight checks ISVC Ready before the pipeline runs |
| wrong dims returned | 384 assertion fails | fail loud, never write to PGVector |

---

## 2. Phases

Sequential; each has a review gate. Total ≈ 5h wall clock, most of it waiting.

### Phase E0 — Preflight (30 min) — **CONTAINS A REAL-MONEY STEP**

Blockers: none.
Files: none (read-only + one cost-bearing command).

1. `cd financial-distress-gitops && make gcp-status` — confirm 0 nodes, both pools RUNNING.
2. Confirm the HF model revision to pin: fetch the current commit sha for
   `intfloat/multilingual-e5-small` and the TEI CPU image digest. Record both.
3. **🔴 REAL COST — STOP AND CONFIRM WITH THE USER BEFORE RUNNING:**
   ```
   make gcp-up
   ```
   Starts the billing meter: ~**USD 0.65–0.80/hr** running vs ~**USD 0.14/hr**
   hibernated (`phase-03-...md:275`, `Makefile:2-3`). Charged to GCP free-trial credit.
4. Verify the node actually came up:
   ```
   kubectl get nodes -o wide                      # expect 1 Ready node
   kubectl top nodes                              # baseline headroom
   gcloud container node-pools describe primary-pool --cluster fsds-evidence \
     --zone asia-southeast1-b --format='value(config.machineType,status)'
   kubectl get pods -A --field-selector=status.phase!=Running   # expect empty-ish
   argocd app list        # or: kubectl get applications -n argocd
   ```
5. Confirm the platform actually reconverged after the node cycle — Knative
   webhook, Kourier, KServe controller all Running:
   ```
   kubectl get pods -n knative-serving -n kourier-system -n kserve
   kubectl get crd | grep -Ec 'knative|kserve'    # expect 21
   ```

Gate: 1 Ready node, 21 CRDs, `platform-inference` Application `Synced/Healthy`.

**Risk (High × High): vCPU quota.** `CPUS_ALL_REGIONS=12` project-wide
(`phase-03-...md:344`). primary-pool e2-standard-8 = 8, evidence VM e2-medium = 2 →
10/12. **Do not start the evidence VM and the secondary pool as well** — it will
fail the quota, and the failure mode is a confusing resize error, not a clean
message. This slice needs neither.

**Risk (Med × High): workloads do not survive a hibernate cycle**
(`phase-03-...md:374`, still unproven — success criterion at `:353` is unchecked).
This slice is the first real gcp-down/up round trip. `make gcp-up` already
restarts ingress and cert-manager; if Knative/KServe come back unhealthy, fix
that **before** adding the ISVC, and record it — it is phase-03 evidence the
project still owes.

### Phase E1 — Deploy the InferenceService via GitOps (1.5h)

Blockers: E0.
Files owned (repo `financial-distress-gitops`, branch `master`):
- `platform/inference/embedding-server.yaml` (NEW)
- `platform/inference/VERSIONS.md` (MODIFY — add the TEI + model rows)

Manifest shape (KServe **v1beta1** `InferenceService`, custom-container
predictor — no `ClusterServingRuntime`, because the bundled
`kserve-huggingfaceserver` v0.14.1 runtime is a KServe-protocol server, not an
OpenAI `/v1/embeddings` server):

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: fd-embeddings
  namespace: default            # matches the Argo Application destination
  annotations:
    serving.kserve.io/deploymentMode: Serverless        # default; explicit for the reader
    autoscaling.knative.dev/min-scale: "0"              # scale to zero
    autoscaling.knative.dev/max-scale: "1"
    autoscaling.knative.dev/scale-to-zero-pod-retention-period: "10m"
spec:
  predictor:
    minReplicas: 0
    maxReplicas: 1
    timeout: 300                                        # Knative revision timeout, seconds
    containers:
      - name: kserve-container
        image: ghcr.io/huggingface/text-embeddings-inference:cpu-<pinned>@sha256:<digest>
        args: ["--model-id", "intfloat/multilingual-e5-small",
               "--revision", "<hf-commit-sha>",
               "--port", "8080",
               "--auto-truncate"]
        ports: [{containerPort: 8080, protocol: TCP}]   # exactly one port (Knative)
        env:
          - {name: HF_HOME, value: /data}
        resources:
          requests: {cpu: "1",   memory: 2Gi}
          limits:   {cpu: "2",   memory: 4Gi}
        readinessProbe:
          httpGet: {path: /health, port: 8080}
          initialDelaySeconds: 20
          periodSeconds: 10
          failureThreshold: 30          # ~5 min budget for HF download + load
        livenessProbe:
          httpGet: {path: /health, port: 8080}
          initialDelaySeconds: 240
          periodSeconds: 30
          failureThreshold: 3
        volumeMounts: [{name: hf-cache, mountPath: /data}]
    volumes:
      - name: hf-cache
        emptyDir: {sizeLimit: 4Gi}
```

Sizing rationale: e2-standard-8 = 8 vCPU / 32 GB, minus ~3–4 vCPU already
requested by Argo CD, ingress-nginx, cert-manager, Knative (activator,
autoscaler, controller, webhook), Kourier, KServe controller. `requests.cpu: 1`
schedules reliably; `limits.cpu: 2` lets a batch soak the spare core. The model
is ~470 MB fp32 → 2 GB request is comfortable, 4 GB limit is headroom for
tokenizer + batch buffers.

Scale-to-zero rationale: a RAG **batch** job tolerates cold start. Documented
cold-start budget: **60–180 s** (image pull on a fresh node + ~470 MB HF
download into `emptyDir` + load). `emptyDir` means every cold start re-downloads —
accepted, because a PVC would add a ReadWriteOnce volume, a StorageClass
decision, and a hibernate-survival question for a ~470 MB download. **KISS; revisit
only if measured cold start exceeds 5 min.** The `10m` retention period keeps the
pod warm across a whole batch run.

Steps:
1. Write the manifest with real pinned digests (no floating tags — `VERSIONS.md`
   convention).
2. Add TEI + model rows to `VERSIONS.md`, including the HFOIL license note.
3. Dry-run against the live cluster before committing:
   `kubectl apply --dry-run=server -f platform/inference/embedding-server.yaml`
4. Commit + push to `master`. **No PR needed** — see Phase E2.
5. Watch Argo pick it up, then:
   ```
   kubectl get isvc fd-embeddings -w        # READY=True
   kubectl get ksvc fd-embeddings -o jsonpath='{.status.url}'; echo
   kubectl get revision,pod -l serving.kserve.io/inferenceservice=fd-embeddings
   ```

**Risk (Med × High): `prune: true` + `selfHeal: true`** on the `platform-inference`
Application. Any `kubectl edit`/`kubectl apply` on this ISVC is reverted within
minutes. **All iteration goes through git commits.** Expect a slower edit loop
than usual; that is the GitOps contract, not a bug. (A short `kubectl -n argocd
patch app platform-inference` to disable selfHeal while iterating is legitimate,
but it must be reverted in the same session.)

**Risk (Med × Med): sync-wave `-10`.** The Application is annotated wave `-10`
(operators). The ISVC is an operator *consumer* in the same Application, so on a
cold reconcile Argo may try to create the ISVC before the KServe webhook is
serving → a transient admission error that self-heals on retry. Acceptable; if it
sticks, the fix is a separate wave-0 Application — do **not** do that
preemptively (YAGNI).

**Risk (Low × High): egress to huggingface.co.** GKE nodes have default egress;
`platform/security/default-deny-networkpolicy.yaml` exists — check whether it
applies to `default` namespace before assuming the pod can reach HF. If it does,
the pod cannot download the model and will CrashLoop with a confusing error.
Check this in E0, not after a failed deploy.

Gate: `kubectl get isvc fd-embeddings` shows `READY=True` and a URL.

### Phase E2 — GitOps flow confirmation (15 min, mostly already true)

**A plain commit + push to `master` is sufficient.** Verified:
`argocd/applications/platform-inference.yaml` already sources `path:
platform/inference` with `directory.recurse: true`, `exclude: "*.md"`, and
`syncPolicy.automated{prune,selfHeal}`. A new `.yaml` in that directory is picked
up with no further wiring.

- **No new Argo `Application`.** (Constraint satisfied — checked, not assumed.)
- **No `ApplicationSet` entry.** `applicationset-dev.yaml` generates from
  `apps/dev/*`, which is for phase-06/07 app workloads, not platform components.
- **No GitHub Actions workflow.** The `phase-04-...md:629-644` digest-PR pattern
  exists to propagate an image digest that **CI builds**. This slice builds no
  image (D-E1); the digest is an upstream published one, pinned by hand once.
  Building a CI pipeline for a single static manifest is exactly the YAGNI
  violation the task warns about. The CI/CD rows are phase-06's own scope.
- Commit convention (gitops repo, per its own history): `feat(inference): ...`,
  no co-author trailer.
- Source repo convention (`AGENTS.md`): `feat(phase2): ...`, branch
  `feat/kebab-slug`, merge to `dev` via PR.

### Phase E3 — `TeiHttpEmbedder` in the source repo (1.5h)

Blockers: E1 (needs a live endpoint to test against — though unit tests are
endpoint-free).
Files owned (repo `Financial-Distress-Data`, branch `feat/embedding-http-backend`):

| File | Change |
|---|---|
| `src/llm/rag/embedding.py` | NEW-or-EXTEND — D5's protocol + a **third** impl `TeiHttpEmbedder` |
| `configs/embedding-backends.yaml` | NEW — the D-E7 pin file |
| `tests/platform/pipelines/test_embedding_http.py` | NEW — unit tests, no network |
| `scripts/smoke_embedding_endpoint.py` | NEW — the live smoke test (Phase E4) |

If phase-04 slice 4B has not run yet, this phase **creates** `src/llm/rag/embedding.py`
with D5's `EmbeddingBackend` protocol and all three impls; 4B then consumes it
rather than defining it. If 4B already landed, this phase only appends the third
impl. Either order works; state which one applies at execution time.

Shape (signature-level only — no implementation here):

```python
class TeiHttpEmbedder:                       # satisfies EmbeddingBackend (D5)
    name = "intfloat/multilingual-e5-small"
    version: str                             # from configs/embedding-backends.yaml
    dims = 384

    def __init__(self, endpoint: str, host_header: str | None = None,
                 prefix: str = "passage: ", timeout: tuple[float, float] = (5.0, 180.0),
                 batch_size: int = 32) -> None: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...
```

Contract details that matter:

- **Lazy import `requests` inside `embed()`**, per D4 (`phase-04-...md:89-97`).
  `httpx` is **not** installed in `.venv-phase2` (verified) — use `requests`,
  which is. Do not add a dependency.
- `tenacity` 8.5.0 (already present): exponential backoff, capped attempts,
  retry **only** on `ConnectionError`/`Timeout`/HTTP 5xx/429. A 4xx (bad request,
  404 from a missing Host header) is a bug — fail immediately, do not retry.
  Reuse `data_governance.retry_policy()` if 4B has already defined it (DRY);
  otherwise define it there and import, not a second copy.
- Timeout is a `(connect, read)` tuple. Read timeout 180 s covers the cold start;
  a warm call is ~50–200 ms.
- Batch in chunks of 32 to bound request size and give tenacity a small retry unit.
- Post-conditions asserted every call: `len(result) == len(texts)`,
  `len(v) == 384` for all v, and `abs(norm(v) - 1.0) < 1e-3` on the first vector
  of each batch (D-E5). Violations raise; **never** silently write a bad vector.
- Config is read from `configs/embedding-backends.yaml`; endpoint + host header
  from env (`EMBEDDING_ENDPOINT`, `EMBEDDING_HOST_HEADER`) so the same class
  works against a port-forward now and a real route later with zero code change.

Verify: `.venv/bin/python -m pytest tests -k embedding`, then the full
`AGENTS.md` gate `.venv/bin/python scripts/run_stage1_quality_gates.py` before
declaring done (the new module must not break the platform .ast loop — that is
D4's whole point).

### Phase E4 — Verification / evidence (1h)

Blockers: E1, E3.

1. **Warm smoke, Vietnamese text.** `scripts/smoke_embedding_endpoint.py`:
   ```
   POST /v1/embeddings
   {"model":"intfloat/multilingual-e5-small",
    "input":["passage: Công ty cổ phần này có tỷ lệ nợ trên tổng tài sản cao.",
             "passage: Doanh nghiệp ghi nhận dòng tiền hoạt động âm ba quý liên tiếp."]}
   ```
   Assert: HTTP 200; `len(data) == 2`; `len(data[0].embedding) == 384`; L2 norm
   ≈ 1.0; the two Vietnamese sentences have higher cosine similarity to each
   other than to an unrelated English control sentence (a real sanity check that
   the multilingual model actually loaded, not a shape-only check).
2. **Cold-start measurement (informational, not a benchmark).**
   ```
   kubectl scale --replicas=0 ... # or just wait out the 10m retention
   kubectl get pod -l serving.kserve.io/inferenceservice=fd-embeddings -w
   time python scripts/smoke_embedding_endpoint.py     # first call after zero
   time python scripts/smoke_embedding_endpoint.py     # warm call
   ```
   Record both numbers and the observed `0 -> 1 -> 0` replica transition. This is
   **not** the phase-06 row-4 benchmark (no TTFT/throughput/optimization table)
   and must not be filed as such.
3. **Idempotence check:** embed the same text twice, assert byte-identical
   vectors. This is what makes `write_vectors`' `ON CONFLICT DO NOTHING`
   idempotency meaningful.
4. Write a short runbook note (endpoint, port-forward command, Host header,
   cold-start numbers, image + model digests) — into this file's §5, **not** into
   `docs/platform/evidence/llm/`. Evidence files belong to rubric rows; this slice
   claims none (D-E2).

### Phase E5 — Hibernate (10 min) — **HARD-TO-REVERSE, CONFIRM FIRST**

Blockers: E4 complete, all numbers recorded.

**🔴 STOP AND CONFIRM WITH THE USER BEFORE RUNNING:**
```
make gcp-down
```
This scales every pool to 0. **The live embedding endpoint disappears** — any
in-flight RAG work, port-forward, or follow-up question that assumes a live
cluster breaks. PVCs survive; running pods do not. Ask before running, and say
plainly that bringing it back is `make gcp-up` + ~2–5 min + another cold start.

Then: `make gcp-status` → both pools at 0. Cost returns to ~USD 0.14/hr.

---

## 3. Cost

| State | Rate | Source |
|---|---|---|
| Running (1× e2-standard-8) | ~USD 0.65–0.80/hr | `Makefile:2-3`, `phase-03-...md:275` |
| Hibernated (0 nodes; disks, LB IP, control plane) | ~USD 0.14/hr | same |

Realistic window for this slice: ~4–5 h of node uptime including debugging →
**≈ USD 3–4** of free-trial credit. The dominant risk is *forgetting* to run
`gcp-down`: a forgotten weekend is ~USD 60–90. Phase E5 is not optional.

Additional (small, not zero): egress for the ~470 MB HF download on every cold
start, and the persistent LB IP that stays billed while hibernated.

---

## 4. Backwards compatibility & rollback

**Compatibility:** additive everywhere.
- No platform .ile, DAG, or docker-compose service is touched.
- No existing gitops file changes except `VERSIONS.md` (append-only rows).
- `model-server.yaml`, `llm-d-router.yaml` untouched / not created.
- PGVector `vector(384)` unchanged (D-E4). Rows produced by this backend carry a
  distinct `embedding_version`, so any existing MiniLM or hash-embedder rows keep
  working and stay separately queryable.
- D5's two existing backends remain; `TeiHttpEmbedder` is a third choice, not a
  replacement. CI keeps using `DeterministicHashEmbedder` — no network in CI.

**Rollback, per phase:**

| Phase | Revert | Blast radius |
|---|---|---|
| E1 | `git revert` the gitops commit; Argo prunes the ISVC within minutes | endpoint gone; nothing else touched |
| E3 | `git revert` on the source branch; PR never merged to `dev` | none — the other two backends still work |
| E0/E5 | `make gcp-down` / `make gcp-up` | cluster-wide; PVCs survive |

No `terraform apply`/`destroy` is required by this slice. If someone proposes
one, that is out of scope and needs its own confirmation.

---

## 5. Test matrix

| Level | What | Where | Needs cluster? |
|---|---|---|---|
| Unit | prefix applied; batching splits at 32; 384-dim assertion raises on wrong dims; norm assertion raises; retry fires on 503/timeout and **not** on 400; Host header always sent | `tests/platform/pipelines/test_embedding_http.py`, `requests` stubbed | no |
| Unit | `configs/embedding-backends.yaml` parses; `digest` recomputes to the committed value | same file | no |
| Contract | manifest is valid against the live API | `kubectl apply --dry-run=server` | yes |
| Integration | ISVC reaches `READY=True`; `/health` 200 | E1 gate | yes |
| E2E | Vietnamese `/v1/embeddings` → 384-dim, normalized, semantically sane | `scripts/smoke_embedding_endpoint.py` | yes |
| E2E | scale 0→1→0 observed; cold vs warm latency recorded | E4 step 2 | yes |
| Regression | platform .ate still green | `scripts/run_stage1_quality_gates.py` | no |

The unit layer must run in `.venv` with **no** network and **no** new
dependency — that is the gate `AGENTS.md` calls definition of done.

---

## 6. Risk register

| Risk | L × I | Mitigation | If it fires |
|---|---|---|---|
| Forgetting `make gcp-down` | Med × High | E5 is a named phase with an explicit confirm; put a reminder at the top of the session summary | run it immediately; note the overspend honestly |
| vCPU quota (`CPUS_ALL_REGIONS=12`) blocks the resize | Med × High | Do not start the evidence VM or secondary-pool; check quota in E0 | free the evidence VM (2 vCPU) first |
| Platform doesn't reconverge after hibernate | Med × High | E0 gate checks Knative/Kourier/KServe before adding anything | fix the platform first; it's owed phase-03 evidence anyway |
| Pod cannot reach huggingface.co (NetworkPolicy) | Low × High | Check `platform/security/default-deny-networkpolicy.yaml` scope during E0 | add a scoped egress-allow, or pre-seed the model into a PVC |
| Argo `selfHeal` reverts manual debug edits | High × Low | All iteration through git; known and accepted | temporarily disable selfHeal, revert same session |
| ISVC admission fails on a cold reconcile (wave `-10`) | Med × Low | Retry; Argo self-heals | if persistent, split into a wave-0 Application |
| Cold start exceeds the 180 s client read timeout | Low × Med | `failureThreshold: 30` on readiness gives ~5 min; the activator queues the request | raise the client read timeout; consider a PVC cache |
| TEI CPU image needs an unsupported AVX level | Low × Med | e2 nodes are Intel/AMD with AVX2; TEI's generic `cpu-` build targets that | fall back to a `sentence-transformers` FastAPI shim (an image build — bigger scope, flag before doing it) |
| e5 prefixes forgotten → silently worse retrieval | Med × High | Prefix is inside `TeiHttpEmbedder`, not the caller; encoded in `embedding_version` | re-embed under a new `embedding_version` |
| ADR-004 (KServe 0.18) vs installed 0.14.1 | **certain** × Med | Recorded as **QE-1**; does not block this slice | phase-06 must decide: upgrade, or amend the ADR and re-price canonical row 2 |

---

## 7. Success criteria (`WHO -> ACTION -> RESULT`)

- [ ] Platform operator -> runs `make gcp-up` after user confirmation -> `kubectl get nodes` shows exactly 1 `Ready` e2-standard-8 node and `kubectl get crd | grep -Ec 'knative|kserve'` returns 21.
- [ ] Argo CD -> reconciles `platform/inference/embedding-server.yaml` from `master` with no new Application -> `kubectl get isvc fd-embeddings` reports `READY=True` with a `.status.url`.
- [ ] Smoke script -> POSTs two Vietnamese sentences to `/v1/embeddings` through the port-forward with the Knative `Host` header -> HTTP 200, 2 vectors, each exactly 384 floats, L2 norm within 1e-3 of 1.0, and the two Vietnamese sentences more cosine-similar to each other than to an English control.
- [ ] Operator -> lets the revision scale to zero, then issues one request -> observes replicas `0 -> 1`, records cold-start seconds and warm-call milliseconds as two distinct numbers.
- [ ] `TeiHttpEmbedder` -> embeds the same text twice -> returns byte-identical 384-float vectors.
- [ ] Developer -> runs `.venv/bin/python scripts/run_stage1_quality_gates.py` -> passes, proving the new module did not leak a dependency into the platform .ast loop.
- [ ] Reviewer -> greps `platform/inference/model-server.yaml` and `docs/platform/evidence/llm/` -> finds the placeholder unchanged and **no** new evidence file, confirming this slice claimed zero rubric rows.
- [ ] Platform operator -> runs `make gcp-down` after user confirmation -> `make gcp-status` shows both pools at 0.

---

## 8. Explicit non-goals

Out of scope for this slice, remaining phase-06 proper's job:

Qwen2.5 (or any chat/generative model) · `platform/inference/model-server.yaml`
content · llm-d router and `llm-d-router.yaml` · kagent · agentgateway · global
`ModelConfig` (`platform/agents/global-model-config.yaml`) · MCP servers · the
three agents (feature analyst, drift analyst, coordinator) · `agents-sandbox`
namespace and its negative proofs · agent registry and its UI · agent chat UI,
auth, rate limit · Prometheus/Grafana/Loki/Jaeger and the three viewer routes ·
GitHub Actions workflows for any of the above · KEDA `ScaledObject` ·
benchmark/optimization before-after table (row 4) · Locust · mutmut · coverage
gate · Jupyter notebooks · A/B testing · warm-up mode · novel ideas ·
`RagRetrievalService` · a public HTTPS route for the embedding endpoint ·
implementing `EmbeddingRegistryService` or its hot-swap · any `terraform
apply`/`destroy` · any DNS or certificate change.

Also out of scope: phase-04's own RAG work. This slice delivers the *endpoint and
the client class*; `write_vectors`, chunking, governance, and the PGVector writes
stay in phase-04 slice 4B.

---

## 5. Runbook (executed 2026-08-08, real cluster)

**gcp-up:** ran clean. `primary-pool` -> 1 node in ~4 min. Platform reconverged
after the hibernate cycle with no manual intervention — Knative/Kourier/KServe
all `Running` post-restart. **This was the first proven gcp-down/up round trip**
(previously unproven risk, phase-03 evidence still owed separately).

**Deploy:** `platform/inference/embedding-server.yaml` +
`fd-embeddings-egress-huggingface` NetworkPolicy committed to
`financial-distress-gitops` `master` (`0b2e476`), pushed, Argo synced via a
manual `sync` patch (didn't wait out the default poll interval). Pod
`fd-embeddings-predictor-00001-deployment-*` reached `2/2 Running` in under
6 minutes including image pull (~16s) and model download (ONNX weights,
~46s).

**Known quirk, not a functional issue:** the top-level `InferenceService`
status stayed `Ready=Unknown` / `"waiting for a Revision to become ready"`
even after the underlying `Configuration`, `Revision`, and `Route` were all
individually `Ready=True` with a working URL
(`fd-embeddings-predictor.default.svc.cluster.local`). This is a KServe
custom-container-predictor aggregate-status reconcile lag, not a real
readiness gap — verified by making real HTTP calls through it successfully.
Do not gate on `kubectl get isvc` alone; check the `Route`/`Configuration`
objects directly if the ISVC-level status looks stuck.

**Smoke test:** `scripts/smoke_embedding_endpoint.py` via `kubectl
port-forward -n kourier-system svc/kourier-internal 18080:80`, `Host:
fd-embeddings-predictor.default.svc.cluster.local`. Result:

```
sim(vi1, vi2) = 0.8930
sim(vi1, en)  = 0.7226
OK: dims=384, normalized, semantically sane, idempotent
```

Two Vietnamese financial sentences (0.893 similarity) vs. an unrelated
English control (0.72-0.73) — the multilingual model is genuinely loaded and
producing sane embeddings, not just shape-correct noise. Idempotence
verified separately: identical input across two calls produced a
byte-identical SHA-256 of the output vector.

**Cold-start note:** not separately measured this session (E4 step 2,
scale-to-zero timing) — the endpoint was kept warm through the whole slice
for iteration speed. `scale-to-zero-pod-retention-period: 10m` means it will
scale down naturally after the last request; a future evidence run can
capture the `0 -> 1` transition time then.

**Route/Host for reuse:**
```
kubectl port-forward -n kourier-system svc/kourier-internal 18080:80
EMBEDDING_ENDPOINT=http://127.0.0.1:18080/v1/embeddings
EMBEDDING_HOST_HEADER=fd-embeddings-predictor.default.svc.cluster.local
```
(Note: the actual host is `fd-embeddings-predictor...`, not `fd-embeddings...`
— Knative names the predictor's own route this way. The plan's D-E6 example
value was approximate; this is the verified real one.)

---

## Unresolved questions

**QE-1 (blocks phase-06, not this slice).** `adr-004-kserve-018-pin.md:24` pins
KServe **0.18** and `adr-010:88-93` restores the llm-d chain on that basis, but
phase-03 vendored **0.14.1** (`VERSIONS.md:14`), which has no `LLMInferenceService`
CRD. Canonical row 2's "satisfied as written" claim
(`phase-06-...md:70-73`) rests on a version that is not installed. Decide in
phase-06: upgrade KServe to 0.18 (CRD migration risk, plus Envoy Gateway
prerequisites that ADR-004 says were dropped), or amend both ADRs and re-price
row 2. Flagging now because it was discovered here.

**QE-2 (blocks E1, cheap to answer).** Does
`platform/security/default-deny-networkpolicy.yaml` apply to the `default`
namespace? If yes, the TEI pod cannot reach huggingface.co and needs a scoped
egress allow (or a pre-seeded model volume). Answer by reading the manifest in E0
before deploying.

**QE-3 (confirm before E1).** Namespace: this plan puts `fd-embeddings` in
`default`, matching the `platform-inference` Application's destination. A
dedicated `inference` namespace would be tidier but needs a `Namespace` manifest
in the same directory and interacts with the default-deny policy. Recommend
`default` for this slice; revisit when the chat model lands.

**QE-4 (supersedes phase-04 Q1 — needs the user's call).** `phase-04-...md:723-728`
Q1 recommends `all-MiniLM-L6-v2` + `sentence-transformers` (~2 GB into
`.venv-phase2`) for real runs. This slice makes the remote endpoint real, which
was Q1's rejected alternative *only because the server did not exist yet*.
Recommendation: **make `TeiHttpEmbedder` the evidence-run backend** (better
Vietnamese, no 2 GB local install, and it exercises the GKE inference platform
the rubric cares about), keep `DeterministicHashEmbedder` for CI, and **drop
`SentenceTransformerEmbedder` entirely** rather than carrying three backends —
YAGNI. Confirm, because it changes phase-04's dependency list and slice ordering
(4B would then depend on this slice).

**QE-5 (nice to know).** The user's brief said the gitops repo is on `main`; it is
actually on **`master`**, and every Argo `targetRevision` says `master`. Confirm
no rename is planned mid-slice — a rename would desync every Argo Application at
once.
