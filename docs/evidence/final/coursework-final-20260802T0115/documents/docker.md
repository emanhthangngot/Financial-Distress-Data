# Docker Optimization

## Method

`infra/airflow/Dockerfile.baseline` deliberately retains apt metadata, installs
recommended packages, and keeps pip's download cache.
`infra/airflow/Dockerfile` uses `--no-install-recommends`, removes apt lists,
and installs Python packages with `--no-cache-dir`.

Both images use the same Airflow base and the same pinned runtime package
versions.

```bash
docker build -f infra/airflow/Dockerfile.baseline \
  -t financial-distress-airflow:baseline .
docker build -f infra/airflow/Dockerfile \
  -t financial-distress-airflow:stage1 .
python scripts/export_docker_optimization.py
```

## Result

| Image | Content size |
|---|---:|
| Baseline | 1,654,286,301 bytes |
| Optimized | 928,642,637 bytes |
| Saved | 725,643,664 bytes |
| Reduction | 43.86% |

Machine-readable proof:
[`phase8-image-sizes.json`](evidence/docker/phase8-image-sizes.json).

Compose also persists PostgreSQL, MinIO, Kafka, and Flink state in named
volumes. PostgreSQL, MinIO, and Kafka expose health checks so dependent init
services wait for readiness rather than process startup.

## Limitation

PySpark and Java dominate the final image. Splitting Spark into a separate
runtime would reduce Airflow further but changes the local deployment contract
and is outside this coursework phase.
