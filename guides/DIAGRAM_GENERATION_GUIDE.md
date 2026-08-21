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
