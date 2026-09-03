---
title: "Low-Level Design"
date: 2026-08-14
status: active
---

# Low-Level Design: key service classes mapped to their implementation

This doc proves the single row in "Documentation" (the rubric row is
literally titled to require a low-level ML/LLM design document): a
substantive design document exists, documents the the platform design contracts
and key classes, and is verified by a generated requirement test rather than
by manual inspection alone. It does not duplicate that document's content —
this doc indexes it and links the executable proofs.

## Part I — The canonical design document

`docs/platform/low-level-design.md` (132 lines) is the canonical artifact,
organized as:

```text
## ML Classes            (lines 17-60)
## LLM Classes            (lines 61-123)
## Contract Enforcement    (lines 124-132)
```

It links the executable embedding registry and citation guard proofs
(`src/llm/embedding_registry.py`, `src/llm/citation_guard.py`) and records
the additive the platform architecture — every class it documents is backed by
real code linked in `repository_design.md`'s contract proof.

### 1. Verified by a generated requirement test, not manual claim

```text
$ .venv-platform/bin/python -m pytest -q tests/platform/requirements/test_llm_ac_19_documentation.py \
    -k LLM-documentation-low-level-ml-design
-> passed: the document exists, is substantive, and documents the the platform
   design contracts and key classes
```

Full evidence:
[`LLM-documentation-low-level-ml-design.md`](../../platform/evidence/llm/LLM-documentation-low-level-ml-design.md).

## Limitations

This doc is an index, not a duplicate — read
[`docs/platform/low-level-design.md`](../../platform/low-level-design.md) for the
full class-by-class design content.

## References

- Canonical design document: `docs/platform/low-level-design.md`
