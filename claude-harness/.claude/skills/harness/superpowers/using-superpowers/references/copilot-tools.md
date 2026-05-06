# Copilot CLI Tool Mapping

Skills use Claude Code tool names. When you encounter these in a skill, use your platform equivalent:

| Skill references | Copilot CLI equivalent |
|-----------------|----------------------|
| `Read` | `view` |
| `Write` | `create` |
| `Edit` | `edit` |
| `Bash` | `bash` |
| `Grep` | `grep` |
| `Glob` | `glob` |
| `Skill` tool | `skill` |
| `WebFetch` | `web_fetch` |
| `Task` tool | `task` |
| `TodoWrite` | `sql` with built-in `todos` table |

## Agent types

| Claude Code agent | Copilot CLI equivalent |
|-------------------|----------------------|
| `general-purpose` | `"general-purpose"` |
| `Explore` | `"explore"` |
| Named plugin agents | Discovered automatically from installed plugins |

## Async shell sessions

| Tool | Purpose |
|------|---------|
| `bash` with `async: true` | Start long-running command in background |
| `write_bash` | Send input to running async session |
| `read_bash` | Read output from async session |
