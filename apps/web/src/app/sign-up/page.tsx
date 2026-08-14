import Link from "next/link";
import { AuthCard } from "@/components/auth/auth-card";
import { SignUpForm } from "@/components/auth/sign-up-form";

/**
 * Open sign-up. New accounts default to `analyst`
 * (`handle_new_user()` in `supabase/migrations/20260814200000_phase2_profile_identity.sql`).
 *
 * Never prerendered, for the same reason as `/sign-in`.
 */
export const dynamic = "force-dynamic";

export default function SignUpPage() {
  return (
    <AuthCard
      title="Đăng ký DistressLens"
      description="Tài khoản mới có vai trò chuyên viên phân tích."
      footer={
        <>
          Đã có tài khoản?{" "}
          <Link href="/sign-in" className="font-medium text-primary-600 hover:underline">
            Đăng nhập
          </Link>
        </>
      }
    >
      <SignUpForm />
    </AuthCard>
  );
}
