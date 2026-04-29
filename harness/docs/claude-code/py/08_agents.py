"""
Agent 系统 Python 实现

展示 Claude Code Agent 系统的核心设计模式在 Python 中的实现：
- Agent 定义类型
- Agent 生命周期
- Agent 间通信
- Mailbox 系统
- 团队管理
"""

from __future__ import annotations

import asyncio
import contextvars
import json
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Optional,
    Set,
)


# =============================================================================
# 1. Agent 类型定义
# =============================================================================

class AgentExecutionMode(str, Enum):
    """Agent 执行模式"""
    IN_PROCESS = "in-process"      # AsyncLocalStorage
    TMUX_SPLIT = "tmux-split"       # Tmux 分屏
    ITERM2_SPLIT = "iterm2-split"   # iTerm2 分屏
    WORKTREE = "worktree"           # Git Worktree


@dataclass
class AgentDefinition:
    """
    Agent 定义

    等价于 TypeScript 的 BaseAgentDefinition
    """
    # 标识
    agent_type: str
    description: Optional[str] = None
    when_to_use: Optional[str] = None

    # 工具控制
    tools: Optional[List[str]] = None
    disallowed_tools: Optional[List[str]] = None
    allowed_tools: Optional[List[str]] = None

    # 技能
    skills: Optional[List[str]] = None

    # MCP 服务器
    mcp_servers: Optional[List[Dict[str, Any]]] = None

    # 生命周期钩子
    hooks: Optional[Dict[str, Any]] = None

    # 模型控制
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    thinking_enabled: Optional[bool] = None

    # 权限控制
    permission_mode: Optional[str] = None

    # 执行控制
    max_turns: Optional[int] = None
    effort: Optional[str] = None
    background: bool = False

    # 上下文控制
    memory: Optional[str] = None  # 'user', 'project', 'local'
    isolation: Optional[str] = None  # 'worktree', 'remote'

    # CLAUDE.md
    omit_claude_md: bool = False


class AgentSource(str, Enum):
    """Agent 来源"""
    BUILT_IN = "built-in"
    USER_SETTINGS = "userSettings"
    PROJECT_SETTINGS = "projectSettings"
    POLICY_SETTINGS = "policySettings"
    PLUGIN = "plugin"


# =============================================================================
# 2. 消息类型
# =============================================================================

@dataclass
class ContentBlock:
    """内容块"""
    type: str
    text: Optional[str] = None
    name: Optional[str] = None
    input: Optional[Dict] = None


@dataclass
class Message:
    """消息"""
    role: str
    content: List[ContentBlock] = field(default_factory=list)


@dataclass
class TeammateMessage:
    """
    teammate 消息

    等价于 TypeScript 的 TeammateMessage
    """
    id: str
    from_agent: str
    to: str  # '*' for broadcast
    type: str = "message"  # 'message', 'shutdown_request', 'shutdown_response'
    content: str = ""
    timestamp: float = field(default_factory=time.time)


# =============================================================================
# 3. Mailbox 系统
# =============================================================================

class Mailbox:
    """
    Mailbox 系统

    等价于 TypeScript 的 Mailbox
    """

    def __init__(self, path: str):
        self._path = path
        self._processed_ids: Set[str] = set()

    async def write(self, message: TeammateMessage) -> None:
        """写入消息"""
        os.makedirs(self._path, exist_ok=True)

        file_path = os.path.join(self._path, f"{message.id}.json")
        with open(file_path, 'w') as f:
            json.dump({
                'id': message.id,
                'from': message.from_agent,
                'to': message.to,
                'type': message.type,
                'content': message.content,
                'timestamp': message.timestamp,
            }, f)

    async def read_all(self) -> List[TeammateMessage]:
        """读取所有消息"""
        if not os.path.exists(self._path):
            return []

        messages: List[TeammateMessage] = []

        for file_name in os.listdir(self._path):
            if not file_name.endswith('.json'):
                continue

            file_path = os.path.join(self._path, file_name)

            with open(file_path, 'r') as f:
                data = json.load(f)

            messages.append(TeammateMessage(
                id=data['id'],
                from_agent=data['from'],
                to=data['to'],
                type=data.get('type', 'message'),
                content=data.get('content', ''),
                timestamp=data.get('timestamp', time.time())
            ))

        return sorted(messages, key=lambda m: m.timestamp)

    async def cleanup(self, processed_ids: Set[str]) -> None:
        """清理已处理消息"""
        for file_name in os.listdir(self._path):
            if not file_name.endswith('.json'):
                continue

            msg_id = file_name[:-5]  # 去除 .json
            if msg_id in processed_ids:
                file_path = os.path.join(self._path, file_name)
                os.remove(file_path)


