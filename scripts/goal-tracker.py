#!/usr/bin/env python3
"""
Goal Tracker - 持久化分析任务状态

解决会话中断导致 goal 状态丢失的问题。

功能：
- register: 注册新的分析任务
- update: 更新任务进度
- complete: 标记任务完成
- list: 列出所有未完成的任务
- check: 检查是否有未完成任务（会话恢复用）
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

import os

# 支持环境变量覆盖，默认使用 OpenClaw 路径
_GOALS_DEFAULT = os.path.expanduser("~/.openclaw/workspace/active-goals.json")
GOALS_FILE = Path(os.environ.get("SOURCE_ANALYZER_GOALS_FILE", _GOALS_DEFAULT))


def load_goals() -> Dict[str, Any]:
    """加载 goals 文件"""
    if GOALS_FILE.exists():
        with open(GOALS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"goals": []}


def save_goals(data: Dict[str, Any]):
    """保存 goals 文件"""
    GOALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(GOALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_goal_id() -> str:
    """生成 goal ID"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"goal-{timestamp}"


def register_goal(args):
    """注册新的分析任务"""
    data = load_goals()
    
    goal_id = generate_goal_id()
    goal = {
        "id": goal_id,
        "objective": args.objective,
        "created": datetime.now().isoformat(timespec='seconds'),
        "status": "in_progress",
        "project": args.project,
        "output_dir": args.output_dir,
        "analysis_mode": args.mode,
        "progress": {
            "current_phase": "Phase 1: 项目级扫描",
            "completed_tasks": 0,
            "total_tasks": args.total_tasks or 0,
            "last_update": datetime.now().isoformat(timespec='seconds')
        },
        "context": {
            "plan_file": args.plan_file if args.plan_file else None,
            "session_key": None,  # 可选，用于追踪会话
            "commit_hash": args.commit_hash if args.commit_hash else None,
            "commit_short": args.commit_short if args.commit_short else None,
            "commit_date": args.commit_date if args.commit_date else None,
            "branch": args.branch if args.branch else None,
        }
    }
    
    data["goals"].append(goal)
    save_goals(data)
    
    print(f"✅ 已注册 goal: {goal_id}")
    print(f"   目标: {args.objective}")
    print(f"   项目: {args.project}")
    print(f"   模式: {args.mode}")
    print(f"   输出: {args.output_dir}")
    return goal_id


def update_goal(args):
    """更新任务进度"""
    data = load_goals()
    
    goal = None
    for g in data["goals"]:
        if g["id"] == args.goal_id:
            goal = g
            break
    
    if not goal:
        print(f"❌ 未找到 goal: {args.goal_id}")
        sys.exit(1)
    
    if args.phase:
        goal["progress"]["current_phase"] = args.phase
    if args.completed is not None:
        goal["progress"]["completed_tasks"] = args.completed
    if args.total is not None:
        goal["progress"]["total_tasks"] = args.total
    
    goal["progress"]["last_update"] = datetime.now().isoformat(timespec='seconds')
    
    save_goals(data)
    
    print(f"✅ 已更新 goal: {args.goal_id}")
    print(f"   阶段: {goal['progress']['current_phase']}")
    print(f"   进度: {goal['progress']['completed_tasks']}/{goal['progress']['total_tasks']}")


def complete_goal(args):
    """标记任务完成"""
    data = load_goals()
    
    goal = None
    for g in data["goals"]:
        if g["id"] == args.goal_id:
            goal = g
            break
    
    if not goal:
        print(f"❌ 未找到 goal: {args.goal_id}")
        sys.exit(1)
    
    goal["status"] = "completed"
    goal["completed_at"] = datetime.now().isoformat(timespec='seconds')
    
    save_goals(data)
    
    print(f"✅ 已完成 goal: {args.goal_id}")
    print(f"   目标: {goal['objective']}")
    print(f"   完成时间: {goal['completed_at']}")


