# 05 - 扩展路线图与未来方向

## 文档概述

本文档梳理了 nanobot 的扩展点、未来发展方向和贡献指南。它旨在为希望扩展 nanobot 功能或为项目做出贡献的开发者提供指导。

**目标读者**：贡献者、扩展开发者和规划定制的架构师。

---

## 目录

1. [当前扩展点](#1-当前扩展点)
2. [扩展模式与示例](#2-扩展模式与示例)
3. [未来路线图](#3-未来路线图)
4. [架构演进](#4-架构演进)
5. [贡献者指南](#5-贡献者指南)

---

## 1. 当前扩展点

nanobot 设计有清晰、明确定义的扩展点，允许开发者在不修改核心代码的情况下自定义功能。

### 1.1 提供商扩展（LLM 后端）

**位置**：`nanobot/providers/`

**当前状态**：通过 LiteLLM 集成支持 20+ 个提供商

**扩展方法**：两步添加提供商

```python
# 步骤 1：添加 ProviderSpec 到 nanobot/providers/registry.py
ProviderSpec(
    name="myprovider",                   # 配置字段名
    keywords=("myprovider", "mymodel"),  # 模型名称关键词
    env_key="MYPROVIDER_API_KEY",        # LiteLLM 的环境变量
    display_name="My Provider",          # 状态显示名称
    litellm_prefix="myprovider",         # 自动添加模型名称前缀
    skip_prefixes=("myprovider/",),      # 不重复添加前缀
)

# 步骤 2：添加字段到 nanobot/config/schema.py
class ProvidersConfig(BaseModel):
    # ... 现有提供商 ...
    myprovider: ProviderConfig = ProviderConfig()
```

**ProviderSpec 选项**：

| 字段 | 类型 | 描述 |
|------|------|-------------|
| `name` | `str` | 配置字段名（小写，无空格） |
| `keywords` | `tuple[str, ...]` | 模型名称关键词，用于自动匹配 |
| `env_key` | `str` | API 密钥的环境变量 |
| `display_name` | `str` | 状态显示的人类可读名称 |
| `litellm_prefix` | `str` | LiteLLM 路由前缀 |
| `skip_prefixes` | `tuple[str, ...]` | 如果模型已有此前缀则不添加 |
| `env_extras` | `tuple[tuple[str, str], ...]` | 额外设置的环境变量 |
| `is_gateway` | `bool` | 是否可以路由任何模型（OpenRouter 风格） |
| `is_local` | `bool` | 本地部署（vLLM、Ollama） |
| `detect_by_key_prefix` | `str` | 通过 API 密钥前缀自动检测 |
| `detect_by_base_keyword` | `str` | 通过 API 基础 URL 自动检测 |
| `default_api_base` | `str` | 未指定时的默认基础 URL |
| `strip_model_prefix` | `bool` | 重新添加前缀前去除现有前缀 |
| `model_overrides` | `tuple[tuple[str, dict], ...]` | 每个模型的参数覆盖 |
| `is_oauth` | `bool` | 使用 OAuth 流程而非 API 密钥 |
| `is_direct` | `bool` | 完全绕过 LiteLLM |
| `supports_prompt_caching` | `bool` | 支持 cache_control 块 |

**此设计为何有效**：
- 无需维护 if-elif 链
- 单一真实数据源
- 自动设置环境变量
- 统一处理模型前缀
- 状态显示自动更新

### 1.2 通道扩展（聊天平台）

**位置**：`nanobot/channels/`

**当前状态**：10 个通道（Telegram、Discord、WhatsApp、飞书、钉钉、Slack、Email、QQ、Matrix、Mochat）

**扩展方法**：实现 BaseChannel 接口

```python
# nanobot/channels/myplatform.py
from nanobot.channels.base import BaseChannel
from nanobot.bus.events import InboundMessage, OutboundMessage

class MyPlatformChannel(BaseChannel):
    name = "myplatform"
    
    def __init__(self, config, bus):
        super().__init__(config, bus)
        self.client = None
    
    async def start(self) -> None:
        """开始监听消息。"""
        # 1. 连接平台
        self.client = MyPlatformClient(self.config.token)
        
        # 2. 设置消息处理器
        @self.client.on_message
        async def handle(msg):
            await self._handle_message(
                sender_id=msg.sender_id,
                chat_id=msg.chat_id,
                content=msg.text,
                media=msg.attachments,
                metadata={"platform_specific": msg.raw_data}
            )
        
        # 3. 开始监听
        await self.client.connect()
        self._running = True
    
    async def stop(self) -> None:
        """清理资源。"""
        if self.client:
            await self.client.disconnect()
        self._running = False
    
    async def send(self, msg: OutboundMessage) -> None:
        """向平台发送消息。"""
        await self.client.send_message(
            chat_id=msg.chat_id,
            text=msg.content,
            attachments=msg.media
        )
```

**BaseChannel 接口**：

```python
class BaseChannel(ABC):
    name: str                    # 通道标识符
    
    # 必需实现
    @abstractmethod
    async def start(self) -> None: ...      # 开始监听
    @abstractmethod
    async def stop(self) -> None: ...       # 清理
    @abstractmethod
    async def send(self, msg: OutboundMessage) -> None: ...  # 发送消息
    
    # 内置辅助方法
    def is_allowed(self, sender_id: str) -> bool: ...  # ACL 检查
    async def _handle_message(self, ...) -> None: ...  # 发布到总线
```

**配置模式添加**：

```python
# nanobot/config/schema.py
class MyPlatformChannelConfig(BaseChannelConfig):
    """MyPlatform 通道的配置。"""
    token: str = Field(default="", description="机器人令牌")
    api_base: str = Field(default="https://api.myplatform.com", description="API 基础 URL")
    webhook_secret: str = Field(default="", description="Webhook 验证密钥")
    group_policy: str = Field(default="mention", description="群组响应策略")

class ChannelsConfig(BaseModel):
    # ... 现有通道 ...
    myplatform: MyPlatformChannelConfig = MyPlatformChannelConfig()
```

**注册**：

```python
# nanobot/channels/manager.py
from nanobot.channels.myplatform import MyPlatformChannel

CHANNEL_CLASSES = {
    # ... 现有通道 ...
    "myplatform": MyPlatformChannel,
}
```

### 1.3 技能扩展（代理能力）

**位置**：`nanobot/skills/`（内置）或 `~/.nanobot/workspace/skills/`（用户）

**扩展方法**：Markdown + 前置元数据

```markdown
---
name: myskill
description: "描述此技能实现的功能"
metadata: {"nanobot":{"emoji":"🎯","requires":{"bins":["mycli"],"env":["MY_API_KEY"]},"always":false}}
---

# 我的技能

教代理如何使用 `mycli` 执行特定任务。

## 常见操作

执行 X：
```bash
mycli do-x --param value
```

执行 Y：
```bash
mycli do-y --format json
```

## 最佳实践

- 始终使用 `--format json` 获取结构化输出
- 通过检查退出码处理错误
```

**前置元数据模式**：

```json
{
  "nanobot": {
    "emoji": "🎯",                    // 显示图标
    "requires": {
      "bins": ["mycli"],              // 必需的 CLI 工具
      "env": ["MY_API_KEY"]           // 必需的环境变量
    },
    "always": false,                   // 自动加载？
    "install": [                       // 安装提示
      {
        "id": "brew",
        "kind": "brew",
        "formula": "mycli",
        "bins": ["mycli"],
        "label": "安装 mycli (brew)"
      }
    ]
  }
}
```

**技能加载优先级**：

1. 工作区技能（`~/.nanobot/workspace/skills/*/`）
2. 内置技能（`nanobot/skills/*/`）

工作区中同名技能会覆盖内置技能。

### 1.4 工具扩展（代理操作）

**位置**：`nanobot/agent/tools/`

**当前工具**：shell、文件系统（读/写/编辑/列表）、web、spawn、mcp、cron

**扩展方法**：添加工具类

```python
# nanobot/agent/tools/my_tool.py
from nanobot.agent.tools.base import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "执行有用的操作"
    
    async def execute(self, params: dict) -> dict:
        """执行工具。"""
        result = await self._do_something(params["input"])
        return {
            "success": True,
            "output": result,
            "metadata": {"tool": self.name}
        }
    
    def get_schema(self) -> dict:
        """返回工具参数的 JSON 模式。"""
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "要处理的输入"
                }
            },
            "required": ["input"]
        }
```

**注册**：

```python
# nanobot/agent/tools/__init__.py
from nanobot.agent.tools.my_tool import MyTool

TOOL_CLASSES = [
    # ... 现有工具 ...
    MyTool,
]
```

**MCP 集成**（外部工具）：

```json
{
  "tools": {
    "mcpServers": {
      "my-server": {
        "command": "npx",
        "args": ["-y", "@myorg/mcp-server"],
        "env": {
          "API_KEY": "xxx"
        }
      }
    }
  }
}
```

### 1.5 配置扩展

**位置**：`nanobot/config/schema.py`

**扩展方法**：Pydantic 模型

```python
from pydantic import BaseModel, Field

class MyExtensionConfig(BaseModel):
    """我的扩展的配置。"""
    enabled: bool = Field(default=False)
    api_key: str = Field(default="", description="API 密钥")
    timeout: int = Field(default=30, description="超时时间（秒）")
    
    class Config:
        # 允许额外字段以确保向前兼容
        extra = "allow"

# 添加到主配置
class NanobotConfig(BaseModel):
    # ... 现有部分 ...
    my_extension: MyExtensionConfig = MyExtensionConfig()
```

---

## 2. 扩展模式与示例

### 2.1 提供商扩展示例：添加 Cohere

```python
# 步骤 1：添加到 nanobot/providers/registry.py
ProviderSpec(
    name="cohere",
    keywords=("cohere", "command"),
    env_key="COHERE_API_KEY",
    display_name="Cohere",
    litellm_prefix="cohere",
    skip_prefixes=("cohere/",),
)

# 步骤 2：添加到 nanobot/config/schema.py
class ProvidersConfig(BaseModel):
    # ... 现有提供商 ...
    cohere: ProviderConfig = ProviderConfig()
```

**完成！** 无需其他更改。提供商注册表自动处理：
- 环境变量设置
- 模型名称前缀
- 配置验证
- 状态显示

### 2.2 通道扩展示例：添加 Microsoft Teams

```python
# nanobot/channels/teams.py
import asyncio
from nanobot.channels.base import BaseChannel
from nanobot.bus.events import OutboundMessage

class TeamsChannel(BaseChannel):
    name = "teams"
    
    def __init__(self, config, bus):
        super().__init__(config, bus)
        self.bot_framework = None
    
    async def start(self):
        from botbuilder.core import BotFrameworkAdapter
        
        self.bot_framework = BotFrameworkAdapter(
            app_id=self.config.app_id,
            app_password=self.config.app_password
        )
        
        # 设置 webhook 或 websocket 监听器
        # 平台特定的连接逻辑
        
        self._running = True
    
    async def stop(self):
        self._running = False
    
    async def send(self, msg: OutboundMessage):
        # 通过 Teams API 发送
        pass
```

```python
# nanobot/config/schema.py
class TeamsChannelConfig(BaseChannelConfig):
    app_id: str = Field(default="")
    app_password: str = Field(default="")
    tenant_id: str = Field(default="")

class ChannelsConfig(BaseModel):
    # ... 现有通道 ...
    teams: TeamsChannelConfig = TeamsChannelConfig()
```

```python
# nanobot/channels/manager.py
from nanobot.channels.teams import TeamsChannel

CHANNEL_CLASSES = {
    # ... 现有 ...
    "teams": TeamsChannel,
}
```

### 2.3 技能扩展示例：Jira 集成

```markdown
---
name: jira
description: "使用 `jira` CLI 与 Jira 问题交互"
metadata: {"nanobot":{"emoji":"📋","requires":{"bins":["jira"]},"install":[{"id":"brew","kind":"brew","formula":"go-jira","bins":["jira"]}]}}
---

# Jira 技能

使用 `jira` CLI 管理 Jira 问题。

## 查看问题

列出的待办问题：
```bash
jira list --assignee $(jira me) --status "In Progress"
```

查看特定问题：
```bash
jira view PROJ-123
```

## 创建问题

创建新问题：
```bash
jira create --project PROJ --issuetype Bug --summary "Bug 摘要" --description "描述"
```

## 状态转换

列出可用转换：
```bash
jira transitions PROJ-123
```

转换到 "In Progress"：
```bash
jira transition "In Progress" PROJ-123
```
```

保存为 `~/.nanobot/workspace/skills/jira/SKILL.md` 即可立即可用。

### 2.4 工具扩展示例：数据库查询工具

```python
# nanobot/agent/tools/db_tool.py
import sqlite3
from pathlib import Path
from nanobot.agent.tools.base import BaseTool

class DatabaseTool(BaseTool):
    name = "query_database"
    description = "在 SQLite 数据库上执行只读 SQL 查询"
    
    def __init__(self, config):
        super().__init__(config)
        self.workspace = Path(config.workspace)
    
    async def execute(self, params: dict) -> dict:
        db_path = params["database"]
        query = params["query"]
        
        # 安全：限制在工作区内
        full_path = self.workspace / db_path
        if not str(full_path.resolve()).startswith(str(self.workspace.resolve())):
            return {"success": False, "error": "访问被拒绝：路径在工作区之外"}
        
        try:
            conn = sqlite3.connect(str(full_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            conn.close()
            
            return {
                "success": True,
                "output": {
                    "columns": columns,
                    "rows": [dict(row) for row in rows]
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "database": {
                    "type": "string",
                    "description": "SQLite 数据库路径（相对于工作区）"
                },
                "query": {
                    "type": "string",
                    "description": "要执行的 SQL SELECT 查询"
                }
            },
            "required": ["database", "query"]
        }
```

---

## 3. 未来路线图

### 3.1 近期（未来 3 个月）

| 功能 | 优先级 | 描述 |
|------|--------|-------------|
| **多模态支持** | 高 | 图像理解、语音输入/输出、视频处理 |
| **增强记忆** | 高 | 带嵌入的长期记忆、语义搜索 |
| **更好的推理** | 高 | 多步规划、反思、思维链 |
| **日历集成** | 中 | Google 日历、Outlook、CalDAV 支持 |
| **更多提供商** | 中 | Ollama 原生、Bedrock、Cohere |
| **Web 仪表板** | 中 | 用于配置和监控的 Web UI |

### 3.2 中期（3-6 个月）

| 功能 | 优先级 | 描述 |
|------|--------|-------------|
| **代理集群** | 高 | 多代理协调、任务分发 |
| **RAG 管道** | 高 | 文档摄取、向量存储集成 |
| **自我改进** | 中 | 从反馈中学习、自动技能生成 |
| **插件系统** | 中 | 热重载插件、插件市场 |
| **更多通道** | 中 | Line、微信公众号、通用 WebSocket |
| **工作流引擎** | 中 | 可视化工作流设计器、自动化规则 |

### 3.3 长期（6-12 个月）

| 功能 | 优先级 | 描述 |
|------|--------|-------------|
| **联邦学习** | 中 | 分布式模型改进 |
| **A2A 协议** | 中 | 代理间通信标准 |
| **自定义模型托管** | 低 | 内置微调和 serving |
| **移动应用** | 低 | 原生 iOS/Android 配套应用 |
| **企业功能** | 低 | SSO、审计日志、管理面板 |

### 3.4 详细功能规格

#### 多模态支持

**视觉**：
```python
# 代理接收图像
{
  "role": "user",
  "content": [
    {"type": "text", "text": "这张图片里是什么？"},
    {"type": "image_url", "image_url": {"url": "https://example.com/img.jpg"}}
  ]
}
```

**语音**：
- 语音转文本：Whisper 集成（Groq 已提供）
- 文本转语音：ElevenLabs、Azure TTS
- Telegram/WhatsApp 语音消息

**视频**：
- 帧提取和分析
- 视频摘要

#### 长期记忆

**架构**：
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   对话记录       │────▶│    嵌入         │────▶│   向量存储       │
│   (Session)     │     │  (text-embed)   │     │ (Chroma/Qdrant) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │                          │
                              ▼                          ▼
                       ┌─────────────────┐     ┌─────────────────┐
                       │    语义         │◀────│    相似性       │
                       │    搜索         │     │    搜索         │
                       └─────────────────┘     └─────────────────┘
```

**实现**：
- 向量数据库集成（Chroma、Qdrant、Pinecone）
- 自动对话摘要
- 实体提取和知识图谱
- 基于当前对话的上下文检索

#### 更好的推理

**组件**：
1. **规划**：将复杂任务分解为子任务
2. **反思**：自我批评和改进
3. **工具选择**：基于上下文智能选择工具
4. **错误恢复**：使用替代方法自动重试

**示例**：
```
用户："为我的作品集建一个网站"

代理计划：
1. [研究] 询问需求的澄清问题
2. [设计] 创建 HTML 结构和 CSS 样式
3. [实现] 使用 shell 和文件工具生成代码
4. [部署] 使用 shell 启动本地服务器
5. [验证] 测试网站并修复问题
6. [交付] 向用户发送链接和代码
```

---

## 4. 架构演进

### 4.1 当前限制

1. **单进程架构**
   - Gateway 和代理共享进程
   - 无水平扩展
   - 隔离性有限

2. **基于文件的存储**
   - 记忆使用 CSV/JSON
   - 无并发访问
   - 大小限制

3. **同步上下文构建**
   - 构建提示时阻塞 I/O
     - 无流式上下文

4. **有限的工具发现**
   - 静态工具列表
   - 无动态工具加载

### 4.2 提议的演进

#### 阶段 1：模块化架构

```
┌─────────────────────────────────────────────────────────────┐
│                         Gateway                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Telegram   │  │   Discord   │  │      WhatsApp       │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└────────────────────┬────────────────────────────────────────┘
                     │ MessageBus (Redis/RabbitMQ)
┌────────────────────┴────────────────────────────────────────┐
│                       Agent Workers                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Worker 1   │  │  Worker 2   │  │  Worker N           │ │
│  │  (Session)  │  │  (Session)  │  │  (Session)          │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**好处**：
- 水平扩展
- 会话隔离
- 独立部署

#### 阶段 2：服务网格

```
┌─────────────────────────────────────────────────────────────┐
│                        API Gateway                          │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
    ┌──────────┴──────────┐      ┌───────────┴──────────┐
    │   Channel Service   │      │   Agent Service      │
    │  (Stateless)        │      │  (Stateful)          │
    └─────────────────────┘      └──────────────────────┘
               │                              │
    ┌──────────┴──────────┐      ┌───────────┴──────────┐
    │   Memory Service    │      │   Tool Service       │
    │  (Vector DB)        │      │  (MCP + Built-in)    │
    └─────────────────────┘      └──────────────────────┘
```

**好处**：
- 每个服务独立扩展
- 每个服务技术多样化
- 更好的故障隔离

#### 阶段 3：分布式智能

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator                             │
│              (任务分发与协调)                                │
└───────┬─────────────────┬─────────────────┬─────────────────┘
        │                 │                 │
   ┌────┴────┐      ┌────┴────┐      ┌────┴────┐
   │ Agent A │      │ Agent B │      │ Agent C │
   │ (研究)  │      │ (代码)  │      │ (设计)  │
   └────┬────┘      └────┬────┘      └────┬────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
                   ┌──────┴──────┐
                   │    共享     │
                   │    记忆     │
                   └─────────────┘
```

**好处**：
- 专业代理
- 并行任务执行
- 集体智能

### 4.3 迁移路径

**当前 → 阶段 1**：
1. 提取消息总线为独立服务
2. 添加 Redis/RabbitMQ 选项
3. 容器化代理工作器
4. 添加负载均衡器

**阶段 1 → 阶段 2**：
1. 提取记忆到向量 DB 服务
2. 提取工具到 MCP 优先架构
3. 添加服务发现
4. 实现健康检查

**阶段 2 → 阶段 3**：
1. 设计代理通信协议
2. 实现协调器
3. 添加专业代理类型
4. 构建共享记忆层

---

## 5. 贡献者指南

### 5.1 入门

**先决条件**：
- Python 3.11+
- Git
- 虚拟环境工具（venv、conda 或 uv）

**设置**：
```bash
# 克隆仓库
git clone https://github.com/HKUDS/nanobot.git
cd nanobot

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate    # Windows

# 以开发模式安装
pip install -e ".[dev]"

# 运行测试
pytest

# 启动开发服务器
nanobot onboard
nanobot gateway
```

### 5.2 开发工作流

**分支命名**：
- `feat/description` - 新功能
- `fix/description` - Bug 修复
- `docs/description` - 文档
- `refactor/description` - 代码重构

**提交信息**：
```
feat: 添加 Discord 通道支持

- 实现 Discord WebSocket 客户端
- 添加消息线程支持
- 更新文档

Fixes #123
```

**Pull Request 检查清单**：
- [ ] 测试通过
- [ ] 新代码遵循现有模式
- [ ] 文档已更新
- [ ] CHANGELOG.md 已更新
- [ ] 无类型错误

### 5.3 代码标准

**Python 风格**：
- 遵循 PEP 8
- 使用类型提示
- 公共 API 使用文档字符串
- 最大行长度：100 字符

**项目约定**：
```python
# 异步函数
async def process_message(self, msg: InboundMessage) -> None:
    """处理传入消息。
    
    Args:
        msg: 要处理的传入消息。
    """
    ...

# 错误处理
try:
    result = await self.client.send(msg)
except Exception as e:
    logger.error(f"发送消息失败：{e}")
    raise ChannelError(f"发送失败：{e}") from e

# 日志
from loguru import logger

logger.info("启动通道：{}", self.name)
logger.debug("收到消息：{}", msg.content)
logger.warning("接近速率限制")
```

### 5.4 测试

**单元测试**：
```python
# tests/channels/test_telegram.py
import pytest
from nanobot.channels.telegram import TelegramChannel

@pytest.fixture
def telegram_channel():
    config = MockConfig(token="test-token", allow_from=["*"])
    bus = MockMessageBus()
    return TelegramChannel(config, bus)

@pytest.mark.asyncio
async def test_send_message(telegram_channel):
    with aioresponses() as mocked:
        mocked.post(
            "https://api.telegram.org/bot test-token/sendMessage",
            payload={"ok": True}
        )
        
        msg = OutboundMessage(
            channel="telegram",
            chat_id="12345",
            content="Hello"
        )
        await telegram_channel.send(msg)
```

**集成测试**：
```bash
# 运行集成测试
pytest tests/integration/ -v

# 运行特定测试
pytest tests/integration/test_telegram.py::test_webhook -v
```

### 5.5 文档

**文档字符串格式**：
```python
def calculate_similarity(text1: str, text2: str, method: str = "cosine") -> float:
    """计算两个文本之间的语义相似度。
    
    使用句子嵌入计算相似度分数。
    
    Args:
        text1: 第一个要比较的文本。
        text2: 第二个要比较的文本。
        method: 相似度方法。选项："cosine"、"euclidean"、"dot"。
               默认为 "cosine"。
    
    Returns:
        0 到 1 之间的相似度分数。
    
    Raises:
        ValueError: 如果方法不受支持。
        EmbeddingError: 如果嵌入计算失败。
    
    Example:
        >>> score = calculate_similarity("hello world", "hi world")
        >>> print(score)
        0.85
    """
    ...
```

### 5.6 常见贡献类型

**添加提供商**：
1. 添加 `ProviderSpec` 到 `nanobot/providers/registry.py`
2. 添加配置字段到 `nanobot/config/schema.py`
3. 使用真实 API 密钥测试
4. 更新 README.md 提供商表格

**添加通道**：
1. 在 `nanobot/channels/` 中实现 `BaseChannel`
2. 添加配置类到 `nanobot/config/schema.py`
3. 在 `nanobot/channels/manager.py` 中注册
4. 添加文档到 README.md
5. 编写测试

**添加技能**：
1. 在 `nanobot/skills/{name}/` 中创建 `SKILL.md`
2. 使用实际 CLI 工具测试技能
3. 更新 `nanobot/skills/README.md`

**添加工具**：
1. 在 `nanobot/agent/tools/` 中实现 `BaseTool`
2. 添加到 `nanobot/agent/tools/__init__.py`
3. 如需要，在代理提示中记录
4. 编写测试

### 5.7 社区资源

- **GitHub Discussions**：功能请求、问答
- **Discord**：与社区实时聊天
- **飞书/Lark**：中文社区讨论
- **Issues**：Bug 报告、功能请求

### 5.8 认可

贡献者在以下位置被认可：
- README.md 贡献者部分
- 发布说明
- 文档中的特别感谢

所有贡献，无论大小，都受到重视和赞赏！

---

## 总结

nanobot 的扩展架构设计注重简洁和清晰：

1. **提供商**：通过注册表模式两步添加
2. **通道**：实现 BaseChannel 接口
3. **技能**：Markdown + 前置元数据，无需代码
4. **工具**：实现 BaseTool 接口
5. **配置**：Pydantic 模型，自动验证

路线图侧重于：
- **多模态**能力（视觉、语音）
- **增强记忆**（向量 DB、RAG）
- **更好推理**（规划、反思）
- **分布式架构**（水平扩展）
- **代理集群**（多代理协调）

凭借约 4,000 行核心代码，nanobot 证明了强大的 AI 代理不需要庞大的代码库。扩展点设计秉承这一理念：简单、明确、可 hack。

**行动号召**：从路线图中选择一个项目，开启 issue 讨论你的方法，并提交 PR！
