# 计划驱动执行指南

> **核心原则**：先有计划，再按计划执行，最后按计划验收。
>
> 计划文件是分析的"契约"——执行中随时对照，执行后逐项检查。

---

## 设计动机

### 当前问题

```
生成计划 → 计划文件躺在磁盘上 → AI 自由发挥 → 结果与计划无关
```

### 改进目标

```
生成计划 → 保存为 PLAN.md → 严格按 PLAN.md 执行 → 检查点追踪 → 按计划验收
```

---

## 核心机制

### 1. 计划即契约

分析开始前，必须先生成 `PLAN.md` 并保存到输出目录。PLAN.md 包含：

- **模块清单**：每个模块的名称、路径、策略、预期输出文件
- **执行批次**：并行分批策略
- **验收标准**：每个任务的完成条件

### 2. 检查点追踪

执行过程中维护 `.checkpoint.json`，记录每个任务的状态：

```json
{
  "plan_version": "1.0",
  "plan_path": "PLAN.md",
  "started_at": "2026-07-02T22:00:00",
  "last_updated": "2026-07-02T22:30:00",
  "phases": {
    "phase_1_scan": { "status": "completed", "completed_at": "..." },
    "phase_2_modules": {
      "status": "in_progress",
      "total": 23,
      "completed": 5,
      "in_progress": 3,
      "pending": 15,
      "failed": 0,
      "tasks": {
        "lib/storage": { "status": "completed", "output": "10-module-deep/lib-storage/", "docs_generated": 12 },
        "lib/encoding": { "status": "completed", "output": "10-module-deep/lib-encoding/", "docs_generated": 7 },
        "lib/metricsql": { "status": "in_progress", "started_at": "..." },
        "lib/promscrape": { "status": "pending" }
      }
    },
    "phase_3_summary": { "status": "pending" }
  }
}
```

### 3. 计划驱动的 sessions_spawn

每个子代理任务必须：
- 在 task 描述中包含计划引用（`计划参考: PLAN.md Task #5`）
- 在输出中生成 `.task-report.json`（记录实际生成了哪些文件）
- 使用统一的输出目录约定

### 4. 验收对比

分析完成后，运行 `plan-vs-actual` 检查：

```
PLAN.md 预期输出          vs          实际生成
├── lib/storage/                      ├── lib/storage/
│   ├── INDEX.md     ✅               │   ├── INDEX.md
│   ├── 00-overview/ (4 files)        │   ├── 00-overview/ (4 files) ✅
│   └── 20-file-level/ (8 files)      │   └── 20-file-level/ (6 files) ⚠️ 少 2 个
├── lib/encoding/                     ├── lib/encoding/
│   ├── INDEX.md     ✅               │   ├── INDEX.md
│   └── 00-overview/ (4 files)        │   └── 00-overview/ (3 files) ⚠️ 少 1 个
└── ...
```

---

## 执行流程

### Step 1: 生成计划（PLAN.md）

```bash
# 递归模式
python3 scripts/generate-module-manifest.py /path/to/project \
  -o output-dir/module-manifest.json

python3 scripts/recursive-orchestrator.py output-dir \
  --manifest output-dir/module-manifest.json \
  --project-path /path/to/project \
  --max-parallel 8 \
  --priority-only \
  -o output-dir/PLAN.md
```

### Step 2: 初始化检查点

```bash
python3 scripts/plan-tracker.py init \
  --plan output-dir/PLAN.md \
  --manifest output-dir/module-manifest.json \
  --output-dir output-dir
```

生成 `.checkpoint.json`，所有任务状态为 `pending`。

### Step 3: 按计划执行

#### Phase 1: 项目级分析（串行）

```
# 读取 PLAN.md 中的 Phase 1 任务
# 执行项目级分析
# 完成后更新检查点
python3 scripts/plan-tracker.py complete \
  --checkpoint output-dir/.checkpoint.json \
  --task phase_1_scan
```

#### Phase 2: 模块级递归（分批并行）

每个 sessions_spawn 任务**必须包含**：

