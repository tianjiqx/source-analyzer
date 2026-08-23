#!/usr/bin/env python3
"""
Mermaid 图表语法检验器

扫描 Markdown 文件中的 mermaid 代码块，检查常见语法错误。

用法:
    # 检查单个文件
    python3 mermaid-validator.py /path/to/analysis/README.md

    # 递归检查目录
    python3 mermaid-validator.py /path/to/analysis/ --recursive

    # 修复模式（输出修复后的文件）
    python3 mermaid-validator.py /path/to/analysis/README.md --fix

检查项:
    1. 代码块语法完整性（```mermaid ... ```）
    2. 图表类型声明（flowchart/sequenceDiagram/classDiagram 等）
    3. 节点名特殊字符（括号、引号、冒号）
    4. 箭头语法（-->、---、-.- 等）
    5. subgraph/end 配对
    6. classDiagram 关系箭头（<|..、-->、*-- 等）
    7. 引用未定义的节点（style、link）
    8. 中文/特殊字符未引号包裹
    9. sequenceDiagram 参与者声明
    10. 节点 ID 重复
"""

import re
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional


# ─── 数据结构 ────────────────────────────────────────────────────────────────

@dataclass
class DiagramIssue:
    line: int              # 在 mermaid 块内的行号
    column: int            # 列号（近似）
    severity: str          # error / warning
    rule: str              # 规则 ID
    message: str           # 描述
    context: str           # 上下文（该行内容）
    fix: str = ""          # 修复建议


@dataclass
class Diagram:
    filepath: str
    start_line: int        # 在 Markdown 文件中的起始行
    end_line: int
    raw: str               # mermaid 原始内容
    diagram_type: str      # flowchart / sequenceDiagram / ...
    issues: List[DiagramIssue] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        return not any(i.severity == 'error' for i in self.issues)
    
    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == 'error')
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == 'warning')


# ─── 合法图表类型 ────────────────────────────────────────────────────────────

VALID_TYPES = {
    'flowchart', 'graph', 'graph TD', 'graph LR', 'graph TB', 'graph BT',
    'graph TD;', 'graph LR;', 
    'sequenceDiagram', 'sequenceDiagram;',
    'classDiagram', 'classDiagram;',
    'stateDiagram', 'stateDiagram-v2',
    'erDiagram', 'erDiagram;',
    'gantt', 'gantt;',
    'pie', 'pie;',
    'mindmap', 'mindmap;',
    'journey', 'journey;',
    'gitGraph', 'gitGraph;',
    'quadrantChart', 'quadrantChart;',
    'timeline', 'timeline;',
    'C4Context', 'C4Container', 'C4Component',
}

VALID_TYPE_PREFIXES = {
    'flowchart', 'graph',
    'sequenceDiagram',
    'classDiagram',
    'stateDiagram',
    'erDiagram',
    'gantt',
    'pie',
    'mindmap',
    'journey',
    'gitGraph',
    'quadrantChart',
    'timeline',
    'C4Context', 'C4Container', 'C4Component',
}


# ─── 提取 Mermaid 块 ────────────────────────────────────────────────────────

def extract_mermaid_blocks(content: str, filepath: str) -> List[Diagram]:
    """从 Markdown 内容中提取所有 mermaid 代码块"""
    diagrams = []
    lines = content.split('\n')
    
    in_block = False
    block_start = 0
    block_lines = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if stripped.startswith('```mermaid'):
            in_block = True
            block_start = i + 1  # mermaid 内容从下一行开始
            block_lines = []
            continue
        
        if in_block:
            if stripped.startswith('```'):
                # 代码块结束
                raw = '\n'.join(block_lines)
                if raw.strip():
                    diagram_type = detect_type(raw)
                    diagrams.append(Diagram(
                        filepath=filepath,
                        start_line=block_start,
                        end_line=i,
                        raw=raw,
                        diagram_type=diagram_type,
                    ))
                in_block = False
                block_lines = []
            else:
                block_lines.append(line)
    
    # 未闭合的代码块
    if in_block:
        raw = '\n'.join(block_lines)
        if raw.strip():
            diagram = Diagram(
                filepath=filepath,
                start_line=block_start,
                end_line=len(lines),
                raw=raw,
                diagram_type=detect_type(raw),
            )
            diagram.issues.append(DiagramIssue(
                line=0, column=0,
                severity='error',
                rule='UNCLOSED_BLOCK',
                message='mermaid 代码块未闭合（缺少结束的 ```）',
                context='',
                fix='在代码块末尾添加 ```',
            ))
            diagrams.append(diagram)
    
    return diagrams


