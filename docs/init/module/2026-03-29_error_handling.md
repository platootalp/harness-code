# Error Handling 统一错误处理

> **模板版本**: 3.0
> **创建日期**: 2026-03-29
> **最后更新**: 2026-03-31

---

## 1. 概述

### 1.1 模块名称

Error Handling（统一错误处理）

### 1.2 职责

错误处理是横切面模块，为整个系统提供统一的错误处理框架。涵盖两类错误：

- **传统错误**：模块级异常（配置错误、存储失败、网络超时等）
- **Agent 错误**：Agent 运行时问题（调错工具、幻觉、推理错误等）

### 1.3 核心能力

| 能力 | 说明 |
| ---- | ---- |
| 统一异常体系 | 所有自定义异常继承 Mozierror，支持错误码和上下文信息 |
| 错误码体系 | 每个异常包含错误码，便于解析和处理 |
| Agent 错误检测器 | ToolMisuseDetector、HallucinationDetector、LoopDetector 等 |
| 错误恢复策略 | RetryPolicy、CircuitBreaker 等弹性机制 |

---

## 2. 核心问题与解决方案

### 2.1 异常体系不统一

**问题描述**：各模块自定义异常，缺乏统一规范，难以统一处理。当错误发生时，上层代码难以有效分类和处理不同来源的错误。

**挑战**：平衡异常粒度，既要覆盖全面又要避免类爆炸。不同模块的错误处理需求差异较大。

**解决方案**：定义 MoziError 基类，所有自定义异常继承 Mozierror。每个异常包含 code、message、details、cause 等标准字段，支持统一的序列化和日志格式。

### 2.2 错误信息不规范与传播链缺失

**问题描述**：错误信息格式不一致，难以解析和追溯。跨模块调用时错误信息丢失或被覆盖。

**挑战**：需要建立统一的错误信息规范，同时保持各模块的灵活性。

**解决方案**：建立统一错误码体系（如 CLI_、ORC_、TSK_ 等前缀），始终使用 `from` 保留异常链，确保原始错误信息可追溯。

### 2.3 Agent 运行时错误难检测

**问题描述**：工具误用、幻觉、推理错误等 Agent 特有错误难以捕获。Agent 错误通常需要基于运行时行为检测，非语法错误。

**挑战**：Agent 错误检测需要在有限的推理步骤内识别问题，同时避免误报影响正常执行。

**解决方案**：实现专门的 Agent 错误检测器：ToolMisuseDetector 检测工具调用错误，HallucinationDetector 检测虚构事实，LoopDetector 检测无限循环，ReasoningValidator 检测推理错误。

### 2.4 错误恢复机制缺失

**问题描述**：缺少统一的错误恢复和降级策略。当错误发生时，系统难以自动恢复或优雅降级。

**挑战**：不同类型的错误需要不同的恢复策略，需要设计可扩展的恢复机制。

**解决方案**：实现 RetryPolicy（重试策略）、CircuitBreaker（熔断器）等弹性机制。针对不同失败类型（EXECUTION_ERROR、VERIFICATION_ERROR、TIMEOUT_ERROR、DELEGATION_ERROR）设计对应的恢复策略。

---

## 3. 数据模型与状态机

### 3.1 异常继承树

```
MoziError (基类)
├── CLIError
│   ├── ReplInitError
│   ├── CommandParseError
│   └── SessionNotFoundError
├── OrchestratorError
│   ├── IntentRecognitionError
│   ├── ComplexityScoringError
│   └── RoutingError
├── TaskError
│   ├── TaskDecompositionError
│   ├── DependencyAnalysisError
│   ├── TaskTimeoutError
│   └── RollbackError
├── SessionError
│   ├── SessionInitError
│   ├── ContextWindowOverflowError
│   └── SessionStorageError
├── ContextError
│   ├── ContextBuildError
│   └── RetrievalError
├── MemoryError
│   ├── MemoryWriteError
│   ├── MemoryReadError
│   └── CompressionError
├── ToolsError
│   ├── ToolNotFoundError
│   ├── ToolExecutionError
│   ├── ToolValidationError
│   ├── SecurityViolationError
│   ├── WhitelistViolationError
│   └── SandboxEscapeError
├── ModelError
│   ├── ModelInvokeError
│   ├── ModelResponseParseError
│   └── RateLimitError
├── ConfigError
│   ├── ConfigLoadError
│   ├── ConfigValidationError
│   └── ConfigNotFoundError
├── StorageError
│   ├── StorageReadError
│   ├── StorageWriteError
│   └── StorageConnectionError
├── EventBusError
│   ├── PublishError
│   ├── SubscriptionError
│   └── EventDeliveryError
├── SecurityError
│   ├── PermissionDeniedError
│   └── SecretDetectedError
├── ResilienceError
│   ├── CircuitBreakerOpenError
│   ├── RateLimitExceededError
│   └── TimeoutError
├── ObservabilityError
│   └── TelemetryExportError
└── AgentError (详见 3.4)
```

