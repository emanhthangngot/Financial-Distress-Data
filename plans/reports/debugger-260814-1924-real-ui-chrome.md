# Debug report — GCP real UI / Chrome profile

Date: 2026-08-14 (Asia/Ho_Chi_Minh)

## Scope

Verify the running GCP evidence platform through two UI tabs: kagent and the DistressLens web UI. The requested browser path was the existing Chrome profile that has the ChatGPT extension; no credentials were copied or exposed.

## Environment

- GCP project: `project-60655616-d84a-4883-867`
- GKE context: `gke_project-60655616-d84a-4883-867_asia-southeast1-b_fsds-evidence`
- One primary node: `Ready`
- Argo CD: 13/13 applications `Synced` and `Healthy`
- kagent UI service: `ClusterIP`, exposed locally with port-forward `127.0.0.1:18082`
- DistressLens web service: exposed locally at `127.0.0.1:18090`
- Local endpoint probes: kagent `200`, web `200`
- Public ingress probe: `401` (Basic Auth challenge; credentials were intentionally not retrieved)

The cluster was already running, so no GCP start/stop, resize, or quota mutation was performed.

## Chrome profile result

The existing Chrome profile was resolved with `chrome-profile`, and two tabs were opened with the profile-aware URL anchors:

1. kagent: `http://127.0.0.1:18082/`
2. DistressLens: `http://127.0.0.1:18090/`

The Chrome DevTools MCP live probe was attempted as required by the profile skill. It failed before page listing with:

`Missing X server to start the headful browser. Either set headless to true or use xvfb-run to run your Puppeteer script.`

Therefore, the tabs are open in the user's Chrome profile, but this session cannot read them through the DevTools bridge. The UI smoke evidence below was collected with a separate local browser session against the same live forwarded services; it does not claim to be an extension-profile readback.

## Real UI smoke results

### kagent

- Initial wizard was skipped.
- The `Agents` page rendered successfully.
- Ten agents were visible across namespaces, including `k8s-agent`, `helm-agent`, `observability-agent`, `promql-agent`, and the Argo Rollouts converter.
- Console and page-error checks were empty.
- Network requests to the kagent page and agent chat resources returned `200`.

Screenshot: [kagent UI](ui-260814-1915-kagent.png)

### DistressLens

- The dashboard rendered with Vietnamese navigation, status indicator, data version, model version, and the `Mở trợ lý phân tích` control.
- The `Doanh nghiệp` navigation interaction reached `/companies` successfully.
- Search input interaction was exercised with `VNM`.
- The page correctly displayed the authorization guard: `Tài khoản hiện tại không được phép tra cứu doanh nghiệp.`
- No application error overlay was observed.

Screenshots: [dashboard](ui-260814-1915-web.png), [companies guard](ui-260814-1915-web-companies-vnm.png)

## Diagnosis

The GCP services and both UIs are reachable. The missing company result is an authorization-state outcome, not a rendering or routing failure. The remaining blocker for direct inspection of the user's actual Chrome tabs is the headful DevTools bridge's missing X server.

## Follow-up needed for full live evidence

- Provide/activate the existing analyst-authenticated session in Chrome (without sending credentials in chat) to exercise company lookup and analyst-only flows.
- Run the Chrome DevTools MCP runtime with a working display/bridge, then re-bind the two profile tabs and collect profile-tab screenshots directly.
- Public-domain checks require the existing Basic Auth mechanism; this run deliberately did not bypass it.

