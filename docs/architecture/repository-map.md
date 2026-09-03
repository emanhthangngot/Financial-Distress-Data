# Repository map

For an interview-oriented, file-by-file lookup with “question → entrypoint →
test → command” routing, start with
[`docs/project-file-map.md`](../project-file-map.md). This document remains the
compact ownership/generated-artifact map used for repository maintenance.

One row per tracked top-level entry (`git ls-files | awk -F/ '{print $1}' | sort -u`).
Owner uses AGENTS.md's role convention: `data_engineer`, `ml_engineer`,
`llm_engineer`, `platform_operator`, `product_engineer`. Re-run the command
above and diff against this table when a top-level entry is added, renamed, or
removed — an entry missing a row is the detectable condition this map exists
to catch.

| Path | Owner | Plane | Generated? | What lives here |
|---|---|---|---|---|
| `.dockerignore` | platform_operator | shared tooling | No | Docker build context exclusions |
| `AGENTS.md` | data_engineer | shared tooling | No | Process rules — HOW-TO-BEHAVE for AI and human contributors |
| `.claude/` | platform_operator | shared tooling | No | Claude Code project settings (`settings.json`) |
| `CLAUDE.md` | data_engineer | shared tooling | No | Claude Code skill-routing pointer to `AGENTS.md` |
| `README.md` | data_engineer | documentation | No | Complete project overview, architecture, setup, product/evidence boundaries, and project tree |
| `apps/` | product_engineer | the platform product | No | the platform web app(s) (pnpm workspace member) |
| `packages/` | product_engineer | the platform product | No | Shared TypeScript packages (pnpm workspace member) |
| `configs/` | data_engineer | the platform local lakehouse | No | Collector, Spark, source, and DQ config YAMLs |
| `dags/` | data_engineer | the platform local lakehouse | No | Airflow DAGs; `dags/platform/` holds additive the platform wrappers |
| `docker-compose.yml` | platform_operator | shared tooling | No | Local platform service definitions (Postgres, Kafka, MinIO, Airflow, Flink) |
| `docs/` | data_engineer | documentation | Partial — `docs/evidence/**` is generated | Specs, ADRs, runbooks, and captured runtime evidence |
| `feature_repo/` | ml_engineer | the platform feature/RAG | No | Feast structured/RAG feature definitions and materialization configuration |
| `.env.example` | platform_operator | shared tooling | No | Local environment variable template |
| `flink/` | data_engineer | the platform local lakehouse | No | PyFlink job source for the opt-in Flink profile |
| `.github/` | platform_operator | shared tooling | No | CI workflow definitions |
| `.gitignore` | platform_operator | shared tooling | No | Git ignore patterns |
| `images/` | data_engineer | documentation | No | Architecture diagrams referenced from docs |
| `infra/` | platform_operator | shared tooling | No | Container build/bootstrap assets: `airflow/` (image build context), `flink/` (image build context), `kafka/` (topic init script) |
| `mutants/` | data_engineer | generated test output | Generated | Mutation-testing workspace/output; regenerate with the the platform mutation gate |
| `notebooks/` | llm_engineer | the platform evidence | No | Agent/MCP demonstration notebooks used by the LLM evidence track |
| `package.json` | product_engineer | the platform product | No | pnpm workspace root manifest |
| `plans/` | data_engineer | documentation | No | Implementation plans, phase files, and reports |
| `pnpm-lock.yaml` | product_engineer | the platform product | Generated (lockfile) | pnpm dependency lock |
| `pnpm-workspace.yaml` | product_engineer | the platform product | No | pnpm workspace member list |
| `pyproject.toml` | data_engineer | shared tooling | No | Python package and tooling config (pytest, ruff, black) |
| `requirements-platform.txt` | platform_operator | the platform shared tooling | No | the platform runtime/test dependency pins |
| `requirements.txt` | data_engineer | shared tooling | No | Python dependency pins |
| `scripts/` | data_engineer | shared tooling | No | Local E2E, DQ-failure-probe, and evidence-audit runners |
| `sql/` | data_engineer | the platform local lakehouse | No | PostgreSQL metadata DDL and DuckDB SQL views |
| `src/` | mixed — see below | mixed | No | Python source: see subdirectory ownership below |
| `supabase/` | product_engineer | the platform product | No | Supabase config and migrations for the the platform backend |
| `tests/` | data_engineer | shared tooling | No | PyTest unit/contract/runtime suite; `tests/platform/` covers the platform |
| `uv.lock` | data_engineer | shared tooling | Generated (lockfile) | uv dependency lock |

