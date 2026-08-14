#!/usr/bin/env python3
"""
弹性分析运行器 (Resilient Analysis Runner)

解决核心问题：分析大项目时 LLM 并发/rate limit 导致 subagent 失败，主 agent 停止。

三层防线：
1. 任务级重试：每个分析任务最多重试 5 次，指数退避
2. 批次级恢复：扫描检查点，自动重试所有 failed/pending 任务
3. 全局续传：通过 cron 定期调用此脚本，实现无人值守恢复

用法:
    # 首次运行（初始化）
    python3 resilient-runner.py --output-dir /path/to/analysis \
        --project-path /path/to/project \
        --plan PLAN.md --init

    # 恢复运行（自动检测失败任务并重试）
    python3 resilient-runner.py --output-dir /path/to/analysis \
        --auto-resume

    # 仅检查状态
    python3 resilient-runner.py --output-dir /path/to/analysis --status
"""

import argparse
import json
import os
import re
import sys
import time
import random
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict


# ============================================================
# 常量
# ============================================================

MAX_RETRIES = 5
RETRY_DELAYS = [30, 60, 120, 240, 480]  # 指数退避（秒）- 首次 30 秒快速恢复
RATE_LIMIT_EXTRA_WAIT = 30  # rate limit 额外等待
CHECKPOINT_FILE = ".resilient-checkpoint.json"


class TaskStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    SIMPLIFIED = "simplified"
    RATE_LIMITED = "rate_limited"
    PARTIAL = "partial"


# ============================================================
# 数据结构
# ============================================================

@dataclass
class TaskState:
    """单个任务的状态"""
    task_id: str
    name: str
    module_path: str = ""
    output_dir: str = ""
    expected_files: List[str] = field(default_factory=list)
    actual_files: List[str] = field(default_factory=list)
    status: str = TaskStatus.PENDING
    retry_count: int = 0
    last_attempt: Optional[str] = None
    next_retry: Optional[str] = None
    last_error: str = ""
    spawned: bool = False
    spawn_label: str = ""
    priority: int = 0


@dataclass
class Checkpoint:
    """全局检查点"""
    project_name: str = ""
    project_path: str = ""
    output_dir: str = ""
    plan_file: str = ""
    phase: str = "init"
    tasks: Dict[str, dict] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    last_scan: str = ""
    total_tasks: int = 0
    stats: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> 'Checkpoint':
        valid_keys = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid_keys)


# ============================================================
# 检查点管理
# ============================================================

class CheckpointManager:
    """检查点持久化管理"""

    def __init__(self, output_dir: str):
        self.checkpoint_path = os.path.join(output_dir, CHECKPOINT_FILE)
        self.output_dir = output_dir

    def load(self) -> Optional[Checkpoint]:
        if not os.path.exists(self.checkpoint_path):
            return None
        try:
            with open(self.checkpoint_path, 'r', encoding='utf-8') as f:
                return Checkpoint.from_dict(json.load(f))
        except Exception as e:
            print(f"⚠️ 加载检查点失败: {e}", file=sys.stderr)
            return None

    def save(self, checkpoint: Checkpoint):
        checkpoint.updated_at = datetime.now().isoformat(timespec='seconds')
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        tmp_path = self.checkpoint_path + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(checkpoint.to_dict(), f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self.checkpoint_path)  # 原子写入

    def exists(self) -> bool:
        return os.path.exists(self.checkpoint_path)


# ============================================================
# PLAN.md 解析器
# ============================================================

def parse_plan(plan_path: str) -> List[TaskState]:
    """从 PLAN.md 解析任务清单"""
    if not os.path.exists(plan_path):
        print(f"⚠️ 计划文件不存在: {plan_path}", file=sys.stderr)
        return []

    content = Path(plan_path).read_text(encoding='utf-8')
    tasks = []

    task_pattern = re.compile(
        r'###\s+Task\s+(\d+):\s+(.+?)(?:\s+\[status:\s*(\w+)\])?$',
        re.IGNORECASE | re.MULTILINE
    )

    for match in task_pattern.finditer(content):
        task_id = f"task_{match.group(1)}"
        name = match.group(2).strip()
        status = match.group(3).strip().lower() if match.group(3) else "pending"

        start = match.end()
        next_match = task_pattern.search(content, start)
        end = next_match.start() if next_match else len(content)
        section = content[start:end]

        expected_files = []
        module_path = ""
        for line in section.split('\n'):
            line = line.strip()
            if line.startswith('- ') and '.md' in line:
                file_ref = re.sub(r'^-\s+', '', line).split('  ')[0].strip()
                if file_ref and not file_ref.startswith('预期') and not file_ref.startswith('完成'):
                    expected_files.append(file_ref)
            mp = re.match(r'.*(?:路径|path):\s*[`"]?([^\s`"]+)', line, re.IGNORECASE)
            if mp:
                module_path = mp.group(1)

        output_match = re.search(r'输出目录:\s*(\S+)', section)
        task_output_dir = output_match.group(1) if output_match else ""

        tasks.append(TaskState(
            task_id=task_id,
            name=name,
            module_path=module_path,
            output_dir=task_output_dir,
            expected_files=expected_files,
            status="pending",
        ))

    return tasks


# ============================================================
# 文件系统扫描器
# ============================================================

