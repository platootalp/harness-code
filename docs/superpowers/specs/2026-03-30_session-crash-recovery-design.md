# Session 模块崩溃恢复设计

## 1. 背景

Session 模块原设计聚焦于基本 CRUD 操作，缺少对以下场景的支持：
- 进程崩溃后的会话恢复
- LLM API 调用中断后的恢复

本文档补充崩溃恢复机制的设计。

## 2. 设计原则

| 原则 | 说明 |
|------|------|
| 消息优先持久化 | 每条消息发送后立即保存，不依赖定时器 |
| 简化恢复流程 | 用户通过 `resume <session-id>` 显式恢复会话 |
| 不保存运行时状态 | Orchestrator 工作循环阶段属于运行时状态，崩溃后不恢复 |
| 流式输出持久化 | 流式输出过程中渐进式保存，崩溃后可恢复 |

## 3. 崩溃恢复流程

```
进程崩溃
    │
    ▼
用户重新启动 Mozi
    │
    ▼
用户执行: resume <session-id>
    │
    ▼
系统加载 Session（从最后一条已保存消息）
    │
    ▼
Orchestrator 重新理解用户意图
（工作循环从头开始决策，不恢复运行时状态）
```

### 3.1 resume 命令行为

```
resume <session-id>
    │
    ├──► Session 不存在 → 报错：Session not found
    │
    └──► Session 存在
            │
            ├──► 加载 session
            ├──► 获取最后一条消息
            ├──► 展示 "Resuming session <id>, last message:"
            ├──► 显示最后一条消息内容
            └──► 继续工作循环
```

## 4. 配置变更

`SessionConfig` 配置项变更：

| 配置项 | 原值 | 新值 | 说明 |
|--------|------|------|------|
| `auto_save_message_count` | 10 | **1** | 每条消息后立即保存 |

## 5. 消息持久化时机

| 时机 | 是否保存 | 说明 |
|------|----------|------|
| 用户消息发送后 | ✅ | 立即保存 |
| LLM 响应接收后（完整） | ✅ | 立即保存 |
| 流式输出过程中 | ✅ | 边输出边保存到 `streaming_content` 字段 |
| 工具调用结果返回 | ✅ | 立即保存 |

### 5.1 流式输出持久化

流式输出时，通过 `streaming_content` 字段渐进式保存：

```python
@dataclass
class Message:
    role: MessageRole
    content: str                    # 最终完整内容
    streaming_content: str = ""    # 流式输出过程中的渐进内容
    is_streaming: bool = False     # 是否正在流式输出
```

| 阶段 | streaming_content | is_streaming | content |
|------|-------------------|--------------|---------|
| 开始流式输出 | "" | True | "" |
| 流式输出中 | 渐进更新 | True | "" |
| 流式输出完成 | → content | False | 完整内容 |

崩溃恢复时：
- 如果 `is_streaming == True`，使用 `streaming_content` 作为上下文继续
- Orchestrator 重新发送 LLM 请求，带上已输出的内容作为 `continue_from` 参数

## 6. 相关模块职责

| 模块 | 职责 |
|------|------|
| Session | 消息持久化，加载恢复 |
| Orchestrator | 不保存运行时状态，恢复后从头决策 |
| Task | Task 自身负责持久化，恢复时由 Orchestrator 重新委托 |
| Memory | 按原有机制工作，不受崩溃恢复影响 |

## 7. 无需实现的功能

以下功能**不需要**实现：

| 功能 | 原因 |
|------|------|
| Checkpoint 机制 | 消息立即持久化后无需 checkpoint |
| 运行时状态保存 | Orchestrator 工作循环阶段属于运行时状态，崩溃后不恢复 |
| 自动恢复 | 用户显式执行 `resume` 命令恢复 |

## 8. 变更记录

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| 1.1 | 2026-03-30 | 支持流式输出持久化 |
| 1.0 | 2026-03-30 | 初始版本，补充崩溃恢复机制 |

---

_版本: 1.1_
_更新日期: 2026-03-30_
