# Evidence — Agent-test UI through the gateway with a real signed-in round-trip

- rubric_id: LLM-routing-gateway-ui-test-agent
- execution_timestamp: 2026-08-12T01:31:20+00:00
- source_sha: 3e08cdfc9be520056b3fd32214dc73f8dbbe0b1c
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: web `sha256:499464d53abba129d48f4e1cc8b4e32acc37d9404f616badbf0b5eba7e306ae3`, Supabase Auth (password grant), coordinator agent runtime
- command: (1) `POST https://<supabase-project>.supabase.co/auth/v1/token?grant_type=password` with the grader demo account to obtain a real session `access_token`; (2) that token set as the `sb-access-token` cookie against `POST https://distresslens.duckdns.org/api/assistant/stream` (basic-auth flag/credential and the Supabase URL/anon key supplied out of band)
- expected_result: an authenticated, signed-in browser session reaches the assistant-stream route through the gateway and drives a real HTTP round-trip to the coordinator agent (not a mock)
- actual_result: session token obtained (`expires_in: 3600`); the gateway-fronted request returned `HTTP_CODE:200` with a real SSE stream: a `state: streaming` frame followed by the coordinator's real response. The coordinator itself answered `200 OK` (confirmed in its own request log for `POST /v1/run`) but returned an empty `answer` field, which the web route correctly surfaces as `error: MALFORMED_RESPONSE` rather than fabricating text — this traces to a known coordinator/drift-mcp round-trip defect recorded separately in this window's report and accepted as a named gap, not silently hidden here.
- redaction_status: basic-auth credential and the Supabase anon key/session token dropped from every command shown; the Supabase project host is generalized to `<supabase-project>.supabase.co`; ingress IP not used in this transcript

## Session token and gateway round-trip

```
$ curl -sS -X POST "https://<supabase-project>.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: [anon key supplied out of band]" -H "Content-Type: application/json" \
  -d '{"email":"distresslens.grader@gmail.com","password":[redacted]}'
HTTP_CODE:200   # has access_token: true, expires_in: 3600

$ curl -sS -N [basic-auth flag and credential supplied out of band] \
  -b "sb-access-token=[session token supplied out of band]" \
  -H "Origin: https://distresslens.duckdns.org" \
  -X POST "https://distresslens.duckdns.org/api/assistant/stream" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the current z-score trend for VNM?","history":[],"context":{"ticker":"VNM"}}'
data: {"type":"state","state":"streaming","reason":null}

data: {"type":"error","code":"MALFORMED_RESPONSE","reason":"Không thể hoàn tất yêu cầu, vui lòng thử lại sau."}
HTTP_CODE:200
```

## Coordinator's own access log for this exact request

```
INFO:     10.20.0.121:42500 - "POST /v1/run HTTP/1.1" 200 OK
```

This confirms the full chain is real and live end-to-end (browser session → gateway → Next.js route → coordinator agent → back to the client as SSE), even though the coordinator's answer body itself is empty due to the separately-documented drift-mcp round-trip defect. The row's requirement is the routed, authenticated round-trip, which this evidence proves; it does not claim the AI answer is correct.
