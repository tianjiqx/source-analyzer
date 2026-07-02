#!/usr/bin/env python3
"""
自动检测项目类型，推荐分析模板

支持的项目类型:
- LLM Agent: AI Agent 项目（LangChain/AutoGen/MemGPT 等）
- Database: 数据库/大数据系统（MySQL/ClickHouse/TiDB 等）
- Fullstack Web: 全栈 Web 应用（Next.js/Nuxt/Remix 等）
- Pipeline: 数据处理管道/工作流引擎
- General: 通用项目

用法:
    python3 detect-project-type.py /path/to/project
    python3 detect-project-type.py /path/to/project --recommend-templates
"""

import os
import sys
import argparse
import json
from pathlib import Path
from collections import Counter

# 项目类型特征定义
PROJECT_TYPE_SIGNATURES = {
    'llm-agent': {
        'name': 'LLM Agent',
        'keywords': [
            # 高特异性关键词（LLM Agent 独有）
            'llm agent', 'ai agent', 'autonomous agent', 'multi-agent',
            'openai api', 'anthropic api', 'claude api', 'gpt-4', 'gpt-3.5',
            'chatcompletion', 'chat completion', 'function calling', 'tool calling',
            'langchain', 'llamaindex', 'autogen', 'crewai', 'mem0', 'memgpt',
            'vector store', 'embedding model', 'retriever', 'rag pipeline',
            'prompt template', 'prompt engineering', 'chain of thought', 'cot',
            'agent memory', 'conversation memory', 'long-term memory',
            'tool use', 'function call', 'action space', 'observation',
            # 中特异性关键词（需要组合判断）
            'openai', 'anthropic', 'claude', 'gemini', 'llama',
            'tokenizer', 'token count', 'context window', 'max tokens',
            'temperature', 'top_p', 'top_k', 'frequency penalty',
            'system prompt', 'user message', 'assistant message',
            'conversation history', 'chat history', 'message history',
        ],
        'file_patterns': [
            'agent', 'llm', 'chat', 'prompt', 'tool', 'embedding',
            'retriever', 'chain', 'completion', 'openai_client', 'anthropic_client',
        ],
        'dir_patterns': [
            'agents', 'tools', 'prompts', 'memory', 'llm', 'chains',
            'retrievers', 'embeddings', 'vector_stores', 'chat',
        ],
        'config_patterns': [
            'openai', 'anthropic', 'llm_config', 'model_config', 'api_key'
        ],
        'weight': 1.2,  # 提高权重
    },
    'database': {
        'name': '数据库/大数据系统',
        'keywords': [
            # 高特异性关键词（数据库系统独有）
            'mvcc', 'btree', 'b+tree', 'lsm-tree', 'lsm tree', 'wal', 'redo log',
            'compaction', 'memtable', 'sst', 'sstable', 'hbase', 'rocksdb', 'leveldb',
            'query optimizer', 'query planner', 'execution engine', 'storage engine',
            'transaction isolation', 'acid', 'two-phase commit', '2pc', 'raft consensus',
            'paxos', 'distributed transaction', 'sharding', 'partition pruning',
            'column family', 'column store', 'row store', 'htap', 'olap', 'oltp',
            # 中特异性关键词（需要组合判断）
            'sql parser', 'sql executor', 'index scan', 'hash join', 'sort merge',
            'buffer pool', 'page cache', 'disk manager', 'log manager',
        ],
        'file_patterns': [
            'storage_engine', 'index_impl', 'query_executor', 'transaction_manager',
            'mvcc', 'btree', 'lsm', 'wal', 'compaction', 'memtable', 'sst',
        ],
        'dir_patterns': [
            'storage_engine', 'query_engine', 'transaction', 'executor',
            'optimizer', 'catalog', 'sql_parser', 'index_impl',
        ],
        'config_patterns': [
            'database_engine', 'storage_config', 'buffer_pool', 'cache_config'
        ],
        'weight': 1.5,  # 提高权重，因为高特异性关键词更可靠
    },
    'fullstack-web': {
        'name': '全栈 Web 应用',
        'keywords': [
            'next', 'nuxt', 'remix', 'svelte', 'react', 'vue', 'angular',
            'api', 'route', 'component', 'page', 'layout', 'middleware',
            'websocket', 'sse', 'server', 'client', 'frontend', 'backend'
        ],
        'file_patterns': [
            'page.tsx', 'page.jsx', 'layout.tsx', 'route.ts', 'api.ts',
            'component', 'middleware', 'server', 'client'
        ],
        'dir_patterns': [
            'app', 'pages', 'components', 'api', 'routes', 'layouts',
            'middleware', 'public', 'assets', 'styles'
        ],
        'config_patterns': [
            'next.config', 'nuxt.config', 'vite.config', 'webpack.config',
            'tailwind.config', 'postcss.config'
        ],
        'weight': 0.8
    },
    'pipeline': {
        'name': 'Pipeline/工作流',
        'keywords': [
            'pipeline', 'workflow', 'worker', 'queue', 'task', 'job',
            'schedule', 'cron', 'batch', 'stream', 'process', 'etl',
            'dag', 'step', 'stage', 'checkpoint', 'resume'
        ],
        'file_patterns': [
            'pipeline', 'worker', 'queue', 'task', 'job', 'scheduler',
            'processor', 'handler'
        ],
        'dir_patterns': [
            'pipelines', 'workers', 'tasks', 'jobs', 'schedulers',
            'processors', 'handlers', 'queues'
        ],
        'config_patterns': [
            'pipeline', 'worker', 'queue', 'task', 'schedule'
        ],
        'weight': 0.7
    }
}

