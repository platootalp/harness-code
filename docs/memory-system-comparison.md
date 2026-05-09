# 记忆系统对比：Claude-Code vs Hermes-Agent

> 对比维度：结构、记忆类型、记忆生命周期（增删改查）、存什么记忆、存到哪里、为什么需要存下来、如何存的

---

## 一、结构（Architecture）

| 维度 | Claude-Code | Hermes-Agent |
|------|-------------|--------------|
| **整体架构** | 文件系统为中心的目录式记忆（memdir），辅以 SessionMemory + extractMemories + autoDream + teamMemorySync 四大服务 | 多层混合架构：文件记忆（MEMORY.md/USER.md）+ SQLite 会话存储 + FTS5 搜索 + 可插拔外部 Provider + 技能系统 + 上下文压缩器 |
| **核心模块** | `memdir/`（记忆目录核心）、`SessionMemory/`（会话记忆）、`extractMemories/`（后台提取）、`autoDream/`（定期整合）、`teamMemorySync/`（团队同步） | `memory_tool.py`（内置记忆）、`memory_manager.py`（编排器）、`memory_provider.py`（插件抽象基类）、`context_compressor.py`（上下文压缩）、`session_search_tool.py`（会话搜索）、`skill_manager_tool.py`（技能/过程记忆） |
| **扩展机制** | 团队记忆子目录（team/），通过 teamMemorySync 服务同步 | 可插拔 MemoryProvider 抽象基类，支持 Honcho、Hindsight、Mem0 等外部记忆服务，最多接入 1 个外部 Provider |
| **编排方式** | 各服务独立运行：extractMemories 在查询循环结束时后台执行，autoDream 按时间/会话门控定期触发，teamMemorySync 通过文件 watcher 监听 | MemoryManager 统一编排：路由工具调用、收集系统提示块、管理 prefetch/recall、生命周期钩子（on_turn_start / on_session_end / on_pre_compress / on_memory_write / on_delegation） |
| **上下文压缩** | `compact/` 服务：包含 sessionMemoryCompact.ts，在上下文溢出时压缩会话记忆 | `context_compressor.py`：有损摘要压缩，保护头部+尾部，迭代式摘要更新，防抖保护（连续 2 次压缩节省 <10% 则跳过），支持 focus topic 引导压缩方向 |
| **架构风格** | **目录式文件系统**：记忆 = 目录中的 Markdown 文件集合，MEMORY.md 作为索引 | **分层混合式**：内置文件记忆 + SQLite 结构化存储 + 可插拔外部服务，MemoryManager 作为统一门面 |

---

## 二、记忆类型（Memory Types）

| 记忆类型 | Claude-Code | Hermes-Agent |
|----------|-------------|--------------|
| **用户偏好/画像** | `user` 类型 — 用户的角色、目标、偏好、知识（始终私有） | `USER.md` — 用户档案，字符上限 1375，存储用户画像信息 |
| **反馈/指导** | `feedback` 类型 — 关于如何开展工作的指导（私有或团队共享） | 无独立类型，但可通过 Skills 的 SKILL.md 存储工作指导 |
| **项目/工作** | `project` 类型 — 正在进行的工作、目标、事件（偏向团队共享） | `MEMORY.md` — Agent 的个人笔记，字符上限 2200，存储项目上下文 |
| **引用/指针** | `reference` 类型 — 指向外部系统的指针（通常团队共享） | 无独立类型 |
| **会话记忆** | `SessionMemory` — 会话作用域内的临时记忆，会话结束时可选择持久化到 memdir | `hermes_state.py` — SQLite SessionDB（WAL 模式 + FTS5 全文索引），存储完整会话轨迹 |
| **过程记忆（Procedural）** | 无独立类型（通过 CLAUDE.md / .claude/ 配置文件间接实现） | `skill_manager_tool.py` — 技能系统，存储"如何做某类任务"的过程知识，目录式组织 `~/.hermes/skills/<name>/SKILL.md` |
| **团队记忆** | `team/` 子目录 + teamMemorySync 服务 + secret scanner | 无内置团队记忆（可通过外部 Provider 如 Honcho 实现） |
| **外部记忆** | 无插件机制 | `memory_provider.py` — 可插拔抽象基类，支持 Honcho、Hindsight、Mem0 等外部服务 |
| **类型数量** | **4 种**（user, feedback, project, reference）+ 会话记忆 + 团队记忆 | **3 种内置**（MEMORY.md, USER.md, Skills）+ 会话存储 + 可插拔外部 |

