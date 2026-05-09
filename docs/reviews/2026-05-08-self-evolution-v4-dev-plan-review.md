# 方案评审报告

## 元信息

| 字段 | 填写 |
| --- | --- |
| 被评文档 | docs/superpowers/plans/2026-05-08-self-evolution-v4.md |
| 被评版本 / 提交 | 未钉版本 |
| 评审日期 | 2026-05-08 |
| 评审者 | 主编排者（合并 C/X/S 三子代理评审） |
| 本报告归档路径 | docs/reviews/2026-05-08-self-evolution-v4-dev-plan-review.md |

---

## 被评方案摘要

| 项 | 填写 |
| --- | --- |
| **要解决的核心问题** | 实现 self-evolution 插件 v4：用 AgentHook 在会话 Stop 时自动审查对话、通过插件自带的 evolve-skill-writer 元技能生成 ~/.claude/skills/ 下的 SKILL.md 文件 |
| **非目标 / 明确不做** | YAML 硬验证、description 优化器、v1 自动化测试的交互式技能开发、事实记忆/情景记忆 |
| **交付形态** | Claude-Code 插件（agents/commands/hooks/skills 四通道）+ 测试脚本 + 文档 |
| **关键外部依赖** | Claude-Code v1.x with plugin marketplace、jq（必需）、POSIX 兼容 shell |
| **安全风险档位** | 高 — 涉及自动化写入用户目录、全局 PreToolUse hook 拦截所有 Write/Edit/MultiEdit、LLM 自动生成内容的安全扫描 |

---

## 发现项

