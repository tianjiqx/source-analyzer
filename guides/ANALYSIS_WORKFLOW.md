# 源码分析工作流指南

> **设计目标**: 提供系统化的源码分析流程，确保分析全面、深入、可重复。

---

# 源码分析工作流指南

> **设计目标**: 提供系统化的源码分析流程，确保分析全面、深入、可重复。

---

## 自动化流程（推荐，快速开始）

```bash
# Step 0: 下载项目（如尚未下载，项目统一放 $WORKSPACE/opensource/）
gh repo clone <owner>/<repo> -- --depth=1
cd $WORKSPACE/opensource

# Step 1: 智能分析（自动检测项目类型 + 推荐模板；必须传 --model 记录当前模型名）
python3 $SKILL_DIR/scripts/smart-analyze.py /path/to/project \
  --model "$(cat $WORKSPACE/.current-model 2>/dev/null || echo 'unknown')" \
  -o $OUTPUT_BASE/project-name

# Step 2: 生成研究计划
python3 $SKILL_DIR/scripts/generate-research-plan.py /path/to/project \
  --depth file-level --max-files 30 \
  -o $OUTPUT_BASE/project-name/RESEARCH_PLAN.md

# Step 3: 按 RESEARCH_PLAN.md 派发执行（[DISPATCH] 六段式，见 SKILL.md）
# Step 4: 验证结果
python3 $SKILL_DIR/scripts/verify-analysis.py $OUTPUT_BASE/project-name --all
```

> 递归深度分析（大型项目）自动流程见 [RECURSIVE_DEEP_ANALYSIS.md](RECURSIVE_DEEP_ANALYSIS.md) 的"并行执行策略"节。

---

## 分析流程概览

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: 快速扫描 (5-10 分钟)                              │
│  ├── README 分析                                            │
│  ├── 目录结构分析                                            │
│  ├── 依赖分析                                                │
│  └── 项目健康度评估                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: 架构理解 (15-30 分钟)                             │
│  ├── 寻找入口点                                              │
│  ├── 理解模块划分                                            │
│  ├── 数据流追踪                                              │
│  └── 配置和环境分析                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: 深度分析 (按需)                                    │
│  ├── 关键算法分析                                            │
│  ├── 设计模式识别                                            │
│  ├── 性能分析                                                │
│  └── 测试分析                                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 4: 质量评估 (按需)                                    │
│  ├── 静态分析 (hefesto-ai)                                   │
│  ├── 质量评分计算                                            │
│  ├── 架构模式识别                                            │
│  └── 技术债务识别                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: 快速扫描

### 1.1 README 分析

**关注点**:
- **What**: 一句话概括项目做什么
- **Why**: 解决了什么问题
- **How**: 核心思路/架构
- **Quick Start**: 如何运行
- **License**: 许可协议

### 1.2 目录结构分析

```bash
# 排除常见噪音
tree -L 2 --dirsfirst -I 'node_modules|dist|.git|__pycache__|venv|.venv' project/
```

**关键识别**:
- `src/` / `lib/` — 核心源码
- `cmd/` / `bin/` — 可执行入口
- `config/` / `conf/` — 配置文件
- `test/` / `tests/` / `spec/` — 测试代码
- `docs/` — 文档
- `scripts/` / `tools/` — 辅助脚本

### 1.3 依赖分析

| 语言 | 文件 | 获取信息 |
|------|------|---------|
| Python | `requirements.txt`, `pyproject.toml` | 库版本、框架 |
| Node.js | `package.json`, `pnpm-lock.yaml` | 依赖、scripts |
| Go | `go.mod`, `go.sum` | 模块、版本 |
| Java | `pom.xml`, `build.gradle` | 依赖、插件 |
| Rust | `Cargo.toml` | crate、特性 |
| C# | `*.csproj`, `*.sln` | 依赖、框架 |

### 1.4 项目健康度