---

## 三、记忆生命周期（增删改查 / CRUD）

### 3.1 创建（Create）

| 操作 | Claude-Code | Hermes-Agent |
|------|-------------|--------------|
| **触发方式** | Agent 在对话中主动写入；extractMemories 后台 Agent 在查询循环结束时自动提取 | 用户/Agent 通过 memory_tool 调用 `add` 操作；Skill 通过 skill_manager_tool 调用 `create` |
| **写入格式** | Markdown 文件 + YAML frontmatter（name, description, type） | `§` 分隔的条目追加到 MEMORY.md / USER.md；Skills 写入 SKILL.md + 支撑文件 |
| **索引更新** | 写入后同步更新 MEMORY.md 索引文件 | 无独立索引；MEMORY.md 本身即存储（append-only 追加） |
| **安全检查** | teamMemorySync 包含 secret scanner，防止敏感信息泄露 | memory_tool 在接受写入前进行注入/泄露模式扫描；skill_manager_tool 在创建/编辑时扫描 |
| **并发安全** | 依赖文件系统原子性 | fcntl（Unix）/ msvcrt（Windows）文件锁 + 原子写入（temp-file + os.replace()） |

### 3.2 读取（Read）

| 操作 | Claude-Code | Hermes-Agent |
|------|-------------|--------------|
| **加载时机** | 会话启动时加载 MEMORY.md 到系统提示 | 会话启动时加载 MEMORY.md + USER.md 到 `_system_prompt_snapshot`（冻结快照） |
| **相关性筛选** | `findRelevantMemories` 使用 Sonnet 侧查询，从全部记忆中选出 top 5 最相关记忆 | 无内置相关性筛选；session_search_tool 通过 FTS5 关键词搜索 + LLM 摘要筛选历史会话 |
| **容量限制** | MEMORY.md 上限 200 行 / 25KB | MEMORY.md 上限 2200 字符；USER.md 上限 1375 字符（模型无关的硬限制） |
| **去重** | 无明确去重机制 | 读取时去重（deduplication on read） |
| **前缀缓存** | 无特殊处理 | **冻结快照模式**：会话启动后写入的记忆立即落盘但 **不更新系统提示**，保护 Anthropic prefix cache |

### 3.3 更新（Update）

| 操作 | Claude-Code | Hermes-Agent |
|------|-------------|--------------|
| **Agent 编辑** | Agent 直接编辑已有记忆 Markdown 文件 | memory_tool 的 `replace` 操作：子串匹配替换（非 ID 定位） |
| **自动提取** | extractMemories 后台 Agent 在每次查询循环结束时运行，提取新记忆 | 无自动提取；依赖用户/Agent 主动调用 |
| **定期整合** | autoDream 服务：时间门控 + 会话门控 + 锁机制，跨会话整合记忆 | 无内置定期整合 |
| **Kairos 模式** | 助手模式使用追加式日志文件，夜间 /dream 蒸馏日志 | 无对应机制 |
| **Skills 更新** | 无 | skill_manager_tool 的 `edit` / `patch` 操作，自动清除技能系统提示缓存 |

### 3.4 删除（Delete）

