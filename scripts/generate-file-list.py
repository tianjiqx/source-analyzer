#!/usr/bin/env python3
"""
自动识别关键文件，生成文件粒度分析列表

功能:
- 扫描项目目录结构
- 识别入口点、核心类、高频修改文件
- 计算文件复杂度
- 按优先级排序
- 输出文件分析列表

用法:
    python3 generate-file-list.py /path/to/project \
        --max-files 30 \
        --priority "entry,service,high-complexity" \
        -o $OUTPUT_BASE/project-name/FILE_LIST.md
"""

import os
import sys
import argparse
import subprocess
import json
from pathlib import Path
from collections import Counter

# 不同项目类型的文件优先级配置
PROJECT_TYPE_PRIORITIES = {
    'llm-agent': {
        'agent': 15,           # Agent 核心
        'llm': 14,             # LLM 集成
        'tool': 13,            # 工具实现
        'memory': 12,          # 记忆系统
        'prompt': 11,          # Prompt 模板
        'embedding': 10,       # 向量嵌入
        'retriever': 10,       # 检索器
        'chain': 9,            # 链式调用
        'service': 8,          # 服务层
        'api': 7,              # API 层
        'config': 6,           # 配置
        'util': 5,             # 工具类
    },
    'database': {
        'storage': 15,         # 存储引擎
        'index': 14,           # 索引实现
        'query': 13,           # 查询处理
        'transaction': 12,     # 事务管理
        'executor': 11,        # 执行器
        'optimizer': 10,       # 优化器
        'parser': 9,           # 解析器
        'catalog': 8,          # 元数据
        'wal': 12,             # 日志
        'compaction': 11,      # 压缩
        'service': 7,          # 服务层
        'api': 6,              # API 层
        'config': 5,           # 配置
        'util': 4,             # 工具类
    },
    'fullstack-web': {
        'page': 14,            # 页面组件
        'route': 13,           # 路由
        'api': 12,             # API 端点
        'component': 11,       # 组件
        'layout': 10,          # 布局
        'middleware': 9,       # 中间件
        'service': 8,          # 服务层
        'store': 7,            # 状态管理
        'hook': 7,             # React Hooks
        'worker': 8,           # Web Worker
        'config': 6,           # 配置
        'util': 5,             # 工具类
    },
    'pipeline': {
        'pipeline': 15,        # 管道定义
        'worker': 14,          # Worker 实现
        'task': 13,            # 任务定义
        'queue': 12,           # 队列管理
        'scheduler': 11,       # 调度器
        'processor': 10,       # 处理器
        'handler': 9,          # 处理器
        'job': 8,              # 作业
        'service': 7,          # 服务层
        'api': 6,              # API 层
        'config': 5,           # 配置
        'util': 4,             # 工具类
    },
    'general': {
        'main': 15,            # 主入口
        'app': 14,             # 应用
        'service': 12,         # 服务层
        'manager': 11,         # 管理器
        'controller': 10,      # 控制器
        'handler': 9,          # 处理器
        'api': 8,              # API
        'model': 7,            # 数据模型
        'config': 6,           # 配置
        'util': 5,             # 工具类
    }
}

# 文件优先级权重（向后兼容）
PRIORITY_WEIGHTS = {
    'entry': 10,      # 入口点 (Main, Application, Bootstrap)
    'service': 9,     # 核心类 (Service, Manager, Engine, Core)
    'high-complexity': 7,  # 高复杂度
    'interface': 6,   # 接口定义 (Interface, API, Protocol)
    'config': 5,      # 配置类 (Config, Settings)
    'model': 4,       # 数据模型 (Model, Entity, DTO)
    'util': 3,        # 工具类 (Util, Helper, Utils)
}

# 入口点文件名模式
ENTRY_PATTERNS = ['Main', 'Application', 'Bootstrap', 'App', 'Server', 'Start', 'Runner']