def detect_type(raw: str) -> str:
    """检测图表类型"""
    first_line = raw.strip().split('\n')[0].strip()
    for prefix in VALID_TYPE_PREFIXES:
        if first_line.startswith(prefix):
            return prefix
    return first_line.split()[0] if first_line else 'unknown'


# ─── 检验规则 ────────────────────────────────────────────────────────────────

def check_diagram_type(diagram: Diagram):
    """规则 1: 检查图表类型声明"""
    first_line = diagram.raw.strip().split('\n')[0].strip()
    
    if not first_line:
        diagram.issues.append(DiagramIssue(
            line=1, column=0, severity='error', rule='EMPTY_DIAGRAM',
            message='mermaid 代码块为空', context='',
        ))
        return
    
    # 检查是否是合法类型
    is_valid = False
    for prefix in VALID_TYPE_PREFIXES:
        if first_line.startswith(prefix):
            is_valid = True
            break
    
    if not is_valid:
        diagram.issues.append(DiagramIssue(
            line=1, column=0, severity='error', rule='INVALID_TYPE',
            message=f'未知的图表类型: "{first_line[:30]}"',
            context=first_line,
            fix=f'使用合法类型如: flowchart TD, sequenceDiagram, classDiagram 等',
        ))


def check_node_syntax_flowchart(diagram: Diagram):
    """规则 2: flowchart/graph 节点语法检查"""
    lines = diagram.raw.split('\n')
    defined_nodes = set()
    
    # 节点定义的正则：A[...], A(...), A{...}, A((...)), A>...], A["..."]
    node_patterns = [
        (r'(\w+)\s*\[([^\]]+)\]', 'square'),       # A[text]
        (r'(\w+)\s*\(([^)]+)\)', 'round'),          # A(text)
        (r'(\w+)\s*\{([^}]+)\}', 'diamond'),        # A{text}
        (r'(\w+)\s*\(\(([^)]+)\)\)', 'circle'),     # A((text))
    ]
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith('%%') or stripped.startswith('---'):
            continue
        if stripped.startswith(('flowchart', 'graph', 'subgraph', 'end', 'style', 'classDef', 'class', 'linkStyle', 'click')):
            # 处理 subgraph 中定义的节点
            if stripped.startswith('subgraph'):
                # subgraph ID ["Title"]
                continue
            continue
        
        # 检查箭头
        arrow_pattern = r'(-->|---|-\.->|==>|-.->|==o|==x|--x|--o|---\|)'
        
        # 检查节点文本中的特殊字符
        # 常见问题：A[Node Name (with parens)] — 括号未转义
        bracket_content = re.findall(r'\[([^\]]*)\]', stripped)
        for content in bracket_content:
            if '(' in content and ')' in content and '"' not in content:
                # 可能未转义的括号
                if not content.startswith('"'):
                    diagram.issues.append(DiagramIssue(
                        line=i+1, column=0, severity='warning', rule='UNESCAPED_PARENS',
                        message=f'节点文本中包含括号，可能导致渲染失败: [{content}]',
                        context=stripped,
                        fix=f'用引号包裹: A["{content}"]',
                    ))
        
        # 检查节点文本中未转义的引号
        for match in re.finditer(r'\["([^"]*"[^"]*)"\]', stripped):
            diagram.issues.append(DiagramIssue(
                line=i+1, column=0, severity='warning', rule='NESTED_QUOTES',
                message=f'节点文本中包含嵌套引号: [{match.group(0)}]',
                context=stripped,
                fix='使用 &quot; 替代内部引号，或用单引号',
            ))
        
        # 收集已定义节点
        for pattern, _ in node_patterns:
            for match in re.finditer(pattern, stripped):
                defined_nodes.add(match.group(1))
        
        # 简单节点引用（如 A --> B 中的 A 和 B）
        if re.search(arrow_pattern, stripped):
            parts = re.split(arrow_pattern, stripped)
            for part in parts:
                part = part.strip().strip(';').strip()
                if part and re.match(r'^\w+$', part):
                    defined_nodes.add(part)
    
    # 检查 style 引用的节点是否存在
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('style '):
            parts = stripped.split()
            if len(parts) >= 2:
                node_id = parts[1]
                if node_id not in defined_nodes:
                    diagram.issues.append(DiagramIssue(
                        line=i+1, column=0, severity='error', rule='UNDEFINED_NODE_STYLE',
                        message=f'style 引用了未定义的节点: {node_id}',
                        context=stripped,
                        fix=f'确保节点 {node_id} 在图表中定义，或移除该 style 行',
                    ))