| 操作 | Claude-Code | Hermes-Agent |
|------|-------------|--------------|
| **Agent 删除** | Agent 主动删除过时/失效的记忆文件 | memory_tool 的 `remove` 操作：子串匹配删除 |
| **Skills 删除** | 无 | skill_manager_tool 的 `delete` 操作 |
| **自动清理** | 无明确自动清理（依赖 Agent 判断） | 无明确自动清理 |

---

## 四、存什么记忆（What to Store）

| 类别 | Claude-Code | Hermes-Agent |
|------|-------------|--------------|
| **用户画像** | ✅ `user` 类型：角色、目标、偏好、知识 | ✅ USER.md：用户档案信息 |
| **工作指导** | ✅ `feedback` 类型：如何开展工作的指导 | ⚠️ 通过 Skills 间接存储 |
| **项目上下文** | ✅ `project` 类型：进行中的工作、目标、事件 | ✅ MEMORY.md：Agent 个人笔记 |
| **外部引用** | ✅ `reference` 类型：指向外部系统的指针 | ❌ 无独立类型 |
| **过程知识** | ❌ 不存（依赖 CLAUDE.md 等配置文件） | ✅ Skills：如何做某类任务的过程知识 |
| **会话轨迹** | ⚠️ SessionMemory（临时，可选持久化） | ✅ SQLite SessionDB：完整会话轨迹 + FTS5 索引 |
| **团队知识** | ✅ team/ 子目录：团队共享记忆 | ❌ 无内置（可通过外部 Provider） |
| **明确不存** | 代码模式、架构、git 历史、文件结构、调试方案、CLAUDE.md 中已有的内容、临时任务细节 | 注入/泄露模式的内容被安全扫描拦截 |

---

## 五、存到哪里（Where to Store）

| 存储位置 | Claude-Code | Hermes-Agent |
|----------|-------------|--------------|
| **主存储** | `~/.claude/projects/<sanitized-git-root>/memory/` 目录下的 Markdown 文件 | `MEMORY.md` + `USER.md`（项目根目录或 ~/.hermes/） |
| **索引文件** | `MEMORY.md` — 所有记忆的索引文件，加载到系统提示 | 无独立索引；MEMORY.md 本身即存储 |
| **团队存储** | `memory/team/` 子目录 | 无内置团队存储 |
| **会话存储** | 内存中（SessionMemory），可选持久化到 memdir | SQLite 数据库（WAL 模式 + FTS5 全文索引） |
| **技能存储** | 无 | `~/.hermes/skills/<name>/SKILL.md` + 支撑文件目录 |
| **外部存储** | 无 | 可插拔 Provider（Honcho、Mem0 等远程服务） |
| **存储格式** | Markdown + YAML frontmatter | Markdown（§ 分隔条目）；SQLite（结构化）；SKILL.md（技能描述） |
| **文件组织** | 每条记忆 = 独立文件（含 frontmatter 元数据） | 单文件追加式（MEMORY.md / USER.md）；目录式（Skills） |

---

## 六、为什么需要存下来（Why Store）

| 动机 | Claude-Code | Hermes-Agent |
|------|-------------|--------------|
| **跨会话连续性** | ✅ 核心动机：用户偏好、项目上下文跨会话保持 | ✅ 核心动机：MEMORY.md + USER.md 跨会话保持；SQLite 存储历史会话供搜索 |
| **团队协作** | ✅ feedback/project/reference 类型可团队共享，teamMemorySync 同步 | ⚠️ 无内置团队记忆，依赖外部 Provider |
| **工作指导传承** | ✅ feedback 类型：关于如何工作的指导跨会话/跨人传递 | ✅ Skills：过程知识可复用、可共享 |
| **上下文效率** | ✅ findRelevantMemories 只加载 top 5 相关记忆，节省 token | ✅ 冻结快照保护 prefix cache；上下文压缩器在有损摘要中保留关键信息 |
| **避免重复劳动** | ✅ 记住用户偏好和项目决策，避免每次重新询问 | ✅ 记住用户画像和项目笔记；Skills 避免重复摸索任务方法 |
| **历史回溯** | ⚠️ SessionMemory 可回溯当前会话；跨会话搜索依赖 autoDream 整合 | ✅ session_search_tool：FTS5 搜索历史会话 + LLM 摘要，支持关键词搜索和最近会话浏览 |
| **安全合规** | ✅ secret scanner 防止敏感信息进入团队记忆 | ✅ 注入/泄露扫描防止恶意内容写入记忆 |

