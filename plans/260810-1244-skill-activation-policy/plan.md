# Skill activation policy

Status: in_progress

## Phases

1. Update `AGENTS.md` and `CLAUDE.md` with explicit skill-selection and activation rules.
2. Verify the documentation-only diff, commit the scoped files, and open a PR targeting `dev`.
3. Monitor the PR and report its merge status.

## Dependencies

- Existing `ak:*` skill catalog available to Codex and Claude Code.
- Current branch remains the feature branch for the PR.

## Acceptance criteria

- Codex or Claude runtime -> classifies each request -> selects the matching primary skill or explicitly records that no skill is needed.
- Selected skill -> reads its complete `SKILL.md` -> announces and follows the skill workflow.
- Implementation request -> uses the documented plan/cook/test workflow -> verifies the affected behavior before completion.
- GitHub workflow -> stages only the rule and plan files -> opens exactly one PR against `dev`.

## Scope

Only agent rule files and the task plan are in scope. No application code, tests, generated artifacts, or unrelated worktree changes will be modified.
