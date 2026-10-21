"""Preparation and structural checks for bounded initial/reading stages.

No model calls, source-tree scans, or changes to legacy analysis metadata.
Checks establish structure and material freshness, not semantic correctness.
"""

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit


INITIAL_DOCS = (
    "INDEX.md", "project-overview.md", "code-map.md", "architecture.md",
    "core-flows.md", "core-mechanisms.md", "design-highlights.md",
    "deep-dive-roadmap.md",
)
WORK_FILES = {"PLAN.md", "VERIFICATION_REPORT.md"}


def fingerprint(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_path(root, name):
    """Require a normalized relative path inside root, including symlink targets."""
    if not isinstance(name, str) or not name:
        raise ValueError("路径必须是非空字符串")
    rel = Path(name)
    if rel.is_absolute() or ".." in rel.parts or rel.as_posix() != name:
        raise ValueError(f"需要规范的相对路径: {name}")
    target = (root / rel).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"路径越出分析目录: {name}")
    return target


def material_path(root, name):
    path = local_path(root, name)
    if path.is_relative_to((root / "reading").resolve()):
        raise ValueError(f"阅读文档不能作为底稿: {name}")
    if path.suffix != ".md" or path.name in WORK_FILES or path.name.endswith("_REPORT.md"):
        raise ValueError(f"不是分析底稿 Markdown: {name}")
    if not path.is_file():
        raise ValueError(f"底稿不存在: {name}")
    return path


