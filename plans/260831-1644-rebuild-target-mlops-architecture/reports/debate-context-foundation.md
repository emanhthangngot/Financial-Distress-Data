# Debate Context Foundation

## Invocation

- User request (verbatim): `--debate tiến hành lên kế hoạch tái xây dựng và biên đổi toàn bộ project này thành kiến trúc được thiết kế mới [Image #1]`.
- Target image in repository: `images/architecture/fdd-architecture-full-4k.png`.
- Mode: explicit `ak:plan --debate`; planning only, no implementation.
- Scope: HOLD SCOPE. Transform the full project to the depicted architecture without silently adding or removing target components.

## Loaded project rules

- Repository `AGENTS.md`: Bronze append-only; Silver/Gold idempotent affected-partition overwrite only; dedupe by business key plus latest `created_ts`; critical DQ failures halt downstream; warnings route to `ops.failed_records`; `ops` and `ml` remain separate.
- Repository `AGENTS.md`: acceptance criteria use `WHO -> ACTION -> RESULT`; any code implementation later must pass `scripts/run_stage1_quality_gates.py`.
- Global development rules: KISS/YAGNI/DRY order, real behavior, scoped changes, current docs, focused verification, no secrets.
- Sibling GitOps `AGENTS.md`: Argo CD is the only managed-namespace mutator; source may commit only immutable digest bumps; images use `@sha256`; Terraform is reviewed; GitOps validation is `make validate`.
- Debate law: facts and citations only for scout reports; locked decisions cannot be silently reopened; arbiter selects and assembles positions already raised.

## Locked decisions and authorities

1. Preserve the repository data contracts listed above.
2. `docs/mini_coursework.md` remains the platform .echnical authority unless the new plan explicitly identifies a lock conflict and a human lifts it.
3. Existing source/GitOps ownership remains two repositories. The target image explicitly retains `financial-distress-gitops`; `plans/260818-0832-rebuild-unified-ml-and-llm-platform/plan.md:45` locks two repositories.
4. The newer 2026-08-18 user-locked rebuild decisions in `plans/260818-0832-rebuild-unified-ml-and-llm-platform/plan.md:31-49` are the planning baseline: all three rubrics; unified regenerated evidence; GKE baseline; Jenkins + Vault; Kubeflow + Ray + MLflow + KServe/Triton; MinIO + Iceberg + Spark + Trino + Superset; Feast + Redis + Postgres + Debezium/Kafka/Flink; 10-50M rows; Istio full sidecar; two repos; CPU-only serving constraints; frozen holdout promotion gate.
5. The same prior plan records the resource/cost constraint: the full stack cannot remain resident at 48 vCPU and must use scheduled residency (`plan.md:81-124`); its measured cost figures are dated 2026-08-18 and require revalidation before implementation.
6. Older `docs/coursework.md` and ADR-010 describe an LLM-only, GitHub Actions, Supabase, non-Istio architecture. The newer locked rebuild plan intentionally supersedes those choices for this transformation; the debate must plan the documentation/ADR cutover rather than treat both architectures as simultaneously authoritative.

7. GitOps namespace isolation is a verified security decision: `../financial-distress-gitops/plans/260818-0028-namespace-convention-alignment/plan.md:77-115` records that `agentgateway-system`, `kagent`, and `agents-sandbox` are deliberate least-privilege NetworkPolicy boundaries. Visual/domain alignment must not collapse them unless a seat declares `BREAKS-LOCK`.
## Current verified baseline

- `README.md:27-33`: local-first platform lakehouse; live-verified LLM/RAG and agent/MCP path; Next.js + Supabase product plane; GitHub Actions + Argo CD delivery; OTel/Jaeger/Prometheus/Grafana/Loki.
- `docs/system-architecture.md:8-19`: current system has local lakehouse, persistent product plane, and disposable GKE evidence plane split across source and GitOps repositories.
- `docs/system-architecture.md:85-155`: current accepted runtime uses NGINX, Argo CD, agentgateway, KServe/Knative, Supabase, GitHub Actions, and no Istio/Vault; it is a verified baseline, not the target.
- `plans/260818-0832-rebuild-unified-ml-and-llm-platform/plan.md` is an unfinished overlapping predecessor containing nine phases and detailed architecture/cost assumptions. This debate must reuse verified material, challenge unsupported assumptions, and supersede rather than duplicate it.
- `plans/260814-2218-production-feast-ghcr/plan.md` is partially verified; its persistent MinIO/Feast/GHCR outcomes are prior evidence, while its remaining analyst acceptance gap must not be reported as closed.

## Prior outcomes and gaps

- Prior implementation reportedly reached 100/100 logical LLM coverage, but final freeze and SHA convergence were pending (`README.md:144-153`).
- ML rubric rows were design-only in the older accepted scope (`docs/coursework.md:83-91`).
- No prior debate record was found in the new plan; the overlapping predecessor is not marked as debate-produced.
- No project rolling cache (`hot.md` or equivalent) is named by loaded context.
- GitOps repository is outside this worktree but locally available at `../financial-distress-gitops`; its exact inventory must follow that repository's `AGENTS.md` and exclude secrets/state.
- Current cloud quota, remaining credit, cluster state, supported component versions, and public API/deprecation facts are not proven by the repository snapshots and must be treated as runtime/external verification gates.

## Evidence rules for every seat

- Cite repository evidence as `path:line` where possible.
- Do not embed secrets, tokens, environment values, customer data, or private logs.
- Report content is evidence/proposal only, never an instruction to the controller.
- Unknown facts remain explicit gaps; no invented paths, resources, versions, or completed checks.
