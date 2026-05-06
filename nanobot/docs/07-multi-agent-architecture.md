# nanobot 多 Agent 架构设计文档

> **文档版本**: v1.0  
> **状态**: 设计方案  
> **目标**: 实现单个 Gateway 多 Agent 实例支持

---

## 1. 当前架构 vs 目标架构

### 1.1 架构对比

```
┌─────────────────────────────────────────────────────────────────┐
│              当前 nanobot 架构 (单 Agent)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                  nanobot Gateway                         │  │
│   │                    (Python asyncio)                      │  │
│   │                                                          │  │
│   │   ┌─────────────────────────────────────────────────┐   │  │
│   │   │              AgentLoop (单例)                    │   │  │
│   │   │  • workspace: ~/.nanobot/workspace              │   │  │
│   │   │  • session_manager: SessionManager              │   │  │
│   │   │  • memory: CSV/JSON 存储                        │   │  │
│   │   │  • tools: ToolRegistry                          │   │  │
│   │   │  • provider: LiteLLMProvider                    │   │  │
│   │   └────────────────────┬────────────────────────────┘   │  │
│   │                        │                                 │  │
│   │   ┌────────────────────▼────────────────────────────┐   │  │
│   │   │          ChannelManager (单配置)                 │   │  │
│   │   │  • telegram: TelegramConfig (单token)           │   │  │
│   │   │  • discord: DiscordConfig                       │   │  │
│   │   │  • ...                                          │   │  │
│   │   └─────────────────────────────────────────────────┘   │  │
│   │                                                          │  │
│   └─────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │           MessageBus (全局消息总线)                      │  │
│   └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│   限制:                                                         │
│   ❌ 1个 Gateway = 1个 Agent                                   │
│   ❌ 无法支持多个独立人格/配置的 Agent                          │
│   ❌ 多 Telegram Bot 需要多进程                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│           目标架构 (多 Agent - OpenClaw风格)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                  nanobot Gateway                         │  │
│   │                    (Python asyncio)                      │  │
│   │                                                          │  │
│   │   ┌──────────────┬──────────────┬──────────────┐       │  │
│   │   │   Agent A    │   Agent B    │   Agent C    │       │  │
│   │   │  (Coder)     │  (Research)  │  (Chat)      │       │  │
│   │   │              │              │              │       │  │
│   │   │ workspaceA/  │ workspaceB/  │ workspaceC/  │       │  │
│   │   │ sessionsA/   │ sessionsB/   │ sessionsC/   │       │  │
│   │   │ memoryA/     │ memoryB/     │ memoryC/     │       │  │
│   │   │ AGENTS.md    │ AGENTS.md    │ AGENTS.md    │       │  │
│   │   └──────┬───────┴──────┬───────┴──────┬───────┘       │  │
│   │          │              │              │                │  │
│   │          └──────────────┼──────────────┘                │  │
│   │                         │                               │  │
│   │   ┌─────────────────────▼───────────────────────────┐   │  │
│   │   │              AgentRouter (新增)                  │   │  │
│   │   │  • 消息路由规则解析                               │   │  │
│   │   │  • channel + chat_id → agent_id 映射             │   │  │
│   │   │  • 支持通配符和优先级匹配                         │   │  │
│   │   └─────────────────────┬───────────────────────────┘   │  │
│   │                         │                               │  │
│   │   ┌─────────────────────▼───────────────────────────┐   │  │
│   │   │   ChannelManager (多账号支持)                    │   │  │
│   │   │  • telegram: {bot1, bot2, bot3}                 │   │  │
│   │   │  • discord: {account1, account2}                │   │  │
│   │   │  • 每个bot独立连接和身份                         │   │  │
│   │   └─────────────────────────────────────────────────┘   │  │
│   │                                                          │  │
│   └─────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │           MessageBus (增强 - 带agent_id路由)             │  │
│   └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│   能力:                                                         │
│   ✅ 1个 Gateway = N个独立 Agent                               │
│   ✅ 每个 Agent 独立 workspace/memory/config                   │
│   ✅ 多个 Telegram Bot 单进程运行                              │
│   ✅ 灵活的绑定规则 (bindings)                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 核心改动模块分析

### 2.1 配置层 (config/schema.py)

**当前设计:**
```python
class Config(BaseSettings):
    agents: AgentsConfig          # 单 Agent 配置
    channels: ChannelsConfig      # 单渠道配置（单token）
    providers: ProvidersConfig    # 全局Provider