# =============================================================================
# 4. Agent Handle
# =============================================================================

@dataclass
class AgentHandle:
    """
    Agent Handle

    等价于 TypeScript 的 AgentHandle
    """
    agent_id: str
    name: str
    agent_type: str
    status: str = "running"  # 'running', 'stopped', 'failed'
    execution_mode: AgentExecutionMode = AgentExecutionMode.IN_PROCESS

    # 消息队列 (进程内)
    message_queue: asyncio.Queue = field(default_factory=asyncio.Queue)

    # Mailbox 路径 (外部执行)
    mailbox_path: Optional[str] = None

    # 进程引用 (外部执行)
    process: Optional[asyncio.subprocess.Process] = None

    # 继续回调 (进程内)
    continue_callback: Optional[Callable] = None

    async def send_message(self, message: TeammateMessage) -> None:
        """发送消息到 Agent"""
        if self.execution_mode == AgentExecutionMode.IN_PROCESS:
            # 进程内，直接入队
            await self.message_queue.put(message)
            if self.continue_callback:
                self.continue_callback()
        else:
            # 外部执行，写入 Mailbox
            if self.mailbox_path:
                mailbox = Mailbox(self.mailbox_path)
                await mailbox.write(message)


# =============================================================================
# 5. 团队管理
# =============================================================================

@dataclass
class Team:
    """
    团队

    等价于 TypeScript 的 Team
    """
    name: str
    leader_id: str
    agents: Dict[str, AgentHandle] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    mailbox_dir: str = ""


class TeamManager:
    """
    团队管理器

    等价于 TypeScript 的 TeamManager
    """

    _instance: Optional['TeamManager'] = None
    _teams: Dict[str, Team] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'TeamManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def create_team(
        self,
        name: str,
        leader_id: str
    ) -> Team:
        """创建团队"""
        mailbox_dir = os.path.join(
            os.path.expanduser('~'),
            '.claude',
            'teams',
            name,
            'mailbox'
        )

        os.makedirs(mailbox_dir, exist_ok=True)

        team = Team(
            name=name,
            leader_id=leader_id,
            mailbox_dir=mailbox_dir
        )

        self._teams[name] = team
        return team

    def get_team(self, name: str) -> Optional[Team]:
        """获取团队"""
        return self._teams.get(name)

    async def add_agent(
        self,
        team: Team,
        agent: AgentHandle
    ) -> None:
        """添加 Agent 到团队"""
        team.agents[agent.name] = agent

        # 创建 mailbox 子目录
        agent_mailbox_dir = os.path.join(team.mailbox_dir, agent.name)
        os.makedirs(agent_mailbox_dir, exist_ok=True)

        if agent.mailbox_path is None:
            agent.mailbox_path = agent_mailbox_dir

    async def remove_agent(
        self,
        team: Team,
        agent_name: str
    ) -> None:
        """从团队移除 Agent"""
        if agent_name in team.agents:
            del team.agents[agent_name]


# =============================================================================
# 6. Agent 间通信
# =============================================================================

class MessagingService:
    """
    消息服务

    等价于 TypeScript 的 deliverMessage()
    """

    def __init__(self, team_manager: TeamManager):
        self._team_manager = team_manager

    async def send_direct(
        self,
        team_name: str,
        to_agent: str,
        message: TeammateMessage
    ) -> None:
        """直接发送消息"""
        team = self._team_manager.get_team(team_name)
        if not team:
            raise ValueError(f"Team not found: {team_name}")

        agent = team.agents.get(to_agent)
        if not agent:
            raise ValueError(f"Agent not found: {to_agent}")

        await agent.send_message(message)

    async def broadcast(
        self,
        team_name: str,
        message: TeammateMessage
    ) -> None:
        """广播消息"""
        team = self._team_manager.get_team(team_name)
        if not team:
            raise ValueError(f"Team not found: {team_name}")

        for agent in team.agents.values():
            await agent.send_message(message)


# =============================================================================
# 7. AsyncLocalStorage 上下文
# =============================================================================

# Python 的等价物是 contextvars
AgentContext = contextvars.ContextVar('agent_context', default=None)


@dataclass
class AgentContextData:
    """Agent 上下文数据"""
    agent_id: str
    agent_name: str
    team: Optional[Team] = None


def set_agent_context(data: AgentContextData) -> None:
    """设置 Agent 上下文"""
    AgentContext.set(data)


def get_agent_context() -> Optional[AgentContextData]:
    """获取 Agent 上下文"""
    return AgentContext.get()


# =============================================================================
# 8. Agent 执行器
# =============================================================================

