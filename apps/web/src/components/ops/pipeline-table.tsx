import type { PipelineRow, PipelineStatus } from "@distresslens/contracts";
import Link from "next/link";
import { EmptyState } from "@/components/ui/state-panel";

/**
 * Pipeline runs behind the current revision.
 *
 * Status is a labelled chip, never a bare colour: an operator scanning six rows
 * for the one that failed must be able to do it from the words. Rows keep the
 * declared order rather than sorting failures to the top, because the order is
 * the pipeline sequence and reordering it would hide which stage broke first.
 */

const STATUS_LABEL: Record<PipelineStatus, string> = {
  SUCCEEDED: "Thành công",
  RUNNING: "Đang chạy",
  DEGRADED: "Suy giảm",
  FAILED: "Thất bại",
  IDLE: "Chưa chạy",
};

const STATUS_TONE: Record<PipelineStatus, string> = {
  SUCCEEDED: "border-risk-stable-fill/35 bg-risk-stable-soft text-risk-stable-ink",
  RUNNING: "border-primary-600/30 bg-primary-050 text-ink-900",
  DEGRADED: "border-risk-watch-fill/35 bg-risk-watch-soft text-risk-watch-ink",
  FAILED: "border-risk-high-fill/35 bg-risk-high-soft text-risk-high-ink",
  IDLE: "border-line-strong bg-paper-2 text-text-muted",
};

export function PipelineTable({ pipelines }: { pipelines: readonly PipelineRow[] }) {
  if (pipelines.length === 0) {
    return (
      <EmptyState
        title="Chưa có pipeline nào chạy"
        description="Revision hiện tại chưa kích hoạt pipeline nào trong môi trường này."
      />
    );
  }

  return (
    <div
      className="overflow-x-auto"
      tabIndex={0}
      role="region"
      aria-label="Pipeline theo revision hiện tại, trạng thái và thời điểm chạy gần nhất"
    >
      <table className="w-full min-w-[640px] border-collapse text-[14px]">
        <caption className="sr-only">
          Pipeline theo revision hiện tại, trạng thái và thời điểm chạy gần nhất
        </caption>
        <thead>
          <tr className="border-b border-line-hairline text-left text-[13px] text-text-muted">
            <th scope="col" className="py-2 pr-3 font-medium">
              Pipeline
            </th>
            <th scope="col" className="py-2 pr-3 font-medium">
              Chủ sở hữu
            </th>
            <th scope="col" className="py-2 pr-3 font-medium">
              Revision
            </th>
            <th scope="col" className="py-2 pr-3 font-medium">
              Trạng thái
            </th>
            <th scope="col" className="py-2 pr-3 font-medium">
              Chạy lúc
            </th>
            <th scope="col" className="py-2">
              <span className="sr-only">Bằng chứng</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line-hairline">
          {pipelines.map((pipeline) => (
            <tr key={pipeline.id} id={`pipeline-${pipeline.id}`}>
              <th scope="row" className="py-2.5 pr-3 text-left">
                <span className="block font-medium text-text-strong">{pipeline.name}</span>
                <span className="block text-[13px] font-normal text-text-muted">
                  {pipeline.description}
                </span>
              </th>
              <td className="py-2.5 pr-3 text-text-body">{pipeline.owner}</td>
              <td data-numeric className="py-2.5 pr-3 font-mono text-[13px] text-text-body">
                {pipeline.revision}
              </td>
              <td className="py-2.5 pr-3">
                <span
                  className={`inline-flex whitespace-nowrap rounded-sm border px-1.5 py-0.5 text-[12px] font-medium ${STATUS_TONE[pipeline.status]}`}
                >
                  {STATUS_LABEL[pipeline.status]}
                </span>
              </td>
              <td
                data-numeric
                className="whitespace-nowrap py-2.5 pr-3 font-mono text-[13px] text-text-muted"
              >
                {formatTimestamp(pipeline.lastRunAt)}
              </td>
              <td className="py-2.5 text-right">
                {pipeline.evidenceUrl === null ? (
                  <span className="text-[13px] text-text-muted">Chưa có</span>
                ) : (
                  <Link
                    href={pipeline.evidenceUrl}
                    className="whitespace-nowrap text-[13px] font-medium text-primary-600 underline-offset-2 hover:underline"
                  >
                    Xem log
                    <span className="sr-only"> của pipeline {pipeline.name}</span>
                  </Link>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatTimestamp(iso: string): string {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(new Date(iso));
}
