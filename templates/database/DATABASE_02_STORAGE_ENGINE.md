# 数据库系统存储引擎与数据模型分析

> 🔍 分析数据库的物理存储布局、存储结构、文件格式、元数据管理、数据维护机制

## ⛔ 强制产出：字节级布局图

本模板的"数据物理布局"与各文件格式（SSTable/WAL/页/MANIFEST 等）章节，**每个必须包含 ≥1 张 ASCII 字节布局图**（mermaid 无法表达空间关系，不达标）。四要素缺一不可：

1. **方向**：字节流从头到尾（顶底框线 + 起止偏移 0x00/EOF）
2. **尺寸**：定长/变长/对齐标注（如 48B 固定 / varint / 8B 对齐）
3. **偏移**：每个区域标注起始 offset
4. **指针**：引用关系箭头（handle → offset、页指针 → 页号）

格式范式见 `guides/DIAGRAM_GENERATION_GUIDE.md` 第三类"空间布局图"。verify-analysis 对含"物理布局/文件格式/页结构"章节却无偏移标注（0x/├/offset/varint 等）的文档报 warning。

## 📋 核心问题清单

### 1. 数据物理布局

#### 1.1 表存储结构
- [ ] **堆表（Heap Table）**
  - 数据是否按插入顺序存储？
  - 是否需要 RowID 定位？
  - 适用场景？
  
- [ ] **索引组织表（IOT）**
  - 数据是否按主键顺序存储？
  - 主键查找是否无需回表？
  - 二级索引是否包含主键？

- [ ] **列式存储**
  - 是否按列存储数据？
  - 列块如何组织？
  - 是否支持列裁剪？

- [ ] **行列混存**
  - 是否同时支持行存和列存？
  - 数据如何同步？
  - 读写路径如何路由？

#### 1.2 数据组织
- [ ] **页/块管理**
  - 页大小是多少？（4KB/8KB/16KB）
  - 页头包含哪些信息？
  - 页内记录如何组织？
  
- [ ] **记录格式**
  - 定长记录还是变长记录？
  - NULL 值如何存储？
  - 变长字段如何编码？

### 2. 主存储结构

#### 2.1 B+Tree
- [ ] **B+Tree 实现**
  - 节点结构（叶子/非叶子）？
  - 分裂/合并策略？
  - 并发控制（锁/闩）？
  
- [ ] **B+Tree 优化**
  - 前缀压缩？
  - 页压缩？
  - 批量加载？

#### 2.2 LSM-Tree
- [ ] **LSM-Tree 实现**
  - MemTable 实现（SkipList/红黑树）？
  - SSTable 格式？
  - Compaction 策略（Size-Tiered/Leveled）？
  
- [ ] **LSM-Tree 优化**
  - Bloom Filter？
  - 布隆过滤器？
  - 写放大优化？

#### 2.3 其他结构
- [ ] **倒排索引**
  - 词项字典结构？
  - 倒排链编码（VarInt/BitPacking）？
  - 跳跃表（SkipList）？
  
- [ ] **列式压缩块**
  - 编码方式（RLE/Dictionary/Delta）？
  - 压缩算法（Snappy/Zstd/LZ4）？
  - 块索引？

### 3. 行存与列存

#### 3.1 行存实现
- [ ] **行格式**
  - 行头包含哪些元信息？
  - 如何表示 NULL？
  - 如何表示变长字段？
  
- [ ] **行组织**
  - 槽目录（Slot Directory）？
  - 链表组织？
  - 溢出页处理？

#### 3.2 列存实现
- [ ] **列块格式**
  - 列块头部信息？
  - 统计信息（min/max/null_count）？
  - 索引数据？
  
- [ ] **编码方式**
  - 整数编码（RLE/Dictionary/Delta）？
  - 字符串编码（Dictionary/Prefix）？
  - 浮点数编码？

#### 3.3 文件组织
- [ ] **文件格式**
  - 自定义格式？
  - 基于 Parquet/ORC？
  - 基于 SSTable？
  
- [ ] **文件管理**
  - 文件命名规则？
  - 文件大小限制？
  - 文件生命周期？

### 4. 元数据管理

#### 4.1 Schema 管理
- [ ] **Schema 存储**
  - Schema 存储在哪里？
  - 如何持久化？
  - 如何加载到内存？
  
