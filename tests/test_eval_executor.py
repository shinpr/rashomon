#!/usr/bin/env python3
"""Tests for eval-executor.py"""

import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Load eval-executor.py (hyphenated filename requires importlib)
_script_path = Path(__file__).parent.parent / "skills" / "recipe-eval-skill" / "scripts" / "eval-executor.py"
_spec = importlib.util.spec_from_file_location("eval_executor", _script_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

StreamProcessor = _mod.StreamProcessor
_error_output = _mod._error_output
execute = _mod.execute
_git_changes = _mod._git_changes
_git_snapshot = _mod._git_snapshot
_resolve_tool_path = _mod._resolve_tool_path
_skill_environment_after = _mod._skill_environment_after
_skill_environment_before = _mod._skill_environment_before
skill_directory_fingerprint = _mod.skill_directory_fingerprint


@pytest.fixture(autouse=True)
def stable_git_state(monkeypatch):
    monkeypatch.setattr(
        _mod,
        "_git_snapshot",
        lambda _cwd: {"head": "abc123", "entries": {}},
    )
    monkeypatch.setattr(_mod, "_git_changes", lambda _cwd, _before, _after: [])


# --- StreamProcessor: init event ---


class TestStreamProcessorInit:
    def test_discovers_skill_when_present_in_skills_list(self):
        processor = StreamProcessor(target_skill="my-skill")
        line = json.dumps({
            "type": "system", "subtype": "init",
            "skills": ["other-skill", "my-skill", "another-skill"],
        })
        processor.process_line(line)
        assert processor.skill_discovered is True

    def test_skill_not_discovered_when_absent(self):
        processor = StreamProcessor(target_skill="my-skill")
        line = json.dumps({
            "type": "system", "subtype": "init",
            "skills": ["other-skill"],
        })
        processor.process_line(line)
        assert processor.skill_discovered is False

    def test_namespaced_skill_is_diagnostic_not_project_discovery(self):
        processor = StreamProcessor(target_skill="my-skill")
        processor.process_line(json.dumps({
            "type": "system",
            "subtype": "init",
            "skills": ["plugin:my-skill"],
        }))
        assert processor.skill_discovered is False
        assert processor.namespaced_skill_discoveries == ["plugin:my-skill"]

    def test_skill_not_discovered_when_skills_list_empty(self):
        processor = StreamProcessor(target_skill="my-skill")
        line = json.dumps({
            "type": "system", "subtype": "init",
            "skills": [],
        })
        processor.process_line(line)
        assert processor.skill_discovered is False

    def test_skill_not_discovered_when_skills_key_missing(self):
        processor = StreamProcessor(target_skill="my-skill")
        line = json.dumps({"type": "system", "subtype": "init"})
        processor.process_line(line)
        assert processor.skill_discovered is False

    def test_ignores_system_events_without_init_subtype(self):
        processor = StreamProcessor(target_skill="my-skill")
        line = json.dumps({
            "type": "system", "subtype": "other",
            "skills": ["my-skill"],
        })
        processor.process_line(line)
        assert processor.skill_discovered is False


# --- StreamProcessor: assistant event (tool_use) ---


class TestStreamProcessorToolUse:
    def test_detects_skill_invocation(self):
        processor = StreamProcessor(target_skill="error-handling")
        line = json.dumps({
            "type": "assistant",
            "message": {"content": [
                {"type": "tool_use", "name": "Skill", "input": {"skill": "error-handling"}},
            ]},
        })
        processor.process_line(line)
        assert processor.skill_invoked is True
        assert processor.build_output()["skill_used"] is True
        assert "Skill" in processor.tools_used

    def test_namespaced_invocation_is_diagnostic_not_project_usage(self):
        processor = StreamProcessor(target_skill="error-handling")
        line = json.dumps({
            "type": "assistant",
            "message": {"content": [
                {"type": "tool_use", "name": "Skill", "input": {"skill": "plugin:error-handling"}},
            ]},
        })
        processor.process_line(line)
        assert processor.skill_invoked is False
        assert processor.build_output()["skill_used"] is False
        assert processor.namespaced_skill_invocations == ["plugin:error-handling"]
        assert "Skill" in processor.tools_used

    def test_does_not_infer_file_modifications_from_tool_name(self):
        processor = StreamProcessor(target_skill="x")
        line = json.dumps({
            "type": "assistant",
            "message": {"content": [
                {"type": "tool_use", "name": "Write", "input": {"file_path": "/src/a.js"}},
            ]},
        })
        processor.process_line(line)
        assert processor.files_modified == []

    def test_direct_skill_read_counts_as_usage(self):
        path = "/repo/.claude/skills/error-handling/SKILL.md"
        processor = StreamProcessor(
            target_skill="error-handling",
            cwd="/repo",
            expected_skill_path=path,
        )
        processor.process_line(json.dumps({
            "type": "assistant",
            "message": {"content": [
                {"type": "tool_use", "name": "Read", "input": {"file_path": path}},
            ]},
        }))
        output = processor.build_output()
        assert output["skill_invoked"] is False
        assert output["skill_used"] is True
        assert output["skill_usage_evidence"] == [
            {"method": "Read", "value": _resolve_tool_path(path, "/repo")}
        ]

    def test_same_named_skill_at_wrong_path_does_not_count_as_usage(self):
        processor = StreamProcessor(
            target_skill="error-handling",
            cwd="/repo",
            expected_skill_path="/repo/.claude/skills/error-handling/SKILL.md",
        )
        processor.process_line(json.dumps({
            "type": "assistant",
            "message": {"content": [
                {
                    "type": "tool_use",
                    "name": "Read",
                    "input": {"file_path": "/repo/skills/error-handling/SKILL.md"},
                },
            ]},
        }))
        assert processor.build_output()["skill_used"] is False

    def test_tracks_multiple_tools(self):
        processor = StreamProcessor(target_skill="x")
        processor.process_line(json.dumps({
            "type": "assistant",
            "message": {"content": [
                {"type": "tool_use", "name": "Read", "input": {"file_path": "/src/a.js"}},
            ]},
        }))
        processor.process_line(json.dumps({
            "type": "assistant",
            "message": {"content": [
                {"type": "tool_use", "name": "Glob", "input": {"pattern": "*.js"}},
            ]},
        }))
        assert processor.tools_used == {"Read", "Glob"}

    def test_ignores_non_tool_use_content(self):
        processor = StreamProcessor(target_skill="x")
        line = json.dumps({
            "type": "assistant",
            "message": {"content": [
                {"type": "text", "text": "Hello"},
            ]},
        })
        processor.process_line(line)
        assert processor.tools_used == set()
        assert processor.files_modified == []

    def test_ignores_write_without_file_path(self):
        processor = StreamProcessor(target_skill="x")
        line = json.dumps({
            "type": "assistant",
            "message": {"content": [
                {"type": "tool_use", "name": "Write", "input": {}},
            ]},
        })
        processor.process_line(line)
        assert processor.files_modified == []


# --- StreamProcessor: result event ---


class TestStreamProcessorResult:
    def test_returns_true_on_result_event(self):
        processor = StreamProcessor(target_skill="x")
        line = json.dumps({"type": "result", "result": "done"})
        assert processor.process_line(line) is True

    def test_result_accessible_via_build_output(self):
        processor = StreamProcessor(target_skill="x")
        processor.process_line(json.dumps({"type": "result", "result": "output text"}))
        assert processor.build_output()["result"] == "output text"

    def test_returns_false_for_non_result_events(self):
        processor = StreamProcessor(target_skill="x")
        assert processor.process_line(json.dumps({"type": "assistant", "message": {"content": []}})) is False
        assert processor.process_line(json.dumps({"type": "system", "subtype": "init", "skills": []})) is False


# --- StreamProcessor: edge cases ---


class TestStreamProcessorEdgeCases:
    def test_handles_empty_line(self):
        processor = StreamProcessor(target_skill="x")
        assert processor.process_line("") is False
        assert processor.process_line("   ") is False

    def test_handles_invalid_json(self):
        processor = StreamProcessor(target_skill="x")
        assert processor.process_line("not json") is False
        assert processor.process_line("{broken") is False

    def test_handles_event_with_missing_type(self):
        processor = StreamProcessor(target_skill="x")
        assert processor.process_line(json.dumps({"data": "something"})) is False

    def test_handles_assistant_with_missing_message(self):
        processor = StreamProcessor(target_skill="x")
        processor.process_line(json.dumps({"type": "assistant"}))
        assert processor.tools_used == set()

    def test_handles_assistant_with_empty_content(self):
        processor = StreamProcessor(target_skill="x")
        processor.process_line(json.dumps({"type": "assistant", "message": {"content": []}}))
        assert processor.tools_used == set()


# --- StreamProcessor: build_output ---


class TestStreamProcessorBuildOutput:
    def test_output_with_full_session(self):
        processor = StreamProcessor(target_skill="my-skill")
        processor.process_line(json.dumps({
            "type": "system", "subtype": "init", "skills": ["my-skill"],
        }))
        processor.process_line(json.dumps({
            "type": "assistant",
            "message": {"content": [
                {"type": "tool_use", "name": "Skill", "input": {"skill": "my-skill"}},
                {"type": "tool_use", "name": "Edit", "input": {"file_path": "/src/a.js"}},
            ]},
        }))
        processor.process_line(json.dumps({"type": "result", "result": "task complete"}))

        output = processor.build_output()
        assert output["result"] == "task complete"
        assert output["skill_discovered"] is True
        assert output["skill_invoked"] is True
        assert output["skill_used"] is True
        assert output["skill_usage_evidence"] == [{"method": "Skill", "value": "my-skill"}]
        assert output["namespaced_skill_discoveries"] == []
        assert output["namespaced_skill_invocations"] == []
        assert output["files_modified"] == []
        assert output["tools_used"] == ["Edit", "Skill"]

    def test_output_without_result(self):
        processor = StreamProcessor(target_skill="x")
        output = processor.build_output()
        assert output["result"] == ""
        assert output["skill_discovered"] is False
        assert output["skill_invoked"] is False
        assert output["skill_used"] is False
        assert output["skill_usage_evidence"] == []
        assert output["namespaced_skill_discoveries"] == []
        assert output["namespaced_skill_invocations"] == []
        assert output["files_modified"] == []
        assert output["tools_used"] == []


# --- _error_output ---


class TestErrorOutput:
    def test_returns_complete_error_structure(self):
        result = _error_output(127, "error", "CLI not found")
        assert result["result"] == ""
        assert result["exit_code"] == 127
        assert result["status"] == "error"
        assert result["error"] == "CLI not found"
        assert result["skill_discovered"] is False
        assert result["skill_invoked"] is False
        assert result["skill_used"] is False
        assert result["skill_usage_evidence"] == []
        assert result["namespaced_skill_discoveries"] == []
        assert result["namespaced_skill_invocations"] == []
        assert result["skill_environment"] is None
        assert result["base_sha"] == ""
        assert result["files_modified"] == []
        assert result["tools_used"] == []


# --- execute: subprocess mocking ---


class TestExecute:
    def _make_mock_process(self, stdout_lines, returncode=0, stderr=""):
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("".join(stdout_lines), stderr)
        mock_process.returncode = returncode
        return mock_process

    def _execute(self, prompt, tmpdir, skill_name, allowed_tools, **kwargs):
        skill_dir = Path(tmpdir) / ".claude" / "skills" / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(f"---\nname: {skill_name}\n---\n")
        fingerprint = skill_directory_fingerprint(str(skill_dir))
        return execute(
            prompt,
            tmpdir,
            skill_name,
            allowed_tools,
            expected_skill_dir=str(skill_dir),
            expected_skill_fingerprint=fingerprint,
            **kwargs,
        )

    def test_success_with_result(self):
        stdout = [
            json.dumps({"type": "system", "subtype": "init", "skills": ["my-skill"]}) + "\n",
            json.dumps({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Skill", "input": {"skill": "my-skill"}},
            ]}}) + "\n",
            json.dumps({"type": "result", "result": "done"}) + "\n",
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=self._make_mock_process(stdout)):
                result = self._execute("test prompt", tmpdir, "my-skill", "Read,Skill")

        assert result["status"] == "success"
        assert result["result"] == "done"
        assert result["skill_discovered"] is True
        assert result["skill_invoked"] is True
        assert result["skill_environment"]["valid"] is True
        assert result["base_sha"] == "abc123"

    def test_namespaced_invocation_invalidates_project_skill_run(self):
        stdout = [
            json.dumps({"type": "system", "subtype": "init", "skills": ["x", "plugin:x"]}) + "\n",
            json.dumps({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Skill", "input": {"skill": "plugin:x"}},
            ]}}) + "\n",
            json.dumps({"type": "result", "result": "done"}) + "\n",
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=self._make_mock_process(stdout)):
                result = self._execute("prompt", tmpdir, "x", "Read,Skill")

        assert result["status"] == "partial"
        assert result["skill_used"] is False
        assert result["skill_environment"]["valid"] is False
        assert result["namespaced_skill_invocations"] == ["plugin:x"]

    def test_error_when_no_result_and_nonzero_exit(self):
        stdout = [json.dumps({"type": "system", "subtype": "init", "skills": []}) + "\n"]
        mock = self._make_mock_process(stdout, returncode=1, stderr="something failed")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=mock):
                result = self._execute("prompt", tmpdir, "x", "Read")

        assert result["status"] == "error"
        assert result["exit_code"] == 1
        assert "something failed" in result["error"]

    def test_error_with_empty_stderr(self):
        stdout = [json.dumps({"type": "system", "subtype": "init", "skills": []}) + "\n"]
        mock = self._make_mock_process(stdout, returncode=1, stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=mock):
                result = self._execute("prompt", tmpdir, "x", "Read")

        assert result["status"] == "error"
        assert result["error"] == "CLI exited with code 1"

    def test_none_returncode_treated_as_zero(self):
        stdout = [json.dumps({"type": "result", "result": "done"}) + "\n"]
        mock = self._make_mock_process(stdout)
        mock.returncode = None

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=mock):
                result = self._execute("prompt", tmpdir, "x", "Read")

        assert result["status"] == "success"
        assert result["exit_code"] == 0

    def test_partial_when_result_exists_but_nonzero_exit(self):
        stdout = [json.dumps({"type": "result", "result": "partial output"}) + "\n"]
        mock = self._make_mock_process(stdout, returncode=2)

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=mock):
                result = self._execute("prompt", tmpdir, "x", "Read")

        assert result["status"] == "partial"
        assert result["result"] == "partial output"
        assert "error" in result

    def test_timeout_handling(self):
        mock_process = MagicMock()
        mock_process.stdout.readline.side_effect = [""]
        mock_process.communicate = MagicMock(
            side_effect=[subprocess.TimeoutExpired("claude", 5), ("", "")]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=mock_process):
                result = self._execute(
                    "prompt", tmpdir, "x", "Read", timeout_ms=5000
                )

        assert result["status"] == "error"
        assert result["exit_code"] == 124
        assert "Timeout" in result["error"]
        mock_process.kill.assert_called_once()

    def test_cli_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", side_effect=FileNotFoundError()):
                result = self._execute("prompt", tmpdir, "x", "Read")

        assert result["status"] == "error"
        assert result["exit_code"] == 127
        assert "CLI not found" in result["error"]

    def test_generic_exception_handling(self):
        mock_process = MagicMock()
        mock_process.communicate.side_effect = [RuntimeError("unexpected"), ("", "")]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=mock_process):
                result = self._execute("prompt", tmpdir, "x", "Read")

        assert result["status"] == "error"
        assert result["exit_code"] == 1
        assert "unexpected" in result["error"]

    def test_constructs_correct_cli_arguments(self):
        stdout = [json.dumps({"type": "result", "result": ""}) + "\n"]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=self._make_mock_process(stdout)) as mock_popen:
                self._execute("my prompt", tmpdir, "test-skill", "Read,Write")

            assert mock_popen.call_args[0][0] == [
                "claude",
                "-p",
                "my prompt",
                "--output-format",
                "stream-json",
                "--verbose",
                "--setting-sources",
                "project,local",
                "--allowedTools",
                "Read,Write",
            ]
            assert mock_popen.call_args.kwargs["env"]["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1"

    def test_omits_allowed_tools_when_empty(self):
        stdout = [json.dumps({"type": "result", "result": ""}) + "\n"]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=self._make_mock_process(stdout)) as mock_popen:
                self._execute("prompt", tmpdir, "x", "")

            call_args = mock_popen.call_args[0][0]
            assert "--allowedTools" not in call_args

    def test_rejects_wrong_expected_fingerprint_before_launch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / ".claude" / "skills" / "x"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: x\n---\n")
            with patch("subprocess.Popen") as mock_popen:
                result = execute(
                    "prompt",
                    tmpdir,
                    "x",
                    "Read",
                    expected_skill_dir=str(skill_dir),
                    expected_skill_fingerprint="0" * 64,
                )

        assert result["status"] == "error"
        assert result["skill_environment"]["valid"] is False
        mock_popen.assert_not_called()

    def test_rejects_competing_same_named_skill_before_launch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            expected = Path(tmpdir) / ".claude" / "skills" / "x"
            competing = Path(tmpdir) / "skills" / "x"
            for skill_dir in (expected, competing):
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text("---\nname: x\n---\n")
            fingerprint = skill_directory_fingerprint(str(expected))
            with patch("subprocess.Popen") as mock_popen:
                result = execute(
                    "prompt",
                    tmpdir,
                    "x",
                    "Read",
                    expected_skill_dir=str(expected),
                    expected_skill_fingerprint=fingerprint,
                )

        assert result["status"] == "error"
        assert result["skill_environment"]["competing_paths"] == [
            os.path.realpath(competing)
        ]
        mock_popen.assert_not_called()


