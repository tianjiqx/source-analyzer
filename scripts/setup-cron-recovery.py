#!/usr/bin/env python3
"""
Cron 自动恢复设置器

为源码分析项目设置定时恢复任务，自动检测失败任务并恢复执行。

工作原理：
1. 主 agent 派发分析任务 → 部分子任务因 rate limit 失败
2. 主 agent session 结束（context 耗尽或错误）
3. 定时恢复触发独立 session 运行 resilient-runner.py --continue
4. Runner 检测失败任务 → 生成 continuation prompt
5. 循环直到所有任务完成或超过最大重试

环境适配：
- OpenClaw: 生成 cron job JSON，通过 cron 工具创建 isolated session
- opencode/其他: 生成系统 crontab 条目
- 纯 CLI: 输出手动恢复命令

用法:
    # 设置自动恢复（默认每 30 分钟检查一次）
    python3 setup-cron-recovery.py \\
        --output-dir $OUTPUT_BASE/my-project \\
        --project-path ~/opensource/my-project \\
        --plan $OUTPUT_BASE/my-project/PLAN.md \\
        --interval 30

    # 查看已设置的恢复任务
    python3 setup-cron-recovery.py --list

    # 移除恢复任务
    python3 setup-cron-recovery.py --remove my-project
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESILIENT_RUNNER = os.path.join(SCRIPT_DIR, "resilient-runner.py")


def generate_cron_job_config(
    output_dir: str,
    project_path: str,
    plan_file: str,
    interval_minutes: int = 30,
    max_retries: int = 5,
) -> dict:
    """生成环境无关的调度配置
    
    返回包含多环境适配信息的配置对象。
    OpenClaw 环境：可直接作为 cron 工具的 job 对象。
    其他环境：使用 crontab 或 manual 字段。
    """
    project_name = os.path.basename(output_dir.rstrip('/'))
    job_name = f"analysis-recovery-{project_name}"
    
    # 构建 agentTurn prompt（环境无关）
    prompt = f"""[自动恢复] 源码分析任务弹性恢复 ({project_name})

这是一个定时驱动的自动恢复任务。执行以下步骤：

## 步骤 1: 检查失败任务

```bash
python3 {RESILIENT_RUNNER} \\
    --output-dir {output_dir} \\
    --project-path {project_path} \\
    --plan {plan_file} \\
    --continue --json
```

## 步骤 2: 根据结果决定行动

查看 JSON 输出的 status 字段：

- **"needs_retry"**: 有失败任务。运行步骤 3
- **"completed"**: 所有任务已完成。
    1. 移除自身的定时恢复任务（如环境支持）
    2. [NOTIFY_SILENT]
- **"waiting_backoff"**: 任务在退避等待中。
    1. [NOTIFY_SILENT]
    2. 等待下次定时触发
- **"dry_run"**: 运行步骤 3 确认具体任务

## 步骤 3: 获取 continuation prompt 并执行

```bash
python3 {RESILIENT_RUNNER} \\
    --output-dir {output_dir} \\
    --project-path {project_path} \\
    --plan {plan_file} \\
    --continue
```

输出的 "Continuation Prompt" 部分包含了你需要的信息：
- 失败任务清单（模块路径、重试次数、已有文件）
- 项目信息和检查点文件路径
- 执行约束

**你不需要死搬硬套 prompt**。根据你的判断：
1. 读取 SKILL.md 了解分析要求
2. 检查已有文件，只补充缺失的
3. 用 [DISPATCH] 并行派发（不要串行）
4. [WAIT] 等待
5. 完成后 --sync 检查结果
6. 如有需要，继续重试（最多 {max_retries} 轮）
7. 如果 rate_limit，减少并行数

## 步骤 4: 检查结果

重试后运行 --sync，如果全部完成则移除定时恢复任务。

## 注意
- 每个任务最多重试 {max_retries} 次
- 超过的自动降级
- 不要生成已有文件