```bash
# Git 活跃度
git log --oneline --since="3 months ago" | wc -l

# 贡献者数量
git log --format='%aN' | sort -u | wc -l

# Issue 状态 (用 gh cli)
gh issue list --state open --limit 5
```

---

## Phase 2: 架构理解

### 2.1 寻找入口点

**Python**:
```bash
# 找 main 函数
rg "if __name__.*==.*__main__|def main\(" --type py

# 找 CLI 入口 (pyproject.toml)
rg "console_scripts|entry_points" pyproject.toml

# 找 FastAPI/Flask 路由
rg "@app\.route|@router\." --type py
```

**Node.js/TypeScript**:
```bash
# 找入口 (package.json)
node -e "console.log(require('./package.json').main || 'index.js')"

# 找 Express/Koa 路由
rg "app\.(get|post|put|delete)|router\.(get|post)" --type ts

# 找 Next.js 路由
fd --type f --glob "page.tsx|page.ts|route.ts|route.tsx" src/
```

**Go**:
```bash
# 找 main 函数
rg "func main\(" --type go

# 找 HTTP handler
rg "http\.HandleFunc|mux\.Handle|router\.GET" --type go
```

**Java**:
```bash
# 找 Spring Boot 入口
rg "@SpringBootApplication|public static void main" --type java

# 找 REST 控制器
rg "@RestController|@RequestMapping|@GetMapping" --type java
```

**C#**:
```bash
# 找 Program.cs 或 Startup.cs
rg "class Program|class Startup" --type cs

# 找 ASP.NET Core 控制器
rg "Controller|HttpGet|HttpPost" --type cs
```

### 2.2 理解模块划分

```bash
# 统计各目录文件数
find src/ -type d -exec sh -c 'echo "$(find "$1" -maxdepth 1 -type f | wc -l) $1"' _ {} \; | sort -rn | head -20
```

### 2.3 数据流追踪

从入口点出发，追踪请求/数据的处理流程：

1. **接收** — 路由定义、参数解析
2. **处理** — 业务逻辑、服务调用
3. **存储** — 数据库操作、缓存
4. **返回** — 响应格式、错误处理

**记录关键函数调用链**。

### 2.4 配置和环境

```bash
# 找配置文件
fd --type f --glob "*.yaml|*.yml|*.json|*.toml|*.env*" .

# 找环境变量引用
rg "os\.environ|process\.env|os\.Getenv|System\.getenv|ENV" --type py --type ts --type go --type java
```

---

## Phase 3: 深度分析（按需）

### 3.1 关键算法

- 定位算法所在文件
- 理解输入/输出
- 分析时间/空间复杂度
- 对比业界方案

### 3.2 设计模式识别

**常见模式**:
- **工厂模式** — 对象创建
- **策略模式** — 算法可替换
- **观察者模式** — 事件通知
- **中间件/管道** — 请求处理链
- **依赖注入** — 解耦

### 3.3 性能分析

**关注点**:
- 数据库查询（N+1 问题）
- 缓存策略
- 并发模型（线程池、协程、事件循环）
- 内存使用
- 网络 I/O

### 3.4 测试分析

```bash
# 测试覆盖率
# Python: pytest --cov
# Node.js: npx vitest --coverage / npx jest --coverage
# Go: go test -cover ./...

# 测试结构
find tests/ test/ -type f -name "*.py" -o -name "*.ts" -o -name "*.go" | head -20
```

**评估**:
- 单元测试覆盖率
- 集成测试范围
- 测试策略（mock vs 真实依赖）

---

## Phase 4: 质量评估（按需）

### 4.1 静态分析（hefesto-ai）

```bash
# 安装
pip install hefesto-ai

# 基础扫描
hefesto analyze /path/to/project --severity HIGH

# 结构化输出（便于解析）
hefesto analyze /path/to/project --output json > /tmp/audit.json

# HTML 报告
hefesto analyze /path/to/project --output html --save-html /tmp/report.html

# CI 模式（HIGH 及以上级别失败）
hefesto analyze /path/to/project --fail-on HIGH
```

