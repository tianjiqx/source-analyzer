# 集成生态与协议分析模板

> 🔍 分析项目的外部集成能力：API 协议支持、第三方平台对接、SDK/CLI 集成、生态扩展性

## 📋 适用场景

- 提供 MCP/API/SDK 供其他系统集成的项目
- 对接多个第三方平台（消息/认证/存储/AI）的项目
- 有插件系统或扩展机制的项目
- 需要与多种 AI 提供商交互的项目

**典型案例**:
- OpenDeepWiki: MCP 协议 + 飞书/QQ/微信/Slack + 多 AI Provider + GitHub App
- DeepWiki: 8 种 LLM Provider + GitHub/GitLab/Bitbucket API
- Mem0: 25+ 向量数据库 + 18+ LLM Provider

## 📋 核心问题清单

### 1. 协议支持

#### 1.1 MCP (Model Context Protocol)
- [ ] 是否实现 MCP 服务器？
- [ ] 支持哪些 MCP Tool？
- [ ] MCP 认证方式？（OAuth 2.1 / API Key / 无认证）
- [ ] SSE KeepAlive 实现？
- [ ] 支持哪些 MCP 客户端？（Claude Desktop / Cursor / 自研）

#### 1.2 REST API
- [ ] API 规范？（OpenAPI / Swagger / 无文档）
- [ ] API 认证？（JWT / OAuth / API Key / Basic Auth）
- [ ] API 版本管理？
- [ ] 速率限制？

#### 1.3 WebSocket / SSE
- [ ] 实时通信协议？
- [ ] 连接管理？（心跳/重连/超时）
- [ ] 消息格式？（JSON / Protobuf / 二进制）

#### 1.4 gRPC / Thrift
- [ ] 是否使用 RPC 框架？
- [ ] Proto/IDL 定义？
- [ ] 流式支持？

### 2. 多平台集成

#### 2.1 消息平台
- [ ] 支持哪些消息平台？（飞书/钉钉/企微/Slack/Discord/Telegram）
- [ ] 统一抽象层设计？（IMessageProvider 策略模式）
- [ ] 消息格式适配？
- [ ] 回调/Webhook 处理？

#### 2.2 代码托管平台
- [ ] 支持哪些平台？（GitHub / GitLab / Bitbucket / Gitee）
- [ ] API 差异如何屏蔽？
- [ ] OAuth 集成？
- [ ] Webhook 接收？

#### 2.3 认证平台
- [ ] SSO/OAuth 提供商？（Google / GitHub / Microsoft / 自建）
- [ ] 多认证方式共存？
- [ ] 认证链/级联？

### 3. AI Provider 集成

#### 3.1 Provider 抽象
- [ ] 统一接口设计？（IChatClient / BaseLLM）
- [ ] Provider 注册方式？（代码注册/配置文件/动态加载）
- [ ] Provider 能力差异如何处理？
- [ ] 运行时切换 Provider？

#### 3.2 Provider 清单
- [ ] 支持哪些 Provider？
  - [ ] OpenAI (GPT-4/4o/o1)
  - [ ] Anthropic (Claude 3/3.5)
  - [ ] Google (Gemini)
  - [ ] 国内（通义/文心/GLM/DeepSeek/Kimi）
  - [ ] 本地（Ollama / vLLM / LM Studio）
  - [ ] 聚合（OpenRouter / LiteLLM）
  - [ ] 云厂商（Bedrock / Azure / Vertex）

#### 3.3 Provider 管理
- [ ] 配置管理？（JSON / YAML / 环境变量 / 数据库）
- [ ] 密钥安全存储？（加密/环境变量/Vault）
- [ ] 用量统计/计费？
- [ ] 故障切换（Fallback）？
- [ ] 负载均衡（多 Key 轮转）？

### 4. 存储后端集成

#### 4.1 数据库
- [ ] 支持哪些数据库？
- [ ] 切换机制？（配置/代码）
- [ ] 方言差异处理？

#### 4.2 向量数据库
- [ ] 支持哪些向量库？（FAISS / Milvus / Qdrant / Pinecone / Chroma）
- [ ] 统一检索接口？
- [ ] 性能差异处理？

#### 4.3 对象存储
- [ ] 支持哪些存储？（本地 / S3 / OSS / MinIO）
- [ ] 统一文件接口？

### 5. 插件/扩展系统

#### 5.1 插件架构
- [ ] 是否有插件系统？
- [ ] 插件接口定义？
- [ ] 插件发现/加载机制？
- [ ] 插件沙箱隔离？

#### 5.2 Skills/Tools 扩展
- [ ] 是否支持自定义 Tool/Skill？
- [ ] Tool 注册方式？（装饰器/配置/代码）
- [ ] Tool 描述格式？（JSON Schema / 自然语言）
- [ ] 动态 Tool 加载？

#### 5.3 主题/模板
- [ ] 是否支持自定义模板？
- [ ] 模板引擎？
- [ ] 主题切换？

### 6. CLI / SDK

#### 6.1 CLI 工具
- [ ] 是否提供 CLI？
- [ ] CLI 功能覆盖？
- [ ] 交互式/非交互式？

