import type { SourceKind, SourceRef } from "@distresslens/contracts";
import { ExternalLinkIcon } from "@/components/shell/icons";
import { EmptyState } from "@/components/ui/state-panel";

/**
 * What the score was built from.
 *
 * The source kind is a visible chip rather than an inferred detail, because an
 * audited financial statement and a news article carry very different weight
 * and an analyst must be able to tell them apart at a glance.
 */

const KIND_LABEL: Record<SourceKind, string> = {
  BCTC: "Báo cáo tài chính",
  NEWS: "Tin tức",
  MARKET: "Dữ liệu thị trường",
  INTERNAL: "Nội bộ",
};

const KIND_TONE: Record<SourceKind, string> = {
  BCTC: "border-primary-600/30 bg-primary-050 text-ink-900",
  NEWS: "border-line-strong bg-paper-2 text-text-body",
  MARKET: "border-line-strong bg-paper-2 text-text-body",
  INTERNAL: "border-line-strong bg-paper-2 text-text-body",
};

export function SourceList({ sources }: { sources: readonly SourceRef[] }) {
  if (sources.length === 0) {
    return (
      <EmptyState
        title="Chưa có nguồn dữ liệu được ghi nhận"
        description="Kết quả này chưa gắn được với báo cáo hoặc tin tức nguồn nào trong kỳ dữ liệu hiện tại."
      />
    );
  }

  return (
    <ol className="flex flex-col divide-y divide-line-hairline">
      {sources.map((source, index) => (
        <li key={source.id} className="flex gap-3 py-3 first:pt-0 last:pb-0">
          <span
            aria-hidden="true"
            className="shrink-0 pt-0.5 font-mono text-[12px] text-text-muted"
          >
            [{index + 1}]
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[14px] text-text-body">
              {source.url === null ? (
                source.title
              ) : (
                <a
                  href={source.url}
                  rel="noreferrer noopener"
                  target="_blank"
                  className="font-medium text-primary-600 underline-offset-2 hover:underline"
                >
                  {source.title}
                  <span className="ml-1 inline-block translate-y-0.5">
                    <ExternalLinkIcon />
                  </span>
                  <span className="sr-only">(mở tab mới)</span>
                </a>
              )}
            </p>
            <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] text-text-muted">
              <span
                className={`rounded-sm border px-1.5 py-0.5 font-medium ${KIND_TONE[source.kind]}`}
              >
                {KIND_LABEL[source.kind]}
              </span>
              <span>{source.publisher}</span>
              <span aria-hidden="true">·</span>
              <time dateTime={source.publishedAt} data-numeric className="font-mono">
                {source.publishedAt}
              </time>
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}
