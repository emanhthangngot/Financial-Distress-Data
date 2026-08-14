# Debug report — analyst AI assistant

Date: 2026-08-14 (Asia/Ho_Chi_Minh)

## Access decision

The live Supabase project contains one analyst profile, but its identity is not a synthetic test identity and no analyst credentials were supplied. I did not reset a password, generate an impersonation link, or modify that account. The repository's supported fixture mode was used instead: `DISTRESSLENS_DATA_SOURCE=fixture`, `DISTRESSLENS_FIXTURE_ROLE=analyst`, AAL2, plane on, with the repository fake inference upstream.

## Automated UI gate

Command:

```text
pnpm --filter @distresslens/web e2e:assistant
```

Result: **6 passed**.

Covered branches:

- streamed answer renders as a complete assistant turn;
- timeout state and retry guidance;
- policy refusal state;
- malformed upstream response without leaking raw content;
- cancel control while a request is pending;
- no inference token or URL rendered in the thread.

## Manual browser verification

Fixture analyst dashboard: `http://127.0.0.1:3212/`

The same fixture analyst dashboard is now open in the requested Chrome profile at `http://127.0.0.1:3212/` for direct visual follow-up. The local fake upstream and fixture server are intentionally kept running for this inspection session.

1. Opened `Trợ lý phân tích` from the analyst dashboard.
2. Clicked the quick action `Giải thích nhóm nguy cơ cao`.
3. Received `NVL rủi ro thanh khoản`.
4. Submitted the typed question `Vì sao NVL có nguy cơ cao?`.
5. Received a second completed assistant turn with the same deterministic answer.
6. Verified the disclaimer remained visible and no `sk-*`, bearer, API-key, or fake token pattern appeared in the rendered text.
7. Browser console and page-error checks were empty.
8. Both assistant POST requests returned HTTP `200`.

Evidence:

- [Analyst AI completed turn](ui-260814-1933-analyst-ai-complete.png)
- [Analyst AI typed question](ui-260814-1933-analyst-ai-typed.png)

## Diagnosis / limitation

The analyst UI and AI transport are working under the deterministic evidence configuration. This is not proof of a live model response from the GCP inference plane: the live analyst session cannot be established without an authorized analyst login, and the real Chrome DevTools bridge still cannot read headful tabs because the runtime lacks an X server. Once an authorized analyst session is available, repeat the same two questions against the live web tab and capture the live provenance/model version.