def list_goals(args):
    """列出所有未完成的任务"""
    data = load_goals()
    
    active_goals = [g for g in data["goals"] if g["status"] == "in_progress"]
    
    if not active_goals:
        print("✅ 没有未完成的任务")
        return
    
    print(f"📋 未完成的任务 ({len(active_goals)} 个)\n")
    
    for i, goal in enumerate(active_goals, 1):
        progress = goal["progress"]
        print(f"{i}. {goal['id']}")
        print(f"   目标: {goal['objective']}")
        print(f"   项目: {goal['project']}")
        print(f"   模式: {goal['analysis_mode']}")
        print(f"   阶段: {progress['current_phase']}")
        print(f"   进度: {progress['completed_tasks']}/{progress['total_tasks']}")
        print(f"   创建: {goal['created']}")
        print(f"   更新: {progress['last_update']}")
        print(f"   输出: {goal['output_dir']}")
        ctx = goal.get('context', {})
        if ctx.get('commit_short'):
            print(f"   Commit: {ctx['commit_short']} ({ctx.get('commit_date', '?')})")
        if ctx.get('branch'):
            print(f"   分支: {ctx['branch']}")
        print()


def check_goals(args):
    """检查是否有未完成任务（会话恢复用）"""
    data = load_goals()
    
    active_goals = [g for g in data["goals"] if g["status"] == "in_progress"]
    
    if not active_goals:
        print("✅ 没有未完成的任务")
        return
    
    print(f"⚠️  发现 {len(active_goals)} 个未完成的任务:\n")
    
    for goal in active_goals:
        progress = goal["progress"]
        last_update = datetime.fromisoformat(progress['last_update'])
        hours_ago = (datetime.now() - last_update).total_seconds() / 3600
        
        stale_marker = " ⚠️ STALE" if hours_ago > 24 else ""
        
        print(f"• {goal['id']}{stale_marker}")
        print(f"  目标: {goal['objective']}")
        print(f"  阶段: {progress['current_phase']}")
        print(f"  进度: {progress['completed_tasks']}/{progress['total_tasks']}")
        print(f"  最后更新: {hours_ago:.1f} 小时前")
        print(f"  输出目录: {goal['output_dir']}")
        
        if goal.get('context', {}).get('plan_file'):
            print(f"  计划文件: {goal['context']['plan_file']}")
        
        print()
    
    print("💡 提示:")
    print("   1. 继续执行: 进入输出目录，运行 resilient-runner.py --continue")
    print("   2. 查看详情: goal-tracker.py list")
    print("   3. 标记完成: goal-tracker.py complete <goal-id>")


def main():
    parser = argparse.ArgumentParser(description="Goal Tracker - 持久化分析任务状态")
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # register
    register_parser = subparsers.add_parser("register", help="注册新的分析任务")
    register_parser.add_argument("--objective", required=True, help="任务目标描述")
    register_parser.add_argument("--project", required=True, help="项目名称")
    register_parser.add_argument("--output-dir", required=True, help="输出目录")
    register_parser.add_argument("--mode", required=True, choices=["layer1", "layer2", "layer3", "maximum", "recursive_deep"], help="分析模式")
    register_parser.add_argument("--total-tasks", type=int, help="总任务数")
    register_parser.add_argument("--plan-file", help="计划文件路径")
    register_parser.add_argument("--commit-hash", help="项目当前 Git commit hash")
    register_parser.add_argument("--commit-short", help="项目当前 Git commit 短 hash")
    register_parser.add_argument("--commit-date", help="项目当前 Git commit 日期")
    register_parser.add_argument("--branch", help="项目当前 Git 分支")
    
    # update
    update_parser = subparsers.add_parser("update", help="更新任务进度")
    update_parser.add_argument("--goal-id", required=True, help="Goal ID")
    update_parser.add_argument("--phase", help="当前阶段")
    update_parser.add_argument("--completed", type=int, help="已完成任务数")
    update_parser.add_argument("--total", type=int, help="总任务数")
    
    # complete
    complete_parser = subparsers.add_parser("complete", help="标记任务完成")
    complete_parser.add_argument("--goal-id", required=True, help="Goal ID")
    
    # list
    list_parser = subparsers.add_parser("list", help="列出所有未完成的任务")
    
    # check
    check_parser = subparsers.add_parser("check", help="检查是否有未完成任务")
    
    args = parser.parse_args()
    
    if args.command == "register":
        register_goal(args)
    elif args.command == "update":
        update_goal(args)
    elif args.command == "complete":
        complete_goal(args)
    elif args.command == "list":
        list_goals(args)
    elif args.command == "check":
        check_goals(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
