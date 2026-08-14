import "server-only";

/**
 * Validates a post-auth redirect target: only a same-origin relative path is
 * accepted. An absolute or protocol-relative value (`https://evil`,
 * `//evil`) is a classic open-redirect shape, so anything but a leading
 * single `/` is rejected in favor of the default `/`. A literal backslash is
 * rejected too -- the WHATWG URL parser treats `\` as `/` for special
 * schemes, so `/\evil.com` and `/\/evil.com` both resolve cross-origin at
 * `new URL(target, request.url)` in `sign-out/route.ts` even though they
 * pass the `//` check; no legitimate route in this app ever contains one.
 *
 * A plain (non-"use server") module: `sign-in-action.ts` is a Server Actions
 * file, and Next.js requires every export from a `"use server"` file to be an
 * async function -- this sync helper has to live outside it to be shared with
 * `sign-out/route.ts`, which is a route handler, not a server action.
 */
export function safeRedirectTarget(next: FormDataEntryValue | string | null): string {
  if (typeof next !== "string" || next === "") {
    return "/";
  }
  if (!next.startsWith("/") || next.startsWith("//") || next.includes("\\")) {
    return "/";
  }
  return next;
}
