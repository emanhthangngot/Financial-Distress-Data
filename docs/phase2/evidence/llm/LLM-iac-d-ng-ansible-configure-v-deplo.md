# Evidence — IaC: Ansible configures and deploys services on the VM

Proves `ansible/playbooks/vast-evidence-worker.yml` (financial-distress-gitops)
configures the evidence/benchmark worker VM through three role-split roles
(`docker`, `gcp-k8s-tools`, `benchmark-client`) and is idempotent — a second
run against the same host reports zero changes.

- rubric_id: LLM-iac-d-ng-ansible-configure-v-deplo
- execution_timestamp: 2026-08-10T00:46:00+00:00
- source_sha: 758722c52ef3035a7e3f9464dc03c5a39e50a74e
- gitops_sha: 921bdc1075ef8335e0f509747bd64db2d525f73e
- versions: ansible-core@2.21, Debian (Container-Optimized OS host), docker-ce (apt), google-cloud-cli, kubectl
- command: `cd ansible && ansible-playbook playbooks/vast-evidence-worker.yml` run twice in a row against `fsds-evidence-worker` over an IAP SSH tunnel
- expected_result: run 1 configures the VM (Docker installed/enabled, GCP apt repo + `google-cloud-cli`/`kubectl` installed, benchmark-client venv + Locustfile deployed) with `changed>0`; run 2 against the same host reports `changed=0`, proving idempotency
- actual_result: run 1 — `ok=17 changed=1 unreachable=0 failed=0 skipped=1`; run 2 — `ok=17 changed=0 unreachable=0 failed=0 skipped=1`
- redaction_status: reviewed — GitOps repository is private; no SSH keys, tokens, or IP addresses appear in this evidence (IAP tunnel is host-name addressed, not IP)

## Command output (real run)

```
$ ansible-playbook playbooks/vast-evidence-worker.yml   # run 1
PLAY [Configure the evidence/benchmark worker VM] ******************************
TASK [Gathering Facts] ********************************************************* ok
TASK [docker : Install Docker prerequisite packages] **************************** ok
TASK [docker : Create apt keyrings directory] *********************************** ok
TASK [docker : Add Docker GPG key] *********************************************** ok
TASK [docker : Add Docker apt repository] **************************************** ok
TASK [docker : Install Docker Engine] ********************************************* ok
TASK [docker : Ensure Docker service is enabled and running] ********************* ok
TASK [docker : Add the connecting user to the docker group] ********************** ok
TASK [gcp-k8s-tools : Download Google Cloud apt GPG key (ASCII-armored)] ********* changed
TASK [gcp-k8s-tools : Dearmor Google Cloud apt GPG key into the keyring] ********* ok
TASK [gcp-k8s-tools : Add Google Cloud SDK apt repository] *********************** ok
TASK [gcp-k8s-tools : Install google-cloud-cli and kubectl] ********************** ok
TASK [gcp-k8s-tools : Check whether the GKE context is already present] ********* ok
TASK [gcp-k8s-tools : Fetch GKE credentials for the evidence cluster] ***** skipping
TASK [benchmark-client : Install pip and venv support] *************************** ok
TASK [benchmark-client : Create the benchmark client virtualenv] ***************** ok
TASK [benchmark-client : Create benchmark client directory] ********************** ok
TASK [benchmark-client : Deploy the Locustfile] *********************************** ok

PLAY RECAP ***********************************************************************
fsds-evidence-worker       : ok=17   changed=1    unreachable=0    failed=0    skipped=1    rescued=0    ignored=0

$ ansible-playbook playbooks/vast-evidence-worker.yml   # run 2, same host, no intervening changes
PLAY RECAP ***********************************************************************
fsds-evidence-worker       : ok=17   changed=0    unreachable=0    failed=0    skipped=1    rescued=0    ignored=0
```

## Sequencing note

Run against the primary node pool only (secondary pool resized to 0 to free
project vCPU quota for the evidence VM — 8 + 4 = 12/12 with both up), per the
capacity budget in `docs/submission/cost.md`. The GKE-credentials task
correctly self-skips (`kubectl config get-contexts` already lists the
context from a prior run), which is itself evidence of idempotent design
rather than a failure.
