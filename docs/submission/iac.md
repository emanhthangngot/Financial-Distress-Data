# IaC

Terraform-provisioned GKE evidence cluster + GCE VM
(`financial-distress-gitops/terraform/gcp/`). Rows: `LLM-AC-14-IAC`.

- Plan/apply/cost output: **TBD phase-08** — link
  `docs/phase2/evidence/llm/LLM-a-terraform-full-thi-t-l-p.md` (or its actual
  slug — see `rubric-matrix.csv`) once executed.
- Repository split (`terraform/gcp/apis.tf`, `network.tf`, `gke.tf`, `vm.tf`,
  `registry.tf`, `iam.tf`, `outputs.tf`, `variables.tf`, `versions.tf`) —
  one file per service, per canonical row 67's `để ý cách chia folder theo
  từng service`.
- Ansible role idempotency proof (row 69): **TBD phase-08**.

Status: cluster live since 2026-08-08 (see `financial-distress-gitops` repo
history); evidence capture pending phase-08.
