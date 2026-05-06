# Finishing a Development Branch

## Core Workflow

1. Announce the skill usage
2. Verify tests pass before proceeding
3. Determine the base branch
4. Present exactly 4 options to the user
5. Execute the chosen option
6. Clean up the worktree when appropriate

## The Four Options

1. Merge locally to the base branch
2. Push and create a Pull Request
3. Keep the branch for later
4. Discard the work entirely

## Key Safeguards

- Tests must pass before presenting options
- Option 4 requires typed "discard" confirmation
- Worktree cleanup only for options 1 and 4
- Never force-push without explicit request

## Integration Points

Pairs with "using-git-worktrees" skill for cleanup.
