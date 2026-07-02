#!/usr/bin/env bash
# quick-scan.sh — 快速扫描开源项目结构
# 用法: bash quick-scan.sh /path/to/project

set -euo pipefail

PROJECT_DIR="${1:-.}"

if [ ! -d "$PROJECT_DIR" ]; then
  echo "❌ 目录不存在: $PROJECT_DIR"
  exit 1
fi

echo "═══════════════════════════════════════════════════════"
echo "  📊 项目扫描: $(basename "$PROJECT_DIR")"
echo "  📍 路径: $PROJECT_DIR"
echo "═══════════════════════════════════════════════════════"

# 1. 目录结构 (排除噪音)
echo ""
echo "📁 目录结构 (前2层):"
echo "───────────────────────────────────────────────────────"
EXCLUDES="node_modules|dist|build|.git|__pycache__|venv|.venv|target|vendor|.next|.nuxt"
if command -v tree &>/dev/null; then
  tree -L 2 --dirsfirst -I "$EXCLUDES" "$PROJECT_DIR" 2>/dev/null | head -50
else
  find "$PROJECT_DIR" -maxdepth 2 -type d \
    | grep -vE "/($EXCLUDES)" \
    | sed "s|$PROJECT_DIR|.|" \
    | sort \
    | head -30
fi

# 2. 代码统计
echo ""
echo "📈 代码统计:"
echo "───────────────────────────────────────────────────────"
if command -v cloc &>/dev/null; then
  cloc "$PROJECT_DIR" --exclude-dir=$(echo $EXCLUDES | tr '|' ',') 2>/dev/null | tail -10
else
  echo "  ⚠️  cloc 未安装，跳过代码统计"
fi

# 3. 语言检测 (从依赖文件判断)
echo ""
echo "🔧 技术栈检测:"
echo "───────────────────────────────────────────────────────"
[ -f "$PROJECT_DIR/package.json" ] && echo "  🟢 Node.js/TypeScript (package.json)"
[ -f "$PROJECT_DIR/requirements.txt" ] && echo "  🟢 Python (requirements.txt)"
[ -f "$PROJECT_DIR/pyproject.toml" ] && echo "  🟢 Python (pyproject.toml)"
[ -f "$PROJECT_DIR/go.mod" ] && echo "  🟢 Go (go.mod)"
[ -f "$PROJECT_DIR/pom.xml" ] && echo "  🟢 Java/Maven (pom.xml)"
[ -f "$PROJECT_DIR/build.gradle" ] && echo "  🟢 Java/Gradle (build.gradle)"
[ -f "$PROJECT_DIR/build.gradle.kts" ] && echo "  🟢 Java/Gradle KTS (build.gradle.kts)"
[ -f "$PROJECT_DIR/Cargo.toml" ] && echo "  🟢 Rust (Cargo.toml)"
[ -f "$PROJECT_DIR/Cargo.lock" ] && echo "  🟢 Rust (Cargo.lock)"
[ -f "$PROJECT_DIR/Makefile" ] && echo "  🟢 Make (Makefile)"
[ -f "$PROJECT_DIR/CMakeLists.txt" ] && echo "  🟢 C/C++ (CMakeLists.txt)"
[ -f "$PROJECT_DIR/Dockerfile" ] && echo "  🐳 Docker (Dockerfile)"
[ -f "$PROJECT_DIR/docker-compose.yml" ] && echo "  🐳 Docker Compose"
[ -f "$PROJECT_DIR/docker-compose.yaml" ] && echo "  🐳 Docker Compose"
[ -f "$PROJECT_DIR/.github/workflows" ] && echo "  🔄 GitHub Actions"

# 4. 入口点检测
echo ""
echo "🚪 入口点检测:"
echo "───────────────────────────────────────────────────────"
if [ -f "$PROJECT_DIR/package.json" ]; then
  MAIN=$(node -e "try{console.log(require('$PROJECT_DIR/package.json').main||'index.js')}catch(e){}" 2>/dev/null)
  echo "  📄 Node.js 入口: ${MAIN:-index.js}"
fi
[ -f "$PROJECT_DIR/src/main.py" ] && echo "  📄 Python 入口: src/main.py"
[ -f "$PROJECT_DIR/main.py" ] && echo "  📄 Python 入口: main.py"
[ -f "$PROJECT_DIR/app.py" ] && echo "  📄 Python 入口: app.py"
[ -d "$PROJECT_DIR/cmd" ] && echo "  📄 Go 入口: cmd/"
[ -f "$PROJECT_DIR/src/main.rs" ] && echo "  📄 Rust 入口: src/main.rs"

# 5. 测试覆盖
echo ""
echo "🧪 测试目录:"
echo "───────────────────────────────────────────────────────"
for test_dir in tests test spec __tests__ src/__tests__; do
  if [ -d "$PROJECT_DIR/$test_dir" ]; then
    COUNT=$(find "$PROJECT_DIR/$test_dir" -type f \( -name "*.py" -o -name "*.ts" -o -name "*.js" -o -name "*.go" -o -name "*.rs" \) 2>/dev/null | wc -l)
    echo "  📂 $test_dir/ ($COUNT 个测试文件)"
  fi
done

# 6. Git 信息
echo ""
echo "📝 Git 信息:"
echo "───────────────────────────────────────────────────────"
if git -C "$PROJECT_DIR" rev-parse --git-dir &>/dev/null; then
  echo "  📊 总提交: $(git -C "$PROJECT_DIR" log --oneline | wc -l | tr -d ' ')"
  echo "  👥 贡献者: $(git -C "$PROJECT_DIR" log --format='%aN' | sort -u | wc -l | tr -d ' ')"
  echo "  📅 最后提交: $(git -C "$PROJECT_DIR" log -1 --format='%ci' | cut -d' ' -f1)"
  echo "  🏷️  标签: $(git -C "$PROJECT_DIR" tag | wc -l | tr -d ' ')"
else
  echo "  ⚠️  不是 git 仓库"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✅ 扫描完成"
echo "═══════════════════════════════════════════════════════"
