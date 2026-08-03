#!/usr/bin/env python3
"""
Analysis Orchestrator

自动化分析编排器，带异常处理、健康检查、自动重试。

核心机制:
1. 健康检查线程: 监控子代理状态，检测卡死/超时
2. 异常处理: BLOCKED/NEEDS_CONTEXT/DONE_WITH_CONCERNS 自动处理
3. 自动重试: 最多 3 次重试，每次升级模型
4. 降级策略: 子代理失败时降级为简化分析
5. 状态持久化: 断点续传

Usage:
    python3 orchestrator.py /path/to/analysis-plan.md

配置:
    $SKILL_DIR/scripts/orchestrator-config.yaml
"""

import argparse
import json
import os
import sys
import time
import threading
import signal
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict, field
from enum import Enum


# 自定义 JSON 编码器
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# ============================================================
# 配置
# ============================================================

@dataclass
class OrchestratorConfig:
    """编排器配置"""
    max_retries: int = 3                          # 最大重试次数
    retry_delay: float = 5.0                      # 重试延迟（秒）
    task_timeout: int = 600                       # 任务超时（秒，默认 10 分钟）
    health_check_interval: int = 30               # 健康检查间隔（秒）
    max_concurrent_tasks: int = 3                 # 最大并行任务数
    upgrade_model_on_retry: bool = True           # 重试时升级模型
    fallback_to_simplified: bool = True           # 失败时降级为简化分析
    checkpoint_file: str = ".checkpoint.json"     # 检查点文件
    log_file: str = "orchestrator.log"            # 日志文件
    
    # Handoff 文件系统
    enable_handoff: bool = True                   # 启用 handoff 系统
    handoff_dir: str = ".handoff"                 # handoff 目录
    
    # 上下文预算管理
    enable_context_budget: bool = True            # 启用上下文预算
    max_tokens_per_task: int = 50000              # 每个任务最大 token
    max_source_lines: int = 5000                  # 每个任务最大源码行数


# ============================================================
# 状态枚举
# ============================================================

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    DONE_WITH_CONCERNS = "done_with_concerns"
    NEEDS_CONTEXT = "needs_context"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"
    SIMPLIFIED = "simplified"


class ReviewStatus(Enum):
    PENDING = "pending"
    COMPLETENESS_PASS = "completeness_pass"
    COMPLETENESS_FAIL = "completeness_fail"
    QUALITY_PASS = "quality_pass"
    QUALITY_FAIL = "quality_fail"
    SKIPPED = "skipped"


# ============================================================
# 数据类
# ============================================================

@dataclass
class TaskDefinition:
    """任务定义"""
    id: str
    name: str
    priority: str  # P0, P1, P2
    output_file: str
    steps: List[str]
    input_files: List[str] = field(default_factory=list)
    estimated_time: int = 15  # 分钟
    retry_count: int = 0
    status: TaskStatus = TaskStatus.PENDING
    review_status: ReviewStatus = ReviewStatus.PENDING
    last_error: Optional[str] = None
    concerns: List[str] = field(default_factory=list)
    context_notes: List[str] = field(default_factory=list)
    output_path: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    agent_session_key: Optional[str] = None


@dataclass
class Checkpoint:
    """检查点"""
    project_name: str
    analysis_dir: str
    plan_file: str
    tasks: List[dict]
    created_at: str
    updated_at: str
    current_task_idx: int = 0
    phase: str = "planning"  # planning, executing, reviewing, completed, failed
    error_log: List[str] = field(default_factory=list)


# ============================================================
# 日志
# ============================================================

