# src_py 功能验收清单

**日期**: 2026-04-03
**审查轮次**: 两轮（首轮并行审查 + 二轮验证）
**版本**: 1.0

---

## 执行摘要

| 维度 | 评级 | 状态 |
|------|------|------|
| 功能完整性 | B+ | ⚠️ 需修复 |
| 代码质量 | B | ⚠️ 需修复 |
| 测试覆盖 | C | ⚠️ 需修复 |
| 安全性 | **C** | 🔴 严重 |
| 架构设计 | **C** | 🔴 严重 |

**通过标准**: 所有维度达到 B+ 且无 H 级别问题

---

## 维度一：功能完整性 — 评级 B+

### P0 问题（已修复）
~~Memory Store~~ — ✅ 已完全实现（Mem0Client、MilvusClient、内存后端）

### P1 问题（需处理）

| # | 模块 | 问题 | 证据 | 建议 |
|---|------|------|------|------|
| 1 | `state_sync/syncer.py` | 静默异常吞噬导致连接失败难以调试 | `reconnect_with_replay()` line 139: `except Exception: pass` | 添加 logger.warning |
| 2 | `api/client.py` | 流式事件 `content_block_start`、`message_delta`、`message_stop` 处理不完整 | line 249-297 | 完善事件处理逻辑 |
| 3 | `observability/span_processors.py` | 抽象方法为空占位，无法真正导出 spans | `SpanProcessor.on_start()` line 46-48: `pass` | 实现 OTLP 导出 |

### P2 问题（次要）

| # | 模块 | 问题 | 证据 |
|---|------|------|------|
| 1 | `state_sync/publisher.py` | 队列满时静默丢弃事件 | `publish()`: QueueFull 被忽略 |
| 2 | `observability/tracer.py` | 观察者通知异常被静默忽略 | `_notify_observers()` line 87-88 |

### 验收标准检查清单

- [ ] Memory Store 有真实后端（非占位）
- [ ] State Sync 至少一种连接可用（非空 pass）
- [ ] 流式响应完整解析（无空操作分支）
- [ ] 异常不被静默忽略（添加日志或重抛）
- [ ] Observability span processors 有实际导出逻辑

---

## 维度二：代码质量 — 评级 B

### 严重问题（H）

| # | 问题 | 证据 | 文件:行 |
|---|------|------|---------|
| 1 | God Class — `AgentOrchestrator` 540 行过多职责 | task management, agent lifecycle, message routing, context compression, error handling, circuit breaker, event loop, shutdown 全部在一个类 | `orchestrator/orchestrator.py:201-741` |
| 2 | 静默异常吞噬 — StateStore 多处 `except Exception: pass` | WAL 写入、快照创建、订阅通知失败全部静默忽略 | `state/store.py:100-291` (10+ 处) |
| 3 | 静默异常吞噬 — StateSyncer 连接方法空实现 | WebSocket/SSE/Polling send/replay 异常被忽略 | `state_sync/syncer.py:82-374` |

### 中等问题（M）

| # | 问题 | 证据 | 文件:行 |
|---|------|------|---------|
| 1 | 事件缓冲区满时静默丢弃 | `except Exception: pass` | `orchestrator/orchestrator.py:698-708` |
| 2 | 审计日志失败静默忽略 | `except Exception: pass` | `security/layer.py:66` |
| 3 | 重复代码 — 三个 Connection 类模式相同 | WebSocket/SSE/Polling 的 send/replay/error handling 几乎一致 | `state_sync/syncer.py` |
| 4 | 过度使用 `Any` 类型 | 多处 `result: Any`, `content: Any`, `streamer: Any` | `lib/models.py:30,128` 等 |

### 轻微问题（L）

| # | 问题 | 证据 |
|---|------|------|
| 1 | 魔术字符串 | Task status 在 `orchestrator/orchestrator.py:372` 使用字面量 `"running"` 而非引用 Task.status |
| 2 | 低效字符串拼接 | `content += block.get("text", "")` 在循环中 | `api/client.py:201-206` |

### 做得好的地方

- ✅ `TaskGraph` — 单一职责，DAG 实现清晰，有循环检测
- ✅ `SecurityLayer` (security/layer.py) — 架构良好的权限系统
- ✅ `LiteLLMClient` — 完善的 HTTP 错误处理和特定异常类型
- ✅ `ToolExecutor` — 清晰的超时、并发控制和权限检查
- ✅ `Compression` — 良好文档化的压缩策略

### 验收标准检查清单

- [ ] AgentOrchestrator 拆分为更小的单一职责类
- [ ] 所有 `except Exception: pass` 添加 logger.warning 或重抛
- [ ] 三个 Connection 类重构为共享基类
- [ ] 减少 `Any` 类型使用，增加泛型约束

---

## 维度三：测试覆盖 — 评级 C

### 已有良好测试的模块

