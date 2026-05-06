# nanobot 核心模块详解

> **文档版本**: v1.0  
> **最后更新**: 2026-03-10  
> **适用范围**: nanobot v0.1.4.post4+

---

## 1. Agent 模块 (1,341 行)

### 1.1 模块结构

```
nanobot/agent/
├── __init__.py          # 模块导出
├── loop.py              # Agent主循环 (核心, ~400行)
├── context.py           # 上下文构建器 (~300行)
├── memory.py            # 记忆系统 (~200行)
├── skills.py            # 技能加载器 (~150行)
├── subagent.py          # 子代理管理 (~200行)
└── tools/               # 工具子模块 (1,312行)
    ├── __init__.py
    ├── base.py          # 工具基类
    ├── registry.py      # 工具注册表
    ├── shell.py         # Shell执行
    ├── filesystem.py    # 文件操作
    ├── web.py           # Web搜索/抓取
    ├── mcp.py           # MCP协议支持
    ├── spawn.py         # 子代理spawn
    ├── cron.py          # 定时任务
    └── message.py       # 消息处理
```

### 1.2 AgentLoop 核心循环

```python
# nanobot/agent/loop.py - 简化示意

class AgentLoop:
    """Agent主循环：协调LLM调用和工具执行"""

    async def process_message(self, message: Message) -> None:
        """处理单条消息的主入口"""

        # 1. 加载或创建会话
        session = self.session_manager.get_or_create(message.user_id)

        # 2. 构建上下文 (系统提示词 + 历史 + 记忆)
        context = self.context_builder.build(
            message=message,
            session=session,
            skills=self.skills_loader.get_active()
        )

        # 3. 调用LLM (流式响应)
        async for chunk in self.llm_provider.stream_chat(context):
            # 实时发送给用户 (打字机效果)
            await self.send_chunk(chunk)

            # 检测工具调用
            if chunk.is_tool_call:
                # 4. 执行工具
                result = await self.tool_registry.execute(
                    tool_name=chunk.tool_name,
                    arguments=chunk.arguments
                )

                # 5. 将结果加入上下文，继续循环
                context.add_tool_result(result)

                # 递归调用LLM获取最终响应
                async for final_chunk in self.llm_provider.stream_chat(context):
                    await self.send_chunk(final_chunk)

        # 6. 保存会话历史
        session.save_turn(message, full_response)
```

### 1.3 ContextBuilder 上下文构建

```python
# nanobot/agent/context.py - 核心逻辑

class ContextBuilder:
    """构建发送给LLM的完整上下文"""

    def build(self, message, session, skills) -> Context:
        """构建上下文，包含7层信息"""

        context = Context()

        # Layer 1: 系统提示词 (固定)
        context.add_system_message(self.get_system_prompt())

        # Layer 2: 可用工具定义 (JSON Schema)
        tools_schema = self.tool_registry.get_schemas()
        context.add_tools(tools_schema)

        # Layer 3: 技能描述
        for skill in skills:
            context.add_system_message(skill.get_description())

        # Layer 4: 用户记忆 (相关记忆检索)
        relevant_memories = self.memory_store.retrieve(
            query=message.content,
            user_id=message.user_id
        )
        if relevant_memories:
            context.add_system_message(f"相关记忆: {relevant_memories}")

        # Layer 5: 会话历史 (最近N轮)
        recent_history = session.get_recent_turns(limit=10)
        for turn in recent_history:
            context.add_message(turn.role, turn.content)

        # Layer 6: 当前用户消息
        context.add_user_message(message.content)

        return context
```

### 1.4 MemoryStore 记忆系统

```python
# nanobot/agent/memory.py - 简化示意

class MemoryStore:
    """
    轻量级记忆系统
    - 存储: CSV/JSON 文件 (~/.nanobot/workspace/memory/)
    - 格式: 每行一条记忆，包含 timestamp, content, importance
    - 检索: 简单的关键词匹配 + 时间衰减
    """

    def __init__(self, workspace_path: Path):
        self.memory_file = workspace_path / "memory" / "store.csv"
        self.memories = self._load()

    def add(self, content: str, importance: int = 1):
        """添加新记忆"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "content": content,
            "importance": importance
        }
        self.memories.append(entry)
        self._save()

    def retrieve(self, query: str, limit: int = 5) -> List[str]:
        """
        检索相关记忆
        简单实现: 关键词匹配 + 重要性排序 + 时间衰减
        """
        scored = []
        for mem in self.memories:
            score = self._calculate_relevance(mem, query)
            scored.append((score, mem))

        # 按分数排序，返回 top N
        scored.sort(reverse=True)
        return [m["content"] for _, m in scored[:limit]]

    def _calculate_relevance(self, memory, query) -> float:
        """计算记忆与查询的相关性分数"""
        score = 0.0

        # 关键词匹配
        query_words = set(query.lower().split())
        mem_words = set(memory["content"].lower().split())
        overlap = len(query_words & mem_words)
        score += overlap * 1.0

        # 重要性权重
        score *= memory["importance"]

        # 时间衰减 (越新的记忆权重越高)
        age_days = (datetime.now() - mem_time).days
        score *= (0.99 ** age_days)

        return score
```

### 1.5 SkillsLoader 技能系统

