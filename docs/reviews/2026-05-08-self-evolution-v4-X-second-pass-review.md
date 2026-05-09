# 方案评审报告（二次评审 — X 角色）

## 元信息

| 字段 | 填写 |
| --- | --- |
| 被评文档 | docs/superpowers/plans/2026-05-08-self-evolution-v4.md |
| 被评版本 / 提交 | 未钉版本（前次评审后修订版） |
| 评审日期 | 2026-05-08 |
| 评审者 | X（执行与运维）二次评审 |
| 本报告归档路径 | docs/reviews/2026-05-08-self-evolution-v4-X-second-pass-review.md |

---

## 被评方案摘要

| 项 | 填写 |
| --- | --- |
| **要解决的核心问题** | 实现 self-evolution 插件 v4：用 AgentHook 在会话 Stop 时自动审查对话、通过元技能 evolve-skill-writer 生成 ~/.claude/skills/ 下的 SKILL.md |
| **非目标 / 明确不做** | YAML 硬验证、description 优化器、v1 自动化测试的交互式技能开发、事实记忆/情景记忆 |
| **交付形态** | Claude-Code 插件（agents/commands/hooks/skills 四通道）+ 测试脚本 + 文档 |
| **关键外部依赖** | bash >= 4.x、jq >= 1.6、Claude-Code v1.x with plugin marketplace、POSIX 兼容 shell |
| **安全风险档位** | 高 — 涉及自动化写入用户目录、全局 PreToolUse hook 拦截所有 Write/Edit/MultiEdit |

---

## 发现项

### 前次评审修复验证（F8/F9/F10/F24/F25/F26/F29/F30）

| 前次 ID | 修复验证 | 结论 |
| --- | --- | --- |
| F8 | Task 0 Step 1 改用 `REPO_ROOT="$(git rev-parse --show-toplevel)"`；Plan 开头新增 `$REPO_ROOT` 与 `$CLAUDE_PLUGIN_ROOT` 段说明 | 已修复 |
| F9 | Task 1 Step 3 新增 `parse_day1_result.sh`，输出标准化 JSON verdict（path A/B/INCONCLUSIVE）；Step 4 提供三分支自校验 | 已修复 |
| F10 | 新增 Task 0.5 `tests/preflight.sh`，E1-E7 自动化检查输出 JSON | 已修复（但见 X-F2 新问题） |
| F24 | 新增 Task 12.5 `scripts/reset-state.sh`（dry-run / --apply / --quiet）；README troubleshooting 段引用脚本 | 已修复（但见 X-F2 新问题） |
| F25 | README 新增 "Upgrade (F25)" 段，含备份、卸载、重装、验证四步 | 已修复 |
| F26 | README 新增 "Monitoring & logs (F7/F26)" 段，含 JSONL 字段表 + jq 查询示例 + Claude-Code telemetry 阈值 | 已修复（但见 X-F4 新问题） |
| F29 | README 新增 "Rollback (F29)" 段，含 git checkout + 重装 + 可选数据恢复 | 已修复 |
| F30 | 与 F17 合并，Task 17 `verify_quality_checklist.sh` 提供脚本化 Quality Checklist 验证 | 已修复（e2e 真实 LLM 场景保持人工是合理设计） |

### 新发现项

