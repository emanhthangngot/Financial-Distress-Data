import type { ReactNode } from "react";

/**
 * Page header for analyst surfaces: what this page is, how current it is, and
 * the controls that change or export what is on it.
 *
 * The freshness line sits next to the title rather than in the chrome, because
 * "as of when" is part of reading a risk number, not a system detail.
 */
export function PageHeader({
  title,
  description,
  freshnessLabel,
  controls,
  primaryAction,
}: {
  title: string;
  description: string;
  freshnessLabel: string;
  /** Range selectors and filters. */
  controls?: ReactNode;
  primaryAction?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
      <div className="min-w-0">
        <h1 className="text-[28px]">{title}</h1>
        <p className="mt-1 text-[15px] text-text-muted">{description}</p>
        <p className="mt-1.5 text-[13px] text-text-muted">{freshnessLabel}</p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {controls}
        {primaryAction}
      </div>
    </div>
  );
}

/**
 * Period selector. A plain GET form so the choice lives in the URL and the page
 * stays screenshot-reproducible for the evidence run.
 */
export function PeriodFilter({
  value,
  options,
}: {
  value: string;
  options: readonly { value: string; label: string }[];
}) {
  return (
    <form method="get" className="flex items-center">
      <label htmlFor="period-filter" className="sr-only">
        Khoảng thời gian
      </label>
      <select
        id="period-filter"
        name="period"
        defaultValue={value}
        className="tap-target rounded-md border border-line-strong bg-paper-0 px-3 py-2 text-[14px] font-medium text-text-strong focus:border-primary-500 focus:outline-none"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {/* Without JS the choice still applies; with JS the form submits on
          change through the browser's native behaviour on the submit button. */}
      <button type="submit" className="tap-target ml-1 rounded-md px-3 text-[14px] text-primary-600 hover:bg-primary-050">
        Áp dụng
      </button>
    </form>
  );
}