# sequenceDiagram 中需要 end 闭合的块关键字（alt/opt/loop/par/rect/critical/break）
# 注意：else/and/option 是块内分隔符，不单独开块，不计入配对
SEQ_BLOCK_KEYWORDS = ('alt', 'opt', 'loop', 'par', 'rect', 'critical', 'break')


def _is_seq_block_start(stripped_lower: str) -> bool:
    """判断行是否为 sequenceDiagram 块起始（alt/opt/loop/par/rect/critical/break）"""
    for kw in SEQ_BLOCK_KEYWORDS:
        if stripped_lower == kw:
            return True
        if stripped_lower.startswith(kw + ' '):
            return True
        if stripped_lower.startswith(kw + ':'):
            return True
    return False


def check_subgraph_pairing(diagram: Diagram):
    """规则 3: subgraph/end 配对检查（sequenceDiagram 识别 alt/loop/par 等块）"""
    lines = diagram.raw.split('\n')
    depth = 0

    for i, line in enumerate(lines):
        stripped = line.strip().lower()

        if diagram.diagram_type == 'sequenceDiagram':
            # sequenceDiagram：alt/opt/loop/par/rect/critical/break 需要 end 闭合
            # else/and/option 是块内分隔符，不计入
            if _is_seq_block_start(stripped):
                depth += 1
            elif stripped == 'end' or stripped.startswith('end '):
                depth -= 1
                if depth < 0:
                    diagram.issues.append(DiagramIssue(
                        line=i + 1, column=0, severity='error', rule='EXTRA_END',
                        message='多余的 end（没有对应的 alt/opt/loop/par/rect/critical/break 块）',
                        context=line.strip(),
                    ))
        else:
            # 其他类型：subgraph/end 配对
            if stripped.startswith('subgraph'):
                depth += 1
            elif stripped == 'end' or stripped.startswith('end '):
                depth -= 1
                if depth < 0:
                    diagram.issues.append(DiagramIssue(
                        line=i + 1, column=0, severity='error', rule='EXTRA_END',
                        message='多余的 end（没有对应的 subgraph）',
                        context=line.strip(),
                    ))

    if depth > 0:
        diagram.issues.append(DiagramIssue(
            line=len(lines), column=0, severity='error', rule='MISSING_END',
            message=f'缺少 {depth} 个 end（块未闭合）',
            context='',
            fix=f'在对应位置添加 {depth} 个 end',
        ))


def check_sequence_diagram(diagram: Diagram):
    """规则 4: sequenceDiagram 专用检查"""
    if diagram.diagram_type != 'sequenceDiagram':
        return
    
    lines = diagram.raw.split('\n')
    has_participant = False
    has_message = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('participant '):
            has_participant = True
        elif re.search(r'(-+>|-->>|->>|-->|->)', stripped) and not stripped.startswith('%'):
            has_message = True
        
        # 检查 participant 别名语法
        if stripped.startswith('participant '):
            # participant A as "Name"
            parts = stripped[len('participant '):].split(' as ')
            if len(parts) == 1:
                # participant Name — 检查是否包含特殊字符
                name = parts[0].strip()
                if ' ' in name and '"' not in name:
                    diagram.issues.append(DiagramIssue(
                        line=i+1, column=0, severity='warning', rule='PARTICIPANT_SPACE',
                        message=f'participant 名称包含空格，建议使用 as 别名: {name}',
                        context=stripped,
                        fix=f'participant {name.split()[0]} as "{name}"',
                    ))
    
    if not has_message:
        diagram.issues.append(DiagramIssue(
            line=0, column=0, severity='warning', rule='NO_MESSAGES',
            message='sequenceDiagram 没有任何消息（->> 或 -->）',
            context='',
        ))