**检测范围**:
- 安全漏洞: SQL 注入、命令注入、硬编码密钥、路径穿越
- 代码质量: 圈复杂度 >10、深度嵌套 >4、函数 >50 行
- DevOps: Dockerfile 最佳实践、Shell 脚本安全
- 语义漂移: AI 生成代码的架构降级、隐藏重复

**支持语言**: Python, TypeScript, JavaScript, Java, Go, Rust, C# + DevOps 配置

### 4.2 质量评分计算

根据 SKILL.md 中的评分体系，逐项打分：

```python
# 自动化评分辅助脚本
scores = {
    "code_structure": 16,  # /20 - 模块划分清晰度
    "code_quality": 14,    # /20 - hefesto 报告反推
    "security": 18,        # /20 - hefesto 安全扫描
    "test_coverage": 12,   # /15 - 测试文件占比
    "documentation": 10,   # /15 - README + 文档完整度
    "community": 8,        # /10 - git 活跃度
}
total = sum(scores.values())  # 78/100 -> B 等级
```

### 4.3 架构模式识别

检测项目采用的架构风格：

```bash
# 检查分层
for d in domain application infrastructure presentation; do
  [ -d "$d" ] && echo "✅ $d" || true
done

# 检查 DDD 模式
rg "AggregateRoot|DomainService|Repository|ValueObject|DomainEvent" --type java --type go --type py

# 检查设计模式
rg "Factory|Strategy|Observer|Decorator|Builder|Singleton" --type java --type go --type py
```

详见 [references/ddd-patterns.md](../references/ddd-patterns.md)

### 4.4 技术债务识别

```bash
# 高变更文件（风险热点）
git log --oneline --name-only | sort | uniq -c | sort -nr | head -20

# TODO/FIXME/HACK 注释
rg "TODO|FIXME|HACK|XXX|WORKAROUND" --type py --type ts --type go --type java

# 长文件（>500 行）
find . -name "*.py" -o -name "*.ts" -o -name "*.java" -o -name "*.go" \
  | xargs wc -l 2>/dev/null | awk '$1 > 500' | sort -rn | head -10

# 大提交（架构变更）
git log --stat --oneline --since="1 year ago" | grep -E "^ [0-9]+ files changed" | head -10
```

---

## 总结模板

```markdown
# [项目名称] 分析报告

## 概览
| 项目 | 信息 |
|------|------|
| 简介 | 一句话描述 |
| 语言 | 主语言 |
| Stars | xxx |
| License | xxx |

## 架构
- 模块 A: 负责 XX
- 模块 B: 负责 XX
- 模块 C: 负责 XX

## 技术栈
- 框架: XX
- 数据库: XX
- 中间件: XX

## 核心流程
1. 请求进入 → XX
2. 处理逻辑 → XX
3. 结果返回 → XX

## 亮点
- ...

## 不足
- ...

## 适用场景
- ...
```

---

## 相关文档

- [FILE_LEVEL_ANALYSIS.md](FILE_LEVEL_ANALYSIS.md) - 文件粒度深度分析模板
- [DETAILED_RESEARCH_PLAN.md](DETAILED_RESEARCH_PLAN.md) - 详细研究计划模板
- [PROBLEM_DRIVEN_ANALYSIS.md](PROBLEM_DRIVEN_ANALYSIS.md) - 问题驱动分析方法
- [DIAGRAM_GENERATION_GUIDE.md](DIAGRAM_GENERATION_GUIDE.md) - 图表生成规范
- [references/ddd-patterns.md](../references/ddd-patterns.md) - DDD 模式识别
- [references/lang-tools.md](../references/lang-tools.md) - 语言专用工具

---

*最后更新: 2026-06-27*