```python
# nanobot/agent/skills.py - 简化示意

class SkillsLoader:
    """
    技能加载器
    技能 = Markdown文件 + (可选) Shell脚本
    """

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills: Dict[str, Skill] = {}

    def load_all(self):
        """扫描并加载所有技能"""
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir():
                skill = self._load_skill(skill_dir)
                self.skills[skill.name] = skill

    def _load_skill(self, path: Path) -> Skill:
        """加载单个技能"""
        skill_md = path / "SKILL.md"

        # 解析 SKILL.md
        with open(skill_md) as f:
            content = f.read()

        # 解析 YAML Frontmatter + Markdown
        metadata, body = self._parse_frontmatter(content)

        return Skill(
            name=metadata["name"],
            description=body,  # Markdown内容作为技能描述
            triggers=metadata.get("triggers", []),
            scripts=list(path.glob("*.sh"))  # 关联的Shell脚本
        )

    def get_active(self) -> List[Skill]:
        """获取当前激活的技能"""
        return list(self.skills.values())
```

**技能文件示例 (SKILL.md)**:
```markdown
---
name: weather
triggers: ["天气", "weather", "forecast"]
---

# Weather Skill

当用户询问天气时，使用以下工具获取信息：
- 工具: `web_search` 搜索天气预报
- 参数: location (城市名)

## 响应格式

请以友好方式告知用户：
- 当前温度
- 天气状况 (晴/雨/云等)
- 建议穿着
```

### 1.6 SubagentManager 子代理

```python
# nanobot/agent/subagent.py - 简化示意

class SubagentManager:
    """
    子代理管理器
    支持后台并行任务执行
    """

    def __init__(self):
        self.running_tasks: Dict[str, Task] = {}

    async def spawn(self, instruction: str, context: Context) -> Task:
        """
        创建子代理任务
        在后台并行执行，不阻塞主循环
        """
        task_id = generate_id()

        # 创建独立上下文 (继承部分父上下文)
        subagent_context = self._create_sub_context(context)
        subagent_context.add_user_message(instruction)

        # 启动异步任务
        task = asyncio.create_task(
            self._run_subagent(task_id, subagent_context)
        )

        self.running_tasks[task_id] = task
        return task

    async def _run_subagent(self, task_id: str, context: Context):
        """子代理执行逻辑"""
        try:
            # 类似主循环的简化版
            response = await self.llm_provider.chat(context)

            # 支持工具调用
            while response.has_tool_calls:
                results = await self._execute_tools(response.tool_calls)
                context.add_tool_results(results)
                response = await self.llm_provider.chat(context)

            # 通知主代理完成
            await self._notify_completion(task_id, response.content)

        except Exception as e:
            await self._notify_error(task_id, str(e))
```

---

## 2. Tools 模块 (1,312 行)

### 2.1 工具注册表

```python
# nanobot/agent/tools/registry.py - 简化示意

class ToolRegistry:
    """
    工具注册表
    管理所有可用工具，支持动态注册
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """注册内置工具"""
        self.register(ShellTool())
        self.register(FilesystemTool())
        self.register(WebSearchTool())
        self.register(WebFetchTool())
        self.register(CronTool())
        self.register(SpawnTool())
        self.register(MessageTool())

    def register(self, tool: Tool):
        """注册工具"""
        self._tools[tool.name] = tool

    async def execute(self, tool_name: str, arguments: dict) -> ToolResult:
        """执行工具调用"""
        if tool_name not in self._tools:
            return ToolResult(error=f"Unknown tool: {tool_name}")

        tool = self._tools[tool_name]

        # 验证参数
        try:
            validated_args = tool.validate_args(arguments)
        except ValidationError as e:
            return ToolResult(error=f"Invalid arguments: {e}")

        # 执行工具
        try:
            result = await tool.execute(**validated_args)
            return ToolResult(data=result)
        except Exception as e:
            return ToolResult(error=str(e))

    def get_schemas(self) -> List[dict]:
        """获取所有工具的JSON Schema (用于LLM)"""
        return [tool.get_schema() for tool in self._tools.values()]
```

### 2.2 文件系统工具

