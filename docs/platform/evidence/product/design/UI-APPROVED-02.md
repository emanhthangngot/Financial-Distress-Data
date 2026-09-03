# UI-APPROVED-02 — Company detail and AI analysis

![Approved company detail and AI analysis](UI-APPROVED-02.png)

- Route baseline: `/companies/[ticker]`; reusable AI interaction at
  `/agents/chat`.
- Preserve: company identity/watchlist action, risk KPI strip, trend chart,
  financial indicators, SHAP explanation, source/news list and AI analysis
  panel with citation IDs and tool trace.
- States to implement: agent selection, streaming, tool-running, citation,
  timeout, policy block, EKS-off and secret-safe error.
- Evolution allowed: improve panel composition and mobile stacking while
  keeping company-data and agent-chat authorization boundaries separate.
- Image SHA-256:
  `5d21bf24f74499f7487f762ff5194f1055fbbad274ad2ad03b2613897186f4f7`