class TestGitChangeComparison:
    def test_reports_new_removed_and_changed_entries(self):
        before = {
            "head": "a",
            "entries": {
                "changed.txt": (("worktree",), "old"),
                "removed.txt": (("untracked",), "old"),
            },
        }
        after = {
            "head": "a",
            "entries": {
                "changed.txt": (("worktree",), "new"),
                "new.txt": (("untracked",), "new"),
            },
        }

        assert _git_changes("/repo", before, after) == [
            "changed.txt",
            "new.txt",
            "removed.txt",
        ]

    def test_snapshot_detects_net_change_from_any_writer(self, tmp_path):
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        target = tmp_path / "artifact.txt"

        before = _git_snapshot(str(tmp_path))
        target.write_text("created by an arbitrary tool")
        after = _git_snapshot(str(tmp_path))

        assert _git_changes(str(tmp_path), before, after) == ["artifact.txt"]


class TestSkillDirectoryFingerprint:
    def test_changes_for_reference_content(self, tmp_path):
        skill_dir = tmp_path / "skill"
        references = skill_dir / "references"
        references.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: x\n---\n")
        reference = references / "rules.md"
        reference.write_text("old")

        original = skill_directory_fingerprint(str(skill_dir))
        reference.write_text("new")
        changed_content = skill_directory_fingerprint(str(skill_dir))

        assert original != changed_content

    def test_environment_becomes_invalid_if_skill_changes(self, tmp_path):
        skill_dir = tmp_path / ".claude" / "skills" / "x"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: x\n---\n")
        fingerprint = skill_directory_fingerprint(str(skill_dir))

        before = _skill_environment_before(
            str(tmp_path), "x", str(skill_dir), fingerprint, False
        )
        skill_file.write_text("---\nname: x\n---\nchanged")
        after = _skill_environment_after(before, str(tmp_path), "x")

        assert before["valid"] is True
        assert after["valid"] is False
        assert after["actual_fingerprint_after"] != fingerprint
