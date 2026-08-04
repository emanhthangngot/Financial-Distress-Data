"use server";

import { headers } from "next/headers";
import { revalidatePath } from "next/cache";
import {
  evaluateCostGate,
  isSessionState,
  type CostBudget,
  type CostProjection,
  type SessionState,
} from "@distresslens/contracts";
import { guardRequest, type GuardResult } from "./guards";
import { resolveSession } from "./session";
import { createRequestClient } from "./supabase";

/**
 * Evidence-session lifecycle mutations.
 *
 * Everything a client sends is treated as a claim to be checked: the target
 * state is validated against the state enum, the role and AAL are re-derived
 * from the signed session rather than read from the form, and the origin is
 * verified before anything touches the database. The database then re-checks
 * the fencing token and the legality of the transition, so a request that gets
 * past this function still cannot corrupt the state machine.
 *
 * The write itself is one RPC — `request_session_transition` — because the
 * transition row, the outbox row and the session update have to commit
 * together. Issuing them as three statements from here would leave a window
 * where infrastructure work is requested but no transition was recorded.
 */

export interface ActionResult {
  ok: boolean;
  /** User-facing message; never a stack trace or a database error string. */
  message: string;
}

export async function requestSessionTransition(formData: FormData): Promise<ActionResult> {
  const targetState = formData.get("targetState");
  const sessionId = formData.get("sessionId");
  const idempotencyKey = formData.get("idempotencyKey");
  const fencingToken = formData.get("fencingToken");

  if (
    typeof targetState !== "string" ||
    !isSessionState(targetState) ||
    typeof sessionId !== "string" ||
    typeof idempotencyKey !== "string" ||
    idempotencyKey.trim() === "" ||
    typeof fencingToken !== "string"
  ) {
    return { ok: false, message: "Yêu cầu không hợp lệ. Tải lại trang rồi thử lại." };
  }

  const { context, accessToken } = await resolveSession();
  const guard = await guardTransition(context.role, context.aal, context.userId, targetState);
  if (!guard.allowed) {
    return { ok: false, message: guard.denial.reason };
  }

  const client = createRequestClient(accessToken);
  const { error } = await client.rpc("request_session_transition", {
    p_session_id: sessionId,
    p_target_state: targetState,
    p_actor: context.userId ?? "unknown",
    p_idempotency_key: idempotencyKey,
    p_fencing_token: fencingToken,
  });

  if (error !== null) {
    return { ok: false, message: explainTransitionError(error.message) };
  }

  revalidatePath("/ops/evidence");
  return { ok: true, message: "Đã ghi nhận yêu cầu. Trạng thái sẽ cập nhật khi worker xử lý xong." };
}

/**
 * The cost gate, applied only to provision. Destroy deliberately bypasses it:
 * refusing teardown because the budget is exhausted would strand the session
 * that is spending the money.
 */
export function checkProvisionCost(
  budget: CostBudget,
  projection: CostProjection,
): ActionResult {
  const decision = evaluateCostGate(budget, projection);
  return decision.result === "ALLOW"
    ? { ok: true, message: `Còn lại ${decision.remainingUsd} USD trong hạn mức.` }
    : { ok: false, message: decision.reason ?? "Chi phí dự kiến vượt hạn mức." };
}

async function guardTransition(
  role: Parameters<typeof guardRequest>[0]["context"]["role"],
  aal: "aal1" | "aal2",
  userId: string | null,
  targetState: SessionState,
): Promise<GuardResult> {
  const headerList = await headers();

  return guardRequest({
    context: {
      role,
      aal,
      userId,
      origin: headerList.get("origin"),
      host: headerList.get("host"),
    },
    // Teardown is a different permission from provisioning, and an operator who
    // may destroy must not thereby be able to provision.
    action: targetState === "DESTROYING" ? "session.destroy" : "session.provision",
    mutating: true,
  });
}

/**
 * Database errors carry table names and internal identifiers, so they are
 * translated rather than forwarded. The error codes come from the RPC.
 */
function explainTransitionError(message: string): string {
  if (message.includes("stale fencing token")) {
    return "Phiên đã được người khác thay đổi. Tải lại trang để lấy trạng thái mới nhất rồi thử lại.";
  }
  if (message.includes("idempotency key")) {
    return "Yêu cầu này đã được xử lý với một đích khác. Tải lại trang rồi thử lại.";
  }
  if (message.includes("illegal transition")) {
    return "Không thể chuyển sang trạng thái đó từ trạng thái hiện tại.";
  }
  if (message.includes("not found")) {
    return "Không tìm thấy phiên evidence. Tải lại trang.";
  }
  return "Không thực hiện được thao tác. Thử lại, hoặc xem lịch sử audit để biết trạng thái hiện tại.";
}
