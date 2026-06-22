"""
Operational metadata writers for the financial-distress pipeline.

Hosts the PostgreSQL clients that write to the ``project_metadata`` schema (run logs, DQ results,
failed records, schema registry). Phase 2 ML lineage lives in ``ml_metadata`` and is gated
separately.
"""