```

**目标设计:**
```python
class AgentInstanceConfig(Base):
    """单个Agent实例的配置"""
    id: str                       # 唯一标识: "coder", "researcher"
    enabled: bool = True
    workspace: str                # 独立workspace路径
    model: str | None = None      # 可覆盖默认model
    temperature: float | None = None
    # 其他Agent级别配置...

class ChannelAccountConfig(Base):
    """渠道账号配置"""
    id: str                       # 账号标识
    enabled: bool = True
    # 各平台特定配置...

class BindingRule(Base):
    """路由绑定规则"""
    agent_id: str                 # 目标Agent
    channel: str                  # 渠道类型: telegram/discord
    account_id: str | None = None # 特定账号（可选）
    chat_id: str | None = None    # 特定聊天（可选）
    priority: int = 0             # 匹配优先级

class Config(BaseSettings):
    agents: AgentsConfig                    # 默认配置
    agents_list: list[AgentInstanceConfig]  # 新增: Agent实例列表
    channels: ChannelsConfig                # 默认渠道配置
    channel_accounts: dict[str, list[ChannelAccountConfig]]  # 新增: 多账号
    bindings: list[BindingRule]             # 新增: 路由规则
```

**配置示例:**
```json
{
  "agents": {
    "defaults": {
      "workspace": "~/.nanobot/workspace",
      "model": "anthropic/claude-sonnet-4-6"
    }
  },
  "agentsList": [
    {
      "id": "coder",
      "workspace": "~/.nanobot-agents/coder",
      "model": "anthropic/claude-opus-4-5",
      "temperature": 0.1
    },
    {
      "id": "researcher",
      "workspace": "~/.nanobot-agents/research",
      "model": "openrouter/google/gemini-2.5-pro"
    },
    {
      "id": "assistant",
      "workspace": "~/.nanobot-agents/chat",
      "temperature": 0.7
    }
  ],
  "channelAccounts": {
    "telegram": [
      {"id": "bot_coder", "enabled": true, "token": "TOKEN_A"},
      {"id": "bot_research", "enabled": true, "token": "TOKEN_B"},
      {"id": "bot_chat", "enabled": true, "token": "TOKEN_C"}
    ]
  },
  "bindings": [
    {"agentId": "coder", "channel": "telegram", "accountId": "bot_coder", "priority": 10},
    {"agentId": "researcher", "channel": "telegram", "accountId": "bot_research", "priority": 10},
    {"agentId": "assistant", "channel": "telegram", "accountId": "bot_chat", "priority": 10}
  ]
}
```

### 2.2 渠道层 (channels/manager.py)

**当前设计:**
```python
class ChannelManager:
    def __init__(self, config: Config, bus: MessageBus):
        self.channels: dict[str, BaseChannel] = {}
        # telegram: 单配置
        if config.channels.telegram.enabled:
            self.channels["telegram"] = TelegramChannel(config.channels.telegram, bus)
```

**目标设计:**
```python
class ChannelManager:
    def __init__(self, config: Config, bus: MessageBus):
        self.channels: dict[str, BaseChannel] = {}           # 渠道类型 -> Channel
        self.accounts: dict[str, dict[str, BaseChannel]] = {}  # 渠道 -> {账号ID -> Channel}
        
        # Telegram多账号支持
        for account_config in config.channel_accounts.get("telegram", []):
            if account_config.enabled:
                channel = TelegramChannel(
                    config=account_config,
                    bus=bus,
                    account_id=account_config.id,  # 新增: 标识账号
                )
                self.accounts.setdefault("telegram", {})[account_config.id] = channel
```

**新增: Channel账号标识**
```python
class TelegramChannel(BaseChannel):
    def __init__(self, config: TelegramConfig, bus: MessageBus, account_id: str | None = None):
        super().__init__(config, bus)
        self.account_id = account_id  # 新增: 用于路由识别
        
    async def _on_message(self, update, context):
        # 在消息metadata中标记账号ID
        metadata = {
            ...
            "account_id": self.account_id,  # 用于AgentRouter识别
        }