class OutputScanner:
    """扫描输出目录，判断任务实际完成状态
    
    完成检测优先级：
    1. .task-complete.json 签名文件（最可靠）
    2. .task-report.json 子代理报告（次可靠）
    3. 文件存在 + 内容质量检查（兖底）
    """

    # 全局超时：如果项目首次启动后超过此时间，停止重试
    GLOBAL_TIMEOUT_HOURS = 1.5  # 1.5 小时
    
    # 单个文件最小内容阈值（字节）
    MIN_FILE_SIZE = 200  # 小于 200 字节的 md 基本是空壳
    
    # 内容质量标记：文件中必须包含这些关键词中的至少一个
    QUALITY_MARKERS = [
        '## ', '### ',  # 有标题结构
        '| ',            # 有表格
        '```',          # 有代码块
        'mermaid',      # 有图表
        '- **',         # 有加粗列表
    ]

    EXCLUDE_FILES = {
        'PLAN.md', 'RESEARCH_PLAN.md', 'PLAN_VERIFICATION_REPORT.md',
        'VERIFICATION_REPORT.md', 'EXECUTION_SUMMARY.json',
        'INDEX.md', 'VERSION.md', 'recursive-plan.md',
        'module-manifest.json',
    }

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)

    def scan_actual_files(self) -> Set[str]:
        """扫描所有实际生成的 .md 文件"""
        actual = set()
        if not self.output_dir.exists():
            return actual

        for md_file in self.output_dir.rglob('*.md'):
            # Only check relative path parts (not the full absolute path)
            # to avoid filtering out files under .openclaw output dirs
            rel = md_file.relative_to(self.output_dir)
            if any(part.startswith('.') for part in rel.parts):
                continue
            if md_file.name in self.EXCLUDE_FILES:
                continue
            actual.add(rel.as_posix())

        return actual

    def scan_completion_signatures(self) -> Dict[str, dict]:
        """扫描 .task-complete.json 签名文件
        
        这是 LLM 完成任务后生成的结构化签名，格式：
        {
            "task": "lib/encoding",
            "status": "completed",
            "files": {
                "INDEX.md": {"size": 3500, "hash": "a1b2c3", "has_mermaid": true},
                "00-overview/README.md": {"size": 5200, "hash": "d4e5f6", "has_mermaid": true}
            },
            "completed_at": "2026-07-03T22:30:00",
            "agent": "subagent-session-key"
        }
        
        Returns:
            {task_name_or_dir: signature_dict}
        """
        signatures = {}
        if not self.output_dir.exists():
            return signatures

        for sig_file in self.output_dir.rglob('.task-complete.json'):
            try:
                with open(sig_file, 'r', encoding='utf-8') as f:
                    sig = json.load(f)
                key = sig.get('task', sig_file.parent.name)
                sig['_dir'] = sig_file.parent.relative_to(self.output_dir).as_posix()
                sig['_path'] = str(sig_file)
                signatures[key] = sig
            except Exception:
                continue

        return signatures

    def scan_task_reports(self) -> List[dict]:
        """扫描所有 .task-report.json"""
        reports = []
        if not self.output_dir.exists():
            return reports

        for report_file in self.output_dir.rglob('.task-report.json'):
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                report['_dir'] = report_file.parent.relative_to(self.output_dir).as_posix()
                reports.append(report)
            except Exception:
                continue

        return reports

    def verify_file_content(self, file_path: Path) -> Tuple[bool, str]:
        """验证单个文件的内容质量
        
        Returns:
            (is_valid, reason)
        """
        if not file_path.exists():
            return False, "文件不存在"
        
        size = file_path.stat().st_size
        if size < self.MIN_FILE_SIZE:
            return False, f"文件太小 ({size}B < {self.MIN_FILE_SIZE}B)"
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            return False, f"无法读取: {e}"
        
        # 检查占位符（词边界正则，避免误报真实 API/宏名如 todo_start/end、REQUIRES_SERVICE_PLACEHOLDER_AS）
        # 先剥离代码块（mermaid/代码），代码块内的 todo/placeholder 等是合法内容
        content_no_code = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
        placeholder_patterns = [
            r'\bTODO\b', r'\bTBD\b', r'待补充', r'占位符', r'\bplaceholder\b', r'Coming soon',
            r'待评估', r'待完善', r'待完成', r'\bFIXME\b', r'\bXXX\b',
        ]
        # 只检查前 800 字符（正常文档不会开头就是占位符）
        head = content_no_code[:800]
        for pat in placeholder_patterns:
            m = re.search(pat, head, re.IGNORECASE)
            if m:
                # 排除代码块内的匹配（如 todo_start/end 出现在代码/行内代码中）
                pre = head[max(0, m.start()-40):m.end()+40]
                if '`' in pre:
                    continue
                return False, f"发现占位符: {pat}"
        
        # 检查质量标记：至少有一个结构标记
        has_structure = any(marker in content for marker in self.QUALITY_MARKERS)
        if not has_structure:
            return False, "无结构标记（标题/表格/代码块）"
        
        return True, "OK"

    def check_task_completion(self, task: TaskState, actual_files: Set[str], 
                               signatures: Dict[str, dict] = None) -> Tuple[str, float, str]:
        """检查单个任务的完成状态
        
        检测优先级：
        1. .task-complete.json 签名（如果有）
        2. .task-report.json 报告（如果有）
        3. 文件存在 + 内容验证
        
        Returns:
            (status, confidence, detail)
            confidence: 0.0-1.0，表示对这个判断的信心度
        """
        task_slug = task.name.replace('/', '-').replace(' ', '-').lower()
        signatures = signatures or {}
        
        # ── 优先级 1: 检查签名文件 ──
        for sig_key, sig in signatures.items():
            if task_slug in sig_key.lower() or sig_key.lower() in task_slug:
                sig_status = sig.get('status', '')
                sig_files = sig.get('files', {})
                
                if sig_status == 'completed' and sig_files:
                    # 验证签名中声称的文件是否真的存在且内容合理
                    valid_count = 0
                    total = len(sig_files)
                    for rel_path, file_info in sig_files.items():
                        full_path = self.output_dir / sig.get('_dir', '.') / rel_path
                        if not full_path.exists():
                            # 尝试从 output_dir 找
                            full_path = self.output_dir / rel_path
                        
                        if full_path.exists():
                            is_valid, _ = self.verify_file_content(full_path)
                            if is_valid:
                                valid_count += 1
                    
                    if valid_count >= total * 0.8:
                        return TaskStatus.COMPLETED, 0.95, f"签名验证通过 ({valid_count}/{total})"
                    else:
                        return TaskStatus.PARTIAL, 0.6, f"签名声称完成但只有 {valid_count}/{total} 文件有效"
                
                elif sig_status == 'failed':
                    return TaskStatus.FAILED, 0.9, f"签名标记失败: {sig.get('error', '?')}"
        
        # ── 优先级 2: 检查 .task-report.json ──
        reports = self.scan_task_reports()
        for r in reports:
            r_task = r.get('module', r.get('_dir', ''))
            if isinstance(r_task, dict):
                r_task = r_task.get('name', str(r_task))
            r_task = str(r_task)
            if task_slug in r_task.lower() or r_task.lower() in task_slug:
                r_status = r.get('status', '')
                if r_status == 'completed':
                    # 进一步验证文件
                    files_claimed = r.get('files_generated', [])
                    if files_claimed:
                        valid = sum(1 for f in files_claimed 
                                   if (self.output_dir / f).exists())
                        if valid >= len(files_claimed) * 0.8:
                            return TaskStatus.COMPLETED, 0.85, f"报告验证通过 ({valid}/{len(files_claimed)})"
                    else:
                        return TaskStatus.COMPLETED, 0.7, "报告标记完成（无文件清单）"
                elif r_status == 'failed':
                    return TaskStatus.FAILED, 0.8, f"报告标记失败"
        
        # ── 优先级 3: 文件存在 + 内容验证 ──
        if not task.expected_files:
            # 无预期文件清单，用任务名模糊匹配
            matching = [f for f in actual_files if task_slug in f.lower()]
            if matching:
                # 验证至少一个文件有实质内容
                for mf in matching[:3]:
                    full = self.output_dir / mf
                    valid, _ = self.verify_file_content(full)
                    if valid:
                        return TaskStatus.COMPLETED, 0.6, f"模糊匹配 + 内容验证 ({len(matching)} 文件)"
            return TaskStatus.PENDING, 0.5, "无预期文件清单，未找到匹配"
        
        # 逐个检查预期文件
        valid_count = 0
        total = len(task.expected_files)
        issues = []
        
        for exp in task.expected_files:
            norm = exp.replace('./', '').lstrip('/')
            norm = norm.split('  ')[0].strip()
            
            if '(' in norm:
                # 目录型预期
                dir_part = norm.split('(')[0].strip().rstrip('/')
                dir_full = self.output_dir / dir_part
                if dir_full.exists() and any(dir_full.rglob('*.md')):
                    # 检查目录下至少有一个有效文件
                    for sub_file in dir_full.rglob('*.md'):
                        valid, _ = self.verify_file_content(sub_file)
                        if valid:
                            valid_count += 1
                            break
                continue
            
            # 找文件
            file_path = None
            if norm in actual_files:
                file_path = self.output_dir / norm
            elif (self.output_dir / norm).exists():
                # 直接检查路径存在（绕过 EXCLUDE_FILES 导致的假阴性）
                file_path = self.output_dir / norm
            else:
                # 模糊匹配
                basename = Path(norm).name
                for af in actual_files:
                    if basename in af:
                        file_path = self.output_dir / af
                        break
            
            if file_path and file_path.exists():
                is_valid, reason = self.verify_file_content(file_path)
                if is_valid:
                    valid_count += 1
                else:
                    issues.append(f"{Path(norm).name}: {reason}")
            else:
                issues.append(f"{Path(norm).name}: 不存在")
        
        ratio = valid_count / total if total > 0 else 0
        detail = f"{valid_count}/{total} 有效" + (f" ({'; '.join(issues[:2])})" if issues else "")
        
        if ratio >= 0.8:
            return TaskStatus.COMPLETED, 0.7, detail  # 文件验证的信心度较低
        elif ratio >= 0.3:
            return TaskStatus.PARTIAL, 0.6, detail
        else:
            return TaskStatus.PENDING, 0.7, detail


