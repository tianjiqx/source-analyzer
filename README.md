# Source Analyzer

🔬 开源项目源码分析的系统化工作流（环境无关）

## 核心特性

| 特性 | 说明 |
|------|------|
| **三层渐进式分析** | 项目级 → 模块级 → 文件粒度 |
| **专项分析模板** | LLM Agent（11维度）、数据库（10维度）、基础设施 |
| **可视化输出** | 自动生成 Mermaid 图表（架构图/时序图/类图） |
| **原则蒸馏** | 提炼可移植设计原则（Golden Rules）和陷阱（Gotchas） |
| **自动化脚本** | 项目检测、研究计划生成、文件列表生成、验证 |

## 安装

将当前 skill 拷贝到目标运行环境的 skills 工作目录即可使用。具体加载方式由运行时决定，参见 [`runtime/adapter.md`](runtime/adapter.md)。

```bash
# 以 OpenClaw 为例：创建目标目录（如果不存在）
mkdir -p ~/.openclaw/workspace/skills

# 拷贝 skill 到工作目录
cp -r /path/to/source-analyzer ~/.openclaw/workspace/skills/
```

安装后即可在对应运行时中使用 `source-analyzer` skill 进行项目分析。

## 快速开始

### 自动化流程（推荐）

```bash
# Step 1: 智能分析（自动检测项目类型 + 推荐模板）
python3 scripts/smart-analyze.py /path/to/project \
  --model "$(cat "$WORKSPACE/.current-model" 2>/dev/null || echo 'unknown')" \
  -o ~/.openclaw/learning/projects/project-name

# Step 2: 生成研究计划
python3 scripts/generate-research-plan.py /path/to/project \
  --depth file-level --max-files 30 \
  -o ~/.openclaw/learning/projects/project-name/RESEARCH_PLAN.md

# Step 3: 执行分析（按 runtime/adapter.md 选择并行或串行机制）
# 根据 RESEARCH_PLAN.md，使用当前环境的派发机制执行子任务

# Step 4: 验证结果
python3 scripts/verify-analysis.py ~/.openclaw/learning/projects/project-name --all
```

### 分析深度选择

| 深度 | 输出 | 时间 | 适合场景 |
|------|------|------|----------|
| **Layer 1** | 3-6 文档 | 10-20min | 快速了解、技术调研 |
| **Layer 2** | 每模块 3 文档 | 每模块 10-15min | 理解架构、设计借鉴 |
| **Layer 3** | 每文件 1 文档 | 每文件 5-10min | 深度学习、二次开发 |

## 项目结构

```
source-analyzer/
├── SKILL.md              # 主文档（完整工作流说明）
├── CHANGELOG.md          # 更新日志
├── guides/               # 引导文档
│   ├── FILE_LEVEL_ANALYSIS.md          # 文件粒度分析模板
│   ├── DETAILED_RESEARCH_PLAN.md       # 详细研究计划模板
│   ├── DIAGRAM_GENERATION_GUIDE.md     # Mermaid 图表生成规范
│   ├── PRINCIPLE_DISTILLATION.md       # 原则蒸馏指南
│   ├── PROBLEM_DRIVEN_ANALYSIS.md      # 问题驱动分析方法
│   └── REFERENCE_ORGANIZATION_GUIDE.md # 参考文献规范
├── scripts/              # 自动化脚本
│   ├── smart-analyze.py              # 🤖 智能分析入口
│   ├── generate-research-plan.py     # 生成详细研究计划
│   ├── generate-file-list.py         # 自动识别关键文件
│   ├── detect-project-type.py        # 自动检测项目类型
│   ├── verify-analysis.py            # 验证分析文档完整性
│   ├── orchestrator.py               # 自动编排执行
│   └── review-agent.py               # 独立审查代理
├── templates/            # 分析模板
│   ├── general/          # 通用模板
│   ├── llm-agent/         # LLM Agent 专项
│   ├── database/          # 数据库专项
│   └── infrastructure/    # 基础设施专项
└── references/           # 参考文档
    ├── ddd-patterns.md
    ├── lang-tools.md
    └── project-comparison-db.md
```

## 项目类型识别与专项模板

| 项目类型 | 识别特征 | 应用模板 |
|----------|----------|----------|
| **LLM Agent** | LLM/AI/Agent/Memory/Tool | `templates/llm-agent/` (11个) |
| **数据库/大数据** | SQL/Storage/Index/Query | `templates/database/` (11个) |
| **基础设施** | 数据库/消息队列/存储 | `templates/infrastructure/` (3个) |
| **通用项目** | 以上都不匹配 | `templates/general/` (9个) |

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

**等级**: 🟢 A (85-100) | 🟡 B (70-84) | 🟠 C (55-69) | 🔴 D (<55)

