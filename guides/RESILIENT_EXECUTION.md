# 弹性执行指南：自动重试与恢复

> **核心问题**：分析大项目时，LLM 并发限制 / rate limit 导致子任务失败 → 主 agent 停止 → 分析中止。
>
> **解决方案**：三层防线 + 自动恢复机制，实现无人值守的分析执行。

---

## 问题分析

### 失败场景

```
主 Agent 派发 8 个并行子任务
    ├── 子任务-1 ✅ 完成
    ├── 子任务-2 ✅ 完成
    ├── 子任务-3 ❌ rate_limit 错误
    ├── 子任务-4 ❌ rate_limit 错误
    ├── 子任务-5 ✅ 完成
    ├── 子任务-6 ❌ context overflow
    ├── 子任务-7 ✅ 完成
    └── 子任务-8 ❌ timeout

结果：4 个失败，主 Agent 不知道怎么重试 → 分析不完整
```

### 根本原因

1. **子任务派发失败后没有重试逻辑** — 主 agent 看到失败就继续下一步
2. **主 agent context 耗尽** — 大量任务压垮主 agent 的上下文窗口
3. **goal 命令的局限** — 需要人工触发"继续"，不是真正的自动恢复
4. **没有持久化的失败追踪** — 跨 session 无法恢复

---

## 三层防线架构

```
Layer 1: 任务级重试 (子任务内部)
├── 每个子任务内部捕获 rate_limit
├── 自主等待 + 重试（最多 3 次）
└── 失败则在 .task-report.json 标记 status=failed

Layer 2: 批次级恢复 (--auto-resume)
├── resilient-runner.py --auto-resume 检测失败任务
├── 生成环境无关的 [DISPATCH] 重试指令
├── 指数退避重试，每任务最多 5 次
├── 持久化状态到 .resilient-checkpoint.json
└── 不需要主 agent 上下文参与

Layer 3: 全局续传 (定时自动恢复)
├── 如环境支持，定时触发独立 session
├── Session 运行 resilient-runner.py --continue
├── 生成 continuation prompt 让恢复 session 自主执行
└── 全部完成后移除定时任务
```

### 环境差异

| 环境 | Layer 3 实现 | 自动化程度 |
|------|-------------|-----------|
| **OpenClaw** | cron + isolated session | 全自动 |
| **opencode** | 系统 crontab + CLI | 半自动 |
| **纯 CLI** | 手动运行 --continue | 手动 |

---

## 快速开始

### 方案 A：一次性设置（推荐）

在开始分析前，运行：

```bash
# 1. 生成分析计划（如 PLAN.md）
python3 $SKILL_DIR/scripts/recursive-orchestrator.py output-dir \
    --manifest module-manifest.json \
    --project-path /path/to/project \
    -o output-dir/PLAN.md

# 2. 初始化弹性检查点
python3 $SKILL_DIR/scripts/resilient-runner.py \
    --output-dir output-dir \
    --project-path /path/to/project \
    --plan output-dir/PLAN.md \
    --init

# 3. 设置定时恢复（多环境适配输出）
python3 $SKILL_DIR/scripts/setup-cron-recovery.py \
    --output-dir output-dir \
    --project-path /path/to/project \
    --plan output-dir/PLAN.md \
    --interval 30
```

### 方案 B：分析过程中添加

如果分析已经开始并遇到失败：

```bash
# 1. 同步当前状态
python3 $SKILL_DIR/scripts/resilient-runner.py \
    --output-dir output-dir \
    --sync

# 2. 查看状态
python3 $SKILL_DIR/scripts/resilient-runner.py \
    --output-dir output-dir \
    --status

# 3. 自动恢复
python3 $SKILL_DIR/scripts/resilient-runner.py \
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
# 3. 如环境支持，设置定时恢复
# 4. 开始派发任务
```

### Phase 2: 任务派发与重试

```python
# 对每个批次的任务：
for batch in batches:
    # 1. 派发本批次任务（使用 [DISPATCH] 行为指令）
    for task in batch:
        [DISPATCH: task=task_description, label=task_label]
    
    # 2. 等待完成
    [WAIT: "等待批次完成"]
    
    # 3. 同步状态
    exec("python3 $SKILL_DIR/scripts/resilient-runner.py --output-dir {output_dir} --sync")
    
    # 4. 检查失败任务
    result = exec("python3 $SKILL_DIR/scripts/resilient-runner.py --output-dir {output_dir} --auto-resume --json")
    
    # 5. 如果有失败任务，重试
    if result.status == "needs_retry":
        for failed_task in result.retryable_tasks:
            # 检查退避时间
            if can_retry_now(failed_task):
                [DISPATCH: task=retry_description, label=f"retry-{task_name}"]
            else:
                # 记录等待，继续下一个
        
        # 等待重试完成
        [WAIT: "等待重试完成"]
        
        # 再次检查
        result = exec("python3 $SKILL_DIR/scripts/resilient-runner.py ...")
    
    # 6. 更新检查点
    exec("python3 $SKILL_DIR/scripts/resilient-runner.py --output-dir {output_dir} --sync")
```

### Phase 3: 收尾

