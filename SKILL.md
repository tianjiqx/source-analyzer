---
name: source-analyzer
description: 开源项目源码分析系统化工作流。支持三层渐进式分析（项目级→模块级→文件粒度）和递归深度分析模式（大型项目模块级递归）。专项模板（LLM Agent/数据库/基础设施），自动生成 Mermaid 图表。
metadata: {"openclaw":{"emoji":"🔬"}}
---

# Source Analyzer

开源项目源码分析的系统化工作流。

## 核心特性

| 特性 | 说明 |
|------|------|
| **三层渐进式分析** | 项目级 → 模块级 → 文件粒度 |
| **🔁 递归深度分析** | 大型项目模块级递归，每个模块完整三层分析 |
| **专项分析模板** | LLM Agent（11维度）、数据库（10维度）、基础设施 |
| **可视化输出** | 自动生成 Mermaid 图表（架构图/时序图/类图） |
| **原则蒸馏** | 提炼可移植设计原则（Golden Rules）和陷阱（Gotchas） |
| **自动化脚本** | 项目检测、模块清单生成、递归编排、验证 |
| **🔄 弹性重试** | LLM rate limit / 并发失败自动重试（最多 5 次），cron 自动恢复 |
| **📌 Goal 持久化** | 任务状态写入文件，会话中断后可恢复，不丢失进度 |

---

## 📌 Goal 持久化协议

> **核心问题**：分析任务耗时长（4-8h），会话中断后 goal 状态丢失，进度无法恢复。
>
> **解决方案**：任务状态持久化到文件 `~/.openclaw/workspace/active-goals.json`，每次会话开始时检查未完成任务。

### 执行前：注册 Goal（必做）

分析开始前，**立即**注册 goal：

```bash
python3 scripts/goal-tracker.py register \
  --objective "深度分析 VictoriaMetrics 项目" \
  --project "VictoriaMetrics" \
  --output-dir "~/.openclaw/learning/projects/victoriametrics" \
  --mode "recursive_deep" \
  --total-tasks 42 \
  --plan-file "~/.openclaw/learning/projects/victoriametrics/PLAN.md"
```

输出：
```
✅ 已注册 goal: goal-20260706-142500
   目标: 深度分析 VictoriaMetrics 项目
   项目: VictoriaMetrics
   模式: recursive_deep
   输出: ~/.openclaw/learning/projects/victoriametrics
```

### 执行中：同步进度（每批次后）

每个批次完成后更新进度：

```bash
python3 scripts/goal-tracker.py update \
  --goal-id "goal-20260706-142500" \
  --phase "Phase 2: 模块级递归分析 (批次 2/5)" \
  --completed 15
```

### 执行后：标记完成（闭环动作）

分析完成后标记 goal 完成：

```bash
python3 scripts/goal-tracker.py complete --goal-id "goal-20260706-142500"
```

### 会话恢复：检查未完成任务

**每次会话开始时**（包括 heartbeat），检查未完成任务：

```bash
python3 scripts/goal-tracker.py check
```

如果发现未完成任务，通知用户并提供恢复选项。

### 查看任务列表

```bash
python3 scripts/goal-tracker.py list
```

---

## 分析深度选择

```
用户请求分析项目
  │
  ├─ 快速了解架构? → DeepWiki MCP（无需下载）
  │
  ├─ 需要源码分析?
  │   │
  │   ├─ 只了解整体? → Layer 1 (项目级, 3-6 文档)
  │   │
  │   ├─ 需要理解模块? → Layer 1+2 (项目级+模块级)
  │   │
  │   ├─ 需要深入关键文件? → Layer 1+2+3 (完整三层)
  │   │
  │   ├─ 大型项目彻底分析? → 🔁 递归深度分析（模块级递归）
  │   │
  │   └─ 针对特定文件? → Layer 3 (指定文件)
  │
  └─ 不确定? → 先用 DeepWiki，再按需升级
```

### 分析深度对比

