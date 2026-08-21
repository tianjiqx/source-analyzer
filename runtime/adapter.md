# 运行时环境适配协议

> **核心原则**：Skill 的分析逻辑（意图）与执行机制（行为）完全分离。  
> 不同运行环境（OpenClaw / opencode / Claude Code / Cursor / 纯 CLI）通过适配层接入。

---

## 架构总览

**三层架构**（从环境无关到环境特定）：

- **SKILL.md（环境无关）** — 分析方法论 · 模板 · 质量标准 · 输出规范
- **runtime/adapter.md（适配层）** — 能力检测 · 任务派发 · 进度追踪 · 恢复机制
- **环境实现（可选/可扩展）** — openclaw.md (sessions_spawn/cron) · opencode.md (Task tool/进程) · dsh.md (subagent/原生 goal) · 纯 CLI (串行)

---

## 三层分离

### Layer 1: 意图 (Intent) — 环境无关

Skill 的核心分析逻辑，定义"做什么"：

- 项目类型检测 → 模板选择
- 模块清单生成 → 分析计划
- 文件级分析维度（11 维度）
- 质量评分体系
- 验证与闭环

**不包含任何环境特定的 API 调用。**

### Layer 2: 行为 (Behavior) — 能力接口

定义"怎么做"的标准接口，由环境适配层实现：

| 行为接口 | 说明 | 必须 |
|----------|------|------|
| `task.dispatch` | 派发一个分析子任务 | ✅ |
| `task.wait` | 等待一批子任务完成 | ✅ |
| `task.list` | 查看活跃子任务状态 | ✅ |
| `progress.persist` | 持久化分析进度 | ✅ |
| `progress.restore` | 恢复中断的分析 | ✅ |
| `progress.check` | 会话开始时检查未完成任务 | ❌ |
| `schedule.recurring` | 设置定时恢复任务 | ❌ |
| `schedule.remove` | 移除定时任务 | ❌ |
| `notify.silent` | 静默返回（不打扰用户） | ❌ |
| `memory.write` | 写入长期记忆文件（如 `$WORKSPACE/MEMORY.md`） | ❌ |
| `db.update` | 更新对比数据库（`$SKILL_DIR/references/project-comparison-db.md`） | ❌ |
| `file.write` | 写入文件 | ✅ |
| `file.read` | 读取文件 | ✅ |
| `shell.exec` | 执行 Shell 命令 | ✅ |

> ⚠️ `memory.write` / `db.update` / `schedule.recurring` / `progress.check` / `notify.silent`
> 均为**可选钩子**：环境不支持时必须**显式跳过**并在 VERSION.md 记录原因，
> 禁止"为了完成闭环而假执行"（写入无消费者消费的文件）。

### Layer 3: 能力 (Capability) — 环境实现

每个运行环境实现 Behavior 接口：

```markdown
## OpenClaw 环境
- task.dispatch → `sessions_spawn(task=..., label=..., mode="run")`
- task.wait → `sessions_yield(message="等待批次完成")`
- schedule.recurring → `cron(action=add, job={sessionTarget:"isolated", ...})`
- notify.silent → `NO_REPLY`
- memory.write → `$WORKSPACE/MEMORY.md`
- db.update → `$SKILL_DIR/references/project-comparison-db.md`（假设 skill 目录可写）

## opencode 环境
- task.dispatch → 通过 Task tool 或 fork 子进程
- task.wait → 等待 Task 完成 / 进程 join
- schedule.recurring → 系统 crontab
- notify.silent → 空输出
- memory.write → `$WORKSPACE/MEMORY.md`
- db.update → 同 OpenClaw（依赖 skill 目录可写）

## DSH 环境 (DeepSeek Harness)
- task.dispatch → `subagent` 工具（后台默认），峰值并发 12-20（实测 20 稳定）
- task.wait → 等待 subagent 完成通知（禁止空轮询）
- task.list → `list_agents`（children/descendants）
- progress.persist/restore → **原生 goal 工具**（`create_goal`/`update_goal`/`get_goal`），自动延续轮次即断点恢复
- progress.check → 由 goal 自动延续轮承担（无需手动检查）
- schedule.recurring → ❌ 不支持（goal 轮次已承担自动恢复，cron 冗余）
- notify.silent → ❌ 不支持（本会话上下文即通知通道）
- memory.write → ❌ 不支持（无长期记忆消费者；恢复依赖 goal 轮次 + 输出目录，写入 MEMORY.md 是假闭环）
- db.update → ❌ 不支持（`$SKILL_DIR` 通常只读挂载）
- file.write → 仅会话工作区可写（其余路径多为只读挂载，需先探测）
- 中断恢复：子代理空消息失败 → `send_message` 续跑（附产出检查清单）；主 agent 手动补齐兜底（INDEX.md + .task-report.json）

## 纯 CLI 环境 (无 agent 框架)
- task.dispatch → 串行执行（无并行）
- task.wait → N/A（同步）
- schedule.recurring → 系统 crontab
- notify.silent → N/A
- memory.write → 用户指定路径（默认跳过）
- db.update → 依赖 skill 目录可写（只读则跳过）
```

---

## 环境能力矩阵

闭环节 B 组可选钩子与恢复机制，按环境对照（❌ = 显式跳过并记录，禁止假执行）：

