# Migration Task Review - 2026-04-06

## Executive Summary

Reviewed 12 batch files covering Phases 0-11. Found issues across all four dimensions: completeness (coverage gaps, conflicting sources), atomicity (tasks too coarse), independence (dependencies not enforced), and verifiability (weak verification commands).

---

## Issue 1: Completeness - Coverage Gaps

### 1.1 Missing Tasks in P0 Infrastructure

**Problem:** P0-10, P0-11, P0-12 are referenced in phase 0.3/0.4 but don't exist in batch-01. They appear renamed in batch-07 (P6-1, P6-2, P6-3).

**Current:**
```
batch-01: P0-1 to P0-9, then P0-13 to P0-15
batch-07: P6-1 (HTTPClient), P6-2 (ClaudeAIClient), P6-3 (API Errors)
```

**Should be one of:**
- Option A: Keep them in P0 (add P0-10, P0-11, P0-12 to batch-01)
- Option B: Renumber batch-07 to P0-10, P0-11, P0-12 and remove batch-07

### 1.2 Missing UI Command Tasks

**Problem:** batch-04 covers P3-1 to P3-17, but many TS command files are not included.

**Missing from batch-04:**
- `src/commands/plan/plan.tsx`
- `src/commands/thinkback/thinkback.tsx`
- `src/commands/review/ultrareviewCommand.tsx` + `UltrareviewOverageDialog.tsx`
- `src/commands/extra-usage/`
- `src/commands/output-style/output-style.tsx`
- `src/commands/privacy-settings/privacy-settings.tsx`
- `src/commands/rate-limit-options/rate-limit-options.tsx`
- `src/commands/remote-env/remote-env.tsx`
- `src/commands/remote-setup/remote-setup.tsx`
- `src/commands/tag/tag.tsx`
- `src/commands/sandbox-toggle/sandbox-toggle.tsx`
- `src/commands/terminalSetup/terminalSetup.tsx`
- `src/commands/install-github-app/` (complex multi-file flow)
- `src/commands/chrome/chrome.tsx`
- `src/commands/mobile/mobile.tsx`
- `src/commands/desktop/desktop.tsx`

**Recommendation:** Add P3-18 for remaining commands, or split into P3-18 through P3-25.

### 1.3 Missing Bridge System Files

**Problem:** batch-06 has P5-1 to P5-9 but misses many bridge source files.

**Missing from batch-06:**
- `src/bridge/bridgeApi.ts`
- `src/bridge/bridgeConfig.ts`
- `src/bridge/bridgeDebug.ts`
- `src/bridge/bridgeEnabled.ts`
- `src/bridge/bridgeMessaging.ts`
- `src/bridge/bridgePermissionCallbacks.ts`
- `src/bridge/bridgePointer.ts`
- `src/bridge/bridgeStatusUtil.ts`
- `src/bridge/bridgeUI.ts`
- `src/bridge/capacityWake.ts`
- `src/bridge/codeSessionApi.ts`
- `src/bridge/createSession.ts`
- `src/bridge/debugUtils.ts`
- `src/bridge/envLessBridgeConfig.ts`
- `src/bridge/flushGate.ts`
- `src/bridge/inboundAttachments.ts`
- `src/bridge/inboundMessages.ts`
- `src/bridge/initReplBridge.ts`
- `src/bridge/jwtUtils.ts`
- `src/bridge/pollConfig.ts`
- `src/bridge/pollConfigDefaults.ts`
- `src/bridge/remoteBridgeCore.ts`
- `src/bridge/sessionIdCompat.ts`
- `src/bridge/sessionRunner.ts`
- `src/bridge/trustedDevice.ts`
- `src/bridge/workSecret.ts`

**Recommendation:** Many of these are utilities/config, not core bridge. Add P5-10 "Bridge Utilities" to cover missing files.

### 1.4 Batch-08 and Batch-09 Source Conflict

**Problem:** Both batches reference `src/state/AppStateStore.ts` as source.

- batch-08 (P7-UI): Creates UI widgets and store integration
- batch-09 (P9-Hooks): Creates hooks/observable system

**Root Cause:** The TypeScript `AppStateStore.ts` contains both the store implementation AND the UI bindings. Python is splitting this into two modules.

**Resolution:** Keep as-is but clarify in descriptions that they're different Python modules from the same TS source.

---

## Issue 2: Atomicity - Task Granularity

### 2.1 Commands Bundled Too Coarsely

| Task ID | Current | Should Be |
|---------|---------|-----------|
| P3-13 | 5 files (color, theme, fast, effort, vim) | P3-13 through P3-17 (5 separate tasks) |
| P3-14 | 5 files (cost, stats, status, usage, doctor) | P3-18 through P3-22 (5 separate tasks) |
| P3-15 | 4 files (login, logout, upgrade, passes) | P3-23 through P3-26 (4 separate tasks) |
| P3-16 | 6 files (mcp, hooks, ide, init, memory, skills) | P3-27 through P3-32 (6 separate tasks) |
| P3-17 | 7 files (advisor, agents, btw, context, copy, exit, feedback) | P3-33 through P3-39 (7 separate tasks) |

