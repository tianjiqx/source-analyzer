---
name: source-analyzer
description: 开源项目源码分析系统化工作流。三层渐进式分析（项目级→模块级→文件粒度），专项模板（LLM Agent/数据库/基础设施），自动生成 Mermaid 图表。
metadata: {"openclaw":{"emoji":"🔬"}}
---

# Source Analyzer

开源项目源码分析的系统化工作流。

## 核心特性

| 特性 | 说明 |
|------|------|
| **三层渐进式分析** | 项目级 → 模块级 → 文件粒度 |
| **专项分析模板** | LLM Agent（11维度）、数据库（10维度）、基础设施 |
| **可视化输出** | 自动生成 Mermaid 图表（架构图/时序图/类图） |
| **原则蒸馏** | 提炼可移植设计原则（Golden Rules）和陷阱（Gotchas） |
| **自动化脚本** | 项目检测、研究计划生成、文件列表生成、验证 |

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

---

## 快速开始

### 自动化流程（推荐）

```bash
# Step 1: 智能分析（自动检测项目类型 + 推荐模板）
python3 scripts/smart-analyze.py /path/to/project \
  -o ~/.openclaw/learning/projects/project-name

# Step 2: 生成研究计划
python3 scripts/generate-research-plan.py /path/to/project \
  --depth file-level --max-files 30 \
  -o ~/.openclaw/learning/projects/project-name/RESEARCH_PLAN.md

# Step 3: 执行分析（使用 sessions_spawn 并行）
# 根据 RESEARCH_PLAN.md 派发子任务

# Step 4: 验证结果
python3 scripts/verify-analysis.py ~/.openclaw/learning/projects/project-name --all
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
| `smart-analyze.py` | 🤖 智能分析入口 - 自动检测项目类型、推荐模板 |
| `generate-research-plan.py` | 生成详细研究计划（预研究 + 任务分解） |
| `generate-file-list.py` | 自动识别关键文件，生成文件列表 |
| `detect-project-type.py` | 自动检测项目类型（LLM Agent/Database/Web） |
| `detect-visualization.sh` | 🎨 检测项目可视化支持（Mermaid/PlantUML） |
| `orchestrator.py` | 自动编排执行（健康检查 + 异常处理） |
| `verify-analysis.py` | 验证分析文档完整性和质量 |
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
| [PRINCIPLE_DISTILLATION.md](guides/PRINCIPLE_DISTILLATION.md) | 💡 原则蒸馏指南 |
| [PROBLEM_DRIVEN_ANALYSIS.md](guides/PROBLEM_DRIVEN_ANALYSIS.md) | 问题驱动分析方法 |
| [REFERENCE_ORGANIZATION_GUIDE.md](guides/REFERENCE_ORGANIZATION_GUIDE.md) | 参考文献规范 |

### 通用模板 (templates/general/)

| 文档 | 内容 |
|------|------|
| [SYSTEM_APPRECIATION_TEMPLATE.md](templates/general/SYSTEM_APPRECIATION_TEMPLATE.md) | 系统鉴赏框架 |
| [ARCHITECTURE_DECISION_TEMPLATE.md](templates/general/ARCHITECTURE_DECISION_TEMPLATE.md) | ADR 架构决策记录 |
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

## 执行注意事项

1. **使用 sessions_spawn 并行执行**：不同维度分析任务分配给子代理
2. **增量生成**：先生成核心文档，再补充专项分析
3. **质量优先**：每个文档必须包含完整的问题清单回答
4. **🎨 图表必生成**：每个分析文档至少 1 个 Mermaid 图表

---

## 执行闭环

分析完成后，必须完成以下闭环动作：

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

*最后更新: 2026-06-30*
