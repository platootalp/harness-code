# src_py 设计规范 Review 报告

**文档**: docs/superpowers/specs/2026-04-02-src-py-design.md
**日期**: 2026-04-02
**Reviewer**: Claude Code (superpowers:code-reviewer)

---

## Executive Summary

`src_py` 是一个轻量级 Python Agent Engine 设计规范，涵盖 17 个章节，包括 CLI、Orchestrator、Tools、Skills、MCP、Observability、Security 等组件。

**总体评估**: 设计文档处于草稿状态，存在需要解决的重大问题。架构方向正确，但规范缺乏一致实施所需的精度。

---

## Critical Issues (必须修复)

### 1. 架构图依赖方向错误 (Section 1)

**问题**: 架构图显示 `LiteLLM Client` 在 `Tools System`、`Skills Sys`、`MCP Client`、`Observability` 下方，意味着工具依赖 LLM，方向错误。

```
├──────────────┬──────────────┬──────────────┬────────────────┤
│ Tools System │ Skills Sys  │ MCP Client   │ Observability  │
├──────────────┴──────────────┴──────────────┴────────────────┤
│                    LiteLLM Client                            │
```

**正确架构**: Tools/Skills/MCP 应在 LLM Client 上方，调用 LLM Client。

**修复建议**: 重构架构图，使 `LiteLLM Client` 处于底层。

---

### 2. 重复 Section 16

**问题**: Section 16 同时标注了"项目结构"和"技术选型"，造成导航混乱。

**修复建议**:
- Section 16: 项目结构 (Project Structure)
- Section 17: 技术选型 (Technical Choices)
- Section 18: 实现优先级 (Implementation Priority)

---

### 3. `Event` 类名与 `asyncio.Event` 冲突

**问题** (Section 4.1):
```python
@dataclass
class Event:
    """事件基类"""
    timestamp: datetime
    source: str
```

与 `asyncio.Event` 产生命名冲突。

**修复建议**: 重命名为 `SrcEvent` 或 `AgentEvent`。

---

### 4. 未定义类型引用

| 未定义类型 | 位置 | 应该是 |
|-----------|------|--------|
| `DAG[str]` | Section 5.2 | 需要定义 DAG 类或使用 TypeVar |
| `CompressionStrategy` | Section 9.2 | 未定义为类型 |
| `ExecutionContext` | Section 7.5 | 使用但 ToolContext 在 4.1 定义 |
| `ArchiveStore` | Section 9.3 | 引用但无接口定义 |
| `LiteLLMClient` | Section 5.2 | 无接口定义 |
| `MCPServerConfig` | Section 8.2 | 无结构定义 |
| `MCPResource` | Section 8.2 | 引用但未定义 |
| `MCPResourceResult` | Section 8.2 | 引用但未定义 |
| `MCPTool` | Section 8.2 | 引用但未定义 |

**修复建议**: 添加"通用类型"章节，集中定义所有共享类型。

---

### 5. `ExecutionContext` vs `ToolContext` 类型不一致

**问题**:
- Section 4.1 定义 `ToolContext` 作为工具执行上下文
- Section 7.5 `SkillRegistry.execute()` 使用 `ExecutionContext`
- 两者功能相同但名称不同

**修复建议**: 统一使用一个上下文类型，或明确说明各自使用场景。

---

### 6. `PermissionLevel.DENY` 用途不明确

**问题** (Section 10.1):
```python
class PermissionLevel(Enum):
    BYPASS = "bypass"
    AUTO_ACCEPT = "auto"
    ACCEPT_EDITS = "accept_edits"
    PLAN = "plan"
    REVIEW = "review"
    DENY = "deny"  # 明确拒绝
```

`DENY` 与 `PermissionRule(action="deny")` 的区别不清晰。

**修复建议**: 明确 DENY 是:
1. 无规则匹配时的默认行为
2. 阻止所有操作的安全模式
3. 其他用途

---

### 7. WebSocket 重连方法签名不匹配

**问题** (Section 3.4):
```python
# _handle_connection_error 中调用:
await self.connect(self._connection.endpoint, from_seq=self._seq)

# 但 connect 签名是:
async def connect(self, endpoint: str) -> None:
```

