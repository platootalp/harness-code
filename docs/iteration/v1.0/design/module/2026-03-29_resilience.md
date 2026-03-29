# Resilience 模块设计文档

## 1. 模块概述

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

### 1.4 核心问题

| 问题 | 说明 |
| ---- | ---- |
| 系统过载 | 高并发请求导致系统资源耗尽 |
| 级联故障 | 依赖服务不可用导致本系统崩溃 |
| 瞬时故障 | 网络抖动、服务短暂不可用 |
| 资源泄漏 | 请求超时后资源未正确释放 |

### 1.5 难点

| 难点 | 说明 |
| ---- | ---- |
| 限流粒度 | 如何在保证公平性的同时不误杀正常请求 |
| 熔断阈值 | 失败率阈值如何设置，过于敏感或迟钝都不行 |
| 重试策略 | 指数退避参数如何选择，抖动如何添加 |
| 超时传递 | 异步调用中超时如何正确传递和取消 |

### 1.6 解决方案

| 方案 | 说明 |
| ---- | ---- |
| TokenBucketRateLimiter | 令牌桶算法，支持滑动窗口统计 |
| CircuitBreaker | 三态状态机（CLOSED/OPEN/HALF_OPEN），自动恢复 |
| RetryPolicy | 指数退避 + 抖动（jitter），避免惊群效应 |
| TimeoutManager | 多层级超时控制，自动取消超时请求 |

---

## 2. 模块结构

### 2.1 目录结构

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

### 2.2 关键文件

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

## 3. Rate Limit（限流）

### 3.1 限流策略

Mozi 支持两种限流算法：

| 算法 | 适用场景 | 特点 |
| ---- | -------- | ---- |
| 令牌桶（Token Bucket） | API 调用限流 | 允许突发流量，匀速消耗 |
| 滑动窗口（Sliding Window） | 请求频率控制 | 统计精确，平滑限制 |

### 3.2 令牌桶实现

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

### 3.3 滑动窗口实现

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

### 3.4 多维度限流

| 维度 | 说明 | 示例 |
| ---- | ---- | ---- |
| 全局限流 | 全局请求总量限制 | 1000 req/s |
| 用户限流 | 按用户 ID 限制 | 10 req/s/user |
| 工具限流 | 按工具名称限制 | 100 req/s/tool |
| 端点限流 | 按 API 端点限制 | 50 req/s/endpoint |

### 3.5 RateLimiter 接口

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


class TokenBucketRateLimiter(RateLimiter):
    """令牌桶限流器"""

    def __init__(
        self,
        capacity: int,
        refill_rate: float,
        storage: dict[str, TokenBucketState] | None = None,
    ) -> None:
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._storage = storage or {}

    async def acquire(self, key: str) -> bool:
        """尝试获取令牌"""
        state = self._get_or_create_state(key)
        now = time.monotonic()

        # 补充令牌
        elapsed = now - state.last_refill
        new_tokens = min(
            self._capacity,
            state.tokens + elapsed * self._refill_rate,
        )
        state.tokens = new_tokens
        state.last_refill = now

        if state.tokens >= 1:
            state.tokens -= 1
            return True
        return False

    def _get_or_create_state(
        self,
        key: str,
    ) -> TokenBucketState:
        """获取或创建桶状态"""
        if key not in self._storage:
            self._storage[key] = TokenBucketState(
                tokens=float(self._capacity),
                last_refill=time.monotonic(),
            )
        return self._storage[key]


class SlidingWindowRateLimiter(RateLimiter):
    """滑动窗口限流器"""

    def __init__(
        self,
        window_size: float,
        max_requests: int,
        storage: dict[str, SlidingWindowState] | None = None,
    ) -> None:
        self._window_size = window_size
        self._max_requests = max_requests
        self._storage = storage or {}

    async def acquire(self, key: str) -> bool:
        """尝试获取令牌"""
        state = self._get_or_create_state(key)
        now = time.monotonic()
        cutoff = now - self._window_size

        # 清理过期时间戳
        while state.timestamps and state.timestamps[0] < cutoff:
            state.timestamps.popleft()

        if len(state.timestamps) < self._max_requests:
            state.timestamps.append(now)
            return True
        return False

    def get_wait_time(self, key: str) -> float:
        """计算需要等待的时间"""
        if key not in self._storage:
            return 0.0

        state = self._storage[key]
        if len(state.timestamps) < self._max_requests:
            return 0.0

        oldest = state.timestamps[0]
        return max(0.0, oldest + self._window_size - time.monotonic())
