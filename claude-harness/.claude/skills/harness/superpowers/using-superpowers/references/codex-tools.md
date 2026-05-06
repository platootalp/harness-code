# Codex Tools Mapping

Skills use Claude Code tool names. This documents Codex equivalents.

## Tool Mapping

| Claude Code | Codex |
|-------------|-------|
| `Task` tool (dispatch) | `spawn_agent` |
| Multiple parallel `Task` | Multiple `spawn_agent` calls |
| Task returns | `wait` |
| Task completion | `close_agent` |
| `TodoWrite` | `update_plan` |
| `Skill` tool | Native skill loading |
| `Read/Write/Edit` | Native file tools |
| `Bash` | Native shell tools |

## Named Agent Dispatch

Codex lacks a named agent registry. To dispatch named agents (like `superpowers:code-reviewer`), read the agent's prompt file, fill template placeholders, and spawn a `worker` agent.

## Configuration

Multi-agent support requires `[features] multi_agent = true` in `~/.codex/config.toml`.

## Sandbox Limitations

When environment blocks branch operations (detached HEAD in external worktree), commit work and inform the user.
