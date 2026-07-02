# 语言专用工具

## Python

### 代码分析
```bash
# AST 分析
pip install astor
python -c "import ast; print(ast.dump(ast.parse(open('file.py').read())))"

# 类型检查
pip install pyright
pyright .

# 复杂度分析
pip install radon
radon cc src/ -a  # 圈复杂度
radon mi src/     # 可维护性指数

# 依赖图
pip install pydeps
pydeps src/ --max-bacon=2

# 导入分析
pip install isort
isort --check-only --diff src/
```

### 项目结构扫描
```bash
# 代码统计
cloc . --exclude-dir=node_modules,dist,.git,__pycache__,.venv

# 找所有类定义
rg "^class " --type py

# 找所有函数定义
rg "^def " --type py

# 找装饰器
rg "^@" --type py
```

---

## Node.js / TypeScript

### 代码分析
```bash
# 依赖图
npx madge --image graph.svg src/

# 类型检查
npx tsc --noEmit

# 循环依赖检测
npx madge --circular src/

# 复杂度分析
npx eslint --ext .ts,.tsx src/ --format codeframe

# Bundle 分析
npx webpack --profile --json > stats.json
npx webpack-bundle-analyzer stats.json
```

### 项目结构扫描
```bash
# 找导出
rg "export (default |const |function |class |interface |type )" --type ts

# 找路由定义
rg "app\.(get|post|put|delete|use)|router\.(get|post|put|delete)" --type ts

# 找 API handler
rg "export const .*Handler|export async function .*" --type ts
```

---

## Go

### 代码分析
```bash
# 依赖图
go mod graph

# 代码统计
cloc . --exclude-dir=.git,vendor

# 复杂度
go install github.com/fzipp/gocyclo/cmd/gocyclo@latest
gocyclo -top 20 .

# 测试覆盖
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out

# 竞态检测
go test -race ./...

# 静态分析
go vet ./...
staticcheck ./...
```

### 项目结构扫描
```bash
# 找 main 包
rg "^package main" --type go

# 找 HTTP handler
rg "http\.HandlerFunc|mux\.HandleFunc" --type go

# 找接口定义
rg "^type .* interface" --type go

# 找结构体
rg "^type .* struct" --type go
```

---

## Java

### 代码分析
```bash
# 依赖分析
mvn dependency:tree
# 或
gradle dependencies

# 代码统计
cloc . --exclude-dir=.git,target,build

# 复杂度 (SonarQube)
# 或使用 maven-pmd-plugin
mvn pmd:check

# 测试覆盖
mvn test jacoco:report
```

### 项目结构扫描
```bash
# 找入口
rg "@SpringBootApplication|public static void main" --type java

# 找 REST 控制器
rg "@RestController|@RequestMapping" --type java

# 找服务层
rg "@Service|@Component" --type java

# 找数据访问层
rg "@Repository|extends JpaRepository" --type java

# 找配置类
rg "@Configuration|@Bean" --type java
```

---

## Rust

### 代码分析
```bash
# 依赖图
cargo tree

# 编译检查
cargo check

# 测试
cargo test

# 复杂度
cargo install cargo-geiger
cargo geiger

# 安全审计
cargo audit

# Clippy (代码质量)
cargo clippy
```

### 项目结构扫描
```bash
# 找公开函数/结构体
rg "^pub (fn |struct |enum |trait |type )" --type rust

# 找宏
rg "^macro_rules!" --type rust

# 找 impl 块
rg "^impl " --type rust
```

---

## 通用工具

### 代码搜索
```bash
# ripgrep (最快)
rg "pattern" .

# 忽略常见目录
rg "pattern" --ignore-dir node_modules --ignore-dir dist --ignore-dir .git

# 多模式搜索
rg "(pattern1|pattern2)" .

# 查找定义
rg "(def |function |class |func |struct )\s+ClassName" .
```

### 文件查找
```bash
# fd (比 find 快)
fd --type f --glob "*.ts" src/
fd --type d src/

# 按大小查找
fd --type f --size +1M .
```

### Git 分析
```bash
# 提交频率
git log --oneline --format="%ad" --date=short | sort | uniq -c

# 贡献者
git shortlog -sn --all

# 文件修改历史
git log --follow --oneline -- path/to/file

# 代码作者 (blame 统计)
git ls-files | xargs -I{} git blame --line-porcelain {} | grep "^author " | sort | uniq -c | sort -rn
```

### 架构可视化
```bash
# Python 依赖图
pip install pydeps && pydeps src/ --max-bacon=2

# JS 依赖图
npx madge --image graph.svg src/

# Go 调用图
go install github.com/kisielk/godepgraph@latest
godepgraph -s ./... | dot -Tpng -o deps.png

# 通用 (基于 import)
# 用 LLM 分析 import 关系生成架构图
```

---

## 工具可用性检查

使用前检查工具是否安装：
```bash
command -v rg && echo "ripgrep OK" || echo "ripgrep 未安装"
command -v cloc && echo "cloc OK" || echo "cloc 未安装"
command -v fd && echo "fd OK" || echo "fd 未安装"
command -v tree && echo "tree OK" || echo "tree 未安装"
```

未安装时安装：
```bash
# macOS
brew install ripgrep cloc fd tree

# Ubuntu/Debian
sudo apt install ripgrep cloc fd-find tree

# 或者通过 cargo
cargo install ripgrep fd-find
```

---

*最后更新: 2026-06-27*
