import type { ShapDriver } from "@distresslens/contracts";
import { EmptyState } from "@/components/ui/state-panel";

/**
 * What moved the score, as signed contributions around a zero axis.
 *
 * Risk-increasing drivers run right in red, risk-reducing drivers run left in
 * green, and both carry their signed value in text — the direction is stated in
 * the label as well as the geometry, so the chart is not the only place the
 * sign exists.
 *
 * This is the model's own attribution, not a causal claim, and the caption says
 * so: a SHAP value explains the prediction, not the company.
 */
export function ShapChart({ drivers }: { drivers: readonly ShapDriver[] }) {
  if (drivers.length === 0) {
    return (
      <EmptyState
        title="Chưa có giải thích cho lần chấm điểm này"
        description="Mô hình chưa sinh được đóng góp của từng yếu tố cho kết quả hiện tại."
      />
    );
  }

  const maxMagnitude = Math.max(...drivers.map((driver) => Math.abs(driver.contribution)));

  return (
    <figure className="flex flex-col gap-3">
      <ul className="flex flex-col gap-2">
        {drivers.map((driver) => {
          const increases = driver.direction === "INCREASES_RISK";
          const width = `${(Math.abs(driver.contribution) / maxMagnitude) * 50}%`;

          return (
            <li key={driver.feature} className="flex flex-col gap-1">
              <span className="flex items-baseline justify-between gap-3 text-[13px]">
                <span className="min-w-0 truncate text-text-body">{driver.feature}</span>
                <span
                  data-numeric
                  className={`shrink-0 font-mono font-semibold ${
                    increases ? "text-risk-high-ink" : "text-risk-stable-ink"
                  }`}
                >
                  {driver.contribution > 0 ? "+" : "−"}
                  {Math.abs(driver.contribution).toFixed(1)}
                </span>
              </span>

              {/* Zero sits at the centre; bars grow outward from it. */}
              <span aria-hidden="true" className="relative flex h-3 w-full">
                <span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-line-strong" />
                <span
                  className={`absolute inset-y-0 rounded-sm ${
                    increases ? "left-1/2 bg-risk-high-fill" : "right-1/2 bg-risk-stable-fill"
                  }`}
                  style={{ width }}
                />
              </span>
            </li>
          );
        })}
      </ul>

      <figcaption className="text-[12px] leading-relaxed text-text-muted">
        Giá trị SHAP theo điểm phần trăm: mức đóng góp của từng yếu tố vào kết quả của mô hình,
        không phải quan hệ nhân quả trong hoạt động doanh nghiệp.
      </figcaption>

      <div className="sr-only">
        <table>
          <caption>Đóng góp của từng yếu tố vào xác suất distress</caption>
          <thead>
            <tr>
              <th scope="col">Yếu tố</th>
              <th scope="col">Đóng góp (điểm phần trăm)</th>
              <th scope="col">Hướng tác động</th>
            </tr>
          </thead>
          <tbody>
            {drivers.map((driver) => (
              <tr key={driver.feature}>
                <th scope="row">{driver.feature}</th>
                <td>{driver.contribution.toFixed(1)}</td>
                <td>
                  {driver.direction === "INCREASES_RISK" ? "làm tăng rủi ro" : "làm giảm rủi ro"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}