项目: {project_name}
输出目录: {output_dir}
"""

    # OpenClaw cron job 配置
    openclaw_job = {
        "name": job_name,
        "description": f"自动恢复 {project_name} 源码分析的失败任务",
        "schedule": {
            "kind": "every",
            "everyMs": interval_minutes * 60 * 1000,
        },
        "sessionTarget": "isolated",
        "payload": {
            "kind": "agentTurn",
            "message": prompt,
            "lightContext": True,
        },
        "delivery": {
            "mode": "none",
        },
        "deleteAfterRun": False,
        "enabled": True,
        "failureAlert": {
            "after": 3,
            "mode": "announce",
            "cooldownMs": 3600000,
        },
    }
    
    # 系统 crontab 条目（opencode / 纯 CLI）
    script_dir = os.path.dirname(RESILIENT_RUNNER)
    crontab_entry = (
        f"*/{interval_minutes} * * * * "
        f"cd {output_dir} && "
        f"python3 {RESILIENT_RUNNER} "
        f"--output-dir {output_dir} "
        f"--project-path {project_path} "
        f"--plan {plan_file} --continue "
        f">> {output_dir}/recovery.log 2>&1"
    )
    
    # 手动恢复命令（无定时能力时）
    manual_cmd = (
        f"python3 {RESILIENT_RUNNER} "
        f"--output-dir {output_dir} "
        f"--project-path {project_path} "
        f"--plan {plan_file} --continue"
    )
    
    return {
        "job_name": job_name,
        "openclaw": openclaw_job,
        "crontab": crontab_entry,
        "manual": manual_cmd,
        "prompt": prompt,
    }


def main():
    parser = argparse.ArgumentParser(
        description='设置源码分析自动恢复 cron job',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--output-dir', '-o', help='分析输出目录')
    parser.add_argument('--project-path', '-p', help='项目源码路径')
    parser.add_argument('--plan', help='PLAN.md 路径')
    parser.add_argument('--interval', type=int, default=2, help='检查间隔（分钟，默认 2）')
    parser.add_argument('--max-retries', type=int, default=5, help='最大重试次数（默认 5）')
    parser.add_argument('--list', action='store_true', help='列出相关 cron jobs')
    parser.add_argument('--remove', help='移除指定项目的恢复 cron job')

    args = parser.parse_args()

    if args.list:
        print("查看已设置的恢复任务：")
        print("  OpenClaw: cron(action=list)")
        print("  系统 crontab: crontab -l | grep analysis-recovery")
        return

    if args.remove:
        print(f"移除恢复任务：")
        print(f"  OpenClaw: cron(action=remove, jobId='analysis-recovery-{args.remove}')")
        print(f"  系统 crontab: crontab -l | grep -v '{args.remove}' | crontab -")
        return

    if not all([args.output_dir, args.project_path, args.plan]):
        parser.error("--output-dir, --project-path, --plan 都是必需的（除非使用 --list/--remove）")

    config = generate_cron_job_config(
        output_dir=os.path.abspath(args.output_dir),
        project_path=os.path.abspath(args.project_path),
        plan_file=os.path.abspath(args.plan),
        interval_minutes=args.interval,
        max_retries=args.max_retries,
    )

    print("=" * 60)
    print("调度恢复配置（多环境适配）")
    print("=" * 60)
    print()
    
    # OpenClaw 环境
    print("─" * 40)
    print("📋 OpenClaw 环境")
    print("─" * 40)
    print("\n直接在对话中让 agent 创建 cron job：")
    print("\n  cron(action=add, job=<下面的JSON>)\n")
    print(json.dumps(config['openclaw'], indent=2, ensure_ascii=False))
    print()
    
    # 系统 crontab
    print("─" * 40)
    print("📋 opencode / 纯 CLI 环境 (系统 crontab)")
    print("─" * 40)
    print("\n添加到 crontab：")
    print(f"\n  {config['crontab']}\n")
    print("或运行 crontab -e 粘贴上面的条目。")
    print()
    
    # 手动恢复
    print("─" * 40)
    print("📋 手动恢复（无定时能力）")
    print("─" * 40)
    print("\n直接运行：")
    print(f"\n  {config['manual']}\n")
    print()
    print("=" * 60)
    print()
    print(f"⏱️  检查间隔: 每 {args.interval} 分钟")
    print(f"🔄 最大重试: {args.max_retries} 次")
    print(f"📂 输出目录: {args.output_dir}")
    print()
    print("✅ 创建后，系统会自动：")
    print(f"  1. 每 {args.interval} 分钟检查一次分析进度")
    print("  2. 自动重试失败/未完成的任务")
    print("  3. 全部完成后需移除定时任务")
    print("  4. 超过 3 次连续失败才通知你")


if __name__ == '__main__':
    main()
