#!/usr/bin/env python3
"""
Generate Analysis Plan

自动生成项目分析计划文件。

Usage:
    python3 generate-analysis-plan.py /path/to/project [--output-dir /path/to/output]

输出:
    - 分析计划文件 (ANALYSIS_PLAN.md)
    - 包含详细的任务定义、步骤、输入/输出文件
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime


def detect_build_system(project_path: Path) -> str:
    """检测构建系统"""
    if (project_path / "pom.xml").exists():
        return "maven"
    elif (project_path / "build.gradle").exists():
        return "gradle"
    elif (project_path / "package.json").exists():
        return "npm"
    elif (project_path / "Cargo.toml").exists():
        return "cargo"
    elif (project_path / "go.mod").exists():
        return "go"
    elif (project_path / "requirements.txt").exists():
        return "pip"
    elif (project_path / "setup.py").exists():
        return "pip"
    return "unknown"


def detect_main_language(project_path: Path) -> str:
    """检测主要语言"""
    counts = {}
    for ext, lang in {
        ".java": "Java",
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".go": "Go",
        ".rs": "Rust",
        ".cpp": "C++",
        ".c": "C",
        ".kt": "Kotlin",
        ".scala": "Scala",
    }.items():
        count = len(list(project_path.rglob(f"*{ext}")))
        if count > 0:
            counts[lang] = count
    
    if not counts:
        return "unknown"
    return max(counts.items(), key=lambda x: x[1])[0]


def count_files(project_path: Path) -> dict:
    """统计代码文件"""
    counts = {}
    for ext, lang in {
        ".java": "Java",
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".go": "Go",
        ".rs": "Rust",
        ".cpp": "C++",
        ".c": "C",
    }.items():
        count = len(list(project_path.rglob(f"*{ext}")))
        if count > 0:
            counts[lang] = count
    return counts


def find_entry_points(project_path: Path, build_system: str) -> list:
    """查找入口点"""
    entry_points = []
    
    if build_system == "gradle" or build_system == "maven":
        for pattern in ["*Application.java", "*Main.java", "*Bootstrap.java", "*Server.java"]:
            for f in project_path.rglob(pattern):
                if ".git" not in str(f) and "test" not in str(f).lower():
                    entry_points.append(str(f.relative_to(project_path)))
    elif build_system == "npm":
        if (project_path / "package.json").exists():
            entry_points.append("package.json (main field)")
    elif build_system == "python":
        for f in project_path.rglob("*.py"):
            if f.name == "__main__.py" or "main" in f.name.lower():
                entry_points.append(str(f.relative_to(project_path)))
    
    return entry_points[:10]  # Limit to top 10


def get_module_structure(project_path: Path) -> list:
    """获取模块结构"""
    modules = []
    for d in project_path.iterdir():
        if d.is_dir() and not d.name.startswith("."):
            modules.append(d.name)
    return sorted(modules)


def generate_analysis_plan(project_path: str, output_dir: str) -> str:
    """生成分析计划"""
    project = Path(project_path)
    output = Path(output_dir)
    
    # 检测项目信息
    build_system = detect_build_system(project)
    main_lang = detect_main_language(project)
    file_counts = count_files(project)
    entry_points = find_entry_points(project, build_system)
    modules = get_module_structure(project)
    
    # 生成计划文件
    plan_file = output / "ANALYSIS_PLAN.md"
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 构建任务列表
    tasks = []
    
    # Task 1: Overview
    tasks.append("""### Task 1: Analyze Project Overview

**Priority**: P0
**Output**: `00-README.md`
**Estimated Time**: 10-15 minutes