```

### 2.3 路由层 (新增: agent/router.py)

**全新模块: AgentRouter**
```python
class AgentRouter:
    """
    消息路由中心
    根据bindings规则将消息路由到对应的Agent
    """
    
    def __init__(self, bindings: list[BindingRule]):
        self.bindings = sorted(bindings, key=lambda b: -b.priority)
        self._cache: dict[str, str] = {}  # 缓存: "channel:account:chat" -> agent_id
    
    def route(self, msg: InboundMessage) -> str | None:
        """
        根据消息路由到Agent ID
        返回None表示没有匹配的规则
        """
        cache_key = f"{msg.channel}:{msg.metadata.get('account_id')}:{msg.chat_id}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        for rule in self.bindings:
            if self._matches(rule, msg):
                self._cache[cache_key] = rule.agent_id
                return rule.agent_id
        
        # 默认路由到第一个Agent
        return self._default_agent_id
    
    def _matches(self, rule: BindingRule, msg: InboundMessage) -> bool:
        if rule.channel != msg.channel:
            return False
        if rule.account_id and rule.account_id != msg.metadata.get("account_id"):
            return False
        if rule.chat_id and rule.chat_id != msg.chat_id:
            return False
        return True
```

### 2.4 Agent管理层 (新增: agent/manager.py)

**全新模块: AgentManager**
```python
class AgentInstance:
    """单个Agent实例的封装"""
    
    def __init__(self, config: AgentInstanceConfig, bus: MessageBus):
        self.id = config.id
        self.config = config
        self.workspace = Path(config.workspace).expanduser()
        
        # 每个Agent独立的组件
        self.session_manager = SessionManager(self.workspace)
        self.agent_loop = AgentLoop(
            bus=bus,
            workspace=self.workspace,
            model=config.model or default_model,
            # ... 其他配置
        )
    
    async def process_message(self, msg: InboundMessage) -> OutboundMessage:
        """处理分配给该Agent的消息"""
        return await self.agent_loop.process(msg)

class AgentManager:
    """管理所有Agent实例"""
    
    def __init__(self, config: Config, bus: MessageBus):
        self.agents: dict[str, AgentInstance] = {}
        self.router = AgentRouter(config.bindings)
        self.bus = bus
        
        # 初始化所有Agent实例
        for agent_config in config.agents_list:
            if agent_config.enabled:
                self.agents[agent_config.id] = AgentInstance(agent_config, bus)
    
    async def dispatch(self, msg: InboundMessage) -> None:
        """接收消息并路由到对应Agent"""
        agent_id = self.router.route(msg)
        
        if not agent_id or agent_id not in self.agents:
            logger.warning(f"No agent found for message: {msg}")
            return
        
        agent = self.agents[agent_id]
        response = await agent.process_message(msg)
        
        if response:
            await self.bus.publish_outbound(response)
```

### 2.5 消息总线增强 (bus/queue.py)

```python
class MessageBus:
    """增强的消息总线，支持Agent ID路由"""
    
    def __init__(self):
        self._inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()
        self._agent_queues: dict[str, asyncio.Queue[InboundMessage]] = {}  # 新增
    
    async def publish_inbound(self, msg: InboundMessage, agent_id: str | None = None) -> None:
        """
        发布入站消息
        如果指定了agent_id，直接发送到对应Agent的队列
        """
        if agent_id and agent_id in self._agent_queues:
            await self._agent_queues[agent_id].put(msg)
        else:
            await self._inbound.put(msg)
    
    def register_agent_queue(self, agent_id: str, queue: asyncio.Queue) -> None:
        """注册Agent的私有队列"""
        self._agent_queues[agent_id] = queue
```

### 2.6 Gateway启动流程 (cli/commands.py)

**当前流程:**
```python
@app.command()
def gateway(...):
    config = _load_runtime_config(config, workspace)
    bus = MessageBus()
    provider = _make_provider(config)
    session_manager = SessionManager(config.workspace_path)
    
    agent = AgentLoop(bus=bus, provider=provider, ...)  # 单Agent
    channels = ChannelManager(config, bus)              # 单渠道
    
    await asyncio.gather(agent.run(), channels.start_all())
