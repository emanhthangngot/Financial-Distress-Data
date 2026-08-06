---
phase: 2
title: "Unify Flink job home and repair the dead compose mount"
status: pending
priority: P1
effort: "2-3h"
dependencies: [1]
---

# Phase 2: Unify Flink job home and repair the dead compose mount

## Overview

The Flink profile is wired to a directory that holds no job, on an image that
cannot run PyFlink. Give the job one home under `src/streaming/flink/jobs/`,
build the image that has PyFlink and the Kafka connector, and mount the paths the
docs already describe.

## Requirements

- Functional: `price_event_job.py` exists in exactly one tracked location, that
  location is mounted into the jobmanager, and the container has PyFlink 1.20.3
  plus `flink-sql-connector-kafka-3.3.0-1.20.jar`.
- Functional: `docs/flink-stream-processing.md`'s reproduce commands name paths
  that exist inside the running container.
- Non-functional: Flink stays opt-in — `profiles: ["flink"]` unchanged, not
  started by plain `docker compose up`.
- Non-functional: no change to DAG 04, `src/streaming/events.py`, or the Kafka
  wire contract.

## Architecture

Current, broken:

```
flink/jobs/price_event_job.py          tracked, NOT mounted, NOT referenced by compose
src/streaming/flink/jobs/README.md     mounted -> /opt/flink/jobs   (README only)
src/streaming/flink/client.py          REST client, imported by DAG 04 + tests   [keep]
infra/flink/Dockerfile                 PyFlink 1.20.3 + kafka connector, built by NOTHING
docker-compose.yml:170                 image: apache/flink:1.19-java17  (no python, no connector)
docker-compose.yml:189                 ./src/streaming/flink/jobs:/opt/flink/jobs:ro
docs/flink-stream-processing.md:34,38  flink run --python /opt/flink/project/flink/jobs/...
                                       --config /opt/flink/config/flink-streaming.yaml
                                       (neither mount exists)
```

Target:

```
src/streaming/flink/
  __init__.py
  client.py                            unchanged
  jobs/
    README.md
    price_event_job.py                 moved here; single home
infra/flink/Dockerfile                 now the build source for flink-jobmanager/-taskmanager
docker-compose.yml                     build: {context: ., dockerfile: infra/flink/Dockerfile}
                                       image: financial-distress-flink:stage1
                                       volumes:
                                         - ./src/streaming/flink/jobs:/opt/flink/jobs:ro
                                         - ./configs:/opt/flink/config:ro
docs/flink-stream-processing.md        flink run --python /opt/flink/jobs/price_event_job.py \
                                         --config /opt/flink/config/flink-streaming.yaml
```

Two path questions the docs raise, decided here:

- **`/opt/flink/project` is dropped.** It implied a whole-repo bind mount. The job
  is self-contained; mounting only the jobs directory is the smaller surface.
  Docs move to `/opt/flink/jobs/price_event_job.py`.
- **`/opt/flink/config` is added** as a read-only mount of `configs/`, which is
  where `flink-streaming.yaml` and `flink-restart-probe.yaml` already live. The
  docs already assume this path; compose just never provided it.

**Version resolution: 1.20.3 everywhere.** Decided in validation session 1;
plan-level Open Question 1 is closed. Evidence: `infra/flink/Dockerfile:1`
(`FROM flink:1.20.3-scala_2.12`), `configs/flink-streaming.yaml:3`, and
`configs/flink-restart-probe.yaml:3` all say 1.20.3, and the pinned connector jar
is `3.3.0-1.20`. Only `docker-compose.yml` says 1.19, and once compose builds
from the Dockerfile the stock `image:` tag stops being a version source at all.

The captured Flink evidence was checked directly and does **not** block this:
`docs/evidence/flink/{baseline,optimized}-contract.json` and the `*-runtime.json`
files record no Flink version string, so no committed artifact asserts 1.19.
Nothing needs regenerating for the version change alone.

## Related Code Files

- Create: `src/streaming/flink/jobs/price_event_job.py` (moved via `git mv`)
- Modify: `docker-compose.yml` (flink-jobmanager + flink-taskmanager service defs)
- Modify: `docs/flink-stream-processing.md` (reproduce commands, lines ~30-40)
- Modify: `scripts/run_mini_coursework_submission.py:48` (`Proof` code_reference path)
- Modify: `src/streaming/flink/jobs/README.md` (state that this is the mounted job root)
- Delete: `flink/` (empty after the move)

