# syntax=docker/dockerfile:1
FROM python:3.11-slim
WORKDIR /service
# Resolve the project's agent extra together with the existing image pins.
RUN --mount=type=bind,source=pyproject.toml,target=/tmp/pyproject.toml <<'SH'
set -eu
python - <<'PY' > /tmp/agent-requirements.txt
import tomllib

with open("/tmp/pyproject.toml", "rb") as metadata:
    print(*tomllib.load(metadata)["project"]["optional-dependencies"]["agents"], sep="\n")
PY
python -m pip install --no-cache-dir -r /tmp/agent-requirements.txt \
    fastapi==0.141.1 feast[redis]==0.65.0 httpx==0.28.1 \
    mcp==1.29.0 prometheus-client==0.24.1 psycopg[binary]==3.3.4 \
    opentelemetry-api==1.44.0 opentelemetry-sdk==1.44.0 \
    opentelemetry-exporter-otlp-proto-grpc==1.44.0 pydantic==2.13.4 uvicorn==0.34.0
rm /tmp/agent-requirements.txt
SH
COPY src ./src
COPY feature_repo ./feature_repo
COPY apps/feature-mcp/app ./app
USER 65532:65532

# Exercise the coordinator ASGI override and its graph without calling upstreams.
RUN --network=none <<'SH'
python - <<'PY'
import os

from fastapi.testclient import TestClient
from uvicorn.importer import import_from_string

os.environ.update(
    AGENT_ROLE="coordinator",
    FEATURE_AGENT_URL="https://feature.invalid",
    DRIFT_AGENT_URL="https://drift.invalid",
    MAX_AGENT_HOPS="1",
)
with TestClient(import_from_string("src.agents.runtime:app")) as client:
    response = client.post(
        "/v1/run",
        json={"question": "startup smoke", "feature_request": {}, "drift_request": {}, "hop": 1},
    )
    response.raise_for_status()
    assert response.json()["error"] == "hop_limit_exceeded", response.text
PY
SH

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
