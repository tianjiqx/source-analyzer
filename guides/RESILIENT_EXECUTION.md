# 弹性执行指南：自动重试与恢复

> **核心问题**：分析大项目时，LLM 并发限制 / rate limit 导致 subagent 失败 → 主 agent 停止 → 分析中止。
>
> **解决方案**：三层防线 + 自动恢复机制，实现无人值守的分析执行。

---

## 问题分析

### 失败场景

```
主 Agent 派发 8 个并行 subagent
    ├── subagent-1 ✅ 完成
    ├── subagent-2 ✅ 完成
    ├── subagent-3 ❌ rate_limit 错误
    ├── subagent-4 ❌ rate_limit 错误
    ├── subagent-5 ✅ 完成
    ├── subagent-6 ❌ context overflow
    ├── subagent-7 ✅ 完成
    └── subagent-8 ❌ timeout

结果：4 个失败，主 Agent 不知道怎么重试 → 分析不完整
```

### 根本原因

1. **sessions_spawn 失败后没有重试逻辑** — 主 agent 看到失败就继续下一步
2. **主 agent context 耗尽** — 大量任务压垮主 agent 的上下文窗口
3. **/goal 命令的局限** — 需要人工触发"继续"，不是真正的自动恢复
4. **没有持久化的失败追踪** — 跨 session 无法恢复

---

## 三层防线架构

```
Layer 1: 任务级重试 (Subagent 内部)
├── 每个 subagent 内部捕获 rate_limit
├── 自主等待 + 重试（最多 3 次）
└── 失败则在 .task-report.json 标记 status=failed

Layer 2: 批次级恢复 (--execute 全自动)
├── resilient-runner.py --execute 直接调用 openclaw agent CLI
├── 每个失败任务通过 openclaw agent --session-key 独立派发
├── 指数退避重试，每任务最多 5 次
├── 持久化状态到 .resilient-checkpoint.json
└── 不需要主 agent 上下文参与

Layer 3: 全局续传 (Cron 自动恢复)
├── Cron 定期触发 isolated session
├── Session 运行 resilient-runner.py --execute
├── 脚本内部直接调用 openclaw agent CLI 派发重试
└── 全部完成后自动删除 cron job
```

### 关键机制：openclaw agent CLI

`resilient-runner.py --execute` 通过 `openclaw agent` 命令直接派发分析任务：

```bash
# 每个失败任务都通过独立 session 派发
openclaw agent \
    --session-key analysis-retry-lib-encoding \
    --message "[弹性重试 #2] 分析模块: lib/encoding..." \
    --timeout 600
```

这样即使主 agent session 已经结束，脚本也能独立完成重试。

---

## 快速开始

### 方案 A：一次性设置（推荐）

在开始分析前，运行：

```bash
# 1. 生成分析计划（如 PLAN.md）
python3 scripts/recursive-orchestrator.py output-dir \
    --manifest module-manifest.json \
    --project-path /path/to/project \
    -o output-dir/PLAN.md

# 2. 初始化弹性检查点
python3 scripts/resilient-runner.py \
    --output-dir output-dir \
    --project-path /path/to/project \
    --plan output-dir/PLAN.md \
    --init

# 3. 设置 cron 自动恢复
python3 scripts/setup-cron-recovery.py \
    --output-dir output-dir \
    --project-path /path/to/project \
    --plan output-dir/PLAN.md \
    --interval 30
```

### 方案 B：分析过程中添加

如果分析已经开始并遇到失败：

```bash
# 1. 同步当前状态
python3 scripts/resilient-runner.py \
    --output-dir output-dir \
    --sync

# 2. 查看状态
python3 scripts/resilient-runner.py \
    --output-dir output-dir \
    --status

# 3. 自动恢复
python3 scripts/resilient-runner.py \
    --output-dir output-dir \
    --project-path /path/to/project \
    --plan output-dir/PLAN.md \
    --auto-resume
```

---

## 主 Agent 执行协议

当主 agent 执行源码分析时，**必须遵循以下协议**：

### Phase 1: 计划生成

```python
# 1. 生成 PLAN.md
# 2. 初始化弹性检查点
# 3. 设置 cron 自动恢复
# 4. 开始派发任务
```

