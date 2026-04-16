# Resilience 模块设计文档

> **模板版本**: 3.0
> **创建日期**: 2026-03-29
> **最后更新**: 2026-03-31

---

## 1. 概述

### 1.1 模块名称

Resilience（稳定性模块）

### 1.2 职责

Resilience 模块是 Mozi AI Coding Agent 的横切面稳定性组件，负责：
- 提供统一的限流机制，防止系统过载
- 实现熔断器模式，快速失败并防止级联故障
- 提供指数退避重试机制，提高请求成功率
- 实现超时控制，避免资源长时间占用
- 监控和记录稳定性指标，支持可观测性

### 1.3 核心能力

| 能力 | 说明 |
| ---- | ---- |
| Rate Limit | 令牌桶/滑动窗口限流，支持多维度配置 |
| 熔断器 | 三态状态机（CLOSED/OPEN/HALF_OPEN），自动恢复 |
| 重试机制 | 指数退避+抖动，支持可配置重试策略 |
| 超时控制 | 多层级超时配置（请求/连接/读取） |
| 指标暴露 | 限流/熔断/重试/超时指标收集 |

---

## 2. 核心问题与解决方案

### 2.1 系统过载与限流保护

**问题描述**：高并发请求导致系统资源耗尽，服务质量下降。需要有效的限流机制来保护系统。

**挑战**：如何在保证公平性的同时不误杀正常请求。限流粒度的设计直接影响系统可用性。

**解决方案**：实现 TokenBucketRateLimiter 令牌桶算法，支持滑动窗口统计。同时支持多维度限流（全境、用户、工具、端点），确保不同维度的请求都能得到公平处理。

### 2.2 级联故障与熔断保护

**问题描述**：依赖服务不可用时，如果持续调用会导致本系统资源耗尽，引发级联故障。

**挑战**：熔断阈值的设置需要权衡——过于敏感会导致误判，过于迟钝则无法快速保护系统。

**解决方案**：实现三态状态机（CLOSED/OPEN/HALF_OPEN）的 CircuitBreaker。CLOSED 状态正常请求，OPEN 状态快速失败防止资源耗尽，HALF_OPEN 状态允许探测请求试探服务是否恢复。

### 2.3 瞬时故障与重试策略

**问题描述**：网络抖动、服务短暂不可用等情况导致的瞬时故障，需要有效的重试机制来提高成功率。

**挑战**：不当的重试策略可能加剧系统负载，甚至引发"惊群效应"。

**解决方案**：实现 RetryPolicy 指数退避策略，重试间隔按指数增长。同时添加 jitter（抖动）避免多请求同时重试。配置可重试异常类型，只对暂时性故障进行重试。

### 2.4 资源泄漏与超时控制

**问题描述**：请求超时后资源未正确释放，导致连接泄漏、内存增长等问题。

**挑战**：异步调用中超时如何正确传递和取消。不同层级的超时（连接/读取/请求/任务）需要协调。

**解决方案**：实现 TimeoutManager 多层级超时控制。使用 asyncio.wait_for 设置超时，确保超时后取消协程释放资源。提供多层级超时配置，满足不同场景需求。

---

## 3. 数据模型与状态机

### 3.1 核心类型定义

```python
from enum import Enum
from mozi.exceptions import MoziError


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: float = 30.0
    half_open_max_calls: int = 3


@dataclass
class CircuitBreakerStats:
    """熔断器统计"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    state_changes: int = 0


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: float = 0.1
    retryable_exceptions: tuple[type[Exception], ...] | None = None


@dataclass
class TimeoutConfig:
    """超时配置"""
    connect_timeout: float = 10.0
    read_timeout: float = 30.0
    request_timeout: float = 60.0
    task_timeout: float = 300.0


class ResilienceError(MoziError):
    """Resilience 模块基础异常"""
    ...


class RateLimitError(ResilienceError):
    """限流异常"""
    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class CircuitOpenError(ResilienceError):
    """熔断器开启异常"""
    def __init__(self, message: str, circuit_name: str) -> None:
        super().__init__(message)
        self.circuit_name = circuit_name


class RetryExhaustedError(ResilienceError):
    """重试次数耗尽异常"""
    ...
```

### 3.2 熔断器状态机

```
        ┌──────────────────────────────────────────┐
        │                                          │
        ▼                                          │
    ┌───────┐    失败次数超限     ┌───────┐   探测   ┌───────────┐
    │CLOSED │ ─────────────────► │ OPEN  │ ───────► │HALF_OPEN  │
    │ 正常   │                   │ 熔断   │          │ 半开      │
    └───────┘ ◄───────────────── └───────┘ 失败    └───────────┘
        ▲                              │   成功        │
        │         成功次数超限          └───────────────┘
        │              │
        └──────────────┘
```

