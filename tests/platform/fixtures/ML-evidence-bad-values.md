# Evidence placeholder — must NOT pass phase-08 audit
#
# All keys are present with non-empty values, but the values cannot be real:
# the timestamp is not ISO-8601, and the SHAs are not valid git SHAs/refs.

- rubric_id: ML-evidence-bad-values
- execution_timestamp: not-a-real-date
- source_sha: zzz-not-a-sha
- gitops_sha: ???
- versions: v1.0.0
- command: pytest tests/platform
- expected_result: all tests pass
- actual_result: all tests pass
- redaction_status: none
