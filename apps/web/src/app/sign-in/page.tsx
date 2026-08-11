import { SignInForm } from "@/components/auth/sign-in-form";

/**
 * The one sign-in path (plans/260811-1627-close-llm-rubric-to-100/phase-03):
 * no sign-up, no password reset, one demo/grader account provisioned out of
 * band in Supabase. Never prerendered — a cached page here would be a
 * meaningless win and the copy has no per-request data anyway, but every
 * other route in this app opts out of the static cache for the same reason,
 * so this one stays consistent with them.
 */
export const dynamic = "force-dynamic";

export default function SignInPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-paper-1 px-4">
      <h1 className="text-[20px] font-semibold text-text-strong">Đăng nhập DistressLens</h1>
      <SignInForm />
    </main>
  );
}