| 状态 | 说明 | 行为 |
| ---- | ---- | ---- |
| CLOSED | 正常工作 | 请求正常通过，失败计数 |
| OPEN | 熔断触发 | 请求直接拒绝，快速失败 |
| HALF_OPEN | 半开探测 | 允许有限探测请求 |

### 3.3 熔断器状态流转表

| 当前状态 | 触发条件 | 下一状态 | 动作 |
| -------- | -------- | -------- | ---- |
| CLOSED | 连续失败 >= failure_threshold | OPEN | 开启熔断 |
| CLOSED | 请求成功 | CLOSED | 重置失败计数 |
| OPEN | 超过 timeout | HALF_OPEN | 允许探测 |
| HALF_OPEN | 探测失败 | OPEN | 重新熔断 |
| HALF_OPEN | 连续成功 >= success_threshold | CLOSED | 恢复正常 |

---

## 4. 模块结构

### 4.1 目录结构

```
mozi/capabilities/resilience/
    __init__.py                  # 模块导出
    rate_limiter.py               # RateLimiter 限流器
    circuit_breaker.py             # CircuitBreaker 熔断器
    retry.py                      # RetryPolicy 重试策略
    timeout.py                    # TimeoutManager 超时管理
    decorators.py                # 装饰器便捷接口
    metrics.py                    # 稳定性指标收集
    exceptions.py                 # 异常类型定义
```

### 4.2 关键文件

| 文件 | 职责 |
| ---- | ---- |
| rate_limiter.py | 令牌桶算法实现，支持滑动窗口统计 |
| circuit_breaker.py | 熔断器状态机实现 |
| retry.py | 指数退避重试策略实现 |
| timeout.py | 超时上下文管理 |
| decorators.py | 便捷装饰器（@rate_limit, @circuit_break, @retry, @timeout） |
| metrics.py | Prometheus 指标暴露 |
| exceptions.py | ResilienceError 等异常定义 |

---

## 5. 接口、交互与流程

### 5.1 核心接口定义

```python
class RateLimiter:
    """限流器基类"""

    @abstractmethod
    async def acquire(self, key: str) -> bool:
        """尝试获取令牌"""
        ...

    @abstractmethod
    async def release(self, key: str) -> None:
        """释放令牌"""
        ...

    @abstractmethod
    def get_wait_time(self, key: str) -> float:
        """获取等待时间（秒）"""
        ...


class CircuitBreaker:
    """熔断器"""

    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        ...

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """执行函数（带熔断保护）"""
        ...


class RetryPolicy:
    """重试策略"""

    def should_retry(
        self,
        exception: Exception,
        attempt: int,
    ) -> bool:
        """判断是否应该重试"""
        ...

    def get_delay(self, attempt: int) -> float:
        """计算延迟时间"""
        ...

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """执行带重试的函数"""
        ...


class TimeoutManager:
    """超时管理器"""

    async def with_timeout(
        self,
        timeout: float,
        coro: Coroutine[Any, Any, T],
    ) -> T:
        """为协程添加超时"""
        ...
```

### 5.2 请求处理流程

```
用户请求
    │
    ▼
RateLimiter.acquire(key)
    │
    ├──► 有令牌 ──► 继续
    │
    └──► 无令牌 ──► RateLimitError（包含 retry_after）
    │
    ▼
CircuitBreaker.call(func)
    │
    ├──► CLOSED ──► 执行请求
    │
    ├──► HALF_OPEN ──► 允许探测请求
    │
    └──► OPEN ──► CircuitOpenError（快速失败）
    │
    ▼
RetryPolicy.execute(func)
    │
    ├──► 成功 ──► 返回结果
    │
    └──► 失败（可重试）─► 计算退避延迟 ─► 等待 ─► 重试
    │                              │
    │                              └──► 达到最大次数 ─► RetryExhaustedError
    ▼
TimeoutManager.with_timeout(coro)
    │
    ├──► 完成 ──► 返回结果
    │
    └──► 超时 ──► TimeoutError
    │
    ▼
EventBus.publish("resilience_event", payload)
    │
    ▼
MetricsCollector 记录指标
```

---

## 6. 边界与契约

### 6.1 错误码定义

| 错误码 | 说明 | 触发场景 |
| ------ | ---- | -------- |
| `Res_001` | 限流触发 | 请求被限流器拒绝 |
| `Res_002` | 熔断器开启 | 熔断器处于 OPEN 状态，请求被拒绝 |
| `Res_003` | 重试次数耗尽 | 达到最大重试次数仍失败 |
| `Res_004` | 超时 | 操作超过指定超时时间 |
| `Res_005` | 熔断器状态转换失败 | 熔断器状态机转换异常 |

