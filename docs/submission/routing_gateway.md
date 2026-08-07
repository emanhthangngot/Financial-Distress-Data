# Routing & Gateway (NGINX Ingress Controller)

Row: `LLM-AC-13-ROUTING`. F5 NGINX Ingress Controller OSS is the only
externally reachable object; every backend Service is `ClusterIP`.

- Public edge live at `https://distresslens.duckdns.org` — cert-manager +
  Let's Encrypt production certificate, verified 2026-08-08.
- Direct-backend-refused / routed-through-ingress-succeeds proof: **TBD
  phase-08**, once the real Web API and agent/MCP/chat routes exist
  (phase-06/07).

Status: ingress + HTTPS pipeline proven with a throwaway test Service;
evidence capture against the real services pending phase-06/07/08.
