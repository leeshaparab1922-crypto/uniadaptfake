"""Offline tests: only .github fixtures may be written; no app or remote actions.

Run: python -B .github/validation/test_port.py
Optional YAML validation uses already-installed PyYAML; never installs it.
"""
import ast
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
AREA = Path(__file__).resolve().parents[1]
ROOT = AREA.parent


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


policy = load(AREA / "hooks/scripts/policy.py")
lookup = load(AREA / "skills/srs-lookup/lookup.py")


def payload(path="backend/app/main.py", name="edit", **extra):
    return {"sessionId": "fixture", "timestamp": 0, "cwd": str(ROOT),
            "toolName": name, "toolArgs": {"path": path}, **extra}


def command(text):
    return payload(name="powershell", toolArgs={"command": text})


class SrsTests(unittest.TestCase):
    def test_protected_paths(self):
        paths = ["SRS_Doc/spec.md", "srs_doc/spec.md", "SRS_DOC/spec.md",
                 "nested/SRS_Doc/spec.md", "SRS_Doc", "./SRS_Doc/../other.md",
                 "SRS_Doc./spec.md", "SRS_Doc /spec.md", "SRS_Doc:stream",
                 r"SRS_Doc\spec.md", r"E:\repo\SRS_Doc\spec.md",
                 r"\\server\repo\srs_doc\spec.md", "/tmp/repo/SRS_Doc/spec.md"]
        for name in ("create", "edit", "str_replace", "str_replace_editor"):
            for path in paths:
                with self.subTest(tool=name, path=path):
                    self.assertEqual(policy.pre(payload(path, name), "srs")["permissionDecision"], "deny")

    def test_unrelated(self):
        for path in ("backend/app/main.py", "frontend/src/App.tsx", "docs/SRS_Doc-notes.md",
                     "docs/srs_doc_backup/spec.md", r"E:\repo\backend\main.py"):
            self.assertEqual(policy.pre(payload(path), "srs"), {})
        data = payload("docs/example.md")
        data["toolArgs"]["new_str"] = "Documentation about SRS_Doc/spec.md"
        self.assertEqual(policy.pre(data, "srs"), {})

    def test_relative_cwd(self):
        for cwd in (str(ROOT / "SRS_Doc"), r"E:\repo\SRS_Doc"):
            self.assertEqual(policy.pre(payload("spec.md", cwd=cwd), "srs")["permissionDecision"], "deny")

    def test_encoded_args(self):
        data = payload(toolArgs=json.dumps({"path": "SRS_Doc/spec.md"}))
        self.assertEqual(policy.pre(data, "srs")["permissionDecision"], "deny")

    def test_patch_all_targets(self):
        for operation in ("Add File", "Update File", "Delete File", "Move to"):
            data = payload(name="apply_patch", toolArgs={"input":
                f"*** Begin Patch\n*** Update File: backend/a.py\n@@\n-a\n+b\n*** {operation}: SRS_Doc/a.md\n*** End Patch"})
            self.assertEqual(policy.pre(data, "srs")["permissionDecision"], "deny")
        data["toolArgs"]["input"] = "*** Begin Patch\n*** Add File: backend/a.py\n+a\n*** End Patch"
        self.assertEqual(policy.pre(data, "srs"), {})

    def test_multi_edit(self):
        data = payload(name="multi_replace_string_in_file", toolArgs={"replacements":
                       [{"filePath": "backend/a.py"}, {"filePath": "SRS_Doc/a.md"}]})
        self.assertEqual(policy.pre(data, "srs")["permissionDecision"], "deny")

    def test_read_only(self):
        self.assertEqual(policy.pre(payload("SRS_Doc/spec.md", name="view"), "srs"), {})
        data = payload("SRS_Doc/spec.md", name="str_replace_editor")
        data["toolArgs"]["command"] = "view"
        self.assertEqual(policy.pre(data, "srs"), {})
        self.assertEqual(policy.pre(command("Get-Content SRS_Doc/spec.md"), "srs"), {})

    def test_shell_write(self):
        for text in ('Set-Content SRS_Doc/spec.md bad', 'echo bad > SRS_Doc/spec.md',
                     'rm -rf SRS_Doc', r'python change.py E:\repo\SRS_Doc\spec.md',
                     'git restore SRS_Doc/spec.md', 'git checkout -- SRS_Doc/spec.md'):
            self.assertEqual(policy.pre(command(text), "srs")["permissionDecision"], "deny")
        data = command('Set-Content spec.md bad')
        data['cwd'] = str(ROOT / 'SRS_Doc')
        self.assertEqual(policy.pre(data, "srs")["permissionDecision"], "deny")

    def test_move_and_delete(self):
        self.assertEqual(policy.pre(payload('SRS_Doc/spec.md', name='delete'), 'srs')['permissionDecision'], 'deny')
        for source, destination in [('SRS_Doc/spec.md', 'docs/a.md'), ('docs/a.md', 'SRS_Doc/spec.md')]:
            data = payload(name='move', toolArgs={'source': source, 'destination': destination})
            self.assertEqual(policy.pre(data, 'srs')['permissionDecision'], 'deny')

    def test_malformed_file_arguments(self):
        for name in policy.WRITERS:
            for args in (None, [], "{", {}, {"path": ""}, {"path": 1}):
                with self.subTest(name=name, args=args):
                    with self.assertRaises((ValueError, TypeError)):
                        policy.pre(payload(name=name, toolArgs=args), "srs")

    def test_unknown_tool_requires_inspection(self):
        self.assertEqual(policy.pre(payload(name="external-write-tool"), "srs")["permissionDecision"], "ask")


