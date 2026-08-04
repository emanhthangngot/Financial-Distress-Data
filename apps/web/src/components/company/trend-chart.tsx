import type { TrendPoint } from "@distresslens/contracts";
import { EmptyState } from "@/components/ui/state-panel";

/**
 * Distress probability and Altman Z over the reported quarters.
 *
 * Two series on one frame because they answer the same question from opposite
 * directions — the model's own probability and the classical accounting score —
 * and an analyst's first move is to check whether they agree. They use separate
 * axes, labelled, because they are not the same unit; drawing them on one axis
 * would be a lie about scale.
 *
 * Plain SVG, no charting dependency: two polylines and a grid do not justify
 * a library that would arrive with its own type scale and colour ramp.
 */

const WIDTH = 720;
const HEIGHT = 240;
const PAD = { top: 16, right: 44, bottom: 28, left: 44 };

export function TrendChart({ points }: { points: readonly TrendPoint[] }) {
  if (points.length < 2) {
    return (
      <EmptyState
        title="Chưa đủ dữ liệu để vẽ xu hướng"
        description="Cần ít nhất hai kỳ báo cáo liên tiếp để hiển thị diễn biến rủi ro."
      />
    );
  }

  const plotWidth = WIDTH - PAD.left - PAD.right;
  const plotHeight = HEIGHT - PAD.top - PAD.bottom;

  const probs = points.map((point) => point.distressProbability);
  const zScores = points.map((point) => point.altmanZScore);
  const probScale = niceScale(Math.min(...probs), Math.max(...probs));
  const zScale = niceScale(Math.min(...zScores), Math.max(...zScores));

  const x = (index: number) => PAD.left + (index / (points.length - 1)) * plotWidth;
  const y = (value: number, scale: Scale) =>
    PAD.top + plotHeight - ((value - scale.min) / (scale.max - scale.min)) * plotHeight;

  const probLine = points.map((p, i) => `${x(i)},${y(p.distressProbability, probScale)}`).join(" ");
  const zLine = points.map((p, i) => `${x(i)},${y(p.altmanZScore, zScale)}`).join(" ");

  const last = points[points.length - 1];
  const first = points[0];

  return (
    <figure className="flex flex-col gap-3">
      <figcaption className="flex flex-wrap items-center gap-x-5 gap-y-1 text-[13px] text-text-muted">
        <span className="flex items-center gap-1.5">
          <span aria-hidden="true" className="h-0.5 w-5 bg-risk-high-fill" />
          Xác suất distress (%), trục trái
        </span>
        <span className="flex items-center gap-1.5">
          <span aria-hidden="true" className="h-0.5 w-5 border-t-2 border-dashed border-ink-700" />
          Altman Z-Score, trục phải
        </span>
      </figcaption>

      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          role="img"
          aria-label={`Diễn biến từ ${first.period} đến ${last.period}: xác suất distress từ ${first.distressProbability.toFixed(1)}% lên ${last.distressProbability.toFixed(1)}%, Altman Z từ ${first.altmanZScore.toFixed(2)} xuống ${last.altmanZScore.toFixed(2)}.`}
          className="h-[240px] w-full min-w-[560px]"
        >
          {/* Horizontal grid, four bands. Ticks carry the probability axis. */}
          {[0, 0.25, 0.5, 0.75, 1].map((fraction) => {
            const gridY = PAD.top + plotHeight * fraction;
            const value = probScale.max - (probScale.max - probScale.min) * fraction;
            return (
              <g key={fraction}>
                <line
                  x1={PAD.left}
                  x2={WIDTH - PAD.right}
                  y1={gridY}
                  y2={gridY}
                  stroke="var(--color-line-hairline)"
                  strokeWidth={1}
                />
                <text
                  x={PAD.left - 8}
                  y={gridY + 4}
                  textAnchor="end"
                  className="fill-[var(--color-text-muted)] font-mono text-[11px]"
                >
                  {value.toFixed(0)}
                </text>
                <text
                  x={WIDTH - PAD.right + 8}
                  y={gridY + 4}
                  className="fill-[var(--color-text-muted)] font-mono text-[11px]"
                >
                  {(zScale.max - (zScale.max - zScale.min) * fraction).toFixed(1)}
                </text>
              </g>
            );
          })}

          <polyline
            points={zLine}
            fill="none"
            stroke="var(--color-ink-700)"
            strokeWidth={2}
            strokeDasharray="5 4"
            strokeLinejoin="round"
          />
          <polyline
            points={probLine}
            fill="none"
            stroke="var(--color-risk-high-fill)"
            strokeWidth={2.5}
            strokeLinejoin="round"
          />

          {/* Only the last point is marked: it is the number the page is about. */}
          <circle
            cx={x(points.length - 1)}
            cy={y(last.distressProbability, probScale)}
            r={4}
            fill="var(--color-risk-high-fill)"
          />

          {points.map((point, index) =>
            index % Math.ceil(points.length / 6) === 0 || index === points.length - 1 ? (
              <text
                key={point.period}
                x={x(index)}
                y={HEIGHT - 8}
                textAnchor="middle"
                className="fill-[var(--color-text-muted)] font-mono text-[11px]"
              >
                {point.period}
              </text>
            ) : null,
          )}
        </svg>
      </div>

      <div className="sr-only">
        <table>
          <caption>Xác suất distress và Altman Z-Score theo kỳ báo cáo</caption>
          <thead>
            <tr>
              <th scope="col">Kỳ</th>
              <th scope="col">Xác suất distress</th>
              <th scope="col">Altman Z-Score</th>
            </tr>
          </thead>
          <tbody>
            {points.map((point) => (
              <tr key={point.period}>
                <th scope="row">{point.period}</th>
                <td>{point.distressProbability.toFixed(1)}%</td>
                <td>{point.altmanZScore.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}

interface Scale {
  min: number;
  max: number;
}

/**
 * Pads the observed range by 10% so the line never touches the frame, and
 * guards the degenerate case where every value is identical.
 */
function niceScale(min: number, max: number): Scale {
  if (min === max) {
    return { min: min - 1, max: max + 1 };
  }
  const padding = (max - min) * 0.1;
  return { min: min - padding, max: max + padding };
}