# 核心类文件名模式
SERVICE_PATTERNS = ['Service', 'Manager', 'Engine', 'Core', 'Handler', 'Controller', 'Processor', 'Executor']

# 接口文件名模式
INTERFACE_PATTERNS = ['Interface', 'API', 'Protocol', 'Contract', 'Facade']

# 配置文件名模式
CONFIG_PATTERNS = ['Config', 'Settings', 'Configuration', 'Options', 'Properties']

# 主语言扩展名映射
LANGUAGE_EXTENSIONS = {
    'java': ['.java'],
    'python': ['.py'],
    'javascript': ['.js', '.jsx', '.ts', '.tsx'],
    'typescript': ['.ts', '.tsx'],
    'go': ['.go'],
    'rust': ['.rs'],
    'cpp': ['.cpp', '.cc', '.cxx', '.hpp', '.h'],
    'c': ['.c', '.h'],
    'csharp': ['.cs'],
    'kotlin': ['.kt', '.kts'],
    'scala': ['.scala', '.sc'],
    'ruby': ['.rb'],
    'php': ['.php'],
    'swift': ['.swift'],
}

# 所有源码文件扩展名（用于多语言项目）
ALL_SOURCE_EXTENSIONS = set()
for exts in LANGUAGE_EXTENSIONS.values():
    ALL_SOURCE_EXTENSIONS.update(exts)

def detect_language(project_path):
    """检测项目主语言（按文件数量统计）"""
    ext_counter = Counter()
    
    for root, dirs, files in os.walk(project_path):
        # 跳过常见非源码目录
        dirs[:] = [d for d in dirs if d not in ['.git', 'target', 'build', 'node_modules', 'vendor', '__pycache__', '.next', 'dist']]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext:
                ext_counter[ext] += 1
    
    # 统计每种语言的文件数量
    lang_counts = {}
    for lang, exts in LANGUAGE_EXTENSIONS.items():
        count = sum(ext_counter.get(ext, 0) for ext in exts)
        if count > 0:
            lang_counts[lang] = count
    
    # 返回文件数量最多的语言
    if lang_counts:
        primary_lang = max(lang_counts.items(), key=lambda x: x[1])
        return primary_lang[0], primary_lang[1]
    
    return 'unknown', 0

def is_entry_file(filename):
    """判断是否为入口点文件"""
    for pattern in ENTRY_PATTERNS:
        if pattern in filename:
            return True
    return False

def is_service_file(filename):
    """判断是否为核心类文件"""
    for pattern in SERVICE_PATTERNS:
        if pattern in filename:
            return True
    return False

def is_interface_file(filename):
    """判断是否为接口文件"""
    for pattern in INTERFACE_PATTERNS:
        if pattern in filename:
            return True
    return False

def is_config_file(filename):
    """判断是否为配置文件"""
    for pattern in CONFIG_PATTERNS:
        if pattern in filename:
            return True
    return False

