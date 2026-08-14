# 项目对比数据库

> 记录已分析项目的关键特性，支持跨项目对比

---

## 已分析项目清单

| 项目 | 类型 | 语言 | 评分 | 核心特性 | 分析日期 |
|------|------|------|------|----------|----------|
| CnosDB | 分布式时序数据库 | Rust | 76/B+ | TSM列式存储, MultiRaft多复制组, DataFusion深度fork, SPI抽象层, 存算分离, 多协议接入 | 2026-08-11 |
| OpenMLDB | 机器学习数据库 | C++/Java | 80/B+ | HybridSE SQL编译引擎, LLVM codegen, 双层SkipList, 在线离线双轨, Spark生态 | 2026-08-11 |
| TDengine | 时序数据库 | C+Go | 79/B+ | 多组件dnode架构, TFS分层存储, WAL接口设计, 条件编译双版本, 多协议接入, TDgpt AI | 2026-08-11 |
| Apache DataFusion | 查询引擎/SQL | Rust | 85-90/A- | 逻辑物理计划分离, 插件化优化器, Arrow生态集成, 宏驱动函数, Spark UDF兼容, 多数据源 | 2026-08-11 |
| DataFusion Ballista | 分布式SQL引擎 | Rust | 85/A- | 三调度策略, 双模式Shuffle, string_id宏, KLL Sketch, 协议版本控制 | 2026-08-11 |
| Apache Druid | 实时OLAP数据库 | Java+TS | 85/A- | 列式Segment+位图索引, Calcite SQL, MSQ多阶段DAG, 双轨执行, 31扩展, Web控制台 | 2026-08-11 |
| TimescaleDB | 时序数据库/PG扩展 | C | 86/A- | Hypertable分块, 压缩引擎(Gorilla/DeltaDelta/FastLanes), 列式扫描, 连续聚合, 双许可架构, PG全扩展点 | 2026-08-10 |
| CockroachDB | 分布式SQL数据库 | Go | 88/A | 分布式事务, Raft定制(Fortification), Pebble, Cascades优化器, 向量化执行, 多租户RU计量 | 2026-08-10 |
| RabbitMQ | 消息代理/MQ | Erlang | 88/A | 三类队列(经典/Quorum/Stream), 多协议, 每连接一进程, Khepri元数据 | 2026-08-05 |
| RocksDB | 数据库/LSM KV | C++ | 87/A | LSM-Tree, 可插拔策略, 无锁SkipList | 2026-08-04 |
| ClickHouse | 列式OLAP数据库 | C++ | 88/A | 向量化执行, 自研JIT, 编译期多态, 双引擎 | 2026-08-05 |
| Apache Spark | 大数据引擎 | Scala+Java | 87/A | DAG调度, Catalyst优化器, 统一内存, Codegen, AQE | 2026-08-04 |
| PixelRAG | Visual RAG | Python+TS | 85/A | 截图检索, 多GPU并行 | 2026-06-27 |
| DeepWiki | Wiki 生成 | Python+TS | 73/B | RAG, 多LLM | 2026-06-26 |
| OpenDeepWiki | Wiki+知识管理 | C#+TS | 85/A- | Agent, MCP | 2026-06-26 |
| DSA | 股票分析 | Python | 89/A | 多Agent, 策略系统 | 2026-06-27 |
| DataAgent | 数据分析 | Java | 85/A | StateGraph, Text-to-SQL | 2026-06-09 |
| Mem0 | AI 记忆层 | Python | 92/A | 多层记忆, 向量存储 | 2026-06-08 |
| TimeCopilot | GenAI预测Agent | Python | 82/B | LLM×TSFM, 37模型统一契约, pydantic-ai, GIFT-Eval#1, Fugue分布式, ModelRetry门禁 | 2026-08-13 |

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

### 数据库类

| 特性 | RocksDB | LevelDB |
|------|---------|--------|
| 架构 | LSM-Tree 四层分离 | LSM-Tree 简易版 |
| 核心代码量 | 686K 行 | 8K 行 |
| 并发写 | 组提交+无锁读 | 单写者 |
| 事务 | 三策略 | 无 |
| 可插拔策略 | 全引擎策略化 | 低 |
| 压缩策略 | 3种+动态 | 单一 |
| 大value | BlobDB 分离 | 无 |
| 观测性 | thread_local 零锁 | 弱 |
| 测试体系 | 单测+db_stress+fuzz 三极 | 基础单测 |

