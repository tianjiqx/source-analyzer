# 分析输出图表生成规范

> 🎨 源码分析的输出文档应包含 Mermaid 图表，让架构、数据流、调用链一目了然

## 核心理念

参考 DeepWiki/OpenDeepWiki 的做法：**分析产出不仅仅是文字，还应包含可视化图表**。

每个分析文档中，凡是能用图表说清楚的内容，都应该生成 Mermaid 图表。

## 支持的图表类型

| 图表类型 | Mermaid 语法 | 适用场景 |
|----------|-------------|----------|
| **架构图** | `flowchart TD` | 系统分层、模块关系 |
| **数据流图** | `flowchart LR` | 请求处理链路、数据管道 |
| **时序图** | `sequenceDiagram` | API 调用、组件交互 |
| **类图** | `classDiagram` | 核心类关系、继承体系 |
| **状态图** | `stateDiagram-v2` | 状态机、生命周期 |
| **ER 图** | `erDiagram` | 数据模型、表关系 |
| **思维导图** | `mindmap` | 模块分解、功能全景 |
| **甘特图** | `gantt` | 处理流程时间线 |
| **饼图** | `pie` | 代码分布、资源占比 |

## 图表生成规则

### 规则 1: 每个分析文档至少包含 1 个图表

| 文档类型 | 必须包含的图表 |
|----------|---------------|
| 架构分析 | 系统分层架构图 (flowchart TD) |
| 模块分析 | 模块依赖图 (flowchart) |
| 文件分析 | 类/函数依赖图 (classDiagram 或 flowchart) |
| 数据流分析 | 数据流图 (flowchart LR) |
| API 分析 | 时序图 (sequenceDiagram) |
| 状态管理 | 状态图 (stateDiagram) |
| 数据模型 | ER 图 (erDiagram) |
| 项目概览 | 思维导图 (mindmap) 或 架构图 |

### 规则 2: 图表必须基于实际代码

```
❌ 错误: 凭想象画架构图
✅ 正确: 阅读代码后，根据实际的 import/依赖/调用关系画图
```

### 规则 3: 图表中标注源码位置

```mermaid
flowchart TD
    A["API Layer<br/><i>src/Endpoints/</i>"] --> B["Service Layer<br/><i>src/Services/</i>"]
    B --> C["Repository<br/><i>src/Repositories/</i>"]
    C --> D[("Database<br/><i>EFCore/</i>")]
```

### 规则 4: 图表风格统一

- 使用 `subgraph` 对模块分组
- 节点文字简洁，不超过 20 字
- 用 `""` 双引号包裹含特殊字符的文字
- 用 `<br/>` 换行
- 用 `<i>` 标注文件路径

## 图表模板库

### 1. 系统分层架构图

```mermaid
flowchart TD
    subgraph Frontend["前端层"]
        UI["UI 组件<br/><i>web/components/</i>"]
        Pages["页面路由<br/><i>web/app/</i>"]
    end
    
    subgraph Backend["后端层"]
        API["API 端点<br/><i>src/Endpoints/</i>"]
        Services["业务服务<br/><i>src/Services/</i>"]
    end
    
    subgraph Data["数据层"]
        Repo["仓储层<br/><i>src/Repositories/</i>"]
        DB[("数据库<br/><i>EFCore/</i>")]
    end
    
    Pages --> API
    API --> Services
    Services --> Repo
    Repo --> DB
```

### 2. 请求处理链路图

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API Layer
    participant S as Service
    participant R as Repository
    participant D as Database
    
    C->>A: HTTP Request
    A->>A: 参数验证
    A->>S: 调用业务方法
    S->>R: 查询数据
    R->>D: SQL Query
    D-->>R: Result Set
    R-->>S: Entity
    S-->>A: DTO
    A-->>C: HTTP Response
```

### 3. 类关系图

```mermaid
classDiagram
    class IService {
        <<interface>>
        +GetData() Task~Result~
        +SaveData() Task
    }
    
    class ServiceImpl {
        -IRepository _repo
        -ILogger _logger
        +GetData() Task~Result~
        +SaveData() Task
    }
    
    class IRepository {
        <<interface>>
        +FindById() Task~Entity~
    }
    
    IService <|.. ServiceImpl
    ServiceImpl --> IRepository
```

### 4. 数据流图

```mermaid
flowchart LR
    Input["输入数据"] --> Parse["解析"]
    Parse --> Validate["验证"]
    Validate --> Transform["转换"]
    Transform --> Store["存储"]
    Store --> Output["输出结果"]
    
    subgraph Pipeline["数据处理管道"]
        Parse --> Validate --> Transform --> Store
    end
