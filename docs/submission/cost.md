# Cost

Doubles as the row-67 (IaC) cost deliverable. GCP free-trial credit only —
**zero out-of-pocket spend**, target under USD 100 of the USD 300 available
(90-day trial, expires 2026-11-06).

- `make gcp-up` / `gcp-down` / `gcp-status` (`financial-distress-gitops/Makefile`)
  hibernate node pools when not actively working — the single largest cost
  lever (~USD 0.65-0.80/hr running vs ~USD 0.14/hr hibernated, per the plan's
  measured estimate on a peer project).
- Cloud Logging/Monitoring disabled cluster-wide (bills per GB; Loki/Grafana
  score the same rubric rows instead).
- Real spend and credit-usage screenshots: **TBD phase-08** — GCP billing
  usage reporting lags several hours behind actual resource creation, so
  this can't be captured meaningfully until near submission.

Status: cost levers implemented; actual spend report pending phase-08.
