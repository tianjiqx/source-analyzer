# Source Analyzer Skill 更新日志

## 2026-09-16 - 🧠 按模型上下文窗口生成 LLM 请求预算

- 新增 `scripts/context_budget.py`，根据显式窗口、环境变量、模型映射或 256K 默认值计算 `max_input_tokens` / `max_output_tokens`。
- `orchestrator.py` 新增 `--model`、`--context-window`，启动时生成 `LLM_REQUEST_BUDGET.json` 并使用动态输入预算。
- SKILL、运行时适配文档和 README 统一要求派发时传递预算，超限按边界拆分，避免把总上下文直接作为输入上限。

## 2026-08-21 - 📦 分仓 - DSH 专属内容迁至 dsh-source-analyzer

### 🎯 概述

依据 SOURCE_ANALYZER_DSH_PLAN.md v1.4 §8.4 分仓策略，将 DSH 专属交付物迁至独立仓库 [dsh-source-analyzer](https://github.com/tianjiqx/dsh-source-analyzer)，skill 仓库保持纯环境无关。

### 🔑 关键变更

1. **迁出 DSH workflow 编排**：`scripts/analysis-workflow.js` → `dsh-source-analyzer/preset/analysis-workflow.js`（随预设分发，注入 system prompt）
2. **skill 仓库职责收窄**：仅保留方法论（SKILL.md）+ 通用验证脚本（evidence-check.py / verify-analysis.py / lint-skill.py）+ guides/templates/references + 环境适配说明（runtime/environments/）

### 📝 分仓理由

- **受众边界**：skill 服务多环境（OpenClaw / opencode / DSH / 纯 CLI），preset/workflow 仅 DSH
- **npm 打包独立可控**：DSH 专属内容独立发布
- **版本钉住比 monorepo 隐性漂移更安全**：dsh-source-analyzer 显式引用 skill 仓库版本
- **与 dsh-ssh / task-board 的 packages 独立维护惯例一致**

### 🔗 版本钉住

dsh-source-analyzer 当前钉住本仓库：
- 版本：**v1.4**
- commit：**`2ab56d8`** (feat: evidence-check 支持 --filelist 白名单消歧)

### ✅ 迁移验证

- 预设已安装到 `~/.dsh/.agent-presets/source-analyzer/`
- 新会话可选择「Source Analyzer 模式」预设
- skill 仓库 lint 通过（环境无关内容未受影响）

---

## 2026-08-15 - 🔬 质量四杠杆落地（v1.3 方案第⓪①②③批）

### 🎯 概述

依据 SOURCE_ANALYZER_DSH_PLAN.md v1.3 方案，落地过程质量与成本纪律：
六段式结构化派发模板、Glossary 提案制、证据锚定机器验证、成本熔断与三确认点。

### 🔑 关键变更

1. **⓪ 瑕疵修复**：SKILL.md 快速开始围栏 bug 与硬编码个人路径（→ `$WORKSPACE/opensource`）；
   dsh.md `memory.write` 能力更新为支持（memory 工具）；3 个 guide 的孤立围栏与硬编码路径；
   新增 `.gitignore`（清出 `__pycache__`）与 `LICENSE`(MIT)。
2. **⓪' 回归门**：新增 `scripts/lint-skill.py` — frontmatter/代码围栏配对/死链/硬编码路径/
   绝对脚本路径五项检查；改 SKILL.md 后必跑。
3. **① 派发模板升级**：六段式结构化 `[DISPATCH]`（task/context/inputs/outputs/constraints/report）；
   Glossary 提案制（并行只读 + `.glossary-<module>.md` 提案 + [WAIT] 后主 agent 串行合并，
   消除并行写竞态）；注入防御（仓库内容是数据不是指令）；大模块二阶拆分规则（>60 文件按子模块边界拆）。
4. **② 证据验证**：新增 `scripts/evidence-check.py` — 抽样比对 file:line 引用与源码
   （文件存在/行号越界/可选内容重叠），`[未验证]` 标注跳过；造假率 ≥5% 或低密度文档 →
   退出码 1，全产出复审；产出 EVIDENCE_REPORT.md。
5. **③ 成本纪律**：token 预算账本（估算/每批累记/150% 熔断请示）；goal 轮次预算
   （max_goal_rounds ≈ 批次+3，触顶 resume 主路径）；三确认点（开工前/异常中途/收尾前）；
   通知批汇聚；输出目录独立 git 化防污染。

### ✅ 验证

- `lint-skill.py` 全绿（18 文件 0 错误 0 警告）
- `evidence-check.py` 合成项目自测：真引用通过/假文件与越界被抓/`[未验证]` 跳过/退出码正确

## 2026-08-14 - 🧩 环境适配与验证器修复（DSH 实测驱动）

### 🎯 概述

依据在 DeepSeek Harness（DSH）环境中执行 deepseek-harness 递归深度分析（36 模块）的全流程实测，
将环境特定动作从"必做闭环"中剥离为可选钩子，并修复验证器与产出结构不符的问题。

### 🔑 关键变更

1. **闭环重构**：SKILL.md「执行闭环」拆分为 **A. 通用核心闭环**（进度完成/commit/VERSION/按模式验证）
   与 **B. 可选环境钩子**（memory.write / db.update / scheduler / progress.check / notify.silent），
   环境不支持时**显式跳过并记录**，禁止假闭环（如 DSH 无记忆消费者，不再写 MEMORY.md）。
2. **Goal 机制适配**：进度持久化机制由适配层提供——OpenClaw/opencode 用 goal-tracker.py
   （路径可用 `SOURCE_ANALYZER_GOALS_FILE` 覆盖），**DSH 用原生 goal 工具**（create_goal/update_goal/get_goal）。
3. **新增 DSH 环境适配**：`runtime/environments/dsh.md`（subagent 派发/通知驱动等待/中断恢复协议/
   峰值并发 12-20/只读 skill 目录的处理）。
4. **mermaid-validator.py**：`check_subgraph_pairing` 支持 sequenceDiagram 的
   alt/opt/loop/par/rect/critical/break 块闭合（else/and/option 为块内分隔符），消除 EXTRA_END 误报。
5. **verify-analysis.py**：
   - `--recursive` 模块计数改为**递归扫描含 INDEX.md 的目录**（支持 `packages/<family>/<module>` 嵌套，
     按 realpath 去重，无需符号链接兼容层）；
   - `--all` 必需文件支持 **00-project-level/ 回退**（递归模式布局不再报 7 文件缺失）；
   - 禁止词检查**剥离代码块/行内代码**且拉丁词**大小写敏感**（工具名 `todo` 不再误报为 TODO），
     新增 `--forbidden-allow` 豁免参数；
   - INDEX 一致性升级：收集**任意层级 INDEX** 的引用 + **目录链接覆盖**其下全部文件 +
     孤儿检查排除导航/元/工作文件（PLAN/VERSION/报告/task-prompts），大语料不再误报数百孤儿。

### 📦 新增文件

| 文件 | 说明 |
|------|------|
| `runtime/environments/dsh.md` | 🧩 DSH 环境适配：行为映射、能力矩阵、闭环节钩子处理、子代理中断恢复协议 |

### 📝 修改文件

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 执行闭环重构（A/B 两层）；Goal 持久化协议改为适配层机制；执行纪律/弹性执行纪律标注 DSH 适配（原生 goal 替代 goal-tracker、跳过 resilient-runner/cron）；派发示例新增 DSH |
| `runtime/adapter.md` | 行为接口新增 memory.write/db.update/progress.check；新增 DSH 环境实现与环境能力矩阵 |
| `scripts/mermaid-validator.py` | sequenceDiagram 块闭合配对修复 |
| `scripts/verify-analysis.py` | 递归计数/项目级回退/禁止词/INDEX 一致性四项修复 |

---

## 2026-08-04 - 🔗 Commit 追踪与增量分析

### 🎯 概述

本次更新解决核心问题：**项目持续迭代，分析文档与实际代码脱节，无法系统性进行增量分析。**

新增 Git commit 追踪机制，每次分析自动记录 commit hash，后续可快速检测变更并针对性增量分析。

### 📦 新增文件

| 文件 | 大小 | 说明 |
|------|------|------|
| `scripts/commit-tracker.py` | 17KB | 🔗 **Commit 追踪器** — 5 个子命令（info/record/status/diff/history），支持获取 commit、记录到分析目录、检测变更、对比差异、查看历史 |

### 📝 修改文件

| 文件 | 说明 |
|------|------|
| `scripts/smart-analyze.py` | 新增 **Step 0: 获取 Git commit 信息**，自动将 commit\_hash/commit\_short/commit\_date/commit\_subject/branch/tag/remote\_url 写入 `project-meta.json` |
| `scripts/goal-tracker.py` | `register` 命令新增 `--commit-hash`/`--commit-short`/`--commit-date`/`--branch` 参数；goal 记录 context 中包含 commit 信息；`list` 输出显示 commit |
| `templates/VERSION_TEMPLATE.md` | 重写模板，增加 commit 完整字段（hash/short/date/subject/branch/tag）和增量分析操作指南 |
| `SKILL.md` | 新增「🔗 Commit 追踪与增量分析」完整章节；核心特性表新增 Commit 追踪；执行纪律新增第 8 条；执行闭环新增 Step 0.5；脚本表新增 commit-tracker.py |

### 🔧 新增功能详解

#### 1. commit-tracker.py — 5 个子命令

| 命令 | 功能 | 退出码 |
|------|------|--------|
| `info <project>` | 获取项目当前 commit 完整信息 | 0 |
| `record <project> --output-dir <dir>` | 记录当前 commit 到分析目录 | 0 |
| `status <project> --output-dir <dir>` | 检查是否需要增量分析 | 0=无变化, 2=有变化 |
| `diff <project> --output-dir <dir>` | 对比上次分析的 commit 与当前 | 0 |
| `history --output-dir <dir>` | 查看分析目录的 commit 历史 | 0 |

#### 2. smart-analyze.py — Step 0 自动获取 commit

新增 Step 0（在项目类型检测之前），自动获取 Git commit 信息：
- commit\_hash / commit\_short / commit\_date / commit\_subject
- branch / tag / remote\_url / total\_files\_in\_repo
- last\_analyzed\_at

写入 `project-meta.json`，同时在终端输出和 ANALYSIS\_PLAN.md 中显示。

#### 3. goal-tracker.py — Goal 关联 commit

`register` 新增参数：
```bash
python3 goal-tracker.py register \
  --objective "深度分析项目" \
  --project "myproject" \
  --output-dir "~/.openclaw/learning/projects/myproject" \
  --mode "recursive_deep" \
  --commit-hash "abc123..." \
  --commit-short "abc123d" \
  --commit-date "2026-08-04T12:00:00" \
  --branch "main"
```

`list` 输出新增 commit 信息行。

#### 4. 增量分析工作流

```
首次分析:
  smart-analyze.py → Step 0 自动记录 commit → project-meta.json
  分析完成 → commit-tracker.py record → 更新 commit-history.json

后续检查:
  commit-tracker.py status → 检测是否有新提交
  ├── 无变化 → 退出码 0，无需分析
  └── 有变化 → 退出码 2，输出变更模块统计

增量分析:
  commit-tracker.py diff → 获取详细变更文件列表
  → 按变更规模选择策略（文件级/模块级/架构级）
  → 对变更部分重新分析
  → commit-tracker.py record → 更新 commit 记录
  → 更新 VERSION.md
```

#### 5. 输出文件结构（新增部分）

```
output-dir/
├── project-meta.json          # ← 新增 commit_* 字段
├── commit-history.json        # ← 新增，完整分析 commit 历史
├── VERSION.md                 # ← 更新模板，含 commit 信息
└── ... (分析文档)
```

#### 6. 增量分析策略

| 变更规模 | 建议操作 |
|----------|----------|
| 无变更 | 无需分析 |
| 微小变更 (< 5 文件) | 重分析变更文件 (Layer 3) |
| 中等变更 (5-20 文件) | 重分析受影响模块 (Layer 1+3) |
| 大范围变更 (> 20 文件) | 递归重分析受影响模块 + 跨模块总结 |
| 架构级变更 | 重新执行完整分析（新版本号） |

### ✅ 验证测试

- [x] `commit-tracker.py info ~/opensource/leveldb` 正确输出 commit 23e35d7
- [x] `commit-tracker.py record` 正确写入 project-meta.json 和 commit-history.json
- [x] `commit-tracker.py status` 无变化时退出码 0，正确提示
- [x] `commit-tracker.py history` 正确列出分析历史
- [x] `smart-analyze.py` Step 0 正确获取 commit 并写入 meta
- [x] `goal-tracker.py register --commit-hash` 正确记录到 context
- [x] `VERSION_TEMPLATE.md` 更新后包含 commit 占位符

### 📊 脚本清单更新

总计 **16 个脚本**（新增 1 个）

---

## 2026-07-12 - 中文输出约束 + Agent Skill 专项分析模板

### 🎯 概述

本次更新解决两个问题：
1. **输出语言不统一**：分析文档中英文混杂，缺少明确的输出语言约束
2. **缺少 Skill 项目专项模板**：`~/opensource` 下有大量 agent skill 项目（agent-skills、code-agent-skills、agentic-harness-patterns-skill、pm-skills、Skill_Seekers 等），现有模板（LLM Agent / 数据库 / 基础设施）不覆盖 Skill 项目特有关切点

### 📝 修改文件

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 新增「📝 基础约束」段落（中文输出）；description 新增 Agent Skill；特性表新增 Agent Skill（10维度）；项目类型识别表新增 Agent Skill；专项模板章节新增 🧩 Agent Skill 专项（10维度）；文档索引新增 Agent Skill 模板表（11个）|
| `scripts/detect-project-type.py` | 新增 `agent-skill` 类型签名（关键词/文件/目录/配置模式，weight=1.3）；模板推荐映射新增 `agent-skill`；分析建议新增 Agent Skill 分支 |

### 📦 新增文件

| 文件 | 大小 | 说明 |
|------|------|------|
| `templates/agent-skill/SKILL_ANALYSIS_OVERVIEW.md` | 8.6KB | Agent Skill 专项分析总览：类型分类（单体/套件/平台/领域）、目标平台兼容性矩阵、核心能力模型、分析流程 |
| `templates/agent-skill/SKILL_01_ARCHITECTURE.md` | 4.2KB | Skill 架构设计：组织形式、目录结构、层级设计、清单管理、元数据、5 种常见架构模式 |
| `templates/agent-skill/SKILL_02_TRIGGER_ROUTING.md` | 3.8KB | 触发与路由：发现策略（关键词/语义/意图/显式/预算约束）、优先级仲裁、反理性化机制 |
| `templates/agent-skill/SKILL_03_INSTRUCTION_ENGINEERING.md` | 4.5KB | 指令工程：SKILL.md 结构模式、6 维质量评估、约束分级（MUST/SHOULD/PREFER）、反理性化体系、指令优先级 |
| `templates/agent-skill/SKILL_04_CONTEXT_MANAGEMENT.md` | 4.7KB | 上下文管理：Token 预算模型、延迟加载、内联 vs 隔离执行、上下文工程四操作（Select/Write/Compress/Isolate）|
| `templates/agent-skill/SKILL_05_TOOL_INTEGRATION.md` | 3.2KB | 工具集成：声明方式、权限管道、安全检查清单（7 项风险等级检测）|
| `templates/agent-skill/SKILL_06_COMPOSITION_ORCHESTRATION.md` | 3.4KB | 组合与编排：6 种 Skill 间关系、3 种编排模式（Coordinator/Fork/Swarm）、子代理委派、4 种任务分解策略 |
| `templates/agent-skill/SKILL_07_PLATFORM_ADAPTATION.md` | 3.2KB | 平台适配：6 平台兼容性矩阵、L0-L4 依赖分级、跨平台迁移成本评估 |
| `templates/agent-skill/SKILL_08_QUALITY_TESTING.md` | 3.2KB | 质量与测试：6 维质量评估、6 种测试类型、遵循度量化方法 |
| `templates/agent-skill/SKILL_09_OBSERVABILITY.md` | 3.7KB | 可观测性：三层追踪模型、7 种失败模式分类、6 个关键性能指标 |
| `templates/agent-skill/SKILL_10_EVOLUTION_GOVERNANCE.md` | 3.1KB | 演进与治理：4 种版本策略、5 维兼容性管理、Skill 生命周期（创建→审核→发布→废弃）|

### 🔧 新增功能 1: 基础约束 — 中文输出

在 SKILL.md 执行注意事项之前新增全局约束段落：

- **输出语言：中文** — 所有分析文档一律中文（含项目级/模块级/文件级/专项/跨模块/元文档/Mermaid 标签）
- 专有名词、类名、函数名、技术术语保留英文原文
- **代码引用** — 保留原始英文代码，配以中文解释

### 🧩 新增功能 2: Agent Skill 专项分析模板（10 维度）

#### 设计依据

结合以下经验提炼分析维度：

| 来源 | 贡献 |
|------|------|
| `agentic-harness-patterns` 分析 | 六大 Harness 层（Memory/Skills/Tools/Context/Multi-agent/Lifecycle）|
| `superpowers` 分析（14 Skill 模块）| Skill 套件组织、生命周期型架构、检查清单验证 |
| `agent-skills` / `code-agent-skills` | Mini 全能型、Skill 清单管理、反理性化设计 |
| `pm-skills` / `Skill_Seekers` | 领域 Skill 包、平台适配、多平台支持 |

#### 10 维度设计

| # | 维度 | 核心关切 |
|---|------|----------|
| 01 | 架构设计 | Skill 如何组织？单体/套件？清单管理？ |
| 02 | 触发与路由 | 意图→Skill 映射？优先级仲裁？反理性化？ |
| 03 | 指令工程 | Prompt 结构？约束分级？遵循度保障？ |
| 04 | 上下文管理 | Token 预算？延迟加载？压缩隔离？ |
| 05 | 工具集成 | 工具声明？权限控制？安全边界？ |
| 06 | 组合与编排 | Skill 间协作？并行编排？子代理委派？ |
| 07 | 平台适配 | 多平台支持？供应商锁定？迁移成本？ |
| 08 | 质量与测试 | Eval 框架？遵循度评估？回归检测？ |
| 09 | 可观测性 | 执行追踪？Token 监控？失败诊断？ |
| 10 | 演进与治理 | 版本管理？兼容性？贡献规范？ |

#### 与传统代码分析的关键差异

| 维度 | 传统代码库 | Agent Skill 项目 |
|------|-----------|-----------------|
| 执行引擎 | CPU / VM | LLM |
| 核心产物 | 可执行二进制 | 指令文档 (SKILL.md) |
| 质量指标 | 性能 / 覆盖率 | 遵循度 / 触发准确率 |
| 依赖管理 | 包管理器 | 元数据声明 |
| 测试方式 | 单元测试 | Eval / 场景回放 |
| 组合方式 | 函数调用 | 意图路由 + 会话上下文 |

### 🔍 新增功能 3: 项目类型检测 — Agent Skill 识别

#### 签名设计

| 信号类型 | 特征示例 |
|----------|----------|
| keywords | `skill`, `harness`, `when_to_use`, `anti-rationalization`, `context budget`, `sub-agent`, `lazy load` (30+ 个) |
| file_patterns | `skill.md`, `manifest.md`, `agents.md`, `claude.md`, `eval` |
| dir_patterns | `skills/`, `.claude/`, `.cursor/`, `references/`, `evals/`, `commands/` |
| config_patterns | `skill`, `claude`, `cursor`, `openclaw`, `metadata.json`, `manifest` |
| weight | 1.3（高特异性，高于 llm-agent 的 1.2）|

#### 验证结果

| 测试项目 | 识别结果 | 置信度 |
|----------|----------|--------|
| `agent-skills` | ✅ Agent Skill | 289.6 |
| `code-agent-skills` | ✅ Agent Skill | 正确识别 |
| `agentic-harness-patterns-skill` | ✅ Agent Skill | 正确识别 |
| `pm-skills` | ✅ Agent Skill | 正确识别 |
| `Skill_Seekers` | ✅ Agent Skill | 正确识别 |
| `doris`（对照组）| ✅ 数据库 | 正确识别 |

### ✅ 验证测试

- [x] `templates/agent-skill/` 下 11 个文件全部创建完成
- [x] SKILL.md description/特性表/类型识别表/专项章节/文档索引全部更新
- [x] detect-project-type.py 新增 agent-skill 签名，5 个 skill 项目全部正确识别
- [x] 非 skill 项目（doris）不受影响，仍正确识别为 database

### 🔀 新增功能 4: 多类型组合分析

#### 核心问题

一个项目可能同时具备多种类型特征（如 Skill 项目包含 LLM Agent 集成、数据库项目内置 AI 能力），之前只取主类型模板，次要类型的专项分析被忽略。

#### 解决方案

| 改动 | 说明 |
|------|--------|
| `detect-project-type.py` 新增 `recommend_templates_multi()` | 合并主类型 + 次要类型的模板，去重后返回 |
| `detect-project-type.py` 报告生成 | 多类型时显示命中类型表 + 组合分析策略建议 |
| `smart-analyze.py` 分析计划生成 | 多类型时 Phase 2 按类型分组，输出到 `30-specialized/<type>/` 子目录 |
| `smart-analyze.py` project-meta.json | 新增 `project_types_all` 数组 + `multi_type` 标记 |
| `SKILL.md` 项目类型章节 | 新增「🔀 多类型组合分析」段落 |

#### 检测阈值

- 主类型: 得分 > 10
- 次要类型命中: 得分 > 主类型 × 50% **且** 得分 > 5

#### 模板合并逻辑

```
recommend_templates_multi(detection_result)
  → 遍历所有命中类型
  → 合并 overview + templates + general
  → 去重（同一模板不重复出现）
  → 返回合并后的模板清单
```

#### 输出目录组织（多类型）

```
30-specialized/
├── agent-skill/              # 主类型专项
│   ├── SKILL_01_ARCHITECTURE.md
│   └── ...
├── llm-agent/                # 次要类型专项
│   ├── LLM_AGENT_01_ARCHITECTURE.md
│   └── ...
└── fullstack-web/            # 次要类型专项（如命中）
    └── ...
```

#### 验证结果

| 测试项目 | 命中类型数 | 模板合并 |
|----------|-----------|----------|
| Skill_Seekers | 3（Agent Skill + LLM Agent + Web）| 22 专项 + 5 通用 + 2 总览 |
| agent-skills | 1（Agent Skill）| 10 专项 + 3 通用 |
| agentic-harness-patterns | 1（Agent Skill）| 10 专项 + 3 通用 |
| autoresearch | 2（General + Pipeline）| 1 专项 + 5 通用 |
| mem0 | 1（LLM Agent）| 11 专项 + 4 通用 |
| doris | 1（Database）| 10 专项 + 2 通用（对照组）|

#### project-meta.json 示例（多类型）

```json
{
  "project_type": "Agent Skill",
  "project_types_all": [
    {"type": "agent-skill", "name": "Agent Skill", "score": 770.3, "role": "primary"},
    {"type": "llm-agent", "name": "LLM Agent", "score": 510.4, "role": "secondary"},
    {"type": "fullstack-web", "name": "全栈 Web 应用", "score": 456.0, "role": "secondary"}
  ],
  "multi_type": true
}
```

### ✅ 验证测试（追加）

- [x] `recommend_templates_multi()` 正确合并去重多类型模板
- [x] Skill_Seekers 命中 3 种类型，22 个专项模板合并
- [x] smart-analyze.py 多类型时 ANALYSIS_PLAN.md 显示类型表 + 分组模板
- [x] project-meta.json 正确记录多类型信息
- [x] 单类型项目不受影响（agent-skills 仍为 1 类型 10 模板）

---

## 2026-07-07 - 模型追踪 + 项目依赖分析（发现优秀第三方库）+ Bug 修复

### 🎯 概述

本次更新解决三个问题：
1. **Bug**: `smart-analyze.py` 引用 `detection_result['primary_name']` 但该 key 不存在，导致崩溃
2. **可追溯性**: 分析输出缺少使用的模型名，无法追踪哪个模型产出的结果
3. **依赖可见性**: 项目依赖散落在各模板，无专门文档，无法系统性发现值得复用的优秀开源库

### 📝 修改文件

| 文件 | 说明 |
|------|------|
| `scripts/smart-analyze.py` | Bug 修复 + 新增 `--model` 参数 + Step 6 生成 `project-meta.json` + Phase 1 加入依赖分析任务 |
| `scripts/verify-analysis.py` | `REQUIRED_FILES` 新增 `dependencies.md` 检查；Layer 1 从 4→5 文档；递归模式也检查 dependencies.md |
| `scripts/generate-research-plan.py` | 新增 Task 2.5 项目依赖分析；研究范围表新增 P0 项目依赖行 |
| `SKILL.md` | 输出结构新增 `dependencies.md`；通用模板表新增依赖分析；快速开始示例加 `--model` 参数 |
| `templates/general/PROJECT_DEPENDENCY_ANALYSIS.md` | **新增** 依赖分析模板 |

### 📦 新增文件

| 文件 | 大小 | 说明 |
|------|------|------|
| `templates/general/PROJECT_DEPENDENCY_ANALYSIS.md` | 4KB | ⭐ 项目依赖分析模板：依赖分类清单、值得关注优秀库分级（⭐/⭐⭐/⭐⭐⭐）、依赖关系图、健康度检查 |

---

### 🔧 新增功能 1: Bug 修复 — primary_name KeyError

**问题**: `detect_project_type()` 返回 `{'primary': 'llm-agent', ...}`，但 `smart-analyze.py` 引用 `detection_result['primary_name']`（不存在），导致 Step 5 崩溃。

**修复**: 从 `PROJECT_TYPE_SIGNATURES[project_type]['name']` 派生显示名，三处引用全部修正。

---

### 🤖 新增功能 2: 模型名追踪

**核心改动**: 分析输出中记录当前使用的模型名，实现可追溯性。

#### 新增参数

```bash
python3 scripts/smart-analyze.py /path/to/project --model "zai/glm-5.2"
# 或通过环境变量
OPENCLAW_MODEL="zai/glm-5.2" python3 scripts/smart-analyze.py /path/to/project
```

#### 输出位置

| 位置 | 内容 |
|------|------|
| `ANALYSIS_PLAN.md` 头部 | `> **分析模型**: \`zai/glm-5.2\`` |
| `ANALYSIS_PLAN.md` 尾部 | `*分析模型: \`zai/glm-5.2\`*` |
| `project-meta.json` | `"model": "zai/glm-5.2"` |
| 终端统计 | `分析模型: zai/glm-5.2` |

#### project-meta.json 结构

```json
{
  "project_name": "BashClaw",
  "project_path": "/home/tianjiqx/opensource/BashClaw",
  "project_type": "LLM Agent",
  "project_type_id": "llm-agent",
  "language": "javascript",
  "model": "zai/glm-5.2",
  "templates_count": 15,
  "files_count": 1,
  "created_at": "2026-07-07 01:04:45",
  "tool": "source-analyzer"
}
```

#### 模型名优先级

1. `--model` 参数（最高）
2. `OPENCLAW_MODEL` 环境变量
3. `"unknown"` 默认值

---

### ⭐ 新增功能 3: 项目依赖分析（强制输出）

**核心目标**: 系统性梳理项目使用的第三方库，发现值得学习和复用的优秀开源库。

#### 模板结构 (PROJECT_DEPENDENCY_ANALYSIS.md)

| 章节 | 内容 |
|------|------|
| 1. 依赖总览 | 语言、包管理器、依赖声明文件、生产/开发依赖数 |
| 2. 依赖分类清单 | 核心框架 / 工具库 / 类型增强 / 开发依赖 / 可选依赖，每个库记录版本/Stars/活跃度/许可证 |
| 3. ⭐ 值得关注的优秀库 | **核心产出** — 分三级：⭐ 了解 / ⭐⭐ 学习 / ⭐⭐⭐ 强烈推荐，每个库有深度点评 |
| 4. 依赖关系图 | Mermaid 依赖树 |
| 5. 依赖健康度 | 版本新鲜度、风险依赖（弃用/漏洞/许可证）|
| 6. 技术选型观察 | 从依赖选择看项目技术品味 |

#### 优秀库评级标准

| 级别 | 标准 |
|------|------|
| ⭐⭐⭐ 强烈推荐 | 解决了通用问题，设计优雅，API 清晰，可直接复用 |
| ⭐⭐ 值得学习 | 有设计亮点，值得借鉴但不一定直接复用 |
| ⭐ 值得了解 | 有特色，一句话亮点说明 |

#### 扫描命令参考（内置）

模板包含各语言的依赖文件扫描命令：Node.js/TypeScript、Python、Go、Rust、Java/Maven、Java/Gradle、Ruby、PHP、Swift。

#### 活跃度判断标准

| 标记 | 含义 | 判断依据 |
|------|------|----------|
| 🟢 活跃 | 持续维护 | 最近 commit < 3 个月 |
| 🟡 维护中 | 低频维护 | 3-12 个月 |
| 🟠 停滞 | 几乎不维护 | 1-2 年 |
| 🔴 弃用 | 已废弃 | > 2 年或标记 deprecated |

#### 输出路径

```
output-dir/
├── 00-project-level/
│   ├── README.md
│   ├── architecture.md
│   ├── dependencies.md    # ⭐ 新增：项目依赖分析
│   ├── quality-score.md
│   └── learning-value.md
```

#### 强制验证

| 验证模式 | 检查内容 |
|----------|----------|
| 标准模式 | Layer 1 必需文件从 4→5（含 dependencies.md），≥4 通过 |
| 递归模式 | 检查 `00-project-level/dependencies.md` 是否存在 |
| REQUIRED_FILES | 检查章节：依赖/版本/许可证/Stars，禁止 TBD/TODO/待补充，≥1 表格 |

---

### ✅ 验证测试

- [x] Bug 修复：BashClaw 项目不再崩溃，输出 `LLM Agent` 而非 KeyError
- [x] `--model` 参数正确写入 ANALYSIS_PLAN.md 头部和尾部
- [x] `OPENCLAW_MODEL` 环境变量正确识别
- [x] `project-meta.json` JSON 格式正确
- [x] ANALYSIS_PLAN.md Phase 1 包含 `1.2 项目依赖分析 ⭐` 任务
- [x] generate-research-plan.py 包含 `Task 2.5: 项目依赖分析`
- [x] verify-analysis.py 正确检查 `dependencies.md` 文件
- [x] verify-analysis.py `--recursive` 正确检查 `00-project-level/dependencies.md`
- [x] 不传 `--model` 时默认 `unknown`，不影响运行

---

## 2026-07-03 - 弹性执行系统：LLM Rate Limit 自动重试 + Cron 无人值守恢复

### 🎯 概述

本次更新解决了核心痛点：**分析大项目时 LLM 并发/rate limit 导致 subagent 失败，主 agent 停止，分析中止，需要手动频繁 `/goal` 续传**。

新增三层防线弹性执行系统，实现无人值守的分析自动重试与恢复。

### 😫 问题根因

```
主 Agent 派发 8 个并行 subagent
    ├── subagent-1 ✅ 完成
    ├── subagent-2 ❌ rate_limit 错误
    ├── subagent-3 ❌ rate_limit 错误
    ├── subagent-4 ❌ context overflow
    ...

结果：部分失败，主 agent 不知道怎么重试 → 分析不完整
更糟：主 agent context 耗尽 → 整个 session 中止
/g goal 虽然能续传 → 需要手动触发，不是真正自动恢复
```

### ✅ 解决方案：三层防线

```
Layer 1: 任务级重试 (Subagent 内部)
├── 每个 subagent 内部捕获 rate_limit
├── 自主等待 + 重试（最多 3 次）
└── 失败则在 .task-report.json 标记 status=failed

Layer 2: 批次级恢复 (主 Agent 职责)
├── sessions_yield 后检查所有 subagent 结果
├── 对失败任务使用指数退避重试
├── 每轮最多重试 5 次
└── 持久化失败状态到 .resilient-checkpoint.json

Layer 3: 全局续传 (Cron 自动恢复)
├── Cron 定期运行 resilient-runner.py --auto-resume
├── 检测失败/未完成任务
├── 自动派发重试任务
└── 全部完成后自动停止
```

### 📦 新增文件

| 文件 | 大小 | 说明 |
|------|------|------|
| `scripts/resilient-runner.py` | 29KB | 🔄 弹性运行器：自动检测失败任务 + 指数退避重试（最多5次）+ 断点续传 |
| `scripts/setup-cron-recovery.py` | 4.8KB | ⏰ Cron 自动恢复设置器：生成定时恢复 cron job 配置 |
| `guides/RESILIENT_EXECUTION.md` | 7.8KB | 📖 弹性执行完整指南（三层防线+主 Agent 协议+退避策略+调试方法）|

### 📝 修改文件

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心特性表格新增「🔄 弹性重试」；可用脚本表格新增 `resilient-runner.py` 和 `setup-cron-recovery.py`；执行纪律新增「弹性执行纪律」6 条；文档索引新增 `RESILIENT_EXECUTION.md` |

---

### 🔄 新增功能 1: 弹性运行器 (resilient-runner.py)

#### 核心能力

| 命令 | 功能 |
|------|------|
| `--init` | 从 PLAN.md 初始化检查点 |
| `--status` | 查看分析进度（含进度条）|
| `--sync` | 扫描输出目录，同步任务完成状态 |
| `--auto-resume` | **核心命令**：自动检测失败任务，生成重试指令 |
| `--json` | JSON 输出（适合 cron / 脚本集成）|

#### 指数退避策略

| 重试次数 | 标准延迟 | Rate Limit 延迟 |
|----------|----------|-----------------|
| 第 1 次 | 60s | 90s |
| 第 2 次 | 120s | 150s |
| 第 3 次 | 240s | 270s |
| 第 4 次 | 480s | 510s |
| 第 5 次 | 960s | 990s |
| 超 5 次 | 自动降级为简化分析或跳过 | |

#### 降级策略

超过 5 次重试后自动降级：
- Layer 3 文件分析 → 跳过（不影响整体）
- Layer 2 模块分析 → 简化分析（只做概览）
- Layer 1 项目分析 → 通知用户（必须手动处理）

#### 关键特性

- **幂等性**：多次运行安全，已完成任务不会重复
- **原子写入**：检查点文件使用 `os.replace()` 保证数据完整
- **断点续传**：所有状态持久化到 `.resilient-checkpoint.json`
- **无人值守**：Cron 驱动，不需要主 agent context 参与

---

### ⏰ 新增功能 2: Cron 自动恢复

#### 工作原理

```
主 Agent 派发任务 → 部分 subagent 因 rate limit 失败
→ 主 Agent session 结束（context 耗尽或错误）
→ Cron 定时触发 isolated session 运行 resilient-runner.py --auto-resume
→ Runner 检测失败任务 → 重新派发 subagent
→ 循环直到所有任务完成或超过最大重试
```

#### 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 检查间隔 | 30 分钟 | cron 定时频率 |
| 最大重试 | 5 次 | 每个任务的尝试上限 |
| 失败通知 | 连续 3 次 | 超过后才通知用户 |
| 通知冷却 | 1 小时 | 避免频繁打扰 |
| delivery | none | 静默执行，不打扰用户 |
| lightContext | true | 轻量上下文，节省 token |

#### 使用方式

```bash
# 生成 cron 配置
python3 scripts/setup-cron-recovery.py \
    --output-dir ~/.openclaw/learning/projects/my-project \
    --project-path ~/opensource/my-project \
    --plan ~/.openclaw/learning/projects/my-project/PLAN.md \
    --interval 30

# → 输出 JSON 配置，通过 cron 工具创建
```

---

### 📖 新增功能 3: 弹性执行指南

#### 指南内容

- 完整的三层防线架构说明
- 快速开始方案 A/B（分析前设置 / 分析中添加）
- 主 Agent 执行协议（Phase 1-3 详细步骤）
- Subagent 任务模板（含弹性重试指令）
- Cron 配置模板和 AgentTurn prompt
- 退避策略详解
- 监控与调试 FAQ
- 完整工作流示例

---

### 📊 脚本清单更新

| 脚本 | 功能 | 状态 |
|------|------|------|
| `resilient-runner.py` | 🔄 弹性运行器 | **新增** |
| `setup-cron-recovery.py` | ⏰ Cron 恢复设置 | **新增** |
| `smart-analyze.py` | 智能分析入口 | 已有 |
| `generate-research-plan.py` | 研究计划生成 | 已有 |
| `generate-file-list.py` | 关键文件识别 | 已有 |
| `generate-module-manifest.py` | 递归模块清单 | 已有 |
| `recursive-orchestrator.py` | 递归编排器 v2 | 已有 |
| `plan-tracker.py` | 计划追踪器 | 已有 |
| `mermaid-validator.py` | Mermaid 检验器 | 已有 |
| `detect-project-type.py` | 项目类型检测 | 已有 |
| `detect-visualization.sh` | 可视化支持检测 | 已有 |
| `orchestrator.py` | 自动编排执行 | 已有 |
| `verify-analysis.py` | 验证 | 已有 |
| `review-agent.py` | 独立审查代理 | 已有 |
| `quick-scan.sh` | 快速扫描 | 已有 |

总计 **15 个脚本**（新增 2 个）

---

### 📚 文档索引更新

| 文档 | 状态 |
|------|-------|
| `guides/RESILIENT_EXECUTION.md` | **新增** — 弹性执行指南 |
| `guides/RECURSIVE_DEEP_ANALYSIS.md` | 已有 |
| `guides/PLAN_DRIVEN_EXECUTION.md` | 已有 |
| `guides/MERMAID_VALIDATION.md` | 已有 |
| `guides/DIAGRAM_GENERATION_GUIDE.md` | 已有 |
| `guides/FILE_LEVEL_ANALYSIS.md` | 已有 |
| `guides/DETAILED_RESEARCH_PLAN.md` | 已有 |
| `guides/PRINCIPLE_DISTILLATION.md` | 已有 |
| `guides/PROBLEM_DRIVEN_ANALYSIS.md` | 已有 |
| `guides/REFERENCE_ORGANIZATION_GUIDE.md` | 已有 |
| `guides/EXECUTION_CLOSURE.md` | 已有 |

总计 **11 个引导文档**（新增 1 个）

---

### ✅ 验证测试

- [x] `resilient-runner.py --help` 语法正确
- [x] `--init` 从模拟 PLAN.md 正确解析 4 个任务
- [x] `--sync` 正确检测已完成任务（1/4 完成）
- [x] `--auto-resume` 正确识别 3 个待重试任务
- [x] `--auto-resume --json` JSON 输出格式正确
- [x] `setup-cron-recovery.py` 生成正确的 cron job JSON
- [x] 检查点文件 `.resilient-checkpoint.json` 原子写入正常
- [x] 幂等性验证：多次运行结果一致

---

### 🔗 相关文档

- [SKILL.md](SKILL.md) - Source Analyzer 主文档
- [guides/RESILIENT_EXECUTION.md](guides/RESILIENT_EXECUTION.md) - 弹性执行指南
- [scripts/resilient-runner.py](scripts/resilient-runner.py) - 弹性运行器
- [scripts/setup-cron-recovery.py](scripts/setup-cron-recovery.py) - Cron 恢复设置器

---

## 2026-07-02 - 递归深度分析模式 + 计划驱动执行 + Mermaid 检验

### 🎯 概述

本次更新解决了核心问题：**大型/超大型项目（500+ 文件）的源码分析深度不足**。

新增三大机制：
1. **🔁 递归深度分析模式** — 对每个模块递归执行完整三层分析
2. **📋 计划驱动执行** — PLAN.md 作为契约，检查点追踪，计划验收
3. **🎨 Mermaid 图表检验** — 自动检测 11 类语法错误

### 📦 新增文件

| 文件 | 大小 | 说明 |
|------|------|------|
| `guides/RECURSIVE_DEEP_ANALYSIS.md` | 6KB | 递归深度分析完整指南 |
| `guides/PLAN_DRIVEN_EXECUTION.md` | 8KB | 计划驱动执行指南（检查点+验收）|
| `guides/MERMAID_VALIDATION.md` | 2.3KB | Mermaid 检验规则说明 |
| `scripts/generate-module-manifest.py` | 11.7KB | 递归模块清单生成器（v2）|
| `scripts/recursive-orchestrator.py` | 9.9KB | 递归编排器 v2（计划驱动）|
| `scripts/plan-tracker.py` | 18.6KB | 计划追踪器（5 子命令）|
| `scripts/mermaid-validator.py` | 22KB | Mermaid 图表语法检验器 |

### 📝 修改文件

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 新增递归深度分析章节、计划驱动执行纪律、脚本列表/文档索引更新、描述更新 |
| `scripts/verify-analysis.py` | 新增 `--recursive` 验证模式（阈值 50 文档 / 5 模块 / 80% INDEX 覆盖率）|
| `guides/DIAGRAM_GENERATION_GUIDE.md` | 质量检查章节新增自动化检验集成 |

---

### 🔁 新增功能 1: 递归深度分析模式

#### 设计动机

最大分析模式对大型项目（如 VictoriaMetrics 267K 行 / 1052 文件）的每个模块仅 3 个文档，深度严重不足。

#### 解决方案

对每个模块递归执行完整三层分析，让每个模块拥有独立、深入的分析报告。

#### 三阶段流程

```
Phase 1: 项目级扫描（递归识别所有模块 + 评估规模与重要性）
Phase 2: 模块级递归（每个模块独立完整三层分析，分批并行）
Phase 3: 项目级总结（跨模块对比 + 可移植模式提炼）
```

#### 模块重要性评估

不只看规模，还看：
- **入口文件检测**（main.go / index.ts / __init__.py 等）
- **行数密度**（少量文件但大量代码 = 核心逻辑）

评估结果分 3 级：`high` / `medium` / `low`

#### 自适应分析策略

| 模块规模 | 重要性 | 策略 | 预期文档 |
|----------|--------|------|----------|
| Large (> 100 文件) | - | 子模块递归 + 10-20 关键文件 | ~25 |
| Medium (20-100 文件) | - | 完整三层 + 5-10 关键文件 | ~15 |
| Small + High | high | Layer 1 + 3-5 关键文件 | ~8 |
| Small + Low | low | Layer 1 only | ~4 |

#### 递归展开

`generate-module-manifest.py` 支持多层递归展开（`--max-recursion-depth`），不再只展开一层。

实际测试 (VictoriaMetrics):
- 递归识别出 **152 个模块**（之前 3 个）
- 精确统计 **229K 行**（之前 128K，准确率 48%→86%）
- 高重要性模块 **23 个**

#### 并行控制

- `--max-parallel N`：分批并行执行（默认 8）
- `--priority-only`：只分析 high 重要性模块

VM 的 152 模块可筛选为 23 个 high，4 批 × 6 并行。

#### 与最大分析模式对比

| 特性 | 最大分析模式 | 递归深度分析 |
|------|--------------|--------------|
| 模块深度 | 浅（3 文档/模块）| 深（完整三层/模块）|
| 文件覆盖 | 部分关键文件 | 每模块独立选择关键文件 |
| 适用规模 | 中小型项目 | 大型/超大型项目 |
| 文档数量 | 40-80 | 100-300+ |
| 并行度 | 中 | 高（模块级分批并行）|
| 重要性评估 | ❌ | ✅ 自动评估 |
| 分批控制 | ❌ | ✅ max-parallel |

---

### 📋 新增功能 2: 计划驱动执行

#### 设计动机

计划生成了但没人按计划执行，执行完了也没人检查是否偏离计划。

#### 核心机制

```
生成 PLAN.md（契约）
  → 初始化检查点 (.checkpoint.json)
  → 按计划执行（子代理引用 Task ID + 预期输出）
  → 每批同步检查点
  → 子代理生成 .task-report.json
  → 计划验收（对比预期 vs 实际）
  → 输出 PLAN_VERIFICATION_REPORT.md
```

#### PLAN.md 结构

每个任务包含 `### Task N: name [status: pending]` 格式：
- 模块名称、路径、策略、规模、重要性
- **预期文件清单**（验收标准）
- 完成条件
- sessions_spawn 命令（含计划引用和报告要求）

#### 检查点追踪 (.checkpoint.json)

记录每个任务的：
- status: pending / in_progress / completed / partial / failed
- expected_files vs actual_files
- started_at / completed_at

#### 子代理报告 (.task-report.json)

每个子代理**必须**在完成后生成结构化报告：
- status: completed / partial / failed
- files_generated: 实际生成的文件清单
- quality_self_score: 自评 0-100
- key_findings: 关键发现
- design_patterns: 设计模式
- mermaid_diagrams: 图表数量

#### plan-tracker.py 5 个子命令

| 命令 | 功能 |
|------|------|
| `init` | 从 PLAN.md 初始化检查点 |
| `sync` | 扫描实际输出，更新任务状态 |
| `status` | 查看进度（含进度条）|
| `complete` | 手动标记任务完成 |
| `verify` | 计划验收（输出符合度报告）|

#### 质量保障闭环

```
生成模块清单 → 生成 PLAN.md → 初始化检查点
  → 按计划执行（Task ID 引用 + .task-report.json）
  → 每批同步检查点
  → 计划验收（预期 vs 实际对比）
  → 标准验证 + Mermaid 检验
  → 补救缺失
```

---

### 🎨 新增功能 3: Mermaid 图表检验

#### 设计动机

生成的 Mermaid 图表经常有语法错误，无法渲染。

#### 检验规则（11 条）

**错误级别**（导致渲染失败）:

| 规则 | 说明 |
|------|------|
| `INVALID_TYPE` | 未知的图表类型声明 |
| `UNCLOSED_BLOCK` | 代码块未闭合 |
| `MISSING_END` / `EXTRA_END` | subgraph/end 配对 |
| `UNDEFINED_NODE_STYLE` | style 引用了未定义的节点 |
| `MMDC_ERROR` | mermaid CLI 报错（可选深度验证）|

**警告级别**（可能渲染异常）:

| 规则 | 说明 |
|------|------|
| `UNESCAPED_PARENS` | 节点文本中未转义的括号 |
| `NESTED_QUOTES` | 嵌套引号 |
| `FULLWIDTH_CHARS` | 全角字符 |
| `TAB_INDENT` | Tab 缩进 |
| `INVALID_RELATION` | classDiagram 无效关系 |
| `PARTICIPANT_SPACE` | participant 名称含空格 |

#### 使用方式

```bash
# 递归检查目录
python3 scripts/mermaid-validator.py output-dir/ --recursive

# 保存报告
python3 scripts/mermaid-validator.py output-dir/ -o MERMAID_VALIDATION_REPORT.md

# 使用 mermaid CLI 深度验证
python3 scripts/mermaid-validator.py file.md --use-mmdc
```

---

### 📊 脚本清单更新

| 脚本 | 功能 | 状态 |
|------|------|------|
| `smart-analyze.py` | 智能分析入口 | 已有 |
| `generate-research-plan.py` | 研究计划生成 | 已有 |
| `generate-file-list.py` | 关键文件识别 | 已有 |
| `generate-module-manifest.py` | 🔁 递归模块清单生成 | **新增** |
| `recursive-orchestrator.py` | 🔁 计划驱动编排器 v2 | **新增** |
| `plan-tracker.py` | 📋 计划追踪器 | **新增** |
| `mermaid-validator.py` | 🎨 Mermaid 检验器 | **新增** |
| `detect-project-type.py` | 项目类型检测 | 已有 |
| `detect-visualization.sh` | 可视化支持检测 | 已有 |
| `orchestrator.py` | 自动编排执行 | 已有 |
| `verify-analysis.py` | 验证（+`--recursive` 模式）| **更新** |
| `review-agent.py` | 独立审查代理 | 已有 |
| `quick-scan.sh` | 快速扫描 | 已有 |

总计 **13 个脚本**（新增 4 个，更新 1 个）

---

### 📚 文档索引更新

| 文档 | 状态 |
|------|------|
| `guides/RECURSIVE_DEEP_ANALYSIS.md` | **新增** — 递归深度分析指南 |
| `guides/PLAN_DRIVEN_EXECUTION.md` | **新增** — 计划驱动执行指南 |
| `guides/MERMAID_VALIDATION.md` | **新增** — Mermaid 检验规则说明 |
| `guides/DIAGRAM_GENERATION_GUIDE.md` | **更新** — 新增自动化检验集成 |
| `guides/FILE_LEVEL_ANALYSIS.md` | 已有 |
| `guides/DETAILED_RESEARCH_PLAN.md` | 已有 |
| `guides/PRINCIPLE_DISTILLATION.md` | 已有 |
| `guides/PROBLEM_DRIVEN_ANALYSIS.md` | 已有 |
| `guides/REFERENCE_ORGANIZATION_GUIDE.md` | 已有 |
| `guides/EXECUTION_CLOSURE.md` | 已有 |

总计 **10 个引导文档**（新增 3 个，更新 1 个）

---

### ✅ 验证测试

- [x] VictoriaMetrics (Go, 1052 文件) — 152 模块，23 个 high 重要性
- [x] KetaOps (Java, 16K 文件) — 73 模块，38 个 high 重要性
- [x] 所有 12 个 Python 脚本语法正确
- [x] PLAN.md 结构化任务格式正确（25 个 Task）
- [x] plan-tracker 5 个子命令均可运行
- [x] mermaid-validator 正确检测 6/6 测试图表（4 正确 + 2 错误）
- [x] verify-analysis.py --recursive 阈值检查正确

---

### 🔗 相关文档

- [SKILL.md](SKILL.md) - Source Analyzer 主文档
- [guides/RECURSIVE_DEEP_ANALYSIS.md](guides/RECURSIVE_DEEP_ANALYSIS.md) - 递归深度分析指南
- [guides/PLAN_DRIVEN_EXECUTION.md](guides/PLAN_DRIVEN_EXECUTION.md) - 计划驱动执行指南
- [guides/MERMAID_VALIDATION.md](guides/MERMAID_VALIDATION.md) - Mermaid 检验规则

---

## 2026-06-27 - 新增核心功能分析与实现逻辑追踪

### 🎯 新增功能

#### 1. 核心功能分析模板 (CORE_FEATURES_ANALYSIS.md)
**文件大小**: 11KB | **行数**: 408 行

**功能定位**: 从"功能视角"分析项目，回答"项目能做什么"

**核心内容**:
- 功能清单与分类体系（核心层/扩展层/集成层）
- 功能分类矩阵（按价值/频率/复杂度/依赖）
- 功能依赖关系图（Mermaid flowchart）
- MoSCoW 优先级分析
- 价值-复杂度矩阵（quadrantChart）
- 功能深度分析（定义、场景、输入输出、边界、依赖、度量）
- 功能交互流程（时序图、数据流图）
- 竞品功能对比
- 功能演进历史与路线图
- **新增**: 功能实现逻辑追踪章节（入口点映射、调用链概览、数据流转换、复杂度评估、实现决策）

**使用场景**:
- 快速了解项目功能全貌
- 评估功能完整性与优先级
- 对比竞品功能差异
- 理解功能间的依赖关系

---

#### 2. 功能实现逻辑追踪模板 (FEATURE_IMPLEMENTATION_LOGIC.md)
**文件大小**: 11KB | **行数**: 366 行

**功能定位**: 从"代码视角"追踪功能实现，回答"功能怎么做"

**核心内容**:
- 功能入口点映射（REST API/gRPC/CLI/Event/Cron/WebSocket）
- 调用链详细分析（分层追踪：入口层 → 业务层 → 数据层）
- 关键分支决策点（条件判断、设计原因）
- 数据流转换链（输入 → DTO → 领域参数 → Entity → 结果 → 输出）
- 错误处理路径（错误类型、处理方式、错误码、日志级别）
- 性能关键路径（耗时占比、瓶颈风险、优化手段）
- 跨功能调用链对比（复杂度对比、共享代码路径）
- 异步与并发分析（异步调用、并发控制、并发模式）
- 缓存与性能路径（缓存命中路径、性能热点分析）

**使用场景**:
- 深入理解功能实现细节
- 定位性能瓶颈与优化点
- 理解代码调用关系
- 评估实现复杂度

**与核心功能分析的区别**:
- **核心功能分析**: 功能"是什么"——功能清单、分类、优先级、依赖关系
- **功能实现逻辑**: 功能"怎么做"——代码调用链、数据流、分支决策、异常路径

---

### 📝 SKILL.md 更新

#### 新增特性表格条目
```markdown
| **🔥🔥 核心功能分析** | 功能清单、分类矩阵、优先级、依赖关系、实现逻辑追踪 | [CORE_FEATURES_ANALYSIS.md] |
| **🔥🔥🔥 功能实现逻辑追踪** | 调用链分析、数据流转换、分支决策、错误处理路径、性能关键路径 | [FEATURE_IMPLEMENTATION_LOGIC.md] |
```

#### 最大分析模式更新
**附加分析表格**新增两行（标记为"必做"）:
```markdown
| **🔥🔥 核心功能分析** | 所有项目（必做） | 1 个功能清单+分类+优先级文档 |
| **🔥🔥🔥 功能实现逻辑追踪** | 核心功能≥3个（必做） | 1 个调用链+数据流+分支决策文档 |
```

**输出目录结构**新增 `30-core-features/` 目录:
```
output-dir/
├── ...
├── 30-core-features/                 # 核心功能分析
│   ├── CORE_FEATURES_ANALYSIS.md     # 功能清单、分类、优先级、依赖关系
│   └── FEATURE_IMPLEMENTATION_LOGIC.md # 功能调用链、数据流、分支决策
├── 40-specialized/                   # 专项分析（原 30-specialized）
└── 50-appendix/                      # 附加分析（原 40-appendix）
```

#### 文档索引表格新增
```markdown
| [CORE_FEATURES_ANALYSIS.md](templates/general/CORE_FEATURES_ANALYSIS.md) | 🔥🔥 核心功能分析（功能清单、分类、优先级、依赖、实现逻辑） |
| [FEATURE_IMPLEMENTATION_LOGIC.md](templates/general/FEATURE_IMPLEMENTATION_LOGIC.md) | 🔥🔥🔥 功能实现逻辑追踪（调用链、数据流、分支决策、错误处理） |
```

---

### 🎨 分析流程优化

#### 新增分析阶段
在最大分析模式中，新增 **Step 3.5: 核心功能分析**（位于模块级分析之后、专项分析之前）:

```
Step 1: 项目类型识别
  ↓
Step 2: 三层分析全开 (Layer 1+2+3)
  ↓
Step 3: 专项模板全开 (LLM Agent/Database/Infrastructure)
  ↓
Step 3.5: 核心功能分析 (新增)
  ├── 识别所有功能入口
  ├── 生成功能清单与分类
  ├── 绘制功能依赖关系图
  ├── 追踪核心功能调用链
  └── 分析数据流转换
  ↓
Step 4: 附加分析（按需）
  ↓
Step 5: 输出汇总
```

---

### 📊 模板对比

| 维度 | 核心功能分析 | 功能实现逻辑 |
|------|--------------|--------------|
| **关注点** | 功能"是什么" | 功能"怎么做" |
| **分析粒度** | 功能级 | 代码级 |
| **核心问题** | 功能清单、优先级、依赖 | 调用链、数据流、分支 |
| **入口** | 功能名称、功能ID | 入口文件、入口函数 |
| **输出** | 功能分类矩阵、依赖图 | 调用链时序图、数据流图 |
| **性能分析** | 功能度量指标 | 性能热点、耗时占比 |
| **错误处理** | 功能边界与限制 | 错误处理路径、错误码 |
| **适用场景** | 产品视角、功能评估 | 开发视角、代码审查 |

---

### ✅ 验证清单

- [x] 创建 `CORE_FEATURES_ANALYSIS.md` 模板（11KB, 408 行）
- [x] 创建 `FEATURE_IMPLEMENTATION_LOGIC.md` 模板（11KB, 366 行）
- [x] 更新 `SKILL.md` 特性表格（新增 2 行）
- [x] 更新 `SKILL.md` 附加分析表格（新增 2 行，标记为"必做"）
- [x] 更新 `SKILL.md` 输出目录结构（新增 `30-core-features/`）
- [x] 更新 `SKILL.md` 文档索引表格（新增 2 行）
- [x] 清理重复条目（删除特性表格中的重复项）
- [x] 验证所有路径引用正确

---

### 📚 使用示例

#### 示例 1: 分析 Web 应用的核心功能
```bash
# 1. 生成功能清单
使用 CORE_FEATURES_ANALYSIS.md 模板
  → 识别所有 REST API 端点
  → 分类：核心层（认证、数据 CRUD）、扩展层（导出、通知）、集成层（第三方登录）
  → 绘制功能依赖关系图
  → MoSCoW 优先级排序

# 2. 追踪核心功能实现
使用 FEATURE_IMPLEMENTATION_LOGIC.md 模板
  → 选择 3-5 个核心功能（如：用户注册、数据查询）
  → 追踪调用链：Handler → Service → Repository → Database
  → 分析数据流转换：JSON → DTO → Entity → Result
  → 识别性能瓶颈：数据库查询占 60% 耗时
```

#### 示例 2: 分析 CLI 工具的核心功能
```bash
# 1. 生成功能清单
使用 CORE_FEATURES_ANALYSIS.md 模板
  → 识别所有 CLI 命令
  → 分类：核心命令（init, build, deploy）、扩展命令（test, lint）
  → 功能依赖关系图：deploy 依赖 build，build 依赖 init

# 2. 追踪核心命令实现
使用 FEATURE_IMPLEMENTATION_LOGIC.md 模板
  → 选择核心命令（如：build）
  → 追踪调用链：cmd.Build() → builder.Compile() → output.Generate()
  → 分析分支决策：根据 target platform 选择不同编译器
  → 错误处理路径：编译失败 → 回滚 → 输出错误日志
```

---

### 🎯 预期收益

1. **功能视角补全**: 现有分析偏"架构视角"和"代码质量视角"，新增"功能视角"后形成完整分析体系
2. **实现逻辑透明化**: 追踪功能从入口到输出的完整代码路径，便于理解实现细节
3. **性能瓶颈定位**: 通过分析调用链和数据流，快速定位性能热点
4. **代码审查支持**: 为代码审查提供结构化的分析框架
5. **知识传递**: 帮助新成员快速理解项目功能和实现

---

### 🔗 相关文档

- [CORE_FEATURES_ANALYSIS.md](templates/general/CORE_FEATURES_ANALYSIS.md) - 核心功能分析模板
- [FEATURE_IMPLEMENTATION_LOGIC.md](templates/general/FEATURE_IMPLEMENTATION_LOGIC.md) - 功能实现逻辑追踪模板
- [SKILL.md](SKILL.md) - Source Analyzer 主文档

---

*最后更新: 2026-06-27*
