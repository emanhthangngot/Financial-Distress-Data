# platform . rule update

## Context

`AGENTS.md` documents skill routing but does not make selection and activation behavior explicit. `CLAUDE.md` only delegates to `AGENTS.md`.

## Requirements

- Make skill selection mandatory for requests that clearly match a listed domain or workflow.
- Keep direct explanations and simple read-only requests lightweight.
- Require reading the selected `SKILL.md`, announcing the skill, and following its workflow.
- Preserve the existing project-specific rules and avoid forcing irrelevant skills.

## Files to modify

- `AGENTS.md`
- `CLAUDE.md`

## Validation

- Review the rendered Markdown and `git diff --check`.
- Confirm the diff excludes unrelated existing worktree files.