# 模板推荐映射
TEMPLATE_RECOMMENDATIONS = {
    'llm-agent': {
        'overview': 'templates/llm-agent/LLM_AGENT_ANALYSIS_OVERVIEW.md',
        'templates': [
            'templates/llm-agent/LLM_AGENT_01_ARCHITECTURE.md',
            'templates/llm-agent/LLM_AGENT_02_LLM_INTEGRATION.md',
            'templates/llm-agent/LLM_AGENT_03_MEMORY_SYSTEM.md',
            'templates/llm-agent/LLM_AGENT_04_TOOL_SYSTEM.md',
            'templates/llm-agent/LLM_AGENT_05_PLANNING_REASONING.md',
            'templates/llm-agent/LLM_AGENT_06_HUMAN_COLLABORATION.md',
            'templates/llm-agent/LLM_AGENT_07_SAFETY_ALIGNMENT.md',
            'templates/llm-agent/LLM_AGENT_08_OBSERVABILITY.md',
            'templates/llm-agent/LLM_AGENT_09_PERFORMANCE.md',
            'templates/llm-agent/LLM_AGENT_10_EVALUATION.md',
            'templates/llm-agent/LLM_AGENT_11_AGENT_FRAMEWORK.md',
        ],
        'general': [
            'templates/general/FULLSTACK_WEB_ANALYSIS.md',
            'templates/general/PIPELINE_WORKFLOW_ANALYSIS.md',
            'templates/general/INTEGRATION_ECOSYSTEM.md',
            'templates/general/FEATURE_TRADEOFF_ANALYSIS.md',
        ]
    },
    'database': {
        'overview': 'templates/database/DATABASE_ANALYSIS_OVERVIEW.md',
        'templates': [
            'templates/database/DATABASE_01_ARCHITECTURE.md',
            'templates/database/DATABASE_02_STORAGE_ENGINE.md',
            'templates/database/DATABASE_03_INDEX_DESIGN.md',
            'templates/database/DATABASE_04_QUERY_PROCESSING.md',
            'templates/database/DATABASE_05_TRANSACTION.md',
            'templates/database/DATABASE_06_HA_FAULT_TOLERANCE.md',
            'templates/database/DATABASE_07_RESOURCE_MANAGEMENT.md',
            'templates/database/DATABASE_08_NETWORK_SERIALIZATION.md',
            'templates/database/DATABASE_09_WORKLOAD_SPECIFIC.md',
            'templates/database/DATABASE_10_OBSERVABILITY.md',
        ],
        'general': [
            'templates/general/FEATURE_TRADEOFF_ANALYSIS.md',
            'templates/general/PIPELINE_WORKFLOW_ANALYSIS.md',
        ]
    },
    'fullstack-web': {
        'overview': None,
        'templates': [
            'templates/general/FULLSTACK_WEB_ANALYSIS.md',
        ],
        'general': [
            'templates/general/PIPELINE_WORKFLOW_ANALYSIS.md',
            'templates/general/INTEGRATION_ECOSYSTEM.md',
            'templates/general/FEATURE_TRADEOFF_ANALYSIS.md',
        ]
    },
    'pipeline': {
        'overview': None,
        'templates': [
            'templates/general/PIPELINE_WORKFLOW_ANALYSIS.md',
        ],
        'general': [
            'templates/general/FEATURE_TRADEOFF_ANALYSIS.md',
            'templates/general/INTEGRATION_ECOSYSTEM.md',
        ]
    },
    'general': {
        'overview': None,
        'templates': [],
        'general': [
            'templates/general/SYSTEM_APPRECIATION_TEMPLATE.md',
            'templates/general/ARCHITECTURE_DECISION_TEMPLATE.md',
            'templates/general/PERFORMANCE_ANALYSIS_TEMPLATE.md',
            'templates/general/FEATURE_TRADEOFF_ANALYSIS.md',
        ]
    }
}

