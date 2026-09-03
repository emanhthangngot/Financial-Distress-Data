# Tham khảo yas-cd + RecSys-MLops — Báo cáo & Plan cải thiện

Ngày: 2026-08-13 · Mode: `--compare` (phân tích, chưa implement) · Trọng tâm: **evidence setup** + **kiến trúc hiện tại**

## 1. Source manifest

| Repo | Vai trò | Commit | Ngày |
|---|---|---|---|
| `emanhthangngot/yas-cd` | tham khảo GitOps/CD (microservice — học có lọc) | `4b82ab0f35fb11ec1dfffa72af8a27bc65eece1c` | 2026-07-18 |
| `itsmekhoathekid/RecSys-MLops` | tham khảo ML track (repo chính) | `e99df9d14ed8da75285990eee17028dc3b06ccc1` | 2026-08-04 |
| `Financial-Distress-Data` (local) | source monorepo | `620975d1e070703f7744e759f57f26ef27443a98` | — |
| `financial-distress-gitops` (local, `~/Studying/FSDS/`) | GitOps control repo | `32483a1bb9775c95047836864e6b2dbef6adb9bf` | — |

Repo tham khảo được đọc như **dữ liệu**, không thực thi lệnh/cài package nào từ đó.

---

## 2. Đo hiện trạng trước khi so sánh

Từ `docs/platform/rubric-matrix.csv` (117 rows):

| Track | Rows | Points | evidence_type |
|---|---:|---:|---|
| LLM | 60 | 100 | **100% executed** |
| ML | 57 | 100 | **100% design_only** |

Chia theo repo sở hữu artifact:

| artifact_repo | design_only | executed |
|---|---:|---:|
| `source` | 38 rows / 66 pts | 31 rows / 54 pts |
| `gitops` | 19 rows / 34 pts | 29 rows / 46 pts |

**Phát hiện đo được, chưa có gate nào bắt:** 20 `artifact_path` khai trong matrix **không tồn tại trên đĩa**, tổng **50 điểm** (12 pts ở gitops, 38 pts ở source). Trong đó có drift tên đường dẫn thật:

- matrix khai `platform/ml/ab-testing.yaml`, repo gitops thực tế có `platform/llm/ab-testing.yaml`
- `charts/feature-api/`, `charts/drift-api/` chưa tồn tại (gitops chỉ có `feature-mcp`, `drift-mcp`, `fastapi-service`, `web`)
- `platform/observability/eck-otel-values.yaml`, `platform/security/vault-external-secrets.yaml`, `platform/security/authorization-policies.yaml` chưa có
- source: `apps/feature-api/`, `apps/drift-api/`, `src/ml/mlflow_registry.py`, `src/ml/leakage_guard.py`, `notebooks/ml-training.ipynb`, `tests/platform/requirements/test_ml_ac_04_validation.py` …

`audit_phase2_evidence.py --require-executed` chỉ bắt cái này ở **phase-08**. Đa số là ML rows nên hôm nay chưa nổ — nhưng nghĩa là ML retrofit đang mù về "còn thiếu file gì".

**Repo gitops hiện trạng:** 117 file, `README.md` + `Makefile` (cost lever `gcp-up/down/status`) + `terraform/` + `charts/` (4) + `platform/` (9 nhóm) + `argocd/` + `ansible/`. **Không có** `.github/`, **không có** script validate, **không có** `AGENTS.md`. → 34-46 điểm rubric nằm trong một repo mà không có một cái gate nào.

---

## 3. Học từ `yas-cd` (GitOps)

### 3.1 ĐÁNG LẤY

**(A) GitOps repo phải có CI của chính nó.** `scripts/validate-gitops.sh` + `.github/workflows/validate-gitops.yml` chạy trên mọi PR/push `main`:
- render **mọi** overlay bằng `kustomize build --enable-helm` (fail nếu chart/values hỏng)
- diff danh sách image trong overlay **với catalog** — lệch là fail
- policy check: đúng 1 replica-state patch mỗi overlay; tập environment active phải khớp `expected_active_environments`
- `validate-staging-immutable.sh`: cấm tag mutable `latest` ở staging
- grep chặn pattern giống secret / kubeconfig / private key trên toàn repo
- `git diff --check` (whitespace)

