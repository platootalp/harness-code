# 方案评审报告（二次评审 — S 角色：安全与证据）

## 元信息

| 字段 | 填写 |
| --- | --- |
| 被评文档 | docs/superpowers/plans/2026-05-08-self-evolution-v4.md |
| 被评版本 / 提交 | 未钉版本 |
| 评审日期 | 2026-05-08 |
| 评审者 | S（安全与证据）二次评审 |
| 本报告归档路径 | docs/reviews/2026-05-08-self-evolution-v4-S2-review.md |
| 前次评审报告 | docs/reviews/2026-05-08-self-evolution-v4-dev-plan-review.md |

---

## 被评方案摘要

| 项 | 填写 |
| --- | --- |
| **要解决的核心问题** | 实现 self-evolution 插件 v4：用 AgentHook 在会话 Stop 时自动审查对话、通过 evolve-skill-writer 元技能生成 SKILL.md 文件 |
| **非目标 / 明确不做** | YAML 硬验证、description 优化器、v1 自动化测试的交互式技能开发、事实记忆/情景记忆 |
| **交付形态** | Claude-Code 插件（agents/commands/hooks/skills 四通道）+ 测试脚本 + 文档 |
| **关键外部依赖** | Claude-Code v1.x with plugin marketplace、jq（必需）、POSIX 兼容 shell |
| **安全风险档位** | 高 — 涉及自动化写入用户目录、全局 PreToolUse hook 拦截所有 Write/Edit/MultiEdit、LLM 自动生成内容的安全扫描 |

---

## 发现项

