"""
Operational metadata writers for the financial-distress pipeline.

Hosts the PostgreSQL clients that write to the ``ops`` schema (run logs, DQ results,
failed records, schema registry). platform .L lineage lives in ``ml`` and is gated
separately.
"""