| 能力 | openclaw.md | opencode.md | **dsh.md** | standalone |
|------|-------------|-------------|------------|------------|
| `task.dispatch` | sessions_spawn | Task tool/进程 | **subagent 工具（后台）** | 串行 |
| `task.wait` | sessions_yield | 进程 join | **完成通知驱动** | 同步 |
| `progress.persist/restore` | goal-tracker.py | goal-tracker.py | **原生 goal 工具** | goal-tracker.py |
| `progress.check` | cron 心跳 | 手动 | **goal 轮次承担** | 手动 |
| `schedule.recurring` | cron + isolated | 系统 crontab | **❌（goal 轮次承担）** | 系统 crontab |
| `notify.silent` | NO_REPLY | 空输出 | **❌（会话即上下文）** | N/A |
| `memory.write` | `$WORKSPACE/MEMORY.md` | 同左 | **❌（无消费者）** | 用户指定/跳过 |
| `db.update` | `$SKILL_DIR/references/` | 同左 | **❌（目录只读）** | 同左（只读跳过） |
| 状态文件路径 | `$WORKSPACE/active-goals.json` | 同左 | **❌（用原生 goal）** | 需 `SOURCE_ANALYZER_GOALS_FILE` 重定向 |

---

## 环境检测协议

Skill 被加载时，通过以下信号检测当前运行环境：

| 信号 | 检测方法 | 可靠性 |
|------|----------|--------|
| **工具可用性** | 检查 `sessions_spawn` 工具是否存在 | 高 |
| **环境变量** | `OPENCLAW_SESSION`, `OPENCODE_TASK` 等 | 中 |
| **文件标记** | 工作区中 `.openclaw/` 目录存在 | 高 |
| **Skill 格式** | frontmatter 中 `metadata.openclaw` | 高 |
| **用户声明** | 用户显式指定环境 | 最高 |

### 检测优先级

1. **用户显式声明** — "用 opencode 模式" → 直接使用
2. **工具可用性** — sessions_spawn 可用 → OpenClaw 模式
3. **环境探测** — `.openclaw/` 目录存在 → OpenClaw 模式
4. **默认降级** → 纯 CLI 串行模式

---

## Skill 中的条件执行语法

SKILL.md 中使用环境无关的**行为指令**，适配层负责翻译：

```markdown
<!-- 环境无关的行为指令 -->
[DISPATCH: task="分析模块 core" label="module-core"]
[WAIT: "等待批次 1 完成"]
[IF-CAPABLE: schedule.recurring]
[SCHEDULE: interval=30min, task="恢复分析"]
[/IF-CAPABLE]
```

Agent 读取到这些指令后，根据当前环境的能力实现来执行。

### 简化约定

在 SKILL.md 的文本中，使用**自然语言行为指令**而非伪代码：

```markdown
### 执行分析

1. **派发子任务** — 将每个模块分析任务派发给并行执行器
2. **等待批次完成** — 当前批次全部完成后继续
3. **同步进度** — 运行 `plan-tracker.py sync` 更新检查点
4. **如支持定时恢复** — 设置自动恢复任务（可选）
```

---

## 运行时能力声明文件

每个环境在加载 skill 时，可以声明自己的能力（可选）：

```yaml
# runtime-capabilities.yaml (示例)
environment: openclaw
capabilities:
  task.dispatch: sessions_spawn
  task.wait: sessions_yield
  task.list: subagents
  parallel.max: 8
  schedule.recurring: cron
  notify.silent: NO_REPLY
  file.read: read
  file.write: write
  shell.exec: exec
```

如果不存在此文件，skill 按默认（纯 CLI 串行）模式运行。

---

## 对现有脚本的影响

### 脚本层（Python）

所有 Python 脚本**只负责数据处理的逻辑**：
- `generate-module-manifest.py` — 扫描目录，生成 JSON ✅ 已解耦
- `detect-project-type.py` — 文件模式匹配 ✅ 已解耦
- `verify-analysis.py` — 文件系统验证 ✅ 已解耦
- `goal-tracker.py` — JSON 状态管理 ✅ 已解耦
- `plan-tracker.py` — 检查点管理 ✅ 已解耦
- `resilient-runner.py` — 状态检测 + 指令生成 → 需要解耦
- `recursive-orchestrator.py` — PLAN.md 生成 → 需要解耦
- `setup-cron-recovery.py` — cron 配置生成 → 需要改为通用调度配置

### 需要解耦的脚本

#### `resilient-runner.py`
- **当前**: 生成 `sessions_spawn` / `sessions_yield` 文本指令
- **目标**: 生成环境无关的任务派发指令，由适配层翻译
- **改动**: `generate_spawn_instructions()` 输出抽象任务描述而非具体 API 调用

#### `recursive-orchestrator.py`
- **当前**: PLAN.md 中硬编码 `sessions_spawn` / `sessions_yield` 命令
- **目标**: PLAN.md 中使用行为指令标签
- **改动**: 生成 `[DISPATCH]` / `[WAIT]` 标签而非 API 调用

#### `setup-cron-recovery.py`
- **当前**: 生成 OpenClaw cron job JSON
- **目标**: 生成通用调度配置，附带环境适配说明
- **改动**: 输出环境无关的调度描述 + 环境适配附录

---

*创建时间: 2026-07-21*