def get_file_priority(filepath, filename, project_type='general'):
    """计算文件优先级（根据项目类型）"""
    priority = 0
    rel_path = filepath.lower()
    filename_lower = filename.lower()
    
    # 获取项目类型特定的优先级配置
    type_priorities = PROJECT_TYPE_PRIORITIES.get(project_type, PROJECT_TYPE_PRIORITIES['general'])
    
    # 检查完整路径（包括目录和文件名）
    for pattern, weight in type_priorities.items():
        if pattern in rel_path:
            priority += weight
            break  # 只匹配第一个最高优先级的模式
    
    # 通用模式检查（向后兼容）
    if is_entry_file(filename):
        priority += PRIORITY_WEIGHTS['entry']
    
    if is_service_file(filename):
        priority += PRIORITY_WEIGHTS['service']
    
    if is_interface_file(filename):
        priority += PRIORITY_WEIGHTS['interface']
    
    if is_config_file(filename):
        priority += PRIORITY_WEIGHTS['config']
    
    # 文件大小加分（较大文件可能更重要）
    try:
        size = os.path.getsize(filepath)
        if size > 10000:  # >10KB
            priority += 2
        elif size > 5000:  # >5KB
            priority += 1
    except:
        pass
    
    # 降低 UI/样式文件的优先级
    ui_patterns = ['component', 'ui', 'style', 'css', 'scss', 'asset', 'icon', 'image', 'img']
    for pattern in ui_patterns:
        if pattern in rel_path:
            priority -= 3
            break
    
    # 提高核心业务逻辑的优先级
    core_patterns = ['core', 'domain', 'business', 'logic', 'engine', 'service', 'manager']
    for pattern in core_patterns:
        if pattern in rel_path:
            priority += 5
            break
    
    # 🔽 测试文件惩罚：测试文件不应排在核心源码前面
    test_indicators = ['_test.', '_test_', 'test_', 'test.', 'tests/', '/test/', 
                       '_spec.', 'spec/', '.test.', '.spec.', '_testing.']
    for indicator in test_indicators:
        if indicator in rel_path:
            priority -= 15
            break
    
    # 🔽 基准测试/benchmark 文件惩罚（优先级低于核心源码）
    bench_indicators = ['benchmark', 'bench/', 'perf_test', 'load_test']
    for indicator in bench_indicators:
        if indicator in rel_path:
            priority -= 10
            break
    
    # 🔽 示例/文档文件惩罚
    example_indicators = ['example', 'sample', 'demo', 'tutorial']
    for indicator in example_indicators:
        if indicator in rel_path:
            priority -= 8
            break
    
    return priority