**修复建议**: 修正 `connect()` 签名或调用点。

---

## Important Concerns (应该修复)

### 8. 错误恢复决策树未指定

**问题**: Section 5.2 的 `handle_error` 描述了决策流程但未实现:
```python
async def handle_error(self, error: Exception, context: dict) -> ErrorAction:
    """错误恢复决策树：
    1. 检查错误类型（retryable?）
    2. 检查重试预算
    3. 决定 RETRY / FALLBACK_MODEL / RECOVER_OUTPUT / MARK_FAILED
    """
```

**修复建议**: 添加流程图或伪代码。

---

### 9. Skills `allowed-tools` 提取脆弱

**问题** (Section 7.5):
```python
def _extract_tool_calls(self, args: dict[str, Any]) -> list[ToolCall]:
    return args.get("tool_calls", [])
```

假设工具调用只在 `args["tool_calls"]` 中，可能存在安全绕过风险。

**修复建议**: 使用更健壮的提取方法或标注为已知限制。

---

### 10. `PermissionRule` glob/regex 模式匹配不明确

**问题** (Section 10.3):
```python
PermissionRule(tool="Bash", pattern="git *", action="allow", priority=50)
```

`git *` 是 glob 还是 regex？`*` 的含义不清。

**修复建议**: 添加模式匹配实现细节和明确示例。

---

### 11. Memory 与 Context Compression 集成未定义

**问题**: Sections 9 和 13 未说明:
- `recall()` 在压缩前还是压缩后发生？
- 压缩的消息会在 Memory 中吗？
- 压缩是否影响 Memory 存储？

**修复建议**: 添加序列图说明 Context Manager + Memory 交互。

---

### 12. 项目结构中 `tools/` 重复

**问题** (Section 16):
```
├── tools/                      # Tool implementations
├── tools/                      # Tool implementations  <-- 重复
```

**修复建议**: 删除重复条目。

---

### 13. `SkillRegistry` 类定义缺失

**问题** (Section 7.5): 代码块中 `class SkillRegistry:` 声明缺失。

**修复建议**: 在 docstring 前添加 `class SkillRegistry:`。

---

### 14. `BUILTIN_COMMANDS` 未定义

**问题** (Section 2.5): `CommandParser` 引用 `self.BUILTIN_COMMANDS` 但未定义。

**修复建议**: 添加 `BUILTIN_COMMANDS = {...}` 定义。

---

## Minor Suggestions (建议修复)

### 15. `observe()` 方法未定义
Section 14 提到"Observer pattern"但未在任何类中展示 `observe()` 方法。

### 16. 无日志规范
规范未提及日志策略（日志级别、输出格式、日志目的地）。

### 17. 无配置文件格式定义
规范提及 `lib/config.py` 但未定义配置文件 schema（JSON? YAML?）。

### 18. `_chunk_text` 实现过于简单
Section 13.3 的文本分块只是按 `. ` 分割，对代码或结构化内容不合适。

---

## 正面评价

1. **安全模型**: 5级权限系统 + BYPASS 显式确认，设计完善
2. **状态同步**: 带序列号的发布/订阅 + 重放协议，健壮
3. **Context Compression**: 4级策略 + 可逆性保证，全面
4. **Skills-as-Tool 模式**: 使 LLM 可直接调用 Skills，创新
5. **错误恢复配置**: `ErrorRecoveryConfig` + 熔断器，面向生产
6. **项目结构**: 目录组织逻辑清晰，模块化
7. **实施优先级**: 分阶段方法务实可行

---

## 问题统计

| 类别 | 数量 |
|------|------|
| Critical Issues | 7 |
| Important Concerns | 8 |
| Minor Suggestions | 4 |

---

## 建议

1. **实施前**: 解决所有 Critical issues，特别是类型系统不一致和未定义类型
2. **添加类型词汇表**: 创建集中式类型定义章节
3. **创建序列图**: 用于复杂流程（错误恢复、context 压缩、状态同步）
4. **修正架构图**: 确保 LiteLLM Client 位置与实际依赖流向一致
5. **修正编号**: 修正重复的 Section 16，确保章节编号连续

---

*Generated by superpowers:code-reviewer*
