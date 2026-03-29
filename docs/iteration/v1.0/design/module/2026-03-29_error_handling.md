# Error Handling 统一错误处理

## 文档信息

| 字段 | 内容 |
|------|------|
| 模块名称 | Error Handling |
| 职责 | 统一异常体系、Agent 错误处理、横切面错误规范 |
| 文档版本 | v1.0 |
| 状态 | 已完成 |
| 创建日期 | 2026-03-29 |
| 更新日期 | 2026-03-29 |

---

## 1. 模块概述

错误处理是横切面模块，为整个系统提供统一的错误处理框架。涵盖两类错误：

| 类型 | 说明 |
|------|------|
| **传统错误** | 模块级异常（配置错误、存储失败、网络超时等） |
| **Agent 错误** | Agent 运行时问题（调错工具、幻觉、推理错误等） |

### 1.3 核心问题

| 问题 | 说明 |
| ---- | ---- |
| 异常体系不统一 | 各模块自定义异常，缺乏统一规范，难以统一处理 |
| 错误信息不规范 | 错误信息格式不一致，难以解析和追溯 |
| Agent 运行时错误难检测 | 工具误用、幻觉、推理错误等 Agent 特有错误难以捕获 |
| 错误恢复机制缺失 | 缺少统一的错误恢复和降级策略 |

### 1.4 难点

| 难点 | 说明 |
| ---- | ---- |
| 异常类层次设计 | 平衡异常粒度，既要覆盖全面又要避免类爆炸 |
| Agent 错误检测 | Agent 错误通常需要基于运行时行为检测，非语法错误 |
| 循环检测 | 无限循环需要在有限的推理步骤内检测 |
| 错误传播链 | 跨模块调用时错误信息的传递和增强 |

### 1.5 解决方案

| 方案 | 说明 |
| ---- | ---- |
| MoziError 基类 | 统一异常继承树，所有异常继承 Mozierror |
| 错误码体系 | 每个异常包含错误码，便于解析和处理 |
| Agent 错误检测器 | ToolMisuseDetector、HallucinationDetector、LoopDetector 等 |
| 错误恢复策略 | RetryPolicy、CircuitBreaker 等弹性机制 |

---

## 2. 统一异常体系

### 2.1 异常继承树

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
│   └── SecurityViolationError
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
│   ├── WhitelistViolationError
│   ├── SandboxEscapeError
│   └── SecretDetectedError
├── ResilienceError
│   ├── CircuitBreakerOpenError
│   ├── RateLimitExceededError
│   └── TimeoutError
├── ObservabilityError
│   └── TelemetryExportError
└── AgentError (详见第 3 节)
```

### 2.2 异常基类定义

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

### 2.3 异常处理规范

| 规范 | 说明 |
|------|------|
| 始终使用 `from` 保留异常链 | `raise SomeError(...) from original_error` |
| 禁止捕获裸 `Exception` | 必须捕获具体异常类型 |
| 所有异常必须继承 `MoziError` | 便于统一处理和分类 |
| 异常必须包含上下文信息 | code、message、details |
| 禁止吞掉异常 | 除非明确知道如何处理 |

### 2.4 统一错误码

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

---

## 3. Agent 错误处理

### 3.1 错误分类

| 类型 | 说明 | 严重程度 |
|------|------|----------|
| **Tool Misuse** | 调错工具、选错工具 | 高 |
| **Parameter Error** | 传错参数、参数类型错误 | 高 |
| **Hallucination** | 产生幻觉、虚构不存在的事实 | 严重 |
| **Reasoning Error** | 推理错误、逻辑矛盾 | 中 |
| **Infinite Loop** | 死循环、重复执行 | 严重 |

### 3.2 Tool Misuse（调错工具）

#### 3.2.1 场景描述

Agent 选择了一个不适合当前任务的工具，或者调用了不存在的工具。

#### 3.2.2 检测机制

```python
class ToolMisuseDetector:
    """检测工具调用错误"""

    async def detect(
        self,
        task: Task,
        tool_call: ToolCall,
        context: Context,
    ) -> ToolMisuseResult:
        """
        检测是否调错工具
        - 工具是否适合任务类型
        - 工具是否存在于注册表中
        - 工具调用参数是否与任务目标一致
        """
        issues: list[MisuseIssue] = []

        # 检查工具是否存在
        if not await self.tool_registry.exists(tool_call.name):
            issues.append(MisuseIssue(
                type=MisuseType.TOOL_NOT_FOUND,
                severity=Severity.HIGH,
                message=f"Tool '{tool_call.name}' does not exist",
            ))

        # 检查工具是否适合任务类型
        if not self._is_tool_suitable(task, tool_call):
            issues.append(MisuseIssue(
                type=MisuseType.TOOL_NOT_SUITABLE,
                severity=Severity.MEDIUM,
                message=f"Tool '{tool_call.name}' may not be suitable for this task",
            ))

        return ToolMisuseResult(has_issues=len(issues) > 0, issues=issues)
