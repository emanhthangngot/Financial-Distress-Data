# syntax=docker/dockerfile:1.7
# Runs dags/phase2/phase2_stream_feature_offline.py's callable
# (src.ml.feast.offline_job.run_offline_job) as a standalone deployable —
# see phase-04-implementation-notes.md section 2, "two processes, two
# images" (this is the offline half; stream-feature-online is the other).
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN pip install --no-cache-dir \
    feast==0.65.0 \
    redis>=5 \
    "psycopg[binary]>=3.2" \
    pandas>=2.2 \
    pyarrow>=17.0 \
    minio>=7.2 \
    kafka-python>=2.0 \
    pyyaml>=6.0

COPY src ./src
COPY configs ./configs
COPY feature_repo ./feature_repo
COPY sql ./sql

ENV PYTHONPATH=/app

CMD ["python", "-c", "from src.ml.feast.offline_job import run_offline_job; print(run_offline_job())"]
