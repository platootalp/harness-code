# Observability 模块设计文档

> **模板版本**: 3.0
> **创建日期**: 2026-03-29
> **最后更新**: 2026-03-31

---

## 1. 概述

### 1.1 模块名称

Observability（可观测性模块）

### 1.2 职责

Observability 模块是 Mozi AI Coding Agent 的横切面可观测性组件，负责：
- 提供统一结构化日志系统
- 定义和采集关键 Metrics 指标
- 实现分布式链路追踪
- 支持运行时诊断和性能分析
- 提供审计追溯能力

### 1.3 核心能力

| 能力 | 说明 |
| ---- | ---- |
| 结构化日志 | JSON 格式日志、多级别输出、上下文关联 |
| Metrics 指标 | Counter/Gauge/Histogram/Timer 指标类型 |
| 链路追踪 | Trace ID 传递、Span 生成、调用链可视化 |
| 性能分析 | 关键操作耗时统计、资源使用监控 |
| 审计日志 | 操作记录、安全事件追溯 |

---

## 2. 核心问题与解决方案

### 2.1 日志分散与统一格式

**问题描述**：各模块独立日志，缺乏统一格式和聚合，难以进行全局搜索和问题诊断。

**挑战**：需要建立统一的日志格式规范，同时保持各模块的灵活性。

**解决方案**：采用 Phoenix (Arize) 作为统一可观测性后端。Phoenix 提供 OpenTelemetry 兼容的追踪、日志和指标采集，支持本地部署和云端分析。采用 JSON 格式结构化日志，包含 trace_id、session_id 等上下文信息。通过 LogExporter 支持多种输出格式（Console/JSON File/OTLP）。

### 2.2 性能诊断与调用链追踪

**问题描述**：无法追踪请求在系统中的完整调用链。当出现问题时，难以快速定位性能瓶颈和根本原因。

**挑战**：需要在不修改业务代码的情况下添加链路追踪。异步调用链中 Trace ID 的传递也是难点。

**解决方案**：采用 Phoenix 的 OpenTelemetry 集成实现 Span 机制支持分布式追踪。Phoenix 提供自动 instrumentation（通过 OpenInference），覆盖 LLM 调用、工具执行、检索等关键路径。通过 TraceContext 在进程内传递 Trace ID，通过 EventBus 在异步调用链中传播。Trace ID 可注入到 HTTP Header 实现跨进程追踪。

### 2.3 零侵入设计与性能开销

**问题描述**：可观测性功能不应该显著影响业务代码性能和可维护性。日志、追踪、指标的采集本身也会带来开销。

**挑战**：在零侵入（Zero Instrumentation）设计和性能开销之间取得平衡。

**解决方案**：采用上下文管理器（Context Manager）模式，通过 with 语句自动管理 Span 生命周期。使用异步非阻塞方式记录日志和指标，减少对主流程的影响。控制日志级别和采样率，在生产环境减少详细日志输出。

### 2.4 存储成本与指标缺失

**问题描述**：大量日志和追踪数据的存储成本高昂。同时缺乏关键业务指标，难以评估系统状态。

**挑战**：需要在数据完整性和存储成本之间取得平衡。

**解决方案**：采用 Phoenix 的评估框架（Phoenix Evals）进行自动化评估和指标聚合。Phoenix 支持指标收集、采样和 TTL 控制。通过 OTLP 协议导出到 Phoenix Cloud 或自托管实例进行长期存储和分析。

---

## 3. 数据模型与状态机

### 3.1 核心类型定义