def scan_file_keywords(project_path, signatures):
    """扫描文件内容中的关键词"""
    keyword_scores = {ptype: 0 for ptype in signatures}
    
    # 限制扫描文件数量，避免太慢
    max_files = 100
    scanned = 0
    
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', 'target', 'build', 'dist', '__pycache__', 'vendor', '.next', '.nuxt']]
        
        for file in files:
            if scanned >= max_files:
                break
            
            ext = os.path.splitext(file)[1]
            if ext not in ['.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs', '.cpp', '.cs', '.md']:
                continue
            
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().lower()
                    
                    for ptype, sig in signatures.items():
                        for keyword in sig['keywords']:
                            count = content.count(keyword.lower())
                            keyword_scores[ptype] += count * sig['weight']
                
                scanned += 1
            except:
                continue
    
    return keyword_scores

def scan_file_names(project_path, signatures):
    """扫描文件名和目录名"""
    name_scores = {ptype: 0 for ptype in signatures}
    
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', 'target', 'build', 'dist', '__pycache__', 'vendor', '.next', '.nuxt']]
        
        # 检查目录名
        for dir_name in dirs:
            dir_lower = dir_name.lower()
            for ptype, sig in signatures.items():
                for pattern in sig['dir_patterns']:
                    if pattern in dir_lower:
                        name_scores[ptype] += 3 * sig['weight']
        
        # 检查文件名
        for file in files:
            file_lower = file.lower()
            for ptype, sig in signatures.items():
                for pattern in sig['file_patterns']:
                    if pattern in file_lower:
                        name_scores[ptype] += 2 * sig['weight']
    
    return name_scores

def scan_config_files(project_path, signatures):
    """扫描配置文件"""
    config_scores = {ptype: 0 for ptype in signatures}
    
    config_files = [
        'package.json', 'requirements.txt', 'pyproject.toml', 'pom.xml',
        'build.gradle', 'Cargo.toml', 'go.mod', 'docker-compose.yml',
        'docker-compose.yaml', '.env', 'config.json', 'config.yaml'
    ]
    
    for config_file in config_files:
        filepath = os.path.join(project_path, config_file)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().lower()
                    
                    for ptype, sig in signatures.items():
                        for pattern in sig['config_patterns']:
                            if pattern in content:
                                config_scores[ptype] += 5 * sig['weight']
            except:
                continue
    
    return config_scores

