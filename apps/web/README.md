# DistressLens web

The DistressLens product uses Next.js App Router and Supabase Auth/Postgres.
See the [product contract](../../docs/platform/product.md) for scope and the
[product-shell plan](../../plans/260802-1037-unified-phase2-ml-llm-gitops/phase-02-build-product-shell-supabase-rbac-and-ux-states.md)
for its coursework acceptance criteria.

For local development with fixtures, run from the repository root:

```bash
pnpm install
DISTRESSLENS_DATA_SOURCE=fixture pnpm --filter @distresslens/web dev
pnpm --filter @distresslens/web test
```

For type checks, lint, and fixture browser checks, use the scripts in the
[web package manifest](package.json). See [source CI](../../.github/workflows/ci.yml)
for Playwright setup and required accessibility gates.

## Live runtime

Use the [platform runtime setup](../../docs/operator-runbook.md#phase-2-runtime-setup)
for configured services. Before using `e2e:live`, review the
[live Supabase browser check precautions](../../docs/operator-runbook.md#optional-live-supabase-browser-check).
The [historical coursework route](../../docs/operator-runbook.md#historical-phase-2-evidence)
is separate from current setup and does not select a deployment target.