```python
class LogLevel(Enum):
    """日志级别"""
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    CRITICAL = 50


class LogFormat(Enum):
    """日志格式"""
    JSON = "json"
    PLAINTEXT = "plaintext"


class LogOutput(Enum):
    """日志输出"""
    CONSOLE = "console"
    FILE = "file"
    STDERR = "stderr"


@dataclass
class LogRecord:
    """日志记录"""
    timestamp: datetime
    level: LogLevel
    message: str
    trace_id: str | None = None
    span_id: str | None = None
    module: str = ""
    function: str = ""
    session_id: str | None = None
    user_id: str | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """追踪跨度"""
    name: str
    trace_id: str
    span_id: str
    parent_span_id: str | None
    start_time: datetime
    end_time: datetime | None = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[SpanEvent] = field(default_factory=list)


@dataclass
class Counter:
    """计数器指标"""
    name: str
    description: str
    labels: dict[str, str]
    value: float = 0.0


@dataclass
class Gauge:
    """可变数值指标"""
    name: str
    description: str
    labels: dict[str, str]
    value: float = 0.0


@dataclass
class Histogram:
    """直方图指标"""
    name: str
    description: str
    labels: dict[str, str]
    buckets: list[float]
    sum: float = 0.0
    count: int = 0
```

### 3.2 日志格式

```json
{
    "timestamp": "2026-03-29T10:30:00.000Z",
    "level": "INFO",
    "message": "Tool executed successfully",
    "trace_id": "abc123-def456-ghi789",
    "span_id": "span-001",
    "module": "tools",
    "function": "execute_tool",
    "session_id": "sess-xxx",
    "user_id": "user-yyy",
    "duration_ms": 45,
    "metadata": {
        "tool_name": "read_file",
        "file_path": "/Users/lijunyi/road/src/README.md",
        "status": "success"
    }
}
```

### 3.3 预定义指标

| 指标名称 | 类型 | 标签 | 说明 |
| -------- | ---- | ---- | ---- |
| mozi_requests_total | Counter | method, endpoint, status | HTTP 请求总数 |
| mozi_tasks_total | Counter | status | 任务执行总数 |
| mozi_tasks_duration_seconds | Histogram | complexity | 任务耗时分布 |
| mozi_tools_invocations_total | Counter | tool_name, status | 工具调用总数 |
| mozi_tools_duration_seconds | Histogram | tool_name | 工具执行耗时 |
| mozi_session_active | Gauge | - | 当前活跃会话数 |
| mozi_context_tokens | Histogram | - | Token 使用量分布 |
| mozi_model_calls_total | Counter | model, status | 模型调用总数 |
| mozi_model_duration_seconds | Histogram | model | 模型响应耗时 |
| mozi_errors_total | Counter | error_type, module | 错误总数 |

---

## 4. 模块结构

### 4.1 目录结构

```
mozi/observability/
    __init__.py                 # 模块导出
    logger.py                   # 结构化日志器（基于 Phoenix LogExporter）
    metrics.py                  # Metrics 指标定义（Phoenix 指标集成）
    tracer.py                   # 链路追踪器（基于 Phoenix OTel）
    context.py                  # 可观测性上下文（Trace ID、Span ID 等）
    evaluator.py                # 评估器（Phoenix Evals 集成）
    service.py                  # 统一可观测性服务（Phoenix 集成入口）
```

### 4.2 关键文件

| 文件 | 职责 |
| ---- | ---- |
| logger.py | 结构化日志器，提供 log()、debug()、info()、warn()、error() 等方法 |
| metrics.py | 定义指标类型和采集接口（基于 Phoenix Metrics） |
| tracer.py | Trace/Span 管理，Context 传播（基于 Phoenix OTel） |
| context.py | 可观测性上下文（Trace ID、Span ID 等） |
| evaluator.py | 评估器，支持 LLM 响应评估和检索评估（Phoenix Evals） |
| service.py | 统一封装，对外提供简洁接口（Phoenix 初始化入口） |

### 4.3 Phoenix 集成

Phoenix 提供开箱即用的 LLM 可观测性能力，集成方式：

