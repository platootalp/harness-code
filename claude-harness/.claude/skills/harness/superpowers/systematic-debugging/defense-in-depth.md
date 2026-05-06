# Defense-in-Depth Validation

**Core principle:** Validate at EVERY layer data passes through. Make the bug structurally impossible.

**The Four Layers:**
1. **Entry Point Validation** — Reject obviously invalid input at API boundary
2. **Business Logic Validation** — Ensure data makes sense for this operation
3. **Environment Guards** — Prevent dangerous operations in specific contexts
4. **Debug Instrumentation** — Capture context for forensics

**Example:** Adding validation at ALL four layers after tracing empty `projectDir` caused `git init` in source code.
