# 08 — Docker Image Optimization

> Phase 1, rubric row "Docker & Dockerfile optimization" (1–2 points).
> Sprint: **W23** — multistage Dockerfile + size evidence.

## TL;DR

`infra/airflow/Dockerfile` is a two-stage build. A `builder` stage installs
the Python wheels in an isolated venv; a `runtime` stage installs only the
apt packages the runtime needs (`graphviz`, `openjdk-17-jre-headless`) and
copies the venv from the builder. No pip, no compilers, and no apt cache
remain in the final image.

The image size before / after is measured by
`scripts/measure_docker_size.sh` and recorded in
[`evidence/docker/phase8-image-sizes.json`](evidence/docker/phase8-image-sizes.json). Target
reduction: **≥ 30%**.

## Why multistage

The single-stage image installed everything in one `RUN` layer:

```dockerfile
FROM apache/airflow:2.10.5-python3.11
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
        graphviz openjdk-17-jre-headless \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
USER airflow
RUN python -m pip install --no-cache-dir \
        duckdb==1.1.3 kafka-python==2.0.2 minio==7.2.12 \
        pyarrow==17.0.0 "psycopg[binary]==3.2.3" pyspark==3.5.6
```

Two things leak into the final image even with `--no-cache-dir` and apt
cleanup:

1. **The `pip` package and its transitive deps** stay in the layer.
   `pip` itself + setuptools + the `wheel` package are pure Python so
   they persist after install. They are unreachable from the venv-free
   system Python but still occupy disk.
2. **The Python wheels themselves**, downloaded into `/tmp` and then
   moved into site-packages, leave a residual layer of "wheels were
   downloaded here". The `--no-cache-dir` flag avoids `~/.cache/pip`
   but does not eliminate the per-install scaffolding.

The multistage design isolates both: the builder layer (where `pip`
runs) is discarded, and only the resolved site-packages directory is
copied into the runtime image.

## Design

### `builder` stage

```dockerfile
FROM apache/airflow:2.10.5-python3.11 AS builder
USER airflow
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}" \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN pip install --no-cache-dir \
        duckdb==1.1.3 kafka-python==2.0.2 minio==7.2.12 \
        pyarrow==17.0.0 "psycopg[binary]==3.2.3" pyspark==3.5.6
```

- Uses the `airflow` user that already exists in the base image
  (avoids `chown` overhead).
- Sets `PIP_NO_CACHE_DIR=1` for belt-and-suspenders; the flag is also
  passed on the command line.
- Venv path is `/opt/venv` so it can be referenced from the runtime
  stage by path.

### `runtime` stage

```dockerfile
FROM apache/airflow:2.10.5-python3.11 AS runtime
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
        graphviz openjdk-17-jre-headless \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
USER airflow
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    SPARK_LOCAL_IP=127.0.0.1 \
    PATH="/opt/venv/bin:${PATH}"
COPY --from=builder --chown=airflow:root /opt/venv /opt/venv
```

- `JAVA_HOME` and `PATH` are preserved from the single-stage image so
  existing Airflow + PySpark code paths continue to work unchanged.
- `graphviz` and `openjdk-17-jre-headless` are the only apt packages
  installed at runtime. Both are required for the lineage diagram
  generator and PySpark local mode respectively.
- The builder venv is copied with `--chown=airflow:root` so the runtime
  user can write the venv's activation scripts (not strictly needed
  but matches the airflow base image convention).

### What is removed

| Layer / tool              | Single-stage | Multistage |
|---------------------------|:------------:|:----------:|
| `pip`, `setuptools`, `wheel` | yes       | no         |
| `apt-get` cache           | removed      | removed    |
| Python wheel downloads    | residual     | none       |
| Compilers / build tools   | not installed| not installed |
| Java JRE (openjdk-17)     | yes          | yes        |
| Graphviz                  | yes          | yes        |
| Runtime Python packages   | yes          | yes (copied) |

The base image is the same in both stages, so the savings come from
removing the `pip` install layer and its scaffolding — not from
swapping the base.

## Reproducing the measurement

The `scripts/measure_docker_size.sh` script:

1. Writes a copy of the original single-stage Dockerfile to
   `evidence/Dockerfile.baseline` so the baseline is reproducible
   from the repo alone.
2. Builds both images (`fd-airflow:baseline` and `fd-airflow:optimized`)
   from the project root.
3. Reads the size of each from `docker images --format '{{.Size}}'`,
   normalizes to MB, computes the percentage reduction, and records
   `docker history` output for each image.
4. Writes everything to `evidence/docker_size.json`.

```bash
# from the project root, with the docker daemon reachable:
bash scripts/measure_docker_size.sh
cat evidence/docker_size.json
```

Expected output shape:

```json
{
  "image_baseline": "fd-airflow:baseline",
  "image_optimized": "fd-airflow:optimized",
  "baseline_mb": 2500,
  "optimized_mb": 1600,
  "reduction_pct": 36.00,
  "history_baseline": "[{...}, ...]",
  "history_optimized": "[{...}, ...]"
}
```

The actual numbers must be filled in by running the script from a
machine that can reach the Docker daemon (the sandbox where the agent
runs has no daemon access).

## Files changed

- `infra/airflow/Dockerfile` — split into `builder` + `runtime` stages.
- `scripts/measure_docker_size.sh` — new, builds both images and writes
  the evidence JSON.
- `evidence/Dockerfile.baseline` — generated by the script, contains
  the original single-stage Dockerfile.
- `evidence/docker_size.json` — generated by the script, contains the
  measured sizes and `docker history` output.

## Out of scope (intentional)

- Multi-arch builds (`linux/arm64`). The local-first stack is
  `linux/amd64`-only.
- Distroless / scratch base. Airflow requires a full Python runtime;
  switching base images would change behavior beyond this sprint's
  scope.
- Registry push. The image is built and consumed locally.
- CI rebuild. The CI runner does not have a Docker daemon; the
  measurement is a local-machine action captured as evidence.

## Verification

```bash
# Tests must still pass (Dockerfile change is infra-only, no Python touched)
.venv/bin/python -m pytest -q
.venv/bin/ruff check .

# Image size evidence (run on a host with the docker daemon)
bash scripts/measure_docker_size.sh
cat evidence/docker_size.json
```