class PublishTests(unittest.TestCase):
    def test_variants(self):
        commands = ["git push", "git push origin main", "gh pr create", "gh pr merge 3",
                    "gh pr list", "git status && git push", "echo ready; gh pr create",
                    "git status | git push", "false || git push", "git status\ngit push",
                    "GIT_TRACE=1 git push", "env git push", "command git push",
                    'git -C "repo path" -c x=y push', 'git --git-dir=.git push',
                    r'& "C:\Program Files\Git\bin\git.exe" push',
                    'bash -lc "git status && git push"', 'pwsh -Command "gh pr create"',
                    'cmd /c "git push"', 'gh --repo owner/repo pr create',
                    'echo "$(git push)"',
                    "git send-pack origin", "npm publish", "docker push image",
                    "twine upload package", "gh api -X POST repos/a/b/pulls"]
        for text in commands:
            with self.subTest(command=text):
                self.assertEqual(policy.command_risk(text), "publish")
                with patch.dict(os.environ, {"UNIADAPT_AGENT1_SESSION": "1"}):
                    self.assertEqual(policy.pre(command(text), "publish")["permissionDecision"], "deny")
                with patch.dict(os.environ, {"UNIADAPT_AGENT1_SESSION": ""}):
                    self.assertEqual(policy.pre(command(text), "publish")["permissionDecision"], "ask")

    def test_ordinary_and_literals(self):
        for text in ("git status --short", "git diff", "pwd", 'echo "git push"',
                     "echo git push", "Write-Output 'gh pr create'", 'printf "%s" "git push"',
                     "echo '$(git push)'",
                     'echo "git push; gh pr create"'):
            self.assertEqual(policy.command_risk(text), "ordinary", text)
            with patch.dict(os.environ, {"UNIADAPT_AGENT1_SESSION": "1"}):
                self.assertEqual(policy.pre(command(text), "publish"), {}, text)

    def test_opaque_requires_review(self):
        for text in ('python script.py', 'git -c alias.pub=push pub', "npm run deploy",
                     'echo "$computed"', 'Invoke-Expression $command', 'curl -X POST https://example.test'):
            self.assertEqual(policy.pre(command(text), "publish")["permissionDecision"], "ask", text)

    def test_identity_not_fabricated(self):
        data = command("git push")
        data.update(agent_type="phase-planner-implementer", agentName="phase-planner-implementer")
        with patch.dict(os.environ, {"UNIADAPT_AGENT1_SESSION": ""}):
            self.assertEqual(policy.pre(data, "publish")["permissionDecision"], "ask")


