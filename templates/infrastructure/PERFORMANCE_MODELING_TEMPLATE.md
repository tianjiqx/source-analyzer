# 性能建模分析模板 - Amplification Framework

> **适用场景**: 数据库系统、存储系统、大数据系统等有 Write/Read/Space Amplification 的系统
> **核心框架**: W/R/S Amplification 三角权衡
> **目标**: 系统化分析性能瓶颈，量化性能权衡，指导优化决策

---

## 一、Amplification 概念框架

### 1.1 核心概念定义

**Amplification（放大因子）**: 实际资源消耗 / 用户需求资源的比值

| Amplification | 定义 | 公式 | 单位 |
|---------------|------|------|------|
| **Write Amplification (WA)** | 实际写入量 / 用户写入量 | `WA = Total Writes / User Writes` | 倍数 |
| **Read Amplification (RA)** | 实际读取量 / 用户读取量 | `RA = Total Reads / User Reads` | 倍数 |
| **Space Amplification (SA)** | 实际空间 / 用户数据 | `SA = Total Space / User Data` | 倍数 |

### 1.2 Amplification 的意义

**为什么需要 Amplification 概念？**

1. **量化性能瓶颈**: 将抽象的性能问题量化为具体数值
2. **指导优化决策**: 明确优化目标，降低某个 Amplification
3. **权衡分析**: 不同优化策略对不同 Amplification 的影响
4. **系统对比**: 不同系统的 Amplification 差异揭示架构差异

**Amplification 的典型范围**:

| 系统 | Write Amp | Read Amp | Space Amp | 特征 |
|------|-----------|----------|-----------|------|
| **RocksDB (Leveled)** | 10-50 | 1-2 | 1.1-1.5 | 读优化、空间优化 |
| **RocksDB (Tiered)** | 1-3 | 10-30 | 1.5-2.5 | 写优化 |
| **B-Tree** | 1 | 1 | 1.5-2 | 无 WA，随机写入慢 |
| **LSM Tree (典型)** | 10-30 | 2-5 | 1.2-2 | WA 高，写入快 |

### 1.3 三角权衡关系

**核心矛盾**: Write Amp ↔ Read Amp ↔ Space Amp 三者相互制约

```
       Write Amp
           ↓
       [降低 WA]
      ↙        ↘
[提高 RA]   [提高 SA]
    ↑            ↑
 Read Amp    Space Amp
```

**权衡矩阵**:

| 优化目标 | 对其他 Amp 影响 | 典型策略 |
|----------|-----------------|----------|
| **降低 WA** | ↑ RA, ↑ SA | Tiered Compaction, 大 Memtable |
| **降低 RA** | ↑ WA, ↓ SA | Leveled Compaction, Bloom Filter |
| **降低 SA** | ↑ WA, ↓ RA | Frequent Compaction, Compression |

**场景化选择**:

| 场景 | 推荐策略 | WA 目标 | RA 目标 | SA 目标 |
|------|----------|---------|---------|---------|
| **写密集** | Tiered Compaction | 1-3 | 10-30 | 1.5-2.5 |
| **读密集** | Leveled Compaction | 10-50 | 1-2 | 1.1-1.5 |
| **空间敏感** | Frequent Compaction | 20-30 | 1-2 | 1.1-1.2 |
| **混合场景** | Hybrid Compaction | 5-10 | 3-5 | 1.2-1.5 |

---

## 二、Write Amplification 分析

### 2.1 WA 计算方法

#### 方法 1: 统计方法（推荐）

**步骤**:
1. 统计所有写入操作（WAL + Flush + Compaction）
2. 统计用户写入量（写入请求的数据量）
3. 计算 WA = Total Writes / User Writes

**示例**:
```bash
# 统计 WAL 写入
wal_bytes = sum(wal_file_sizes)

# 统计 SST 写入（包含多次 Compaction 重写）
sst_bytes = sum(all_sst_file_writes)

# 统计用户写入
user_bytes = sum(user_write_requests)

# 计算 WA
WA = (wal_bytes + sst_bytes) / user_bytes
```