def check_class_diagram(diagram: Diagram):
    """规则 5: classDiagram 专用检查"""
    if diagram.diagram_type != 'classDiagram':
        return
    
    lines = diagram.raw.split('\n')
    
    # 合法的关系箭头
    valid_relations = [
        '<|--', '--|>', '<|..', '..|>',
        '-->', '<--', '..>', '<..',
        '*--', '--*', 'o--', '--o',
        '..<', '>..', '<|.', '.|>',
        '===', '--%', '..%',
    ]
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith('%%') or stripped.startswith('class '):
            continue
        
        # 检查关系行（包含 -- 或 .. 的行）
        if '--' in stripped or '..' in stripped:
            # 提取关系操作符
            found_relation = False
            for rel in valid_relations:
                if rel in stripped:
                    found_relation = True
                    break
            
            if not found_relation and not stripped.startswith(('note', '<<', 'namespace', '%%')):
                # 可能的关系语法错误
                if re.search(r'\w+\s*-\s*\w+', stripped) and '<' not in stripped and '>' not in stripped:
                    diagram.issues.append(DiagramIssue(
                        line=i+1, column=0, severity='warning', rule='INVALID_RELATION',
                        message=f'可能无效的类关系语法: {stripped[:50]}',
                        context=stripped,
                        fix='使用合法关系如: <|--, ..|>, -->, *--, o--',
                    ))


def check_syntax_basics(diagram: Diagram):
    """规则 6: 基础语法检查（适用于所有类型）"""
    lines = diagram.raw.split('\n')
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if not stripped or stripped.startswith('%%'):
            continue
        
        # 检查中文全角字符（可能导致渲染失败）
        fullwidth = re.findall(r'[（）【】：；""''！？]', stripped)
        if fullwidth:
            diagram.issues.append(DiagramIssue(
                line=i+1, column=0, severity='warning', rule='FULLWIDTH_CHARS',
                message=f'包含全角字符: {" ".join(fullwidth[:3])}',
                context=stripped,
                fix='替换为半角字符: () [] : ; "" \'\' ! ?',
            ))
        
        # 检查行尾多余的分号（除了 type 声明行）
        if stripped.endswith(';;') and not stripped.startswith(('flowchart', 'graph', 'sequenceDiagram', 'classDiagram')):
            diagram.issues.append(DiagramIssue(
                line=i+1, column=0, severity='warning', rule='DOUBLE_SEMICOLON',
                message='行尾多余的分号',
                context=stripped,
                fix='去除多余的 ;',
            ))
        
        # 检查 Tab 缩进（Mermaid 对 tab 敏感）
        if '\t' in line:
            diagram.issues.append(DiagramIssue(
                line=i+1, column=0, severity='warning', rule='TAB_INDENT',
                message='使用 Tab 缩进（Mermaid 可能无法正确解析）',
                context=stripped,
                fix='替换 Tab 为空格',
            ))


