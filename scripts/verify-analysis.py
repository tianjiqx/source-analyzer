#!/usr/bin/env python3
"""
Verify Analysis Output

验证分析文档的完整性和质量。

Usage:
    python3 verify-analysis.py /path/to/analysis-dir [--completeness | --quality | --all]

输出:
    - 验证报告 (VERIFICATION_REPORT.md)
    - 缺失项列表
    - 质量评分
"""

import argparse
import os
import re
import sys
from pathlib import Path
from datetime import datetime


# 必需文件定义（支持两种结构：扁平式 00-README.md 和 目录式 00-project-level/README.md）
REQUIRED_FILES = {
    "00-README.md": {
        "sections": ["项目", "简介", "技术栈", "快速开始", "Stars", "License"],
        "forbidden": ["TBD", "TODO", "待补充", "xxx", "xx "],
        "min_tables": 2,
        "alt_paths": ["00-project-level/README.md"],  # 替代路径
    },
    "01-architecture.md": {
        "sections": ["模块", "架构", "数据流", "入口", "组件"],
        "forbidden": ["TBD", "TODO", "待补充"],
        "min_tables": 1,
        "alt_paths": ["00-project-level/architecture.md"],
    },
    "03-quality-score.md": {
        "sections": ["评分", "质量", "安全", "测试", "建议", "改进"],
        "forbidden": ["TBD", "TODO", "待补充", "评分 TBD"],
        "min_tables": 1,
        "alt_paths": ["00-project-level/quality-score.md"],
    },
    "04-learning-value.md": {
        "sections": ["学习", "借鉴", "场景", "推荐", "价值"],
        "forbidden": ["TBD", "TODO", "待补充", "推荐 TBD"],
        "min_tables": 1,
        "alt_paths": ["00-project-level/learning-value.md"],
    },
    "dependencies.md": {
        "sections": ["依赖", "版本", "许可证", "Stars"],
        "forbidden": ["TBD", "TODO", "待补充"],
        "min_tables": 1,
        "alt_paths": ["00-project-level/dependencies.md"],
    },
    "data-flow.md": {
        "sections": ["数据流", "核心", "模块", "mermaid"],
        "forbidden": ["TBD", "TODO", "待补充"],
        "min_tables": 0,
        "alt_paths": ["00-project-level/data-flow.md", "20-cross-module/data-flow.md"],
    },
    "INDEX.md": {
        "sections": ["导航", "索引", "概览"],
        "forbidden": [],
        "min_tables": 1,
        "alt_paths": [],
    },
}


# 孤儿检查排除的元/工作文件（非分析内容，无需被 INDEX 导航）
ORPHAN_EXCLUDE_NAMES = {
    'INDEX.md',                     # 导航文件本身
    'PLAN.md', 'PLAN_FULL.md',      # 计划
    'ANALYSIS_PLAN.md',             # 智能分析计划
    'RESEARCH_PLAN.md',             # 研究计划
    'FILE_LIST.md',                 # 文件列表
    'VERSION.md',                   # 版本记录
    'CONVENTIONS.md',               # 写作约定
    'VERIFICATION_REPORT.md', 'PLAN_VERIFICATION_REPORT.md',
    'RECURSIVE_MODE_REPORT.md', 'MAXIMUM_MODE_REPORT.md',
    'MERMAID_VALIDATION_REPORT.md', # 验证报告
    'project-meta.json',            # 项目元数据
    'EVALUATION_REPORT.md',         # 评估报告
}
ORPHAN_EXCLUDE_DIRS = {'task-prompts', '.handoff'}  # 工作目录（派发提示等）


def extract_links_from_markdown(content: str) -> list:
    """从 Markdown 内容中提取所有相对链接（.md 文件与目录链接）"""
    # 匹配 [text](path) 和 [text](path#anchor)
    pattern = r'\[([^\]]*)\]\(([^)]+)\)'
    links = []
    for match in re.finditer(pattern, content):
        text, path = match.group(1), match.group(2)
        # 去除 anchor (#xxx) 和 query (?xxx)
        path = path.split('#')[0].split('?')[0]
        # 关注 .md 文件与目录链接（以 / 结尾）
        if (path.endswith('.md') or path.endswith('/')) and not path.startswith('http'):
            links.append({'text': text, 'path': path})
    return links


def check_index_consistency(analysis_dir: Path) -> dict:
    """检查 INDEX.md 与实际文件的一致性

    检测两类问题：
    1. 幽灵引用：任意 INDEX.md 引用了文件，但文件实际不存在
    2. 孤儿文件：文件实际存在，但**任何层级**的 INDEX.md 均未引用
       （根 INDEX + 各模块目录内的 INDEX 都计入，适合 600+ 文件的大语料）
    """
    result = {
        'index_exists': False,
        'total_links': 0,
        'phantom_refs': [],      # INDEX 有但文件不存在
        'orphan_files': [],      # 文件存在但任何 INDEX 均未引用
        'valid_links': 0,
        'details': [],
    }

    # Resolve to absolute path to avoid relative_to() errors
    analysis_dir = analysis_dir.resolve()
    
    index_path = analysis_dir / 'INDEX.md'
    if not index_path.exists():
        result['details'].append('INDEX.md 不存在，跳过一致性检查')
        return result

    result['index_exists'] = True

    # 收集所有 INDEX.md（根 + 任意层级，如 10-module-deep/<module>/INDEX.md）
    index_files = [index_path]
    for nested in analysis_dir.rglob('INDEX.md'):
        if nested == index_path:
            continue
        rel = nested.relative_to(analysis_dir)
        if any(part.startswith('.') for part in rel.parts):
            continue
        index_files.append(nested)
    result['details'].append(f'索引文件数: {len(index_files)}（根 + 模块级）')

    # 汇总所有 INDEX 的引用
    referenced_paths = set()
    for index_file in index_files:
        content = index_file.read_text()
        links = extract_links_from_markdown(content)
        result['total_links'] += len(links)
        for link in links:
            ref_path = link['path']
            # 解析相对路径（相对于该 INDEX.md 所在目录）
            abs_path = (index_file.parent / ref_path).resolve()
            if abs_path.is_dir():
                # 目录链接（如 [00-project-level/](00-project-level/)）：
                # 视为覆盖该目录下全部 .md 文件（该目录是导航单元，内部由自身/子 INDEX 负责）
                referenced_paths.update(str(f.resolve()) for f in abs_path.rglob('*.md'))
                result['valid_links'] += 1
                continue
            referenced_paths.add(str(abs_path))
            if abs_path.exists():
                result['valid_links'] += 1
            else:
                result['phantom_refs'].append({
                    'text': link['text'],
                    'path': ref_path,
                    'resolved': str(abs_path),
                    'index': str(index_file.relative_to(analysis_dir)),
                })

    # 反向检查：扫描所有 .md 文件，找出未被任何 INDEX 引用的
    all_md_files = set()
    for md_file in analysis_dir.rglob('*.md'):
        rel = md_file.relative_to(analysis_dir)
        # 排除验证报告自身、导航/元/工作文件、隐藏文件
        if md_file.name in ORPHAN_EXCLUDE_NAMES:
            continue
        if any(part in ORPHAN_EXCLUDE_DIRS for part in rel.parts):
            continue
        if any(part.startswith('.') for part in rel.parts):
            continue
        all_md_files.add(str(md_file.resolve()))

    orphan_paths = all_md_files - referenced_paths
    for orphan in sorted(orphan_paths):
        rel_path = str(Path(orphan).relative_to(analysis_dir))
        result['orphan_files'].append(rel_path)

    # 陈旧状态检查：INDEX 标记"待生成/失败/⏳"但目标文件已实际存在
    # （实战：LightRAG LEARN_03 重试成功后 INDEX 未回写，仍标 ⏳）
    result['stale_pending'] = []
    stale_markers = ('⏳', '待生成', '未生成', '生成失败', '待补充')
    for index_file in index_files:
        content = index_file.read_text()
        for line_no, line in enumerate(content.splitlines(), 1):
            if not any(marker in line for marker in stale_markers):
                continue
            # 候选 1：该行链接到已存在的 .md 文件
            linked = False
            for link in extract_links_from_markdown(line):
                abs_path = (index_file.parent / link['path']).resolve()
                if abs_path.suffix == '.md' and abs_path.exists():
                    result['stale_pending'].append({
                        'file': str(abs_path.relative_to(analysis_dir)),
                        'index': str(index_file.relative_to(analysis_dir)),
                        'line': line_no,
                        'line_text': line.strip()[:80],
                    })
                    linked = True
            if linked:
                continue
            # 候选 2：无链接的裸标记行——按行内命名 token（如 LEARN_03 / LEARN_03_XXX）
            # 在 INDEX 同目录树中匹配实际存在的文件名
            for token in re.findall(r'[A-Za-z0-9]+_[A-Z0-9_]+|\bLEARN_\d+\b|\b[A-Z]+_\d+\b', line):
                for hit in index_file.parent.rglob(f'*{token}*.md'):
                    rel_hit = hit.relative_to(analysis_dir)
                    # 命中文件不能自身就是那个 INDEX
                    if hit.name != 'INDEX.md':
                        result['stale_pending'].append({
                            'file': str(rel_hit),
                            'index': str(index_file.relative_to(analysis_dir)),
                            'line': line_no,
                            'line_text': line.strip()[:80],
                        })
                        break

    return result