Đây là thứ repo gitops của chúng ta thiếu **hoàn toàn**, và là gap lớn nhất tìm được.

**(B) `services.yaml` — desired state là data, không phải hardcode.** Một file catalog khai từng service: `imageName`, `chart`, `type`, `deploy`, `dependencies`, `demoRole`. Validator so catalog ↔ overlay. AGENTS.md của họ ghi thẳng: *"Do not hardcode service lists when `services.yaml` can be used."*

**(C) `AGENTS.md` trong chính repo gitops** với "Hard Rules" cụ thể theo runtime:
- không bao giờ `kubectl set image` / `kubectl apply` trực tiếp vào namespace do Argo CD quản
- CI ở app repo **chỉ** commit vào CD repo; Argo CD độc quyền sync cluster
- không dùng `latest` ở staging
- checklist bắt buộc trước commit: render overlay đã đổi, chạy validate immutable, xác nhận không có secret trong staged diff

**(D) Evidence kể chuyện thất bại → sửa.** `evidence/35_cd_demo_summary.md` không phải bảng "PASS/PASS/PASS": nó dựng chuỗi 4 lần release `v0.1.0 → v0.1.1 (x2) → v0.1.2`, mỗi lần fail trỏ đúng 1 file log (`21_…txt`, `21b_…`, `21c_…`, `21d_…`), rồi 2 PR sửa gốc. Kèm một mục "Known issue" tự khai lỗi runtime không thuộc luồng CD. Evidence đánh số tuần tự `00_ → 35_` theo trình tự demo.

Ta đã có manifest chặt hơn (SHA + redaction), nhưng **thiếu lớp narrative** dạng này — thứ chấm/ bảo vệ đọc được trong 2 phút.

**(E) Active/dormant qua replica patch (ý tưởng, không phải code).** Họ hibernate bằng patch replicas per-environment với `active_limit=2`, giữ PVC. Ta hibernate bằng `gcloud container clusters resize --num-nodes 0` — all-or-nothing. Với quota `E2_CPUS=8` đã bão hoà (ghi trong `Makefile` gitops), hibernate **từng platform component** thay vì cả node pool là đòn bẩy thật để chạy ML evidence mà không đụng quota.

### 3.2 KHÔNG LẤY (đặc thù microservice)

| Thứ | Lý do bỏ |
|---|---|
| 20+ Helm chart per-service, `base/` + 4 overlay | Ta có 4 chart + 1 chart chung `fastapi-service`. Overlay-per-env không cần khi chỉ có `apps/dev/`. |
| Validate gateway route Spring Cloud Gateway | Không có Spring, không có BFF. |
| `platform/base/` Keycloak, Debezium, Elasticsearch, Zookeeper | Platform ta là KServe/agentgateway/pgvector/Redis — khác hẳn. |
| Jenkins (`Jenkinsfile.*`) | Ta dùng GitHub Actions + Argo CD. |
| `overlays/mesh-demo/` Istio retry-proof | Ngoài scope rubric hiện tại. |
| Spec Kit (`.specify/`) | Ta đã có `plans/` + `AGENTS.md` làm việc tương đương. |

---

## 4. Học từ `RecSys-MLops` (ML track)

Repo này cùng khung coursework với ta (có cả `docs/submission/rubic-(mini-coursework)/` lẫn `rubic-final-coursework-(final-ml)/`), nên so sánh 1-1 được.

### 4.1 ĐÁNG LẤY

**(A) CI logic là Python module có unit test, không phải YAML/Groovy.** `jenkins/python/` chứa `image_catalog.py`, `promotion_gates.py`, `migration_policy.py`, `container_scan_policy.py`, `change_detection/detector.py`, `release_plan.py` — và `tests/unit/jenkins/` test chúng. Groovy chỉ là vỏ gọi.

Ta ngược lại: toàn bộ quyết định CI nằm trong `.github/workflows/*.yaml` (8 file caller nhúng JSON deployable inline) — **không test được**, chỉ biết sai khi CI đỏ trên `main`.

