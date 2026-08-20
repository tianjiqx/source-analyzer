#!/usr/bin/env python3
"""
递归深度分析编排器 v2 - 计划驱动执行

生成的 PLAN.md 包含:
1. 结构化任务清单（### Task N: name [status: pending] 格式）
2. 每个任务的预期输出文件清单
3. 分批并行策略
4. [DISPATCH] 指令（含计划引用和报告要求）

用法:
    python3 recursive-orchestrator.py <output-dir> --manifest module-manifest.json --project-path /path/to/project
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime


def load_manifest(manifest_path: Path) -> dict:
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def module_slug(name: str) -> str:
    """
    将模块名转换为目录路径（保持层级结构）
    
    例如:
        apps/app/src/app -> apps/app/src/app (保持目录结构)
        packages/core -> packages/core
    
    只替换空格和点号，保留斜杠作为目录分隔符
    """
    # 保留 / 作为目录分隔符，只替换空格和点号
    return name.replace(' ', '-').replace('.', '-')


def get_expected_files(module: dict, output_dir: str) -> list:
    """根据模块策略生成预期文件清单"""
    name = module['name']
    slug = module_slug(name)
    strategy = module['analysis_strategy']
    base = f"{output_dir}/10-module-deep/{slug}"
    
    files = [
        f"{base}/INDEX.md",
        f"{base}/00-overview/README.md",
        f"{base}/00-overview/architecture.md",
        f"{base}/00-overview/quality-score.md",
        f"{base}/00-overview/learning-value.md",
    ]
    
    if strategy in ('full_three_layers', 'full_with_submodule_recursion'):
        files.append(f"{base}/10-submodule/ (子模块分析)")
        files.append(f"{base}/20-file-level/ (5-10 关键文件)")
    elif strategy == 'layer1_plus_key_files':
        files.append(f"{base}/20-file-level/ (3-5 关键文件)")
    
    return files


def generate_spawn_task(module: dict, task_id: int, output_dir: str, project_path: str) -> tuple:
    """生成计划驱动的分析任务描述（环境无关）"""
    
    name = module['name']
    path = module['path']
    files = module.get('total_files', module.get('files', 0))
    lines = module.get('total_lines', module.get('lines', 0))
    size = module['size_category']
    strategy = module['analysis_strategy']
    importance = module.get('importance', 'medium')
    slug = module_slug(name)
    
    expected = get_expected_files(module, output_dir)
    expected_str = '\n'.join(f"  - {f}" for f in expected)
    
    if strategy == 'layer1_only':
        layers_desc = "Layer 1 (4 文档)"
    elif strategy == 'layer1_plus_key_files':
        layers_desc = "Layer 1 (4 文档) + Layer 3 (3-5 关键文件)"
    elif strategy == 'full_three_layers':
        layers_desc = "Layer 1 (4 文档) + Layer 2 (子模块) + Layer 3 (5-10 关键文件)"
    else:
        layers_desc = "Layer 1 (4 文档) + Layer 2 (子模块递归) + Layer 3 (10-20 关键文件)"
    
    # 统计预期文件数
    est = len(expected)
    
    task = f"""[计划驱动执行] PLAN.md Task #{task_id}

你正在执行递归深度分析计划中的一个模块任务。
全局计划文件: {output_dir}/PLAN.md
你的任务编号: #{task_id}
模块名称: {name}

=== 模块信息 ===
- 路径: {project_path}/{path}
- 文件数: {files} (含子目录)
- 行数: {lines:,}
- 规模: {size}
- 重要性: {importance}
- 分析策略: {strategy}
- 分析深度: {layers_desc}

=== 预期输出 ===
输出目录: {output_dir}/10-module-deep/{slug}/

必须生成:
{expected_str}

=== 分析维度 ===
- 模块职责与定位（在项目中的角色）
- 核心数据结构
- 关键算法/逻辑
- 接口设计（对外暴露的 API）
- 依赖关系（上下游模块）
- 设计模式
- 质量评分
- 学习价值（可移植的设计模式/架构经验）

每个文档至少包含 1 个 Mermaid 图表。