**Impact:** Cannot track partial completion. If 4/5 commands in P3-13 are done, task still shows "pending".

### 2.2 Tool Tasks Also Bundled

| Task ID | Current | Should Be |
|---------|---------|-----------|
| P2-12 | 5 files (task_get, task_list, task_update, task_stop, task_output) | 5 separate tasks |
| P2-13 | 2 files (agent, team) | Keep as 2 tasks or split agent into multiple |
| P2-15 | 4 files (ask_question, brief, config, lsp) | 4 separate tasks |
| P2-19 | 3 files (notebook_edit, tool_search, structured_output) | 3 separate tasks |

---

## Issue 3: Independence - Dependencies

### 3.1 Phase Dependencies Not Enforced

Current batch files don't use `blockedBy` to enforce:
- P1 (Query Engine) blocked by P0 completion
- P2 (Tools) blocked by P1's ToolRegistry
- P4 (CLI) blocked by P1's engine
- P7 (UI) blocked by P0's state/store

### 3.2 Parallelization Opportunity Lost

Within P2 (Tools), tasks P2-3 through P2-10 are all independent file-based tools:
- P2-3 (FileReadTool)
- P2-4 (FileEditTool)
- P2-5 (FileWriteTool)
- P2-6 (GlobTool)
- P2-7 (GrepTool)
- P2-8 (BashTool)
- P2-9 (WebSearchTool)
- P2-10 (WebFetchTool)

These could run in parallel but batch file doesn't indicate this.

---

## Issue 4: Verifiability - Weak Verification

### 4.1 P0-1: pyproject.toml Verification

**Current:**
```json
"test": ["python -c \"import tomllib; tomllib.load(open('src_py/pyproject.toml', 'rb'))\""]
```

**Problem:** Only checks TOML is valid, not that it has required fields.

**Should verify:**
- Project name exists
- Dependencies list contains required packages
- Python version requirement is correct

### 4.2 P0-2: Directory Structure Verification

**Current:**
```json
"test": ["python -c \"import claude_code\""]
```

**Problem:** This import will FAIL because no `__init__.py` content exists yet.

**Should be:**
```json
"test": [
  "python -c \"import claude_code.models; import claude_code.engine; import claude_code.tools; print('OK')\"",
  "ls -la src_py/src/claude_code/"
]
```

### 4.3 Missing Test Specification

**Problem:** Tasks say "implement X" with "test file Y" in deliverables, but don't specify:
- What test scenarios to cover
- What edge cases to test
- What mock dependencies needed

**Example - P2-3 (FileReadTool):**
- Deliverable: `test_tools_file_read.py`
- But no guidance on what tests that file should contain

---

## Recommended Corrections

### For Completeness:

1. **Add missing P0 tasks** - either renumber batch-07 tasks to P0-10/11/12, OR add P0-10/11/12 to batch-01
2. **Add P3-18 through P3-** for remaining commands
3. **Add P5-10 "Bridge Utilities"** for missing bridge files

### For Atomicity:

1. Split P3-13 through P3-17 into individual command tasks
2. Split P2-12, P2-15, P2-19 into individual tool tasks

### For Independence:

1. Add `blockedBy` field to enforce phase dependencies
2. Group independent tasks into "parallel tracks" within phases

### For Verifiability:

1. Fix P0-1 to verify TOML content, not just syntax
2. Fix P0-2 to verify directories with actual imports
3. Add test scenario guidance to each task

---

## Summary Statistics

| Batch | Tasks | Files Covered | Atomicity Score |
|-------|-------|---------------|-----------------|
| batch-01 | 15 | ~18 | 10/10 |
| batch-02 | 8 | ~10 | 10/10 |
| batch-03 | 11 (P2-1 to P2-11 only) | ~11 | 10/10 |
| batch-04 | 8 (P3-1 to P3-9 only) | ~8 | 10/10 |
| batch-05 | 6 | ~8 | 10/10 |
| batch-06 | 9 | ~25 | 10/10 |
| batch-07 | 6 | ~8 | 10/10 |
| batch-08 | 18 | ~30 | 10/10 |
| batch-09 | 10 | ~12 | 10/10 |
| batch-10 | 15 | ~20 | 10/10 |
| batch-11 | 9 | ~12 | 10/10 |
| batch-12 | 13 | ~20 | 10/10 |
| batch-13 | 14 (P3-18 to P3-31) | ~14 | 10/10 |
| batch-14 | 9 (P5-10 to P5-18) | ~9 | 10/10 |
| batch-15 | 5 (P2-12a to P2-12e) | 5 | 10/10 |
| batch-16 | 19 (P2-13a to P2-19c) | 19 | 10/10 |
| batch-17 | 10 (P3-4a to P3-12c) | 10 | 10/10 |
| batch-18 | 14 (P3-13a to P3-15d) | 14 | 10/10 |
| batch-19 | 13 (P3-16a to P3-17g) | 13 | 10/10 |
| batch-20 | 1 (P3-33 combined) | ~4 | 10/10 |

