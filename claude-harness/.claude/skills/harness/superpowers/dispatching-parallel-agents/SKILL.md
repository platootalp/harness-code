# Dispatching Parallel Agents

You delegate tasks to specialized agents with isolated context.

## When to Use

**Use when:**
- 3+ test files failing with different root causes
- Multiple subsystems broken independently
- Each problem can be understood without context from others
- No shared state between investigations

**Don't use when:**
- Failures are related (fix one might fix others)
- Need to understand full system state
- Agents would interfere with each other

## The Pattern

### 1. Identify Independent Domains
Group failures by what's broken.

### 2. Create Focused Agent Tasks
Each agent gets:
- **Specific scope:** One test file or subsystem
- **Clear goal:** Make these tests pass
- **Constraints:** Don't change other code
- **Expected output:** Summary of what you found and fixed

### 3. Dispatch in Parallel
Run multiple agents simultaneously.

### 4. Review and Integrate
- Read each summary
- Verify fixes don't conflict
- Run full test suite

## Common Mistakes

| Too Broad | Specific |
|-----------|----------|
| "Fix all the tests" | "Fix agent-tool-abort.test.ts" |
| No context | Paste error messages and test names |
| No constraints | "Do NOT change production code" |