def detect_project_type(project_path):
    """检测项目类型"""
    signatures = PROJECT_TYPE_SIGNATURES
    
    # 多维度扫描
    print("  [1/3] 扫描文件名和目录名...")
    name_scores = scan_file_names(project_path, signatures)
    
    print("  [2/3] 扫描配置文件...")
    config_scores = scan_config_files(project_path, signatures)
    
    print("  [3/3] 扫描文件内容关键词...")
    keyword_scores = scan_file_keywords(project_path, signatures)
    
    # 综合评分
    total_scores = {}
    for ptype in signatures:
        total_scores[ptype] = (
            name_scores[ptype] +
            config_scores[ptype] +
            keyword_scores[ptype] * 0.1  # 关键词权重降低，避免过度依赖
        )
    
    # 排序
    sorted_types = sorted(total_scores.items(), key=lambda x: -x[1])
    
    # 判断主类型（需要达到一定阈值）
    primary_type = sorted_types[0][0] if sorted_types[0][1] > 10 else 'general'
    primary_score = sorted_types[0][1]
    
    # 判断次要类型（得分超过主类型 50% 的）
    secondary_types = []
    for ptype, score in sorted_types[1:]:
        if score > primary_score * 0.5 and score > 5:
            secondary_types.append((ptype, score))
    
    return {
        'primary': primary_type,
        'primary_score': primary_score,
        'secondary': secondary_types,
        'all_scores': dict(sorted_types),
        'details': {
            'name_scores': name_scores,
            'config_scores': config_scores,
            'keyword_scores': keyword_scores,
        }
    }

def recommend_templates(project_type):
    """推荐分析模板"""
    return TEMPLATE_RECOMMENDATIONS.get(project_type, TEMPLATE_RECOMMENDATIONS['general'])