```

---

## 4. 熔断器（Circuit Breaker）

### 4.1 熔断状态机

熔断器实现三态状态机：

```
        ┌──────────────────────────────────────────┐
        │                                          │
        ▼                                          │
    ┌───────┐    失败次数超限     ┌───────┐   探测   ┌───────────┐
    │CLOSED │ ─────────────────► │ OPEN  │ ───────► │HALF_OPEN  │
    │ 正常   │                   │ 熔断   │          │ 半开      │
    └───────┘ ◄─────────────────� └───────┘ 失败    └───────────┘
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

### 4.2 配置参数

| 参数 | 说明 | 默认值 |
| ---- | ---- | ------ |
| failure_threshold | 熔断触发失败次数 | 5 |
| success_threshold | 恢复成功次数 | 2 |
| timeout | OPEN 状态持续时间（秒） | 30 |
| half_open_max_calls | 半开状态最大探测数 | 3 |

### 4.3 CircuitBreaker 接口

```python
from enum import Enum


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


class CircuitBreaker:
    """熔断器"""

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        self._name = name
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._half_open_calls = 0
        self._stats = CircuitBreakerStats()

    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """执行函数（带熔断保护）"""
        if not self._can_execute():
            self._stats.rejected_calls += 1
            raise CircuitOpenError(
                f"Circuit {self._name} is OPEN"
            )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            self._stats.successful_calls += 1
            return result
        except Exception as e:
            self._on_failure()
            self._stats.failed_calls += 1
            raise

    def _can_execute(self) -> bool:
        """判断是否可以执行"""
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self._config.half_open_max_calls
        return False

    def _on_success(self) -> None:
        """处理成功"""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._config.success_threshold:
                self._transition_to(CircuitState.CLOSED)
        else:
            self._failure_count = 0

    def _on_failure(self) -> None:
        """处理失败"""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)
        elif self._failure_count >= self._config.failure_threshold:
            self._transition_to(CircuitState.OPEN)

    def _should_attempt_reset(self) -> bool:
        """判断是否应该尝试重置"""
        if self._last_failure_time is None:
            return False
        elapsed = time.monotonic() - self._last_failure_time
        return elapsed >= self._config.timeout

    def _transition_to(self, new_state: CircuitState) -> None:
        """状态转换"""
        old_state = self._state
        self._state = new_state
        self._stats.state_changes += 1

        # 重置计数器
        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._success_count = 0
            self._half_open_calls = 0

        logger.info(
            f"Circuit {self._name}: {old_state.value} -> {new_state.value}"
        )
```

---

## 5. 重试机制（Retry）

### 5.1 指数退避策略

重试机制使用指数退避算法：

```
重试间隔 = base_delay * (2 ^ attempt) + jitter

参数：
    - base_delay: 基础延迟（秒），默认 1.0
    - max_delay: 最大延迟（秒），默认 60.0
    - max_attempts: 最大重试次数，默认 3
    - jitter: 抖动系数，默认 0.1

示例（base_delay=1, max_delay=60）：
    尝试 1: 1s + random(0, 0.1)
    尝试 2: 2s + random(0, 0.2)
    尝试 3: 4s + random(0, 0.4)
```

### 5.2 可重试异常

| 异常类型 | 可重试 | 说明 |
| -------- | ------ | ---- |
| NetworkError | 是 | 网络连接失败 |
| TimeoutError | 是 | 请求超时 |
| ServiceUnavailable | 是 | 服务不可用（503） |
| RateLimitError | 是 | 限流错误（429） |
| ValidationError | 否 | 参数验证错误 |
| AuthError | 否 | 认证错误 |

### 5.3 RetryPolicy 接口

