#!/usr/bin/env python3
"""
智能源码分析脚本 - 自动检测项目类型并生成分析计划

功能：
1. 自动检测项目类型（LLM Agent / Database / Fullstack Web / Pipeline / General）
2. 根据项目类型推荐分析模板
3. 生成优化的文件分析列表
4. 输出完整的分析计划

用法：
    python3 smart-analyze.py /path/to/project
    python3 smart-analyze.py /path/to/project --output ~/.openclaw/learning/projects/xxx/
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# 导入其他脚本
import importlib.util
_script_dir = os.path.dirname(__file__)

def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_script_dir, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_dpt = _load_module('detect_project_type', 'detect-project-type.py')
detect_project_type = _dpt.detect_project_type
recommend_templates = _dpt.recommend_templates
PROJECT_TYPE_SIGNATURES = _dpt.PROJECT_TYPE_SIGNATURES

_gfl = _load_module('generate_file_list', 'generate-file-list.py')
scan_project_files = _gfl.scan_project_files
generate_file_list_markdown = _gfl.generate_file_list_markdown

def run_analysis_plan(project_path, project_type, templates, files_info, output_dir, model_name=None):
    """生成分析执行计划"""
    lines = []
    
    lines.append(f"# {project_path.name} 智能分析计划\n\n")
    lines.append(f"> **项目类型**: {project_type}\n")
    lines.append(f"> **推荐模板**: {len(templates['templates']) + len(templates['general'])} 个\n")
    lines.append(f"> **关键文件**: {len(files_info)} 个\n")
    if model_name:
        lines.append(f"> **分析模型**: `{model_name}`\n")
    lines.append("\n---\n\n")
    
    # Phase 1: 项目类型分析
    lines.append("## Phase 1: 项目级分析（必做）\n\n")
    lines.append(f"**检测到的项目类型**: {project_type}\n\n")
    
    if templates['overview']:
        lines.append(f"### 1.1 总览文档\n\n")
        lines.append(f"- [ ] 阅读 `{templates['overview']}`\n")
        lines.append(f"- [ ] 生成 `00-project-level/README.md`\n\n")
    
    lines.append(f"### 1.2 项目依赖分析 ⭐\n\n")
    lines.append(f"- [ ] 扫描依赖声明文件（package.json / requirements.txt / go.mod / Cargo.toml 等）\n")
    lines.append(f"- [ ] 阅读 `templates/general/PROJECT_DEPENDENCY_ANALYSIS.md`\n")
    lines.append(f"- [ ] 生成 `00-project-level/dependencies.md`\n")
    lines.append(f"- [ ] 筛选「值得关注的优秀库」清单\n\n")
    
    # Phase 2: 专项模板分析
    if templates['templates']:
        lines.append("## Phase 2: 专项模板分析\n\n")
        for i, template in enumerate(templates['templates'], 1):
            template_name = Path(template).stem
            lines.append(f"### 2.{i} {template_name}\n\n")
            lines.append(f"- [ ] 阅读 `{template}`\n")
            lines.append(f"- [ ] 生成 `{project_path.name}/{template_name}.md`\n\n")
    
    # Phase 3: 通用模板分析
    if templates['general']:
        lines.append("## Phase 3: 通用模板分析\n\n")
        for i, template in enumerate(templates['general'], 1):
            template_name = Path(template).stem
            lines.append(f"### 3.{i} {template_name}\n\n")
            lines.append(f"- [ ] 阅读 `{template}`\n")
            lines.append(f"- [ ] 生成 `{project_path.name}/{template_name}.md`\n\n")
    
    # Phase 4: 文件级分析
    lines.append("## Phase 4: 文件级分析\n\n")
    lines.append("### 4.1 高优先级文件（前 10 个）\n\n")
    for i, file_info in enumerate(files_info[:10], 1):
        lines.append(f"- [ ] 分析 `{file_info['file']}` ({file_info['lines']} 行)\n")
    
    if len(files_info) > 10:
        lines.append(f"\n### 4.2 其他关键文件（{len(files_info) - 10} 个）\n\n")
        for i, file_info in enumerate(files_info[10:], 1):
            lines.append(f"- [ ] 分析 `{file_info['file']}` ({file_info['lines']} 行)\n")
    
    lines.append("\n---\n\n")
    
    # 统计信息
    total_templates = len(templates['templates']) + len(templates['general'])
    total_files = len(files_info)
    total_docs = 1 + total_templates + total_files  # overview + templates + files    
    lines.append("## 📊 分析统计\n\n")
    lines.append(f"- **预计生成文档数**: {total_docs} 个（含 dependencies.md）\n")
    lines.append(f"  - 总览文档: 1 个\n")
    lines.append(f"  - 专项模板: {len(templates['templates'])} 个\n")
    lines.append(f"  - 通用模板: {len(templates['general'])} 个\n")
    lines.append(f"  - 文件分析: {total_files} 个\n\n")
    
    lines.append("---\n\n")
    timestamp = subprocess.run(['date'], capture_output=True, text=True).stdout.strip()
    lines.append(f"*生成时间: {timestamp}*\n")
    if model_name:
        lines.append(f"*分析模型: `{model_name}`*\n")
    
    return ''.join(lines)

def main():
    parser = argparse.ArgumentParser(description='智能源码分析 - 自动检测项目类型并生成分析计划')
    parser.add_argument('project_path', help='项目路径')
    parser.add_argument('--output', '-o', help='输出目录（默认: ~/.openclaw/learning/projects/<project-name>/）')
    parser.add_argument('--max-files', type=int, default=30, help='最大文件数量（默认: 30）')
    parser.add_argument('--model', '-m', help='当前分析使用的模型名（如 zai/glm-5.2）')
    
    args = parser.parse_args()
    
    project_path = Path(args.project_path).resolve()
    if not project_path.exists():
        print(f"❌ 项目路径不存在: {project_path}")
        sys.exit(1)
    
    project_name = project_path.name
    
    # 设置输出目录
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = Path.home() / '.openclaw' / 'learning' / 'projects' / project_name
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🚀 智能源码分析: {project_name}")
    print(f"   项目路径: {project_path}")
    print(f"   输出目录: {output_dir}")
    print()
    
    # Step 1: 检测项目类型
    print("=" * 60)
    print("Step 1: 检测项目类型")
    print("=" * 60)
    detection_result = detect_project_type(str(project_path))
    project_type = detection_result['primary']
    print(f"✅ 项目类型: {project_type}")
    print()
    
    # Step 2: 推荐模板
    print("=" * 60)
    print("Step 2: 推荐分析模板")
    print("=" * 60)
    templates = recommend_templates(project_type)
    total_templates = len(templates['templates']) + len(templates['general'])
    print(f"✅ 推荐模板: {total_templates} 个")
    if templates['overview']:
        print(f"   - 总览: {templates['overview']}")
    print(f"   - 专项: {len(templates['templates'])} 个")
    print(f"   - 通用: {len(templates['general'])} 个")
    print()
    
    # Step 3: 扫描文件
    print("=" * 60)
    print("Step 3: 扫描关键文件")
    print("=" * 60)
    files_info, language = scan_project_files(str(project_path), args.max_files, None, project_type)
    print(f"✅ 识别文件: {len(files_info)} 个")
    print(f"   主语言: {language}")
    print()
    
    # Step 4: 生成文件列表
    print("=" * 60)
    print("Step 4: 生成文件列表")
    print("=" * 60)
    file_list_path = output_dir / 'FILE_LIST.md'
    file_list_md = generate_file_list_markdown(files_info, project_name, language)
    with open(file_list_path, 'w', encoding='utf-8') as f:
        f.write(file_list_md)
    print(f"✅ 文件列表: {file_list_path}")
    print()
    
    # Step 5: 生成分析计划
    print("=" * 60)
    print("Step 5: 生成分析计划")
    print("=" * 60)
    analysis_plan_path = output_dir / 'ANALYSIS_PLAN.md'
    primary_name = PROJECT_TYPE_SIGNATURES.get(project_type, {}).get('name', project_type)
    model_name = args.model or os.environ.get('OPENCLAW_MODEL', '') or 'unknown'
    analysis_plan_md = run_analysis_plan(
        project_path, 
        primary_name,
        templates, 
        files_info, 
        output_dir,
        model_name=model_name
    )
    with open(analysis_plan_path, 'w', encoding='utf-8') as f:
        f.write(analysis_plan_md)
    print(f"✅ 分析计划: {analysis_plan_path}")
    print()
    
    # Step 6: 生成项目元数据
    print("=" * 60)
    print("Step 6: 生成项目元数据")
    print("=" * 60)
    meta_path = output_dir / 'project-meta.json'
    meta = {
        'project_name': project_name,
        'project_path': str(project_path),
        'project_type': primary_name,
        'project_type_id': project_type,
        'language': language,
        'model': model_name,
        'templates_count': total_templates,
        'files_count': len(files_info),
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'tool': 'source-analyzer',
    }
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"✅ 项目元数据: {meta_path}")
    print()
    
    # 输出总结
    print("=" * 60)
    print("✅ 智能分析准备完成")
    print("=" * 60)
    print(f"📁 输出目录: {output_dir}")
    print(f"📄 文件列表: {file_list_path}")
    print(f"📋 分析计划: {analysis_plan_path}")
    print()
    print("📊 统计信息:")
    print(f"   - 项目类型: {primary_name}")
    print(f"   - 分析模型: {model_name}")
    print(f"   - 推荐模板: {total_templates} 个")
    print(f"   - 关键文件: {len(files_info)} 个")
    print(f"   - 预计文档: {1 + total_templates + len(files_info)} 个")
    print()
    print("💡 下一步:")
    print(f"   1. 查看分析计划: cat {analysis_plan_path}")
    print(f"   2. 按照计划逐步分析")
    print(f"   3. 使用对应的模板文档指导分析")
    print()

if __name__ == '__main__':
    main()
