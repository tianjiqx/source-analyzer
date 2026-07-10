#!/usr/bin/env python3
"""
生成模块清单 - 递归识别项目中的所有模块并评估规模

用法:
    python3 generate-module-manifest.py /path/to/project -o output-dir/module-manifest.json
    python3 generate-module-manifest.py /path/to/project --expand-threshold 30 --max-recursion-depth 3

特性:
    - 递归展开大型目录（不止一层）
    - 精确统计所有源文件（含子目录）
    - 模块重要性评估（文件数 + 行数 + 是否有入口文件）
    - 分析策略自适应（不再一刀切跳过小型模块）
"""

import os
import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple

# 支持的源代码文件扩展名
SOURCE_EXTENSIONS = {
    '.go', '.py', '.java', '.ts', '.tsx', '.js', '.jsx',
    '.rs', '.c', '.cpp', '.h', '.hpp', '.cs', '.vb',
    '.rb', '.php', '.swift', '.kt', '.scala', '.dart'
}

# 排除的目录（完全不统计）
EXCLUDE_DIRS = {
    'node_modules', 'vendor', '.git', '__pycache__', 'venv', '.venv',
    'dist', 'build', 'target', 'bin', 'obj', '.idea', '.vscode',
    'fixtures', 'mocks', 'stubs', 'testdata', 'examples',
    'third_party', 'thirdparty', '3rdparty',
}

# 测试目录（从模块扫描中排除，但记录存在）
TEST_DIRS = {
    'test', 'tests', 'spec', 'specs', '__tests__', 'e2e', 'tst'
}

# 入口文件特征（用于判断模块重要性）
ENTRY_FILE_PATTERNS = {
    'main.go', 'index.ts', 'index.js', 'index.py', '__init__.py',
    'main.py', 'app.py', 'server.py', 'main.java', 'Main.java',
    'Program.cs', 'Startup.cs', 'mod.rs', 'lib.rs', 'main.rs',
}


@dataclass
class Module:
    name: str
    path: str
    files: int               # 直接子文件数（不含子目录）
    total_files: int          # 含子目录的总文件数
    lines: int                # 直接子文件行数
    total_lines: int          # 含子目录的总行数
    size_category: str        # small/medium/large
    submodules: List[str]
    analysis_strategy: str    # layer1_plus_key_files / full_three_layers / full_with_submodule_recursion
    has_entry_file: bool      # 是否包含入口文件
    importance: str           # high/medium/low
    
    def to_dict(self):
        return asdict(self)


def count_files_recursive(directory: Path) -> Tuple[int, int, int, int]:
    """递归统计目录中的所有源文件
    
    Returns:
        (direct_files, direct_lines, total_files, total_lines)
        - direct: 只含直接子文件
        - total: 含所有子目录
    """
    direct_files = 0
    direct_lines = 0
    total_files = 0
    total_lines = 0
    
    for root, dirs, files in os.walk(directory):
        # 排除目录
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and d not in TEST_DIRS]
        
        # 判断是否为直接子文件
        is_direct = (Path(root) == directory)
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in SOURCE_EXTENSIONS:
                continue
            
            file_path = Path(root) / file
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    line_count = sum(1 for _ in f)
            except Exception:
                line_count = 0
            
            total_files += 1
            total_lines += line_count
            
            if is_direct:
                direct_files += 1
                direct_lines += line_count
    
    return direct_files, direct_lines, total_files, total_lines


def detect_submodules(directory: Path) -> List[str]:
    """检测包含源文件的子目录"""
    submodules = []
    
    for item in sorted(directory.iterdir()):
        if not item.is_dir():
            continue
        if item.name in EXCLUDE_DIRS or item.name in TEST_DIRS or item.name.startswith('.'):
            continue
        
        # 检查是否有源文件（递归检查）
        _, _, total_files, _ = count_files_recursive(item)
        if total_files > 0:
            submodules.append(item.name)
    
    return submodules


def has_entry_file(directory: Path) -> bool:
    """检查目录是否包含入口文件"""
    for item in directory.iterdir():
        if item.is_file() and item.name in ENTRY_FILE_PATTERNS:
            return True
    return False


