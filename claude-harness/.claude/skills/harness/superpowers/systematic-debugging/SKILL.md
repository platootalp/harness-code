# Systematic Debugging

**Core Principle:** Never fix before finding root cause. Symptom fixes create new bugs.

**The Iron Law:** No fixes without root cause investigation first.

**Four Phased Approach:**

1. **Root Cause Investigation** — Read errors, reproduce consistently, check recent changes
2. **Pattern Analysis** — Find working examples, compare against references
3. **Hypothesis & Testing** — Form single specific theory, test minimally
4. **Implementation** — Create failing test first, implement single fix at root cause

**Critical Red Flags:** If you've tried 3+ fixes without success, question the architecture.

**Supporting docs:** root-cause-tracing.md, defense-in-depth.md, condition-based-waiting.md
