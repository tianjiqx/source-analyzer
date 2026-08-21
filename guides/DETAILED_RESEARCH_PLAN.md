# 详细研究计划模板

> **做什么**: 分析前制定详细研究计划（预研究 + 任务分解），确保覆盖全面、不遗漏关键。

---

## 研究计划设计理念

### 核心改进点

**现有问题**:
- 分析计划过于粗略（"分析架构"）
- 缺少具体文件/函数指引
- 容易遗漏重要内容

**改进方案**:
- 三层研究计划（项目 → 模块 → 文件）
- 明确输入文件、输出内容、验证标准
- 任务管理集成，追踪进度
- **问题驱动研究方法** (新增)

### 问题驱动研究方法

**核心理念**: 从实际问题出发，而非从技术出发

**问题驱动流程**:
```
识别问题 → 分析根因 → 研究方案 → 实验验证 → 总结沉淀
   ↓           ↓           ↓           ↓           ↓
 问题定位    深入分析    对比方案    benchmark    文档记录
```

**与传统方法对比**:

| 对比维度 | 传统方法 | 问题驱动方法 |
|----------|----------|--------------|
| **起点** | 技术方案 | 实际问题 |
| **研究目标** | 技术掌握 | 问题解决 |
| **评估标准** | 知识完整性 | 问题解决程度 |
| **适用场景** | 技术学习 | 性能优化、系统改进 |

**问题驱动优势**:
- ✅ 研究目标明确
- ✅ 评估标准清晰
- ✅ 避免过度研究
- ✅ 实用性强

**参考**: 《向量化执行》从IPC低问题出发的分析方法

---

## 研究计划模板

### 完整研究计划结构

```markdown
# [Project Name] 详细研究计划

> **For agentic workers:** Follow this plan step-by-step

**研究目标**: [一句话描述]
**项目路径**: `/path/to/project`
**技术栈**: [主要语言 + 框架]
**输出目录**: `$OUTPUT_BASE/project-name/`
**计划版本**: v1.0
**预计时间**: XX 小时
**研究方法**: [ ] 传统方法 / [x] 问题驱动方法

---

## 零、问题驱动阶段（可选）

> **适用场景**: 性能优化、系统改进、故障排查、设计改进

### Task 0-1: 问题识别

**目的**: 识别并量化实际问题，明确研究目标

**问题描述模板**:
```markdown
# 问题: [问题描述]

## 问题现象
- 现象1: [具体描述]
- 现象2: [具体描述]

## 问题量化
| 指标 | 当前值 | 预期值 | 差距 |
|------|--------|--------|------|
| 指标1 | X | Y | Z% |

## 问题影响
| 影响维度 | 影响程度 | 具体影响 |
|----------|----------|----------|
| 性能 | 高 | 吞吐降低X% |
```

**详细步骤**:

- [ ] **Step 0-1.1: 观察问题现象**
  - Method: 监控工具、日志分析、用户反馈
  - Extract: 问题具体表现
  - Output: 问题现象清单

- [ ] **Step 0-1.2: 量化问题影响**
  - Method: 性能测试、对比基准
  - Extract: 具体数值差距
  - Output: 问题量化数据表

- [ ] **Step 0-1.3: 确定问题边界**
  - Method: 场景测试、触发条件分析
  - Extract: 受影响场景、不受影响场景
  - Output: 问题边界界定

**完成标准**:
- [ ] 问题现象描述具体
- [ ] 问题量化数据完整
- [ ] 问题边界清晰

**示例 (IPC低问题)**:
```markdown
# 问题: MySQL表达式计算IPC低

## 问题现象
- TPC-H Q1执行时IPC只有0.7
- 科学计算IPC可达2.0

## 问题量化
| 指标 | 当前值 | 预期值 | 差距 |
|------|--------|--------|------|
| IPC | 0.7 | 2.0 | 65%差距 |

## 问题边界
- 触发: OLAP查询（大量表达式计算）
- 受影响: MySQL, PostgreSQL
- 不受影响: MonetDB/X100（向量化执行）
```

---

### Task 0-2: 根因分析

**目的**: 分析问题根本原因，找到关键瓶颈

**根因分析模板**:
```markdown
## 根因分析

### 表层分析
- 原因1: [直接原因]
- 原因2: [直接原因]

