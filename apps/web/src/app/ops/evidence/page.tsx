import type { CostProjection, OpsDashboard } from "@distresslens/contracts";
import { AbExperimentPanel } from "@/components/ops/ab-experiment-summary";
import { AuditTimeline } from "@/components/ops/audit-timeline";
import { CostGauge } from "@/components/ops/cost-gauge";
import { GitRevisionCard } from "@/components/ops/git-revision-card";
import { PipelineTable } from "@/components/ops/pipeline-table";
import { PromotionQueue } from "@/components/ops/promotion-queue";
import { RoleActionButton } from "@/components/ops/role-action-button";
import { SessionStateTimeline } from "@/components/ops/session-state-timeline";
import { AdminShell } from "@/components/shell/admin-shell";
import { ExternalLinkIcon } from "@/components/shell/icons";
import { PlaneStatusRow } from "@/components/shell/plane-status";
import { ButtonLink } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { StatePanel } from "@/components/ui/state-panel";
import { getDataPort } from "@/lib/data";
import { LIVE_FIXTURE_PROVENANCE } from "@/lib/data/fixtures/provenance-fixtures";
import { resolveSession } from "@/lib/server/session";
import { LOADING_COPY } from "@/lib/states/loading-copy";
import { isFailureState, viewCopy, viewData } from "@/lib/states/view-state";

/**
 * The evidence control room.
 *
 * A viewer inspects, an operator mutates lifecycle state, an admin promotes.
 * Every control on this page renders for every role and explains its own
 * denial, so an operator can see that promotion exists and that they may not do
 * it — hiding the control would make a missing permission look like a missing
 * feature. The server re-checks each action regardless of what this page drew.
 */

export const dynamic = "force-dynamic";

/**
 * What a new evidence session is expected to cost. Shown before provision so
 * the cap denial is visible in advance rather than discovered by a rejected
 * request.
 */
const SESSION_PROJECTION: CostProjection = {
  budgetLabel: "Chi phí AWS",
  projectedUsd: 12.5,
  basis: "2 giờ EKS + 1 GPU Vast",
  estimatedDurationMinutes: 120,
};

