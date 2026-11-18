---
phase: 8
title: "Flink CDC parallel ingestion path"
status: cancelled
priority: P2
effort: "2d"
dependencies: [7]
---

> **CANCELLED 2026-08-14 (user decision, ML track dropped).** Zero LLM rubric rows reference CDC (measured 2026-08-14). Closed only ML rows (~4 pts).
> Body below is kept as the historical record of what was planned/built; nothing further is executed against it. See `plan.md` Overview.

# Phase 8: Flink CDC parallel ingestion path

## Overview

Fix the architecture's one genuine ingestion weakness — `generator -> Kafka`
direct, which no real system does — by adding a log-based CDC path that captures
writes from an OLTP database. Added **in parallel**, so the platform .ath stays
byte-for-byte untouched and both paths can be compared against each other.

The comparison is the point: running both and reconciling them is stronger
evidence than either path alone, and it is a defensible novel-idea claim.

## Requirements

- Functional: a Flink CDC job reads Postgres logical replication and lands changes
  in the platform .ceberg Bronze layer; row counts reconcile with the generator
  path over the same window; the reconciliation is reported.
- Non-functional: zero modification to `src/streaming/`, `src/generator/` or
  `dags/`; the CDC path uses its own Postgres instance.

## Architecture

**Flink CDC, not Debezium + Kafka Connect.** Debezium captures changes; everything
else — delivery, schema evolution, failure recovery — remains the operator's
problem, and Kafka Connect is a second runtime to run. Current guidance is
explicit that when CDC events feed a single downstream consumer, the Kafka hop is
operational overhead with no architectural benefit. This project already runs
Flink, and Flink CDC embeds the Debezium engine directly against Postgres logical
replication. Net effect: the same capability, two fewer services than the
reference architecture.

**Own Postgres, deliberately.** CDC requires `wal_level=logical` and a replication
slot. The platform protected territory and reconfiguring it
would be a platform .utation. This phase provisions a dedicated cluster Postgres as
the OLTP source, fed by the platform .roduct plane's writes — which is also the
more honest production story, since the OLTP database is where a real application
writes.

**Parallel-path reconciliation.**

```
                  ┌─ generator -> Kafka -> (Phase 1, untouched) ─┐
  source events ──┤                                              ├─> reconcile report
                  └─ product writes -> Postgres WAL -> Flink CDC ┘
                                       -> Iceberg Bronze (Phase 2)
```

Both paths carry the same business keys, so a windowed count and key-set diff
gives a concrete correctness signal.

## Related Code Files

Source repo (all new):

- Create: `src/cdc/__init__.py`, `config.py`, `flink_cdc_job.py`, `reconcile.py`
- Create: `infra/cdc/Dockerfile` (flattened layout — phase 1 removed the `infra/phase2/` tier)
- Create: `tests/platform/pipelines/test_cdc_config.py`, `test_cdc_reconcile.py`
- Create: `dags/phase2/phase2_cdc_reconciliation.py` (thin wrapper, zero import-time side effects)
- Create: `docs/platform/adr/adr-013-cdc-ingestion-path.md`
- Modify: `configs/phase2-deployables.yaml` — add the CDC deployable

GitOps repo:

- Create: `platform/data/cdc-postgres.yaml`, `platform/data/flink-cdc-job.yaml`
- Modify: `platform/data/network-policies.yaml`

**Protected — must not appear in this phase's diff:** `src/streaming/`,
`src/generator/`, `src/transforms/`, `dags/*.py` outside `dags/phase2/`.

## Implementation Steps

1. Provision the CDC Postgres with `wal_level=logical`, a replication slot and a
   dedicated replication user with least privilege.
2. Write `src/cdc/flink_cdc_job.py` using the Flink Postgres CDC connector, with
   the Iceberg sink from phase 7. Handle the initial snapshot plus incremental
   phases explicitly.
3. Write `src/cdc/reconcile.py`: for a time window, compare row counts and
   business-key sets between the generator-fed Bronze and the CDC-fed Iceberg
   Bronze, emitting a structured report.
4. Add the thin `dags/phase2/` wrapper scheduling the reconciliation. Confirm it
   introduces no import-time side effects and renames no existing DAG ID or task.
5. Unit-test config parsing and reconciliation logic against fixtures — no live
   Postgres needed in the fast loop, matching the existing Flink test convention.
6. Run both paths concurrently over a real window; capture the reconciliation
   report and the Flink job UI.
7. Write ADR-013: why Flink CDC over Debezium + Kafka Connect, why a separate
   Postgres, and what the parallel-path comparison proves.
8. Confirm the protected-path diff is clean — this is the phase most likely to
   violate it, so check explicitly rather than assuming.

## Verification

```bash
.venv/bin/python -m pytest tests/platform/pipelines -k cdc
.venv/bin/python scripts/audit_phase2_evidence.py --matrix-only --strict
git diff --name-only $PHASE1_BASE_SHA..HEAD | grep -E '^(src/(collectors|transforms|quality|catalog|metadata|streaming|generator)|sql|dags/[^p])' && echo "PROTECTED VIOLATION" || echo "clean"
kubectl logs -l app=flink-cdc --tail=50
```

## Success Criteria

- [ ] Flink CDC job -> runs against the CDC Postgres -> lands inserts, updates and deletes in Iceberg Bronze
- [ ] Both ingestion paths -> run over the same window -> reconciliation report shows matching row counts and key sets
- [ ] Protected-path diff -> checked at phase end -> clean, no platform .ile touched
- [ ] `dags/phase2/phase2_cdc_reconciliation.py` -> imported -> no side effects, no existing DAG ID changed
- [ ] Strict `--track LLM` gate -> unchanged PASS 100/100

## ML rubric rows closed

- Novel idea candidate: dual-path ingestion with automated reconciliation —
  measurable, and absent from both reference repos
- Supports Improve-the-Data-Generator and Feature-Store rows by giving streaming
  features a real change-capture source

Approximately 4 points, subject to which novel-idea rows are claimed here versus
in phase 3.

## Risk Assessment

- **Highest protected-path risk in the plan.** The temptation to "just tweak" the
  generator to emit into the OLTP database must be resisted; the product plane
  writes there instead. Step 8's explicit check is mandatory.
- **Replication slots leak disk if the consumer stalls.** Set a slot size limit and
  alert on lag; an abandoned slot will fill the Postgres volume.
- **Reconciliation may legitimately not match** if the two paths observe different
  event sets. Define the comparison window and key scope precisely before
  claiming a mismatch is a bug.
