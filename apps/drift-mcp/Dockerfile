FROM python:3.11-slim
WORKDIR /service
COPY src ./src
COPY feature_repo ./feature_repo
RUN pip install --no-cache-dir fastapi==0.141.1 httpx==0.28.1 mcp==1.29.0 \
    prometheus-client==0.24.1 pydantic==2.13.4 PyYAML==6.0.3 uvicorn==0.34.0
COPY apps/drift-mcp/app ./app
USER 65532:65532
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