=== 必备蒸馏章节（每个分析文档末尾必须有）===
1. `## 💡 设计洞察`：至少 2 条可移植原则，每条含【原理】【证据(file:line)】【去名检验】
2. `## ⚠️ 隐含陷阱`：至少 2 条非显而易见陷阱，每条含【现象】【原因】【正确做法】
这是质量验证的强制项，缺失会扣分。格式见 guides/FILE_LEVEL_ANALYSIS.md 第十二节。

=== 完成报告 ===
分析完成后，在输出目录生成 .task-report.json:
{{
  "module": "{name}",
  "task_id": {task_id},
  "status": "completed",
  "files_generated": ["INDEX.md", "00-overview/README.md", ...],
  "files_count": {est},
  "quality_self_score": 85,
  "key_findings": ["发现1", "发现2"],
  "design_patterns": ["策略模式", ...],
  "issues": [],
  "mermaid_diagrams": 3
}}

参考模板:
- guides/FILE_LEVEL_ANALYSIS.md
- templates/general/
"""
    return task, est


def generate_plan(manifest, output_dir, project_path, max_parallel, priority_only):
    modules = manifest['modules']
    
    if priority_only:
        modules = [m for m in modules if m.get('importance') == 'high']
    
    importance_order = {'high': 0, 'medium': 1, 'low': 2}
    modules.sort(key=lambda m: (
        importance_order.get(m.get('importance', 'medium'), 1),
        -m.get('total_lines', m.get('lines', 0)),
    ))
    
    batches = [modules[i:i+max_parallel] for i in range(0, len(modules), max_parallel)]
    
    # 统计
    total_est = 0
    for m in modules:
        _, est = generate_spawn_task(m, 0, output_dir, project_path)
        total_est += est
    
    dist = {
        'high': sum(1 for m in modules if m.get('importance') == 'high'),
        'medium': sum(1 for m in modules if m.get('importance') == 'medium'),
        'low': sum(1 for m in modules if m.get('importance') == 'low'),
    }
    
    size_counts = {'large': 0, 'medium': 0, 'small': 0}
    for m in modules:
        sc = m.get('size_category', 'small')
        size_counts[sc] = size_counts.get(sc, 0) + 1
    
    priority_suffix = " (仅 high 重要性)" if priority_only else ""
    
    # ─── 生成 PLAN.md ───
    
    plan = f"""# 递归深度分析计划 (PLAN.md)

> **这是执行的契约。** 执行中随时对照，执行后逐项检查。

## 元信息

- 项目: {manifest['project']}
- 计划版本: 1.0
- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
- 模块清单: module-manifest.json
- 项目路径: {project_path}
- 输出目录: {output_dir}

## 计划摘要

| 指标 | 值 |
|------|-----|
| 分析模块数 | {len(modules)}{priority_suffix} |
| 并行批次 | {len(batches)} 批 × {max_parallel} 并行 |
| 预计文档 | ~{total_est} |
| 总文件 | {manifest['total_files']:,} |
| 总行数 | {manifest['total_lines']:,} |

### 重要性分布
- 🔴 High: {dist['high']}
- 🟡 Medium: {dist['medium']}
- 🟢 Low: {dist['low']}

---

## Phase 1: 项目级分析 (串行)

### Task 1: 项目级分析 [status: pending]

- 输出目录: `{output_dir}/00-project-level/`
- 预期文件:
  - {output_dir}/00-project-level/README.md
  - {output_dir}/00-project-level/architecture.md
  - {output_dir}/00-project-level/quality-score.md
  - {output_dir}/00-project-level/learning-value.md
- 完成条件: 4 个文件全部存在，无 placeholder

```
[DISPATCH: task="项目级分析: 概览、架构、质量评分、学习价值" label="project-level"]
```

---

## Phase 2: 模块级递归分析 (分批并行)

共 {len(modules)} 个模块，分为 {len(batches)} 批。
模块按重要性排序：high 优先分析。

"""

    task_id = 2  # Task 1 是项目级
    
    for batch_idx, batch in enumerate(batches):
        plan += f"### 批次 {batch_idx + 1} / {len(batches)}\n\n"
        
        for module in batch:
            task_desc, est = generate_spawn_task(module, task_id, output_dir, project_path)
            label = f"module-{module_slug(module['name'])}"
            expected = get_expected_files(module, output_dir)
            expected_list = '\n'.join(f"  - {f}" for f in expected)
            
            plan += f"""#### Task {task_id}: {module['name']} [status: pending]