| ID | 级别 | 位置 | 现象 | 触发条件 | 影响 | 建议 | 维度 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | 严重 | Task 4: security-scan.sh + Task 8: evolve-skill-writer/SKILL.md | prompt injection 检测模式可被编码绕过，且元技能 Quality Checklist 无嵌套检查 | 恶意用户诱导 reviewer 生成包含编码后的 prompt 注入的 SKILL.md | security-scan.sh 的 grep 模式无法检测到 base64/十六进制编码的攻击；元技能已"清理"危险内容但可能包含 subtle 的 prompt 注入模式 | 在元技能 Quality Checklist 中增加"无 prompt-injection 嵌套检查"项；在 security-scan.sh 中增加解码检测（至少 base64） | 安全性 |
| F2 | 高 | Task 5: hooks.json Stop[1] prompt | reviewer 决策逻辑无合理性验证，可能生成大量垃圾或有害技能 | 恶意用户构造诱导性的对话内容 | 安全 gate 只扫描内容，但不验证 CREATE/UPDATE 决策本身的合理性，可能生成无用的垃圾技能 | 在 Stop[1] prompt 中增加"合理性检查"步骤，要求 reviewer 说明为何该 workflow 应被捕获为 skill，并验证决策逻辑是否与 spec 契约一致 | 安全性 |
| F3 | 高 | Task 4: security-scan.sh | dangerous bash 检测模式存在误报和漏报 | 正常文档包含"rm -rf temp/"或用户意图的 eval 用法 | 阻止合法技能内容；复杂的 bash obfuscation 可能漏报 | 添加上下文感知检测（如检查是否在代码块示例中），并扩展危险模式列表覆盖更多 obfuscation 形式 | 安全性 |
| F4 | 高 | Task 4: security-scan.sh | secret leak 检测模式可能误报和漏报 | 正常文档包含类似 token 格式的示例文本或脱敏后的 API key | 误报阻止合法内容；非标准格式的 secret 可能漏报 | 实现 context-aware 检测，区分示例文本与真实 secret；允许白名单模式用于已知安全的示例 | 安全性 |
| F5 | 高 | Task 8: evolve-skill-writer/SKILL.md | 元技能未验证 category 前缀白名单 | 用户提出非白名单 category（如"evil"）或拼写错误（如"debugg"） | 生成违反规范的 skill，或导致无法被发现/调用的 skill | 在元技能 Quality Checklist 中强制验证 category 必须在 8 个白名单之一中（debug/refactor/test/deploy/data/web/cli/meta） | 安全性 |
| F6 | 高 | Task 12: stop-gate.sh | POSIX 锁超时设置为 5s，未考虑高并发死锁处理 | 多个并发会话同时触发 Stop hook | 进程持有锁超过 5s 时其他进程失败退出，可能导致触发标志丢失 | 实现指数退避重试机制，或增加锁超时日志以便调试 | 安全性 |
| F7 | 高 | 全局：监控与日志缺失 | 插件执行过程中缺少安全事件日志和告警机制 | security-scan.sh 拦截事件、异常 reviewer 决策、hook 超时等 | 无法事后审计安全事件，无法及时发现异常行为 | 增加日志机制：记录所有安全扫描拦截事件（时间、路径、拦截原因）、所有 reviewer 决策（CREATE/UPDATE/SKIP 及理由）、hook 执行时长 | 可验证性 |
| F8 | 高 | Task 0 Step 1 | 目录结构命令使用硬编码绝对路径 | 在其他机器或不同用户执行 | 步骤直接失败，无法继续开始 | 将硬编码绝对路径改为使用变量或文档中说明需要调整 | 可执行性 |
| F9 | 高 | Task 1 Step 2 + Task 15 | Day 1 验证完全依赖人工手动操作且无明确验收自动化 | Day 1 执行时 | 验证结果可能不一致，难以复现 | 至少提供脚本化的验证脚本，输出标准化的 JSON 结果供解析 | 可执行性 |
| F10 | 高 | Task 0 前缺失 | 缺少环境前置条件检查清单 | 开始实施前 | 开发者可能遇到依赖缺失导致的运行时错误 | 在 Task 0 前添加独立的环境验证步骤，检查 jq、Claude-Code 版本、插件路径等 | 可执行性 |
| F11 | 高 | Task 5 Step 4 | Timeout 累计验证未包含所有 Stop hooks | 执行验证脚本时 | 验证可能通过但实际超时仍超标 | 验证 jq 命令包含所有三个 Stop hooks 的 timeout 值（3 + 90 + 2 = 95） | 正确性 |
| F12 | 高 | Task 15 Step 2 | Day 1 验证结论记录步骤不完整 | SkillTool 验证失败 | 无法正确记录决策结果，导致后续步骤执行错误路径 | 明确如何根据测试结果选择并记录决策（Path A: SkillTool 可用 / Path B: F1 fallback） | 完整性 |
| F13 | 高 | Test scripts: Hook 输入格式不一致 | 测试中 hook 输入格式与脚本期望不一致 | 运行测试脚本 | stop-gate.sh 可能无法正确解析 session_id | 统一所有测试中的 hook 输入格式，确保包含 `session_id` 字段 | 一致性 |
| F14 | 中 | Task 8: evolve-skill-writer/SKILL.md | 元技能未验证路径白名单一致性 | 生成的 SKILL.md 包含非 ~/.claude/skills/ 路径引用 | 元技能声称遵循 Quality Checklist 但实际可能输出违反安全约束的内容 | 在元技能 Quality Checklist 中增加"生成的 SKILL.md 不得引用非白名单路径"检查项 | 安全性 |
| F15 | 中 | Task 10-12: 集成测试 | 缺少对真实 LLM reviewer 决策的红队测试 | 恶意用户构造诱导性的对话内容，使 reviewer 误判 workflow 为可复用 | 可能生成大量无用的垃圾技能，或被诱导生成恶意技能 | 补充红队测试用例：构造包含"看起来可复用但实际是一次性"的对话，验证 reviewer 是否能正确 SKIP | 安全性 |
| F16 | 中 | Task 16: 端到端验收 | 红队测试覆盖不足，缺少对并发、边界、失败场景的验证 | 多个并发会话同时触发技能生成、极端长度的 transcript、网络超时等 | 可能出现未预期的竞态条件或资源耗尽，导致系统不稳定 | 补充以下红队测试：并发场景（10+ 同时 Stop）、边界场景（超长内容、极端格式）、失败场景（reviewer 决策超时、元技能生成失败） | 可验证性 |
| F17 | 中 | Task 16: 端到端验收 | 缺少对"元技能 Quality Checklist"的独立验证 | 元技能自身声称遵循 Quality Checklist，但无外部验证机制 | 元技能可能生成不符合其自身声明标准的 SKILL.md，且无监督 | 在 Task 16 的验收中增加：对生成的每个 SKILL.md，由独立的验证脚本检查是否真正符合 Quality Checklist | 可验证性 |
| F18 | 中 | Task 4-5: security-scan.sh 和 hooks.json | 未定义 security-scan.sh 阻塞后的用户通知机制 | security-scan.sh 拦截某次 Write 操作 | 用户不知道技能生成失败的原因，可能误以为系统正常工作 | 在 Stop[1] prompt 中增加：如果 Write 返回 "BLOCKED:" 错误，必须在 StructuredOutput reason 中明确包含该错误信息 | 可验证性 |
| F19 | 中 | File Structure §1 vs Task 0-15 | 目录结构图与任务实施路径不一致 | 比较文档中的目录结构与实际任务步骤 | 实施时可能因路径不匹配导致文件创建位置错误 | 统一文档中所有路径引用：要么全部使用 `claude-self-evolution/` 前缀，要么在文档开头明确定义实施根目录别名 | 一致性 |
| F20 | 中 | Task 4 Step 1 vs Task 4 Step 2 | 红队 fixture 内容与单元测试期望不匹配 | 执行单元测试时 | 测试因找不到预期的危险模式而失败 | 确保 oversize fixture 在运行时通过 dd 生成 16KB 内容，而非占位符 | 正确性 |
| F21 | 中 | Task 8 Step 1 | 元技能 SKILL.md 内容未明确说明来源 | Task 8 实施时 | 可能与 spec §5.6 内容不完全一致 | Task 8 Step 1 应明确说明"内容引自 spec §5.6，需确保与 spec 完全一致" | 一致性 |
| F22 | 中 | Task 10 Step 1 | 集成测试 fixture 的 transcript_path 未验证 | 执行集成测试时 | stop-gate.sh 可能因为无效路径而失败 | 在 test_auto_path.sh 开始阶段验证 transcript_create.json 文件存在且可读 | 正确性 |
| F23 | 中 | 全文 | `$CLAUDE_PLUGIN_ROOT` 环境变量未定义说明 | 执行任何脚本时 | 脚本可能无法找到正确的工作目录 | 在文档开头明确 `$CLAUDE_PLUGIN_ROOT` 的默认值和设置方式 | 完整性 |
| F24 | 中 | Task 13 README.md | Reset 状态的操作需要手动修改数据目录路径 | 用户在不同机器或不同配置下 | rm 命令可能找不到文件或删除错误文件 | 提供脚本命令如 ${CLAUDE_PLUGIN_ROOT}/scripts/reset-state.sh 封装清理操作 | 可运维性 |
| F25 | 中 | 全文档 | 缺少升级流程说明 | 插件版本升级时 | 用户可能不知道如何安全升级，可能导致数据丢失 | 添加升级文档：备份 nudge-state.json、禁用旧插件、安装新插件、验证 | 可运维性 |
| F26 | 中 | 全文档 | 缺少监控和日志采集指引 | 系统运行时 | 难以诊断性能问题、失败频率 | 列出关键指标（stop hook duration、trigger count 等）和日志位置（~/.claude/logs/） | 可运维性 |
| F27 | 低 | Task 13 README.md | Install 指令路径与实际配置不匹配 | 用户按 README 安装插件 | 安装可能失败或插件未正确加载 | README 安装示例中的路径应使用实际目录结构，或说明路径替换 | 一致性 |
| F28 | 低 | Task 4 security-scan.sh | 危险模式正则可能在合法用例中误拦截 | 用户编写正常但含相关模式的代码 | 合法操作被错误阻止 | 在 README.md 中记录已知的误拦截案例和绕过方法 | 可运维性 |
| F29 | 低 | 全文档 | 缺少回滚（rollback）流程 | 新版本引入严重 bug 时 | 无法快速恢复到稳定版本 | 添加回滚文档：如何退回到上一个稳定版本、恢复配置 | 可运维性 |
| F30 | 低 | Task 16 | 10 个端到端场景未提供脚本化的准备和验证 | 验收时 | 人工执行可能遗漏场景或验收标准不一致 | 至少提供场景描述和验证 checklist，理想情况提供部分自动化验证脚本 | 可执行性 |

