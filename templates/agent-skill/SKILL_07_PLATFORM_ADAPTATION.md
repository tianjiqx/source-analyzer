# SKILL 07 - 平台适配分析

> **核心问题**: Skill 支持哪些平台？如何适配多平台？供应商锁定程度？迁移成本？

## 1. 目标平台分析

### 1.1 平台兼容性矩阵

| 平台 | Skill 格式 | 执行模型 | 扩展机制 | 市场份额 |
|------|-----------|----------|----------|----------|
| **Claude Code** | `.claude/` + SKILL.md | Anthropic API + 工具 | Plugin / MCP | 高 |
| **Cursor** | `.cursor/rules/` | 内嵌 + API | 规则文件 | 中高 |
| **GitHub Copilot** | `.github/copilot-instructions.md` | 内嵌 + Chat | 命令 | 高 |
| **OpenClaw** | `.openclaw/skills/` + SKILL.md | 多模型 + 多通道 | Plugin / Cron / MCP | 中 |
| **Cline / Windsurf** | `.clinerules/` / `rules/` | 内嵌 + API | 规则 | 中 |
| **通用 / 无平台** | SKILL.md + metadata.json | LLM 无关 | 自定义 | 通用 |

### 1.2 平台依赖检测

```
检查 Skill 对平台的依赖程度:

L0 完全无关: 纯 Markdown 指令，任何 LLM 可执行
L1 格式依赖: 使用特定目录格式 (.claude/, .cursor/)
L2 工具依赖: 依赖平台特定工具 (Claude Code commands / OpenClaw cron)
L3 API 依赖: 依赖特定 LLM API (Anthropic / OpenAI)
L4 深度耦合: 依赖平台内部机制 (MCP / Plugin SDK)
```

## 2. 适配层设计

### 2.1 多平台策略

| 策略 | 描述 | 示例 |
|------|------|------|
| **单一平台** | 只支持一个平台 | `agent-skills` → Claude Code |
| **格式适配** | 相同逻辑，不同目录/格式 | agentic-harness-patterns → 多平台 |
| **抽象层** | 隐藏平台差异的中间层 | Skill_Seekers |
| **平台无关** | 不依赖任何平台特定功能 | 纯 Markdown Skill |

### 2.2 跨平台迁移成本评估

```
迁移成本因素:
- 目录结构重组: 低（复制+改名）
- 指令重写: 中（执行模型差异）
- 工具适配: 高（平台特定工具替换）
- 扩展机制替换: 高（MCP → 插件）
- 测试重建: 中（场景可能不同）
```

## 3. 核心分析问题清单

- [ ] Skill 支持哪些平台？是否有显式声明？
- [ ] 是否有平台特定的代码/配置？多少？
- [ ] 迁移到其他平台的成本如何？
- [ ] 是否使用了平台专有功能？（MCP / Plugin / Cron）
- [ ] 是否有平台检测/适配逻辑？
- [ ] 是否有供应商锁定风险？如何缓解？
- [ ] Skill 的可移植性评分？

## 4. Golden Rules 提炼

- **平台无关优先**: Skill 核心逻辑应该是纯指令，与平台无关
- **适配层隔离**: 平台差异集中在入口/配置，不侵入核心逻辑
- **渐进式适配**: 先支持一个平台，再逐步扩展
- **工具抽象**: 平台特定工具应封装为统一接口
- **格式标准化**: frontmatter 元数据应跨平台一致

## 5. Gotchas

- **隐性平台假设**: Skill 假设 Agent 有某些工具但未声明（只在特定平台可用）
- **格式碎片化**: 不同平台的 frontmatter 格式不同（YAML vs JSON）
- **工具语义差异**: 同名工具在不同平台行为不同（如 `exec`）
- **上下文窗口差异**: 不同平台窗口大小不同，Skill 在小窗口平台溢出
- **权限模型差异**: 平台 A 允许的操作在平台 B 被禁止
