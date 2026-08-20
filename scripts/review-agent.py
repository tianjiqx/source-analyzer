#!/usr/bin/env python3
"""
Review Agent - 独立审查代理

基于 Harness Patterns 的 Review/Execute 分离模式，
对分析文档进行独立审查，输出结构化审查报告。

审查维度：
1. 事实准确性 - 代码引用是否正确
2. 深度充分性 - 分析是否足够深入
3. 蒸馏质量 - Golden Rules 和 Gotchas 的质量
4. 去名检验 - 原则是否可移植
5. 结构完整性 - 文档结构是否完整

用法：
    python3 review-agent.py <analysis-dir> [--round N] [--strict]

输出：
    <analysis-dir>/.handoff/review-report-N.json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class ReviewFinding:
    """审查发现"""
    severity: str  # P0, P1, P2, P3
    category: str  # factual_error, missing_depth, weak_distillation, etc.
    file: str
    location: str  # line number or section
    description: str
    suggestion: str


@dataclass
class ReviewReport:
    """审查报告"""
    round: int
    timestamp: str
    analysis_dir: str
    findings: List[ReviewFinding]
    summary: Dict[str, int]  # severity counts
    convergence: bool  # 是否收敛
    verdict: str  # PASS, FAIL, NEEDS_REVISION


class ReviewAgent:
    """独立审查代理"""
    
    def __init__(self, analysis_dir: str, strict: bool = False):
        self.analysis_dir = Path(analysis_dir)
        self.strict = strict
        self.findings: List[ReviewFinding] = []
        
        # 审查标准
        self.min_golden_rules = 2 if not strict else 3
        self.min_gotchas = 2 if not strict else 3
        self.min_code_blocks = 3
        self.min_tables = 2
        
    def review(self, round_num: int = 1) -> ReviewReport:
        """执行审查"""
        print(f"🔍 Starting review round {round_num}...")
        
        # 跳过非分析文档（计划文件、元数据、工作文件）
        SKIP_PREFIXES = (
            "INDEX", "VERIFICATION", "PLAN", "ANALYSIS_PLAN", "RESEARCH_PLAN",
            "FILE_LIST", "VERSION", "CONVENTIONS", "MERMAID_VALIDATION",
            "PLAN_VERIFICATION", "RECURSIVE_MODE_REPORT", "MAXIMUM_MODE_REPORT",
        )
        SKIP_NAMES = {".checkpoint.json", "project-meta.json", "commit-history.json"}
        
        # 遍历所有分析文档
        for md_file in self.analysis_dir.glob("**/*.md"):
            # 跳过元/工作文件
            if any(md_file.name.startswith(prefix) for prefix in SKIP_PREFIXES):
                continue
            if md_file.name in SKIP_NAMES:
                continue
            # 跳过 .handoff 目录（审查报告自身）
            if ".handoff" in md_file.parts:
                continue
            # 跳过 task-prompts 目录（派发提示）
            if "task-prompts" in md_file.parts:
                continue
            
            self._review_file(md_file)
        
        # 生成报告
        report = self._generate_report(round_num)
        
        # 保存报告
        self._save_report(report, round_num)
        
        return report
    
    def _review_file(self, file_path: Path):
        """审查单个文件"""
        content = file_path.read_text()
        rel_path = file_path.relative_to(self.analysis_dir)
        
        # 判断文档类型（目录名无关，兼容 10-module-level / 10-module-deep / 20-file-level 等布局）
        rel_str = str(rel_path)
        first_part = rel_str.split('/')[0]
        is_module_analysis = (
            '/' in rel_str
            and re.match(r'\d{2}-', first_part)
            and first_part != '00-project-level'
        )
        is_project_overview = first_part == '00-project-level'
        
        # 1. 检查蒸馏章节（仅对模块/文件级分析文档）
        if is_module_analysis:
            self._check_distillation(content, rel_path)
        
        # 2. 检查代码引用（所有分析文档）
        if is_module_analysis or (is_project_overview and file_path.name in ['architecture.md', 'core-code.md']):
            self._check_code_references(content, rel_path)
        
        # 3. 检查深度（仅对模块/文件级分析）
        if is_module_analysis:
            self._check_depth(content, rel_path)
        
        # 4. 检查结构完整性（所有文档）
        self._check_structure(content, rel_path)
    
    def _check_distillation(self, content: str, file_path: Path):
        """检查蒸馏章节质量（与 verify-analysis 的宽松匹配保持一致）

        标准格式（两份脚本共用）：
        - 设计洞察：`## 💡 设计洞察`（兼容 `## 12. 💡 设计洞察（xxx）` 带编号变体）
          - 每条原则用 `**原则N：**` 或 `**原则N**：` 或 `N. **标题**：`，且应含「去名检验」
        - 隐含陷阱：`## ⚠️ 隐含陷阱`（兼容带编号变体）
          - 每条陷阱用 `**陷阱N：**` 等格式
        """
        # ── 设计洞察 ──
        # 宽松匹配标题（支持带编号、emoji 可选），段落截取到下一个 ##（含编号标题）
        # 注意：lookahead 用 \n##\s 避免匹配 ### 子标题
        insight_header = re.search(
            r'##\s*(?:\d+\.\s*)?(?:💡\s*)?设计洞察.*?(?=\n##\s|\Z)',
            content, re.DOTALL
        )
        has_insight_section = bool(re.search(r'#{2,4}\s*(?:\d+\.\s*)?(?:💡)?\s*设计洞察', content))
        if not has_insight_section:
            self.findings.append(ReviewFinding(
                severity="P1",
                category="missing_distillation",
                file=str(file_path),
                location="N/A",
                description="缺少💡设计洞察章节",
                suggestion="添加设计洞察章节，提炼可移植的设计原则（每条含 原理/证据/去名检验）"
            ))
        else:
            # 统计原则数量（宽松，兼容各变体）
            insight_section = insight_header.group(0) if insight_header else content
            principle_patterns = [
                r'\*\*原则\s*\d+\s*\*\*[:：]',     # **原则 1**：
                r'\*\*原则\s*\d+[:：]',             # **原则1：
                r'>\s*\*\*原则\s*\d+\*\*[:：]',     # > **原则 1**：
                r'^\d+\.\s*\*\*[^*]+\*\*\s*[:：]', # 1. **标题**：
                r'^#{2,4}\s*洞察\s*[一二三四五六七八九十\d]+',  # ### 洞察一 / ### 洞察1
                r'^#{2,4}\s*原则\s*[一二三四五六七八九十\d]+',  # ### 原则一
                r'\*\*洞察\s*[一二三四五六七八九十\d]+\*\*',    # **洞察一**
            ]
            principles = 0
            for pat in principle_patterns:
                found = re.findall(pat, insight_section, re.MULTILINE)
                principles = max(principles, len(found))
            if principles < self.min_golden_rules:
                self.findings.append(ReviewFinding(
                    severity="P2",
                    category="weak_distillation",
                    file=str(file_path),
                    location="💡设计洞察",
                    description=f"设计原则数量不足：{principles} < {self.min_golden_rules}",
                    suggestion=f"至少提炼 {self.min_golden_rules} 条可移植的设计原则（**原则N：** + 原理/证据/去名检验）"
                ))
            
            # 检查去名检验（可位于设计洞察章节任意位置）
            name_test_patterns = [r'去名检验', r'Name[-\s]Removal[-\s]?Test', r'可移植']
            if not any(re.search(p, insight_section, re.IGNORECASE) for p in name_test_patterns):
                self.findings.append(ReviewFinding(
                    severity="P2",
                    category="missing_name_test",
                    file=str(file_path),
                    location="💡设计洞察",
                    description="原则缺少去名检验",
                    suggestion="为每条原则添加去名检验，说明是否可移植（去名检验：✅/⚠️）"
                ))
        
        # ── 隐含陷阱 ──
        # 注意：lookahead 用 \n##\s 避免匹配 ### 子标题
        gotcha_header = re.search(
            r'##\s*(?:\d+\.\s*)?(?:⚠️\s*)?隐含陷阱.*?(?=\n##\s|\Z)',
            content, re.DOTALL
        )
        # ⚠️ 是 U+26A0+U+FE0F 双码点，字符类只能匹配单码点，必须用分组
        has_gotcha_section = bool(re.search(r'#{2,4}\s*(?:\d+\.\s*)?(?:⚠️|⚠)?\s*隐含陷阱', content))
        if not has_gotcha_section:
            self.findings.append(ReviewFinding(
                severity="P1",
                category="missing_distillation",
                file=str(file_path),
                location="N/A",
                description="缺少⚠️隐含陷阱章节",
                suggestion="添加隐含陷阱章节，记录非显而易见的实现陷阱（每条含 现象/原因/正确做法）"
            ))
        else:
            gotcha_section = gotcha_header.group(0) if gotcha_header else content
            gotcha_patterns = [
                r'\*\*陷阱\s*\d+\s*\*\*[:：]',
                r'\*\*陷阱\s*\d+[:：]',
                r'>\s*\*\*陷阱\s*\d+\*\*[:：]',
                r'^\d+\.\s*\*\*[^*]+\*\*\s*[:：]',
                r'\*\*陷阱\*\*[:：]',  # 未编号变体
                r'^#{2,4}\s*陷阱\s*[一二三四五六七八九十\d]+',  # ### 陷阱一 / ### 陷阱1
                r'\*\*陷阱\s*[一二三四五六七八九十\d]+\*\*',    # **陷阱一**
            ]
            gotchas = 0
            for pat in gotcha_patterns:
                found = re.findall(pat, gotcha_section, re.MULTILINE)
                gotchas = max(gotchas, len(found))
            if gotchas < self.min_gotchas:
                self.findings.append(ReviewFinding(
                    severity="P2",
                    category="weak_distillation",
                    file=str(file_path),
                    location="⚠️隐含陷阱",
                    description=f"隐含陷阱数量不足：{gotchas} < {self.min_gotchas}",
                    suggestion=f"至少记录 {self.min_gotchas} 个非显而易见的实现陷阱（**陷阱N：** + 现象/原因/正确做法）"
                ))
    
    def _check_code_references(self, content: str, file_path: Path):
        """检查代码引用准确性"""
        # 检查是否有代码块
        code_blocks = re.findall(r'```[\s\S]*?```', content)
        if len(code_blocks) < self.min_code_blocks:
            self.findings.append(ReviewFinding(
                severity="P2",
                category="insufficient_evidence",
                file=str(file_path),
                location="N/A",
                description=f"代码示例不足：{len(code_blocks)} < {self.min_code_blocks}",
                suggestion="添加更多代码示例作为分析依据"
            ))
        
        # 检查是否有 TODO 或 TBD（排除引用源码中 TODO 注释的合法分析内容）
        # 合法引用模式：TODO 注释、TODO:、TODO（、源码.*TODO、已知.*TODO
        todo_matches = list(re.finditer(r'\bTODO\b|\bTBD\b', content, re.IGNORECASE))
        if todo_matches:
            # 检查是否有独立未完成的 TODO 标记（非引用源码）
            unfinished_patterns = [
                r'^[-*]\s*\[.*\]\s*(TODO|TBD)',  # 复选框式 TODO
                r'^TODO[:：]\s*$',  # 独立 TODO: 行
                r'^TBD[:：]\s*$',  # 独立 TBD: 行
            ]
            has_unfinished = False
            for pattern in unfinished_patterns:
                if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                    has_unfinished = True
                    break
            
            # 如果没有明确的未完成标记，检查 TODO 是否都在合法引用上下文中
            if not has_unfinished and todo_matches:
                # 检查每个 TODO 出现是否在合法引用上下文中
                for match in todo_matches:
                    start = max(0, match.start() - 50)
                    end = min(len(content), match.end() + 30)
                    context = content[start:end]
                    # 合法引用模式：TODO 注释、TODO: xxx、TODO（、源码中 TODO
                    if not re.search(r'(TODO\s*注释|TODO[:：]|TODO[（(]|源码.*TODO|已知.*TODO|TODO\s+已)', context, re.IGNORECASE):
                        # 可能是未完成的 TODO
                        has_unfinished = True
                        break
            
            if has_unfinished:
                self.findings.append(ReviewFinding(
                    severity="P1",
                    category="incomplete_analysis",
                    file=str(file_path),
                    location="N/A",
                    description="文档中包含 TODO 或 TBD 标记",
                    suggestion="完成所有待办项或移除标记"
                ))
    
    def _check_depth(self, content: str, file_path: Path):
        """检查分析深度"""
        # 检查是否有表格
        tables = re.findall(r'\|.*\|.*\|', content)
        if len(tables) < self.min_tables:
            self.findings.append(ReviewFinding(
                severity="P3",
                category="shallow_analysis",
                file=str(file_path),
                location="N/A",
                description=f"表格数量不足：{len(tables)} < {self.min_tables}",
                suggestion="添加更多结构化表格来组织信息"
            ))
        
        # 检查文档长度
        if len(content) < 2000:
            self.findings.append(ReviewFinding(
                severity="P2",
                category="shallow_analysis",
                file=str(file_path),
                location="N/A",
                description=f"文档过短：{len(content)} 字符",
                suggestion="扩展分析内容，提供更多细节"
            ))
    
    def _check_structure(self, content: str, file_path: Path):
        """检查文档结构"""
        # 检查是否有标题
        if not re.search(r'^#\s+', content, re.MULTILINE):
            self.findings.append(ReviewFinding(
                severity="P1",
                category="missing_structure",
                file=str(file_path),
                location="N/A",
                description="缺少主标题",
                suggestion="添加 # 标题"
            ))
        
        # 检查是否有章节
        sections = re.findall(r'^##\s+', content, re.MULTILINE)
        if len(sections) < 3:
            self.findings.append(ReviewFinding(
                severity="P2",
                category="missing_structure",
                file=str(file_path),
                location="N/A",
                description=f"章节数量不足：{len(sections)} < 3",
                suggestion="添加更多 ## 章节来组织内容"
            ))
    
    def _generate_report(self, round_num: int) -> ReviewReport:
        """生成审查报告"""
        # 统计严重性
        summary = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        for f in self.findings:
            summary[f.severity] = summary.get(f.severity, 0) + 1
        
        # 判断是否收敛（P0=0 且 P1<=2）
        convergence = summary["P0"] == 0 and summary["P1"] <= 2
        
        # 判断结论
        if convergence and summary["P2"] <= 3:
            verdict = "PASS"
        elif convergence:
            verdict = "NEEDS_REVISION"
        else:
            verdict = "FAIL"
        
        return ReviewReport(
            round=round_num,
            timestamp=datetime.now().isoformat(),
            analysis_dir=str(self.analysis_dir),
            findings=self.findings,
            summary=summary,
            convergence=convergence,
            verdict=verdict
        )
    
    def _save_report(self, report: ReviewReport, round_num: int):
        """保存审查报告"""
        handoff_dir = self.analysis_dir / ".handoff"
        handoff_dir.mkdir(exist_ok=True)
        
        report_path = handoff_dir / f"review-report-{round_num}.json"
        
        # 转换为可序列化格式
        report_dict = asdict(report)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Review report saved: {report_path}")
        
        # 同时生成 Markdown 版本
        self._save_markdown_report(report, round_num)
    
    def _save_markdown_report(self, report: ReviewReport, round_num: int):
        """保存 Markdown 格式的审查报告"""
        handoff_dir = self.analysis_dir / ".handoff"
        report_path = handoff_dir / f"review-report-{round_num}.md"
        
        lines = [
            f"# Review Report - Round {report.round}",
            "",
            f"**Timestamp**: {report.timestamp}",
            f"**Analysis Dir**: {report.analysis_dir}",
            f"**Verdict**: {report.verdict}",
            f"**Convergence**: {'✅ Yes' if report.convergence else '❌ No'}",
            "",
            "## Summary",
            "",
            "| Severity | Count |",
            "|----------|-------|",
        ]
        
        for severity in ["P0", "P1", "P2", "P3"]:
            count = report.summary.get(severity, 0)
            lines.append(f"| {severity} | {count} |")
        
        lines.extend([
            "",
            "## Findings",
            "",
        ])
        
        for i, finding in enumerate(report.findings, 1):
            lines.extend([
                f"### {i}. [{finding.severity}] {finding.category}",
                "",
                f"**File**: {finding.file}",
                f"**Location**: {finding.location}",
                "",
                f"**Description**: {finding.description}",
                "",
                f"**Suggestion**: {finding.suggestion}",
                "",
            ])
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"✅ Markdown report saved: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Review Agent - 独立审查代理")
    parser.add_argument("analysis_dir", help="分析目录路径")
    parser.add_argument("--round", type=int, default=1, help="审查轮次")
    parser.add_argument("--strict", action="store_true", help="严格模式")
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.analysis_dir):
        print(f"❌ Error: {args.analysis_dir} is not a directory")
        sys.exit(1)
    
    agent = ReviewAgent(args.analysis_dir, strict=args.strict)
    report = agent.review(round_num=args.round)
    
    print("\n" + "=" * 60)
    print("Review Summary")
    print("=" * 60)
    print(f"Round: {report.round}")
    print(f"Verdict: {report.verdict}")
    print(f"Convergence: {'✅ Yes' if report.convergence else '❌ No'}")
    print("\nFindings by Severity:")
    for severity in ["P0", "P1", "P2", "P3"]:
        count = report.summary.get(severity, 0)
        print(f"  {severity}: {count}")
    
    # 返回非零退出码表示审查未通过
    if report.verdict == "FAIL":
        sys.exit(1)
    elif report.verdict == "NEEDS_REVISION":
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
