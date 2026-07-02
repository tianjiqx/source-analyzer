#!/bin/bash
# detect-visualization.sh - 检测项目中的可视化支持
# 用法: ./detect-visualization.sh /path/to/project

set -e

PROJECT_DIR="$1"

if [ -z "$PROJECT_DIR" ]; then
    echo "❌ 请提供项目路径"
    echo "用法: $0 /path/to/project"
    exit 1
fi

if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ 目录不存在: $PROJECT_DIR"
    exit 1
fi

echo "🔍 检测可视化支持: $(basename "$PROJECT_DIR")"
echo "================================================"

FOUND=0

# 检测 Mermaid
if grep -r "mermaid" "$PROJECT_DIR" --include="*.tsx" --include="*.ts" --include="*.jsx" --include="*.js" -q 2>/dev/null; then
    echo "✅ Mermaid 支持"
    echo "   相关文件:"
    grep -r "mermaid" "$PROJECT_DIR" --include="*.tsx" --include="*.ts" --include="*.jsx" --include="*.js" -l 2>/dev/null | head -5 | sed 's/^/     - /'
    FOUND=1
fi

# 检测 MindMap
if grep -r "mindmap\|MindMap\|mind_map" "$PROJECT_DIR" --include="*.cs" --include="*.py" --include="*.ts" --include="*.tsx" -q 2>/dev/null; then
    echo "✅ MindMap 支持"
    echo "   相关文件:"
    grep -r "mindmap\|MindMap\|mind_map" "$PROJECT_DIR" --include="*.cs" --include="*.py" --include="*.ts" --include="*.tsx" -l 2>/dev/null | head -5 | sed 's/^/     - /'
    FOUND=1
fi

# 检测 Graphify
if grep -r "graphify\|Graphify" "$PROJECT_DIR" --include="*.cs" --include="*.py" --include="*.ts" --include="*.tsx" -q 2>/dev/null; then
    echo "✅ Graphify 支持"
    echo "   相关文件:"
    grep -r "graphify\|Graphify" "$PROJECT_DIR" --include="*.cs" --include="*.py" --include="*.ts" --include="*.tsx" -l 2>/dev/null | head -5 | sed 's/^/     - /'
    FOUND=1
fi

# 检测 PlantUML
if grep -r "plantuml\|PlantUML\|@startuml" "$PROJECT_DIR" -q 2>/dev/null; then
    echo "✅ PlantUML 支持"
    FOUND=1
fi

# 检测 D2
if grep -r "d2 lang\|D2 Lang\|\.d2$" "$PROJECT_DIR" -q 2>/dev/null; then
    echo "✅ D2 Lang 支持"
    FOUND=1
fi

# 检测 Excalidraw
if grep -r "excalidraw\|Excalidraw" "$PROJECT_DIR" -q 2>/dev/null; then
    echo "✅ Excalidraw 支持"
    FOUND=1
fi

# 检测图表生成 Prompt
if grep -r "diagram.*prompt\|chart.*prompt\|mindmap.*prompt" "$PROJECT_DIR" --include="*.md" -q 2>/dev/null; then
    echo "✅ 图表生成 Prompt"
    echo "   相关文件:"
    grep -r "diagram.*prompt\|chart.*prompt\|mindmap.*prompt" "$PROJECT_DIR" --include="*.md" -l 2>/dev/null | head -3 | sed 's/^/     - /'
    FOUND=1
fi

echo "================================================"
if [ $FOUND -eq 0 ]; then
    echo "⚠️  未检测到可视化支持"
else
    echo "💡 建议使用 VISUALIZATION_DIAGRAMS.md 模板进行深度分析"
fi