- [ ] **Schema 版本**
  - 是否支持 Schema 版本？
  - 在线 DDL 如何实现？
  - Schema 变更如何同步？

#### 4.2 分区元数据
- [ ] **分区信息**
  - 分区键如何存储？
  - 分区裁剪信息？
  - 分区统计信息？
  
- [ ] **分区管理**
  - 分区创建/删除？
  - 分区合并/拆分？
  - 分区路由？

#### 4.3 索引元数据
- [ ] **索引信息**
  - 索引定义存储？
  - 索引统计信息？
  - 索引状态？

### 5. 数据维护

#### 5.1 删除与更新
- [ ] **删除实现**
  - 标记删除（Tombstone）？
  - 物理删除？
  - 空洞回收？
  
- [ ] **更新实现**
  - In-place 更新？
  - Copy-on-Write？
  - 版本链？

#### 5.2 过期与分层
- [ ] **TTL 支持**
  - 如何实现数据过期？
  - 过期检查时机？
  - 过期数据清理？
  
- [ ] **冷热分层**
  - 如何定义冷热数据？
  - 数据如何迁移？
  - 存储介质选择？

### 6. OLAP 特性

#### 6.1 预聚合
- [ ] **物化视图**
  - 物化视图存储？
  - 自动刷新机制？
  - 查询路由？
  
- [ ] **聚合表**
  - 预聚合实现？
  - 增量更新？
  - 查询加速？

#### 6.2 分区裁剪
- [ ] **裁剪实现**
  - 分区统计信息？
  - 裁剪算法？
  - 动态裁剪？

### 7. 搜索特性

#### 7.1 倒排结构
- [ ] **倒排表**
  - 倒排链组织？
  - 位置信息？
  - 频率信息？
  
- [ ] **正排表**
  - DocValue 存储？
  - 列式存储？
  - 快速访问？

#### 7.2 词项字典
- [ ] **字典结构**
  - FST（Finite State Transducer）？
  - Trie 树？
  - 内存映射？

## 🔍 代码检查点

### 存储结构
```bash
# 查找 B+Tree 实现
rg "class.*BPlusTree|class.*BTree|struct.*BTreeNode" --type cpp --type rust

# 查找 LSM-Tree 实现
rg "class.*LSM|class.*MemTable|class.*SSTable" --type cpp --type rust

# 查找页/块管理
rg "class.*Page|class.*Block|page_size|block_size" --type cpp --type rust
```

### 数据格式
```bash
# 查找行格式
rg "class.*Row|struct.*Row|row_format" --type cpp --type rust

# 查找列格式
rg "class.*Column|struct.*ColumnBlock|column_format" --type cpp --type rust

# 查找编码
rg "encode|decode|compress|decompress" --type cpp --type rust
```

### 元数据管理
```bash
# 查找 Schema 管理
rg "class.*Schema|class.*TableMeta|class.*ColumnMeta" --type cpp --type rust

# 查找分区管理
rg "class.*Partition|class.*Shard" --type cpp --type rust
```

### 数据维护
```bash
# 查找删除实现
rg "tombstone|delete|mark_delete" --type cpp --type rust

# 查找 Compaction
rg "compaction|merge|compact" --type cpp --type rust
```

## 📊 评估标准

| 维度 | 优秀 (5分) | 良好 (4分) | 一般 (3分) | 需改进 (1-2分) |
|------|-----------|-----------|-----------|---------------|
| **存储结构** | 多种结构，优化完善 | 有优化 | 基础实现 | 简单实现 |
| **数据格式** | 高效紧凑，支持压缩 | 格式合理 | 格式简单 | 格式混乱 |
| **元数据管理** | 完善版本管理 | 有版本控制 | 基础管理 | 无管理 |
| **数据维护** | 高效维护，自动清理 | 有维护机制 | 基础维护 | 无维护 |
| **OLAP/搜索** | 特性丰富，优化到位 | 有特性支持 | 有限支持 | 无支持 |

## 📝 分析输出模板

