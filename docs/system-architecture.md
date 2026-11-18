# System Architecture

Phase 1 is a local-first lakehouse. Phase 2 adds a persistent product and
on-demand evidence execution without changing Phase 1 DAGs or storage
contracts. The source contract does not choose a deployment provider.

## Architecture boundaries

| Boundary | Authority |
|---|---|
| Phase 1 lakehouse | [Local Compose](../docker-compose.yml) and the [Phase 1 spec](mini_coursework.md) |
| Persistent product | [Web workspace](../apps/web/) and [Supabase migrations](../supabase/migrations/) |
| Live evidence execution | [Operator-selected runtime](operator-runbook.md#phase-2-runtime-setup) managed by the external deployment owner |
| Image handoff and promotion | [Source CI](../.github/workflows/phase2-ci.yaml) hands off signed immutable images; rollout and rollback are external |

The persistent product must remain useful when live evidence services are
unavailable. Hosting is a deployment decision, not a product dependency:
the external owner supplies compatible services through explicit endpoints
and is responsible for their readiness. [Handoff criteria](operator-runbook.md#external-deployment-handoff)
and [repository ownership](architecture/repository-map.md) identify where to
make that decision.

## Coursework diagram index

The composed diagram and subsystem views preserve the coursework topology,
including the captured GKE/GitOps deployment. They do not prescribe a
provider for this source checkout. Color legend (see the
[diagram rule](docs-style-contract.md#7-diagram-rule)): `edge` = client/ingress boundary,
`service` = running deployable unit, `store` = persisted state, `model` =
ML/LLM artifact or serving endpoint, `result` = observability/output surface.

| # | Subsystem | Source | Owning narrative doc |
|---|---|---|---|
| 1 | Phase 1 lakehouse | `docs/architecture/subsystem-01-lakehouse.mmd` | `docs/submission/rubric-(mini-coursework)/data_pipeline_orchestration.md` |
| 2 | LLM inference platform | `docs/architecture/subsystem-02-llm-inference-platform.mmd` | `docs/submission/rubric-final-coursework-(final-llm)/llm_inference_platform.md` |
| 3 | RAG pipeline | `docs/architecture/subsystem-03-rag-pipeline.mmd` | `docs/submission/rubric-final-coursework-(final-llm)/rag.md` |
| 4 | Agent plane | `docs/architecture/subsystem-04-agent-plane.mmd` | `docs/submission/rubric-final-coursework-(final-llm)/coordinator_agent.md` |
| 5 | Product plane | `docs/architecture/subsystem-05-product-plane.mmd` | `docs/submission/rubric-final-coursework-(final-llm)/web_api_user_data.md` |
| 6 | GitOps / CI-CD | `docs/architecture/subsystem-06-gitops-cicd.mmd` | `docs/submission/rubric-final-coursework-(final-llm)/ci_cd.md` |
| 7 | Observability + drift | `docs/architecture/subsystem-07-observability-drift.mmd` | `docs/submission/rubric-final-coursework-(final-llm)/observability.md` |

Composed system diagram (README hero):

![System architecture overview — seven subsystems and their cross-boundary contracts](pngs/system_architecture_overview.png)

Source: `docs/architecture/system-overview.mmd`. Regenerate with:

```bash
PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome-stable \
  npx -y @mermaid-js/mermaid-cli \
  -i docs/architecture/system-overview.mmd \
  -o docs/pngs/system_architecture_overview.png -b white -w 1400
```

Keep the [spec-pinned Phase 1 image](../images/architecture/architecture-stage-1.png)
for the [Phase 1 deliverable](mini_coursework.md). The composed hero is the
cross-subsystem coursework view; the DOT-rendered image below is Phase 1 only.

## Phase 1 — verified local lakehouse

![Deployment architecture](../images/architecture/system_deployment_diagram.png)

Use the [local runbook](operator-runbook.md#local-setup) and [naming convention](operator-runbook.md#naming-convention)
for current Phase 1 setup and storage boundaries.

## Runtime trust and coursework evidence

Live evidence must come from the configured runtime, not from fixture data,
an old receipt, or an assumption that the coursework cluster is reachable.
Keep credentials and provisioning out of source and docs. Preserve the
Phase 1 metadata and evidence boundary when adding a Phase 2 runtime.

The GKE architecture and the source/GitOps SHAs belong to the
[historical coursework evidence](operator-runbook.md#historical-phase-2-evidence).
They establish the topology and revisions for that captured run, not the
identity, readiness, or provenance of a runtime chosen now.

## Related source-of-truth documents

- [Runtime setup and verification](operator-runbook.md#phase-2-runtime-setup)
- [Repository ownership map](architecture/repository-map.md)
- [Coursework scope](coursework.md) and [submission reviewer index](submission/README.md)