def check_glossary(analysis_dir: Path) -> dict:
    """检查 Glossary 提案制落地情况
    
    SKILL.md 要求：项目级扫描时创建 Glossary.md（核心概念统一术语表）。
    检查：根目录或 00-project-level/ 下存在 Glossary.md 且非空（≥3 条术语行）。
    """
    candidates = [
        analysis_dir / "Glossary.md",
        analysis_dir / "00-project-level" / "Glossary.md",
        analysis_dir / "glossary.md",
    ]
    glossary_path = next((p for p in candidates if p.exists()), None)
    if glossary_path is None:
        return {"exists": False, "path": None, "terms": 0, "ok": False,
                "message": "缺少 Glossary.md（SKILL.md：项目级扫描时必建统一术语表）"}
    try:
        content = glossary_path.read_text()
    except (OSError, UnicodeDecodeError) as e:
        return {"exists": True, "path": str(glossary_path), "terms": 0, "ok": False,
                "message": f"Glossary.md 读取失败: {e}"}
    # 术语行近似计数：表格数据行（跳过表头与分隔线） 或 以 - 开头且含 →/: 的行
    lines = content.splitlines()
    table_data_lines = []
    in_table = False
    for ln in lines:
        s = ln.strip()
        if s.startswith("|") and s.count("|") >= 2:
            if "---" in s:
                in_table = True  # 分隔线之后才是数据行
                continue
            if in_table:
                table_data_lines.append(ln)
        else:
            in_table = False
    term_lines = table_data_lines + [ln for ln in lines
                  if ln.strip().startswith("-") and ("→" in ln or ":" in ln)]
    ok = len(term_lines) >= 3
    return {"exists": True, "path": str(glossary_path), "terms": len(term_lines), "ok": ok,
            "message": "" if ok else f"Glossary.md 术语条目过少（{len(term_lines)} < 3）"}


def _mermaid_blocks(content: str) -> list:
    """提取 markdown 中所有 mermaid 代码块的文本"""
    blocks = []
    parts = content.split("```mermaid")
    for part in parts[1:]:
        end = part.find("```")
        if end != -1:
            blocks.append(part[:end])
    return blocks


def check_diagram_types(analysis_dir: Path) -> dict:
    """检查图表类型多样性（学习视角：原理讲解型图 + 空间布局图）

    检查（均为 warning 级，不影响通过率）：
    1. 40-learning/ 学习卡片：缺 mermaid 图报 warning；至少 30% 卡片的 mermaid 块
       含讲解型图型语法特征（quadrantChart/timeline/gitGraph/Note over 等图内语法，
       不匹配正文自然语言，避免假通过）。
    2. 含"物理布局/文件格式/页结构/内存布局"章节的文档：要求 ASCII 字节图组合证据
       （box-drawing 行 ≥2 或 0x 十六进制偏移行 ≥2），缺失报 warning。
    """
    warnings = []
    # 讲解型图的 mermaid 图型语法特征（只在 mermaid 块内匹配）
    explanatory_kw = ["quadrantChart", "timeline", "gitGraph", "Note over", "Note right", "Note left", "note right of", "note left of"]
    # 对比型图特征：同一 mermaid 块内出现两个 subgraph（双列对比的语法特征）
    layout_section_kw = ["物理布局", "文件格式", "页结构", "内存布局", "磁盘布局", "存储格式"]
    
    # 1) 学习卡片讲解型图覆盖率
    learning_dir = analysis_dir / "40-learning"
    cards = list(learning_dir.glob("LEARN_*.md")) if learning_dir.exists() else []
    explanatory_cards = 0
    for card in cards:
        c = card.read_text(errors="ignore")
        blocks = _mermaid_blocks(c)
        if not blocks:
            warnings.append(f"学习卡片缺 mermaid 图: {card.name}")
        # 讲解型判定：任一 mermaid 块含图型语法特征，或含 ≥2 个 subgraph（对比双列）
        is_explanatory = any(any(k in b for k in explanatory_kw) for b in blocks) \
                          or any(b.count("subgraph ") >= 2 for b in blocks)
        if is_explanatory:
            explanatory_cards += 1
    if cards:
        rate = explanatory_cards / len(cards)
        if rate < 0.3:
            warnings.append(f"讲解型图覆盖率低: {explanatory_cards}/{len(cards)} ({rate:.0%} < 30%)——原理讲解型图（quadrantChart/timeline/gitGraph/Note/双列对比 subgraph）不足")
    
    # 2) 布局章节的字节图证据（组合条件，防正文单词假通过）
    layout_docs = 0
    layout_missing = []
    for md in analysis_dir.glob("**/*.md"):
        c = md.read_text(errors="ignore")
        if any(k in c for k in layout_section_kw):
            layout_docs += 1
            box_lines = sum(1 for ln in c.splitlines() if any(ch in ln for ch in "┌├└│┤"))
            hex_lines = sum(1 for ln in c.splitlines() if re.search(r"0x[0-9A-Fa-f]+", ln))
            if box_lines < 2 and hex_lines < 2:
                layout_missing.append(str(md.relative_to(analysis_dir)))
    if layout_missing:
        warnings.append(f"{len(layout_missing)} 个含布局/格式章节的文档缺字节级布局图（需 box-drawing ≥2 行或 0x 偏移 ≥2 行）: " + "; ".join(layout_missing[:5]) + ("..." if len(layout_missing) > 5 else ""))
    
    return {"cards": len(cards), "explanatory_cards": explanatory_cards,
            "layout_docs": layout_docs, "warnings": warnings,
            "ok": len(warnings) == 0}


def format_index_consistency(index_consistency: dict) -> str:
    """格式化 INDEX.md 一致性检查摘要"""
    if not index_consistency:
        return "未检查"
    if not index_consistency['index_exists']:
        return "❌ INDEX.md 不存在"
    phantom = len(index_consistency['phantom_refs'])
    orphan = len(index_consistency['orphan_files'])
    stale = len(index_consistency.get('stale_pending', []))
    if phantom == 0 and orphan == 0 and stale == 0:
        return "✅ 完全一致"
    parts = []
    if phantom:
        parts.append(f"{phantom} 个幽灵引用")
    if orphan:
        parts.append(f"{orphan} 个孤儿文件")
    if stale:
        parts.append(f"{stale} 个陈旧待生成标记")
    return "⚠️ " + ", ".join(parts)


