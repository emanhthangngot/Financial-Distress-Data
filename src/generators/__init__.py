"""
Synthetic data generators used by the fixture adapter.

This subpackage powers the offline data generator required by rubric row 2 (skew, cardinality,
schema evolution, duplicates) and the streaming problem factory (burst, late, duplicate events).
Output is fed into the Bronze zone via the fixture adapter so the rest of the pipeline stays
vendor-agnostic.
"""