### 消息队列类

| 特性 | RabbitMQ |
|------|---------|
| 语言 | Erlang/OTP |
| 核心代码量 | 395K 行 (1258 .erl) |
| 并发模型 | 每连接/通道/队列一进程 |
| 队列类型 | 经典(磁盘) / Quorum(Raft) / Stream(日志) |
| 协议支持 | AMQP 0-9-1/1.0, MQTT, STOMP, Stream |
| 消息确认 | Publisher Confirm + Consumer Ack |
| 高可用 | 镜像队列 + Quorum 队列 (Raft) |
| 元数据存储 | Khepri (树形, 取代 Mnesia) |
| 流控 | Credit-based + 内存/磁盘水位 |
| 集群 | 对等发现 (AWS/Consul/etcd/K8s/DNS) |
| 插件体系 | 60+ 插件 (管理/监控/协议/联邦) |

### 对比维度选择

- **架构类**: Agent架构、记忆系统、工具系统、人机协作
- **性能类**: 延迟、吞吐、资源占用、并发模型
- **功能类**: 核心特性、扩展性、集成能力
- **质量类**: 代码质量、测试覆盖、文档完善度

---

*最后更新: 2026-06-30*

### 插件框架类

| 特性 | Cordis | NestJS | InversifyJS |
|------|--------|--------|-------------|
| 语言 | TypeScript | TypeScript | TypeScript |
| 核心代码量 | ~4.1K 行 (9 packages) | 大型 | 中型 |
| 注入方式 | Proxy 属性拦截（魔法） | 构造器+装饰器 | 构造器+装饰器 |
| 生命周期 | Fiber 六态状态机 + epoch | Provider scope | Container/scope |
| 资源清理 | effect 声明式自动逆序 | onModuleDestroy 手动 | unbind 手动 |
| 动态重载 | epoch 变化自动 reload | 需重启 | 手动 rebind |
| 隔离 | isolate Symbol 链 | 模块作用域 | 命名容器 |
| 配置覆盖 | intercept 原型链 | ConfigModule | 无原生 |
| 热更新 | 模块级 HMR (Node 内部 API) | 无原生 | 无 |
| 事件系统 | 5 模式 + internal/* 钩子 | EventEmitter | 无 |
| 学习成本 | 高（Proxy 魔法） | 中 | 中 |
| 质量评分 | 77/100 (B+) | - | - |

**结论**: Cordis 是"框架级"设计（魔法换体验，调试成本高），适合作为插件系统/DI 容器学习范本；业务应用建议 NestJS 等显式方案。

*2026-08-13*

---

### Agent 控制平面类 (2026-08-13)

| 特性 | LoopX | TimeCopilot | OpenAgentPack |
|------|-------|-------------|---------------|
| 语言 | Python (零依赖) | Python (pydantic-ai) | TypeScript |
| 定位 | Loop Engineering 控制平面 | GenAI 预测 Agent | Agent IaC 控制平面 |
| 规模 | 764 .py / 337K 行 | 43 文件 / 14.2K 行 | 352 文件 / 44K 行 |
| 状态模型 | 事件溯源 + 投影 | 对话 5 轮滑窗 | 声明式 YAML + StateManager |
| 执行模型 | turn = 事务 (七阶段 journal) | 三入口 analyze/forecast/query | validate→plan→apply |
| 预算控制 | ⭐ 配额一等公民 (29 文件) | ModelRetry 降级 | 依赖图拓扑 |
| 多 Agent | 对等者仲裁 + 监督者事件 | 无 | 无 |
| 安全 | 五层防线 + 收据防篡改 | 列名重映射 | Provider 适配 |
| 运行时 | Codex/Claude/opencode/Lagent | - | Bailian/Qoder/Claude/Ark |
| 质量评分 | 86/100 (A) | ~82/B | 85/100 (A-) |
| 学习价值 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

**结论**: 三者代表 Agent 基础设施的三种形态——LoopX 治理"长运行循环的状态"，TimeCopilot 专注"预测任务本身"，OpenAgentPack 管理"云端 Agent 的 IaC 生命周期"。LoopX 的配额闸门 + 回合事务模型是最独特的。

*2026-08-13*