#### 方法 2: 理论分析方法

**LSM Tree WA 理论公式**:

```
WA = (L0→L1) + (L1→L2) + ... + (Ln-1→Ln)
   = size_ratio * num_levels
   = (size_ratio) * log(user_data / memtable_size) / log(size_ratio)
```

**示例计算**:
```
假设:
- size_ratio = 10 (每层是上层的 10倍)
- num_levels = 7 (L0-L6)
- memtable_size = 64MB
- user_data = 1TB

WA = 10 * 7 = 70  (理论值)
实测 WA = 40-50  (考虑优化策略)
```

### 2.2 WA 来源分析

#### WA 来源分解表

| 来源 | 说明 | WA 贡献 | 优化方法 |
|------|------|---------|----------|
| **WAL** | 预写日志，每次写入必写 | 1.0-1.2 | 异步 WAL, Group Commit |
| **Flush** | Memtable → SST (L0) | 1.0 | 大 Memtable, 并行 Flush |
| **L0→L1 Compaction** | L0 与 L1 合并 | size_ratio | Universal Compaction |
| **L1→L2 Compaction** | L1 与 L2 合并 | size_ratio | Leveled Compaction |
| **Ln-1→Ln Compaction** | 层层合并 | size_ratio * (num_levels-1) | - |
| **Total WA** | 所有来源加和 | 10-50 | 综合优化 |

#### WA 来源示例分析

**RocksDB Leveled Compaction WA 分析**:

```
Write Path:
1. User Write: 1.0 GB
2. WAL:        1.0 GB  (WA = 1.0)
3. Flush L0:   1.0 GB  (WA = 1.0)
4. Compaction:
   - L0→L1:    10 GB   (WA = 10)
   - L1→L2:    10 GB   (WA = 10)
   - L2→L3:    10 GB   (WA = 10)
   - L3→L4:    10 GB   (WA = 10)
   - L4→L5:    10 GB   (WA = 10)
   - L5→L6:    10 GB   (WA = 10)

Total Writes = 1 + 1 + 10*6 = 62 GB
WA = 62 / 1 = 62  (理论值)

实测考虑优化: WA = 30-40
```

### 2.3 WA 优化策略

#### 优化策略矩阵

| 策略 | 说明 | WA 降低幅度 | 对 RA/SA 影响 | 适用场景 |
|------|------|-------------|---------------|----------|
| **Tiered Compaction** | 延迟合并，减少 Compaction 次数 | WA: 1-3 (降低 70-90%) | ↑ RA (10-30), ↑ SA (1.5-2.5) | 写密集 |
| **大 Memtable** | 减少 Flush 频率 | WA: 降低 20-30% | ↓ RA (Cache命中率提高) | 写密集 |
| **Universal Compaction** | 优化 L0→L1 合并策略 | WA: 降低 30-50% | ↑ RA, ↑ SA | 写密集 |
| **Parallel Compaction** | 并行 Compaction，不降低 WA | 不降低 WA | 不影响 RA/SA | Compaction 延迟高 |
| **Compression** | 数据压缩 | WA: 降低 30-50% | ↑ RA (解压开销) | 空间敏感 |
| **异步 WAL** | WAL 异步写入 | WA: 降低 10-20% | ↑ RA (恢复时间) | 写密集 |
| **Group Commit** | 批量提交 | WA: 降低 10-15% | ↑ 延迟 | 写密集 |

#### 优化策略详细说明

**策略 1: Tiered Compaction**

```
原理:
- 不立即合并，等待多层累积后一次性合并
- 减少 Compaction 次数，降低 WA

WA 计算:
- Leveled: WA = size_ratio * num_levels = 10*7 = 70
- Tiered:  WA = num_levels = 7 (降低 90%)

代价:
- RA 提高: L0 层数增加，查询需要读更多 SST
- SA 提高: 多层未合并，冗余数据增加
```

