# 执行闭环指南

> 确保分析结果持久化、可追溯、可复用

---

## 1. 分析结果回写 MEMORY.md

### 回写时机

分析完成后，**必须**将关键信息回写到 `$WORKSPACE/MEMORY.md`：

1. **分析完成时**：记录项目基本信息和分析状态
2. **发现重要模式时**：记录可移植的设计原则
3. **遇到典型问题时**：记录陷阱和解决方案

### 回写格式

```markdown
### [项目名称] - [项目定位] (分析日期)
**位置**: `$OUTPUT_BASE/[project-name]/`
**GitHub**: https://github.com/[owner]/[repo]
**源码**: `/home/tianjiqx/opensource/[project-name]` (已下载/未下载)

**关键数据**:
- Stars: [数字]
- 主语言: [语言]
- 代码规模: [文件数/行数]
- 综合评分: **[分数]/100 (等级 [A/B/C/D])**

**核心架构**:
1. **[模块1]**: [一句话描述]
2. **[模块2]**: [一句话描述]
3. ...

**关键发现**:
- ⭐⭐⭐⭐⭐ **[发现1]**: [一句话说明]
- ⭐⭐⭐⭐ **[发现2]**: [一句话说明]
- ...

**分析文档** ([N] 个, [大小]KB):
- INDEX.md (总索引)
- [文档列表]

**学习价值**: ⭐⭐⭐⭐⭐ ([评分]/5)
- ⭐⭐⭐⭐⭐ [可移植模式1]
- ⭐⭐⭐⭐ [可移植模式2]
- ...

**与已分析项目对比**:
| 特性 | [当前项目] | [对比项目1] | [对比项目2] |
|------|-----------|------------|------------|
| [维度1] | ... | ... | ... |
| [维度2] | ... | ... | ... |

**状态**: ✅ 分析完成 / 🚧 进行中 / ❌ 失败
```

### 回写示例

```markdown
### PixelRAG 视觉检索增强生成系统 (2026-06-27)
**位置**: `$OUTPUT_BASE/pixelrag/`
**GitHub**: https://github.com/StarTrail-org/PixelRAG
**源码**: `/home/tianjiqx/opensource/pixelrag` (已下载)

**关键数据**:
- Stars: 新兴项目
- 主语言: Python 3.12+ (后端) + TypeScript (前端)
- 代码规模: 134 Python 文件 (~51K 行) + 4K 行 TypeScript
- 综合评分: **85/100 (等级 A)**

**核心架构**:
1. **render/**: Chrome CDP 截图渲染（Standard + Turbo 两种模式）
2. **embed/**: 多后端嵌入（vLLM/SGLang/direct_gpu）+ PersistentGpuWorkerPool
3. **index/**: FAISS IVFFlat 索引构建
4. **serve/**: FastAPI 搜索 API
5. **train/**: LoRA 微调 Qwen3-VL-Embedding

**关键发现**:
- ⭐⭐⭐⭐⭐ **Visual RAG 范式**: 截图替代文本，保留表格/图表/布局信息
- ⭐⭐⭐⭐⭐ **多 GPU 并行**: PersistentGpuWorkerPool 动态负载均衡
- ⭐⭐⭐⭐⭐ **智能分块**: 8192px tiles → 1024px chunks（8x token 压缩）

**分析文档** (7 个, ~134KB):
- INDEX.md (总索引)
- 00-README.md (12KB)
- 01-architecture.md (22KB)
- ...

**学习价值**: ⭐⭐⭐⭐⭐ (5/5)
- ⭐⭐⭐⭐⭐ Visual RAG 范式创新
- ⭐⭐⭐⭐⭐ 多 GPU 并行架构

**状态**: ✅ Layer 1-3 分析完成
```

---

## 2. 跨项目对比的结构化方法

### 对比数据库

维护 `$SKILL_DIR/references/project-comparison-db.md`：

```markdown
# 项目对比数据库

## 已分析项目清单

| 项目 | 类型 | 语言 | 评分 | 核心特性 | 分析日期 |
|------|------|------|------|----------|----------|
| PixelRAG | Visual RAG | Python+TS | 85/A | 截图检索, 多GPU并行 | 2026-06-27 |
| DeepWiki | Wiki 生成 | Python+TS | 73/B | RAG, 多LLM | 2026-06-26 |
| OpenDeepWiki | Wiki+知识管理 | C#+TS | 85/A- | Agent, MCP | 2026-06-26 |
| DSA | 股票分析 | Python | 89/A | 多Agent, 策略系统 | 2026-06-27 |
| DataAgent | 数据分析 | Java | 85/A | StateGraph, Text-to-SQL | 2026-06-09 |
| Mem0 | AI 记忆层 | Python | 92/A | 多层记忆, 向量存储 | 2026-06-08 |

## 对比维度矩阵

### 按项目类型

#### LLM Agent 类
| 特性 | DSA | DataAgent | Mem0 |
|------|-----|-----------|------|
| Agent 架构 | 顺序链 | StateGraph | ❌ |
| 记忆系统 | SQLite | RAG | 多层向量 |
| 工具系统 | 13+ 工具 | 14 节点 | 25+ 存储 |
| 人机协作 | 5 模式 | 中断恢复 | ❌ |

#### RAG 类
| 特性 | PixelRAG | DeepWiki | OpenDeepWiki |
|------|----------|----------|--------------|
| 检索方式 | 视觉嵌入 | 文本嵌入 | Agent+MCP |
| 向量库 | FAISS | FAISS | ❌ |
| 多模态 | ✅ | ❌ | ❌ |
| 预建索引 | 8.28M | ❌ | ❌ |
```