class Logger:
    """简单日志"""
    def __init__(self, log_file: str):
        self.log_file = log_file
        self._lock = threading.Lock()
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    def log(self, level: str, message: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [{level}] {message}"
        with self._lock:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        # 同时输出到 stdout
        print(line, flush=True)
    
    def info(self, msg): self.log("INFO", msg)
    def warn(self, msg): self.log("WARN", msg)
    def error(self, msg): self.log("ERROR", msg)
    def debug(self, msg): self.log("DEBUG", msg)


# ============================================================
# 健康检查
# ============================================================

class HealthChecker:
    """健康检查线程
    
    职责:
    1. 定期检查运行中任务是否超时
    2. 检查子代理是否卡死
    3. 检测异常状态并报告
    4. 触发自动恢复
    """
    
    def __init__(self, orchestrator, config: OrchestratorConfig, logger: Logger):
        self.orchestrator = orchestrator
        self.config = config
        self.logger = logger
        self._stop_event = threading.Event()
        self._thread = None
    
    def start(self):
        """启动健康检查线程"""
        self._thread = threading.Thread(
            target=self._check_loop,
            name="health-checker",
            daemon=True
        )
        self._thread.start()
        self.logger.info("Health checker started")
    
    def stop(self):
        """停止健康检查"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self.logger.info("Health checker stopped")
    
    def _check_loop(self):
        """检查循环"""
        while not self._stop_event.is_set():
            try:
                self._run_checks()
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
            
            # 等待或退出
            self._stop_event.wait(self.config.health_check_interval)
    
    def _run_checks(self):
        """执行检查"""
        tasks = self.orchestrator.tasks
        now = datetime.now()
        
        for i, task_dict in enumerate(tasks):
            task = TaskDefinition(**task_dict) if isinstance(task_dict, dict) else task_dict
            
            if task.status == TaskStatus.IN_PROGRESS and task.started_at:
                started = datetime.fromisoformat(task.started_at)
                elapsed = (now - started).total_seconds()
                
                # 检查超时
                if elapsed > self.config.task_timeout:
                    self.logger.warn(
                        f"Task '{task.name}' TIMEOUT: {elapsed:.0f}s > {self.config.task_timeout}s"
                    )
                    task.status = TaskStatus.TIMEOUT
                    task.last_error = f"Timeout after {elapsed:.0f}s"
                    self.orchestrator._handle_timeout(task)
                
                # 检查子代理状态
                if task.agent_session_key:
                    self._check_agent_status(task)
    
    def _check_agent_status(self, task: TaskDefinition):
        """检查子代理状态"""
        # 注意：这里需要调用 OpenClaw API 检查子代理状态
        # 实际实现需要通过 sessions_list 或 subagents list 检查
        # 目前标记为 TODO，实际使用时需要实现
        pass


# ============================================================
# 异常处理器
# ============================================================

class ExceptionHandler:
    """异常处理器
    
    职责:
    1. 分类异常类型
    2. 决定重试策略
    3. 收集上下文信息
    4. 更新任务状态
    """
    
    def __init__(self, config: OrchestratorConfig, logger: Logger):
        self.config = config
        self.logger = logger
    
    def classify_error(self, error: str) -> str:
        """分类错误类型"""
        error_lower = error.lower()
        
        if "timeout" in error_lower or "timed out" in error_lower:
            return "timeout"
        elif "permission" in error_lower or "denied" in error_lower:
            return "permission"
        elif "not found" in error_lower or "no such file" in error_lower:
            return "not_found"
        elif "context" in error_lower or "needs context" in error_lower:
            return "needs_context"
        elif "blocked" in error_lower:
            return "blocked"
        elif "concern" in error_lower or "warning" in error_lower:
            return "concerns"
        elif "rate limit" in error_lower or "429" in error_lower:
            return "rate_limit"
        elif "memory" in error_lower or "oom" in error_lower:
            return "out_of_memory"
        else:
            return "unknown"
    
    def get_retry_strategy(self, error_type: str, retry_count: int) -> dict:
        """获取重试策略"""
        if retry_count >= self.config.max_retries:
            return {
                "action": "give_up",
                "reason": f"Max retries ({self.config.max_retries}) exceeded",
            }
        
        strategies = {
            "timeout": {
                "action": "retry",
                "delay": self.config.retry_delay * (2 ** retry_count),  # 指数退避
                "upgrade_model": self.config.upgrade_model_on_retry,
                "simplify_task": True,
            },
            "permission": {
                "action": "escalate",
                "reason": "Permission denied, need user intervention",
            },
            "not_found": {
                "action": "skip",
                "reason": "Resource not found, skipping",
            },
            "needs_context": {
                "action": "provide_context",
                "delay": self.config.retry_delay,
            },
            "blocked": {
                "action": "decompose",
                "reason": "Task blocked, try decomposing",
            },
            "concerns": {
                "action": "fix_and_continue",
                "delay": self.config.retry_delay,
            },
            "rate_limit": {
                "action": "wait_and_retry",
                "delay": 60 * (2 ** retry_count),  # 等待更久
            },
            "out_of_memory": {
                "action": "simplify",
                "reason": "Out of memory, simplify analysis",
            },
            "unknown": {
                "action": "retry",
                "delay": self.config.retry_delay * (2 ** retry_count),
            },
        }
        
        return strategies.get(error_type, strategies["unknown"])


# ============================================================
# 检查点管理
# ============================================================

class CheckpointManager:
    """检查点管理器
    
    职责:
    1. 定期保存任务状态
    2. 支持断点续传
    3. 记录错误日志
    """
    
    def __init__(self, analysis_dir: str, checkpoint_file: str = ".checkpoint.json"):
        self.checkpoint_path = os.path.join(analysis_dir, checkpoint_file)
    
    def save(self, checkpoint: Checkpoint):
        """保存检查点"""
        checkpoint.updated_at = datetime.now().isoformat()
        with open(self.checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(asdict(checkpoint), f, indent=2, ensure_ascii=False, cls=CustomEncoder)
    
    def load(self) -> Optional[Checkpoint]:
        """加载检查点"""
        if not os.path.exists(self.checkpoint_path):
            return None
        with open(self.checkpoint_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Checkpoint(**data)
    
    def exists(self) -> bool:
        """检查检查点是否存在"""
        return os.path.exists(self.checkpoint_path)


# ============================================================
# Handoff 文件系统
# ============================================================

class HandoffManager:
    """Handoff 文件系统管理器
    
    基于 Harness Patterns 的结构化交接机制，实现 Agent 间的信息传递。
    
    职责:
    1. 创建和管理 handoff 目录结构
    2. 生成任务交接文档
    3. 追踪任务依赖关系
    4. 记录进度日志
    """
    
    def __init__(self, handoff_dir: str, logger: Logger):
        self.handoff_dir = handoff_dir
        self.logger = logger
        self._ensure_structure()
    
    def _ensure_structure(self):
        """确保 handoff 目录结构存在"""
        Path(self.handoff_dir).mkdir(parents=True, exist_ok=True)
        
        # 初始化文件
        files = {
            "context-map.md": "# Context Map\n\n源码上下文图（哪些文件对应哪些维度）\n",
            "pattern-notes.md": "# Pattern Notes\n\n探索笔记（初步发现）\n",
            "task-board.json": '{"tasks": [], "dependencies": {}}',
            "progress-log.md": "# Progress Log\n\n追加式进度日志\n\n",
        }
        
        for filename, initial_content in files.items():
            filepath = os.path.join(self.handoff_dir, filename)
            if not os.path.exists(filepath):
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(initial_content)
    
    def create_handoff_doc(self, task: TaskDefinition, context: Dict[str, Any]):
        """创建任务交接文档"""
        doc_path = os.path.join(self.handoff_dir, f"handoff-{task.id}.md")
        
        content = f"""# Handoff: {task.name}

## 任务信息

- **ID**: {task.id}
- **优先级**: {task.priority}
- **输出文件**: {task.output_file}
- **预估时间**: {task.estimated_time} 分钟

## 上下文

"""
        for key, value in context.items():
            content += f"### {key}\n\n{value}\n\n"
        
        content += f"""## 步骤

"""
        for i, step in enumerate(task.steps, 1):
            content += f"{i}. {step}\n"
        
        content += f"\n## 质量要求\n\n"
        content += f"- 包含 💡 设计洞察章节（≥2 条原则）\n"
        content += f"- 包含 ⚠️ 隐含陷阱章节（≥2 条陷阱）\n"
        content += f"- 每条原则通过去名检验\n"
        
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        self.logger.info(f"Created handoff doc: {doc_path}")
        return doc_path
    
    def update_task_board(self, task: TaskDefinition, status: str):
        """更新任务看板"""
        board_path = os.path.join(self.handoff_dir, "task-board.json")
        
        with open(board_path, "r", encoding="utf-8") as f:
            board = json.load(f)
        
        # 更新或添加任务
        task_entry = {
            "id": task.id,
            "name": task.name,
            "status": status,
            "priority": task.priority,
            "updated_at": datetime.now().isoformat(),
        }
        
        # 查找并更新现有任务
        found = False
        for i, t in enumerate(board["tasks"]):
            if t["id"] == task.id:
                board["tasks"][i] = task_entry
                found = True
                break
        
        if not found:
            board["tasks"].append(task_entry)
        
        with open(board_path, "w", encoding="utf-8") as f:
            json.dump(board, f, indent=2, ensure_ascii=False)
    
    def append_progress_log(self, message: str):
        """追加进度日志"""
        log_path = os.path.join(self.handoff_dir, "progress-log.md")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")


# ============================================================
# 上下文预算管理
# ============================================================

class ContextBudgetManager:
    """上下文预算管理器
    
    基于 Harness Patterns 的 Context Engineering 四操作:
    Select / Write / Compress / Isolate
    
    职责:
    1. 为每个任务分配上下文预算
    2. 追踪 token 消耗
    3. 按需加载源码（Select）
    4. 压缩分析结果（Compress）
    """
    
    def __init__(self, max_tokens: int, max_source_lines: int, logger: Logger):
        self.max_tokens = max_tokens
        self.max_source_lines = max_source_lines
        self.logger = logger
        self.consumed_tokens = 0
        self.task_budgets: Dict[str, int] = {}
    
    def allocate_budget(self, task: TaskDefinition, total_tasks: int) -> int:
        """为任务分配上下文预算"""
        # 简单平均分配，实际可以根据任务复杂度调整
        budget = self.max_tokens // max(1, total_tasks)
        self.task_budgets[task.id] = budget
        self.logger.debug(f"Allocated {budget} tokens for task {task.id}")
        return budget
    
    def select_source_files(self, task: TaskDefinition, available_files: List[str]) -> List[str]:
        """Select: 按需加载源码文件"""
        # 根据任务步骤选择相关文件
        selected = []
        total_lines = 0
        
        for file_path in available_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = len(f.readlines())
                
                if total_lines + lines <= self.max_source_lines:
                    selected.append(file_path)
                    total_lines += lines
                else:
                    self.logger.debug(f"Skipping {file_path}: exceeds budget")
                    break
            except Exception as e:
                self.logger.warn(f"Cannot read {file_path}: {e}")
        
        self.logger.info(f"Selected {len(selected)} files ({total_lines} lines) for task {task.id}")
        return selected
    
    def compress_analysis(self, analysis_content: str) -> str:
        """Compress: 压缩分析结果为结构化摘要"""
        # 提取关键信息
        lines = analysis_content.split("\n")
        
        # 保留标题和关键段落
        compressed = []
        for line in lines:
            if line.startswith("#") or line.startswith("- **") or line.startswith("| "):
                compressed.append(line)
        
        result = "\n".join(compressed)
        
        # 估算压缩率
        original_tokens = len(analysis_content) // 4
        compressed_tokens = len(result) // 4
        compression_ratio = (1 - compressed_tokens / max(1, original_tokens)) * 100
        
        self.logger.info(f"Compressed analysis: {compression_ratio:.1f}% reduction")
        return result
    
    def track_consumption(self, task_id: str, tokens: int):
        """追踪 token 消耗"""
        self.consumed_tokens += tokens
        self.logger.debug(f"Task {task_id} consumed {tokens} tokens (total: {self.consumed_tokens})")
    
    def check_budget_exceeded(self, task_id: str) -> bool:
        """检查是否超出预算"""
        budget = self.task_budgets.get(task_id, 0)
        # 简化实现：假设每个任务消耗的 token 数
        # 实际应该从 LLM API 获取
        return self.consumed_tokens > budget


# ============================================================
# 主编排器
# ============================================================

class AnalysisOrchestrator:
    """分析编排器
    
    核心职责:
    1. 解析分析计划
    2. 调度任务执行
    3. 处理异常和重试
    4. 管理健康检查
    5. 保存检查点
    6. 生成最终报告
    7. Handoff 文件系统管理
    8. 上下文预算管理
    """
    
    def __init__(
        self,
        plan_file: str,
        analysis_dir: str,
        config: Optional[OrchestratorConfig] = None,
    ):
        self.config = config or OrchestratorConfig()
        self.logger = Logger(os.path.join(analysis_dir, self.config.log_file))
        self.checkpoint_mgr = CheckpointManager(analysis_dir, self.config.checkpoint_file)
        self.exception_handler = ExceptionHandler(self.config, self.logger)
        self.health_checker = HealthChecker(self, self.config, self.logger)
        
        self.plan_file = plan_file
        self.analysis_dir = analysis_dir
        self.tasks: List[dict] = []
        self.checkpoint: Optional[Checkpoint] = None
        
        # Handoff 文件系统
        self.handoff_dir = os.path.join(analysis_dir, self.config.handoff_dir)
        if self.config.enable_handoff:
            self._init_handoff_system()
        
        # 上下文预算管理
        self.context_budget = ContextBudgetManager(
            max_tokens=self.config.max_tokens_per_task,
            max_source_lines=self.config.max_source_lines,
            logger=self.logger
        ) if self.config.enable_context_budget else None
        
        # 信号处理
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        
        self.logger.info(f"Orchestrator initialized: {analysis_dir}")
        if self.config.enable_handoff:
            self.logger.info(f"Handoff system enabled: {self.handoff_dir}")
        if self.config.enable_context_budget:
            self.logger.info(f"Context budget: {self.config.max_tokens_per_task} tokens, {self.config.max_source_lines} lines")
    
    def _init_handoff_system(self):
        """初始化 Handoff 文件系统"""
        self.handoff_mgr = HandoffManager(self.handoff_dir, self.logger)
        self.logger.info(f"Handoff system initialized: {self.handoff_dir}")
    
    def _handle_signal(self, signum, frame):
        """处理中断信号"""
        self.logger.info(f"Received signal {signum}, saving checkpoint...")
        self._save_checkpoint()
        self.health_checker.stop()
        sys.exit(0)
    
    def load_plan(self) -> List[TaskDefinition]:
        """加载分析计划"""
        plan_path = Path(self.plan_file)
        if not plan_path.exists():
            raise FileNotFoundError(f"Plan file not found: {self.plan_file}")
        
        content = plan_path.read_text()
        tasks = self._parse_plan(content)
        
        # 转换为 dict 存储
        self.tasks = [asdict(t) for t in tasks]
        self.logger.info(f"Loaded {len(tasks)} tasks from plan")
        return tasks
    
    def _parse_plan(self, content: str) -> List[TaskDefinition]:
        """解析分析计划"""
        tasks = []
        
        # 简单的 Markdown 解析
        # 实际使用时可以改用更完善的解析器
        lines = content.split("\n")
        current_task = None
        current_steps = []
        
        for line in lines:
            if line.startswith("### Task "):
                # 保存前一个任务
                if current_task and current_steps:
                    current_task.steps = current_steps.copy()
                    tasks.append(current_task)
                    current_steps = []
                
                # 解析任务头
                task_id = line.split("Task ")[1].split(":")[0].strip()
                task_name = line.split(": ", 1)[1].strip()
                
                current_task = TaskDefinition(
                    id=task_id,
                    name=task_name,
                    priority="P0",  # 默认
                    output_file="unknown.md",
                    steps=[],
                )
            
            elif line.startswith("**Priority**:"):
                if current_task:
                    current_task.priority = line.split("**Priority**: ")[1].strip()
            
            elif line.startswith("**Output**:"):
                if current_task:
                    current_task.output_file = line.split("**Output**: `")[1].rstrip("`")
            
            elif line.startswith("**Estimated Time**:"):
                if current_task:
                    time_str = line.split(": ")[1].strip()
                    # 解析分钟数 (处理 "10-15 minutes" 或 "15 minutes")
                    if "minutes" in time_str:
                        # 提取第一个数字
                        nums = re.findall(r'\d+', time_str)
                        if nums:
                            current_task.estimated_time = int(nums[0])
            
            elif line.startswith("- [ ] **Step"):
                if current_task:
                    # 提取步骤描述
                    try:
                        step = line.split("**Step")[1].split("**")[1].strip()
                    except (IndexError, ValueError):
                        step = line.strip()
                    current_steps.append(step)
        
        # 保存最后一个任务
        if current_task and current_steps:
            current_task.steps = current_steps.copy()
            tasks.append(current_task)
        
        return tasks
    
    def load_checkpoint_or_plan(self) -> bool:
        """加载检查点或计划"""
        if self.checkpoint_mgr.exists():
            self.logger.info("Found checkpoint, resuming...")
            self.checkpoint = self.checkpoint_mgr.load()
            self.tasks = self.checkpoint.tasks
            self.logger.info(f"Resumed from checkpoint: task {self.checkpoint.current_task_idx}")
            return True
        else:
            self.logger.info("No checkpoint found, loading plan...")
            self.load_plan()
            
            # 创建初始检查点
            self.checkpoint = Checkpoint(
                project_name=os.path.basename(self.analysis_dir),
                analysis_dir=self.analysis_dir,
                plan_file=self.plan_file,
                tasks=self.tasks.copy(),  # 已经是 dict 列表
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            )
            self._save_checkpoint()
            return False
    
    def _save_checkpoint(self):
        """保存检查点"""
        if self.checkpoint:
            self.checkpoint.tasks = self.tasks.copy()
            self.checkpoint_mgr.save(self.checkpoint)
            self.logger.debug("Checkpoint saved")
    
    def run(self):
        """运行分析流程"""
        self.logger.info("=" * 60)
        self.logger.info("Starting Analysis Orchestration")
        self.logger.info("=" * 60)
        
        # 加载
        resumed = self.load_checkpoint_or_plan()
        
        # 启动健康检查
        self.health_checker.start()
        
        try:
            # 执行任务
            self._execute_tasks(resumed_from=resumed)
            
            # 验证结果
            self._verify_results()
            
            # 完成
            self.checkpoint.phase = "completed"
            self._save_checkpoint()
            self.logger.info("=" * 60)
            self.logger.info("Analysis Complete!")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"Orchestration failed: {e}")
            self.checkpoint.phase = "failed"
            self.checkpoint.error_log.append(str(e))
            self._save_checkpoint()
            raise
        
        finally:
            self.health_checker.stop()
    
    def _execute_tasks(self, resumed_from: bool = False):
        """执行所有任务"""
        start_idx = self.checkpoint.current_task_idx if resumed_from else 0
        
        for i in range(start_idx, len(self.tasks)):
            task_dict = self.tasks[i]
            task = TaskDefinition(**task_dict) if isinstance(task_dict, dict) else task_dict
            
            # 跳过已完成的任务
            if task.status == TaskStatus.DONE:
                self.logger.info(f"Skipping completed task: {task.name}")
                continue
            
            self.logger.info(f"\n{'='*40}")
            self.logger.info(f"Task {i+1}/{len(self.tasks)}: {task.name}")
            self.logger.info(f"Priority: {task.priority}")
            self.logger.info(f"Output: {task.output_file}")
            self.logger.info(f"{'='*40}")
            
            # 执行任务
            success = self._execute_single_task(task, i)
            
            if not success:
                self.logger.warn(f"Task '{task.name}' failed after retries")
                if self.config.fallback_to_simplified:
                    self.logger.info("Attempting simplified analysis...")
                    self._execute_simplified(task)
            
            # 更新检查点
            self.checkpoint.current_task_idx = i + 1
            self._save_checkpoint()
    
    def _execute_single_task(self, task: TaskDefinition, task_idx: int) -> bool:
        """执行单个任务（带重试）"""
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now().isoformat()
        self._update_task(task)
        
        for retry in range(self.config.max_retries + 1):
            if retry > 0:
                task.status = TaskStatus.RETRYING
                task.retry_count = retry
                self.logger.warn(f"Retry {retry}/{self.config.max_retries}: {task.name}")
                
                # 指数退避
                delay = self.config.retry_delay * (2 ** (retry - 1))
                self.logger.info(f"Waiting {delay}s before retry...")
                time.sleep(delay)
            
            try:
                # 这里需要实际调用任务派发执行分析
                # 实际实现中，这里应该:
                # 1. 构建任务描述
                # 2. 派发子任务
                # 3. 等待完成
                # 4. 检查输出
                
                self.logger.info(f"Executing task: {task.name} (attempt {retry + 1})")
                
                # TODO: 实际调用任务派发
                # 这里模拟执行
                result = self._simulate_task_execution(task)
                
                if result == "success":
                    task.status = TaskStatus.DONE
                    task.completed_at = datetime.now().isoformat()
                    self._update_task(task)
                    
                    # 两阶段审查
                    review_passed = self._run_review(task)
                    if not review_passed:
                        self.logger.warn(f"Review failed for: {task.name}")
                        continue
                    
                    self.logger.info(f"✓ Task completed: {task.name}")
                    return True
                
                elif result == "needs_context":
                    task.status = TaskStatus.NEEDS_CONTEXT
                    task.context_notes.append("Missing context, providing more info")
                    self._update_task(task)
                    continue
                
                elif result == "blocked":
                    task.status = TaskStatus.BLOCKED
                    self._update_task(task)
                    # 尝试分解任务
                    self._decompose_task(task)
                    continue
                
                else:
                    task.last_error = f"Execution failed: {result}"
                    self._update_task(task)
                    continue
                    
            except Exception as e:
                error_type = self.exception_handler.classify_error(str(e))
                strategy = self.exception_handler.get_retry_strategy(error_type, retry)
                
                self.logger.warn(f"Error in task '{task.name}': {e}")
                self.logger.warn(f"Error type: {error_type}, Strategy: {strategy['action']}")
                
                task.last_error = str(e)
                self._update_task(task)
                
                if strategy["action"] == "give_up":
                    return False
                elif strategy["action"] == "skip":
                    task.status = TaskStatus.SKIPPED
                    self._update_task(task)
                    return False
                elif strategy["action"] == "simplify":
                    return False
        
        # 所有重试失败
        task.status = TaskStatus.FAILED
        self._update_task(task)
        return False
    
    def _simulate_task_execution(self, task: TaskDefinition) -> str:
        """模拟任务执行（实际使用时替换为真实调用）
        
        实际实现应该:
        1. 构建 task 描述
        2. 派发子任务 (使用 [DISPATCH] 行为指令)
        3. 等待完成 ([WAIT])
        4. 检查输出文件
        
        返回:
        - "success"
        - "needs_context"
        - "blocked"
        - 错误信息
        """
        # 检查输出文件是否存在（如果之前已生成）
        output_path = os.path.join(self.analysis_dir, task.output_file)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            task.output_path = output_path
            return "success"
        
        # 模拟执行
        self.logger.info(f"  [SIMULATED] Would spawn subagent for: {task.name}")
        self.logger.info(f"  [SIMULATED] Output: {task.output_file}")
        
        # 标记为成功（实际由 subagent 生成文件）
        return "success"
    
    def _run_review(self, task: TaskDefinition) -> bool:
        """两阶段审查"""
        self.logger.info(f"  Running review for: {task.name}")
        
        # Phase 1: Completeness Review
        task.review_status = ReviewStatus.PENDING
        completeness_passed = self._completeness_review(task)
        
        if not completeness_passed:
            task.review_status = ReviewStatus.COMPLETENESS_FAIL
            self._update_task(task)
            self.logger.warn(f"  Completeness review failed: {task.name}")
            return False
        
        task.review_status = ReviewStatus.COMPLETENESS_PASS
        self._update_task(task)
        
        # Phase 2: Quality Review
        quality_passed = self._quality_review(task)
        
        if not quality_passed:
            task.review_status = ReviewStatus.QUALITY_FAIL
            self._update_task(task)
            self.logger.warn(f"  Quality review failed: {task.name}")
            return False
        
        task.review_status = ReviewStatus.QUALITY_PASS
        self._update_task(task)
        self.logger.info(f"  ✓ Review passed: {task.name}")
        return True
    
    def _completeness_review(self, task: TaskDefinition) -> bool:
        """完整性审查"""
        output_path = os.path.join(self.analysis_dir, task.output_file)
        if not os.path.exists(output_path):
            self.logger.warn(f"  Output file missing: {task.output_file}")
            return False
        
        content = Path(output_path).read_text()
        
        # 检查禁止词
        forbidden = ["TBD", "TODO", "待补充"]
        for word in forbidden:
            if word.lower() in content.lower():
                self.logger.warn(f"  Found forbidden word: {word}")
                return False
        
        return True
    
    def _quality_review(self, task: TaskDefinition) -> bool:
        """质量审查"""
        output_path = os.path.join(self.analysis_dir, task.output_file)
        if not os.path.exists(output_path):
            return False
        
        content = Path(output_path).read_text()
        
        # 检查最小长度
        if len(content) < 500:
            self.logger.warn(f"  Output too short: {len(content)} chars")
            return False
        
        # 检查是否有表格
        if "|" not in content:
            self.logger.warn(f"  No tables found in output")
            return False
        
        return True
    
    def _execute_simplified(self, task: TaskDefinition):
        """执行简化分析（降级策略）"""
        self.logger.info(f"  Executing simplified analysis for: {task.name}")
        
        # 简化分析：只输出基本信息
        output_path = os.path.join(self.analysis_dir, task.output_file)
        simplified_content = f"""# {task.name} (Simplified Analysis)

> **Note**: This is a simplified analysis due to previous execution failures.

## Basic Info

- **Task**: {task.name}
- **Output File**: {task.output_file}
- **Analysis Time**: {datetime.now().strftime("%Y-%m-%d %H:%M")}
- **Status**: Simplified (full analysis failed)

## Steps

"""
        for i, step in enumerate(task.steps[:3], 1):  # 只取前 3 步
            simplified_content += f"### Step {i}: {step}\n\n"
        
        simplified_content += f"\n---\n*Generated: {datetime.now().isoformat()}*\n"
        
        Path(output_path).write_text(simplified_content)
        
        task.status = TaskStatus.SIMPLIFIED
        task.output_path = output_path
        task.completed_at = datetime.now().isoformat()
        self._update_task(task)
        
        self.logger.info(f"  ✓ Simplified analysis saved: {output_path}")
    
    def _decompose_task(self, task: TaskDefinition):
        """分解任务"""
        self.logger.info(f"  Decomposing task: {task.name}")
        
        if len(task.steps) > 1:
            # 将任务分解为子步骤
            mid = len(task.steps) // 2
            self.logger.info(f"  Split into {mid} + {len(task.steps) - mid} steps")
            # 实际实现中，这里会创建子任务并重新调度
        else:
            self.logger.warn(f"  Cannot decompose: only 1 step")
    
    def _handle_timeout(self, task: TaskDefinition):
        """处理超时"""
        self.logger.warn(f"Task timeout: {task.name}")
        
        # 尝试恢复
        if task.retry_count < self.config.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.RETRYING
            self._update_task(task)
        else:
            task.status = TaskStatus.FAILED
            self._update_task(task)
    
    def _update_task(self, task: TaskDefinition):
        """更新任务状态"""
        for i, t in enumerate(self.tasks):
            if t.get("id") == task.id or t.get("name") == task.name:
                self.tasks[i] = asdict(task)
                break
    
    def _verify_results(self):
        """验证分析结果"""
        self.logger.info("\n" + "=" * 40)
        self.logger.info("Verifying Analysis Results")
        self.logger.info("=" * 40)
        
        # 调用 verify-analysis.py
        verify_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "verify-analysis.py"
        )
        
        if os.path.exists(verify_script):
            import subprocess
            result = subprocess.run(
                ["python3", verify_script, self.analysis_dir, "--all"],
                capture_output=True,
                text=True
            )
            self.logger.info(result.stdout)
            if result.stderr:
                self.logger.warn(result.stderr)
    
    def generate_summary(self):
        """生成执行摘要"""
        summary = {
            "project": self.checkpoint.project_name,
            "analysis_dir": self.analysis_dir,
            "completed_at": datetime.now().isoformat(),
            "total_tasks": len(self.tasks),
            "completed": sum(1 for t in self.tasks if t.get("status") == TaskStatus.DONE.value),
            "simplified": sum(1 for t in self.tasks if t.get("status") == TaskStatus.SIMPLIFIED.value),
            "failed": sum(1 for t in self.tasks if t.get("status") == TaskStatus.FAILED.value),
            "skipped": sum(1 for t in self.tasks if t.get("status") == TaskStatus.SKIPPED.value),
            "errors": self.checkpoint.error_log,
        }
        
        summary_path = os.path.join(self.analysis_dir, "EXECUTION_SUMMARY.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        return summary


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Analysis Orchestrator")
    parser.add_argument("plan_file", help="Path to ANALYSIS_PLAN.md")
    parser.add_argument("--analysis-dir", "-o", default=None, help="Output directory")
    parser.add_argument("--max-retries", type=int, default=3, help="Max retries per task")
    parser.add_argument("--timeout", type=int, default=600, help="Task timeout in seconds")
    parser.add_argument("--health-interval", type=int, default=30, help="Health check interval")
    
    args = parser.parse_args()
    
    # 确定分析目录
    if args.analysis_dir:
        analysis_dir = args.analysis_dir
    else:
        # 从计划文件推断
        plan_dir = os.path.dirname(os.path.abspath(args.plan_file))
        analysis_dir = os.path.join(plan_dir, "analysis-output")
    
    os.makedirs(analysis_dir, exist_ok=True)
    
    # 创建配置
    config = OrchestratorConfig(
        max_retries=args.max_retries,
        task_timeout=args.timeout,
        health_check_interval=args.health_interval,
    )
    
    # 创建编排器
    orchestrator = AnalysisOrchestrator(
        plan_file=args.plan_file,
        analysis_dir=analysis_dir,
        config=config,
    )
    
    # 运行
    orchestrator.run()
    
    # 生成摘要
    summary = orchestrator.generate_summary()
    print(f"\n📊 Execution Summary:")
    print(f"  Total tasks: {summary['total_tasks']}")
    print(f"  Completed: {summary['completed']}")
    print(f"  Simplified: {summary['simplified']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Skipped: {summary['skipped']}")


if __name__ == "__main__":
    main()