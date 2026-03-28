#!/usr/bin/env python3
"""
eval-executor.py - Execute a prompt via claude -p and capture skill usage metadata.

Parses stream-json output to detect skill discovery/invocation separately from
task result text.

Output JSON:
  result           - Final text output
  status           - "success" | "partial" | "error"
  exit_code        - Process exit code
  skill_discovered - Target skill appeared in init skills list
  skill_invoked    - Skill tool was called with target skill name
  files_modified   - File paths passed to Write, Edit, or MultiEdit
  tools_used       - Deduplicated tool names used during execution
  error            - Error message (only on error)

Usage:
    eval-executor.py --prompt "<task>" --cwd <path> --skill-name <name> [options]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

DEFAULT_TOOLS = ",".join([
    "Read", "Write", "Edit", "MultiEdit", "Bash",
    "Glob", "Grep", "Skill", "WebSearch", "WebFetch",
    "NotebookEdit", "ToolSearch",
])


class StreamProcessor:
    """Parse stream-json events from claude CLI."""

    def __init__(self, target_skill: str):
        self.target_skill = target_skill
        self.result_json = None
        self.skill_discovered = False
        self.skill_invoked = False
        self.files_modified: list[str] = []
        self.tools_used: set[str] = set()

    def process_line(self, line: str) -> bool:
        """Process one line. Returns True when result event is found."""
        line = line.strip()
        if not line:
            return False

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return False

        event_type = data.get("type", "")

        if event_type == "system" and data.get("subtype") == "init":
            self.skill_discovered = self.target_skill in data.get("skills", [])

        elif event_type == "assistant":
            self._process_assistant(data)

        elif event_type == "result":
            self.result_json = data
            return True

        return False

    def _process_assistant(self, data: dict) -> None:
        for block in data.get("message", {}).get("content", []):
            if block.get("type") != "tool_use":
                continue

            tool_name = block.get("name", "")
            tool_input = block.get("input", {})
            self.tools_used.add(tool_name)

            if tool_name == "Skill":
                if tool_input.get("skill", "") == self.target_skill:
                    self.skill_invoked = True

            elif tool_name in ("Write", "Edit", "MultiEdit"):
                path = tool_input.get("file_path", "")
                if path and path not in self.files_modified:
                    self.files_modified.append(path)

    def build_output(self) -> dict:
        return {
            "result": self.result_json.get("result", "") if self.result_json else "",
            "skill_discovered": self.skill_discovered,
            "skill_invoked": self.skill_invoked,
            "files_modified": self.files_modified,
            "tools_used": sorted(self.tools_used),
        }


def _error_output(exit_code: int, status: str, error: str) -> dict:
    return {
        "result": "", "exit_code": exit_code, "status": status,
        "skill_discovered": False, "skill_invoked": False,
        "files_modified": [], "tools_used": [],
        "error": error,
    }


def execute(
    prompt: str, cwd: str, skill_name: str,
    allowed_tools: str, timeout_ms: int = 600000,
) -> dict:
    args = [
        "claude",
        "--output-format", "stream-json",
        "--verbose",
        "-p", prompt,
    ]
    if allowed_tools:
        args.extend(["--allowedTools", allowed_tools])

    timeout_sec = timeout_ms / 1000
    processor = StreamProcessor(target_skill=skill_name)

    try:
        process = subprocess.Popen(
            args, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )
    except FileNotFoundError:
        return _error_output(127, "error", "CLI not found: claude")

    try:
        for line in iter(process.stdout.readline, ""):
            if processor.process_line(line):
                process.terminate()
                break

        try:
            _, stderr = process.communicate(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            output = processor.build_output()
            output["exit_code"] = 124
            output["status"] = "partial" if processor.result_json else "error"
            output["error"] = f"Timeout after {timeout_ms}ms"
            return output

        exit_code = process.returncode or 0
        # 143/-15 = SIGTERM from process.terminate() after getting result
        if exit_code == 0 or (exit_code in (143, -15) and processor.result_json):
            status = "success"
        elif processor.result_json:
            status = "partial"
        else:
            status = "error"

        output = processor.build_output()
        output["exit_code"] = exit_code
        output["status"] = status
        if status in ("error", "partial"):
            msg = f"CLI exited with code {exit_code}"
            if stderr and stderr.strip():
                msg += f": {stderr.strip()}"
            output["error"] = msg
        return output

    except Exception as e:
        process.kill()
        process.communicate()
        output = processor.build_output()
        output["exit_code"] = 1
        output["status"] = "error"
        output["error"] = str(e)
        return output


def main():
    parser = argparse.ArgumentParser(description="Execute prompt via claude -p with skill tracking")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--cwd", required=True, help="Absolute path to working directory")
    parser.add_argument("--skill-name", required=True, help="Target skill name to track")
    parser.add_argument("--allowed-tools", default=DEFAULT_TOOLS)
    parser.add_argument("--timeout", type=int, default=600000, help="Timeout in ms")

    args = parser.parse_args()

    if not os.path.isabs(args.cwd):
        print(json.dumps(_error_output(1, "error", "cwd must be absolute")))
        sys.exit(1)

    if not os.path.isdir(args.cwd):
        print(json.dumps(_error_output(1, "error", f"cwd does not exist: {args.cwd}")))
        sys.exit(1)

    result = execute(
        prompt=args.prompt, cwd=args.cwd, skill_name=args.skill_name,
        allowed_tools=args.allowed_tools, timeout_ms=args.timeout,
    )
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