### 深层根因
| 原因类别 | 根因描述 | 影响程度 | 影响范围 |
|----------|----------|----------|----------|
| 架构层面 | [根因] | 高 | 全局 |
| 算法层面 | [根因] | 中 | 局部 |

### 影响传导图
```
根因 → 中间影响 → 最终问题
```
```

**详细步骤**:

- [ ] **Step 0-2.1: 表层分析**
  - Method: Profiling工具、热点分析
  - Tool: perf, flamegraph, memory profiler
  - Extract: 直接观察到的原因
  - Output: 表层原因清单

- [ ] **Step 0-2.2: 根因挖掘**
  - Method: 代码深入、架构分析
  - Extract: 架构层面/算法层面的根本原因
  - Output: 根因分析表

- [ ] **Step 0-2.3: 影响评估**
  - Method: 影响路径分析
  - Extract: 根因→问题的传导路径
  - Output: 影响传导图

**完成标准**:
- [ ] 表层原因明确
- [ ] 根因分析到架构层面
- [ ] 影响传导路径清晰

**示例 (IPC低根因)**:
```markdown
## 根因分析

### 表层分析
- 函数调用开销大（38指令/49周期）
- IPC仅0.7（理论值2.0）

### 深层根因
| 原因类别 | 根因描述 | 影响程度 |
|----------|----------|----------|
| 架构层面 | Volcano迭代模型解释执行 | 高 |
| 实现层面 | 解释执行指令效率低 | 中 |

### 影响传导图
```
Volcano架构 → 解释执行开销 → IPC低 → 吞吐低
```
```

---

### Task 0-3: 方案研究

**目的**: 调研多种解决方案，对比优劣

**方案研究模板**:
```markdown
## 方案研究

### 方案A: [方案名称]
- 原理: [方案原理]
- 效果: [预期效果]
- 成本: [实施成本]
- 风险: [风险评估]

### 方案对比矩阵
| 维度 | 方案A | 方案B | 方案C |
|------|-------|-------|-------|
| 效果 | X倍 | Y倍 | Z倍 |
| 成本 | 低/中/高 | | |
```

**详细步骤**:

- [ ] **Step 0-3.1: 技术调研**
  - Method: 论文阅读、开源项目研究
  - Extract: 相关技术方案列表
  - Output: 技术方案调研表

- [ ] **Step 0-3.2: 方案对比**
  - Method: 效果估算、成本评估、风险分析
  - Extract: 各方案优劣对比
  - Output: 方案对比矩阵

- [ ] **Step 0-3.3: 推荐方案**
  - Method: 综合评估、场景匹配
  - Extract: 最佳方案推荐
  - Output: 推荐方案及理由

**完成标准**:
- [ ] 至少研究2-3种方案
- [ ] 对比矩阵完整
- [ ] 有明确的推荐方案

**示例 (向量化vs编译)**:
```markdown
## 方案研究

### 方案A: 向量化执行
- 原理: 批量操作分摊开销
- 效果: IPC提升至1.5+, 吞吐5-10倍
- 成本: 中

### 方案B: 编译执行
- 原理: 生成专用代码
- 效果: 指令数减少2倍
- 成本: 高（编译开销ms级）

