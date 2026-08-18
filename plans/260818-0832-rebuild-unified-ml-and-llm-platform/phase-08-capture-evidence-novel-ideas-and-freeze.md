---
title: "Phase 8: Capture Evidence, Novel Ideas And Freeze"
status: todo
priority: P1
effort: "1.5 weeks"
dependencies: [2, 3, 4, 5, 6, 7, 9]
---

# Phase 8: Capture Evidence, Novel Ideas And Freeze

## Overview

Deliver the three novel ideas, the remaining documentation rows, and then capture
evidence for all 161 rows in one disciplined pass, audit strictly with zero cuts,
mock-grade row by row, reconcile the cost ledger, and freeze.

## Requirements

Functional — novel ideas (**6 rows, 18 points** — mini 2 x 5 pts, ML 2 x 2 pts, LLM 2 x 2 pts):
- [ ] DuckLake vs Iceberg benchmark on the streaming small-file problem, with measured results
- [ ] Point-in-time leakage guard for the feature store, with a demonstrated caught leak
- [ ] LLM semantic cache + speculative decoding benchmark, with measured TTFT and token-cost deltas
- [ ] **Three further ideas, one per uncovered row** — see the assignment note below; three locked ideas cannot cover six rows
- [ ] Each idea documented with the idea, the method, and proof it worked

Functional — documentation and repository rows:
- [ ] README with business domain, table of contents, repo structure, and a high-level deployment diagram where every component is a deployable unit
- [ ] Diagram arrows follow data flow, are numbered and described, with separate numbering per user flow
- [ ] Docstrings on every module, class and function; file-level descriptions
- [ ] Low-level ML design documenting 5 key classes
- [ ] Design patterns identified and evidenced in the code
- [ ] Docker image size reduction documented, from-value to to-value, with the optimization method named

Functional — closeout:
- [ ] Evidence captured for all 161 rows into the unified tree
- [ ] `audit_rubric_evidence.py --strict --require-executed --run-validations` passes with zero design-only rows
- [ ] Row-by-row mock grade produced
- [ ] Cost ledger reconciled against actual GCP billing
- [ ] Cluster hibernated; final revisions tagged in both repos

## Architecture

Evidence capture is a single pass, not an ongoing trickle, because screenshots and
live-cluster artifacts must all reflect the same final system state. A screenshot
taken in week 4 against a component reinstalled in week 8 is stale evidence, and
the auditor cannot detect that. So the cluster is brought fully up, everything runs,
and capture happens in one window.

The three novel ideas are placed here rather than earlier because each builds on
finished infrastructure: DuckLake needs the streaming small-file problem to exist
(phase 3), the leakage guard needs real point-in-time joins over real volume
(phases 2-3, 5), and the semantic cache needs the benchmarked LLM platform (phase 6).

**Six novel-idea rows, 18 points, all six now assigned.** mini has two at **5 points
each** — the most valuable novel-idea rows in the coursework — plus two at 2 points
in each of ML and LLM. mini's sections are pure data engineering (Engineering
Fundamentals, Data Generator, Processing Jobs, Data Storage, Data Governance), so
its two ideas must be data ideas, not platform or LLM ideas.

| # | Idea | Row | Pts | Why it fits that rubric | Proof |
|---|---|---|---|---|---|
| 1 | **DuckLake vs Iceberg** on the streaming small-file problem | mini | 5 | Table-format choice is a Data Storage concern | File-count growth, commit latency, query latency before/after compaction, both formats, same write pattern |
| 2 | **Point-in-time leakage guard** | mini | 5 | Correctness check over the pipeline — a Data Governance concern | Guard catches a deliberately introduced leak; clean run over the real training pull |
| 3 | **Iceberg snapshot incremental versioning** vs copy-based | ML | 2 | ML rubric owns the data-versioning row this extends | Storage delta per training run showing metadata-only growth |
| 4 | **Sidecar vs ambient mesh, measured** | ML | 2 | ML rubric owns the service-mesh row this extends | Run the same workload under both modes and report RAM, p99 latency and per-pod overhead. The platform ships sidecar mode by decision; this idea is the measurement that justifies it — including the cost paid, not only the benefit. A comparison that only flatters the chosen mode is not a finding. |
| 5 | **GraphRAG on Neo4j** beside the vector RAG | LLM | 2 | Multi-hop retrieval the vector path cannot do | Retrieval precision and answer correctness vs the Feast-vector baseline on a fixed question set |
| 6 | **LLM semantic cache + speculative decoding** | LLM | 2 | Serving-layer optimization | TTFT, round-trip, token cost before/after, plus cache hit rate |

Two constraints on this set. First, **no artifact is reused across two rows** — a
grader comparing the mini and ML submissions must not find the same write-up twice.
Second, **KV-cache aware routing is deliberately not on this list**: it stays in
phase 6 as evidence for the "benchmark model server and optimize the platform" row,
where it already earns points. Promoting it here would double-count one measurement.

Neo4j earns row 5; it does **not** replace the required RAG path. The RAG rubric row
says the chunks' embedding vectors go into the feature store through Feast, and that
remains the graded path — the graph sits beside it.

## Related Code Files