| 深度 | 输出 | 时间 | 适合场景 |
|------|------|------|----------|
| **Layer 1** | 3-6 文档 | 10-20min | 快速了解、技术调研 |
| **Layer 2** | 每模块 3 文档 | 每模块 10-15min | 理解架构、设计借鉴 |
| **Layer 3** | 每文件 1 文档 | 每文件 5-10min | 深度学习、二次开发 |
| **🔁 递归深度** | 100-300+ 文档 | 4-8h | 大型项目彻底分析 |

---

## 快速开始

### 自动化流程（推荐）

```bash
# Step 1: 智能分析（自动检测项目类型 + 推荐模板）
# ⚠️ 必须传入 --model 参数记录当前使用的模型名
python3 scripts/smart-analyze.py /path/to/project \
  --model "$(cat ~/.openclaw/.current-model 2>/dev/null || echo 'unknown')" \
  -o ~/.openclaw/learning/projects/project-name

# 或者直接指定模型名
python3 scripts/smart-analyze.py /path/to/project \
  --model "zai/glm-5.2" \
  -o ~/.openclaw/learning/projects/project-name
```

# Step 2: 生成研究计划
python3 scripts/generate-research-plan.py /path/to/project \
  --depth file-level --max-files 30 \
  -o ~/.openclaw/learning/projects/project-name/RESEARCH_PLAN.md

# Step 3: 执行分析（使用 sessions_spawn 并行）
# 根据 RESEARCH_PLAN.md 派发子任务

# Step 4: 验证结果
python3 scripts/verify-analysis.py ~/.openclaw/learning/projects/project-name --all
```

### 递归深度分析流程（大型项目）

```bash
# Step 1: 递归生成模块清单（自动展开大型目录）
python3 scripts/generate-module-manifest.py /path/to/project \
  --expand-threshold 30 --max-recursion-depth 3 \
  -o output-dir/module-manifest.json

# Step 2: 生成分批并行分析计划
python3 scripts/recursive-orchestrator.py output-dir \
  --manifest output-dir/module-manifest.json \
  --project-path /path/to/project \
  --max-parallel 8 \
  [--priority-only]  # 可选：只分析高重要性模块
  -o output-dir/recursive-plan.md

# Step 3: 按 recursive-plan.md 执行 sessions_spawn（分批并行）
# Phase 1: 项目级分析
# Phase 2: 模块级递归分析（分批，每批 max-parallel 个并行）
# Phase 3: 项目级总结

# Step 4: 验证结果
python3 scripts/verify-analysis.py output-dir --recursive
```

### 手动执行

```bash
# Layer 1: 项目级分析（并行）
sessions_spawn task="分析项目概览，输出到 00-README.md" label="overview"
sessions_spawn task="分析架构设计，输出到 01-architecture.md" label="architecture"

# Layer 2: 模块级分析（按模块派发）
sessions_spawn task="分析 core 模块" label="module-core"

# Layer 3: 文件粒度分析（按文件组派发）
sessions_spawn task="分析 Bootstrap.java, Service.java" label="file-group-1"
```

---

## 输出结构

```
output-dir/
├── INDEX.md                          # 总索引
├── 00-project-level/                 # Layer 1: 项目级
│   ├── README.md                     # 项目概览
│   ├── architecture.md               # 架构设计
│   ├── dependencies.md               # ⭐ 项目依赖分析（发现优秀第三方库）
│   ├── quality-score.md              # 质量评分
│   └── learning-value.md             # 学习价值
├── 10-module-level/                  # Layer 2: 模块级
│   └── <module>/
│       ├── overview.md
│       ├── interface.md
│       └── dependencies.md
└── 20-file-level/                    # Layer 3: 文件粒度
    └── <file>-analysis.md
