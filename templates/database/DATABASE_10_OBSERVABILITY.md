# 数据库系统监控与可观测性分析

> 🔍 分析数据库的指标暴露、慢查询日志、链路追踪、错误码体系

## 📋 核心问题清单

### 1. 指标暴露（Metrics）

#### 1.1 指标类型
- [ ] **系统指标**
  - CPU 使用率？
  - 内存使用率？
  - 磁盘 IO？
  - 网络 IO？
  
- [ ] **数据库指标**
  - QPS/TPS？
  - 连接数？
  - 缓存命中率？
  - 锁等待？
  
- [ ] **查询指标**
  - 查询延迟（P50/P90/P99）？
  - 查询错误率？
  - 慢查询数量？
  - 查询分布？

#### 1.2 指标暴露方式
- [ ] **Prometheus**
  - Prometheus 端点？
  - 指标格式？
  - 指标标签？
  
- [ ] **JMX**（Java 系统）
  - JMX MBeans？
  - JMX 端口？
  - JMX 认证？
  
- [ ] **系统表**
  - 指标系统表？
  - 实时查询？
  - 历史数据？
  
- [ ] **其他**
  - StatsD？
  - Graphite？
  - 自定义？

#### 1.3 指标粒度
- [ ] **全局指标**
  - 全局聚合指标？
  - 全局统计？
  
- [ ] **节点指标**
  - 单节点指标？
  - 节点对比？
  
- [ ] **查询级指标**
  - 单查询指标？
  - 查询追踪？

### 2. 慢查询日志

#### 2.1 慢查询定义
- [ ] **阈值配置**
  - 慢查询阈值？
  - 可配置？
  - 动态调整？
  
- [ ] **慢查询判定**
  - 执行时间？
  - 扫描行数？
  - 返回行数？
  - 资源消耗？

#### 2.2 日志内容
- [ ] **基本信息**
  - SQL 语句？
  - 执行时间？
  - 时间戳？
  - 用户信息？
  
- [ ] **执行计划**
  - 执行计划？
  - 索引使用？
  - 扫描行数？
  
- [ ] **资源消耗**
  - CPU 消耗？
  - 内存消耗？
  - IO 消耗？
  - 网络消耗？

#### 2.3 日志管理
- [ ] **日志存储**
  - 文件存储？
  - 系统表存储？
  - 外部系统？
  
- [ ] **日志轮转**
  - 日志大小限制？
  - 日志保留时间？
  - 日志压缩？
  
- [ ] **日志分析**
  - 慢查询分析工具？
  - 慢查询统计？
  - 慢查询告警？

### 3. 链路追踪（Trace）

#### 3.1 追踪实现
- [ ] **追踪标准**
  - OpenTelemetry？
  - Jaeger？
  - Zipkin？
  - 自定义？
  
- [ ] **追踪范围**
  - SQL 解析追踪？
  - 查询优化追踪？
  - 执行追踪？
  - 存储追踪？
  - 分布式追踪？

#### 3.2 追踪数据
- [ ] **Span 信息**
  - Span 名称？
  - Span 时间？
  - Span 标签？
  - Span 事件？
  
- [ ] **上下文传播**
  - Trace ID？
  - Span ID？
  - 跨节点传播？

#### 3.3 追踪可视化
- [ ] **可视化工具**
  - Jaeger UI？
  - Zipkin UI？
  - 自定义 UI？
  
- [ ] **追踪分析**
  - 关键路径分析？
  - 性能瓶颈？
  - 依赖关系？

### 4. 错误码体系

#### 4.1 错误码设计
- [ ] **错误码结构**
  - 错误码格式？
  - 错误码分类？
  - 错误码层级？
  
- [ ] **错误码范围**
  - 系统错误？
  - 语法错误？
  - 运行时错误？
  - 分布式错误？

#### 4.2 错误信息
- [ ] **错误描述**
  - 错误消息？
  - 错误原因？
  - 解决建议？
  