### 方案对比
| 维度 | 向量化 | 编译 |
|------|--------|------|
| IPC提升 | 1.5+ | 2.0+ |
| 编译开销 | 无 | ms级 |
| 推荐指数 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
```

---

### 问题驱动总结

**问题驱动方法适用场景**:

| 场景 | 适用程度 | 说明 |
|----------|----------|------|
| 性能优化 | ⭐⭐⭐⭐⭐ | 从瓶颈出发系统优化 |
| 系统改进 | ⭐⭐⭐⭐⭐ | 从问题出发改进设计 |
| 故障排查 | ⭐⭐⭐⭐⭐ | 从症状出发定位根因 |
| 技术学习 | ⭐⭐⭐ | 问题驱动+技术驱动结合 |
| 架构设计 | ⭐⭐⭐⭐ | 从需求出发设计 |

**问题驱动方法关键要点**:

| 要点 | 说明 |
|------|------|
| **明确问题** | 问题现象具体化、量化 |
| **深入根因** | 分析到架构/算法层面 |
| **多方案对比** | 至少研究2-3种方案 |
| **验证效果** | Benchmark对比验证 |
| **文档沉淀** | 记录问题→方案→效果 |

---

## 一、研究范围定义

### 1.1 分析维度

| 维度 | 重要性 | 分析深度 | 输出文件 |
|------|--------|----------|----------|
| 项目概览 | P0 | Layer 1 | 00-README.md |
| 架构设计 | P0 | Layer 1+2 | 01-architecture.md + 模块文档 |
| 核心代码 | P0 | Layer 3 | 02-core-code.md + 文件分析 |
| 质量评估 | P1 | Layer 1 | 03-quality-score.md |
| 学习价值 | P1 | Layer 1 | 04-learning-value.md |

### 1.2 分析深度选择

**已选择**: [ ] Layer 1 (项目级) / [ ] Layer 2 (模块级) / [x] Layer 3 (文件粒度)

**文件数量**: XX 个关键文件

**模块数量**: XX 个核心模块

---

## 二、预研究阶段（探索性扫描）

### Task 0: 项目探索扫描

**目的**: 快速了解项目结构，为详细计划提供依据

**步骤**:

- [ ] **Step 0.1: 目录结构扫描**
  ```bash
  # 命令
  tree -L 2 -I 'target|.git|node_modules' /path/to/project
  
  # 提取内容
  - 顶层模块列表
  - 每个模块的文件数估算
  - 构建系统类型 (Maven/Gradle/npm/...)
  
  # 输出
  记录到 scratchpad.md
  ```

- [ ] **Step 0.2: 语言统计**
  ```bash
  # 命令
  cloc /path/to/project --by-lang
  
  # 提取内容
  - 主语言及占比
  - 文件总数
  - 代码行数
  
  # 输出
  记录到 scratchpad.md
  ```

- [ ] **Step 0.3: 入口点识别**
  ```bash
  # 命令
  find . -name "*Application*" -o -name "*Main*" -o -name "*Bootstrap*"
  
  # 提取内容
  - 启动类路径
  - CLI 入口
  - API 入口
  
  # 输出
  记录入口列表到 scratchpad.md
  ```

- [ ] **Step 0.4: Git 历史扫描**
  ```bash
  # 命令
  git log --oneline --name-only | head -200
  
  # 提取内容
  - 最近修改频率 Top 10 文件
  - 主要贡献者
  - 提交频率
  
  # 输出
  记录高频文件列表到 scratchpad.md
  ```

- [ ] **Step 0.5: 文档扫描**
  ```bash
  # 命令
  ls -la *.md README*
  
  # 提取内容
  - README.md 是否存在
  - 文档完整性
  - 架构文档
  
  # 输出
  记录文档清单到 scratchpad.md
  ```

**完成标准**:
- [ ] scratchpad.md 包含目录结构
- [ ] scratchpad.md 包含语言统计
- [ ] scratchpad.md 包含入口点列表
- [ ] scratchpad.md 包含高频文件列表

---

## 三、详细研究计划（分层任务）

### Phase 1: 项目级分析

#### Task 1: 项目概览分析

**目标**: 输出 `00-project-level/README.md`

**输入文件**:
- `README.md` (如果存在)
- `pom.xml` 或 `build.gradle` 或 `package.json`
- `LICENSE`
- scratchpad.md (预研究结果)

**输出要求**:

| 章节 | 必需内容 | 验证标准 |
|------|----------|----------|
| 基本信息 | 名称、Stars、语言、License | 所有字段有具体值 |
| 核心特性 | 3-5 个关键特性 | 有代码示例或链接 |
| 快速开始 | 安装 + 运行命令 | 命令可执行 |
| 技术栈 | 语言 + 框架 + 工具 | 有版本号 |

**详细步骤**:

- [ ] **Step 1.1: 提取基本信息**
  - Read: `README.md` lines 1-100
  - Extract: name, description, stars, license
  - Verify: 所有字段非空

- [ ] **Step 1.2: 提取构建信息**
  - Read: `pom.xml` OR `build.gradle` OR `package.json`
  - Extract: dependencies, version, build system
  - Verify: 依赖列表 > 5 个

- [ ] **Step 1.3: 提取统计数据**
  - From: scratchpad.md
  - Extract: file count, line count, language distribution
  - Verify: 数据一致

- [ ] **Step 1.4: 提取核心特性**
  - Read: `README.md` Features section
  - Extract: 3-5 个特性 + 对应代码路径
  - Verify: 每个特性有说明

- [ ] **Step 1.5: 生成快速开始**
  - Read: `README.md` Installation section
  - Extract: install commands + run commands
  - Verify: 命令格式正确

- [ ] **Step 1.6: 写入文档**
  - Write: `00-project-level/README.md`
  - Verify: 文件存在 + 包含所有章节

- [ ] **Step 1.7: 完整性验证**
  - Check: 所有必需章节存在
  - Check: 无 placeholder ("TBD", "TODO")
  - Pass: 验证通过 → Task 完成

---

#### Task 2: 架构设计分析

**目标**: 输出 `00-project-level/architecture.md` + 模块文档

**输入文件**:
- scratchpad.md (目录结构)
- 入口点文件
- 主要配置文件

**输出要求**:

| 章节 | 必需内容 | 验证标准 |
|------|----------|----------|
| 模块划分 | 模块列表 + 职责 | > 3 个模块 |
| 数据流 | 流程图 | 有起点终点 |
| 组件交互 | 组件关系图 | 有调用关系 |
| 启动流程 | 启动链 | 有步骤说明 |

**详细步骤**:

- [ ] **Step 2.1: 提取模块列表**
  - From: scratchpad.md 目录结构
  - Extract: 顶层模块 + 职责推断
  - Verify: 模块数 > 3

- [ ] **Step 2.2: 分析启动链**
  - Read: 入口点文件 (e.g., `Bootstrap.java`)
  - Extract: 初始化顺序 + 关键依赖
  - Verify: 有流程说明

- [ ] **Step 2.3: 分析数据流**
  - Read: 核心处理类
  - Extract: 请求 → 处理 → 存储 → 响应
  - Verify: 有流向图

- [ ] **Step 2.4: 分析配置系统**
  - Read: 配置文件 (e.g., `application.yml`)
  - Extract: 配置项 + 环境变量
  - Verify: 配置项 > 5

- [ ] **Step 2.5: 写入文档**
  - Write: `00-project-level/architecture.md`
  - Verify: 文件存在 + 包含所有章节

- [ ] **Step 2.6: 完整性验证**
  - Check: 所有必需章节存在
  - Check: 有架构图
  - Pass: 验证通过 → Task 完成

---

### Phase 2: 模块级分析

#### Task 3: Core 模块分析

**目标**: 输出 `10-module-level/core/` (3 个文档)

**输入文件**:
- `core/` 目录下所有核心文件
- 相关接口定义

**输出要求**:

| 文档 | 必需内容 |
|------|----------|
| overview.md | 模块职责 + 核心类列表 |
| interface.md | 公开接口 + 参数定义 |
| dependencies.md | 上游/下游依赖图 |

**详细步骤**:

- [ ] **Step 3.1: 扫描模块文件**
  ```bash
  find core/ -type f -name "*.java" -o -name "*.py"
  ```
  Extract: 文件列表 + 估算职责

- [ ] **Step 3.2: 识别核心类**
  - Read: Top 5 largest files
  - Extract: 类名 + 职责 + 关键方法

- [ ] **Step 3.3: 提取公开接口**
  - Read: Interface files
  - Extract: 方法签名 + 参数

- [ ] **Step 3.4: 分析依赖关系**
  ```bash
  rg "import.*core" --type java
  ```
  Extract: 调用者列表

- [ ] **Step 3.5: 写入模块文档**
  - Write: `overview.md`, `interface.md`, `dependencies.md`

- [ ] **Step 3.6: 完整性验证**
  - Check: 3 个文档都存在
  - Check: 有类列表 + 接口定义

---

#### Task 4: Service 模块分析

**目标**: 输出 `10-module-level/service/` (3 个文档)

**详细步骤**: (同 Task 3，替换模块名)

---

#### Task 5: Storage 模块分析

**目标**: 输出 `10-module-level/storage/` (3 个文档)

**详细步骤**: (同 Task 3，替换模块名)

---

### Phase 3: 文件粒度分析

#### Task 6: Bootstrap.java 文件分析

**目标**: 输出 `20-file-level/Bootstrap.java-analysis.md`

**输入文件**:
- `core/Bootstrap.java` (150 行)

**分析维度** (见 [FILE_LEVEL_ANALYSIS.md](FILE_LEVEL_ANALYSIS.md)):

| 维度 | 必需分析 |
|------|----------|
| 文件职责 | 一句话定位 + 职责分解 |
| 关键类/函数 | 类清单 + 核心方法详解 |
| 数据结构 | 核心数据结构 + 流向 |
| 依赖关系 | 上游/下游依赖图 |
| 设计模式 | 已应用模式 + 可改进 |
| 代码质量 | 复杂度 + 异味 + SOLID |
| 测试覆盖 | 单测情况 + 缺失测试 |
| 改进建议 | 立即/中期/长期改进 |

**详细步骤**:

- [ ] **Step 6.1: 提取文件基本信息**
  ```bash
  wc -l core/Bootstrap.java
  ```
  Extract: 行数、位置、模块

- [ ] **Step 6.2: 分析文件职责**
  - Read: 文件头部注释 + 类名
  - Extract: 职责定位 + 职责分解表

- [ ] **Step 6.3: 提取类/方法清单**
  ```bash
  rg "class|public|private" core/Bootstrap.java
  ```
  Extract: 类/方法列表 + 复杂度

- [ ] **Step 6.4: 分析核心方法**
  - Read: 主方法 (e.g., `main()`, `start()`)
  - Extract: 调用链 + 关键逻辑
  - Code snippet: 核心代码片段

- [ ] **Step 6.5: 分析依赖关系**
  ```bash
  rg "import" core/Bootstrap.java
  ```
  Extract: 上游调用者 + 下游依赖

- [ ] **Step 6.6: 识别设计模式**
  - Analyze: 类结构 + 方法命名
  - Extract: Factory/Builder/Strategy...

- [ ] **Step 6.7: 评估代码质量**
  ```bash
  lizard core/Bootstrap.java --CCN 15
  ```
  Extract: 复杂度 + 异味

- [ ] **Step 6.8: 检查测试覆盖**
  ```bash
  find . -name "Bootstrap*Test*"
  ```
  Extract: 测试文件 + 覆盖估算

- [ ] **Step 6.9: 生成改进建议**
  - From: 质量评估结果
  - Extract: 立即/中期/长期改进

- [ ] **Step 6.10: 写入文档**
  - Write: `20-file-level/Bootstrap.java-analysis.md`
  - Verify: 包含所有 10 个维度

- [ ] **Step 6.11: 完整性验证**
  - Check: 文件存在
  - Check: 无 placeholder
  - Check: 有代码示例

---

#### Task 7: IndicesService.java 文件分析

**目标**: 输出 `20-file-level/IndicesService.java-analysis.md`

**详细步骤**: (同 Task 6，替换文件名)

---

#### Task 8: MemoryManager.java 文件分析

**目标**: 输出 `20-file-level/MemoryManager.java-analysis.md`

**详细步骤**: (同 Task 6，替换文件名)

---

... (更多文件任务)

---

### Phase 4: 质量评估与总结

#### Task N-1: 项目质量评分

**目标**: 输出 `00-project-level/quality-score.md`

**输入**:
- 所有文件级分析的质量评分
- 静态分析结果

**输出要求**:

| 章节 | 必需内容 |
|------|----------|
| 总评分 | 0-100 分 + 等级 |
| 六维评估 | 6 个维度得分表 |
| 文件质量汇总 | Top/Bottom 文件列表 |
| 改进建议 | 优先级排序改进项 |

---

#### Task N: 学习价值总结

**目标**: 输出 `00-project-level/learning-value.md`

**输入**:
- 所有分析文档
- 设计模式汇总

**输出要求**:

| 章节 | 必需内容 |
|------|----------|
| 值得借鉴 | Top 10 设计点 |
| 适用场景 | 3-5 个应用场景 |
| 对比分析 | 与相似项目对比 |
| 推荐程度 | 1-5 星评级 |

---

## 四、任务管理集成

### 4.1 创建 Todo 项目

```bash
# 创建主项目
todo add "[Project] 深度源码分析" \
  --priority P0 \
  --description "三层深度分析：项目级 + 模块级 + 文件粒度" \
  --due YYYY-MM-DD

