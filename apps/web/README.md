# DistressLens web

platform .roduct shell: Next.js 16 (App Router) + Supabase Auth/Postgres. See
`docs/platform/product.md` and `../../plans/260802-1037-unified-platform-ml-llm-gitops/phase-02-build-product-shell-supabase-rbac-and-ux-states.md`
for scope and acceptance criteria.

```bash
pnpm install
pnpm --filter @distresslens/web dev
pnpm --filter @distresslens/web test
```

## Live platform .2E

The complete service graph runs in the GitOps/GKE evidence cluster. From the
GitOps checkout, run the source-repo runner after the node pool is available:

```bash
make platform-e2e \
  SOURCE_REPO=/home/pearspringmind/Studying/FSDS/Financial-Distress-Data \
  PHASE2_E2E_ARGS="--json"
```

The runner waits for the web, MCP, agent, gateway, data, and observability
workloads; warms the active model revision through agentgateway; then sends a
live coordinator request with a numeric drift observation. It exits non-zero
and prints the failed check when a service or evidence contract is not ready.
`--web-url` can be added to probe a reachable ingress URL. The authenticated
browser smoke remains `pnpm --filter @distresslens/web e2e:live` because it
provisions a real Supabase session.