```

### 5. 思维导图（项目全景）

```
mindmap
  root((项目名))
    核心架构
      API层
      服务层
      数据层
    关键特性
      特性A
      特性B
    技术栈
      前端
      后端
      存储
```

### 6. 状态图

```mermaid
stateDiagram-v2
    [*] --> Pending
    Pending --> Processing: 开始处理
    Processing --> Completed: 处理成功
    Processing --> Failed: 处理失败
    Failed --> Processing: 重试
    Completed --> [*]
```

### 7. ER 图

```mermaid
erDiagram
    USER ||--o{ POST : writes
    USER {
        int id PK
        string name
        string email
    }
    POST {
        int id PK
        int user_id FK
        string title
        string content
    }
```

### 8. 模块依赖图

```mermaid
flowchart TD
    A["模块A<br/><i>core/</i>"] --> B["模块B<br/><i>service/</i>"]
    A --> C["模块C<br/><i>utils/</i>"]
    B --> D["模块D<br/><i>repository/</i>"]
    B --> C
    D --> E[("数据库")]
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#e8f5e9
    style D fill:#fff3e0
```

## 图表质量检查

每个图表生成后，自检：

- [ ] 节点文字是否简洁？（不超过 20 字）
- [ ] 是否标注了源码路径？
- [ ] 箭头方向是否正确？
- [ ] subgraph 分组是否合理？
- [ ] 是否基于实际代码？（不是凭空想象）
- [ ] Mermaid 语法是否正确？（避免渲染失败）

### 自动化检验

```bash
# 检验所有分析文档中的 mermaid 图表
python3 scripts/mermaid-validator.py output-dir/ --recursive -o output-dir/MERMAID_VALIDATION_REPORT.md
```

检验规则详见 [MERMAID_VALIDATION.md](MERMAID_VALIDATION.md)

**集成到验证流程**: 在 `verify-analysis.py --all` 和 `plan-tracker.py verify` 之后运行。

## 第二类：原理讲解型图表（回答"为什么"）

> 结构图（第一类）回答"系统长什么样"；讲解型图回答学习者真正的问题：**为什么这样设计、没有它会怎样、如何演进而来**。
> 💡设计洞察章节至少 1 条洞察必须配讲解型图（对比/权衡/演进三选一）；费曼学习卡片每张至少 1 张讲解型图。

### 9. 对比图（有 vs 无某机制）

双列 subgraph 并排展示：左列无该机制的朴素实现，右列有该机制的实现，用虚线箭头标注关键差异点。

```mermaid
flowchart LR
    subgraph WITHOUT["❌ 无合并步骤：直接落库"
        A1["chunk 后直接写入"] --> A2["实体各自独立"] --> A3["查询召回碎片化<br/>同义实体重复出现"]
    end
    subgraph WITH["✅ 有实体合并"
        B1["chunk 后实体抽取"] --> B2["合并同义实体"] --> B3["查询召回集中<br/>图结构连通"]
    end
    WITHOUT -.->|"合并步骤消除的缺陷"| WITH
```

### 10. 权衡象限图（quadrantChart）

展示方案在权衡空间中的位置，说明"为什么选它"。

```mermaid
quadrantChart
    title 检索方案权衡：召回率 vs 成本
    x-axis "低成本" --> "高成本"
    y-axis "低召回" --> "高召回"
    quadrant-1 "高价值区"
    quadrant-2 "需论证"
    quadrant-3 "不推荐"
    quadrant-4 "高性价比"
    "纯向量检索": [0.35, 0.3]
    "纯关键词检索": [0.4, 0.25]
    "混合检索(hybrid)": [0.78, 0.6]
    "多路召回+rerank": [0.9, 0.85]
```

### 11. 演进时间线（timeline）

展示机制如何逐步解决上一版的缺陷——学习迁移的关键：知道每一步解决什么问题，才知道何时适用。

```mermaid
timeline
    title 查询模式演进
    naive : 直接 chunk 检索<br/>（无法回答全局问题）
    local : 实体邻域检索<br/>（解决局部精准）
    global : 社区摘要检索<br/>（解决全局理解）
    hybrid : local+global 融合<br/>（解决单一模式偏科）
```

### 12. 失败路径标注（stateDiagram + 红色分支）

正常流程之外，必须画出失败/降级路径（红色），说明"没有 X 会怎样"。

```mermaid
stateDiagram-v2
    direction LR
    [*] --> Normal: 正常请求
    Normal --> Retrying: 下游超时
    Retrying --> Normal: 重试成功
    Retrying --> Degraded: 重试耗尽 --> 降级
    Degraded --> [*]: 返回兜底结果
    Normal --> [*]: 成功

    Degraded: ⚠️ 降级：读旧快照
    note right of Degraded : 降级期间写入被拒<br/>防止脑裂
```

### 13. 决策点标注（sequenceDiagram + Note）

在关键调用旁用 Note 标注设计决策的"为什么"。

```mermaid
sequenceDiagram
    participant C as Client
    participant W as Writer
    participant M as Merger
    C->>W: insert(document)
    Note over W: 决策：先写 WAL 再抽取<br/>（抽取失败不丢数据）
    W->>W: chunk + 实体抽取
    W->>M: 提交合并
    Note over M: 决策：串行合并<br/>（避免并发写竞态）
    M-->>W: 合并完成
    W-->>C: 确认
```

---

## 第三类：空间布局图（回答"数据长什么样"）

> mermaid 是拓扑图工具，**无法表达空间关系**（字节流方向、定长/变长、偏移、指针指向）。
> 凡涉及物理存储/文件格式/内存布局/页结构/消息格式/序列化格式，必须用 **ASCII 字节布局图**，四要素缺一不可：

| 要素 | 说明 | 标注方式 |
|------|------|----------|
| **方向** | 字节流从头到尾 | 图顶底框线 + 起止偏移（0x00 / EOF） |
| **尺寸** | 定长/变长/对齐 | 区域旁标注（48B 固定 / varint 变长 / 8B 对齐） |
| **偏移** | 每区域起始位置 | 左侧 offset 列（0x00、offset 处） |
| **指针** | 引用关系 | 箭头（handle → offset） |

### 14. ASCII 字节布局图范式

以 LevelDB SSTable 为例（文件末 8B 为 magic number，Footer 内两个 BlockHandle 指回数据区）：

```
SSTable 文件逻辑布局（纵向=字节流方向，非比例）
┌─────────────────────────────┐ 0x00
│ Data Block 0                │ 变长（重启点数组在块尾）
├─────────────────────────────┤
│ ...                         │
├─────────────────────────────┤
│ Data Block N                │ 变长
├─────────────────────────────┤
│ Meta Block (filter)         │ 变长
├─────────────────────────────┤ ← metaindex_handle.offset
│ Metaindex Block             │ 变长
├─────────────────────────────┤ ← index_handle.offset
│ Index Block                 │ 变长（每条目一个 BlockHandle）
├─────────────────────────────┤
│ Footer (48B, 固定)          │ metaindex_handle + index_handle + padding + magic
└─────────────────────────────┘ EOF-8 ← magic=0xdb4775248b80fb57（最后 8B）
        ▲
        └── Footer.index_handle {offset:varint, size:varint} 指回 Index Block 起点
            Footer.metaindex_handle 同理指回 Metaindex Block
说明：读 SSTable 时先读末 48B Footer → 两个 handle 定位索引区 → 索引区的
BlockHandle 数组定位任意 Data Block —— 一次 lseek + 顺序读即可二分查找。
```

### 15. 简版：mermaid 纵向堆叠（仅表达组成顺序，不标偏移时可用）

```mermaid
flowchart TB
    F["Footer (48B 固定)<br/><i>table/format.cc</i>"] --> I["Index Block"]
    I --> MX["Metaindex Block"]
    MX --> MB["Meta Block (filter)"]
    MB --> D["Data Block 0..N"]
```

> ⚠️ mermaid 堆叠只能表达"组成与顺序"。凡能写出具体偏移/定长的，一律升级为 ASCII 字节图（范式见上）。

---

## 在不同模板中的应用

### 项目级分析 (00-README.md)

必须包含：
1. **系统全景图** (flowchart TD) - 展示整体架构分层
2. **核心数据流** (flowchart LR) - 展示主要请求处理链路

### 架构分析 (01-architecture.md)

必须包含：
1. **分层架构图** (flowchart TD + subgraph) - 详细展示各层组件
2. **模块依赖图** (flowchart) - 展示模块间依赖关系
3. **部署架构图** (flowchart) - 展示部署拓扑（如有）

### 文件级分析

必须包含：
1. **类/函数关系图** (classDiagram 或 flowchart) - 展示文件内核心关系
2. **调用链路图** (sequenceDiagram) - 展示关键方法的调用时序

### 专项分析

| 专项 | 必须包含的图表 |
|------|---------------|
| LLM Agent | Agent 工作流图 (flowchart) + 工具调用时序图 (sequence) |
| 数据库系统 | 查询执行计划图 (flowchart) + 存储引擎架构图 |
| 全栈 Web | 前后端交互时序图 + 路由结构图 |
| Pipeline | 管道阶段图 (flowchart LR) + 状态流转图 (stateDiagram) |

---
