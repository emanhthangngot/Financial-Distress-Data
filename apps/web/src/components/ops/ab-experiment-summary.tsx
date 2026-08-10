import type { AbExperimentSummary } from "@distresslens/contracts";
import { ExternalLinkIcon } from "@/components/shell/icons";
import { EmptyState } from "@/components/ui/state-panel";

/**
 * Live A/B comparison between agent variants.
 *
 * Success rate, latency and tool-error rate sit side by side because a variant
 * that answers more often but fails its tools more is not an improvement, and
 * showing success rate alone would say it is. No variant is declared the winner
 * here: this page reports the measurements, and promotion is a separate,
 * audited decision.
 */
export function AbExperimentPanel({
  experiments,
}: {
  experiments: readonly AbExperimentSummary[];
}) {
  if (experiments.length === 0) {
    return (
      <EmptyState
        title="Không có thử nghiệm nào đang chạy"
        description="Toàn bộ lưu lượng đang đi vào phiên bản production hiện tại."
      />
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {experiments.map((experiment) => (
        <section key={experiment.id} className="flex flex-col gap-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="font-mono text-[13px] font-semibold text-text-strong">
              {experiment.id}
            </h3>
            <p className="text-[12px] text-text-muted">
              Bắt đầu{" "}
              <time dateTime={experiment.startedAt} data-numeric className="font-mono">
                {experiment.startedAt.slice(0, 10)}
              </time>
            </p>
          </div>

          <div
            className="overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label={`Kết quả 24 giờ gần nhất của từng biến thể trong thử nghiệm ${experiment.id}`}
          >
            <table className="w-full min-w-[520px] border-collapse text-[14px]">
              <caption className="sr-only">
                Kết quả 24 giờ gần nhất của từng biến thể trong thử nghiệm {experiment.id}
              </caption>
              <thead>
                <tr className="border-b border-line-hairline text-[13px] text-text-muted">
                  <th scope="col" className="py-2 pr-3 text-left font-medium">
                    Biến thể
                  </th>
                  <th scope="col" className="py-2 pr-3 text-right font-medium">
                    Lưu lượng
                  </th>
                  <th scope="col" className="py-2 pr-3 text-right font-medium">
                    Lượt gọi 24h
                  </th>
                  <th scope="col" className="py-2 pr-3 text-right font-medium">
                    Tỷ lệ thành công
                  </th>
                  <th scope="col" className="py-2 pr-3 text-right font-medium">
                    p95
                  </th>
                  <th scope="col" className="py-2 text-right font-medium">
                    Lỗi tool
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-hairline">
                {experiment.variants.map((variant) => (
                  <tr key={variant.name}>
                    <th scope="row" className="py-2.5 pr-3 text-left font-medium text-text-strong">
                      {variant.name}
                    </th>
                    <td data-numeric className="py-2.5 pr-3 text-right font-mono text-text-body">
                      {variant.trafficShare}%
                    </td>
                    <td data-numeric className="py-2.5 pr-3 text-right font-mono text-text-body">
                      {variant.callCount24h.toLocaleString("vi-VN")}
                    </td>
                    <td data-numeric className="py-2.5 pr-3 text-right font-mono text-text-body">
                      {variant.successRate.toFixed(1)}%
                    </td>
                    <td data-numeric className="py-2.5 pr-3 text-right font-mono text-text-body">
                      {variant.p95LatencyMs} ms
                    </td>
                    <td data-numeric className="py-2.5 text-right font-mono text-text-body">
                      {variant.toolErrorRate.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {experiment.dashboardUrl === null ? null : (
            <a
              href={experiment.dashboardUrl}
              rel="noreferrer noopener"
              target="_blank"
              className="inline-flex items-center gap-1 text-[13px] font-medium text-primary-600 underline-offset-2 hover:underline"
            >
              Xem dashboard chi tiết
              <ExternalLinkIcon />
              <span className="sr-only">(mở tab mới)</span>
            </a>
          )}
        </section>
      ))}
    </div>
  );
}
