#!/usr/bin/env python3
"""
计划追踪器 - 维护检查点、对比计划与实际输出、生成验收报告

用法:
    # 初始化检查点
    python3 plan-tracker.py init --plan PLAN.md --manifest module-manifest.json --output-dir .

    # 同步检查点（扫描已完成任务）
    python3 plan-tracker.py sync --checkpoint .checkpoint.json --output-dir .

    # 查看状态
    python3 plan-tracker.py status --checkpoint .checkpoint.json

    # 标记任务完成
    python3 plan-tracker.py complete --checkpoint .checkpoint.json --task phase_1_scan

    # 计划验收
    python3 plan-tracker.py verify --plan PLAN.md --checkpoint .checkpoint.json --output-dir .
"""

import json
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


def now_iso() -> str:
    return datetime.now().isoformat(timespec='seconds')


def load_json(path: Path) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ─── INIT ───────────────────────────────────────────────────────────────────

def parse_plan_tasks(plan_path: Path) -> List[dict]:
    """从 PLAN.md 中解析任务清单
    
    支持两种格式：
    1. `### Task N: name [status: xxx]` (recursive-orchestrator 格式)
    2. `- [ ] 任务描述` (smart-analyze 复选框格式)
    """
    content = plan_path.read_text(encoding='utf-8')
    tasks = []
    
    # 格式 1: 匹配 ### Task N: name [status: xxx]
    task_pattern = re.compile(
        r'###\s+Task\s+(\d+):\s+(.+?)\s+\[status:\s*(\w+)\]',
        re.IGNORECASE
    )
    
    for match in task_pattern.finditer(content):
        task_id = int(match.group(1))
        task_name = match.group(2).strip()
        status = match.group(3).strip().lower()
        
        # 提取该任务的预期文件（从任务标题到下一个 ### 之间）
        start = match.end()
        next_task = task_pattern.search(content, start)
        end = next_task.start() if next_task else len(content)
        task_section = content[start:end]
        
        # 查找预期文件
        expected_files = []
        for line in task_section.split('\n'):
            line = line.strip()
            if line.startswith('- ') and ('/' in line or '.md' in line):
                # 提取文件路径（去掉前导 "- " 和可能的注释）
                file_path = re.sub(r'^-\s+', '', line).split('  ')[0].strip()
                if file_path and not file_path.startswith('预期') and '.md' in file_path:
                    expected_files.append(file_path)
        
        tasks.append({
            'task_id': task_id,
            'name': task_name,
            'status': status,
            'expected_files': expected_files,
        })
    
    # 格式 2: 如果格式 1 没匹配到，尝试复选框格式
    if not tasks:
        checkbox_pattern = re.compile(r'^-\s+\[\s*\]\s+(.+)$', re.MULTILINE)
        task_id = 1
        for match in checkbox_pattern.finditer(content):
            task_desc = match.group(1).strip()
            # 提取预期文件（从描述中提取 .md 路径）
            expected_files = []
            file_match = re.search(r'`([^`]+\.md)`', task_desc)
            if file_match:
                expected_files.append(file_match.group(1))
            
            # 跳过纯阅读/分析步骤（没有明确输出文件的）
            if expected_files or '生成' in task_desc or '输出' in task_desc:
                tasks.append({
                    'task_id': task_id,
                    'name': task_desc[:60],  # 截断过长的描述
                    'status': 'pending',
                    'expected_files': expected_files,
                })
                task_id += 1
    
    return tasks


