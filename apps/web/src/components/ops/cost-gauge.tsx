import {
  evaluateCostGate,
  type CostBudget,
  type CostProjection,
} from "@distresslens/contracts";

/**
 * Spend against a hard cap.
 *
 * The bar shows what is already spent and, when a projection is supplied, what
 * the requested action would add on top — because the number that decides
 * whether provision is allowed is the sum, not either half. Crossing the cap is
 * drawn as a distinct segment and stated in words: an operator must not have to
 * infer a denial from a bar being slightly too long.
 */
export function CostGauge({
  budget,
  projection = null,
}: {
  budget: CostBudget;
  /** The pending action's projected cost, when one is being considered. */
  projection?: CostProjection | null;
}) {
  const decision = projection === null ? null : evaluateCostGate(budget, projection);
  const spentShare = Math.min(100, (budget.spentUsd / budget.capUsd) * 100);
  const projectedShare =
    projection === null ? 0 : Math.min(100 - spentShare, (projection.projectedUsd / budget.capUsd) * 100);
  const denied = decision?.result === "DENY_CAP_EXCEEDED";

  return (
    <section className="flex flex-col gap-2.5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-[14px] font-medium text-text-body">{budget.label}</h3>
        <p data-numeric className="font-mono text-[13px] text-text-muted">
          <span className="font-semibold text-text-strong">{budget.spentUsd.toFixed(2)}</span> /{" "}
          {budget.capUsd.toFixed(2)} USD
        </p>
      </div>

      <div
        role="img"
        aria-label={`${budget.label}: đã dùng ${budget.spentUsd.toFixed(2)} trên hạn mức ${budget.capUsd.toFixed(2)} USD của ${budget.periodLabel}`}
        className="flex h-2.5 w-full overflow-hidden rounded-sm bg-paper-2"
      >
        <span
          className={denied ? "bg-risk-high-fill" : "bg-primary-500"}
          style={{ width: `${spentShare}%` }}
        />
        {projectedShare > 0 ? (
          <span
            className="bg-primary-300"
            style={{ width: `${projectedShare}%` }}
          />
        ) : null}
      </div>

      <p className="text-[12px] text-text-muted">Hạn mức {budget.periodLabel}</p>

      {decision !== null ? (
        <p
          className={`rounded-md border px-3 py-2 text-[13px] ${
            denied
              ? "border-risk-high-fill/30 bg-risk-high-soft text-risk-high-ink"
              : "border-line-hairline bg-paper-1 text-text-body"
          }`}
        >
          {denied
            ? decision.reason
            : `Dự kiến thêm ${projection?.projectedUsd.toFixed(2)} USD (${projection?.basis}), còn lại ${decision.remainingUsd.toFixed(2)} USD.`}
        </p>
      ) : null}
    </section>
  );
}