def check_mermaid_live(diagram: Diagram):
    """规则 7: 尝试用 mermaid CLI 验证（如果安装了 @mermaid-js/mermaid-cli）"""
    import shutil
    mmdc = shutil.which('mmdc')
    if not mmdc:
        return  # 未安装，跳过
    
    import tempfile
    import subprocess
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False, encoding='utf-8') as f:
        f.write(diagram.raw)
        temp_path = f.name
    
    try:
        result = subprocess.run(
            [mmdc, '-i', temp_path, '-o', '/dev/null', '--silent'],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            # 提取错误信息
            error_lines = result.stderr.strip().split('\n')
            for err_line in error_lines[:3]:
                if err_line.strip():
                    diagram.issues.append(DiagramIssue(
                        line=0, column=0, severity='error', rule='MMDC_ERROR',
                        message=f'mermaid CLI 报错: {err_line.strip()[:100]}',
                        context='',
                    ))
    except subprocess.TimeoutExpired:
        pass  # 超时跳过
    except FileNotFoundError:
        pass
    finally:
        Path(temp_path).unlink(missing_ok=True)


# ─── 主检验函数 ──────────────────────────────────────────────────────────────

def validate_diagram(diagram: Diagram, use_mmdc: bool = False):
    """运行所有检验规则"""
    check_diagram_type(diagram)
    check_syntax_basics(diagram)
    check_subgraph_pairing(diagram)
    
    if diagram.diagram_type in ('flowchart', 'graph'):
        check_node_syntax_flowchart(diagram)
    
    if diagram.diagram_type == 'sequenceDiagram':
        check_sequence_diagram(diagram)
    
    if diagram.diagram_type == 'classDiagram':
        check_class_diagram(diagram)
    
    if use_mmdc:
        check_mermaid_live(diagram)


# ─── 报告生成 ────────────────────────────────────────────────────────────────

def validate_file(filepath: Path, use_mmdc: bool = False) -> List[Diagram]:
    """验证单个文件中的所有 mermaid 图表"""
    content = filepath.read_text(encoding='utf-8', errors='ignore')
    diagrams = extract_mermaid_blocks(content, str(filepath))
    
    for diagram in diagrams:
        validate_diagram(diagram, use_mmdc)
    
    return diagrams


def validate_directory(dirpath: Path, use_mmdc: bool = False) -> Dict[str, List[Diagram]]:
    """递归验证目录中所有 .md 文件的 mermaid 图表"""
    results = {}
    
    for md_file in sorted(dirpath.rglob('*.md')):
        # 跳过报告文件
        if md_file.name in ('VERIFICATION_REPORT.md', 'PLAN_VERIFICATION_REPORT.md'):
            continue
        diagrams = validate_file(md_file, use_mmdc)
        if diagrams:
            results[str(md_file.relative_to(dirpath))] = diagrams
    
    return results


def generate_report(results: dict, output_path: Path = None) -> str:
    """生成检验报告"""
    total_diagrams = sum(len(diagrams) for diagrams in results.values())
    total_errors = sum(d.error_count for diagrams in results.values() for d in diagrams)
    total_warnings = sum(d.warning_count for diagrams in results.values() for d in diagrams)
    valid_diagrams = sum(1 for diagrams in results.values() for d in diagrams if d.is_valid)
    
    content = f"""# Mermaid 图表检验报告

**检验时间**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 总览

| 指标 | 数量 |
|------|------|
| 图表总数 | {total_diagrams} |
| ✅ 有效图表 | {valid_diagrams} |
| ❌ 有错误的图表 | {total_diagrams - valid_diagrams} |
| ⚠️ 警告总数 | {total_warnings} |
| ❌ 错误总数 | {total_errors} |
| **通过率** | **{valid_diagrams}/{total_diagrams} ({valid_diagrams/max(1,total_diagrams)*100:.0f}%)** |

---

## 详细问题

"""
    
    has_issues = False
    for filepath, diagrams in sorted(results.items()):
        for diagram in diagrams:
            if not diagram.issues:
                continue
            
            has_issues = True
            status = '✅' if diagram.is_valid else '❌'
            content += f"### {status} `{filepath}` L{diagram.start_line}-{diagram.end_line} ({diagram.diagram_type})\n\n"
            
            if not diagram.is_valid:
                # 显示错误
                errors = [i for i in diagram.issues if i.severity == 'error']
                for issue in errors:
                    content += f"- ❌ **[{issue.rule}]** L{issue.line}: {issue.message}\n"
                    if issue.context:
                        content += f"  ```\n  {issue.context}\n  ```\n"
                    if issue.fix:
                        content += f"  💡 **修复**: {issue.fix}\n"
                    content += "\n"
            
            # 显示警告
            warnings = [i for i in diagram.issues if i.severity == 'warning']
            if warnings:
                content += f"<details><summary>⚠️ {len(warnings)} 个警告</summary>\n\n"
                for issue in warnings:
                    content += f"- **[{issue.rule}]** L{issue.line}: {issue.message}\n"
                    if issue.fix:
                        content += f"  💡 {issue.fix}\n"
                content += "\n</details>\n\n"
    
    if not has_issues:
        content += "✅ 所有图表均无问题\n"
    
    content += f"""
---

## 规则说明

| 规则 | 说明 |
|------|------|
| INVALID_TYPE | 未知的图表类型声明 |
| UNCLOSED_BLOCK | mermaid 代码块未闭合 |
| UNESCAPED_PARENS | 节点文本中包含未转义的括号 |
| NESTED_QUOTES | 节点文本中包含嵌套引号 |
| UNDEFINED_NODE_STYLE | style 引用了未定义的节点 |
| MISSING_END | subgraph 缺少对应的 end |
| EXTRA_END | 多余的 end |
| FULLWIDTH_CHARS | 使用了全角字符（可能导致渲染失败） |
| TAB_INDENT | 使用 Tab 缩进 |
| INVALID_RELATION | classDiagram 中无效的关系语法 |
| PARTICIPANT_SPACE | participant 名称包含空格 |

---

*由 mermaid-validator.py 生成*
"""
    
    if output_path:
        output_path.write_text(content, encoding='utf-8')
    
    return content


# ─── 入口 ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Mermaid 图表语法检验器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('path', type=Path, help='文件或目录路径')
    parser.add_argument('--recursive', '-r', action='store_true', help='递归检查目录')
    parser.add_argument('--fix', action='store_true', help='输出修复建议（不修改原文件）')
    parser.add_argument('-o', '--output', type=Path, help='输出报告文件路径')
    parser.add_argument('--use-mmdc', action='store_true', help='使用 mermaid CLI 验证（如果已安装）')
    
    args = parser.parse_args()
    
    if not args.path.exists():
        print(f"❌ 路径不存在: {args.path}", file=sys.stderr)
        sys.exit(1)
    
    # 验证
    if args.path.is_file():
        diagrams = validate_file(args.path, args.use_mmdc)
        results = {str(args.path): diagrams}
    else:
        results = validate_directory(args.path, args.use_mmdc)
    
    if not results or all(not diagrams for diagrams in results.values()):
        print("ℹ️  未找到 mermaid 图表")
        return
    
    # 统计
    total = sum(len(d) for d in results.values())
    errors = sum(d.error_count for diagrams in results.values() for d in diagrams)
    valid = sum(1 for diagrams in results.values() for d in diagrams if d.is_valid)
    
    # 生成报告
    report = generate_report(results, args.output)
    
    # 打印摘要
    print(f"\n🎨 Mermaid 图表检验")
    print(f"{'=' * 50}")
    print(f"图表总数: {total}")
    print(f"✅ 有效: {valid}")
    print(f"❌ 错误: {errors}")
    print(f"通过率: {valid}/{total} ({valid/max(1,total)*100:.0f}%)")
    
    if errors > 0:
        print(f"\n❌ 有错误的图表:")
        for filepath, diagrams in results.items():
            for d in diagrams:
                if not d.is_valid:
                    err_msgs = [i.message for i in d.issues if i.severity == 'error']
                    short_path = filepath.split('/')[-1] if '/' in filepath else filepath
                    print(f"  L{d.start_line} {short_path} ({d.diagram_type}): {err_msgs[0]}")
    
    # 保存报告
    report_path = args.output or (args.path / 'MERMAID_VALIDATION_REPORT.md' if args.path.is_dir() else None)
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        # report() 已经写了文件，如果 args.output 指定的话
        if not args.output:
            report_path.write_text(report, encoding='utf-8')
        print(f"\n📄 报告: {report_path}")
    
    return 0 if errors == 0 else 1


if __name__ == '__main__':
    sys.exit(main() or 0)