## Implementation Steps

1. `git mv flink/jobs/price_event_job.py src/streaming/flink/jobs/price_event_job.py`
   then `rmdir` the emptied `flink/jobs` and `flink`. Use `git mv` so history follows.
2. Point both flink services at the Dockerfile:
   ```yaml
   flink-jobmanager:
     profiles: ["flink"]
     build:
       context: .
       dockerfile: infra/flink/Dockerfile
     image: financial-distress-flink:stage1
   ```
   Apply the identical `build`/`image` pair to `flink-taskmanager` so the
   taskmanager can execute Python UDFs. Remove both `image: apache/flink:1.19-java17`
   lines. Keep `profiles`, `depends_on`, `FLINK_PROPERTIES`, healthcheck, and the
   `flink-checkpoints` volume exactly as they are.
3. Add the config mount to the jobmanager volumes and keep the jobs mount:
   ```yaml
   volumes:
     - ./src/streaming/flink/jobs:/opt/flink/jobs:ro
     - ./configs:/opt/flink/config:ro
     - flink-checkpoints:/tmp/flink-checkpoints
   ```
4. Rewrite the two `flink run` commands in `docs/flink-stream-processing.md` to
   `/opt/flink/jobs/price_event_job.py`. Keep
   `--config /opt/flink/config/flink-streaming.yaml` — that path is now real.
   Keep the `docker compose --profile flink build flink-jobmanager` line; it is
   correct again.
5. Fix the stale proof path in `scripts/run_mini_coursework_submission.py:48`:
   `"flink/jobs/price_event_job.py"` -> `"src/streaming/flink/jobs/price_event_job.py"`.
6. Update `src/streaming/flink/jobs/README.md` to say the directory is mounted
   read-only at `/opt/flink/jobs` and now contains the job, not just jars.
7. Static verify:
   ```bash
   docker compose config >/dev/null            # wiring parses, mounts resolve
   git grep -n "flink/jobs" -- ':!plans'       # no path outside src/streaming survives
   .venv/bin/python scripts/run_stage1_quality_gates.py
   ```
8. **Opt-in live verify (operator authorizes; time-costly per AGENTS.md).** Only
   if the operator asks for it:
   ```bash
   ENABLE_FLINK=1 docker compose --profile flink build flink-jobmanager
   ENABLE_FLINK=1 docker compose --profile flink up -d kafka flink-jobmanager flink-taskmanager
   docker compose --profile flink exec flink-jobmanager ls /opt/flink/jobs /opt/flink/config
   docker compose --profile flink exec flink-jobmanager python -c "import pyflink; print(pyflink.__file__)"
   ```
   If this step is skipped, say so in the PR. Do not claim a live run that did
   not happen.

## Success Criteria

- [ ] Maintainer -> `git grep price_event_job` -> one source path,
      `src/streaming/flink/jobs/price_event_job.py`, plus doc/script references
      that all point at it.
- [ ] `docker compose config` -> exits 0 and shows the jobmanager building from
      `infra/flink/Dockerfile` with both the jobs and config mounts.
- [ ] Reader -> follows `docs/flink-stream-processing.md` reproduce block ->
      every path named in it is a path compose actually creates.
- [ ] `scripts/run_stage1_quality_gates.py` -> same result as the phase-1 baseline.
- [ ] Plain `docker compose up` -> starts no Flink container (profile intact).

## Risk Assessment

- Risk: the Dockerfile was orphaned because the build was broken (network fetch of
  the connector jar at line 9-10 can fail behind a proxy). Mitigation: step 8's
  build is the first thing to try if the operator opts in; if the jar fetch fails,
  vendor the jar under `infra/flink/lib/` and `COPY` it instead of `wget`.
- Risk: 1.19 -> 1.20.3 invalidates a captured Flink benchmark artifact under
  `docs/evidence/flink/`. **Checked and cleared** in validation session 1: the
  10 committed JSONs record no version string, so none of them contradicts
  1.20.3. If a future run needs regenerating, use `scripts/run_flink_benchmark.py`
  and `scripts/audit_flink_evidence.py` — never hand-edit `docs/evidence/**`.
- Risk: taskmanager also needs Python and was left on the stock image.
  Mitigation: step 2 explicitly applies the same build to both services.
- Rollback: `git revert` the commit; the job file returns to `flink/jobs/` and
  compose returns to the (broken but inert, profile-gated) prior state.
