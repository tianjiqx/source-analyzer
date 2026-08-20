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

# 匹配文件引用：支持反引号内外的格式
# 格式1: `file.py:123` 或 `file.py:123-456`（标准）
# 格式2: file.py:123 或 file.py:123-456（非标准，但实际存在）
REF_RE = re.compile(r"`?([a-zA-Z0-9_/]+\.(?:go|py|rs|java|ts|js|c|cc|cpp|h|hpp|rb|php|kt|swift|scala)):(\d+)(?:-(\d+))?`?")
FORBIDDEN_NOTE = "[未验证]"


def find_md_files(analysis_dir: Path):
    return sorted(p for p in analysis_dir.rglob("*.md") if p.name != "EVIDENCE_REPORT.md")

def extract_module_path(analysis_dir: Path, md_file: Path) -> str:
    """从文档路径推断模块路径（用于多文件匹配时的路径推断）"""
    # 例如：analysis_dir="openviking-analysis/10-module-deep/crates", md_file=".../crates/00-overview/README.md"
    # 返回："crates"
    try:
        # 尝试从 analysis_dir 推断模块名
        # 如果 analysis_dir 包含 "10-module-deep"，取其后的第一级目录
        parts = analysis_dir.parts
        if "10-module-deep" in parts:
            idx = parts.index("10-module-deep")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        # 否则尝试从 md_file 推断
        rel = md_file.relative_to(analysis_dir.parent if "10-module-deep" in analysis_dir.parts else analysis_dir)
        if rel.parts and rel.parts[0] != "10-module-deep":
            return rel.parts[0]
    except (ValueError, IndexError):
        pass
    return ""

