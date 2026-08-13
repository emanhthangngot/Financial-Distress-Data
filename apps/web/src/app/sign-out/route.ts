import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const ACCESS_TOKEN_COOKIE = "sb-access-token";

/**
 * Ends the server-side session created by the sign-in action.
 *
 * The shell exposes this as a normal link so it remains usable when a client
 * bundle is unavailable. Keep the redirect same-origin and use the exact
 * cookie contract read by `resolveSession`.
 */
export async function GET(request: Request): Promise<NextResponse> {
  (await cookies()).delete(ACCESS_TOKEN_COOKIE);

  return NextResponse.redirect(new URL("/sign-in", request.url));
}