### 七维索引

| 维度 | 相关 F 编号 |
| --- | --- |
| 一致性 | F13, F19, F21, F27 |
| 正确性 | F11, F20, F22 |
| 完整性 | F12, F23 |
| 可执行性 | F8, F9, F10, F30 |
| 安全性 | F1, F2, F3, F4, F5, F6, F14, F15 |
| 可验证性 | F7, F16, F17, F18 |
| 可运维性 | F24, F25, F26, F28, F29 |

---

## 开放问题

| ID | 问题 | 是否阻塞结论 | 建议决策方 |
| --- | --- | --- | --- |
| Q1 | security-scan.sh 的 prompt injection 检测模式是否需要支持编码绕过的检测（如 base64）？ | 是（必须在实施前明确） | 方案作者 + 安全团队 |
| Q2 | 元技能 Quality Checklist 是否需要增加"路径白名单一致性"检查？ | 是（必须在实施前明确） | 方案作者 |
| Q3 | Task 16 的端到端验收是否需要扩展红队测试以覆盖并发、边界、失败场景？ | 是（必须在实施前明确） | 方案作者 + 测试团队 |
| Q4 | `$CLAUDE_PLUGIN_ROOT` 环境变量的默认值是多少？未设置时脚本如何处理？ | 否 | spec 作者 |
| Q5 | Day 1 SkillTool 验证的具体判定标准是什么？如何判断"reason contains HELLO_FROM_META_SKILL_OK"？ | 否 | spec author / plan author |

