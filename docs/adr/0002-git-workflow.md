# 2. Git Workflow

Date: 2026-09-29

## Context
Collaborative AI/human development easily degrades without strict boundary enforcement and incremental verification.

## Decision
- One step per conversation; never commit directly to `main`.
- Each step develops on an isolated branch named `step/NN-<name>` cut from `main`.
- Checkpoints within each step receive small, atomic commits after passing verification.
- Completion produces a pull request via `gh pr create` documenting changes, real check outputs, and out-of-scope boundaries.
- Only the human merges PRs into `main`. The agent never merges, never force-pushes, and never deletes branches.

## Consequences & Cost
- Prevents accidental regressions and context corruption across conversations.
- Requires explicit verification and PR review before advancing to the next step.
