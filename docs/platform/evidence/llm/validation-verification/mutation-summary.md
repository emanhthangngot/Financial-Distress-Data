# Mutation Testing

- Mutation score: 86.11%
- Gate: > 80.00%
- Killed: 62
- Survived: 9
- Timeout: 1
- Suspicious: 0
- No tests: 0
- Targets: src/llm/rag/chunking.py
- Mutant filters: none — full-module scope via `llm.rag.chunking.*`
- Command: `python scripts/run_phase5_mutation_gate.py`
- Captured: 2026-08-14 (re-verified; canonical run 2026-08-10 recorded the
  identical 86.11%/62/9/1/72 — deterministic, no drift)

No screenshot: `mutmut` (this repo's pinned version) has no browser/HTML
report command — only `browse` (terminal TUI), `results`, and `show`, all
text-only (`python -m mutmut --help`, checked 2026-08-14). The JSON above is
the real tool's own machine-readable summary, not a rendering built for this
document.