- 模块: {module['name']}
- 路径: {module['path']}
- 策略: {module['analysis_strategy']}
- 规模: {module['size_category']} ({module.get('total_files', '?')} 文件)
- 重要性: {module.get('importance', 'medium')}
- 预期文件:
{expected_list}
- 完成条件: INDEX.md 存在 + Layer 1 完整 + 按策略完成对应深度

```
[DISPATCH: task=\"\"\"{task_desc}\"\"\" label=\"{label}\"]
```

"""
            task_id += 1
        
        if batch_idx < len(batches) - 1:
            plan += f"```\n[WAIT: \"等待批次 {batch_idx + 1} 完成\"]\n```\n\n---\n\n"
    
    plan += f"""---

## Phase 3: 项目级总结 (串行)

### Task {task_id}: 跨模块总结 [status: pending]

- 输出目录: `{output_dir}/10-module-deep/` + `{output_dir}/20-cross-module/`
- 预期文件:
  - {output_dir}/10-module-deep/_MODULE_SUMMARY.md
  - {output_dir}/20-cross-module/comparison.md
  - {output_dir}/20-cross-module/patterns.md
  - {output_dir}/20-cross-module/recommendations.md
  - {output_dir}/20-cross-module/dependency-graph.md
- 完成条件: 5 个文件全部存在

```
[DISPATCH: task="整合所有模块分析，生成跨模块报告" label="project-summary"]
```

---

## 执行流程

1. 初始化检查点: `python3 scripts/plan-tracker.py init --plan PLAN.md --manifest module-manifest.json --output-dir .`
2. 执行 Phase 1 → 更新检查点
3. 执行 Phase 2（分批）→ 每批后同步检查点
4. 执行 Phase 3 → 更新检查点
5. 计划验收: `python3 scripts/plan-tracker.py verify --plan PLAN.md --checkpoint .checkpoint.json --output-dir .`
6. 标准验证: `python3 scripts/verify-analysis.py . --recursive`
"""

    return plan


def main():
    parser = argparse.ArgumentParser(
        description='递归深度分析编排器 v2 - 计划驱动执行',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('output_dir', type=Path, help='分析输出目录')
    parser.add_argument('--manifest', type=Path, required=True, help='模块清单 JSON 文件')
    parser.add_argument('--project-path', type=str, required=True, help='项目源码路径')
    parser.add_argument('-o', '--output', type=Path, help='输出计划文件路径 (默认: <output-dir>/PLAN.md)')
    parser.add_argument('--max-parallel', type=int, default=8, help='最大并行子代理数（默认: 8）')
    parser.add_argument('--priority-only', action='store_true', help='只生成 high 重要性模块的任务')
    
    args = parser.parse_args()
    
    if not args.manifest.exists():
        print(f"❌ 清单文件不存在: {args.manifest}", file=sys.stderr)
        sys.exit(1)
    
    manifest = load_manifest(args.manifest)
    
    plan = generate_plan(
        manifest,
        str(args.output_dir),
        args.project_path,
        args.max_parallel,
        args.priority_only,
    )
    
    output_path = args.output or (args.output_dir / 'PLAN.md')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(plan)
    print(f"✅ 计划已生成: {output_path}")
    
    # 摘要
    modules = manifest['modules']
    if args.priority_only:
        modules = [m for m in modules if m.get('importance') == 'high']
    batch_count = (len(modules) + args.max_parallel - 1) // args.max_parallel
    
    print(f"\n📊 计划摘要:")
    print(f"   分析模块: {len(modules)}" + (" (仅 high)" if args.priority_only else ""))
    print(f"   并行批次: {batch_count} 批 × {args.max_parallel}")
    print(f"\n📋 下一步:")
    print(f"   1. python3 scripts/plan-tracker.py init --plan {output_path} --manifest {args.manifest} --output-dir {args.output_dir}")
    print(f"   2. 按 PLAN.md 执行 [DISPATCH] 指令")
    print(f"   3. python3 scripts/plan-tracker.py sync --checkpoint {args.output_dir}/.checkpoint.json --output-dir {args.output_dir}")
    print(f"   4. python3 scripts/plan-tracker.py verify --plan {output_path} --checkpoint {args.output_dir}/.checkpoint.json --output-dir {args.output_dir}")


if __name__ == '__main__':
    main()