class FormattingTests(unittest.TestCase):
    def test_absent_tools_and_directories(self):
        with patch.object(policy.subprocess, "run") as run:
            policy.format_written(payload(toolResult={"resultType": "success"}))
            policy.format_written(payload("frontend/App.tsx", toolResult={"resultType": "success"}))
            self.assertFalse(run.called)

    def test_single_file_scope_and_failures(self):
        with tempfile.TemporaryDirectory(dir=AREA / "validation") as temp:
            root = Path(temp)
            backend = root / "backend"
            backend.mkdir()
            target, unrelated = backend / "main.py", backend / "other.py"
            target.write_text("x=1\n", encoding="utf-8")
            unrelated.write_text("do not change\n", encoding="utf-8")
            config = backend / "ruff.toml"
            config.write_text("line-length = 88\n", encoding="utf-8")
            data = payload(str(target), cwd=str(root), toolResult={"resultType": "success"})
            with patch.object(policy, "ROOT", root), patch.object(policy.shutil, "which", return_value="ruff"), \
                    patch.object(policy.subprocess, "run", side_effect=OSError("missing")) as run:
                policy.format_written(data)
                self.assertEqual(run.call_count, 2)
                for call in run.call_args_list:
                    self.assertEqual(call.args[0][-1], str(target))
                    self.assertIn("--no-cache", call.args[0])
                run.reset_mock()
                policy.format_written(payload(str(unrelated), cwd=str(root), toolResult={"resultType": "failure"}))
                self.assertFalse(run.called)
            self.assertEqual(unrelated.read_text(), "do not change\n")
            self.assertEqual(target.read_text(), "x=1\n")

    def test_frontend_local_tools(self):
        with tempfile.TemporaryDirectory(dir=AREA / "validation") as temp:
            root = Path(temp)
            frontend = root / "frontend"
            frontend.mkdir()
            for relative, content in {"App.tsx": "const x=1", "Other.tsx": "untouched",
                                      "package.json": "{}", "eslint.config.js": "export default []",
                                      ".prettierrc": "{}", "node_modules/eslint/bin/eslint.js": "",
                                      "node_modules/prettier/bin/prettier.cjs": ""}.items():
                path = frontend / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            with patch.object(policy, "ROOT", root), patch.object(policy.shutil, "which", return_value="node"), \
                    patch.object(policy.subprocess, "run") as run:
                policy.format_written(payload(str(frontend / "App.tsx"), cwd=str(root), toolResult={"resultType": "success"}))
                self.assertEqual(run.call_count, 2)
                for call in run.call_args_list:
                    self.assertEqual(call.args[0][-1], str(frontend / "App.tsx"))
                    self.assertNotIn("npx", call.args[0])
                run.reset_mock()
                policy.format_written(payload(str(AREA / "copilot-instructions.md"), toolResult={"resultType": "success"}))
                self.assertFalse(run.called)
            self.assertEqual((frontend / "Other.tsx").read_text(), "untouched")


