FROM python:3.11-slim
WORKDIR /service
COPY src ./src
COPY feature_repo ./feature_repo
RUN pip install --no-cache-dir fastapi==0.141.1 feast[redis]==0.65.0 httpx==0.28.1 \
    mcp==1.29.0 prometheus-client==0.24.1 psycopg[binary]==3.3.4 \
    opentelemetry-api==1.44.0 opentelemetry-sdk==1.44.0 \
    opentelemetry-exporter-otlp-proto-grpc==1.44.0 pydantic==2.13.4 uvicorn==0.34.0
RUN cd /service/feature_repo/structured && \
    cp feature_store.cluster.yaml feature_store.yaml && \
    PYTHONPATH=/service \
    FEAST_REGISTRY_PATH=/service/feature_repo/structured/registry.db \
    FEAST_REDIS_HOST=platform-redis.dataflow.svc.cluster.local \
    feast apply
COPY apps/feature-mcp/app ./app
USER 65532:65532
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