**(B) Catalog + config-driven CI.** `images/catalog.json` khai đồ thị phụ thuộc image (`recsys-base-python → recsys-spark → …` qua `buildArg`), `jenkins/config/components.json` + `deploy-units.json`. `make validate` validate **chính catalog** trước khi build. Cùng bài học với `services.yaml` của yas-cd — hai repo độc lập hội tụ về một pattern → tín hiệu mạnh.

**(C) `make full-cicd-preflight` — một lệnh preflight cho toàn stack hạ tầng:**
```
validate (catalog + CI config)
+ helm lint & helm template MỌI chart trong infra/helm/*
+ terraform fmt -check -recursive && terraform validate
+ bash -n MỌI file .sh
+ pytest tests/unit/jenkins tests/contract
```
Ta có `scripts/run_stage1_quality_gates.py` (pytest + ruff + black + `docker compose config`) — nhưng **không** phủ helm/terraform/shell, và không phủ repo gitops chút nào.

**(D) `docs/submission/README.md` — semantics của reference.** Quy ước 3 dòng, rất đáng chép:
> - link tương đối = source/config **hiện tại**
> - URL GitHub pin theo full commit SHA = proof **lịch sử** đã bị xoá/thay, không phải path chạy được
> - screenshot/run-ID/metric/timestamp = mô tả **một lần chạy đã capture**; phải chạy lại lệnh hiện hành trước khi coi đó là phát biểu về cluster live

Cộng bảng "Current Production Sources" map mỗi mối quan tâm → 1 file authoritative. Đây là thuốc chữa đúng bệnh "50 điểm artifact_path không tồn tại" ở §2.

**(E) Bundle validation & verification.** `validation-verification/` gồm: bảng coverage per-component (11 dòng, 90-99%), `mutation-summary.md` (score 86.67% / gate >80%, killed/survived/timeout, liệt kê target file + mutant filter), `locust-api.html` **kèm** `locust-sla-summary.md` (machine-readable: p95, throughput, failure rate, SLA, PASS), và **screenshot checklist** liệt kê chính xác ảnh nào chứng minh gì.

Ta có `scripts/run_phase5_mutation_gate.py` + `mutants/` + `tests/load/`, nhưng chưa gói thành bundle có bảng coverage per-component và SLA summary song song file raw.

**(F) Split chart theo domain thay vì một Helm release khổng lồ.** Họ ghi rõ trong submission README: data platform từ 1 release tách thành `recsys-data-config` / `-lakehouse` / `-source-store` / `-event-stream` / `-feature-store` / `-kafka-connect` / `-streaming` / `-airflow`. Ta đang đi đúng hướng đó (`platform/` chia 9 nhóm) — xác nhận kiến trúc hiện tại ổn, không cần đổi.

### 4.2 KHÔNG LẤY

| Thứ | Lý do bỏ |
|---|---|
| Jenkins toàn bộ (controller EC2, agent GCP) | Ta GitHub Actions + Argo CD; thêm Jenkins = thêm bề mặt không tính điểm. |
| Kubeflow Pipelines + KubeRay/Ray Tune | Quota `E2_CPUS=8`. ML rows của ta không đòi distributed HPO ở mức đó. |
| 15-image catalog, multi-node-pool autoscale, KEDA HTTP scaler đầy đủ | Vượt xa 4 deployable của ta. |
| Istio mTLS + Vault + External Secrets đầy đủ | Ta đã có Sealed Secrets + NetworkPolicy default-deny — đủ cho rows security đang khai. |
| Triton/ONNX packaging, BST model | Domain khác (recsys sequence model ≠ financial distress). |
| Superset/dbt/Trino/DataHub full | platform .a đã có DataHub + DuckDB; không mở rộng. |

---

## 5. Decision matrix