## `src/` subdirectory ownership

`src/` is a single top-level row above but mixes two planes; each subdirectory
has one owner:

| Subdirectory | Owner | Plane |
|---|---|---|
| `src/collectors/`, `src/generator/`, `src/streaming/`, `src/transforms/`, `src/quality/`, `src/catalog/`, `src/metadata/`, `src/io/`, `src/jobs/`, `src/security/` | data_engineer | the platform local lakehouse |
| `src/ml/`, `src/drift/` | ml_engineer | the platform product |
| `src/llm/`, `src/agents/` | llm_engineer | the platform product |

`src/generators/` no longer exists — its two modules were split into
`src/collectors/fixture_config.py` and `src/streaming/problem_factory.py`
(they never had one owner; each belonged to what it configured).

## Separate deployment repository

`financial-distress-gitops` is intentionally not a top-level entry in this
source repository. It owns Terraform/GKE bootstrap, Helm-rendered platform
manifests, Argo CD applications, image digests, ingress, security policies,
model serving, agents, and observability desired state. This repository owns
the application code, contracts, tests, product migrations, runbooks, and
canonical evidence. The two repositories are joined by the source SHA +
GitOps SHA recorded in the platform evidence; the final submission freeze requires
those stamps to be regenerated after the latest commits.

## Python package boundary

`pyproject.toml` declares `[build-system]`/`[tool.setuptools.packages.find]`
so the tree is installable (`pip install -e .`) from a working directory other
than the repo root — required for phases 5-6 to `pip install` this repo into a
model/agent container image. The distributed package is named `src`, which is
a known wart: `src` is conventionally a layout directory, not an importable
name. A proper fix renames it to `financial_distress` with a repo-wide import
rewrite across `src/`, `dags/`, `tests/`, `scripts/`, and the the platform spec's
file tables in `docs/mini_coursework.md` — rejected for now (YAGNI) since
declaring `src` as the package name buys full installability at a few lines of
config. `dags/` is deliberately excluded from the distribution: Airflow
discovers DAGs by filesystem path via the compose bind mount, not by import,
and packaging them would create a second, competing discovery path.

Runtime dependency versions are declared in three places that can drift; each
is authoritative for a different consumer:

| Manifest | Authoritative for | Content |
|---|---|---|
| `requirements.txt` | CI (`Install dependencies` step) | Overlapping floors, plus dev tools, minus `pyspark`/`kafka-python`/`minio` |
| `pyproject.toml` `[project.optional-dependencies] runtime` | Local dev extras | `duckdb>=1.1`, `kafka-python>=2.0`, `minio>=7.2`, `pyarrow>=17.0`, `psycopg[binary]>=3.2`, `pyspark>=3.5` (floors) |
| `infra/airflow/Dockerfile` | The Airflow image | Exact pins (`duckdb==1.1.3`, `pyspark==3.5.6`, …) |

Consolidating them is a separate change with its own blast radius (CI installs
from `requirements.txt`; the image rebuild is expensive) — not done here.

## Generated — do not hand-edit

Matching AGENTS.md: regenerate via the producing script, never hand-edit.

- `docs/evidence/**` — produced by the various `scripts/audit_*` and
  `scripts/run_*` evidence runners.
- `warehouse.db` (gitignored, not a tracked top-level entry) — the local
  DuckDB catalog, rebuilt by the pipeline DAGs.