```python
# nanobot/agent/tools/filesystem.py

class FilesystemTool(Tool):
    """
    安全的文件系统操作
    支持: read, write, edit, list
    """

    name = "filesystem"
    description = "Read, write, and edit files in the workspace"

    def __init__(self, workspace: Path, restrict: bool = True):
        self.workspace = workspace
        self.restrict = restrict  # 是否限制在工作区内

    async def read(self, path: str) -> str:
        """读取文件内容"""
        full_path = self._resolve_path(path)

        # 安全检查
        if self.restrict and not self._is_in_workspace(full_path):
            raise PermissionError(f"Path outside workspace: {path}")

        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()

    async def write(self, path: str, content: str) -> str:
        """写入文件"""
        full_path = self._resolve_path(path)

        if self.restrict and not self._is_in_workspace(full_path):
            raise PermissionError(f"Path outside workspace: {path}")

        # 确保目录存在
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"Successfully wrote to {path}"

    async def edit(self, path: str, old_string: str, new_string: str) -> str:
        """
        精确编辑文件 (类似AI代码助手的编辑方式)
        通过匹配old_string来定位修改位置
        """
        content = await self.read(path)

        if old_string not in content:
            raise ValueError(f"old_string not found in file: {old_string[:50]}...")

        # 替换 (确保唯一性)
        if content.count(old_string) > 1:
            raise ValueError(f"old_string appears multiple times, please provide more context")

        new_content = content.replace(old_string, new_string, 1)
        await self.write(path, new_content)

        return f"Successfully edited {path}"

    async def list(self, path: str = ".") -> List[dict]:
        """列出目录内容"""
        full_path = self._resolve_path(path)

        entries = []
        for entry in full_path.iterdir():
            entries.append({
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "size": entry.stat().st_size if entry.is_file() else None
            })

        return entries

    def _resolve_path(self, path: str) -> Path:
        """解析路径，处理 ~ 和相对路径"""
        if path.startswith("~"):
            path = str(Path.home()) + path[1:]
        return (self.workspace / path).resolve()

    def _is_in_workspace(self, path: Path) -> bool:
        """检查路径是否在工作区内"""
        try:
            path.relative_to(self.workspace.resolve())
            return True
        except ValueError:
            return False
```

### 2.3 Shell 工具

```python
# nanobot/agent/tools/shell.py

class ShellTool(Tool):
    """
    Shell 命令执行
    带超时、输出限制、安全检查
    """

    name = "shell"
    description = "Execute shell commands"

    def __init__(self, timeout: int = 30, max_output: int = 10000):
        self.timeout = timeout
        self.max_output = max_output

    async def execute(self, command: str, working_dir: str = None) -> dict:
        """执行Shell命令"""

        # 创建子进程
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir
        )

        try:
            # 带超时等待
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )

            # 截断长输出
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')

            if len(stdout_str) > self.max_output:
                stdout_str = stdout_str[:self.max_output] + "\n... (truncated)"

            return {
                "exit_code": process.returncode,
                "stdout": stdout_str,
                "stderr": stderr_str
            }

        except asyncio.TimeoutError:
            process.kill()
            return {
                "exit_code": -1,
                "error": f"Command timed out after {self.timeout}s"
            }
```

### 2.4 Web 工具

```python
# nanobot/agent/tools/web.py

class WebSearchTool(Tool):
    """
    Web 搜索 (集成 Brave Search API)
    """

    name = "web_search"
    description = "Search the web for information"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    async def execute(self, query: str, count: int = 10) -> List[dict]:
        """执行搜索"""

        headers = {
            "X-Subscription-Token": self.api_key,
            "Accept": "application/json"
        }

        params = {
            "q": query,
            "count": min(count, 20)  # 限制最大结果数
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                headers=headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()

        # 格式化结果
        results = []
        for item in data.get("web", {}).get("results", []):
            results.append({
                "title": item.get("title"),
                "url": item.get("url"),
                "description": item.get("description")
            })

        return results


class WebFetchTool(Tool):
    """
    网页抓取与内容提取
    """

    name = "web_fetch"
    description = "Fetch and extract content from a URL"

    async def execute(self, url: str) -> dict:
        """抓取网页内容"""

        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            html = response.text

        # 使用 readability-lxml 提取正文
        from readability import Document
        doc = Document(html)

        return {
            "title": doc.title(),
            "content": doc.summary(),  # HTML格式
            "text": doc.summary().get_text(),  # 纯文本
            "url": url
        }
```

### 2.5 MCP 工具集成

```python
# nanobot/agent/tools/mcp.py

class MCPTool(Tool):
    """
    Model Context Protocol 工具集成
    连接外部MCP服务器，将其工具暴露给Agent
    """

    name = "mcp"
    description = "Tools from MCP servers"

    def __init__(self, servers_config: dict):
        self.servers = {}
        self.tools = {}

        # 初始化MCP服务器连接
        for name, config in servers_config.items():
            self.servers[name] = MCPClient(config)

    async def discover_tools(self):
        """从所有MCP服务器发现工具"""
        for server_name, client in self.servers.items():
            server_tools = await client.list_tools()

            for tool in server_tools:
                # 使用 server_name/tool_name 作为唯一标识
                full_name = f"{server_name}/{tool.name}"
                self.tools[full_name] = {
                    "server": server_name,
                    "tool": tool
                }

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """执行MCP工具调用"""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown MCP tool: {tool_name}")

        tool_info = self.tools[tool_name]
        client = self.servers[tool_info["server"]]

        # 调用MCP服务器
        result = await client.call_tool(
            tool_info["tool"].name,
            arguments
        )

        return result
```

---

## 3. Channels 模块 (~2,000 行)

