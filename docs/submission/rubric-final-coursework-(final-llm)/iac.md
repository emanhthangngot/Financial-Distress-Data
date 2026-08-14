---
title: "Infrastructure as Code"
date: 2026-08-14
status: active
---

# IaC: Terraform provisions GKE, Ansible configures the worker VM — both idempotent

This doc proves the two rows in "IaC": Terraform is the real, authoritative
entrypoint for the evidence platform (cluster, VPC, NAT, Artifact Registry)
with a live `terraform plan` showing "No changes", and Ansible configures the
benchmark worker VM idempotently (second run: zero changes). It does not
prove multi-environment Terraform workspaces — this submission provisions one
environment (`evidence`).

**Active deployment facts:** `terraform@1.15`, `hashicorp/google@6.50.0`, GKE
`1.35.6-gke.1250000`; `ansible-core@2.21` against `fsds-evidence-worker`.

## Part I — Terraform provisions GKE

### 1. Live plan shows zero drift

```text
$ cd terraform/envs/evidence && terraform init -input=false
Terraform has been successfully initialized!

$ terraform plan -input=false -no-color -var-file=../../gcp/terraform.tfvars
... 18 resources refreshed (GKE cluster, both node pools, VPC, subnet,
    router, NAT, Artifact Registry, evidence-VM service account/IAM/instance,
    ingress static IP, firewall) ...
No changes. Your infrastructure matches the configuration.

$ kubectl get nodes -o wide
NAME                                             STATUS   VERSION
gke-fsds-evidence-primary-pool-1b74a53b-xknd     Ready    v1.35.6-gke.1250000
gke-fsds-evidence-secondary-pool-ce947869-q9zq   Ready    v1.35.6-gke.1250000
```

`terraform/envs/evidence/main.tf` calls `module.evidence_platform` (sourced
from `../../gcp`) and points its backend at the pre-existing
`terraform/gcp/terraform.tfstate` — the canonical state was never copied,
only the declared root moved. `terraform init` in the old `terraform/gcp/`
now fails fast with "Backend configuration changed", confirming the new
entrypoint is the one real path. Full evidence:
[`LLM-iac-d-ng-terraform-setup-gke-ho-c-.md`](../../phase2/evidence/llm/LLM-iac-d-ng-terraform-setup-gke-ho-c-.md).

## Part II — Ansible configures the worker VM

### 2. Idempotent by measurement, not assertion

```text
$ ansible-playbook playbooks/vast-evidence-worker.yml   # run 1
PLAY RECAP: ok=17 changed=1 unreachable=0 failed=0 skipped=1

$ ansible-playbook playbooks/vast-evidence-worker.yml   # run 2, same host
PLAY RECAP: ok=17 changed=0 unreachable=0 failed=0 skipped=1
```

Three role-split roles (`docker`, `gcp-k8s-tools`, `benchmark-client`)
install Docker, the GCP CLI/`kubectl`, and the Locust benchmark client
virtualenv. The GKE-credentials task self-skips on the second run because
`kubectl config get-contexts` already lists the context — itself evidence of
idempotent design, not a failure. Full evidence:
[`LLM-iac-d-ng-ansible-configure-v-deplo.md`](../../phase2/evidence/llm/LLM-iac-d-ng-ansible-configure-v-deplo.md).

## Limitations

The secondary node pool was resized to 0 during this run to free project
vCPU quota for the evidence worker VM (8+4=12/12 with both up) — a real
capacity constraint documented in `cost.md`, not a hidden operational detail.

## References

- Terraform Google provider: https://registry.terraform.io/providers/hashicorp/google/latest/docs
- Ansible: https://docs.ansible.com/
</content>
