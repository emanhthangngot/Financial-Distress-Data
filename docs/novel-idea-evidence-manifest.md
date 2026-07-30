# Novel Idea: Correlated Evidence Manifest

## Problem

Coursework screenshots and metrics can look valid while coming from different
runs or after manual editing. A final score needs evidence integrity, not only
file presence.

## Design

`src/evidence/run_manifest.py` binds the run ID, Git revision, configuration
hash, artifact path, proof type, byte size, and SHA-256 digest. Safe relative
paths and unique artifact names prevent directory traversal and ambiguous
records. The rubric auditor accepts only artifacts present in the verified
manifest and carrying the same run ID.

## Evaluation

`scripts/export_novel_idea_evidence.py` verifies an untouched artifact, changes
its row count, then verifies again. The clean control returns no errors; the
mutated artifact returns `artifact hash mismatch`. Unit tests also cover unsafe
paths and duplicate records.

Runtime result: [`phase8-novel-ideas.json`](evidence/novel/phase8-novel-ideas.json).

## Limitations

SHA-256 proves consistency with the generated manifest, not authorship. A
submission requiring non-repudiation should sign the final manifest externally.