**策略 2: 大 Memtable**

```
配置:
write_buffer_size = 256MB  (默认 64MB)

效果:
- Flush 频率降低 4倍
- L0 SST 数量减少 4倍
- WA 降低约 20-30%

代价:
- 内存占用增加
- Flush 时写入阻塞时间增加
```

---

## 三、Read Amplification 分析

### 3.1 RA 计算方法

#### 方法 1: 统计方法

**步骤**:
1. 统计所有读取操作（Cache + Memtable + SST + Block Cache）
2. 统计用户读取量（读取请求的数据量）
3. 计算 RA = Total Reads / User Reads

**示例**:
```bash
# 统计 SST 读取次数
sst_reads = sum(sst_file_reads)

# 统计 Block Cache 读取次数
block_cache_reads = sum(block_cache_reads)

# 统计用户读取次数
user_reads = sum(user_read_requests)

# 计算 RA
RA = (sst_reads + block_cache_reads) / user_reads
```

#### 方法 2: 理论分析方法

**LSM Tree RA 理论公式**:

```
RA = num_levels + bloom_filter_effect
   = log(user_data / memtable_size) / log(size_ratio) + bf_effect
```

**示例计算**:
```
假设:
- num_levels = 7 (L0-L6)
- Bloom Filter 优化: 每层减少 90% 无效读取

RA = 7 + 0.1 = 7.1  (无 Bloom Filter)
RA = 7 * 0.1 + 1 = 1.7  (有 Bloom Filter)
```

### 3.2 RA 来源分析

#### RA 来源分解表

| 来源 | 说明 | RA 贡献 | 优化方法 |
|------|------|---------|----------|
| **Memtable** | 内存查找，RA=1 | 1.0 | 大 Memtable |
| **Immutable Memtable** | 内存查找，RA=1 | 1.0 | 增加 Immutable 数量 |
| **L0 SST** | 需读所有 L0 SST | num_L0_files | 限制 L0 文件数, Compact L0 |
| **L1-Ln SST** | 每层最多读 1个 SST | num_levels | Bloom Filter |
| **Block Cache** | Block 缓存命中 | 0.1-0.5 | 大 Block Cache |
| **Total RA** | 所有来源加和 | 2-30 | 综合优化 |

#### RA 来源示例分析

**RocksDB Leveled Compaction RA 分析**:

```
Read Path (Point Lookup):
1. Memtable:      1 次  (RA = 1)
2. Immutable:     1 次  (RA = 1)
3. L0 SST:        8 次  (RA = 8, 假设 L0 有 8 个文件)
4. L1-L6 SST:     7 次  (RA = 7, 每层最多读 1 个)
5. Bloom Filter:  减少 90% 无效读取

Total RA = 1 + 1 + 8 + 7 = 17 (无 Bloom Filter)
Total RA = 1 + 1 + 0.8 + 0.7 = 3.5 (有 Bloom Filter)
```

### 3.3 RA 优化策略

#### 优化策略矩阵

| 策略 | 说明 | RA 降低幅度 | 对 WA/SA 影响 | 适用场景 |
|------|------|-------------|---------------|----------|
| **Bloom Filter** | SST 元数据过滤，减少无效读取 | RA: 降低 90% | ↑ WA (构建开销) | 读密集 |
| **大 Block Cache** | 缓存 SST Block | RA: 降低 50-80% | ↑ 内存占用 | 读密集 |
| **Leveled Compaction** | 减少每层文件数 | RA: 降低到 1-2 | ↑ WA (10-50) | 读密集 |
| **限制 L0 文件数** | 减少 L0 查找次数 | RA: 降低 30-50% | ↑ WA (频繁 Compact) | 读密集 |
| **Partitioned Index/Filters** | 分区索引/过滤器 | RA: 降低 20-30% | ↑ SA (索引空间) | 读密集 |

