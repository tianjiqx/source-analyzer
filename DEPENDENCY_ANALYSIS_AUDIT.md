# Source Analyzer Skill - 依赖分析文件生成审计报告

**审计时间**: 2026-07-10  
**审计范围**: source-analyzer skill 中所有涉及 dependencies.md 生成的脚本和模板  
**触发原因**: autoresearch 项目分析时发现 dependencies.md 文件未生成

---

## 问题清单

### 🔴 严重问题（必须修复）

#### 1. SKILL.md - 递归深度分析输出结构缺少 dependencies.md
**位置**: `SKILL.md` 第 245-270 行  
**问题**: 递归深度分析模式的输出结构定义中，项目级和模块级都缺少 `dependencies.md`  
**影响**: Agent 执行时不会生成依赖分析文件

**当前结构**:
```
00-project-level/                 # 项目级 (4 文档)
├── README.md
├── architecture.md
├── quality-score.md              # ❌ 缺少 dependencies.md
└── learning-value.md
```

**应改为**:
```
00-project-level/                 # 项目级 (5 文档)
├── README.md
├── architecture.md
├── dependencies.md               # ✅ 必须添加
├── quality-score.md
└── learning-value.md
```

---

#### 2. recursive-orchestrator.py - PROJECT_TASKS 缺少 dependencies 任务
**位置**: `scripts/recursive-orchestrator.py` 第 50-90 行  
**问题**: `PROJECT_TASKS` 列表中没有 `project-dependencies` 任务定义  
**影响**: 自动生成的 PLAN.md 不包含依赖分析任务

**当前任务列表**:
- project-readme ✅
- project-architecture ✅
- project-quality ✅
- project-learning ✅
- **project-dependencies ❌ 缺失**

**应添加**:
```python
{
    "task_id": "project-dependencies",
    "title": "项目依赖分析",
    "layer": "project",
    "description": "分析项目第三方依赖、版本选择、依赖评估",
    "output_file": "00-project-level/dependencies.md",
    "priority": "high",
    "estimated_time": 15,
    "subagent_label": "project-dependencies"
}
```

---

#### 3. recursive-orchestrator.py - MODULE_TASKS_TEMPLATE 缺少 dependencies
**位置**: `scripts/recursive-orchestrator.py` 第 95-110 行  
**问题**: 模块级任务模板中没有 dependencies 任务  
**影响**: 每个模块的分析不会包含依赖分析

**当前模板**:
```python
MODULE_TASKS_TEMPLATE = """
### 模块: {module_name}

| Task ID | 标题 | 输出文件 | 优先级 | 预计时间 |
|---------|------|---------|--------|----------|
| {module_id}-overview | {module_name} 概览 | {module_path}/00-overview.md | high | 15min |
| {module_id}-architecture | {module_name} 架构 | {module_path}/01-architecture.md | high | 20min |
| {module_id}-quality | {module_name} 质量评分 | {module_path}/02-quality-score.md | medium | 15min |
| {module_id}-learning | {module_name} 学习价值 | {module_path}/03-learning-value.md | medium | 15min |
"""
```

**应改为**:
```python
MODULE_TASKS_TEMPLATE = """
### 模块: {module_name}

| Task ID | 标题 | 输出文件 | 优先级 | 预计时间 |
|---------|------|---------|--------|----------|
| {module_id}-overview | {module_name} 概览 | {module_path}/00-overview.md | high | 15min |
| {module_id}-architecture | {module_name} 架构 | {module_path}/01-architecture.md | high | 20min |
| {module_id}-dependencies | {module_name} 依赖 | {module_path}/02-dependencies.md | high | 15min |
| {module_id}-quality | {module_name} 质量评分 | {module_path}/03-quality-score.md | medium | 15min |
| {module_id}-learning | {module_name} 学习价值 | {module_path}/04-learning-value.md | medium | 15min |
"""
```

---

#### 4. verify-analysis.py - RECURSIVE_REQUIRED 缺少 dependencies.md
**位置**: `scripts/verify-analysis.py` 第 450-460 行  
**问题**: 递归模式验证时不检查 dependencies.md 是否存在  
**影响**: 即使缺少依赖分析文件，验证也会通过

**当前定义**:
```python
RECURSIVE_REQUIRED = {
    "project": ["README.md", "architecture.md", "quality-score.md", "learning-value.md"],
    "module": ["INDEX.md", "00-overview/", "10-submodule/", "20-file-level/"]
}
```

**应改为**:
```python
RECURSIVE_REQUIRED = {
    "project": ["README.md", "architecture.md", "dependencies.md", "quality-score.md", "learning-value.md"],
    "module": ["INDEX.md", "00-overview/", "02-dependencies.md", "10-submodule/", "20-file-level/"]
}
```

---

### 🟡 中等问题（建议修复）

#### 5. smart-analyze.py - 文档数量统计不一致
**位置**: `scripts/smart-analyze.py` 第 180-190 行  
**问题**: 文档数量统计没有包含 dependencies.md  
**影响**: 生成的分析报告中文档数量不准确

**当前统计**:
```python
doc_counts = {
    "project_level": 4,  # README + architecture + quality + learning
    "module_level": 3,   # overview + architecture + quality
    "file_level": 1,     # 每文件 1 文档
}
```

**应改为**:
```python
doc_counts = {
    "project_level": 5,  # README + architecture + dependencies + quality + learning
    "module_level": 4,   # overview + architecture + dependencies + quality
    "file_level": 1,     # 每文件 1 文档
}
```

---