```python
# 安装依赖
# pip install arize-phoenix arize-phoenix-otel arize-phoenix-evals

# 初始化 Phoenix
import phoenix as px
px.launch_app()

# 配置 OpenTelemetry 导出到 Phoenix
from phoenix.otel import Metro
metro = Metro()
tracer_provider = metro.tracer_provider()
```

| Phoenix 包 | 用途 |
| ---- | ---- |
| arize-phoenix | 核心库，本地 UI 和数据管理 |
| arize-phoenix-otel | OpenTelemetry 集成，自动 instrumentation |
| arize-phoenix-evals | 自动化评估框架 |

---

## 5. 接口、交互与流程

### 5.1 结构化日志接口

```python
class StructuredLogger:
    """结构化日志器"""

    def __init__(
        self,
        module: str,
        exporter: LogExporter,
        trace_context: TraceContext | None = None,
    ) -> None:
        self._module = module
        self._exporter = exporter
        self._trace_context = trace_context or TraceContext()

    def debug(self, message: str, **metadata: Any) -> None:
        """DEBUG 级别日志"""
        ...

    def info(self, message: str, **metadata: Any) -> None:
        """INFO 级别日志"""
        ...

    def warn(self, message: str, **metadata: Any) -> None:
        """WARN 级别日志"""
        ...

    def error(self, message: str, **metadata: Any) -> None:
        """ERROR 级别日志"""
        ...
```

### 5.2 链路追踪接口

```python
class Tracer:
    """链路追踪器"""

    def start_span(
        self,
        name: str,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Span:
        """启动新跨度"""
        ...

    def end_span(self, span: Span) -> None:
        """结束跨度"""
        ...

    def inject_context(self, carrier: dict[str, str]) -> dict[str, str]:
        """注入追踪上下文到载体（如 HTTP Header）"""
        ...


class TraceContext:
    """追踪上下文管理器（用于 with 语句）"""

    def __enter__(self) -> Span:
        """进入上下文"""
        ...

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """退出上下文"""
        ...
```

### 5.3 追踪数据流

```
1. 请求进入 Ingress
       │
       ▼
2. Phoenix OTel 自动创建根 Span (ingress)
       │
       ▼
3. Trace ID 存入 TraceContext
       │
       ▼
4. Phoenix 自动 instrumentation 传播到 Orchestrator
       │
       ▼
5. EventBus 携带 trace_id 发布事件（Phoenix span link）
       │
       ▼
6. Tools/Model/Memory 执行，自动生成子 Span（OpenInference）
       │
       ▼
7. Span.end() 记录 end_time
       │
       ▼
8. Phoenix Collector 收集完整 Trace，可视化分析
```

### 5.4 追踪 Span 层次

```
Trace (trace_id)
├── Span: ingress (CLI/MCP 请求入口)
│   └── Span: orchestrator (编排层)
│       ├── Span: intent_detection (意图识别)
│       ├── Span: complexity_scoring (复杂度评估)
│       └── Span: routing (路由决策)
│       ├── Span: context_building (上下文构建)
│       │   ├── Span: memory_recall (记忆检索)
│       │   └── Span: context_compile (上下文编译)
│       ├── Span: agent_execution (Agent 执行)
│       │   └── Span: model_invocation (模型调用)
│       │       └── Span: tools_execution (工具执行)
│       │           ├── Span: tool_name (各工具调用)
│       │           └── Span: tool_result (工具结果处理)
│       └── Span: response_formation (响应生成)
└── Span: storage (存储操作)
    └── Span: session_save (会话保存)
```

---

## 6. 边界与契约

### 6.1 错误码定义

| 错误码 | 说明 | 触发场景 |
| ------ | ---- | -------- |
| `Obs_001` | 追踪初始化失败 | 无法初始化 Phoenix OTel |
| `Obs_002` | Span 创建失败 | 无法创建新的 Span |
| `Obs_003` | 上下文传播失败 | Trace ID 无法在调用链中传播 |
| `Obs_004` | 指标导出失败 | 指标无法导出到后端 |
| `Obs_005` | 日志写入失败 | 日志无法写入到指定输出 |

