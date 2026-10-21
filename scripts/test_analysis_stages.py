"""Contract checks for stage isolation, provenance and legacy compatibility."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from analysis_stages import INITIAL_DOCS, prepare_stage, verify_stage


SCRIPTS = Path(__file__).resolve().parent


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "source"
        self.root = self.base / "analysis"
        self.source.mkdir()
        self.root.mkdir()

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def update(self, path, **values):
        state = json.loads(path.read_text())
        state.update(values)
        path.write_text(json.dumps(state), encoding="utf-8")

    def reading(self):
        material = self.root / "10-module-deep/core/00-overview/architecture.md"
        self.write(material, "# 核心模块\n入口调用存储接口，证据 src/core.py:3。\n")
        ref = material.relative_to(self.root).as_posix()
        stage = prepare_stage("reading", self.root, materials=[ref])
        self.write(stage / "README.md", "# 阅读入口\n[架构](overview/architecture.md)\n")
        self.write(stage / "overview/architecture.md",
                   f"# 核心架构\n入口通过接口调用存储。\n## 来源与未确认项\n[材料](../../{ref})\n")
        self.update(stage / "sources.json", status="complete", pages={"overview/architecture.md": [ref]})
        return stage, material, ref

    def test_initial_prepare_isolated_no_false_completion_or_overwrite(self):
        self.write(self.root / "INDEX.md", "已有索引")
        self.write(self.root / "project-meta.json", '{"original": true}')
        stage = prepare_stage("initial", self.source, self.root)
        state = json.loads((stage / "analysis-state.json").read_text())
        self.assertIsNone(state["source"]["commit"])
        self.assertEqual(self.root.joinpath("INDEX.md").read_text(), "已有索引")
        self.assertEqual(set(p.name for p in stage.iterdir()), {"PLAN.md", "analysis-state.json"})
        self.assertTrue(verify_stage(self.root, "initial"))
        before = (stage / "analysis-state.json").read_bytes()
        with self.assertRaises(ValueError):
            prepare_stage("initial", self.source, self.root)
        self.assertEqual((stage / "analysis-state.json").read_bytes(), before)
        self.assertEqual(json.loads((self.root / "project-meta.json").read_text()), {"original": True})

    def test_initial_complete_partial_and_broken_navigation(self):
        stage = prepare_stage("initial", self.source, self.root)
        for name in INITIAL_DOCS:
            body = "# 项目分析\n已检查关键入口及模块关系。\n## 证据与未确认项\n源码确认：src/main.py:1。\n"
            if name in {"architecture.md", "core-flows.md"}:
                body += '```mermaid\nflowchart LR\n A["入口"] --> B["处理"]\n```\n'
            self.write(stage / name, body)
        self.write(stage / "INDEX.md", "# 初步入口\n" + "\n".join(f"[{n}]({n})" for n in INITIAL_DOCS[1:]))
        self.update(stage / "analysis-state.json", status="complete", sampled_files=["src/main.py"],
                    usage={"source_lines": 12, "rounds": 1})
        self.assertEqual(verify_stage(self.root, "initial"), [])
        self.update(stage / "analysis-state.json", status="partial")
        self.assertTrue(verify_stage(self.root, "initial"))
        self.update(stage / "analysis-state.json", status="complete")
        self.update(stage / "analysis-state.json", usage={"source_lines": 3001, "rounds": 1})
        self.assertTrue(any("超过预算" in i for i in verify_stage(self.root, "initial")))
        self.update(stage / "analysis-state.json", usage={"source_lines": 12, "rounds": 1})
        (stage / "code-map.md").unlink()
        self.assertTrue(verify_stage(self.root, "initial"))

    def test_reading_supports_old_material_and_detects_staleness(self):
        stage, material, ref = self.reading()
        self.assertFalse((self.root / "00-initial").exists())
        self.assertEqual(verify_stage(self.root, "reading"), [])
        material.write_text("# 新架构\n采用了新的存储接口。", encoding="utf-8")
        issues = verify_stage(self.root, "reading")
        self.assertTrue(any("材料已变化" in i and "overview/architecture.md" in i for i in issues))
        material.unlink()
        self.assertTrue(any("底稿不存在" in i for i in verify_stage(self.root, "reading")))

    def test_reject_missing_self_and_escaped_sources_before_writing(self):
        for ref in ["missing.md", "../outside.md", "reading/overview/page.md", "PLAN.md"]:
            with self.subTest(ref=ref):
                with self.assertRaises(ValueError):
                    prepare_stage("reading", self.root, materials=[ref])
                self.assertFalse((self.root / "reading").exists())
        self.write(self.base / "outside.md", "# 外部内容")
        (self.root / "alias.md").symlink_to(self.base / "outside.md")
        with self.assertRaises(ValueError):
            prepare_stage("reading", self.root, materials=["alias.md"])

    def test_reading_checks_page_sources_and_navigation(self):
        stage, material, ref = self.reading()
        self.write(stage / "overview/orphan.md", "# 无来源文档")
        self.assertTrue(any("正文未登记来源" in i for i in verify_stage(self.root, "reading")))
        (stage / "overview/orphan.md").unlink()
        self.write(stage / "overview/architecture.md", "# 文档\n## 来源与未确认项\n未链接材料。")
        self.assertTrue(any("正文未链接来源" in i for i in verify_stage(self.root, "reading")))
        self.write(stage / "README.md", "# 导航\n[错误](missing.md)")
        self.assertTrue(any("断链" in i for i in verify_stage(self.root, "reading")))

    def test_invalid_state_fails_cleanly(self):
        stage, _, _ = self.reading()
        for value in ([], {"mode": "reading", "pages": [], "materials": []}):
            (stage / "sources.json").write_text(json.dumps(value))
            self.assertTrue(verify_stage(self.root, "reading"))

    def test_legacy_counts_and_orphans_ignore_new_stage_docs(self):
        verifier = load_script("verify-analysis")
        self.write(self.root / "INDEX.md", "# 索引\n")
        old_count = verifier.check_recursive_mode(str(self.root))["total_files"]
        for directory in ("00-initial", "reading"):
            for n in range(55):
                self.write(self.root / directory / f"doc-{n}.md", "# 文档\n")
        self.assertEqual(verifier.check_recursive_mode(str(self.root))["total_files"], old_count)
        self.assertEqual(verifier.check_maximum_mode(str(self.root))["total_files"], old_count)
        self.assertEqual(verifier.check_index_consistency(self.root)["orphan_files"], [])
        evidence = load_script("evidence-check")
        self.assertEqual(evidence.find_md_files(self.root), [])
        self.assertEqual(len(evidence.find_md_files(self.root / "00-initial")), 55)

    def test_prepare_cli_real_git_snapshot_and_preserves_existing_root(self):
        subprocess.run(["git", "init", "-q", str(self.source)], check=True)
        self.write(self.source / "main.py", "print('hello')\n")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "prepare-stage.py"), "initial", str(self.source), "-o", str(self.root)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        snapshot = json.loads((self.root / "00-initial/analysis-state.json").read_text())["source"]
        self.assertTrue(snapshot["dirty"])
        self.assertIsNone(snapshot["commit"])
        self.assertEqual(len(snapshot["worktree_status_sha256"]), 64)

    def test_recursive_handoff_preserves_expected_output_paths(self):
        orchestrator = load_script("recursive-orchestrator")
        module = dict(name="pkg/core", path="pkg/core", total_files=3, total_lines=40,
                      size_category="small", analysis_strategy="layer1_plus_key_files")
        expected = orchestrator.get_expected_files(module, str(self.root))
        prepare_stage("initial", self.source, self.root)
        plan_path = self.root / "PLAN-round2.md"
        task, _ = orchestrator.generate_spawn_task(module, 2, str(self.root), str(self.source), plan_path)
        self.assertIn(str(plan_path), task)
        self.assertIn("deep-dive-roadmap.md", task)
        self.assertEqual(orchestrator.get_expected_files(module, str(self.root)), expected)
        self.assertTrue(all("/10-module-deep/pkg/core/" in p for p in expected))

    def test_cli_rejects_mixed_modes_and_reports_missing_state(self):
        command = [sys.executable, str(SCRIPTS / "verify-analysis.py"), str(self.root)]
        result = subprocess.run(command + ["--initial", "--all"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        result = subprocess.run(command + ["--reading"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
