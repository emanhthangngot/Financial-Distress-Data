"use client";

import { useActionState, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { signUp, type SignUpResult } from "@/lib/server/sign-up-action";

const INITIAL_RESULT: SignUpResult = { ok: true, message: "" };

/**
 * Registration. Confirm-password is validated client-side before submit so a
 * typo is caught before the round trip; the server still only ever sees
 * `password`, never the confirmation field.
 *
 * On success without `needsEmailConfirmation`, `signUp` redirects itself
 * (throws `NEXT_REDIRECT`), so this component only ever has to render the
 * "check your email" state or a failure -- there is no client-side success
 * branch to draw.
 */
export function SignUpForm() {
  const [result, formAction, pending] = useActionState(signUp, INITIAL_RESULT);
  const [mismatch, setMismatch] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    const form = event.currentTarget;
    const password = (form.elements.namedItem("password") as HTMLInputElement).value;
    const confirm = (form.elements.namedItem("confirmPassword") as HTMLInputElement).value;

    if (password !== confirm) {
      event.preventDefault();
      setMismatch(true);
      return;
    }
    setMismatch(false);
  }

  if (result.ok && result.needsEmailConfirmation === true) {
    return (
      <p role="status" className="text-[14px] text-text-body">
        {result.message}
      </p>
    );
  }

  return (
    <form action={formAction} onSubmit={handleSubmit} className="flex w-full flex-col gap-4">
      <label className="flex flex-col gap-1 text-[14px] text-text-body">
        Tên hiển thị <span className="text-text-muted">(tùy chọn)</span>
        <input
          type="text"
          name="displayName"
          autoComplete="name"
          maxLength={80}
          className="tap-target rounded-md border border-line-strong bg-paper-0 px-3 py-2 text-[14px]"
        />
      </label>
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
          minLength={6}
          autoComplete="new-password"
          className="tap-target rounded-md border border-line-strong bg-paper-0 px-3 py-2 text-[14px]"
        />
      </label>
      <label className="flex flex-col gap-1 text-[14px] text-text-body">
        Xác nhận mật khẩu
        <input
          type="password"
          name="confirmPassword"
          required
          minLength={6}
          autoComplete="new-password"
          className="tap-target rounded-md border border-line-strong bg-paper-0 px-3 py-2 text-[14px]"
        />
      </label>
      <Button type="submit" variant="primary" disabled={pending}>
        {pending ? "Đang đăng ký…" : "Đăng ký"}
      </Button>
      {mismatch ? (
        <span role="alert" className="text-[13px] text-risk-high-ink">
          Mật khẩu xác nhận không khớp.
        </span>
      ) : null}
      {!result.ok && result.message !== "" ? (
        <span role="alert" className="text-[13px] text-risk-high-ink">
          {result.message}
        </span>
      ) : null}
    </form>
  );
}
