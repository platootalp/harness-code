# Testing Anti-Patterns

**Core principle:** Test what the code does, not what the mocks do.

## The Iron Laws

```
1. NEVER test mock behavior
2. NEVER add test-only methods to production classes
3. NEVER mock without understanding dependencies
```

## Anti-Pattern 1: Testing Mock Behavior

**The violation:**
```typescript
expect(screen.getByTestId('sidebar-mock')).toBeInTheDocument();
```

**The fix:**
```typescript
expect(screen.getByRole('navigation')).toBeInTheDocument();
```

## Anti-Pattern 2: Test-Only Methods in Production

Move test utilities to test-utils/, not production classes.

## Anti-Pattern 3: Mocking Without Understanding

Mock at correct level - preserve behavior test depends on.

## Anti-Pattern 4: Incomplete Mocks

Mock COMPLETE data structure as it exists in reality.

## TDD Prevents These Anti-Patterns

1. **Write test first** → Forces thinking about what you're actually testing
2. **Watch it fail** → Confirms test tests real behavior
3. **Minimal implementation** → No test-only methods creep in