### 3.1 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                      Channel 架构                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  ChannelBase (抽象基类)                  │   │
│  │  - send_message()     # 发送消息                        │   │
│  │  - start_listening()  # 开始监听                        │   │
│  │  - stop_listening()   # 停止监听                        │   │
│  │  - parse_message()    # 解析平台特定格式                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           ▲                                     │
│           ┌───────────────┼───────────────┐                     │
│           │               │               │                     │
│  ┌────────┴─────┐  ┌──────┴──────┐  ┌─────┴──────┐             │
│  │   Telegram   │  │   Discord   │  │  WhatsApp  │             │
│  │   Channel    │  │   Channel   │  │   Channel  │             │
│  │              │  │             │  │            │             │
│  │  python-     │  │  discord.py │  │  Baileys   │             │
│  │  telegram-   │  │  library    │  │  (Node.js) │             │
│  │  bot         │  │             │  │  bridge    │             │
│  └──────────────┘  └─────────────┘  └────────────┘             │
│                                                                 │
│  ┌──────────────┐  ┌─────────────┐  ┌────────────┐             │
│  │    Feishu    │  │    Slack    │  │    QQ      │             │
│  │   (飞书)      │  │             │  │            │             │
│  │  lark-oapi   │  │ slack-sdk   │  │  qq-botpy  │             │
│  └──────────────┘  └─────────────┘  └────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 基类定义

```python
# nanobot/channels/base.py

class ChannelBase(ABC):
    """
    聊天渠道抽象基类
    所有具体渠道必须继承此类
    """

    def __init__(self, config: ChannelConfig, message_bus: MessageBus):
        self.config = config
        self.bus = message_bus
        self._running = False

    @abstractmethod
    async def send_message(self, user_id: str, content: str, **kwargs) -> None:
        """
        发送消息到用户

        Args:
            user_id: 用户标识
            content: 消息内容
            **kwargs: 平台特定参数 (如 Telegram 的 parse_mode)
        """
        pass

    @abstractmethod
    async def start_listening(self) -> None:
        """开始监听用户消息"""
        pass

    @abstractmethod
    async def stop_listening(self) -> None:
        """停止监听"""
        pass

    @abstractmethod
    def parse_message(self, raw_data: Any) -> Optional[Message]:
        """
        解析平台特定的消息格式为统一Message对象
        """
        pass

    async def handle_incoming(self, raw_data: Any) -> None:
        """
        处理收到的消息 (通用流程)
        """
        # 1. 解析消息
        message = self.parse_message(raw_data)
        if not message:
            return

        # 2. 权限检查
        if not self._check_access(message.user_id):
            logger.warning(f"Access denied for user: {message.user_id}")
            return

        # 3. 发布到消息总线
        await self.bus.publish(EventType.MESSAGE_RECEIVED, {
            "message": message,
            "channel": self.name
        })

    def _check_access(self, user_id: str) -> bool:
        """检查用户是否有权限访问"""
        allowed = self.config.allow_from

        # 空列表 = 拒绝所有 (安全默认)
        if not allowed:
            return False

        # ["*"] = 允许所有
        if "*" in allowed:
            return True

        return user_id in allowed

    @property
    @abstractmethod
    def name(self) -> str:
        """渠道名称标识"""
        pass
```

### 3.3 Telegram 渠道实现

```python
# nanobot/channels/telegram.py

class TelegramChannel(ChannelBase):
    """
    Telegram 渠道实现
    使用 python-telegram-bot 库
    """

    name = "telegram"

    def __init__(self, config: TelegramConfig, message_bus: MessageBus):
        super().__init__(config, message_bus)
        self.token = config.token

        # 初始化 bot
        self.application = Application.builder().token(self.token).build()

        # 注册消息处理器
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message)
        )
        self.application.add_handler(
            MessageHandler(filters.VOICE, self._on_voice)
        )

    async def start_listening(self) -> None:
        """启动 Telegram Bot (长轮询)"""
        self._running = True
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("Telegram channel started")

    async def stop_listening(self) -> None:
        """停止"""
        self._running = False
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()

    async def send_message(self, user_id: str, content: str, **kwargs) -> None:
        """发送消息"""
        # 支持Markdown格式
        parse_mode = kwargs.get('parse_mode', ParseMode.MARKDOWN)

        # 分割长消息 (Telegram限制4096字符)
        chunks = self._split_message(content, 4000)

        for chunk in chunks:
            await self.application.bot.send_message(
                chat_id=user_id,
                text=chunk,
                parse_mode=parse_mode
            )

    def parse_message(self, update: Update) -> Optional[Message]:
        """解析 Telegram Update 为 Message"""
        if not update.message or not update.message.text:
            return None

        return Message(
            id=str(update.message.message_id),
            user_id=str(update.message.from_user.id),
            content=update.message.text,
            timestamp=update.message.date,
            metadata={
                "chat_id": update.message.chat_id,
                "is_group": update.message.chat.type in ["group", "supergroup"]
            }
        )

    async def _on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """收到文本消息"""
        await self.handle_incoming(update)

    async def _on_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """收到语音消息 - 支持语音转文字"""
        # 下载语音文件
        voice_file = await update.message.voice.get_file()
        voice_bytes = await voice_file.download_as_bytearray()

        # 使用 Groq Whisper 转录
        transcription = await self.transcribe_voice(voice_bytes)

        # 创建文本消息继续处理
        message = Message(
            id=str(update.message.message_id),
            user_id=str(update.message.from_user.id),
            content=transcription,  # 转录后的文本
            timestamp=update.message.date,
            is_voice=True,
            metadata={"original_voice": True}
        )

        await self.bus.publish(EventType.MESSAGE_RECEIVED, {
            "message": message,
            "channel": self.name
        })

    def _split_message(self, text: str, max_length: int) -> List[str]:
        """分割长消息"""
        if len(text) <= max_length:
            return [text]

        chunks = []
        while text:
            if len(text) <= max_length:
                chunks.append(text)
                break

            # 在句子边界分割
            split_point = text.rfind('.', 0, max_length)
            if split_point == -1:
                split_point = text.rfind('\n', 0, max_length)
            if split_point == -1:
                split_point = max_length

            chunks.append(text[:split_point + 1])
            text = text[split_point + 1:]

        return chunks
```