- [ ] **错误上下文**
  - 错误位置？
  - 错误堆栈？
  - 相关 SQL？

#### 4.3 错误处理
- [ ] **错误分类**
  - 可重试错误？
  - 不可重试错误？
  - 致命错误？
  
- [ ] **错误恢复**
  - 自动恢复？
  - 手动恢复？
  - 降级策略？

### 5. 日志系统

#### 5.1 日志级别
- [ ] **日志级别**
  - DEBUG？
  - INFO？
  - WARN？
  - ERROR？
  - FATAL？
  
- [ ] **日志控制**
  - 动态调整？
  - 模块级控制？
  - 组件级控制？

#### 5.2 日志内容
- [ ] **结构化日志**
  - JSON 格式？
  - 日志字段？
  - 日志标签？
  
- [ ] **日志上下文**
  - 请求 ID？
  - 会话 ID？
  - 事务 ID？

#### 5.3 日志管理
- [ ] **日志存储**
  - 本地存储？
  - 集中存储（ELK/Loki）？
  - 日志轮转？
  
- [ ] **日志检索**
  - 全文搜索？
  - 结构化查询？
  - 时间范围查询？

### 6. 告警机制

#### 6.1 告警规则
- [ ] **告警条件**
  - 性能告警？
  - 错误告警？
  - 资源告警？
  - 容量告警？
  
- [ ] **告警阈值**
  - 静态阈值？
  - 动态阈值？
  - 基线对比？

#### 6.2 告警通知
- [ ] **通知方式**
  - 邮件？
  - 即时通讯？
  - 短信？
  - Webhook？
  
- [ ] **告警分级**
  - 告警级别？
  - 告警升级？
  - 告警抑制？

## 🔍 代码检查点

### 指标暴露
```bash
# 查找 Prometheus
rg "prometheus|metrics|counter|histogram|gauge" --type cpp --type rust --type go

# 查找 JMX
rg "jmx|mbean|mxbean" --type java

# 查找系统表
rg "system_table|metrics_table|stats_table" --type cpp --type rust --type go
```

### 慢查询日志
```bash
# 查找慢查询
rg "slow_query|slow_log|long_query" --type cpp --type rust --type go

# 查找日志记录
rg "log_slow|record_slow|slow_threshold" --type cpp --type rust --type go
```

### 链路追踪
```bash
# 查找 OpenTelemetry
rg "opentelemetry|otel|tracing|span" --type cpp --type rust --type go

# 查找追踪
rg "trace_id|span_id|distributed_trace" --type cpp --type rust --type go
```

### 错误码
```bash
# 查找错误码
rg "error_code|err_code|status_code" --type cpp --type rust --type go

# 查找错误定义
rg "enum.*Error|class.*Error|ERROR_" --type cpp --type rust --type go
```

### 日志系统
```bash
# 查找日志
rg "logging|logger|log_" --type cpp --type rust --type go

# 查找结构化日志
rg "json_log|struct_log|log_format" --type cpp --type rust --type go
```

### 告警
```bash
# 查找告警
rg "alert|alarm|notification" --type cpp --type rust --type go

# 查找阈值
rg "threshold|limit|warning" --type cpp --type rust --type go
```

## 📊 评估标准

| 维度 | 优秀 (5分) | 良好 (4分) | 一般 (3分) | 需改进 (1-2分) |
|------|-----------|-----------|-----------|---------------|
| **指标暴露** | Prometheus+JMX+系统表 | 指标完善 | 基础指标 | 无指标 |
| **慢查询日志** | 完善日志+执行计划 | 日志完善 | 基础日志 | 无日志 |
| **链路追踪** | OpenTelemetry 完整追踪 | 有追踪 | 有限追踪 | 无追踪 |
| **错误码** | 完善错误码体系 | 错误码完善 | 基础错误码 | 错误码混乱 |
| **日志系统** | 结构化+集中存储 | 日志完善 | 基础日志 | 日志混乱 |
| **告警机制** | 完善告警+通知 | 告警完善 | 基础告警 | 无告警 |