#### 优化策略详细说明

**策略 1: Bloom Filter**

```
配置:
bloom_filter_bits_per_key = 10  (默认 10)
bloom_filter_block_size = 4096

效果:
- 每层减少 90% 无效读取
- RA 降低: 17 → 3.5 (降低 79%)

代价:
- 构建 Bloom Filter 开销: WA 增加 5-10%
- Bloom Filter 空间: SA 增加 1-2%
```

**策略 2: Leveled Compaction**

```
原理:
- 每层文件有序，每层最多读 1 个 SST
- RA 最小化

RA 计算:
- Tiered: RA = num_L0_files + num_levels = 30 + 7 = 37
- Leveled: RA = num_levels = 7 (降低 81%)

代价:
- WA 提高: Leveled WA = 50, Tiered WA = 3
- Compaction 频率提高
```

---

## 四、Space Amplification 分析

### 4.1 SA 计算方法

#### 方法 1: 统计方法

**步骤**:
1. 统计实际存储空间（所有 SST 文件大小）
2. 统计用户数据大小（实际有效数据）
3. 计算 SA = Total Space / User Data

**示例**:
```bash
# 统计所有 SST 文件大小
sst_total_size = sum(sst_file_sizes)

# 统计用户数据大小（压缩后的有效数据）
user_data_size = sum(user_data_compressed)

# 计算 SA
SA = sst_total_size / user_data_size
```

#### 方法 2: 理论分析方法

**LSM Tree SA 理论公式**:

```
SA = 1 + redundancy_ratio
   = 1 + (pending_compaction_data / total_data)
```

**示例计算**:
```
假设:
- Tiered Compaction: L0-L6 每层有 1 个未合并 SST
- redundancy_ratio = 0.5 (50% 冗余数据)

SA = 1 + 0.5 = 1.5 (Tiered)
SA = 1 + 0.1 = 1.1 (Leveled, 频繁 Compaction)
```

### 4.2 SA 来源分析

#### SA 来源分解表

| 来源 | 说明 | SA 贡献 | 优化方法 |
|------|------|---------|----------|
| **有效数据** | 用户实际数据 | 1.0 | - |
| **Compaction 未完成数据** | Compaction 过程中的冗余数据 | 0.1-0.5 | Frequent Compaction |
| **L0 多文件冗余** | L0 层多文件重叠 | 0.2-0.8 | Compact L0 |
| **Tiered 多层冗余** | Tiered 策略的多层冗余 | 0.5-1.5 | Leveled Compaction |
| **索引/元数据** | Bloom Filter, Index Block | 0.1-0.2 | 索引优化 |
| **Total SA** | 所有来源加和 | 1.1-2.5 | 综合优化 |

#### SA 来源示例分析

**RocksDB Compaction Strategy SA 分析**:

```
Leveled Compaction:
- L0: 8 个小文件 (部分重叠)
- L1-L6: 每层文件有序，无重叠
- Compaction 持续进行

SA = 1 + 0.1 (L0 重叠) + 0.05 (索引) = 1.15

Tiered Compaction:
- L0-L6: 每层累积多个文件，延迟合并
- 冗余数据多

SA = 1 + 0.5 (多层冗余) + 0.05 (索引) = 1.55
```

### 4.3 SA 优化策略

#### 优化策略矩阵

| 策略 | 说明 | SA 降低幅度 | 对 WA/RA 影响 | 适用场景 |
|------|------|-------------|---------------|----------|
| **Frequent Compaction** | 频繁 Compaction，减少冗余 | SA: 降低 20-30% | ↑ WA (Compaction 频率) | 空间敏感 |
| **Leveled Compaction** | 每层有序，减少冗余 | SA: 降低到 1.1-1.2 | ↑ WA (10-50) | 读密集 |
| **Compression** | 数据压缩 | SA: 降低 30-50% | ↑ RA (解压开销), ↑ WA (压缩开销) | 空间敏感 |
| **Delete Obsolete Files** | 及时删除旧 SST | SA: 降低 10-20% | 不影响 WA/RA | 空间敏感 |

