"use client";

import { useActionState } from "react";
import { Button } from "@/components/ui/button";
import { signIn, type SignInResult } from "@/lib/server/sign-in-action";

const INITIAL_RESULT: SignInResult = { ok: true, message: "" };

/**
 * The entire sign-in surface: one form, one demo/grader account, no sign-up
 * or password reset. `useActionState` mirrors the pattern already used for
 * session lifecycle transitions (`role-action-button.tsx`) — the server
 * action is the single source of truth for whether the credential is valid;
 * this component only renders its result.
 */
export function SignInForm() {
  const [result, formAction, pending] = useActionState(signIn, INITIAL_RESULT);

  return (
    <form action={formAction} className="flex w-full max-w-[360px] flex-col gap-4">
      <label className="flex flex-col gap-1 text-[14px] text-text-body">
        Email
        <input
          type="email"
          name="email"
          required
          autoComplete="email"
          className="tap-target rounded-md border border-line-strong bg-paper-0 px-3 py-2 text-[14px]"
        />
      </label>
      <label className="flex flex-col gap-1 text-[14px] text-text-body">
        Mật khẩu
        <input
          type="password"
          name="password"
          required
          autoComplete="current-password"
          className="tap-target rounded-md border border-line-strong bg-paper-0 px-3 py-2 text-[14px]"
        />
      </label>
      <Button type="submit" variant="primary" disabled={pending}>
        {pending ? "Đang đăng nhập…" : "Đăng nhập"}
      </Button>
      {!result.ok && result.message !== "" ? (
        <span role="alert" className="text-[13px] text-risk-high-ink">
          {result.message}
        </span>
      ) : null}
    </form>
  );
}
