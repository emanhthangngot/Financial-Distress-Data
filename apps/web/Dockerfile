# Build from the repository root so the workspace contracts package is available
# to Next.js and stays on the same revision as the product UI.
FROM node:22-bookworm-slim AS builder

WORKDIR /workspace
RUN corepack enable

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/contracts/package.json packages/contracts/package.json
RUN pnpm install --frozen-lockfile

COPY apps/web apps/web
COPY packages/contracts packages/contracts

ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter @distresslens/web build

FROM node:22-bookworm-slim AS runner

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app

RUN groupadd --system --gid 1001 nextjs \
  && useradd --system --uid 1001 --gid nextjs nextjs

COPY --from=builder --chown=nextjs:nextjs /workspace/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /workspace/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=nextjs:nextjs /workspace/apps/web/public ./apps/web/public

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["node", "apps/web/server.js"]