def try_auto_fix(project: Path, rel: str, l1: int, l2: int, module_path: str) -> str:
    """尝试自动修复错误的引用，返回修复后的引用字符串，如果无法修复返回 None"""
    # 1. 尝试查找文件
    candidates = [
        project / rel,
        project / module_path / rel if module_path else None,
    ]
    f = None
    for candidate in candidates:
        if candidate and candidate.exists():
            f = candidate
            break
    
    if f is None:
        # 文件不存在，尝试搜索同名文件
        try:
            matches = list(project.rglob(Path(rel).name))
            if len(matches) == 1:
                f = matches[0]
            elif len(matches) > 1 and module_path:
                # 多个匹配，尝试从模块路径推断；module_path 可能是简写（如
                # "crates-redis"）不命中真实目录（"crates/ragfs-cache-redis"），此时
                # candidates_for_fuzzy 回退到全部 matches 做后缀+关键段子串消歧。
                candidates_for_fuzzy = matches
                module_matches = [m for m in matches if module_path in str(m)]
                if len(module_matches) == 1:
                    f = module_matches[0]
                elif len(module_matches) > 1:
                    candidates_for_fuzzy = module_matches
                if f is None and len(candidates_for_fuzzy) > 1:
                    # 尝试匹配路径后缀 + 关键段子串（如 rel="redis/src/provider.rs"
                    # → 真实 "crates/ragfs-cache-redis/src/provider.rs"）
                    rel_parts = Path(rel).parts
                    if len(rel_parts) > 1:
                        suffix_parts = rel_parts[1:]
                        for m in candidates_for_fuzzy:
                            m_str = str(m)
                            if m_str.endswith("/".join(suffix_parts)):
                                key_part = rel_parts[0]
                                m_key_part = m.parts[-(len(suffix_parts) + 1)] if len(m.parts) > len(suffix_parts) else ""
                                if key_part in m_key_part:
                                    f = m
                                    break
        except ValueError:
            pass

        # 如果文件名完全匹配不到，尝试部分文件名匹配
        # 例如：bridge.h 匹配 yuanrong_bridge.h（子代理可能写简写）
        if f is None:
            stem = Path(rel).stem  # 去掉扩展名，如 "bridge"
            ext = Path(rel).suffix  # 如 ".h"
            try:
                partial_matches = []
                for m in project.rglob(f"*{stem}*{ext}"):
                    if module_path and module_path not in str(m):
                        continue
                    partial_matches.append(m)
                if len(partial_matches) == 1:
                    f = partial_matches[0]
            except ValueError:
                pass

    if f is None:
        return None
    
    # 2. 验证行号
    try:
        total_lines = sum(1 for _ in f.open(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    
    # 如果行号越界，尝试在文件中搜索相关内容
    if l1 > total_lines or l2 > total_lines:
        # 无法自动修复行号问题
        return None
    
    # 3. 构建修复后的引用
    # 使用项目根相对路径
    try:
        fixed_rel = f.relative_to(project)
    except ValueError:
        return None
    
    if l1 == l2:
        return f"{fixed_rel}:{l1}"
    else:
        return f"{fixed_rel}:{l1}-{l2}"


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


# —— 允许引用白名单（--filelist 注入）——
# 用于裸文件名/短路径消歧：子代理被要求只引用 fileList 内文件，验证时用同一
# 白名单把裸名（如 base.py）归位到唯一完整路径（如 openviking/parse/base.py）。
_FILELIST_PATHS = []          # 完整路径列表（项目根相对）
_FILELIST_BY_BASENAME = {}    # basename -> [完整路径,...]

def _load_filelist(filelist_arg):
    global _FILELIST_PATHS, _FILELIST_BY_BASENAME
    _FILELIST_PATHS, _FILELIST_BY_BASENAME = [], {}
    if not filelist_arg:
        return
    try:
        data = json.loads(Path(filelist_arg).read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return
        for item in data:
            if not isinstance(item, str):
                continue
            p = item.split(" (")[0].strip()  # 去掉 " (N 行)" 后缀
            if not p:
                continue
            _FILELIST_PATHS.append(p)
            bn = Path(p).name
            _FILELIST_BY_BASENAME.setdefault(bn, []).append(p)
    except (OSError, ValueError):
        pass

def _filelist_disambiguate(rel):
    """用白名单把裸文件名/短路径归位到唯一完整路径；无法唯一确定返回 None。"""
    if not _FILELIST_PATHS:
        return None
    bn = Path(rel).name
    cands = _FILELIST_BY_BASENAME.get(bn, [])
    # 优先：rel 是某白名单完整路径的子串/后缀（覆盖 'ragfs/src/lib.rs' 这类短路径）
    for p in _FILELIST_PATHS:
        if p == rel or p.endswith("/" + rel) or (p.startswith(rel + "/")) or (rel in p):
            if cands and p not in cands:
                cands.append(p)
    # 去掉重复
    seen, uniq = set(), []
    for p in cands:
        if p not in seen:
            seen.add(p); uniq.append(p)
    return uniq[0] if len(uniq) == 1 else None


def check_ref(project: Path, rel: str, l1: int, l2: int, content_mode: bool, claim_tokens=None, module_path: str = ""):
    """返回 (ok, reason)"""
    # 尝试多种路径：项目根相对 / 模块相对
    candidates = [
        project / rel,
        project / module_path / rel if module_path else None,
    ]
    f = None
    for candidate in candidates:
        if candidate and candidate.exists():
            f = candidate
            break
    
    if f is None:
        # 尝试宽松匹配：文件名在项目中唯一存在
        try:
            matches = list(project.rglob(Path(rel).name))
            if len(matches) == 1:
                f = matches[0]
            elif len(matches) > 1:
                # 多个匹配时，尝试从模块路径推断正确文件。
                # 注意：module_path 可能是简写（如 "crates-redis"），真实目录是
                # "crates/ragfs-cache-redis"（不含 "crates-redis" 子串），故按 module_path
                # 过滤可能得到 0 个匹配——这时应回退到「后缀 + 关键段子串」的模糊消歧。
                candidates_for_fuzzy = matches
                if module_path:
                    module_matches = [m for m in matches if module_path in str(m)]
                    if len(module_matches) == 1:
                        f = module_matches[0]
                    elif len(module_matches) > 1:
                        candidates_for_fuzzy = module_matches
                    # module_matches 为空（简写不命中真实目录）→ 保持 candidates_for_fuzzy = matches
                if f is None and len(candidates_for_fuzzy) > 1:
                    # 尝试匹配路径后缀 + 关键段子串（子代理常用模块内相对路径，如
                    # rel="redis/src/provider.rs"，真实为 "crates/ragfs-cache-redis/src/provider.rs"）
                    rel_parts = Path(rel).parts
                    if len(rel_parts) > 1:
                        suffix_parts = rel_parts[1:]
                        # 先精确后缀
                        for m in candidates_for_fuzzy:
                            if str(m).endswith(rel) or str(m).endswith("/".join(rel_parts)):
                                f = m
                                break
                        if f is None:
                            for m in candidates_for_fuzzy:
                                m_str = str(m)
                                if m_str.endswith("/".join(suffix_parts)):
                                    key_part = rel_parts[0]
                                    m_key_part = m.parts[-(len(suffix_parts) + 1)] if len(m.parts) > len(suffix_parts) else ""
                                    if key_part in m_key_part:  # 模糊匹配：redis in ragfs-cache-redis
                                        f = m
                                        break
                if f is None:
                    # 白名单消歧：裸文件名/短路径 → 注入 fileList 唯一完整路径。
                    # 多候选（如多个 lib.rs）时用「行号界内」过滤取唯一。
                    cands = []
                    for p in _FILELIST_PATHS:
                        if p == rel or p.endswith("/" + rel) or Path(p).name == Path(rel).name:
                            cands.append(p)
                    uniq = [p for p in dict.fromkeys(cands) if (project / p).exists()]
                    if len(uniq) == 1:
                        t = sum(1 for _ in (project / uniq[0]).open(encoding="utf-8", errors="replace"))
                        if 1 <= l1 and l2 >= l1 and l2 <= t:
                            return True, ""
                    elif len(uniq) > 1:
                        viable = []
                        for p in uniq:
                            t = sum(1 for _ in (project / p).open(encoding="utf-8", errors="replace"))
                            if 1 <= l1 and l2 >= l1 and l2 <= t:
                                viable.append(p)
                        if len(viable) == 1:
                            return True, ""
                    # 无法确定，标记为"文件不唯一"但降低严重性
                    return False, f"文件不唯一: {rel}（找到 {len(matches)} 个匹配，建议子代理使用完整路径）"
            else:
                return False, f"文件不存在: {rel}（尝试了项目根和模块路径）"
        except ValueError as e:
            return False, f"路径模式错误: {rel}（{e}）"
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
    ap.add_argument("--auto-fix", action="store_true", help="自动修复可确定的错误引用")
    ap.add_argument("--filelist", default=None, help="允许引用白名单 JSON（数组，每项为 'path (N 行)' 或 'path'），用于裸文件名/短路径消歧")
    args = ap.parse_args()
    _load_filelist(args.filelist)

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
    fixed_refs = 0
    for md in sampled:
        text = md.read_text(encoding="utf-8", errors="replace")
        module_path = extract_module_path(analysis_dir, md)
        if args.json:
            pass  # 静默模式
        elif module_path:
            print(f"📄 {md.relative_to(analysis_dir)} (module: {module_path})")
        refs = collect_refs(md)
        doc_bad = []
        doc_fixed = []
        
        # 如果需要自动修复，先收集所有需要修复的引用
        if args.auto_fix:
            fixes = []
            for m in REF_RE.finditer(text):
                line_start = text.rfind("\n", 0, m.start()) + 1
                if FORBIDDEN_NOTE in text[line_start:text.find("\n", m.start())]:
                    continue
                rel, l1 = m.group(1), int(m.group(2))
                l2 = int(m.group(3) or l1)
                tokens = extract_claim_tokens(text, m.span()) if args.content else None
                ok, reason = check_ref(project, rel, l1, l2, args.content, tokens, module_path)
                total_refs += 1
                if not ok:
                    # 尝试自动修复
                    fixed_path = try_auto_fix(project, rel, l1, l2, module_path)
                    if fixed_path:
                        fixes.append((m.group(0), fixed_path))
                        doc_fixed.append(f"{rel}:{l1}-{l2} → {fixed_path}")
                    else:
                        bad_refs += 1
                        doc_bad.append(f"{rel}:{l1}-{l2} — {reason}")
            
            # 应用修复
            if fixes:
                new_text = text
                for old_ref, new_ref in fixes:
                    new_text = new_text.replace(old_ref, new_ref)
                md.write_text(new_text, encoding="utf-8")
                fixed_refs += len(fixes)
                if not args.json:
                    print(f"  🔧 自动修复 {len(fixes)} 个引用")
        else:
            for m in REF_RE.finditer(text):
                line_start = text.rfind("\n", 0, m.start()) + 1
                if FORBIDDEN_NOTE in text[line_start:text.find("\n", m.start())]:
                    continue
                rel, l1 = m.group(1), int(m.group(2))
                l2 = int(m.group(3) or l1)
                tokens = extract_claim_tokens(text, m.span()) if args.content else None
                ok, reason = check_ref(project, rel, l1, l2, args.content, tokens, module_path)
                total_refs += 1
                if not ok:
                    bad_refs += 1
                    doc_bad.append(f"{rel}:{l1}-{l2} — {reason}")
        
        if len(refs) < args.min_per_doc:
            low_docs.append(f"{md.relative_to(analysis_dir)} — 引用数 {len(refs)} < {args.min_per_doc}")
        if doc_bad:
            results.append((md.relative_to(analysis_dir), doc_bad))
        if doc_fixed:
            results.append((md.relative_to(analysis_dir), doc_fixed, "fixed"))

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
