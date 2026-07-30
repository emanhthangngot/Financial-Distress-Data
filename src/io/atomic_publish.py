"""Filesystem publication primitive that preserves the previous validated snapshot."""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Callable
from pathlib import Path


class AtomicDirectoryPublisher:
    """Build in a sibling staging directory and atomically swap after validation."""

    def __init__(self, published_path: str | Path) -> None:
        self.published_path = Path(published_path)
        self.pointer_path = self.published_path.parent / f".{self.published_path.name}.current.json"

    @property
    def current_run_id(self) -> str | None:
        """Return the run ID recorded by the last successful promotion."""
        if not self.pointer_path.is_file():
            return None
        return json.loads(self.pointer_path.read_text(encoding="utf-8"))["run_id"]

    def publish(
        self,
        run_id: str,
        build: Callable[[Path], object],
        validate: Callable[[Path], object],
    ) -> None:
        """Build and validate a snapshot before replacing the published directory."""
        if not run_id.strip():
            raise ValueError("run_id must not be empty")
        parent = self.published_path.parent
        parent.mkdir(parents=True, exist_ok=True)
        staging = parent / f".{self.published_path.name}.staging-{run_id}"
        backup = parent / f".{self.published_path.name}.backup-{run_id}"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(backup, ignore_errors=True)
        staging.mkdir()
        try:
            build(staging)
            result = validate(staging)
            if result is False:
                raise RuntimeError("publication validation returned false")
            if self.published_path.exists():
                os.replace(self.published_path, backup)
            try:
                os.replace(staging, self.published_path)
            except Exception:
                if backup.exists():
                    os.replace(backup, self.published_path)
                raise
            shutil.rmtree(backup, ignore_errors=True)
            temporary_pointer = self.pointer_path.with_suffix(".tmp")
            temporary_pointer.write_text(json.dumps({"run_id": run_id}) + "\n", encoding="utf-8")
            os.replace(temporary_pointer, self.pointer_path)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
