# src_py 未实现功能清单

**日期**: 2026-04-02
**状态**: 进行中
**版本**: 1.0

---

## 一、核心未实现功能

### 1.1 Memory Store (记忆系统) - 严重

| 文件 | 方法 | 问题 |
|------|------|------|
| `memory/store.py:23` | `_get_client()` | 返回占位字典 `{"provider": ...}`，未实现 Mem0 SDK |
| `memory/store.py:30` | `_get_vector_store()` | 返回占位字典，未实现 Milvus 客户端 |
| `memory/store.py:68` | `search()` | 直接返回 `[]`，未实现向量搜索 |
| `memory/store.py:77` | `get()` | 直接返回 `None`，未实现按 ID 查询 |
| `memory/store.py:90` | `list_by_user()` | 直接返回 `[]`，未实现用户记忆列表 |

**影响**: Agent 无法使用长期记忆功能

---

### 1.2 State Sync 连接 (实时同步) - 严重

| 文件 | 类/方法 | 问题 |
|------|------|------|
| `state_sync/syncer.py:186` | `WebSocketConnection.connect` | `pass` 空实现 |
| `state_sync/syncer.py:189` | `WebSocketConnection.send` | `pass` 空实现 |
| `state_sync/syncer.py:191` | `WebSocketConnection.close` | `pass` 空实现 |
| `state_sync/syncer.py:207` | `SSEConnection.send` | `pass` 空实现 |
| `state_sync/syncer.py:209` | `SSEConnection.close` | `pass` 空实现 |
| `state_sync/syncer.py:222` | `PollingConnection.send` | `pass` 空实现 |
| `state_sync/syncer.py:224` | `PollingConnection.close` | `pass` 空实现 |
| `state_sync/syncer.py:140` | `reconnect_with_replay` | 异常被静默忽略 |
| `state_sync/syncer.py:153` | `_apply_update` | 回调异常被静默忽略 |

**影响**: CLI 无法接收实时状态更新

---

### 1.3 LiteLLM Client 流式处理 - 中等

| 文件 | 位置 | 问题 |
|------|------|------|
| `api/client.py:157` | `_parse_stream_chunk` | 处理 `content_block_start` 但无操作 |
| `api/client.py:230` | `_parse_stream_chunk` | 处理 `message_delta` 但无操作 |
| `api/client.py:236` | `_parse_stream_chunk` | 处理 `message_stop` 但无操作 |
| `api/client.py:15,20,25` | 异常类 | 空 `pass` 实现 |

**影响**: 流式输出不完整

---

## 二、次要未实现功能

### 2.1 Observability (观测系统)

| 文件 | 方法 | 问题 |
|------|------|------|
| `observability/span_processors.py:45,50,55` | `SpanProcessor` 抽象方法 | `pass` 占位 |
| `observability/span_processors.py:66,74` | `InMemorySpanProcessor` | `pass` 占位 |
| `observability/span_processors.py:116` | `BatchSpanProcessor.on_start` | `pass` 占位 |
| `observability/span_processors.py:218,223` | `SpanExporter` 抽象方法 | `pass` 占位 |
| `observability/span_processors.py:297` | `OTLPExporter.export` | 异常被静默忽略 |
| `observability/evaluator.py:213` | `_try_phoenix_eval` | 异常导致返回 None |

---

### 2.2 Skills System

| 文件 | 方法 | 问题 |
|------|------|------|
| `skills/registry.py:21,26,31,36,41` | 异常类 | 空 `pass` 实现 |
| `skills/registry.py:211` | `ToolRegistryInterface.get` | 始终返回 `None` |
| `skills/registry.py:215` | `ToolRegistryInterface.list` | 始终返回 `[]` |
| `skills/registry.py:585` | `find_by_trigger` | 无匹配时返回 `None` |

---

### 2.3 State Store (状态存储)

| 文件 | 方法 | 问题 |
|------|------|------|
| `state/store.py:101` | `_notify_subscribers` | 异常被静默忽略 |
| `state/store.py:166` | `_write_jl` | 异常被静默忽略 |
| `state/store.py:195` | `_create_snapshot` | 异常被静默忽略 |
| `state/store.py:248` | `restore` | 清理异常被静默忽略 |

---

### 2.4 Session Manager

| 文件 | 方法 | 问题 |
|------|------|------|
| `session/manager.py:57` | `get` | 未找到时返回 `None` |
| `session/manager.py:145,148` | `_load` | 失败时返回 `None` |

---

## 三、空异常处理器 (Silent Exception Handlers)

以下位置的异常被静默忽略，可能导致问题难以调试：

### state_sync/publisher.py
- `publish()` 方法中 QueueFull 和通知异常被静默忽略

### state_sync/syncer.py
- `_on_state_change`, `reconnect_with_replay`, `_apply_update` 异常被忽略

### state/store.py
- 多个 checkpoint 和通知方法的异常被静默忽略

### observability/tracer.py
- `_notify_observers` 异常被忽略

---

## 四、Protocol 接口 (预期行为)

以下 Protocol 定义使用 `...` 是正常的，因为它们是接口声明，实际实现在其他位置：

| 文件 | Protocol | 说明 |
|------|----------|------|
| `orchestrator/orchestrator.py:96` | `LiteLLMClient` | 实现在 `api/client.py` |
| `orchestrator/orchestrator.py:114` | `ToolRegistry` | 实现在 `tools/base.py` |
| `orchestrator/orchestrator.py:121` | `SkillRegistry` | 实现在 `skills/registry.py` |
| `orchestrator/orchestrator.py:128` | `MCPClient` | 实现在 `mcp/client.py` |
| `orchestrator/orchestrator.py:135` | `StateStore` | 实现在 `state/store.py` |

---

## 五、按优先级分类

### P0 - 核心功能缺失 (阻断发布)

1. **Memory Store** - Mem0/Milvus 客户端未实现，Agent 无法使用长期记忆
2. **State Sync 连接** - WebSocket/SSE/Polling 都是空实现，实时状态同步不可用

### P1 - 重要功能不完整

3. **流式输出** - LLM 流式响应处理未完成
4. **Observability** - Phoenix/Arize 集成未完成

### P2 - 次要功能

5. **Session Manager** - 存储后端未实现
6. **异常处理** - 多处静默忽略异常

---

## 六、已完整实现的模块

以下模块经审核确认实现完整：

- ✅ `context/compression.py` - 4级压缩算法完整
- ✅ `utils/dag.py` - DAG 实现完整
- ✅ `mcp/client.py` - MCP JSON-RPC 客户端完整
- ✅ `mcp/server.py` - FastMCP 服务端完整
- ✅ `orchestrator/task_graph.py` - Task DAG 调度完整

---

## 七、建议实现顺序

1. **Memory Store** - 先实现内存后端作为占位，后续接入 Mem0
2. **State Sync** - 至少实现一种连接方式 (推荐 WebSocket)
3. **流式处理** - 完成 LLM 流式响应的完整解析
4. **Observability** - 实现 OTLP 导出或 Console 导出作为占位
