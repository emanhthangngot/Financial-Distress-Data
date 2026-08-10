"""Locust SLA client for the feature Web API through the public gateway.

Run with ``locust -f tests/load/locustfile.py --headless`` and provide
``BENCHMARK_TARGET_HOST``. The HTML report records Locust's p95 latency,
throughput, failure rate, concurrency and the command-line test parameters.
Gateway basic-auth credentials are optional for local port-forward runs and
are injected through environment variables for the evidence cluster.
"""

from __future__ import annotations

import os

from locust import HttpUser, between, task

TARGET_HOST = os.environ.get("BENCHMARK_TARGET_HOST", "https://distresslens.duckdns.org")
FEATURE_PATH = os.environ.get("BENCHMARK_FEATURE_PATH", "/v1/features/by-id")
BENCHMARK_USER = os.environ.get("BENCHMARK_BASIC_AUTH_USER")
BENCHMARK_PASSWORD = os.environ.get("BENCHMARK_BASIC_AUTH_PASSWORD")


class FeatureApiUser(HttpUser):
    """Representative analyst request over the F5 gateway route."""

    host = TARGET_HOST
    wait_time = between(0.5, 2.0)

    def on_start(self) -> None:
        self.auth = (
            (BENCHMARK_USER, BENCHMARK_PASSWORD) if BENCHMARK_USER and BENCHMARK_PASSWORD else None
        )

    @task
    def lookup_features(self) -> None:
        response = self.client.post(
            FEATURE_PATH,
            json={"user_id": "AAA", "feature_names": ["company_features:risk_score"]},
            auth=self.auth,
            name="POST /v1/features/by-id",
            catch_response=True,
        )
        if response.status_code != 200:
            response.failure(f"expected 200, got {response.status_code}")