| ID | 级别 | 位置 | 现象 | 触发条件 | 影响 | 建议 | 维度 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S-F1 | 高 | Task 4 security-scan.sh L1117-1121 | base64 解码扫描对非 base64 的长字母数字串（UUID、SHA-1 hash、长标识符）会产生垃圾解码输出，可能误匹配 PI/bash/secret 模式 | SKILL.md 包含合法长标识符（如 git commit SHA-1 40 字符 hex） | 合法内容被误拦截为 prompt-injection 或 secret leak；频繁误报会削弱 hard gate 的可信度 | 在 base64 token 提取后增加合法性校验：解码后验证输出是否为可打印文本（如 `grep -cP '[\x20-\x7E\t\n]'` 比例 > 80%），丢弃明显是二进制垃圾的解码结果 | 安全性 |
| S-F2 | 中 | Task 4 security-scan.sh L1117 `while read` | base64 解码循环逐 token 调用 `base64 -d`，当内容含大量 base64-like 串时可能超过 PreToolUse hook 的 10s timeout | SKILL.md 内容含 100+ 个长字母数字标识符 | security-scan.sh 被 hook engine 强制 kill，Write 操作返回未定义错误，用户无法正常写入 | 增加解码循环的计数器上限（如最多解码 50 个 token），或对 $TMP 文件大小设上限后提前退出；同时将 PreToolUse timeout 从 10s 提升到 15s 留出余量 | 安全性 |
| S-F3 | 高 | Task 4 security-scan.sh L1067-1078 | 路径白名单 `~/.claude/skills/*/SKILL.md` 不校验 `*` 部分是否为合法 category 前缀 | 恶意或失控 agent 直接 Write 到 `~/.claude/skills/evil-foo/SKILL.md` | 非白名单 category 的 skill 被写入磁盘；虽经内容扫描但 category 约束被绕过；后续 `verify_quality_checklist.sh` 是事后验证，skill 已落地 | 在 security-scan.sh 路径白名单层增加 category 前缀校验：提取 `*/SKILL.md` 中 `*` 的 `-` 前缀，与 8 类白名单比对，不匹配则 block `category_not_whitelisted` | 安全性 |
| S-F4 | 中 | Task 5 hooks.json L1192 + Task 6 agents/skill-reviewer.md | reviewer 的 CREATE/UPDATE/SKIP 决策及理由未写入 `self-evolution.jsonl` | 事后安全审计需要追溯 reviewer 的所有决策 | F7 修复仅覆盖 scan_block / lock_timeout / reset_state 三类事件，reviewer 决策事件缺失；Claude-Code 内部 telemetry 可能不持久化 StructuredOutput 内容，审计链断裂 | 在 Stop[2] cleanup 脚本（stop-gate.sh --cleanup）中增加：读取 trigger-flag JSON 中的 StructuredOutput reason 字段（如 hook engine 暴露），调用 `log_event info reviewer_decision`；或在 README 监控段明确说明 reviewer 决策仅存于 Claude-Code telemetry、不在插件 JSONL 中 | 可验证性 |
| S-F5 | 中 | Task 2 lib/posix-lock.sh L608-626 | 锁超时后直接 return 1，无重试机制；nudge-state.sh PostToolUse 为 async 但失败后丢失本次计数 | 多个并发会话同时触发 PostToolUse，锁竞争激烈 | 计数丢失导致频率门控不准确，可能减少或增加 skill 生成频率；日志记录了超时事件但无恢复手段 | 在 nudge-state.sh 的 `acquire_lock` 调用处增加一次重试（总等待 10s），或在锁超时后以 "best-effort" 模式写入（不计入原子更新但至少记录事件）；在 README 监控段补充 lock_timeout 的含义与影响说明 | 安全性 |
| S-F6 | 中 | Task 16 Step 4 R1-R4 | LLM 红队场景未覆盖"恶意 UPDATE"攻击向量 | 用户对话诱导 reviewer 选择 UPDATE 一个已有安全 skill，注入恶意内容 | 已验证的安全 skill 被篡改，hard gate 仅扫描增量内容（Edit 的 old_string + new_string），可能遗漏上下文依赖的注入 | 在 R1-R4 后增加 R5：构造一个对话使得 reviewer 选择 UPDATE 已有 skill，并在 new_string 中嵌入 subtle prompt injection（如看似正常的注释实则含指令），验证 hard gate 和元技能均能拦截 | 安全性 |
| S-F7 | 中 | Task 12 test_redteam_full.sh F16-A L2047-2061 | 并发测试断言过弱：仅验证 JSON 未破损且 count 不在"不可能"状态，不验证计数准确性 | 10 并发 PostToolUse 事件，threshold=2 | 10 个事件中可能丢失任意数量，测试仍通过；无法发现锁竞争导致的计数丢失 | 增加 POST_COUNT 校验：并发前记录 nudge-state.json 的 count，并发后验证 count 增量 + threshold-crossing 次数之和等于 10（容忍最后一次 pending=true 的边界情况） | 可验证性 |
| S-F8 | 中 | Task 17 verify_quality_checklist.sh | 独立 Checklist 验证脚本不含 base64 解码扫描，与 security-scan.sh 检测能力不一致 | 生成的 SKILL.md 含 base64 编码的 PI 内容 | SKILL.md 通过 verify_quality_checklist.sh 但被 security-scan.sh 拦截，造成"验证通过但运行时被拦"的混淆 | 在 verify_quality_checklist.sh 的内容危险模式检查段（第 6 步）后增加 base64 解码扫描，逻辑复用 security-scan.sh 的提取+解码+grep 模式 | 可验证性 |
| S-F9 | 高 | Task 13 README.md L2405 vs Task 4 security-scan.sh | README 声称可设置 `DISABLE_SELF_EVOLUTION_PREHOOK=1` 绕过 PreToolUse hook，但 security-scan.sh 代码未实现此 env var 检查 | 用户按 README 设置该 env var 后期望 hook 被跳过，但实际仍生效；或未来实现时缺乏安全审查 | 若为文档遗留则误导用户；若未来实现则成为绕过所有安全门控的通道，且无审计日志记录 | 1. 若 bypass 不计划实现：删除 README 中该句；2. 若计划实现：在 security-scan.sh 开头增加 `if [ "${DISABLE_SELF_EVOLUTION_PREHOOK:-0}" = "1" ]; then log_event warn prehook_bypass '{...}'; exit 0; fi`，并确保 bypass 事件被记录 | 安全性 |

### 七维索引

| 维度 | 相关 F 编号 |
| --- | --- |
| 一致性 | — |
| 正确性 | — |
| 完整性 | — |
| 可执行性 | — |
| 安全性 | S-F1, S-F2, S-F3, S-F5, S-F6, S-F9 |
| 可验证性 | S-F4, S-F7, S-F8 |
| 可运维性 | — |

---

## 前次问题修复验证