| ID | 级别 | 位置 | 现象 | 触发条件 | 影响 | 建议 | 维度 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| X-F1 | 高 | README.md "Security model" 段 vs security-scan.sh | README 声明 `DISABLE_SELF_EVOLUTION_PREHOOK=1` 可绕过全局 PreToolUse hook，但 security-scan.sh 脚本不检查此环境变量 | 用户按 README 文档设置该变量后期望 hook 被 bypass | 文档承诺的逃生舱口不生效，用户无法在紧急情况下按文档操作绕过 hook | 在 security-scan.sh 开头（HOOK_INPUT 解析之前）加 `if [ "${DISABLE_SELF_EVOLUTION_PREHOOK:-0}" = "1" ]; then exit 0; fi`；或从 README 删除该声明 | 可执行性 |
| X-F2 | 高 | preflight.sh / reset-state.sh / verify_quality_checklist.sh / 多个 test 脚本 | 多个脚本使用 bash 4+ 特有语法（`declare -a`、`mapfile`）但 shebang 为 `#!/usr/bin/env bash`，在 macOS 上解析到 /bin/bash (3.2) | 开发者在未安装 bash 4+ 的 macOS 上执行任何脚本 | 脚本以语法错误崩溃而非给出可操作的诊断信息；尤其 preflight.sh 本身就是检测 bash 版本的脚本，却依赖 bash 4+ 才能运行——自举悖论 | 二选一：(a) 将 preflight.sh 重写为 bash 3.2 兼容（用普通数组赋值替代 `declare -a`，用 while-read 替代 `mapfile`），使其能先检测并报告 E2 失败；其余脚本改 shebang 为 `#!/usr/local/bin/bash` 或 `#!/opt/homebrew/bin/bash`；(b) 在所有脚本前加一个 bash-3.2 兼容的 wrapper 脚本检测版本并给出明确指引 | 可执行性 |
| X-F3 | 中 | test_security_scan.sh Test 8 / test_redteam_full.sh S5 + F16-B | 性能测试使用 `date +%s%N` 获取纳秒时间戳，但 `%N` 是 GNU coreutils 扩展，macOS 的 date 不支持 | 在 macOS 上运行包含性能断言的测试 | `date +%s%N` 在 macOS 输出含字面 `%N` 或 `N` 的非数字字符串，后续算术 `$(( (END - START) / 1000000 ))` 在 `set -e` 下会导致脚本崩溃而非跳过性能检查 | 替换为跨平台计时方案：`python3 -c 'import time; print(int(time.monotonic()*1e9))'` 或用 `perl -MTime::HiRes=time -e 'printf "%.0f\n", time*1e9'`；或检测平台 `if date +%s%N 2>/dev/null | grep -qE '^[0-9]+$'; then ... ; else SKIP_TIMING=1; fi` 并在 SKIP 时跳过性能断言 | 可执行性 |
| X-F4 | 低 | README "Monitoring & logs" 段 / lib/log.sh | JSONL 日志文件 `self-evolution.jsonl` 无轮转策略，持续增长无上限 | 插件长期运行（数周/数月） | 日志文件静默膨胀，可能占用大量磁盘空间且 jq 查询变慢 | 在 README 监控段补充日志管理建议：`logrotate` 配置示例或手动清理命令 `find ~/.claude/logs -name 'self-evolution.jsonl' -size +10M -exec truncate -s 0 {} \;`；或在 log.sh 中加 `SIZE > threshold` 时自动 rotate | 可运维性 |
| X-F5 | 低 | Task 14 run_all.sh + Task 17 Step 4 | Task 14 的 run_all.sh 已内联包含 verify_quality_checklist.sh self-test（第 2475-2484 行），Task 17 Step 4 指示"把以下三行加入 tests/run_all.sh"，造成同一自检逻辑被执行两次 | 按 Task 顺序实施后运行 run_all.sh | 自检运行两次，输出中 `pass=` 计数可能与预期 `pass=7` 不符（实际为 pass=8）；不影响正确性但造成混淆 | Task 17 Step 4 改为"替换 run_all.sh 中已有的 verify_quality_checklist.sh 内联自检"或明确标注"以下代码已在 Task 14 中预置，此步骤无需修改" | 可执行性 |
| X-F6 | 低 | File Structure 第 96 行 vs 全部 Task 步骤 | 文件结构图列出 `tests/fixtures/redteam/outside-skills.txt`，但无任何 Task 创建此文件，也无测试引用它 | 按文件结构图检查交付完整性 | 文件结构图与实际交付不一致；实施者可能困惑是否遗漏了步骤 | 从文件结构图中删除 `outside-skills.txt`，或补充创建步骤（如写一个包含引用 `~/.ssh/id_rsa` 路径的 fixture 用于路径白名单测试） | 一致性 |

