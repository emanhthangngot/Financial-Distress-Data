"""Register and inspect the local Debezium Postgres connector."""

from __future__ import annotations

import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.cdc.config import CDCConfig


def _request(url: str, *, method: str = "GET", payload: dict | None = None) -> object:
    body = None if payload is None else json.dumps(payload).encode()
    request = Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=10) as response:  # noqa: S310 - operator-selected local endpoint
        raw = response.read()
    return json.loads(raw) if raw else None


def register(base_url: str, config: CDCConfig, *, wait_seconds: int = 30) -> dict[str, object]:
    connector_name = "financial-distress-postgres"
    payload = {
        "name": connector_name,
        "config": config.debezium_connector_config(),
    }
    try:
        _request(
            f"{base_url}/connectors/{connector_name}/config",
            method="PUT",
            payload=payload["config"],
        )
    except HTTPError as exc:
        if exc.code not in {404, 405}:
            raise
        _request(f"{base_url}/connectors", method="POST", payload=payload)
    deadline = time.monotonic() + wait_seconds
    status: object = None
    while time.monotonic() < deadline:
        status = _request(f"{base_url}/connectors/{connector_name}/status")
        if isinstance(status, dict) and status.get("connector", {}).get("state") == "RUNNING":
            return {"connector": connector_name, "status": status, "state": "RUNNING"}
        time.sleep(1)
    return {"connector": connector_name, "status": status, "state": "TIMEOUT"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--connect-url", default="http://localhost:8083")
    parser.add_argument("--wait-seconds", type=int, default=30)
    args = parser.parse_args()
    try:
        result = register(args.connect_url, CDCConfig.from_env(), wait_seconds=args.wait_seconds)
    except (HTTPError, URLError, TimeoutError) as exc:
        print(json.dumps({"state": "ERROR", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["state"] == "RUNNING" else 1


if __name__ == "__main__":
    raise SystemExit(main())