**Input Files**:
- `README.md` (lines 1-100)
""")
    
    if build_system == "gradle":
        tasks.append("- `settings.gradle` (modules list)")
        tasks.append("- `build.gradle` (dependencies, plugins)")
    elif build_system == "maven":
        tasks.append("- `pom.xml` (dependencies, modules)")
    elif build_system == "npm":
        tasks.append("- `package.json` (dependencies, scripts)")
    
    tasks.append("")
    tasks.append("**Steps**:")
    tasks.append("")
    tasks.append("- [ ] **Step 1: Extract basic info**")
    tasks.append("  - Read: `README.md` (first 100 lines)")
    tasks.append("  - Extract: project name, description, license, tech stack")
    tasks.append("  - Write to: Project Info Table")
    tasks.append("")
    tasks.append("- [ ] **Step 2: Analyze build system**")
    tasks.append(f"  - Read: {get_build_file(build_system, project)}")
    tasks.append("  - Extract: dependencies, modules, version")
    tasks.append("  - Write to: Build System Section")
    tasks.append("")
    tasks.append("- [ ] **Step 3: Count code statistics**")
    for lang, count in file_counts.items():
        tasks.append(f"  - Count {lang} files: {count}")
    tasks.append("")
    tasks.append("- [ ] **Step 4: Write overview document**")
    tasks.append("  - Write: `00-README.md` with:")
    tasks.append("    - Project Info Table (name, description, license, stars)")
    tasks.append("    - Tech Stack Table (languages, frameworks, tools)")
    tasks.append("    - Quick Start Steps")
    tasks.append("")
    tasks.append("- [ ] **Step 5: Verify output**")
    tasks.append("  - Check: file exists, has basic info table, no placeholders")
    tasks.append("")
    
    # Task 2: Architecture
    tasks.append("""### Task 2: Analyze Architecture

**Priority**: P0
**Output**: `01-architecture.md`
**Estimated Time**: 20-30 minutes

**Input Files**:
- Directory structure (`tree -L 2`)
- Entry points
""")
    
    for ep in entry_points[:5]:
        tasks.append(f"- `{ep}`")
    
    tasks.append("")
    tasks.append("**Steps**:")
    tasks.append("")
    tasks.append("- [ ] **Step 1: Map module structure**")
    tasks.append("  - Run: `tree -L 2 -I '.git|target|node_modules'`")
    tasks.append("  - Extract: top-level modules, their purposes")
    tasks.append("")
    tasks.append("- [ ] **Step 2: Identify entry points**")
    for ep in entry_points[:3]:
        tasks.append(f"  - Read: `{ep}`")
        tasks.append("    - Extract: startup chain, initialization flow")
    tasks.append("")
    tasks.append("- [ ] **Step 3: Map core services**")
    tasks.append("  - Read: entry point file")
    tasks.append("  - Extract: service initialization order, dependencies")
    tasks.append("")
    tasks.append("- [ ] **Step 4: Analyze data flow**")
    tasks.append("  - Trace: request → processing → storage → response")
    tasks.append("  - Draw: data flow diagram (text format)")
    tasks.append("")
    tasks.append("- [ ] **Step 5: Write architecture document**")
    tasks.append("  - Write: `01-architecture.md` with:")
    tasks.append("    - Module Diagram (tree structure)")
    tasks.append("    - Entry Points Table")
    tasks.append("    - Data Flow Diagram")
    tasks.append("")
    tasks.append("- [ ] **Step 6: Verify output**")
    tasks.append("  - Check: has module table, data flow, no placeholders")
    tasks.append("")
    
    # Task 3: Core Code
    tasks.append("""### Task 3: Analyze Core Code

**Priority**: P0
**Output**: `02-core-code.md`
**Estimated Time**: 30-45 minutes