# 创建阶段分组
todo add "Phase 1: 项目级分析" --parent 1
todo add "Phase 2: 模块级分析" --parent 1
todo add "Phase 3: 文件粒度分析" --parent 1
todo add "Phase 4: 质量评估总结" --parent 1

# 创建具体任务
todo add "Task 1: 项目概览分析" --parent 2 --estimate 20
todo add "Task 2: 架构设计分析" --parent 2 --estimate 30
todo add "Task 3: Core 模块分析" --parent 3 --estimate 15
...
```

### 4.2 执行时状态更新

```bash
# 开始任务
todo update <task-id> --status in_progress

# 完成子步骤（可选）
# 在分析文档中标记步骤完成

# 完成任务
todo complete <task-id>

# 自动计算进度
# Phase 1: 50% → 项目: 12.5%
```

### 4.3 心跳进度检查

```bash
todo summary

# 输出示例：
# 📋 [Project] 深度源码分析 (进度: 45%)
# 🔴 P0: Phase 1 完成, Phase 2 进行中
# ⏳ 当前: Task 6 Bootstrap.java 分析
# ✅ 已完成: 5 个文件分析
```

---

## 五、验证标准

### 5.1 完整性验证（Phase 1）

**检查项**:

| 项目 | 验证方法 | 通过标准 |
|------|----------|----------|
| 文件存在 | `ls` 检查 | 所有输出文件存在 |
| 章节完整 | `grep` 检查标题 | 包含所有必需章节 |
| 内容具体 | 人工/脚本检查 | 无 placeholder |
| 数据一致 | 跨文档检查 | 数据一致 |

### 5.2 质量验证（Phase 2）

**检查项**:

| 项目 | 验证方法 | 通过标准 |
|------|----------|----------|
| 内容准确 | 关键类名正确 | 类名/方法名一致 |
| 分析深度 | 有代码示例 | 每个核心方法有示例 |
| 结构清晰 | 有架构图 | 有可视化图表 |
| 建议可行 | 有改进建议 | 每个问题有建议 |

---

## 六、异常处理

### 任务失败处理

| 失败类型 | 处理策略 |
|----------|----------|
| 文件不存在 | 标记 SKIP，记录原因 |
| 文件过大 | 分段分析，简化输出 |
| 复杂度过高 | 降级为概览分析 |
| 测试超时 | 记录部分结果 |

### 恢复机制

- **断点续传**: 记录已完成的任务
- **增量分析**: 只分析未完成部分
- **降级策略**: 复杂文件简化分析

---

## 七、研究计划生成自动化

### 自动生成脚本

```bash
python3 generate-research-plan.py \
  /path/to/project \
  --depth file-level \
  --max-files 30 \
  -o $OUTPUT_BASE/project-name/RESEARCH_PLAN.md
