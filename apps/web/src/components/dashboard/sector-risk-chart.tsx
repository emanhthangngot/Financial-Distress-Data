import type { SectorRisk } from "@distresslens/contracts";
import { EmptyState } from "@/components/ui/state-panel";

/**
 * Average distress probability by sector, as horizontal bars.
 *
 * Drawn with CSS rather than a charting dependency: the shape is eight
 * proportional bars, and a chart library would arrive with its own colours,
 * radii and fonts to fight the token system for no gain.
 *
 * Every bar carries its number in text next to it, and the whole chart repeats
 * as a table for screen readers, so nothing here is legible only as a picture.
 * The market average sits on the axis as a reference line, which is the
 * comparison an analyst actually makes.
 */

export function SectorRiskChart({
  sectors,
  marketAverage,
}: {
  sectors: readonly SectorRisk[];
  marketAverage: number;
}) {
  if (sectors.length === 0) {
    return (
      <EmptyState
        title="Chưa có số liệu theo ngành"
        description="Kỳ dữ liệu hiện tại chưa đủ doanh nghiệp để tính rủi ro trung bình ngành."
      />
    );
  }

  const max = Math.max(
    ...sectors.map((sector) => sector.averageDistressProbability),
    marketAverage,
  );
  const scale = (value: number) => `${(value / max) * 100}%`;

  return (
    <figure className="flex flex-col gap-3">
      <figcaption className="flex items-center gap-4 text-[13px] text-text-muted">
        <span className="flex items-center gap-1.5">
          <span aria-hidden="true" className="h-2.5 w-2.5 rounded-[2px] bg-primary-500" />
          Xác suất distress trung bình
        </span>
        <span className="flex items-center gap-1.5">
          <span aria-hidden="true" className="h-3.5 w-0.5 bg-text-strong" />
          Trung bình thị trường {marketAverage.toFixed(1)}%
        </span>
      </figcaption>

      <ul aria-hidden="true" className="flex flex-col gap-2.5">
        {sectors.map((sector) => (
          <li
            key={sector.sector}
            className="grid grid-cols-[minmax(0,1fr)] gap-1 sm:grid-cols-[190px_minmax(0,1fr)] sm:items-center sm:gap-3"
          >
            <span className="truncate text-[13px] text-text-body">{sector.sector}</span>
            <span className="relative flex h-6 items-center">
              <span className="absolute inset-y-0 left-0 w-full rounded-sm bg-paper-2" />
              <span
                className="absolute inset-y-0 left-0 rounded-sm bg-primary-500"
                style={{ width: scale(sector.averageDistressProbability) }}
              />
              {/* Market average reference line. */}
              <span
                className="absolute inset-y-0 w-0.5 bg-text-strong"
                style={{ left: scale(marketAverage) }}
              />
              <span
                data-numeric
                className="relative ml-auto pr-2 font-mono text-[12px] font-semibold text-text-strong"
              >
                {sector.averageDistressProbability.toFixed(1)}%
              </span>
            </span>
          </li>
        ))}
      </ul>

      {/* The same data as a table: this is what a screen reader reads, and what
          a reader who cannot compare bar lengths uses instead.

          `sr-only` sits on the wrapper, not the table: a table ignores the 1px
          width the utility sets and lays out to its content, which pushed the
          document 96px wider than the viewport on a phone. */}
      <div className="sr-only">
        <table>
          <caption>Xác suất distress trung bình theo ngành và thay đổi trong 7 ngày</caption>
          <thead>
            <tr>
              <th scope="col">Ngành</th>
              <th scope="col">Xác suất distress trung bình</th>
              <th scope="col">Thay đổi 7 ngày</th>
            </tr>
          </thead>
          <tbody>
            {sectors.map((sector) => (
              <tr key={sector.sector}>
                <th scope="row">{sector.sector}</th>
                <td>{sector.averageDistressProbability.toFixed(1)}%</td>
                <td>
                  {sector.changeOver7Days === 0
                    ? "không đổi"
                    : `${sector.changeOver7Days > 0 ? "tăng" : "giảm"} ${Math.abs(sector.changeOver7Days).toFixed(1)} điểm phần trăm`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}
