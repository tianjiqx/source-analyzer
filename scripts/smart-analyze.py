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
    python3 smart-analyze.py /path/to/project --output $OUTPUT_BASE/xxx/
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# 导入路径工具（支持环境变量 SOURCE_ANALYZER_OUTPUT_BASE）
sys.path.insert(0, str(Path(__file__).parent))
from path_utils import get_output_dir

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
recommend_templates_multi = _dpt.recommend_templates_multi
PROJECT_TYPE_SIGNATURES = _dpt.PROJECT_TYPE_SIGNATURES

_gfl = _load_module('generate_file_list', 'generate-file-list.py')
scan_project_files = _gfl.scan_project_files
generate_file_list_markdown = _gfl.generate_file_list_markdown

_ct = _load_module('commit_tracker', 'commit-tracker.py')
get_commit_info = _ct.get_commit_info

def run_analysis_plan(project_path, detection_result, multi_templates, files_info, output_dir, model_name=None):
    """生成分析执行计划（支持多类型）"""
    lines = []
    
    active_types = multi_templates['types']
    primary_name = active_types[0][1]
    primary_type = active_types[0][0]
    is_multi = len(active_types) > 1
    
    lines.append(f"# {project_path.name} 智能分析计划\n\n")
    lines.append(f"> **项目类型**: {primary_name}")
    if is_multi:
        secondary_names = ', '.join([f"{pname}" for _, pname, _ in active_types[1:]])
        lines.append(f" + {secondary_names} (多类型)")
    lines.append("\n")
    total_overviews = len(multi_templates['overviews'])
    total_specialized = len(multi_templates['templates'])
    total_general = len(multi_templates['general'])
    lines.append(f"> **推荐模板**: {total_specialized + total_general} 个（{total_overviews} 总览 + {total_specialized} 专项 + {total_general} 通用）\n")
    lines.append(f"> **关键文件**: {len(files_info)} 个\n")
    if model_name:
        lines.append(f"> **分析模型**: `{model_name}`\n")
    lines.append("\n---\n\n")
    
    # 多类型提示
    if is_multi:
        lines.append("## ⚠️ 多类型命中\n\n")
        lines.append("该项目同时具备多种特征，将合并多组专项模板进行综合分析。\n\n")
        lines.append("| 类型 | 得分 | 角色 |\n")
        lines.append("|------|------|------|\n")
        for i, (ptype, pname, score) in enumerate(active_types):
            role = "主类型" if i == 0 else "次要类型"
            lines.append(f"| {pname} (`{ptype}`) | {score:.1f} | {role} |\n")
        lines.append("\n---\n\n")
    
    # Phase 1: 项目级分析
    lines.append("## Phase 1: 项目级分析（必做）\n\n")
    lines.append(f"**检测到的项目类型**: {primary_name}")
    if is_multi:
        lines.append(f" + {len(active_types) - 1} 个次要类型")
    lines.append("\n\n")
    
    if multi_templates['overviews']:
        lines.append(f"### 1.1 总览文档（{len(multi_templates['overviews'])} 个）\n\n")
        for ov in multi_templates['overviews']:
            lines.append(f"- [ ] 阅读 `{ov}`\n")
        lines.append("\n")
    
    lines.append(f"### 1.2 项目依赖分析 ⭐\n\n")
    lines.append(f"- [ ] 扫描依赖声明文件（package.json / requirements.txt / go.mod / Cargo.toml 等）\n")
    lines.append(f"- [ ] 阅读 `templates/general/PROJECT_DEPENDENCY_ANALYSIS.md`\n")
    lines.append(f"- [ ] 生成 `00-project-level/dependencies.md`\n")
    lines.append(f"- [ ] 筛选「值得关注的优秀库」清单\n\n")
    
    # Phase 2: 专项模板分析（按类型分组）
    if multi_templates['templates']:
        lines.append("## Phase 2: 专项模板分析\n\n")
        
        if is_multi:
            # 多类型：按类型分组输出
            lines.append(f"> 共 {len(active_types)} 种类型，{len(multi_templates['templates'])} 个专项模板（合并去重后）\n\n")
            
            # 按类型分组
            type_counter = 0
            global_idx = 0
            for ptype, pname, score in active_types:
                rec = recommend_templates(ptype)
                type_templates = rec.get('templates', [])
                if not type_templates:
                    continue
                
                type_counter += 1
                role = "主类型" if type_counter == 1 else f"次要类型 {type_counter - 1}"
                lines.append(f"### 2.{type_counter} {pname}（{role}，{len(type_templates)} 个模板）\n\n")
                lines.append(f"> 输出到 `30-specialized/{ptype}/`\n\n")
                
                for template in type_templates:
                    global_idx += 1
                    template_name = Path(template).stem
                    lines.append(f"- [ ] 阅读 `{template}`\n")
                    lines.append(f"- [ ] 生成 `30-specialized/{ptype}/{template_name}.md`\n\n")
        else:
            # 单类型
            for i, template in enumerate(multi_templates['templates'], 1):
                template_name = Path(template).stem
                lines.append(f"### 2.{i} {template_name}\n\n")
                lines.append(f"- [ ] 阅读 `{template}`\n")
                lines.append(f"- [ ] 生成 `{project_path.name}/{template_name}.md`\n\n")
    
    # Phase 3: 通用模板分析
    if multi_templates['general']:
        lines.append("## Phase 3: 通用模板分析\n\n")
        for i, template in enumerate(multi_templates['general'], 1):
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
    total_templates = total_specialized + total_general
    total_files = len(files_info)
    total_docs = total_overviews + total_templates + total_files
    lines.append("## 📊 分析统计\n\n")
    lines.append(f"- **预计生成文档数**: {total_docs} 个（含 dependencies.md）\n")
    lines.append(f"  - 总览文档: {total_overviews} 个\n")
    lines.append(f"  - 专项模板: {total_specialized} 个\n")
    if is_multi:
        lines.append(f"  - （来源: {len(active_types)} 种类型合并）\n")
    lines.append(f"  - 通用模板: {total_general} 个\n")
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
    parser.add_argument('--output', '-o', help='输出目录（默认: $OUTPUT_BASE/<project-name>/）')
    parser.add_argument('--max-files', type=int, default=30, help='最大文件数量（默认: 30）')
    parser.add_argument('--model', '-m', help='当前分析使用的模型名（如 zai/glm-5.2）')
    
    args = parser.parse_args()
    
    project_path = Path(args.project_path).resolve()
    if not project_path.exists():
        print(f"❌ 项目路径不存在: {project_path}")
        sys.exit(1)
    
    project_name = project_path.name
    
    # 设置输出目录（支持环境变量 SOURCE_ANALYZER_OUTPUT_BASE）
    output_dir = get_output_dir(project_name, args.output)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🚀 智能源码分析: {project_name}")
    print(f"   项目路径: {project_path}")
    print(f"   输出目录: {output_dir}")
    print()
    
    # Step 0: 获取 Git commit 信息
    print("=" * 60)
    print("Step 0: 获取 Git commit 信息")
    print("=" * 60)
    commit_info = get_commit_info(str(project_path))
    if commit_info:
        print(f"✅ Commit: {commit_info['commit_hash']}")
        print(f"   Short:  {commit_info['commit_short']}")
        print(f"   日期:   {commit_info['commit_date']}")
        print(f"   消息:   {commit_info['commit_subject']}")
        print(f"   分支:   {commit_info['branch']}")
        if commit_info.get('tag'):
            print(f"   Tag:    {commit_info['tag']}")
    else:
        print(f"⚠️  非 Git 仓库或无法获取 commit 信息（继续分析）")
    print()
    
    # Step 1: 检测项目类型
    print("=" * 60)
    print("Step 1: 检测项目类型")
    print("=" * 60)
    detection_result = detect_project_type(str(project_path))
    project_type = detection_result['primary']
    print(f"✅ 项目类型: {project_type}")
    print()
    
    # Step 2: 推荐模板（多类型合并）
    print("=" * 60)
    print("Step 2: 推荐分析模板（多类型合并）")
    print("=" * 60)
    multi_templates = recommend_templates_multi(detection_result)
    total_templates = len(multi_templates['templates']) + len(multi_templates['general'])
    print(f"✅ 推荐模板: {total_templates} 个")
    for ov in multi_templates['overviews']:
        print(f"   - 总览: {ov}")
    print(f"   - 专项: {len(multi_templates['templates'])} 个")
    print(f"   - 通用: {len(multi_templates['general'])} 个")
    if len(multi_templates['types']) > 1:
        print(f"   ⚠️ 多类型命中: {' + '.join([pname for _, pname, _ in multi_templates['types']])}")
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
    
    # Step 5: 生成分析计划（多类型）
    print("=" * 60)
    print("Step 5: 生成分析计划")
    print("=" * 60)
    analysis_plan_path = output_dir / 'ANALYSIS_PLAN.md'
    primary_name = PROJECT_TYPE_SIGNATURES.get(project_type, {}).get('name', project_type)
    model_name = args.model or os.environ.get('OPENCLAW_MODEL', '') or 'unknown'
    analysis_plan_md = run_analysis_plan(
        project_path, 
        detection_result,
        multi_templates, 
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
        'project_types_all': [{'type': ptype, 'name': pname, 'score': score, 'role': 'primary' if i == 0 else 'secondary'} for i, (ptype, pname, score) in enumerate(multi_templates['types'])],
        'language': language,
        'model': model_name,
        'templates_count': total_templates,
        'templates_overviews': len(multi_templates['overviews']),
        'templates_specialized': len(multi_templates['templates']),
        'templates_general': len(multi_templates['general']),
        'multi_type': len(multi_templates['types']) > 1,
        'files_count': len(files_info),
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'tool': 'source-analyzer',
        # Git commit 信息（支持增量分析）
        'commit_hash': commit_info.get('commit_hash', '') if commit_info else '',
        'commit_short': commit_info.get('commit_short', '') if commit_info else '',
        'commit_date': commit_info.get('commit_date', '') if commit_info else '',
        'commit_subject': commit_info.get('commit_subject', '') if commit_info else '',
        'branch': commit_info.get('branch', '') if commit_info else '',
        'tag': commit_info.get('tag') if commit_info else None,
        'remote_url': commit_info.get('remote_url', '') if commit_info else '',
        'total_files_in_repo': commit_info.get('total_files', 0) if commit_info else 0,
        'last_analyzed_at': datetime.now().isoformat(timespec='seconds'),
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
    if len(multi_templates['types']) > 1:
        print(f"   - 多类型: {' + '.join([pname for _, pname, _ in multi_templates['types']])}")
    print(f"   - 分析模型: {model_name}")
    print(f"   - 推荐模板: {total_templates} 个")
    if len(multi_templates['types']) > 1:
        print(f"   - 多类型合并: {len(multi_templates['overviews'])} 总览 + {len(multi_templates['templates'])} 专项 + {len(multi_templates['general'])} 通用")
    print(f"   - 关键文件: {len(files_info)} 个")
    print(f"   - 预计文档: {len(multi_templates['overviews']) + total_templates + len(files_info)} 个")
    if commit_info:
        print(f"   - Git Commit: {commit_info['commit_short']} ({commit_info['commit_date']})")
    print()
    print("💡 下一步:")
    print(f"   1. 查看分析计划: cat {analysis_plan_path}")
    print(f"   2. 按照计划逐步分析")
    print(f"   3. 使用对应的模板文档指导分析")
    if commit_info:
        print(f"   4. 增量分析: python3 $SKILL_DIR/scripts/commit-tracker.py status {project_path} --output-dir {output_dir}")
    print()

if __name__ == '__main__':
    main()
