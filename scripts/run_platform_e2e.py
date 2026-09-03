#!/usr/bin/env python3
"""Run the live Phase 2 service-graph contract against a Kubernetes cluster.

The runner is intentionally operational rather than a second deployment system:
GitOps owns manifests, while this command waits for their workloads, warms the
active model revision through agentgateway, and proves one coordinator round
trip with bounded checks.
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

DEFAULT_TIMEOUT_SECONDS = 300.0
POLL_SECONDS = 3.0


@dataclass(frozen=True)
class Workload:
    kind: str
    namespace: str
    name: str


@dataclass
class Step:
    name: str
    status: str
    detail: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_ms: int = 0


REQUIRED_WORKLOADS: tuple[Workload, ...] = (
    Workload("deployment", "phase2-data", "web"),
    Workload("deployment", "phase2-data", "feature-mcp"),
    Workload("deployment", "phase2-data", "drift-mcp"),
    Workload("deployment", "phase2-data", "phase2-redis"),
    Workload("statefulset", "phase2-data", "phase2-postgres"),
    Workload("deployment", "agents-sandbox", "feature-agent"),
    Workload("deployment", "agents-sandbox", "drift-agent"),
    Workload("deployment", "agents-sandbox", "coordinator"),
    Workload("deployment", "agentgateway-system", "agentgateway-proxy"),
    Workload("deployment", "kagent", "agentregistry"),
    Workload("deployment", "monitoring", "jaeger"),
    Workload("daemonset", "monitoring", "otel-collector"),
    Workload("deployment", "monitoring", "monitoring-grafana"),
    Workload(
        "statefulset",
        "monitoring",
        "prometheus-monitoring-kube-prometheus-prometheus",
    ),
)

REQUIRED_SERVICES: tuple[tuple[str, str, str], ...] = (
    ("web", "phase2-data", "web"),
    ("feature-mcp", "phase2-data", "feature-mcp"),
    ("drift-mcp", "phase2-data", "drift-mcp"),
    ("feature-agent", "agents-sandbox", "feature-agent"),
    ("drift-agent", "agents-sandbox", "drift-agent"),
    ("coordinator", "agents-sandbox", "coordinator"),
    ("agentgateway", "agentgateway-system", "agentgateway-proxy"),
    ("agentregistry", "kagent", "agentregistry"),
    ("jaeger", "monitoring", "jaeger"),
    ("prometheus", "monitoring", "monitoring-kube-prometheus-prometheus"),
)


def _kubectl(*args: str, timeout: float = 30.0) -> str:
    result = subprocess.run(
        ["kubectl", *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "kubectl failed"
        raise RuntimeError(message)
    return result.stdout


def _kubectl_json(*args: str) -> dict[str, Any]:
    return json.loads(_kubectl(*args))


def _workload_ready(workload: Workload) -> tuple[bool, dict[str, Any]]:
    data = _kubectl_json(
        "get",
        workload.kind,
        workload.name,
        "-n",
        workload.namespace,
        "-o",
        "json",
    )
    spec = data.get("spec") or {}
    status = data.get("status") or {}
    desired = int(spec.get("replicas", status.get("desiredNumberScheduled", 1)) or 0)
    if workload.kind == "daemonset":
        ready = int(status.get("numberReady", 0) or 0)
        desired = int(status.get("desiredNumberScheduled", desired) or 0)
    else:
        ready = int(status.get("readyReplicas", 0) or 0)
    return ready >= desired and desired > 0, {
        "desired": desired,
        "ready": ready,
        "observed_generation": status.get("observedGeneration"),
    }


def wait_for_workload(workload: Workload, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            ready, detail = _workload_ready(workload)
            if ready:
                return detail
            last_error = f"ready={detail['ready']}/{detail['desired']}"
        except (RuntimeError, json.JSONDecodeError) as exc:
            last_error = str(exc)
        time.sleep(POLL_SECONDS)
    raise RuntimeError(f"{workload.kind}/{workload.name} not ready: {last_error}")


def _service_ready(namespace: str, service: str) -> bool:
    data = _kubectl_json(
        "get",
        "endpointslice",
        "-n",
        namespace,
        "-l",
        f"kubernetes.io/service-name={service}",
        "-o",
        "json",
    )
    for item in data.get("items", []):
        for endpoint in item.get("endpoints", []):
            if (endpoint.get("conditions") or {}).get("ready") is True:
                return True
    return False


def wait_for_service(namespace: str, service: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if _service_ready(namespace, service):
                return
        except (RuntimeError, json.JSONDecodeError):
            pass
        time.sleep(POLL_SECONDS)
    raise RuntimeError(f"service/{service} in {namespace} has no ready endpoint")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


@contextmanager
def port_forward(namespace: str, service: str, remote_port: int, timeout: float) -> Iterator[str]:
    local_port = _free_port()
    process = subprocess.Popen(
        [
            "kubectl",
            "port-forward",
            "-n",
            namespace,
            f"svc/{service}",
            f"{local_port}:{remote_port}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + min(timeout, 30.0)
        while time.monotonic() < deadline:
            if process.poll() is not None:
                output = process.stdout.read() if process.stdout else ""
                raise RuntimeError(f"port-forward exited: {output.strip()}")
            if _port_open(local_port):
                yield f"http://127.0.0.1:{local_port}"
                return
            time.sleep(0.25)
        raise RuntimeError(f"port-forward svc/{service} did not open a local port")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def http_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> tuple[int, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else None
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return exc.code, raw
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(str(exc)) from exc


def model_payload() -> dict[str, Any]:
    return {
        "model": "qwen2.5-0.5b-instruct",
        "messages": [
            {"role": "user", "content": "Reply with the single word READY."},
        ],
        "temperature": 0,
        "max_tokens": 8,
        "stream": False,
    }


def coordinator_payload() -> dict[str, Any]:
    return {
        "question": "Run the live feature and drift checks and summarize the evidence.",
        "feature_request": {
            "user_id": "PHASE3_CONTRACT_PROBE",
            "feature_names": ["stream_market_features:last_price"],
            "scope": "financial-distress:read",
        },
        "drift_request": {
            "rows": [{"ticker": "PHASE3_CONTRACT_PROBE", "close_price": 100.0}],
            "scenario": {
                "name": "market_stress",
                "seed": 7,
                "start_quarter": 1,
                "affected_fraction": 1.0,
                "feature_shifts": {"close_price": {"mode": "multiplicative", "magnitude": 0.5}},
                "target_metric": "close_price",
                "observed_stat": "mean",
                "expected_direction": "increase",
                "threshold": 0.1,
            },
            "scope": "financial-distress:drift",
        },
    }


def _active_model_deployment() -> str | None:
    try:
        kservice = _kubectl_json(
            "get", "ksvc", "fd-chat-model-predictor", "-n", "default", "-o", "json"
        )
    except (RuntimeError, json.JSONDecodeError):
        return None
    status = kservice.get("status") or {}
    revision = status.get("latestReadyRevisionName")
    if not revision:
        traffic = status.get("traffic") or []
        revision = next(
            (item.get("revisionName") for item in traffic if item.get("percent") == 100),
            None,
        )
    if not revision:
        return None
    try:
        data = _kubectl_json(
            "get",
            "deployment",
            "-n",
            "default",
            "-l",
            f"serving.knative.dev/revision={revision}",
            "-o",
            "json",
        )
    except (RuntimeError, json.JSONDecodeError):
        return None
    items = data.get("items") or []
    return str(items[0]["metadata"]["name"]) if items else None


def warm_model(timeout: float) -> dict[str, Any]:
    scaled_revision: str | None = None
    deadline = time.monotonic() + timeout
    with port_forward("agentgateway-system", "agentgateway-proxy", 8080, timeout) as base_url:
        last_error = ""
        while time.monotonic() < deadline:
            try:
                status, response = http_json(
                    f"{base_url}/v1/chat/completions",
                    method="POST",
                    payload=model_payload(),
                    timeout=30,
                )
                if status == 200 and isinstance(response, dict):
                    choices = response.get("choices") or []
                    if choices:
                        return {
                            "http_status": status,
                            "model": model_payload()["model"],
                            "scaled_revision": scaled_revision,
                        }
                last_error = f"gateway status={status}: {response}"
            except RuntimeError as exc:
                last_error = str(exc)

            # The direct stable Service deliberately bypasses Knative's
            # activator. If hibernation left the active revision at zero, the
            # runner performs the bounded operational warm-up once; it does
            # not modify the GitOps manifest or leave an arbitrary replica count.
            if scaled_revision is None:
                deployment = _active_model_deployment()
                if deployment:
                    try:
                        data = _kubectl_json(
                            "get", "deployment", deployment, "-n", "default", "-o", "json"
                        )
                        replicas = int((data.get("spec") or {}).get("replicas", 0) or 0)
                        if replicas == 0:
                            _kubectl(
                                "scale", "deployment", deployment, "-n", "default", "--replicas=1"
                            )
                            scaled_revision = deployment
                    except (RuntimeError, json.JSONDecodeError) as exc:
                        last_error = str(exc)
            time.sleep(POLL_SECONDS)
    raise RuntimeError(f"model warm-up failed: {last_error}")


def validate_coordinator_response(response: Any) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise RuntimeError("coordinator response is not an object")
    answer = response.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("coordinator returned an empty answer")
    specialists = response.get("specialists")
    specialist_names = {
        item.get("specialist")
        for item in specialists or []
        if isinstance(item, dict) and isinstance(item.get("specialist"), str)
    }
    if not {"feature", "drift"}.issubset(specialist_names):
        raise RuntimeError(f"missing specialist calls: {sorted(specialist_names)}")
    citations = response.get("citations")
    citation_uris = {
        item.get("source_uri")
        for item in citations or []
        if isinstance(item, dict) and isinstance(item.get("source_uri"), str)
    }
    if not any(uri.startswith("feature:") for uri in citation_uris):
        raise RuntimeError("feature citation missing")
    if not any(uri.startswith("drift:") for uri in citation_uris):
        raise RuntimeError("drift citation missing")
    hops_used = response.get("hops_used")
    if not isinstance(hops_used, int) or hops_used < 1:
        raise RuntimeError("coordinator did not report a completed hop")
    return {
        "answer_chars": len(answer),
        "specialists": sorted(specialist_names),
        "citations": sorted(citation_uris),
        "hops_used": hops_used,
        "drift_rows_sent": len(coordinator_payload()["drift_request"]["rows"]),
    }


def run_coordinator(timeout: float) -> dict[str, Any]:
    with port_forward("agents-sandbox", "coordinator", 80, timeout) as base_url:
        for path in ("/healthz", "/readyz"):
            status, response = http_json(f"{base_url}{path}", timeout=15)
            if status != 200:
                raise RuntimeError(f"{path} status={status}: {response}")
        status, response = http_json(
            f"{base_url}/v1/run",
            method="POST",
            payload=coordinator_payload(),
            timeout=timeout,
        )
        if status != 200:
            raise RuntimeError(f"coordinator status={status}: {response}")
        result = validate_coordinator_response(response)
        result["http_status"] = status
        return result


def run_telemetry(timeout: float) -> dict[str, Any]:
    with port_forward(
        "monitoring", "monitoring-kube-prometheus-prometheus", 9090, timeout
    ) as base_url:
        query = 'up{namespace=~"agents-sandbox|phase2-data"}'
        status, response = http_json(f"{base_url}/api/v1/query?query={quote(query)}", timeout=30)
        if status != 200 or not isinstance(response, dict):
            raise RuntimeError(f"Prometheus query failed: status={status}")
        series = (response.get("data") or {}).get("result") or []
        expected = {"coordinator", "feature-agent", "drift-agent", "feature-mcp", "drift-mcp"}
        observed: dict[str, float] = {}
        for item in series:
            labels = item.get("metric") or {}
            service = labels.get("service")
            if service in expected:
                values = item.get("value") or []
                if len(values) == 2:
                    observed[service] = float(values[1])
        missing = sorted(expected - set(observed))
        down = sorted(name for name, value in observed.items() if value != 1.0)
        if missing or down:
            raise RuntimeError(f"Prometheus targets missing={missing} down={down}")
    with port_forward("monitoring", "jaeger", 16686, timeout) as base_url:
        expected_services = {
            "coordinator-agent",
            "feature-agent",
            "drift-agent",
            "feature-mcp",
            "drift-mcp",
        }
        deadline = time.monotonic() + min(timeout, 60.0)
        services: list[str] = []
        last_status = 0
        while time.monotonic() < deadline:
            last_status, response = http_json(f"{base_url}/jaeger/api/services", timeout=30)
            services = (response.get("data") or []) if isinstance(response, dict) else []
            if last_status == 200 and expected_services.issubset(services):
                break
            time.sleep(2)
        if last_status != 200:
            raise RuntimeError(f"Jaeger query failed: status={last_status}")
        missing = sorted(expected_services - set(services))
        if missing:
            raise RuntimeError(f"Jaeger services missing={missing}; observed={sorted(services)}")
    return {"targets": observed, "jaeger_services": services}


def run_web_probe(url: str, timeout: float) -> dict[str, Any]:
    status, _ = http_json(url.rstrip("/"), timeout=min(timeout, 30.0))
    if status >= 500:
        raise RuntimeError(f"web returned HTTP {status}")
    return {"url": url, "http_status": status}


def _run_step(name: str, action: Any) -> Step:
    started = time.monotonic()
    try:
        detail = action()
        return Step(
            name, "PASS", detail or {}, duration_ms=int((time.monotonic() - started) * 1000)
        )
    except Exception as exc:  # noqa: BLE001 - CLI converts every check to a report row
        return Step(
            name,
            "FAIL",
            duration_ms=int((time.monotonic() - started) * 1000),
            error=str(exc),
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--web-url",
        help="Optional externally reachable web URL to probe after the cluster service checks.",
    )
    parser.add_argument("--json", action="store_true", help="Emit only the JSON report.")
    return parser.parse_args(argv)


def run(argv: list[str]) -> int:
    args = parse_args(argv)
    steps: list[Step] = []
    steps.append(
        _run_step(
            "cluster-context", lambda: {"context": _kubectl("config", "current-context").strip()}
        )
    )
    for workload in REQUIRED_WORKLOADS:
        steps.append(
            _run_step(
                f"workload/{workload.namespace}/{workload.name}",
                lambda workload=workload: wait_for_workload(workload, args.timeout),
            )
        )
    for _label, namespace, service in REQUIRED_SERVICES:
        steps.append(
            _run_step(
                f"service/{namespace}/{service}",
                lambda namespace=namespace, service=service: (
                    wait_for_service(namespace, service, args.timeout),
                    {"service": service},
                )[1],
            )
        )
    steps.append(_run_step("model-warmup-via-agentgateway", lambda: warm_model(args.timeout)))
    steps.append(_run_step("coordinator-live-roundtrip", lambda: run_coordinator(args.timeout)))
    steps.append(_run_step("prometheus-targets", lambda: run_telemetry(args.timeout)))
    if args.web_url:
        steps.append(_run_step("web-http-probe", lambda: run_web_probe(args.web_url, args.timeout)))

    report = {
        "status": "PASS" if all(step.status == "PASS" for step in steps) else "FAIL",
        "cluster_context": next(
            (step.detail.get("context") for step in steps if step.name == "cluster-context"),
            None,
        ),
        "steps": [
            {
                "name": step.name,
                "status": step.status,
                "detail": step.detail,
                "error": step.error,
                "duration_ms": step.duration_ms,
            }
            for step in steps
        ],
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for step in steps:
            suffix = f" — {step.error}" if step.error else ""
            print(f"[{step.status}] {step.name}{suffix}")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
