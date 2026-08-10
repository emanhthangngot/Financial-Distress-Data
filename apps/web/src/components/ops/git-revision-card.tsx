import { isGitOpsDrifted, type ArgoSyncHealth, type GitRevisionCardData } from "@distresslens/contracts";
import { ExternalLinkIcon } from "@/components/shell/icons";

/**
 * Desired versus live GitOps revision.
 *
 * Drift is the single fact this card exists to surface: when the two SHAs
 * differ, the cluster is not running what the repository says it should, and
 * every other number on the operations page describes a state nobody declared.
 * It is called out in words above the SHAs rather than left for the reader to
 * diff two hashes by eye.
 */

const HEALTH_LABEL: Record<ArgoSyncHealth, string> = {
  HEALTHY: "Khỏe mạnh",
  PROGRESSING: "Đang tiến hành",
  DEGRADED: "Suy giảm",
  UNKNOWN: "Không xác định",
};

const HEALTH_TONE: Record<ArgoSyncHealth, string> = {
  HEALTHY: "border-risk-stable-fill/35 bg-risk-stable-soft text-risk-stable-ink",
  PROGRESSING: "border-primary-600/30 bg-primary-050 text-ink-900",
  DEGRADED: "border-risk-watch-fill/35 bg-risk-watch-soft text-risk-watch-ink",
  UNKNOWN: "border-line-strong bg-paper-2 text-text-muted",
};

export function GitRevisionCard({ revision }: { revision: GitRevisionCardData }) {
  const drifted = isGitOpsDrifted(revision);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded-sm border px-2 py-1 text-[12px] font-medium ${HEALTH_TONE[revision.syncHealth]}`}
        >
          Argo: {HEALTH_LABEL[revision.syncHealth]}
        </span>
        {drifted ? (
          <span className="rounded-sm border border-risk-watch-fill/35 bg-risk-watch-soft px-2 py-1 text-[12px] font-medium text-risk-watch-ink">
            Desired và live đang lệch nhau
          </span>
        ) : null}
      </div>

      <dl className="grid grid-cols-1 gap-2 text-[13px] sm:grid-cols-2">
        <Revision label="Desired" sha={revision.desiredRevision} branch={revision.desiredBranch} />
        <Revision label="Live" sha={revision.liveRevision} branch={revision.liveBranch} />
      </dl>

      <p className="text-[12px] text-text-muted">
        Đồng bộ lần cuối{" "}
        <time dateTime={revision.lastSyncedAt} data-numeric className="font-mono">
          {formatTimestamp(revision.lastSyncedAt)}
        </time>
      </p>

      <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-[13px]">
        <li>
          <RepoLink href={revision.appRepoUrl} label="Repo ứng dụng" />
        </li>
        <li>
          <RepoLink href={revision.gitopsRepoUrl} label="Repo GitOps" />
        </li>
      </ul>
    </div>
  );
}

function Revision({ label, sha, branch }: { label: string; sha: string; branch: string }) {
  return (
    <div className="rounded-md border border-line-hairline bg-paper-1 px-3 py-2">
      <dt className="text-[12px] uppercase tracking-[0.06em] text-text-muted">{label}</dt>
      <dd className="mt-0.5 font-mono text-[14px] font-semibold text-text-strong">{sha}</dd>
      <dd className="font-mono text-[12px] text-text-muted">{branch}</dd>
    </div>
  );
}

function RepoLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      rel="noreferrer noopener"
      target="_blank"
      className="inline-flex items-center gap-1 font-medium text-primary-600 underline-offset-2 hover:underline"
    >
      {label}
      <ExternalLinkIcon />
      <span className="sr-only">(mở tab mới)</span>
    </a>
  );
}

function formatTimestamp(iso: string): string {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(new Date(iso));
}
