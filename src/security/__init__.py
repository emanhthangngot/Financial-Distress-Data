"""
Secrets loader and helpers for the financial-distress pipeline.

Hosts the runtime secrets loader used by every job that needs MinIO or PostgreSQL credentials. Reads
from environment variables (preferred) or from ``secrets/local.env`` (local dev only); never from
defaults.
"""
