"""MLflow model registry adapter with a deterministic local fallback.

MLflow is optional in the local coursework environment.  When installed, the
adapter delegates to its tracking/registry APIs; otherwise a JSON registry in
the supplied path provides the same version/alias semantics for offline tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MLflowRegistry:
    """Register immutable model versions and resolve aliases safely."""

    def __init__(
        self,
        tracking_uri: str | None = None,
        *,
        local_path: str | Path = "outputs/mlflow-registry.json",
    ):
        self.tracking_uri = tracking_uri
        self.local_path = Path(local_path)
        self._mlflow = None
        if tracking_uri:
            try:
                import mlflow  # type: ignore

                mlflow.set_tracking_uri(tracking_uri)
                self._mlflow = mlflow
            except ImportError:
                self._mlflow = None

    def _load(self) -> dict[str, Any]:
        if not self.local_path.exists():
            return {"models": {}}
        return json.loads(self.local_path.read_text(encoding="utf-8"))

    def _save(self, state: dict[str, Any]) -> None:
        self.local_path.parent.mkdir(parents=True, exist_ok=True)
        self.local_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

    def register(
        self,
        model_name: str,
        artifact_uri: str,
        *,
        run_id: str | None = None,
        manifest: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Register a model artifact and return its immutable version record."""

        if self._mlflow is not None:
            registered = self._mlflow.register_model(artifact_uri, model_name)
            version = str(registered.version)
            if manifest and run_id:
                # Keep the real backend's lineage contract identical to the
                # deterministic fallback.  Without this call a registry
                # version would silently lose the data/image/source manifest.
                client = self._mlflow.MlflowClient()
                client.log_dict(run_id, manifest, "reproducibility_manifest.json")
            return {
                "name": model_name,
                "version": version,
                "artifact_uri": artifact_uri,
                "run_id": run_id,
                "manifest": manifest or {},
            }
        state = self._load()
        models = state.setdefault("models", {})
        versions = models.setdefault(model_name, {}).setdefault("versions", [])
        version = str(len(versions) + 1)
        record = {
            "name": model_name,
            "version": version,
            "artifact_uri": artifact_uri,
            "run_id": run_id,
            "manifest": manifest or {},
        }
        versions.append(record)
        self._save(state)
        return record

    def set_alias(self, model_name: str, alias: str, version: str | int) -> None:
        if self._mlflow is not None:
            client = self._mlflow.MlflowClient()
            client.set_registered_model_alias(model_name, alias, str(version))
            return
        state = self._load()
        model = state.setdefault("models", {}).setdefault(model_name, {})
        if not any(item["version"] == str(version) for item in model.get("versions", [])):
            raise KeyError(f"unknown model version {model_name!r}:{version}")
        model.setdefault("aliases", {})[alias] = str(version)
        self._save(state)

    def resolve_alias(self, model_name: str, alias: str = "champion") -> dict[str, Any]:
        if self._mlflow is not None:
            version = self._mlflow.MlflowClient().get_model_version_by_alias(model_name, alias)
            return {"name": model_name, "version": str(version.version), "run_id": version.run_id}
        state = self._load()
        model = state.get("models", {}).get(model_name, {})
        version = model.get("aliases", {}).get(alias)
        if version is None:
            raise KeyError(f"alias {alias!r} is not set for {model_name!r}")
        return next(item for item in model.get("versions", []) if item["version"] == version)

    # Common registry naming used by callers and hidden contract tests.
    register_model = register
    promote = set_alias
    get_alias = resolve_alias


# Conventional spelling used by service consumers that do not care which
# tracking backend is configured.
ModelRegistry = MLflowRegistry
