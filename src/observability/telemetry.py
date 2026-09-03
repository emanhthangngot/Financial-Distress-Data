"""Small, safe telemetry layer shared by the platform .TTP, MCP and agents.

The module deliberately does not configure exporters, open sockets, or create
network clients at import time.  Prometheus and OpenTelemetry are optional:
the application gets valid Prometheus text exposition and redaction/context
helpers even in the repository's dependency-light test environment.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

try:  # pragma: no cover - availability is environment-dependent
    from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest
    from prometheus_client.exposition import CONTENT_TYPE_LATEST

    _PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised by dependency-light fallback tests
    CollectorRegistry = Counter = Gauge = Histogram = generate_latest = None  # type: ignore[assignment]
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
    _PROMETHEUS_AVAILABLE = False

try:  # pragma: no cover - availability is environment-dependent
    from opentelemetry import propagate as _otel_propagate
    from opentelemetry import trace as _otel_trace
    from opentelemetry.trace import Status, StatusCode

    _OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised by dependency-light fallback tests
    _otel_propagate = _otel_trace = Status = StatusCode = None  # type: ignore[assignment]
    _OTEL_AVAILABLE = False

try:  # pragma: no cover - availability is environment-dependent
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    _OTEL_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - dependency-light test environment
    OTLPSpanExporter = Resource = TracerProvider = BatchSpanProcessor = None  # type: ignore[assignment]
    _OTEL_SDK_AVAILABLE = False


_SENSITIVE_FIELD_RE = re.compile(
    r"(?:prompt|document|chunk[_-]?text|raw[_-]?output|model[_-]?output|completion|"
    r"credential|password|secret|api[_-]?key|authorization|bearer|private[_-]?key|"
    r"access[_-]?token|refresh[_-]?token|pii|email|phone|national[_-]?id)",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\s.\-]?){8,15}(?!\d)")
_JWT_RE = re.compile(r"\b eyJ[\w-]+\.[\w-]+\.[\w-]+ \b", re.IGNORECASE | re.VERBOSE)
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[^\s,;]+")
_PEM_RE = re.compile(r"-----BEGIN [^-]+-----.*?-----END [^-]+-----", re.IGNORECASE | re.DOTALL)
_KEY_RE = re.compile(r"(?i)\b(?:sk|pk|ghp|glpat|xox[baprs])-[-_A-Za-z0-9]{8,}\b")
_SENSITIVE_VALUE_RE = re.compile(
    r"(?i)\b(prompt|document|chunk[_-]?text|raw[_-]?output|model[_-]?output|"
    r"completion|credential|password|secret|api[_-]?key|authorization|bearer|"
    r"private[_-]?key|access[_-]?token|refresh[_-]?token|pii)\s*[:=]\s*"
    r"(?:\"[^\"]*\"|'[^']*'|[^,;\n}]+)"
)
_SAFE_ID_FIELDS = {
    "request_id",
    "correlation_id",
    "release_id",
    "session_id",
    "trace_id",
    "span_id",
    "operation",
    "service",
    "route",
    "method",
    "status",
    "agent",
    "agent_identity",
    "tool",
    "finding_type",
}

_OTEL_PROVIDER_CONFIGURED = False


def _configure_otel_exporter(service: str) -> None:
    """Configure an OTLP exporter only when deployment supplies an endpoint."""

    global _OTEL_PROVIDER_CONFIGURED
    if _OTEL_PROVIDER_CONFIGURED or not (_OTEL_AVAILABLE and _OTEL_SDK_AVAILABLE):
        return
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    try:
        resource = Resource.create(
            {
                "service.name": service,
                "service.version": os.getenv("RELEASE_ID", "unknown"),
            }
        )
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=endpoint,
                    insecure=os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "false").lower()
                    in {"1", "true", "yes"},
                )
            )
        )
        _otel_trace.set_tracer_provider(provider)
        _OTEL_PROVIDER_CONFIGURED = True
    except Exception:
        # Telemetry must never prevent the business process from starting.
        return


def pii_finding_types(value: str) -> tuple[str, ...]:
    """Return PII categories without ever returning the matched values."""

    try:
        from src.llm.data_governance import detect_pii

        return tuple(finding.finding_type for finding in detect_pii(value))
    except (ImportError, AttributeError):
        findings: list[str] = []
        if _EMAIL_RE.search(value):
            findings.append("email")
        if _PHONE_RE.search(value):
            findings.append("phone")
        return tuple(findings)


def _field_is_sensitive(field_name: str | None) -> bool:
    return bool(field_name and _SENSITIVE_FIELD_RE.search(field_name))


def redact_text(value: str) -> str:
    """Remove credentials and common PII from free-form telemetry text."""

    redacted = _PEM_RE.sub("[redacted]", value)
    redacted = _SENSITIVE_VALUE_RE.sub(lambda match: f"{match.group(1)}=[redacted]", redacted)
    redacted = _BEARER_RE.sub("Bearer [redacted]", redacted)
    redacted = _JWT_RE.sub("[redacted]", redacted)
    redacted = _KEY_RE.sub("[redacted]", redacted)
    redacted = _EMAIL_RE.sub("[redacted:email]", redacted)
    redacted = _PHONE_RE.sub("[redacted:phone]", redacted)
    return redacted


def redact_value(value: Any, field_name: str | None = None) -> Any:
    """Recursively redact telemetry values while preserving correlation IDs."""

    if field_name and field_name.lower() in _SAFE_ID_FIELDS and isinstance(value, str):
        return value[:128]
    if _field_is_sensitive(field_name) and (field_name or "").lower() not in _SAFE_ID_FIELDS:
        return "[redacted]"
    if isinstance(value, Mapping):
        return {str(key): redact_value(item, str(key)) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [redact_value(item, field_name) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def redact_fields(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): redact_value(value, str(key)) for key, value in fields.items()}


def _label(value: Any, default: str = "unknown") -> str:
    text = redact_text(str(value or default)).strip()
    return text[:128] or default


def safe_error(error: Any) -> str:
    return redact_text(str(error))[:256] or "unknown_error"


@dataclass(frozen=True)
class RequestMetadata:
    request_id: str = "unknown"
    correlation_id: str = "unknown"
    release_id: str = "unknown"
    session_id: str = "unknown"

    def as_attributes(self) -> dict[str, str]:
        return {
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "release_id": self.release_id,
            "session_id": self.session_id,
        }


def metadata_from_headers(headers: Mapping[str, str] | None = None) -> RequestMetadata:
    headers = headers or {}
    lower = {str(key).lower(): str(value) for key, value in headers.items()}

    def get(name: str, env_name: str) -> str:
        value = str(lower.get(name) or os.getenv(env_name) or "unknown").strip()
        return value[:128] or "unknown"

    return RequestMetadata(
        request_id=get("x-request-id", "REQUEST_ID"),
        correlation_id=get("x-correlation-id", "CORRELATION_ID"),
        release_id=get("x-release-id", "RELEASE_ID"),
        session_id=get("x-session-id", "SESSION_ID"),
    )


def inject_trace_headers(headers: Mapping[str, str] | None = None) -> dict[str, str]:
    """Inject the current W3C trace context without making telemetry required."""

    carrier = {str(key): str(value) for key, value in (headers or {}).items()}
    if _OTEL_AVAILABLE:
        try:
            _otel_propagate.inject(carrier)
        except Exception:
            pass
    return carrier


def _extract_context(headers: Mapping[str, str] | None) -> Any:
    if not _OTEL_AVAILABLE or not headers:
        return None
    try:
        return _otel_propagate.extract(dict(headers))
    except Exception:
        return None


@contextmanager
def trace_span(
    name: str,
    attributes: Mapping[str, Any] | None = None,
    *,
    service: str = "financial-distress",
    headers: Mapping[str, str] | None = None,
) -> Iterator[Any]:
    """Create a redaction-safe span and optionally attach an inbound parent."""

    if not _OTEL_AVAILABLE:
        yield None
        return

    parent = _extract_context(headers)
    try:
        from opentelemetry import context as _otel_context
    except ImportError:  # pragma: no cover - guarded by _OTEL_AVAILABLE
        _otel_context = None
    token = _otel_context.attach(parent) if parent is not None and _otel_context else None
    try:
        tracer = _otel_trace.get_tracer("financial-distress.observability")
        with tracer.start_as_current_span(_label(name, "operation")) as span:
            safe_attributes = redact_fields({"service": service, **(attributes or {})})
            for key, value in safe_attributes.items():
                if isinstance(value, (str, bool, int, float)):
                    span.set_attribute(str(key), value)
                else:
                    span.set_attribute(str(key), json.dumps(value, sort_keys=True))
            try:
                yield span
            except Exception as exc:
                # Raw exception events may contain prompt/document content;
                # retain only a type and a redacted status description.
                try:
                    span.set_attribute("exception.type", type(exc).__name__)
                    span.set_status(Status(StatusCode.ERROR, safe_error(exc)))
                except Exception:
                    pass
                raise
    finally:
        if token is not None:
            if _otel_context is not None:
                _otel_context.detach(token)


_current_telemetry: ContextVar[Telemetry | NoopTelemetry | None] = ContextVar(
    "phase2_telemetry", default=None
)


@contextmanager
def use_telemetry(telemetry: Telemetry | NoopTelemetry) -> Iterator[Telemetry | NoopTelemetry]:
    token = _current_telemetry.set(telemetry)
    try:
        yield telemetry
    finally:
        _current_telemetry.reset(token)


def current_telemetry() -> Telemetry | NoopTelemetry:
    return _current_telemetry.get() or _NOOP_TELEMETRY


class _FallbackChild:
    def __init__(self, metric: _FallbackMetric, labels: tuple[tuple[str, str], ...]) -> None:
        self.metric = metric
        self.labels = labels

    def inc(self, amount: float = 1.0) -> None:
        self.metric._values[self.labels] = self.metric._values.get(self.labels, 0.0) + amount

    def dec(self, amount: float = 1.0) -> None:
        self.inc(-amount)

    def set(self, value: float) -> None:
        self.metric._values[self.labels] = value

    def observe(self, value: float) -> None:
        self.metric._observations.setdefault(self.labels, []).append(value)


class _FallbackMetric:
    def __init__(
        self,
        registry: _FallbackRegistry,
        name: str,
        help_text: str,
        metric_type: str,
        label_names: tuple[str, ...],
    ) -> None:
        self.registry = registry
        self.name = name
        self.help_text = help_text
        self.metric_type = metric_type
        self.label_names = label_names
        self._values: dict[tuple[tuple[str, str], ...], float] = {}
        self._observations: dict[tuple[tuple[str, str], ...], list[float]] = {}
        registry.metrics.append(self)

    def labels(self, **labels: str) -> _FallbackChild:
        key = tuple((name, _label(labels.get(name))) for name in self.label_names)
        return _FallbackChild(self, key)


class _FallbackRegistry:
    def __init__(self) -> None:
        self.metrics: list[_FallbackMetric] = []

    def metric(
        self,
        name: str,
        help_text: str,
        metric_type: str,
        label_names: tuple[str, ...],
    ) -> _FallbackMetric:
        return _FallbackMetric(self, name, help_text, metric_type, label_names)

    @staticmethod
    def _labels(labels: tuple[tuple[str, str], ...], extra: tuple[str, str] | None = None) -> str:
        values = dict(labels)
        if extra is not None:
            values[extra[0]] = extra[1]
        if not values:
            return ""
        escaped = {
            key: value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            for key, value in values.items()
        }
        return "{" + ",".join(f'{key}="{escaped[key]}"' for key in sorted(escaped)) + "}"

    def render(self) -> bytes:
        lines: list[str] = []
        for metric in self.metrics:
            lines.append(f"# HELP {metric.name} {metric.help_text}")
            lines.append(f"# TYPE {metric.name} {metric.metric_type}")
            for labels, value in sorted(metric._values.items()):
                lines.append(f"{metric.name}{self._labels(labels)} {value}")
            if metric.metric_type == "histogram":
                for labels, observations in sorted(metric._observations.items()):
                    for boundary in (0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, float("inf")):
                        count = sum(value <= boundary for value in observations)
                        bound = "+Inf" if boundary == float("inf") else str(boundary)
                        lines.append(
                            f"{metric.name}_bucket{self._labels(labels, ('le', bound))} {count}"
                        )
                    lines.append(f"{metric.name}_count{self._labels(labels)} {len(observations)}")
                    lines.append(f"{metric.name}_sum{self._labels(labels)} {sum(observations)}")
        return ("\n".join(lines) + "\n").encode()


def _metric(
    registry: Any,
    kind: str,
    name: str,
    help_text: str,
    labels: tuple[str, ...],
) -> Any:
    if _PROMETHEUS_AVAILABLE:
        constructor = {"counter": Counter, "histogram": Histogram, "gauge": Gauge}[kind]
        return constructor(name, help_text, labels, registry=registry)
    return registry.metric(name, help_text, kind, labels)


class Telemetry:
    """Prometheus families and tracing helpers for one service process."""

    canonical_metric_names = (
        "fd_llm_tokens_total",
        "fd_llm_generation_round_trip_seconds",
        "fd_llm_ttft_seconds",
        "fd_llm_pii_safety_catches_total",
        "fd_agent_calls_total",
        "fd_mcp_tool_calls_total",
        "fd_invocation_failures_total",
        "fd_web_api_requests_total",
        "fd_web_api_request_duration_seconds",
        "fd_web_api_request_errors_total",
        "fd_web_api_in_flight",
    )

    def __init__(self, service: str = "financial-distress") -> None:
        self.service = _label(service, "financial-distress")
        _configure_otel_exporter(self.service)
        self.registry = CollectorRegistry() if _PROMETHEUS_AVAILABLE else _FallbackRegistry()

        # These families preserve the existing app/test contract. New
        # service-labeled families below are the Phase 04 canonical metrics.
        self._legacy_requests = _metric(
            self.registry,
            "counter",
            "fd_http_requests_total",
            "HTTP requests completed by the service.",
            ("route", "status"),
        )
        self._legacy_latency = _metric(
            self.registry,
            "histogram",
            "fd_http_request_duration_seconds",
            "HTTP request latency.",
            ("route",),
        )
        self._legacy_tokens = _metric(
            self.registry,
            "counter",
            "fd_model_tokens_total",
            "Model token counts supplied by agent/model integrations.",
            ("model", "direction"),
        )
        self._legacy_ttft = _metric(
            self.registry,
            "histogram",
            "fd_model_ttft_seconds",
            "Model time to first token supplied by model integrations.",
            ("model",),
        )
        self.tokens = _metric(
            self.registry,
            "counter",
            "fd_llm_tokens_total",
            "Input, output and total model tokens.",
            ("service", "model", "direction"),
        )
        self.generation = _metric(
            self.registry,
            "histogram",
            "fd_llm_generation_round_trip_seconds",
            "Total model generation round-trip time.",
            ("service", "model"),
        )
        self.ttft = _metric(
            self.registry,
            "histogram",
            "fd_llm_ttft_seconds",
            "Model time to first token.",
            ("service", "model"),
        )
        self.pii_catches = _metric(
            self.registry,
            "counter",
            "fd_llm_pii_safety_catches_total",
            "Prompt or retrieved-content PII safety catches.",
            ("service", "agent", "finding_type"),
        )
        self.agent_calls = _metric(
            self.registry,
            "counter",
            "fd_agent_calls_total",
            "Agent invocation count.",
            ("service", "agent"),
        )
        self.tool_calls = _metric(
            self.registry,
            "counter",
            "fd_mcp_tool_calls_total",
            "MCP tool invocation count.",
            ("service", "tool"),
        )
        self.invocation_failures = _metric(
            self.registry,
            "counter",
            "fd_invocation_failures_total",
            "Invocation failures by operation and safe reason.",
            ("service", "operation", "reason"),
        )
        self.http_requests = _metric(
            self.registry,
            "counter",
            "fd_web_api_requests_total",
            "Web API request rate by route and status.",
            ("service", "method", "route", "status"),
        )
        self.http_duration = _metric(
            self.registry,
            "histogram",
            "fd_web_api_request_duration_seconds",
            "Web API request duration.",
            ("service", "method", "route"),
        )
        self.http_errors = _metric(
            self.registry,
            "counter",
            "fd_web_api_request_errors_total",
            "Web API error responses.",
            ("service", "method", "route", "status"),
        )
        self.http_in_flight = _metric(
            self.registry,
            "gauge",
            "fd_web_api_in_flight",
            "Web API requests currently in flight.",
            ("service", "route"),
        )

    def span(
        self,
        name: str,
        attributes: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        return trace_span(name, attributes, service=self.service, headers=headers)

    def observe_http(
        self,
        route: str,
        status_code: int,
        elapsed_seconds: float,
        method: str = "GET",
    ) -> None:
        route_label = _label(route, "/unknown")
        method_label = _label(method, "GET")
        status_label = _label(status_code, "500")
        self._legacy_requests.labels(route=route_label, status=status_label).inc()
        self._legacy_latency.labels(route=route_label).observe(max(0.0, elapsed_seconds))
        self.http_requests.labels(
            service=self.service,
            method=method_label,
            route=route_label,
            status=status_label,
        ).inc()
        self.http_duration.labels(
            service=self.service, method=method_label, route=route_label
        ).observe(max(0.0, elapsed_seconds))
        if status_code >= 400:
            self.http_errors.labels(
                service=self.service,
                method=method_label,
                route=route_label,
                status=status_label,
            ).inc()

    def observe(self, route: str, status_code: int, elapsed_seconds: float) -> None:
        self.observe_http(route, status_code, elapsed_seconds)

    def observe_tokens(self, model: str, direction: str, count: int) -> None:
        if count < 0:
            raise ValueError("token count cannot be negative")
        model_label = _label(model, "unknown-model")
        direction_label = _label(direction, "unknown")
        self._legacy_tokens.labels(model=model_label, direction=direction_label).inc(count)
        self.tokens.labels(
            service=self.service,
            model=model_label,
            direction=direction_label,
        ).inc(count)

    def observe_generation(self, model: str, elapsed_seconds: float) -> None:
        if elapsed_seconds < 0:
            raise ValueError("generation duration cannot be negative")
        self.generation.labels(service=self.service, model=_label(model, "unknown-model")).observe(
            elapsed_seconds
        )

    def observe_ttft(self, model: str, elapsed_seconds: float) -> None:
        if elapsed_seconds < 0:
            raise ValueError("TTFT cannot be negative")
        model_label = _label(model, "unknown-model")
        self._legacy_ttft.labels(model=model_label).observe(elapsed_seconds)
        self.ttft.labels(service=self.service, model=model_label).observe(elapsed_seconds)

    def observe_pii_catch(self, agent: str, finding_type: str) -> None:
        self.pii_catches.labels(
            service=self.service,
            agent=_label(agent, "unknown-agent"),
            finding_type=_label(finding_type, "unknown"),
        ).inc()

    def observe_agent_call(self, agent: str) -> None:
        self.agent_calls.labels(service=self.service, agent=_label(agent, "unknown-agent")).inc()

    def observe_tool_call(self, tool: str) -> None:
        self.tool_calls.labels(service=self.service, tool=_label(tool, "unknown-tool")).inc()

    def observe_failure(self, operation: str, reason: Any) -> None:
        self.invocation_failures.labels(
            service=self.service,
            operation=_label(operation, "unknown-operation"),
            reason=_label(safe_error(reason), "unknown_error"),
        ).inc()

    def request_in_flight(self, route: str, amount: int) -> None:
        child = self.http_in_flight.labels(service=self.service, route=_label(route, "/unknown"))
        if amount >= 0:
            child.inc(amount)
        else:
            child.dec(-amount)

    def render(self) -> bytes:
        if _PROMETHEUS_AVAILABLE:
            return generate_latest(self.registry)
        return self.registry.render()


class NoopTelemetry:
    service = "disabled"

    def span(self, *_args: Any, **_kwargs: Any) -> Any:
        return nullcontext()

    def observe(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    observe_http = observe
    observe_tokens = observe
    observe_generation = observe
    observe_ttft = observe
    observe_pii_catch = observe
    observe_agent_call = observe
    observe_tool_call = observe
    observe_failure = observe
    request_in_flight = observe

    def render(self) -> bytes:
        return b""


_NOOP_TELEMETRY = NoopTelemetry()
