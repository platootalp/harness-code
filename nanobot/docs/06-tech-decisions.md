# 06 - 技术决策与架构决策记录

## 文档概述

本文档记录了 nanobot 开发过程中的关键技术决策。每个决策都以 ADR（架构决策记录）格式记录，解释决策背景、考虑的选项、做出的决策以及后果。

**目标读者**: 贡献者、维护者以及任何希望理解 nanobot 设计背后"为什么"的人。

---

## 目录

1. [ADR-001: 使用 LiteLLM 进行提供商抽象](#adr-001-使用-litellm-进行提供商抽象)
2. [ADR-002: 使用 Pydantic v2 进行配置管理](#adr-002-使用-pydantic-v2-进行配置管理)
3. [ADR-003: 使用 Markdown + Shell 编写技能](#adr-003-使用-markdown--shell-编写技能)
4. [ADR-004: 使用 CSV/JSON 进行记忆存储](#adr-004-使用-csvjson-进行记忆存储)
5. [ADR-005: 使用 MessageBus 进行内部通信](#adr-005-使用-messagebus-进行内部通信)
6. [ADR-006: 使用 Typer 作为 CLI 框架](#adr-006-使用-typer-作为-cli-框架)
7. [ADR-007: 基于文件的配置](#adr-007-基于文件的配置)
8. [ADR-008: Async/Await 并发模型](#adr-008-asyncawait-并发模型)
9. [ADR-009: 单体架构](#adr-009-单体架构)
10. [ADR-010: 提供商注册表模式](#adr-010-提供商注册表模式)
11. [决策总结矩阵](#决策总结矩阵)

---

## ADR-001: 使用 LiteLLM 进行提供商抽象

### 状态
**已接受** - 已实现并投入生产

### 背景
nanobot 需要支持多个 LLM 提供商（OpenAI、Anthropic、Google、DeepSeek、本地模型等）。每个提供商都有不同的 API、认证方法和参数约定。

问题是：我们应该构建自己的提供商抽象层，还是使用现有的库？

### 考虑的选项

| 选项 | 优点 | 缺点 |
|------|------|------|
| **A. 自建** | 完全控制，无依赖，针对我们的用例优化 | 约 20,000 行代码，持续维护负担，bug 修复，新提供商支持 |
| **B. 使用 LiteLLM** | 经过实战检验，支持 100+ 提供商，统一接口，活跃的社区 | 外部依赖，控制较少，可能存在冗余 |
| **C. 使用 LangChain** | 丰富的生态系统，许多集成 | 重度依赖，固化的模式，不必要的复杂性 |

### 决策
**使用 LiteLLM** 进行提供商抽象，并添加一个薄包装层用于配置和错误处理。

### 理由

1. **代码节省**: 相比自建节省约 20,000 行代码
2. **维护性**: LiteLLM 团队处理新提供商、API 变更、bug 修复
3. **可靠性**: 经过数千个应用程序的生产环境测试
4. **灵活性**: 支持云和本地提供商
5. **简洁性**: 我们的包装层约 100 行代码，而自建需要 20,000 行

### 实现

```python
# nanobot/providers/litellm_provider.py (简化版)
import litellm
from nanobot.providers.registry import find_by_model

class LiteLLMProvider:
    def __init__(self, config):
        self.config = config
        spec = find_by_model(config.model)
        
        # 从注册表设置环境变量
        if spec.env_key:
            os.environ[spec.env_key] = config.api_key
        for env, value in spec.env_extras:
            os.environ[env] = value.format(api_key=config.api_key, api_base=config.api_base)
    
    async def complete(self, messages, **kwargs):
        # LiteLLM 处理所有提供商特定的细节
        response = await litellm.acompletion(
            model=self.config.model,
            messages=messages,
            **kwargs
        )
        return response
```

### 后果

**正面**:
- 降低代码复杂性
- 更快添加新提供商
- 通过更新自动修复 bug
- 访问高级功能（回退、重试）

**负面**:
- 依赖外部项目
- 对提供商特定问题的可见性较低
- LiteLLM 可能发生破坏性变更

### 缓解措施
- 在 requirements 中固定 LiteLLM 版本
- 抽象在我们自己的接口后面，以便将来替换
- 监控 LiteLLM 变更日志

---

## ADR-002: 使用 Pydantic v2 进行配置管理

### 状态
**已接受** - 已实现并投入生产

### 背景
nanobot 有复杂的配置需求：嵌套结构、验证、类型安全、默认值、环境变量支持。问题是应该使用哪个配置框架。

### 考虑的选项

| 选项 | 优点 | 缺点 |
|------|------|------|
| **A. Pydantic v1** | 成熟，知名，良好的生态系统 | 较慢，遗留版本，v2 是未来 |
| **B. Pydantic v2** | 快 5-50 倍，更清晰的 API，Rust 核心 | 与 v1 有破坏性变更，较新 |
| **C. dataclasses + 手动验证** | 标准库，无依赖 | 手动验证代码，无自动文档 |
| **D. attrs** | 清晰的 API，良好的验证 | 较小的生态系统，较少的工具支持 |

### 决策
**使用 Pydantic v2** 进行所有配置模式定义。

### 理由

1. **性能**: 比 v1 快 5-50 倍的验证速度
2. **类型安全**: 完整的 mypy 兼容性
3. **文档**: 自动生成 JSON 模式
4. **生态系统**: 丰富的工具和集成生态系统
5. **面向未来**: v2 是长期发展方向

### 实现

```python
# nanobot/config/schema.py (摘录)
from pydantic import BaseModel, Field, field_validator
from pathlib import Path

class AgentConfig(BaseModel):
    """代理行为配置。"""
    model: str = Field(default="openrouter/anthropic/claude-opus-4-5")
    provider: str = Field(default="")
    workspace: str = Field(default="~/.nanobot/workspace")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4000, gt=0)
    
    @field_validator("workspace")
    @classmethod
    def expand_workspace_path(cls, v: str) -> str:
        return str(Path(v).expanduser())
    
    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if v < 0 or v > 2:
            raise ValueError("temperature 必须在 0 和 2 之间")
        return v

class NanobotConfig(BaseModel):
    """根配置。"""
    agents: AgentsConfig = AgentsConfig()
    channels: ChannelsConfig = ChannelsConfig()
    providers: ProvidersConfig = ProvidersConfig()
    tools: ToolsConfig = ToolsConfig()
```

### 后果

**正面**:
- 自动验证并提供清晰的错误信息
- IDE 自动补全和类型检查
- 自文档化的配置
- 易于序列化/反序列化

**负面**:
- Pydantic v2 特性的学习曲线
- 比原始字典启动稍慢

---

## ADR-003: 使用 Markdown + Shell 编写技能

### 状态
**已接受** - 已实现并投入生产

### 背景
技能是 nanobot 学习使用工具的方式。问题是：技能应该使用什么格式？

### 考虑的选项

| 选项 | 优点 | 缺点 |
|------|------|------|
| **A. Python API** | Python 的完整能力，类型安全，IDE 支持 | 需要编程知识，更难编写，安全风险 |
| **B. YAML/JSON** | 结构化，机器可读 | 冗长，难以编写散文，表达能力有限 |
| **C. Markdown + Shell** | 人类可读，易于编写，LLM 友好，无需代码 | 结构化程度较低，解析复杂性 |
| **D. DSL（领域特定语言）** | 专为用途构建，优化 | 实现成本高，学习曲线 |

### 决策
**使用 Markdown + Shell 命令** 编写技能。

### 理由

1. **可访问性**: 任何人都可以编写 markdown
2. **LLM 原生**: LLM 擅长理解 markdown
3. **人类可读**: 易于审查和维护
4. **无需代码**: 非开发者也能创建技能
5. **可移植**: 不绑定特定编程语言

### 实现

```markdown
---
name: github
description: "与 GitHub 交互"
metadata: {"nanobot":{"requires":{"bins":["gh"]}}}
---

# GitHub 技能

使用 `gh` CLI 进行 GitHub 操作。

## 拉取请求

检查 CI 状态：
```bash
gh pr checks 55 --repo owner/repo
```

## API 查询

获取 PR 详情：
```bash
gh api repos/owner/repo/pulls/55 --jq '.title, .state'
```
```

### 后果

**正面**:
- 降低技能创建的门槛
- 易于版本控制
- 自文档化
- 与现有 CLI 工具配合工作

**负面**:
- 逻辑能力有限（有意为之 - 保持技能简单）
- 解析 frontmatter 增加复杂性
- 无编译时检查

---

## ADR-004: 使用 CSV/JSON 进行记忆存储

### 状态
**已接受** - 已实现并计划演进

### 背景
nanobot 需要持久化存储：对话历史、用户偏好、技能状态、计划任务。问题是：使用什么存储后端？

### 考虑的选项

| 选项 | 优点 | 缺点 |
|------|------|------|
| **A. SQLite** | SQL 查询，ACID，广泛支持 | 模式迁移，复杂性，二进制格式 |
| **B. PostgreSQL** | 生产级，可扩展 | 对个人代理来说过度，设置复杂 |
| **C. CSV/JSON** | 人类可读，可调试，无需设置，透明 | 效率较低，无并发访问，大小限制 |
| **D. 向量数据库** | 语义搜索，嵌入 | 设置复杂，当前需求过度 |

### 决策
**目前使用 CSV/JSON，并带有抽象层以便将来迁移。**

### 理由

1. **简洁性**: 无需设置，无依赖
2. **透明性**: 用户可以直接检查和修改数据
3. **可调试性**: 易于查看存储的内容
4. **备份**: 简单的文件复制
5. **迁移路径**: 抽象层允许将来切换到 SQLite/Postgres

### 实现

```python
# nanobot/agent/memory.py (简化版)
import csv
import json
from pathlib import Path

class MemoryStore:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.conversations_file = workspace / "conversations.csv"
        self.preferences_file = workspace / "preferences.json"
    
    def save_conversation(self, session_id: str, messages: list):
        """保存对话到 CSV。"""
        with open(self.conversations_file, "a", newline="") as f:
            writer = csv.writer(f)
            for msg in messages:
                writer.writerow([
                    session_id,
                    msg["timestamp"],
                    msg["role"],
                    msg["content"]
                ])
    
    def load_preferences(self) -> dict:
        """从 JSON 加载偏好设置。"""
        if self.preferences_file.exists():
            return json.loads(self.preferences_file.read_text())
        return {}
```

### 未来演进

```python
# 计划：抽象接口以便将来替换
class StorageBackend(ABC):
    @abstractmethod
    async def save_message(self, session_id: str, message: dict) -> None: ...
    
    @abstractmethod
    async def get_messages(self, session_id: str, limit: int = 100) -> list: ...

# 当前：FileStorage
# 未来：SQLiteStorage, PostgresStorage, VectorStorage
```

### 后果

**正面**:
- 用户零设置
- 易于调试和检查
- 简单备份
- 无依赖

**负面**:
- 无并发访问（单用户限制）
- 大数据集时性能下降
- 无 ACID 保证

### 缓解措施
- 抽象层以便将来迁移
- 定期压缩/轮换
- 文档大小限制

---

## ADR-005: 使用 MessageBus 进行内部通信

### 状态
**已接受** - 已实现并投入生产

### 背景
频道从外部平台（Telegram、Discord 等）接收消息，需要将它们转发给代理。代理产生需要返回给频道的响应。这些组件应该如何通信？

### 考虑的选项

| 选项 | 优点 | 缺点 |
|------|------|------|
| **A. 直接方法调用** | 简单，无开销 | 紧耦合，难以测试，无异步隔离 |
| **B. MessageBus（内存）** | 松耦合，易于测试，异步友好 | 单进程限制 |
| **C. Redis/RabbitMQ** | 分布式，持久化 | 额外基础设施，复杂性 |
| **D. 事件发射器** | 灵活，解耦 | 难以追踪，潜在内存泄漏 |

### 决策
**使用内存中的 MessageBus，并带有清晰的抽象以便将来使用 Redis。**

### 理由

1. **简洁性**: 单实例部署无需外部依赖
2. **可测试性**: 易于模拟和测试
3. **解耦**: 频道不了解代理，代理不了解频道
4. **灵活性**: 以后可以更换后端为 Redis

### 实现

```python
# nanobot/bus/queue.py
from asyncio import Queue
from typing import Callable

class MessageBus:
    def __init__(self):
        self._inbound_queue: Queue[InboundMessage] = Queue()
        self._outbound_queue: Queue[OutboundMessage] = Queue()
        self._inbound_handlers: list[Callable] = []
        self._outbound_handlers: list[Callable] = []
    
    async def publish_inbound(self, msg: InboundMessage) -> None:
        """频道在消息到达时调用此方法。"""
        await self._inbound_queue.put(msg)
        for handler in self._inbound_handlers:
            await handler(msg)
    
    def subscribe_inbound(self, handler: Callable) -> None:
        """代理订阅以接收消息。"""
        self._inbound_handlers.append(handler)
    
    async def publish_outbound(self, msg: OutboundMessage) -> None:
        """代理调用此方法发送响应。"""
        await self._outbound_queue.put(msg)
        for handler in self._outbound_handlers:
            await handler(msg)
```

### 后果

**正面**:
- 清晰的关注点分离
- 易于添加新频道/代理
- 可用模拟总线测试
- 无外部依赖

**负面**:
- 单进程限制
- 重启时消息丢失
- 无消息持久化

### 未来演进

```python
# nanobot/bus/redis_queue.py (计划中)
import redis.asyncio as redis

class RedisMessageBus(MessageBus):
    """使用 Redis 的分布式消息总线。"""
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.pubsub = self.redis.pubsub()
    
    async def publish_inbound(self, msg: InboundMessage) -> None:
        await self.redis.publish("inbound", msg.to_json())
```

---

## ADR-006: 使用 Typer 作为 CLI 框架

### 状态
**已接受** - 已实现并投入生产

### 背景
nanobot 需要一个 CLI 用于：初始化、代理聊天、网关管理、频道/提供商配置。应该使用哪个 CLI 框架？

### 考虑的选项

| 选项 | 优点 | 缺点 |
|------|------|------|
| **A. argparse (stdlib)** | 无依赖，标准 | 冗长，手动帮助生成 |
| **B. Click** | 成熟，广泛使用，文档良好 | 复杂情况冗长，基于回调 |
| **C. Typer** | 现代，类型提示，自动补全，FastAPI 风格 | 较新，较小的生态系统 |
| **D. Fire** | 零样板 | 控制较少，难以自定义 |

### 决策
**使用 Typer** 进行 CLI 实现。

### 理由

1. **类型提示**: 原生 Python 类型注解驱动 CLI
2. **自动补全**: 自动生成 shell 补全
3. **文档**: 从文档字符串自动生成帮助文本
4. **现代**: 基于 Click 但更 Pythonic
5. **可维护性**: 比 Click 更少的样板代码

### 实现

```python
# nanobot/cli/main.py
import typer
from typing import Optional

app = typer.Typer(help="nanobot - 超轻量级 AI 助手")

@app.command()
def onboard(
    config_path: Optional[str] = typer.Option(
        None, "--config", "-c", help="配置文件路径"
    ),
    workspace: Optional[str] = typer.Option(
        None, "--workspace", "-w", help="工作目录"
    ),
):
    """初始化 nanobot 配置和工作空间。"""
    # 实现...

@app.command()
def agent(
    message: Optional[str] = typer.Option(
        None, "--message", "-m", help="要发送的消息"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="交互模式"
    ),
):
    """启动代理会话。"""
    # 实现...

@app.command()
def gateway(
    port: int = typer.Option(18790, "--port", "-p", help="监听端口"),
    config: Optional[str] = typer.Option(None, "--config", "-c"),
):
    """启动网关服务器。"""
    # 实现...
```

### 后果

**正面**:
- 类型安全的 CLI 参数
- 自动生成帮助
- 支持 shell 补全
- 比 Click 更少的样板代码

**负面**:
- 额外依赖
- 比 Click 小的生态系统
- 某些高级 Click 功能未暴露

---

## ADR-007: 基于文件的配置

### 状态
**已接受** - 已实现并投入生产

### 背景
用户需要配置 nanobot：API 密钥、模型偏好、频道设置。配置应该如何存储？

### 考虑的选项

| 选项 | 优点 | 缺点 |
|------|------|------|
| **A. 环境变量** | 12-factor 应用兼容，容器中易于使用 | 结构有限，难以编辑 |
| **B. 数据库** | 结构化，可查询 | 过度，需要设置 |
| **C. 基于文件 (JSON/YAML)** | 人类可读，可版本控制，易于备份 | 手动编辑，语法错误 |
| **D. 交互式 CLI 向导** | 用户友好，引导 | 难以自动化，版本控制问题 |

### 决策
**使用基于 JSON 文件的配置**，并支持环境变量覆盖。

### 理由

1. **透明性**: 用户可以查看和编辑所有设置
2. **版本控制**: 易于跟踪变更，共享配置
3. **备份**: 简单的文件复制
4. **结构**: JSON 支持嵌套配置
5. **覆盖**: 环境变量用于机密和 Docker

### 实现

```python
# nanobot/config/loader.py
import json
import os
from pathlib import Path

class ConfigLoader:
    DEFAULT_PATH = Path.home() / ".nanobot" / "config.json"
    
    def load(self, path: Optional[Path] = None) -> NanobotConfig:
        config_path = path or self.DEFAULT_PATH
        
        # 从文件加载
        if config_path.exists():
            data = json.loads(config_path.read_text())
        else:
            data = {}
        
        # 使用环境变量覆盖
        data = self._apply_env_overrides(data)
        
        return NanobotConfig(**data)
    
    def _apply_env_overrides(self, data: dict) -> dict:
        """应用环境变量覆盖。"""
        if api_key := os.getenv("NANOBOT_API_KEY"):
            data.setdefault("providers", {}).setdefault("openrouter", {})["apiKey"] = api_key
        return data
```

### 后果

**正面**:
- 易于理解和编辑
- 可版本控制
- 简单备份
- 跨平台工作

**负面**:
- JSON 语法可能容易出错
- 无内联注释（使用单独的 README）
- 机密以明文存储（对敏感数据使用环境变量）

### 最佳实践

```json
{
  "_comment": "API 密钥可以使用环境变量: ${OPENROUTER_API_KEY}",
  "providers": {
    "openrouter": {
      "apiKey": "${OPENROUTER_API_KEY}"
    }
  }
}
```

---

## ADR-008: Async/Await 并发模型

### 状态
**已接受** - 已实现并投入生产

### 背景
nanobot 需要处理：多个并发对话、I/O 密集型操作（API 调用、文件操作）、WebSocket 连接。应该使用哪种并发模型？

### 考虑的选项

| 选项 | 优点 | 缺点 |
|------|------|------|
| **A. 同步 + 线程** | 易于理解，stdlib | GIL 限制，更难推理 |
| **B. Async/Await (asyncio)** | 高效的 I/O，原生 Python，结构化并发 | 学习曲线，误用会导致回调地狱 |
| **C. 多进程** | 真正的并行，绕过 GIL | 高内存开销，IPC 复杂性 |
| **D. Trio/Curio** | 更好的结构化并发 | 较少的生态系统支持，额外依赖 |

### 决策
**在整个项目中使用 asyncio 和 async/await。**

### 理由

1. **I/O 效率**: 非常适合 API 调用、网络操作
2. **结构化**: 相比回调，控制流清晰
3. **生态系统**: 丰富的异步库生态系统
4. **Pythonic**: 原生 Python 特性（3.7+）
5. **面向未来**: 现代 Python 的标准

### 实现

```python
# nanobot/agent/loop.py
import asyncio
from typing import AsyncIterator

class AgentLoop:
    async def run(self, session_id: str) -> AsyncIterator[str]:
        """带流式响应的主代理循环。"""
        while True:
            # 获取用户消息
            message = await self.get_user_message(session_id)
            
            # 构建上下文（异步 I/O）
            context = await self.context_builder.build(session_id, message)
            
            # 流式 LLM 响应
            async for chunk in self.provider.complete_stream(context):
                yield chunk.content
                
                # 检查工具调用
                if chunk.tool_calls:
                    # 并发执行工具
                    results = await asyncio.gather(*[
                        self.execute_tool(call)
                        for call in chunk.tool_calls
                    ])
                    # 用结果继续循环
```

### 后果

**正面**:
- 高并发，低资源使用
- 干净、可读的代码
- 高效的 I/O 处理
- 易于添加异步库

**负面**:
- 新手有学习曲线
- 混合同步/异步可能导致问题
- 调试异步代码更难

### 最佳实践

```python
# ✅ 良好：对阻塞操作使用 asyncio.to_thread
result = await asyncio.to_thread(blocking_function, arg)

# ✅ 良好：并发收集
results = await asyncio.gather(*[task1(), task2(), task3()])

# ❌ 不良：阻塞事件循环
result = blocking_function()  # 永远不要在异步代码中这样做
```

---

## ADR-009: 单体架构

### 状态
**已接受** - 带有计划的演进路径

### 背景
nanobot 应该是单体、微服务还是模块化？这会影响复杂性、部署和扩展。

### 考虑的选项

| 选项 | 优点 | 缺点 |
|------|------|------|
| **A. 微服务** | 独立扩展，技术多样性 | 高复杂性，运营开销 |
| **B. 单体** | 部署简单，易于调试 | 更难扩展，紧耦合 |
| **C. 模块化单体** | 清晰的边界，未来可提取 | 需要纪律来维持 |

### 决策
**从模块化单体开始，需要时提取服务。**

### 理由

1. **简洁性**: 单一可部署单元
2. **开发速度**: 开发期间无网络边界
3. **调试**: 单进程追踪
4. **资源效率**: 无服务间通信开销
5. **未来路径**: 清晰的模块边界支持未来提取

### 实现

```
nanobot/
├── agent/          # 代理逻辑 - 可成为代理服务
├── channels/       # 频道适配器 - 可成为频道服务
├── providers/      # LLM 提供商 - 可成为提供商服务
├── memory/         # 记忆存储 - 可成为记忆服务
└── bus/            # 消息总线 - 可成为消息队列
```

### 演进路径

**第一阶段：单体（当前）**
```
[Gateway] ──▶ [Agent] ──▶ [Memory]
     │
     ▼
[MessageBus (内存)]
```

**第二阶段：分离网关**（如果需要扩展）
```
[Gateway] ──▶ [Redis] ──▶ [Agent Workers]
```

**第三阶段：分离服务**（如果特定瓶颈）
```
[Gateway] ──▶ [Agent Service] ──▶ [Memory Service]
                 │
                 ▼
            [Provider Service]
```

### 后果

**正面**:
- 部署简单（单一二进制文件）
- 本地开发容易
- 低运营开销
- 快速迭代

**负面**:
- 水平扩展受限
- 技术栈统一
- 单一故障域

---

## ADR-010: 提供商注册表模式

### 状态
**已接受** - 已实现并投入生产

### 背景
支持 20+ 个 LLM 提供商需要一致地处理：API 密钥、模型名称前缀、环境变量、自动检测。如何管理这种复杂性？

### 考虑的选项

| 选项 | 优点 | 缺点 |
|------|------|------|
| **A. If-Elif 链** | 少量提供商时简单 | 规模大了难以维护，重复 |
| **B. 类层次结构** | 清晰的 OOP，可扩展 | 样板代码，更难自动检测 |
| **C. 注册表模式** | 单一数据源，声明式，自动检测 | 需要理解模式 |
| **D. 仅配置** | 无需代码更改 | 灵活性有限，无逻辑 |

### 决策
**使用提供商注册表模式和 ProviderSpec 数据类。**

### 理由

1. **单一数据源**: 所有提供商元数据在一个地方
2. **声明式**: 通过添加条目添加提供商，无需逻辑更改
3. **自动检测**: 注册表支持基于密钥/基础的检测
4. **DRY**: 无提供商逻辑重复
5. **类型安全**: 数据类确保定义完整

### 实现

```python
# nanobot/providers/registry.py
from dataclasses import dataclass

@dataclass(frozen=True)
class ProviderSpec:
    name: str                          # 配置字段名
    keywords: tuple[str, ...]        # 模型名称关键词
    env_key: str                       # API 密钥环境变量
    display_name: str = ""
    litellm_prefix: str = ""          # 模型前缀
    skip_prefixes: tuple[str, ...] = ()
    is_gateway: bool = False
    detect_by_key_prefix: str = ""    # 自动检测模式

# 注册表
PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        name="openrouter",
        keywords=("openrouter",),
        env_key="OPENROUTER_API_KEY",
        display_name="OpenRouter",
        litellm_prefix="openrouter",
        is_gateway=True,
        detect_by_key_prefix="sk-or-",
    ),
    ProviderSpec(
        name="anthropic",
        keywords=("anthropic", "claude"),
        env_key="ANTHROPIC_API_KEY",
        display_name="Anthropic",
        supports_prompt_caching=True,
    ),
    # ... 更多提供商
)

# 查找函数
def find_by_model(model: str) -> ProviderSpec | None:
    """通过模型名称关键词查找提供商。"""
    model_lower = model.lower()
    for spec in PROVIDERS:
        if any(kw in model_lower for kw in spec.keywords):
            return spec
    return None

def find_gateway(api_key: str | None = None, api_base: str | None = None) -> ProviderSpec | None:
    """自动检测网关提供商。"""
    for spec in PROVIDERS:
        if spec.detect_by_key_prefix and api_key and api_key.startswith(spec.detect_by_key_prefix):
            return spec
        if spec.detect_by_base_keyword and api_base and spec.detect_by_base_keyword in api_base:
            return spec
    return None
```

### 后果

**正面**:
- 添加提供商：2 步，约 10 行代码
- 无 if-elif 链
- 自动环境设置
- 易于测试

**负面**:
- 注册表文件变大（缓解：20 个提供商约 400 行）
- 所有提供商在导入时加载（成本可忽略）

### 添加新提供商

```python
# 步骤 1：添加到注册表
ProviderSpec(
    name="newprovider",
    keywords=("newprovider", "np"),
    env_key="NEWPROVIDER_API_KEY",
    display_name="New Provider",
    litellm_prefix="newprovider",
)

# 步骤 2：添加到配置模式
class ProvidersConfig(BaseModel):
    # ... 现有 ...
    newprovider: ProviderConfig = ProviderConfig()

# 完成！环境变量、前缀、状态显示全部自动工作。
```

---

## 决策总结矩阵

| 决策 | 状态 | 主要收益 | 权衡 |
|------|------|----------|------|
| LiteLLM | ✅ 已接受 | -20K 行代码 | 外部依赖 |
| Pydantic v2 | ✅ 已接受 | 类型安全，验证 | 学习曲线 |
| Markdown 技能 | ✅ 已接受 | 可访问，LLM 原生 | 逻辑有限 |
| CSV/JSON 存储 | ✅ 已接受 | 透明，无设置 | 性能限制 |
| MessageBus | ✅ 已接受 | 松耦合 | 单进程 |
| Typer CLI | ✅ 已接受 | 类型安全，现代 | 较新的生态系统 |
| 文件配置 | ✅ 已接受 | 可版本控制 | JSON 语法 |
| Async/Await | ✅ 已接受 | 高效的 I/O | 学习曲线 |
| 模块化单体 | ✅ 已接受 | 部署简单 | 扩展限制 |
| 提供商注册表 | ✅ 已接受 | 单一数据源 | 注册表大小 |

---

## 结论

nanobot 的技术决策反映了其核心哲学：**超轻量级但生产就绪**。每个决策都优化了：

1. **简洁性**: 最小化代码，最大化清晰度
2. **可维护性**: 易于理解和修改
3. **可扩展性**: 清晰的扩展点，无需核心更改
4. **性能**: 在重要的地方高效（异步 I/O、LiteLLM）
5. **面向未来**: 抽象层支持演进

结果：约 4,000 行核心代码，在功能上可媲美 200,000 行的替代方案，同时保持可 hack 和可理解。

**核心洞察**: 好的架构在于知道**不**构建什么。nanobot 的决策无情地消除不必要的复杂性，同时保留能力。

---

## 参考

- [LiteLLM 文档](https://docs.litellm.ai/)
- [Pydantic v2 文档](https://docs.pydantic.dev/)
- [Typer 文档](https://typer.tiangolo.com/)
- [Python AsyncIO 文档](https://docs.python.org/3/library/asyncio.html)
- [架构决策记录](https://adr.github.io/)
