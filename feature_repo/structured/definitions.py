# Re-export only — the entity and every FeatureView are constructed in
# src/ml/feast/feature_definitions.py (the row-77 pinned artifact that names
# every TTL). Loaded only by the `feast` CLI (.venv-phase2), never by
# `.venv`'s pytest, so calling build_feature_objects() here (which imports
# Feast) is safe. Verified against Feast 0.65 in a throwaway spike,
# 2026-08-08: `feast apply` discovers module-level attributes via
# introspection, so injecting into globals() here works the same as a plain
# `from ... import *` would.
from src.ml.feast.feature_definitions import build_feature_objects

globals().update(build_feature_objects())
