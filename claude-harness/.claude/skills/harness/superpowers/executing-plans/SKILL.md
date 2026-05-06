# Executing Plans Skill

## Core Process

1. **Load and Review** - Read plan, review critically, raise concerns before starting
2. **Execute Tasks** - Mark in_progress, follow steps exactly, run verifications, mark completed
3. **Complete Development** - Use the finishing-a-development-branch skill

## Key Principles

- Stop immediately when blocked or instruction is unclear
- Don't skip verifications
- Never implement on main/master without consent
- Announce: "I'm using the executing-plans skill to implement this plan"

## Required Integration

- **superpowers:using-git-worktrees** - Set up isolated workspace
- **superpowers:writing-plans** - Creates plans this skill executes
- **superpowers:finishing-a-development-branch** - Complete development