#### 优化策略详细说明

**策略 1: Compression**

```
配置:
compression = kLZ4Compression  (快速压缩)
compression = kZSTDCompression  (高压缩比)

效果:
- LZ4: SA 降低 30-40%, WA 增加 5-10%
- ZSTD: SA 降低 50-60%, WA 增加 15-20%

代价:
- WA 增加: 压缩/解压开销
- RA 增加: 解压延迟
```

---

## 五、性能建模完整流程

### 5.1 性能建模方法论

```
Step 1: 建立基线 → 测量当前 Amplification
Step 2: 分解来源 → 分析每个 Amp 的来源
Step 3: 理论分析 → 计算理论 Amp 值
Step 4: 对比差异 → 分析实测 vs 理论差异
Step 5: 优化策略 → 制定优化方案
Step 6: Benchmark → 验证优化效果
Step 7: 权衡分析 → 评估对其他 Amp 影响
Step 8: 文档记录 → ADR + 性能报告
```

### 5.2 性能建模文档结构

```markdown
# [项目名] - 性能建模分析报告

## 1. Amplification 基线测量

### 1.1 Write Amplification
| 测试场景 | 实测 WA | 理论 WA | 差异 | 差异原因 |
|----------|---------|---------|------|----------|
| 场景A | 35 | 70 | -50% | [优化策略] |

### 1.2 Read Amplification
[同上]

### 1.3 Space Amplification
[同上]

## 2. Amplification 来源分解

### 2.1 WA 来源
| 来源 | WA 贡献 | 占比 | 优化方法 |
|------|---------|------|----------|
| WAL | 1.0 | 3% | 异步 WAL |

### 2.2 RA 来源
[同上]

### 2.3 SA 来源
[同上]

## 3. 优化策略分析

### 3.1 WA 优化策略
| 策略 | WA 降低 | RA 影响 | SA 影响 | 推荐度 |
|------|---------|---------|---------|--------|
| Tiered | 降低70% | ↑300% | ↑50% | ⭐⭐⭐ |

### 3.2 RA 优化策略
[同上]

### 3.3 SA 优化策略
[同上]

## 4. 场景化推荐配置

### 4.1 写密集场景
| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| compaction_style | kTiered | 降低 WA |

### 4.2 读密集场景
[同上]

### 4.3 空间敏感场景
[同上]

## 5. Benchmark 测试结果

### 5.1 Amplification 测试
| 场景 | WA | RA | SA | QPS | P99延迟 |
|------|----|----|----|-----|---------|
| 写密集 | 3 | 30 | 2.5 | 50K | 10ms |

### 5.2 对比测试
| 系统 | WA | RA | SA | 差异分析 |
|------|----|----|----|----------|
| 本系统 | 35 | 3.5 | 1.15 | - |
| RocksDB | 40 | 2 | 1.1 | [对比分析] |

## 6. ADR 记录

### ADR-001: Compaction 策略选择
[权衡考量]

## 7. 参考文献
[相关论文 + 文档]
```

---

## 六、Benchmark 测试方法

### 6.1 Amplification 测试

**测试脚本示例**:
```bash
# 测试 Write Amplification
# 1. 清空数据库
rocksdb --destroy_db

# 2. 写入 1GB 数据
rocksdb --put=1GB

# 3. 统计写入量
wal_size=$(du -b WAL/ | cut -f1)
sst_size=$(du -b SST/ | cut -f1)
total_writes=$((wal_size + sst_size))

# 4. 计算 WA
WA=$((total_writes / 1073741824))  # 1GB = 1073741824 bytes

echo "Write Amplification: $WA"
```

### 6.2 性能测试

