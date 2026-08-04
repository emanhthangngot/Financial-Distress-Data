import { SearchIcon } from "./icons";

/**
 * Global company/ticker search. A plain GET form so it works before hydration
 * and keeps the query in the URL, which is also what makes the search states
 * screenshot-reproducible for the evidence run.
 */
export function HeaderSearch({ defaultValue = "" }: { defaultValue?: string }) {
  return (
    <form action="/companies" method="get" role="search" className="w-full max-w-[520px]">
      <label htmlFor="global-company-search" className="sr-only">
        Tìm kiếm doanh nghiệp hoặc mã chứng khoán
      </label>
      <div className="relative">
        <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-text-muted">
          <SearchIcon />
        </span>
        <input
          id="global-company-search"
          name="q"
          type="search"
          defaultValue={defaultValue}
          placeholder="Tìm kiếm doanh nghiệp hoặc mã (ví dụ: HPG, FPT, VNM)"
          autoComplete="off"
          className="tap-target w-full rounded-md border border-line-hairline bg-paper-0 py-2.5 pl-10 pr-3 text-[15px] text-text-body placeholder:text-text-muted focus:border-ink-500 focus:outline-none"
        />
      </div>
    </form>
  );
}
