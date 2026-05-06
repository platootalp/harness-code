# Iterative Refinement Rule

## Core Principle

**Multiple iteration cycles with feedback flow from Evaluator back to Generator.**

Don't expect perfection on the first try. The goal is continuous improvement through
structured feedback loops.

## Iteration Loop

```
┌─────────────────────────────────────────────────────────────┐
│                     ITERATION CYCLE                         │
│                                                             │
│   Generator ──→ Evaluator ──→ Decision Node               │
│       ↑              │                                      │
│       │              │                                      │
│       └── feedback ──┘                                      │
│                                                             │
│   Decision:                                                 │
│   • Trending well → Refine current direction                │
│   • Approach failing → Pivot or abort                        │
└─────────────────────────────────────────────────────────────┘
```

## Strategic Decisions After Each Evaluation

### Decision 1: Trending Well (Score improving)

**Signal:** Scores are consistently improving, issues are minor

**Action:** Continue with current direction
- Address remaining issues in next iteration
- Keep scope the same or slightly expand
- Maintain momentum

### Decision 2: Stuck (Score plateauing)

**Signal:** Same issues recurring, no improvement

**Action:** Analyze root cause
- Is the issue fundamental to the approach?
- Should you try a different implementation strategy?
- Should you escalate to Planner for scope change?

### Decision 3: Failing (Score declining or consistently low)

**Signal:** Approach fundamentally not working

**Action:** Strategic pivot
- Return to Planner for approach revision
- Consider breaking into smaller pieces
- Consider if feature is worth pursuing at all

## Iteration Limits

| Situation | Max Iterations | Action if Unresolved |
|-----------|----------------|---------------------|
| Single spec document | 3 | Escalate to human review |
| Sprint deliverable | 5 | Abort sprint, reassess |
| Overall feature | 10 | Consider dropping feature |

## Feedback Quality

### Good Feedback (Actionable)

```
## Issue: Unclear acceptance criteria

**Problem:** REQ-003 says "system should be fast" but doesn't define fast

**Evidence:** "The system shall respond quickly to user requests"

**Suggestion:** Change to "The system shall respond in <200ms for 95th percentile"
```

### Bad Feedback (Not Actionable)

```
## Issue: Needs more detail

**Problem:** This section needs more work

**Suggestion:** Make it better
```

## State Management Across Iterations

### Iteration Tracking

Track iterations in document metadata:

```markdown
---
iteration: 2
last-evaluator-feedback: 2026-04-01
changes-since-last: Added specific metrics to REQ-003, clarified F-001 scope
---
```

### What to Include in Revision

When resubmitting:
1. Summary of changes made
2. Response to each feedback point
3. Any new issues introduced (be honest)
4. Remaining known issues

## When to Stop Iterating

### Stop Signals

- **Resource exhaustion:** Time/budget spent
- **Scope creep:** Original goal has drifted
- **Complexity explosion:** Solution became too complex
- **Value diminishment:** ROI of another iteration is low

### Exit Strategies

| Situation | Exit Strategy |
|-----------|---------------|
| Can't meet criteria | Document as known limitation, proceed with waiver |
| Criteria no longer relevant | Update criteria, not the deliverable |
| Fundamental mismatch | Abandon feature, document learnings |
| External blocker | Park feature, address blocker |

## Review Decision Expansion

Standard decisions now include:

| Decision | Meaning | Next Step |
|----------|---------|-----------|
| Approved | Meets all criteria | Proceed to next stage |
| Approved with Conditions | Minor issues | Fix in next version |
| Needs Iteration | Substantial revision | Return to Generator |
| Rejected | Major issues | Major rework, may need Planner |

## Handoff Between Iterations

When Generator receives feedback:

1. **Acknowledge** each point (even if you disagree)
2. **Prioritize** feedback items
3. **Plan** changes before starting
4. **Validate** your interpretation with Evaluator if unclear

```markdown
## Response to Feedback

### REQ-003 acceptance criteria (Priority: High)
- Acknowledged: Criteria was vague
- Changed: Now specifies <200ms response time
- Concern: May need to verify with load testing

### F-001 scope creep (Priority: Medium)
- Acknowledged: Scope expanded beyond original
- Changed: Narrowed back to core use cases
- Disagree: Original scope was too narrow
```

## Benefits of Iteration

- **Higher quality output** through multiple refinement passes
- **Clearer communication** between Generator and Evaluator
- **Learning opportunity** for both agents
- **Reduced risk** of shipping incomplete work
- **Documented decisions** through feedback trail
