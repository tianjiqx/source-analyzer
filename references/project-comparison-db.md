# 项目对比数据库

> 记录已分析项目的关键特性，支持跨项目对比

---

## 已分析项目清单

| 项目 | 类型 | 语言 | 评分 | 核心特性 | 分析日期 |
|------|------|------|------|----------|----------|
| PixelRAG | Visual RAG | Python+TS | 85/A | 截图检索, 多GPU并行 | 2026-06-27 |
| DeepWiki | Wiki 生成 | Python+TS | 73/B | RAG, 多LLM | 2026-06-26 |
| OpenDeepWiki | Wiki+知识管理 | C#+TS | 85/A- | Agent, MCP | 2026-06-26 |
| DSA | 股票分析 | Python | 89/A | 多Agent, 策略系统 | 2026-06-27 |
| DataAgent | 数据分析 | Java | 85/A | StateGraph, Text-to-SQL | 2026-06-09 |
| Mem0 | AI 记忆层 | Python | 92/A | 多层记忆, 向量存储 | 2026-06-08 |

---

## 对比维度矩阵

### LLM Agent 类

| 特性 | DSA | DataAgent | Mem0 |
|------|-----|-----------|------|
| Agent 架构 | 顺序链(4阶段) | StateGraph(14节点) | ❌ |
| 记忆系统 | SQLite+置信度 | RAG双通道 | 多层向量(25+) |
| 工具系统 | 13+ @tool | 14节点+Python | 25+存储 |
| 人机协作 | 5种模式 | interruptBefore | ❌ |
| 策略系统 | ✅ 15种YAML | ❌ | ❌ |
| 回测系统 | ✅ Long-only | ❌ | ❌ |

### RAG 类

| 特性 | PixelRAG | DeepWiki | OpenDeepWiki |
|------|----------|----------|--------------|
| 检索方式 | 视觉嵌入 | 文本嵌入 | Agent+MCP |
| 向量库 | FAISS IVFFlat | FAISS | ❌ |
| 多模态 | ✅ 视觉 | ❌ 文本 | ❌ 文本 |
| 预建索引 | 8.28M页面 | ❌ | ❌ |
| 多GPU | ✅ 持久Worker池 | ❌ | ❌ |
| MCP支持 | ❌ | ❌ | ✅ 完整OAuth |

### Wiki 生成类

| 特性 | DeepWiki | OpenDeepWiki |
|------|----------|--------------|
| 语言 | Python+TS | C#+TS |
| AI框架 | AdalFlow | Microsoft.Agents.AI |
| Agent Tools | 多个 | 9个 |
| MCP支持 | ❌ | ✅ OAuth 2.1 |
| 多平台Chat | ❌ | ✅ 飞书/QQ/微信 |
| 增量更新 | ❌ | ✅ Worker定时 |

---

## 更新指南

### 新增项目时

1. 在"已分析项目清单"表格添加一行
2. 根据项目类型，在对应"对比维度矩阵"添加列
3. 如果是新类型，创建新的对比表格

### 对比维度选择

- **架构类**: Agent架构、记忆系统、工具系统、人机协作
- **性能类**: 延迟、吞吐、资源占用、并发模型
- **功能类**: 核心特性、扩展性、集成能力
- **质量类**: 代码质量、测试覆盖、文档完善度

---

*最后更新: 2026-06-30*