#### 6. generate-research-plan.py - 任务模板缺少 dependencies
**位置**: `scripts/generate-research-plan.py` 第 120-140 行  
**问题**: 生成的研究计划模板中没有 dependencies 任务  
**影响**: 手动执行时可能遗漏依赖分析

**修复方案**: 在 `generate_project_tasks()` 和 `generate_module_tasks()` 函数中添加 dependencies 任务

---

### 🟢 轻微问题（可选修复）

#### 7. SKILL.md - 文档数量描述不一致
**位置**: `SKILL.md` 多处  
**问题**: 不同位置的文档数量描述不一致  
**影响**: 用户可能对输出规模产生误解

**需要统一的位置**:
- 第 180 行: "Layer 1: 项目级分析 (必做) → 4 文档" → 应改为 5 文档
- 第 220 行: "Layer 2: 模块级分析 (必做) → 每模块 3 文档" → 应改为 4 文档
- 第 280 行: "预计输出文档数量: 40-80+ 个" → 应更新为包含 dependencies 后的数量

---

## 修复优先级

| 优先级 | 问题编号 | 修复难度 | 预计时间 |
|--------|---------|---------|---------|
| 🔴 P0 | #1, #2, #3, #4 | 中等 | 30 分钟 |
| 🟡 P1 | #5, #6 | 简单 | 15 分钟 |
| 🟢 P2 | #7 | 简单 | 10 分钟 |

---

## 修复步骤

### 步骤 1: 修复 SKILL.md（问题 #1, #7）

1. 更新递归深度分析输出结构，添加 `dependencies.md`
2. 统一所有文档数量描述

### 步骤 2: 修复 recursive-orchestrator.py（问题 #2, #3）

1. 在 `PROJECT_TASKS` 中添加 `project-dependencies` 任务
2. 在 `MODULE_TASKS_TEMPLATE` 中添加 dependencies 任务

### 步骤 3: 修复 verify-analysis.py（问题 #4）

1. 在 `RECURSIVE_REQUIRED` 中添加 `dependencies.md` 检查

### 步骤 4: 修复 smart-analyze.py（问题 #5）

1. 更新 `doc_counts` 字典，包含 dependencies.md

### 步骤 5: 修复 generate-research-plan.py（问题 #6）

1. 在任务生成函数中添加 dependencies 任务

---

## 验证方法

修复完成后，使用以下命令验证：

```bash
# 1. 检查 SKILL.md 中的结构定义
grep -A 10 "00-project-level/" ~/.openclaw/workspace/skills/source-analyzer/SKILL.md

# 2. 检查 recursive-orchestrator.py 中的任务定义
grep -A 5 "project-dependencies" ~/.openclaw/workspace/skills/source-analyzer/scripts/recursive-orchestrator.py

# 3. 检查 verify-analysis.py 中的验证规则
grep -A 3 "RECURSIVE_REQUIRED" ~/.openclaw/workspace/skills/source-analyzer/scripts/verify-analysis.py

# 4. 运行测试分析（小项目）
python3 ~/.openclaw/workspace/skills/source-analyzer/scripts/smart-analyze.py \
  /path/to/test-project \
  --model "test" \
  -o /tmp/test-analysis

# 5. 验证输出是否包含 dependencies.md
ls -la /tmp/test-analysis/00-project-level/dependencies.md
```

---

## 影响范围

### 受影响的分析模式

1. **递归深度分析模式** - 主要影响
2. **最大分析模式** - 次要影响
3. **标准三层分析** - 无影响（已有 dependencies.md）

### 受影响的脚本

1. `recursive-orchestrator.py` - 必须修复
2. `verify-analysis.py` - 必须修复
3. `smart-analyze.py` - 建议修复
4. `generate-research-plan.py` - 建议修复

### 受影响的模板

1. `templates/general/PROJECT_DEPENDENCY_ANALYSIS.md` - 无需修改（模板本身完整）
2. 模块级依赖分析模板 - 需要创建（当前缺失）

---

## 后续改进建议

### 1. 创建模块级依赖分析模板

当前只有项目级依赖分析模板 `PROJECT_DEPENDENCY_ANALYSIS.md`，缺少模块级模板。

**建议创建**: `templates/general/MODULE_DEPENDENCY_ANALYSIS.md`

**模板内容**:
- 模块内部依赖关系
- 模块对外部库的依赖
- 模块间依赖关系
- 依赖版本和兼容性
- 依赖风险评估

### 2. 添加依赖分析自动化

当前依赖分析完全依赖 LLM 手动生成，可以考虑：

- 自动解析 `pyproject.toml` / `package.json` / `pom.xml`
- 自动生成依赖树
- 自动检测版本冲突
- 自动评估依赖健康度

### 3. 添加依赖可视化

- 生成依赖关系图（Mermaid）
- 生成依赖版本对比表
- 生成依赖风险评估报告

---

## 总结

**核心问题**: source-analyzer skill 在递归深度分析模式下，缺少 dependencies.md 文件的生成逻辑。

**根本原因**: 
1. SKILL.md 的输出结构定义不完整
2. recursive-orchestrator.py 的任务模板缺少 dependencies 任务
3. verify-analysis.py 的验证规则不严格

**修复方案**: 按照上述步骤逐一修复，预计总耗时 1 小时。

**验证标准**: 
- 所有分析模式都能正确生成 dependencies.md
- verify-analysis.py 能正确检测缺失的 dependencies.md
- 文档数量统计准确一致

---

**审计人**: AI Assistant  
**审计日期**: 2026-07-10  
**下次审计**: 修复完成后进行回归测试