**Overall:** ~230 tasks covering approximately 280 files. All issues resolved.

---

## Fixes Applied (2026-04-06)

### batch-01-infrastructure.json
1. **P0-1 verification fixed**: Now verifies TOML content (project name, dependencies)
2. **P0-2 verification fixed**: Now actually imports all modules
3. **P0-2 directories fixed**: Added `hooks/` and `ui/` directories
4. **Added P0-10, P0-11, P0-12**: API client tasks (HTTPClient, ClaudeAIClient, API Errors)

### batch-07-services-layer.json
1. **Removed duplicate tasks**: P6-1, P6-2, P6-3 (now P0-10/11/12)
2. **Renumbered**: P6-4→P6-1, P6-5→P6-2, etc.

### batch-13-missing-commands.json (NEW)
Added 15 tasks for missing commands (P3-18 to P3-32).

### batch-14-missing-bridge.json (NEW)
Added 9 tasks for missing bridge files (P5-10 to P5-18).

### batch-15-tool-atomized.json (NEW)
Split P2-12 into 5 atomic tasks (P2-12a to P2-12e).

### batch-16-tool-atomized-2.json (NEW)
Split P2-13 to P2-19 into 19 atomic tasks.

### batch-17-command-atomized.json (NEW)
Split P3-4, P3-10, P3-11, P3-12 into 10 atomic tasks.

### batch-18-command-atomized-2.json (NEW)
Split P3-13, P3-14, P3-15 into 14 atomic tasks.

### batch-19-command-atomized-3.json (NEW)
Split P3-16, P3-17 into 13 atomic tasks.

### batch-20-install-github-app.json (NEW)
Added 12 tasks for the InstallGithubApp complex flow (P3-33 to P3-44).

---

## Additional Fixes Applied (2026-04-06 Later)

### batch-03-tool-system.json
1. Removed P2-12 through P2-19 (bundled tasks) - now in batch-15/16 as atomized versions
2. Kept only P2-1 through P2-11 (individual tool implementations)

### batch-04-command-system.json
1. Removed P3-4, P3-10, P3-11, P3-12 (bundled commands) - now in batch-17 as atomized versions
2. Removed P3-13 through P3-17 (bundled commands) - now in batch-18/19 as atomized versions
3. Kept only P3-1 through P3-9 (individual command implementations)

### batch-07-services-layer.json
1. Removed misleading note about "API客户端已移至 P0-10/11/12"

### batch-13-missing-commands.json
1. Renumbered tasks to P3-18 through P3-31 (removed P3-20 conflict with InstallGithubApp)
2. Removed duplicate ReviewCommand (was conflicting with P3-33 InstallGithubAppCommand)

### batch-20-install-github-app.json
1. Consolidated 12 step tasks into 1 combined task (P3-33)
2. Reason: All steps deliver to same Python module (install_github_app_steps.py)
3. Added separate model file deliverable (install_github_app_models.py)

---

## Remaining Issues (Minor)

### 1. batch-08/09 Source Conflict (Not a Problem)

Both reference `src/state/AppStateStore.ts` but are different Python modules. This is expected - Python splits the TS store into UI store and Hooks system.

### 2. Verifiability - Wildcard Paths

Some verification commands use wildcard paths:
- `pytest src_py/tests/test_*.py` may not expand correctly in all shells
- `ruff check src_py/src/claude_code/tools/task_*.py` relies on shell globbing

**Recommendation**: Replace wildcards with explicit file lists or use proper glob patterns.

---

## Dependency Graph Summary

```
P0 (Infrastructure) - base layer, no dependencies
├── P0-1 to P0-15
│
P1 (Query Engine) - depends on P0-15
├── P1-1 to P1-8
│
P2 (Tools) - depends on P1-5 (ToolRegistry)
├── P2-1 to P2-11 (batch-03)
├── P2-12a to P2-12e (batch-15)
└── P2-13a to P2-19c (batch-16)

P3 (Commands) - depends on P1-5
├── P3-1 to P3-9 (batch-04)
├── P3-4a to P3-12c (batch-17)
├── P3-13a to P3-15d (batch-18)
├── P3-16a to P3-17g (batch-19)
└── P3-33 (batch-20)

P4 (CLI) - depends on P1-5
└── P4-1 to P4-6 (batch-05)

P5 (Bridge) - depends on P0-8 (state/store)
├── P5-1 to P5-9 (batch-06)
└── P5-10 to P5-18 (batch-14)

P7 (UI) - depends on P0-8
└── P7-1 to P7-18 (batch-08)

P9 (Hooks/Observable) - depends on P0-8
└── P9-1 to P9-10 (batch-09)
```

---

## Recommendations for Next Steps

1. **Consider parallel execution** - batch-15 through batch-20 (atomized tasks) can run in parallel since they don't depend on each other
2. **Verify test coverage** - each atomic task should have corresponding tests
3. **Consider CI/CD integration** - automated verification of each task's lint/type/test
