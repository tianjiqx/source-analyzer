# DSH（DeepSeek Harness）环境适配

> source-analyzer 在 DeepSeek Harness（DSH）环境中的行为映射。
> 依据：2026-08-14 deepseek-harness 递归深度分析（36 模块，峰值并发 20）全流程实测。

---

## 环境画像

| 维度 | DSH 实况 |
|------|---------|
| 派发机制 | `subagent` 工具（后台默认，返回 durable id）；批内结构化派发可用 `workflow` 工具（scripts/analysis-workflow.js，纯内存编排） |
| 等待机制 | 子代理完成通知（禁止空轮询；阻塞时用 `job_output(wait=true)` 或依赖通知） |
| 进度持久化 | **原生 goal 工具**（`create_goal`/`update_goal`/`get_goal`），自动延续轮次即断点恢复 |
| 并行上限 | 建议 12-20（实测峰值 20 稳定；workflow 引擎实测并发 12/20 全放行，2026-08 探针验证） |
| workflow schema 门 | ⚠️ **实测不可靠**（拒绝 JSON/多余字段/缺 required 均被放行，2026-08 严格探针）——结构校验必须在 workflow JS 脚本内代码级实现（analysis-workflow.js 的 validateReport） |
| 文件系统 | 仅会话工作区可写（如 `/mnt/disk2/dsh-ws`）；`$SKILL_DIR`、home 等多为只读挂载 |
| 恢复机制 | goal 自动延续轮 + 输出目录（PLAN/checkpoint/active-goals.json） |

## 行为接口映射

| 行为接口 | DSH 实现 |
|----------|---------|
| `task.dispatch` | `subagent(prompt=..., run_in_background=true)`；`[DISPATCH: ...]` 块 → subagent |
| `task.wait` | 等完成通知；`[WAIT: ...]` 块 → 通知驱动，不轮询 |
| `task.list` | `list_agents(scope=children/descendants)` |
| `progress.persist` | `create_goal(objective=...)`（长任务开始时） |
| `progress.restore` | `get_goal` + `update_goal(action=resume)`（会话恢复/续跑时） |
| `progress.check` | ❌ 由 goal 自动延续轮承担 |
| `schedule.recurring` | ❌ 不支持（goal 轮次已承担断点恢复，cron 冗余） |
| `notify.silent` | ⚠️ 环境相关：Web GUI 会话即通知通道；长任务可选 `de_channel_send`（若装 dsh 渠道插件）推送批级汇总 |
| `memory.write` | ✅ 支持（memory 工具，target=project/daily 记录分析进展；可选） |
| `db.update` | ❌ 不支持（`$SKILL_DIR` 只读挂载） |
| `file.write` | 仅会话工作区；先探测可写性（如 `touch` 试写） |
| `shell.exec` | bash 工具；`/tmp` 不跨调用持久（需重建或写入工作区） |

## 闭环节钩子（B 组）在 DSH 的处理

| 钩子 | DSH 动作 | 记录位置 |
|------|---------|---------|
| 记忆回写 | ✅ 可选：memory 工具 target=project 写 1-2 行分析进展（不做大段回写，恢复仍靠 goal 轮 + 输出目录） | VERSION.md 记录已写轨道 |
| 对比数据库 | **跳过**：`$SKILL_DIR` 只读 | VERSION.md「可选钩子跳过记录」 |
| 定时恢复 | **跳过**：goal 自动延续轮承担（可选第二保险：task-board cron） | VERSION.md 同上 |
| 会话检查 | **跳过**：goal 轮次承担 | — |
| 完成通知 | 可选：`de_channel_send` 批级汇总（未配置渠道则跳过，会话即通道） | — |

## 子代理中断恢复协议（本次实测 5 次踩坑总结）

1. **空消息失败**（子代理返回空结果）：`send_message(subagent_id, 恢复指令)` 续跑。
   恢复指令须包含：产出清单检查、缺失文件补齐要求、报告补写（`.task-report.json`）。
2. **产出部分缺失**：用 `verify-analysis.py --recursive` / `mermaid-validator.py` 复核缺口，
   让子代理补齐（如 INDEX.md、10-submodule/、20-file-level/、learning-value.md、报告）。
3. **主 agent 兜底**：子代理无法恢复时，主 agent 手动补齐关键产出（INDEX.md + 报告），
   并在报告中注明"由主 agent 补齐"。
4. **并行报告写冲突**：同一输出目录的并行子代理应使用独立报告文件名
   （如 `.task-report-<suffix>.json`），避免互相覆盖。

## 其他实测注意事项

- `verify-analysis.py --recursive` 的模块计数按"含 INDEX.md 的目录"统计（任意深度），
  家族嵌套路径（`packages/<family>/<module>`）无需符号链接兼容层。
- `--all` 的项目级模板检查（顶层 `00-README.md` 等）与递归模式产出（`00-project-level/`）结构不符，
  递归模式闭环节以 `--recursive` 为准，不追改关键词。
- `mermaid-validator.py` 已支持 sequenceDiagram 的 `alt/loop/opt/par/rect/critical/break` 块闭合，
  不再误报 EXTRA_END。
- 禁止词检查会剥离代码块与行内代码后再扫描，合法包名（如 `todo`）不再误报；
  仍有个例可用 `--forbidden-allow` 显式豁免。

---

## 防中断辅助程序在 DSH 中的冗余对照

skill 为"分析过程不中断"准备了多个辅助程序，**在 DSH 中基本冗余**——
DSH 的断点恢复由三层原生机制天然承担：**goal 自动延续轮 + 持久 background subagent + 输出目录**。

| 防中断关切 | skill 程序 | DSH 原生替代 | 是否使用 |
|-----------|-----------|-------------|---------|
| 进度持久化 | `goal-tracker.py`（`$WORKSPACE/active-goals.json`） | 原生 goal 工具（`create_goal`/`update_goal`/`get_goal`），自动延续轮即恢复 | ❌ 不用（避免双机制重复） |
| 断点续传/重试 | `resilient-runner.py`（检查点+指数退避+`--continue`） | goal 轮次 + subagent 持久（跨轮存活，`send_message` 续跑）+ 主 agent 即 runner | ❌ 不用 |
| 定时恢复 | `setup-cron-recovery.py`（cron 配置） | goal 自动延续轮 = 内置调度器，无需外部 cron | ❌ 不用 |
| 编排+健康检查 | `orchestrator.py` | agent 自编排 subagent；`list_agents` 查状态；完成通知驱动 | ❌ 不用 |
| 完成签名 | `.task-complete.json` | `.task-report.json`（子代理报告）+ `verify-analysis` | ❌ 换成报告 |

**保留价值的部分**（作为数据/生成器，而非防中断机制）：
- `plan-tracker.py verify` → 可选验收工具（验收前需先修正预期文件估算与派发提示不一致的问题）；
- `recursive-orchestrator.py` / `generate-module-manifest.py` → PLAN/清单**生成器**，可用；
- `.checkpoint.json` / `.task-report.json` → 作为**数据**存于输出目录，跨轮引用。

**DSH 中断恢复实操**（实测有效）：
1. 会话中断 → 重启后 goal 自动延续轮携带 objective 恢复，先 `get_goal` 确认状态；
2. 子代理中断（空消息）→ `send_message` 续跑（附产出检查清单）；
3. 无法恢复的子代理 → 主 agent 手动补齐关键产出（INDEX.md + 报告）并注明。
