"""Configuration for server-side Phase 2 HTTP transports."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import httpx

from src.observability.telemetry import inject_trace_headers

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def absolute_http_url(raw: str | None) -> str | None:
    """Keep credentials out of URLs and reject malformed endpoints before I/O."""
    if not raw or re.search(r"[\s\x00-\x1f\x7f\\?#]", raw):
        return None
    try:
        parsed = urlsplit(raw)
        if (
            parsed.scheme in {"http", "https"}
            and parsed.hostname
            and parsed.username is None
            and "%" not in parsed.netloc
            and not parsed.netloc.endswith(":")
            and parsed.password is None
            and parsed.port != 0
        ):
            httpx.URL(raw)
            return raw
    except (ValueError, httpx.InvalidURL):
        pass
    return None


@dataclass(frozen=True)
class HttpEndpoint:
    url: str
    token: str | None = field(default=None, repr=False)

    @classmethod
    def from_env(cls, url_key: str, token_key: str) -> HttpEndpoint | None:
        url = absolute_http_url(os.getenv(url_key))
        token = os.getenv(token_key) or None
        if url is None or (token is not None and not re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", token)):
            return None
        parsed = urlsplit(url)
        if token and parsed.scheme != "https" and parsed.hostname not in _LOOPBACK_HOSTS:
            return None
        return cls(url, token)

    @property
    def origin(self) -> tuple[str, str | None, int]:
        parsed = urlsplit(self.url)
        default_port = 443 if parsed.scheme == "https" else 80
        return parsed.scheme, parsed.hostname, parsed.port or default_port

    @property
    def trust_env(self) -> bool:
        """Never proxy a plaintext bearer; preserve configured TLS trust for HTTPS."""
        return not (self.token and self.origin[0] == "http")

    def at(self, path: str) -> HttpEndpoint:
        return HttpEndpoint(self.url.rstrip("/") + path, self.token)

    def headers(self) -> dict[str, str]:
        return inject_trace_headers({"Authorization": f"Bearer {self.token}"} if self.token else {})


async def reject_redirect(response: httpx.Response) -> None:
    if response.is_redirect:
        raise httpx.HTTPError("upstream_redirect_rejected")


async def endpoint_ready(client: httpx.AsyncClient, endpoint: HttpEndpoint) -> bool:
    """Probe a ready endpoint without leaking response or redirect details."""
    try:
        response = await client.get(endpoint.url, headers=endpoint.headers(), timeout=2.0)
        return response.is_success
    except (httpx.HTTPError, httpx.InvalidURL):
        return False


def mcp_allowed_hosts() -> list[str]:
    """Maintain DNS-rebinding protection; allow only loopback and configured hosts."""
    configured = os.getenv("MCP_ALLOWED_HOSTS", "").split(",")
    return ["127.0.0.1:*", "localhost:*", *(host.strip() for host in configured if host.strip())]