### 对比流程

1. **分析前**：查询对比数据库，确定对比对象
2. **分析中**：记录关键特性，准备对比数据
3. **分析后**：
   - 更新对比数据库
   - 在 MEMORY.md 中记录对比表
   - 在分析文档中生成详细对比章节

### 对比模板

```markdown
## 与已分析项目对比

| 特性 | [当前项目] | [对比项目1] | [对比项目2] |
|------|-----------|------------|------------|
| **定位** | ... | ... | ... |
| **语言** | ... | ... | ... |
| **核心创新** | ... | ... | ... |
| **[维度1]** | ✅/❌ | ✅/❌ | ✅/❌ |
| **[维度2]** | ... | ... | ... |
| **代码规模** | ... | ... | ... |
```

---

## 3. 增量更新机制

### 版本追踪

在分析目录中维护 `VERSION.md`：

```markdown
# 分析版本记录

## 当前版本
- **版本**: v1.0
- **分析日期**: 2026-06-27
- **基于提交**: [commit-hash] (2026-06-25)
- **分析深度**: Layer 1-3

## 历史版本
| 版本 | 日期 | 提交 | 变更说明 |
|------|------|------|----------|
| v1.0 | 2026-06-27 | abc1234 | 初始分析 |
```

### 增量更新触发条件

1. **项目更新**：GitHub 有新提交（检查 `git log`）
2. **分析不完整**：验证发现缺失文档
3. **用户要求**：明确要求更新分析

### 增量更新流程

```bash
# 1. 检查项目更新
cd /home/tianjiqx/opensource/[project-name]
git fetch
git log HEAD..origin/main --oneline

# 2. 如果有更新，记录新提交
git pull
NEW_COMMIT=$(git rev-parse HEAD)

# 3. 对比分析版本
cat $OUTPUT_BASE/[project]/VERSION.md

# 4. 决定更新范围
# - 小更新（文档修复）：跳过
# - 中更新（bug 修复）：更新受影响文档
# - 大更新（新功能）：重新执行 Layer 2-3

# 5. 执行增量分析
# 只分析变更文件及其依赖

# 6. 更新版本记录
echo "- v1.1 | $(date +%Y-%m-%d) | $NEW_COMMIT | 增量更新" >> VERSION.md
```

### 增量分析策略

| 变更类型 | 影响范围 | 更新策略 |
|----------|----------|----------|
| 文档更新 | 无 | 跳过 |
| Bug 修复 | 单文件 | 更新对应文件分析 |
| 新功能 | 多文件 | 更新模块级 + 新增文件 |
| 架构重构 | 全局 | 重新执行完整分析 |

---

## 4. 失败恢复与断点续传

### 检查点机制

分析过程中自动保存检查点：

```json
// $OUTPUT_BASE/[project]/.checkpoint.json
{
  "version": "1.0",
  "last_update": "2026-06-27T14:00:00",
  "completed_tasks": [
    "00-README.md",
    "01-architecture.md"
  ],
  "in_progress": "02-core-code.md",
  "pending_tasks": [
    "03-quality-score.md",
    "04-learning-value.md"
  ],
  "failed_tasks": [],
  "context": {
    "project_type": "llm-agent",
    "total_files": 134,
    "analyzed_files": 45
  }
}
```

### 恢复流程

```bash
# 1. 检查是否存在检查点
if [ -f .checkpoint.json ]; then
  echo "发现检查点，恢复分析..."
  python3 scripts/orchestrator.py RESEARCH_PLAN.md --resume
else
  echo "无检查点，开始新分析"
  python3 scripts/orchestrator.py RESEARCH_PLAN.md
fi
```

### 失败处理策略

| 错误类型 | 处理方式 |
|----------|----------|
| 超时 | 自动重试 3 次，指数退避 |
| 上下文不足 | 简化分析，标记为"部分分析" |
| 文件不存在 | 跳过，记录到失败列表 |
| 子代理崩溃 | 重新派发任务 |

### 验证恢复

```bash
# 验证分析完整性
python3 scripts/verify-analysis.py [analysis-dir] --all

# 如果有缺失，补充分析
python3 scripts/orchestrator.py RESEARCH_PLAN.md --only-missing
```

---

## 5. 执行闭环检查清单

分析完成后，逐项确认：

- [ ] **MEMORY.md 已更新**：项目信息、关键发现、学习价值
- [ ] **对比数据库已更新**：新特性已录入对比表
- [ ] **版本记录已创建**：VERSION.md 记录分析版本
- [ ] **验证通过**：`verify-analysis.py` 无严重问题
- [ ] **INDEX.md 一致**：无幽灵引用、无孤儿文件
- [ ] **检查点已清理**：删除 `.checkpoint.json`（如果存在）

---

*最后更新: 2026-06-30*