```

---

## 🚀 最大分析模式 (MAXIMUM ANALYSIS)

### 触发条件

用户请求包含以下**任意关键词**时自动启用：

| 触发词 | 示例 |
|--------|------|
| 深度/深入 | "深度分析"、"深入了解" |
| 详细/全面 | "详细分析"、"全面分析" |
| 彻底/系统化 | "彻底研究"、"系统化分析" |
| 完整/最大化 | "完整分析"、"最大化分析" |

### 执行策略

进入最大分析模式后，**三层全开 + 专项模板全开**：

```
Layer 1: 项目级分析 (必做) → 4 文档
Layer 2: 模块级分析 (必做) → 每模块 3 文档，预计 15-30 文档
Layer 3: 文件粒度分析 (必做) → 每文件 1 文档，预计 20-50 文档
专项模板 (按项目类型) → LLM Agent 11个 / Database 11个 / Infrastructure 3个
附加分析 (按需) → 核心功能、ADR、性能建模、竞品对比等
```

### 输出预期

**预计输出文档数量**: **40-80+ 个**

```
output-dir/
├── INDEX.md                          # 总索引
├── 00-project-level/                 # Layer 1 (4 文档)
├── 10-module-level/                  # Layer 2 (15-30 文档)
├── 20-file-level/                    # Layer 3 (20-50 文档)
├── 30-core-features/                 # 核心功能分析
├── 40-specialized/                   # 专项分析 (11 文档)
│   ├── llm-agent/ 或 database/
│   └── adr/
└── 50-appendix/                      # 附加分析
```

### 验证

```bash
python3 scripts/verify-analysis.py <output-dir> --maximum
```

验证维度：文档总数 >= 40、Layer 1-3 完整、专项模板 >= 8、附加分析 >= 3

---

## 🔁 递归深度分析模式 (RECURSIVE DEEP ANALYSIS)

### 触发条件

用户请求包含以下**任意关键词**时启用：

| 触发词 | 示例 |
|--------|------|
| 递归分析 | "递归分析"、"递归深度分析" |
| 模块深入 | "每个模块深入分析"、"逐模块分析" |
| 彻底分析 | "彻底分析每个模块" |
| 完整覆盖 | "完整覆盖所有模块" |

### 设计动机

**问题**：最大分析模式对大型项目（如 VictoriaMetrics 267K 行 / 1052 文件）的每个模块仍然只能浅尝辄止。Layer 2 模块级分析每个模块只生成 3 个文档，深度有限。

**解决方案**：对每个模块递归执行完整的三层分析，让每个模块都拥有独立、深入的分析报告。

### 执行策略

```
Phase 1: 项目级扫描 (Layer 1)
├── 识别所有模块（按目录/包/命名空间）
├── 生成模块清单 + 依赖图
├── 评估模块规模（文件数/行数）
└── 创建分析计划

Phase 2: 模块级递归分析 (每个模块完整三层)
├── 对每个模块执行完整三层分析
│   ├── Layer 1: 模块概览（README、架构、质量、学习价值）→ 4 文档
│   ├── Layer 2: 子模块/组件分析 → 每子模块 3 文档
│   └── Layer 3: 关键文件深度分析 → 每文件 1 文档
├── 生成模块独立报告
└── 使用 sessions_spawn 并行执行