# ============================================================
# 退避策略
# ============================================================

def get_retry_delay(retry_count: int, error_type: str = "") -> float:
    """获取重试延迟（秒）"""
    if retry_count >= MAX_RETRIES:
        return -1

    base_delay = RETRY_DELAYS[min(retry_count, len(RETRY_DELAYS) - 1)]

    if error_type == "rate_limit":
        base_delay += RATE_LIMIT_EXTRA_WAIT
    elif error_type == "timeout":
        base_delay = int(base_delay * 0.5)

    jitter = base_delay * 0.1 * random.random()
    return base_delay + jitter


def should_retry(task: TaskState) -> bool:
    """判断任务是否应该重试"""
    if task.retry_count >= MAX_RETRIES:
        return False
    if task.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED, TaskStatus.SIMPLIFIED):
        return False
    return True


def can_retry_now(task: TaskState) -> bool:
    """判断任务是否可以立即重试（考虑退避时间）"""
    if not task.next_retry:
        return True
    try:
        next_retry_time = datetime.fromisoformat(task.next_retry)
        return datetime.now() >= next_retry_time
    except Exception:
        return True


# ============================================================
# Subagent 派发指令生成
# ============================================================

def generate_spawn_command(task: TaskState, checkpoint: Checkpoint) -> str:
    """生成单个任务的环境无关派发描述（由适配层翻译为具体实现）"""
    output_base = checkpoint.output_dir
    project_path = checkpoint.project_path
    # 保持目录层级结构，只替换空格，保留斜杠作为目录分隔符
    module_slug = task.name.replace(' ', '-').lower()

    if task.module_path:
        expected_str = '\n'.join(f"  - {f}" for f in task.expected_files[:10])
        return (
            f"[重试 #{task.retry_count + 1}] 分析模块: {task.name}\n\n"
            f"项目路径: {project_path}\n"
            f"模块路径: {task.module_path}\n"
            f"输出目录: {output_base}/10-module-deep/{module_slug}/\n\n"
            f"预期生成文件:\n{expected_str}\n\n"
            f"按照 source-analyzer SKILL.md 的分析要求执行。\n"
            f"完成后在输出目录生成 .task-report.json。\n"
        )
    else:
        return (
            f"[重试 #{task.retry_count + 1}] {task.name}\n\n"
            f"项目路径: {project_path}\n"
            f"输出目录: {output_base}/\n"
            f"预期文件: {', '.join(task.expected_files[:5])}\n\n"
            f"按照 source-analyzer SKILL.md 执行。完成后生成 .task-report.json。\n"
        )