def cmd_init(args):
    """初始化检查点"""
    plan_path = Path(args.plan)
    manifest_path = Path(args.manifest)
    output_dir = Path(args.output_dir)
    checkpoint_path = output_dir / '.checkpoint.json'
    
    if not plan_path.exists():
        print(f"❌ 计划文件不存在: {plan_path}", file=sys.stderr)
        sys.exit(1)
    
    # 解析计划
    tasks = parse_plan_tasks(plan_path)
    
    # 加载清单
    manifest = load_json(manifest_path) if manifest_path.exists() else {}
    
    # 构建检查点
    checkpoint = {
        'plan_version': '1.0',
        'plan_path': str(plan_path.relative_to(output_dir)) if plan_path.is_relative_to(output_dir) else str(plan_path),
        'project': manifest.get('project', 'unknown'),
        'started_at': now_iso(),
        'last_updated': now_iso(),
        'total_tasks': len(tasks),
        'phases': {
            'phase_1_scan': {'status': 'pending', 'tasks': []},
            'phase_2_modules': {'status': 'pending', 'tasks': {}},
            'phase_3_summary': {'status': 'pending', 'tasks': []},
        },
        'tasks': {},
    }
    
    for task in tasks:
        task_key = f"task_{task['task_id']}"
        checkpoint['tasks'][task_key] = {
            'name': task['name'],
            'status': 'pending',
            'expected_files': task['expected_files'],
            'actual_files': [],
            'started_at': None,
            'completed_at': None,
        }
    
    save_json(checkpoint_path, checkpoint)
    print(f"✅ 检查点已初始化: {checkpoint_path}")
    print(f"   总任务数: {len(tasks)}")
    print(f"   预期文件数: {sum(len(t['expected_files']) for t in tasks)}")


# ─── SYNC ───────────────────────────────────────────────────────────────────

def find_task_reports(output_dir: Path) -> List[dict]:
    """扫描输出目录中的所有 .task-report.json"""
    reports = []
    for report_file in output_dir.rglob('.task-report.json'):
        try:
            report = load_json(report_file)
            report['_path'] = str(report_file.parent.relative_to(output_dir))
            reports.append(report)
        except Exception as e:
            print(f"⚠️  无法读取 {report_file}: {e}", file=sys.stderr)
    return reports


def find_actual_files(output_dir: Path) -> dict:
    """扫描输出目录中所有实际生成的 .md 文件（排除报告文件）
    
    Returns:
        dict: {relative_path: absolute_path}
    """
    exclude = {
        'VERIFICATION_REPORT.md', 'MAXIMUM_MODE_REPORT.md',
        'RECURSIVE_MODE_REPORT.md', 'PLAN_VERIFICATION_REPORT.md',
        'PLAN.md', 'RESEARCH_PLAN.md', 'recursive-plan.md',
    }
    actual = {}
    for md_file in output_dir.rglob('*.md'):
        if md_file.name in exclude:
            continue
        if any(p.startswith('.') for p in md_file.parts):
            continue
        rel = str(md_file.relative_to(output_dir))
        actual[rel] = str(md_file)
    return actual


def normalize_path(path_str: str, output_dir: str) -> str:
    """将路径标准化为相对于 output_dir 的路径"""
    # 去除 output_dir 前缀
    output_abs = str(Path(output_dir).resolve())
    path_abs = str(Path(path_str).resolve())
    
    if path_abs.startswith(output_abs):
        return path_abs[len(output_abs)+1:]
    
    # 去除前导 ./
    path_str = path_str.lstrip('./')
    return path_str


