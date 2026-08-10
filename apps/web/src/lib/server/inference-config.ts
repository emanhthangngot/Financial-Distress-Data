import "server-only";

/**
 * Inference endpoint resolution for the assistant stream route.
 *
 * The endpoint and its token live in the environment, not in the repo or the
 * audit path. This module is the only place that reads them, and it hands
 * callers either a configured flag or a redacted URL — so a log line or audit
 * row can never carry the bearer token or a `:token@` userinfo.
 */

export const DEFAULT_ASSISTANT_TIMEOUT_MS = 55_000;

/**
 * Hard ceiling below the hosting platform's response limit. The route's timeout
 * must fire and emit a `timeout` frame before the platform kills the request,
 * so the effective value is clamped strictly under 60s.
 */
export const MAX_ASSISTANT_TIMEOUT_MS = 59_000;

export interface InferenceConfig {
  url: string | null;
  token: string | null;
  timeoutMs: number;
  isConfigured: boolean;
}

export function readInferenceConfig(): InferenceConfig {
  const url = process.env.DISTRESSLENS_INFERENCE_URL ?? null;
  const token = process.env.DISTRESSLENS_INFERENCE_TOKEN ?? null;

  const rawTimeout = Number.parseInt(process.env.ASSISTANT_TIMEOUT_MS ?? "", 10);
  const timeoutMs = Number.isFinite(rawTimeout)
    ? Math.min(Math.max(rawTimeout, 1_000), MAX_ASSISTANT_TIMEOUT_MS)
    : DEFAULT_ASSISTANT_TIMEOUT_MS;

  return { url, token, timeoutMs, isConfigured: url !== null && token !== null };
}

/**
 * A URL safe to log or audit: userinfo (`user:token@`) and query parameters are
 * stripped because either can carry a credential. Invalid input becomes a
 * stable literal so nothing about the endpoint shape leaks into logs.
 */
export function redactUrl(url: string): string {
  try {
    const parsed = new URL(url);
    parsed.username = "";
    parsed.password = "";
    parsed.search = "";
    return parsed.toString();
  } catch {
    return "(invalid url)";
  }
}