def generate_continuation_prompt(failed_tasks: List[TaskState], checkpoint: 'Checkpoint') -> str:
    """生成 continuation prompt — 让 agent session 自主决定怎么完成

    核心思路：脚本负责检测和报告状态，agent 负责决策和执行。
    不硬编码具体步骤，不替 agent 做决定。
    """
    cp = checkpoint
    script_path = os.path.abspath(__file__)

    lines = [
        f"源码分析自动恢复：{cp.project_name}",
        "",
        "之前的分析任务部分失败，需要继续完成。",
        "",
        "## 项目信息",
        "",
        f"- 项目: {cp.project_name}",
        f"- 源码路径: `{cp.project_path}`",
        f"- 输出目录: `{cp.output_dir}`",
        f"- 计划文件: `{cp.plan_file}`",
        "- Skill: source-analyzer ($SKILL_DIR/SKILL.md)",
        "",
        "## 当前状态",
        "",
        f"{cp.stats.get('completed', 0)}/{cp.total_tasks} 已完成 ({cp.stats.get('completion_rate', 0):.1f}%)",
        "",
        f"## 失败任务 ({len(failed_tasks)} 个)",
        "",
        "| 任务 | 模块路径 | 重试 | 状态 | 上次错误 | 已有文件 |",
        "|------|----------|------|------|----------|----------|",
    ]

    for task in failed_tasks:
        module_path = task.module_path or '-'
        error = task.last_error[:50] + '...' if len(task.last_error) > 50 else (task.last_error or '-')
        existing = str(len(task.actual_files)) + ' 个' if task.actual_files else '无'
        lines.append(
            f"| {task.name} | {module_path} | {task.retry_count}/{MAX_RETRIES} | {task.status} | {error} | {existing} |"
        )

    lines.extend([
        "",
        "## 你的任务",
        "",
        "请自主决定最佳执行方式：",
        "1. 读取 source-analyzer SKILL.md 了解分析要求",
        "2. 检查每个失败任务已有的输出文件，只补充缺失的部分",
        "3. 用 [DISPATCH] 行为指令并行派发失败任务（不要串行）",
        "4. 用 [WAIT] 等待完成",
        "5. 完成后运行同步检查：",
        f"   `python3 {script_path} -o {cp.output_dir} --sync`",
        f"6. 如果仍有失败，继续重试（每个任务最多 {MAX_RETRIES} 次）",
        "7. 如果遇到 rate_limit，减少并行数，增加等待时间",
        "8. 全部完成后移除定时恢复任务（如环境支持）",
        "",
        "## 关键约束",
        "",
        "- 不要重新生成已有的文件（浪费 token）",
        "- 根据 PLAN.md 中定义的策略选择分析深度",
        f"- 检查点文件: `{cp.output_dir}/.resilient-checkpoint.json`",
        f"- 如果某任务已重试 {MAX_RETRIES} 次仍失败，降级为简化分析或跳过",
        "",
        "开始执行。",
    ])

    return '\n'.join(lines)


# ============================================================
# 核心运行器
# ============================================================

