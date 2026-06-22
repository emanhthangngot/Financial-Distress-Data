"""Lightweight Flink REST client for Stage 1 job submission.

Speaks only to the jobmanager HTTP API surface that the local
``apache/flink:1.19`` image exposes. We do NOT pull in ``pyflink``
and we do NOT pull in ``requests``: job submission is a thin HTTP
POST, the heavy lifting stays on the Flink cluster side. Sticking
to the standard library keeps the Airflow image slim, the test venv
honest (no extra deps to ``pip install`` just to test a two-endpoint
client), and the supply chain small.

Env contract (all optional except where noted):

* ``ENABLE_FLINK``         -- ``"1"`` to opt in. Empty/unset = opt out.
* ``FLINK_JOBMANAGER_URL`` -- required when opt in. e.g. ``http://flink-jobmanager:8081``.
* ``FLINK_PARALLELISM``    -- task parallelism for the submitted job. Default ``1``.

Failure mode: any REST error or missing required env raises ``RuntimeError``
so DAG tasks fail loudly rather than silently swallow the Flink toggle.

Security notes:

* ``FLINK_JOBMANAGER_URL`` must use ``http`` or ``https``. Other schemes
  (e.g. ``file://``) are rejected so a misconfigured env cannot turn this
  client into a local-file fetcher.
* ``jar_id`` is restricted to ``[A-Za-z0-9_.-]+`` because it is embedded
  in a URL path segment.
* ``program_args`` is joined into a single string and forwarded verbatim
  to the jobmanager. Callers must hard-code their args; never pass
  untrusted input here, as Flink will shell-split the string on the
  worker side.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

DEFAULT_TIMEOUT_SECONDS = 10


def is_enabled() -> bool:
    """Return True only when ENABLE_FLINK is set to a truthy value."""
    return os.getenv("ENABLE_FLINK", "").strip().lower() in {"1", "true", "yes", "on"}


_ALLOWED_SCHEMES = frozenset({"http", "https"})
_JAR_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def _jobmanager_url() -> str:
    url = os.getenv("FLINK_JOBMANAGER_URL", "").strip()
    if not url:
        raise RuntimeError(
            "FLINK_JOBMANAGER_URL is not set. Either set it (e.g. "
            "http://flink-jobmanager:8081) or unset ENABLE_FLINK to fall back "
            "to the MicroBatchConsumer streaming path."
        )
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise RuntimeError(
            f"FLINK_JOBMANAGER_URL has disallowed scheme {parsed.scheme!r}; "
            f"only http and https are accepted (got {url!r})."
        )
    return url.rstrip("/")


def _validate_jar_id(jar_id: str) -> str:
    """Reject jar_id values that are not safe path-segment material.

    The jobmanager URL embeds the jar_id directly in a path segment
    (e.g. ``/jars/{jar_id}/run``), so a value containing ``/`` or ``..``
    could pivot the request to an unintended endpoint. Allow letters,
    digits, ``_``, ``-``, and ``.`` only.
    """
    if not jar_id or not _JAR_ID_PATTERN.match(jar_id):
        raise RuntimeError(
            f"jar_id must match {_JAR_ID_PATTERN.pattern!r}; got {jar_id!r}."
        )
    return jar_id


def _parallelism() -> int:
    raw = os.getenv("FLINK_PARALLELISM", "1").strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"FLINK_PARALLELISM must be an integer, got {raw!r}") from exc
    if value < 1:
        raise RuntimeError(f"FLINK_PARALLELISM must be >= 1, got {value}")
    return value


def _request_json(url: str, method: str, body: dict[str, Any] | None,
                  timeout_seconds: int) -> dict[str, Any]:
    """Issue an HTTP request and return the parsed JSON body.

    Translates HTTP errors and connection failures into ``RuntimeError``
    with a single, predictable message shape so callers and tests can
    assert on it.
    """
    data: bytes | None = None
    headers: dict[str, str] = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(
            f"Flink jobmanager HTTP {exc.code} on {method} {url}: {detail!r}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Flink jobmanager unreachable on {method} {url}: {exc.reason}"
        ) from exc
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Flink jobmanager returned non-JSON on {method} {url}: {raw[:200]!r}"
        ) from exc


def submit_job(
    jar_id: str,
    program_args: list[str] | None = None,
    parallelism: int | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """Submit a Flink job by jar_id and return the jobmanager jobid.

    Parameters
    ----------
    jar_id:
        The jar id registered with the jobmanager (see
        ``GET /jars/overview``). For Stage 1 we use a single bundled
        jar id ``stage1-burst-handler`` that contains the
        burst / late-arrival / dedup streaming job.
    program_args:
        CLI args forwarded to the job's ``main(...)``. Each element is
        joined into a single ``programArgs`` string, matching the
        jobmanager's documented schema.
    parallelism:
        Override ``FLINK_PARALLELISM`` for this call. Defaults to env.
    timeout_seconds:
        HTTP timeout for the submit request.
    """
    base = _jobmanager_url()
    _validate_jar_id(jar_id)
    args = program_args or []
    payload: dict[str, Any] = {
        "programArgs": " ".join(args),
        "parallelism": parallelism if parallelism is not None else _parallelism(),
    }
    url = f"{base}/jars/{jar_id}/run"
    body = _request_json(url, "POST", payload, timeout_seconds)
    job_id = body.get("jobid")
    if not job_id:
        raise RuntimeError(
            f"Flink jobmanager at {url} returned 2xx but no jobid. body={body!r}"
        )
    return str(job_id)


def job_status(job_id: str, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Fetch the current status of a previously submitted Flink job.

    Returns the raw JSON dict from ``GET /jobs/{jobid}`` so callers can
    inspect ``state`` and timing fields. Raises ``RuntimeError`` on
    non-2xx responses (job not found, jobmanager down, ...).
    """
    base = _jobmanager_url()
    url = f"{base}/jobs/{job_id}"
    return _request_json(url, "GET", None, timeout_seconds)