### 3.4 飞书渠道实现

```python
# nanobot/channels/feishu.py

class FeishuChannel(ChannelBase):
    """
    飞书(Feishu/Lark)渠道实现
    使用 WebSocket 长连接，无需公网IP
    """

    name = "feishu"

    def __init__(self, config: FeishuConfig, message_bus: MessageBus):
        super().__init__(config, message_bus)
        self.app_id = config.app_id
        self.app_secret = config.app_secret

        # 初始化飞书客户端
        self.client = LarkClient(
            app_id=self.app_id,
            app_secret=self.app_secret
        )

        # WebSocket 连接
        self.ws = None
        self.ws_client = None

    async def start_listening(self) -> None:
        """建立 WebSocket 连接"""
        self._running = True

        # 获取 tenant_access_token
        token = await self._get_access_token()

        # 建立 WebSocket 连接
        ws_url = f"wss://ws.feishu.cn/v1/events?token={token}"

        self.ws_client = aiohttp.ClientSession()
        self.ws = await self.ws_client.ws_connect(ws_url)

        # 启动消息接收循环
        asyncio.create_task(self._receive_loop())

        logger.info("Feishu channel started (WebSocket)")

    async def _receive_loop(self):
        """WebSocket 消息接收循环"""
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                await self._handle_event(data)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error(f"WebSocket error: {self.ws.exception()}")
                break

    async def _handle_event(self, event: dict):
        """处理飞书事件"""
        event_type = event.get("header", {}).get("event_type")

        if event_type == "im.message.receive_v1":
            # 收到消息
            message_data = event.get("event", {}).get("message", {})
            await self.handle_incoming(message_data)

    def parse_message(self, raw_data: dict) -> Optional[Message]:
        """解析飞书消息"""
        content = json.loads(raw_data.get("content", "{}"))
        text = content.get("text", "")

        return Message(
            id=raw_data.get("message_id"),
            user_id=raw_data.get("sender", {}).get("sender_id", {}).get("open_id"),
            content=text,
            timestamp=datetime.fromtimestamp(
                int(raw_data.get("create_time", "0")) / 1000
            ),
            metadata={
                "chat_id": raw_data.get("chat_id"),
                "msg_type": raw_data.get("msg_type")
            }
        )

    async def send_message(self, user_id: str, content: str, **kwargs) -> None:
        """发送飞书消息"""
        # 飞书API要求特定的消息格式
        message = {
            "receive_id": user_id,
            "content": json.dumps({"text": content}),
            "msg_type": "text"
        }

        await self.client.im.v1.message.create(message)
```

---

## 4. Providers 模块 (~800 行)

### 4.1 Provider 注册表设计

```python
# nanobot/providers/registry.py

"""
Provider Registry - 单一事实来源
添加新Provider只需2步：
1. 在此添加 ProviderSpec
2. 在 schema.py 添加配置字段
"""

from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any

@dataclass
class ProviderSpec:
    """提供商规格定义"""
    name: str                      # 配置字段名 (如 "openrouter")
    keywords: Tuple[str, ...]      # 模型名关键词 (用于自动匹配)
    env_key: str                   # 环境变量名
    display_name: str              # 显示名称
    litellm_prefix: str            # LiteLLM前缀
    skip_prefixes: Tuple[str, ...] = ()      # 跳过的前缀
    env_extras: Tuple[tuple, ...] = ()       # 额外环境变量
    model_overrides: Tuple[tuple, ...] = ()  # 模型参数覆盖
    is_gateway: bool = False                   # 是否网关 (如OpenRouter)
    detect_by_key_prefix: Optional[str] = None # API Key前缀检测
    detect_by_base_keyword: Optional[str] = None # API Base关键词检测
    strip_model_prefix: bool = False           # 是否去除前缀

# 所有支持的Provider定义
PROVIDERS = [
    # 网关型 (可路由任意模型)
    ProviderSpec(
        name="openrouter",
        keywords=("openrouter",),
        env_key="OPENROUTER_API_KEY",
        display_name="OpenRouter",
        litellm_prefix="openrouter",
        skip_prefixes=("openrouter/",),
        is_gateway=True,
        detect_by_key_prefix="sk-or-",
    ),

    # 直连型
    ProviderSpec(
        name="anthropic",
        keywords=("claude", "anthropic"),
        env_key="ANTHROPIC_API_KEY",
        display_name="Anthropic",
        litellm_prefix="anthropic",
    ),

    ProviderSpec(
        name="openai",
        keywords=("gpt", "openai"),
        env_key="OPENAI_API_KEY",
        display_name="OpenAI",
        litellm_prefix="openai",
    ),

    ProviderSpec(
        name="deepseek",
        keywords=("deepseek",),
        env_key="DEEPSEEK_API_KEY",
        display_name="DeepSeek",
        litellm_prefix="deepseek",
    ),

    ProviderSpec(
        name="groq",
        keywords=("groq", "llama", "mixtral"),
        env_key="GROQ_API_KEY",
        display_name="Groq",
        litellm_prefix="groq",
    ),

    # 中国厂商
    ProviderSpec(
        name="dashscope",
        keywords=("qwen", "dashscope", "qwq"),
        env_key="DASHSCOPE_API_KEY",
        display_name="Dashscope (Qwen)",
        litellm_prefix="dashscope",
    ),

    ProviderSpec(
        name="moonshot",
        keywords=("moonshot", "kimi"),
        env_key="MOONSHOT_API_KEY",
        display_name="Moonshot (Kimi)",
        litellm_prefix="moonshot",
        model_overrides=(("kimi-k2.5", {"temperature": 1.0}),),
    ),

    # OAuth型
    ProviderSpec(
        name="openai_codex",
        keywords=("codex",),
        env_key="OPENAI_CODEX_TOKEN",  # OAuth token
        display_name="OpenAI Codex",
        litellm_prefix="openai-codex",
    ),

    # ... 更多Provider
]


def get_provider_for_model(model: str) -> Optional[ProviderSpec]:
    """
    根据模型名自动匹配Provider
    例如: "gpt-4" → OpenAI, "claude-3" → Anthropic
    """
    model_lower = model.lower()

    for provider in PROVIDERS:
        # 关键词匹配
        if any(kw in model_lower for kw in provider.keywords):
            return provider

    return None


def detect_provider_from_key(api_key: str) -> Optional[ProviderSpec]:
    """
    根据API Key前缀自动检测Provider
    例如: "sk-or-xxx" → OpenRouter
    """
    for provider in PROVIDERS:
        if provider.detect_by_key_prefix:
            if api_key.startswith(provider.detect_by_key_prefix):
                return provider
    return None
```