### 3.2 异常基类定义

```python
class MoziError(Exception):
    """所有 Mozi 自定义异常的基类"""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        self.__cause__ = cause

    def to_dict(self) -> dict:
        """序列化为字典，用于日志和 API 响应"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "details": self.details,
        }
```

### 3.3 统一错误码

| 前缀 | 模块 | 示例 |
|------|------|------|
| `CLI_` | 接入层 | `CLI_001` |
| `ORC_` | 编排层 | `ORC_001` |
| `TSK_` | 任务模块 | `TSK_001` |
| `Sess_` | 会话模块 | `Sess_001` |
| `Ctx_` | 上下文模块 | `Ctx_001` |
| `Mem_` | 记忆模块 | `Mem_001` |
| `Tool_` | 工具模块 | `Tool_001` |
| `Model_` | 模型模块 | `Model_001` |
| `Cfg_` | 配置模块 | `Cfg_001` |
| `Store_` | 存储模块 | `Store_001` |
| `EBus_` | 事件总线 | `EBus_001` |
| `Sec_` | 安全模块 | `Sec_001` |
| `Rsl_` | 稳定性模块 | `Rsl_001` |
| `Obs_` | 可观测性模块 | `Obs_001` |
| `Agent_` | Agent 错误 | `Agent_001` |

### 3.4 Agent 错误分类

```python
class FailureType(Enum):
    """失败类型枚举"""
    EXECUTION_ERROR = "execution_error"     # 执行错误
    VERIFICATION_ERROR = "verification_error" # 验证错误
    TIMEOUT_ERROR = "timeout_error"         # 超时
    DELEGATION_ERROR = "delegation_error"    # 委托失败


class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
```

---

## 4. 模块结构

### 4.1 目录结构

```
mozi/core/error/
    __init__.py              # 模块导出
    base.py                   # MoziError 基类
    codes.py                   # 错误码定义
    handlers.py               # 错误处理器
    agents/
        __init__.py
        detectors.py           # Agent 错误检测器
        recovery.py            # 恢复策略
```

### 4.2 关键文件

| 文件 | 职责 |
| ---- | ---- |
| `base.py` | MoziError 基类定义 |
| `codes.py` | 错误码枚举和定义 |
| `handlers.py` | 全局错误处理器 |
| `agents/detectors.py` | Agent 错误检测器实现 |
| `agents/recovery.py` | 错误恢复策略实现 |

---

## 5. 接口、交互与流程

### 5.1 异常处理规范

| 规范 | 说明 |
|------|------|
| 始终使用 `from` 保留异常链 | `raise SomeError(...) from original_error` |
| 禁止捕获裸 `Exception` | 必须捕获具体异常类型 |
| 所有异常必须继承 `MoziError` | 便于统一处理和分类 |
| 异常必须包含上下文信息 | code、message、details |
| 禁止吞掉异常 | 除非明确知道如何处理 |

### 5.2 Agent 错误检测器接口

```python
class ToolMisuseDetector:
    """检测工具调用错误"""

    async def detect(
        self,
        task: Task,
        tool_call: ToolCall,
        context: Context,
    ) -> ToolMisuseResult:
        """检测是否调错工具"""
        ...


class HallucinationDetector:
    """幻觉检测器"""

    async def detect(
        self,
        agent_output: str,
        context: Context,
    ) -> HallucinationResult:
        """检测输出中是否存在幻觉"""
        ...


class LoopDetector:
    """死循环检测器"""

    def __init__(
        self,
        max_iterations: int = 20,
        similarity_threshold: float = 0.85,
    ) -> None:
        self.max_iterations = max_iterations
        self.similarity_threshold = similarity_threshold
        self.execution_history: list[ExecutionSnapshot] = []

    def detect_loop(self) -> LoopDetectionResult | None:
        """检测是否存在死循环"""
        ...
```

### 5.3 错误处理数据流

```
错误发生
    │
    ▼
错误分类 ─────────────────────────────────────────┐
    │                                             │
    ├──► 传统错误 ──► MoziError 异常体系            │
    │                   │                         │
    │                   ▼                         │
    │              统一错误处理器                   │
    │                   │                         │
    │                   ▼                         │
    │              错误恢复/传播                    │
    │                                             │
    └──► Agent 错误 ──► AgentError 特定处理器      │
                        │                         │
                        ▼                         │
                   错误检测器                      │
                   (Misuse/Param/Hallucination/   │
                    Reasoning/Loop)               │
                        │                         │
                        ▼                         │
                   恢复策略选择                    │
                        │                         │
                        ▼                         │
                   自我纠正/回退/降级              │
```

---

## 6. 边界与契约

### 6.1 错误码定义

