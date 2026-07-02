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
        
        # 遍历所有分析文档
        for md_file in self.analysis_dir.glob("**/*.md"):
            if md_file.name.startswith("INDEX") or md_file.name.startswith("VERIFICATION"):
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
        
        # 1. 检查蒸馏章节
        self._check_distillation(content, rel_path)
        
        # 2. 检查代码引用
        self._check_code_references(content, rel_path)
        
        # 3. 检查深度
        self._check_depth(content, rel_path)
        
        # 4. 检查结构完整性
        self._check_structure(content, rel_path)
    
    def _check_distillation(self, content: str, file_path: Path):
        """检查蒸馏章节质量"""
        # 检查设计洞察
        insight_match = re.search(r'##\s*💡\s*设计洞察(.*?)(?=##|\Z)', content, re.DOTALL)
        if not insight_match:
            self.findings.append(ReviewFinding(
                severity="P1",
                category="missing_distillation",
                file=str(file_path),
                location="N/A",
                description="缺少💡设计洞察章节",
                suggestion="添加设计洞察章节，提炼可移植的设计原则"
            ))
        else:
            insight_section = insight_match.group(1)
            # 统计原则数量
            principles = re.findall(r'\*\*原则\d+[：:]', insight_section)
            if len(principles) < self.min_golden_rules:
                self.findings.append(ReviewFinding(
                    severity="P2",
                    category="weak_distillation",
                    file=str(file_path),
                    location="💡设计洞察",
                    description=f"设计原则数量不足：{len(principles)} < {self.min_golden_rules}",
                    suggestion=f"至少提炼 {self.min_golden_rules} 条可移植的设计原则"
                ))
            
            # 检查去名检验
            if "去名检验" not in insight_section:
                self.findings.append(ReviewFinding(
                    severity="P2",
                    category="missing_name_test",
                    file=str(file_path),
                    location="💡设计洞察",
                    description="原则缺少去名检验",
                    suggestion="为每条原则添加去名检验，说明是否可移植"
                ))
        
        # 检查隐含陷阱
        gotcha_match = re.search(r'##\s*⚠️\s*隐含陷阱(.*?)(?=##|\Z)', content, re.DOTALL)
        if not gotcha_match:
            self.findings.append(ReviewFinding(
                severity="P1",
                category="missing_distillation",
                file=str(file_path),
                location="N/A",
                description="缺少⚠️隐含陷阱章节",
                suggestion="添加隐含陷阱章节，记录非显而易见的实现陷阱"
            ))
        else:
            gotcha_section = gotcha_match.group(1)
            # 统计陷阱数量
            gotchas = re.findall(r'\*\*陷阱\d+[：:]', gotcha_section)
            if len(gotchas) < self.min_gotchas:
                self.findings.append(ReviewFinding(
                    severity="P2",
                    category="weak_distillation",
                    file=str(file_path),
                    location="⚠️隐含陷阱",
                    description=f"隐含陷阱数量不足：{len(gotchas)} < {self.min_gotchas}",
                    suggestion=f"至少记录 {self.min_gotchas} 个非显而易见的实现陷阱"
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
        
        # 检查是否有 TODO 或 TBD
        if re.search(r'\bTODO\b|\bTBD\b', content, re.IGNORECASE):
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
