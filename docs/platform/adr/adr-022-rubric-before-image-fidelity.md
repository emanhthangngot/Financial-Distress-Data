# ADR-022: Rubric before image fidelity

## Status

Accepted — 2026-09-10.

Supersedes the image-fidelity portion of ADR-016's O-1. ADR-016 remains the historical reference inventory for the target image; it is not a binding requirement to make every image-only component live.

## Context

The rebuild is graded by 161 canonical rubric rows worth 300 points. The architecture image contains components that are not required to satisfy those rows and would consume scarce implementation and evidence capacity without improving the scored contract. A visual inventory and an executable capability inventory are different artifacts.

## Decision

Rubric capability and executable evidence take precedence over image fidelity. The project must preserve all rubric capabilities, assign each canonical row one owning phase, and prove behavior with the validators and runtime evidence named by that phase. Image-only components remain documented as historical reference inventory and may be implemented later when an owner, acceptance criterion, resource budget, and validation artifact exist.

This decision does not remove any rubric row, downgrade a rubric score, or make an unselected image-only component a verifier failure. `scripts/verify_target_architecture.py` validates the selected capability inventory; `scripts/verify_rubric_coverage.py` validates ownership, acceptance-criterion citations, and executed evidence as separate modes.

## Consequences

- ADR-016's former “every component and annotated edge must be live” statement is historical, not a release gate.
- P2 data contracts remain binding for downstream phases: versioned dimension joins, vintage-preserving facts, `known_from_ts`, Feast reserved timestamps, and explicit source provenance.
- Optional platform extensions require an owner, gate, artifact, and non-rubric threshold before implementation.
- Final evidence must distinguish design completeness from executed behavior.