def format_index_consistency_detail(index_consistency: dict) -> str:
    """格式化 INDEX.md 一致性检查详情"""
    if not index_consistency:
        return "未检查"
    if not index_consistency['index_exists']:
        return "❌ INDEX.md 不存在，跳过一致性检查"
    
    lines = []
    lines.append(f"**引用总数**: {index_consistency['total_links']}")
    lines.append(f"**有效引用**: {index_consistency['valid_links']}")
    lines.append(f"**幽灵引用**: {len(index_consistency['phantom_refs'])}")
    lines.append(f"**孤儿文件**: {len(index_consistency['orphan_files'])}")
    lines.append(f"**陈旧待生成标记**: {len(index_consistency.get('stale_pending', []))}")
    lines.append("")
    
    if index_consistency.get('stale_pending'):
        lines.append("### 陈旧待生成标记（文件已存在但 INDEX 仍标 ⏳/待生成——重试成功后未回写）")
        lines.append("")
        for s in index_consistency['stale_pending'][:10]:
            lines.append(f"- `{s['file']}` ← {s['index']}:{s['line']}「{s['line_text']}」")
        if len(index_consistency['stale_pending']) > 10:
            lines.append(f"- ... 还有 {len(index_consistency['stale_pending']) - 10} 个")
        lines.append("")
    
    if index_consistency['phantom_refs']:
        lines.append("### 幽灵引用（INDEX 有但文件不存在）")
        lines.append("")
        for ref in index_consistency['phantom_refs'][:10]:
            lines.append(f"- `{ref['path']}` ({ref['text']})")
        if len(index_consistency['phantom_refs']) > 10:
            lines.append(f"- ... 还有 {len(index_consistency['phantom_refs']) - 10} 个")
        lines.append("")
    
    if index_consistency['orphan_files']:
        lines.append("### 孤儿文件（文件存在但 INDEX 未引用）")
        lines.append("")
        for f in index_consistency['orphan_files'][:10]:
            lines.append(f"- `{f}`")
        if len(index_consistency['orphan_files']) > 10:
            lines.append(f"- ... 还有 {len(index_consistency['orphan_files']) - 10} 个")
        lines.append("")
    
    if not index_consistency['phantom_refs'] and not index_consistency['orphan_files']:
        lines.append("✅ INDEX.md 与实际文件完全一致")
    
    return "\n".join(lines)


def resolve_required_file(analysis_dir: Path, filename: str) -> Path:
    """解析必需文件路径：根目录 → 00-project-level/ → REQUIRED_FILES.alt_paths
    
    支持两种布局 + alt_paths：
    - 扁平式: 00-README.md, 01-architecture.md, ...
    - 目录式: 00-project-level/README.md, ...
    - alt_paths: REQUIRED_FILES 显式声明的替代路径（如 20-cross-module/data-flow.md）
    """
    # 1. 先检查根目录（扁平式布局）
    root_path = analysis_dir / filename
    if root_path.exists():
        return root_path
    
    # 2. 检查 00-project-level/ 目录（目录式布局）
    # 去掉文件名前缀数字（如 00-, 01- 等）
    base_name = re.sub(r'^\d+-', '', filename)
    project_level = analysis_dir / '00-project-level' / base_name
    if project_level.exists():
        return project_level
    
    # 3. 也检查原始文件名在 00-project-level/ 下
    project_level_original = analysis_dir / '00-project-level' / filename
    if project_level_original.exists():
        return project_level_original
    
    # 4. 检查 REQUIRED_FILES 中声明的 alt_paths
    alt_paths = REQUIRED_FILES.get(filename, {}).get("alt_paths", [])
    for alt in alt_paths:
        alt_path = analysis_dir / alt
        if alt_path.exists():
            return alt_path
    
    # 返回默认路径（用于报错）
    return project_level


def check_file_exists(analysis_dir: Path, filename: str) -> dict:
    """检查文件是否存在"""
    filepath = resolve_required_file(analysis_dir, filename)
    exists = filepath.exists()

    return {
        "file": filename,
        "exists": exists,
        "size": filepath.stat().st_size if exists else 0,
        "status": "✅" if exists else "❌",
        "resolved": str(filepath),
    }


def check_sections(content: str, required_sections: list) -> list:
    """检查必需章节"""
    missing = []
    for section in required_sections:
        # 检查是否包含关键词（不区分大小写）
        if not re.search(section, content, re.IGNORECASE):
            missing.append(section)
    return missing


# 禁止词豁免列表（命令行 --forbidden-allow 可追加；用于包名等合法词汇，如 todo）
FORBIDDEN_ALLOW = []


def strip_code(content: str) -> str:
    """剥离 fenced 代码块与行内代码，避免目录树/包名/源码引用被误判为占位符"""
    # 剥离 fenced 代码块（``` ... ```）
    content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    # 剥离行内代码 `...`
    content = re.sub(r'`[^`]*`', '', content)
    return content


def check_forbidden(content: str, forbidden_words: list) -> list:
    """检查禁止词（先剥离代码块/行内代码；FORBIDDEN_ALLOW 内的词不报）

    大小写语义：拉丁词（TODO/TBD/xxx）大小写敏感匹配，
    避免把小写名词（如工具名 todo、包名 workflow）误判为占位符；
    中文词（待补充）无大小写，直接匹配。
    """
    found = []
    stripped = strip_code(content)
    for word in forbidden_words:
        if word in stripped:
            # 豁免列表：word 出现在某个豁免词内（如禁止词 TODO vs 豁免 todo_write）
            if any(word in a for a in FORBIDDEN_ALLOW):
                continue
            found.append(word)
    return found


