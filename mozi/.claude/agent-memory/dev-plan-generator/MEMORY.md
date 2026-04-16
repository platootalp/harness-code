# Dev Plan Generator Memory

## Project: Mozi AI Coding Agent

## Key Patterns

### Task Decomposition Heuristics
- Foundation tasks (init, config) are complexity 1-2
- Core feature tasks are complexity 2-3
- Integration/ orchestration tasks are complexity 2-3
- Test tasks tend to be higher complexity due to mocking requirements

### Batch Sizing Guidelines
- D0 (Foundation): ~3 days, 2-3 tasks
- D1 (Infrastructure + Capabilities): ~9-10 days, 4-5 tasks
- D2 (Orchestration): ~7-8 days, 4-5 tasks
- D3 (Integration): ~3-4 days, 2-3 tasks
- Total: ~22-25 days for MVP

### Dependency Patterns
- First batch (D0) has no dependencies
- Each subsequent batch depends on the previous batch's branch
- Within a batch: parallel tasks should have minimal interdependencies
- Tool framework often becomes a dependency for agent runtime

### Common Pitfalls
- Async modules must not have circular imports
- Database initialization must happen before use
- Config loader depends on schema definitions
- Agent runtime has many dependencies (model, tools, session, orchestrator core)

### Worktree Naming Convention
- Pattern: `feature/d{N}-{short-name}`
- Example: `feature/d0-infrastructure`, `feature/d1-core-features`
- Worktree path: `./worktrees/d{N}-{short-name}`

## MVP v1.0 Task Count
- Total: 16 tasks
- Phases: 6 (Foundation, Infrastructure, Capabilities, Orchestrator, CLI, Integration)

## Files
- Plan document: `docs/superpowers/plans/2026-03-26-mozi-mvp-v1.0-dev-plan.md`
