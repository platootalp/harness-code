# Multi-Agent Separation Rule

## Core Principle

**Separate the agent doing work from the agent judging it.**

Agents inherently praise their own outputs. A standalone evaluator can be tuned to
be skeptical — far easier than making a generator critical of its own work.

## Why Separation Works

| Self-Evaluation | Independent Evaluation |
|-----------------|----------------------|
| Tends to be lenient | Can be calibrated skeptical |
| Biased by effort invested | Neutral assessment |
| Hard to maintain standards | Consistent standards |
| Praises rather than critiques | Provides actionable feedback |

## The Three-Agent System

```
┌─────────────────────────────────────────────────────────────┐
│                         PLANNER                             │
│  Expands simple prompts into full product specs             │
│  Stays at high-level design, not implementation             │
└─────────────────────────────────────────────────────────────┘
                              ↓
                              ↓ (State Summary + Contract)
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       GENERATOR                             │
│  Works in sprints, implements features against contracts    │
│  Proposes scope and verification methods                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
                              ↓ (Deliverable)
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       EVALUATOR                             │
│  Tests via appropriate tools (Playwright MCP, etc.)         │
│  Grades against concrete criteria                            │
│  Provides actionable feedback                                │
│  Is inherently skeptical — MUST counteract leniency          │
└─────────────────────────────────────────────────────────────┘
```

## Separation Rules

### 1. Never Self-Evaluate

**Prohibited patterns:**
- Generator reviewing its own output
- Planner approving its own specs
- Any agent marking its own work as complete

**Required pattern:**
```
Generator → Evaluator → (Decision: Approved/Needs Revision)
```

### 2. Independent Calibration

The Evaluator must:
- Use few-shot examples for calibration
- Track judgment patterns
- Periodically review its own leniency
- Update prompts based on divergence analysis

### 3. Clear Handoff Protocol

Every handoff MUST include:
- State Summary (what was done, decisions made)
- Open questions (what Generator should know)
- Key assumptions

### 4. Evaluation Criteria are Public

All agents know:
- What dimensions Evaluator checks
- How scores map to decisions
- What feedback looks like

## Cost-Benefit Awareness

**When Evaluator overhead is worth it:**
- Complex architectural decisions
- High-stakes features
- Tasks beyond model's reliable solo capability

**When Evaluator overhead may not be worth it:**
- Simple, well-understood tasks
- Templates and boilerplate
- Low-risk incremental work

**Rule of thumb:** If the task sits beyond what the current model does reliably solo, the Evaluator is worth its cost.

## Context Management

### Reset vs. Compaction

| Approach | When to Use | Trade-off |
|----------|-------------|-----------|
| Context Reset | When state becomes stale | Clean slate, needs handoff artifacts |
| Compaction | When you need to keep context | May lose nuance |

**Note:** Model improvements (e.g., Opus 4.6) may eliminate the need for context resets entirely. Regularly reassess this assumption.

## Simplification Principle

**Every component encodes assumptions about what the model can't do.**

Regularly stress-test these assumptions:
1. List all workflow components
2. Ask: "Is this still necessary with current model capabilities?"
3. Remove pieces that are no longer load-bearing

The space of interesting harness combinations doesn't shrink — it moves.