def count_tables(content: str) -> int:
    """统计 Markdown 表格数量"""
    # Markdown 表格以 | 开头
    table_lines = [line for line in content.split("\n") if line.strip().startswith("|")]
    # 每表格至少 3 行 (header, separator, content)
    tables = max(1, len(table_lines) // 4)
    return tables


def count_code_blocks(content: str) -> int:
    """统计代码块数量"""
    return content.count("```") // 2  # 每个代码块有 2 个 ```


def check_distillation_sections(content: str) -> dict:
    """检查蒸馏章节（设计洞察和隐含陷阱）"""
    line_count = content.count("\n") + 1
    result = {
        "has_insights": False,
        "has_gotchas": False,
        "insight_count": 0,
        "gotcha_count": 0,
        "has_name_removal_test": False,
        "issues": []
    }
    
    # 检查设计洞察章节
    insight_patterns = [
        r"##\s*(\d+\.\s*)?💡\s*设计洞察",
        r"##\s*(\d+\.\s*)?设计洞察",
        r"##\s*(\d+\.\s*)?Design\s*Insights",
        r"设计洞察",  # Fallback: any mention
    ]
    for pattern in insight_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            result["has_insights"] = True
            break
    
    # 统计原则数量（查找 **原则** 或 **Golden Rule** 或 > **原则 N** 或 > **原则** 或数字列表格式）
    principle_patterns = [
        r"\*\*原则\s*\d+\*\*",
        r"\*\*Golden\s*Rule\s*\d+\*\*",
        r"###\s*原则\s*\d+",
        r">\s*\*\*原则\s*\d+\*\*",  # Match "> **原则 1**:" format
        r"原则\s*\d+[:：]",  # Match "原则 1:" or "原则 1："
        r">\s*\*\*原则\*\*[:：]",  # Match "> **原则**:" format (unnumbered)
        r"^\d+\.\s*\*\*[^*]+\*\*[:：]",  # Match "1. **标题**:" format (numbered list with bold title)
        r"###\s*(?:洞察|Insight)\s*\d+",  # Match "### 洞察 1:"（实战格式，LightRAG 复盘确认）
        r"\*\*(?:洞察|Insight)\s*\d+\*\*",
    ]
    for pattern in principle_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
        result["insight_count"] = max(result["insight_count"], len(matches))
    
    # 检查隐含陷阱章节
    gotcha_patterns = [
        r"##\s*(\d+\.\s*)?⚠️\s*隐含陷阱",
        r"##\s*(\d+\.\s*)?隐含陷阱",
        r"##\s*(\d+\.\s*)?Gotchas",
        r"##\s*(\d+\.\s*)?Pitfalls",
        r"隐含陷阱",  # Fallback: any mention
    ]
    for pattern in gotcha_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            result["has_gotchas"] = True
            break
    
    # 统计陷阱数量（查找 **陷阱** 或 **Gotcha** 或 > **陷阱 N** 或 > **陷阱** 或数字列表格式）
    gotcha_count_patterns = [
        r"\*\*陷阱\s*\d+\*\*",
        r"\*\*Gotcha\s*\d+\*\*",
        r"###\s*陷阱\s*\d+",
        r">\s*\*\*陷阱\s*\d+\*\*",  # Match "> **陷阱 1**:" format
        r"陷阱\s*\d+[:：]",  # Match "陷阱 1:" or "陷阱 1："
        r">\s*\*\*陷阱\*\*[:：]",  # Match "> **陷阱**:" format (unnumbered)
        r"^\d+\.\s*\*\*[^*]+\*\*[:：]",  # Match "1. **标题**:" format (numbered list with bold title)
        r"###\s*(?:陷阱|Gotcha)\s*\d+",  # Match "### 陷阱 1:"（实战格式）
        r"\*\*(?:陷阱|Gotcha)\s*\d+\*\*",
    ]
    for pattern in gotcha_count_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
        result["gotcha_count"] = max(result["gotcha_count"], len(matches))
    
    # 检查去名检验
    name_test_patterns = [
        r"去名检验",
        r"Name[-\s]Removal\s*Test",
        r"通用原则"
    ]
    for pattern in name_test_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            result["has_name_removal_test"] = True
            break
    
    # 生成问题列表（阈值按文档厚度分档：厚文档要求更高——实战确认浅模块 1 条洞察也通过的问题）
    # 分档：<80 行=薄(1条)；80-150 行=中(2条)；≥150 行=厚(3条)
    min_required = 1 if line_count < 80 else (2 if line_count < 150 else 3)
    if not result["has_insights"]:
        result["issues"].append("缺少💡设计洞察章节")
    elif result["insight_count"] < min_required:
        result["issues"].append(f"设计洞察数量不足（{result['insight_count']} < {min_required}，{line_count} 行文档按分档要求 {min_required} 条）")
    
    if not result["has_gotchas"]:
        result["issues"].append("缺少⚠️隐含陷阱章节")
    elif result["gotcha_count"] < min_required:
        result["issues"].append(f"隐含陷阱数量不足（{result['gotcha_count']} < {min_required}，{line_count} 行文档按分档要求 {min_required} 条）")
    
    if not result["has_name_removal_test"]:
        result["issues"].append("缺少去名检验说明")
    
    return result


def check_file_content(analysis_dir: Path, filename: str) -> dict:
    """检查单个文件内容"""
    filepath = resolve_required_file(analysis_dir, filename)

    if not filepath.exists():
        return {
            "file": filename,
            "exists": False,
            "sections_ok": False,
            "forbidden_ok": True,
            "tables_ok": False,
            "code_blocks_ok": True,
            "issues": ["文件不存在"],
            "score": 0,
        }
    
    content = filepath.read_text()
    requirements = REQUIRED_FILES.get(filename, {})
    
    # 检查章节
    required_sections = requirements.get("sections", [])
    missing_sections = check_sections(content, required_sections)
    sections_ok = len(missing_sections) == 0
    
    # 检查禁止词
    forbidden_words = requirements.get("forbidden", [])
    found_forbidden = check_forbidden(content, forbidden_words)
    forbidden_ok = len(found_forbidden) == 0
    
    # 检查表格
    min_tables = requirements.get("min_tables", 1)
    table_count = count_tables(content)
    tables_ok = table_count >= min_tables
    
    # 检查代码块
    min_code_blocks = requirements.get("min_code_blocks", 0)
    code_block_count = count_code_blocks(content)
    code_blocks_ok = code_block_count >= min_code_blocks
    
    # 检查蒸馏章节（设计洞察和隐含陷阱）
    # 仅对架构、依赖、模块分析文档检查
    # 跳过：README/INDEX（元数据）、quality-score/learning-value（汇总文档）
    skip_distillation_names = {
        "00-README.md", "INDEX.md",
        "03-quality-score.md", "04-learning-value.md",
    }
    skip_distillation = filename in skip_distillation_names
    if skip_distillation:
        distillation = {"issues": []}
        distillation_ok = True
    else:
        distillation = check_distillation_sections(content)
        distillation_ok = len(distillation["issues"]) == 0
    
    # 收集问题
    issues = []
    if missing_sections:
        issues.append(f"缺失章节: {', '.join(missing_sections)}")
    if found_forbidden:
        issues.append(f"包含禁止词: {', '.join(found_forbidden)}")
    if table_count < min_tables:
        issues.append(f"表格不足: {table_count} < {min_tables}")
    if code_block_count < min_code_blocks:
        issues.append(f"代码块不足: {code_block_count} < {min_code_blocks}")
    issues.extend(distillation["issues"])
    
    # 计算分数
    score = 100
    score -= len(missing_sections) * 15
    score -= len(found_forbidden) * 20
    score -= max(0, min_tables - table_count) * 10
    score -= len(distillation["issues"]) * 10  # 蒸馏问题每个扣10分
    score = max(0, score)
    
    return {
        "file": filename,
        "exists": True,
        "size": filepath.stat().st_size,
        "sections_ok": sections_ok,
        "forbidden_ok": forbidden_ok,
        "tables_ok": tables_ok,
        "code_blocks_ok": code_blocks_ok,
        "distillation_ok": distillation_ok,
        "tables_count": table_count,
        "code_blocks_count": code_block_count,
        "distillation": distillation,
        "issues": issues,
        "score": score,
    }


def generate_verification_report(analysis_dir: str, results: list, index_consistency: dict = None,
                                 glossary_check: dict = None, diagram_check: dict = None) -> str:
    """生成验证报告"""
    analysis_path = Path(analysis_dir)
    report_file = analysis_path / "VERIFICATION_REPORT.md"
    
    # 计算总体分数
    total_score = 0
    completed_files = 0
    for r in results:
        if r["exists"]:
            total_score += r["score"]
            completed_files += 1
    
    avg_score = total_score / completed_files if completed_files > 0 else 0
    
    # 检查 INDEX.md
    index_exists = any(r["file"] == "INDEX.md" and r["exists"] for r in results)
    
    content = f"""# 分析验证报告

**分析目录**: `{analysis_dir}`
**验证时间**: {datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## 总体评估

| 指标 | 结果 |
|------|------|
| **文件完整性** | {completed_files}/{len(REQUIRED_FILES)} |
| **平均质量分数** | {avg_score:.0f}/100 |
| **INDEX.md** | {'✅ 存在' if index_exists else '❌ 缺失'} |
| **INDEX 一致性** | {format_index_consistency(index_consistency) if index_consistency else '未检查'} |
| **Glossary 术语表** | {('✅ ' + str(glossary_check['terms']) + ' 条术语') if glossary_check and glossary_check['ok'] else ('⚠️ ' + glossary_check['message']) if glossary_check else '未检查'} |
| **图表多样性** | {((str(diagram_check['explanatory_cards']) + '/' + str(diagram_check['cards']) + ' 学习卡片含讲解型图') if diagram_check and diagram_check['cards'] else ('⚠️ ' + str(len(diagram_check['warnings'])) + ' 项提示') if diagram_check and diagram_check['warnings'] else '✅ 无提示') if diagram_check else '未检查'} |
| **评估等级** | {'✅ 优秀' if avg_score >= 85 else '⚠️ 良好' if avg_score >= 70 else '❌ 需改进'} |

---

## INDEX.md 一致性检查

{format_index_consistency_detail(index_consistency) if index_consistency else '未检查'}

---

## Glossary 与图表多样性

**Glossary 术语表**: {('✅ ' + str(glossary_check.get('terms', 0)) + ' 条术语（' + glossary_check.get('path', '') + '）') if glossary_check and glossary_check.get('ok') else ('❌/⚠️ ' + glossary_check.get('message', '')) if glossary_check else '未检查'}

**图表类型多样性**:
{(chr(10).join('- ' + w for w in diagram_check['warnings']) if diagram_check and diagram_check.get('warnings') else '- ✅ 学习卡片讲解型图覆盖率达标，布局章节均有字节级布局图') if diagram_check else '未检查'}

---

## 文件检查

| 文件 | 存在 | 章节 | 禁止词 | 表格 | 代码块 | 蒸馏 | 分数 |
|------|------|------|--------|------|--------|------|------|
"""
    
    for r in results:
        status = "✅" if r["exists"] else "❌"
        sections = "✅" if r.get("sections_ok", True) else "❌"
        forbidden = "✅" if r.get("forbidden_ok", True) else "❌"
        tables = "✅" if r.get("tables_ok", True) else "❌"
        code = "✅" if r.get("code_blocks_ok", True) else "❌"
        distillation = "✅" if r.get("distillation_ok", True) else "❌"
        score = r.get("score", 0) if r["exists"] else "N/A"
        
        content += f"| {r['file']} | {status} | {sections} | {forbidden} | {tables} | {code} | {distillation} | {score} |\n"
    
    content += """
---

## 问题详情

"""
    
    has_issues = False
    for r in results:
        if r.get("issues"):
            has_issues = True
            content += f"### {r['file']}\n\n"
            for issue in r["issues"]:
                content += f"- ⚠️ {issue}\n"
            content += "\n"
    
    if not has_issues:
        content += "✅ 未发现明显问题\n"
    
    content += """
---

## 改进建议

"""
    
    # 生成建议
    suggestions = []
    for r in results:
        if not r["exists"]:
            suggestions.append(f"1. **创建 {r['file']}**: 文件缺失，需要生成")
        elif r.get("issues"):
            for issue in r["issues"]:
                if "缺失章节" in issue:
                    suggestions.append(f"- **{r['file']}**: 补充缺失的章节 ({issue})")
                elif "禁止词" in issue:
                    suggestions.append(f"- **{r['file']}**: 移除占位符 ({issue})")
                elif "表格不足" in issue:
                    suggestions.append(f"- **{r['file']}**: 添加更多数据表格")
                elif "代码块不足" in issue:
                    suggestions.append(f"- **{r['file']}**: 添加更多代码示例")
    
    if suggestions:
        content += "\n".join(suggestions)
    else:
        content += "✅ 无需改进建议"
    
    content += f"""

---

*生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}*
"""
    
    report_file.write_text(content)
    return str(report_file)


def verify_analysis(analysis_dir: str, mode: str = "all") -> list:
    """验证分析文档"""
    analysis_path = Path(analysis_dir)
    
    if not analysis_path.exists():
        print(f"Error: Analysis directory not found: {analysis_dir}")
        sys.exit(1)
    
    results = []
    
    for filename in REQUIRED_FILES:
        if mode == "completeness":
            # 只检查文件存在
            result = check_file_exists(analysis_path, filename)
            results.append(result)
        else:
            # 检查内容
            result = check_file_content(analysis_path, filename)
            results.append(result)
    
    return results


def check_maximum_mode(analysis_dir: str) -> dict:
    """检查是否满足最大化模式要求
    
    最大化模式要求：
    1. 三层分析全开（项目级 + 模块级 + 文件粒度）
    2. 专项模板全开（根据项目类型，11个专项文档）
    3. 附加分析（核心功能、功能实现逻辑、ADR、性能建模等）
    4. 文档总数 >= 40
    """
    analysis_path = Path(analysis_dir)
    
    result = {
        "is_maximum_mode": False,
        "total_files": 0,
        "layer1_ok": False,
        "layer2_ok": False,
        "layer3_ok": False,
        "specialized_templates_ok": False,
        "additional_analysis_ok": False,
        "issues": [],
        "details": {}
    }
    
    # 1. 统计总文件数
    md_files = list(analysis_path.glob("**/*.md"))
    result["total_files"] = len(md_files)
    result["details"]["total_files"] = result["total_files"]
    
    # 2. 检查 Layer 1: 项目级分析
    layer1_files = ["00-README.md", "01-architecture.md", "03-quality-score.md", "04-learning-value.md", "dependencies.md", "data-flow.md"]
    layer1_exists = [f for f in layer1_files if resolve_required_file(analysis_path, f).exists()]
    result["layer1_ok"] = len(layer1_exists) >= 5
    result["details"]["layer1"] = {
        "required": layer1_files,
        "exists": layer1_exists,
        "count": len(layer1_exists)
    }
    if not result["layer1_ok"]:
        result["issues"].append(f"Layer 1 不完整：{len(layer1_exists)}/6 个文件")
    
    # 3. 检查 Layer 2: 模块级分析
    module_dirs = [d for d in analysis_path.iterdir() if d.is_dir() and d.name.startswith("10-module-")]
    module_files = []
    for module_dir in module_dirs:
        module_files.extend(module_dir.glob("*.md"))
    result["layer2_ok"] = len(module_files) >= 5
    result["details"]["layer2"] = {
        "module_dirs": len(module_dirs),
        "module_files": len(module_files)
    }
    if not result["layer2_ok"]:
        result["issues"].append(f"Layer 2 不完整：{len(module_files)} 个模块文件（需要 >= 5）")
    
    # 4. 检查 Layer 3: 文件粒度分析
    file_analysis_dirs = [d for d in analysis_path.iterdir() if d.is_dir() and d.name.startswith("20-file-")]
    file_analysis_files = []
    for file_dir in file_analysis_dirs:
        file_analysis_files.extend(file_dir.glob("*.md"))
    result["layer3_ok"] = len(file_analysis_files) >= 10
    result["details"]["layer3"] = {
        "file_dirs": len(file_analysis_dirs),
        "file_analysis_files": len(file_analysis_files)
    }
    if not result["layer3_ok"]:
        result["issues"].append(f"Layer 3 不完整：{len(file_analysis_files)} 个文件分析（需要 >= 10）")
    
    # 5. 检查专项模板（根据项目类型）
    # 检测项目类型
    project_type = "unknown"
    if any((analysis_path / f).exists() for f in ["llm-agent-overview.md", "agent-architecture.md"]):
        project_type = "llm-agent"
    elif any((analysis_path / f).exists() for f in ["database-overview.md", "storage-engine.md"]):
        project_type = "database"
    
    specialized_count = 0
    if project_type == "llm-agent":
        llm_agent_files = [
            "llm-agent-overview.md",
            "agent-architecture.md",
            "llm-integration.md",
            "memory-system.md",
            "tool-system.md",
            "planning-reasoning.md",
            "human-collaboration.md",
            "safety-alignment.md",
            "observability.md",
            "performance.md",
            "evaluation.md",
            "agent-framework.md"
        ]
        specialized_count = sum(1 for f in llm_agent_files if (analysis_path / f).exists())
        result["specialized_templates_ok"] = specialized_count >= 8
        result["details"]["specialized"] = {
            "type": "llm-agent",
            "required": len(llm_agent_files),
            "exists": specialized_count
        }
    elif project_type == "database":
        database_files = [
            "database-overview.md",
            "architecture.md",
            "storage-engine.md",
            "index-design.md",
            "query-processing.md",
            "transaction.md",
            "ha-fault-tolerance.md",
            "resource-management.md",
            "network-serialization.md",
            "workload-specific.md",
            "observability.md"
        ]
        specialized_count = sum(1 for f in database_files if (analysis_path / f).exists())
        result["specialized_templates_ok"] = specialized_count >= 8
        result["details"]["specialized"] = {
            "type": "database",
            "required": len(database_files),
            "exists": specialized_count
        }
    else:
        # 通用项目，检查是否有专项分析
        specialized_count = sum(1 for f in md_files if any(kw in f.name.lower() for kw in ["core-features", "feature-implementation", "adr-", "performance-model"]))
        result["specialized_templates_ok"] = specialized_count >= 3
        result["details"]["specialized"] = {
            "type": "general",
            "exists": specialized_count
        }
    
    if not result["specialized_templates_ok"]:
        result["issues"].append(f"专项模板不完整：{specialized_count} 个（需要 >= 8）")
    
    # 6. 检查附加分析
    additional_keywords = ["core-features", "feature-implementation", "adr-", "performance-model", "tradeoff", "visualization"]
    additional_files = [f for f in md_files if any(kw in f.name.lower() for kw in additional_keywords)]
    result["additional_analysis_ok"] = len(additional_files) >= 3
    result["details"]["additional"] = {
        "count": len(additional_files),
        "files": [f.name for f in additional_files[:10]]
    }
    if not result["additional_analysis_ok"]:
        result["issues"].append(f"附加分析不足：{len(additional_files)} 个（需要 >= 3）")
    
    # 7. 判断是否满足最大化模式
    result["is_maximum_mode"] = (
        result["total_files"] >= 40 and
        result["layer1_ok"] and
        result["layer2_ok"] and
        result["layer3_ok"] and
        result["specialized_templates_ok"] and
        result["additional_analysis_ok"]
    )
    
    if result["total_files"] < 40:
        result["issues"].append(f"文档总数不足：{result['total_files']} 个（需要 >= 40）")
    
    return result


def generate_maximum_mode_report(analysis_dir: str, check_result: dict) -> str:
    """生成最大化模式验证报告"""
    analysis_path = Path(analysis_dir)
    report_file = analysis_path / "MAXIMUM_MODE_REPORT.md"
    
    content = f"""# 🚀 最大化模式验证报告

**分析目录**: `{analysis_dir}`
**验证时间**: {datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## 总体评估

| 指标 | 结果 | 状态 |
|------|------|------|
| **是否满足最大化模式** | {'✅ 是' if check_result['is_maximum_mode'] else '❌ 否'} | {'✅' if check_result['is_maximum_mode'] else '❌'} |
| **文档总数** | {check_result['total_files']} / 40 | {'✅' if check_result['total_files'] >= 40 else '❌'} |
| **Layer 1 项目级** | {'✅ 完整' if check_result['layer1_ok'] else '❌ 不完整'} | {'✅' if check_result['layer1_ok'] else '❌'} |
| **Layer 2 模块级** | {'✅ 完整' if check_result['layer2_ok'] else '❌ 不完整'} | {'✅' if check_result['layer2_ok'] else '❌'} |
| **Layer 3 文件粒度** | {'✅ 完整' if check_result['layer3_ok'] else '❌ 不完整'} | {'✅' if check_result['layer3_ok'] else '❌'} |
| **专项模板** | {'✅ 完整' if check_result['specialized_templates_ok'] else '❌ 不完整'} | {'✅' if check_result['specialized_templates_ok'] else '❌'} |
| **附加分析** | {'✅ 完整' if check_result['additional_analysis_ok'] else '❌ 不完整'} | {'✅' if check_result['additional_analysis_ok'] else '❌'} |

---

## 详细检查

### Layer 1: 项目级分析

| 文件 | 状态 |
|------|------|
"""
    
    for f in check_result["details"]["layer1"]["required"]:
        exists = f in check_result["details"]["layer1"]["exists"]
        content += f"| {f} | {'✅' if exists else '❌'} |\n"
    
    content += f"""
**统计**: {check_result['details']['layer1']['count']}/4 个文件

### Layer 2: 模块级分析

- **模块目录数**: {check_result['details']['layer2']['module_dirs']}
- **模块文件数**: {check_result['details']['layer2']['module_files']}
- **状态**: {'✅ 完整' if check_result['layer2_ok'] else '❌ 不完整'}

### Layer 3: 文件粒度分析

- **文件分析目录数**: {check_result['details']['layer3']['file_dirs']}
- **文件分析文件数**: {check_result['details']['layer3']['file_analysis_files']}
- **状态**: {'✅ 完整' if check_result['layer3_ok'] else '❌ 不完整'}

### 专项模板

- **项目类型**: {check_result['details']['specialized'].get('type', 'unknown')}
- **专项文档数**: {check_result['details']['specialized']['exists']}
- **状态**: {'✅ 完整' if check_result['specialized_templates_ok'] else '❌ 不完整'}

### 附加分析

- **附加文档数**: {check_result['details']['additional']['count']}
- **文档列表**: {', '.join(check_result['details']['additional']['files'][:5])}
- **状态**: {'✅ 完整' if check_result['additional_analysis_ok'] else '❌ 不完整'}

---

## 问题清单

"""
    
    if check_result["issues"]:
        for issue in check_result["issues"]:
            content += f"- ⚠️ {issue}\n"
    else:
        content += "✅ 无问题\n"
    
    content += f"""

---

## 改进建议

"""
    
    if not check_result["is_maximum_mode"]:
        content += "### 当前不满足最大化模式，建议：\n\n"
        
        if not check_result["layer1_ok"]:
            content += "1. **补充 Layer 1 项目级分析**\n"
            content += "   - 确保包含 README、architecture、quality-score、learning-value\n\n"
        
        if not check_result["layer2_ok"]:
            content += "2. **补充 Layer 2 模块级分析**\n"
            content += "   - 为每个核心模块生成 overview、interface、dependencies 文档\n"
            content += "   - 至少 5 个模块文件\n\n"
        
        if not check_result["layer3_ok"]:
            content += "3. **补充 Layer 3 文件粒度分析**\n"
            content += "   - 为关键文件生成详细分析文档\n"
            content += "   - 至少 10 个文件分析\n\n"
        
        if not check_result["specialized_templates_ok"]:
            content += "4. **补充专项模板分析**\n"
            content += "   - 根据项目类型应用对应的专项模板\n"
            content += "   - LLM Agent 项目：11 个专项文档\n"
            content += "   - 数据库项目：11 个专项文档\n\n"
        
        if not check_result["additional_analysis_ok"]:
            content += "5. **补充附加分析**\n"
            content += "   - 核心功能分析\n"
            content += "   - 功能实现逻辑追踪\n"
            content += "   - ADR 架构决策记录\n"
            content += "   - 性能建模\n\n"
        
        if check_result["total_files"] < 40:
            content += f"6. **增加文档总数**\n"
            content += f"   - 当前：{check_result['total_files']} 个\n"
            content += f"   - 目标：>= 40 个\n\n"
    else:
        content += "✅ 已满足最大化模式要求，无需改进\n"
    
    content += f"""
---

*生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}*
"""
    
    report_file.write_text(content)
    return str(report_file)


def check_recursive_mode(analysis_dir: str) -> dict:
    """检查是否满足递归深度分析模式要求
    
    递归深度分析模式要求：
    1. 项目级分析 (00-project-level/)
    2. 模块深度分析 (10-module-deep/) - 每个模块有独立的完整分析
    3. 跨模块分析 (20-cross-module/)
    4. 每个模块有 INDEX.md
    5. 中型模块有 Layer 2+3
    """
    analysis_path = Path(analysis_dir)
    
    result = {
        "is_recursive_mode": False,
        "total_files": 0,
        "project_level_ok": False,
        "module_deep_ok": False,
        "cross_module_ok": False,
        "module_count": 0,
        "modules_with_index": 0,
        "modules_with_layer2": 0,
        "modules_with_layer3": 0,
        "issues": [],
        "details": {}
    }
    
    # 1. 统计总文件数
    md_files = list(analysis_path.glob("**/*.md"))
    result["total_files"] = len(md_files)
    result["details"]["total_files"] = result["total_files"]
    
    # 2. 检查项目级分析
    project_level_dir = analysis_path / "00-project-level"
    if project_level_dir.exists():
        project_files = list(project_level_dir.glob("*.md"))
        has_dependencies = (project_level_dir / "dependencies.md").exists()
        result["project_level_ok"] = len(project_files) >= 3 and has_dependencies
        result["details"]["project_level"] = {
            "exists": True,
            "files": len(project_files),
            "has_dependencies": has_dependencies
        }
        if not has_dependencies:
            result["issues"].append("缺少 00-project-level/dependencies.md（项目依赖分析）")
    else:
        result["details"]["project_level"] = {"exists": False, "files": 0}
        result["issues"].append("缺少 00-project-level/ 目录")
    
    # 3. 检查模块深度分析
    module_deep_dir = analysis_path / "10-module-deep"
    if module_deep_dir.exists():
        # 统计模块目录：递归扫描含 INDEX.md 的目录（支持 packages/<family>/<module> 嵌套，
        # 及符号链接兼容层），按 realpath 去重避免重复计数
        seen = set()
        module_dirs = []
        for index_file in module_deep_dir.rglob("INDEX.md"):
            real = index_file.parent.resolve()
            if real in seen:
                continue
            seen.add(real)
            module_dirs.append(index_file.parent)
        result["module_count"] = len(module_dirs)
        
        # 检查每个模块的完整性
        for module_dir in module_dirs:
            module_name = module_dir.name
            
            # 检查 INDEX.md
            if (module_dir / "INDEX.md").exists():
                result["modules_with_index"] += 1
            
            # 检查 Layer 2 (子模块)
            layer2_dirs = [d for d in module_dir.iterdir() if d.is_dir() and d.name.startswith("10-")]
            if layer2_dirs:
                result["modules_with_layer2"] += 1
            
            # 检查 Layer 3 (文件级)
            layer3_dirs = [d for d in module_dir.iterdir() if d.is_dir() and d.name.startswith("20-")]
            if layer3_dirs:
                result["modules_with_layer3"] += 1
        
        result["module_deep_ok"] = result["module_count"] >= 3
        result["details"]["module_deep"] = {
            "exists": True,
            "module_count": result["module_count"],
            "with_index": result["modules_with_index"],
            "with_layer2": result["modules_with_layer2"],
            "with_layer3": result["modules_with_layer3"]
        }
    else:
        result["details"]["module_deep"] = {"exists": False}
        result["issues"].append("缺少 10-module-deep/ 目录")
    
    # 4. 检查跨模块分析
    cross_module_dir = analysis_path / "20-cross-module"
    if cross_module_dir.exists():
        cross_files = list(cross_module_dir.glob("*.md"))
        result["cross_module_ok"] = len(cross_files) >= 2
        result["details"]["cross_module"] = {
            "exists": True,
            "files": len(cross_files)
        }
    else:
        result["details"]["cross_module"] = {"exists": False, "files": 0}
        result["issues"].append("缺少 20-cross-module/ 目录")
    
    # 5. 判断是否满足递归模式
    # 阈值：递归模式应远超最大模式的 40 个文档
    min_total_files = 50
    min_module_count = 5
    min_index_ratio = 0.8  # 至少 80% 的模块有 INDEX.md
    
    index_ratio = result["modules_with_index"] / max(1, result["module_count"])
    
    result["is_recursive_mode"] = (
        result["total_files"] >= min_total_files and
        result["project_level_ok"] and
        result["module_deep_ok"] and
        result["cross_module_ok"] and
        result["module_count"] >= min_module_count and
        result["modules_with_index"] >= 3 and
        index_ratio >= min_index_ratio
    )
    
    if result["total_files"] < min_total_files:
        result["issues"].append(f"文档总数不足：{result['total_files']} 个（需要 >= {min_total_files}）")
    if result["module_count"] < min_module_count:
        result["issues"].append(f"模块数不足：{result['module_count']} 个（需要 >= {min_module_count}）")
    if result["modules_with_index"] < 3:
        result["issues"].append(f"模块 INDEX.md 不足：{result['modules_with_index']} 个（需要 >= 3）")
    if index_ratio < min_index_ratio:
        result["issues"].append(f"INDEX.md 覆盖率不足：{index_ratio:.0%}（需要 >= {min_index_ratio:.0%}）")
    
    return result


def generate_recursive_mode_report(analysis_dir: str, check_result: dict) -> str:
    """生成递归深度分析模式验证报告"""
    analysis_path = Path(analysis_dir)
    report_file = analysis_path / "RECURSIVE_MODE_REPORT.md"
    
    content = f"""# 🔁 递归深度分析模式验证报告

**分析目录**: `{analysis_dir}`
**验证时间**: {datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## 总体评估

| 指标 | 结果 | 状态 |
|------|------|------|
| **是否满足递归模式** | {'✅ 是' if check_result['is_recursive_mode'] else '❌ 否'} | {'✅' if check_result['is_recursive_mode'] else '❌'} |
| **文档总数** | {check_result['total_files']} / 50 | {'✅' if check_result['total_files'] >= 50 else '❌'} |
| **项目级分析** | {'✅ 完整' if check_result['project_level_ok'] else '❌ 不完整'} | {'✅' if check_result['project_level_ok'] else '❌'} |
| **模块深度分析** | {'✅ 完整' if check_result['module_deep_ok'] else '❌ 不完整'} | {'✅' if check_result['module_deep_ok'] else '❌'} |
| **跨模块分析** | {'✅ 完整' if check_result['cross_module_ok'] else '❌ 不完整'} | {'✅' if check_result['cross_module_ok'] else '❌'} |

---

## 模块统计

| 指标 | 数量 |
|------|------|
| **模块总数** | {check_result['module_count']} |
| **有 INDEX.md** | {check_result['modules_with_index']} |
| **有 Layer 2** | {check_result['modules_with_layer2']} |
| **有 Layer 3** | {check_result['modules_with_layer3']} |

---

## 问题清单

"""
    
    if check_result["issues"]:
        for issue in check_result["issues"]:
            content += f"- ⚠️ {issue}\n"
    else:
        content += "✅ 无问题\n"
    
    content += f"""

---

## 改进建议

"""
    
    if not check_result["is_recursive_mode"]:
        if not check_result["project_level_ok"]:
            content += "1. **补充项目级分析**\n"
            content += "   - 创建 00-project-level/ 目录\n"
            content += "   - 包含 README/architecture/quality-score/learning-value\n\n"
        
        if not check_result["module_deep_ok"]:
            content += "2. **补充模块深度分析**\n"
            content += "   - 创建 10-module-deep/ 目录\n"
            content += "   - 为每个模块生成独立分析（至少 3 个模块）\n\n"
        
        if not check_result["cross_module_ok"]:
            content += "3. **补充跨模块分析**\n"
            content += "   - 创建 20-cross-module/ 目录\n"
            content += "   - 包含 comparison.md 和 patterns.md\n\n"
        
        if check_result["modules_with_index"] < 3:
            content += "4. **为每个模块添加 INDEX.md**\n\n"
    else:
        content += "✅ 已满足递归深度分析模式要求\n"
    
    content += f"""
---

*生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}*
"""
    
    report_file.write_text(content)
    return str(report_file)


def main():
    parser = argparse.ArgumentParser(description="Verify analysis output completeness and quality")
    parser.add_argument("analysis_dir", help="Path to analysis output directory")
    parser.add_argument("--completeness", action="store_true", help="Check only completeness (file existence)")
    parser.add_argument("--quality", action="store_true", help="Check quality (content)")
    parser.add_argument("--all", action="store_true", help="Check both completeness and quality (default)")
    parser.add_argument("--maximum", action="store_true", help="Check if analysis meets maximum mode requirements")
    parser.add_argument("--recursive", action="store_true", help="Check if analysis meets recursive deep analysis mode requirements")
    parser.add_argument("--forbidden-allow", default="", help="禁止词豁免列表（逗号分隔，如：todo,workflow）")

    args = parser.parse_args()

    if args.forbidden_allow:
        FORBIDDEN_ALLOW.extend(w.strip() for w in args.forbidden_allow.split(',') if w.strip())
    
    analysis_dir = args.analysis_dir
    
    # 递归深度分析模式检查
    if args.recursive:
        print(f"\n🔁 递归深度分析模式验证")
        print(f"=" * 50)
        
        check_result = check_recursive_mode(analysis_dir)
        report_file = generate_recursive_mode_report(analysis_dir, check_result)
        
        print(f"\n文档总数: {check_result['total_files']}/50")
        print(f"项目级分析: {'✅' if check_result['project_level_ok'] else '❌'}")
        print(f"模块深度分析: {'✅' if check_result['module_deep_ok'] else '❌'}")
        print(f"跨模块分析: {'✅' if check_result['cross_module_ok'] else '❌'}")
        print(f"模块数: {check_result['module_count']}")
        print(f"有 INDEX.md 的模块: {check_result['modules_with_index']}")
        
        print(f"\n{'✅ 满足递归模式' if check_result['is_recursive_mode'] else '❌ 不满足递归模式'}")
        
        if check_result["issues"]:
            print(f"\n⚠️ 发现 {len(check_result['issues'])} 个问题:")
            for issue in check_result["issues"]:
                print(f"  - {issue}")
        
        print(f"\n📄 详细报告: {report_file}")
        
        return 0 if check_result["is_recursive_mode"] else 1
    
    # 最大化模式检查
    if args.maximum:
        print(f"\n🚀 最大化模式验证")
        print(f"=" * 50)
        
        check_result = check_maximum_mode(analysis_dir)
        report_file = generate_maximum_mode_report(analysis_dir, check_result)
        
        print(f"\n文档总数: {check_result['total_files']}/40")
        print(f"Layer 1 项目级: {'✅' if check_result['layer1_ok'] else '❌'}")
        print(f"Layer 2 模块级: {'✅' if check_result['layer2_ok'] else '❌'}")
        print(f"Layer 3 文件粒度: {'✅' if check_result['layer3_ok'] else '❌'}")
        print(f"专项模板: {'✅' if check_result['specialized_templates_ok'] else '❌'}")
        print(f"附加分析: {'✅' if check_result['additional_analysis_ok'] else '❌'}")
        
        print(f"\n{'✅ 满足最大化模式' if check_result['is_maximum_mode'] else '❌ 不满足最大化模式'}")
        
        if check_result["issues"]:
            print(f"\n⚠️ 发现 {len(check_result['issues'])} 个问题:")
            for issue in check_result["issues"]:
                print(f"  - {issue}")
        
        print(f"\n📄 详细报告: {report_file}")
        
        return 0 if check_result["is_maximum_mode"] else 1
    
    # 确定检查模式
    if args.completeness:
        mode = "completeness"
    elif args.quality:
        mode = "quality"
    else:
        mode = "all"
    
    # 执行验证
    results = verify_analysis(analysis_dir, mode)
    
    # INDEX.md 一致性检查
    index_consistency = check_index_consistency(Path(analysis_dir))
    
    # Glossary 提案制落地检查
    glossary_check = check_glossary(Path(analysis_dir))
    
    # 图表类型多样性检查（讲解型图 / 空间布局图）
    diagram_check = check_diagram_types(Path(analysis_dir))
    
    # 生成报告
    report_file = generate_verification_report(analysis_dir, results, index_consistency,
                                               glossary_check=glossary_check, diagram_check=diagram_check)
    
    # 打印摘要
    print(f"\n📊 分析验证报告")
    print(f"=" * 50)
    
    completed = sum(1 for r in results if r["exists"])
    total = len(results)
    
    print(f"文件完整性: {completed}/{total}")
    
    if mode != "completeness":
        avg_score = sum(r.get("score", 0) for r in results if r["exists"]) / max(1, completed)
        print(f"平均质量分数: {avg_score:.0f}/100")
    
    # INDEX 一致性
    if index_consistency['index_exists']:
        phantom = len(index_consistency['phantom_refs'])
        orphan = len(index_consistency['orphan_files'])
        if phantom == 0 and orphan == 0:
            print(f"INDEX 一致性: ✅ 完全一致")
        else:
            print(f"INDEX 一致性: ⚠️ {phantom} 个幽灵引用, {orphan} 个孤儿文件")
    else:
        print(f"INDEX 一致性: ❌ INDEX.md 不存在")
    
    # Glossary
    if glossary_check["ok"]:
        print(f"Glossary 术语表: ✅ {glossary_check['terms']} 条术语")
    elif glossary_check["exists"]:
        print(f"Glossary 术语表: ⚠️ {glossary_check['message']}")
    else:
        print(f"Glossary 术语表: ❌ {glossary_check['message']}")
    
    # 图表类型多样性
    if diagram_check["cards"]:
        print(f"学习卡片: {diagram_check['explanatory_cards']}/{diagram_check['cards']} 含讲解型图特征")
    if diagram_check["warnings"]:
        print(f"图表多样性: ⚠️ {len(diagram_check['warnings'])} 项提示:")
        for w in diagram_check["warnings"]:
            print(f"  - {w}")
    
    # 打印问题
    issues = []
    for r in results:
        if r.get("issues"):
            issues.extend([(r["file"], issue) for issue in r["issues"]])
    
    if issues:
        print(f"\n⚠️ 发现 {len(issues)} 个问题:")
        for file, issue in issues:
            print(f"  - {file}: {issue}")
    else:
        print(f"\n✅ 未发现明显问题")
    
    # 打印幽灵引用详情
    if index_consistency.get('phantom_refs'):
        print(f"\n👻 幽灵引用（INDEX 有但文件不存在）:")
        for ref in index_consistency['phantom_refs'][:5]:
            print(f"  - {ref['path']}")
        if len(index_consistency['phantom_refs']) > 5:
            print(f"  ... 还有 {len(index_consistency['phantom_refs']) - 5} 个")
    
    # 打印孤儿文件详情
    if index_consistency.get('orphan_files'):
        print(f"\n🏚️ 孤儿文件（文件存在但 INDEX 未引用）:")
        for f in index_consistency['orphan_files'][:5]:
            print(f"  - {f}")
        if len(index_consistency['orphan_files']) > 5:
            print(f"  ... 还有 {len(index_consistency['orphan_files']) - 5} 个")
    
    print(f"\n📄 详细报告: {report_file}")
    
    # 返回码：文件缺失、INDEX 不一致都算失败
    has_index_issues = (
        index_consistency.get('phantom_refs') or 
        index_consistency.get('orphan_files')
    )
    return 0 if (completed == total and not has_index_issues) else 1


if __name__ == "__main__":
    sys.exit(main())