```

#### 3.2.3 恢复策略

| 策略 | 触发条件 | 处理方式 |
|------|----------|----------|
| **工具替换** | 检测到更合适的工具 | 建议替换为同类工具 |
| **参数修正** | 参数类型错误 | 修正参数后重试 |
| **任务重分析** | 工具完全不适合 | 重新分析任务意图 |
| **放弃执行** | 工具不存在且无替代 | 返回错误，通知用户 |

### 3.3 Parameter Error（参数错误）

#### 3.3.1 场景描述

Agent 传递给工具的参数类型错误、数量错误、或者包含无效值。

#### 3.3.2 检测机制

```python
class ParameterValidator:
    """参数验证器"""

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry

    async def validate(
        self,
        tool_call: ToolCall,
    ) -> ValidationResult:
        """验证工具参数是否符合 Schema"""
        tool_schema = await self.tool_registry.get_schema(tool_call.name)

        errors: list[ParameterError] = []

        # 检查必需参数
        for param_name in tool_schema.required_params:
            if param_name not in tool_call.arguments:
                errors.append(ParameterError(
                    param=param_name,
                    error_type=ErrorType.MISSING_REQUIRED,
                    message=f"Required parameter '{param_name}' is missing",
                ))

        # 检查参数类型
        for param_name, param_value in tool_call.arguments.items():
            expected_type = tool_schema.get_param_type(param_name)
            if not self._check_type(param_value, expected_type):
                errors.append(ParameterError(
                    param=param_name,
                    error_type=ErrorType.TYPE_MISMATCH,
                    message=f"Parameter '{param_name}' expected {expected_type}, got {type(param_value)}",
                ))

        # 检查参数值范围
        for param_name, param_value in tool_call.arguments.items():
            constraints = tool_schema.get_constraints(param_name)
            if constraints and not self._check_constraints(param_value, constraints):
                errors.append(ParameterError(
                    param=param_name,
                    error_type=ErrorType.VALUE_CONSTRAINT_VIOLATION,
                    message=f"Parameter '{param_name}' violates constraints",
                ))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
        )
```

#### 3.3.3 恢复策略

| 策略 | 触发条件 | 处理方式 |
|------|----------|----------|
| **自动修正** | 简单类型错误 | 根据 Schema 自动推断正确类型 |
| **重试执行** | 参数校验失败 | 修正后重试（最多 2 次） |
| **回退到对话** | 无法自动修正 | 请求用户确认正确参数 |
| **跳过任务** | 参数错误无法解决 | 记录错误，继续下一个子任务 |

### 3.4 Hallucination（幻觉）

#### 3.4.1 场景描述

Agent 生成了不存在的事实、不存在的代码文件内容、不存在的函数签名等。

#### 3.4.2 检测机制

```python
class HallucinationDetector:
    """幻觉检测器"""

    def __init__(
        self,
        file_system: FileSystem,
        memory: Memory,
    ) -> None:
        self.file_system = file_system
        self.memory = memory

    async def detect(
        self,
        agent_output: str,
        context: Context,
    ) -> HallucinationResult:
        """检测输出中是否存在幻觉"""
        issues: list[HallucinationIssue] = []

        # 检测不存在的文件引用
        file_refs = self._extract_file_references(agent_output)
        for file_ref in file_refs:
            if not await self.file_system.exists(file_ref.path):
                issues.append(HallucinationIssue(
                    type=HallucinationType.NONEXISTENT_FILE,
                    claim=f"File '{file_ref.path}' exists",
                    severity=Severity.HIGH,
                    verification=f"File does not exist at line {file_ref.line}",
                ))

        # 检测不存在的代码元素
        code_elements = self._extract_code_elements(agent_output)
        for element in code_elements:
            if element.type == "function" and not await self._function_exists(element):
                issues.append(HallucinationIssue(
                    type=HallucinationType.NONEXISTENT_FUNCTION,
                    claim=f"Function '{element.name}' exists",
                    severity=Severity.HIGH,
                    verification=f"Function not found in codebase",
                ))

        # 检测与记忆矛盾的事实
        factual_claims = self._extract_factual_claims(agent_output)
        for claim in factual_claims:
            stored_fact = await self.memory.retrieve_fact(claim.subject)
            if stored_fact and not self._is_consistent(claim, stored_fact):
                issues.append(HallucinationIssue(
                    type=HallucinationType.CONTRADICTS_MEMORY,
                    claim=claim.text,
                    severity=Severity.MEDIUM,
                    verification=f"Memory contains: {stored_fact.content}",
                ))

        return HallucinationResult(
            has_issues=len(issues) > 0,
            issues=issues,
            confidence=1.0 - (len(issues) * 0.1),  # 降低置信度
        )