**测试指标**:
- QPS (每秒操作数)
- P50/P99/P999 延迟
- CPU/内存/磁盘占用
- IOPS
- 吞吐量

**测试工具**:
- RocksDB: `db_bench`
- MySQL: `sysbench`
- PostgreSQL: `pgbench`
- Generic: `fio`, `iostat`

---

## 七、参考文献

### Amplification 相关论文

- **LSM Tree**: The Log-Structured Merge-Tree (LSM-Tree), O'Neil et al., 1996
- **WiscKey**: Separating Keys from Values in SSD-conscious Storage, FAST 2016
- **Pebble**: 设计文档, CockroachDB Blog
- **RocksDB Tuning**: RocksDB Tuning Guide, Facebook Wiki

### Amplification 分析文章

- [Understanding Write Amplification in RocksDB](https://...
- [LSM Tree Amplification Analysis](https://...
- [Compaction Strategies Comparison](https://...

---

## 八、💡 设计洞察（从性能建模中提炼的可移植原则）

> **说明**: 基于 Amplification 分析，提炼出超越具体实现的性能设计原则。

### 8.1 性能权衡原则

**原则1**: 性能优化是三角权衡，不存在银弹

- **原理**: Write/Read/Space Amplification 三者相互制约，优化一个往往会恶化另一个
- **证据**: Leveled Compaction 降低 RA（读放大）但增加 WA（写放大）；Tiered Compaction 降低 WA 但增加 RA
- **适用范围**: 任何存储/数据库/缓存系统
- **去名检验**: ✅ 通用原则（适用于所有需要权衡的系统）

**原则2**: 性能测试应该测量放大因子，而非只看端到端延迟

- **原理**: 端到端延迟受硬件影响，放大因子是算法层面的特性，跨硬件可比
- **证据**: RocksDB 分别测试 WA/RA/SA，而非只测 QPS 和延迟
- **适用范围**: 任何需要性能对标的系统
- **去名检验**: ✅ 通用原则

### 8.2 场景化设计原则

**原则1**: 没有"最优"配置，只有"最适合场景"的配置

- **原理**: 不同场景的负载特征不同，最优配置也不同
- **证据**: 写密集场景用 Tiered Compaction，读密集场景用 Leveled Compaction
- **适用范围**: 任何可配置系统
- **去名检验**: ✅ 通用原则

## 9. ⚠️ 隐含陷阱（性能建模中的非显而易见问题）

> **说明**: 从性能分析中发现的隐性假设和潜在陷阱。

### 9.1 测量陷阱

**陷阱1**: 放大因子测量需要区分"用户视角"和"系统视角"

- **现象**: 测量的 WA 值与论文/文档不符
- **原因**: 没有明确"用户写入量"的定义（是逻辑写入量还是物理写入量？）
- **正确做法**: 明确定义用户视角的基准线，区分逻辑写入和物理写入
- **检测方法**: 对比不同测量工具的结果，检查定义是否一致

### 9.2 优化陷阱

**陷阱1**: 优化单个放大因子可能导致整体性能下降

- **现象**: 优化了 WA，但 QPS 反而下降
- **原因**: 优化 WA 的策略（如增加 compaction）可能增加了 RA 或 SA，导致整体性能下降
- **正确做法**: 优化前评估对其他放大因子的影响，进行整体权衡
- **检测方法**: 优化前后同时测量所有三个放大因子

### 9.3 配置陷阱

**陷阱1**: 默认配置通常不是最优配置

- **现象**: 使用默认配置，性能远低于预期
- **原因**: 默认配置通常是"通用"配置，不是针对特定场景优化的
- **正确做法**: 根据场景特征（读/写/空间敏感度）调整配置
- **检测方法**: 对比默认配置和场景化配置的性能差异

---

*最后更新: 2026-06-29*
*参考: RocksDB Wiki + LSM Tree 论文*
*版本: v2.0 - 增加设计洞察与隐含陷阱章节*