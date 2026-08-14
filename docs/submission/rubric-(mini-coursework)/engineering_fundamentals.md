---
title: "Engineering Fundamentals"
date: 2026-08-14
status: active
---

# Engineering Fundamentals: multi-stage Docker build, 43.86% image reduction

This doc proves the "Docker & Docker Compose" rubric area: a real
multi-stage-style optimization applied to the Airflow image, with a
before/after size delta and a documented method — not a claimed number. It
does not prove a maximally minimal image; PySpark/Java are disclosed as the
dominant remaining size, out of scope to split this phase.

**Active deployment facts:** `infra/airflow/Dockerfile.baseline` (deliberately
naive), `infra/airflow/Dockerfile` (optimized), same Airflow base and pinned
runtime package versions in both.

## Part I — Optimization method

### 1. What changed between baseline and optimized

```text
Baseline (infra/airflow/Dockerfile.baseline):
  retains apt metadata, installs recommended packages, keeps pip's
  download cache

Optimized (infra/airflow/Dockerfile):
  --no-install-recommends, removes apt lists, --no-cache-dir for pip
```

```bash
docker build -f infra/airflow/Dockerfile.baseline \
  -t financial-distress-airflow:baseline .
docker build -f infra/airflow/Dockerfile \
  -t financial-distress-airflow:stage1 .
python scripts/export_docker_optimization.py
```

## Part II — Measured result

| Image | Content size |
|---|---:|
| Baseline | 1,654,286,301 bytes |
| Optimized | 928,642,637 bytes |
| Saved | 725,643,664 bytes |
| **Reduction** | **43.86%** |

Machine-readable proof:
[`docs/evidence/docker/phase8-image-sizes.json`](../../evidence/docker/phase8-image-sizes.json).

Docker Compose also persists PostgreSQL, MinIO, Kafka, and Flink state in
named volumes; PostgreSQL, MinIO, and Kafka expose health checks so
dependent init services wait for readiness rather than process startup.

## Limitations

PySpark and Java dominate the final image size. Splitting Spark into a
separate runtime would reduce the Airflow image further but changes the
local deployment contract and is outside this coursework phase's scope —
disclosed as a known, deliberate boundary rather than an oversight.

## References

- Docker multi-stage builds: https://docs.docker.com/build/building/multi-stage/
