#!/usr/bin/env python3
"""evidence-check.py — 证据锚定真实性验证（防幻觉 file:line 引用）

扫描分析文档中的 `path/to/file.ext:LINE` 或 `path/to/file.ext:L1-L2` 引用，
比对被分析项目源码：
  1. 文件是否存在
  2. 行号是否在文件范围内
  3. （可选 --content）引用处附近的原文是否与文档论断中的关键 token 重叠

用法：
  python3 scripts/evidence-check.py <analysis-dir> --project <project-path> \
      [--sample 0.2] [--min-per-doc 3] [--content] [--json]

  analysis-dir : 分析输出目录（递归扫描 .md）
  --project    : 被分析项目根目录
  --sample     : 抽样比例（默认 0.2 = 20% 文档；1 = 全量）
  --min-per-doc: 每文档最低引用数（默认 3，低于则该文档不合格）
  --content    : 启用内容重叠校验（较慢，抽查阶段用）
输出：
  EVIDENCE_REPORT.md 写入 analysis-dir，含造假率与不合格文档清单
退出码：0=通过（造假率 < 阈值）；1=不合格（需全产出复审）；2=用法错误
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

REF_RE = re.compile(r"`([^`\n]+?\.(?:go|py|rs|java|ts|js|c|cc|cpp|h|hpp|go|rb|php|kt|swift|scala)):(\d+)(?:-(\d+))?(:\d+)?`?")
FORBIDDEN_NOTE = "[未验证]"


def find_md_files(analysis_dir: Path):
    return sorted(p for p in analysis_dir.rglob("*.md") if p.name != "EVIDENCE_REPORT.md")


def collect_refs(md: Path):
    text = md.read_text(encoding="utf-8", errors="replace")
    # 去掉 [未验证] 标注的论断行（规范允许显式放弃引用）
    refs = []
    for m in REF_RE.finditer(text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        line = text[line_start:text.find("\n", m.start())]
        if FORBIDDEN_NOTE in line:
            continue
        refs.append((m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))))
    return refs


def check_ref(project: Path, rel: str, l1: int, l2: int, content_mode: bool, claim_tokens=None):
    """返回 (ok, reason)"""
    f = project / rel
    if not f.exists():
        # 尝试宽松匹配：文件名在项目中唯一存在
        matches = list(project.rglob(Path(rel).name))
        if len(matches) != 1:
            return False, f"文件不存在: {rel}"
        f = matches[0]
    try:
        total = sum(1 for _ in f.open(encoding="utf-8", errors="replace"))
    except OSError as e:
        return False, f"读取失败: {e}"
    if l1 < 1 or l2 < l1:
        return False, f"行号非法: {l1}-{l2}"
    if l2 > total:
        return False, f"行号越界: {l2} > 文件总行数 {total} ({rel})"
    if content_mode and claim_tokens:
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        src = "\n".join(lines[l1 - 1:l2]).lower()
        hit = sum(1 for t in claim_tokens if t.lower() in src)
        if hit == 0 and len(claim_tokens) >= 2:
            return False, f"内容不重叠: 引用行不含论断关键词 {claim_tokens[:3]}"
    return True, ""


def extract_claim_tokens(text: str, ref_match_span):
    """取引用所在句中的代码标识符作为论断 token"""
    s = text.rfind("。", 0, ref_match_span[0]) + 1
    e = text.find("。", ref_match_span[1])
    claim = text[s:e if e != -1 else ref_match_span[1] + 40]
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", claim)
    return tokens[:5]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("analysis_dir")
    ap.add_argument("--project", required=True)
    ap.add_argument("--sample", type=float, default=0.2)
    ap.add_argument("--min-per-doc", type=int, default=3)
    ap.add_argument("--content", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    analysis_dir, project = Path(args.analysis_dir), Path(args.project)
    if not analysis_dir.is_dir():
        print(f"❌ 分析目录不存在: {analysis_dir}"); sys.exit(2)
    if not project.is_dir():
        print(f"❌ 项目目录不存在: {project}"); sys.exit(2)

    random.seed(args.seed)
    mds = find_md_files(analysis_dir)
    sample_n = max(1, int(len(mds) * args.sample)) if mds else 0
    sampled = random.sample(mds, min(sample_n, len(mds)))

    results, total_refs, bad_refs, low_docs = [], 0, 0, []
    for md in sampled:
        text = md.read_text(encoding="utf-8", errors="replace")
        refs = collect_refs(md)
        doc_bad = []
        for m in REF_RE.finditer(text):
            line_start = text.rfind("\n", 0, m.start()) + 1
            if FORBIDDEN_NOTE in text[line_start:text.find("\n", m.start())]:
                continue
            rel, l1 = m.group(1), int(m.group(2))
            l2 = int(m.group(3) or l1)
            tokens = extract_claim_tokens(text, m.span()) if args.content else None
            ok, reason = check_ref(project, rel, l1, l2, args.content, tokens)
            total_refs += 1
            if not ok:
                bad_refs += 1
                doc_bad.append(f"{rel}:{l1}-{l2} — {reason}")
        if len(refs) < args.min_per_doc:
            low_docs.append(f"{md.relative_to(analysis_dir)} — 引用数 {len(refs)} < {args.min_per_doc}")
        if doc_bad:
            results.append((md.relative_to(analysis_dir), doc_bad))

    fake_rate = bad_refs / total_refs if total_refs else 0.0
    passed = fake_rate < 0.05 and not low_docs
    summary = {
        "scanned_docs": len(sampled), "total_docs": len(mds),
        "total_refs": total_refs, "bad_refs": bad_refs,
        "fake_rate": round(fake_rate, 4), "passed": passed,
        "low_evidence_docs": low_docs,
    }
    if args.json:
        print(json.dumps({**summary, "bad_details": [(str(a), b) for a, b in results]}, ensure_ascii=False, indent=1))
    else:
        print(f"扫描文档: {len(sampled)}/{len(mds)}（抽样 {args.sample:.0%}）")
        print(f"引用总数: {total_refs}，失效引用: {bad_refs}，造假率: {fake_rate:.1%}")
        for doc, bads in results:
            print(f"\n❌ {doc}")
            for b in bads[:5]:
                print(f"   - {b}")
        for d in low_docs:
            print(f"⚠️  低证据密度: {d}")
        print("\n" + ("✅ 通过（造假率 < 5% 且无低密度文档）" if passed else "❌ 不合格：造假率超标或存在低密度文档 → 按协议全产出复审"))
        report = ["# 证据锚定验证报告", "",
                  f"- 抽样: {len(sampled)}/{len(mds)}（{args.sample:.0%}，seed={args.seed}）",
                  f"- 引用: {total_refs}，失效: {bad_refs}，造假率: {fake_rate:.1%}",
                  f"- 结论: {'✅ 通过' if passed else '❌ 不合格（全产出复审）'}", "",
                  "## 失效引用明细", ""]
        for doc, bads in results:
            report.append(f"### {doc}")
            report += [f"- {b}" for b in bads]
            report.append("")
        (analysis_dir / "EVIDENCE_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
