---
phase: 3
title: "Gap 03: Establish platform and Jenkins runtime"
status: blocked
priority: P1
effort: "Remaining implementation after capacity gate"
dependencies: ["phase-01-gates-and-inventory.md"]
---

# Gap 03: Establish platform and Jenkins runtime

## Objective

Use the existing platform/GitOps structure to restore only the missing runtime substrate and Jenkins
control plane.

## Tasks

1. Apply approved Terraform/Ansible changes only inside the measured zero-spend window.
2. Configure Jenkins LTS, JCasC, pinned plugins, persistent backup/restore and zero built-in executors.
3. Configure disposable Kubernetes agents with bounded resources and no production deploy credentials.
4. Verify Vault/ESO or credential-ID retrieval, redaction, agent cleanup and controller recovery.
5. Complete required mesh, namespace, ingress and service authorization checks needed by later gaps.

## Progress snapshot

Repository contracts are implemented and locally validated: `Jenkinsfile` is declarative with
`agent none`, a Kubernetes ephemeral-agent label, catalog validation, focused checks, redacted
delivery handoff and no direct cluster mutation; `infra/jenkins/jenkins.yaml` sets zero controller
executors and restricted agent security; `infra/jenkins/plugins.txt` pins the required plugins; and
`scripts/ci/delivery.py` plus 7 focused tests enforce digest-only promotion/rollback. The live
Jenkins controller, Kubernetes agent lifecycle, backup/restore, credential-ID retrieval, and
permission inspection remain unverified because no controller host or approved deployment window is
available. This phase is still blocked.

## Acceptance criteria

- [ ] Ansible -> configures the controller twice -> second run is idempotent and Jenkins health is green.
- [ ] Jenkins -> runs and cancels an agent build -> the ephemeral pod is isolated and deleted.
- [ ] Recovery operator -> restores controller state -> jobs, JCasC revision and credential references return without secret values.
- [ ] Platform operator -> inspects deployment permissions -> Jenkins cannot mutate production; Argo CD remains sole mutator.

## Risks

No quota or host means this gap remains blocked. Do not substitute Docker Compose or a screenshot for
runtime proof.