| Quyết định | Cách yas-cd | Cách RecSys | Cách ta hiện tại | Khuyến nghị |
|---|---|---|---|---|
| Gate cho GitOps repo | `validate-gitops.sh` + GH Actions | `make helm-validate` + `terraform-validate` | **không có** | **Lấy cả hai**, gộp thành 1 script + 1 workflow trong repo gitops |
| Nguồn sự thật deployable | `services.yaml` | `images/catalog.json` | JSON inline trong 8 workflow | Tách ra `deployables.yaml` ở source repo, workflow đọc từ đó |
| Logic CI | Groovy + bash | **Python có unit test** | YAML thuần | Theo RecSys: đẩy quyết định (path mapping, digest bump) vào Python có test |
| Artifact path drift | validator diff catalog↔overlay | bảng "Current Production Sources" | chỉ bắt ở phase-08 | Thêm check `artifact_path` tồn tại vào **mọi** lần chạy audit, không đợi phase-08 |
| Evidence integrity | SHA commit + numbering | pinned-SHA URL + semantics | **SHA nguồn+gitops, ancestry, redaction, clean worktree** | **Giữ nguyên của ta** — chặt hơn cả hai |
| Evidence narrative | `35_cd_demo_summary.md` fail→fix | `validation-verification/README.md` + checklist | manifest per-row, không có narrative | Bổ sung 1 file narrative/track |
| Cost lever | replica patch active/dormant, giữ PVC | `make gcp-services-down` | node pool → 0 (all-or-nothing) | Thêm mức hibernate per-component cho ML window |
| Immutable image | `validate-staging-immutable.sh` | digest immutable trong release script | contract yêu cầu, không ai enforce | Thêm check digest-pinned vào gate gitops |
| Secret | grep pattern trong validate + Gitleaks CI | External Secrets + Vault | Sealed Secrets, không có grep gate | Thêm grep gate rẻ tiền vào script validate gitops |

---

## 6. Plan cải thiện đề xuất

Xếp theo tỉ lệ (điểm được bảo vệ + rủi ro chặn) / công sức. Tất cả **additive** — không đụng Phase 1, không đụng LLM rows đã executed.

### P0 — Chặn rủi ro đang mở (≈1 ngày)

**P0.1 · `scripts/validate-gitops.sh` + workflow trong repo `financial-distress-gitops`**
Nội dung gate (lấy khung yas-cd, cắt phần microservice):
- `helm lint` + `helm template` mọi chart trong `charts/`
- render mọi `apps/dev/*/values.yaml` với chart tương ứng
- `kubectl --dry-run=client` (hoặc `kubeconform`) mọi manifest trong `platform/**`, `argocd/**`
- `terraform fmt -check -recursive` + `terraform validate` (skip có thông báo nếu chưa `init`)
- mọi image reference phải pin **digest** `@sha256:`, cấm `:latest`
- grep chặn pattern secret / `BEGIN PRIVATE` / kubeconfig
- `git diff --check`

AC: `financial-distress-gitops` CI -> chạy trên PR/push `main` -> đỏ khi chart hỏng, manifest sai schema, image không pin digest, hoặc lộ secret.

**P0.2 · `AGENTS.md` cho repo gitops**
Hard rules: Argo CD độc quyền sync (`kubectl apply` trực tiếp vào namespace managed = cấm); source repo chỉ commit digest bump; digest immutable; checklist trước commit (render chart đã đổi, chạy validate, quét staged diff). Kèm bảng ownership `source` ↔ `gitops` khớp `artifact_repo` trong rubric matrix.

AC: agent/người mở repo gitops -> đọc `AGENTS.md` -> biết ranh giới repo mà không cần mở monorepo.

**P0.3 · Kéo check tồn tại `artifact_path` ra khỏi phase-08**
Thêm flag (vd `--check-artifacts`) cho `scripts/audit_phase2_evidence.py`: với **mọi** row bất kể `evidence_type`, verify `artifact_path` tồn tại trong đúng repo; `design_only` báo WARN + liệt kê, `executed` báo FAIL. Sửa luôn `platform/ml/ab-testing.yaml` → `platform/llm/ab-testing.yaml`.

AC: chạy auditor -> in đúng 20 path còn thiếu / 50 điểm -> ML retrofit có backlog file cụ thể thay vì mò.

### P1 — Bọc lại evidence (≈1 ngày)

**P1.1 · `docs/platform/evidence/README.md` — semantics của reference** (theo RecSys §4.1-D)
3 quy ước link + bảng "Current Authoritative Sources" (concern → file). Bổ sung, không thay `evidence-contract.md`.