def source_snapshot(source):
    def git(*args):
        try:
            result = subprocess.run(
                ["git", "-C", str(source), *args], capture_output=True, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return result.stdout if result.returncode == 0 else None

    commit = git("rev-parse", "HEAD")
    status = git("status", "--porcelain=v1", "-z", "--untracked-files=normal")
    return {
        "path": str(source),
        "commit": commit.decode().strip() if commit else None,
        "dirty": bool(status) if status is not None else None,
        # Status fingerprint is not a digest of dirty file contents.
        "worktree_status_sha256": hashlib.sha256(status).hexdigest() if status is not None else None,
    }


def prepare_stage(mode, target, output=None, materials=()):
    target = Path(target).resolve()
    if not target.is_dir():
        raise ValueError(f"目录不存在: {target}")
    root = Path(output).resolve() if mode == "initial" and output else target
    stage = root / ("00-initial" if mode == "initial" else "reading")
    if stage.exists() or stage.is_symlink():
        raise ValueError(f"阶段目录已存在，请续接现有计划，拒绝覆盖: {stage}")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    state = {"schema_version": 1, "mode": mode, "status": "pending", "created_at": now}
    if mode == "initial":
        if not output:
            raise ValueError("initial 必须指定 --output 分析根目录")
        if materials:
            raise ValueError("initial 不接受 --material")
        state.update({
            "source": source_snapshot(target),
            "budget": {"source_files": 20, "source_lines": 3000, "rounds": 3},
            "sampled_files": [], "usage": {"source_lines": 0, "rounds": 0}, "unresolved": [],
        })
        name = "analysis-state.json"
        plan = """# 初步分析计划

状态：pending。准备器仅建立计划，尚未开展源码分析。

1. 阅读 guides/INITIAL_ANALYSIS.md 和 templates/initial/OUTPUT_SPEC.md。
2. 记录用户关注问题、项目类型、模块边界；建立功能—模块—机制映射。
3. 默认最多 20 个源码文件、3000 行源码片段、3 轮取证；按问题选样并更新状态。
4. 按八篇文档规格写作；预算耗尽时标记 partial、记录缺口，不自动递归。
5. 更新根 INDEX.md 导航；执行 verify-analysis.py <分析根目录> --initial。
6. 按用户范围续接递归分析或文档整理，保留本阶段基线。
"""
    else:
        if output:
            raise ValueError("reading 的位置由分析根目录确定，不接受 --output")
        if not materials:
            raise ValueError("reading 至少需要一个 --material（相对分析根目录）")
        hashes = {name: fingerprint(material_path(root, name)) for name in materials}
        state.update({"materials": hashes, "pages": {}, "unresolved": []})
        name = "sources.json"
        plan = """# 阅读文档整理计划

状态：pending。来源指纹已记录，尚未编写阅读文档。

1. 阅读 guides/READING_SYNTHESIS.md 和 templates/reading/OUTPUT_SPEC.md。
2. 明确读者、本轮问题、选定材料；核对材料版本与相互冲突。
3. 默认最多 12 份底稿、60000 字符、6 篇正文；预算不足则缩小本轮范围。
4. 在 overview/topics/modules 中按材料创建实际需要的页面，填写 sources.json 的 pages。
5. 每篇正文链接实际材料并保留证据状态；README.md 导航与覆盖说明保持一致。
6. 执行 verify-analysis.py <分析根目录> --reading；根 INDEX.md 增加阅读入口。
7. 更新时先修订受影响页面，再刷新材料指纹；不借整理阶段启动源码分析。
"""
    # Validate all inputs before creating anything. Never overwrite a previous stage.
    stage.mkdir(parents=True, exist_ok=False)
    (stage / name).write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (stage / "PLAN.md").write_text(plan, encoding="utf-8")
    return stage


def markdown_links(path):
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$", "", text)
    # Inline Markdown links, including <paths with spaces>. External/anchor-only links are skipped.
    targets = re.findall(r"\[[^\]]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)", text)
    links = []
    for target in targets:
        target = target.strip("<>")
        url = urlsplit(target)
        if url.scheme or url.netloc or not url.path:
            continue
        links.append((path.parent / unquote(url.path)).resolve())
    return links


def check_document(path, errors, section=None):
    if not path.is_file():
        errors.append(f"文档不存在: {path.name}")
        return
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        errors.append(f"文档为空: {path.name}")
    if section and not re.search(r"(?m)^##\s+" + re.escape(section) + r"\s*$", text):
        errors.append(f"{path.name}: 缺少章节 {section}")
    for link in markdown_links(path):
        if not link.exists():
            errors.append(f"{path.name}: 断链 {link}")


def verify_stage(root, mode):
    """Return structural issues; never treat prepared scaffolding as completed work."""
    root = Path(root).resolve()
    stage = root / ("00-initial" if mode == "initial" else "reading")
    errors = []
    state_path = stage / ("analysis-state.json" if mode == "initial" else "sources.json")
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"状态记录不可读: {exc}"]
    if not isinstance(state, dict):
        return ["状态记录必须是 JSON 对象"]
    if state.get("schema_version") != 1 or state.get("mode") != mode:
        errors.append("状态 schema_version/mode 不匹配")
    if state.get("status") != "complete":
        errors.append(f"阶段未全部完成: {state.get('status')}（partial 可交付但不判完成）")
    if not isinstance(state.get("unresolved"), list):
        errors.append("unresolved 必须是列表")

    if mode == "initial":
        docs = [stage / name for name in INITIAL_DOCS]
        for path in docs:
            check_document(path, errors, None if path.name == "INDEX.md" else "证据与未确认项")
        index = stage / "INDEX.md"
        if index.is_file():
            linked = set(markdown_links(index))
            for path in docs[1:]:
                if path.resolve() not in linked:
                    errors.append(f"INDEX.md 未导航到 {path.name}")
        for name in ("architecture.md", "core-flows.md"):
            path = stage / name
            if path.is_file() and "```mermaid" not in path.read_text(encoding="utf-8"):
                errors.append(f"{name}: 缺少 Mermaid 图")
        source = state.get("source")
        if not isinstance(source, dict) or not source.get("path") or "commit" not in source or "dirty" not in source:
            errors.append("缺少源码路径/版本/工作区状态")
        samples = state.get("sampled_files")
        if not isinstance(samples, list) or not samples or not all(isinstance(p, str) and p for p in samples):
            errors.append("缺少已取证的源码路径列表 sampled_files")
        elif isinstance(source, dict) and isinstance(source.get("path"), str):
            for sample in samples:
                try:
                    local_path(Path(source["path"]), sample)
                except ValueError as exc:
                    errors.append(str(exc))
        for field, keys in (("budget", ("source_files", "source_lines", "rounds")),
                            ("usage", ("source_lines", "rounds"))):
            values = state.get(field)
            if not isinstance(values, dict) or any(type(values.get(k)) is not int or values[k] < 0 for k in keys):
                errors.append(f"{field} 缺少有效的预算/用量记录")
        budget, usage = state.get("budget", {}), state.get("usage", {})
        if isinstance(budget, dict) and isinstance(usage, dict):
            for key in ("source_lines", "rounds"):
                used, limit = usage.get(key), budget.get(key)
                if type(used) is int and type(limit) is int and (used < 1 or used > limit):
                    errors.append(f"{key} 用量为零或超过预算，不能判定本轮完成")
            limit = budget.get("source_files")
            if isinstance(samples, list) and all(isinstance(p, str) for p in samples) and type(limit) is int:
                if len(set(samples)) > limit:
                    errors.append("源码文件取证数量超过预算")
    else:
        index = stage / "README.md"
        check_document(index, errors)
        pages = state.get("pages")
        materials = state.get("materials")
        if not isinstance(pages, dict) or not pages:
            errors.append("pages 必须登记至少一篇实际阅读正文及来源")
            pages = {}
        if not isinstance(materials, dict) or not materials:
            errors.append("materials 必须包含材料路径及 SHA-256")
            materials = {}
        for name, digest in materials.items():
            try:
                path = material_path(root, name)
                if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                    errors.append(f"无效的材料指纹: {name}")
                elif fingerprint(path) != digest:
                    affected = [page for page, refs in pages.items() if isinstance(refs, list) and name in refs]
                    errors.append(f"材料已变化: {name}; 待同步页面: {', '.join(affected) or '待检查'}")
            except ValueError as exc:
                errors.append(str(exc))
        linked = set(markdown_links(index)) if index.is_file() else set()
        for page, refs in pages.items():
            try:
                path = local_path(stage, page)
                if Path(page).parts[0] not in {"overview", "topics", "modules"} or path.suffix != ".md":
                    raise ValueError(f"正文应位于 overview/topics/modules: {page}")
                check_document(path, errors, "来源与未确认项")
                if path not in linked:
                    errors.append(f"README.md 未导航到 {page}")
                if not isinstance(refs, list) or not refs or not all(isinstance(r, str) for r in refs):
                    errors.append(f"{page}: 缺少有效来源列表")
                    continue
                page_links = set(markdown_links(path)) if path.is_file() else set()
                for ref in refs:
                    if ref not in materials:
                        errors.append(f"{page}: 来源未登记指纹 {ref}")
                    elif material_path(root, ref) not in page_links:
                        errors.append(f"{page}: 正文未链接来源 {ref}")
            except ValueError as exc:
                errors.append(str(exc))
        for path in stage.rglob("*.md"):
            if path.name in WORK_FILES or path == index:
                continue
            if path.relative_to(stage).as_posix() not in pages:
                errors.append(f"正文未登记来源: {path.relative_to(stage)}")
    return errors


def run_verification(root, mode):
    try:
        issues = verify_stage(root, mode)
    except (OSError, ValueError) as exc:
        issues = [f"检查失败: {exc}"]
    result = {"mode": mode, "ok": not issues, "issues": issues,
              "scope": "结构、导航与材料指纹；不证明语义正确或运行验证"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if issues else 0
