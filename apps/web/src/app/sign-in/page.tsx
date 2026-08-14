import Link from "next/link";
import { AuthCard } from "@/components/auth/auth-card";
import { SignInForm } from "@/components/auth/sign-in-form";

/**
 * Sign-in. `?email=` prefills the field -- the account switcher (user-menu.tsx)
 * lands here with the demo profile's address already in place. `?next=` is
 * forwarded to the form and validated server-side by `safeRedirectTarget`
 * before it is ever used as a redirect target.
 *
 * Never prerendered — the copy has no per-request data, but every other route
 * in this app opts out of the static cache for the same reason, so this one
 * stays consistent with them.
 */
export const dynamic = "force-dynamic";

export default async function SignInPage({
  searchParams,
}: {
  searchParams: Promise<{ email?: string; next?: string }>;
}) {
  const { email, next } = await searchParams;

  return (
    <AuthCard
      title="Đăng nhập DistressLens"
      footer={
        <>
          Chưa có tài khoản?{" "}
          <Link href="/sign-up" className="font-medium text-primary-600 hover:underline">
            Đăng ký
          </Link>
        </>
      }
    >
      <SignInForm defaultEmail={email ?? ""} next={next} />
    </AuthCard>
  );
}