class AgentRunner:
    """
    Agent 执行器

    等价于 TypeScript 的 runAgent()
    """

    def __init__(
        self,
        config: AgentDefinition,
        team_manager: Optional[TeamManager] = None
    ):
        self._config = config
        self._team_manager = team_manager or TeamManager.get_instance()
        self._abort_event: Optional[asyncio.Event] = None

    async def run(
        self,
        initial_messages: List[Message],
        context: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        运行 Agent

        等价于 TypeScript 的 runAgent()
        """
        # 1. 初始化
        agent_id = str(uuid.uuid4())
        agent_name = context.get('name', f"agent-{agent_id[:8]}")

        # 设置上下文
        set_agent_context(AgentContextData(
            agent_id=agent_id,
            agent_name=agent_name,
            team=context.get('team')
        ))

        self._abort_event = asyncio.Event()

        # 2. 执行查询循环
        messages = list(initial_messages)
        turn_count = 0
        max_turns = self._config.max_turns or 100

        while turn_count < max_turns:
            # 检查中止
            if self._abort_event.is_set():
                break

            # 3. 调用模型
            response = await self._call_model(messages)

            # 4. 处理响应
            for event in response:
                yield event

                # 处理工具调用
                if event.get('type') == 'tool_use':
                    result = await self._execute_tool(event)
                    messages.append(Message(
                        role='user',
                        content=[{
                            'type': 'tool_result',
                            'tool_use_id': event.get('id'),
                            'content': result
                        }]
                    ))

            turn_count += 1

        # 5. 清理
        self._cleanup()

    async def _call_model(
        self,
        messages: List[Message]
    ) -> List[Dict[str, Any]]:
        """调用模型 (简化实现)"""
        # 简化实现
        await asyncio.sleep(0.1)

        return [{
            'type': 'assistant',
            'content': [{'type': 'text', 'text': 'Response from model'}]
        }]

    async def _execute_tool(self, event: Dict[str, Any]) -> str:
        """执行工具 (简化实现)"""
        tool_name = event.get('name', 'unknown')
        return f"Result from {tool_name}"

    def _cleanup(self) -> None:
        """清理"""
        pass

    def abort(self) -> None:
        """中止 Agent"""
        if self._abort_event:
            self._abort_event.set()


# =============================================================================
# 9. Agent 派生
# =============================================================================

class AgentSpawner:
    """
    Agent 派生器

    等价于 TypeScript 的 spawnAgent()
    """

    def __init__(
        self,
        team_manager: Optional[TeamManager] = None
    ):
        self._team_manager = team_manager or TeamManager.get_instance()

    async def spawn_in_process(
        self,
        config: AgentDefinition,
        team: Team,
        options: Dict[str, Any]
    ) -> AgentHandle:
        """
        进程内派生

        等价于 TypeScript 的 spawnInProcess()
        """
        agent_id = str(uuid.uuid4())
        agent_name = options.get('name', f"agent-{agent_id[:8]}")

        handle = AgentHandle(
            agent_id=agent_id,
            name=agent_name,
            agent_type=config.agent_type,
            status="running",
            execution_mode=AgentExecutionMode.IN_PROCESS
        )

        # 添加到团队
        await self._team_manager.add_agent(team, handle)

        # 在异步上下文中运行
        asyncio.create_task(self._run_in_context(handle, config, options))

        return handle

    async def _run_in_context(
        self,
        handle: AgentHandle,
        config: AgentDefinition,
        options: Dict[str, Any]
    ) -> None:
        """在上下文中运行"""
        context_data = AgentContextData(
            agent_id=handle.agent_id,
            agent_name=handle.name,
            team=options.get('team')
        )

        async def run_with_context():
            AgentContext.set(context_data)
            runner = AgentRunner(config)
            async for _ in runner.run([], options):
                pass

        try:
            await run_with_context()
        except Exception as e:
            handle.status = "failed"
        finally:
            handle.status = "stopped"

    async def spawn_tmux(
        self,
        config: AgentDefinition,
        team: Team,
        options: Dict[str, Any]
    ) -> AgentHandle:
        """
        Tmux 分屏派生

        等价于 TypeScript 的 spawnTmuxPane()
        """
        agent_id = str(uuid.uuid4())
        agent_name = options.get('name', f"agent-{agent_id[:8]}")

        # 创建 tmux pane
        proc = await asyncio.create_subprocess_shell(
            f'tmux split-window -h -t {team.name}:0',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.wait()

        # 构建 mailbox 路径
        mailbox_path = os.path.join(team.mailbox_dir, agent_name)

        handle = AgentHandle(
            agent_id=agent_id,
            name=agent_name,
            agent_type=config.agent_type,
            status="running",
            execution_mode=AgentExecutionMode.TMUX_SPLIT,
            mailbox_path=mailbox_path
        )

        await self._team_manager.add_agent(team, handle)

        return handle

    async def spawn_worktree(
        self,
        config: AgentDefinition,
        team: Team,
        options: Dict[str, Any]
    ) -> AgentHandle:
        """
        Worktree 派生

        等价于 TypeScript 的 spawnWorktree()
        """
        agent_id = str(uuid.uuid4())
        agent_name = options.get('name', f"agent-{agent_id[:8]}")
        cwd = options.get('cwd', os.getcwd())

        # 创建 worktree
        worktree_path = os.path.join(cwd, '.claude', 'worktrees', agent_id)

        proc = await asyncio.create_subprocess_exec(
            'git', 'worktree', 'add',
            '-b', f'agent-{agent_id}',
            worktree_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.wait()

        # 构建 CLI 命令
        cli_args = self._build_cli_args(options)

        # 派生进程
        process = await asyncio.create_subprocess_exec(
            'claude',
            *cli_args,
            cwd=worktree_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        handle = AgentHandle(
            agent_id=agent_id,
            name=agent_name,
            agent_type=config.agent_type,
            status="running",
            execution_mode=AgentExecutionMode.WORKTREE,
            process=process
        )

        await self._team_manager.add_agent(team, handle)

        return handle

    def _build_cli_args(self, options: Dict[str, Any]) -> List[str]:
        """构建 CLI 参数"""
        args = [
            '--agent-id', options.get('agent_id', ''),
            '--session-id', options.get('session_id', ''),
        ]

        if options.get('verbose'):
            args.append('--verbose')

        return args


# =============================================================================
# 10. 内置 Agent 定义
# =============================================================================

BUILTIN_AGENTS: List[AgentDefinition] = [
    AgentDefinition(
        agent_type='GeneralPurpose',
        description='General purpose agent for any task',
        tools=['Read', 'Edit', 'Write', 'Bash', 'Glob', 'Grep'],
        thinking_enabled=True,
        max_turns=50,
    ),

    AgentDefinition(
        agent_type='Explore',
        description='Explore and understand a codebase',
        tools=['Read', 'Glob', 'Grep', 'Bash'],
        omit_claude_md=True,
        max_turns=30,
    ),

    AgentDefinition(
        agent_type='Plan',
        description='Create a plan for implementing a feature or fix',
        tools=['Read', 'Glob', 'Grep'],
        omit_claude_md=True,
        max_turns=10,
    ),

    AgentDefinition(
        agent_type='Verification',
        description='Verify changes and run tests',
        tools=['Bash', 'Read'],
        max_turns=20,
    ),

    AgentDefinition(
        agent_type='CodeReview',
        description='Review code changes',
        tools=['Bash', 'Read', 'Glob', 'Grep'],
        allowed_tools=['Bash(git diff:*)', 'Bash(git log:*)'],
        max_turns=30,
    ),
]


# =============================================================================
# 11. 示例用法
# =============================================================================

async def main():
    """示例用法"""

    # 1. 创建团队管理器
    team_manager = TeamManager.get_instance()

    # 2. 创建团队
    team = await team_manager.create_team(
        name="my-team",
        leader_id="leader-1"
    )

    print(f"Created team: {team.name}")

    # 3. 创建 Agent 定义
    config = AgentDefinition(
        agent_type='GeneralPurpose',
        description='Test agent',
        max_turns=10
    )

    # 4. 派生 Agent
    spawner = AgentSpawner(team_manager)

    handle = await spawner.spawn_in_process(
        config=config,
        team=team,
        options={
            'name': 'worker-1',
            'team': team
        }
    )

    print(f"Spawned agent: {handle.name} ({handle.agent_id})")

    # 5. Agent 间通信
    messaging = MessagingService(team_manager)

    message = TeammateMessage(
        id=str(uuid.uuid4()),
        from_agent='leader',
        to='worker-1',
        type='message',
        content='Hello, worker!'
    )

    await messaging.send_direct(
        team_name=team.name,
        to_agent='worker-1',
        message=message
    )

    print(f"Sent message to {message.to}")

    # 6. 广播
    broadcast_msg = TeammateMessage(
        id=str(uuid.uuid4()),
        from_agent='leader',
        to='*',
        type='message',
        content='Broadcast message'
    )

    await messaging.broadcast(
        team_name=team.name,
        message=broadcast_msg
    )

    print("Broadcast sent")

    # 7. Mailbox 读取
    if handle.mailbox_path:
        mailbox = Mailbox(handle.mailbox_path)
        await mailbox.write(message)
        messages = await mailbox.read_all()
        print(f"Mailbox messages: {len(messages)}")


if __name__ == "__main__":
    asyncio.run(main())
