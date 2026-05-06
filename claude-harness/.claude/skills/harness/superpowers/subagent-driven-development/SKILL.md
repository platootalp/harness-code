# Subagent-Driven Development

Execute plan by dispatching fresh subagent per task, with two-stage review: spec compliance review first, then code quality review.

**Why subagents:** Fresh subagent per task + two-stage review = high quality, fast iteration

## When to Use

Use when you have an implementation plan with mostly independent tasks and want to stay in the current session.

## The Process

1. Read plan, extract all tasks with full text, create TodoWrite
2. For each task:
   - Dispatch implementer subagent
   - Dispatch spec reviewer subagent
   - Dispatch code quality reviewer subagent
   - Mark task complete
3. After all tasks: dispatch final code reviewer
4. Use finishing-a-development-branch superpower

## Model Selection

- **Mechanical implementation** (isolated functions): fast, cheap model
- **Integration and judgment** (multi-file): standard model
- **Architecture, design, and review**: most capable model

## Status Handling

- **DONE:** Proceed to spec compliance review
- **DONE_WITH_CONCERNS:** Address concerns before proceeding
- **NEEDS_CONTEXT:** Provide missing context and re-dispatch
- **BLOCKED:** Escalate or break into smaller pieces

## Red Flags

**Never:**
- Skip reviews (spec compliance OR code quality)
- Proceed with unfixed issues
- Dispatch multiple implementation subagents in parallel