| 前次 ID | 前次级别 | 修复状态 | 验证结论 |
| --- | --- | --- | --- |
| F1 | 严重 | 已修复，有残余风险 | base64 解码扫描已实现（Task 4 L1112-1127）；元技能 Quality Checklist 嵌套 PI 检查已添加（Task 8 L1613-1617）；trade-off 已文档化（L1139）。残余风险：(1) 垃圾解码误报（见 S-F1）；(2) 解码循环性能（见 S-F2） |
| F2 | 高 | 已修复，有残余风险 | SECOND.5 STEP 决策理由强制已加入 hooks.json 和 skill-reviewer.md；元技能也验证 rationale。残余风险：reviewer 决策未写入插件日志（见 S-F4） |
| F5 | 高 | 已修复，有缺口 | 元技能 Quality Checklist 显式列出 8 类白名单 + ABORT 出口；verify_quality_checklist.sh 独立校验。缺口：security-scan.sh 路径白名单不校验 category 前缀（见 S-F3） |
| F6 | 高 | 部分修复 | 超时日志已添加（lib/posix-lock.sh L618-620）。但原建议的"指数退避重试"未实现，锁超时后直接 return 1 无恢复（见 S-F5） |
| F7 | 高 | 部分修复 | lib/log.sh + scan_block/lock_timeout/reset_state 事件已实现；README 监控段已添加。缺口：reviewer 决策事件和 hook 执行时长未记录（见 S-F4）；无日志轮转机制 |
| F15 | 中 | 已修复，有缺口 | Task 16 新增 R1-R4 四个 LLM 红队场景。缺口：未覆盖恶意 UPDATE 攻击向量（见 S-F6） |
| F16 | 中 | 已修复，有残余风险 | F16-A（并发）/F16-B（超长）/F16-C（日志失败）三类已添加。残余风险：F16-A 并发断言过弱（见 S-F7） |
| F17 | 中 | 已修复，有缺口 | verify_quality_checklist.sh 独立验证已实现。缺口：不含 base64 解码扫描，与 hard gate 检测能力不一致（见 S-F8） |

---

## 开放问题

| ID | 问题 | 是否阻塞结论 | 建议决策方 |
| --- | --- | --- | --- |
| SQ1 | security-scan.sh 是否应增加 category 前缀校验以补全路径白名单的最后一环？（见 S-F3） | 是 — 如果不修复，非白名单 category 的 skill 可被直接写入磁盘 | 方案作者 |
| SQ2 | README 中 `DISABLE_SELF_EVOLUTION_PREHOOK=1` bypass 是文档错误还是待实现功能？（见 S-F9） | 是 — 必须在实施前明确，否则安全模型描述不完整 | 方案作者 |
| SQ3 | base64 解码扫描的垃圾解码误报风险是否可接受？是否需要增加可打印文本比例校验？（见 S-F1） | 否 — 可在实施中微调 | 方案作者 |

---

## 总体结论

### 决策摘要

| 项 | 填写 |
| --- | --- |
| **结论** | 修补后可实现 |
| **发现项最高级别** | 高 |
| **是否阻塞实现或发布** | 是 — 需先修复 S-F3（category 前缀不在 hard gate 中校验）和 S-F9（bypass 文档/代码不一致）两个高级别问题 |
| **下一步必须先做的 1～3 件事** | 1. 修复 S-F3：在 security-scan.sh 路径白名单层增加 category 前缀校验<br>2. 修复 S-F9：明确 DISABLE_SELF_EVOLUTION_PREHOOK 的去留，若删除则修正 README<br>3. 修复 S-F1：在 base64 解码后增加可打印文本比例校验以减少误报 |

### 理由

前次评审 F1-F7 五个严重/高问题已基本修复，但修复引入了新的安全缺口和残余风险。

**最高级别问题 S-F3**：security-scan.sh 的路径白名单 `~/.claude/skills/*/SKILL.md` 不校验 `*` 部分的 category 前缀。前次 F5 修复在元技能 Quality Checklist 和 verify_quality_checklist.sh 中增加了 category 白名单校验，但这两者分别是 LLM 自检和事后验证，均非硬门控。一个恶意或失控的 agent 可直接 Write 到 `~/.claude/skills/evil-foo/SKILL.md`，路径白名单放行、内容扫描通过（如果内容无危险模式），skill 即落地。这等于在三层硬门控的 L4 层留了一个未校验的通配符。

**S-F9**：README 文档声称存在 `DISABLE_SELF_EVOLUTION_PREHOOK=1` 环境变量可绕过 PreToolUse hook，但 security-scan.sh 代码中未实现此检查。这要么是文档错误（误导用户），要么是待实现功能（将成为绕过所有安全门控的通道，且当前无审计日志）。无论哪种情况，安全模型描述与实际不一致，必须在实施前明确。

