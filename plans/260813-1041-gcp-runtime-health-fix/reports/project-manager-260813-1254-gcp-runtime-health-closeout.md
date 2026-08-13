# GCP runtime health fix closeout

## Status

| Plan | Status | Evidence | Residual |
|---|---|---|---|
| `260813-1041-gcp-runtime-health-fix` | Complete | Runtime + source + web gates pass | GHCR cold-node pull still needs user-supplied `read:packages` credential |

## Acceptance criteria

- ArgoCD `platform-agents` -> applies kagent CRDs -> `agents.kagent.dev` and
  `sandboxagents.kagent.dev` exist, `Established=True`, API-discoverable, and
  cluster ends at `13/13` apps `Synced/Healthy`.
- kagent controller -> reconciles installed API types -> controller ready and
  built-in Agents `Ready`.
- GitOps `phase2-data/web` -> serves runtime path without orphan regression ->
  cluster healthy after fix; no open evidence of the broken orphan state
  remaining.
- OTLP/telemetry path -> stays live through the fix -> Grafana MCP reconciled,
  controller registered `65` tools, direct MCP initialize probe returns HTTP
  `200`.
- SealedSecret controller -> unseals the active Grafana token -> condition
  `Synced=True`; PR `#65` corrected the intermediate ciphertext that used a
  stale cached controller certificate.
- Validation gates -> run after the fix -> `scripts/run_phase2_e2e.py` PASS
  `28/28`; source gate PASS (`311` pytest + `ruff` + `black` + `docker compose config`
  + Stage 1 evidence audit); prior web checks PASS (`184` tests, typecheck/lint,
  live e2e `6`, assistant e2e `6`).
- Secret handling -> avoids plaintext Git exposure -> `ghcr-pull-secret`
  placeholder remains excluded/invalid; required package-pull credential stays
  out-of-band.

## Final live closeout

- ArgoCD -> evaluates every managed application -> `13/13 Synced/Healthy`.
- kagent controller -> registers Grafana MCP -> `Accepted=True`, `65` tools,
  and no new `Forbidden`, rest-mapping, crash-loop, or panic errors in the
  final five-minute log window.
- Temporary token-creator pods -> finish credential rotation -> deleted; two
  obsolete Grafana Viewer service accounts were removed, leaving only the
  active account for the sealed runtime Secret.

## Scope sync

- Updated: plan status and closeout tracking only.
- Not changed: source repo code, GitOps manifests, generated evidence, secrets.
- Task tools: unavailable in this session; tracking synced directly in plan
  files.

## Risks / residuals

- Open: GHCR web image uses a private digest. Current node cache keeps service
  up; a cold-node reschedule can fail image pull until the user provides a
  sealed `read:packages` credential.
- Impact: runtime-health fix is complete now, but node replacement is not fully
  self-healing for web.
- Unblock path: user supplies package-read credential out-of-band; operator
  seals/applies it in the GitOps repo; rerun cold-node pull check.

## Next actions

1. Main agent -> complete the implementation plan bookkeeping everywhere this
   fix is referenced -> no stale in-progress status remains.
2. User/operator -> provide sealed GHCR `read:packages` credential -> cold-node
   pull path becomes recoverable.
3. Main agent -> keep the residual visible in successor/runtime reports ->
   do not let this slip before final submission.

## Unresolved questions

- None for plan closure. Residual credential dependency is known and recorded.

Status: DONE_WITH_CONCERNS