### Phase 2: 任务派发与重试

```python
# 对每个批次的任务：
for batch in batches:
    # 1. 派发本批次任务
    for task in batch:
        sessions_spawn(task=task_description, label=task_label, mode="run")
    
    # 2. 等待完成
    sessions_yield(message="等待批次完成")
    
    # 3. 同步状态
    exec("python3 scripts/resilient-runner.py --output-dir {output_dir} --sync")
    
    # 4. 检查失败任务
    result = exec("python3 scripts/resilient-runner.py --output-dir {output_dir} --auto-resume --json")
    
    # 5. 如果有失败任务，重试
    if result.status == "needs_retry":
        for failed_task in result.retryable_tasks:
            # 检查退避时间
            if can_retry_now(failed_task):
                sessions_spawn(task=retry_description, label=f"retry-{task_name}")
            else:
                # 记录等待，继续下一个
        
        # 等待重试完成
        sessions_yield(message="等待重试完成")
        
        # 再次检查
        result = exec("python3 scripts/resilient-runner.py ...")
    
    # 6. 更新检查点
    exec("python3 scripts/resilient-runner.py --output-dir {output_dir} --sync")
```

### Phase 3: 收尾

```python
# 1. 最终验证
exec("python3 scripts/verify-analysis.py {output_dir} --recursive")

# 2. 计划验收
exec("python3 scripts/plan-tracker.py verify ...")

# 3. 移除 cron job
cron(action=remove, jobId="analysis-recovery-{project_name}")

# 4. 更新 MEMORY.md
```

---

## Subagent 任务模板（带弹性重试）

派发给 subagent 的任务描述应包含以下弹性指令：

```
你正在执行源码分析任务。

## 任务信息
- 模块: {module_name}
- 路径: {project_path}/{module_path}
- 输出目录: {output_dir}/10-module-deep/{module_slug}/

## 弹性执行规则
1. 如果遇到 rate_limit 错误，等待 30 秒后自动重试
2. 如果连续 3 次 rate_limit，在 .task-report.json 标记 status="failed"，error="rate_limit"
3. 如果遇到 context overflow，减少分析范围（只做 Layer 1）
4. 如果遇到其他错误，记录到 .task-report.json 的 error 字段

## 完成报告
分析完成后，在输出目录生成 .task-report.json:
{{
  "module": "{module_name}",
  "status": "completed" | "failed" | "partial",
  "files_generated": ["INDEX.md", ...],
  "files_count": N,
  "error": "",
  "retry_count": 0,
  "key_findings": ["发现1", "发现2"]
}}

## 分析要求
（同标准分析要求...）
```

---

## Cron 自动恢复配置

### 创建自动恢复 Cron Job

```
cron(action=add, job={{
    "name": "analysis-recovery-{project_name}",
    "description": "自动恢复 {project_name} 源码分析的失败任务",
    "schedule": {{
        "kind": "every",
        "everyMs": 1800000  // 30分钟
    }},
    "sessionTarget": "isolated",
    "payload": {{
        "kind": "agentTurn",
        "message": "[自动恢复] 检查并重试失败的分析任务...",
        "lightContext": true
    }},
    "delivery": {{
        "mode": "none"  // 静默执行
    }},
    "failureAlert": {{
        "after": 3,
        "mode": "announce",
        "cooldownMs": 3600000
    }}
}})
```

### Cron Job 的 AgentTurn Prompt 模板

```
[自动恢复] 源码分析任务弹性恢复

执行以下命令检查失败任务：
```bash
python3 {runner_path} --output-dir {output_dir} \\
    --project-path {project_path} \\
    --plan {plan_file} --auto-resume --json
```

根据 JSON 输出处理：
1. status="needs_retry": 读取 instructions，对每个任务 sessions_spawn 派发，然后 sessions_yield
2. status="completed": 所有任务完成，用 cron(action=remove) 删除自身
3. status="waiting_backoff": 回复 NO_REPLY
4. status="all_exhausted": 通知用户有任务超过最大重试

重试策略：
- rate_limit 错误: 等待 60s 后重试
- timeout 错误: 立即重试（可能需要减少分析范围）
- 其他错误: 记录后重试
- 每个任务最多重试 5 次
```