---

## 总体结论

### 决策摘要

| 项 | 填写 |
| --- | --- |
| **结论** | 修补后可实现 |
| **发现项最高级别** | 严重 |
| **是否阻塞实现或发布** | 是 — 需先修复 F1-F13 的严重和高级别问题 |
| **下一步必须先做的 1～3 件事** | 1. 修复 F1：在元技能 Quality Checklist 中增加 prompt-injection 嵌套检查，并在 security-scan.sh 中增加解码检测<br>2. 修复 F2：在 hooks.json Stop[1] prompt 中增加 reviewer 决策合理性检查<br>3. 补充 F7：增加安全事件日志机制，记录拦截事件、reviewer 决策、hook 执行时长 |

### 理由

本方案在**安全性**和**可验证性**方面存在一个**严重级别问题**（F1）和六个**高严重级别问题**（F2-F7）。F1 涉及 security-scan.sh 的 prompt injection 检测模式可被编码绕过，且元技能 Quality Checklist 缺少嵌套检查，这可能导致生成包含 subtle prompt injection 的 SKILL.md，在后续调用时执行任意指令。F2 指出 reviewer 决策逻辑无合理性验证，恶意用户可能诱导生成大量垃圾或有害技能。F6 指出 POSIX 锁超时处理不足，高并发下可能导致触发标志丢失。F7 指出安全事件日志和告警机制完全缺失，无法事后审计。

**评审覆盖**方面，虽然单元测试和集成测试覆盖了脚本链层面，但**缺少对真实 LLM reviewer 决策的红队测试**（F15、F16），且**监控与日志机制完全缺失**（F7），这使得安全事件难以事后审计和及时发现。

**开放问题**中，Q1（是否支持编码绕过检测）、Q2（是否增加路径白名单检查）、Q3（是否扩展红队测试）必须先拍板，否则无法验证系统的鲁棒性。

**双视角一致项：**
- C-F11（Hook 输入格式不一致）与 X-F4（hooks.json timeout 计算无自动化）都指向可执行性阻塞问题
- S-F1（prompt injection 可被绕过）与 C-F12（Day 1 验证结论不完整）都强调关键路径的正确性和完整性

**冲突项：**
- C-F12 认为 Day 1 验证结论记录步骤不完整，但 X-F2 认为可提供脚本化输出。建议合并：提供脚本化验证输出，同时明确结论记录和 fallback 路径的决策逻辑。

综上，方案架构合理，但**必须在实施前修复上述严重和高级别安全问题**，特别是加强元技能的自我验证、扩展 security-scan.sh 的检测能力、并完善测试覆盖和日志机制。修复后可进入实施阶段。

---

## 评审覆盖

### 阅读与假设

- **已读：**
  - 被评文档全文（2049 行）
  - 设计规格 `docs/superpowers/specs/2026-05-08-self-evolution-design-v4.md`（特别是 §5.6 和 §8.11）
  - 评审输出模板和检查清单模板
  - 相关系统文档：Hermes 自进化学习循环、Agent Hook 系统设计
- **未读或未验证：**
  - 实际脚本文件（只阅读了文档中提供的代码片段）
  - Claude-Code hook 引擎源码（仅阅读了 spec 中的引用片段）
  - 所有单元测试和集成测试的实际执行
  - PreToolUse 性能基准测试结果
- **假定：**
  - 假设设计规格 §5.6（元技能 SKILL.md）的内容是最终版本
  - 假设 `$CLAUDE_PLUGIN_ROOT` 是 Claude-Code 插件系统提供的环境变量
  - 假设 jq 工具在所有目标平台上可用
  - 假设 POSIX 锁机制在所有并发场景下可靠工作

### 证据与验证

