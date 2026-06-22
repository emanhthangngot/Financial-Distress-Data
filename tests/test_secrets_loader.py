"""Tests for the W14 secrets loader.

WHO: data-engineer enforcing no-default-credentials for S3/MinIO/Postgres
clients.
ACTION: drive src.security.secrets.require() and .optional() through
env-var scenarios (set / unset / blank).
RESULT: secrets are surfaced loudly when missing and returned verbatim
when set, with no silent fallback to demo credentials.
"""

from __future__ import annotations

import importlib

import pytest


def _import_secrets():
    """Import src.security.secrets freshly so monkeypatch.setenv() takes
    effect (the module reads env at call time, but importlib.reload keeps
    the test honest against future caching changes)."""
    from src.security import secrets

    return importlib.reload(secrets)


def test_require_returns_env_value_when_set(monkeypatch):
    monkeypatch.setenv("MINIO_ROOT_USER", "alice")
    secrets = _import_secrets()
    assert secrets.require("MINIO_ROOT_USER") == "alice"


def test_require_raises_when_unset(monkeypatch):
    monkeypatch.delenv("MINIO_ROOT_USER", raising=False)
    secrets = _import_secrets()
    with pytest.raises(RuntimeError, match="MINIO_ROOT_USER"):
        secrets.require("MINIO_ROOT_USER")


def test_require_raises_when_blank(monkeypatch):
    monkeypatch.setenv("MINIO_ROOT_USER", "   ")
    secrets = _import_secrets()
    with pytest.raises(RuntimeError, match="MINIO_ROOT_USER"):
        secrets.require("MINIO_ROOT_USER")


def test_optional_returns_none_when_unset(monkeypatch):
    monkeypatch.delenv("UNSET_VAR_X", raising=False)
    secrets = _import_secrets()
    assert secrets.optional("UNSET_VAR_X") is None


def test_optional_returns_value_when_set(monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT", "http://minio:9000")
    secrets = _import_secrets()
    assert secrets.optional("MINIO_ENDPOINT") == "http://minio:9000"


def test_require_error_message_mentions_dotenv(monkeypatch):
    """The error should hint that .env is the source of truth so the
    developer knows to set it there rather than passing empty strings."""
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    secrets = _import_secrets()
    with pytest.raises(RuntimeError) as excinfo:
        secrets.require("POSTGRES_PASSWORD")
    assert "POSTGRES_PASSWORD" in str(excinfo.value)
    assert ".env" in str(excinfo.value)
