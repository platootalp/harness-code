# Sprint Contract Rule

## Purpose

Bridge the gap between high-level specs and testable implementation by negotiating
what "done" looks like before each work chunk begins.

## When to Use

Sprint Contracts are used:
- **Before each sprint** in iterative development
- **Before major feature implementation**
- **When scope changes mid-sprint**
- **At handoff between stages** (e.g., Design → Dev-Plan)

## Sprint Contract Template

See: `docs/specs/templates/sprint-contract.md`

## Contract Negotiation Process

### Step 1: Generator Proposes

Generator reviews the specs and proposes:
- Scope for this sprint
- Completion criteria
- Verification methods

```markdown
## Generator's Proposal

**Scope:**
- F-001: User authentication
- F-002: Session management

**Done Criteria:**
- All auth endpoints return 200/401 correctly
- Session expires after 30 minutes

**Verification:**
- Unit tests for auth service
- Integration test for login flow
```

### Step 2: Evaluator Reviews

Evaluator reviews the proposal and:
- Ensures criteria are testable
- Checks for gaps or ambiguities
- Proposes adjustments

```markdown
## Evaluator's Review

**Concerns:**
- "Correctly" is vague - what about edge cases?
- Session expiry not verified in tests

**Suggestions:**
- Add: Return 401 for expired sessions
- Change: "Session expires" → "Session invalidates after 30min inactivity"
```

### Step 3: Negotiation

Generator and Evaluator discuss until agreement:
- Scope may be adjusted
- Criteria made concrete
- Verification methods finalized

### Step 4: Sign-off

Both parties sign the contract:
- Generator commits to delivering
- Evaluator commits to testing against criteria
- Contract stored for reference

## Contract Components

### Must Have vs Should Have vs Could Have

| Category | Commitment | Consequence if Missed |
|----------|-----------|----------------------|
| Must Have | Hard commitment | Sprint failed |
| Should Have | Soft commitment | Discuss before proceeding |
| Could Have | Best effort | Nice to have |

### Verification Methods

| Verification Type | Tools/Methods |
|-------------------|---------------|
| Automated tests | Jest, Pytest, Playwright |
| Manual review | Evaluator checks output |
| User testing | Human performs task |
| Performance benchmarks | Load testing tools |
| Security audit | Static analysis, penetration testing |

### Success Metrics

Metrics should be:
- **Specific:** "Response time < 200ms"
- **Measurable:** Can be verified numerically
- **Achievable:** Realistic given constraints
- **Relevant:** Tied to business goals
- **Time-bound:** Measured at sprint end

## Contract Lifecycle

```
PROPOSE → REVIEW → NEGOTIATE → SIGN-OFF → EXECUTE → EVALUATE → CLOSE
    │         │         │          │         │         │         │
    │         │         │          │         │         │         │
  Generator  Evaluator  Discussion  Mutual    Generator  Evaluator Sprint
                              │      agreement              │       Complete
```

## Mid-Sprint Changes

If scope must change mid-sprint:

1. **Document the change** - Why is scope changing?
2. **Re-negotiate** - What can realistically be delivered?
3. **Update contract** - Amend or create new contract
4. **Assess impact** - Does this affect other sprints?

## Contract Storage

Contracts are stored at:
```
docs/specs/sprint-contracts/{feature-name}-sprint-{n}.md
```

## Benefits

- **Clear expectations** for both Generator and Evaluator
- **Reduced surprises** at evaluation time
- **Documented rationale** for scope decisions
- **Accountability** through mutual sign-off

## Common Pitfalls

| Pitfall | Why It Happens | Prevention |
|---------|----------------|------------|
| Vague criteria | Hurrying to start | Spend time on this |
| Over-committing | Wanting to please | Be realistic |
| Missing verification | Assuming it will work | Specify how to test |
| No metrics | Not thinking about measurement | Add success metrics |