```markdown
# [系统名] - 存储引擎与数据模型分析

## 1. 物理布局

**存储模型**: 行存 / 列存 / 行列混存

**页结构**:
```cpp
struct Page {
    PageHeader header;  // 页头
    SlotDirectory slots; // 槽目录
    RecordData data;     // 记录数据
};
```

**页大小**: 16KB

## 2. 主存储结构

**B+Tree 实现**:
```cpp
class BPlusTree {
    BTreeNode* root;
    int key_size;
    int fanout;
    
    Status insert(Key key, Value value);
    Status search(Key key, Value& value);
};
```

**节点结构**:
- 叶子节点: [keys, pointers, next_pointer]
- 非叶子节点: [keys, child_pointers]

## 3. 数据格式

**行格式**:
```
[header][null_bitmap][fixed_fields][variable_fields]
```

**NULL 表示**: 位图（bitmap）

**变长字段**: [offset][length][data]

## 4. 元数据管理

**Schema 存储**: 系统表

**Schema 版本**: ✅ 支持版本控制

**在线 DDL**: ✅ 支持

## 5. 数据维护

**删除实现**: 标记删除（Tombstone）

**Compaction**: Leveled Compaction

**TTL 支持**: ✅ 支持

## 6. 设计亮点

- ✅ **亮点1**: [具体说明]

## 7. 学习价值

- ⭐⭐⭐⭐⭐ [值得借鉴的设计]
```

## 8. 💡 设计洞察

> 从该项目的存储引擎设计中提炼的可移植原则

### 8.1 存储布局原则

**原则1**: [原则名称]
- **原理**: [为什么重要]
- **证据**: [项目中的具体实现]
- **适用范围**: [什么场景适用]
- **去名检验**: ✅/⚠️

示例:
> **原则**: 存储布局应该匹配访问模式
>
> **原理**: 行存适合 OLTP（频繁更新整行），列存适合 OLAP（只读少量列），行列混存适合 HTAP
>
> **证据**: OceanBase 使用行列混存，同时支持事务处理和 analytical 查询
>
> **适用范围**: 任何需要选择存储格式的数据系统
>
> **去名检验**: ✅ 通用原则

**原则2**: [同上格式]

### 8.2 数据结构原则

**原则1**: [同上格式]

示例:
> **原则**: 索引结构应该平衡读写放大
>
> **原理**: B+Tree 读放大低但写放大高，LSM-Tree 写放大低但读放大高，没有银弹
>
> **证据**: MySQL 使用 B+Tree（读多写少场景），RocksDB 使用 LSM-Tree（写密集场景）
>
> **去名检验**: ✅ 适用于任何需要索引的系统

## 9. ⚠️ 隐含陷阱

> 从源码分析中发现的非显而易见的存储引擎陷阱

### 9.1 存储陷阱

**陷阱1**: [陷阱名称]
- **现象**: [说明]
- **原因**: [说明]
- **正确做法**: [说明]

示例:
> **陷阱**: 页分裂导致的空间浪费
>
> **现象**: 数据量不大，但磁盘占用远超预期
>
> **原因**: B+Tree 页分裂时只填充 50%，导致大量半空页
>
> **正确做法**: 使用延迟分裂或批量插入时预排序

### 9.2 数据格式陷阱

**陷阱1**: [同上格式]

示例:
> **陷阱**: NULL 值处理不当导致索引失效
>
> **现象**: 包含 NULL 的列查询性能下降
>
> **原因**: NULL 值在索引中的表示不一致，导致索引扫描时需要额外判断
>
> **正确做法**: 使用 COALESCE 或默认值替代 NULL，或在索引中显式处理 NULL

### 9.3 维护陷阱

**陷阱1**: [同上格式]

## 🔗 参考项目

| 项目 | 存储特点 | 学习价值 |
|------|----------|----------|
| **MySQL InnoDB** | B+Tree 索引组织表 | ⭐⭐⭐⭐⭐ 经典实现 |
| **RocksDB** | LSM-Tree 存储引擎 | ⭐⭐⭐⭐⭐ LSM 优化 |
| **ClickHouse** | 列式存储 | ⭐⭐⭐⭐⭐ 列存优化 |
| **PostgreSQL** | 堆表 + MVCC | ⭐⭐⭐⭐⭐ 堆表实现 |
| **OceanBase** | 行列混存 | ⭐⭐⭐⭐⭐ HTAP 存储 |

---

*最后更新: 2026-06-27*