def generate_report(project_path, detection_result, recommend_templates_flag):
    """生成检测报告"""
    lines = []
    
    lines.append(f"# 项目类型检测报告\n\n")
    lines.append(f"**项目路径**: `{project_path}`\n\n")
    lines.append("---\n\n")
    
    # 主类型
    primary = detection_result['primary']
    primary_name = PROJECT_TYPE_SIGNATURES[primary]['name']
    primary_score = detection_result['primary_score']
    
    lines.append(f"## 🎯 识别结果\n\n")
    lines.append(f"**主类型**: {primary_name} (`{primary}`)\n")
    lines.append(f"**置信度**: {primary_score:.1f} 分\n\n")
    
    # 次要类型
    if detection_result['secondary']:
        lines.append("**次要类型**:\n")
        for ptype, score in detection_result['secondary']:
            pname = PROJECT_TYPE_SIGNATURES[ptype]['name']
            lines.append(f"- {pname} (`{ptype}`) - {score:.1f} 分\n")
        lines.append("\n")
    
    lines.append("---\n\n")
    
    # 评分详情
    lines.append("## 📊 评分详情\n\n")
    lines.append("| 项目类型 | 文件名得分 | 配置文件得分 | 关键词得分 | 总分 |\n")
    lines.append("|----------|------------|--------------|------------|------|\n")
    
    details = detection_result['details']
    for ptype, total_score in detection_result['all_scores'].items():
        if total_score > 0:
            pname = PROJECT_TYPE_SIGNATURES[ptype]['name']
            name_s = details['name_scores'][ptype]
            config_s = details['config_scores'][ptype]
            keyword_s = details['keyword_scores'][ptype] * 0.1
            lines.append(f"| {pname} | {name_s:.1f} | {config_s:.1f} | {keyword_s:.1f} | **{total_score:.1f}** |\n")
    
    lines.append("\n---\n\n")
    
    # 模板推荐
    if recommend_templates_flag:
        lines.append("## 📚 推荐分析模板\n\n")
        
        templates = recommend_templates(primary)
        
        if templates['overview']:
            lines.append(f"### 总览文档\n\n")
            lines.append(f"- `{templates['overview']}`\n\n")
        
        if templates['templates']:
            lines.append(f"### 专项模板 ({len(templates['templates'])} 个)\n\n")
            for t in templates['templates']:
                lines.append(f"- `{t}`\n")
            lines.append("\n")
        
        if templates['general']:
            lines.append(f"### 通用模板 ({len(templates['general'])} 个)\n\n")
            for t in templates['general']:
                lines.append(f"- `{t}`\n")
            lines.append("\n")
        
        total_count = len(templates['templates']) + len(templates['general'])
        lines.append(f"**总计**: {total_count} 个模板\n\n")
        lines.append("---\n\n")
    
    # 分析建议
    lines.append("## 💡 分析建议\n\n")
    
    if primary == 'llm-agent':
        lines.append("1. **重点关注**: Agent 架构、LLM 集成、记忆系统、工具系统、Agent 框架选型\n")
        lines.append("2. **核心文件**: Agent/Tool/Memory/Prompt 相关文件\n")
        lines.append("3. **分析模式**: 建议启用最大分析模式（40-80+ 文档）\n")
    elif primary == 'database':
        lines.append("1. **重点关注**: 存储引擎、索引设计、查询处理、事务管理\n")
        lines.append("2. **核心文件**: Storage/Index/Query/Transaction 相关文件\n")
        lines.append("3. **分析模式**: 建议启用最大分析模式（40-80+ 文档）\n")
    elif primary == 'fullstack-web':
        lines.append("1. **重点关注**: 前后端架构、路由设计、数据流、部署架构\n")
        lines.append("2. **核心文件**: 路由/组件/API/Worker 相关文件\n")
        lines.append("3. **分析模式**: 建议启用最大分析模式（40-60+ 文档）\n")
    elif primary == 'pipeline':
        lines.append("1. **重点关注**: Pipeline 设计、状态管理、错误处理、并发控制\n")
        lines.append("2. **核心文件**: Pipeline/Worker/Queue/Task 相关文件\n")
        lines.append("3. **分析模式**: 建议启用最大分析模式（30-50+ 文档）\n")
    else:
        lines.append("1. **重点关注**: 架构设计、核心模块、代码质量\n")
        lines.append("2. **核心文件**: 入口点/核心类/高频修改文件\n")
        lines.append("3. **分析模式**: 根据项目规模选择分析深度\n")
    
    lines.append("\n---\n\n")
    
    return ''.join(lines)

def main():
    parser = argparse.ArgumentParser(description='自动检测项目类型，推荐分析模板')
    parser.add_argument('project_path', help='项目路径')
    parser.add_argument('--recommend-templates', action='store_true', help='推荐分析模板')
    parser.add_argument('-o', '--output', help='输出文件路径（可选）')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式')
    
    args = parser.parse_args()
    
    project_path = Path(args.project_path).resolve()
    if not project_path.exists():
        print(f"❌ 项目路径不存在: {project_path}")
        sys.exit(1)
    
    print(f"🔍 检测项目类型: {project_path.name}")
    print(f"   路径: {project_path}\n")
    
    # 检测项目类型
    detection_result = detect_project_type(project_path)
    
    primary = detection_result['primary']
    primary_name = PROJECT_TYPE_SIGNATURES[primary]['name']
    
    print(f"\n✅ 识别结果:")
    print(f"   主类型: {primary_name} ({primary})")
    print(f"   置信度: {detection_result['primary_score']:.1f} 分")
    
    if detection_result['secondary']:
        print(f"   次要类型: {', '.join([PROJECT_TYPE_SIGNATURES[t]['name'] for t, _ in detection_result['secondary']])}")
    
    # 生成报告
    report = generate_report(project_path, detection_result, args.recommend_templates)
    
    # 输出
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n📝 报告已保存: {output_path}")
    elif args.json:
        print(json.dumps(detection_result, indent=2, ensure_ascii=False))
    else:
        print("\n" + report)
    
    # 返回项目类型（供其他脚本调用）
    return detection_result

if __name__ == '__main__':
    result = main()
