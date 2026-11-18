# DistressLens web

Phase 2 product shell: Next.js (App Router) and Supabase Auth/Postgres. See the
[product contract](../../docs/phase2/product.md) for scope.

For local development with fixtures, run from the repository root:

```bash
pnpm install
DISTRESSLENS_DATA_SOURCE=fixture pnpm --filter @distresslens/web dev
pnpm --filter @distresslens/web test
```

## Live runtime

Use the [Phase 2 runtime setup](../../docs/operator-runbook.md#phase-2-runtime-setup)
for configured services. Read the [live Supabase browser check precautions](../../docs/operator-runbook.md#optional-live-supabase-browser-check)
before using `e2e:live`. The [historical coursework route](../../docs/operator-runbook.md#historical-phase-2-evidence)
is separate from current setup and does not select a deployment target.