Phase 3: 项目级总结
├── 整合所有模块分析
├── 生成跨模块对比
├── 提炼可移植模式
└── 创建项目总结文档
```

### 输出结构

```
output-dir/
├── INDEX.md                          # 总索引
├── 00-project-level/                 # 项目级 (4 文档)
│   ├── README.md
│   ├── architecture.md
│   ├── quality-score.md
│   └── learning-value.md
├── 10-module-deep/                   # 🔥 模块深度分析
│   ├── _MODULE_SUMMARY.md            # 模块总结对比
│   ├── module-a/                     # 模块 A 完整分析
│   │   ├── INDEX.md                  # 模块索引
│   │   ├── 00-overview/              # Layer 1 (4 文档)
│   │   │   ├── README.md
│   │   │   ├── architecture.md
│   │   │   ├── quality-score.md
│   │   │   └── learning-value.md
│   │   ├── 10-submodule/             # Layer 2 (子模块)
│   │   └── 20-file-level/            # Layer 3 (关键文件)
│   ├── module-b/                     # 模块 B 完整分析
│   │   └── ...
│   └── module-c/
│       └── ...
├── 20-cross-module/                  # 跨模块分析
│   ├── comparison.md                 # 模块对比
│   ├── patterns.md                   # 可移植模式
│   └── recommendations.md            # 改进建议
└── 30-specialized/                   # 专项分析 (按项目类型)
```

### 模块规模评估与策略

| 模块规模 | 文件数 | 重要性 | 分析策略 |
|----------|--------|--------|----------|
| **大型** | > 100 文件 | - | Layer 1+2+3 + 子模块递归 |
| **中型** | 20-100 文件 | - | Layer 1+2+3（选 5-10 关键文件）|
| **小型-高重要性** | < 20 文件 | high | Layer 1 + 3-5 关键文件（代码密集/入口模块）|
| **小型-低重要性** | < 20 文件 | low | Layer 1 only |

> 重要性评估不只看规模，还看：是否有入口文件、行数密度（少量文件但大量代码 = 核心逻辑）。例如 VictoriaMetrics 的 `lib/encoding` 虽小但是核心模块。

### 并行执行策略

```bash
# Step 1: 生成模块清单（自动递归展开）
python3 scripts/generate-module-manifest.py /path/to/project \
  --expand-threshold 30 --max-recursion-depth 3 \
  -o output-dir/module-manifest.json

# Step 2: 生成分析计划（分批并行）
python3 scripts/recursive-orchestrator.py output-dir \
  --manifest output-dir/module-manifest.json \
  --project-path /path/to/project \
  --max-parallel 8 \
  --priority-only  # 可选：只分析高重要性模块
  -o output-dir/recursive-plan.md

# Step 3: 按 recursive-plan.md 分批执行
# Phase 1: 项目级扫描（串行）
sessions_spawn task="项目级扫描，识别所有模块" label="project-scan"

# Phase 2: 模块级递归（分批并行，每批 max-parallel 个）
# 批次 1
for module in batch_1; do
  sessions_spawn task="递归分析模块: $module" label="module-$module"
done
sessions_yield message="等待批次 1 完成"

# 批次 2...