---

## 退避策略详解

### 重试延迟表

| 重试次数 | 标准延迟 | Rate Limit 延迟 | 说明 |
|----------|----------|-----------------|------|
| 第 1 次 | 60s | 90s | 快速重试 |
| 第 2 次 | 120s | 150s | 等待限流恢复 |
| 第 3 次 | 240s | 270s | 较长等待 |
| 第 4 次 | 480s | 510s | 长等待 |
| 第 5 次 | 960s | 990s | 最后一次 |

### 降级策略

超过 5 次重试后，自动降级：

```
重试 5 次失败
    ├── Layer 3 文件分析 → 跳过（不影响整体）
    ├── Layer 2 模块分析 → 简化分析（只做概览）
    └── Layer 1 项目分析 → 通知用户（必须手动处理）
```

---

## 监控与调试

### 查看分析状态

```bash
# 快速状态
python3 scripts/resilient-runner.py --output-dir {dir} --status

# JSON 输出（脚本集成）
python3 scripts/resilient-runner.py --output-dir {dir} --auto-resume --json
```

### 检查点文件

`.resilient-checkpoint.json` 包含完整的状态信息：

```json
{{
  "project_name": "my-project",
  "phase": "phase2",
  "total_tasks": 23,
  "tasks": {{
    "task_1": {{
      "name": "lib/storage",
      "status": "completed",
      "retry_count": 0,
      "actual_files": ["10-module-deep/lib-storage/INDEX.md", ...]
    }},
    "task_5": {{
      "name": "lib/metricsql",
      "status": "failed",
      "retry_count": 2,
      "last_error": "rate_limit after 3 retries",
      "next_retry": "2026-07-03T22:15:00"
    }}
  }},
  "stats": {{
    "completed": 18,
    "failed": 2,
    "pending": 3,
    "completion_rate": 78.3
  }}
}}
```

### 常见问题

**Q: Cron job 没有触发？**
A: 检查 cron 状态：`cron(action=status)`，确保 job enabled=true

**Q: 重试次数不重置？**
A: 设计如此。重试次数是累计的，防止无限重试。如需重置，删除 `.resilient-checkpoint.json`。

**Q: 主 agent 和 cron 同时运行？**
A: 安全。检查点文件有原子写入，且任务是幂等的（已完成的任务会被跳过）。

**Q: 如何手动重置某个任务？**
A: 编辑 `.resilient-checkpoint.json`，将任务的 status 改为 "pending"，retry_count 改为 0。

---

## 与 SKILL.md 集成

在 SKILL.md 的执行纪律部分增加：

```markdown
## 弹性执行纪律

1. **先初始化弹性检查点** — 分析开始前运行 resilient-runner.py --init
2. **设置 cron 自动恢复** — 使用 setup-cron-recovery.py 设置定时恢复
3. **批次间同步状态** — 每批 sessions_yield 后运行 resilient-runner.py --sync
4. **失败任务自动重试** — 使用 resilient-runner.py --auto-resume 检测并重试
5. **完成后清理** — 分析结束后移除 cron job
```

---

## 完整工作流示例

```
用户: "递归深度分析 VictoriaMetrics 项目"

主 Agent:
1. 生成模块清单 → module-manifest.json
2. 生成分析计划 → PLAN.md
3. 初始化弹性检查点 → .resilient-checkpoint.json
4. 设置 cron 自动恢复（每 30 分钟）
5. 开始 Phase 1: 项目级分析（sessions_spawn + yield）
6. 开始 Phase 2: 模块级分析
   - 批次 1: 6 个模块并行
   - sessions_yield → 检查结果
   - resilient-runner.py --sync → 更新状态
   - 发现 2 个失败 → --auto-resume 生成重试指令
   - 重新 spawn 失败任务
   - sessions_yield → 检查结果
   - 全部成功 → 进入下一批次
7. Phase 3: 项目级总结
8. 验证 + 清理

如果主 Agent 中途停止：
- Cron 每 30 分钟检测 → 自动恢复
- 无需人工干预
```

---

*最后更新: 2026-07-03*
