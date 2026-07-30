"""Centralised environment-variable loader for protected credentials.

WHO: data-engineer enforcing no-default-credentials (W14, S-A).
ACTION: expose :func:`require` and :func:`optional` so call sites can
fetch ``MINIO_ROOT_USER`` / ``POSTGRES_PASSWORD`` / etc. without ever
silently defaulting to a demo literal. ``require`` raises a
:class:`RuntimeError` whose message names the missing variable and
points the operator at the ``.env`` file (which is gitignored), so
the failure mode is loud rather than a hidden production misconfig.
RESULT: every credential lookup in the codebase goes through one of
two helpers; demo strings can no longer mask a missing env var.
"""

from __future__ import annotations

import os

_ENV_FILE_HINT = (
    "Set it in the project-root .env file (gitignored) or export it in "
    "the Airflow/scheduler environment before retrying."
)


def require(name: str) -> str:
    """Return the value of env var ``name`` or raise :class:`RuntimeError`.

    Blank/whitespace-only values are treated as missing so an empty
    string cannot sneak through and corrupt a downstream S3/Postgres
    client.
    """
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Required environment variable {name!r} is not set. {_ENV_FILE_HINT}")
    return value


def optional(name: str) -> str | None:
    """Return the value of env var ``name`` or ``None`` if missing/blank.

    Useful for non-required knobs such as ``MINIO_ENDPOINT`` whose
    default the caller can still resolve from a parsed YAML config.
    """
    value = os.environ.get(name)
    if value is None or not value.strip():
        return None
    return value


__all__ = ["require", "optional"]