def cmd_sync(args):
    """同步检查点：扫描实际输出，更新任务状态"""
    checkpoint_path = Path(args.checkpoint)
    output_dir = Path(args.output_dir)
    
    if not checkpoint_path.exists():
        print(f"❌ 检查点不存在: {checkpoint_path}", file=sys.stderr)
        sys.exit(1)
    
    checkpoint = load_json(checkpoint_path)
    
    # 收集子代理报告
    reports = find_task_reports(output_dir)
    report_by_module = {}
    for r in reports:
        module = r.get('module', r.get('_path', ''))
        report_by_module[module] = r
    
    # 扫描实际文件
    actual_files = find_actual_files(output_dir)
    actual_rels = set(actual_files.keys())
    
    # 更新每个任务的状态
    completed_count = 0
    partial_count = 0
    pending_count = 0
    failed_count = 0
    
    for task_key, task in checkpoint['tasks'].items():
        expected = task.get('expected_files', [])
        
        if not expected:
            for r in reports:
                if r.get('status') == 'completed' and task['name'] in r.get('module', ''):
                    task['status'] = 'completed'
                    task['actual_files'] = r.get('files_generated', [])
                    task['completed_at'] = r.get('completed_at')
                    completed_count += 1
                    break
            else:
                pending_count += 1
            continue
        
        # 检查预期文件是否都存在（路径标准化后比较）
        found_files = []
        for exp_file in expected:
            norm = normalize_path(exp_file, str(output_dir))
            if norm in actual_rels:
                found_files.append(norm)
            elif '(' not in norm:
                # 模糊匹配：文件名在某个实际文件中
                basename = Path(norm).name
                if any(basename in af for af in actual_rels):
                    found_files.append(norm)
        
        # 模糊匹配：任务名相关的文件
        task_name_slug = task['name'].replace('/', '-').replace(' ', '-')
        for af in actual_rels:
            if task_name_slug in af and af not in found_files:
                found_files.append(af)
        
        task['actual_files'] = found_files
        
        # 判断状态
        if expected:
            match_ratio = len(found_files) / max(1, len(expected))
            if match_ratio >= 0.8:
                task['status'] = 'completed'
                completed_count += 1
            elif match_ratio >= 0.3:
                task['status'] = 'partial'
                partial_count += 1
            elif found_files:
                task['status'] = 'partial'
                partial_count += 1
            else:
                task['status'] = 'pending'
                pending_count += 1
        else:
            if found_files:
                task['status'] = 'completed'
                completed_count += 1
            else:
                task['status'] = 'pending'
                pending_count += 1
    
    checkpoint['last_updated'] = now_iso()
    checkpoint['summary'] = {
        'completed': completed_count,
        'partial': partial_count,
        'pending': pending_count,
        'failed': failed_count,
        'completion_rate': f"{completed_count}/{checkpoint['total_tasks']}",
    }
    
    save_json(checkpoint_path, checkpoint)
    
    print(f"✅ 检查点已同步: {checkpoint_path}")
    print(f"   完成: {completed_count} | 部分: {partial_count} | 待处理: {pending_count}")
    total_expected = sum(len(t.get('expected_files', [])) for t in checkpoint['tasks'].values())
    total_actual = sum(len(t.get('actual_files', [])) for t in checkpoint['tasks'].values())
    print(f"   预期文件: {total_expected} | 实际文件: {total_actual}")
    
    # 打印子代理报告摘要
    if reports:
        print(f"\n📋 子代理报告 ({len(reports)} 个):")
        for r in reports[:10]:
            status_icon = '✅' if r.get('status') == 'completed' else '⚠️' if r.get('status') == 'partial' else '❌'
            module = r.get('module', r.get('_path', '?'))
            files = len(r.get('files_generated', []))
            score = r.get('quality_self_score', '?')
            print(f"   {status_icon} {module}: {files} 文件, 自评 {score}")


# ─── STATUS ─────────────────────────────────────────────────────────────────

def cmd_status(args):
    """查看检查点状态"""
    checkpoint_path = Path(args.checkpoint)
    
    if not checkpoint_path.exists():
        print(f"❌ 检查点不存在: {checkpoint_path}", file=sys.stderr)
        sys.exit(1)
    
    checkpoint = load_json(checkpoint_path)
    
    print(f"\n📊 计划执行状态")
    print(f"{'=' * 60}")
    print(f"项目: {checkpoint.get('project', 'unknown')}")
    print(f"开始: {checkpoint.get('started_at', '?')}")
    print(f"更新: {checkpoint.get('last_updated', '?')}")
    
    summary = checkpoint.get('summary', {})
    total = checkpoint.get('total_tasks', 0)
    completed = summary.get('completed', 0)
    
    if total > 0:
        pct = completed / total * 100
        bar_len = 30
        filled = int(bar_len * completed / total)
        bar = '█' * filled + '░' * (bar_len - filled)
        print(f"\n进度: [{bar}] {completed}/{total} ({pct:.0f}%)")
    
    print(f"\n{'任务':<35} {'状态':<12} {'预期':>4} {'实际':>4}")
    print(f"{'-'*35} {'-'*12} {'-'*4} {'-'*4}")
    
    for task_key, task in sorted(checkpoint['tasks'].items()):
        name = task['name'][:33]
        status = task['status']
        expected = len(task.get('expected_files', []))
        actual = len(task.get('actual_files', []))
        
        icon = {'completed': '✅', 'partial': '⚠️', 'pending': '⏳', 'failed': '❌'}.get(status, '?')
        
        print(f"  {name:<33} {icon} {status:<8} {expected:>4} {actual:>4}")