def get_git_modification_count(project_path, filepath):
    """获取 Git 修改频率（最近 100 commits）"""
    try:
        rel_path = os.path.relpath(filepath, project_path)
        result = subprocess.run(
            ['git', 'log', '--oneline', '--name-only', '-100'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            files = result.stdout.strip().split('\n')
            # 统计文件出现次数（排除 commit 消息行）
            file_counter = Counter(f for f in files if f and not f.startswith('['))
            return file_counter.get(rel_path, 0)
    except:
        pass
    
    return 0

def count_file_lines(filepath):
    """计算文件行数"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except:
        return 0

def scan_project_files(project_path, max_files=30, priority_filter=None, project_type='general'):
    """扫描项目文件，识别关键文件"""
    language, _ = detect_language(project_path)
    
    files_info = []
    
    for root, dirs, files in os.walk(project_path):
        # 跳过常见非源码目录
        dirs[:] = [d for d in dirs if d not in ['.git', 'target', 'build', 'node_modules', 'vendor', '__pycache__', '.idea', '.vscode']]
        
        for file in files:
            filepath = os.path.join(root, file)
            ext = os.path.splitext(file)[1]
            
            # 只处理源码文件（支持多语言项目）
            if ext not in ALL_SOURCE_EXTENSIONS:
                continue
            
            # 计算优先级（传入项目类型）
            priority = get_file_priority(filepath, file, project_type)
            
            # Git 修改频率加分
            git_count = get_git_modification_count(project_path, filepath)
            if git_count > 10:
                priority += PRIORITY_WEIGHTS['high-complexity'] + 2
            elif git_count > 5:
                priority += PRIORITY_WEIGHTS['high-complexity']
            
            # 行数
            lines = count_file_lines(filepath)
            
            # 提取模块名
            rel_path = os.path.relpath(filepath, project_path)
            parts = rel_path.split(os.sep)
            module = parts[0] if len(parts) > 1 else 'root'
            
            files_info.append({
                'file': file,
                'path': rel_path,
                'priority': priority,
                'lines': lines,
                'module': module,
                'git_count': git_count,
            })
    
    # 按优先级排序
    files_info.sort(key=lambda x: (-x['priority'], -x['lines']))
    
    # 限制文件数量
    if max_files:
        files_info = files_info[:max_files]
    
    return files_info, language

def generate_file_list_markdown(files_info, project_name, language):
    """生成 Markdown 文件列表"""
    lines = []
    lines.append(f"# {project_name} 文件粒度分析列表\n\n")
    lines.append(f"> **主语言**: {language}\n")
    lines.append(f"> **选中文件**: {len(files_info)} 个\n\n")
    lines.append("---\n\n")
    
    lines.append("## 关键文件清单\n\n")
    lines.append("| 序号 | 文件 | 路径 | 优先级 | 行数 | 模块 | Git频次 |\n")
    lines.append("|------|------|------|--------|------|------|----------|\n")
    
    for i, info in enumerate(files_info, 1):
        priority_emoji = '🔴' if info['priority'] >= 10 else '🟡' if info['priority'] >= 7 else '🟢'
        lines.append(f"| {i} | {info['file']} | `{info['path']}` | {priority_emoji} P{info['priority']} | {info['lines']} | {info['module']} | {info['git_count']} |\n")
    
    lines.append("\n---\n\n")
    
    # 模块统计
    lines.append("## 模块分布\n\n")
    module_counter = Counter(f['module'] for f in files_info)
    lines.append("| 模块 | 文件数 |\n")
    lines.append("|------|--------|\n")
    for module, count in module_counter.most_common():
        lines.append(f"| {module} | {count} |\n")
    
    lines.append("\n---\n\n")
    
    # 分析建议
    lines.append("## 分析建议\n\n")
    
    # 找出最高优先级文件
    top_files = [f for f in files_info if f['priority'] >= 10]
    if top_files:
        lines.append("### 🔴 高优先级文件（建议首先分析）\n\n")
        for f in top_files[:5]:
            lines.append(f"- `{f['file']}` - {f['lines']} 行\n")
    
    # 找出高频修改文件
    high_git = [f for f in files_info if f['git_count'] > 5]
    if high_git:
        lines.append("\n### 📊 高频修改文件（最近活跃）\n\n")
        for f in high_git[:5]:
            lines.append(f"- `{f['file']}` - {f['git_count']} commits\n")
    
    lines.append("\n---\n\n")
    lines.append("*生成时间: " + subprocess.run(['date'], capture_output=True, text=True).stdout.strip() + "*\n")
    
    return ''.join(lines)

def main():
    parser = argparse.ArgumentParser(description='自动识别关键文件，生成文件粒度分析列表')
    parser.add_argument('project_path', help='项目路径')
    parser.add_argument('--max-files', type=int, default=30, help='最大文件数量')
    parser.add_argument('--priority', default=None, help='优先级过滤 (entry,service,high-complexity)')
    parser.add_argument('--project-type', default='general', 
                        choices=['general', 'llm-agent', 'database', 'fullstack-web', 'pipeline'],
                        help='项目类型 (影响文件优先级排序)')
    parser.add_argument('-o', '--output', required=True, help='输出文件路径')
    
    args = parser.parse_args()
    
    project_path = Path(args.project_path).resolve()
    if not project_path.exists():
        print(f"❌ 项目路径不存在: {project_path}")
        sys.exit(1)
    
    project_name = project_path.name
    
    print(f"🔍 扫描项目: {project_name}")
    print(f"   路径: {project_path}")
    print(f"   项目类型: {args.project_type}")
    
    # 扫描文件（传入项目类型）
    files_info, language = scan_project_files(project_path, args.max_files, args.priority, args.project_type)
    
    print(f"✅ 识别关键文件: {len(files_info)} 个")
    print(f"   主语言: {language}")
    
    # 生成 Markdown
    markdown = generate_file_list_markdown(files_info, project_name, language)
    
    # 写入文件
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print(f"📝 输出文件: {output_path}")
    
    # 输出摘要
    print("\n📊 文件分布:")
    module_counter = Counter(f['module'] for f in files_info)
    for module, count in module_counter.most_common(5):
        print(f"   {module}: {count} 个文件")

if __name__ == '__main__':
    main()