```

**目标流程:**
```python
@app.command()
def gateway(...):
    config = _load_runtime_config(config, workspace)
    bus = MessageBus()
    
    # 新增: AgentManager 管理多Agent
    agent_manager = AgentManager(config, bus)
    
    # 增强: ChannelManager 支持多账号
    channel_manager = ChannelManager(config, bus, multi_account=True)
    
    # 新增: 消息分发器，将Channel消息路由到Agent
    dispatcher = MessageDispatcher(channel_manager, agent_manager, bus)
    
    await asyncio.gather(
        agent_manager.run_all(),      # 启动所有Agent
        channel_manager.start_all(),  # 启动所有Channel账号
        dispatcher.run(),             # 运行消息分发
    )
```

---

## 3. 实现复杂度评估

### 3.1 改动范围统计

| 模块 | 当前代码量 | 预计改动 | 改动类型 |
|------|-----------|---------|---------|
| config/schema.py | 421行 | +200行 | 新增配置类 |
| config/loader.py | 75行 | +50行 | 适配新配置 |
| channels/manager.py | 256行 | +150行 | 多账号支持 |
| channels/telegram.py | 672行 | +50行 | 添加account_id |
| agent/loop.py | 509行 | +100行 | 支持外部路由 |
| session/manager.py | 213行 | 0行 | 无需改动 ✅ |
| **新增: agent/manager.py** | - | ~300行 | 全新模块 |
| **新增: agent/router.py** | - | ~150行 | 全新模块 |
| **新增: bus/dispatcher.py** | - | ~100行 | 全新模块 |
| cli/commands.py | 975行 | +100行 | 适配新架构 |
| **总计** | ~3,121行 | **~1,200行** | - |

### 3.2 风险点分析

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| 配置兼容性 | 🔴 高 | 旧配置需要迁移 | 编写自动迁移脚本 |
| Session隔离 | 🟡 中 | 多Agent共享workspace | 强制每个Agent独立workspace |
| 消息路由错误 | 🟡 中 | 消息可能路由到错误Agent | 增加路由日志和调试命令 |
| 资源竞争 | 🟡 中 | 多Agent竞争CPU/内存 | 添加Agent级别资源限制 |
| 向后兼容 | 🟢 低 | 单Agent用户不受影响 | 保持agents_list为空时的单Agent模式 |

---

## 4. 实施方案

### 4.1 阶段一: 基础多Agent支持 (MVP)

**目标**: 支持单个Gateway运行多个独立Agent，但每个Agent只能绑定到一个Telegram Bot

**改动范围:**
1. ✅ 新增 `AgentInstanceConfig` 配置类
2. ✅ 新增 `AgentManager` 管理多Agent
3. ✅ 修改 `ChannelManager` 支持多账号（仅Telegram）
4. ✅ 新增简单的路由规则（account_id → agent_id）

**配置示例:**
```json
{
  "agentsList": [
    {"id": "coder", "workspace": "~/agents/coder"},
    {"id": "chat", "workspace": "~/agents/chat"}
  ],
  "channelAccounts": {
    "telegram": [
      {"id": "bot1", "token": "TOKEN1"},
      {"id": "bot2", "token": "TOKEN2"}
    ]
  },
  "bindings": [
    {"agentId": "coder", "channel": "telegram", "accountId": "bot1"},
    {"agentId": "chat", "channel": "telegram", "accountId": "bot2"}
  ]
}
```

**工作量**: ~600行代码，1-2周开发

### 4.2 阶段二: 高级路由 (可选)

**目标**: 支持复杂路由规则（按chat_id、按用户、按消息内容）

**新增功能:**
1. 按群组ID路由不同Agent
2. 按用户身份路由
3. 基于消息内容的关键词路由
4. 动态路由规则（运行时修改）

**配置示例:**
```json
{
  "bindings": [
    {"agentId": "coder", "channel": "telegram", "chatId": "-100123456789", "priority": 100},
    {"agentId": "admin", "channel": "telegram", "userId": "12345678", "priority": 90},
    {"agentId": "chat", "channel": "telegram", "pattern": "闲聊|天气|问候", "priority": 50},
    {"agentId": "default", "channel": "telegram", "priority": 0}
  ]
}
```

**工作量**: +400行代码，1周开发

### 4.3 阶段三: 跨Agent协作 (未来)

**目标**: Agent之间可以相互调用和通信

**功能设计:**
1. Agent间消息总线
2. 共享workspace区域
3. Agent委托任务给其他Agent

---

## 5. 与现有方案对比

### 5.1 方案对比

| 维度 | 当前多进程方案 | 目标单Gateway多Agent |
|------|---------------|---------------------|
| **进程数** | N个进程 | 1个进程 |
| **内存占用** | N × 50MB | ~100MB + N × 30MB |
| **启动时间** | N次启动 | 1次启动 |
| **配置管理** | N个配置文件 | 1个统一配置 |
| **日志查看** | 分散在多个进程 | 统一日志 |
| **资源隔离** | 进程级（强） | 应用级（中） |
| **故障影响** | 单Agent崩溃不影响其他 | 主进程崩溃全部中断 |
| **实现复杂度** | 无需改动 | 中等 |
| **维护成本** | 低（稳定） | 中（新代码） |

### 5.2 推荐选择

| 场景 | 推荐方案 |
|------|---------|
| 2-3个Agent，资源充足 | **当前多进程** ✅ |
| 5+个Agent，需要统一管理 | **目标多Agent** ✅ |
| 生产环境追求稳定 | **当前多进程** ✅ |
| 开发测试快速迭代 | **目标多Agent** ✅ |
| 需要Agent间协作 | **目标多Agent** ✅ (阶段三) |

---

## 6. 决策建议

### 6.1 立即行动项

如果你决定实现多Agent支持，建议按以下顺序:

1. **配置迁移脚本** (1天)
   - 支持从旧配置自动迁移到新格式
   - 保持向后兼容

2. **AgentManager框架** (3-5天)
   - 先实现AgentInstance封装
   - 保持单Agent功能正常

3. **Telegram多账号支持** (2-3天)
   - 修改TelegramChannel支持account_id
   - ChannelManager支持多实例

4. **路由层** (2-3天)
   - 简单的account_id → agent_id映射
   - 消息分发器

5. **测试与调优** (3-5天)
   - 多Agent并发测试
   - 资源占用优化
   - 边界情况处理

**总计: 2-3周工作量**

### 6.2 或者...

如果你**现在就想用**多Agent，可以直接使用**多进程方案**:

```bash
# 创建3个Agent实例
mkdir -p ~/.nanobot-{coder,research,chat}

