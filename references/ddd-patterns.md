# DDD 模式识别

## 何时使用

当分析企业级项目（尤其 Java/Go）时，检查是否采用 DDD 架构模式。

## DDD 核心模式检测

### 1. 聚合根 (Aggregate Root)

**特征**:
- 控制对聚合内部对象的访问
- 维护聚合内一致性规则
- 通常是 Entity，有唯一标识

**检测**:
```bash
# Java
rg "class.*AggregateRoot|extends.*AbstractAggregateRoot" --type java
rg "@Entity|class.*Root" --type java

# Go
rg "type.*Aggregate struct" --type go
```

### 2. 实体 (Entity)

**特征**:
- 有唯一标识 (ID)
- 可变状态
- 有业务逻辑方法

**检测**:
```bash
# Java
rg "class.*Entity|@Entity" --type java

# Python (SQLAlchemy)
rg "class.*\(Base\)|@Column" --type py
```

### 3. 值对象 (Value Object)

**特征**:
- 无唯一标识，通过值比较相等
- 不可变
- 通常轻量级

**检测**:
```bash
# Java
rg "class.*ValueObject|@Value|@Immutable" --type java

# Python (dataclass)
rg "@dataclass\(frozen=True\)|class.*ValueObject" --type py
```

### 4. 领域服务 (Domain Service)

**特征**:
- 操作不属于任何实体/值对象
- 无状态
- 包含跨聚合的业务逻辑

**检测**:
```bash
rg "class.*Service|class.*DomainService" --type java --type go --type py
```

### 5. 仓储 (Repository)

**特征**:
- 抽象持久化操作
- 提供集合式接口
- 隐藏数据访问细节

**检测**:
```bash
# Java
rg "interface.*Repository|extends.*JpaRepository|extends.*CrudRepository" --type java

# Go
rg "type.*Repository interface" --type go

# Python
rg "class.*Repository" --type py
```

### 6. 领域事件 (Domain Event)

**特征**:
- 表示领域中发生的重要事情
- 通常是不可变对象
- 有时间戳

**检测**:
```bash
rg "class.*Event|implements.*DomainEvent|class.*Event.*:" --type java --type go --type py

# 事件发布
rg "eventBus\.publish|publishEvent|domainEventPublisher" --type java --type go --type py
```

### 7. 限界上下文 (Bounded Context)

**特征**:
- 明确的业务边界
- 独立的模块/包
- 上下文映射

**检测**:
```bash
# 检查模块/包划分是否按业务域
find . -maxdepth 3 -type d -name "*context*" -o -name "*domain*" -o -name "*bounded*"

# 检查包/模块名是否包含业务域
find . -name "*.java" -o -name "*.go" -o -name "*.py" | head -50 \
  | xargs dirname | sort -u | grep -E "order|payment|user|inventory|shipping"
```

## DDD 架构层级检测

检查项目是否有清晰的分层：

```
├── presentation/     # 表现层（Controller、API）
├── application/      # 应用层（用例编排、DTO）
├── domain/           # 领域层（实体、值对象、领域服务）
└── infrastructure/   # 基础设施层（DB、外部服务）
```

**检测**:
```bash
# 检查是否有标准分层
for layer in presentation application domain infrastructure; do
  [ -d "$layer" ] && echo "✅ $layer/" || echo "❌ $layer/ 缺失"
done

# 或检查包名中的分层
rg "package.*\.presentation|package.*\.application|package.*\.domain|package.*\.infrastructure" --type java
```

## 常见架构模式

### 整洁架构 (Clean Architecture)

```
├── entities/         # 企业级业务规则
├── usecases/         # 应用业务规则
├── adapters/         # 适配器（外部接口转换）
└── frameworks/       # 框架和驱动
```

### 六边形架构 (Hexagonal)

```
├── core/             # 核心领域
├── ports/            # 端口（输入/输出接口）
├── adapters/         # 适配器（实现端口）
└── config/           # 配置
```

### 洋葱架构 (Onion)

```
├── domain/           # 最内层：领域模型
├── application/      # 应用服务
├── infrastructure/   # 基础设施
└── presentation/     # 最外层：用户界面
```

## 分析报告模板

```markdown
## DDD 架构评估

### 架构模式
- [ ] 整洁架构
- [ ] 六边形架构
- [ ] 洋葱架构
- [ ] 传统三层架构
- [ ] 无明显架构

### DDD 模式检测
| 模式 | 是否存在 | 位置 | 评价 |
|------|---------|------|------|
| 聚合根 | ✅/❌ | xx/xx.java | ... |
| 实体 | ✅/❌ | xx/xx.java | ... |
| 值对象 | ✅/❌ | xx/xx.java | ... |
| 领域服务 | ✅/❌ | xx/xx.java | ... |
| 仓储 | ✅/❌ | xx/xx.java | ... |
| 领域事件 | ✅/❌ | xx/xx.java | ... |
| 限界上下文 | ✅/❌ | 模块划分 | ... |

### 分层清晰度
| 层级 | 是否存在 | 职责分离 | 评价 |
|------|---------|---------|------|
| 表现层 | ✅/❌ | 好/中/差 | ... |
| 应用层 | ✅/❌ | 好/中/差 | ... |
| 领域层 | ✅/❌ | 好/中/差 | ... |
| 基础设施层 | ✅/❌ | 好/中/差 | ... |

### 建议
- ...
```

---

*最后更新: 2026-06-27*
