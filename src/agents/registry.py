"""Read-only HTTP projection of the GitOps-owned agent registry."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException


def load_registry(path: str | Path | None = None) -> dict[str, Any]:
    registry_path = Path(path or os.getenv("AGENT_REGISTRY_PATH", "/registry/registry.json"))
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(payload.get("agents"), list):
        raise ValueError("registry must contain an agents list")
    return payload


def create_app() -> FastAPI:
    application = FastAPI(title="agent-registry", version="1.0.0")

    @application.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/readyz")
    async def readyz() -> dict[str, Any]:
        payload = load_registry()
        return {"status": "ready", "agents": len(payload["agents"])}

    @application.get("/v1/agents")
    async def agents() -> dict[str, Any]:
        return load_registry()

    @application.get("/v1/agents/{name}")
    async def agent(name: str) -> dict[str, Any]:
        for entry in load_registry()["agents"]:
            if entry.get("name") == name:
                return dict(entry)
        raise HTTPException(status_code=404, detail="agent not found")

    return application


app = create_app()
