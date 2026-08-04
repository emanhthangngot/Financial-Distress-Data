import type { ModelComparison, ModelComparisonSide } from "@distresslens/contracts";
import { RiskBadge } from "@/components/ui/risk-badge";

/**
 * Candidate against baseline for one company.
 *
 * The delta between them is computed and shown once, in the middle, rather than
 * left for the reader to subtract: the entire question on this page is "does
 * the new model change the call", and a 3-point move that crosses a band
 * boundary matters more than a 6-point move inside one.
 */
export function ComparisonSplit({ comparison }: { comparison: ModelComparison }) {
  const { candidate, baseline } = comparison;
  const delta = baseline === null ? null : candidate.distressProbability - baseline.distressProbability;
  const bandChanged = baseline !== null && baseline.band !== candidate.band;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] lg:items-center">
        <ComparisonSide side={baseline} label="Phiên bản nền" />

        <div className="flex flex-col items-center gap-1 px-2">
          {delta === null ? (
            <span className="text-[13px] text-text-muted">Không có nền để so sánh</span>
          ) : (
            <>
              <span className="text-[12px] uppercase tracking-[0.06em] text-text-muted">
                Chênh lệch
              </span>
              <span
                data-numeric
                className={`font-mono text-[22px] font-bold ${
                  delta > 0 ? "text-risk-high-ink" : delta < 0 ? "text-risk-stable-ink" : "text-text-body"
                }`}
              >
                {delta > 0 ? "+" : delta < 0 ? "−" : ""}
                {Math.abs(delta).toFixed(1)}
              </span>
              <span className="text-[12px] text-text-muted">điểm %</span>
            </>
          )}
        </div>

        <ComparisonSide side={candidate} label="Phiên bản ứng viên" />
      </div>

      {bandChanged ? (
        <p className="rounded-md border border-risk-watch-fill/30 bg-risk-watch-soft px-3.5 py-2.5 text-[13px] text-risk-watch-ink">
          Hai phiên bản xếp doanh nghiệp này vào hai nhóm rủi ro khác nhau. Kiểm tra yếu tố tác động
          trước khi dùng kết quả của phiên bản ứng viên.
        </p>
      ) : null}
    </div>
  );
}

function ComparisonSide({ side, label }: { side: ModelComparisonSide | null; label: string }) {
  if (side === null) {
    return (
      <section className="flex flex-col gap-2 rounded-lg border border-dashed border-line-strong bg-paper-1 px-5 py-4">
        <h3 className="text-[13px] font-medium uppercase tracking-[0.06em] text-text-muted">
          {label}
        </h3>
        <p className="text-[14px] text-text-muted">
          Chưa có phiên bản mô hình nào được promote làm nền cho doanh nghiệp này.
        </p>
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-3 rounded-lg border border-line-hairline bg-paper-0 px-5 py-4 shadow-(--shadow-card)">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-[13px] font-medium uppercase tracking-[0.06em] text-text-muted">
          {label}
        </h3>
        <span className="font-mono text-[13px] font-semibold text-text-strong">
          {side.modelVersion}
        </span>
      </div>

      <p className="flex items-baseline gap-2">
        <span data-numeric className="text-[32px] font-bold leading-none text-text-strong">
          {side.distressProbability.toFixed(1)}
        </span>
        <span className="text-[16px] font-medium text-text-muted">%</span>
      </p>

      <div className="flex flex-wrap items-center gap-3">
        <RiskBadge band={side.band} size="sm" />
        <span data-numeric className="text-[13px] text-text-muted">
          Độ tin cậy {side.confidence}%
        </span>
      </div>

      <div className="border-t border-line-hairline pt-3">
        <h4 className="text-[13px] font-medium text-text-muted">Yếu tố tác động lớn nhất</h4>
        <ul className="mt-2 flex flex-col gap-1.5">
          {side.topDrivers.map((driver) => (
            <li
              key={driver.feature}
              className="flex items-baseline justify-between gap-3 text-[13px]"
            >
              <span className="min-w-0 truncate text-text-body">{driver.feature}</span>
              <span
                data-numeric
                className={`shrink-0 font-mono font-semibold ${
                  driver.direction === "INCREASES_RISK"
                    ? "text-risk-high-ink"
                    : "text-risk-stable-ink"
                }`}
              >
                {driver.contribution > 0 ? "+" : "−"}
                {Math.abs(driver.contribution).toFixed(1)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