| 错误码范围 | 模块 | 说明 |
|-----------|------|------|
| CLI_001 ~ CLI_099 | 接入层 | 命令行接口错误 |
| ORC_001 ~ ORC_099 | 编排层 | 任务编排错误 |
| TSK_001 ~ TSK_099 | 任务模块 | 任务执行错误 |
| Sess_001 ~ Sess_099 | 会话模块 | 会话管理错误 |
| Ctx_001 ~ Ctx_099 | 上下文模块 | 上下文构建错误 |
| Mem_001 ~ Mem_099 | 记忆模块 | 记忆存储错误 |
| Tool_001 ~ Tool_099 | 工具模块 | 工具执行错误 |
| Model_001 ~ Model_099 | 模型模块 | 模型调用错误 |
| Cfg_001 ~ Cfg_099 | 配置模块 | 配置加载错误 |
| Store_001 ~ Store_099 | 存储模块 | 持久化错误 |
| EBus_001 ~ EBus_099 | 事件总线 | 事件传递错误 |
| Sec_001 ~ Sec_099 | 安全模块 | 安全检查错误 |
| Rsl_001 ~ Rsl_099 | 稳定性模块 | 熔断/限流错误 |
| Obs_001 ~ Obs_099 | 可观测性模块 | 日志/追踪错误 |
| Agent_001 ~ Agent_099 | Agent 错误 | Agent 运行时错误 |

### 6.2 API 契约

**异常序列化格式**：

```json
{
    "error_type": "MoziError",
    "message": "详细错误信息",
    "code": "ERR_001",
    "details": {
        "context_key": "context_value"
    }
}
```

**错误响应规范**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| error_type | string | 是 | 异常类名 |
| message | string | 是 | 人类可读的错误描述 |
| code | string | 是 | 错误码 |
| details | object | 否 | 额外的上下文信息 |

### 6.3 异常处理契约

| 契约 | 要求 |
|------|------|
| 异常链保留 | 所有 `raise` 必须使用 `from` 保留原始异常 |
| 禁止裸捕获 | 禁止 `except Exception:`，必须捕获具体类型 |
| 禁止异常吞没 | 除非明确知道如何处理，否则必须传播 |
| 统一序列化 | 所有异常必须支持 `to_dict()` 方法 |

---

## 7. 实现细节

### 7.1 恢复策略

| 失败类型 | 策略 |
|----------|------|
| EXECUTION_ERROR | 重试（最多2次）→ 仍失败则升级 |
| VERIFICATION_ERROR | 修复后重试（最多1次）→ 仍失败则澄清 |
| TIMEOUT_ERROR | 重试（最多1次）→ 仍失败则拆分任务 |
| DELEGATION_ERROR | 重试委托或更换 Agent 类型 |

### 7.2 升级路径

```
失败次数超过阈值
    │
    ▼
升级到更专业的 Agent
    │
    ▼
如果所有 Agent 都失败
    │
    ▼
返回用户，请求澄清或人工介入
```

---

## 8. 配置

### 8.1 错误处理配置

> **说明**：本模块的配置项已汇总到 [Config 模块设计文档](./2026-03-29_config.md#711-error-handling-配置)。

---

## 9. 度量指标

### 9.1 错误监控指标

| 指标 | 说明 | 目标 |
|------|------|------|
| 错误率 | 每分钟错误数 / 总请求数 | < 5% |
| 未捕获异常率 | 未捕获异常数 / 总异常数 | < 1% |
| Agent 错误检测率 | 检测到的 Agent 错误 / 实际 Agent 错误 | > 90% |
| 错误恢复成功率 | 成功恢复次数 / 总错误次数 | > 80% |

### 9.2 性能指标

| 指标 | 说明 | 目标 |
|------|------|------|
| 错误处理延迟 | 从错误发生到处理完成的时间 | < 100ms |
| 检测器开销 | Agent 错误检测额外耗时 | < 5% 总时间 |

### 9.3 业务指标

| 指标 | 说明 | 目标 |
|------|------|------|
| 用户感知错误率 | 用户看到错误消息的比率 | < 2% |
| 平均错误恢复时间 | 从错误发生到服务恢复的平均时间 | < 30s |

> **待定义**：具体指标采集方式和告警阈值待实现时确定。

---

## 10. 参考

- **测试策略**：见 [testing.md](./2026-03-29_testing.md)
- **相关模块**：Config、[EventBus](./2026-03-29_eventbus.md)、[Resilience](./2026-03-29_resilience.md)

---

## 变更记录

| 版本 | 日期 | 变更内容 |
| ---- | ---- | -------- |
| 3.0 | 2026-03-31 | 升级至模板 v3.0：新增 §6 边界与契约（错误码定义、API契约）、§9 度量指标；重组章节结构 |
| 2.2 | 2026-03-31 | 配置项迁移至 Config 模块统一管理 |
| 2.1 | 2026-03-31 | 调整异常继承树：WhitelistViolationError/SandboxEscapeError 移至 ToolsError |
| 2.0 | 2026-03-30 | 重构为模板 v2.0 结构，核心问题改为段落描述 |
| 1.0 | 2026-03-29 | 初始版本，包含统一异常体系和 Agent 错误处理 |

_版本: 3.0_
_更新日期: 2026-03-31_