# ─── COMPLETE ───────────────────────────────────────────────────────────────

def cmd_complete(args):
    """标记任务完成"""
    checkpoint_path = Path(args.checkpoint)
    
    if not checkpoint_path.exists():
        print(f"❌ 检查点不存在: {checkpoint_path}", file=sys.stderr)
        sys.exit(1)
    
    checkpoint = load_json(checkpoint_path)
    task_name = args.task
    
    # 查找任务
    found = False
    for task_key, task in checkpoint['tasks'].items():
        if task_name in task_key or task_name in task['name']:
            task['status'] = 'completed'
            task['completed_at'] = now_iso()
            found = True
            print(f"✅ 已标记完成: {task['name']}")
            break
    
    if not found:
        print(f"❌ 未找到任务: {task_name}", file=sys.stderr)
        sys.exit(1)
    
    checkpoint['last_updated'] = now_iso()
    save_json(checkpoint_path, checkpoint)


# ─── VERIFY ─────────────────────────────────────────────────────────────────

def cmd_verify(args):
    """计划验收：对比计划与实际输出，生成报告"""
    plan_path = Path(args.plan)
    checkpoint_path = Path(args.checkpoint)
    output_dir = Path(args.output_dir)
    
    if not checkpoint_path.exists():
        print(f"❌ 检查点不存在: {checkpoint_path}", file=sys.stderr)
        sys.exit(1)
    
    checkpoint = load_json(checkpoint_path)
    actual_files = find_actual_files(output_dir)
    actual_rels = set(actual_files.keys())
    reports = find_task_reports(output_dir)
    
    # 统计
    total_expected = 0
    total_actual_matched = 0
    task_results = []
    
    for task_key, task in sorted(checkpoint['tasks'].items()):
        expected = task.get('expected_files', [])
        actual = task.get('actual_files', [])
        
        # 检查预期文件是否都存在
        matched = []
        missing = []
        for exp in expected:
            norm = normalize_path(exp, str(output_dir))
            if '(' in norm:
                continue  # 跳过目录型预期
            if norm in actual_rels:
                matched.append(norm)
            else:
                basename = Path(norm).name
                if any(basename in af for af in actual_rels):
                    matched.append(norm)
                else:
                    missing.append(norm)
        
        total_expected += len(expected)
        total_actual_matched += len(matched)
        
        match_ratio = len(matched) / max(1, len(expected)) * 100 if expected else 100
        
        if match_ratio >= 80:
            status = '✅'
        elif match_ratio >= 50:
            status = '⚠️'
        else:
            status = '❌'
        
        task_results.append({
            'name': task['name'],
            'expected': len(expected),
            'matched': len(matched),
            'missing': missing,
            'ratio': match_ratio,
            'status': status,
        })
    
    overall_ratio = total_actual_matched / max(1, total_expected) * 100
    
    # 生成报告
    report_path = output_dir / 'PLAN_VERIFICATION_REPORT.md'
    
    content = f"""# 计划验收报告

**计划文件**: `{plan_path}`
**检查点**: `{checkpoint_path}`
**验收时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 总体符合度

| 指标 | 结果 |
|------|------|
| **总体符合度** | {overall_ratio:.0f}% |
| **预期文件** | {total_expected} |
| **实际匹配** | {total_actual_matched} |
| **任务总数** | {len(task_results)} |
| **子代理报告** | {len(reports)} 个 |

---

## 模块符合度

| 模块 | 预期 | 实际 | 符合度 | 状态 |
|------|------|------|--------|------|
"""
    
    for t in task_results:
        content += f"| {t['name']} | {t['expected']} | {t['matched']} | {t['ratio']:.0f}% | {t['status']} |\n"
    
    # 缺失文件
    all_missing = [t for t in task_results if t['missing']]
    if all_missing:
        content += f"\n---\n\n## 缺失文件\n\n"
        content += f"| 模块 | 缺失文件 |\n|------|----------|\n"
        for t in all_missing:
            for m in t['missing'][:5]:
                content += f"| {t['name']} | `{m}` |\n"
            if len(t['missing']) > 5:
                content += f"| {t['name']} | ... +{len(t['missing']) - 5} 个 |\n"
    
    # 子代理报告
    if reports:
        content += f"\n---\n\n## 子代理报告\n\n"
        content += f"| 模块 | 状态 | 文件数 | 自评 | 关键发现 |\n"
        content += f"|------|------|--------|------|----------|\n"
        for r in reports:
            module = r.get('module', r.get('_path', '?'))
            status = r.get('status', '?')
            files = len(r.get('files_generated', []))
            score = r.get('quality_self_score', '?')
            findings = r.get('key_findings', [])
            finding_summary = findings[0][:30] + '...' if findings else '-'
            content += f"| {module} | {status} | {files} | {score} | {finding_summary} |\n"
    
    # 建议
    content += f"\n---\n\n## 建议\n\n"
    if overall_ratio >= 90:
        content += "✅ 执行质量优秀，计划完成度高\n"
    elif overall_ratio >= 70:
        low_tasks = [t for t in task_results if t['ratio'] < 80]
        content += f"⚠️ 有 {len(low_tasks)} 个任务完成度不足，建议补充:\n"
        for t in low_tasks[:5]:
            content += f"- **{t['name']}**: 符合度 {t['ratio']:.0f}%，缺失 {len(t['missing'])} 个文件\n"
    else:
        content += f"❌ 总体完成度偏低 ({overall_ratio:.0f}%)，建议检查执行流程\n"
    
    content += f"\n---\n\n*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n"
    
    report_path.write_text(content, encoding='utf-8')
    
    # 打印摘要
    print(f"\n📊 计划验收报告")
    print(f"{'=' * 60}")
    print(f"总体符合度: {overall_ratio:.0f}%")
    print(f"预期文件: {total_expected} | 实际匹配: {total_actual_matched}")
    print(f"任务完成: {sum(1 for t in task_results if t['status'] == '✅')}/{len(task_results)}")
    
    if overall_ratio >= 90:
        print(f"\n✅ 执行质量优秀")
    elif overall_ratio >= 70:
        print(f"\n⚠️ 部分任务未完成")
    else:
        print(f"\n❌ 完成度偏低")
    
    print(f"\n📄 详细报告: {report_path}")
    
    return 0 if overall_ratio >= 70 else 1


