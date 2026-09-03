# platform .luster runtime

`Dockerfile.pipeline` packages the existing platform .ource tree for a cluster
runtime. It does not alter `src/`, `dags/`, SQL, or the local Compose path. The
GitOps sibling repository owns the Kubernetes workload, immutable image digest,
PVCs, secrets, and resource requests.

Build locally with:

```bash
docker build -f infra/lakehouse-cluster/Dockerfile.pipeline .
```

The cluster image is an additional runtime target. Local `docker compose` and
the Stage 1 quality gates remain the reproduction path for the protected Phase 1
evidence set.
