# TASK-SYSTEM.md Review Findings

## Review Summary

Reviewed by: Claude Code analysis of source at `/Users/lijunyi/road/reference/harness-code/harness/claude-code/`

Date: 2026-04-20

Overall assessment: Document is largely accurate but has several issues requiring fixes.

---

## Issue 1: Mermaid subgraph with `["Label"]` pattern - INVALID (CRITICAL)

**Location**: Lines 270, 274

**Problem**: The pattern `subgraph 0-30秒[宽限期 30 秒]` uses `["label"]` syntax which is invalid in Mermaid. The correct syntax for subgraph labels with special characters is `subgraph name["label"]` where the name is an identifier and the label is quoted.

**Current (INVALID)**:
```
subgraph 0-30秒[宽限期 30 秒]
subgraph 30秒后[30 秒后]
```

**Fix required**:
```
subgraph zero_to_thirty_sec["宽限期 30 秒"]
subgraph after_thirty_sec["30 秒后"]
```

Note: Mermaid subgraph labels with special characters (Chinese, spaces, etc.) need to be quoted with double quotes in the label portion. The `["label"]` syntax is not valid Mermaid.

---

## Issue 2: `claimTask()` documentation is incomplete

**Location**: Section 1.2, lines 64-75

**Problem**: The document only shows part of the `claimTask()` logic. It omits:
1. The `checkAgentBusy` option that checks if the agent already owns other open tasks
2. The `agent_busy` failure reason
3. The `already_claimed` check (task already owned by another agent)

**Actual implementation** (from `utils/tasks.ts` lines 574-593):
```typescript
// Check if already claimed by another agent
if (task.owner && task.owner !== claimantAgentId) {
  return { success: false, reason: 'already_claimed', task }
}

// Check if already resolved
if (task.status === 'completed') {
  return { success: false, reason: 'already_resolved', task }
}

// Check for unresolved blockers (open or in_progress tasks block)
const unresolvedTaskIds = new Set(
  allTasks.filter(t => t.status !== 'completed').map(t => t.id),
)
const blockedByTasks = task.blockedBy.filter(id =>
  unresolvedTaskIds.has(id),
)
if (blockedByTasks.length > 0) {
  return { success: false, reason: 'blocked', task, blockedByTasks }
}
```

**Fix required**: Add the complete claim logic including `already_claimed` and `already_resolved` checks.

---

## Issue 3: `getTeamName()` routing priority is misdescribed

**Location**: Section 1.3, lines 82-95 (the routing code snippet)

**Problem**: The comment says "进程内 teammate → 用 teamName（与 tmux/iTerm2 teammates 共享）" but `getTeamName()` in `utils/teammate.ts` has this priority:
1. `getTeammateContext().teamName` - in-process teammates
2. `dynamicTeamContext?.teamName` - tmux/iTerm2 teammates via CLI args
3. `teamContext?.teamName` - explicit team context

The tmux/iTerm2 routing goes through `dynamicTeamContext.teamName`, NOT `teammateCtx`. The document correctly shows `teammateCtx` in the code snippet but the comment conflates in-process teammates with tmux/iTerm2 teammates.

**Fix required**: Clarify in the comment that `teammateCtx` refers to in-process teammates only, and tmux/iTerm2 teammates use `dynamicTeamContext` (via `getTeamName()`).

---

## Issue 4: File path reference inconsistency

**Location**: Section 8.5, line 489

**Problem**: The code comment shows `// TodoWriteTool.tsx` but the actual file is `tools/TodoWriteTool/TodoWriteTool.ts` (`.ts` not `.tsx`).

**Fix required**: Change `TodoWriteTool.tsx` to `TodoWriteTool.ts`.

---

## Issue 5: Section numbering is non-sequential

**Location**: Section 8 (八), then jumps to 11 (十一)

**Problem**: The document skips sections 9 and 10 (九、十). This is likely intentional (the document may have been reorganized), but it should be verified or sections added for consistency.

---

## Verified Accurate Sections

The following sections match the source code correctly:

- Task type prefixes and ID format (Section 2.1, 2.3) - verified in `Task.ts`
- `PANEL_GRACE_MS = 30_000` - verified in `utils/task/framework.ts`
- `registerTask()`, `updateTaskState()`, `pollTasks()`, `evictTerminalTask()`, `applyTaskOffsetsAndEvictions()` - all verified in `utils/task/framework.ts`
- `enqueueAgentNotification()` signature and XML format - verified in `tasks/LocalAgentTask/LocalAgentTask.tsx`
- `stopTask()` implementation - verified in `tasks/stopTask.ts`
- `getTaskListId()` priority - verified in `utils/tasks.ts`
- `getAllTasks()` and `getTaskByType()` - verified in `tasks.ts`
- `TodoWriteTool` `todoKey` logic (`context.agentId ?? getSessionId()`) - verified in `tools/TodoWriteTool/TodoWriteTool.ts`

---

## Summary of Required Fixes

| # | Issue | Severity | Fix |
|---|-------|----------|-----|
| 1 | Mermaid `["Label"]` pattern invalid | CRITICAL | Change subgraph labels to use valid Mermaid syntax |
| 2 | `claimTask()` docs incomplete | Medium | Add `already_claimed` and `already_resolved` checks |
| 3 | `getTeamName()` routing comment | Low | Clarify in-process vs tmux/iTerm2 routing |
| 4 | File extension `.tsx` vs `.ts` | Low | Fix file extension in code comment |
| 5 | Missing section numbers | Low | Verify if intentional or needs correction |

---

## Note on Read-Only Mode

Per the system constraints, this review was conducted in READ-ONLY mode. The fixes listed above need to be applied manually or by a session with write permissions.