class SkillTests(unittest.TestCase):
    def test_lookup_forms_and_errors(self):
        lines = ["## 12. Requirements", "| FR-AUTH-001 | login |", "## 23. Mastery", "formula",
                 "## 43. Project Phase Mapping", "| 1 | Foundation | FR-AUTH-001 |", "## 44. Next"]
        self.assertEqual(lookup.lookup("FR-AUTH-001", lines),
                         ["2:| FR-AUTH-001 | login |", "6:| 1 | Foundation | FR-AUTH-001 |"])
        self.assertEqual(lookup.lookup("23", lines), lines[2:4])
        for query in ("phase 1", "phase-1", "Phase_1"):
            self.assertEqual(lookup.lookup(query, lines), [lines[5]])
        for query in ("phase 99", "99", "FR-MISSING-001", "Section 43"):
            with self.assertRaises(ValueError):
                lookup.lookup(query, lines)

    def test_generator_isolated(self):
        generator = load(AREA / "skills/update-claude-md/generate.py")
        with tempfile.TemporaryDirectory(dir=AREA / "validation") as temp:
            root = Path(temp)
            state, target = root / "state.json", root / "CLAUDE.md"
            state.write_text(json.dumps({"current_phase": 1, "phase_name": "Foundation", "status": "planned", "phases": []}))
            with patch.object(generator, "STATE_FILE", str(state)), patch.object(generator, "CLAUDE_MD", str(target)), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(generator.main(), 0)
                self.assertIn(generator.BEGIN_MARKER, target.read_text(encoding="utf-8"))
                target.write_text("BEFORE\n\n" + generator.BEGIN_MARKER + "\nstale\n" + generator.END_MARKER + "\n\nAFTER", encoding="utf-8")
                self.assertEqual(generator.main(), 0)
                text = target.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("BEFORE\n\n"))
                self.assertTrue(text.endswith("\n\nAFTER"))
                self.assertNotIn("stale", text)
                target.write_text("Manual text\n", encoding="utf-8")
                self.assertEqual(generator.main(), 0)
                self.assertTrue(target.read_text(encoding="utf-8").startswith("Manual text\n\n"))

    def test_static_audit_exit_codes(self):
        audit = load(AREA / "skills/verify-live/scripts/audit_phases.py")
        checker = load(AREA / "skills/phase-status/check.py")
        with tempfile.TemporaryDirectory(dir=AREA / "validation") as temp:
            root = Path(temp)
            state = root / "phase-state.json"
            srs = root / "spec.md"
            srs.write_text("fixture")
            state.write_text(json.dumps({"phases": []}))
            with patch.object(audit, "REPO_ROOT", str(root)), patch.object(audit, "STATE_FILE", str(state)), \
                    patch.object(audit, "SRS_FILE", str(srs)), patch.object(sys, "argv", ["audit_phases.py"]), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(audit.main(), 0)
                phase = {"phase": 1, "name": "fixture", "status": "verified", "srs_requirements": ["FR-AUTH-001"],
                         "plan_path": "plan.md", "verification_report_path": "report.md"}
                state.write_text(json.dumps({"phases": [phase]}))
                self.assertEqual(audit.main(), 1)
                (root / "plan.md").write_text("Plan")
                (root / "report.md").write_text("PASS")
                (root / "backend").mkdir()
                (root / "backend/app.py").write_text("# FR-AUTH-001")
                self.assertEqual(audit.main(), 0)
                for excluded in (".github", ".agents", ".claude", "docs", "SRS_Doc"):
                    (root / excluded).mkdir()
                    (root / excluded / "planner-report.py").write_text("# FR-FAKE-999")
                self.assertEqual(audit.grep_repo_for_id("FR-FAKE-999"), [])
                with patch.object(checker, "REPO_ROOT", str(root)):
                    self.assertFalse(checker.find_hint_anywhere("planner"))
                    self.assertTrue(checker.find_hint_anywhere("backend"))