**Input Files**:
- Key classes identified in architecture
""")
    
    tasks.append("")
    tasks.append("**Steps**:")
    tasks.append("")
    tasks.append("- [ ] **Step 1: Identify top 15 classes**")
    tasks.append("  - Run: find largest files by line count")
    tasks.append("  - Filter: exclude test, generated, vendor files")
    tasks.append("  - Extract: file name, size, module, purpose")
    tasks.append("")
    tasks.append("- [ ] **Step 2: Analyze entry class")
    if entry_points:
        tasks.append(f"  - Read: `{entry_points[0]}`")
    tasks.append("  - Extract: initialization flow, key dependencies")
    tasks.append("")
    tasks.append("- [ ] **Step 3: Analyze core service classes")
    tasks.append("  - Read: 5-10 core service classes")
    tasks.append("  - Extract: core methods, data structures, algorithms")
    tasks.append("")
    tasks.append("- [ ] **Step 4: Identify design patterns**")
    tasks.append("  - Analyze: plugin pattern, factory pattern, strategy pattern, etc.")
    tasks.append("  - Document: where used, why used, benefits")
    tasks.append("")
    tasks.append("- [ ] **Step 5: Write core code document**")
    tasks.append("  - Write: `02-core-code.md` with:")
    tasks.append("    - Key Classes Table (name, module, purpose, line count)")
    tasks.append("    - Design Patterns Table (pattern, location, description)")
    tasks.append("    - Code Snippets (at least 3 examples)")
    tasks.append("")
    tasks.append("- [ ] **Step 6: Verify output**")
    tasks.append("  - Check: has class table, code examples, no placeholders")
    tasks.append("")
    
    # Task 4: Quality
    tasks.append("""### Task 4: Evaluate Quality

**Priority**: P1
**Output**: `03-quality-score.md`
**Estimated Time**: 20-30 minutes

**Steps**:""")
    tasks.append("")
    tasks.append("- [ ] **Step 1: Check code structure**")
    tasks.append("  - Analyze: module cohesion, dependency graph")
    tasks.append("  - Check: circular dependencies, tight coupling")
    tasks.append("")
    tasks.append("- [ ] **Step 2: Run static analysis")
    tasks.append("  - Check: code complexity (large files, long methods)")
    tasks.append("  - Check: code smells (duplication, god classes)")
    tasks.append("")
    tasks.append("- [ ] **Step 3: Check security issues**")
    tasks.append("  - Run: search for hardcoded passwords/secrets")
    tasks.append("  - Check: SQL injection, XSS risks")
    tasks.append("")
    tasks.append("- [ ] **Step 4: Check test coverage**")
    tasks.append("  - Count: test files vs source files")
    tasks.append("  - Estimate: coverage percentage")
    tasks.append("")
    tasks.append("- [ ] **Step 5: Calculate quality score**")
    tasks.append("  - Apply: 6-dimension scoring system")
    tasks.append("  - Score: structure, quality, security, tests, docs, community")
    tasks.append("")
    tasks.append("- [ ] **Step 6: Write quality document**")
    tasks.append("  - Write: `03-quality-score.md` with:")
    tasks.append("    - Score Table (6 dimensions, weighted)")
    tasks.append("    - Security Issues List")
    tasks.append("    - Improvement Suggestions")
    tasks.append("")
    tasks.append("- [ ] **Step 7: Verify output**")
    tasks.append("  - Check: has score table, suggestions, no placeholders")
    tasks.append("")
    
    # Task 5: Learning Value
    tasks.append("""### Task 5: Summarize Learning Value

**Priority**: P1
**Output**: `04-learning-value.md`
**Estimated Time**: 15-20 minutes

**Steps**:""")
    tasks.append("")
    tasks.append("- [ ] **Step 1: Extract design highlights**")
    tasks.append("  - From: architecture + core code docs")
    tasks.append("  - Extract: notable patterns, clever solutions")
    tasks.append("")
    tasks.append("- [ ] **Step 2: Identify applicable scenarios**")
    tasks.append("  - Analyze: where can these patterns be applied")
    tasks.append("")
    tasks.append("- [ ] **Step 3: Compare with similar projects**")
    tasks.append("  - Compare: vs similar projects in same domain")
    tasks.append("")
    tasks.append("- [ ] **Step 4: Write learning value document**")
    tasks.append("  - Write: `04-learning-value.md` with:")
    tasks.append("    - Design Highlights Table (pattern, rating, why)")
    tasks.append("    - Applicable Scenarios")
    tasks.append("    - Target Audience")
    tasks.append("    - Recommendation (1-5 stars)")
    tasks.append("")
    tasks.append("- [ ] **Step 5: Verify output**")
    tasks.append("  - Check: has ratings, target audience, no placeholders")
    tasks.append("")
    
    # Task 6: Index
    tasks.append("""### Task 6: Generate Index

