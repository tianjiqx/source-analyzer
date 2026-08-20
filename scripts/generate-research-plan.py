#!/usr/bin/env python3
"""
自动生成详细研究计划

功能:
- 预研究阶段（扫描项目）
- 识别模块和入口点
- 生成关键文件列表
- 创建详细任务分解
- 生成 Todo 任务结构
- 输出研究计划文档

用法:
    python3 generate-research-plan.py /path/to/project \
        --depth file-level \
        --max-files 30 \
        -o $OUTPUT_BASE/project-name/RESEARCH_PLAN.md
"""

import os
import sys
import argparse
import subprocess
import json
from pathlib import Path
from datetime import datetime
from collections import Counter

# 导入 generate-file-list 功能
import importlib.util
_script_dir = os.path.dirname(__file__)

def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_script_dir, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_gfl = _load_module('generate_file_list', 'generate-file-list.py')
detect_language = _gfl.detect_language
scan_project_files = _gfl.scan_project_files
get_file_priority = _gfl.get_file_priority
count_file_lines = _gfl.count_file_lines
ENTRY_PATTERNS = _gfl.ENTRY_PATTERNS
SERVICE_PATTERNS = _gfl.SERVICE_PATTERNS

def pre_research_scan(project_path):
    """预研究阶段：探索性扫描"""
    results = {}
    
    # 1. 目录结构扫描
    print("  [Step 0.1] 目录结构扫描...")
    try:
        result = subprocess.run(
            ['tree', '-L', '2', '-I', 'target|.git|node_modules|vendor', project_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        results['directory_structure'] = result.stdout if result.returncode == 0 else "tree 命令不可用"
    except:
        results['directory_structure'] = "无法获取目录结构"
    
    # 2. 语言统计
    print("  [Step 0.2] 语言统计...")
    language, lang_count = detect_language(project_path)
    results['language'] = language
    results['file_count'] = lang_count
    
    # 代码行数统计
    try:
        result = subprocess.run(
            ['cloc', project_path, '--by-lang', '--json'],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            cloc_data = json.loads(result.stdout)
            results['cloc'] = cloc_data
        else:
            results['cloc'] = "cloc 命令不可用"
    except:
        results['cloc'] = "无法获取代码统计"
    
    # 3. 入口点识别
    print("  [Step 0.3] 入口点识别...")
    entry_files = []
    # 扩展入口模式：支持多语言
    EXTRA_ENTRY_PATTERNS = [
        '__main__', 'main', 'cli', 'manage', 'setup', 'wsgi', 'asgi',
        'index', 'server', 'bootstrap', 'entry', 'launcher', '__init__',
    ]
    all_patterns = ENTRY_PATTERNS + EXTRA_ENTRY_PATTERNS
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in ['.git', 'target', 'build', 'node_modules', 'vendor', '__pycache__']]
        for file in files:
            fname_no_ext = os.path.splitext(file)[0]
            for pattern in all_patterns:
                if pattern.lower() == fname_no_ext.lower() or pattern.lower() in file.lower():
                    entry_files.append(os.path.relpath(os.path.join(root, file), project_path))
                    break
    
    # 检测项目级入口配置（pyproject.toml / setup.py / package.json）
    project_root_files = []
    for f in ['pyproject.toml', 'setup.py', 'setup.cfg', 'package.json', 'Cargo.toml', 'go.mod']:
        if os.path.exists(os.path.join(project_path, f)):
            project_root_files.append(f)
    results['project_config_files'] = project_root_files
    
    # 只保留顶层入口文件 + 包级 __init__.py（最多 10 个）
    # 优先显示顶层入口，然后是包级 __init__.py
    top_entries = [f for f in entry_files if os.sep not in f]
    pkg_inits = [f for f in entry_files if f.endswith('__init__.py') and f.count(os.sep) == 1]
    other_entries = [f for f in entry_files if f not in top_entries and f not in pkg_inits]
    entry_files = top_entries + pkg_inits + other_entries
    
    results['entry_files'] = entry_files[:10]  # 最多 10 个
    
    # 4. Git 历史扫描
    print("  [Step 0.4] Git 历史扫描...")
    try:
        # 先检测是否为浅克隆（depth=1 时 git log 只有 1 条 commit）
        rev_count = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD'],
            cwd=project_path, capture_output=True, text=True, timeout=10
        )
        total_commits = int(rev_count.stdout.strip()) if rev_count.returncode == 0 else 0
        results['total_commits'] = total_commits
        results['is_shallow'] = total_commits < 5
        
        # 使用 --format="" 只输出文件名，避免 commit 消息混入
        log_range = '--all' if total_commits < 5 else '-100'
        result = subprocess.run(
            ['git', 'log', '--format=', '--name-only', log_range],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            # 只统计非空行（--format= 确保不会有 commit 消息）
            file_counter = Counter(f for f in lines if f and not f.startswith('['))
            results['high_freq_files'] = [f for f, _ in file_counter.most_common(10)]
            
            # 提取主要贡献者
            result2 = subprocess.run(
                ['git', 'log', '--format=%aN', log_range],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result2.returncode == 0:
                authors = result2.stdout.strip().split('\n')
                author_counter = Counter(authors)
                results['top_authors'] = [a for a, _ in author_counter.most_common(5)]
        else:
            results['high_freq_files'] = []
            results['top_authors'] = []
    except:
        results['high_freq_files'] = []
        results['top_authors'] = []
        results['total_commits'] = 0
        results['is_shallow'] = True
    
    # 5. 文档扫描
    print("  [Step 0.5] 文档扫描...")
    doc_files = []
    for file in os.listdir(project_path):
        if file.endswith('.md') or file.startswith('README'):
            doc_files.append(file)
    
    results['doc_files'] = doc_files
    
    return results

def identify_modules(project_path, directory_structure):
    """识别项目模块"""
    modules = []
    
    # 从目录结构推断模块
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in ['.git', 'target', 'build', 'node_modules', 'vendor', 'test', 'tests']]
        
        # 跳过顶层目录
        if root == project_path:
            continue
        
        # 只处理一级目录作为模块
        rel_path = os.path.relpath(root, project_path)
        if os.sep not in rel_path:
            module_name = rel_path
            
            # 统计模块文件数
            file_count = sum(1 for f in files if os.path.splitext(f)[1] in ['.java', '.py', '.go', '.js', '.ts', '.cpp', '.rs'])
            
            if file_count > 0:
                modules.append({
                    'name': module_name,
                    'path': rel_path,
                    'file_count': file_count,
                })
    
    # 按文件数排序
    modules.sort(key=lambda x: -x['file_count'])
    
    return modules[:10]  # 最多 10 个模块

def estimate_analysis_time(file_count, module_count, depth):
    """估算分析时间"""
    base_time = 10  # 项目级基础时间（分钟）
    
    if depth == 'project-level':
        return base_time
    elif depth == 'module-level':
        return base_time + module_count * 10
    elif depth == 'file-level':
        return base_time + module_count * 10 + file_count * 5
    
    return base_time

def generate_todo_structure(project_name, depth, modules, files_info):
    """生成 Todo 任务结构"""
    lines = []
    lines.append("## 任务管理集成\n\n")
    lines.append("### 创建 Todo 项目\n\n")
    lines.append("```bash\n")
    lines.append(f"# 创建主项目\n")
    lines.append(f"todo add \"[{project_name}] 深度源码分析\" \\")
    lines.append(f"  --priority P0 \\")
    lines.append(f"  --description \"三层深度分析\" \\")
    lines.append(f"  --due YYYY-MM-DD\n\n")
    
    lines.append("# 创建阶段分组\n")
    lines.append("todo add \"Phase 1: 项目级分析\" --parent 1\n")
    
    if depth in ['module-level', 'file-level']:
        lines.append("todo add \"Phase 2: 模块级分析\" --parent 1\n")
    
    if depth == 'file-level':
        lines.append("todo add \"Phase 3: 文件粒度分析\" --parent 1\n")
    
    lines.append("todo add \"Phase 4: 质量评估总结\" --parent 1\n\n")
    
    lines.append("# 创建具体任务\n")
    lines.append("todo add \"Task 1: 项目概览分析\" --parent 2 --estimate 20\n")
    lines.append("todo add \"Task 2: 架构设计分析\" --parent 2 --estimate 30\n")
    
    if depth in ['module-level', 'file-level']:
        for i, module in enumerate(modules[:5], 3):
            lines.append(f"todo add \"Task {i}: {module['name']} 模块分析\" --parent 3 --estimate 15\n")
    
    if depth == 'file-level':
        file_task_start = 3 + len(modules[:5])
        for i, file_info in enumerate(files_info[:10], file_task_start):
            lines.append(f"todo add \"Task {i}: {file_info['file']} 分析\" --parent 4 --estimate 10\n")
    
    lines.append("```\n")
    
    return ''.join(lines)

def generate_research_plan_markdown(project_path, project_name, depth, max_files, pre_results, modules, files_info, vectors=None):
    """生成研究计划 Markdown"""
    lines = []
    
    # 标题
    lines.append(f"# {project_name} 详细研究计划\n\n")
    lines.append("> **For agentic workers:** Follow this plan step-by-step\n\n")
    
    # 基本信息
    lines.append(f"**研究目标**: 深度分析 {project_name} 源码架构 + 核心实现\n")
    lines.append(f"**项目路径**: `{project_path}`\n")
    lines.append(f"**技术栈**: {pre_results['language']}\n")
    lines.append(f"**输出目录**: `$OUTPUT_BASE/{project_name}/`\n")
    lines.append(f"**计划版本**: v1.0\n")
    
    estimated_time = estimate_analysis_time(len(files_info), len(modules), depth)
    lines.append(f"**预计时间**: {estimated_time} 分钟\n\n")
    
    # 基向量声明（如果提供）
    if vectors:
        lines.append("### 🎯 分析基向量\n\n")
        lines.append("本次分析关注以下方向（从这些视角提取可移植原则）：\n\n")
        for i, vector in enumerate(vectors, 1):
            lines.append(f"{i}. **{vector}**\n")
        lines.append("\n")
    
    lines.append("---\n\n")
    
    # 一、研究范围定义
    lines.append("## 一、研究范围定义\n\n")
    
    lines.append("### 1.1 分析维度\n\n")
    lines.append("| 维度 | 重要性 | 分析深度 | 输出文件 |\n")
    lines.append("|------|--------|----------|----------|\n")
    
    lines.append("| 项目概览 | P0 | Layer 1 | 00-project-level/README.md |\n")
    lines.append("| 项目依赖 | P0 | Layer 1 | 00-project-level/dependencies.md |\n")
    lines.append("| 架构设计 | P0 | Layer 1+2 | 00-project-level/architecture.md + 模块文档 |\n")
    
    if depth == 'file-level':
        lines.append("| 核心代码 | P0 | Layer 3 | 02-core-code.md + 文件分析 |\n")
    
    lines.append("| 质量评估 | P1 | Layer 1 | 00-project-level/quality-score.md |\n")
    lines.append("| 学习价值 | P1 | Layer 1 | 00-project-level/learning-value.md |\n\n")
    
    lines.append("### 1.2 分析深度选择\n\n")
    lines.append(f"**已选择**: ")
    if depth == 'project-level':
        lines.append("[x] Layer 1 (项目级)\n")
    elif depth == 'module-level':
        lines.append("[x] Layer 1+2 (项目级 + 模块级)\n")
    else:
        lines.append("[x] Layer 1+2+3 (完整三层)\n")
    
    lines.append(f"**文件数量**: {len(files_info)} 个关键文件\n")
    lines.append(f"**模块数量**: {len(modules)} 个核心模块\n\n")
    
    lines.append("---\n\n")
    
    # 二、预研究结果
    lines.append("## 二、预研究结果（探索性扫描）\n\n")
    
    lines.append("### 2.1 目录结构\n\n")
    lines.append("```\n")
    lines.append(pre_results['directory_structure'][:500])  # 截取前 500 字符
    lines.append("\n```\n\n")
    
    lines.append("### 2.2 语言统计\n\n")
    lines.append(f"- **主语言**: {pre_results['language']}\n")
    lines.append(f"- **源码文件数**: {pre_results['file_count']}\n\n")
    
    lines.append("### 2.3 入口点列表\n\n")
    if pre_results['entry_files']:
        for f in pre_results['entry_files']:
            lines.append(f"- `{f}`\n")
    else:
        lines.append("- 未识别到明确入口点\n")
    
    # 显示项目配置文件（可能包含入口点定义）
    if pre_results.get('project_config_files'):
        lines.append(f"\n> 📦 项目配置: {', '.join(['`' + f + '`' for f in pre_results['project_config_files']])}（可能定义了 CLI/脚本入口）\n")
    
    lines.append("\n")
    
    is_shallow = pre_results.get('is_shallow', False)
    total_commits = pre_results.get('total_commits', 0)
    
    if is_shallow:
        lines.append(f"### 2.4 高频修改文件\n\n")
        lines.append(f"> ⚠️ 浅克隆（仅 {total_commits} 个 commit），Git 历史分析受限。如需完整分析，请运行 `git fetch --unshallow`\n\n")
        if pre_results['high_freq_files']:
            for f in pre_results['high_freq_files'][:5]:
                lines.append(f"- `{f}`\n")
        else:
            lines.append("- 无足够数据\n")
    else:
        lines.append(f"### 2.4 高频修改文件（最近 {min(total_commits, 100)} commits）\n\n")
        if pre_results['high_freq_files']:
            for f in pre_results['high_freq_files'][:5]:
                lines.append(f"- `{f}`\n")
        else:
            lines.append("- 无法获取 Git 历史\n")
    
    lines.append("\n")
    
    lines.append("### 2.5 主要贡献者\n\n")
    if pre_results.get('top_authors'):
        for a in pre_results['top_authors']:
            lines.append(f"- {a}\n")
    elif is_shallow:
        lines.append(f"- ⚠️ 浅克隆仅 {total_commits} 个 commit，贡献者信息不完整\n")
    else:
        lines.append("- 无法获取贡献者信息\n")
    
    lines.append("\n")
    
    lines.append("### 2.6 文档文件\n\n")
    if pre_results['doc_files']:
        for d in pre_results['doc_files']:
            lines.append(f"- `{d}`\n")
    else:
        lines.append("- 未发现文档文件\n")
    
    lines.append("\n---\n\n")
    
    # 三、详细任务分解
    lines.append("## 三、详细任务分解（分层任务）\n\n")
    
    # Phase 1: 项目级分析
    lines.append("### Phase 1: 项目级分析\n\n")
    
    lines.append("#### Task 1: 项目概览分析\n\n")
    lines.append("**目标**: 输出 `00-project-level/README.md`\n\n")
    lines.append("**输入文件**:\n")
    if pre_results['doc_files']:
        lines.append(f"- `{pre_results['doc_files'][0]}` (README)\n")
    else:
        lines.append("- README.md (如存在)\n")
    
    lines.append(f"- 构建文件 (pom.xml/build.gradle/package.json)\n")
    lines.append("- LICENSE\n\n")
    
    lines.append("**详细步骤**:\n\n")
    lines.append("- [ ] **Step 1.1**: 提取基本信息\n")
    lines.append("- [ ] **Step 1.2**: 提取构建信息\n")
    lines.append("- [ ] **Step 1.3**: 提取统计数据\n")
    lines.append("- [ ] **Step 1.4**: 提取核心特性\n")
    lines.append("- [ ] **Step 1.5**: 生成快速开始\n")
    lines.append("- [ ] **Step 1.6**: 写入文档\n")
    lines.append("- [ ] **Step 1.7**: 完整性验证\n\n")
    
    lines.append("#### Task 2: 架构设计分析\n\n")
    lines.append("**目标**: 输出 `00-project-level/architecture.md`\n\n")
    lines.append("**输入文件**:\n")
    lines.append(f"- 目录结构\n")
    if pre_results['entry_files']:
        lines.append(f"- `{pre_results['entry_files'][0]}` (入口点)\n")
    lines.append("- 主要配置文件\n\n")
    
    lines.append("**详细步骤**:\n\n")
    lines.append("- [ ] **Step 2.1**: 提取模块列表\n")
    lines.append("- [ ] **Step 2.2**: 分析启动链\n")
    lines.append("- [ ] **Step 2.3**: 分析数据流\n")
    lines.append("- [ ] **Step 2.4**: 分析配置系统\n")
    lines.append("- [ ] **Step 2.5**: 写入文档\n")
    lines.append("- [ ] **Step 2.6**: 完整性验证\n\n")
    
    lines.append("#### Task 2.5: 项目依赖分析 ⭐\n\n")
    lines.append("**目标**: 输出 `00-project-level/dependencies.md`\n")
    lines.append("**模板**: `templates/general/PROJECT_DEPENDENCY_ANALYSIS.md`\n\n")
    lines.append("**输入文件**:\n")
    lines.append("- package.json / requirements.txt / go.mod / Cargo.toml / pom.xml 等依赖声明文件\n")
    lines.append("- 锁定文件（package-lock.json / poetry.lock / go.sum 等）\n\n")
    lines.append("**详细步骤**:\n\n")
    lines.append("- [ ] **Step 1**: 扫描依赖声明文件，提取完整依赖清单\n")
    lines.append("- [ ] **Step 2**: 分类整理（核心框架 / 工具库 / 开发依赖）\n")
    lines.append("- [ ] **Step 3**: 对关键依赖调研 Stars / 活跃度 / 许可证\n")
    lines.append("- [ ] **Step 4**: 筛选「值得关注的优秀库」清单（⭐/⭐⭐/⭐⭐⭐）\n")
    lines.append("- [ ] **Step 5**: 检查依赖健康度（版本新鲜度 / 风险依赖）\n")
    lines.append("- [ ] **Step 6**: 生成依赖关系图（Mermaid）\n")
    lines.append("- [ ] **Step 7**: 写入文档\n\n")
    
    lines.append("---\n\n")
    
    # Phase 2: 模块级分析（如果需要）
    if depth in ['module-level', 'file-level']:
        lines.append("### Phase 2: 模块级分析\n\n")
        
        for i, module in enumerate(modules[:5], 4):
            lines.append(f"#### Task {i}: {module['name']} 模块分析\n\n")
            lines.append(f"**目标**: 输出 `10-module-level/{module['name']}/` (3 个文档)\n\n")
            lines.append(f"**输入文件**:\n")
            lines.append(f"- `{module['path']}/` 目录下核心文件\n\n")
            
            lines.append("**详细步骤**:\n\n")
            lines.append("- [ ] **Step 1**: 扫描模块文件\n")
            lines.append("- [ ] **Step 2**: 识别核心类\n")
            lines.append("- [ ] **Step 3**: 提取公开接口\n")
            lines.append("- [ ] **Step 4**: 分析依赖关系\n")
            lines.append("- [ ] **Step 5**: 写入模块文档\n")
            lines.append("- [ ] **Step 6**: 完整性验证\n\n")
        
        lines.append("---\n\n")
    
    # Phase 3: 文件粒度分析（如果需要）
    if depth == 'file-level':
        lines.append("### Phase 3: 文件粒度分析\n\n")
        
        file_task_start = 4 + len(modules[:5])
        
        for i, file_info in enumerate(files_info[:10], file_task_start):
            lines.append(f"#### Task {i}: {file_info['file']} 文件分析\n\n")
            lines.append(f"**目标**: 输出 `20-file-level/{file_info['file']}-analysis.md`\n\n")
            lines.append(f"**输入文件**:\n")
            lines.append(f"- `{file_info['path']}` ({file_info['lines']} 行)\n\n")
            
            lines.append("**分析维度**:\n\n")
            lines.append("- 文件职责与定位\n")
            lines.append("- 关键类/函数分析\n")
            lines.append("- 数据结构分析\n")
            lines.append("- 依赖关系分析\n")
            lines.append("- 设计模式识别\n")
            lines.append("- 代码质量评估\n")
            lines.append("- 测试覆盖分析\n")
            lines.append("- 改进建议\n\n")
            
            lines.append("**详细步骤**:\n\n")
            lines.append("- [ ] **Step 1**: 提取文件基本信息\n")
            lines.append("- [ ] **Step 2**: 分析文件职责\n")
            lines.append("- [ ] **Step 3**: 提取类/方法清单\n")
            lines.append("- [ ] **Step 4**: 分析核心方法\n")
            lines.append("- [ ] **Step 5**: 分析依赖关系\n")
            lines.append("- [ ] **Step 6**: 识别设计模式\n")
            lines.append("- [ ] **Step 7**: 评估代码质量\n")
            lines.append("- [ ] **Step 8**: 检查测试覆盖\n")
            lines.append("- [ ] **Step 9**: 生成改进建议\n")
            lines.append("- [ ] **Step 10**: 写入文档\n")
            lines.append("- [ ] **Step 11**: 完整性验证\n\n")
        
        lines.append("---\n\n")
    
    # Phase 4: 质量评估总结
    lines.append("### Phase 4: 质量评估总结\n\n")
    
    quality_task = 4 + len(modules[:5]) + len(files_info[:10]) if depth == 'file-level' else 4 + len(modules[:5]) if depth == 'module-level' else 4
    
    lines.append(f"#### Task {quality_task}: 项目质量评分\n\n")
    lines.append("**目标**: 输出 `00-project-level/quality-score.md`\n\n")
    lines.append("**输入**:\n")
    lines.append("- 所有文件级分析的质量评分\n")
    lines.append("- 静态分析结果\n\n")
    
    lines.append(f"#### Task {quality_task + 1}: 学习价值总结\n\n")
    lines.append("**目标**: 输出 `00-project-level/learning-value.md`\n\n")
    
    lines.append("---\n\n")
    
    # 四、任务管理集成
    lines.append(generate_todo_structure(project_name, depth, modules, files_info))
    
    lines.append("---\n\n")
    
    # 五、验证标准
    lines.append("## 五、验证标准\n\n")
    
    lines.append("### 5.1 完整性验证\n\n")
    lines.append("| 项目 | 验证方法 | 通过标准 |\n")
    lines.append("|------|----------|----------|\n")
    lines.append("| 文件存在 | `ls` 检查 | 所有输出文件存在 |\n")
    lines.append("| 章节完整 | `grep` 检查标题 | 包含所有必需章节 |\n")
    lines.append("| 内容具体 | 检查 placeholder | 无 TBD/TODO |\n\n")
    
    lines.append("### 5.2 质量验证\n\n")
    lines.append("| 项目 | 验证方法 | 通过标准 |\n")
    lines.append("|------|----------|----------|\n")
    lines.append("| 内容准确 | 类名检查 | 类名/方法名一致 |\n")
    lines.append("| 分析深度 | 代码示例检查 | 每个核心方法有示例 |\n")
    lines.append("| 结构清晰 | 架构图检查 | 有可视化图表 |\n\n")
    
    lines.append("---\n\n")
    
    # 六、异常处理
    lines.append("## 六、异常处理\n\n")
    
    lines.append("| 失败类型 | 处理策略 |\n")
    lines.append("|----------|----------|\n")
    lines.append("| 文件不存在 | 标记 SKIP，记录原因 |\n")
    lines.append("| 文件过大 | 分段分析，简化输出 |\n")
    lines.append("| 复杂度过高 | 降级为概览分析 |\n")
    lines.append("| 测试超时 | 记录部分结果 |\n\n")
    
    lines.append("---\n\n")
    
    # 结尾
    lines.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
    
    return ''.join(lines)

def main():
    parser = argparse.ArgumentParser(description='自动生成详细研究计划')
    parser.add_argument('project_path', help='项目路径')
    parser.add_argument('--depth', choices=['project-level', 'module-level', 'file-level'], 
                        default='file-level', help='分析深度')
    parser.add_argument('--max-files', type=int, default=30, help='最大文件数量')
    parser.add_argument('--vectors', type=str, help='分析基向量（逗号分隔，如：性能优先,可扩展性,安全性）')
    parser.add_argument('-o', '--output', required=True, help='输出文件路径')
    
    args = parser.parse_args()
    
    project_path = Path(args.project_path).resolve()
    if not project_path.exists():
        print(f"❌ 项目路径不存在: {project_path}")
        sys.exit(1)
    
    project_name = project_path.name
    
    print(f"🔍 生成详细研究计划: {project_name}")
    print(f"   路径: {project_path}")
    print(f"   分析深度: {args.depth}")
    
    # Step 1: 预研究扫描
    print("\n📊 Step 1: 预研究阶段...")
    pre_results = pre_research_scan(project_path)
    
    # Step 2: 识别模块
    print("\n🏗️  Step 2: 识别模块...")
    modules = identify_modules(project_path, pre_results['directory_structure'])
    print(f"   识别到 {len(modules)} 个模块")
    
    # Step 3: 识别关键文件
    print("\n📄 Step 3: 识别关键文件...")
    files_info, language = scan_project_files(project_path, args.max_files)
    print(f"   识别到 {len(files_info)} 个关键文件")
    
    # Step 4: 生成研究计划
    print("\n📝 Step 4: 生成研究计划...")
    
    # 解析基向量
    vectors = []
    if args.vectors:
        vectors = [v.strip() for v in args.vectors.split(',')]
        print(f"   分析基向量: {', '.join(vectors)}")
    
    markdown = generate_research_plan_markdown(
        project_path, project_name, args.depth, args.max_files,
        pre_results, modules, files_info, vectors
    )
    
    # 写入文件
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print(f"\n✅ 研究计划生成完成: {output_path}")
    
    # 同时生成文件列表
    file_list_path = output_path.parent / 'FILE_LIST.md'
    file_list_md = _gfl.generate_file_list_markdown(files_info, project_name, language)
    
    with open(file_list_path, 'w', encoding='utf-8') as f:
        f.write(file_list_md)
    
    print(f"   文件列表: {file_list_path}")
    
    # 输出摘要
    print("\n📊 项目摘要:")
    print(f"   主语言: {language}")
    print(f"   模块数: {len(modules)}")
    print(f"   关键文件: {len(files_info)}")
    print(f"   入口点: {len(pre_results['entry_files'])}")
    
    estimated_time = estimate_analysis_time(len(files_info), len(modules), args.depth)
    print(f"   预计时间: {estimated_time} 分钟")

if __name__ == '__main__':
    main()