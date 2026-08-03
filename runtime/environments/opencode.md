# opencode 环境适配

> 当 source-analyzer 运行在 opencode 等非 OpenClaw agent 环境时，使用此适配层。

## 能力映射

| 行为接口 | opencode 实现 | 说明 |
|----------|--------------|------|
| `task.dispatch` | Task tool / 子进程 fork | 派发分析子任务 |
| `task.wait` | Task 等待 / 进程 join | 等待完成 |
| `task.list` | Task 状态查询 | 查看活跃任务 |
| `progress.persist` | Python 脚本写 JSON 文件 | 同 OpenClaw |
| `progress.restore` | Python 脚本 + 手动/系统 cron | 恢复中断分析 |
| `schedule.recurring` | 系统 crontab | 定时恢复（无内置 cron） |
| `schedule.remove` | crontab -r / 手动 | 移除定时任务 |
| `notify.silent` | 空输出 / 静默退出 | 静默返回 |
| `file.read` | 文件读取 | 读取文件 |
| `file.write` | 文件写入 | 写入文件 |
| `shell.exec` | Shell 执行 | 执行命令 |
| `parallel.max` | 4-6 | 推荐并行数（视 LLM 限制） |

## 检测信号

1. `sessions_spawn` 工具**不可用**
2. Task tool 可用（或等价机制）
3. 无 `~/.openclaw/` 目录

## 与 OpenClaw 的差异

| 功能 | OpenClaw | opencode |
|------|----------|----------|
| 并行派发 | sessions_spawn (原生) | Task tool / 子进程 |
| 批次等待 | sessions_yield | Task 等待 |
| 定时恢复 | cron (isolated session) | 系统 crontab + CLI |
| 静默协议 | NO_REPLY | 无等价（不回复即可） |
| Goal 追踪 | active-goals.json + heartbeat | 手动检查 |

## 降级策略

不支持的功能自动降级：

| 缺失能力 | 降级方案 |
|----------|----------|
| 并行子任务 | 串行执行（可用 `--serial` 标志） |
| 定时恢复 | 手动重新运行 `resilient-runner.py` |
| Goal 持久化 | 仅检查点文件（`.checkpoint.json`） |
| 自动验证 | 手动运行 `verify-analysis.py` |

## PLAN.md 行为指令翻译

```
[DISPATCH: task="分析模块 core" label="module-core"]
  → Task(prompt="分析模块 core", ...) 或 子进程执行

[WAIT: "等待批次完成"]
  → 等待所有 Task 完成

[SCHEDULE: interval=30min, task="恢复分析"]
  → (crontab) */30 * * * * cd /path && python3 scripts/resilient-runner.py --continue

[NOTIFY_SILENT]
  → (无输出)
```

## 纯 CLI 模式（无 agent 框架）

完全无并行能力时：

```bash
# 串行执行所有分析任务
python3 scripts/smart-analyze.py /path/to/project --serial -o output-dir
python3 scripts/recursive-orchestrator.py output-dir --manifest ... --serial
python3 scripts/resilient-runner.py --output-dir output-dir --serial
```

---

*创建时间: 2026-07-21*