### 4.2 LiteLLM 集成

```python
# nanobot/providers/litellm_provider.py

import litellm
from typing import AsyncIterator

class LiteLLMProvider:
    """
    LiteLLM 统一接口封装
    支持100+ LLM，自动处理模型路由
    """

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._setup_env()

    def _setup_env(self):
        """设置环境变量供LiteLLM使用"""
        import os

        # 设置API Key
        if self.config.api_key:
            os.environ[self.spec.env_key] = self.config.api_key

        # 设置额外环境变量
        for key, value in self.spec.env_extras:
            os.environ[key] = value.format(api_key=self.config.api_key)

    async def stream_chat(
        self,
        messages: List[dict],
        model: str,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式对话
        """
        # 自动添加Provider前缀 (如需要)
        full_model = self._prepare_model_name(model)

        # 调用LiteLLM
        response = await litellm.acompletion(
            model=full_model,
            messages=messages,
            stream=True,
            api_base=self.config.api_base,
            temperature=kwargs.get('temperature', 0.7),
            max_tokens=kwargs.get('max_tokens'),
        )

        # 流式输出
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    def _prepare_model_name(self, model: str) -> str:
        """
        准备模型名称
        例如: "gpt-4" → "openai/gpt-4"
        """
        # 如果已包含前缀，跳过
        if any(model.startswith(p) for p in self.spec.skip_prefixes):
            return model

        # 添加Provider前缀
        return f"{self.spec.litellm_prefix}/{model}"
```

---

## 5. Config 模块 (581 行)

### 5.1 Pydantic Schema 设计

```python
# nanobot/config/schema.py

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any


class AgentConfig(BaseModel):
    """Agent配置"""
    model: str = Field(default="anthropic/claude-sonnet-4")
    provider: Optional[str] = None  # 自动检测
    workspace: str = Field(default="~/.nanobot/workspace")
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: Optional[int] = None
    thinking_mode: bool = Field(default=False)


class TelegramConfig(BaseModel):
    """Telegram渠道配置"""
    enabled: bool = False
    token: str = ""
    allow_from: List[str] = Field(default_factory=list)
    group_policy: str = Field(default="mention")  # mention/open/allowlist


class DiscordConfig(BaseModel):
    """Discord渠道配置"""
    enabled: bool = False
    token: str = ""
    allow_from: List[str] = Field(default_factory=list)
    group_policy: str = Field(default="mention")


class ChannelsConfig(BaseModel):
    """所有渠道配置"""
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)
    feishu: FeishuConfig = Field(default_factory=FeishuConfig)
    slack: SlackConfig = Field(default_factory=SlackConfig)
    # ... 更多渠道


class ProviderConfig(BaseModel):
    """单个Provider配置"""
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    timeout: int = 60


class ProvidersConfig(BaseModel):
    """所有Provider配置"""
    openrouter: ProviderConfig = Field(default_factory=ProviderConfig)
    anthropic: ProviderConfig = Field(default_factory=ProviderConfig)
    openai: ProviderConfig = Field(default_factory=ProviderConfig)
    deepseek: ProviderConfig = Field(default_factory=ProviderConfig)
    # ... 更多Provider


class MCPServerConfig(BaseModel):
    """MCP服务器配置"""
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    tool_timeout: int = 30


class ToolsConfig(BaseModel):
    """工具配置"""
    restrict_to_workspace: bool = Field(default=False)
    exec_path_append: str = ""
    mcp_servers: Dict[str, MCPServerConfig] = Field(default_factory=dict)


class RootConfig(BaseModel):
    """根配置 - 对应 config.json"""
    agents: Dict[str, AgentConfig] = Field(
        default_factory=lambda: {"defaults": AgentConfig()}
    )
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)

    @field_validator('agents')
    @classmethod
    def ensure_defaults(cls, v):
        """确保 defaults 配置存在"""
        if 'defaults' not in v:
            v['defaults'] = AgentConfig()
        return v
```

