"""
Target architecture verifier (plan phase-03-contracts-rubric.md, Step 6).

One check per component/annotated edge in
``images/architecture/fdd-architecture-full-4k.png`` (83 total, from
``reports/debate-proposal.md`` Section 10). The source table's own Phase
column uses the predecessor plan's 10-phase numbering and is stale; every
component below is re-mapped against each current phase file's ``owns:``
frontmatter, not against the source table's Phase column.

Each check is a live cluster probe: it looks for a real Kubernetes
resource, namespace, or object matching the component. Against an empty
cluster every check fails, so the script exits non-zero listing all 83 as
missing (AC-P3-6) -- this is the expected baseline result, not a bug.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class TargetComponent:
    number: int
    name: str
    image_location: str
    change_class: str  # A restore, B bind, C build, D drift, E exists unchanged
    owning_phase: str
    # kubectl probe: (resource_type, namespace or None for cluster-scoped, name_substring)
    probe: tuple[str, str | None, str]


TARGET_COMPONENTS: tuple[TargetComponent, ...] = (
    TargetComponent(
        1,
        "Analytic Stakeholder (watch dashboard)",
        "top, external",
        "E",
        "P9",
        ("resource", None, "analytic stakeholder"),
    ),
    TargetComponent(
        2, "Web user (access)", "left, external", "E", "P9", ("resource", None, "web user")
    ),
    TargetComponent(
        3,
        "Developer (git push / git merge)",
        "left, external",
        "E",
        "P10",
        ("resource", None, "developer"),
    ),
    TargetComponent(
        4,
        "GitHub (SCM + webhook trigger)",
        "left, external",
        "E",
        "P10",
        ("resource", None, "github"),
    ),
    TargetComponent(
        5,
        "Terraform (provision, IaC)",
        "left, external",
        "E",
        "P6",
        ("resource", None, "terraform"),
    ),
    TargetComponent(6, "Ansible", "left, external", "E", "P6", ("resource", None, "ansible")),
    TargetComponent(
        7, "GKE / Kubernetes", "left + top-right", "E", "P6", ("resource", None, "gke / kubernetes")
    ),
    TargetComponent(
        8,
        "Vietnam API HOSE/HNX Stock (streaming event)",
        "left of dataflow",
        "E",
        "P4",
        ("resource", None, "vietnam api hose/hnx stock"),
    ),
    TargetComponent(
        9,
        "financial-distress-gitops repo",
        "bottom",
        "E",
        "P10",
        ("resource", None, "financial-distress-gitops repo"),
    ),
    TargetComponent(
        10,
        "Argo CD (reconcile/sync, argo watch)",
        "bottom",
        "E",
        "P10",
        ("resource", None, "argo cd"),
    ),
    TargetComponent(
        11,
        "NGINX System Controller",
        "ns: ingress",
        "E",
        "P9",
        ("resource", "ingress", "nginx system controller"),
    ),
    TargetComponent(
        12, "cert-manager", "ns: ingress", "E", "P9", ("resource", "ingress", "cert-manager")
    ),
    TargetComponent(
        13,
        "Next.js UI + Route Handlers",
        "ns: web",
        "C",
        "P9",
        ("resource", "web", "next.js ui + route handlers"),
    ),
    TargetComponent(
        14,
        "prediction-api",
        "ns: api-serving",
        "C",
        "P9",
        ("resource", "api-serving", "prediction-api"),
    ),
    TargetComponent(
        15,
        "feature-api (get online features)",
        "ns: api-serving",
        "A",
        "P9",
        ("resource", "api-serving", "feature-api"),
    ),
    TargetComponent(
        16,
        "feature-mcp (http -> feature-api)",
        "ns: api-serving",
        "E",
        "P8",
        ("resource", "api-serving", "feature-mcp"),
    ),
    TargetComponent(
        17, "drift-api", "ns: api-serving", "A", "P9", ("resource", "api-serving", "drift-api")
    ),
    TargetComponent(
        18, "drift-mcp", "ns: api-serving", "E", "P8", ("resource", "api-serving", "drift-mcp")
    ),
    TargetComponent(
        19,
        "KEDA (autoscale api-serving)",
        "ns: api-serving",
        "C+A",
        "P9",
        ("resource", "api-serving", "keda"),
    ),
    TargetComponent(
        20,
        "kagent controllers + CRDs",
        "ns: agents",
        "E",
        "P8",
        ("resource", "agents", "kagent controllers + crds"),
    ),
    TargetComponent(
        21,
        "Coordinator Agent (replicas=3 + autoscale)",
        "Sandbox",
        "E",
        "P8",
        ("resource", None, "coordinator agent"),
    ),
    TargetComponent(22, "Feature Agent", "Sandbox", "E", "P8", ("resource", None, "feature agent")),
    TargetComponent(23, "Drift Agent", "Sandbox", "E", "P8", ("resource", None, "drift agent")),
    TargetComponent(
        24,
        "agentgateway (retained egress boundary)",
        "implied by basic auth + rate limit edge",
        "E",
        "P8",
        ("resource", None, "agentgateway"),
    ),
    TargetComponent(
        25, "Superset", "ns: analytic", "C", "P9", ("resource", "analytic", "superset")
    ),
    TargetComponent(
        26, "Trino (Run SQL)", "ns: analytic", "C", "P9", ("resource", "analytic", "trino")
    ),
    TargetComponent(
        27, "dbt - Build Gold Data Mart", "ns: analytic", "C", "P9", ("resource", "analytic", "dbt")
    ),
    TargetComponent(
        28,
        "Data Generator (simulate batch ingestion)",
        "ns: dataflow",
        "E",
        "P4",
        ("resource", "dataflow", "data generator"),
    ),
    TargetComponent(
        29, "MinIO (object storage)", "ns: dataflow", "A", "P4", ("resource", "dataflow", "minio")
    ),
    TargetComponent(
        30,
        "Iceberg + Lakekeeper REST catalog",
        "ns: dataflow",
        "B+A",
        "P4",
        ("resource", "dataflow", "iceberg + lakekeeper rest catalog"),
    ),
    TargetComponent(
        31, "Bronze tables", "ns: dataflow", "B", "P4", ("resource", "dataflow", "bronze tables")
    ),
    TargetComponent(
        32,
        "Silver/Gold tables",
        "ns: dataflow",
        "B",
        "P4",
        ("resource", "dataflow", "silver/gold tables"),
    ),
    TargetComponent(
        33,
        "gold.distress_holdout @ tag holdout-v1",
        "ns: dataflow",
        "C",
        "P4",
        ("resource", "dataflow", "gold.distress_holdout @ tag holdout-v1"),
    ),
    TargetComponent(
        34,
        "Spark - batch feature engineering",
        "ns: dataflow",
        "B",
        "P4",
        ("resource", "dataflow", "spark"),
    ),
    TargetComponent(
        35,
        "Source system (Postgres, logical WAL)",
        "ns: dataflow",
        "C",
        "P5",
        ("resource", "dataflow", "source system"),
    ),
    TargetComponent(
        36, "Debezium", "ns: dataflow", "B", "P5", ("resource", "dataflow", "debezium")
    ),
    TargetComponent(37, "Kafka", "ns: dataflow", "A", "P5", ("resource", "dataflow", "kafka")),
    TargetComponent(
        38,
        "Flink - realtime feature engineering",
        "ns: dataflow",
        "A+B",
        "P5",
        ("resource", "dataflow", "flink"),
    ),
    TargetComponent(39, "Feast", "ns: dataflow", "B", "P5", ("resource", "dataflow", "feast")),
    TargetComponent(
        40,
        "FEAST offline store (Postgres)",
        "ns: dataflow",
        "C",
        "P5",
        ("resource", "dataflow", "feast offline store"),
    ),
    TargetComponent(
        41,
        "FEAST online store (Redis)",
        "ns: dataflow",
        "E",
        "P5",
        ("resource", "dataflow", "feast online store"),
    ),
    TargetComponent(
        42,
        "Airflow (trigger sync/materialize, drift DAG, daily DAG, retrain trigger)",
        "adjacent to dataflow",
        "A",
        "P4",
        ("resource", None, "airflow"),
    ),
    TargetComponent(
        43, "DataHub", "adjacent to dataflow", "B", "P4", ("resource", None, "datahub")
    ),
    TargetComponent(
        44,
        "Kubeflow Pipeline",
        "ns: kubeflow",
        "C",
        "P7",
        ("resource", "kubeflow", "kubeflow pipeline"),
    ),
    TargetComponent(
        45,
        "Ray Cluster (distributed training)",
        "ns: kubeflow",
        "B+C",
        "P7",
        ("resource", "kubeflow", "ray cluster"),
    ),
    TargetComponent(46, "MLflow", "ns: tracking", "B+C", "P7", ("resource", "tracking", "mlflow")),
    TargetComponent(
        47,
        "Postgres - metadata + registry",
        "ns: tracking",
        "C",
        "P7",
        ("resource", "tracking", "postgres"),
    ),
    TargetComponent(
        48,
        "MinIO - checkpoint + model artifacts",
        "ns: tracking",
        "C",
        "P7",
        ("resource", "tracking", "minio"),
    ),
    TargetComponent(
        49, "KServe (operator, 0.18)", "ns: kserve", "D", "P8", ("resource", "kserve", "kserve")
    ),
    TargetComponent(
        50,
        "NVIDIA Triton InferenceService",
        "ns: kserve",
        "C",
        "P7",
        ("resource", "kserve", "nvidia triton inferenceservice"),
    ),
    TargetComponent(
        51,
        "canaryTrafficPercent 10->25->50",
        "ns: kserve",
        "C",
        "P7",
        ("resource", "kserve", "canarytrafficpercent 10->25->50"),
    ),
    TargetComponent(
        52,
        "Gateway / GatewayClass: istio / ClusterIP",
        "ns: kserve",
        "C",
        "P8",
        ("resource", "kserve", "gateway / gatewayclass: istio / clusterip"),
    ),
    TargetComponent(
        53,
        "HTTPRoute group llm-ab",
        "ns: kserve",
        "C",
        "P8",
        ("resource", "kserve", "httproute group llm-ab"),
    ),
    TargetComponent(
        54, "llm-d isvc-a (w=9)", "ns: kserve", "C", "P8", ("resource", "kserve", "llm-d isvc-a")
    ),
    TargetComponent(
        55, "llm-d isvc-b (w=1)", "ns: kserve", "C", "P8", ("resource", "kserve", "llm-d isvc-b")
    ),
    TargetComponent(
        56, "LWS - multi-node serving", "ns: kserve", "C", "P8", ("resource", "kserve", "lws")
    ),
    TargetComponent(
        57,
        "mTLS STRICT + AuthorizationPolicy (kserve)",
        "ns: kserve",
        "A",
        "P8",
        ("resource", "kserve", "mtls strict + authorizationpolicy"),
    ),
    TargetComponent(
        58,
        "Knative Serving + Kourier net layer",
        "ns: kserve group",
        "D",
        "P8",
        ("resource", "kserve", "knative serving + kourier net layer"),
    ),
    TargetComponent(
        59,
        "Argo Rollouts (Deployments only)",
        "ns: rollouts",
        "C",
        "P10",
        ("resource", "rollouts", "argo rollouts"),
    ),
    TargetComponent(
        60,
        "canary + AnalysisTemplate",
        "ns: rollouts",
        "A",
        "P10",
        ("resource", "rollouts", "canary + analysistemplate"),
    ),
    TargetComponent(
        61, "Istio (istiod)", "ns: istio-system", "C", "P6", ("resource", "istio-system", "istio")
    ),
    TargetComponent(
        62, "Kiali", "ns: istio-system", "C", "P6", ("resource", "istio-system", "kiali")
    ),
    TargetComponent(
        63,
        "mTLS STRICT + AuthorizationPolicy (mesh-wide)",
        "ns: istio-system",
        "A",
        "P6",
        ("resource", "istio-system", "mtls strict + authorizationpolicy"),
    ),
    TargetComponent(
        64,
        "HashiCorp Vault",
        "ns: security",
        "A",
        "P6",
        ("resource", "security", "hashicorp vault"),
    ),
    TargetComponent(
        65,
        "External Secrets Operator",
        "ns: security",
        "A",
        "P6",
        ("resource", "security", "external secrets operator"),
    ),
    TargetComponent(
        66,
        "OpenTelemetry Collector",
        "ns: observability",
        "A",
        "P12",
        ("resource", "observability", "opentelemetry collector"),
    ),
    TargetComponent(
        67, "Loki", "ns: observability", "E", "P12", ("resource", "observability", "loki")
    ),
    TargetComponent(
        68,
        "Prometheus",
        "ns: observability",
        "E",
        "P12",
        ("resource", "observability", "prometheus"),
    ),
    TargetComponent(
        69, "Grafana", "ns: observability", "E", "P12", ("resource", "observability", "grafana")
    ),
    TargetComponent(
        70, "Jaeger", "ns: observability", "E", "P12", ("resource", "observability", "jaeger")
    ),
    TargetComponent(
        71, "PushGateway", "implied edge", "C", "P12", ("resource", None, "pushgateway")
    ),
    TargetComponent(
        72, "Jenkins Controller", "ns: ci", "C", "P10", ("resource", "ci", "jenkins controller")
    ),
    TargetComponent(
        73, "Jenkins Agents", "ns: ci", "C", "P10", ("resource", "ci", "jenkins agents")
    ),
    TargetComponent(
        74,
        "app-ci lane: lint -> test-build -> scan -> push-by-digest",
        "ns: ci",
        "C",
        "P10",
        ("resource", "ci", "app-ci lane: lint -> test-build -> scan -> push-by-digest"),
    ),
    TargetComponent(
        75,
        "model-promote lane: fetch-run -> holdout gate -> smoke-test -> scan -> sign",
        "ns: ci",
        "C",
        "P10",
        (
            "resource",
            "ci",
            "model-promote lane: fetch-run -> holdout gate -> smoke-test -> scan -> sign",
        ),
    ),
    TargetComponent(
        76, "bump-gitops (shared terminus)", "ns: ci", "C", "P10", ("resource", "ci", "bump-gitops")
    ),
    TargetComponent(
        77,
        "frozen eval set (holdout gate input)",
        "ns: ci edge",
        "C",
        "P7",
        ("resource", "ci", "frozen eval set"),
    ),
    TargetComponent(
        78,
        "sync: triton-isvc.yaml, llm-isvc-b.yaml",
        "Argo edge",
        "C",
        "P10",
        ("resource", None, "sync: triton-isvc.yaml"),
    ),
    TargetComponent(
        79,
        "commit: canaryTrafficPercent + llm HTTPRoute weight",
        "Argo edge",
        "C",
        "P10",
        ("resource", None, "commit: canarytrafficpercent + llm httproute weight"),
    ),
    TargetComponent(
        80,
        "ML gate: p99 latency, error rate, drift",
        "annotation",
        "C",
        "P7",
        ("resource", None, "ml gate: p99 latency"),
    ),
    TargetComponent(
        81,
        "LLM gate: TTFT, tokens/s, KV-cache hit",
        "annotation",
        "C",
        "P8",
        ("resource", None, "llm gate: ttft"),
    ),
    TargetComponent(
        82,
        "query metrics, analysis latency, error rate -> AnalysisTemplate",
        "annotation",
        "C",
        "P10",
        ("resource", None, "query metrics"),
    ),
    TargetComponent(
        83,
        "Developer stress test -> Web",
        "dotted edge",
        "C",
        "P11",
        ("resource", None, "developer stress test -> web"),
    ),
)


def _kubectl(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["kubectl", *args], capture_output=True, text=True, timeout=10, check=False
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return result.stdout if result.returncode == 0 else ""


def _namespace_exists(namespace: str) -> bool:
    return bool(_kubectl(["get", "namespace", namespace, "-o", "name"]).strip())


def _resource_present(namespace: str, name_substring: str) -> bool:
    if not _namespace_exists(namespace):
        return False
    output = _kubectl(["get", "all,ingress,secret", "-n", namespace, "-o", "name"])
    return name_substring in output.lower()


def check_component(component: TargetComponent) -> bool:
    """True if the component is live in the cluster; False (missing) otherwise.

    External actors, GitOps/CI artifacts, and annotated edges (Class E actors
    and most Class C pipeline steps) are not Kubernetes resources at all --
    they are reported missing/unverifiable via this probe by design, and are
    expected to be confirmed by their owning phase's own exit gate instead.
    """
    _, namespace, name_substring = component.probe
    if namespace is None:
        return False
    return _resource_present(namespace, name_substring)


def verify() -> list[TargetComponent]:
    """Return every component NOT found live in the cluster."""
    return [c for c in TARGET_COMPONENTS if not check_component(c)]


def main() -> int:
    missing = verify()
    if missing:
        for component in missing:
            print(f"MISSING #{component.number} [{component.owning_phase}] {component.name}")
        print(f"\n{len(missing)}/{len(TARGET_COMPONENTS)} target components missing — FAIL")
        return 1
    print(f"Target architecture: all {len(TARGET_COMPONENTS)} components live — PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
