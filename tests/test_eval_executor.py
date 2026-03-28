#!/usr/bin/env python3
"""Tests for eval-executor.py"""

import importlib.util
import json
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
        assert "Skill" in processor.tools_used

    def test_ignores_skill_invocation_for_different_skill(self):
        processor = StreamProcessor(target_skill="error-handling")
        line = json.dumps({
            "type": "assistant",
            "message": {"content": [
                {"type": "tool_use", "name": "Skill", "input": {"skill": "other-skill"}},
            ]},
        })
        processor.process_line(line)
        assert processor.skill_invoked is False
        assert "Skill" in processor.tools_used

    @pytest.mark.parametrize("tool_name", ["Write", "Edit", "MultiEdit"])
    def test_tracks_file_modifications(self, tool_name):
        processor = StreamProcessor(target_skill="x")
        line = json.dumps({
            "type": "assistant",
            "message": {"content": [
                {"type": "tool_use", "name": tool_name, "input": {"file_path": "/src/a.js"}},
            ]},
        })
        processor.process_line(line)
        assert processor.files_modified == ["/src/a.js"]

    def test_deduplicates_file_modifications(self):
        processor = StreamProcessor(target_skill="x")
        for _ in range(3):
            line = json.dumps({
                "type": "assistant",
                "message": {"content": [
                    {"type": "tool_use", "name": "Edit", "input": {"file_path": "/src/a.js"}},
                ]},
            })
            processor.process_line(line)
        assert processor.files_modified == ["/src/a.js"]

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
        assert output["files_modified"] == ["/src/a.js"]
        assert output["tools_used"] == ["Edit", "Skill"]

    def test_output_without_result(self):
        processor = StreamProcessor(target_skill="x")
        output = processor.build_output()
        assert output["result"] == ""
        assert output["skill_discovered"] is False
        assert output["skill_invoked"] is False
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
        assert result["files_modified"] == []
        assert result["tools_used"] == []


# --- execute: subprocess mocking ---


class TestExecute:
    def _make_mock_process(self, stdout_lines, returncode=0, stderr=""):
        mock_process = MagicMock()
        mock_process.stdout.readline.side_effect = stdout_lines + [""]
        mock_process.communicate.return_value = ("", stderr)
        mock_process.returncode = returncode
        return mock_process

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
                result = execute("test prompt", tmpdir, "my-skill", "Read,Skill")

        assert result["status"] == "success"
        assert result["result"] == "done"
        assert result["skill_discovered"] is True
        assert result["skill_invoked"] is True

    def test_sigterm_exit_code_treated_as_success(self):
        stdout = [json.dumps({"type": "result", "result": "done"}) + "\n"]
        mock = self._make_mock_process(stdout, returncode=143)

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=mock):
                result = execute("prompt", tmpdir, "x", "Read")

        assert result["status"] == "success"

    def test_negative_sigterm_exit_code_treated_as_success(self):
        stdout = [json.dumps({"type": "result", "result": "done"}) + "\n"]
        mock = self._make_mock_process(stdout, returncode=-15)

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=mock):
                result = execute("prompt", tmpdir, "x", "Read")

        assert result["status"] == "success"

    def test_error_when_no_result_and_nonzero_exit(self):
        stdout = [json.dumps({"type": "system", "subtype": "init", "skills": []}) + "\n"]
        mock = self._make_mock_process(stdout, returncode=1, stderr="something failed")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=mock):
                result = execute("prompt", tmpdir, "x", "Read")

        assert result["status"] == "error"
        assert result["exit_code"] == 1
        assert "something failed" in result["error"]

    def test_error_with_empty_stderr(self):
        stdout = [json.dumps({"type": "system", "subtype": "init", "skills": []}) + "\n"]
        mock = self._make_mock_process(stdout, returncode=1, stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=mock):
                result = execute("prompt", tmpdir, "x", "Read")

        assert result["status"] == "error"
        assert result["error"] == "CLI exited with code 1"

    def test_none_returncode_treated_as_zero(self):
        stdout = [json.dumps({"type": "result", "result": "done"}) + "\n"]
        mock = self._make_mock_process(stdout)
        mock.returncode = None

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=mock):
                result = execute("prompt", tmpdir, "x", "Read")

        assert result["status"] == "success"
        assert result["exit_code"] == 0

    def test_partial_when_result_exists_but_nonzero_exit(self):
        stdout = [json.dumps({"type": "result", "result": "partial output"}) + "\n"]
        mock = self._make_mock_process(stdout, returncode=2)

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=mock):
                result = execute("prompt", tmpdir, "x", "Read")

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
                result = execute("prompt", tmpdir, "x", "Read", timeout_ms=5000)

        assert result["status"] == "error"
        assert result["exit_code"] == 124
        assert "Timeout" in result["error"]
        mock_process.kill.assert_called_once()

    def test_cli_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", side_effect=FileNotFoundError()):
                result = execute("prompt", tmpdir, "x", "Read")

        assert result["status"] == "error"
        assert result["exit_code"] == 127
        assert "CLI not found" in result["error"]

    def test_generic_exception_handling(self):
        mock_process = MagicMock()
        mock_process.stdout.readline.side_effect = RuntimeError("unexpected")
        mock_process.communicate.return_value = ("", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=mock_process):
                result = execute("prompt", tmpdir, "x", "Read")

        assert result["status"] == "error"
        assert result["exit_code"] == 1
        assert "unexpected" in result["error"]

    def test_constructs_correct_cli_arguments(self):
        stdout = [json.dumps({"type": "result", "result": ""}) + "\n"]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=self._make_mock_process(stdout)) as mock_popen:
                execute("my prompt", tmpdir, "test-skill", "Read,Write")

            call_args = mock_popen.call_args[0][0]
            assert call_args[0] == "claude"
            assert "--output-format" in call_args
            assert "stream-json" in call_args
            assert "--verbose" in call_args
            assert "-p" in call_args
            assert "my prompt" in call_args
            assert "--allowedTools" in call_args
            assert "Read,Write" in call_args

    def test_omits_allowed_tools_when_empty(self):
        stdout = [json.dumps({"type": "result", "result": ""}) + "\n"]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.Popen", return_value=self._make_mock_process(stdout)) as mock_popen:
                execute("prompt", tmpdir, "x", "")

            call_args = mock_popen.call_args[0][0]
            assert "--allowedTools" not in call_args
