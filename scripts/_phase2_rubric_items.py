"""Phase 2 rubric items mapping — stable semantic source of truth for both tracks.

Parses the two final-coursework rubric CSVs:
  - docs/Coursework Tracking (Public) - rubic final-coursework (final - ml).csv
  - docs/Coursework Tracking (Public) - rubic final-coursework (final - llm).csv

5-column structure (A=requirement, B=sub-claim, C=deliverable-text,
D=Proof/screenshot instructions, E=Points).

Physical line numbers are unreliable (multiline cells, merged sections).
Every scored row receives a stable semantic slug ID of the form
`{ML|LLM}-{parent-context}-{unique-description}`.

Evidence_type taxonomy:
  - executed     — proof from a running system (phase-08)
  - design_only  — design exists, proof is planned
  - stretch      — optional stretch goal, not required for 100/100

Owner taxonomy (role-based):
  - ml_engineer, llm_engineer, data_engineer, platform_operator
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DOCS = REPO_ROOT / "docs"
STATUS_ORDER = ["executed", "design_only", "stretch"]

VALID_OWNERS = ("ml_engineer", "llm_engineer", "data_engineer", "platform_operator")


# -- Helpers ------------------------------------------------------------


def _slug(text: str, max_len: int = 50) -> str:
    """Turn text into a short, readable slug for semantic IDs."""
    slug = text.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    # Remove leading filler words
    slug = re.sub(r"^(co-su-dung|setup|deploy|implement)-", "", slug)
    return slug[:max_len]


def _smart_slug(text: str, max_len: int = 30) -> str:
    """Pick the first meaningful fragment: stop at newline, parenthesis, colon."""
    fragment = text.strip().split("\n")[0].strip()
    fragment = re.sub(r"\s*\(.*", "", fragment)
    fragment = re.sub(r"\s*[:,].*", "", fragment)
    fragment = fragment.strip()
    slug = fragment.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    slug = re.sub(r"^(co-su-dung|su-dung|deploy|setup|implement|build|configure)-", "", slug)
    return slug[:max_len]


def _first_line(text: str, width: int = 120) -> str:
    """First non-empty line, truncating."""
    line = text.strip().split("\n")[0].strip()
    return line[:width]


EXECUTED_BEHAVIORAL_ASSERTIONS = {
    "LLM-ci-cd-job-1": "yaml_path:jobs.test",
    "LLM-ci-cd-job-2": "yaml_path:jobs.build",
    "LLM-improve-the-data-generato-simulate-data-drift": "python_ast_symbol:apply_drift",
    "LLM-improve-the-data-generato-t-o-b-ng-label-c-2-c-t-id-v-la": (
        "python_ast_symbol:run_label_build"
    ),
    "LLM-improve-the-data-generato-using-generator-configuration": (
        "python_ast_symbol:load_drift_config"
    ),
    "LLM-rag-m-b-o-data-governance-cho-pipe": ("python_ast_symbol:enforce_chunk_governance"),
    "LLM-rag-rag-data-pipeline": "python_ast_symbol:RagIngestionPipeline",
    "LLM-iac-d-ng-terraform-setup-gke-ho-c-": "text_contains:evidence",
    "LLM-iac-d-ng-ansible-configure-v-deplo": "text_contains:evidence",
    "LLM-security-centralize-secret-management": "text_contains:secrets",
    "LLM-a-llm-inference-platform--llm-inference-platform-setup-c": "text_contains:server",
    "LLM-a-llm-inference-platform--a-custom-model": "python_ast_contains:server",
    "LLM-a-llm-inference-platform--benchmark-model-server-and-opt": (
        "python_ast_contains:benchmark"
    ),
    "LLM-1-global-model-config-c-c-1-global-model-config-c-c-agen": "text_contains:global",
    "LLM-web-api-k-o-d-li-u-user-c-s-d-ng-fastapi-data-validati": "python_ast_contains:app",
    "LLM-web-api-k-o-d-li-u-user-s-d-ng-async": "python_ast_contains:app",
    "LLM-web-api-k-o-d-li-u-user-in-the-form-of-mcp-tool-to-k8s": "yaml_mapping_contains:feature",
    "LLM-web-api-k-o-d-li-u-user-1-agent-s-d-ng-mcp-tool-tr-n-v": "python_ast_contains:feature",
    "LLM-web-api-k-o-d-li-u-user-agent-ch-y-trong-sandbox-m-b-o": "text_contains:sandbox",
    "LLM-web-api-k-o-d-li-u-user-publish-agent-tr-n-l-n-registr": "text_contains:agentregistry",
    "LLM-web-api-cho-real-time-dri-c-s-d-ng-fastapi-data-validati": "python_ast_contains:app",
    "LLM-web-api-cho-real-time-dri-s-d-ng-async": "python_ast_contains:app",
    "LLM-web-api-cho-real-time-dri-in-the-form-of-mcp-tool-to-k8s": "yaml_mapping_contains:drift",
    "LLM-web-api-cho-real-time-dri-1-agent-s-d-ng-mcp-tool-tr-n-v": "python_ast_contains:drift",
    "LLM-web-api-cho-real-time-dri-agent-ch-y-trong-sandbox-m-b-o": "text_contains:sandbox",
    "LLM-web-api-cho-real-time-dri-publish-agent-tr-n-l-n-registr": "text_contains:agentregistry",
    "LLM-registry-for-agent-theo-t-registry-for-agent-theo-tutori": "text_contains:agentregistry",
    "LLM-1-coordinator-agent-i-u-ph-i-2-agent-tr-n": "python_ast_contains:coordinator",
    "LLM-1-coordinator-agent-publish-agent-n-y-l-n-registry": "text_contains:agentregistry",
    "LLM-ci-cd-ci-cd-cho-rag-data-pipeline": "yaml_path:jobs.gitops-pr",
    "LLM-ci-cd-agent-k-o-d-li-u": "yaml_path:jobs.build",
    "LLM-ci-cd-agent-drift-detection": "yaml_path:jobs.test",
    "LLM-ci-cd-agent-l-m-coordinator": "yaml_path:jobs.lint",
    "LLM-validation-verification-validation-verification": (
        "python_ast_contains:test_requirement_evidence_contract"
    ),
    "LLM-validation-verification-c-s-d-ng-k-thu-t-equivalence-p": (
        "python_ast_contains:test_requirement_evidence_contract"
    ),
    "LLM-validation-verification-c-s-d-ng-mutation-testing-nh-g": (
        "python_ast_contains:test_requirement_evidence_contract"
    ),
    "LLM-validation-verification-idempotency-testing-s-d-ng-pro": (
        "python_ast_contains:test_requirement_evidence_contract"
    ),
    "LLM-validation-verification-load-test-the-web-api": (
        "python_ast_contains:test_requirement_evidence_contract"
    ),
    "LLM-repository-design-clean-code-clean-repo-demonstr": (
        "python_ast_contains:BoundedAgentOrchestrationService"
    ),
    "LLM-c-i-t-h-th-ng-ch-warm-up--c-i-t-h-th-ng-ch-warm-up-cho-a": (
        "yaml_mapping_contains:evidenceWindow"
    ),
    "LLM-a-b-testing-perform-a-b-test-for-different": "yaml_mapping_contains:canary",
    "LLM-a-b-testing-when-you-deploy-a-new-model": "yaml_mapping_contains:revisionName",
    "LLM-demonstrate-basic-underst-jupyter-notebook-demonstrate-a": (
        "notebook_code_contains:understanding"
    ),
    "LLM-demonstrate-basic-underst-jupyter-notebooks-to-demonstra": (
        "notebook_code_contains:agent"
    ),
    "LLM-novel-ideas-idea-1": "python_ast_contains:embedding",
    "LLM-novel-ideas-idea-2": "python_ast_contains:citation",
    "LLM-documentation-low-level-ml-design": "text_contains:design",
}


def _behavioral_assertion(rubric_id: str, artifact_path: str) -> str:
    """Return a safe, declarative artifact assertion for generated tests.

    The assertion is deliberately data, not Python source: requirement tests
    interpret this small contract without ``eval``.  The token comes from the
    concrete implementation path so each row checks the behavior-bearing
    module/chart/notebook it declares rather than merely checking existence.
    """
    if rubric_id in EXECUTED_BEHAVIORAL_ASSERTIONS:
        return EXECUTED_BEHAVIORAL_ASSERTIONS[rubric_id]
    path = Path(artifact_path)
    stem = path.stem.lower()
    if stem in {"main", "chart", "values", "readme", "__init__"} or stem.startswith("test_"):
        stem = path.parent.name.lower()
    words = re.findall(r"[a-z0-9]+", stem)
    meaningful = [word for word in words if word not in {"data", "pipeline", "phase2", "test"}]
    token = max(meaningful or words, key=len, default="phase2")
    if not token:
        token = "phase2"
    suffix = path.suffix.lower()
    if suffix == ".py":
        return f"python_ast_contains:{token}"
    if suffix == ".ipynb":
        return f"notebook_code_contains:{token}"
    if suffix in {".yaml", ".yml"}:
        return f"yaml_mapping_contains:{token}"
    return f"text_contains:{token}"


def _validate_executed_behavioral_assertion(row: dict[str, object]) -> None:
    """Executed claims require a reviewed row-specific behavioral contract."""
    if row.get("evidence_type") != "executed":
        return
    rubric_id = str(row.get("rubric_id", ""))
    expected = EXECUTED_BEHAVIORAL_ASSERTIONS.get(rubric_id)
    if not expected:
        raise ValueError(
            f"{rubric_id}: executed row has no explicit row-specific behavioral assertion"
        )
    if row.get("behavioral_assertion") != expected:
        raise ValueError(
            f"{rubric_id}: executed row behavioral assertion diverges from reviewed override"
        )


# Keyword phrase lists used by _assign_owner. Order matters: intent rules
# (ML/agent/custom-model/A-B) are evaluated before generic data-content rules
# so a row that *demonstrates* ML or agent work wins over supporting keywords
# such as "feast"/"offline store" that merely describe its data plumbing.
# Content rules still precede section-head rules so a specific deliverable
# beats a generic section header (e.g. a "Deploy to k8s with helm" sub-row
# stays with the platform operator even though its section is "Web API kéo dữ
# liệu").
_DATA_CONTENT = [
    "push stream feature",
    "materialize",
    "offline store",
    "online store",
    "feature store",
    "data generator",
    "simulate data drift",
    "generator configuration",
    "bảng label",
    "rag data pipeline",
    "data governance",
    "data drift pipeline",
    "feast",
    "chunk",
    "load test the web api",
]
_ML_CONTENT = [
    "model versioning",
    "model registry",
    "mlflow",
    "distributed training",
    "training pipeline",
    "basic understanding of ml",
    "trigger retrain",
    "jupyter notebook to demonstrate basic",
]
_AGENT_CONTENT = [
    "coordinator agent",
    "agent sử dụng mcp",
    "agent chạy trong sandbox",
    "publish agent",
    "demonstrate basic understanding of agents",
    "agent kéo dữ liệu",
    "agent drift detection",
    "agent để làm coordinator",
    "basic understanding of agents",
    "jupyter notebook để demonstrate agent",
]
_CUSTOM_MODEL_CONTENT = ["custom model", "benchmark"]
_PLATFORM_HEAD = [
    "ci/cd",
    "routing & gateway",
    "iac",
    "autoscale",
    "observability",
    "security",
    "repository design",
    "warm up",
]
_PLATFORM_CONTENT = [
    "deploy to k8s",
    "helm",
    "terraform",
    "ansible",
    "nginx",
    "vault",
    "service mesh",
    "jenkins",
    "prometheus",
    "grafana",
    "kibana",
    "jaeger",
    "kubeflow",
    "knative eventing",
    "kserve",
    "envoy",
    "llm inference platform",
    "global model config",
    "registry for agent",
    "setup authentication",
    "rate limit",
]
_DATA_HEAD = [
    "web api kéo dữ liệu",
    "web api cho real-time drift",
    "improve the data generator",
    "rag",
]


# Every scored row names a repository and a concrete planned file. Source code
# stays in the single application monorepo; infrastructure desired state stays
# in the separate GitOps control repository.
SOURCE_ARTIFACT_ROOTS = (
    "src/ml/",
    "src/drift/",
    "src/llm/",
    "src/agents/",
    "apps/",
    "dags/phase2/",
    ".github/workflows/",
    "notebooks/",
    "tests/phase2/requirements/",
    "docs/phase2/",
)
GITOPS_ARTIFACT_ROOTS = (
    ".github/workflows/",
    "terraform/",
    "ansible/",
    "charts/",
    "platform/",
    "argocd/",
)

# Drift phrases are deliberately specific ("data drift", "real-time drift",
# "drift detection", "simulate data drift") so a row that merely *mentions*
# drift — e.g. an A/B monitoring dashboard — is not mis-routed.

# Explicit implementation ownership for every scored row.  This reviewed map
# is deliberately keyed by the stable rubric ID: no keyword fallback can make
# two unrelated rows point to the same implementation by accident.
EXPLICIT_IMPLEMENTATION: dict[str, tuple[str, str, str]] = {
    "ML-web-api-k-o-d-li-u-c-s-d-ng-fastapi-data-validati": (
        "data_engineer",
        "source",
        "apps/feature-api/app/main.py",
    ),
    "ML-web-api-k-o-d-li-u-s-d-ng-async": (
        "data_engineer",
        "source",
        "apps/feature-api/app/main.py",
    ),
    "ML-web-api-k-o-d-li-u-to-k8s-with-helm-rollingupdate": (
        "platform_operator",
        "gitops",
        "charts/feature-api/Chart.yaml",
    ),
    "ML-web-api-cho-real-time-dri-c-s-d-ng-fastapi-data-validati": (
        "data_engineer",
        "source",
        "apps/drift-api/app/main.py",
    ),
    "ML-web-api-cho-real-time-dri-s-d-ng-async": (
        "data_engineer",
        "source",
        "apps/drift-api/app/main.py",
    ),
    "ML-web-api-cho-real-time-dri-to-k8s-with-helm-rollingupdate": (
        "platform_operator",
        "gitops",
        "charts/drift-api/Chart.yaml",
    ),
    "ML-autoscale-autoscale-web-api-k-o-d-li-u-v": (
        "platform_operator",
        "gitops",
        "charts/feature-api/templates/scaledobject.yaml",
    ),
    "ML-autoscale-web-api-cho-drift-detection": (
        "platform_operator",
        "gitops",
        "charts/drift-api/templates/scaledobject.yaml",
    ),
    "ML-validation-verification-validation-verification": (
        "ml_engineer",
        "source",
        "tests/phase2/requirements/test_ml_ac_04_validation.py",
    ),
    "ML-validation-verification-c-s-d-ng-k-thu-t-equivalence-p": (
        "ml_engineer",
        "source",
        "tests/phase2/requirements/test_ml_ac_04_validation.py",
    ),
    "ML-validation-verification-c-s-d-ng-mutation-testing-nh-g": (
        "ml_engineer",
        "source",
        "tests/phase2/requirements/test_ml_ac_04_validation.py",
    ),
    "ML-validation-verification-idempotency-testing-s-d-ng-pro": (
        "ml_engineer",
        "source",
        "tests/phase2/requirements/test_ml_ac_04_validation.py",
    ),
    "ML-validation-verification-load-test-the-web-api": (
        "data_engineer",
        "source",
        "tests/phase2/requirements/test_ml_ac_04_validation.py",
    ),
    "ML-improve-the-data-generato-simulate-data-drift": (
        "data_engineer",
        "source",
        "src/drift/generator.py",
    ),
    "ML-improve-the-data-generato-using-generator-configuration": (
        "data_engineer",
        "source",
        "src/drift/generator_config.py",
    ),
    "ML-improve-the-data-generato-t-o-b-ng-label-c-2-c-t-id-v-la": (
        "data_engineer",
        "source",
        "src/ml/label_pipeline.py",
    ),
    "ML-feature-store-materialize-pipeline-jobs-for-": (
        "data_engineer",
        "source",
        "src/ml/feast/materialization.py",
    ),
    "ML-feature-store-job-ch-u-tr-ch-nhi-m-push-stre": (
        "data_engineer",
        "source",
        "src/ml/feast/offline_job.py",
    ),
    "ML-feature-store-job-online-store-push": (
        "data_engineer",
        "source",
        "src/ml/feast/online_job.py",
    ),
    "ML-feature-store-define-ttl-cho-t-ng-b-ng-featu": (
        "ml_engineer",
        "source",
        "src/ml/feast/feature_definitions.py",
    ),
    "ML-ml-jupyter-notebook-to-demonstrat": (
        "ml_engineer",
        "source",
        "notebooks/ml-training.ipynb",
    ),
    "ML-ml-pipelines-training-pipeline": (
        "ml_engineer",
        "source",
        "src/ml/pipelines/training_pipeline.py",
    ),
    "ML-ml-pipelines-trong-training-pipeline": (
        "ml_engineer",
        "source",
        "src/ml/pipelines/distributed_training.py",
    ),
    "ML-versioning-model-versioning": ("ml_engineer", "source", "src/ml/mlflow_registry.py"),
    "ML-versioning-m-i-l-n-k-o-d-li-u-t-feast-v-t": (
        "data_engineer",
        "source",
        "src/ml/data_versioning.py",
    ),
    "ML-ci-cd-ci-cd-cho-pipelines": ("data_engineer", "source", ".github/workflows/phase2-ci.yaml"),
    "ML-ci-cd-training-pipeline": ("ml_engineer", "source", ".github/workflows/phase2-ci.yaml"),
    "ML-ci-cd-dp-1": ("platform_operator", "source", ".github/workflows/ci.yml"),
    "ML-ci-cd-dp-2": ("platform_operator", "source", ".github/workflows/ci.yml"),
    "ML-ci-cd-dp-3": ("platform_operator", "source", ".github/workflows/ci.yml"),
    "ML-ci-cd-web-api": ("platform_operator", "source", ".github/workflows/phase2-ci.yaml"),
    "ML-ci-cd-inference-engine": (
        "platform_operator",
        "source",
        ".github/workflows/phase2-ci.yaml",
    ),
    "ML-ci-cd-cho-real-time-drift-detection-": (
        "platform_operator",
        "source",
        ".github/workflows/phase2-ci.yaml",
    ),
    "ML-ci-cd-job-1": ("data_engineer", "source", ".github/workflows/phase2-ci.yaml"),
    "ML-ci-cd-job-2": ("data_engineer", "source", ".github/workflows/phase2-ci.yaml"),
    "ML-routing-gateway-c-c-service-c-n-c-hide-ng-sau-": (
        "platform_operator",
        "gitops",
        "platform/ingress/f5-nginx-values.yaml",
    ),
    "ML-routing-gateway-service-coi-log": (
        "platform_operator",
        "gitops",
        "platform/ingress/f5-nginx-values.yaml",
    ),
    "ML-routing-gateway-service-coi-trace": (
        "platform_operator",
        "gitops",
        "platform/ingress/f5-nginx-values.yaml",
    ),
    "ML-routing-gateway-web-api-k-o-d-li-u": (
        "platform_operator",
        "gitops",
        "platform/ingress/f5-nginx-values.yaml",
    ),
    "ML-routing-gateway-authentication-rate-limit-cho-": (
        "platform_operator",
        "gitops",
        "platform/ingress/f5-nginx-values.yaml",
    ),
    "ML-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-": (
        "platform_operator",
        "gitops",
        "platform/ingress/f5-nginx-values.yaml",
    ),
    "ML-iac-d-ng-terraform-setup-gke-ho-c-": (
        "platform_operator",
        "gitops",
        "terraform/envs/evidence/main.tf",
    ),
    "ML-iac-d-ng-ansible-configure-v-deplo": (
        "platform_operator",
        "gitops",
        "ansible/playbooks/vast-evidence-worker.yml",
    ),
    "ML-observability-web-api-metrics": (
        "platform_operator",
        "gitops",
        "platform/observability/prometheus-values.yaml",
    ),
    "ML-observability-collect-v-visualize-metrics-v-": (
        "platform_operator",
        "gitops",
        "platform/observability/prometheus-values.yaml",
    ),
    "ML-observability-t-ng-t-cho-logs": (
        "platform_operator",
        "gitops",
        "platform/observability/eck-otel-values.yaml",
    ),
    "ML-observability-t-ng-t-cho-traces": (
        "platform_operator",
        "gitops",
        "platform/observability/eck-otel-values.yaml",
    ),
    "ML-observability-airflow-data-drift-pipeline-to": (
        "data_engineer",
        "source",
        "dags/phase2/phase2_drift_monitoring.py",
    ),
    "ML-observability-trigger-retrain-by-calling-kub": (
        "ml_engineer",
        "source",
        "dags/phase2/phase2_drift_monitoring.py",
    ),
    "ML-a-b-testing-when-you-deploy-a-new-model": ("ml_engineer", "source", "src/ml/ab_router.py"),
    "ML-a-b-testing-monitoring-dashboard-to-monito": (
        "ml_engineer",
        "gitops",
        "platform/ml/ab-testing.yaml",
    ),
    "ML-security-centralize-secret-management": (
        "platform_operator",
        "gitops",
        "platform/security/vault-external-secrets.yaml",
    ),
    "ML-security-using-service-mesh-to-authoriz": (
        "platform_operator",
        "gitops",
        "platform/security/authorization-policies.yaml",
    ),
    "ML-repository-design-clean-code-clean-repo-demonstr": (
        "platform_operator",
        "source",
        "src/ml/contracts.py",
    ),
    "ML-documentation-low-level-ml-design": (
        "ml_engineer",
        "source",
        "docs/phase2/low-level-design.md",
    ),
    "ML-novel-ideas-idea-1": ("ml_engineer", "source", "src/ml/leakage_guard.py"),
    "ML-novel-ideas-idea-2": ("ml_engineer", "source", "src/ml/reproducibility_manifest.py"),
    "LLM-a-llm-inference-platform--llm-inference-platform-setup-c": (
        "llm_engineer",
        "gitops",
        "platform/inference/model-server.yaml",
    ),
    "LLM-a-llm-inference-platform--a-custom-model": (
        "llm_engineer",
        "source",
        "src/llm/model_server.py",
    ),
    "LLM-a-llm-inference-platform--benchmark-model-server-and-opt": (
        "llm_engineer",
        "source",
        "src/llm/benchmark.py",
    ),
    "LLM-1-global-model-config-c-c-1-global-model-config-c-c-agen": (
        "platform_operator",
        "gitops",
        "platform/agents/global-model-config.yaml",
    ),
    "LLM-registry-for-agent-theo-t-registry-for-agent-theo-tutori": (
        "platform_operator",
        "gitops",
        "platform/agents/agentregistry.yaml",
    ),
    "LLM-rag-rag-data-pipeline": ("data_engineer", "source", "src/llm/rag_pipeline.py"),
    "LLM-rag-m-b-o-data-governance-cho-pipe": (
        "data_engineer",
        "source",
        "src/llm/data_governance.py",
    ),
    "LLM-web-api-k-o-d-li-u-user-c-s-d-ng-fastapi-data-validati": (
        "data_engineer",
        "source",
        "apps/feature-mcp/app/main.py",
    ),
    "LLM-web-api-k-o-d-li-u-user-s-d-ng-async": (
        "data_engineer",
        "source",
        "apps/feature-mcp/app/main.py",
    ),
    "LLM-web-api-k-o-d-li-u-user-in-the-form-of-mcp-tool-to-k8s": (
        "platform_operator",
        "gitops",
        "charts/feature-mcp/Chart.yaml",
    ),
    "LLM-web-api-k-o-d-li-u-user-1-agent-s-d-ng-mcp-tool-tr-n-v": (
        "llm_engineer",
        "source",
        "src/agents/feature_agent.py",
    ),
    "LLM-web-api-k-o-d-li-u-user-agent-ch-y-trong-sandbox-m-b-o": (
        "llm_engineer",
        "gitops",
        "platform/agents/agent-sandbox.yaml",
    ),
    "LLM-web-api-k-o-d-li-u-user-publish-agent-tr-n-l-n-registr": (
        "llm_engineer",
        "gitops",
        "platform/agents/agentregistry.yaml",
    ),
    "LLM-web-api-cho-real-time-dri-c-s-d-ng-fastapi-data-validati": (
        "data_engineer",
        "source",
        "apps/drift-mcp/app/main.py",
    ),
    "LLM-web-api-cho-real-time-dri-s-d-ng-async": (
        "data_engineer",
        "source",
        "apps/drift-mcp/app/main.py",
    ),
    "LLM-web-api-cho-real-time-dri-in-the-form-of-mcp-tool-to-k8s": (
        "platform_operator",
        "gitops",
        "charts/drift-mcp/Chart.yaml",
    ),
    "LLM-web-api-cho-real-time-dri-1-agent-s-d-ng-mcp-tool-tr-n-v": (
        "llm_engineer",
        "source",
        "src/agents/drift_agent.py",
    ),
    "LLM-web-api-cho-real-time-dri-agent-ch-y-trong-sandbox-m-b-o": (
        "llm_engineer",
        "gitops",
        "platform/agents/agent-sandbox.yaml",
    ),
    "LLM-web-api-cho-real-time-dri-publish-agent-tr-n-l-n-registr": (
        "llm_engineer",
        "gitops",
        "platform/agents/agentregistry.yaml",
    ),
    "LLM-demonstrate-basic-underst-jupyter-notebooks-to-demonstra": (
        "llm_engineer",
        "source",
        "notebooks/agent-mcp-demo.ipynb",
    ),
    "LLM-demonstrate-basic-underst-jupyter-notebook-demonstrate-a": (
        "llm_engineer",
        "source",
        "notebooks/agent-understanding-demo.ipynb",
    ),
    "LLM-1-coordinator-agent-i-u-ph-i-2-agent-tr-n": (
        "llm_engineer",
        "source",
        "src/agents/coordinator.py",
    ),
    "LLM-1-coordinator-agent-publish-agent-n-y-l-n-registry": (
        "llm_engineer",
        "gitops",
        "platform/agents/agentregistry.yaml",
    ),
    "LLM-c-i-t-h-th-ng-ch-warm-up--c-i-t-h-th-ng-ch-warm-up-cho-a": (
        "llm_engineer",
        "gitops",
        "platform/agents/warm-pool.yaml",
    ),
    "LLM-validation-verification-validation-verification": (
        "llm_engineer",
        "source",
        "tests/phase2/requirements/test_llm_ac_10_validation.py",
    ),
    "LLM-validation-verification-c-s-d-ng-k-thu-t-equivalence-p": (
        "llm_engineer",
        "source",
        "tests/phase2/requirements/test_llm_ac_10_validation.py",
    ),
    "LLM-validation-verification-c-s-d-ng-mutation-testing-nh-g": (
        "llm_engineer",
        "source",
        "tests/phase2/requirements/test_llm_ac_10_validation.py",
    ),
    "LLM-validation-verification-idempotency-testing-s-d-ng-pro": (
        "llm_engineer",
        "source",
        "tests/phase2/requirements/test_llm_ac_10_validation.py",
    ),
    "LLM-validation-verification-load-test-the-web-api": (
        "data_engineer",
        "source",
        "tests/phase2/requirements/test_llm_ac_10_validation.py",
    ),
    "LLM-improve-the-data-generato-simulate-data-drift": (
        "data_engineer",
        "source",
        "src/drift/generator.py",
    ),
    "LLM-improve-the-data-generato-using-generator-configuration": (
        "data_engineer",
        "source",
        "src/drift/generator_config.py",
    ),
    "LLM-improve-the-data-generato-t-o-b-ng-label-c-2-c-t-id-v-la": (
        "data_engineer",
        "source",
        "src/ml/label_pipeline.py",
    ),
    "LLM-ci-cd-ci-cd-cho-rag-data-pipeline": (
        "data_engineer",
        "source",
        ".github/workflows/phase2-ci.yaml",
    ),
    "LLM-ci-cd-agent-k-o-d-li-u": ("llm_engineer", "source", ".github/workflows/phase2-ci.yaml"),
    "LLM-ci-cd-agent-drift-detection": (
        "llm_engineer",
        "source",
        ".github/workflows/phase2-ci.yaml",
    ),
    "LLM-ci-cd-agent-l-m-coordinator": (
        "llm_engineer",
        "source",
        ".github/workflows/phase2-ci.yaml",
    ),
    "LLM-ci-cd-job-1": ("data_engineer", "source", ".github/workflows/phase2-ci.yaml"),
    "LLM-ci-cd-job-2": ("data_engineer", "source", ".github/workflows/phase2-ci.yaml"),
    "LLM-routing-gateway-c-c-service-c-n-c-hide-ng-sau-": (
        "platform_operator",
        "gitops",
        "platform/ingress/f5-nginx-values.yaml",
    ),
    "LLM-routing-gateway-service-coi-log": (
        "platform_operator",
        "gitops",
        "platform/ingress/f5-nginx-values.yaml",
    ),
    "LLM-routing-gateway-service-coi-trace": (
        "platform_operator",
        "gitops",
        "platform/ingress/f5-nginx-values.yaml",
    ),
    "LLM-routing-gateway-ui-test-agent": (
        "platform_operator",
        "gitops",
        "platform/ingress/f5-nginx-values.yaml",
    ),
    "LLM-routing-gateway-ui-cho-agent-registry": (
        "platform_operator",
        "gitops",
        "platform/ingress/f5-nginx-values.yaml",
    ),
    "LLM-routing-gateway-authentication-cho-ui-test-age": (
        "platform_operator",
        "gitops",
        "platform/ingress/f5-nginx-values.yaml",
    ),
    "LLM-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-": (
        "platform_operator",
        "gitops",
        "platform/ingress/f5-nginx-values.yaml",
    ),
    "LLM-iac-d-ng-terraform-setup-gke-ho-c-": (
        "platform_operator",
        "gitops",
        "terraform/envs/evidence/main.tf",
    ),
    "LLM-iac-d-ng-ansible-configure-v-deplo": (
        "platform_operator",
        "gitops",
        "ansible/playbooks/vast-evidence-worker.yml",
    ),
    "LLM-observability-web-api-metrics": (
        "platform_operator",
        "gitops",
        "platform/observability/prometheus-values.yaml",
    ),
    "LLM-observability-collect-v-visualize-metrics-v-": (
        "platform_operator",
        "gitops",
        "platform/observability/prometheus-values.yaml",
    ),
    "LLM-observability-t-ng-t-cho-logs": (
        "platform_operator",
        "gitops",
        "platform/observability/loki-otel-values.yaml",
    ),
    "LLM-observability-t-ng-t-cho-traces": (
        "platform_operator",
        "gitops",
        "platform/observability/loki-otel-values.yaml",
    ),
    "LLM-observability-m-b-o-t-nh-t-c-c-metrics": (
        "platform_operator",
        "gitops",
        "platform/observability/prometheus-values.yaml",
    ),
    "LLM-observability-agent-tool-call-metrics": (
        "platform_operator",
        "gitops",
        "platform/observability/prometheus-values.yaml",
    ),
    "LLM-a-b-testing-when-you-deploy-a-new-model": (
        "llm_engineer",
        "gitops",
        "platform/llm/ab-testing.yaml",
    ),
    "LLM-a-b-testing-perform-a-b-test-for-different": (
        "llm_engineer",
        "gitops",
        "platform/llm/ab-testing.yaml",
    ),
    "LLM-security-centralize-secret-management": (
        "platform_operator",
        "gitops",
        "platform/security/sealed-secrets.yaml",
    ),
    "LLM-repository-design-clean-code-clean-repo-demonstr": (
        "platform_operator",
        "source",
        "src/llm/contracts.py",
    ),
    "LLM-documentation-low-level-ml-design": (
        "llm_engineer",
        "source",
        "docs/phase2/low-level-design.md",
    ),
    "LLM-novel-ideas-idea-1": ("llm_engineer", "source", "src/llm/embedding_registry.py"),
    "LLM-novel-ideas-idea-2": ("llm_engineer", "source", "src/llm/citation_guard.py"),
}


ACCEPTANCE_BY_SECTION = {
    "ML": {
        "Web API kéo dữ liệu": "ML-AC-01-WEB-API",
        "Web API cho Real-time Drift Detection": "ML-AC-02-DRIFT-API",
        "Autoscale": "ML-AC-03-AUTOSCALE",
        "Validation & Verification": "ML-AC-04-VALIDATION",
        "Improve the Data Generator": "ML-AC-05-DATA-GENERATOR",
        "Feature Store": "ML-AC-06-FEAST",
        "ML": "ML-AC-07-ML-UNDERSTANDING",
        "ML Pipelines": "ML-AC-08-PIPELINES",
        "Versioning": "ML-AC-09-VERSIONING",
        "CI/CD": "ML-AC-10-CICD",
        "Routing & Gateway (NGINX Ingress Controller)": "ML-AC-11-ROUTING",
        "IaC": "ML-AC-12-IAC",
        "Observability": "ML-AC-13-OBSERVABILITY",
        "A/B Testing": "ML-AC-14-AB",
        "Security": "ML-AC-15-SECURITY",
        "Repository Design": "ML-AC-16-REPOSITORY",
        "Documentation": "ML-AC-17-DOCUMENTATION",
        "Novel ideas": "ML-AC-18-NOVEL",
    },
    "LLM": {
        (
            "Deploy a LLM inference platform theo hướng dẫn này và set up gateway "
            "cho agent theo hướng dẫn này"
        ): "LLM-AC-01-INFERENCE",
        (
            "Deploy 1 global model config để các Agent có thể dùng follow tutorial này, "
            "config này sẽ link tới inference platform ở trên thông qua cái agent "
            "gateway đề cập ở trên nốt"
        ): "LLM-AC-02-MODEL-CONFIG",
        "Deploy registry for agent theo tutorial này": "LLM-AC-03-REGISTRY",
        "RAG": "LLM-AC-04-RAG",
        (
            "Web API kéo dữ liệu user (đã lưu thông qua feature pipeline) và chunk "
            "(đã được lưu thông qua RAG pipeline)"
        ): "LLM-AC-05-FEATURE-RAG-API",
        (
            "Web API cho Real-time Drift Detection (để làm MCP tool, tương tự như trên)"
        ): "LLM-AC-06-DRIFT-MCP",
        "Demonstrate basic understanding of Agents": "LLM-AC-07-AGENT-UNDERSTANDING",
        "Deploy 1 Coordinator Agent": "LLM-AC-08-COORDINATOR",
        (
            "Cài đặt hệ thống ở chế độ Warm Up cho agent theo hướng dẫn sau để tối ưu "
            "chi phí, đồng thời giảm thiểu thời gian startup"
        ): "LLM-AC-09-WARMUP",
        "Validation & Verification": "LLM-AC-10-VALIDATION",
        "Improve the Data Generator": "LLM-AC-11-DATA-GENERATOR",
        "CI/CD": "LLM-AC-12-CICD",
        "Routing & Gateway (NGINX Ingress Controller)": "LLM-AC-13-ROUTING",
        "IaC": "LLM-AC-14-IAC",
        "Observability": "LLM-AC-15-OBSERVABILITY",
        "A/B Testing": "LLM-AC-16-AB",
        "Security": "LLM-AC-17-SECURITY",
        "Repository Design": "LLM-AC-18-REPOSITORY",
        "Documentation": "LLM-AC-19-DOCUMENTATION",
        "Novel ideas": "LLM-AC-20-NOVEL",
    },
}


def _source_digest(cells: list[str]) -> str:
    """Hash normalized canonical source cells without relying on totals."""
    normalized = [" ".join(cell.split()) for cell in cells[:5]]
    return hashlib.sha256("\x1f".join(normalized).encode("utf-8")).hexdigest()


def _assign_owner(track: str, section: str, requirement: str, deliverables: str) -> str:
    """Assign a role-based owner from the locked taxonomy.

    Rule order (first match wins):
      1. ML-engineer intent (model versioning, training, MLflow, "basic
         understanding of ML" notebooks, trigger-retrain) — must precede data
         content so an ML demonstration row that happens to read from Feast's
         offline store is owned by the ML engineer, not the data engineer
      2. LLM-agent intent (MCP tools, coordinator, registry publication,
         agent demonstration notebooks)
      3. LLM custom-model/benchmark work
      4. A/B testing → track owner (ML or LLM)
      5. data-engineer content (Feast, materialization, generator, labels)
      6. platform-operator section heads (CI/CD, gateway, IaC, autoscale,
         observability, security, repository design, warm-up)
      7. platform-operator content (helm, terraform, mesh, gateway config)
      8. data-engineer section heads (data web APIs, generator, RAG)
      9. track default (ml_engineer / llm_engineer)
    """
    head = section.split("\n")[0].lower()
    blob = " ".join([requirement.lower(), deliverables.lower()])

    if any(k in blob for k in _ML_CONTENT):
        return "ml_engineer"
    if any(k in blob for k in _AGENT_CONTENT):
        return "llm_engineer"
    if any(k in blob for k in _CUSTOM_MODEL_CONTENT):
        return "llm_engineer"
    if "a/b" in head or "a/b test" in blob or "a-b test" in blob:
        return "ml_engineer" if track == "ML" else "llm_engineer"
    if any(k in blob for k in _DATA_CONTENT):
        return "data_engineer"
    if any(k in head for k in _PLATFORM_HEAD):
        return "platform_operator"
    if any(k in blob for k in _PLATFORM_CONTENT):
        return "platform_operator"
    if any(k in head for k in _DATA_HEAD):
        return "data_engineer"
    return "ml_engineer" if track == "ML" else "llm_engineer"


def _parse_csv(csv_path: Path, track: str) -> list[dict[str, object]]:
    """Parse a rubric CSV into a flat list of scored-row dicts.

    Logic
    -----
    - The header row (idx 0) has 5 columns: A,B,C,D(Proof),E(Point).
    - A row where column E is a positive integer is a *scored row*.
    - When column A of a scored row is non-empty, it's the top-level
      item and becomes the current parent context.
    - When column A is empty, the row inherits from the current parent.
    - The deliverable text is the most specific non-empty column among
      B, C, and D.
    - The Proof column (D) carries the required evidence screenshot/text.
    - The E row with Points='Sum' (total row) is skipped.
    """
    contents = csv_path.read_text(encoding="utf-8", errors="replace")
    reader = csv.reader(io.StringIO(contents))
    all_rows = list(reader)

    current_parent: str = ""
    current_section: str = track + "-section"
    current_proof: str = ""
    out: list[dict[str, object]] = []

    for source_row_index, raw_row in enumerate(all_rows[1:], start=1):  # skip header
        if not raw_row or all(v.strip() == "" for v in raw_row):
            continue

        cells = list(raw_row)
        while len(cells) < 5:
            cells.append("")

        a = cells[0].strip()
        b = cells[1].strip()
        c = cells[2].strip()
        d = cells[3].strip()
        e = cells[4].strip()

        # Determine points
        try:
            points = int(e)
        except (ValueError, TypeError):
            points = 0

        if not points and not a and not b and not c and not d:
            continue
        # Skip Sum row
        if d.lower() == "sum" and a == "" and b == "" and c == "":
            continue

        # Non-scored header / category row — carry forward as section
        if not points and a:
            # Skip the README instruction block (it's not a rubric section)
            if a.startswith("Viết file README.md"):
                current_parent = "README"
                continue
            current_section = a
            current_parent = a
            continue

        # Non-scored desc row (parent with no points) — update parent only
        if not points:
            if a:
                current_parent = a
            continue

        # --- Scored row ---
        # Determine the semantic parent context and primary requirement text
        if a:
            # A is non-empty: this is a new parent row
            parent = a
            current_parent = a
            current_section = a  # A acts as the section/group label
            current_proof = d if d else current_proof
            # Requirement: combine A + B
            req = a
            if b:
                req = a + " — " + b
            proof = d if d else current_proof
            deliverables = c if c else d if d else b
            # Use A as the slug context — first meaningful fragment only
            slug_parent = _smart_slug(a, 25)
        else:
            parent = current_parent
            # For sub-rows, the deliverable is in C or B or D
            req = c or b or d or parent
            proof = d if d else current_proof
            deliverables = c if c else req
            slug_parent = _smart_slug(current_parent, 25)

        # Generate semantic ID: ML/LLM + parent slug + unique delimiter
        child_src = c or b or d if not a else b or a
        slug_child = _smart_slug(child_src, 30) if child_src else "item"
        rid = f"{track}-{slug_parent}-{slug_child}" if slug_child else f"{track}-{slug_parent}"

        # Taxonomy — role-based owner from the locked ruleset
        owner = _assign_owner(track, current_section, req, deliverables)

        # Contract test proves the mapping exists. The behavior-validation
        # command is a distinct future gate that must execute before Phase 8.
        test = "pytest tests/phase2 -k '" + rid + "'"

        etype: str = "design_only"

        section_key = current_section.strip().split("\n")[0].strip()
        acceptance_id = ACCEPTANCE_BY_SECTION.get(track, {}).get(section_key, "")
        validation_slug = acceptance_id.lower().replace("-", "_")
        validation_command = (
            f"pytest tests/phase2/requirements/test_{validation_slug}.py -k '{rid}'"
        )
        out.append(
            {
                "rubric_id": rid,
                "track": track,
                "section": current_section,
                "points": points,
                "requirement": req,
                "proof": proof,
                "deliverables": deliverables,
                "owner": owner,
                "test": test,
                "validation_command": validation_command,
                "evidence_path": f"docs/phase2/evidence/{track.lower()}/{rid}.md",
                "evidence_type": etype,
                "acceptance_id": acceptance_id,
                "source_file": csv_path.relative_to(REPO_ROOT).as_posix(),
                "source_row_index": source_row_index,
                "source_digest": _source_digest(cells),
                "artifact_repo": "",
                "artifact_path": "",
                "behavioral_assertion": "",
            }
        )

        if not a:
            # Keep parent context for the next row
            pass

    return out


# -- Build ITEMS ------------------------------------------------------------------


_ML_PATH = DOCS / "Coursework Tracking (Public) - rubic final-coursework (final - ml).csv"
_LLM_PATH = DOCS / "Coursework Tracking (Public) - rubic final-coursework (final - llm).csv"


_RAW_ML = _parse_csv(_ML_PATH, "ML")
_RAW_LLM = _parse_csv(_LLM_PATH, "LLM")


# A numeric dedup suffix (below) keeps the un-suffixed id as an exact prefix
# of the suffixed one, so `pytest -k '<base>'` — the exact command every row's
# own validation_command carries — matches both rows instead of one. `-k`
# does substring search, not prefix/anchor matching, and there is no numeric
# suffix that fixes this; only a slug describing what actually differs does.
# Content-based renames for the two pairs found to collide this way (verified
# 2026-08-07 — every other `-N` suffix in the matrix does not share a prefix
# with an unsuffixed sibling id, so this table stays this small on purpose).
_COLLISION_RENAMES = {
    "LLM-observability-m-b-o-t-nh-t-c-c-metrics-1": "LLM-observability-agent-tool-call-metrics",
    "ML-feature-store-job-ch-u-tr-ch-nhi-m-push-stre-1": "ML-feature-store-job-online-store-push",
}

# De-duplicate semantic IDs (slugs may collide for very similar rows). Any
# field derived from the id — the validation command and the evidence path —
# must be regenerated against the final deduplicated id so `pytest -k '<rid>'`
# matches exactly one contract test.
_seen: set[str] = set()
_deduped: list[dict[str, object]] = []
for row in _RAW_ML + _RAW_LLM:
    rid = str(row["rubric_id"])
    track = str(row["track"])
    n = 1
    while rid in _seen:
        original = rid
        rid = f"{original}-{n}"
        n += 1
    rid = _COLLISION_RENAMES.get(rid, rid)
    _seen.add(rid)
    row["rubric_id"] = rid
    row["test"] = "pytest tests/phase2 -k '" + rid + "'"
    row["evidence_path"] = f"docs/phase2/evidence/{track.lower()}/{rid}.md"
    acceptance_id = str(row["acceptance_id"])
    validation_slug = acceptance_id.lower().replace("-", "_")
    row["validation_command"] = (
        f"pytest tests/phase2/requirements/test_{validation_slug}.py -k '{rid}'"
    )
    try:
        mapped_owner, artifact_repo, artifact_path = EXPLICIT_IMPLEMENTATION[rid]
    except KeyError as exc:
        raise ValueError(f"Missing explicit implementation mapping for {rid}") from exc
    if mapped_owner != row["owner"]:
        raise ValueError(f"Owner mismatch for {rid}: rubric={row['owner']!r}, map={mapped_owner!r}")
    row["artifact_repo"] = artifact_repo
    row["artifact_path"] = artifact_path
    row["behavioral_assertion"] = _behavioral_assertion(rid, artifact_path)
    _deduped.append(row)


EXECUTED_RUBRIC_IDS = {
    "LLM-ci-cd-job-1",
    "LLM-ci-cd-job-2",
    "LLM-improve-the-data-generato-simulate-data-drift",
    "LLM-improve-the-data-generato-t-o-b-ng-label-c-2-c-t-id-v-la",
    "LLM-improve-the-data-generato-using-generator-configuration",
    "LLM-rag-m-b-o-data-governance-cho-pipe",
    "LLM-rag-rag-data-pipeline",
    "LLM-iac-d-ng-terraform-setup-gke-ho-c-",
    "LLM-iac-d-ng-ansible-configure-v-deplo",
    "LLM-security-centralize-secret-management",
    "LLM-a-llm-inference-platform--llm-inference-platform-setup-c",
    "LLM-a-llm-inference-platform--a-custom-model",
    "LLM-a-llm-inference-platform--benchmark-model-server-and-opt",
    "LLM-1-global-model-config-c-c-1-global-model-config-c-c-agen",
    "LLM-web-api-k-o-d-li-u-user-c-s-d-ng-fastapi-data-validati",
    "LLM-web-api-k-o-d-li-u-user-s-d-ng-async",
    "LLM-web-api-k-o-d-li-u-user-in-the-form-of-mcp-tool-to-k8s",
    "LLM-web-api-k-o-d-li-u-user-1-agent-s-d-ng-mcp-tool-tr-n-v",
    "LLM-web-api-k-o-d-li-u-user-agent-ch-y-trong-sandbox-m-b-o",
    "LLM-web-api-k-o-d-li-u-user-publish-agent-tr-n-l-n-registr",
    "LLM-web-api-cho-real-time-dri-c-s-d-ng-fastapi-data-validati",
    "LLM-web-api-cho-real-time-dri-s-d-ng-async",
    "LLM-web-api-cho-real-time-dri-in-the-form-of-mcp-tool-to-k8s",
    "LLM-web-api-cho-real-time-dri-1-agent-s-d-ng-mcp-tool-tr-n-v",
    "LLM-web-api-cho-real-time-dri-agent-ch-y-trong-sandbox-m-b-o",
    "LLM-web-api-cho-real-time-dri-publish-agent-tr-n-l-n-registr",
    "LLM-registry-for-agent-theo-t-registry-for-agent-theo-tutori",
    "LLM-1-coordinator-agent-i-u-ph-i-2-agent-tr-n",
    "LLM-1-coordinator-agent-publish-agent-n-y-l-n-registry",
    "LLM-ci-cd-ci-cd-cho-rag-data-pipeline",
    "LLM-ci-cd-agent-k-o-d-li-u",
    "LLM-ci-cd-agent-drift-detection",
    "LLM-ci-cd-agent-l-m-coordinator",
    "LLM-validation-verification-validation-verification",
    "LLM-validation-verification-c-s-d-ng-k-thu-t-equivalence-p",
    "LLM-validation-verification-c-s-d-ng-mutation-testing-nh-g",
    "LLM-validation-verification-idempotency-testing-s-d-ng-pro",
    "LLM-validation-verification-load-test-the-web-api",
    "LLM-repository-design-clean-code-clean-repo-demonstr",
    "LLM-c-i-t-h-th-ng-ch-warm-up--c-i-t-h-th-ng-ch-warm-up-cho-a",
    "LLM-a-b-testing-perform-a-b-test-for-different",
    "LLM-a-b-testing-when-you-deploy-a-new-model",
    "LLM-demonstrate-basic-underst-jupyter-notebook-demonstrate-a",
    "LLM-demonstrate-basic-underst-jupyter-notebooks-to-demonstra",
    "LLM-novel-ideas-idea-1",
    "LLM-novel-ideas-idea-2",
    "LLM-documentation-low-level-ml-design",
}
for row in _deduped:
    if row["rubric_id"] in EXECUTED_RUBRIC_IDS:
        row["evidence_type"] = "executed"
    _validate_executed_behavioral_assertion(row)

if set(EXPLICIT_IMPLEMENTATION) != _seen:
    missing = sorted(_seen - set(EXPLICIT_IMPLEMENTATION))
    extra = sorted(set(EXPLICIT_IMPLEMENTATION) - _seen)
    raise ValueError(f"Explicit implementation map mismatch: missing={missing}, extra={extra}")


@dataclass(frozen=True)
class Phase2RubricItem:
    rubric_id: str
    track: str
    section: str
    points: int
    requirement: str
    proof: str
    deliverables: str
    owner: str
    test: str = ""
    validation_command: str = ""
    evidence_path: str = ""
    evidence_type: str = "executed"
    acceptance_id: str = ""
    source_file: str = ""
    source_row_index: int = 0
    source_digest: str = ""
    artifact_repo: str = ""
    artifact_path: str = ""
    behavioral_assertion: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> Phase2RubricItem:
        return cls(
            rubric_id=str(d.get("rubric_id", "")),
            track=str(d.get("track", "")),
            section=str(d.get("section", "")),
            points=int(d.get("points", 0)),  # type: ignore[arg-type]
            requirement=str(d.get("requirement", "")),
            proof=str(d.get("proof", "")),
            deliverables=str(d.get("deliverables", "")),
            owner=str(d.get("owner", "")),
            test=str(d.get("test", "")),
            validation_command=str(d.get("validation_command", "")),
            evidence_path=str(d.get("evidence_path", "")),
            evidence_type=str(d.get("evidence_type", "executed")),
            acceptance_id=str(d.get("acceptance_id", "")),
            source_file=str(d.get("source_file", "")),
            source_row_index=int(d.get("source_row_index", 0)),  # type: ignore[arg-type]
            source_digest=str(d.get("source_digest", "")),
            artifact_repo=str(d.get("artifact_repo", "")),
            artifact_path=str(d.get("artifact_path", "")),
            behavioral_assertion=str(d.get("behavioral_assertion", "")),
        )


ITEMS: tuple[Phase2RubricItem, ...] = tuple(Phase2RubricItem.from_dict(d) for d in _deduped)


# -- Public API --------------------------------------------------------------


def total_points(track: str) -> int:
    return sum(item.points for item in ITEMS if item.track == track)


def by_track() -> dict[str, list[Phase2RubricItem]]:
    out: dict[str, list[Phase2RubricItem]] = {"ML": [], "LLM": []}
    for item in ITEMS:
        out[item.track].append(item)
    return out


def by_section(track: str) -> dict[str, list[Phase2RubricItem]]:
    out: dict[str, list[Phase2RubricItem]] = {}
    for item in ITEMS:
        if item.track != track:
            continue
        out.setdefault(item.section, []).append(item)
    return out


def validate_matrix() -> tuple[list[str], bool]:
    """Return (errors, is_valid).  Checks completeness, sums, ids, etc."""
    errors: list[str] = []

    ml_total = total_points("ML")
    llm_total = total_points("LLM")
    if ml_total != 100:
        errors.append(f"ML total points = {ml_total}, expected 100")
    if llm_total != 100:
        errors.append(f"LLM total points = {llm_total}, expected 100")

    owners_seen: set[str] = set()
    for item in ITEMS:
        if not item.rubric_id:
            errors.append(f"row without rubric_id: requirement='{item.requirement[:40]}'")
            continue
        if item.points <= 0:
            errors.append(f"{item.rubric_id}: missing or zero points ({item.points})")
        if not item.requirement:
            errors.append(f"{item.rubric_id}: missing requirement text")
        if not item.proof:
            errors.append(f"{item.rubric_id}: missing Proof")
        if not item.deliverables:
            errors.append(f"{item.rubric_id}: missing Deliverables")
        if not item.owner:
            errors.append(f"{item.rubric_id}: missing owner")
        if item.owner not in VALID_OWNERS:
            errors.append(f"{item.rubric_id}: owner '{item.owner}' not a recognized role")
        owners_seen.add(item.owner)
        if not item.test:
            errors.append(f"{item.rubric_id}: missing contract test")
        if not item.validation_command:
            errors.append(f"{item.rubric_id}: missing behavior validation command")
        if not item.evidence_path:
            errors.append(f"{item.rubric_id}: missing evidence_path")
        if not item.acceptance_id:
            errors.append(f"{item.rubric_id}: missing acceptance_id")
        if not item.source_file:
            errors.append(f"{item.rubric_id}: missing source_file")
        if item.source_row_index <= 0:
            errors.append(f"{item.rubric_id}: invalid source_row_index")
        if not re.fullmatch(r"[0-9a-f]{64}", item.source_digest):
            errors.append(f"{item.rubric_id}: invalid source_digest")
        expected_validation = (
            "pytest tests/phase2/requirements/test_"
            f"{item.acceptance_id.lower().replace('-', '_')}.py -k '{item.rubric_id}'"
        )
        if item.validation_command != expected_validation:
            errors.append(
                f"{item.rubric_id}: validation command is not bound to its acceptance row"
            )
        if item.rubric_id not in EXPLICIT_IMPLEMENTATION:
            errors.append(f"{item.rubric_id}: missing explicit implementation map entry")
        if item.artifact_repo not in {"source", "gitops"}:
            errors.append(f"{item.rubric_id}: invalid artifact_repo '{item.artifact_repo}'")
        if not item.artifact_path:
            errors.append(f"{item.rubric_id}: missing artifact_path (exact implementation)")
        elif item.artifact_repo == "source" and not item.artifact_path.startswith(
            SOURCE_ARTIFACT_ROOTS
        ):
            errors.append(
                f"{item.rubric_id}: artifact_path '{item.artifact_path}' not under "
                f"an allowed source root {SOURCE_ARTIFACT_ROOTS}"
            )
        elif item.artifact_repo == "gitops" and not item.artifact_path.startswith(
            GITOPS_ARTIFACT_ROOTS
        ):
            errors.append(
                f"{item.rubric_id}: artifact_path '{item.artifact_path}' not under "
                f"an allowed GitOps root {GITOPS_ARTIFACT_ROOTS}"
            )
        if not item.behavioral_assertion:
            errors.append(f"{item.rubric_id}: missing behavioral_assertion")
        if item.evidence_type == "executed":
            expected_assertion = EXECUTED_BEHAVIORAL_ASSERTIONS.get(item.rubric_id)
            if item.behavioral_assertion != expected_assertion:
                errors.append(
                    f"{item.rubric_id}: executed row lacks its reviewed behavioral assertion"
                )
        if item.evidence_type not in ("executed", "design_only", "stretch"):
            errors.append(f"{item.rubric_id}: bad evidence_type '{item.evidence_type}'")

    # Every role must own at least one scored row (locked taxonomy)
    for role in VALID_OWNERS:
        if role not in owners_seen:
            errors.append(f"owner '{role}' owns no scored row in the rubric matrix")

    return errors, len(errors) == 0


def export_matrix_csv() -> str:
    """Export all items as a single-line-per-row CSV string."""
    header = (
        "rubric_id,track,section,points,requirement,proof,deliverables,"
        "owner,test,validation_command,evidence_path,evidence_type,acceptance_id,"
        "source_file,source_row_index,source_digest,artifact_repo,artifact_path,"
        "behavioral_assertion\n"
    )
    lines = []

    def _clean(value: str) -> str:
        return value.replace("\n", "; ").replace('"', '""')

    for item in sorted(ITEMS, key=lambda i: (i.track, i.rubric_id)):
        section = _clean(item.section)
        req = _clean(item.requirement)
        proof = _clean(item.proof)
        deliverables = _clean(item.deliverables)
        acceptance_id = _clean(item.acceptance_id)
        test = _clean(item.test)
        validation_command = _clean(item.validation_command)
        lines.append(
            f'{item.rubric_id},{item.track},"{section}",{item.points},'
            f'"{req}","{proof}","{deliverables}",'
            f'{item.owner},"{test}","{validation_command}",{item.evidence_path},'
            f'{item.evidence_type},"{acceptance_id}",{item.source_file},'
            f"{item.source_row_index},{item.source_digest},{item.artifact_repo},"
            f'{item.artifact_path},"{_clean(item.behavioral_assertion)}"'
        )
    return header + "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Regenerate the committed matrix, or check it for drift."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 when the CSV is stale")
    args = parser.parse_args(argv)
    path = DOCS / "phase2" / "rubric-matrix.csv"
    expected = export_matrix_csv()
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if args.check:
        if current != expected:
            print(f"stale/missing: {path.relative_to(REPO_ROOT)}", file=sys.stderr)
            return 1
        print("✅ rubric matrix is up to date.")
        return 0
    path.write_text(expected, encoding="utf-8")
    print(f"✅ wrote {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
