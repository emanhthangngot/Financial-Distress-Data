import { LIVE_FIXTURE_PROVENANCE } from "@/lib/data/fixtures/provenance-fixtures";
import { resolveSession } from "@/lib/server/session";
import { AnalystShell } from "@/components/shell/analyst-shell";
import { DisclaimerBanner } from "@/components/shell/disclaimer-banner";

/**
 * Analyst overview. The shell, provenance ribbon and page frame are in place;
 * the risk cards, attention table, alert rail and sector chart are built on
 * this frame in the analyst-routes step.
 */
export default async function OverviewPage() {
  const { user, context } = await resolveSession();

  return (
    <AnalystShell
      user={user}
      provenance={LIVE_FIXTURE_PROVENANCE}
      freshnessLabel="Đồng bộ lần cuối: 23/05/2025 08:46"
    >
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-[26px]">Tổng quan</h1>
            <p className="mt-1 text-[15px] text-text-muted">
              Theo dõi và đánh giá rủi ro tài chính của danh mục doanh nghiệp
            </p>
          </div>
          <a
            href="/agents/chat"
            className="tap-target flex items-center rounded-md bg-ink-800 px-4 py-2.5 text-[15px] font-semibold text-paper-0 transition-colors duration-(--duration-fast) ease-(--ease-standard) hover:bg-ink-700"
          >
            Phân tích với AI
          </a>
        </div>

        <DisclaimerBanner surface="company" />

        <p className="text-[14px] text-text-muted">
          Vai trò hiện tại:{" "}
          <strong className="text-text-body">{context.role ?? "chưa đăng nhập"}</strong>
        </p>
      </div>
    </AnalystShell>
  );
}