### 6.2 API 契约

#### 6.2.1 限流器状态

```
GET /resilience/rate_limit/{key}

Response:
{
    "key": "string",
    "allowed": true,
    "wait_time": 0.0,
    "tokens": 100.0
}
```

#### 6.2.2 熔断器状态

```
GET /resilience/circuit_breaker/{name}

Response:
{
    "name": "string",
    "state": "closed|open|half_open",
    "stats": {
        "total_calls": 0,
        "successful_calls": 0,
        "failed_calls": 0,
        "rejected_calls": 0,
        "state_changes": 0
    },
    "config": {
        "failure_threshold": 5,
        "success_threshold": 2,
        "timeout": 30.0
    }
}
```

### 6.3 可重试异常类型

| 异常类型 | 可重试 | 说明 |
| -------- | ------ | ---- |
| NetworkError | 是 | 网络连接失败 |
| TimeoutError | 是 | 请求超时 |
| ServiceUnavailable | 是 | 服务不可用（503） |
| RateLimitError | 是 | 限流错误（429） |
| ValidationError | 否 | 参数验证错误 |
| AuthError | 否 | 认证错误 |

---

## 7. 实现细节

### 7.1 限流算法

**令牌桶算法**：

```
令牌桶核心参数：
    - capacity: 桶容量（最大令牌数）
    - refill_rate: 令牌填充速率（每秒）
    - tokens: 当前令牌数

工作原理：
    1. 每次请求消耗 1 个令牌
    2. 令牌以 refill_rate 速度补充
    3. 桶满时新令牌溢出
    4. 无令牌时请求被拒绝
```

**滑动窗口算法**：

```
滑动窗口核心参数：
    - window_size: 窗口大小（秒）
    - max_requests: 窗口内最大请求数
    - requests: 时间戳列表

工作原理：
    1. 记录每个请求的时间戳
    2. 窗口滑动时清理过期时间戳
    3. 窗口内请求数超过限制则拒绝
    4. 使用链表实现 O(1) 插入删除
```

### 7.2 重试策略

指数退避公式：

```
重试间隔 = base_delay * (2 ^ attempt) + jitter
```

### 7.3 多维度限流

| 维度 | 说明 | 示例 |
| ---- | ---- | ---- |
| 全局限流 | 全局请求总量限制 | 1000 req/s |
| 用户限流 | 按用户 ID 限制 | 10 req/s/user |
| 工具限流 | 按工具名称限制 | 100 req/s/tool |
| 端点限流 | 按 API 端点限制 | 50 req/s/endpoint |

---

## 8. 配置

> **说明**：本模块的配置项已汇总到 [Config 模块设计文档](./2026-03-29_config.md#79-resilience-配置)。

---

## 9. 度量指标

### 9.1 核心指标

| 指标名称 | 类型 | 标签 | 说明 |
| -------- | ---- | ---- | ---- |
| `resilience_rate_limit_total` | Counter | key, result | 限流器请求总数 |
| `resilience_rate_limit_wait_time_seconds` | Histogram | key | 限流等待时间分布 |
| `resilience_circuit_breaker_state` | Gauge | name, state | 熔断器当前状态 |
| `resilience_circuit_breaker_calls_total` | Counter | name, result | 熔断器调用总数 |
| `resilience_retry_total` | Counter | name, exception | 重试次数统计 |
| `resilience_timeout_total` | Counter | name | 超时次数统计 |
| `resilience_failure_total` | Counter | name, type | 失败次数统计 |

### 9.2 指标采集状态

**状态**：待定义

---

## 10. 参考

- **错误处理**：遵循统一异常体系，见 [error_handling.md](./2026-03-29_error_handling.md)
- **测试策略**：见 [testing.md](./2026-03-29_testing.md)
- **相关模块**：Model、[EventBus](./2026-03-29_eventbus.md)、[Observability](./2026-03-29_observability.md)

---

## 变更记录

| 版本 | 日期 | 变更内容 |
| ---- | ---- | -------- |
| 3.0 | 2026-03-31 | 重组为模板 v3.0 结构，新增 §6 边界与契约、§9 度量指标 |
| 2.1 | 2026-03-31 | 配置项迁移至 Config 模块统一管理 |
| 2.0 | 2026-03-30 | 重构为模板 v2.0 结构，核心问题改为段落描述 |
| 1.0 | 2026-03-29 | 初始版本 |

_版本: 3.0_
_更新日期: 2026-03-31_
