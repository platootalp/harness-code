# OpenHarness 项目简历

## 项目背景

为构建可扩展的开源 AI Agent 基础设施，实现 Claude Code 的 Python 移植版 OpenHarness，支持工具调用、技能加载、持久记忆与多智能体协同；作为通用 Agent 运行时，支撑编码、调试与自动化完整闭环。

## 技术栈

Python + Pydantic + Typer + Rich + Anthropic SDK + OpenAI SDK + MCP SDK + httpx + WebSockets + React/Ink

## 核心工作

### 多 Agent 编排

- 构建 Orchestrator-Worker 编排层，Orchestrator 会话级常驻负责意图理解与任务分配，协同五类专家 Agent（Explorer/Planner/Coder/Tester/Reviewer），只读任务并行调度、写任务串行避免冲突
- 设计 in-process / subprocess 双重 spawn 机制：in-process 基于 ContextVar 任务级隔离、零进程开销；subprocess 进程级隔离、更安全；BackendRegistry 自动检测并优先级降级
- 实现文件邮箱通信（原子写入 + 文件锁），Task-Notification XML 信封回传 Worker 结果，Leader-Worker 权限请求流（只读工具自动放行、写操作需审批）
- Team 生命周期持久化 + Git Worktree 隔离各 Agent 工作目录，会话退出自动清理资源

### 任务体系构建

- Planner Agent 拆解任务并构建依赖图，Reviewer Agent 四维度校验（完整性/原子性/独立性/可验证性），不通过则回退修订
- 基于 DAG 拓扑排序确定执行顺序，无依赖任务并行调度；支持前台/后台双模式，后台涵盖 shell 命令与 Agent 子任务
- BackgroundTaskManager 管理完整生命周期（create → run → stop → complete），TODOList 可视化追踪状态，CompletionListener 驱动下游逻辑
- file-system 持久化任务记录与输出日志，Agent 任务断线自动重启，优雅终止（SIGTERM → SIGKILL 降级）

### 分层上下文

- 三层上下文架构：L1 会话层（系统提示词/Tool 描述/Skills 元数据/AGENT.md/MEMORY.md）+ L2 任务层（User Message/TODOList/Task/关键决策）+ L3 工作层（工具结果/LLM thinking/检索内容），按重要性分级组织
- 上下文生命周期流水线：Gather（预加载 + JIT 即时检索 + RAG 三重检索）→ Compact（按层级渐进压缩）→ Extract（主动 + 定时 + 事件触发，提取跨会话长期记忆）
- 多层渐进压缩：工具压缩（清除 L3 旧工具结果）→ 上下文折叠（L2+L3 超长文本截断）→ LLM 摘要压缩（手动/自动触发），CompactAttachment 跨压缩边界携带关键状态
- 5 类长期记忆提取（用户偏好/项目规范/反馈处理/外部系统指针/情景日志），持久化为 Markdown，跨会话语义召回

### 能力即工具

- 42+ 内置工具覆盖全链路（Bash/Glob/Grep/LSP/FileXxx/TaskXxx/Agent/Cron/Memory），McpToolAdapter 适配 MCP Server 工具（stdio + HTTP 双传输）
- 延迟动态加载工具 Schema（按需注册减少 Token 占用），三级容错（重试 → 降级 → LLM Reflect）；PreToolUse/PostToolUse 钩子支持插件注入安全策略
- Skills 三层集成：Built-in Skills + Disk Skills（固定目录加载）+ Remote Skills（动态发现），条件技能激活与渐进式加载

### IM Channel 多平台适配

- BaseChannel 抽象 + MessageBus 异步总线，10 平台适配（Telegram/Discord/Slack/Feishu/Email/WhatsApp/Matrix/QQ/DingTalk/Mochat）
- ChannelBridge 桥接 Chat ↔ QueryEngine，session_key 保持多轮对话，各平台深度适配（Feishu 富文本卡片/Slack Thread/Telegram 语音转写/Matrix E2EE）

## 项目成果

42+ 内置工具 | 10 IM 平台 | 5 类专家 Agent 编排 | 3 层上下文 + Gather-Compact-Extract 流水线 | 三级渐进压缩 | 5 类长期记忆 | DAG 任务调度