# Phase 3: 项目级总结（等待所有模块完成后）
sessions_spawn task="整合所有模块分析，生成总结" label="project-summary"
```

> **提示**: 对于 100+ 模块的超大型项目，先用 `--priority-only` 分析 high 重要性模块，再按需扩展。

### 验证

```bash
python3 scripts/verify-analysis.py <output-dir> --recursive
```

验证维度：
- ✅ 文档总数 >= 50
- ✅ 模块数 >= 5
- ✅ 每个模块有独立的 INDEX.md（覆盖率 >= 80%）
- ✅ 中大型模块有 Layer 2+3
- ✅ 项目级总结文档完整

### 预计输出

**小型项目** (< 100 文件): 20-40 文档
**中型项目** (100-500 文件): 50-150 文档
**大型项目** (> 500 文件): 100-300+ 文档

### 与最大分析模式对比

| 特性 | 最大分析模式 | 递归深度分析 |
|------|--------------|--------------|
| 模块深度 | 浅（3 文档/模块）| 深（完整三层/模块）|
| 文件覆盖 | 部分关键文件 | 每模块独立选择关键文件 |
| 适用规模 | 中小型项目 | 大型/超大型项目 |
| 文档数量 | 40-80 | 100-300+ |
| 执行时间 | 2-4 小时 | 4-8 小时 |
| 并行度 | 中 | 高（模块级分批并行）|
| 子模块分析 | ❌ | ✅ 递归展开 |
| 跨模块对比 | 浅 | 深 |
| 重要性评估 | ❌ | ✅ 自动评估 |

---

## 项目类型识别与专项模板

| 项目类型 | 识别特征 | 应用模板 |
|----------|----------|----------|
| **LLM Agent** | LLM/AI/Agent/Memory/Tool | `templates/llm-agent/` (11个) |
| **数据库/大数据** | SQL/Storage/Index/Query | `templates/database/` (11个) |
| **基础设施** | 数据库/消息队列/存储 | `templates/infrastructure/` (3个) |
| **通用项目** | 以上都不匹配 | `templates/general/` (9个) |

**自动检测**: `python3 scripts/detect-project-type.py /path/to/project --recommend-templates`

---

## 质量评分体系

### 项目级评分（100分）

| 维度 | 权重 | 评分项 |
|------|------|--------|
| 代码结构 | 20% | 模块划分清晰、职责单一 |
| 代码质量 | 20% | 复杂度 <10、无异味 |
| 安全性 | 20% | 无硬编码密钥、注入风险 |
| 测试覆盖 | 15% | 覆盖率 >60% |
| 文档 | 15% | README、API 文档 |
| 社区 | 10% | 维护活跃度 |

### 文件级评分（100分）

| 维度 | 权重 | 评分项 |
|------|------|--------|
| 职责清晰 | 20% | 单一职责、定位明确 |
| 代码质量 | 20% | 复杂度 <10、无异味 |
| 设计模式 | 15% | 合理应用、可扩展 |
| 依赖管理 | 15% | 松耦合、可替换 |
| 测试覆盖 | 15% | 单测 >70% |
| 文档完善 | 10% | 注释、API 文档 |

**等级**: 🟢 A (85-100) | 🟡 B (70-84) | 🟠 C (55-69) | 🔴 D (<55)

---

## 文件粒度分析（11维度）

每个文件分析包含：

1. **文件基本信息** - 行数、语言、职责、所属模块
2. **文件职责与定位** - 核心职责、职责分解、系统位置
3. **关键类/函数分析** - 类清单、核心方法详解
4. **数据结构分析** - 核心数据结构、数据流向
5. **依赖关系分析** - 上游调用者、下游依赖
6. **设计模式识别** - 已应用模式、可改进模式
7. **代码质量评估** - 复杂度、异味、SOLID 符合度
8. **测试覆盖分析** - 单元测试、测试缺失
9. **改进建议** - 立即/中期/长期改进
10. **学习价值** - 值得借鉴、需要注意
11. **设计动机分析** - 为什么这样设计、设计权衡

详见 [guides/FILE_LEVEL_ANALYSIS.md](guides/FILE_LEVEL_ANALYSIS.md)

---

## 专项分析模板

### 🔥 LLM Agent 专项（11维度）

针对 AI Agent 项目（LangChain/AutoGen/MemGPT/CrewAI 等）：

| # | 文档 | 核心问题 |
|---|------|----------|
| 0 | LLM_AGENT_ANALYSIS_OVERVIEW.md | 总览、分析流程 |
| 1 | LLM_AGENT_01_ARCHITECTURE.md | Agent 类型、状态管理、工作流 |
| 2 | LLM_AGENT_02_LLM_INTEGRATION.md | 模型选择、Prompt 工程、成本控制 |
| 3 | LLM_AGENT_03_MEMORY_SYSTEM.md | 记忆架构、检索策略、遗忘机制 |
| 4 | LLM_AGENT_04_TOOL_SYSTEM.md | 工具定义、调用机制、安全沙箱 |
| 5 | LLM_AGENT_05_PLANNING_REASONING.md | 任务分解、推理方式、自我反思 |
| 6 | LLM_AGENT_06_HUMAN_COLLABORATION.md | 中断机制、用户干预、权限控制 |
| 7 | LLM_AGENT_07_SAFETY_ALIGNMENT.md | Prompt 注入防护、数据保护 |
| 8 | LLM_AGENT_08_OBSERVABILITY.md | 日志追踪、指标监控、调试 |
| 9 | LLM_AGENT_09_PERFORMANCE.md | 延迟优化、成本控制、并发 |
| 10 | LLM_AGENT_10_EVALUATION.md | 评估基准、测试方法 |
| 11 | LLM_AGENT_11_AGENT_FRAMEWORK.md | 框架选型、集成深度、供应商锁定、迁移可行性 |

### 🗄️ 数据库/大数据专项（10维度）

针对数据库系统（MySQL/PostgreSQL/ClickHouse/TiDB 等）：

| # | 文档 | 核心问题 |
|---|------|----------|
| 0 | DATABASE_ANALYSIS_OVERVIEW.md | 总览、系统类型识别 |
| 1 | DATABASE_01_ARCHITECTURE.md | 模块划分、调用链、配置体系 |
| 2 | DATABASE_02_STORAGE_ENGINE.md | 物理布局、存储结构、元数据 |
| 3 | DATABASE_03_INDEX_DESIGN.md | 索引类型、并发控制、编码 |
| 4 | DATABASE_04_QUERY_PROCESSING.md | 解析、优化、执行模型 |
| 5 | DATABASE_05_TRANSACTION.md | 隔离级别、MVCC、分布式事务 |
| 6 | DATABASE_06_HA_FAULT_TOLERANCE.md | 数据复制、故障切换、备份 |
| 7 | DATABASE_07_RESOURCE_MANAGEMENT.md | 内存管理、磁盘IO、线程模型 |
| 8 | DATABASE_08_NETWORK_SERIALIZATION.md | 通信协议、序列化、零拷贝 |
| 9 | DATABASE_09_WORKLOAD_SPECIFIC.md | OLTP/OLAP/HTAP 专项 |
| 10 | DATABASE_10_OBSERVABILITY.md | 指标暴露、慢查询、链路追踪 |

---

## 可用脚本

| 脚本 | 功能 |
|------|------|
| `resilient-runner.py` | 🔄 **弹性运行器** - 自动检测失败任务、指数退避重试、断点续传 |
| `setup-cron-recovery.py` | ⏰ **Cron 自动恢复设置** - 配置定期检查+重试的定时任务 |
| `smart-analyze.py` | 🤖 智能分析入口 - 自动检测项目类型、推荐模板 |
| `generate-research-plan.py` | 生成详细研究计划（预研究 + 任务分解） |
| `generate-file-list.py` | 自动识别关键文件，生成文件列表 |
| `generate-module-manifest.py` | 🔁 生成模块清单 - 识别所有模块并评估规模（递归分析专用） |
| `recursive-orchestrator.py` | 🔁 递归深度分析编排器 v2 - 生成计划驱动的 PLAN.md |
| `mermaid-validator.py` | 🎨 Mermaid 图表语法检验器（11 条规则） |
| `plan-tracker.py` | 📋 计划追踪器 - 检查点管理、进度同步、计划验收 |
| `detect-project-type.py` | 自动检测项目类型（LLM Agent/Database/Web） |
| `detect-visualization.sh` | 🎨 检测项目可视化支持（Mermaid/PlantUML） |
| `orchestrator.py` | 自动编排执行（健康检查 + 异常处理） |
| `verify-analysis.py` | 验证分析文档完整性和质量（支持 `--recursive` 模式） |
| `review-agent.py` | 独立审查代理 |
| `quick-scan.sh` | 快速扫描项目结构 |

---

## 文档索引

### 引导文档 (guides/)

| 文档 | 内容 |
|------|------|
| [FILE_LEVEL_ANALYSIS.md](guides/FILE_LEVEL_ANALYSIS.md) | 文件粒度分析模板 |
| [DETAILED_RESEARCH_PLAN.md](guides/DETAILED_RESEARCH_PLAN.md) | 详细研究计划模板 |
| [DIAGRAM_GENERATION_GUIDE.md](guides/DIAGRAM_GENERATION_GUIDE.md) | 🎨 Mermaid 图表生成规范 |
| [MERMAID_VALIDATION.md](guides/MERMAID_VALIDATION.md) | 🎨 Mermaid 图表检验规则说明 |
| [PRINCIPLE_DISTILLATION.md](guides/PRINCIPLE_DISTILLATION.md) | 💡 原则蒸馏指南 |
| [PROBLEM_DRIVEN_ANALYSIS.md](guides/PROBLEM_DRIVEN_ANALYSIS.md) | 问题驱动分析方法 |
| [REFERENCE_ORGANIZATION_GUIDE.md](guides/REFERENCE_ORGANIZATION_GUIDE.md) | 参考文献规范 |
| [RECURSIVE_DEEP_ANALYSIS.md](guides/RECURSIVE_DEEP_ANALYSIS.md) | 🔁 递归深度分析指南 |
| [PLAN_DRIVEN_EXECUTION.md](guides/PLAN_DRIVEN_EXECUTION.md) | 📋 计划驱动执行指南（检查点+验收）|
| [RESILIENT_EXECUTION.md](guides/RESILIENT_EXECUTION.md) | 🔄 弹性执行指南（自动重试+Cron恢复）|

### 通用模板 (templates/general/)

| 文档 | 内容 |
|------|------|
| [SYSTEM_APPRECIATION_TEMPLATE.md](templates/general/SYSTEM_APPRECIATION_TEMPLATE.md) | 系统鉴赏框架 |
| [ARCHITECTURE_DECISION_TEMPLATE.md](templates/general/ARCHITECTURE_DECISION_TEMPLATE.md) | ADR 架构决策记录 |
| [PROJECT_DEPENDENCY_ANALYSIS.md](templates/general/PROJECT_DEPENDENCY_ANALYSIS.md) | ⭐ **项目依赖分析**（发现优秀第三方库，强制输出） |
| [PERFORMANCE_ANALYSIS_TEMPLATE.md](templates/general/PERFORMANCE_ANALYSIS_TEMPLATE.md) | 性能瓶颈分析 |
| [FEATURE_TRADEOFF_ANALYSIS.md](templates/general/FEATURE_TRADEOFF_ANALYSIS.md) | 特性优势与代价分析 |
| [FULLSTACK_WEB_ANALYSIS.md](templates/general/FULLSTACK_WEB_ANALYSIS.md) | 全栈 Web 应用分析 |
| [PIPELINE_WORKFLOW_ANALYSIS.md](templates/general/PIPELINE_WORKFLOW_ANALYSIS.md) | Pipeline 工作流分析 |
| [INTEGRATION_ECOSYSTEM.md](templates/general/INTEGRATION_ECOSYSTEM.md) | 集成生态与协议分析 |
| [CORE_FEATURES_ANALYSIS.md](templates/general/CORE_FEATURES_ANALYSIS.md) | 核心功能分析 |
| [FEATURE_IMPLEMENTATION_LOGIC.md](templates/general/FEATURE_IMPLEMENTATION_LOGIC.md) | 🔥 功能实现逻辑追踪 |
| [VISUALIZATION_DIAGRAMS.md](templates/general/VISUALIZATION_DIAGRAMS.md) | 可视化系统分析 |

### 基础设施模板 (templates/infrastructure/)

| 文档 | 内容 |
|------|------|
| [INFRASTRUCTURE_SYSTEM_TEMPLATE.md](templates/infrastructure/INFRASTRUCTURE_SYSTEM_TEMPLATE.md) | 大型基础软件系统分析 |
| [PERFORMANCE_MODELING_TEMPLATE.md](templates/infrastructure/PERFORMANCE_MODELING_TEMPLATE.md) | 性能建模（Amplification框架） |
| [CONFIGURATION_TUNING_TEMPLATE.md](templates/infrastructure/CONFIGURATION_TUNING_TEMPLATE.md) | 配置与调优指南 |

---

## 执行纪律

0. **📌 先注册 Goal** — 分析开始前，运行 `goal-tracker.py register` 注册任务，确保状态持久化
1. **先有计划再执行** — 递归深度分析模式必须先生成 PLAN.md 并保存到输出目录
2. **按计划执行** — 每个 sessions_spawn 任务必须引用 PLAN.md 中的 Task ID 和预期输出
3. **追踪进度** — 使用 plan-tracker.py 维护检查点，每批完成后同步；同时运行 `goal-tracker.py update` 更新 goal 状态
4. **子代理报告** — 每个子代理完成后必须生成 .task-report.json
5. **按计划验收** — 分析完成后运行 plan-tracker.py verify，输出符合度报告
6. **补救缺失** — 对验收中符合度 < 80% 的任务，补充分析
7. **📌 标记完成** — 分析完成后运行 `goal-tracker.py complete` 标记 goal 完成

## 🔄 弹性执行纪律（解决 LLM rate limit / 并发失败）

> **核心问题**：分析大项目时 LLM 并发限制导致 subagent 失败 → 主 agent 停止 → 分析中止
>
> **解决方案**：三层防线 + 自动恢复。详见 [RESILIENT_EXECUTION.md](guides/RESILIENT_EXECUTION.md)

1. **先初始化弹性检查点** — 分析开始前运行 `resilient-runner.py --init`
2. **设置 cron 自动恢复** — 使用 `setup-cron-recovery.py` 设置定时恢复（每 2 分钟）
3. **批次间同步状态** — 每批 sessions_yield 后运行 `resilient-runner.py --sync`
4. **失败任务全自动重试** — 运行 `resilient-runner.py --continue` 生成 continuation prompt（让 cron session 自主执行）
5. **指数退避** — rate_limit 错误等待 60→120→240→480→960 秒递增
6. **全局超时** — 1.5h 后停止重试，避免无限循环
7. **完成后清理** — 分析结束后移除 cron job

**完成检测机制**（可靠性递减）：
1. `.task-complete.json` 签名文件（LLM 完成后必须生成，包含文件哈希）— 信心度 0.95
2. `.task-report.json` 子代理报告 — 信心度 0.85
3. 文件存在 + 内容验证（最小大小、占位符检测、结构标记）— 信心度 0.7

**两种重试模式**：
- `--auto-resume`：生成详细的重试指令文本（列出每个任务的 sessions_spawn 命令）
- `--continue`：生成 continuation prompt（让 agent session 自主决定最佳执行方式，适合 cron）

**关键原则**：脚本负责检测+报告，agent 负责决策+执行。主 agent 不需要一次性完成所有任务。即使 session 中断，cron 触发的新 session 会拿过接力棒。

详见 [guides/PLAN_DRIVEN_EXECUTION.md](guides/PLAN_DRIVEN_EXECUTION.md)

---

## 执行注意事项

1. **使用 sessions_spawn 并行执行**：不同维度分析任务分配给子代理
2. **增量生成**：先生成核心文档，再补充专项分析
3. **质量优先**：每个文档必须包含完整的问题清单回答
4. **🎨 图表必生成**：每个分析文档至少 1 个 Mermaid 图表

---

## 执行闭环

分析完成后，必须完成以下闭环动作：

### 0. 📌 标记 Goal 完成（必做，最先执行）

```bash
python3 scripts/goal-tracker.py complete --goal-id "<goal-id>"
```

确保任务状态从 `in_progress` 变为 `completed`，避免下次会话误判为未完成。

### 1. 回写 MEMORY.md

将分析结果写入 `~/.openclaw/workspace/MEMORY.md`：

```markdown
### [项目名] - [定位] (日期)
**位置**: `~/.openclaw/learning/projects/[name]/`
**关键数据**: Stars、语言、规模、评分
**核心架构**: 3-5 个要点
**关键发现**: ⭐ 评分的可移植模式
**学习价值**: 可借鉴的设计原则
**状态**: ✅ 完成 / 🚧 进行中
```

### 2. 更新对比数据库

编辑 `references/project-comparison-db.md`，添加新项目和对比维度。

### 3. 创建版本记录

复制 `templates/VERSION_TEMPLATE.md` 到分析目录的 `VERSION.md`。

### 4. 验证完整性

```bash
python3 scripts/verify-analysis.py [analysis-dir] --all
```

检查：
- ✅ 文件完整性
- ✅ INDEX.md 一致性（无幽灵引用、无孤儿文件）
- ✅ 内容质量分数

详见 [guides/EXECUTION_CLOSURE.md](guides/EXECUTION_CLOSURE.md)

---

*最后更新: 2026-07-03*