```

**生成内容**:
- 预研究结果（自动扫描）
- 模块识别
- 关键文件列表
- 详细任务步骤
- Todo 任务结构

---

## 八、示例研究计划

### 简化示例 (OceanBase)

```markdown
# OceanBase 详细研究计划

**目标**: 深度分析 OceanBase HTAP 架构 + 核心代码
**路径**: `$WORKSPACE/opensource/oceanbase`
**技术栈**: C++,分布式数据库
**预计**: 8 小时

## Phase 1: 项目级分析

### Task 1: 项目概览
- Read: README.md, CMakeLists.txt
- Output: 00-README.md

### Task 2: 架构设计
- Read: src/ 目录结构, observer/entry
- Output: 01-architecture.md

## Phase 2: 模块级分析

### Task 3: SQL引擎模块
- Read: src/sql/ 所有核心文件
- Output: 10-sql-engine/*.md

### Task 4: 存储引擎模块
- Read: src/storage/ 所有核心文件
- Output: 10-storage-engine/*.md

## Phase 3: 文件粒度分析

### Task 5: observer_main.cpp
- 分析: 启动流程、依赖关系
- Output: 20-observer_main.cpp-analysis.md

### Task 6: ObSchemaService.cpp
- 分析: Schema 管理、数据结构
- Output: 20-ObSchemaService.cpp-analysis.md

---
