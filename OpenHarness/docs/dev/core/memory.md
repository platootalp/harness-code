# 记忆系统

本文档介绍 OpenHarness 的持久化记忆系统，包括上下文压缩和跨会话知识存储。

## 概述

OpenHarness 的记忆系统提供：
- 跨会话持久化知识
- 上下文自动压缩
- CLAUDE.md 自动发现和注入
- MEMORY.md 记忆入口

## 架构概览

```
src/openharness/memory/
├── __init__.py      # 包初始化
├── memdir.py        # 记忆目录处理
├── paths.py         # 路径管理
├── manager.py       # 记忆管理器
└── types.py         # 类型定义
```

## 核心概念

### 记忆文件结构

```
~/.openharness/
├── memory/                    # 全局记忆目录
│   ├── MEMORY.md             # 主记忆文件
│   ├── project-name/         # 项目特定记忆
│   │   ├── MEMORY.md
│   │   └── topics/           # 主题文件
│   └── ...
└── settings.json

project/
├── MEMORY.md                 # 项目记忆（自动发现）
└── .claude/                  # Claude Code 兼容
    └── CLAUDE.md
```

### 记忆入口 (MEMORY.md)

MEMORY.md 是记忆系统的入口文件：

```markdown
# Memory

## 项目概述
这是一个 Python 项目...

## 重要上下文
- 使用 uv 作为包管理器
- 主要依赖在 pyproject.toml

## 已知问题
- 某模块存在性能问题 (#123)

## 待办
- [ ] 重构 auth 模块
- [ ] 优化数据库查询
```

## 记忆加载

### 加载记忆提示

```python
def load_memory_prompt(
    cwd: str | Path,
    *,
    max_entrypoint_lines: int = 200,
) -> str | None:
    memory_dir = get_project_memory_dir(cwd)
    entrypoint = get_memory_entrypoint(cwd)

    lines = [
        "# Memory",
        f"- Persistent memory directory: {memory_dir}",
        "- Use this directory to store durable user or project context...",
        "- Prefer concise topic files plus an index entry in MEMORY.md.",
    ]

    if entrypoint.exists():
        content_lines = entrypoint.read_text(encoding="utf-8").splitlines()
        lines.extend(["", "## MEMORY.md", "```md", *content_lines, "```"])
    else:
        lines.extend(["", "## MEMORY.md", "(not created yet)"])

    return "\n".join(lines)
```

### 记忆目录解析

```python
def get_project_memory_dir(cwd: str | Path) -> Path:
    """返回项目特定的记忆目录"""
    return get_config_dir() / "memory" / slugify_project(cwd)


def get_memory_entrypoint(cwd: str | Path) -> Path:
    """返回记忆入口文件"""
    return get_project_memory_dir(cwd) / "MEMORY.md"
```

## 上下文压缩

### 自动压缩流程

当对话历史过长时，系统自动压缩：

```python
async def auto_compact_if_needed(
    messages: list[ConversationMessage],
    api_client: SupportsStreamingMessages,
    model: str,
    system_prompt: str,
    state: AutoCompactState,
) -> tuple[list[ConversationMessage], bool]:
    # 1. 估算 Token 数量
    estimated_tokens = estimate_token_count(messages, system_prompt)

    # 2. 检查是否超过阈值
    if estimated_tokens < AUTO_COMPACT_THRESHOLD:
        return messages, False

    # 3. Microcompact: 清理旧工具结果
    if state.microcompact_attempts < MAX_MICROCOMPACT_ATTEMPTS:
        messages = microcompact(messages)
        state.microcompact_attempts += 1
        return messages, True

    # 4. Full compact: 使用 LLM 总结
    summary = await summarize_messages(
        api_client,
        model,
        messages,
    )
    messages = replace_old_messages_with_summary(messages, summary)
    return messages, True
```

### Microcompact

清理旧工具结果的内容，保留结构：

