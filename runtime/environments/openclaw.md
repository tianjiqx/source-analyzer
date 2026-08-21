# OpenClaw 环境适配

> 当 source-analyzer 运行在 OpenClaw 环境时，使用此适配层。

## 能力映射

| 行为接口 | OpenClaw 实现 | 说明 |
|----------|--------------|------|
| `task.dispatch` | `sessions_spawn(task=..., label=..., mode="run")` | 创建并行子代理 |
| `task.wait` | `sessions_yield(message="...")` | 等待批次完成 |
| `task.list` | `subagents(action="list")` | 列出活跃子代理 |
| `progress.persist` | Python 脚本写 JSON 文件 | 检查点持久化 |
| `progress.restore` | Python 脚本读 JSON 文件 + agent 续传 | 恢复中断分析 |
| `schedule.recurring` | `cron(action="add", job={sessionTarget:"isolated", ...})` | 定时恢复 |
| `schedule.remove` | `cron(action="remove", jobId="...")` | 移除定时任务 |
| `notify.silent` | `NO_REPLY` | 静默返回 |
| `file.read` | `read(path=...)` | 读取文件 |
| `file.write` | `write(path=..., content=...)` | 写入文件 |
| `shell.exec` | `exec(command=...)` | 执行命令 |
| `parallel.max` | 8 | 推荐最大并行数 |

## 检测信号

以下信号出现时，判定为 OpenClaw 环境：

1. `sessions_spawn` 工具可用
2. 工作区 `~/.openclaw/` 目录存在
3. Skill frontmatter 包含 `metadata.openclaw`
4. 环境变量 `OPENCLAW_SESSION` 存在

## 使用方式

当 agent 加载 source-analyzer skill 时：

1. 检测到 OpenClaw 环境
2. 读取本文件了解能力映射
3. 在 SKILL.md 中的行为指令替换为 OpenClaw 具体实现
4. 弹性恢复等高级功能自动启用

## PLAN.md 中的行为指令翻译

SKILL.md 中的环境无关指令在 OpenClaw 中的翻译：

```
[DISPATCH: task="分析模块 core" label="module-core"]
  → sessions_spawn(task="分析模块 core", label="module-core", mode="run")

[WAIT: "等待批次完成"]
  → sessions_yield(message="等待批次完成")

[SCHEDULE: interval=30min, task="恢复分析"]
  → cron(action="add", job={sessionTarget:"isolated", payload:{kind:"agentTurn", ...}})

[NOTIFY_SILENT]
  → NO_REPLY
```

## 弹性恢复 (OpenClaw 专有)

OpenClaw 环境支持完整的弹性恢复链：

1. **检查点持久化** — `.resilient-checkpoint.json` + `.checkpoint.json`
2. **Cron 自动恢复** — isolated session 每 N 分钟检查失败任务
3. **Continuation Prompt** — 生成恢复指令让 cron session 自主执行
4. **Goal 持久化** — `active-goals.json` 跨会话状态追踪

> 这些功能依赖 OpenClaw 的 cron + isolated session 机制。  
> 在其他环境中，降级为手动恢复或系统 crontab。

## 路径约定

| 变量 | OpenClaw 默认 | 说明 |
|------|--------------|------|
| `$WORKSPACE` | `~/.openclaw/workspace` | 工作区根 |
| `$OUTPUT_BASE` | `~/.openclaw/learning/projects` | 分析输出基目录 |
| `$SKILL_DIR` | `$WORKSPACE/skills/source-analyzer` | Skill 根目录 |
| `$GOALS_FILE` | `$WORKSPACE/active-goals.json` | Goal 状态文件 |

---


---

## Goal 持久化（goal-tracker.py）

本环境的 goal 机制由 `$SKILL_DIR/scripts/goal-tracker.py` 提供，状态写入 `$WORKSPACE/active-goals.json`（可用环境变量 `SOURCE_ANALYZER_GOALS_FILE` 覆盖）：

```bash
# 执行前：注册 Goal（必做）
python3 $SKILL_DIR/scripts/goal-tracker.py register \
  --objective "深度分析 <项目名>" \
  --project "<项目名>" \
  --output-dir "$OUTPUT_BASE/<name>" \
  --mode "recursive_deep" \
  --total-tasks <N> \
  --plan-file "$OUTPUT_BASE/<name>/PLAN.md"

# 执行中：每批次后同步进度
python3 $SKILL_DIR/scripts/goal-tracker.py update \
  --goal-id "<goal-id>" --phase "Phase 2 (批次 2/5)" --completed 15

# 执行后：标记完成
python3 $SKILL_DIR/scripts/goal-tracker.py complete --goal-id "<goal-id>"

# 会话恢复：检查未完成任务（心跳/定时触发时）
python3 $SKILL_DIR/scripts/goal-tracker.py check

# 查看任务列表
python3 $SKILL_DIR/scripts/goal-tracker.py list
```