## 📝 分析输出模板

```markdown
# [系统名] - 监控与可观测性分析

## 1. 指标暴露

**暴露方式**: Prometheus + 系统表

**关键指标**:
| 指标 | 类型 | 说明 |
|------|------|------|
| query_duration_seconds | Histogram | 查询延迟 |
| query_total | Counter | 查询总数 |
| connections_active | Gauge | 活跃连接数 |
| cache_hit_rate | Gauge | 缓存命中率 |

**Prometheus 端点**: `/metrics`

## 2. 慢查询日志

**阈值**: 1 秒（可配置）

**日志内容**:
- SQL 语句
- 执行时间
- 执行计划
- 扫描行数
- 用户信息

**日志存储**: 文件 + 系统表

## 3. 链路追踪

**追踪标准**: OpenTelemetry

**追踪范围**:
- SQL 解析
- 查询优化
- 执行
- 存储访问
- 分布式调用

**可视化工具**: Jaeger UI

## 4. 错误码体系

**错误码格式**: `[模块][类型][编号]`

**错误码分类**:
- 1000-1999: 语法错误
- 2000-2999: 运行时错误
- 3000-3999: 分布式错误

**错误信息**: 包含错误描述、原因、解决建议

## 5. 日志系统

**日志格式**: JSON 结构化

**日志级别**: DEBUG/INFO/WARN/ERROR/FATAL

**日志字段**:
```json
{
  "timestamp": "2026-06-26T10:00:00Z",
  "level": "INFO",
  "module": "query_executor",
  "message": "Query executed",
  "query_id": "xxx",
  "duration_ms": 100
}
```

**日志存储**: ELK Stack

## 6. 告警机制

**告警规则**:
- 查询延迟 P99 > 10s
- 错误率 > 5%
- 连接数 > 1000
- 磁盘使用率 > 80%

**通知方式**: 邮件 + 即时通讯

## 7. 设计亮点

- ✅ **亮点1**: [具体说明]

## 8. 学习价值

- ⭐⭐⭐⭐⭐ [值得借鉴的设计]
```

## 9. 💡 设计洞察

> 从该项目的可观测性设计中提炼的可移植原则

### 9.1 监控设计原则

**原则1**: [原则名称]
- **原理/证据/适用范围/去名检验**

示例:
> **原则**: 监控指标应该分层：系统级 + 查询级 + 会话级
>
> **原理**: 不同粒度的指标服务于不同的排查场景，系统级指标发现宏观问题，查询级指标定位具体瓶颈
>
> **证据**: PostgreSQL 提供 pg_stat_database（系统级）、pg_stat_statements（查询级）、pg_stat_activity（会话级）三层监控
>
> **去名检验**: ✅ 通用原则

### 9.2 诊断工具原则

**原则1**: [同上格式]

## 10. ⚠️ 隐含陷阱

> 从源码分析中发现的非显而易见的可观测性陷阱

### 10.1 性能开销陷阱

**陷阱1**: [陷阱名称]
- **现象/原因/正确做法**

### 10.2 信息过载陷阱

**陷阱1**: [同上格式]

## 🔗 参考项目

| 项目 | 可观测性特点 | 学习价值 |
|------|-------------|----------|
| **MySQL** | Performance Schema + 慢查询日志 | ⭐⭐⭐⭐⭐ 经典实现 |
| **PostgreSQL** | pg_stat + log_min_duration | ⭐⭐⭐⭐⭐ 系统表 |
| **ClickHouse** | system tables + metrics | ⭐⭐⭐⭐⭐ OLAP 监控 |
| **TiDB** | Prometheus + OpenTelemetry | ⭐⭐⭐⭐⭐ 分布式追踪 |
| **Elasticsearch** | X-Pack Monitoring | ⭐⭐⭐⭐ 搜索监控 |

---

*最后更新: 2026-06-27*
