# Novel Idea: Point-In-Time Leakage Guard

## Problem

Financial features computed with prices or news published after a reporting
event leak future information into training data and overstate model quality.

## Design

`src/transforms/features/pit.py` selects only feature rows whose event timestamp
is at or before the reference timestamp. The DP3 publication gate independently
checks `feature_event_timestamp <= event_timestamp` and requires `created_ts`.
The second check protects publication even if upstream feature logic regresses.

## Evaluation

The positive/negative probe supplies one past and one future candidate. The join
selects the past candidate. A deliberately leaked snapshot is then submitted to
the DP3 gate and must raise `PipelineValidationError`.

Runtime result: [`phase8-novel-ideas.json`](evidence/novel/phase8-novel-ideas.json).

## Limitations

Correct timestamps remain a source-data responsibility. The guard prevents
chronological leakage but cannot detect a publisher that supplied a false event
time.
