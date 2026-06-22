"""
Data quality framework for the financial-distress pipeline.

Hosts the check catalog and the runner that executes DQ checks against each zone, classifies results
as hard/soft failures, and logs to ``project_metadata.data_quality_result``.
"""
