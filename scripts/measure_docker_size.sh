#!/usr/bin/env bash
# Measure baseline vs optimized Airflow image size and write evidence.
#
# Usage:
#   bash scripts/measure_docker_size.sh
#
# Output:
#   evidence/docker_size.json
#
# The script tags the current `infra/airflow/Dockerfile` as the optimized build
# and a known-good single-stage Dockerfile (kept in evidence/) as the baseline.
# Both images are built, sized with `docker images`, and their `docker history`
# is recorded. The JSON also reports the percentage reduction.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE_DIR="${PROJECT_ROOT}/evidence"
EVIDENCE_FILE="${EVIDENCE_DIR}/docker_size.json"
BASELINE_DOCKERFILE="${EVIDENCE_DIR}/Dockerfile.baseline"
IMAGE_BASELINE="fd-airflow:baseline"
IMAGE_OPTIMIZED="fd-airflow:optimized"

mkdir -p "${EVIDENCE_DIR}"

# Write a known-good single-stage Dockerfile next to the evidence so the
# baseline is reproducible. This mirrors the original single-stage file that
# shipped before W23.
cat > "${BASELINE_DOCKERFILE}" <<'DOCKERFILE_EOF'
FROM apache/airflow:2.10.5-python3.11

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        graphviz \
        openjdk-17-jre-headless \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV SPARK_LOCAL_IP=127.0.0.1

RUN python -m pip install --no-cache-dir \
    duckdb==1.1.3 \
    kafka-python==2.0.2 \
    minio==7.2.12 \
    pyarrow==17.0.0 \
    "psycopg[binary]==3.2.3" \
    pyspark==3.5.6
DOCKERFILE_EOF

echo ">> building baseline image (single-stage)"
docker build -f "${BASELINE_DOCKERFILE}" -t "${IMAGE_BASELINE}" "${PROJECT_ROOT}" >/dev/null

echo ">> building optimized image (multistage)"
docker build -f "${PROJECT_ROOT}/infra/airflow/Dockerfile" -t "${IMAGE_OPTIMIZED}" "${PROJECT_ROOT}" >/dev/null

# Pull the size in MB from `docker images`. Format: "<repo>:<tag>  <id>  <created>  <size>"
baseline_mb="$(docker images --format '{{.Size}}' "${IMAGE_BASELINE}")"
optimized_mb="$(docker images --format '{{.Size}}' "${IMAGE_OPTIMIZED}")"

# docker prints sizes with a unit suffix (e.g. "1.23GB", "456MB"). Normalize to MB.
to_mb() {
    local size="$1"
    local num unit
    num="$(echo "${size}" | sed -E 's/([0-9.]+)[A-Za-z]+/\1/')"
    unit="$(echo "${size}" | sed -E 's/[0-9.]+([A-Za-z]+)/\1/')"
    case "${unit}" in
        GB) awk -v n="${num}" 'BEGIN { printf "%.0f", n * 1024 }' ;;
        MB) awk -v n="${num}" 'BEGIN { printf "%.0f", n }' ;;
        KB) awk -v n="${num}" 'BEGIN { printf "%.0f", n / 1024 }' ;;
        B)  echo "${num}" ;;
        *)  echo "${num}" ;;
    esac
}

baseline_mb_num="$(to_mb "${baseline_mb}")"
optimized_mb_num="$(to_mb "${optimized_mb}")"
reduction_pct="$(awk -v b="${baseline_mb_num}" -v o="${optimized_mb_num}" 'BEGIN { if (b > 0) printf "%.2f", (b - o) * 100 / b; else print "0.00" }')"

# Capture docker history as a JSON-friendly list. Use --format to keep the
# output stable.
history_baseline="$(docker history "${IMAGE_BASELINE}" --format '{{json .}}' | paste -sd, - || true)"
history_optimized="$(docker history "${IMAGE_OPTIMIZED}" --format '{{json .}}' | paste -sd, - || true)"

# Write the JSON evidence using python (always present on the airflow image).
python - "${EVIDENCE_FILE}" "${baseline_mb_num}" "${optimized_mb_num}" "${reduction_pct}" "${history_baseline}" "${history_optimized}" <<'PY_EOF'
import json
import sys

out_path, baseline, optimized, reduction, hist_b, hist_o = sys.argv[1:6]
payload = {
    "image_baseline": "fd-airflow:baseline",
    "image_optimized": "fd-airflow:optimized",
    "baseline_mb": int(baseline),
    "optimized_mb": int(optimized),
    "reduction_pct": float(reduction),
    "history_baseline": hist_b,
    "history_optimized": hist_o,
}
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2, sort_keys=True)
PY_EOF

echo ">> wrote ${EVIDENCE_FILE}"
echo "   baseline  = ${baseline_mb_num} MB"
echo "   optimized = ${optimized_mb_num} MB"
echo "   reduction = ${reduction_pct}%"