---

## 七、如何存的（How to Store）

| 机制 | Claude-Code | Hermes-Agent |
|------|-------------|--------------|
| **写入方式** | Agent 创建 Markdown 文件 + YAML frontmatter；extractMemories 后台 Agent 自动提取 | `§` 分隔符追加条目到 MEMORY.md / USER.md；原子写入（temp-file + os.replace()） |
| **元数据** | YAML frontmatter：name, description, type（user/feedback/project/reference） | 无 frontmatter；条目以 § 分隔，纯文本追加 |
| **索引机制** | MEMORY.md 索引文件（所有记忆的摘要列表，加载到系统提示） | 无独立索引；SQLite FTS5 作为会话搜索的索引 |
| **相关性检索** | findRelevantMemories：Sonnet 侧查询，从全部记忆中选 top 5 | session_search_tool：FTS5 关键词搜索 → LLM 摘要匹配会话 |
| **容量控制** | MEMORY.md 上限 200 行 / 25KB；超出时 Agent 需整理 | 硬字符限制：MEMORY=2200, USER=1375；上下文压缩器在溢出时有损摘要 |
| **缓存优化** | 无特殊缓存机制 | 冻结快照（_system_prompt_snapshot）：写入即落盘但不更新系统提示，保护 prefix cache |
| **并发安全** | 依赖文件系统 | 文件锁（fcntl/msvcrt）+ 原子写入 |
| **自动维护** | extractMemories（查询循环结束提取）+ autoDream（定期跨会话整合）+ teamMemorySync（团队同步 watcher） | 无自动提取/整合；依赖用户/Agent 主动管理 |
| **压缩策略** | sessionMemoryCompact：会话记忆压缩 | context_compressor：有损摘要（保护头尾）+ 迭代摘要 + 防抖 + focus topic + 工具对完整性 + token 预算尾保护 |
| **安全扫描** | teamMemorySync 的 secret scanner | memory_tool + skill_manager_tool 的注入/泄露模式扫描 |
| **Kairos 模式** | 追加式日志 + 夜间 /dream 蒸馏 | 无对应机制 |

---

## 总结对比

| 特征 | Claude-Code | Hermes-Agent |
|------|-------------|--------------|
| **架构哲学** | 目录式文件系统，每条记忆独立文件 | 分层混合式，单文件追加 + SQLite + 可插拔外部 |
| **记忆粒度** | 细粒度（每条记忆 = 一个文件） | 粗粒度（单文件追加，§ 分隔） |
| **类型系统** | 4 种显式类型 + 团队子类型 | 3 种内置 + 可插拔扩展 |
| **自动化程度** | 高（自动提取 + 定期整合 + 团队同步） | 低（依赖主动调用，无自动提取/整合） |
| **搜索能力** | LLM 相关性筛选（top 5） | FTS5 全文搜索 + LLM 摘要 |
| **缓存优化** | 无 | 冻结快照保护 prefix cache |
| **扩展性** | 低（无插件机制） | 高（MemoryProvider 抽象基类，支持外部服务） |
| **并发安全** | 基础（依赖文件系统） | 完善（文件锁 + 原子写入） |
| **团队协作** | 内置（team/ + sync + scanner） | 外部（依赖 Provider） |
| **过程记忆** | 无 | Skills 系统 |
| **历史回溯** | 弱（依赖 autoDream 整合） | 强（FTS5 + LLM 搜索历史会话） |
| **压缩策略** | 基础会话记忆压缩 | 高级有损摘要（多轮迭代 + 防抖 + focus topic） |
