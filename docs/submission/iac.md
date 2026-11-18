# IaC

Terraform-provisioned GKE evidence cluster + GCE VM
(`financial-distress-gitops/terraform/gcp/`). Rows: `LLM-AC-14-IAC`.

- Plan/apply/cost output: the executed Terraform evidence is linked from the
  canonical `LLM-iac-d-ng-terraform-setup-gke-ho-c-` row in
  `docs/platform/rubric-matrix.csv`.
- Repository split (`terraform/gcp/apis.tf`, `network.tf`, `gke.tf`, `vm.tf`,
  `registry.tf`, `iam.tf`, `outputs.tf`, `variables.tf`, `versions.tf`) —
  one file per service, per canonical row 67's `để ý cách chia folder theo
  từng service`.
- Ansible role idempotency proof is linked from the executed
  `LLM-iac-d-ng-ansible-configure-v-deplo` row.

Status: IaC and Ansible rows are executed. The evidence plane is hibernated
between capture sessions; current node/VM state is recorded in `cost.md`.