### 5.2 配置加载流程

```python
# nanobot/config/loader.py

import json
from pathlib import Path
from .schema import RootConfig

class ConfigLoader:
    """
    配置加载器
    支持从文件加载和验证
    """

    DEFAULT_CONFIG_PATH = Path.home() / ".nanobot" / "config.json"

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> RootConfig:
        """加载配置"""
        path = config_path or cls.DEFAULT_CONFIG_PATH

        # 如果配置文件不存在，创建默认配置
        if not path.exists():
            cls._create_default_config(path)

        # 读取并解析JSON
        with open(path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        # Pydantic验证
        try:
            config = RootConfig.model_validate(raw_data)
        except ValidationError as e:
            logger.error(f"Config validation error: {e}")
            raise ConfigError(f"Invalid config: {e}")

        return config

    @classmethod
    def _create_default_config(cls, path: Path):
        """创建默认配置文件"""
        path.parent.mkdir(parents=True, exist_ok=True)

        default_config = {
            "agents": {
                "defaults": {
                    "model": "anthropic/claude-sonnet-4",
                    "workspace": "~/.nanobot/workspace"
                }
            },
            "channels": {},
            "providers": {},
            "tools": {
                "restrictToWorkspace": False
            }
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)

        logger.info(f"Created default config at {path}")
```

---

## 6. 其他支撑模块

### 6.1 Session 模块 (218 行)

```python
# nanobot/session/manager.py

class SessionManager:
    """
    会话管理器
    维护用户会话状态和对话历史
    """

    def __init__(self, sessions_dir: Path):
        self.sessions_dir = sessions_dir
        self._active_sessions: Dict[str, Session] = {}

    def get_or_create(self, user_id: str) -> Session:
        """获取或创建会话"""
        if user_id not in self._active_sessions:
            self._active_sessions[user_id] = self._load_session(user_id)
        return self._active_sessions[user_id]

    def _load_session(self, user_id: str) -> Session:
        """从磁盘加载会话"""
        session_file = self.sessions_dir / f"{user_id}.json"

        if session_file.exists():
            with open(session_file) as f:
                data = json.load(f)
            return Session.from_dict(data)

        return Session(user_id=user_id)

    def save_session(self, user_id: str):
        """保存会话到磁盘"""
        session = self._active_sessions.get(user_id)
        if session:
            session_file = self.sessions_dir / f"{user_id}.json"
            with open(session_file, 'w') as f:
                json.dump(session.to_dict(), f, indent=2)


class Session:
    """单个用户会话"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.turns: List[Turn] = []
        self.created_at = datetime.now()
        self.metadata: dict = {}

    def add_turn(self, role: str, content: str, tool_calls: list = None):
        """添加一轮对话"""
        self.turns.append(Turn(
            role=role,
            content=content,
            timestamp=datetime.now(),
            tool_calls=tool_calls or []
        ))

    def get_recent_turns(self, limit: int = 10) -> List[Turn]:
        """获取最近N轮对话"""
        return self.turns[-limit:]

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "turns": [t.to_dict() for t in self.turns],
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }
```

### 6.2 Cron 模块 (441 行)

```python
# nanobot/cron/service.py

from croniter import croniter

class CronService:
    """
    定时任务服务
    基于 croniter 实现自然语言Cron解析
    """

    def __init__(self, cron_dir: Path):
        self.cron_dir = cron_dir
        self.jobs: Dict[str, CronJob] = {}
        self._running = False

    async def start(self):
        """启动Cron服务"""
        self._running = True
        self._load_jobs()

        # 启动调度循环
        while self._running:
            await self._check_and_run_jobs()
            await asyncio.sleep(60)  # 每分钟检查一次

    def _load_jobs(self):
        """加载所有Cron任务"""
        for job_file in self.cron_dir.glob("*.json"):
            with open(job_file) as f:
                data = json.load(f)
                job = CronJob.from_dict(data)
                self.jobs[job.id] = job

    async def _check_and_run_jobs(self):
        """检查并执行到期的任务"""
        now = datetime.now()

        for job in self.jobs.values():
            if not job.enabled:
                continue

            # 检查是否到期
            if job.next_run and now >= job.next_run:
                asyncio.create_task(self._execute_job(job))

                # 计算下次执行时间
                itr = croniter(job.cron_expr, now)
                job.next_run = itr.get_next(datetime)

    async def _execute_job(self, job: CronJob):
        """执行单个任务"""
        logger.info(f"Executing cron job: {job.name}")

        try:
            # 创建任务执行上下文
            context = {
                "instruction": job.instruction,
                "user_id": job.user_id
            }

            # 发布执行事件
            await self.bus.publish(EventType.CRON_TRIGGERED, context)

        except Exception as e:
            logger.error(f"Cron job failed: {e}")

    def add_job(self, name: str, cron_expr: str, instruction: str, user_id: str) -> CronJob:
        """
        添加新任务
        cron_expr: 标准Cron表达式 (如 "0 9 * * *" 每天9点)
                   或自然语言 (如 "every day at 9am")
        """
        # 尝试解析自然语言
        if not self._is_valid_cron(cron_expr):
            cron_expr = self._natural_to_cron(cron_expr)

        job = CronJob(
            id=generate_id(),
            name=name,
            cron_expr=cron_expr,
            instruction=instruction,
            user_id=user_id,
            next_run=croniter(cron_expr, datetime.now()).get_next(datetime)
        )

        self.jobs[job.id] = job
        self._save_job(job)

        return job

    def _natural_to_cron(self, natural: str) -> str:
        """自然语言转Cron表达式"""
        # 简单示例实现
        natural = natural.lower().strip()

        patterns = {
            "every minute": "* * * * *",
            "every hour": "0 * * * *",
            "every day": "0 0 * * *",
            "every day at 9am": "0 9 * * *",
            "every week": "0 0 * * 0",
        }

        if natural in patterns:
            return patterns[natural]

        raise ValueError(f"Cannot parse natural language: {natural}")
```