```

#### 3.4.3 预防与恢复策略

| 策略 | 说明 |
|------|------|
| **置信度阈值** | 输出置信度 < 0.7 时标记警告 |
| **事实核查** | 对高风险声明进行二次验证 |
| **记忆对齐** | 生成内容前先检索相关记忆 |
| **自我纠正** | 发现幻觉后主动纠正输出 |
| **用户确认** | 无法确认的事实在输出中标注 `[未验证]` |

### 3.5 Reasoning Error（推理错误）

#### 3.5.1 场景描述

Agent 的推理过程存在逻辑矛盾、前提错误、或者步骤跳跃。

#### 3.5.2 检测机制

```python
class ReasoningValidator:
    """推理验证器"""

    def __init__(self, model: ModelAdapter) -> None:
        self.model = model

    async def validate_reasoning_chain(
        self,
        reasoning_chain: list[ThoughtStep],
    ) -> ReasoningValidationResult:
        """验证推理链的一致性"""
        issues: list[ReasoningIssue] = []

        # 检查逻辑矛盾
        for i, step in enumerate(reasoning_chain):
            for j, other_step in enumerate(reasoning_chain[i + 1:], i + 1):
                if self._is_contradictory(step.conclusion, other_step.conclusion):
                    issues.append(ReasoningIssue(
                        type=ReasoningErrorType.LOGICAL_CONTRADICTION,
                        step_a=i,
                        step_b=j,
                        message=f"Step {i} and {j} contain contradictory conclusions",
                    ))

        # 检查前提支持
        for i, step in enumerate(reasoning_chain):
            if step.depends_on:
                for dep_idx in step.depends_on:
                    if not self._is_supported(step.premise, reasoning_chain[dep_idx].conclusion):
                        issues.append(ReasoningIssue(
                            type=ReasoningErrorType.UNSUPPORTED_PREMISE,
                            step=i,
                            depends_on=dep_idx,
                            message=f"Step {i} depends on unsupported conclusion from step {dep_idx}",
                        ))

        # 检查步骤完整性
        expected_steps = self._estimate_required_steps(reasoning_chain[0].goal)
        if len(reasoning_chain) < expected_steps * 0.5:  # 步骤过少
            issues.append(ReasoningIssue(
                type=ReasoningErrorType.STEP_SKIP,
                expected_min=expected_steps,
                actual=len(reasoning_chain),
                message="Reasoning chain may be missing intermediate steps",
            ))

        return ReasoningValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
        )
```

#### 3.5.3 恢复策略

| 策略 | 触发条件 | 处理方式 |
|------|----------|----------|
| **推理回溯** | 检测到矛盾 | 回退到上一个有效状态重新推理 |
| **前提验证** | 前提不支持 | 先验证前提的正确性 |
| **步骤补全** | 步骤跳跃 | 要求补充中间推理步骤 |
| **降级执行** | 无法修正 | 降级为更保守的执行策略 |

### 3.6 Infinite Loop（死循环）

#### 3.6.1 场景描述

Agent 在执行过程中陷入重复操作，无法自行退出。

#### 3.6.2 检测机制

```python
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

    def record_execution(self, snapshot: ExecutionSnapshot) -> None:
        """记录执行快照"""
        self.execution_history.append(snapshot)

    def detect_loop(self) -> LoopDetectionResult | None:
        """检测是否存在死循环"""
        history = self.execution_history

        # 检查迭代次数
        if len(history) >= self.max_iterations:
            return LoopDetectionResult(
                detected=True,
                loop_type=LoopType.ITERATION_LIMIT,
                message=f"Exceeded maximum iterations ({self.max_iterations})",
            )

        # 检查重复执行相同操作
        if len(history) >= 3:
            last_three = history[-3:]
            if self._is_same_operation(last_three):
                return LoopDetectionResult(
                    detected=True,
                    loop_type=LoopType.IDENTICAL_OPERATION,
                    message="Repeated identical operation detected",
                )

        # 检查状态循环
        states = [h.state_hash for h in history[-10:]]
        if self._has_cyclic_pattern(states):
            return LoopDetectionResult(
                detected=True,
                loop_type=LoopType.STATE_CYCLE,
                message="Detected cyclic state pattern",
            )

        # 检查输出相似度
        if len(history) >= 2:
            outputs = [h.output_summary for h in history[-3:]]
            if self._are_similar(outputs, self.similarity_threshold):
                return LoopDetectionResult(
                    detected=True,
                    loop_type=LoopType.SIMILAR_OUTPUT,
                    message="Recent outputs are highly similar",
                )

        return None
```

#### 3.6.3 恢复策略

| 策略 | 触发条件 | 处理方式 |
|------|----------|----------|
| **强制终止** | 达到最大迭代次数 | 停止执行，返回当前结果 |
| **操作变更** | 检测到重复操作 | 强制更换为不同操作 |
| **状态重置** | 检测到状态循环 | 重置到上一个检查点 |
| **回退重试** | 无法自行恢复 | 回退到决策点重新规划 |

---

## 4. 错误处理数据流

### 4.1 错误处理流程

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

### 4.2 错误处理配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `error.max_retries` | int | 3 | 最大重试次数 |
| `error.retry_backoff` | str | "exponential" | 退避策略 |
| `error.loop.max_iterations` | int | 20 | 最大迭代次数 |
| `error.hallucination.threshold` | float | 0.7 | 置信度阈值 |
| `error.uncaught_handler` | str | "log_and_raise" | 未捕获异常处理 |

---

## 5. 测试策略

> **说明**：本模块的测试策略已汇总到 [Testing 模块设计文档](./2026-03-29_testing.md)。

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | 2026-03-29 | 初始版本，包含统一异常体系和 Agent 错误处理 |
