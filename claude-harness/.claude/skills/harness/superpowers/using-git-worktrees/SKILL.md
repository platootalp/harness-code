# Using Git Worktrees

## Key Workflow

1. **Directory Selection** (in priority order):
   - Check for existing `.worktrees/` or `worktrees/` directories
   - Look for CLAUDE.md preferences
   - Ask user if neither exists

2. **Safety Verification** (for project-local directories):
   - Must verify directory is gitignored before creating worktree
   - If not ignored, add to .gitignore and commit first

3. **Creation Steps**:
   - Detect project name
   - Create worktree with new branch
   - Auto-detect and run project setup
   - Run tests to verify clean baseline

## Critical Rules

- Always verify `.gitignore` status before creating project-local worktrees
- Never proceed with failing tests without explicit permission
- Follow priority order: existing directory > CLAUDE.md preference > ask user

## Integration

Required before executing implementation plans or any tasks requiring isolation.
