# 记忆系统使用

## 概述

OpenHarness 的记忆系统让 Agent 能够跨会话保持上下文和知识。记忆系统支持多种机制，包括 MEMORY.md 文件、CLAUDE.md 自动发现和会话恢复。

## 记忆存储位置

### 项目级记忆

项目记忆存储在项目目录的 `.openharness/memory/` 目录下：

```
project/
├── .openharness/
│   └── memory/
│       ├── MEMORY.md          # 记忆索引
│       ├── project-context.md
│       └── architecture.md
```

### 用户级记忆

用户级记忆位于配置目录：

```
~/.config/openharness/memory/
```

### ohmo 个人记忆

ohmo 的个人记忆位于：

```
~/.ohmo/memory/
```

## MEMORY.md 索引文件

MEMORY.md 是记忆索引文件，包含所有记忆条目的链接：

```markdown
# Memory Index

- [project-context](project-context.md)
- [architecture](architecture.md)
```

## 记忆文件格式

记忆文件使用 Markdown 格式：

```markdown
# 项目上下文

这是一个项目的关键上下文信息。

## 技术栈

- Python 3.10+
- FastAPI
- PostgreSQL

## 关键约定

- 使用 uv 管理依赖
- 代码风格遵循 ruff 规范
```

## 添加记忆

### 交互式添加

在 TUI 中使用记忆命令：

```
/memory add 项目上下文
```

### 命令行添加

```bash
# 使用 ohmo memory 命令
ohmo memory add "项目上下文" "这是一个 FastAPI 项目，使用 PostgreSQL 数据库"
```

### 手动添加

直接在 `.openharness/memory/` 目录下创建 Markdown 文件，然后更新 MEMORY.md 索引。

## 记忆搜索

OpenHarness 自动扫描相关记忆文件并注入到 Agent 上下文。搜索基于：

- 文件名
- 标题
- 内容关键词

### 触发条件

记忆注入在以下情况下触发：

1. 项目根目录存在 `.openharness/memory/`
2. 存在 MEMORY.md 或至少一个 .md 文件
3. 新会话开始时

## CLAUDE.md 自动发现

OpenHarness 支持 CLAUDE.md 文件的自动发现和注入。

### CLAUDE.md 位置

- 项目根目录
- 用户主目录（作为全局默认值）

### CLAUDE.md 内容

```markdown
# 项目指导

## 项目概述

这是一个 Python CLI 项目。

## 开发规范

- 使用 uv 管理依赖
- 遵循 PEP 8 代码风格
- 所有公共 API 需要类型注解

## 命令

- 测试: uv run pytest
- Lint: uv run ruff check
- 类型检查: uv run mypy
```

### CLAUDE.md 与记忆的区别

| 特性 | CLAUDE.md | MEMORY.md |
|------|-----------|-----------|
| 用途 | 项目指导原则 | 持久化知识 |
| 加载时机 | 会话开始时自动 | 按需搜索 |
| 内容 | 配置、指导、命令 | 事实、上下文、约定 |

## 会话恢复

OpenHarness 支持会话恢复功能，可以从中断处继续。

### 保存会话

会话在以下情况自动保存：

- 使用 `/exit` 或 `Ctrl+C` 退出
- 会话超时
- 定期自动保存

### 恢复会话

```bash
# 继续最近一次会话
oh --continue

# 按 ID 恢复指定会话
oh --resume <session_id>

# 交互式选择会话
oh --resume
```

### 会话存储

会话快照保存在：

```
~/.openharness/sessions/
```

## 记忆自动压缩

当记忆文件过多或过大时，OpenHarness 会提示进行压缩整理。

### 压缩建议

1. 合并相关记忆
2. 删除过时信息
3. 更新 MEMORY.md 索引

## 最佳实践

### 1. 保持记忆简洁

每个记忆文件应该专注于一个主题，便于检索。

### 2. 定期整理

定期检查并更新记忆，删除过时内容。

### 3. 命名规范

使用描述性文件名，便于搜索：

```
# 好
database-connection.md
api-authentication.md

# 差
note1.md
stuff.md
```

### 4.CLAUDE.md 精炼

CLAUDE.md 应该简洁，聚焦于指导原则，而非详细文档。

## 配置

在 `settings.json` 中配置记忆系统：

```json
{
  "memory": {
    "enabled": true,
    "max_files": 10,
    "max_entrypoint_lines": 200
  }
}
```

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| enabled | 是否启用记忆系统 | true |
| max_files | 最大记忆文件数 | 10 |
| max_entrypoint_lines | MEMORY.md 最大行数 | 200 |

## 常见问题

### Q: 记忆没有加载？

1. 确认 `.openharness/memory/` 目录存在
2. 检查记忆文件格式是否为 .md
3. 确保 MEMORY.md 索引正确

### Q: 如何迁移记忆？

直接复制 `.openharness/memory/` 目录到新位置。

### Q: 记忆占用空间大？

运行记忆压缩，或手动删除过时文件。