1. **计划引用**：告诉子代理它在执行 PLAN.md 中的哪个任务
2. **预期输出清单**：子代理应该生成哪些文件
3. **报告要求**：完成后生成 `.task-report.json`

```
sessions_spawn task="""
[计划驱动执行] PLAN.md Task #{task_id}

你正在执行递归深度分析计划中的一个模块任务。
全局计划文件: {output_dir}/PLAN.md
你的任务: 分析模块 {module_name}

=== 模块信息 ===
- 路径: {project_path}/{module_path}
- 文件数: {files} (含子目录)
- 行数: {lines}
- 规模: {size_category}
- 重要性: {importance}
- 分析策略: {strategy}

=== 预期输出 ===
输出目录: {output_dir}/10-module-deep/{module_slug}/

必须生成:
1. INDEX.md - 模块索引
2. 00-overview/README.md - 模块概览
3. 00-overview/architecture.md - 模块架构
4. 00-overview/quality-score.md - 质量评分
5. 00-overview/learning-value.md - 学习价值
{layer_2_files}
{layer_3_files}

=== 分析维度 ===
- 模块职责与定位（在项目中的角色）
- 核心数据结构
- 关键算法/逻辑
- 接口设计（对外暴露的 API）
- 依赖关系（上下游模块）
- 设计模式
- 质量评分
- 学习价值

每个文档至少包含 1 个 Mermaid 图表。

=== 完成报告 ===
分析完成后，在输出目录生成 .task-report.json:
{{
  "module": "{module_name}",
  "task_id": #{task_id},
  "status": "completed",
  "files_generated": ["INDEX.md", "00-overview/README.md", ...],
  "files_count": N,
  "quality_self_score": N,  // 自评 0-100
  "key_findings": ["发现1", "发现2"],
  "issues": []
}}

参考模板:
- guides/FILE_LEVEL_ANALYSIS.md
- templates/general/
""" label="module-{module_slug}"
```

#### 批次间管理

```
# 批次 1 完成后
sessions_yield message="等待批次 1 完成"

# 更新检查点
python3 scripts/plan-tracker.py sync \
  --checkpoint output-dir/.checkpoint.json \
  --output-dir output-dir

# 检查是否有失败的任务
python3 scripts/plan-tracker.py status \
  --checkpoint output-dir/.checkpoint.json

# 如果有失败，重试
python3 scripts/plan-tracker.py retry-failed \
  --checkpoint output-dir/.checkpoint.json
```

#### Phase 3: 项目级总结（串行）

```
# 读取所有模块的 .task-report.json
# 生成跨模块总结
python3 scripts/plan-tracker.py complete \
  --checkpoint output-dir/.checkpoint.json \
  --task phase_3_summary
```

### Step 4: 计划验收

```bash
# 对比计划与实际输出
python3 scripts/plan-tracker.py verify \
  --plan output-dir/PLAN.md \
  --checkpoint output-dir/.checkpoint.json \
  --output-dir output-dir
```

输出 `PLAN_VERIFICATION_REPORT.md`：

```markdown
# 计划验收报告

## 总体符合度: 87%

## 模块符合度

| 模块 | 预期文件 | 实际文件 | 符合度 | 状态 |
|------|----------|----------|--------|------|
| lib/storage | 12 | 12 | 100% | ✅ |
| lib/encoding | 7 | 7 | 100% | ✅ |
| lib/metricsql | 10 | 8 | 80% | ⚠️ |
| lib/promscrape | 8 | 5 | 62% | ❌ |

## 缺失文件

| 模块 | 缺失文件 | 原因 |
|------|----------|------|
| lib/metricsql | 20-file-level/metricsql-parser.md | 未生成 |
| lib/promscrape | 00-overview/quality-score.md | 未生成 |

## 建议

- 补充 lib/promscrape 的质量评分文档
- lib/metricsql 缺失 2 个文件分析，需补充
```

### Step 5: 最终验证

```bash
# 标准验证
python3 scripts/verify-analysis.py output-dir --recursive

# 计划验收
python3 scripts/plan-tracker.py verify \
  --plan output-dir/PLAN.md \
  --checkpoint output-dir/.checkpoint.json \
  --output-dir output-dir
```