**S-F1**：base64 解码扫描是 F1 修复的核心，但 `grep -oE '[A-Za-z0-9+/]{20,}={0,2}'` 会匹配大量非 base64 字符串（SHA-1 hash、UUID、长标识符），解码后产生二进制垃圾可能误匹配 PI 模式。这在实践中可能导致合法 skill 被误拦截，削弱 hard gate 的可信度。

**残余风险**：F6 修复仅增加了超时日志而未实现重试或恢复机制；F7 修复缺少 reviewer 决策事件和 hook 执行时长的日志记录；F17 修复的独立验证脚本不含 base64 解码扫描。这些均为中级别问题，不阻塞实施但应在后续迭代中补全。

---

## 评审覆盖

### 阅读与假设

- **已读：**
  - 被评文档全文（2891 行），重点精读 Task 2 (lib/log.sh, lib/posix-lock.sh)、Task 4 (security-scan.sh)、Task 5 (hooks.json)、Task 6 (skill-reviewer.md)、Task 8 (元技能 SKILL.md Quality Checklist)、Task 12 (红队测试)、Task 16 (端到端验收)、Task 17 (verify_quality_checklist.sh)、Self-Review 修复对照表
  - 前次评审报告全文
  - 评审输出模板
- **未读或未验证：**
  - 设计规格 spec §5.6 原文（仅阅读了 plan 中引用的完整文本）
  - 实际脚本文件（只阅读了 plan 中提供的代码片段）
  - Claude-Code hook engine 源码（仅阅读了 spec 中的引用片段）
  - 所有单元测试和集成测试的实际执行
- **假定：**
  - 假设 Claude-Code AgentHook 的 StructuredOutput 内容不持久化于插件可访问的存储中
  - 假设 `DISABLE_SELF_EVOLUTION_PREHOOK` 环境变量在当前 plan 代码中未实现
  - 假设 base64 -d 在 macOS 和 GNU 上的行为差异已由 `base64 -d 2>/dev/null || base64 -D 2>/dev/null` 覆盖

### 证据与验证

| 类别 | 已有 | 缺口 |
| --- | --- | --- |
| 自动化测试 | Task 4: 5 类红队 + base64 fixture; Task 12: S1-S6 + F16-A/B/C | base64 解码的误报场景未测试（S-F1）；F16-A 并发断言过弱（S-F7）<br>是否阻塞结论：否（建议补测试用例） |
| 手工验收 / 演练 | Task 16: 10 正常 + 4 红队 LLM 场景 | 未覆盖恶意 UPDATE 攻击（S-F6 / S-F3）<br>是否阻塞结论：否（建议补 R5 场景） |
| 监控与日志 | lib/log.sh + scan_block/lock_timeout/reset_state 事件 + README 监控段 | reviewer 决策事件未记录（S-F4）；无日志轮转<br>是否阻塞结论：否 |
| 回滚或恢复验证 | Task 2: POSIX 锁超时日志; Task 12.5: reset-state.sh | 锁超时无重试/恢复机制（S-F5）<br>是否阻塞结论：否 |
| 红队 / 滥用面 | Task 4: 5 类红队 fixture; Task 12: S1-S6; Task 16: R1-R4 LLM 红队 | category 前缀绕过未在 hard gate 中拦截（S-F3）；恶意 UPDATE 未测试（S-F6）；bypass 环境变量文档/代码不一致（S-F9）<br>是否阻塞结论：是（S-F3 + S-F9） |

---

## 附录

### 术语

| 术语 | 说明 |
| --- | --- |
| **hard gate** | 全局 PreToolUse hook 的硬性阻止机制（路径白名单 + 内容扫描），不可被 LLM 跳过 |
| **category 前缀** | SKILL.md 目录名中 `-` 前的部分，限定为 8 类白名单之一 |
| **垃圾解码** | 对非 base64 字符串执行 base64 -d 产生的二进制输出，可能偶然匹配安全模式 |
| **DISABLE_SELF_EVOLUTION_PREHOOK** | README 中声称的 PreToolUse hook bypass 环境变量，代码中未实现 |

---

**评审完成日期：** 2026-05-08
**评审方法：** S 角色二次评审，独立审查前次 F1/F2/F5/F6/F7/F15/F16/F17 修复 + 新引入安全问题扫描