**P1.2 · Narrative summary mỗi track** — `docs/platform/evidence/{llm,ml}/00-run-summary.md`
Theo khuôn `35_cd_demo_summary.md`: kể chuỗi fail → nguyên nhân gốc → fix, mỗi bước trỏ đúng file evidence đã có; mục "Known issues" tự khai. Không sinh evidence mới, chỉ index cái đã có.

**P1.3 · Bundle validation & verification** — `docs/platform/evidence/validation-verification/`
Bảng coverage per-component; `mutation-summary.md` (score/gate/killed/survived/target — `run_phase5_mutation_gate.py` đã có số, chỉ cần render); load test raw + `sla-summary.md` (p95/throughput/failure-rate/SLA/verdict); screenshot checklist.

### P2 — Kiến trúc CI (≈1-1.5 ngày, mở đường cho ML retrofit)

**P2.1 · `configs/phase2-deployables.yaml` làm catalog**
Gom 8 spec deployable đang inline trong workflow thành 1 file: `name`, `dockerfile`, `test_selector`, `lint_paths`, `gitops_chart`, `gitops_values_path`. Workflow đọc từ file.

**P2.2 · Logic CI thành Python có test** (`scripts/phase2_ci/`)
Module thuần: parse catalog, resolve gitops path, dựng digest-bump patch. Test ở `tests/platform/` — bao gồm test khẳng định **mọi `gitops_values_path` trong catalog tồn tại trong repo gitops**. Đây là chỗ bắt drift `platform/ml/` vs `platform/llm/` ngay tại unit test.

**P2.3 · Mở rộng one-shot gate**
`scripts/run_stage1_quality_gates.py` giữ nguyên (Phase 1). Thêm target platform .ong song: `bash -n` mọi shell script + gọi validate của repo gitops khi có `--gitops-root`.

### P3 — Cost/quota, mở khoá ML window (≈0.5 ngày)

**P3.1 · Hibernate per-component**
Trong repo gitops, thêm `platform/**/replicas-dormant` patch + `make platform-down COMPONENT=…` để ngủ từng nhóm (observability, agents, inference) giữ PVC, thay vì chỉ resize node pool. Cho phép chạy ML evidence trong trần `E2_CPUS=8`.

**P3.2** Không lấy Kubeflow/Ray. ML rows chạy trên KServe + Airflow đã có.

### Thứ tự thực thi
`P0.1 → P0.2 → P0.3` (chặn rủi ro, cho ra backlog ML) → `P1.*` (làm dày evidence hiện có, không cần cluster) → `P2.*` (nền cho retrofit) → `P3.*` (ngay trước khi bật ML window).

Ước lượng: ~4 ngày, chạy được song song với ML retrofit 4-5 ngày trong `phase-05`.

---

## 7. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Sửa `artifact_path` trong matrix chạm cột `source_digest` được pin theo CSV gốc | `artifact_path` là cột do ta sở hữu, không thuộc digest nguồn — verify bằng `--matrix-only --strict` sau khi sửa |
| Thêm CI vào repo gitops làm đỏ ngay do manifest hiện tại chưa pin digest | Chạy script local trước, sửa hết, mới bật workflow |
| Catalog hoá deployable đụng 8 workflow đang xanh | Đổi từng workflow một, giữ nguyên schema JSON mà job reusable nhận |
| P2 lấn thời gian ML retrofit | P2 tuỳ chọn; P0+P1 đã đứng độc lập |

## 8. Câu hỏi mở

1. ML retrofit có chạy trước hay sau khi làm P0-P1 không? P0.3 sinh ra chính backlog file của ML — nên làm trước, nhưng nếu deadline ML gấp thì đảo được.
2. Repo `financial-distress-gitops` có bật GitHub Actions không (private repo, quota minute)? Nếu không, P0.1 vẫn giá trị dưới dạng script chạy local + pre-push hook.
3. 50 điểm artifact còn thiếu — có row nào định bỏ hẳn (stretch) thay vì implement không? Hiện `evidence-contract.md` cấm scored row ở trạng thái `stretch` khi nộp.