### 6.2 API 契约

#### 6.2.1 日志查询

```
GET /observability/logs
Query Parameters:
    - level: DEBUG|INFO|WARN|ERROR|CRITICAL
    - start_time: ISO8601
    - end_time: ISO8601
    - trace_id: string
    - session_id: string
    - limit: integer (default 100)

Response:
{
    "logs": [
        {
            "timestamp": "datetime",
            "level": "string",
            "message": "string",
            "trace_id": "string",
            "span_id": "string",
            "module": "string",
            "function": "string",
            "metadata": {}
        }
    ],
    "total": 100
}
```

#### 6.2.2 链路追踪查询

```
GET /observability/traces/{trace_id}

Response:
{
    "trace_id": "string",
    "spans": [
        {
            "span_id": "string",
            "parent_span_id": "string",
            "name": "string",
            "start_time": "datetime",
            "end_time": "datetime",
            "status": "string",
            "attributes": {},
            "events": []
        }
    ]
}
```

#### 6.2.3 指标查询

```
GET /observability/metrics
Query Parameters:
    - name: string (metric name)
    - labels: string (label filters)

Response:
{
    "metrics": [
        {
            "name": "string",
            "type": "counter|gauge|histogram",
            "labels": {},
            "value": 0.0,
            "timestamp": "datetime"
        }
    ]
}
```

### 6.3 日志级别规范

| 级别 | 使用场景 |
| ---- | -------- |
| DEBUG | 详细调试信息，参数值、返回值 |
| INFO | 正常业务流程：任务开始/结束、工具执行 |
| WARN | 潜在问题：重试、fallback、配置缺失 |
| ERROR | 操作失败：工具执行失败、API 错误 |
| CRITICAL | 系统级错误：认证失败、安全违规 |

### 6.4 指标类型说明

| 类型 | 说明 | 使用场景 |
| ---- | ---- | -------- |
| Counter | 递增计数器 | 请求次数、错误次数、任务完成数 |
| Gauge | 可变数值 | 当前队列深度、活跃连接数 |
| Histogram | 分布统计 | 请求耗时、文件大小分布 |
| Timer | 时间测量 | 操作耗时，自动记录 duration_ms |

### 6.5 Trace 上下文传播方式

| 传播方式 | 说明 | 实现 |
| -------- | ---- | ---- |
| In-Process | 同一进程内传递 | ThreadLocal/ContextVar |
| Cross-Process | 进程间传递（如 MCP） | HTTP Header (traceparent) |
| Event-Driven | 事件总线传递 | Event Payload |

---

## 7. 实现细节

### 7.1 日志级别规范

| 级别 | 使用场景 |
| ---- | -------- |
| DEBUG | 详细调试信息，参数值、返回值 |
| INFO | 正常业务流程：任务开始/结束、工具执行 |
| WARN | 潜在问题：重试、fallback、配置缺失 |
| ERROR | 操作失败：工具执行失败、API 错误 |
| CRITICAL | 系统级错误：认证失败、安全违规 |

### 7.2 指标类型说明

| 类型 | 说明 | 使用场景 |
| ---- | ---- | -------- |
| Counter | 递增计数器 | 请求次数、错误次数、任务完成数 |
| Gauge | 可变数值 | 当前队列深度、活跃连接数 |
| Histogram | 分布统计 | 请求耗时、文件大小分布 |
| Timer | 时间测量 | 操作耗时，自动记录 duration_ms |

### 7.3 Trace 上下文传播方式

| 传播方式 | 说明 | 实现 |
| -------- | ---- | ---- |
| In-Process | 同一进程内传递 | ThreadLocal/ContextVar |
| Cross-Process | 进程间传递（如 MCP） | HTTP Header (traceparent) |
| Event-Driven | 事件总线传递 | Event Payload |