#### 6.2 SDK
- [ ] 提供哪些语言的 SDK？
- [ ] SDK 发布渠道？（npm / pip / Maven / NuGet）
- [ ] SDK 文档？

### 7. 生态集成质量

#### 7.1 集成深度
- [ ] 集成是表面级还是深度？
- [ ] 是否利用了平台特有能力？
- [ ] 集成是否经过生产验证？

#### 7.2 集成维护
- [ ] 集成代码是否有测试？
- [ ] API 变更如何感知？
- [ ] 集成文档是否完善？

## 🔍 代码检查点

```bash
# 查找 MCP 实现
rg "mcp|MCP|ModelContextProtocol|SseServer" --type py --type cs --type go

# 查找 Provider 抽象
rg "class.*Provider|class.*Client|IChatClient|BaseLLM" --type py --type cs --type go

# 查找多平台适配
rg "class.*Adapter|class.*Connector|class.*Integration|IMessageProvider" --type py --type cs

# 查找插件/Tool 系统
rg "class.*Plugin|class.*Tool|class.*Skill|@tool|register_tool" --type py --type cs --type go

# 查找认证集成
rg "OAuth|JWT|ApiKey|auth_provider|passport" --type py --type cs --type go

# 查找 SDK/CLI
find . -name "cli*" -o -name "*_cli*" -o -name "sdk*" | head -20
```

## 📊 评估标准

| 维度 | 优秀 (5分) | 良好 (4分) | 一般 (3分) | 需改进 (1-2分) |
|------|-----------|-----------|-----------|---------------|
| **协议支持** | MCP+REST+WS 完整 | 多协议 | REST only | 无标准协议 |
| **平台集成** | 5+ 平台，统一抽象 | 多平台 | 单平台 | 无集成 |
| **AI Provider** | 8+ Provider，可插拔 | 多 Provider | 单 Provider | 硬编码 |
| **扩展性** | 插件系统+动态加载 | 有扩展点 | 有限扩展 | 不可扩展 |
| **SDK/CLI** | 多语言 SDK+CLI | 有 SDK 或 CLI | 基础 CLI | 无 |

## 📝 分析输出模板

```markdown
# [项目名] - 集成生态分析

## 1. 协议支持

| 协议 | 实现 | 认证 | 说明 |
|------|------|------|------|
| MCP | ✅ 完整 | OAuth 2.1 + API Key | 支持 Claude/Cursor |
| REST API | ✅ OpenAPI | JWT + API Key | |
| WebSocket | ✅ | 同 REST | 流式响应 |

## 2. AI Provider 集成

**统一接口**: IChatClient / BaseLLM

**支持的 Provider**:
| Provider | 模型 | 流式 | 特殊处理 |
|----------|------|------|----------|
| OpenAI | GPT-4/4o | ✅ | |
| Anthropic | Claude 3 | ✅ | |
| Google | Gemini | ✅ | |
| Ollama | 本地模型 | ✅ | /no_think 后缀 |
| ... | | | |

**配置方式**: JSON + 环境变量

**故障切换**: ✅ 自动 Fallback

## 3. 平台集成

| 平台 | 集成方式 | 深度 |
|------|----------|------|
| GitHub | OAuth + Webhook + App | 深度 |
| 飞书 | Bot + 消息卡片 | 中度 |
| Slack | Bot + Block Kit | 中度 |

## 4. 扩展系统

**Tool/Skill 扩展**: ✅ 支持自定义

**注册方式**: 装饰器 + 配置文件

**动态加载**: ✅ 运行时注册

## 5. 设计亮点

- ✅ [亮点1]

## 6. 学习价值

- ⭐⭐⭐⭐⭐ [值得借鉴的设计]
```

## 7. 💡 设计洞察

> 从该项目的集成生态设计中提炼的可移植原则

### 7.1 集成设计原则

**原则1**: [原则名称]
- **原理**: [为什么重要]
- **证据**: [项目中的具体实现]
- **适用范围**: [什么场景适用]
- **去名检验**: ✅/⚠️

示例:
> **原则**: 外部服务集成应该使用适配器模式，而非直接耦合
>
> **原理**: 外部服务 API 可能变化，直接耦合会导致修改业务代码；适配器模式可以隔离变化
>
> **证据**: 项目为每个外部服务（GitHub、Slack、飞书）实现了独立的适配器接口
>
> **适用范围**: 需要集成多个外部服务的系统
>
> **去名检验**: ✅ 通用原则

### 7.2 扩展性原则

**原则1**: [同上格式]

## 8. ⚠️ 隐含陷阱

> 从源码分析中发现的非显而易见的集成生态陷阱

### 8.1 API 版本陷阱

**陷阱1**: [陷阱名称]
- **现象**: [说明]
- **原因**: [说明]
- **正确做法**: [说明]

### 8.2 认证授权陷阱

**陷阱1**: [同上格式]

---

*模板版本: v2.0 - 增加设计洞察与隐含陷阱章节*
*最后更新: 2026-06-29*
