---
phase: 1
title: "Reconcile contracts, capacity and platform gaps"
status: done (9/10 criteria; gcp-down deferred to end of multi-phase session)
priority: P1
effort: "1.5d"
dependencies: []
---

# Phase 1: Reconcile contracts, capacity and platform gaps

## Overview

Make the audit gate satisfiable and the cluster honest **before** any feature
code is written against them. The 2026-08-09 red team found seven Critical
defects that all share one shape: the plan was built against a starting state
that does not exist. This phase closes that gap, then harvests the three IaC and
security points — which turned out to need real build work, not just capture.

Rubric rows owned (3 points):

| Points | rubric_id | artifact_path (authority) |
|---:|---|---|
| 1 | `LLM-iac-d-ng-terraform-setup-gke-ho-c-` | gitops `terraform/envs/evidence/main.tf` — **placeholder today** |
| 1 | `LLM-iac-d-ng-ansible-configure-v-deplo` | gitops `ansible/playbooks/vast-evidence-worker.yml` — real |
| 1 | `LLM-security-centralize-secret-management` | gitops `platform/security/sealed-secrets.yaml` — **placeholder today** |

Only the Ansible row was genuinely "earned but uncaptured". The other two point
at empty placeholder files, so their evidence would cite a comment.

## Requirements

- Functional: `--require-executed` is satisfiable in principle; `artifact_path`
  and `rubric_id` collisions resolved; a Phase 2 dependency manifest exists and
  CI installs it; sealed-secrets actually runs; the Terraform row's declared
  artifact is the real entrypoint; NetworkPolicy is enforced; every GitOps path
  phases 2-5 write to has an Argo Application watching it.
- Non-functional: `.venv` (Phase 1) is not mutated — proven by re-running the
  Phase 1 gate; the cluster returns to zero nodes and the evidence VM stops when
  the session ends.

## Architecture

Six contract defects to close, in dependency order. Each is cheap now and
expensive after code lands.

**1. `evidence_type` is generated, and nothing flips it.** All 117 rows are
`design_only`, including the seven with real evidence.
`scripts/_phase2_rubric_items.py:919` defaults it and `EXPLICIT_IMPLEMENTATION`
overrides it; the CSV is regenerated from that module. Establish the loop —
flip in the module, regenerate the CSV, regenerate the requirement tests,
re-run `--matrix-only --strict` — and prove it on the seven phase-04 rows.
Every later phase repeats this loop as its last step.

**2. The SHA contract is unsatisfiable as written.**
`audit_phase2_evidence.py:580-640` requires `source_sha == HEAD` and a clean
worktree, but the evidence records the SHA of the commit that contains it, and
`git commit --amend` produces a new HEAD. A commit cannot contain its own hash.
Fix the auditor, not the ritual: accept a `source_sha`/`gitops_sha` that is
**HEAD or an ancestor of HEAD**, and additionally assert that the diff from that
commit to HEAD touches only `source_sha`/`gitops_sha` lines in evidence files.
That keeps the property the gate actually wants — the recorded commit contains
the implementation, and nothing else changed since — while being reachable.

**3. `--require-executed` is all-or-nothing, so any cut fails the gate.** Add
`--accept-design-only <rubric_id>[,<rubric_id>...]`, which downgrades exactly
the named rows to a warning. The cut ladder in `plan.md` stays honest because
cutting forces you to name the row on the command line and in
`docs/submission/README.md`.

**4. Requirement tests are generator-owned and vacuous.** They carry a
"do not hand-edit; regenerate instead" banner and assert only that the evidence
file parses, nine keys are non-empty, and `artifact_path` `is_file()` — which a
five-line placeholder YAML satisfies. Extend
`scripts/generate_phase2_requirement_tests.py` to emit a per-row behavioral
assertion sourced from a new `behavioral_assertion` column, and add a
non-placeholder check (the artifact must contain something other than comments).
Every later phase then *regenerates* these tests; no phase hand-edits them.

**5. The auditor claims a secret gate it does not have.** `redaction_status` is
a self-declared string; there is no scanning. Add a denylist pass over every
evidence file body: the GCP project ID, the control-plane IP, `34.21.242.110`,
the SSH username, `ghp_`/`github_pat_`, `-----BEGIN`, `Authorization:` headers,
and base64 blobs over 200 chars. Also correct the two existing evidence files
that assert `redaction_status: none — public repo` for artifacts that live in
the **private** GitOps repo.