| 类别 | 已有 | 缺口 |
| --- | --- | --- |
| 自动化测试 | - Task 2-4: 单元测试覆盖 nudge-state.sh、stop-gate.sh、security-scan.sh<br>- Task 10-12: 集成测试覆盖自动路径、手动路径、红队完整测试集（S1-S6）<br>- Task 14: 顶层 run_all.sh 测试运行器 | 缺少对真实 LLM reviewer 决策的自动化验证（F15、F16）<br>缺少对元技能 Quality Checklist 的独立验证（F17）<br>是否阻塞结论：是 |
| 手工验收 / 演练 | - Task 1: Day 1 SkillTool-in-AgentHook 可行性验证<br>- Task 16: 端到端验收（10 个场景的 5/5 自动 + 5/5 手动） | 缺少红队对手工验收的覆盖（F16：并发、边界、失败场景）<br>Day 1 验证无自动化输出（F9）<br>是否阻塞结论：是 |
| 监控与日志 | README.md 提及检查 `tengu_agent_stop_hook_duration_ms` | 完全缺失安全事件日志和告警机制（F7）<br>是否阻塞结论：是 |
| 回滚或恢复验证 | Task 2 Step 1 定义了 POSIX 锁机制用于并发控制；Task 3 定义了 --cleanup 模式用于清理 trigger flag | 缺少插件安装失败的回滚步骤<br>未定义元技能生成失败后的数据清理流程<br>是否阻塞结论：否（建议 v5 补充） |
| 红队 / 滥用面 | - Task 4: 5 类红队 fixture（prompt-injection、dangerous-bash、secret-leak、oversize）<br>- Task 12: 红队完整测试集（S1-S6） | 缺少对 LLM reviewer 决策逻辑的红队（F15）<br>缺少并发、边界、失败场景的红队（F16）<br>security-scan.sh 的编码绕过检测（F1）<br>是否阻塞结论：是 |

---

## 附录

### 主路径 / 失败路径要点

**主路径（成功场景）：**
1. 用户安装插件 → 插件加载 hooks.json
2. PostToolUse 触发 → nudge-state.sh 计数
3. Stop 触发 → stop-gate.sh 检查阈值 → Stop[1] AgentHook 调用 SkillTool('evolve-skill-writer')
4. 元技能生成 SKILL.md 内容 → 全局 PreToolUse security-scan.sh 扫描
5. Write 成功 → Stop[2] cleanup
6. 手动 /evolve-review → Task subagent → 调用元技能 → Write 被 PreToolUse 扫描 → 生成 SKILL.md

**失败路径：**
1. SkillTool 不可用 → Day 1 验证失败 → F1 fallback（Read 元技能路径）
2. Nudge 阈值未达 → Stop[0] 不创建 trigger flag → 跳过审查
3. Security scan 拦截 → Write 返回 exit 2 → reviewer 记录 "SKIPPED: hard_gate_blocked"
4. Stop[1] reviewer 决策 SKIP → 不调用元技能 → 不生成 SKILL.md
5. Stop[1] reviewer 超时 → AgentHook 被取消 → 触发标志可能残留 → 下次 Stop 时被覆盖
6. 元技能生成失败 → 返回 "ABORT: <reason>" → reviewer 记录 SKIP
7. Trigger flag cleanup 失败 → 下轮触发时 flag 已存在 → stop-gate.sh 覆盖旧 flag
8. POSIX 锁超时 → 进程失败退出 → 触发标志丢失

### 术语

| 术语 | 说明 |
| --- | --- |
| **AgentHook 子 agent** | Stop hook type:agent 触发的独立 agent 实例，负责审查对话并决策 CREATE/UPDATE/SKILL |
| **元技能（meta-skill）** | `evolve-skill-writer/SKILL.md`，插件自带的精简版 skill-creator，用于生成 SKILL.md 内容 |
| **三层硬门控** | L1 频率半硬（PostToolUse 计数 + Stop 触发标志） / L4 路径白名单（PreToolUse） / L5 内容扫描（PreToolUse） |
| **F1 fallback** | Day 1 验证失败后的回退方案：reviewer 使用 Read 工具直接读取元技能 SKILL.md 而非通过 SkillTool 调用 |
| **$CLAUDE_PLUGIN_ROOT** | 插件根目录的环境变量，由 Claude-Code 插件系统自动设置 |
| **nudge-state** | PostToolUse 计数器状态，记录每个会话的工具调用次数 |
| **trigger-flag** | Stop[0] 写入的 JSON 文件，标记该会话需要 reviewer 处理 |
| **hard gate** | 全局 PreToolUse hook 的硬性阻止机制（路径白名单 + 内容扫描） |

### 子代理原始稿

- **C 角色稿：** docs/reviews/2026-05-08-self-evolution-v4-C-review.md（归档于 claude-harness/.claude/skills/self/dev-plan-review/reviews/）
- **X 角色稿：** docs/reviews/2026-05-08-self-evolution-v4-X-review.md
- **S 角色稿：** docs/reviews/2026-05-08-self-evolution-v4-S-review.md

---

**评审完成日期：** 2026-05-08
**评审方法：** 三子代理并行评审 + 主编排者合并
**子代理角色分配：** C（契约与正确性）、X（执行与运维）、S（安全与证据）
