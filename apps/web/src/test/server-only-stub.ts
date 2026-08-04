/**
 * Test-only stand-in for the `server-only` package.
 *
 * The real module throws when imported outside a React Server Component, which
 * is what keeps server code out of the client bundle. Vitest is neither, so it
 * hits that guard on every server-boundary unit test. Aliasing it here removes
 * the runner's problem without weakening the build, where Next.js still refuses
 * to bundle a `server-only` import into a client component.
 */
export {};
