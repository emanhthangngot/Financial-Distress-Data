# Phase 1 report — align the contract, the repos and the audit mechanics

Status: complete. All 10 implementation steps done, all 7 success criteria met.

## Step 1-2: baseline gate

- `reports/phase-01-step-01-baseline-gate.txt` — pre-merge baseline, 47
  finding(s), all `source_sha`-axis frozen-revision (expected: this plan's own
  evidence commit is a non-SHA-line change).
- GitOps `feat/phase5-ab-pvc-clones` was already merged to `master` upstream
  (PR #34, `99c0125`); local checkout reset to `origin/master`.
  `git merge-base --is-ancestor 921bdc1... origin/master` → success.
- `reports/phase-01-step-02-postmerge-gate.txt` — post-reset gate, 95
  finding(s), same 47 rubric IDs now tripping both `source_sha` and
  `gitops_sha` axes (gitops HEAD moved past the recorded `921bdc1`, itself
  expected — any gitops commit invalidates `gitops_sha` for all 47 rows until
  phase 6 re-stamps). No new finding class.

## Step 3: PHASE1_BASE_SHA

Recorded in `docs/phase2/evidence-contract.md`:
`PHASE1_BASE_SHA=ddbcbe7bd41ae4883954b8a247efdc67c7329078`. Corrected the
HEAD-equality claim to the actual ancestor rule the auditor enforces
(`scripts/audit_phase2_evidence.py:595-702`).

## Step 4: re-point 8 collided rows

`scripts/_phase2_rubric_items.py` `EXPLICIT_IMPLEMENTATION` re-pointed (old →
new):

| Rubric ID | Old `artifact_path` | New `artifact_path` |
|---|---|---|
| `LLM-routing-gateway-c-c-service-c-n-c-hide-ng-sau-` | `platform/ingress/f5-nginx-values.yaml` | `platform/ingress/routes-ui.yaml` |
| `LLM-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-` | `platform/ingress/f5-nginx-values.yaml` | `platform/ingress/routes-ui.yaml` |
| `LLM-routing-gateway-ui-test-agent` | `platform/ingress/f5-nginx-values.yaml` | `platform/ingress/routes-ui.yaml` |
| `LLM-routing-gateway-ui-cho-agent-registry` | `platform/ingress/f5-nginx-values.yaml` | `platform/ingress/routes-ui.yaml` |
| `LLM-routing-gateway-authentication-cho-ui-test-age` | `platform/ingress/f5-nginx-values.yaml` | `platform/ingress/basic-auth-sealed-secret.yaml` |
| `LLM-routing-gateway-service-coi-log` | `platform/ingress/f5-nginx-values.yaml` | `platform/ingress/routes-viewers.yaml` |
| `LLM-routing-gateway-service-coi-trace` | `platform/ingress/f5-nginx-values.yaml` | `platform/ingress/routes-viewers.yaml` |
| `LLM-observability-t-ng-t-cho-traces` | `platform/observability/loki-otel-values.yaml` | `platform/observability/jaeger.yaml` |

Regenerated `docs/phase2/rubric-matrix.{csv,md}` and
`tests/phase2/requirements/*.py` (22 files rewritten, byte-identical except
the CSV/MD, since the test files parametrize off the matrix at import time).
`git diff` on the CSV touches exactly these 13 rubric IDs — confirmed via
`git diff | grep -E '^[+-]LLM-' | sort -u`; the other 47 executed rows are
untouched. `pytest tests/phase2/test_rubric_matrix.py
tests/phase2/requirements/` → 95 passed, 30 skipped.

The 4 remaining prometheus-values.yaml rows (visualize-metrics,
token-metrics, agent-tool-call-metrics, web-api-metrics) were **not**
re-pointed — the file's `additionalPrometheusRulesMap` groups already carry
distinct, real recording-rule names per row, so they can carry distinct
assertions at their existing path. Only the 8 rows above genuinely collided.

## Step 5+8: the 13 behavioral assertions (verified present today)

All added to `EXECUTED_BEHAVIORAL_ASSERTIONS` in
`scripts/_phase2_rubric_items.py`, each verified present in its target file
**today** by a standalone script mirroring
`tests/phase2/requirements/conftest.py::assert_behavioral_contract` (13/13
`OK`, zero failures). Full CSV `requirement` text copied below verbatim
(includes TTFT and PII-catch frequency on the token-metrics row, per the
canonical CSV the mock grade scores against, not the plan's paraphrase).

| Rubric ID | Pts | Requirement (verbatim from canonical CSV) | `artifact_path` | `behavioral_assertion` |
|---|--:|---|---|---|
| `LLM-routing-gateway-c-c-service-c-n-c-hide-ng-sau-` | 2 | Routing & Gateway (NGINX Ingress Controller) — Các service cần được hide đằng sau gateway | `platform/ingress/routes-ui.yaml` | `text_contains:nginxorguseclusteriptrue` |
| `LLM-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-` | 1 | Làm cái này cho Web API kéo dữ liệu. Mọi người có thể tham khảo 2 đồ án sau: cái này và cái này | `platform/ingress/routes-ui.yaml` | `text_contains:namefeaturemcp` |
| `LLM-routing-gateway-ui-test-agent` | 2 | UI để test agent (xem tại đây) | `platform/ingress/routes-ui.yaml` | `text_contains:gatewayuichat` |
| `LLM-routing-gateway-ui-cho-agent-registry` | 2 | UI cho agent registry | `platform/ingress/routes-ui.yaml` | `text_contains:gatewayuiregistry` |
| `LLM-routing-gateway-authentication-cho-ui-test-age` | 2 | Setup authentication cho UI test agent ở trên | `platform/ingress/basic-auth-sealed-secret.yaml` | `text_contains:nginxorghtpasswd` |
| `LLM-routing-gateway-service-coi-log` | 2 | Service để coi log (ví dụ Kibana) | `platform/ingress/routes-viewers.yaml` | `text_contains:nameloki` |
| `LLM-routing-gateway-service-coi-trace` | 2 | Service để coi trace (ví dụ Jaeger) | `platform/ingress/routes-viewers.yaml` | `text_contains:namejaeger` |
| `LLM-observability-collect-v-visualize-metrics-v-` | 1 | Collect và visualize metrics với Prometheus + Grafana (hoặc tool tương tự) | `platform/observability/prometheus-values.yaml` | `yaml_path:grafana.enabled` |
| `LLM-observability-m-b-o-t-nh-t-c-c-metrics` | 2 | Đảm bảo ít nhất các metrics; + token metrics (count of input tokens, output tokens and total tokens per req); + total round-trip time for a generation; + TTFT; + Frequencies of prompts caught by safety of PII | `platform/observability/prometheus-values.yaml` | `text_contains:llmsafetypiipromptcatchestotal` |
| `LLM-observability-agent-tool-call-metrics` | 2 | Đảm bảo ít nhất các metrics; + total num of times each agent is called; + total num of times each MCP tool is called; + total failures cho mỗi lượt call tool | `platform/observability/prometheus-values.yaml` | `text_contains:mcptoolcallstotalrate5m` |
| `LLM-observability-web-api-metrics` | 1 | Observability — Web API metrics | `platform/observability/prometheus-values.yaml` | `text_contains:webapirequestdurationsecondsp95` |
| `LLM-observability-t-ng-t-cho-logs` | 1 | Tương tự cho logs | `platform/observability/loki-otel-values.yaml` | `yaml_path:loki.limits_config` |
| `LLM-observability-t-ng-t-cho-traces` | 1 | Tương tự cho traces | `platform/observability/jaeger.yaml` | `text_contains:jaegerstorageexporter` |

Total: 21 points across 13 rows, matches plan.

## Step 6-7: denylist + redaction convention

- `EVIDENCE_SECRET_DENYLIST` extended with 3 patterns: curl basic-auth flag
  (`-u`/`--user`), userinfo credential in an `http(s)://` URL (scoped to
  http(s) only — an unscoped version broke 2 already-passing evidence rows
  that legitimately embed a local dev Postgres DSN
  (`postgresql://phase2:phase2@localhost:5433`); narrowed and re-verified),
  and bcrypt htpasswd hashes.
- Re-ran the strict gate after the denylist change: same 95 findings as
  step 2, zero new. Confirmed no regression.
- `reports/phase-01-redaction-template.md` — synthetic redacted capture
  (hide-services negative + basic-auth positive + sealed-secret ciphertext
  block), scanned with the auditor's own `_audit_evidence_secrets` function:
  **PASS, zero denylist hits**. Kept as phase 5's capture template. Note: the
  substitution table itself had to be written *about* the trigger shapes
  without *reproducing* them (e.g. "curl's basic-auth flag" rather than
  literal `curl -u`), since the denylist doesn't distinguish documentation
  from a leak — this is itself the phase-5 authoring discipline.

## Step 9: docs/submission/README.md corrected

- Status line now states 47/60 executed (79/100 pts), matches the audit.
- The "grant private repo read access" paragraph replaced with the accepted
  scrubbed-mirror decision (2026-08-11 red-team adjudication, finding 3): the
  GitOps repo stays private (committed `terraform.tfstate` +
  `ansible/inventory.ini`, both denylist-flagged), a scrubbed public mirror of
  `platform/`, `apps/`, `charts/`, `argocd/` ships instead. Mirror URL is a
  phase-6 deliverable, referenced but not yet published.

## Step 10: final baseline re-run

Re-ran the strict gate one more time after all edits — see
`reports/phase-01-step-02-postmerge-gate.txt`-equivalent output: same 95
frozen-revision findings, nothing new. Cluster still at zero nodes (no `make
gcp-*` command run this phase).

## Success criteria

- [x] `git merge-base --is-ancestor 921bdc1... origin/master` succeeds;
      `git branch --show-current` → `master` (gitops checkout).
- [x] `evidence-contract.md` has a 40-hex `PHASE1_BASE_SHA`, ancestor rule
      stated correctly.
- [x] This report has 13 assertion strings, each verified present today.
- [x] Synthetic redacted capture: zero denylist hits.
- [x] 47 executed rows still pass after every change (95-finding set
      unchanged across the whole phase, all frozen-revision, none new).
- [x] `docs/submission/README.md` matches the repository.
- [x] `make gcp-status` not run — no infra command issued this phase; cluster
      was never touched (design-time-only phase, as required).