```python
@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: float = 0.1
    retryable_exceptions: tuple[type[Exception], ...] | None = None


class RetryPolicy:
    """重试策略"""

    DEFAULT_RETRYABLE: tuple[type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        ServiceUnavailableError,
        RateLimitError,
    )

    def __init__(self, config: RetryConfig | None = None) -> None:
        self._config = config or RetryConfig()
        self._retryable = (
            self._config.retryable_exceptions
            or self.DEFAULT_RETRYABLE
        )

    def should_retry(
        self,
        exception: Exception,
        attempt: int,
    ) -> bool:
        """判断是否应该重试"""
        if attempt >= self._config.max_attempts:
            return False
        return isinstance(exception, self._retryable)

    def get_delay(self, attempt: int) -> float:
        """计算延迟时间"""
        import random

        exponential_delay = min(
            self._config.base_delay * (2 ** attempt),
            self._config.max_delay,
        )
        jitter_range = exponential_delay * self._config.jitter
        jitter = random.uniform(-jitter_range, jitter_range)
        return max(0.0, exponential_delay + jitter)

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """执行带重试的函数"""
        last_exception: Exception | None = None

        for attempt in range(self._config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if not self.should_retry(e, attempt):
                    raise
                if attempt < self._config.max_attempts - 1:
                    delay = self.get_delay(attempt)
                    logger.warning(
                        f"Retry attempt {attempt + 1} after {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)

        if last_exception is not None:
            raise last_exception
```

---

## 6. 超时控制（Timeout）

### 6.1 超时层级

| 层级 | 说明 | 默认值 |
| ---- | ---- | ------ |
| 连接超时 | 建立连接的时间 | 10s |
| 读取超时 | 等待响应的时间 | 30s |
| 请求超时 | 整个请求的时间 | 60s |
| 任务超时 | 任务执行的总时间 | 300s |

### 6.2 TimeoutManager 接口

```python
@dataclass
class TimeoutConfig:
    """超时配置"""
    connect_timeout: float = 10.0
    read_timeout: float = 30.0
    request_timeout: float = 60.0
    task_timeout: float = 300.0


class TimeoutManager:
    """超时管理器"""

    def __init__(self, config: TimeoutConfig | None = None) -> None:
        self._config = config or TimeoutConfig()

    async def with_timeout(
        self,
        timeout: float,
        coro: Coroutine[Any, Any, T],
    ) -> T:
        """为协程添加超时"""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation timed out after {timeout}s")

    async def with_request_timeout(
        self,
        coro: Coroutine[Any, Any, T],
    ) -> T:
        """使用请求超时"""
        return await self.with_timeout(
            self._config.request_timeout,
            coro,
        )

    async def with_task_timeout(
        self,
        coro: Coroutine[Any, Any, T],
    ) -> T:
        """使用任务超时"""
        return await self.with_timeout(
            self._config.task_timeout,
            coro,
        )

    def create_timed_task(
        self,
        coro: Coroutine[Any, Any, T],
        timeout: float | None = None,
    ) -> asyncio.Task[T]:
        """创建带超时的任务"""
        loop = asyncio.get_event_loop()
        if timeout is None:
            timeout = self._config.request_timeout
        return loop.create_task(
            self.with_timeout(timeout, coro)
        )
```

---

## 7. 接口设计

### 7.1 核心类型定义

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from asyncio import Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class ResilienceError(Exception):
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
    def __init__(
        self,
        message: str,
        attempts: int,
        last_exception: Exception,
    ) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception


@dataclass
class ResilienceMetrics:
    """稳定性指标"""
    rate_limit_hits: int = 0
    rate_limit_rejections: int = 0
    circuit_state_changes: int = 0
    circuit_rejections: int = 0
    retry_attempts: int = 0
    timeout_errors: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)