### 七维索引

| 维度 | 相关 F 编号 |
| --- | --- |
| 一致性 | X-F6 |
| 正确性 | — |
| 完整性 | — |
| 可执行性 | X-F1, X-F2, X-F3, X-F5 |
| 安全性 | — |
| 可验证性 | — |
| 可运维性 | X-F4 |

---

## 开放问题

| ID | 问题 | 是否阻塞结论 | 建议决策方 |
| --- | --- | --- | --- |
| X-Q1 | `DISABLE_SELF_EVOLUTION_PREHOOK` 环境变量是设计意图（应在 security-scan.sh 实现）还是 README 误写？ | 是（决定是补实现还是删文档） | 方案作者 |
| X-Q2 | macOS 默认 bash 3.2 的兼容性问题，方案选择是"要求用户预装 bash 4+（在 preflight 外围加检测）"还是"所有脚本兼容 bash 3.2"？ | 是（影响所有脚本的 shebang 和语法选择） | 方案作者 |

---

## 总体结论

### 决策摘要

| 项 | 填写 |
| --- | --- |
| **结论** | 修补后可实现 |
| **发现项最高级别** | 高 |
| **是否阻塞实现或发布** | 是 — 需先修复 X-F1 和 X-F2 |
| **下一步必须先做的 1～3 件事** | 1. 修复 X-F1：在 security-scan.sh 中实现 `DISABLE_SELF_EVOLUTION_PREHOOK` 检查，或从 README 删除该声明<br>2. 修复 X-F2：将 preflight.sh 重写为 bash 3.2 兼容（至少能检测并报告 bash 版本不足），其余 bash 4+ 脚本的 shebang 指向 brew bash 或在脚本开头加版本检测<br>3. 修复 X-F3：替换 `date +%s%N` 为跨平台计时方案 |

### 理由

前次评审 F8/F9/F10/F24/F25/F26/F29/F30 的修复已逐项验证通过，文档层面的 Upgrade/Rollback/Monitoring 段落内容完整、步骤可操作。然而修复过程中引入了两个**高级别新问题**：

**X-F1** 是文档与实现不一致：README Security model 段声明了 `DISABLE_SELF_EVOLUTION_PREHOOK=1` 作为紧急 bypass 手段，但 `security-scan.sh` 完全没有检查该变量。运维人员在生产环境遇到 PreToolUse hook 误拦截阻塞工作时，按文档操作将无效——这是可运维性阻塞。

**X-F2** 是平台可执行性阻塞：`preflight.sh` 的设计目标是检测 bash >= 4.x 是否可用，但脚本自身使用了 `declare -a`（bash 4+ 语法），在 macOS 默认 bash 3.2 上直接语法错误退出，无法完成检测使命。`reset-state.sh` 使用 `mapfile`（同为 bash 4+ 特有），同样在 macOS 上无法执行。这构成了自举悖论。

**X-F3** 影响测试可靠性：`date +%s%N` 在 macOS 上不工作，导致性能断言测试崩溃而非跳过。虽然不影响核心功能，但在主流开发平台上测试套件不可跑通会降低开发者信心。

其余 X-F4/X-F5/X-F6 为低级别问题，不阻塞实施但应在 v4 发布前清理。

---

## 评审覆盖

### 阅读与假设

- **已读：**
  - 被评文档全文（2891 行），逐段阅读
  - 前次评审报告全文
  - 评审输出模板
  - 重点审查：Task 0.5（preflight.sh）、Task 1 Step 3（parse_day1_result.sh）、Task 12.5（reset-state.sh）、Task 13（README Upgrade/Rollback/Monitoring）、Task 17（verify_quality_checklist.sh）、Self-Review 对照表
