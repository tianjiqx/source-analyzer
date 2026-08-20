#!/usr/bin/env python3
"""lint-skill.py — source-analyzer skill 回归门（结构自检）

检测项：
  1. frontmatter 合法性（name/description 必填、name kebab-case）
  2. 代码围栏配对（``` 开闭平衡，且无嵌套异常）
  3. 相对链接死链扫描（SKILL.md 及 guides/ 中引用的本仓文件必须存在）
  4. 硬编码个人路径检测（/home/<user>、C:\\Users\\ 等）
  5. 路径变量使用检查（示例命令应使用 $SKILL_DIR/$WORKSPACE 而非绝对路径）

用法：
  python3 scripts/lint-skill.py [--skill-dir DIR] [--json]
退出码：0=通过，1=有错误
"""
import argparse
import json
import re
import sys
from pathlib import Path

FENCE_RE = re.compile(r"^\s*(```|~~~)")
HOME_RE = re.compile(r"/home/[a-zA-Z0-9_-]+|C:\\\\Users\\\\[a-zA-Z0-9_.-]+")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)#?\s]+)(?:#[^)\s]*)?\)")
VAR_OK = re.compile(r"\$\{?(SKILL_DIR|OUTPUT_BASE|WORKSPACE)\}?")
ABS_CMD_RE = re.compile(r"(?:python3?|bash|sh)\s+(/[^$\s]+\.(?:py|sh))")


def lint_frontmatter(skill_md: str, errors, warnings):
    m = re.match(r"^---\n(.*?)\n---\n", skill_md, re.DOTALL)
    if not m:
        errors.append("SKILL.md 缺少 frontmatter（--- ... ---）")
        return None
    fm = m.group(1)
    name = re.search(r"^name:\s*(\S+)", fm, re.MULTILINE)
    desc = re.search(r"^description:\s*(.+)", fm, re.MULTILINE)
    if not name:
        errors.append("frontmatter 缺少 name")
    elif not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name.group(1)):
        errors.append(f"frontmatter name 非 kebab-case: {name.group(1)}")
    if not desc:
        errors.append("frontmatter 缺少 description")
    elif len(desc.group(1)) > 500:
        warnings.append(f"description 过长（{len(desc.group(1))} 字符 > 500）")
    return fm


def lint_fences(path: Path, errors):
    lines = path.read_text(encoding="utf-8").splitlines()
    depth = 0
    for i, line in enumerate(lines, 1):
        if FENCE_RE.match(line):
            depth ^= 1
            if depth == 1 and i > 1 and FENCE_RE.match(lines[i - 2] or ""):
                pass  # consecutive fence open after blank is fine
    if depth != 0:
        errors.append(f"{path.name}: 代码围栏不配对（奇数个 ``` 行）")


def lint_links(path: Path, root: Path, errors):
    text = path.read_text(encoding="utf-8")
    # 去掉代码块内的内容，避免把示例中的伪链接当死链
    stripped = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    for target in LINK_RE.findall(stripped):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        if not (path.parent / target).resolve().exists() and not (root / target).exists():
            errors.append(f"{path.relative_to(root)}: 死链 [{target}]")


def lint_hardcoded_paths(path: Path, errors):
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if HOME_RE.search(line):
            errors.append(f"{path.name}:L{i} 硬编码个人路径: {line.strip()[:80]}")


def lint_abs_script_refs(skill_md: str, warnings):
    for m in ABS_CMD_RE.finditer(skill_md):
        warnings.append(f"SKILL.md 示例使用绝对脚本路径（应使用 $SKILL_DIR）: {m.group(1)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill-dir", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = Path(args.skill_dir)
    skill_md_path = root / "SKILL.md"
    errors, warnings = [], []

    if not skill_md_path.exists():
        print(f"❌ 找不到 {skill_md_path}")
        sys.exit(1)
    skill_md = skill_md_path.read_text(encoding="utf-8")

    lint_frontmatter(skill_md, errors, warnings)
    lint_fences(skill_md_path, errors)
    lint_links(skill_md_path, root, errors)
    lint_hardcoded_paths(skill_md_path, errors)
    lint_abs_script_refs(skill_md, warnings)

    md_files = sorted(root.glob("guides/*.md")) + sorted(root.glob("runtime/**/*.md"))
    for f in md_files:
        lint_fences(f, errors)
        lint_links(f, root, errors)
        lint_hardcoded_paths(f, errors)

    if args.json:
        print(json.dumps({"errors": errors, "warnings": warnings}, ensure_ascii=False, indent=1))
    else:
        for e in errors:
            print(f"❌ {e}")
        for w in warnings:
            print(f"⚠️  {w}")
        if not errors:
            print(f"✅ lint 通过（{len(warnings)} 警告），扫描 {1 + len(md_files)} 个文件")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