---

## PLAN.md 结构规范

PLAN.md 不只是执行计划，还是验收标准。每个任务必须有明确的预期输出：

```markdown
# 递归深度分析计划

## 元信息
- 项目: VictoriaMetrics
- 计划版本: 1.0
- 生成时间: 2026-07-02 22:00
- 模块清单: module-manifest.json

## Phase 1: 项目级分析
- 任务数: 1
- 预期输出: 4 文档

### Task 1: 项目级分析 [status: pending]
- 输出目录: 00-project-level/
- 预期文件:
  - 00-project-level/README.md
  - 00-project-level/architecture.md
  - 00-project-level/quality-score.md
  - 00-project-level/learning-value.md
- 完成条件: 4 个文件全部存在，无 placeholder

## Phase 2: 模块级递归分析
- 任务数: 23 (仅 high 重要性)
- 并行批次: 4 批 × 6 并行
- 预期输出: ~238 文档

### Task 2: app/vmselect/promql [status: pending]
- 模块: app/vmselect/promql
- 策略: full_three_layers
- 预期文件:
  - 10-module-deep/app-vmselect-promql/INDEX.md
  - 10-module-deep/app-vmselect-promql/00-overview/README.md
  - 10-module-deep/app-vmselect-promql/00-overview/architecture.md
  - 10-module-deep/app-vmselect-promql/00-overview/quality-score.md
  - 10-module-deep/app-vmselect-promql/00-overview/learning-value.md
  - 10-module-deep/app-vmselect-promql/20-file-level/ (5-10 files)
- 完成条件: INDEX.md 存在 + Layer 1 完整 + 至少 5 个文件分析

### Task 3: lib/encoding [status: pending]
...

## Phase 3: 项目级总结
- 任务数: 1
- 预期输出: 5 文档

### Task N: 跨模块总结 [status: pending]
- 预期文件:
  - 10-module-deep/_MODULE_SUMMARY.md
  - 20-cross-module/comparison.md
  - 20-cross-module/patterns.md
  - 20-cross-module/recommendations.md
  - 20-cross-module/dependency-graph.md
- 完成条件: 5 个文件全部存在
```

---

## 子代理完成约定

每个子代理**必须**在完成后生成两个文件：

### 1. .task-complete.json（完成签名 — 弹性运行器主要判断依据）

```json
{
  "task": "lib/encoding",
  "status": "completed",
  "files": {
    "INDEX.md": {"size": 3500, "lines": 85, "has_mermaid": true},
    "00-overview/README.md": {"size": 5200, "lines": 120, "has_mermaid": true}
  },
  "completed_at": "2026-07-03T22:30:00",
  "total_files": 5,
  "total_size": 19500,
  "has_placeholder": false
}
```

弹性运行器验证签名中声称的文件：
- 文件是否实际存在
- 文件大小是否 >= 200B
- 内容是否有结构标记（标题/表格/代码块）
- 是否包含占位符（TODO/TBD/待补充）

### 2. .task-report.json（过程报告）

```json
{
  "module": "lib/encoding",
  "task_id": 5,
  "status": "completed",
  "files_generated": ["INDEX.md", "00-overview/README.md", ...],
  "files_count": 7,
  "key_findings": ["发现1"],
  "issues": []
}
```

**如果 LLM 因故中断，不会生成签名文件** — 弹性运行器会检测到缺失签名，回退到文件内容验证。

---

## 与 SKILL.md 集成

在 SKILL.md 的执行注意事项中增加：

```markdown
## 执行纪律

1. **先有计划再执行** — 任何分析模式都必须先生成 PLAN.md
2. **按计划执行** — 子代理任务必须引用 PLAN.md 中的 Task ID
3. **追踪进度** — 使用 plan-tracker.py 维护检查点
4. **按计划验收** — 分析完成后运行计划验收，输出符合度报告
5. **补救缺失** — 对计划验收中发现缺失的文档，补充分析
```

---

*最后更新: 2026-07-02*
