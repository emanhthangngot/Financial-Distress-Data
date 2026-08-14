"use client";

import { useActionState } from "react";
import { updateDisplayName, type ActionResult } from "@/lib/server/profile-actions";

const INITIAL_RESULT: ActionResult = { ok: true, message: "" };

/**
 * One-field self-rename, inline in the account menu. `updateDisplayName`
 * only ever writes `profiles.display_name` -- the owner-only column grant
 * (`supabase/migrations/20260814200000_phase2_profile_identity.sql`) refuses
 * anything else at the database, so there is nothing here to restrict beyond
 * form validation.
 */
export function DisplayNameForm({ currentName }: { currentName: string }) {
  const [result, formAction, pending] = useActionState(updateDisplayName, INITIAL_RESULT);

  return (
    <form action={formAction} className="flex flex-col gap-1.5 px-2.5 py-2">
      <label className="flex flex-col gap-1 text-[13px] text-text-muted" htmlFor="display-name-input">
        Tên hiển thị
      </label>
      <div className="flex gap-1.5">
        <input
          id="display-name-input"
          type="text"
          name="displayName"
          defaultValue={currentName}
          maxLength={80}
          className="tap-target min-w-0 flex-1 rounded-md border border-line-strong bg-paper-0 px-2.5 py-1.5 text-[13px]"
        />
        <button
          type="submit"
          disabled={pending}
          className="tap-target shrink-0 rounded-md border border-line-strong px-2.5 text-[13px] font-medium text-text-body hover:bg-paper-2 disabled:text-text-muted"
        >
          Lưu
        </button>
      </div>
      {result.message !== "" && !result.ok ? (
        <span role="alert" className="text-[12px] text-risk-high-ink">
          {result.message}
        </span>
      ) : null}
      {result.message !== "" && result.ok ? (
        <span role="status" className="text-[12px] text-text-muted">
          {result.message}
        </span>
      ) : null}
    </form>
  );
}
