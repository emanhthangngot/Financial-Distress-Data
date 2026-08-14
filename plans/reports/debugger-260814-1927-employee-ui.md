# Debug report — employee UI smoke

Date: 2026-08-14 (Asia/Ho_Chi_Minh)

## Identity and access

The live forwarded DistressLens UI was opened at `http://127.0.0.1:18090/sign-in` and signed in with the repository's disposable smoke-operator test identity. The session resolved as `platform_operator`, displayed as `Smoke Operator / Nền tảng — vận hành`, and did not expose credentials.

## Passed employee flows

- `/` loaded the authenticated shell and current revision/provenance banner.
- `/ops/evidence` rendered `Vận hành & Evidence`.
- Platform status showed Web, Supabase, and EKS AI as `Trực tuyến`.
- Cost/limit cards rendered.
- Pipeline table rendered six pipeline rows with status and evidence links.
- A/B experiment table and audit history rendered.
- `/agents/registry` rendered the live agent registry with feature-agent, drift-agent, and coordinator entries plus egress policies.
- Network document/RSC requests returned `200`; browser console and page-error checks were empty.

## Authorization checks

The employee is AAL1/password-only, so mutation controls were correctly disabled:

- `Tạo phiên evidence`, `Hủy phiên`, `Xuất evidence`
- `Yêu cầu rollback`
- promotion controls on the agent registry

The UI explicitly explained that the current role cannot perform `session.promote`. This is expected fail-closed behavior, not a UI regression.

Analyst-only routes were also checked under the same employee session:

- `/companies`: denied with the analyst-role message.
- `/reports`: denied for saved reports.
- `/compare`: denied for model comparison.

This confirms separation between platform-operator operations and analyst data access.

## Evidence

- [Employee operations UI](ui-260814-1927-employee-ops.png)
- [Employee agent registry](ui-260814-1927-employee-registry.png)

The same employee route was also opened in the requested existing Chrome profile. Because the profile bridge is unavailable, the route's authenticated state could not be read back from that headful tab; the authenticated smoke session above is the source of the UI assertions.

## Remaining limitation

This test used the live service through the existing local port-forward/browser smoke session. The user's real Chrome profile tabs remain open, but the Chrome DevTools bridge still cannot read headful tabs because the runtime reports a missing X server. A separate analyst-role identity is required to test company/report/model-analysis flows as an employee analyst; the available smoke identity is intentionally a platform operator.
