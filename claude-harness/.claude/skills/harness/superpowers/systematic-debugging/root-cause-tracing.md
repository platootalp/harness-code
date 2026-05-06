# Root Cause Tracing

**Core principle:** Always trace backward through the call chain to find the original trigger—never fix where the error appears.

**The process:**
1. Observe the symptom
2. Find the immediate cause
3. Ask: "What called this code?"
4. Keep tracing upward
5. Fix at the source

**Key tactic:** When manual tracing fails, add stack trace instrumentation before dangerous operations.

**Example trace:**
- Symptom: git init fails in wrong directory
- 5-level trace found: Test accessed `tempDir` before `beforeEach` ran
- Fix: Made `tempDir` a getter that throws if accessed prematurely
