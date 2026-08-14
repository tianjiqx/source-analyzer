# DSH（DeepSeek Harness）环境适配

> source-analyzer 在 DeepSeek Harness（DSH）环境中的行为映射。
> 依据：2026-08-14 deepseek-harness 递归深度分析（36 模块，峰值并发 20）全流程实测。

---

## 环境画像

| 维度 | DSH 实况 |
|------|---------|
| 派发机制 | `subagent` 工具（后台默认，返回 durable id） |
| 等待机制 | 子代理完成通知（禁止空轮询；阻塞时用 `job_output(wait=true)` 或依赖通知） |
| 进度持久化 | **原生 goal 工具**（`create_goal`/`update_goal`/`get_goal`），自动延续轮次即断点恢复 |
| 并行上限 | 建议 12-20（实测峰值 20 稳定；`[WAIT]` 批次等待通知驱动） |
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
| `notify.silent` | ❌ 不支持（本会话上下文即通知通道） |
| `memory.write` | ❌ 不支持（无长期记忆消费者；写入 MEMORY.md 是假闭环） |
| `db.update` | ❌ 不支持（`$SKILL_DIR` 只读挂载） |
| `file.write` | 仅会话工作区；先探测可写性（如 `touch` 试写） |
| `shell.exec` | bash 工具；`/tmp` 不跨调用持久（需重建或写入工作区） |

## 闭环节钩子（B 组）在 DSH 的处理

| 钩子 | DSH 动作 | 记录位置 |
|------|---------|---------|
| 记忆回写 | **跳过**：无记忆消费者，恢复靠 goal 轮次 + 输出目录 | VERSION.md「可选钩子跳过记录」 |
| 对比数据库 | **跳过**：`$SKILL_DIR` 只读 | VERSION.md 同上 |
| 定时恢复 | **跳过**：goal 自动延续轮承担 | VERSION.md 同上 |
| 会话检查 | **跳过**：goal 轮次承担 | — |
| 完成通知 | **跳过**：即本会话上下文 | — |

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