```python
def microcompact(
    messages: list[ConversationMessage],
) -> list[ConversationMessage]:
    # 保留用户消息和助手消息的结构
    # 将工具结果替换为简短摘要
    for msg in messages:
        for block in msg.content:
            if isinstance(block, ToolResultBlock):
                block.content = f"[{block.tool_name}: {len(block.content)} bytes]"
    return messages
```

### Full Compact

使用 LLM 生成总结：

```python
async def summarize_messages(
    api_client: SupportsStreamingMessages,
    model: str,
    messages: list[ConversationMessage],
) -> str:
    request = ApiMessageRequest(
        model=model,
        messages=[ConversationMessage.from_user_text(
            "请总结以下对话的要点，保留关键信息和决定：\n\n"
            + format_messages_for_summary(messages)
        )],
        system_prompt="你是一个助手，负责总结对话。",
        max_tokens=1024,
    )

    summary_parts = []
    async for event in api_client.stream_message(request):
        if isinstance(event, ApiTextDeltaEvent):
            summary_parts.append(event.text)

    return "".join(summary_parts)
```

## CLAUDE.md 集成

### 自动发现

OpenHarness 自动发现项目中的 CLAUDE.md：

```python
def find_claudemd(cwd: str | Path) -> Path | None:
    """查找 CLAUDE.md 文件"""
    search_paths = [
        Path(cwd) / "CLAUDE.md",
        Path(cwd) / ".claude" / "CLAUDE.md",
        Path(cwd) / ".claude.md",
    ]

    for path in search_paths:
        if path.exists():
            return path

    return None
```

### 注入 CLAUDE.md 内容

```python
def build_system_prompt(
    custom_prompt: str | None = None,
    env: EnvironmentInfo | None = None,
    cwd: str | None = None,
) -> str:
    base = custom_prompt if custom_prompt is not None else _BASE_SYSTEM_PROMPT

    # 添加环境信息
    env_section = _format_environment_section(env)

    # 添加 CLAUDE.md 内容（如果存在）
    claudemd_path = find_claudemd(cwd)
    claudemd_section = ""
    if claudemd_path:
        claudemd_content = claudemd_path.read_text()
        claudemd_section = f"\n\n# CLAUDE.md\n\n{claudemd_content}"

    return f"{base}\n\n{env_section}{claudemd_section}"
```

## 持久化记忆

### 记忆写入

模型可以使用 skill 工具写入记忆：

```python
class SkillTool(BaseTool):
    async def execute(self, args: SkillInput, ctx: ToolExecutionContext) -> ToolResult:
        if args.name == "memory":
            # 写入记忆
            memory_path = get_memory_entrypoint(ctx.cwd)
            memory_path.parent.mkdir(parents=True, exist_ok=True)
            memory_path.write_text(args.content)
            return ToolResult(output=f"Memory saved to {memory_path}")
```

### 记忆结构建议

```
memory/
├── MEMORY.md              # 主入口（必需）
├── project-overview.md     # 项目概述
├── architecture.md         # 架构笔记
├── decisions/              # 决策记录
│   └── 001-use-uv.md
├── todos/                 # 待办事项
│   └── active.md
└── topics/                # 主题知识
    ├── auth-patterns.md
    └── api-design.md
```

## 记忆设置

### MemorySettings

```python
class MemorySettings(BaseModel):
    enabled: bool = True                    # 是否启用记忆
    max_files: int = 5                     # 最大记忆文件数
    max_entrypoint_lines: int = 200        # 入口最大行数
```

## 与其他模块的关系

- **QueryEngine**: 上下文压缩在查询循环中触发
- **Prompts**: CLAUDE.md 注入系统提示
- **Skills**: 技能可以访问记忆
- **Settings**: 记忆配置存储在 Settings 中

## 使用建议

### 1. 保持 MEMORY.md 简洁

MEMORY.md 应该是一个索引，指向详细的主题文件。

### 2. 使用主题文件

详细知识放在主题文件中，MEMORY.md 只是一个概览。

### 3. 定期清理

定期审查和更新 MEMORY.md，删除过时的信息。

### 4. 关键决策记录

将重要的架构决策记录在 decisions/ 目录中。