- **未读或未验证：**
  - 实际脚本文件（只审查了文档中的代码片段）
  - Claude-Code hook engine 源码（仅阅读了 plan 中的引用）
  - 所有测试脚本的实际执行结果
  - spec 原文（仅通过 plan 的引用间接了解）
- **假定：**
  - 假设 Claude-Code 插件系统的 `/plugin` 命令行为与 README 描述一致
  - 假设 `$CLAUDE_PLUGIN_ROOT` 由 hook engine 在运行时正确注入
  - 假设 macOS 用户会遵循 E2 提示安装 bash 4+，但需 preflight.sh 能先检测到版本不足

### 证据与验证

| 类别 | 已有 | 缺口 |
| --- | --- | --- |
| 自动化测试 | Task 2-4 单元测试 + Task 10-12 集成测试 + Task 14 run_all.sh + Task 17 verify_quality_checklist.sh | 性能测试在 macOS 上不可跑通（X-F3）；run_all.sh 可能重复执行自检（X-F5）。是否阻塞结论：否（可跳过性能断言；重复不影响正确性） |
| 手工验收 / 演练 | Task 15 Day 1 SkillTool 验证 + Task 16 端到端 10+4 场景 | Day 1 验证步骤仍需人工触发（设计如此）。是否阻塞结论：否 |
| 监控与日志 | README 监控段 + lib/log.sh + jq 查询示例 | 无日志轮转策略（X-F4）。是否阻塞结论：否 |
| 回滚或恢复验证 | README Upgrade/Rollback 段 + reset-state.sh | DISABLE_SELF_EVOLUTION_PREHOOK 逃生舱口未实现（X-F1）。是否阻塞结论：是 |
| 红队 / 滥用面 | Task 4 五类红队 fixture + base64 解码 + Task 12 S1-S6 + Task 16 R1-R4 | outside-skills.txt fixture 缺失（X-F6）。是否阻塞结论：否 |

---

## 附录

### 主路径 / 失败路径要点

**实施者在 macOS 上可能遇到的阻塞路径：**

1. 克隆仓库 → 运行 preflight.sh → 语法错误（bash 3.2 不支持 `declare -a`）→ 无法得到 E2 检测结果 → 需人工判断安装 bash 4+ → 重新运行
2. 安装 bash 4+ → 重新运行 preflight.sh → E2 通过 → 继续实施
3. 运行 test_security_scan.sh → Test 8 崩溃（`date +%s%N` 不兼容）→ 需手动跳过性能测试
4. 运行 reset-state.sh → 语法错误（`mapfile` 不支持）→ 需改用 README 中的手动 rm 命令

**前次问题修复后的可操作路径：**

1. Task 0 Step 1 使用 `$REPO_ROOT` → 任意机器可执行
2. Task 0.5 preflight.sh → 一行命令检测环境 → 但 macOS 自举问题需先解决
3. Task 1 parse_day1_result.sh → JSON verdict 输出 → CI 可解析
4. Task 12.5 reset-state.sh → dry-run/--apply → 运维可复现
5. README Upgrade/Rollback/Monitoring → 步骤完整可操作 → 但 DISABLE_SELF_EVOLUTION_PREHOOK 需补实现

### 术语

| 术语 | 说明 |
| --- | --- |
| **自举悖论** | preflight.sh 需要 bash 4+ 才能运行，但其职责正是检测 bash 4+ 是否可用 |
| **DISABLE_SELF_EVOLUTION_PREHOOK** | README 文档声称的环境变量逃生舱口，用于在紧急情况下绕过全局 PreToolUse hook（当前未实现） |
| **bash 4+ 特有语法** | `declare -a`、`mapfile` 等，在 macOS 默认 bash 3.2 中不可用 |

---

**评审完成日期：** 2026-05-08
**评审方法：** X 角色（执行与运维）独立二次评审
**评审重点：** 前次 F8/F9/F10/F24/F25/F26/F29/F30 修复验证 + 新增脚本可执行性 + README 可操作性 + 修复引入的新问题
