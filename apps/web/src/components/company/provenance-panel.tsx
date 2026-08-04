import { isCached, provenanceLabels, type Provenance } from "@distresslens/contracts";

/**
 * The full provenance record for one result.
 *
 * The header status is stated in words before any of the identifiers, because
 * the question a reader has is "is this live or saved", and a wall of SHAs
 * answers it only to someone who already knows the answer. Cached results carry
 * their age explicitly — a saved score with no timestamp is indistinguishable
 * from a fresh one, which is the failure this panel exists to prevent.
 */
export function ProvenancePanel({ provenance }: { provenance: Provenance }) {
  const cached = isCached(provenance);
  const labels = provenanceLabels(provenance);

  return (
    <div className="flex flex-col gap-3">
      <p
        className={`flex items-center gap-2 rounded-md border px-3 py-2 text-[13px] font-medium ${
          cached
            ? "border-risk-watch-fill/30 bg-risk-watch-soft text-risk-watch-ink"
            : "border-risk-stable-fill/30 bg-risk-stable-soft text-risk-stable-ink"
        }`}
      >
        <span
          aria-hidden="true"
          className={`h-2 w-2 shrink-0 rounded-full ${
            cached ? "bg-status-pending" : "bg-status-live"
          }`}
        />
        {cached
          ? "Kết quả đã lưu, không phải suy luận trực tiếp"
          : "Kết quả sinh trực tiếp từ mặt phẳng suy luận"}
      </p>

      {labels.length > 0 ? (
        <ul className="flex flex-wrap gap-1.5">
          {labels.map((label) => (
            <li
              key={label}
              className="rounded-sm border border-line-strong bg-paper-2 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-text-strong"
            >
              {label}
            </li>
          ))}
        </ul>
      ) : null}

      <dl className="flex flex-col gap-2 text-[13px]">
        {provenance.cachedAt !== null ? (
          <Field label="Lưu lúc" value={formatTimestamp(provenance.cachedAt)} />
        ) : null}
        <Field label="Phiên bản dữ liệu" value={provenance.dataVersion} mono />
        {provenance.modelVersion !== null ? (
          <Field label="Mô hình" value={provenance.modelVersion} mono />
        ) : null}
        {provenance.agentVersion !== null ? (
          <Field label="Agent" value={provenance.agentVersion} mono />
        ) : null}
        <Field label="Commit nguồn" value={provenance.sourceSha} mono />
        {provenance.gitopsSha !== null ? (
          <Field label="Commit GitOps" value={provenance.gitopsSha} mono />
        ) : null}
        {provenance.runId !== null ? (
          <Field label="Mã lần chạy" value={provenance.runId} mono />
        ) : null}
      </dl>
    </div>
  );
}

function Field({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-line-hairline pb-2 last:border-b-0 last:pb-0">
      <dt className="shrink-0 text-text-muted">{label}</dt>
      <dd
        className={`min-w-0 truncate text-right text-text-body ${mono ? "font-mono text-[12px]" : ""}`}
      >
        {value}
      </dd>
    </div>
  );
}

function formatTimestamp(iso: string): string {
  // Fixed locale and timezone: the evidence screenshots must be byte-stable
  // regardless of where the run happens.
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(new Date(iso));
}