---

## 8. 配置

> **说明**：Observability 模块的配置通过 Phoenix 初始化参数配置，暂不支持外部配置文件。

### 8.1 Phoenix 配置项

| 配置项 | 类型 | 默认值 | 说明 |
| ------ | ---- | ------ | ---- |
| `phoenix.endpoint` | string | `http://localhost:6006` | Phoenix server 端点 |
| `phoenix.project_name` | string | `mozi` | Phoenix 项目名称 |
| `phoenix.export_strategy` | string | `always` | 导出策略（always/never/batch） |
| `phoenix.span_batch_size` | integer | `100` | Span 批次大小 |
| `otel.service_name` | string | `mozi` | OpenTelemetry 服务名 |
| `otel.exporter` | string | `otlp` | OTLP 导出器类型 |

---

## 9. 度量指标

### 9.1 核心指标

| 指标名称 | 类型 | 标签 | 说明 |
| -------- | ---- | ---- | ---- |
| `observability_logs_total` | Counter | level, module | 日志记录总数 |
| `observability_spans_created_total` | Counter | operation | Span 创建总数 |
| `observability_traces_exported_total` | Counter | status | Trace 导出总数 |
| `observability_metrics_export_duration_seconds` | Histogram | - | 指标导出耗时 |
| `observability_tracer_initialization_duration_seconds` | Histogram | - | 追踪器初始化耗时 |

### 9.2 Phoenix 预定义指标

| 指标名称 | 类型 | 标签 | 说明 |
| -------- | ---- | ---- | ---- |
| `mozi_requests_total` | Counter | method, endpoint, status | HTTP 请求总数 |
| `mozi_tasks_total` | Counter | status | 任务执行总数 |
| `mozi_tasks_duration_seconds` | Histogram | complexity | 任务耗时分布 |
| `mozi_tools_invocations_total` | Counter | tool_name, status | 工具调用总数 |
| `mozi_tools_duration_seconds` | Histogram | tool_name | 工具执行耗时 |
| `mozi_session_active` | Gauge | - | 当前活跃会话数 |
| `mozi_context_tokens` | Histogram | - | Token 使用量分布 |
| `mozi_model_calls_total` | Counter | model, status | 模型调用总数 |
| `mozi_model_duration_seconds` | Histogram | model | 模型响应耗时 |
| `mozi_errors_total` | Counter | error_type, module | 错误总数 |

### 9.3 指标采集状态

**状态**：待定义

---

## 10. 参考

- **Phoenix (Arize)**：[GitHub - Arize-ai/phoenix](https://github.com/Arize-ai/phoenix)
- **OpenTelemetry Python**：[opentelemetry-python](https://opentelemetry.io/docs/instrumentation/python/)
- **OpenInference**：[LLM 自动 instrumentation 规范](https://github.com/Arize-ai/openinference)
- **错误处理**：遵循统一异常体系，见 [error_handling.md](./2026-03-29_error_handling.md)
- **测试策略**：见 [testing.md](./2026-03-29_testing.md)
- **相关模块**：Config、[EventBus](./2026-03-29_eventbus.md)、[Ingress](./2026-03-29_ingress.md)

---

## 变更记录

| 版本 | 日期 | 变更内容 |
| ---- | ---- | -------- |
| 3.0 | 2026-03-31 | 重组为模板 v3.0 结构，新增 §6 边界与契约、§9 度量指标 |
| 2.1 | 2026-03-30 | 集成 Phoenix (Arize) 作为可观测性后端，添加 OTel 集成和 Evals 评估 |
| 2.0 | 2026-03-30 | 重构为模板 v2.0 结构，核心问题改为段落描述 |
| 1.1 | 2026-03-29 | 汇总各模块可观测性内容 |
| 1.0 | 2026-03-29 | 初始版本 |

_版本: 3.0_
_更新日期: 2026-03-31_