class ConfigTests(unittest.TestCase):
    def test_syntax_and_frontmatter(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML unavailable; install nothing, use Copilot discovery plus schema review")
        for file in AREA.rglob("*.py"):
            ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        for file in list((AREA / "agents").glob("*.agent.md")) + list((AREA / "skills").glob("*/SKILL.md")) + list((AREA / "instructions").glob("*.instructions.md")):
            front = yaml.safe_load(file.read_text(encoding="utf-8").split("---", 2)[1])
            self.assertIsInstance(front, dict)
            if file.parent.name == "instructions":
                self.assertIsInstance(front["applyTo"], str)
                self.assertEqual(set(front), {"applyTo"})
            else:
                self.assertIsInstance(front["name"], str)
                self.assertIsInstance(front["description"], str)
                self.assertLess(len(file.read_text(encoding="utf-8")), 30000)
                self.assertFalse(set(front) & {"permissionMode", "maxTurns", "color", "shell", "skills"})

    def test_hooks_schema(self):
        config = json.loads((AREA / "hooks/uniadapt.json").read_text())
        self.assertEqual(config["version"], 1)
        self.assertEqual(set(config["hooks"]), {"preToolUse", "postToolUse"})
        for hooks in config["hooks"].values():
            for hook in hooks:
                self.assertEqual(hook["type"], "command")
                self.assertGreater(hook["timeoutSec"], 0)
                self.assertEqual(hook["cwd"], ".")
                for key in ("bash", "powershell"):
                    path = ROOT / hook[key].split()[-1]
                    self.assertTrue(path.is_file())
                self.assertFalse(set(hook) & {"matcher", "hooks", "command"})


class WrapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        git_bash = Path("C:/Program Files/Git/bin/bash.exe")
        cls.bash = str(git_bash) if git_bash.is_file() else shutil.which("bash")
        cls.pwsh = shutil.which("pwsh")

    def test_bash_syntax(self):
        if not self.bash:
            self.skipTest("Bash unavailable")
        for file in AREA.rglob("*.sh"):
            result = subprocess.run([self.bash, "-n", file.as_posix()], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_powershell_syntax(self):
        if not self.pwsh:
            self.skipTest("PowerShell unavailable")
        command_text = "$failed = $false; Get-ChildItem .github -Recurse -Filter *.ps1 | ForEach-Object { $tokens=$null; $issues=$null; [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$tokens,[ref]$issues); if ($issues.Count) { $issues; $failed=$true } }; if ($failed) { exit 1 }"
        result = subprocess.run([self.pwsh, "-NoProfile", "-Command", command_text], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lookup_cross_platform_parity_from_nested_cwd(self):
        if not self.bash:
            self.skipTest("Bash unavailable")
        skill = AREA / 'skills/srs-lookup'
        for query in ('FR-AUTH-001', 'BUS-014', 'AC-010', '23', '43', 'phase 1', 'phase-9',
                      'FR-NOTREAL-999', 'phase 999', '999', 'Section 43', ''):
            env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
            native = subprocess.run([sys.executable, '-B', str(skill / 'lookup.py'), query],
                                    cwd=AREA / 'validation', capture_output=True, encoding='utf-8', env=env)
            bash = subprocess.run([self.bash, (skill / 'lookup.sh').as_posix(), query],
                                  cwd=AREA / 'validation', capture_output=True, encoding='utf-8', env=env)
            self.assertEqual(native.returncode, bash.returncode, query)
            if native.returncode == 0:
                self.assertEqual(native.stdout.rstrip(), bash.stdout.rstrip(), query)
        if self.pwsh:
            result = subprocess.run([self.pwsh, '-NoProfile', '-File', str(skill / 'lookup.ps1'), 'phase 1'],
                                    cwd=AREA / 'validation', capture_output=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Foundation', result.stdout)

    def test_hook_fixture_processes(self):
        fixtures = [("block-srs-doc-edits", json.dumps(payload("SRS_Doc/spec.md")), "deny"),
                    ("block-srs-doc-edits", json.dumps(payload()), None),
                    ("block-srs-doc-edits", json.dumps(payload("frontend/App.tsx")), None),
                    ("block-srs-doc-edits", json.dumps(payload(r"E:\repo\srs_doc\spec.md")), "deny"),
                    ("block-srs-doc-edits", "{bad", "deny"),
                    ("block-srs-doc-edits", json.dumps(payload(toolArgs={})), "deny"),
                    ("block-agent1-publish", json.dumps(command("git push")), "deny"),
                    ("block-agent1-publish", json.dumps(command("gh pr create")), "deny"),
                    ("block-agent1-publish", json.dumps(command("git status")), None),
                    ("format-on-write", json.dumps(payload(toolResult={"resultType": "success"})), None),
                    ("format-on-write", "{bad", None)]
        platforms = []
        if self.bash:
            platforms.append((self.bash, ".sh", []))
        if self.pwsh:
            platforms.append((self.pwsh, ".ps1", ["-NoProfile", "-File"]))
        for exe, suffix, options in platforms:
            for name, data, expected in fixtures:
                with self.subTest(platform=suffix, hook=name, data=data):
                    script = AREA / "hooks/scripts" / (name + suffix)
                    result = subprocess.run([exe, *options, script.as_posix()], input=data, capture_output=True,
                                            text=True, cwd=AREA / "validation", timeout=10,
                                            env={**os.environ, "UNIADAPT_AGENT1_SESSION": "1"})
                    self.assertEqual(result.returncode, 0, result.stderr)
                    output = json.loads(result.stdout)
                    self.assertEqual(output.get("permissionDecision"), expected)
                    if expected:
                        self.assertTrue(output["permissionDecisionReason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
