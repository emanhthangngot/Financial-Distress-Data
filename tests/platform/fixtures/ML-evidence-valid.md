# Valid executed evidence for ML-evidence-missing-artifact.
#
# This file fully satisfies the evidence contract. The audit must still fail
# because the row's artifact_path (src/ml/ML-evidence-missing-artifact) does
# not exist on disk: an executed row must prove a real implementation.

- rubric_id: ML-evidence-missing-artifact
- execution_timestamp: 2026-08-02T12:00:00+07:00
- source_sha: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f80910
- gitops_sha: 0f1e2d3c4b5a697887766554433221100aabbcc
- versions: v1.0.0
- command: pytest tests/platform -k 'ML-evidence-missing-artifact'
- expected_result: all tests pass
- actual_result: all tests pass
- redaction_status: none
