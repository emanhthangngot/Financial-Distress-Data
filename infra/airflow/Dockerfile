# syntax=docker/dockerfile:1.7
# Multistage build for the Airflow image.
#
# Stage 1 (builder): create a Python venv with all wheels prebuilt. This stage
# carries pip, build tools, and source distributions — none of which are needed
# at runtime.
#
# Stage 2 (runtime): start from the same base, install only the apt packages
# the runtime actually needs (graphviz, openjdk-17 JRE headless), and copy the
# prebuilt venv from the builder. No compilers, no pip, no apt cache remain
# in the final image.

FROM apache/airflow:2.10.5-python3.11 AS builder

USER airflow

# Create an isolated venv so its site-packages can be copied wholesale into
# the runtime stage.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}" \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install all Python dependencies in the builder only. pyspark, psycopg,
# pyarrow, etc. ship pure wheels for the cp311 / manylinux2014 target, so
# no compilers are required.
RUN pip install --no-cache-dir \
    duckdb==1.1.3 \
    kafka-python==2.0.2 \
    minio==7.2.12 \
    pyarrow==17.0.0 \
    "psycopg[binary]==3.2.3" \
    pyspark==3.5.6


FROM apache/airflow:2.10.5-python3.11 AS runtime

USER root

# Runtime-only apt packages: openjdk-17 JRE for PySpark local mode, graphviz
# for the lineage diagram. --no-install-recommends keeps the layer small;
# apt cache is wiped in the same layer to keep the image lean.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        graphviz \
        openjdk-17-jre-headless \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    SPARK_LOCAL_IP=127.0.0.1 \
    PATH="/opt/venv/bin:${PATH}"

# Copy the prebuilt venv (already a multi-GB savings vs reinstalling on the
# runtime image, because pip wheel downloads are skipped).
COPY --from=builder --chown=airflow:root /opt/venv /opt/venv
