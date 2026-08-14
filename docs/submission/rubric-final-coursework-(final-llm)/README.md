---
title: "LLM Track Submission Index"
date: 2026-08-14
status: active
scope: "docs/submission/rubric-final-coursework-(final-llm)/**"
---

# LLM Track — Reviewer Index

60 rubric rows, 100 points, mapped exclusively (no row claimed twice, no row
unclaimed) across 21 narrative docs. Source of truth for the mapping is
`docs/phase2/rubric-matrix.csv` (`track=LLM`). Each doc follows the skeleton in
`docs/docs-style-contract.md`. `docs/phase2/evidence/llm/*.md` stays the
canonical, audit-pinned evidence — these docs tell the story and link down into
it, they never move or duplicate it.

## Area index

| Area | Doc | Rows | Points |
|---|---|---|---|
| Deploy a LLM inference platform theo hướng dẫn này và set up gateway cho agent theo hướng dẫn này | [`llm_inference_platform.md`](./llm_inference_platform.md) | 3 | 6 |
| Deploy 1 global model config để các Agent có thể dùng follow tutorial này, config này sẽ link tới inference platform ở trên thông qua cái agent gateway đề cập ở trên nốt | [`global_model_config.md`](./global_model_config.md) | 1 | 2 |
| Deploy registry for agent theo tutorial này | [`agent_registry.md`](./agent_registry.md) | 1 | 2 |
| RAG | [`rag.md`](./rag.md) | 2 | 4 |
| Web API kéo dữ liệu user | [`web_api_user_data.md`](./web_api_user_data.md) | 6 | 9 |
| Web API cho Real-time Drift Detection | [`web_api_drift_detection.md`](./web_api_drift_detection.md) | 6 | 9 |
| Demonstrate basic understanding of Agents | [`agent_understanding.md`](./agent_understanding.md) | 2 | 4 |
| Deploy 1 Coordinator Agent | [`coordinator_agent.md`](./coordinator_agent.md) | 2 | 4 |
| Cài đặt hệ thống ở chế độ Warm Up cho agent theo hướng dẫn sau để tối ưu chi phí, đồng thời giảm thiểu thời gian startup | [`agent_warm_up.md`](./agent_warm_up.md) | 1 | 2 |
| Validation & Verification | [`validation_verification.md`](./validation_verification.md) | 5 | 9 |
| Improve the Data Generator | [`improve_data_generator.md`](./improve_data_generator.md) | 3 | 4 |
| CI/CD | [`ci_cd.md`](./ci_cd.md) | 6 | 12 |
| Routing & Gateway | [`routing_gateway.md`](./routing_gateway.md) | 7 | 13 |
| IaC | [`iac.md`](./iac.md) | 2 | 2 |
| Observability | [`observability.md`](./observability.md) | 6 | 8 |
| A/B Testing | [`ab_testing.md`](./ab_testing.md) | 2 | 2 |
| Security | [`security.md`](./security.md) | 1 | 1 |
| Repository Design | [`repository_design.md`](./repository_design.md) | 1 | 2 |
| Documentation | [`low_level_design.md`](./low_level_design.md) | 1 | 1 |
| Novel ideas | [`novel_ideas.md`](./novel_ideas.md) | 2 | 4 |
| Cost deliverable | [`cost.md`](./cost.md) | — (not a 60-row LLM matrix item) | — |

**Totals: 60 rows, 100 points.** Matches the accepted 60-row /
100-point LLM track scope exactly.

## Row-level mapping