class ResilientRunner:
    """弹性分析运行器"""

    def __init__(self, output_dir: str, project_path: str = "", plan_file: str = ""):
        self.output_dir = os.path.abspath(output_dir)
        self.project_path = os.path.abspath(project_path) if project_path else ""
        self.plan_file = plan_file
        self.cp_mgr = CheckpointManager(self.output_dir)
        self.scanner = OutputScanner(self.output_dir)

    def init_checkpoint(self, tasks: List[TaskState]) -> Checkpoint:
        """初始化检查点"""
        project_name = os.path.basename(self.project_path) if self.project_path else \
                       os.path.basename(self.output_dir)

        checkpoint = Checkpoint(
            project_name=project_name,
            project_path=self.project_path,
            output_dir=self.output_dir,
            plan_file=self.plan_file,
            phase="phase2",
            created_at=datetime.now().isoformat(timespec='seconds'),
            total_tasks=len(tasks),
        )

        for task in tasks:
            checkpoint.tasks[task.task_id] = asdict(task)

        self._update_stats(checkpoint)
        self.cp_mgr.save(checkpoint)
        return checkpoint

    def load_or_init(self) -> Checkpoint:
        """加载或初始化检查点"""
        cp = self.cp_mgr.load()
        if cp is None:
            if self.plan_file and os.path.exists(self.plan_file):
                tasks = parse_plan(self.plan_file)
                if tasks:
                    cp = self.init_checkpoint(tasks)
                    print(f"✅ 从 PLAN.md 初始化检查点: {len(tasks)} 个任务")
                else:
                    cp = self._init_empty()
                    print("⚠️ PLAN.md 中未找到任务")
            else:
                cp = self._init_empty()
                print("⚠️ 无检查点无计划，将仅扫描输出目录")
        else:
            print(f"✅ 加载检查点: {cp.total_tasks} 个任务")
        return cp

    def _init_empty(self) -> Checkpoint:
        project_name = os.path.basename(self.project_path) if self.project_path else \
                       os.path.basename(self.output_dir)
        cp = Checkpoint(
            project_name=project_name,
            project_path=self.project_path,
            output_dir=self.output_dir,
            plan_file=self.plan_file,
            created_at=datetime.now().isoformat(timespec='seconds'),
        )
        self.cp_mgr.save(cp)
        return cp

    def _update_stats(self, cp: Checkpoint):
        """更新统计信息"""
        status_counts = {}
        for task_dict in cp.tasks.values():
            s = task_dict.get('status', 'unknown')
            status_counts[s] = status_counts.get(s, 0) + 1

        total = len(cp.tasks)
        completed = status_counts.get(TaskStatus.COMPLETED, 0)
        cp.stats = {
            'total': total,
            'completed': completed,
            'failed': status_counts.get(TaskStatus.FAILED, 0),
            'pending': status_counts.get(TaskStatus.PENDING, 0),
            'in_progress': status_counts.get(TaskStatus.IN_PROGRESS, 0),
            'skipped': status_counts.get(TaskStatus.SKIPPED, 0),
            'simplified': status_counts.get(TaskStatus.SIMPLIFIED, 0),
            'rate_limited': status_counts.get(TaskStatus.RATE_LIMITED, 0),
            'partial': status_counts.get(TaskStatus.PARTIAL, 0),
            'completion_pct': f"{completed}/{total}" if total > 0 else "0/0",
            'completion_rate': round(completed / total * 100, 1) if total > 0 else 0,
        }

    def sync_status(self, cp: Checkpoint) -> Checkpoint:
        """同步状态：扫描输出目录，更新任务完成状态"""
        actual_files = self.scanner.scan_actual_files()
        signatures = self.scanner.scan_completion_signatures()
        reports = self.scanner.scan_task_reports()

        report_by_module = {}
        for r in reports:
            module = r.get('module', r.get('_dir', ''))
            if isinstance(module, dict):
                module = module.get('name', str(module))
            report_by_module[str(module)] = r

        updated_count = 0
        for task_id, task_dict in cp.tasks.items():
            task = TaskState(**{k: v for k, v in task_dict.items() if k in TaskState.__dataclass_fields__})

            if task.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED, TaskStatus.SIMPLIFIED):
                continue

            # 使用新的三级检测
            status, confidence, detail = self.scanner.check_task_completion(
                task, actual_files, signatures
            )

            if status == TaskStatus.COMPLETED:
                task.status = TaskStatus.COMPLETED
                task_slug = task.name.replace('/', '-').replace(' ', '-').lower()
                task.actual_files = [f for f in actual_files if task_slug in f.lower()][:20]
                updated_count += 1
            elif status == TaskStatus.FAILED:
                task.last_error = detail
                if task.status != TaskStatus.FAILED:
                    task.status = TaskStatus.FAILED
                    updated_count += 1
            elif status == TaskStatus.PARTIAL:
                task.status = TaskStatus.PARTIAL
                task_slug = task.name.replace('/', '-').replace(' ', '-').lower()
                task.actual_files = [f for f in actual_files if task_slug in f.lower()][:20]

            # 补充检查 subagent 报告（低优先级信号）
            task_slug = task.name.replace('/', '-').replace(' ', '-')
            for module_key, report in report_by_module.items():
                if task_slug.lower() in module_key.lower() or module_key.lower() in task_slug.lower():
                    report_status = report.get('status', '')
                    if report_status == 'completed':
                        # 验证 report 声称的文件是否真实存在（防假完成）
                        claimed = report.get('files_generated', []) or report.get('documents_generated', [])
                        outdir = task.output_dir
                        exists_count = 0
                        if outdir:
                            for f in claimed:
                                base = os.path.basename(str(f))
                                for root, dirs, files in os.walk(outdir):
                                    if base in files:
                                        exists_count += 1
                                        break
                        # 目录中实际 md 数
                        md_count = 0
                        if outdir and os.path.isdir(outdir):
                            for root, dirs, files in os.walk(outdir):
                                md_count += sum(1 for f in files if f.endswith('.md'))
                        if claimed and exists_count >= max(1, int(len(claimed) * 0.6)):
                            task.status = TaskStatus.COMPLETED
                            task.actual_files = report.get('files_generated', [])
                            updated_count += 1
                        elif md_count >= 3:
                            task.status = TaskStatus.COMPLETED
                            task.actual_files = report.get('files_generated', [])
                            updated_count += 1
                        else:
                            # 假完成：报告声称完成但文件缺失
                            task.last_error = 'report claims completed but files missing (%d/%d, md=%d)' % (exists_count, len(claimed), md_count)
                            task.status = TaskStatus.PARTIAL
                            updated_count += 1
                    elif report_status == 'failed':
                        task.last_error = report.get('error', 'Subagent reported failure')
                        if task.status != TaskStatus.FAILED:
                            task.status = TaskStatus.FAILED
                            updated_count += 1

            cp.tasks[task_id] = asdict(task)

        cp.last_scan = datetime.now().isoformat(timespec='seconds')
        self._update_stats(cp)
        self.cp_mgr.save(cp)

        if updated_count > 0:
            print(f"📊 状态同步: 更新了 {updated_count} 个任务")

        return cp

    def check_global_timeout(self, cp: Checkpoint) -> bool:
        """检查是否超过全局超时时间
        
        如果项目首次启动后超过 1.5 小时且仍有未完成任务，
        则认为 LLM 服务不可用，停止继续重试。
        """
        if not cp.created_at:
            return False
        try:
            started = datetime.fromisoformat(cp.created_at)
        except Exception:
            return False
        elapsed = (datetime.now() - started).total_seconds() / 3600
        return elapsed > self.scanner.GLOBAL_TIMEOUT_HOURS

    def get_retryable_tasks(self, cp: Checkpoint) -> List[TaskState]:
        """获取需要重试的任务"""
        retryable = []
        now = datetime.now()

        for task_dict in cp.tasks.values():
            task = TaskState(**{k: v for k, v in task_dict.items() if k in TaskState.__dataclass_fields__})

            if not should_retry(task):
                continue

            if task.status in (TaskStatus.PENDING, TaskStatus.FAILED, TaskStatus.PARTIAL,
                               TaskStatus.RATE_LIMITED, TaskStatus.IN_PROGRESS):
                if can_retry_now(task):
                    retryable.append(task)
                else:
                    if task.next_retry:
                        try:
                            wait_until = datetime.fromisoformat(task.next_retry)
                            remaining = (wait_until - now).total_seconds()
                            if remaining > 0:
                                print(f"  ⏳ {task.name}: 还需等待 {remaining:.0f}s")
                        except Exception:
                            pass

        retryable.sort(key=lambda t: t.priority)
        return retryable

    def mark_task_spawned(self, cp: Checkpoint, task: TaskState):
        """标记任务已派发"""
        task.spawned = True
        task.status = TaskStatus.IN_PROGRESS
        task.last_attempt = datetime.now().isoformat(timespec='seconds')
        task.retry_count += 1

        delay = get_retry_delay(task.retry_count)
        if delay > 0:
            task.next_retry = (datetime.now() + timedelta(seconds=delay)).isoformat(timespec='seconds')

        cp.tasks[task.task_id] = asdict(task)
        self.cp_mgr.save(cp)

    def generate_spawn_instructions(self, tasks: List[TaskState], cp: Checkpoint) -> str:
        """为需要重试的任务生成环境无关的派发指令"""
        if not tasks:
            return "✅ 所有任务已完成，无需重试。"

        lines = [
            f"# 弹性重试指令 ({len(tasks)} 个任务)",
            "",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"输出目录: `{self.output_dir}`",
            "",
            "以下任务需要重新派发。使用 `[DISPATCH]` 行为指令派发每个任务，",
            "然后 `[WAIT]` 等待完成。",
            "",
        ]

        for i, task in enumerate(tasks, 1):
            spawn_desc = generate_spawn_command(task, cp)
            module_slug = task.name.replace('/', '-').replace(' ', '-').lower()
            label = f"retry-{module_slug}"

            lines.append(f"## 重试任务 {i}/{len(tasks)}: {task.name}")
            lines.append("")
            lines.append(f"- **Task ID**: {task.task_id}")
            lines.append(f"- **重试次数**: {task.retry_count}/{MAX_RETRIES}")
            lines.append(f"- **上次错误**: {task.last_error or '无'}")
            lines.append(f"- **状态**: {task.status}")
            lines.append("")
            lines.append("```")
            lines.append(f'[DISPATCH:')
            lines.append(f'    task="""{spawn_desc}""",')
            lines.append(f'    label="{label}"')
            lines.append(f']')
            lines.append("``")
            lines.append("")

        script_path = os.path.abspath(__file__)
        lines.append("---")
        lines.append("")
        lines.append("派发完所有任务后:")
        lines.append("```")
        lines.append(f'[WAIT: "等待 {len(tasks)} 个重试任务完成"]')
        lines.append("```")
        lines.append("")
        lines.append("等待完成后，再次运行此脚本检查状态:")
        lines.append("```")
        lines.append(f"python3 {script_path} --output-dir {self.output_dir} --auto-resume")
        lines.append("```")

        return '\n'.join(lines)

    def generate_status_report(self, cp: Checkpoint) -> str:
        """生成状态报告"""
        self._update_stats(cp)
        stats = cp.stats

        lines = [
            "# 分析状态报告",
            "",
            f"**项目**: {cp.project_name}",
            f"**输出目录**: `{cp.output_dir}`",
            f"**最后扫描**: {cp.last_scan or '未扫描'}",
            f"**最后更新**: {cp.updated_at}",
            "",
            "## 总览",
            "",
            "| 指标 | 值 |",
            "|------|------|",
            f"| 总任务数 | {stats.get('total', 0)} |",
            f"| ✅ 已完成 | {stats.get('completed', 0)} ({stats.get('completion_rate', 0):.1f}%) |",
            f"| ⏳ 待处理 | {stats.get('pending', 0)} |",
            f"| 🔄 进行中 | {stats.get('in_progress', 0)} |",
            f"| ❌ 失败 | {stats.get('failed', 0)} |",
            f"| ⏭️ 已跳过 | {stats.get('skipped', 0)} |",
            f"| 📝 简化分析 | {stats.get('simplified', 0)} |",
            f"| 🔒 被限流 | {stats.get('rate_limited', 0)} |",
            f"| 📦 部分完成 | {stats.get('partial', 0)} |",
            "",
        ]

        total = stats.get('total', 0)
        completed = stats.get('completed', 0)
        if total > 0:
            pct = completed / total
            bar_len = 40
            filled = int(bar_len * pct)
            bar = '█' * filled + '░' * (bar_len - filled)
            lines.append(f"进度: [{bar}] {completed}/{total} ({pct*100:.1f}%)")
            lines.append("")

        retryable = self.get_retryable_tasks(cp)
        if retryable:
            lines.append(f"## 需要重试的任务 ({len(retryable)} 个)")
            lines.append("")
            lines.append("| 任务 | 状态 | 重试 | 下次重试 | 错误 |")
            lines.append("|------|------|------|----------|------|")
            for task in retryable[:20]:
                next_retry = task.next_retry if task.next_retry else "立即"
                error = task.last_error[:40] + '...' if len(task.last_error) > 40 else (task.last_error or '-')
                lines.append(f"| {task.name} | {task.status} | {task.retry_count}/{MAX_RETRIES} | {next_retry} | {error} |")

            if len(retryable) > 20:
                lines.append(f"| ... 还有 {len(retryable) - 20} 个 | | | | |")
            lines.append("")

        exhausted = []
        for task_dict in cp.tasks.values():
            if task_dict.get('retry_count', 0) >= MAX_RETRIES and task_dict.get('status') != TaskStatus.COMPLETED:
                exhausted.append(task_dict)

        if exhausted:
            lines.append(f"## ⚠️ 超过最大重试次数的任务 ({len(exhausted)} 个)")
            lines.append("")
            for t in exhausted:
                lines.append(f"- **{t['name']}**: 重试 {t['retry_count']} 次，最后错误: {t.get('last_error', 'unknown')}")
            lines.append("")

        lines.append("## 建议")
        lines.append("")
        if stats.get('completion_rate', 0) >= 100:
            lines.append("✅ 所有任务已完成！可以运行验证脚本检查质量。")
        elif retryable:
            lines.append(f"📋 有 {len(retryable)} 个任务可以重试。运行 --auto-resume 自动恢复。")
        elif exhausted:
            lines.append(f"⚠️ {len(exhausted)} 个任务超过最大重试次数。考虑手动检查或简化分析。")
        else:
            lines.append("📋 等待任务完成中...")

        return '\n'.join(lines)

    def auto_resume(self) -> dict:
        """自动恢复：扫描 + 判断 + 输出指令"""
        cp = self.load_or_init()
        cp = self.sync_status(cp)

        self._update_stats(cp)
        if cp.stats.get('completion_rate', 0) >= 100:
            return {
                'status': 'completed',
                'retryable_count': 0,
                'completed_count': cp.stats.get('completed', 0),
                'instructions': '✅ 所有任务已完成！',
                'report': self.generate_status_report(cp),
            }

        retryable = self.get_retryable_tasks(cp)

        if not retryable:
            all_done = all(
                t.get('status') in (TaskStatus.COMPLETED, TaskStatus.SKIPPED, TaskStatus.SIMPLIFIED)
                for t in cp.tasks.values()
            )
            if all_done:
                return {
                    'status': 'completed',
                    'retryable_count': 0,
                    'completed_count': cp.stats.get('completed', 0),
                    'instructions': '✅ 所有任务已完成或处理！',
                    'report': self.generate_status_report(cp),
                }
            else:
                return {
                    'status': 'waiting_backoff',
                    'retryable_count': 0,
                    'completed_count': cp.stats.get('completed', 0),
                    'instructions': '⏳ 所有未完成任务都在退避等待中，请稍后再运行。',
                    'report': self.generate_status_report(cp),
                }

        instructions = self.generate_spawn_instructions(retryable, cp)

        for task in retryable:
            if task.task_id in cp.tasks:
                cp.tasks[task.task_id]['spawned'] = True

        self.cp_mgr.save(cp)

        return {
            'status': 'needs_retry',
            'retryable_count': len(retryable),
            'completed_count': cp.stats.get('completed', 0),
            'instructions': instructions,
            'report': self.generate_status_report(cp),
        }

    # ============================================================
    # Continuation prompt（给 cron session 的恢复指令）
    # ============================================================

    def generate_continuation(self, dry_run: bool = False) -> dict:
        """生成 continuation prompt 并输出
        
        这不直接派发任务，而是生成一段 prompt 文本。
        cron session 拿到这段 prompt 后，自主决定怎么执行。
        
        核心设计：脚本检测 + 报告，agent 决策 + 执行。
        """
        cp = self.load_or_init()
        cp = self.sync_status(cp)
        self._update_stats(cp)

        # 检查全局超时
        if self.check_global_timeout(cp):
            return {
                'status': 'global_timeout',
                'failed_count': 0,
                'prompt': '',
                'report': self.generate_status_report(cp) + '\n\n## ⏱️ 全局超时\n\n项目启动已超过 1.5 小时，LLM 服务可能不可用。停止重试。\n建议检查 LLM 服务状态后手动恢复。',
            }

        # 全部完成
        if cp.stats.get('completion_rate', 0) >= 100:
            return {
                'status': 'completed',
                'failed_count': 0,
                'prompt': '',
                'report': self.generate_status_report(cp),
            }

        failed_tasks = self.get_retryable_tasks(cp)

        if not failed_tasks:
            all_done = all(
                t.get('status') in (TaskStatus.COMPLETED, TaskStatus.SKIPPED, TaskStatus.SIMPLIFIED)
                for t in cp.tasks.values()
            )
            return {
                'status': 'completed' if all_done else 'waiting_backoff',
                'failed_count': 0,
                'prompt': '',
                'report': self.generate_status_report(cp),
            }

        if dry_run:
            print(f"🔄 发现 {len(failed_tasks)} 个待重试任务 (dry-run)")
            for task in failed_tasks:
                print(f"  → [{task.retry_count+1}/{MAX_RETRIES}] {task.name}: {task.status}")
            return {
                'status': 'dry_run',
                'failed_count': len(failed_tasks),
                'prompt': '',
                'report': self.generate_status_report(cp),
            }

        # 更新重试计数和退避时间
        for task in failed_tasks:
            if task.task_id in cp.tasks:
                cp.tasks[task.task_id]['spawned'] = True
                cp.tasks[task.task_id]['last_attempt'] = datetime.now().isoformat(timespec='seconds')
        self.cp_mgr.save(cp)

        # 生成 continuation prompt
        prompt = generate_continuation_prompt(failed_tasks, cp)

        return {
            'status': 'needs_retry',
            'failed_count': len(failed_tasks),
            'completed_count': cp.stats.get('completed', 0),
            'prompt': prompt,
            'report': self.generate_status_report(cp),
        }


