#!/usr/bin/env python3
"""
路径工具模块 - 统一处理输出目录和环境变量
"""
import os
from pathlib import Path


def get_output_base() -> Path:
    """
    获取分析输出基目录
    
    优先级：
    1. 环境变量 SOURCE_ANALYZER_OUTPUT_BASE
    2. 默认值 ~/.openclaw/learning/projects
    
    Returns:
        Path: 输出基目录的绝对路径
    """
    env_base = os.environ.get("SOURCE_ANALYZER_OUTPUT_BASE")
    if env_base:
        # 支持 ~ 展开
        return Path(os.path.expanduser(env_base)).resolve()
    
    # 默认路径
    return Path.home() / '.openclaw' / 'learning' / 'projects'


def get_output_dir(project_name: str, output_arg: str = None) -> Path:
    """
    获取项目的输出目录
    
    优先级：
    1. 命令行参数 output_arg
    2. 环境变量 SOURCE_ANALYZER_OUTPUT_BASE + project_name
    3. 默认路径 ~/.openclaw/learning/projects/project_name
    
    Args:
        project_name: 项目名称
        output_arg: 命令行指定的输出目录（可选）
    
    Returns:
        Path: 项目输出目录的绝对路径
    """
    if output_arg:
        # 命令行参数优先
        return Path(os.path.expanduser(output_arg)).resolve()
    
    # 使用环境变量或默认路径
    return get_output_base() / project_name


def get_goals_file() -> Path:
    """
    获取 active-goals.json 文件路径
    
    优先级：
    1. 环境变量 SOURCE_ANALYZER_GOALS_FILE
    2. 默认值 ~/.openclaw/workspace/active-goals.json
    
    Returns:
        Path: goals 文件路径
    """
    env_file = os.environ.get("SOURCE_ANALYZER_GOALS_FILE")
    if env_file:
        return Path(os.path.expanduser(env_file)).resolve()
    
    return Path.home() / '.openclaw' / 'workspace' / 'active-goals.json'