### 6.3 Heartbeat 模块 (178 行)

```python
# nanobot/heartbeat/service.py

class HeartbeatService:
    """
    心跳服务
    周期性检查 HEARTBEAT.md 并执行任务
    """

    CHECK_INTERVAL = 30 * 60  # 30分钟

    def __init__(self, workspace: Path, message_bus: MessageBus):
        self.workspace = workspace
        self.bus = message_bus
        self._running = False

    async def start(self):
        """启动心跳服务"""
        self._running = True

        while self._running:
            await self._check_heartbeat()
            await asyncio.sleep(self.CHECK_INTERVAL)

    async def _check_heartbeat(self):
        """检查HEARTBEAT.md"""
        heartbeat_file = self.workspace / "HEARTBEAT.md"

        if not heartbeat_file.exists():
            return

        # 解析Markdown中的任务列表
        tasks = self._parse_heartbeat(heartbeat_file)

        for task in tasks:
            if not task.done:  # 未完成的任务
                await self.bus.publish(EventType.HEARTBEAT_TASK, {
                    "instruction": task.description,
                    "source": "heartbeat"
                })

    def _parse_heartbeat(self, file: Path) -> List[HeartbeatTask]:
        """解析HEARTBEAT.md"""
        with open(file) as f:
            content = f.read()

        tasks = []
        for line in content.split('\n'):
            # 匹配 Markdown 任务列表: - [ ] 或 - [x]
            match = re.match(r'\s*-\s*\[([ x])\]\s*(.+)', line)
            if match:
                is_done = match.group(1) == 'x'
                description = match.group(2).strip()
                tasks.append(HeartbeatTask(
                    description=description,
                    done=is_done
                ))

        return tasks


@dataclass
class HeartbeatTask:
    """心跳任务"""
    description: str
    done: bool = False
```

---

## 7. 总结

### 7.1 模块依赖图

```
┌─────────────────────────────────────────────────────────────────┐
│                      模块依赖关系                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CLI (入口)                                                     │
│    │                                                            │
│    ▼                                                            │
│  Config ──► Schema (Pydantic)                                   │
│    │                                                            │
│    ├──► AgentLoop ◄──► Session                                  │
│    │       │                                                    │
│    │       ├──► ContextBuilder ◄──► Memory                      │
│    │       │                                                    │
│    │       ├──► ToolRegistry ◄──► Skills                        │
│    │       │        │                                           │
│    │       │        ├──► Shell, Filesystem, Web, MCP, ...       │
│    │       │                                                    │
│    │       ├──► LLMProvider ◄──► LiteLLM ◄──► 100+ models       │
│    │       │                                                    │
│    │       └──► SubagentManager                                 │
│    │                                                            │
│    ├──► ChannelManager ◄──► 10+ Channels                        │
│    │       │                                                    │
│    │       └──► MessageBus ◄──► Event-Driven                    │
│    │                                                            │
│    ├──► CronService                                             │
│    │                                                            │
│    └──► HeartbeatService                                        │
│                                                                 │
│  核心原则: 高层模块依赖低层模块，通过Bus解耦                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 扩展点总结

| 扩展类型 | 文件位置 | 难度 | 示例 |
|----------|----------|------|------|
| **添加Provider** | `providers/registry.py` | ⭐ | 2步添加新LLM |
| **添加Channel** | `channels/` | ⭐⭐ | 继承Base，~100行 |
| **添加Tool** | `agent/tools/` | ⭐⭐ | 继承Tool基类 |
| **添加Skill** | `workspace/skills/` | ⭐ | Markdown文件 |
| **自定义行为** | `AGENTS.md`, `SOUL.md` | ⭐ | 修改提示词 |

---

## 参考文档

- [Architecture Overview](./01-architecture-overview.md) - 架构总览
- [OpenClaw Comparison](./03-openclaw-comparison.md) - 与OpenClaw对比
- [Deployment Guide](./04-deployment-operations.md) - 部署指南
