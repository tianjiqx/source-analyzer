#!/usr/bin/env python3
"""
Commit Tracker - 跟踪分析项目的 Git commit，支持增量分析

功能：
- info: 获取项目当前 commit 信息（hash, date, branch, tag）
- record: 在分析输出目录记录 commit 元数据
- diff: 对比上次分析的 commit 与当前 commit，输出变更文件
- status: 检查项目是否需要增量分析（commit 是否变化）
- history: 查看分析目录的 commit 历史

用法：
    # 获取项目当前 commit
    python3 commit-tracker.py info /path/to/project

    # 记录分析 commit（分析开始时调用）
    python3 commit-tracker.py record /path/to/project --output-dir ~/.openclaw/learning/projects/myproject

    # 检查是否需要增量分析
    python3 commit-tracker.py status /path/to/project --output-dir ~/.openclaw/learning/projects/myproject

    # 查看 commit 变更
    python3 commit-tracker.py diff /path/to/project --output-dir ~/.openclaw/learning/projects/myproject

    # 查看分析历史
    python3 commit-tracker.py history --output-dir ~/.openclaw/learning/projects/myproject
"""

import json
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Tuple


def run_git(project_path: str, *args) -> str:
    """运行 git 命令，返回输出"""
    result = subprocess.run(
        ['git', '-C', project_path] + list(args),
        capture_output=True, text=True
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if 'not a git repository' in stderr:
            print(f"❌ 不是 Git 仓库: {project_path}", file=sys.stderr)
        else:
            print(f"❌ Git 命令失败: {stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def get_commit_info(project_path: str) -> Dict[str, Any]:
    """获取项目当前 commit 的完整信息"""
    # 检查是否是 git 仓库
    try:
        run_git(project_path, 'rev-parse', '--git-dir')
    except SystemExit:
        return {}

    commit_hash = run_git(project_path, 'rev-parse', 'HEAD')
    commit_short = run_git(project_path, 'rev-parse', '--short', 'HEAD')
    commit_date = run_git(project_path, 'log', '-1', '--format=%cI', 'HEAD')
    commit_author = run_git(project_path, 'log', '-1', '--format=%cN', 'HEAD')
    commit_subject = run_git(project_path, 'log', '-1', '--format=%s', 'HEAD')
    branch = run_git(project_path, 'rev-parse', '--abbrev-ref', 'HEAD')
    
    # 获取 tag（如果有）
    try:
        describe = run_git(project_path, 'describe', '--tags', '--always')
    except SystemExit:
        describe = commit_short

    # 获取远程 URL（如果有）
    remote_url = ''
    try:
        remote_url = run_git(project_path, 'remote', 'get-url', 'origin')
    except SystemExit:
        pass

    # 统计文件数
    file_count = run_git(project_path, 'ls-files', '--cached', '--no-deleted')
    total_files = len([f for f in file_count.split('\n') if f]) if file_count else 0

    return {
        'commit_hash': commit_hash,
        'commit_short': commit_short,
        'commit_date': commit_date,
        'commit_author': commit_author,
        'commit_subject': commit_subject,
        'branch': branch,
        'tag': describe if describe != commit_short else None,
        'remote_url': remote_url,
        'total_files': total_files,
    }


def get_changed_files(project_path: str, old_commit: str, new_commit: str = 'HEAD') -> Dict[str, Any]:
    """获取两个 commit 之间的变更文件"""
    # 先检查 new_commit 是否存在
    try:
        run_git(project_path, 'cat-file', '-e', new_commit)
    except SystemExit:
        return {'error': f'commit {new_commit} 不存在'}

    # 如果 old_commit 不存在（可能是浅克隆后被 unshallow）
    try:
        run_git(project_path, 'cat-file', '-e', old_commit)
    except SystemExit:
        return {'error': f'旧 commit {old_commit} 不存在（可能需要 git fetch --unshallow）'}

    diff_output = run_git(project_path, 'diff', '--name-status', old_commit, new_commit)
    
    added = []
    modified = []
    deleted = []
    renamed = []
    
    for line in diff_output.split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        status = parts[0][0]  # A/M/D/R/C
        
        if status == 'A':
            added.append(parts[1])
        elif status == 'M':
            modified.append(parts[1])
        elif status == 'D':
            deleted.append(parts[1])
        elif status in ('R', 'C'):
            renamed.append({'from': parts[1], 'to': parts[2]})
        else:
            modified.append(parts[-1])
    
    # 获取 diff 统计
    stat_output = run_git(project_path, 'diff', '--stat', old_commit, new_commit)
    
    # 获取 commits 之间的提交数
    commits_between = run_git(project_path, 'rev-list', '--count', old_commit, new_commit)
    
    return {
        'old_commit': old_commit,
        'new_commit': new_commit,
        'commits_between': int(commits_between) if commits_between.isdigit() else 0,
        'added': added,
        'modified': modified,
        'deleted': deleted,
        'renamed': renamed,
        'summary': {
            'added': len(added),
            'modified': len(modified),
            'deleted': len(deleted),
            'renamed': len(renamed),
            'total_changed': len(added) + len(modified) + len(deleted) + len(renamed),
        },
        'stat': stat_output,
    }


def load_analysis_meta(output_dir: str) -> Dict[str, Any]:
    """加载分析目录的元数据"""
    meta_path = Path(output_dir) / 'project-meta.json'
    if meta_path.exists():
        with open(meta_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_analysis_meta(output_dir: str, meta: Dict[str, Any]):
    """保存分析目录的元数据"""
    meta_path = Path(output_dir) / 'project-meta.json'
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def load_commit_history(output_dir: str) -> list:
    """加载 commit 历史"""
    history_path = Path(output_dir) / 'commit-history.json'
    if history_path.exists():
        with open(history_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_commit_history(output_dir: str, history: list):
    """保存 commit 历史"""
    history_path = Path(output_dir) / 'commit-history.json'
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def cmd_info(args):
    """获取项目当前 commit 信息"""
    info = get_commit_info(args.project_path)
    if not info:
        print(f"❌ 无法获取 Git 信息: {args.project_path}")
        sys.exit(1)
    
    print(f"📦 项目: {Path(args.project_path).name}")
    print(f"   Commit: {info['commit_hash']}")
    print(f"   Short:  {info['commit_short']}")
    print(f"   日期:   {info['commit_date']}")
    print(f"   作者:   {info['commit_author']}")
    print(f"   消息:   {info['commit_subject']}")
    print(f"   分支:   {info['branch']}")
    if info.get('tag'):
        print(f"   Tag:    {info['tag']}")
    if info.get('remote_url'):
        print(f"   远程:   {info['remote_url']}")
    print(f"   文件数: {info['total_files']}")
    
    if args.json:
        print()
        print(json.dumps(info, indent=2, ensure_ascii=False))


def cmd_record(args):
    """在分析输出目录记录当前 commit"""
    project_path = args.project_path
    output_dir = args.output_dir

    info = get_commit_info(project_path)
    if not info:
        print(f"❌ 无法获取 Git 信息: {project_path}")
        sys.exit(1)

    # 更新 project-meta.json
    meta = load_analysis_meta(output_dir)
    
    # 记录到 meta
    old_commit = meta.get('commit_hash')
    meta['commit_hash'] = info['commit_hash']
    meta['commit_short'] = info['commit_short']
    meta['commit_date'] = info['commit_date']
    meta['commit_subject'] = info['commit_subject']
    meta['branch'] = info['branch']
    if info.get('tag'):
        meta['tag'] = info['tag']
    if info.get('remote_url'):
        meta['remote_url'] = info['remote_url']
    meta['total_files'] = info['total_files']
    meta['last_analyzed_at'] = datetime.now().isoformat(timespec='seconds')
    
    save_analysis_meta(output_dir, meta)

    # 追加到 commit 历史
    history = load_commit_history(output_dir)
    
    # 避免重复记录同一个 commit
    if not history or history[-1].get('commit_hash') != info['commit_hash']:
        history.append({
            'commit_hash': info['commit_hash'],
            'commit_short': info['commit_short'],
            'commit_date': info['commit_date'],
            'commit_subject': info['commit_subject'],
            'branch': info['branch'],
            'analyzed_at': datetime.now().isoformat(timespec='seconds'),
            'analysis_mode': args.analysis_mode or meta.get('analysis_mode', 'unknown'),
            'tag': info.get('tag'),
        })
        save_commit_history(output_dir, history)

    print(f"✅ 已记录 commit 到分析目录")
    print(f"   项目: {Path(project_path).name}")
    print(f"   Commit: {info['commit_hash']}")
    print(f"   日期:   {info['commit_date']}")
    print(f"   消息:   {info['commit_subject']}")
    print(f"   分支:   {info['branch']}")
    if info.get('tag'):
        print(f"   Tag:    {info['tag']}")
    print(f"   输出:   {output_dir}")
    
    if old_commit and old_commit != info['commit_hash']:
        print(f"   ⚠️ 与上次分析不同 (旧: {old_commit[:12]}...)")


def cmd_status(args):
    """检查项目是否需要增量分析"""
    project_path = args.project_path
    output_dir = args.output_dir

    meta = load_analysis_meta(output_dir)
    if not meta or not meta.get('commit_hash'):
        print(f"❌ 分析目录中未找到 commit 记录: {output_dir}")
        print(f"   可能是首次分析，请先运行: commit-tracker.py record")
        sys.exit(1)

    old_commit = meta['commit_hash']
    old_short = meta.get('commit_short', old_commit[:12])
    old_date = meta.get('commit_date', 'unknown')
    
    current_info = get_commit_info(project_path)
    if not current_info:
        sys.exit(1)
    
    current_hash = current_info['commit_hash']
    current_short = current_info['commit_short']
    
    if old_commit == current_hash:
        print(f"✅ 无变化")
        print(f"   项目: {Path(project_path).name}")
        print(f"   Commit: {current_short}")
        print(f"   日期:   {current_info['commit_date']}")
        print(f"   上次分析: {meta.get('last_analyzed_at', 'unknown')}")
        print(f"   💡 项目未更新，无需增量分析")
        sys.exit(0)
    
    # 有变化
    diff = get_changed_files(project_path, old_commit, 'HEAD')
    
    print(f"⚠️  检测到项目更新!")
    print(f"   项目: {Path(project_path).name}")
    print(f"   上次分析: {old_short} ({old_date})")
    print(f"   当前版本: {current_short} ({current_info['commit_date']})")
    
    if 'error' in diff:
        print(f"   ❌ 无法获取变更: {diff['error']}")
    else:
        s = diff['summary']
        print(f"   新增提交: {diff['commits_between']} 个")
        print(f"   文件变更: +{s['added']} ~{s['modified']} -{s['deleted']} 📝{s['renamed']} (共 {s['total_changed']} 个)")
        
        if s['total_changed'] > 0:
            print(f"\n   建议增量分析以下模块/文件:")
            
            # 分析变更文件所属的模块
            module_changes = {}
            for f in diff['added'] + diff['modified']:
                parts = f.split('/')
                module = parts[0] if len(parts) > 1 else 'root'
                if len(parts) > 2:
                    module = f"{parts[0]}/{parts[1]}"
                module_changes.setdefault(module, {'added': 0, 'modified': 0})
                if f in diff['added']:
                    module_changes[module]['added'] += 1
                else:
                    module_changes[module]['modified'] += 1
            
            # 按变更数排序
            for module, counts in sorted(module_changes.items(), key=lambda x: x[1]['added'] + x[1]['modified'], reverse=True)[:10]:
                print(f"     • {module}: +{counts['added']} ~{counts['modified']}")
    
    print(f"\n💡 增量分析命令:")
    print(f"   python3 commit-tracker.py diff {project_path} --output-dir {output_dir}")
    print(f"   # 然后对变更模块重新分析，完成后:")
    print(f"   python3 commit-tracker.py record {project_path} --output-dir {output_dir}")
    
    sys.exit(2 if 'error' not in diff else 1)


def cmd_diff(args):
    """对比上次分析的 commit 与当前 commit"""
    project_path = args.project_path
    output_dir = args.output_dir

    meta = load_analysis_meta(output_dir)
    if not meta or not meta.get('commit_hash'):
        print(f"❌ 分析目录中未找到 commit 记录: {output_dir}")
        sys.exit(1)

    old_commit = meta['commit_hash']
    
    diff = get_changed_files(project_path, old_commit, 'HEAD')
    
    if 'error' in diff:
        print(f"❌ {diff['error']}")
        sys.exit(1)
    
    s = diff['summary']
    
    print(f"📊 Commit 变更对比")
    print(f"   项目: {Path(project_path).name}")
    print(f"   旧: {meta.get('commit_short', old_commit[:12])} ({meta.get('commit_date', '?')})")
    print(f"   新: HEAD")
    print(f"   提交数: {diff['commits_between']}")
    print(f"   变更: +{s['added']} ~{s['modified']} -{s['deleted']} 📝{s['renamed']}")
    
    if diff['added']:
        print(f"\n🟢 新增文件 ({s['added']}):")
        for f in diff['added'][:30]:
            print(f"   + {f}")
        if s['added'] > 30:
            print(f"   ... 还有 {s['added'] - 30} 个")
    
    if diff['modified']:
        print(f"\n🟡 修改文件 ({s['modified']}):")
        for f in diff['modified'][:30]:
            print(f"   ~ {f}")
        if s['modified'] > 30:
            print(f"   ... 还有 {s['modified'] - 30} 个")
    
    if diff['deleted']:
        print(f"\n🔴 删除文件 ({s['deleted']}):")
        for f in diff['deleted'][:20]:
            print(f"   - {f}")
        if s['deleted'] > 20:
            print(f"   ... 还有 {s['deleted'] - 20} 个")
    
    if diff['renamed']:
        print(f"\n🔵 重命名/移动 ({s['renamed']}):")
        for r in diff['renamed'][:20]:
            print(f"   {r['from']} → {r['to']}")
    
    # 输出 diff stat
    if diff['stat'] and args.show_stat:
        print(f"\n📈 Diff Stat:")
        print(diff['stat'])
    
    # 输出 JSON（用于脚本消费）
    if args.json:
        print()
        print(json.dumps(diff, indent=2, ensure_ascii=False))


def cmd_history(args):
    """查看分析目录的 commit 历史"""
    output_dir = args.output_dir
    history = load_commit_history(output_dir)
    
    if not history:
        print(f"📭 无 commit 历史: {output_dir}")
        return
    
    meta = load_analysis_meta(output_dir)
    project_name = meta.get('project_name', Path(output_dir).name)
    
    print(f"📜 分析 Commit 历史: {project_name}")
    print(f"   输出目录: {output_dir}")
    print(f"   记录数: {len(history)}")
    print()
    
    for i, entry in enumerate(history, 1):
        print(f"{i}. {entry['commit_short']} | {entry['commit_date']}")
        print(f"   消息: {entry['commit_subject']}")
        print(f"   分支: {entry['branch']}")
        print(f"   分析时间: {entry['analyzed_at']}")
        print(f"   分析模式: {entry.get('analysis_mode', 'unknown')}")
        if entry.get('tag'):
            print(f"   Tag: {entry['tag']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='Commit Tracker - 跟踪分析项目的 Git commit，支持增量分析',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 获取项目当前 commit
  %(prog)s info /path/to/project

  # 记录分析 commit（分析开始和完成时都应该调用）
  %(prog)s record /path/to/project --output-dir ~/.openclaw/learning/projects/myproject

  # 检查是否需要增量分析
  %(prog)s status /path/to/project --output-dir ~/.openclaw/learning/projects/myproject

  # 查看详细变更
  %(prog)s diff /path/to/project --output-dir ~/.openclaw/learning/projects/myproject --show-stat

  # 查看分析历史
  %(prog)s history --output-dir ~/.openclaw/learning/projects/myproject
        """)
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # info
    info_parser = subparsers.add_parser('info', help='获取项目当前 commit 信息')
    info_parser.add_argument('project_path', help='项目路径')
    info_parser.add_argument('--json', action='store_true', help='输出 JSON 格式')
    
    # record
    record_parser = subparsers.add_parser('record', help='记录当前 commit 到分析输出目录')
    record_parser.add_argument('project_path', help='项目路径')
    record_parser.add_argument('--output-dir', required=True, help='分析输出目录')
    record_parser.add_argument('--analysis-mode', help='分析模式 (layer1/layer2/layer3/maximum/recursive_deep)')
    
    # status
    status_parser = subparsers.add_parser('status', help='检查项目是否需要增量分析')
    status_parser.add_argument('project_path', help='项目路径')
    status_parser.add_argument('--output-dir', required=True, help='分析输出目录')
    
    # diff
    diff_parser = subparsers.add_parser('diff', help='对比上次分析的 commit 与当前 commit')
    diff_parser.add_argument('project_path', help='项目路径')
    diff_parser.add_argument('--output-dir', required=True, help='分析输出目录')
    diff_parser.add_argument('--show-stat', action='store_true', help='显示 diff stat')
    diff_parser.add_argument('--json', action='store_true', help='输出 JSON 格式')
    
    # history
    history_parser = subparsers.add_parser('history', help='查看分析目录的 commit 历史')
    history_parser.add_argument('--output-dir', required=True, help='分析输出目录')
    
    args = parser.parse_args()
    
    if args.command == 'info':
        cmd_info(args)
    elif args.command == 'record':
        cmd_record(args)
    elif args.command == 'status':
        cmd_status(args)
    elif args.command == 'diff':
        cmd_diff(args)
    elif args.command == 'history':
        cmd_history(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
