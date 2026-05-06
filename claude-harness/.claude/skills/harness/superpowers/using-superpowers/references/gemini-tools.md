# Gemini CLI Tool Mapping

Skills use Claude Code tool names. This documents Gemini CLI equivalents.

## Tool Mapping

| Claude Code | Gemini CLI |
|------------|-----------|
| `Read/Write/Edit` | `read_file`/`write_file`/`replace` |
| `Bash` | `run_shell_command` |
| `Grep/Glob` | `grep_search`/`glob` |
| `TodoWrite` | `write_todos` |
| `Skill` | `activate_skill` |
| `WebSearch/WebFetch` | `google_web_search`/`web_fetch` |

## Key Limitation

Gemini CLI lacks a `Task` tool equivalent, so subagent-driven skills fall back to single-session execution.
