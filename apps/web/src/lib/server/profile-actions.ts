"use server";

import "server-only";
import { revalidatePath } from "next/cache";
import { resolveSession } from "./session";
import { createRequestClient } from "./supabase";

/**
 * Self-service profile mutations for the signed-in caller.
 *
 * `role` is never accepted as input here, by construction: the only field
 * this action reads from the form is `displayName`, and the client it writes
 * through carries the caller's own access token, so the request runs under
 * RLS -- the owner-only column grant added in
 * `supabase/migrations/20260814200000_phase2_profile_identity.sql` refuses a
 * role write at the database even if a caller tried to smuggle one in.
 */

export interface ActionResult {
  ok: boolean;
  message: string;
}

export async function updateDisplayName(
  _prevState: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const displayName = formData.get("displayName");

  if (typeof displayName !== "string" || displayName.trim() === "") {
    return { ok: false, message: "Nhập tên hiển thị." };
  }
  if (displayName.trim().length > 80) {
    return { ok: false, message: "Tên hiển thị quá dài." };
  }

  const { context, accessToken } = await resolveSession();
  if (context.userId === null) {
    return { ok: false, message: "Phiên đăng nhập không hợp lệ. Đăng nhập lại để tiếp tục." };
  }

  const client = createRequestClient(accessToken);
  const { error } = await client
    .from("profiles")
    .update({ display_name: displayName.trim() })
    .eq("user_id", context.userId);

  if (error !== null) {
    return { ok: false, message: "Không cập nhật được tên. Thử lại." };
  }

  revalidatePath("/", "layout");
  return { ok: true, message: "Đã cập nhật tên hiển thị." };
}