| 模块 | 测试文件 | 质量 |
|------|----------|------|
| lib/models | `test_models.py` | Good |
| lib/dag | `test_dag.py` | Good |
| state/store | `test_state_store.py` | Good |
| memory/store | `test_memory_store.py` | Good |
| api/client | `test_client.py` | Good |
| observability | `test_observability.py` | Good |
| skills/registry | `test_skills_registry.py` | Good |
| state_sync/syncer | `test_syncer.py` | Good |
| streaming/events | `test_stream_event_types.py` | Good |
| streaming/streamer | `test_agent_streamer_basic.py` | Good |

### 缺少测试的高优先级模块

| 模块 | 风险 |
|------|------|
| **orchestrator** (orchestrator.py, task_graph.py) | 核心执行引擎 — bug 导致级联故障 |
| **tools** (bash, file_read, file_edit, grep, glob, web_fetch, etc.) | 用户面向功能 — 安全和正确性关键 |

### 缺少测试的中等优先级模块

| 模块 | 风险 |
|------|------|
| state/app_state | 中心状态管理 — 集成断裂静默发生 |
| state/hooks | 事件 hook 传播 — 故障难以调试 |
| context/manager | Context budget 和压缩 — 可导致内存问题 |
| session/manager | Session 生命周期 — 内存泄漏和状态损坏 |

### 测试覆盖率估算

- **已测试模块**: 11 / ~28 (~39%)
- **核心模块覆盖率**: 低（orchestrator 和 tools 未测试）

### 验收标准检查清单

- [ ] 为 orchestrator 添加核心测试（task_graph 已有，orchestrator.py 缺失）
- [ ] 为 tools 添加集成测试（bash_tool, file_read_tool, file_edit_tool 高优先）
- [ ] state/app_state 和 state/hooks 添加测试
- [ ] 覆盖率目标：核心模块达到 70%+

---

## 维度四：安全性 — 评级 C 🔴

### 🔴 严重漏洞（已验证）

#### 1. 路径遍历 — H（已确认）

| 文件 | 漏洞代码 | 证据 |
|------|----------|------|
| `tools/file_read_tool.py:18` | `path = Path(ctx.cwd) / file_path` | 无 `.resolve()`，无 `../` 验证 |
| `tools/file_edit_tool.py:22` | 同上 | 同上 |
| `tools/glob_tool.py:20` | `base = Path(ctx.cwd) / path` | 同上 |

**利用**: 可读取 `../../etc/passwd` 等任意文件

**修复建议**:
```python
path = (Path(ctx.cwd) / file_path).resolve()
if not str(path).startswith(str(Path(ctx.cwd).resolve())):
    return {"error": "Path outside cwd"}
```

#### 2. 命令注入 — H（已确认）

| 文件 | 漏洞代码 | 证据 |
|------|----------|------|
| `tools/bash_tool.py:44` | `asyncio.create_subprocess_shell(cmd, ...)` | `_is_readonly()` 存在但**从未被调用** |

**利用**: 可执行任意 shell 命令

**修复建议**:
```python
if not _is_readonly(cmd):
    return {"stdout": "", "stderr": "Command not allowed", "exit_code": 1}
```
或使用 `create_subprocess_exec` 替代 shell

#### 3. SSRF — M（已确认）

| 文件 | 漏洞代码 | 证据 |
|------|----------|------|
| `tools/web_fetch_tool.py:28` | `response = await client.get(url, headers=headers)` | 无 URL 验证，可访问 `http://localhost`、`http://169.254.169.254` |

**利用**: 可获取 AWS 元数据（云凭据）、探测内部服务

**修复建议**:
```python
from urllib.parse import urlparse
parsed = urlparse(url)
if parsed.hostname in {"localhost", "127.0.0.1"} or parsed.hostname.startswith("169.254."):
    return {"error": "SSRF blocked: disallowed host"}
```

### 🟡 中等安全问题

#### 4. 两个 SecurityLayer 实现冲突 — M（已确认）

| 实现 | 位置 | `check()` 签名 |
|------|------|----------------|
| 真实实现 | `security/layer.py:106` | `check(tool_name: str, args, context)` |
| 占位实现（生产使用） | `tools/base.py:185` | `check(tool: ToolDefinition, args, context)` |

**问题**: `security/layer.py` 的完整实现（rules、budgets）**从未被实例化**。实际使用的是 `tools/base.py` 的占位实现，该实现**无 budgets，无 rules**，仅做 mode-based allow/deny。

#### 5. 审计日志失败静默忽略 — L

| 文件 | 证据 |
|------|------|
| `security/layer.py:66` | `except Exception: pass` — 安全事件可能不被记录 |

### 安全做得好的地方

- ✅ 5级权限系统架构设计良好
- ✅ BYPASS 模式需要显式 flag 防止意外
- ✅ Budget 系统带窗口重置
- ✅ 凭据从环境变量加载（`ANTHROPIC_AUTH_TOKEN`），非硬编码
- ✅ `yaml.safe_load` 防止代码执行
- ✅ Skills 执行有沙箱和内存限制

### 验收标准检查清单

- [ ] 🔴 **P0**: 修复 file_read/edit/glob_tool 的路径遍历漏洞
- [ ] 🔴 **P0**: 在 bash_tool 中调用 `_is_readonly()` 或改用 `create_subprocess_exec`
- [ ] 🔴 **P0**: 在 web_fetch_tool 添加 URL 验证（阻止 localhost、169.254.x.x）
- [ ] 🟡 **P1**: 统一 SecurityLayer — `tools/base.py` 导入 `security.layer` 而非定义占位类
- [ ] 🟡 **P1**: 审计日志失败应记录而非静默忽略

