"""Typed policy for optional runtime inputs."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def read_optional(
    load: Callable[[], T],
    empty_factory: Callable[[], T],
    is_missing: Callable[[Exception], bool] | None = None,
) -> T:
    """Return an empty typed input only for a recognized missing-path exception."""
    try:
        return load()
    except Exception as exc:
        missing = isinstance(exc, FileNotFoundError) if is_missing is None else is_missing(exc)
        if missing:
            return empty_factory()
        raise