def assess_importance(files: int, lines: int, has_entry: bool, size_category: str) -> str:
    """评估模块重要性
    
    不只看规模，还看：
    - 是否有入口文件（被其他模块依赖的可能性高）
    - 行数密度（少量文件但大量代码 = 核心逻辑）
    """
    if has_entry:
        return 'high'
    
    # 小型但代码密集的模块（如 encoding: 19 文件但 3K+ 行）
    if size_category == 'small' and lines > 2000:
        return 'high'
    
    if size_category == 'large' or lines > 10000:
        return 'high'
    elif size_category == 'medium' or lines > 3000:
        return 'medium'
    else:
        return 'low'


def determine_analysis_strategy(files: int, size_category: str, importance: str) -> str:
    """根据模块规模和重要性确定分析策略
    
    策略矩阵:
    - 大型模块: 始终 full_with_submodule_recursion
    - 中型模块: 始终 full_three_layers
    - 小型模块: 
      - importance=high → layer1_plus_key_files（Layer 1 + 3-5 关键文件深度分析）
      - importance=medium/low → layer1_only
    """
    if size_category == 'large':
        return 'full_with_submodule_recursion'
    elif size_category == 'medium':
        return 'full_three_layers'
    else:  # small
        if importance == 'high':
            return 'layer1_plus_key_files'
        return 'layer1_only'


def classify_size(total_files: int) -> str:
    """根据总文件数分类规模"""
    if total_files < 20:
        return 'small'
    elif total_files < 100:
        return 'medium'
    else:
        return 'large'


def analyze_directory_recursive(
    directory: Path,
    project_path: Path,
    expand_threshold: int,
    current_depth: int = 0,
    max_recursion_depth: int = 3,
    parent_name: str = "",
) -> List[Module]:
    """递归分析目录，展开大型模块
    
    当目录的文件数超过 expand_threshold 且未达到 max_recursion_depth 时，
    继续向下展开子目录为独立模块。
    """
    modules: List[Module] = []
    
    # 统计当前目录
    direct_files, direct_lines, total_files, total_lines = count_files_recursive(directory)
    
    if total_files == 0:
        return modules
    
    # 检测子目录
    sub_dirs = detect_submodules(directory)
    
    # 构建模块全名
    dir_name = directory.name
    if parent_name:
        full_name = f"{parent_name}/{dir_name}"
    else:
        full_name = dir_name
    
    # 判断是否需要继续展开
    should_expand = (
        total_files > expand_threshold
        and len(sub_dirs) > 1
        and current_depth < max_recursion_depth
    )
    
    if should_expand:
        # 递归展开子目录
        for subdir_name in sub_dirs:
            subdir_path = directory / subdir_name
            child_name = full_name
            # 对于顶层目录（parent_name 为空），保留顶层名称作为前缀
            if not parent_name:
                child_name = dir_name
            
            child_modules = analyze_directory_recursive(
                subdir_path,
                project_path,
                expand_threshold,
                current_depth + 1,
                max_recursion_depth,
                child_name,
            )
            modules.extend(child_modules)
    else:
        # 不展开，创建独立模块条目
        size_category = classify_size(total_files)
        has_entry = has_entry_file(directory)
        importance = assess_importance(total_files, total_lines, has_entry, size_category)
        strategy = determine_analysis_strategy(total_files, size_category, importance)
        
        module = Module(
            name=full_name,
            path=str(directory.relative_to(project_path)),
            files=direct_files,
            total_files=total_files,
            lines=direct_lines,
            total_lines=total_lines,
            size_category=size_category,
            submodules=sub_dirs,
            analysis_strategy=strategy,
            has_entry_file=has_entry,
            importance=importance,
        )
        modules.append(module)
    
    return modules


