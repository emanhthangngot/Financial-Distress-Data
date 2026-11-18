import "server-only";

/** Apply the same fixture gate to identity, data selection and quota/audit. */
export function fixtureModeEnabled(env: NodeJS.ProcessEnv = process.env): boolean {
  if (env.DISTRESSLENS_DATA_SOURCE !== "fixture") return false;
  if (
    env.DISTRESSLENS_RELEASE_IMAGE === "1" ||
    env.VERCEL_ENV === "production" ||
    (env.NODE_ENV === "production" && env.DISTRESSLENS_ALLOW_LOCAL_FIXTURES !== "1")
  ) {
    throw new Error("fixture mode is not permitted in this deployment; configure Supabase auth");
  }
  return true;
}
