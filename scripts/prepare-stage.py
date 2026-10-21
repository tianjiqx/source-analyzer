#!/usr/bin/env python3
"""Prepare bounded analysis stages without scanning source or writing conclusions."""

import argparse
import sys

from analysis_stages import prepare_stage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("initial", "reading"))
    parser.add_argument("target", help="initial: 源码目录；reading: 分析根目录")
    parser.add_argument("--output", "-o", help="initial 必需：分析根目录")
    parser.add_argument("--material", action="append", default=[], help="reading：底稿相对路径，可重复")
    args = parser.parse_args()
    try:
        stage = prepare_stage(args.mode, args.target, args.output, args.material)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"准备完成（尚未执行分析/整理）: {stage}")
    print("读取阶段 PLAN.md 与对应指南，再生成正文并运行专用验收。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