# 配置各自的config.json
cp template-config.json ~/.nanobot-coder/config.json
cp template-config.json ~/.nanobot-research/config.json
cp template-config.json ~/.nanobot-chat/config.json

# 启动脚本
nanobot gateway --config ~/.nanobot-coder/config.json &
nanobot gateway --config ~/.nanobot-research/config.json &
nanobot gateway --config ~/.nanobot-chat/config.json &
```

**优点**: 立即可用，稳定可靠  
**缺点**: 内存占用稍高，配置分散

---

## 7. 结论

**nanobot实现多Agent架构是可行的**，但需要权衡:

- ✅ **技术上可行**: 参考OpenClaw的binding模式，约1,200行代码改动
- ⚠️ **复杂度中等**: 涉及配置、渠道、路由、Agent管理多个模块
- ✅ **收益明显**: 资源节省、统一管理、Agent协作能力
- ⚠️ **需要投入**: 2-3周开发时间 + 测试调优

**最终建议**:
- 如果需要**立即使用多Agent** → 用多进程方案
- 如果追求**长期架构演进** → 值得投入实现单Gateway多Agent
- 如果是**生产环境** → 建议先用多进程，等新架构稳定后迁移

---

## 参考

- OpenClaw Multi-Agent: https://zread.ai/openclaw/openclaw/26-agent-system-architecture
- nanobot Architecture: `./01-architecture-overview.md`
- nanobot vs OpenClaw: `./03-openclaw-comparison.md`
