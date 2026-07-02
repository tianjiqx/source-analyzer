# Analysis Runner

> 自动化分析工作流执行指南

---

## 快速开始

### 方式 1: 全自动编排（推荐）

```bash
# Step 1: 生成分析计划
python3 ~/.openclaw/workspace/skills/source-analyzer/scripts/generate-analysis-plan.py \
  /path/to/project \
  -o ~/.openclaw/learning/projects/project-name-analysis

# Step 2: 运行编排器（自动执行 + 异常处理 + 健康检查）
python3 ~/.openclaw/workspace/skills/source-analyzer/scripts/orchestrator.py \
  ~/.openclaw/learning/projects/project-name-analysis/ANALYSIS_PLAN.md \
  -o ~/.openclaw/learning/projects/project-name-analysis

# Step 3: 验证结果（编排器已自动执行）
python3 ~/.openclaw/workspace/skills/source-analyzer/scripts/verify-analysis.py \
  ~/.openclaw/learning/projects/project-name-analysis --all
```

### 方式 2: 手动执行（灵活控制）

```bash
# Step 1: 生成分析计划
python3 generate-analysis-plan.py /path/to/project -o /path/to/output

# Step 2: 读取 ANALYSIS_PLAN.md，手动派发 sessions_spawn

# Step 3: 验证分析结果
python3 verify-analysis.py /path/to/output --all
```

---

## 编排器特性

### 1. 健康检查线程

**独立线程**，持续监控任务状态：

| 检查项 | 间隔 | 处理 |
|--------|------|------|
| 任务超时 | 30 秒 | 标记 TIMEOUT，触发重试 |
| 子代理卡死 | 30 秒 | 检查 agent_session_key |
| 异常状态 | 30 秒 | 自动恢复 |

### 2. 异常处理

| 错误类型 | 处理策略 |
|----------|----------|
| timeout | 指数退避重试，简化任务 |
| needs_context | 提供上下文，重试 |
| blocked | 分解任务，重试 |
| permission | 升级，通知用户 |
| rate_limit | 等待 60s+ 重试 |
| out_of_memory | 简化分析 |

### 3. 自动重试

- **最大重试**: 3 次
- **指数退避**: 5s → 10s → 20s
- **升级模型**: 重试时自动升级模型
- **降级策略**: 所有重试失败 → 简化分析

### 4. 断点续传

- 检查点文件: `.checkpoint.json`
- 中断后自动恢复
- 记录错误日志

### 5. 信号处理

- `SIGINT` (Ctrl+C): 保存检查点，优雅退出
- `SIGTERM`: 保存检查点，优雅退出

---

## 编排器流程

```
启动
  │
  ├─ 加载检查点（如有）
  │   └─ 有 → 恢复状态
  │   └─ 无 → 加载计划
  │
  ├─ 启动健康检查线程
  │
  ├─ 执行任务循环
  │   ├─ 派发子代理
  │   ├─ 等待完成
  │   ├─ 两阶段审查
  │   │   ├─ 完整性审查
  │   │   └─ 质量审查
  │   ├─ 成功 → 下一任务
  │   └─ 失败 → 重试/降级
  │
  ├─ 验证结果 (verify-analysis.py)
  │
  ├─ 生成执行摘要
  │
  └─ 停止健康检查
```

---

## 配置

编辑 `orchestrator-config.yaml`:

```yaml
orchestrator:
  max_retries: 3              # 最大重试次数
  task_timeout: 600           # 任务超时（秒）
  health_check_interval: 30   # 健康检查间隔（秒）
  max_concurrent_tasks: 3     # 最大并行任务数
  fallback_to_simplified: true # 失败时降级
```

---

## 输出文件

| 文件 | 内容 |
|------|------|
| `00-README.md` | 项目概览 |
| `01-architecture.md` | 架构设计 |
| `02-core-code.md` | 核心代码 |
| `03-quality-score.md` | 质量评分 |
| `04-learning-value.md` | 学习价值 |
| `INDEX.md` | 索引导航 |
| `ANALYSIS_PLAN.md` | 分析计划 |
| `VERIFICATION_REPORT.md` | 验证报告 |
| `EXECUTION_SUMMARY.json` | 执行摘要 |
| `orchestrator.log` | 运行日志 |
| `.checkpoint.json` | 检查点 |

---

## 故障排查

### 任务超时

```bash
# 查看日志
tail -f orchestrator.log

# 检查检查点
cat .checkpoint.json | jq '.tasks[] | select(.status == "timeout")'

# 手动重试
python3 orchestrator.py ANALYSIS_PLAN.md --max-retries 5 --timeout 900
```

### 子代理卡死

健康检查线程会自动检测并标记 TIMEOUT。

### 权限错误

编排器会升级权限或通知用户。

---

*最后更新: 2026-06-27*