# ============================================================
# CLI 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='弹性分析运行器 - 自动检测失败任务并重试',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--output-dir', '-o', required=True, help='分析输出目录')
    parser.add_argument('--project-path', '-p', default='', help='项目源码路径')
    parser.add_argument('--plan', default='', help='PLAN.md 路径')
    parser.add_argument('--init', action='store_true', help='初始化检查点')
    parser.add_argument('--status', action='store_true', help='仅显示状态')
    parser.add_argument('--sync', action='store_true', help='仅同步状态')
    parser.add_argument('--auto-resume', action='store_true', help='检测失败任务，生成重试指令（交互式）')
    parser.add_argument('--continue', action='store_true', help='🚀 生成 continuation prompt（供 cron session 使用）')
    parser.add_argument('--dry-run', action='store_true', help='模拟执行，不实际派发任务')
    parser.add_argument('--json', action='store_true', help='JSON 输出（用于 cron）')
    parser.add_argument('--max-retries', type=int, default=MAX_RETRIES, help=f'最大重试次数 (默认 {MAX_RETRIES})')

    args = parser.parse_args()

    # Note: --max-retries affects get_retry_delay/should_retry via module-level MAX_RETRIES
    if args.max_retries != MAX_RETRIES:
        # Can't use global in same scope after use; just warn
        print(f"Note: --max-retries={args.max_retries} (default is {MAX_RETRIES}). Edit script to change globally.)")

    runner = ResilientRunner(
        output_dir=args.output_dir,
        project_path=args.project_path,
        plan_file=args.plan,
    )

    if args.init:
        if args.plan:
            tasks = parse_plan(args.plan)
            if tasks:
                cp = runner.init_checkpoint(tasks)
                print(f"✅ 检查点已初始化: {cp.total_tasks} 个任务")
                print(runner.generate_status_report(cp))
            else:
                print("❌ PLAN.md 中未找到任务", file=sys.stderr)
                sys.exit(1)
        else:
            print("❌ --init 需要 --plan 参数", file=sys.stderr)
            sys.exit(1)
        return

    if args.status:
        cp = runner.load_or_init()
        cp = runner.sync_status(cp)
        print(runner.generate_status_report(cp))
        return

    if args.sync:
        cp = runner.load_or_init()
        cp = runner.sync_status(cp)
        print("✅ 同步完成")
        print(runner.generate_status_report(cp))
        return

    if args.auto_resume:
        result = runner.auto_resume()

        if args.json:
            print(json.dumps({
                'status': result['status'],
                'retryable_count': result['retryable_count'],
                'completed_count': result['completed_count'],
                'timestamp': datetime.now().isoformat(timespec='seconds'),
                'output_dir': args.output_dir,
            }, indent=2, ensure_ascii=False))
        else:
            print(result['report'])
            print("\n" + "=" * 60)
            if result['status'] == 'needs_retry':
                print(f"\n📋 重试指令 ({result['retryable_count']} 个任务):")
                print("=" * 60)
                print(result['instructions'])
            elif result['status'] == 'completed':
                print("\n🎉 全部完成！")
            elif result['status'] == 'waiting_backoff':
                print("\n⏳ 等待退避结束后再运行")
        return

    # ─── CONTINUE（生成 continuation prompt）───
    if getattr(args, 'continue'):
        result = runner.generate_continuation(dry_run=args.dry_run)

        if args.json:
            print(json.dumps({
                'status': result.get('status', 'unknown'),
                'failed_count': result.get('failed_count', 0),
                'completed_count': result.get('completed_count', 0),
                'timestamp': datetime.now().isoformat(timespec='seconds'),
                'output_dir': args.output_dir,
            }, indent=2, ensure_ascii=False))
        else:
            print(result.get('report', ''))
            if result['status'] == 'needs_retry':
                print("\n" + "=" * 60)
                print(f"📋 Continuation Prompt ({result['failed_count']} 个失败任务):")
                print("=" * 60)
                print(result['prompt'])
            elif result['status'] == 'completed':
                print("\n🎉 全部完成！")
            elif result['status'] == 'waiting_backoff':
                print("\n⏳ 等待退避结束后再运行")
        return

    parser.print_help()


if __name__ == '__main__':
    main()
