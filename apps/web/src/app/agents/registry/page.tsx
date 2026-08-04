import type { AgentRegistryView } from "@distresslens/contracts";
import { AgentRegistryList } from "@/components/ops/agent-registry-list";
import { AdminShell } from "@/components/shell/admin-shell";
import { ButtonLink } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { StatePanel } from "@/components/ui/state-panel";
import { getDataPort } from "@/lib/data";
import { LIVE_FIXTURE_PROVENANCE } from "@/lib/data/fixtures/provenance-fixtures";
import { resolveSession } from "@/lib/server/session";
import { LOADING_COPY } from "@/lib/states/loading-copy";
import { isFailureState, viewCopy, viewData } from "@/lib/states/view-state";

/**
 * Agent governance.
 *
 * A separate route from the operations control room and from the analyst
 * assistant: reading which agents exist and what they may reach is a platform
 * question, and mixing it into either of the other two would blur the
 * authorization boundary the registry exists to document.
 */

export const dynamic = "force-dynamic";

export default async function AgentRegistryPage() {
  const { user, context } = await resolveSession();
  const result = await getDataPort().getAgentRegistry(context);
  const data: AgentRegistryView | null = viewData(result);
  const copy = viewCopy(result, LOADING_COPY.registry);
  const provenance = data?.provenance ?? LIVE_FIXTURE_PROVENANCE;

  return (
    <AdminShell
      user={user}
      provenance={provenance}
      syncedAtLabel="22/05/2025 18:32"
      environmentLabel="AWS Evidence"
      planeHealth={context.planeReady ? "ONLINE" : "OFFLINE"}
      desiredCommit={provenance.gitopsSha ?? "—"}
    >
      <div className="flex flex-col gap-5">
        <div className="min-w-0">
          <h1 className="text-[28px]">Sổ đăng ký agent</h1>
          <p className="mt-1 text-[15px] text-text-muted">
            Phiên bản agent đã đăng ký, chính sách sandbox và số bản sao đang chạy
          </p>
        </div>

        {data === null ? (
          <StatePanel
            copy={copy ?? LOADING_COPY.registry}
            tone={isFailureState(result) ? "critical" : "neutral"}
            action={
              <ButtonLink href="/ops/evidence" variant="secondary">
                Về trung tâm vận hành
              </ButtonLink>
            }
          />
        ) : (
          <>
            {copy !== null ? (
              <StatePanel copy={copy} tone={isFailureState(result) ? "critical" : "warning"} />
            ) : null}

            <Card>
              <CardHeader
                title="Agent đã đăng ký"
                description={`${data.entries.length} phiên bản trong môi trường hiện tại`}
              />
              <CardBody>
                <AgentRegistryList
                  entries={data.entries}
                  role={context.role}
                  aal={context.aal}
                  replicaCountsKnown={context.planeReady}
                />
              </CardBody>
            </Card>
          </>
        )}
      </div>
    </AdminShell>
  );
}