| Doc | Rubric IDs claimed |
|---|---|
| `llm_inference_platform.md` | `LLM-a-llm-inference-platform--a-custom-model`, `LLM-a-llm-inference-platform--benchmark-model-server-and-opt`, `LLM-a-llm-inference-platform--llm-inference-platform-setup-c` |
| `global_model_config.md` | `LLM-1-global-model-config-c-c-1-global-model-config-c-c-agen` |
| `agent_registry.md` | `LLM-registry-for-agent-theo-t-registry-for-agent-theo-tutori` |
| `rag.md` | `LLM-rag-m-b-o-data-governance-cho-pipe`, `LLM-rag-rag-data-pipeline` |
| `web_api_user_data.md` | `LLM-web-api-k-o-d-li-u-user-1-agent-s-d-ng-mcp-tool-tr-n-v`, `LLM-web-api-k-o-d-li-u-user-agent-ch-y-trong-sandbox-m-b-o`, `LLM-web-api-k-o-d-li-u-user-c-s-d-ng-fastapi-data-validati`, `LLM-web-api-k-o-d-li-u-user-in-the-form-of-mcp-tool-to-k8s`, `LLM-web-api-k-o-d-li-u-user-publish-agent-tr-n-l-n-registr`, `LLM-web-api-k-o-d-li-u-user-s-d-ng-async` |
| `web_api_drift_detection.md` | `LLM-web-api-cho-real-time-dri-1-agent-s-d-ng-mcp-tool-tr-n-v`, `LLM-web-api-cho-real-time-dri-agent-ch-y-trong-sandbox-m-b-o`, `LLM-web-api-cho-real-time-dri-c-s-d-ng-fastapi-data-validati`, `LLM-web-api-cho-real-time-dri-in-the-form-of-mcp-tool-to-k8s`, `LLM-web-api-cho-real-time-dri-publish-agent-tr-n-l-n-registr`, `LLM-web-api-cho-real-time-dri-s-d-ng-async` |
| `agent_understanding.md` | `LLM-demonstrate-basic-underst-jupyter-notebook-demonstrate-a`, `LLM-demonstrate-basic-underst-jupyter-notebooks-to-demonstra` |
| `coordinator_agent.md` | `LLM-1-coordinator-agent-i-u-ph-i-2-agent-tr-n`, `LLM-1-coordinator-agent-publish-agent-n-y-l-n-registry` |
| `agent_warm_up.md` | `LLM-c-i-t-h-th-ng-ch-warm-up--c-i-t-h-th-ng-ch-warm-up-cho-a` |
| `validation_verification.md` | `LLM-validation-verification-c-s-d-ng-k-thu-t-equivalence-p`, `LLM-validation-verification-c-s-d-ng-mutation-testing-nh-g`, `LLM-validation-verification-idempotency-testing-s-d-ng-pro`, `LLM-validation-verification-load-test-the-web-api`, `LLM-validation-verification-validation-verification` |
| `improve_data_generator.md` | `LLM-improve-the-data-generato-simulate-data-drift`, `LLM-improve-the-data-generato-t-o-b-ng-label-c-2-c-t-id-v-la`, `LLM-improve-the-data-generato-using-generator-configuration` |
| `ci_cd.md` | `LLM-ci-cd-agent-drift-detection`, `LLM-ci-cd-agent-k-o-d-li-u`, `LLM-ci-cd-agent-l-m-coordinator`, `LLM-ci-cd-ci-cd-cho-rag-data-pipeline`, `LLM-ci-cd-job-1`, `LLM-ci-cd-job-2` |
| `routing_gateway.md` | `LLM-routing-gateway-authentication-cho-ui-test-age`, `LLM-routing-gateway-c-c-service-c-n-c-hide-ng-sau-`, `LLM-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-`, `LLM-routing-gateway-service-coi-log`, `LLM-routing-gateway-service-coi-trace`, `LLM-routing-gateway-ui-cho-agent-registry`, `LLM-routing-gateway-ui-test-agent` |
| `iac.md` | `LLM-iac-d-ng-ansible-configure-v-deplo`, `LLM-iac-d-ng-terraform-setup-gke-ho-c-` |
| `observability.md` | `LLM-observability-agent-tool-call-metrics`, `LLM-observability-collect-v-visualize-metrics-v-`, `LLM-observability-m-b-o-t-nh-t-c-c-metrics`, `LLM-observability-t-ng-t-cho-logs`, `LLM-observability-t-ng-t-cho-traces`, `LLM-observability-web-api-metrics` |
| `ab_testing.md` | `LLM-a-b-testing-perform-a-b-test-for-different`, `LLM-a-b-testing-when-you-deploy-a-new-model` |
| `security.md` | `LLM-security-centralize-secret-management` |
| `repository_design.md` | `LLM-repository-design-clean-code-clean-repo-demonstr` |
| `low_level_design.md` | `LLM-documentation-low-level-ml-design` |
| `novel_ideas.md` | `LLM-novel-ideas-idea-1`, `LLM-novel-ideas-idea-2` |

## Reading order

Dependency order, so shared context (platform, model routing, agent identity)
accumulates before the docs that assume it:

1. `llm_inference_platform.md` — platform + custom model + benchmark
2. `global_model_config.md` — shared model config, secret ref, agent use
3. `agent_registry.md` — registry deploy + UI
4. `rag.md` — RAG pipeline + data governance for it
5. `web_api_user_data.md` — feature-pull Web API (MCP tool + agent)
6. `web_api_drift_detection.md` — real-time drift Web API (MCP tool + agent)
7. `agent_understanding.md` — the two demonstration notebooks
8. `coordinator_agent.md` — coordinator orchestrating 2+ agents
9. `agent_warm_up.md` — warm-up mode + measurement
10. `ci_cd.md` — the six CI/CD jobs
11. `routing_gateway.md` — NGINX ingress, hidden services, auth, UIs
12. `iac.md` — Terraform + Ansible
13. `observability.md` — metrics, logs, traces, per-agent/tool metrics
14. `ab_testing.md` — model/prompt A/B + per-version monitoring
15. `security.md` — centralized secret management
16. `validation_verification.md` — coverage, equivalence partitioning,
    boundary, mutation, property-based, load
17. `improve_data_generator.md` — drift simulation, label table, config
18. `repository_design.md` — clean repo, clean code, design patterns
19. `low_level_design.md` — key service classes -> implementation map
20. `novel_ideas.md` — embedding registry + citation guard
21. `cost.md` — cost deliverable

## Related

- [Docs style contract](../../docs-style-contract.md)
- [Mini-coursework rubric index](../rubric-(mini-coursework)/README.md)
- [ML-track deferred index](../ml-track-deferred.md)
- [Canonical LLM evidence rows](../../phase2/evidence/llm/)
- [Rubric matrix](../../phase2/rubric-matrix.csv)