```

### 7.2 装饰器接口

```python
def rate_limit(
    calls: int,
    period: float,
    key_func: Callable[..., str] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """限流装饰器

    Args:
        calls: 周期内最大调用次数
        period: 周期（秒）
        key_func: 限流 key 提取函数
    """
    ...


def circuit_break(
    name: str,
    failure_threshold: int = 5,
    success_threshold: int = 2,
    timeout: float = 30.0,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """熔断装饰器

    Args:
        name: 熔断器名称
        failure_threshold: 熔断触发失败次数
        success_threshold: 恢复成功次数
        timeout: OPEN 状态持续时间
    """
    ...


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: float = 0.1,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """重试装饰器

    Args:
        max_attempts: 最大重试次数
        base_delay: 基础延迟
        max_delay: 最大延迟
        jitter: 抖动系数
        retryable_exceptions: 可重试异常列表
    """
    ...


def timeout_decorator(
    seconds: float,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """超时装饰器

    Args:
        seconds: 超时时间（秒）
    """
    ...
```

### 7.3 ResilienceService 统一接口

```python
class ResilienceService:
    """统一稳定性服务"""

    def __init__(
        self,
        rate_limiter: RateLimiter,
        circuit_breaker: CircuitBreaker,
        retry_policy: RetryPolicy,
        timeout_manager: TimeoutManager,
    ) -> None:
        self._rate_limiter = rate_limiter
        self._circuit_breaker = circuit_breaker
        self._retry_policy = retry_policy
        self._timeout_manager = timeout_manager

    async def execute(
        self,
        key: str,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        rate_limit_enabled: bool = True,
        circuit_break_enabled: bool = True,
        retry_enabled: bool = True,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> T:
        """统一执行入口

        整合限流、熔断、重试、超时功能
        """
        # 1. 限流检查
        if rate_limit_enabled:
            if not await self._rate_limiter.acquire(key):
                wait_time = self._rate_limiter.get_wait_time(key)
                raise RateLimitError(
                    f"Rate limit exceeded for {key}",
                    retry_after=wait_time,
                )

        # 2. 执行（熔断 + 重试 + 超时）
        coro = self._circuit_breaker.call(func, *args, **kwargs)
        if retry_enabled:
            coro = self._execute_with_retry(coro)
        if timeout is not None:
            coro = self._timeout_manager.with_timeout(timeout, coro)

        return await coro

    async def _execute_with_retry(
        self,
        coro: Coroutine[Any, Any, T],
    ) -> Coroutine[Any, Any, T]:
        """包装重试逻辑"""
        # 重试逻辑实现
        ...
```

---

## 8. 数据流

### 8.1 与各模块的交互关系

```
┌─────────────────────────────────────────────────────────┐
│                    Orchestrator                          │
│              （任务编排与 Resilience 上下文构建）             │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  Resilience Module                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ RateLimiter │  │ Circuit     │  │ RetryPolicy     │  │
│  │             │  │ Breaker     │  │                 │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
│                          │                               │
│  ┌─────────────┐         │                               │
│  │ Timeout     │         │                               │
│  │ Manager     │         │                               │
│  └─────────────┘         │                               │
└─────────────────────────┼───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    Model Adapter                         │
│              （模型调用，受稳定性保护）                      │
└─────────────────────────────────────────────────────────┘
```

### 8.2 请求处理流程

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

### 8.3 熔断器状态流转

| 当前状态 | 触发条件 | 下一状态 | 动作 |
| -------- | -------- | -------- | ---- |
| CLOSED | 连续失败 >= failure_threshold | OPEN | 开启熔断 |
| CLOSED | 请求成功 | CLOSED | 重置失败计数 |
| OPEN | 超过 timeout | HALF_OPEN | 允许探测 |
| HALF_OPEN | 探测失败 | OPEN | 重新熔断 |
| HALF_OPEN | 连续成功 >= success_threshold | CLOSED |恢复正常 |

---

## 9. 错误处理

> **统一错误处理**：本模块的错误处理遵循统一异常体系，详细规范见 [error_handling.md](./2026-03-29_error_handling.md)。

---

## 10. 测试策略

> **说明**：本模块的测试策略已汇总到 [Testing 模块设计文档](./2026-03-29_testing.md)。
> 统一错误处理规范见 [error_handling.md](./2026-03-29_error_handling.md)。

---

## 变更记录

| 版本 | 日期 | 变更内容 |
| ---- | ---- | -------- |
| 1.0 | 2026-03-29 | 初始版本 |

_版本: 1.0_
_更新日期: 2026-03-29_