export default async function OpsEvidencePage() {
  const { user, context } = await resolveSession();
  const result = await getDataPort().getOpsDashboard(context);
  const data: OpsDashboard | null = viewData(result);
  const copy = viewCopy(result, LOADING_COPY.ops);
  const provenance = data?.provenance ?? LIVE_FIXTURE_PROVENANCE;
  const eksPlane = data?.planes.find((plane) => plane.component === "EKS_AI");

  return (
    <AdminShell
      user={user}
      provenance={provenance}
      syncedAtLabel="22/05/2025 18:32"
      environmentLabel={data?.environmentLabel ?? "AWS Evidence"}
      planeHealth={eksPlane?.health ?? "UNKNOWN"}
      desiredCommit={data?.revision.desiredRevision ?? "—"}
    >
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
          <div className="min-w-0">
            <h1 className="text-[28px]">Vận hành & Evidence</h1>
            <p className="mt-1 text-[15px] text-text-muted">
              Vòng đời phiên evidence, chi phí, trạng thái GitOps và lịch sử thao tác
            </p>
          </div>
        </div>

        {data === null ? (
          <StatePanel
            copy={copy ?? LOADING_COPY.ops}
            tone={isFailureState(result) ? "critical" : "neutral"}
            action={
              <ButtonLink href="/ops/evidence" variant="secondary">
                Tải lại bảng điều khiển
              </ButtonLink>
            }
          />
        ) : (
          <>
            {copy !== null ? (
              <StatePanel copy={copy} tone={isFailureState(result) ? "critical" : "warning"} />
            ) : null}

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
              <Card>
                <CardHeader
                  title="Tình trạng các mặt phẳng"
                  description="Web, Supabase và mặt phẳng suy luận EKS"
                />
                <CardBody>
                  <div className="flex flex-col divide-y divide-line-hairline">
                    {data.planes.map((plane) => (
                      <PlaneStatusRow key={plane.component} status={plane} />
                    ))}
                  </div>

                  <ul className="mt-4 flex flex-wrap gap-x-4 gap-y-2 border-t border-line-hairline pt-3 text-[13px]">
                    {data.observability.map((link) => (
                      <li key={link.label}>
                        {link.available ? (
                          <a
                            href={link.href}
                            rel="noreferrer noopener"
                            className="inline-flex items-center gap-1 font-medium text-primary-600 underline-offset-2 hover:underline"
                          >
                            {link.label}
                            <ExternalLinkIcon />
                          </a>
                        ) : (
                          <span
                            aria-disabled="true"
                            title="Mặt phẳng evidence đang ngoại tuyến"
                            className="text-text-muted"
                          >
                            {link.label} (ngoại tuyến)
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </CardBody>
              </Card>

              <Card>
                <CardHeader
                  title="Chi phí và hạn mức"
                  description="Chi phí dự kiến của một phiên evidence mới được cộng vào trước khi cấp phát"
                />
                <CardBody className="flex flex-col gap-5">
                  {data.budgets.map((budget) => (
                    <CostGauge
                      key={budget.label}
                      budget={budget}
                      projection={
                        budget.label === SESSION_PROJECTION.budgetLabel ? SESSION_PROJECTION : null
                      }
                    />
                  ))}
                </CardBody>
              </Card>
            </div>

            <Card>
              <CardHeader
                title="Phiên evidence"
                description="Vòng đời phiên và các thao tác được phép với vai trò hiện tại"
                action={
                  <div className="flex flex-wrap items-start gap-2">
                    <RoleActionButton
                      action="session.provision"
                      role={context.role}
                      aal={context.aal}
                      label="Tạo phiên evidence"
                      variant="primary"
                    />
                    {/* Destroy is never gated on the cost cap: blocking teardown
                        at the cap strands the session that is spending. */}
                    <RoleActionButton
                      action="session.destroy"
                      role={context.role}
                      aal={context.aal}
                      label="Hủy phiên"
                    />
                    <RoleActionButton
                      action="session.export_evidence"
                      role={context.role}
                      aal={context.aal}
                      label="Xuất evidence"
                    />
                  </div>
                }
              />
              <CardBody>
                <SessionStateTimeline session={data.session} />
                {data.nextSessionAt !== null ? (
                  <p className="mt-4 border-t border-line-hairline pt-3 text-[13px] text-text-muted">
                    Phiên tiếp theo dự kiến{" "}
                    <time dateTime={data.nextSessionAt} data-numeric className="font-mono">
                      {data.nextSessionAt.slice(0, 16).replace("T", " ")}
                    </time>
                  </p>
                ) : null}
              </CardBody>
            </Card>

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
              <Card>
                <CardHeader
                  title="Trạng thái GitOps"
                  description="Revision mong muốn trong Git so với revision đang chạy"
                  action={
                    <RoleActionButton
                      action="session.rollback"
                      role={context.role}
                      aal={context.aal}
                      label="Yêu cầu rollback"
                    />
                  }
                />
                <CardBody>
                  <GitRevisionCard revision={data.revision} />
                </CardBody>
              </Card>

              <Card>
                <CardHeader
                  title="Hàng đợi promotion"
                  description="Mô hình và agent đang chờ được đưa lên production"
                />
                <CardBody>
                  <PromotionQueue
                    promotions={data.promotions}
                    role={context.role}
                    aal={context.aal}
                  />
                </CardBody>
              </Card>
            </div>

            <Card>
              <CardHeader
                title="Pipeline"
                description="Các pipeline chạy trên revision hiện tại"
              />
              <CardBody>
                <PipelineTable pipelines={data.pipelines} />
              </CardBody>
            </Card>

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
              <Card>
                <CardHeader
                  title="Thử nghiệm A/B"
                  description="So sánh biến thể agent trong 24 giờ gần nhất"
                />
                <CardBody>
                  <AbExperimentPanel experiments={data.experiments} />
                </CardBody>
              </Card>

              <Card>
                <CardHeader
                  title="Lịch sử audit"
                  description="Thao tác đã ghi nhận, kèm kết quả"
                />
                <CardBody>
                  <AuditTimeline events={data.auditEvents} />
                </CardBody>
              </Card>
            </div>
          </>
        )}
      </div>
    </AdminShell>
  );
}