```python
# 1. 最终验证
exec("python3 $SKILL_DIR/scripts/verify-analysis.py {output_dir} --recursive")

# 2. 计划验收
exec("python3 $SKILL_DIR/scripts/plan-tracker.py verify ...")

# 3. 移除定时恢复任务（如已设置）
#    OpenClaw: cron(action=remove, jobId="analysis-recovery-{project_name}")
#    系统 crontab: crontab -l | grep -v '{project_name}' | crontab -

# 4. 更新记忆文件
```

---

## 子任务模板（带弹性重试）

派发给子任务的描述应包含以下弹性指令：

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
{
  "module": "{module_name}",
  "status": "completed" | "failed" | "partial",
  "files_generated": ["INDEX.md", ...],
  "files_count": N,
  "error": "",
  "retry_count": 0,
  "key_findings": ["发现1", "发现2"]
}

## 分析要求
（同标准分析要求...）
```

---

## 定时恢复配置

### 多环境适配

`setup-cron-recovery.py` 输出三种环境的恢复配置：

1. **OpenClaw**: cron job JSON（通过 cron 工具创建 isolated session）
2. **系统 crontab**: 标准 crontab 条目（opencode / 纯 CLI）
3. **手动命令**: 直接运行的恢复命令（无定时能力时）

### OpenClaw 环境

```
cron(action=add, job={
    "name": "analysis-recovery-{project_name}",
    "schedule": {"kind": "every", "everyMs": 1800000},
    "sessionTarget": "isolated",
    "payload": {"kind": "agentTurn", "message": "...", "lightContext": true},
    "delivery": {"mode": "none"},
    ...
})
```

### 系统 crontab (opencode / 纯 CLI)

```bash
*/30 * * * * cd /path/to/output && python3 $SKILL_DIR/scripts/resilient-runner.py \
    --output-dir /path/to/output \
    --project-path /path/to/project \
    --plan /path/to/PLAN.md --continue \
    >> /path/to/output/recovery.log 2>&1
```

### 定时恢复 Session 的行为

恢复 session 被触发后的行为：

1. 运行 `resilient-runner.py --continue` 检查失败任务
2. 根据 JSON 输出处理：
   - `needs_retry`: 读取 continuation prompt，用 `[DISPATCH]` 派发，然后 `[WAIT]`
   - `completed`: 所有任务完成，移除自身定时任务，`[NOTIFY_SILENT]`
   - `waiting_backoff`: `[NOTIFY_SILENT]`
   - `all_exhausted`: 通知用户有任务超过最大重试

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
python3 $SKILL_DIR/scripts/resilient-runner.py --output-dir {dir} --status

# JSON 输出（脚本集成）
python3 $SKILL_DIR/scripts/resilient-runner.py --output-dir {dir} --auto-resume --json
```

### 检查点文件

`.resilient-checkpoint.json` 包含完整的状态信息：

```json
{
  "project_name": "my-project",
  "phase": "phase2",
  "total_tasks": 23,
  "tasks": {
    "task_1": {
      "name": "lib/storage",
      "status": "completed",
      "retry_count": 0,
      "actual_files": ["10-module-deep/lib-storage/INDEX.md", ...]
    },
    "task_5": {
      "name": "lib/metricsql",
      "status": "failed",
      "retry_count": 2,
      "last_error": "rate_limit after 3 retries",
      "next_retry": "2026-07-03T22:15:00"
    }
  },
  "stats": {
    "completed": 18,
    "failed": 2,
    "pending": 3,
    "completion_rate": 78.3
  }
}
```

### 常见问题

**Q: 定时恢复没有触发？**
- OpenClaw: 检查 cron 状态：`cron(action=status)`，确保 job enabled=true
- 系统 crontab: 检查 `crontab -l` 和 recovery.log

**Q: 重试次数不重置？**
A: 设计如此。重试次数是累计的，防止无限重试。如需重置，删除 `.resilient-checkpoint.json`。

**Q: 主 agent 和定时恢复同时运行？**
A: 安全。检查点文件有原子写入，且任务是幂等的（已完成的任务会被跳过）。

**Q: 如何手动重置某个任务？**
A: 编辑 `.resilient-checkpoint.json`，将任务的 status 改为 "pending"，retry_count 改为 0。

---

## 完整工作流示例

```
用户: "递归深度分析 VictoriaMetrics 项目"

主 Agent:
1. 生成模块清单 → module-manifest.json
2. 生成分析计划 → PLAN.md
3. 初始化弹性检查点 → .resilient-checkpoint.json
4. 如环境支持，设置定时恢复（每 30 分钟）
5. 开始 Phase 1: 项目级分析（[DISPATCH] + [WAIT]）
6. 开始 Phase 2: 模块级分析
   - 批次 1: 6 个模块并行
   - [WAIT] → 检查结果
   - resilient-runner.py --sync → 更新状态
   - 发现 2 个失败 → --auto-resume 生成重试指令
   - 重新 [DISPATCH] 失败任务
   - [WAIT] → 检查结果
   - 全部成功 → 进入下一批次
7. Phase 3: 项目级总结
8. 验证 + 清理

如果主 Agent 中途停止：
- 如环境支持定时恢复 → 自动恢复（OpenClaw cron / 系统 crontab）
- 否则 → 手动运行 resilient-runner.py --continue
```

---

*最后更新: 2026-07-21*
