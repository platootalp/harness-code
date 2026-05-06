# Receiving Code Review

## Core Approach

Verify before implementing. Technical correctness over social comfort.

## Key Guidelines

- **Don't perform agreement.** No "You're absolutely right!" — just state the technical fix or act.
- **Verify against codebase.** External feedback is *suggestions to evaluate*, not orders.
- **Push back when needed** using technical reasoning.
- **Clarify unclear items first.** Partial understanding leads to wrong implementation.
- **Test one item at a time.** Verify no regressions.

## When to Question

- Suggestion breaks existing functionality
- Reviewer lacks full context
- Violates YAGNI (unused feature)
- Technically incorrect for your stack
- Conflicts with architectural decisions

## Handling Unclear Feedback

```
IF any item is unclear:
  STOP - do not implement anything yet
  ASK for clarification on unclear items
```

## Acknowledging Correct Feedback

State the fix — that's acknowledgment enough:
> "Fixed. Removed unused endpoint in `api.py`."
> "Good catch — null check missing. Added in `user.py:42`."
