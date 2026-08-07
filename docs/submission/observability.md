# Observability

Row: `LLM-AC-15-OBSERVABILITY`. Prometheus + Grafana (metrics), Loki +
Grafana Explore (logs), Jaeger (traces) — each its own gateway-reachable
viewer route. GKE Cloud Logging/Monitoring disabled (see phase-03 Scope
Changes); scored via this stack instead.

Status: **not yet installed** — phase-04/07 work. Cluster/ingress/cert
platform is ready to host it (NetworkPolicy addon and NGINX Ingress class
already live).
