# Writing Plans

Generate detailed, step-by-step implementation plans for multi-step tasks.

## Key Requirements

- Save plans to `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`
- Start each plan with: Goal, Architecture, and Tech Stack
- Break work into 2-5 minute steps following TDD workflow
- Every step must include actual code, exact file paths, and exact commands
- No placeholders like "TBD", "TODO", or "implement later"

## No Placeholders Rule

Steps must contain complete content—actual code, exact paths, and expected outputs.

## File Structure

Before defining tasks, map out which files will be created/modified and why.

## Self-Review Checklist

1. **Spec coverage** — can you point to a task for every requirement?
2. **Placeholder scan** — look for TBD, TODO, "add appropriate handling"
3. **Type consistency** — ensure names match across all tasks

## Execution Options

- **Subagent-Driven** (recommended) — fresh subagent per task with review
- **Inline Execution** — batch execution with checkpoints
