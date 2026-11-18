# Review — platform .LM submission completion vs rubric

Date: 2026-08-11 · Branch `codex/phase06-llm-submission` (HEAD `d72f15f`, clean)
Plan: `plans/260809-2039-complete-phase2-llm-submission/`
Rubric: `docs/Coursework Tracking (Public) - rubic final-coursework (final - llm).csv`

## Verdict

Plan **not complete**. Rubric coverage **79 / 100 LLM points** executed and
audit-clean. 21 points (13 rows) remain `design_only`: Observability 8, Routing
& Gateway 13. Phase 04 is the single blocker; Phase 06 has 4 open closing steps.

## Measured state

| Check | Command | Result |
|---|---|---|
| Matrix rows | `docs/platform/rubric-matrix.csv` | 117 rows; LLM 47 executed / 13 design_only; ML 57 design_only |
| LLM points | sum over matrix | total 100, executed **79** |
| Evidence files | `docs/platform/evidence/llm/` | 47 canonical `.md` + Locust/warm-up artifacts |
| Strict audit (no validations) | `audit_phase2_evidence.py --strict --require-executed --track LLM --gitops-root …` | FAIL — exactly the 13 design_only rows, nothing else |
| Full gate | same + `--run-validations --ml 100 --llm 100 --phase1-base ddbcbe7… --accept-design-only <13 rows>` | **PASS** — "platform .ubric matrix is complete and consistent." |
| platform .o-regression | `.venv/bin/python scripts/run_stage1_quality_gates.py` | exit 0, `status: pass` |
| Worktrees | source + `~/Studying/FSDS/financial-distress-gitops` | both clean; gitops HEAD `921bdc1` = `gitops_sha` in evidence; `source_sha` `6dc70ba` is ancestor of HEAD (stamp rule satisfied) |
| Artifacts at declared paths | `src/agents/`, `apps/{feature,drift}-mcp/`, `src/llm/{model_server,benchmark,embedding_registry,citation_guard}.py`, both notebooks | all present |

So the 79 executed points survive the strictest available gate, including the
47 `validation_command` subprocesses. That part is real, not asserted.

## Phase status

| Phase | Declared | Actual |
|---|---|---|
| 1 | done (9/10) | consistent |
| 2 | done (4/5) | consistent |
| 3 | Completed | consistent (24 pts executed) |
| 4 | **Blocked** | correct — 21 pts unearned; source + GitOps manifests exist, no live cluster reconciliation |
| 5 | Completed | consistent (23 pts executed, live A/B captured) |
| 6 | In progress | correct — see gaps below |

`plan.md`'s phase table is stale for phases 1-2 ("In Progress" / "Pending"
vs the phase files' `done`). Cosmetic, but it misreports progress.

## Gaps blocking "complete"

1. **21 rubric points, phase 04** — needs schedulable cluster capacity, the four
   `REPLACE_WITH_KUBESEAL_OUTPUT` ciphertexts replaced, the web image digest
   pinned (`digest: ""` today), then live capture of: 5 gateway routes, TLS,
   auth challenge + 429, hide-services enforcement, Prometheus/Grafana metrics,
   Loki logs, Jaeger traces. Manifests and Argo Applications for
   `platform-observability` / `nginx-ingress` already exist, so this is a
   deploy-and-capture job, not new build work.
2. **`PHASE1_BASE_SHA` never frozen anywhere** — evidence contract and both plans
   reference `$PHASE1_BASE_SHA`, but no doc records the value. The final gate
   cannot be reproduced without it. Empirically the only base that passes the
   Phase-1-protected-path diff is `ddbcbe7bd41ae4883954b8a247efdc67c7329078`
   (`fix(generators): resolve generator package collision`, 2026-08-07); earlier
   bases fail on `src/collectors/`, `src/streaming/`, `docs/evidence/`,
   `docs/01_data_generator.md`. Record that SHA in `docs/platform/evidence-contract.md`.
3. **Mock-grade (phase 06 step 10) not done** — no row-by-row grade report against
   the canonical CSV under `plans/.../reports/`.
4. **`docs/submission/cost.md` incomplete** — per-session credit deltas and final
   balance still say "TBD phase-08" / "pending"; a plan success criterion.
5. **`docs/submission/README.md` stale** — still says "evidence materialization and
   SHA stamping pending commit approval" and "42 previously materialized" rows.
   Evidence is committed and stamped; the text under-reports the real state.
6. **Grader read access to the private GitOps repo** — granted/verified nowhere.
   Every `gitops_sha` link 404s for the grader until done.
7. **Final hibernation check open** — primary/secondary pools at 0 + evidence VM
   stopped not yet verified this session.

## Two ways to close

- **Full 100:** one cluster window for phase 04 capture (13 evidence files), then
  phase 06 steps 2-11. Everything else is already in place.
- **Ship 79 honestly:** run the final audit with the 13 rows in
  `--accept-design-only` (already passes today), fix gaps 2-7. Plan's cut ladder
  never authorized cutting observability ("Never cut: … observability"), so this
  concedes more than the ladder budgeted.

## Unresolved questions

- Is another GCP window available/affordable for the phase 04 capture, or is 79
  the target?
- Does the grader have a GitHub account handle to grant read access to?