def analyze_project(
    project_path: Path,
    expand_threshold: int = 30,
    max_recursion_depth: int = 3,
) -> Dict:
    """分析项目，递归识别所有模块
    
    Args:
        project_path: 项目路径
        expand_threshold: 超过此文件数的目录将被展开（递归）
        max_recursion_depth: 最大递归深度
    """
    all_modules: List[Module] = []
    
    # 扫描顶层目录
    for item in sorted(project_path.iterdir()):
        if not item.is_dir():
            continue
        if item.name in EXCLUDE_DIRS or item.name in TEST_DIRS or item.name.startswith('.'):
            continue
        
        # 递归分析
        module_list = analyze_directory_recursive(
            item,
            project_path,
            expand_threshold,
            current_depth=0,
            max_recursion_depth=max_recursion_depth,
            parent_name="",
        )
        all_modules.extend(module_list)
    
    # 按总行数排序（比文件数更能反映模块重要性）
    all_modules.sort(key=lambda m: m.total_lines, reverse=True)
    
    # 统计
    total_files = sum(m.total_files for m in all_modules)
    total_lines = sum(m.total_lines for m in all_modules)
    
    # 按重要性分类统计
    high_count = sum(1 for m in all_modules if m.importance == 'high')
    medium_count = sum(1 for m in all_modules if m.importance == 'medium')
    low_count = sum(1 for m in all_modules if m.importance == 'low')
    
    return {
        'project': project_path.name,
        'total_files': total_files,
        'total_lines': total_lines,
        'module_count': len(all_modules),
        'importance_distribution': {
            'high': high_count,
            'medium': medium_count,
            'low': low_count,
        },
        'modules': [m.to_dict() for m in all_modules],
    }


def main():
    parser = argparse.ArgumentParser(
        description='生成模块清单 - 递归识别项目中的所有模块并评估规模',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基础用法
  python3 generate-module-manifest.py /path/to/project

  # 自定义展开阈值和递归深度
  python3 generate-module-manifest.py /path/to/project --expand-threshold 20 --max-recursion-depth 4

  # 输出到文件
  python3 generate-module-manifest.py /path/to/project -o manifest.json
        """,
    )
    parser.add_argument('project_path', type=Path, help='项目路径')
    parser.add_argument('-o', '--output', type=Path, help='输出 JSON 文件路径')
    parser.add_argument(
        '--expand-threshold', type=int, default=30,
        help='超过此文件数的目录将被递归展开（默认: 30）',
    )
    parser.add_argument(
        '--max-recursion-depth', type=int, default=3,
        help='最大递归展开深度（默认: 3）',
    )
    
    args = parser.parse_args()
    
    if not args.project_path.exists():
        print(f"错误: 项目路径不存在: {args.project_path}", file=sys.stderr)
        sys.exit(1)
    
    if not args.project_path.is_dir():
        print(f"错误: 路径不是目录: {args.project_path}", file=sys.stderr)
        sys.exit(1)
    
    # 分析项目
    manifest = analyze_project(
        args.project_path,
        expand_threshold=args.expand_threshold,
        max_recursion_depth=args.max_recursion_depth,
    )
    
    # 输出 JSON
    output_json = json.dumps(manifest, indent=2, ensure_ascii=False)
    
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output_json)
        print(f"✅ 模块清单已生成: {args.output}")
    else:
        print(output_json)
    
    # 打印摘要
    print(f"\n📊 项目摘要:")
    print(f"   项目: {manifest['project']}")
    print(f"   总文件数: {manifest['total_files']}")
    print(f"   总行数: {manifest['total_lines']:,}")
    print(f"   模块数: {manifest['module_count']}")
    
    dist = manifest['importance_distribution']
    print(f"   重要性分布: 🔴 high={dist['high']}, 🟡 medium={dist['medium']}, 🟢 low={dist['low']}")
    
    print(f"\n📦 模块列表 (Top 15):")
    print(f"   {'模块':<30} {'文件':>6} {'行数':>8} {'规模':<8} {'重要性':<8} {'策略'}")
    print(f"   {'-'*30} {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*30}")
    for m in manifest['modules'][:15]:
        print(
            f"   {m['name']:<30} {m['total_files']:>6} {m['total_lines']:>8,} "
            f"{m['size_category']:<8} {m['importance']:<8} {m['analysis_strategy']}"
        )


if __name__ == '__main__':
    main()
