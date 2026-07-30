"""
I/O helpers for the financial-distress lakehouse.

Wraps MinIO/S3 writes and centralizes the canonical S3A path scheme used across Bronze, Silver, and
Gold zones. The goal is one place to change endpoint, bucket, or partitioning defaults.
"""