---

## 维度五：架构设计 — 评级 C 🔴

### 🔴 架构违规（已验证）

#### 1. CLI 直接依赖 lower 层组件 — H（已确认）

| 违反层级的代码 | 导入/使用 |
|---------------|----------|
| `cli/cli.py:220-240` | 直接实例化 `LiteLLMClient`、`StateStore`、`ToolRegistry`、`ToolExecutor` |
| `cli/builtin_commands.py:9` | 导入 `state.store` |
| `cli/status_bar.py:8` | 导入 `state.store` |
| `repl_launcher.py:8-14` | 组合所有 lower 层组件 |

**问题**: CLI 绕过 Orchestrator，直接依赖 lower 层组件

#### 2. AgentOrchestrator 从未实例化 — H（已确认）

- `AgentOrchestrator` 定义于 `orchestrator/orchestrator.py:201`
- 整个代码库中**从未被实例化**
- `repl_launcher.py` 和 `cli/cli.py` 直接创建组件而非通过 Orchestrator
- `_handle_message()` 打印 "Agent processing requires Phase 2" 而非调用 Orchestrator

**问题**: `AgentOrchestrator` 是死代码

#### 3. 两个 SecurityLayer 实现冲突 — H（已确认）

见安全性维度 #4

### 架构做得好的地方

- ✅ `orchestrator/task_graph.py` — 正确依赖 `utils/dag.py`
- ✅ `lib/models.py` — 共享类型层，依赖方向正确
- ✅ `context/manager.py` — 使用 `TYPE_CHECKING` 避免循环依赖
- ✅ `tools/base.py` — Tool 系统结构正确
- ✅ `security/layer.py` — 跨切面层，架构正确

### 验收标准检查清单

- [ ] 🔴 **P0**: 重构 CLI 为纯 UI 层 — 接收 Orchestrator 实例，所有 lower 层通过 Orchestrator 注入
- [ ] 🔴 **P0**: 在 `repl_launcher.py` 或新增 `Application` 类中创建并使用 `AgentOrchestrator`
- [ ] 🔴 **P0**: 统一 SecurityLayer — 删除 `tools/base.py` 中的占位类，导入 `security.layer`
- [ ] 🟡 **P1**: `_handle_message()` 应调用 Orchestrator 而非打印消息
- [ ] 🟡 **P1**: `cli/builtin_commands.py`、`cli/status_bar.py` 应通过 Orchestrator 访问状态

---

## 修复优先级汇总

### 🔴 P0 — 阻断性问题（必须修复后才能发布）

| # | 维度 | 问题 | 修复工作量 |
|---|------|------|------------|
| 1 | 安全 | 路径遍历（file_read/edit/glob） | 小 |
| 2 | 安全 | 命令注入（bash_tool 未调用 _is_readonly） | 小 |
| 3 | 安全 | SSRF（web_fetch 无 URL 验证） | 小 |
| 4 | 架构 | AgentOrchestrator 从未使用（死代码） | 大 |
| 5 | 架构 | CLI 绕过 Orchestrator 直接依赖 lower 层 | 大 |
| 6 | 架构 | 两个 SecurityLayer 实现冲突 | 中 |

### 🟡 P1 — 重要问题（发布前应修复）

| # | 维度 | 问题 | 修复工作量 |
|---|------|------|------------|
| 1 | 功能 | State Sync 静默异常吞噬 | 小 |
| 2 | 功能 | 流式事件处理不完整 | 中 |
| 3 | 功能 | Observability span processors 为占位 | 中 |
| 4 | 质量 | AgentOrchestrator God Class | 大 |
| 5 | 质量 | StateStore 多处静默异常 | 小 |
| 6 | 架构 | 统一 SecurityLayer | 中 |
| 7 | 测试 | orchestrator 无测试 | 大 |
| 8 | 测试 | tools 无测试 | 大 |

### 🟢 P2 — 次要优化（可后续迭代）

| # | 维度 | 问题 |
|---|------|------|
| 1 | 质量 | 三个 Connection 类重复代码 |
| 2 | 质量 | 过度使用 Any 类型 |
| 3 | 质量 | 审计日志失败静默忽略 |
| 4 | 功能 | state_sync publisher 队列满时静默丢弃 |

---

## 总体结论

**当前状态**: ⚠️ 不适合发布（2 个 P0 安全漏洞 + 3 个 P0 架构违规）

**最低通过条件**:
1. 修复所有 P0 安全问题（路径遍历、命令注入、SSRF）
2. 修复 SecurityLayer 重复实现冲突
3. 让 AgentOrchestrator 被实际使用

**预计修复工作量**:
- 安全修复: ~1-2 人日
- 架构修复: ~1 周（需要较大重构）
- 完整测试覆盖: ~1 周

---

*审查完成时间: 2026-04-03*
*审查工具: 多 Agent 并行审查 + 二轮验证*