## 🚀 最大分析模式

触发关键词：深度/深入、详细/全面、彻底/系统化、完整/最大化

**输出预期**: 40-80+ 个文档，包括：
- Layer 1: 项目级分析 (4 文档)
- Layer 2: 模块级分析 (15-30 文档)
- Layer 3: 文件粒度分析 (20-50 文档)
- 专项分析 (11+ 文档)
- 附加分析 (核心功能、ADR、性能建模等)

```bash
python3 scripts/verify-analysis.py <output-dir> --maximum
```

## 可用脚本

| 脚本 | 功能 |
|------|------|
| `smart-analyze.py` | 🤖 智能分析入口 - 自动检测项目类型、推荐模板 |
| `generate-research-plan.py` | 生成详细研究计划（预研究 + 任务分解） |
| `generate-file-list.py` | 自动识别关键文件，生成文件列表 |
| `detect-project-type.py` | 自动检测项目类型（LLM Agent/Database/Web） |
| `verify-analysis.py` | 验证分析文档完整性和质量 |
| `orchestrator.py` | 自动编排执行（健康检查 + 异常处理） |
| `review-agent.py` | 独立审查代理 |

## 文档索引

### 引导文档 (guides/)

- [FILE_LEVEL_ANALYSIS.md](guides/FILE_LEVEL_ANALYSIS.md) - 文件粒度分析模板
- [DETAILED_RESEARCH_PLAN.md](guides/DETAILED_RESEARCH_PLAN.md) - 详细研究计划模板
- [DIAGRAM_GENERATION_GUIDE.md](guides/DIAGRAM_GENERATION_GUIDE.md) - 🎨 Mermaid 图表生成规范
- [PRINCIPLE_DISTILLATION.md](guides/PRINCIPLE_DISTILLATION.md) - 💡 原则蒸馏指南
- [PROBLEM_DRIVEN_ANALYSIS.md](guides/PROBLEM_DRIVEN_ANALYSIS.md) - 问题驱动分析方法

### 通用模板 (templates/general/)

- [SYSTEM_APPRECIATION_TEMPLATE.md](templates/general/SYSTEM_APPRECIATION_TEMPLATE.md) - 系统鉴赏框架
- [ARCHITECTURE_DECISION_TEMPLATE.md](templates/general/ARCHITECTURE_DECISION_TEMPLATE.md) - ADR 架构决策记录
- [PERFORMANCE_ANALYSIS_TEMPLATE.md](templates/general/PERFORMANCE_ANALYSIS_TEMPLATE.md) - 性能瓶颈分析
- [CORE_FEATURES_ANALYSIS.md](templates/general/CORE_FEATURES_ANALYSIS.md) - 🔥 核心功能分析
- [FEATURE_IMPLEMENTATION_LOGIC.md](templates/general/FEATURE_IMPLEMENTATION_LOGIC.md) - 🔥 功能实现逻辑追踪

## 执行注意事项

1. **按运行时适配层执行**：支持并行时将独立维度分配给子代理，否则串行执行
2. **增量生成**：先生成核心文档，再补充专项分析
3. **质量优先**：每个文档必须包含完整的问题清单回答
4. **🎨 图表必生成**：每个分析文档至少 1 个与内容匹配的图表；物理布局使用 ASCII 图

## 执行闭环

分析完成后执行闭环动作，分两层（详见 [runtime/adapter.md](runtime/adapter.md) 能力矩阵）：

**A. 通用核心闭环（所有环境必做）**：
1. **标记进度完成** - 机制由适配层提供（OpenClaw/opencode：`goal-tracker.py complete`；DSH：原生 goal 工具）
2. **记录 Commit** - `python3 scripts/commit-tracker.py record <project> --output-dir <analysis-dir>`
3. **创建版本记录** - 复制 `templates/VERSION_TEMPLATE.md` 到分析目录
4. **验证完整性** - 按模式选命令：递归模式 `--recursive`，标准模式 `--all`

**B. 可选环境钩子（环境不支持则显式跳过并记录，禁止假闭环）**：
- **回写 MEMORY.md**（`memory.write`，OpenClaw 默认 `~/.openclaw/workspace/MEMORY.md`；DSH 无记忆消费者→跳过）
- **更新对比数据库**（`db.update`，仅当 `references/` 可写；只读环境→跳过）
- 定时恢复 / 会话检查 / 完成通知（`scheduler` / `progress.check` / `notify.silent`）

详见 [guides/EXECUTION_CLOSURE.md](guides/EXECUTION_CLOSURE.md)

## 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解版本历史和更新内容。

## 许可证

MIT License

---

*最后更新: 2026-07-02*