# ─── MAIN ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='计划追踪器 - 维护检查点、对比计划与实际输出',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # init
    p_init = subparsers.add_parser('init', help='初始化检查点')
    p_init.add_argument('--plan', required=True, help='PLAN.md 路径')
    p_init.add_argument('--manifest', required=True, help='模块清单 JSON 路径')
    p_init.add_argument('--output-dir', required=True, help='分析输出目录')
    p_init.set_defaults(func=cmd_init)
    
    # sync
    p_sync = subparsers.add_parser('sync', help='同步检查点（扫描实际输出）')
    p_sync.add_argument('--checkpoint', required=True, help='检查点文件路径')
    p_sync.add_argument('--output-dir', required=True, help='分析输出目录')
    p_sync.set_defaults(func=cmd_sync)
    
    # status
    p_status = subparsers.add_parser('status', help='查看检查点状态')
    p_status.add_argument('--checkpoint', required=True, help='检查点文件路径')
    p_status.set_defaults(func=cmd_status)
    
    # complete
    p_complete = subparsers.add_parser('complete', help='标记任务完成')
    p_complete.add_argument('--checkpoint', required=True, help='检查点文件路径')
    p_complete.add_argument('--task', required=True, help='任务名称或 ID')
    p_complete.set_defaults(func=cmd_complete)
    
    # verify
    p_verify = subparsers.add_parser('verify', help='计划验收')
    p_verify.add_argument('--plan', required=True, help='PLAN.md 路径')
    p_verify.add_argument('--checkpoint', required=True, help='检查点文件路径')
    p_verify.add_argument('--output-dir', required=True, help='分析输出目录')
    p_verify.set_defaults(func=cmd_verify)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == '__main__':
    main()