**6. Path and ID collisions.** Adopt the matrix `artifact_path` as authority
(see `plan.md`'s Path Authority Rule). Retarget exactly one pair: both
`LLM-demonstrate-basic-underst-*` rows point at `notebooks/agent-mcp-demo.ipynb`;
give the second row its own notebook path in `EXPLICIT_IMPLEMENTATION`.

Then four platform gaps:

**Capacity.** `make gcp-up` restores `primary-pool` only, one `e2-standard-8`.
Produce a written vCPU/GiB budget for the full phase 2-5 workload against ~7.6
allocatable, including the already-running Argo CD, cert-manager, NGINX,
Knative, KServe and the TEI embedding pod (requests 1 CPU / 2 GiB). Answer
empirically whether stopping the evidence VM frees enough quota to run
`secondary_pool_node_count = 1` (8 + 4 = 12, exactly the `CPUS_ALL_REGIONS`
cap). Without headroom, phase 3's KEDA scale-out evidence has nothing to scale
into.

**NetworkPolicy.** `gke.tf` has no `network_policy` block, so enforcement is
off and Cloud NAT is provisioned — an agent pod's `curl https://example.com`
will succeed. Enable it, then prove enforcement empirically with a deny-all in a
scratch namespace before phases 3-4 write any evidence citing it.

**Hibernation correctness.** `gcp-down` never stops the evidence VM (2 vCPU,
billed continuously). Add `instances stop`/`start` to the targets and instance
state to `gcp-status`. Add `lifecycle { ignore_changes = [node_count] }` to both
pools so an imperative resize does not make `terraform plan` diff — the
Terraform row's proof is a no-change plan.

**Argo coverage.** Four Applications exist; nothing watches `platform/agents`,
`platform/llm`, `platform/observability` or `charts/`, and `applicationset-dev.yaml`
generates from a non-existent `apps/dev/*`. Without this, phases 2-4 will commit
correct manifests, see everything `Synced Healthy`, and deploy nothing.

## Related Code Files

- Modify: `scripts/audit_phase2_evidence.py` (ancestor-SHA rule,
  `--accept-design-only`, secret denylist)
- Modify: `scripts/_phase2_rubric_items.py` (`evidence_type` flips, the one
  notebook retarget, `behavioral_assertion` column)
- Modify: `scripts/generate_phase2_requirement_tests.py` (per-row assertion,
  non-placeholder check)
- Regenerate: `docs/phase2/rubric-matrix.csv`, `tests/phase2/requirements/*`
- Create: `requirements-phase2.txt` (or a `[project.optional-dependencies] phase2`
  group in `pyproject.toml`)
- Modify: `.github/workflows/phase2-ci.yaml` (install the phase-2 deps; replace
  the `eval` on the `test_selector` input with an array form)
- Modify: `docs/phase2/evidence/llm/LLM-ci-cd-job-1.md`,
  `LLM-ci-cd-job-2.md` (redaction status)
- Create/modify (GitOps): `terraform/gcp/gke.tf` (network policy, lifecycle),
  `terraform/envs/evidence/main.tf` (make it the real entrypoint),
  `platform/security/sealed-secrets.yaml` (real controller),
  `Makefile` (VM stop/start, node-registration poll before `kubectl wait`),
  `argocd/applications/platform-agents.yaml`,
  `argocd/applications/platform-observability.yaml`,
  `argocd/applications/platform-llm.yaml`, `apps/dev/.gitkeep`
- Create: 3 evidence files under `docs/phase2/evidence/llm/` (IDs copied from
  the table above)

## Implementation Steps

1. Read `scripts/audit_phase2_evidence.py` executed-mode checks and one accepted
   phase-04 evidence file end to end. Do not infer the contract.
2. Close contract defects 1-6 above. Prove the whole loop by flipping the seven
   phase-04 rows to `executed`, regenerating the CSV and tests, and running
   `--strict --require-executed --track LLM --accept-design-only <the 53 not yet
   done>` — it must pass on the seven.
3. Create the Phase 2 dependency manifest with `fastapi`, `feast`, `hypothesis`,
   `mutmut`, `locust`, `mcp` and the rest; install into **`.venv-phase2` only**;
   wire it into `phase2-ci.yaml`. Then run
   `.venv/bin/python scripts/run_stage1_quality_gates.py` to prove `.venv` is
   untouched.
4. `make gcp-up`; record the pre-session credit balance. Fix the Makefile's
   node-registration race (`kubectl wait --all` exits non-zero when zero Nodes
   are registered, aborting before the ingress and cert-manager restarts).
5. Write the capacity budget. Stop the evidence VM, try
   `secondary_pool_node_count = 1`, and record whether the quota allows it.
6. Enable NetworkPolicy on the cluster and prove enforcement with a scratch
   deny-all namespace: a pod inside it must fail to reach the internet.
7. Add the three missing Argo Applications and the `apps/dev/` directory, and
   confirm each new path actually reconciles.
8. Install sealed-secrets for real (controller + key pair + one sealed secret
   reconciled through Argo), replacing the placeholder. This is a prerequisite
   for phase 4's basic-auth secret and phase 5's registry credentials.
9. Make `terraform/envs/evidence/main.tf` the real entrypoint for the row's
   declared artifact path — either move the `terraform/gcp/` root behind it or
   have it call that module. Then run `terraform plan` with the cluster up and
   capture a no-change plan plus `terraform output`.
10. Run the Ansible evidence-host playbook twice against the (now started) VM;
    capture both recaps and `changed=0` on the second.
11. Write the three evidence files. Record the security row honestly:
    **sealed-secrets in-cluster + GitHub Actions encrypted secrets. There is no
    OIDC** — `grep id-token .github/workflows/` returns zero, and the pipeline
    uses two long-lived PATs. Do not claim otherwise.
12. Flip those three rows to `executed`, regenerate, re-run the audit.
    `make gcp-down` (now also stopping the VM); record the credit delta.

## Success Criteria

- [x] Maintainer -> runs the strict audit with the seven phase-04 rows flipped -> passes, proving the executed gate is satisfiable end to end. (verified: `--strict --require-executed --track LLM --accept-design-only <53 remaining>` exits 0)
- [x] Maintainer -> stamps a test evidence file and commits -> the ancestor-SHA rule accepts it, and a tampered non-ancestor SHA is rejected. (`test_ancestor_sha_allows_only_evidence_sha_delta`, `test_nonancestor_sha_is_rejected` in `tests/phase2/test_rubric_matrix.py`)
- [x] Maintainer -> runs the audit against an evidence file containing a fake `ghp_` token -> the secret denylist fails it. (`test_secret_denylist_rejects_adversarial_forms`)
- [x] Test runner -> regenerates the requirement tests -> each row's test asserts something behavioral, and a placeholder-comment artifact fails the non-placeholder check. (`test_generated_contract_rejects_placeholder_artifacts` + friends; 72 requirement tests pass)
- [x] Phase 1 maintainer -> runs the Stage 1 quality gate after the phase-2 install -> passes, proving `.venv` untouched. (`.venv/bin/python -m pytest tests -m "not slow"` → 658 passed; ruff/black clean)
- [x] Operator -> deploys a deny-all NetworkPolicy in a scratch namespace -> a pod inside it cannot reach the internet. (`platform/security/default-deny-networkpolicy.yaml`, GitOps-tracked via `platform-security` Argo app, live in `networkpolicy-negative-test` ns; probe pod log: `curl: (28) Resolving timed out` → `EGRESS_BLOCKED`)
- [x] Operator -> reads the capacity budget -> knows the vCPU/GiB ceiling for phases 2-5 and whether a second node is available. (`docs/submission/cost.md`: 8+2=10/12 with VM up, 8+4=12/12 only after VM stop, secondary pool must return to 0 before VM restart)
- [x] Platform operator -> runs `terraform plan` with the cluster up -> gets "No changes", captured with `terraform output`. (`terraform/envs/evidence` init + plan against live cluster: "No changes. Your infrastructure matches the configuration." — `docs/phase2/evidence/llm/LLM-iac-d-ng-terraform-setup-gke-ho-c-.md`, flipped to `executed`)
- [x] Platform operator -> runs the Ansible playbook twice -> healthy host, `changed=0` on the second run. (run 1 `changed=1`, run 2 `changed=0`; `docs/phase2/evidence/llm/LLM-iac-d-ng-ansible-configure-v-deplo.md`, flipped to `executed`)
- [ ] Operator -> runs `make gcp-down` then `gcp-status` -> node pools at zero **and** the evidence VM stopped. **Deliberately deferred** — user decision 2026-08-10: keep the cluster up across phases 2-6 in this session rather than hibernate between every phase; run this at the true end of the multi-phase session.

## Risk Assessment

- **This phase earns 3 points for 1.5 days.** That is the correct trade: every
  later phase depends on a gate that is currently unsatisfiable and a cluster
  that cannot schedule the workload. Skipping it moves the failure to day 9.
- **Enabling NetworkPolicy may require a cluster recreate** on some GKE paths.
  Mitigation: attempt the in-place update first, and if it forces replacement,
  decide immediately — the sandbox and hide-services rows (3 points) depend on
  enforcement, and a recreate is cheaper on day 1 than on day 7.
- **Making `terraform/envs/evidence/main.tf` the real root risks state
  migration.** Mitigation: prefer a thin module call that leaves
  `terraform/gcp/` state intact over moving the root; the row asks for
  Terraform-provisioned GKE, not a specific directory layout.
- **Auditor changes could weaken the gate.** Mitigation: the ancestor rule adds
  the "only SHA lines changed since" assertion, so it is narrower than a plain
  ancestor check; `--accept-design-only` requires explicit row IDs and never
  takes a wildcard.
