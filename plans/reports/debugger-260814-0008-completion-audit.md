# Production Hardening Completion Audit

## Executive Summary

- **Issue:** Xác định toàn bộ production-hardening overlay đã hoàn thành và đạt 100% chưa.
- **Impact:** Không được đóng plan hoặc claim production/live 100% khi các gate executed/live còn thiếu.
- **Root cause:** Matrix ML hiện đủ 100 điểm nhưng cả 57/57 dòng vẫn `design_only`; các acceptance criteria live chưa được chứng minh.
- **Status:** **Chưa hoàn thành 100%.** LLM track và các gate local đã xanh; ML executed/live và evidence freeze còn pending.
- **Fix trong audit:** Sửa lỗi import-order trong regression test CDC; không tạo evidence giả, không mutate cluster.

## Evidence

| Gate / kiểm tra | Kết quả mới nhất |
|---|---|
| `uv run --offline python -m pytest tests -q` | **311 passed** |
| Ruff | **PASS** |
| Black | **326 files unchanged** |
| `docker compose config` | **PASS** |
| Phase 2 matrix strict | **PASS**, 117 rows; LLM 60 rows/100 points, ML 57 rows/100 points |
| LLM `--require-executed` | **PASS**, 60/60 rows executed |
| ML `--require-executed` | **FAIL**, 57/57 rows `design_only` |
| `--check-artifacts` | **PASS**, missing artifact count 0 (design-only rows vẫn không phải executed evidence) |
| Source Phase 2 quality gate | **PASS**, 72 passed / 1 skipped |
| GitOps default validation | **PASS**, kubeconform unavailable nên skipped |
| GitOps strict real-digest mode | **FAIL**, 7 zero-placeholder digests |
| Ansible syntax | **PASS** (deprecation warnings only) |
| Rollout evidence capture | **Fail-closed**, `kubectl-argo-rollouts` missing |

## Phase Status

`plans/260813-1846-production-hardening-overlay/plan.md` vẫn `status: in_progress`.
Cả 12 phase files vẫn `status: in_progress`; acceptance checklist có **0 checked / 84 unchecked**.

### Confirmed complete locally

- Guardrails and protected-path audit.
- Source/GitOps lint, unit tests, matrix validation.
- Additive lakehouse, CDC, ML/API contracts and focused tests.
- GitOps Helm/Terraform/secret/diff checks.
- Read-only cluster observation: 1 node `Ready`; existing Argo applications report `Synced/Healthy`.

### Not complete / not proven live

1. **Phase 3:** CI has signing shape, but no verified real image digest + SBOM + SLSA attestation from registry.
2. **Phase 4:** quota is `CPUS 32`, usage 8; `E2_CPUS` remains 8. No approved 24-vCPU capacity soak or billing ledger.
3. **Phase 5:** Kyverno manifests exist, but unsigned/tagged rejection evidence is not captured; several policies remain `Audit`.
4. **Phase 6:** ESO rotation, SecretSynced, Linkerd mTLS and denial evidence absent.
5. **Phase 7:** Lakekeeper live REST registration, concurrent commit, time travel and schema evolution absent.
6. **Phase 8:** Flink CDC live inserts/updates/deletes and Bronze reconciliation absent.
7. **Phase 9:** Phase 1 cluster parity/admission/run evidence absent.
8. **Phase 10:** MLflow/Kubeflow distributed run and live drift/retrain evidence absent; ML executed gate fails all 57 rows.
9. **Phase 11:** Argo canary/rollback, KEDA load soak, gateway security and dashboards not demonstrated.
10. **Phase 12:** checklist has only 3 generic sections and 0 screenshot declarations; no final concurrent soak/evidence freeze.

## Root-Cause Findings

- “100/100” currently means **rubric matrix totals**, not completion of all implementation/live acceptance criteria.
- GitOps local validator intentionally grandfathered zero digests; CI strict mode correctly exposes 7 unresolved image digests.
- Rollout capture cannot succeed in this environment because `kubectl-argo-rollouts` is not installed.
- The audit initially reproduced a Ruff import-order failure in `tests/phase2/pipelines/test_cdc_reconciliation.py`; import ordering was corrected and the full suite was rerun successfully.

## Recommendations

### P0

- [ ] Build/push/sign all seven images, replace zero digests, then rerun strict GitOps validation.
- [ ] Install `kubectl-argo-rollouts`, `kubeconform`, `cosign`, and `syft` in the verification environment.
- [ ] Run ML live acceptance rows and convert only evidence backed by real execution from `design_only` to `executed`.

### P1

- [ ] Execute Kyverno, ESO/Linkerd, Lakekeeper, Flink CDC and Argo rollback scenarios; capture logs/screenshots with source/GitOps SHAs.
- [ ] Expand `configs/evidence-checklist.yaml` to the full phase-12 capture contract.

## Unresolved Questions

- Có được phép request quota/billing changes và chạy concurrent soak trên GKE không?
- Registry nào sẽ là source-of-truth để thay 7 digest placeholder?
- Submission chỉ cần giữ LLM 100/100 hay bắt buộc đóng cả ML 100/100 executed?
