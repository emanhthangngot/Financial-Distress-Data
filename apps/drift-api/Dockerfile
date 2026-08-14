# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY apps/drift-api/app ./app

RUN pip install --no-cache-dir --disable-pip-version-check \
    "fastapi==0.115.6" "pydantic==2.10.5" "uvicorn[standard]==0.34.0"

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid 10001 --no-create-home app
USER 10001:10001

EXPOSE 8000
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
