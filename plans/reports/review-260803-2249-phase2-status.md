# platform .eview — Status Report (2026-08-03, local, uncommitted)

## Verdict

**platform .hưa hoàn thành. Checklist KHÔNG tick** — chỉ mới xong phần foundation (DB/auth layer), chưa có product shell (UI) như tiêu đề phase yêu cầu.

Plan status field hiện: `status: todo` — giữ nguyên, đúng thực tế.

## Evidence

### Đã có (commit `5472c98`, "product shell foundation")

| Item | File | Note |
|---|---|---|
| Supabase schema + RLS migration | `supabase/migrations/20260803214500_phase2_schema.sql`, `..._phase2_rls.sql` | RBAC roles + AAL2 enforced tại DB layer |
| Session state machine contract | `packages/contracts/src/session-state.ts`, `session-transitions.json` | OFF→...→DESTROYING + FAILED/EXPIRED, single source of truth |
| Role/RBAC contract | `packages/contracts/src/role.ts` | analyst/platform_viewer/operator/admin |
| Outbox event type | `packages/contracts/src/outbox-event.ts` | type only, chưa có worker/consumer |
| RLS/RBAC test suite | `tests/platform/product/test_rbac_rls.py` | 19 pytest case, real ephemeral Postgres |
| Contract vitest | `packages/contracts/src/*.test.ts` | |
| CI job | `.github/workflows/ci.yml` | contracts job + Postgres binaries |
| Next.js scaffold | `apps/web/` (pnpm workspace) | **default `create-next-app` template, chưa sửa** |

### Chưa có (Requirements + Success Criteria của phase-02)

- Analyst pages (company search, risk snapshot, model explanation, RAG answer, comparison, saved report, data freshness) — không tồn tại, `page.tsx` vẫn là boilerplate Vercel template.
- Agent chat UI / agent registry UI — không có route nào ngoài `apps/web/src/app`.
- Admin surfaces (session timeline, cost, GitOps revision, health, evidence export, promotion, rollback, teardown UI) — không có.
- Fixed disclaimer ("educational coursework, not investment advice") — grep toàn repo không match, chưa render ở đâu.
- `docs/platform/product.md`, `docs/platform/security/rbac.md`, `docs/platform/evidence/product/` — không tồn tại (Files section của phase-02 yêu cầu tạo).
- Playwright flows (analyst/viewer/operator/admin/EKS-off/cost-cap/fencing/chat/registry) — không có Playwright test project trong repo (chỉ `.venv` chứa lib Playwright do dependency khác).
- Outbox worker (claim leases, reject stale fencing token) — chỉ có TS type, chưa có consumer process.
- Preflight cost projection UI, rate limit/AI quota enforcement tại product boundary — chưa implement.
- Accessibility checks, deterministic screenshot fixtures — chưa có.

### Kết luận theo Success Criteria (phase-02)

Tất cả 5 success criteria đều cần UI/E2E flow (Playwright) để verify — hiện tại không có UI thật nên không thể chứng minh criteria nào đạt. 0/5 tick được.

## platform .`phase-01-start.md`) — tham chiếu nhanh

Đã đóng, checklist tick đủ, qua 3 vòng review (Session 1-3), status `in_review`. Không phải phần review yêu cầu lần này nhưng đối chiếu để xác nhận platform .uild đúng trên nền spec đã lock (rubric matrix, ADR, class contracts) — không phát hiện lệch spec ở phần đã làm của Phase 2.

## Đề xuất

Giữ `status: todo` cho phase-02, không tick bất kỳ checkbox nào. Việc còn lại: toàn bộ UI (analyst/admin/agent surfaces), disclaimer, outbox worker, docs 2 file còn thiếu, Playwright suite.

## Unresolved questions

- Không có.
