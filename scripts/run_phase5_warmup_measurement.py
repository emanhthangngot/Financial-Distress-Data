"""One-shot cold-vs-warm startup and TTFT measurement for the agent warm pool.

Runs against the live ``feature-agent`` Deployment in ``agents-sandbox``.
Scales to zero and back to measure a true cold start, then scales one
replica up from an already-warm pool to measure a warm start, and issues
``/v1/run`` requests at each point to record TTFT. Writes JSON with the
fields declared in ``platform/agents/warm-pool.yaml``'s ``measurement``
block.

Requires ``kubectl`` on PATH with a working context, and ``httpx``.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import time

import httpx

NAMESPACE = "agents-sandbox"
DEPLOYMENT = "feature-agent"
RUN_PAYLOAD = {
    "question": "what is the risk score",
    "user_id": "VNM",
    "feature_names": ["company_risk_features:z_score"],
    "scope": "financial-distress:read",
    "tool_budget": 1,
}
# Per-replica requested resources (source of truth: the live Deployment spec).
CPU_REQUEST_CORES = 0.025
MEMORY_REQUEST_GB = 96 / 1024
# Rough on-demand e2 pricing used only for an order-of-magnitude cost delta;
# not a billing-accurate figure.
CPU_COST_PER_CORE_HOUR = 0.031611
MEMORY_COST_PER_GB_HOUR = 0.004237


def kubectl(*args: str) -> str:
    result = subprocess.run(["kubectl", *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def scale(replicas: int) -> None:
    kubectl("scale", "deployment", DEPLOYMENT, "-n", NAMESPACE, f"--replicas={replicas}")


def wait_ready(min_ready: int, timeout_s: float = 180.0) -> float:
    started = time.perf_counter()
    while True:
        out = kubectl(
            "get", "pods", "-n", NAMESPACE, "-l", f"app={DEPLOYMENT}",
            "-o", "jsonpath={range .items[*]}{.status.containerStatuses[0].ready}{\"\\n\"}{end}",
        )
        ready_count = out.count("true")
        if ready_count >= min_ready:
            return time.perf_counter() - started
        if time.perf_counter() - started > timeout_s:
            raise TimeoutError(f"timed out waiting for {min_ready} ready replicas")
        time.sleep(1)


def run_once(port_forward_port: int) -> float:
    started = time.perf_counter()
    response = httpx.post(
        f"http://127.0.0.1:{port_forward_port}/v1/run", json=RUN_PAYLOAD, timeout=30.0
    )
    response.raise_for_status()
    return time.perf_counter() - started


def with_port_forward(port: int):
    return subprocess.Popen(
        ["kubectl", "port-forward", "-n", NAMESPACE, f"deployment/{DEPLOYMENT}", f"{port}:8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--warm-replicas", type=int, default=2)
    parser.add_argument("--port", type=int, default=18000)
    args = parser.parse_args()

    proc = with_port_forward(args.port)
    time.sleep(3)
    try:
        # Warm baseline: pool already at target replicas.
        warm_ttfts = [run_once(args.port) for _ in range(5)]
        warm_ttft_seconds = statistics.median(warm_ttfts)

        proc.terminate()
        proc.wait(timeout=10)

        # Cold start: scale to zero, then back up from nothing.
        scale(0)
        kubectl(
            "wait", "--for=delete", "pod", "-n", NAMESPACE, f"-l app={DEPLOYMENT}",
            "--timeout=120s",
        )
        scale(1)
        cold_start_seconds = wait_ready(1)

        proc = with_port_forward(args.port)
        time.sleep(3)
        cold_ttft_seconds = run_once(args.port)
        proc.terminate()
        proc.wait(timeout=10)

        # Warm start: pool already warm at 1, add one more replica.
        warm_start_started = time.perf_counter()
        scale(2)
        warm_start_seconds = wait_ready(2)

        # Restore the warm-pool policy's minimum agent replica count.
        scale(args.warm_replicas)
        wait_ready(args.warm_replicas)

        replica_spread = {"min": 1, "max": max(2, args.warm_replicas), "target": args.warm_replicas}
        # Cost delta: replicas kept warm outside the evidence window vs the
        # scale-to-zero policy, at the Deployment's declared resource requests.
        hourly_cost_per_replica = (
            CPU_REQUEST_CORES * CPU_COST_PER_CORE_HOUR
            + MEMORY_REQUEST_GB * MEMORY_COST_PER_GB_HOUR
        )
        estimated_cost_delta = {
            "hourly_cost_per_replica_usd": round(hourly_cost_per_replica, 6),
            "warm_replicas_during_window": args.warm_replicas,
            "hourly_cost_during_window_usd": round(hourly_cost_per_replica * args.warm_replicas, 6),
            "hourly_cost_outside_window_usd": 0.0,
            "note": "scale-to-zero outside the evidence window per warm-pool.yaml operations.evidenceEnd",
        }

        result = {
            "cold_start_seconds": round(cold_start_seconds, 3),
            "warm_start_seconds": round(warm_start_seconds, 3),
            "cold_ttft_seconds": round(cold_ttft_seconds, 3),
            "warm_ttft_seconds": round(warm_ttft_seconds, 3),
            "warm_ttft_samples_seconds": [round(v, 3) for v in warm_ttfts],
            "replica_spread": replica_spread,
            "estimated_cost_delta": estimated_cost_delta,
            "deployment": DEPLOYMENT,
            "namespace": NAMESPACE,
        }
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
        print(json.dumps(result, indent=2))
    finally:
        if proc.poll() is None:
            proc.terminate()


if __name__ == "__main__":
    main()
