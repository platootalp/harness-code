# Test-Driven Development (TDD)

## Core Principle

> "If you didn't watch the test fail, you don't know if it tests the right thing."

## The Iron Law

> "NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST"

## Red-Green-Refactor Cycle

1. **RED** - Write one minimal failing test
2. **Verify RED** - Confirm test fails for the right reason
3. **GREEN** - Write minimal code to pass
4. **Verify GREEN** - Confirm all tests pass
5. **REFACTOR** - Clean up without changing behavior
6. **Repeat**

## Key Requirements

- One behavior per test
- Clear, descriptive test names
- Use real code (minimize mocks)
- Watch test fail before implementing
- Write minimal code to pass

## Common Rationalizations to Avoid

| Excuse | Reality |
|--------|---------|
| "I'll test after" | Tests passing immediately prove nothing |
| "Too simple to test" | Simple code breaks; test takes 30 seconds |
| "Deleting code is wasteful" | Sunk cost fallacy |
| "TDD is dogmatic" | TDD is pragmatic |

## Verification Checklist

- [ ] Every new function/method has a test
- [ ] Watched each test fail before implementing
- [ ] Wrote minimal code to pass
- [ ] All tests pass
