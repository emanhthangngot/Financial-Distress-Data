# Equivalence partitions and boundary cases

This document maps the currently implemented ML validation cases to their input partitions. It is a partial P11 artifact; rows marked pending still need a corresponding parametrized case before AC-P11-2 can close.

| Input / contract | Equivalence partitions | Boundary value | Existing case |
|---|---|---|---|
| Leakage rows | empty frame; all rows valid; one future feature row | `feature_timestamp == decision_timestamp` | `test_equivalence_partition_clean_and_empty_frames`, `test_leakage_partition_names_offending_rows`, `test_boundary_timestamp_is_not_leakage` |
| A/B weights | positive weights summing to one; all-zero weights; negative weight | zero and negative weights | `test_router_is_stable_and_validates_weight_boundaries` |
| Manifest `snapshot_id` | non-empty identifier; empty/whitespace identifier | empty string | `test_build_manifest_rejects_invalid_inputs` |
| Manifest compute source | `local`, `gke`, `kaggle`; unsupported source | unsupported `remote` | `test_build_manifest_rejects_invalid_inputs` |
| Manifest compute seconds | non-negative duration | `0`; negative duration | `test_manifest_and_data_version_are_deterministic`, `test_build_manifest_rejects_invalid_inputs` |
| Manifest accelerator | non-empty accelerator; empty accelerator | empty string | `test_build_manifest_rejects_invalid_inputs` |
| Manifest marginal cost | non-negative cost | `0`; negative cost | `test_manifest_and_data_version_are_deterministic`, `test_build_manifest_rejects_invalid_inputs` |
| Git source SHA | successful git output; `CalledProcessError`; `OSError` | empty stdout | `test_current_source_sha_success_and_failures` |
| Data version rows | original order; reversed order | empty input | `test_manifest_and_data_version_are_deterministic` |
| Training inputs | reproducible local run; distributed two-worker run | two equal shards | `test_training_and_distributed_local_paths_are_reproducible` |

## Mapping rule

Every row must map to a real `@pytest.mark.parametrize` case for AC-P11-2. The current legacy-style tests include several direct assertions rather than parametrization; those rows remain identified here so they can be converted without losing the boundary contract.

## Open coverage

This table covers the bounded ML validation pilot only. Partitions for the full `src/ml/`, `src/transforms/`, and `src/quality/` target scope are pending.