- Create: `scripts/run_ducklake_iceberg_benchmark.py`, `src/quality/pit_leakage_guard.py`, `scripts/run_semantic_cache_benchmark.py`, `docs/novel-ideas.md`, `docs/low-level-design.md`, `docs/design-patterns.md`, `docs/docker-optimization.md`, `scripts/capture_evidence.py`, `scripts/mock_grade.py`, `docs/cost.md`
- Modify: `README.md`, `images/architecture/` (new deployment diagram), all modules lacking docstrings
- Create: `docs/evidence/**` (161 artifacts)

## Implementation Steps

1. **DuckLake vs Iceberg benchmark.** Replay the same streaming write pattern into both formats; measure file count growth, checkpoint/commit latency, and query latency before and after compaction. Report where each wins and state the conclusion honestly, including where Iceberg is the right production choice despite DuckLake's numbers.
2. **Point-in-time leakage guard.** Implement a check that detects a feature computed from data timestamped after the label event, run it over the training pull, and deliberately introduce a leak to prove the guard catches it. A guard that has never caught anything is not proof.
3. **Semantic cache + speculative decoding.** Add an embedding-similarity cache in front of the LLM gateway and enable speculative decoding on the model server; measure TTFT, total round-trip and token cost before and after, and report the cache hit rate.
4. Redraw the deployment diagram against the running cluster: every box a deployable unit, arrows following data flow with numbered descriptions, separate numbering and colour per user flow (end user, developer, analytic stakeholder), dashed arrows reserved for non-primary flows.
5. Rewrite `README.md`: business domain, table of contents, repo structure table, the diagram, and links out to `docs/` — summary only, detail lives in `docs/`.
6. Sweep docstrings across every module, class and function; add file-level descriptions. Enforce with a lint rule so it cannot regress.
7. Write the low-level ML design naming 5 key classes with their method signatures and responsibilities.
8. Evidence the design patterns and the layering that phases 5-7 **built** — this step verifies and documents, it does not introduce architecture. For each of the five patterns in `plan.md`, cite the interface, at least two implementations or call sites, and the test that exercises it through the abstraction. Add a dependency check proving the layering holds: no import from the service layer into a framework or store client, and none from a repository back up into a service. A pattern with one implementation and no test is decoration — either it earns its place or it comes out of the write-up.
9. Re-measure Docker image sizes: baseline vs multi-stage optimized, per image, with the from→to values and the method.
10. Bring the whole cluster up. Run every pipeline, service and agent. Capture all 161 evidence artifacts in one window using `scripts/capture_evidence.py` for the automatable ones and a checklist for screenshots.
11. Run the strict audit with validations. Fix every finding. Re-run until it passes with zero cuts and zero design-only rows.
12. Produce the row-by-row mock grade: rubric ID, points claimed, artifact, and a one-line justification.
13. Reconcile the cost ledger against actual GCP billing once usage reporting has caught up. Report the real figure, not an estimate.
14. Hibernate the cluster, tag the final revision in both repos, and record both SHAs in the submission index.

## Success Criteria

- [ ] Six novel-idea documents, each with a method and a measured result table, one per rubric row, no artifact reused across two rows
- [ ] The leakage guard catches a deliberately introduced leak, captured
- [ ] Deployment diagram matches the running cluster component-for-component, with numbered per-flow arrows
- [ ] README carries business domain, TOC, repo structure and the diagram, and links to `docs/`
- [ ] Docstring lint passes across `src`, `dags`, `apps`, `scripts`
- [ ] Low-level design documents exactly 5 key classes that exist in the code
- [ ] Every claimed design pattern cites an interface, ≥2 implementations or call sites, and a test that goes through the abstraction
- [ ] An automated import check proves the layering direction holds across `src/` and `apps/`
- [ ] Docker size table gives from→to per image with the method named
- [ ] All 161 evidence artifacts exist, and each was generated during this plan
- [ ] `python scripts/audit_rubric_evidence.py --strict --require-executed --run-validations --gitops-root ../financial-distress-gitops` exits 0
- [ ] Mock grade totals 100/100 on each of the three rubric scales (mini, ML, LLM), reported separately — never as one blended 300-point figure
- [ ] Cost ledger reports an actual billed figure inside the free-trial credit
- [ ] Both repos tagged; cluster hibernated

## Risk Assessment

- **Single-window capture means a cluster failure mid-window costs the whole window.** Mitigation: capture in dependency order (data → platform → ML → LLM → gateway) so a failure loses only the tail; automate everything automatable so only screenshots need the live window.
- **The audit will surface gaps at the worst possible time.** Mitigation: run `--check-artifacts` at the end of every phase from phase 2 onward, so phase 8 discovers presentation gaps rather than structural ones.
- **The novel ideas may not produce a favourable result.** That is acceptable and should be reported as measured — the rubric asks for proof it worked, meaning proof the experiment ran and yielded a real finding. Do not tune a benchmark until it flatters the idea.
- **Credit may run out before the capture window.** Mitigation: track spend weekly from phase 4 onward, not at the end. If burn projects past the credit before week 9, hibernate more aggressively and cut Superset and the third novel idea first.
- **Cost reconciliation depends on GCP billing lag.** Mitigation: schedule the final reconciliation ≥24 h after the last cluster window, and do not freeze the submission until the real figure is in.
