import type { DemoAccount } from "@/lib/server/demo-accounts";
import { ROLE_LABELS } from "./role-labels";

/**
 * Demo-profile switcher, listed below the identity block in the account
 * menu. Picking one is a real sign-out followed by a real sign-in -- no
 * impersonation, no client-held credentials, per the plan's accepted
 * decision. It reuses the existing GET sign-out route, extended with a
 * validated `next` that lands on `/sign-in` with the chosen email prefilled.
 *
 * Renders nothing when `DISTRESSLENS_DEMO_ACCOUNTS` is unset, so a
 * misconfigured env var only removes a convenience, never breaks sign-in.
 */
export function AccountSwitcher({ accounts }: { accounts: readonly DemoAccount[] }) {
  if (accounts.length === 0) {
    return null;
  }

  return (
    <div className="border-t border-line-hairline pt-1">
      <p className="px-2.5 py-1.5 text-[12px] font-medium uppercase tracking-wide text-text-muted">
        Chuyển hồ sơ
      </p>
      {accounts.map((account) => {
        const next = `/sign-in?email=${encodeURIComponent(account.email)}`;
        return (
          <a
            key={account.email}
            href={`/sign-out?next=${encodeURIComponent(next)}`}
            className="tap-target flex flex-col justify-center gap-0 rounded-sm px-2.5 py-1.5 text-[13px] text-text-body hover:bg-paper-2"
          >
            <span className="font-medium">{account.label}</span>
            <span className="text-[12px] text-text-muted">{ROLE_LABELS[account.role]}</span>
          </a>
        );
      })}
    </div>
  );
}