**Priority**: P0
**Output**: `INDEX.md`
**Estimated Time**: 10 minutes

**Steps**:""")
    tasks.append("")
    tasks.append("- [ ] **Step 1: Create navigation table**")
    tasks.append("  - From: all document titles + summaries")
    tasks.append("")
    tasks.append("- [ ] **Step 2: Extract key metrics**")
    tasks.append("  - From: quality score + overview")
    tasks.append("")
    tasks.append("- [ ] **Step 3: Write index document**")
    tasks.append("  - Write: `INDEX.md` with:")
    tasks.append("    - Quick Navigation Table")
    tasks.append("    - Key Info Summary")
    tasks.append("    - Reading Recommendations")
    tasks.append("")
    tasks.append("- [ ] **Step 4: Verify output**")
    tasks.append("  - Check: has links to all docs, key info")
    tasks.append("")
    
    # Write plan file
    total_tasks = 6
    
    content = f"""# Analysis Plan: {project.name}

> **For agentic workers:** Use source-analyzer:analysis-driven-execution

**Project Path**: `{project_path}`
**Output Directory**: `{output_dir}`
**Build System**: {build_system}
**Main Language**: {main_lang}
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## Project Overview

| Attribute | Value |
|-----------|-------|
| **Name** | {project.name} |
| **Build System** | {build_system} |
| **Main Language** | {main_lang} |
| **Total Modules** | {len(modules)} |
| **Entry Points** | {len(entry_points)} |

### File Statistics

| Language | Count |
|----------|-------|
"""
    
    for lang, count in file_counts.items():
        content += f"| {lang} | {count} |\n"
    
    content += f"""
### Modules

{chr(10).join([f"- {m}" for m in modules[:20]])}

### Entry Points

{chr(10).join([f"- `{ep}`" for ep in entry_points[:10]])}

---

## Analysis Tasks

**Total Tasks**: {total_tasks}
**Estimated Time**: {sum([15, 30, 45, 30, 20, 10])} minutes (~2.5 hours)

"""
    
    content += "\n\n".join(tasks)
    
    content += f"""
---

## Execution Notes

1. **Order**: Tasks 1-6 should be executed in order
2. **Parallel**: Tasks 2-5 can be partially parallelized after Task 1
3. **Dependencies**: Task 6 depends on all previous tasks
4. **Review**: Each task requires two-stage review (completeness + quality)
"""
    
    plan_file.write_text(content)
    return str(plan_file)


def get_build_file(build_system: str, project_path: Path) -> str:
    """获取构建文件路径"""
    if build_system == "gradle":
        return "build.gradle"
    elif build_system == "maven":
        return "pom.xml"
    elif build_system == "npm":
        return "package.json"
    return "unknown"


def main():
    parser = argparse.ArgumentParser(description="Generate analysis plan for a project")
    parser.add_argument("project_path", help="Path to the project to analyze")
    parser.add_argument("--output-dir", "-o", default=None, help="Output directory for analysis plan")
    
    args = parser.parse_args()
    
    project_path = args.project_path
    project_name = os.path.basename(os.path.normpath(project_path))
    
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = os.path.expanduser(f"~/.openclaw/learning/projects/{project_name}-analysis")
    
    # 验证项目路径
    if not os.path.exists(project_path):
        print(f"Error: Project path not found: {project_path}")
        sys.exit(1)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成计划
    plan_file = generate_analysis_plan(project_path, output_dir)
    
    print(f"✓ Analysis plan generated: {plan_file}")
    print(f"  Output directory: {output_dir}")
    
    return plan_file


if __name__ == "__main__":
    main()