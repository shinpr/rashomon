#!/usr/bin/env python3
"""
eval-executor.py - Execute a prompt via claude -p and capture skill usage metadata.

Parses stream-json output to detect skill discovery and use separately from task
result text. Skill use includes either the Skill tool or a direct target
SKILL.md Read.

Output JSON:
  result           - Final text output
  status           - "success" | "partial" | "error"
  exit_code        - Process exit code
  skill_discovered - Exact project skill name appeared in init skills list
  skill_invoked    - Skill tool was called with the exact project skill name
  skill_used       - Skill tool call or direct target SKILL.md Read observed
  skill_usage_evidence - Events that established skill use
  namespaced_skill_discoveries - Same short name discovered from a plugin
  namespaced_skill_invocations - Same short name invoked from a plugin
  files_modified   - Net file changes observed from git state and HEAD
  tools_used       - Deduplicated tool names used during execution
  error            - Error message (only on error)

Usage:
    eval-executor.py --fingerprint-skill-dir <path>
    eval-executor.py --prompt "<task>" --cwd <path> --skill-name <name>
      (--expected-skill-dir <path> --expected-skill-fingerprint <sha256>
       | --expect-skill-absent) [options]
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

DEFAULT_TOOLS = ",".join([
    "Read", "Write", "Edit", "MultiEdit", "Bash",
    "Glob", "Grep", "Skill", "WebSearch", "WebFetch",
    "NotebookEdit", "ToolSearch",
])


class StreamProcessor:
    """Parse stream-json events from claude CLI."""

    def __init__(
        self,
        target_skill: str,
        cwd: str | None = None,
        expected_skill_path: str | None = None,
    ):
        self.target_skill = target_skill
        self.cwd = os.path.realpath(cwd or os.getcwd())
        self.expected_skill_path = (
            _resolve_tool_path(expected_skill_path, self.cwd)
            if expected_skill_path
            else None
        )
        self.result_json = None
        self.skill_discovered = False
        self.skill_invoked = False
        self.skill_usage_evidence: list[dict[str, str]] = []
        self.namespaced_skill_discoveries: list[str] = []
        self.namespaced_skill_invocations: list[str] = []
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
            skills = data.get("skills", [])
            self.skill_discovered = any(skill == self.target_skill for skill in skills)
            for skill in skills:
                if (
                    isinstance(skill, str)
                    and skill != self.target_skill
                    and skill.endswith(f":{self.target_skill}")
                    and skill not in self.namespaced_skill_discoveries
                ):
                    self.namespaced_skill_discoveries.append(skill)

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
                skill = tool_input.get("skill", "")
                if skill == self.target_skill:
                    self.skill_invoked = True
                    self._record_skill_usage("Skill", skill)
                elif (
                    isinstance(skill, str)
                    and skill.endswith(f":{self.target_skill}")
                    and skill not in self.namespaced_skill_invocations
                ):
                    self.namespaced_skill_invocations.append(skill)

            elif tool_name == "Read":
                path = tool_input.get("file_path", "")
                resolved_path = _resolve_tool_path(path, self.cwd)
                if self.expected_skill_path and resolved_path == self.expected_skill_path:
                    self._record_skill_usage("Read", resolved_path)

    def _record_skill_usage(self, method: str, value: str) -> None:
        evidence = {"method": method, "value": value}
        if evidence not in self.skill_usage_evidence:
            self.skill_usage_evidence.append(evidence)

    def build_output(
        self,
        skill_environment: dict | None = None,
        base_sha: str = "",
    ) -> dict:
        environment_valid = (
            skill_environment is None or skill_environment.get("valid", False)
        )
        return {
            "result": self.result_json.get("result", "") if self.result_json else "",
            "skill_discovered": self.skill_discovered,
            "skill_invoked": self.skill_invoked,
            "skill_used": bool(self.skill_usage_evidence) and environment_valid,
            "skill_usage_evidence": self.skill_usage_evidence,
            "namespaced_skill_discoveries": self.namespaced_skill_discoveries,
            "namespaced_skill_invocations": self.namespaced_skill_invocations,
            "skill_environment": skill_environment,
            "base_sha": base_sha,
            "files_modified": self.files_modified,
            "tools_used": sorted(self.tools_used),
        }


def _error_output(exit_code: int, status: str, error: str) -> dict:
    return {
        "result": "", "exit_code": exit_code, "status": status,
        "skill_discovered": False, "skill_invoked": False,
        "skill_used": False, "skill_usage_evidence": [],
        "namespaced_skill_discoveries": [], "namespaced_skill_invocations": [],
        "skill_environment": None, "base_sha": "",
        "files_modified": [], "tools_used": [],
        "error": error,
    }


def _resolve_tool_path(path: str, cwd: str) -> str:
    expanded = os.path.expanduser(path)
    if not os.path.isabs(expanded):
        expanded = os.path.join(cwd, expanded)
    return os.path.realpath(expanded)


def _git_paths(cwd: str, args: list[str]) -> set[str]:
    completed = subprocess.run(
        ["git", "-C", cwd, *args],
        capture_output=True,
        text=False,
        check=False,
    )
    if completed.returncode != 0:
        return set()
    return {
        value.decode("utf-8", errors="surrogateescape")
        for value in completed.stdout.split(b"\0")
        if value
    }


def _fingerprint(path: str) -> str:
    if os.path.islink(path):
        return f"link:{os.readlink(path)}"
    if not os.path.exists(path):
        return "missing"
    if not os.path.isfile(path):
        return "non-file"

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def skill_directory_fingerprint(directory: str) -> str:
    """Return a stable fingerprint for paths, modes, symlinks, and file content."""
    root = Path(directory).expanduser().resolve()
    if not root.is_dir() or not (root / "SKILL.md").is_file():
        raise ValueError(f"Not a skill directory: {directory}")

    digest = hashlib.sha256()
    for current_root, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        filenames.sort()
        current = Path(current_root)
        for name in [*dirnames, *filenames]:
            path = current / name
            relative = path.relative_to(root).as_posix()
            metadata = path.lstat()
            mode = stat.S_IMODE(metadata.st_mode)

            if path.is_symlink():
                kind = "link"
                payload = os.readlink(path).encode()
            elif path.is_dir():
                kind = "directory"
                payload = b""
            elif path.is_file():
                kind = "file"
                payload = _fingerprint(str(path)).encode()
            else:
                kind = "other"
                payload = b""

            digest.update(f"{kind}\0{mode:o}\0{relative}\0".encode())
            digest.update(payload)
            digest.update(b"\0")
    return digest.hexdigest()


def _known_skill_directories(cwd: str, skill_name: str) -> list[str]:
    root = Path(cwd).resolve()
    candidates: set[str] = set()
    search_roots = [
        root / ".claude",
        root / "skills",
        root / "plugins",
    ]
    for search_root in search_roots:
        if not search_root.exists():
            continue
        for skill_file in search_root.rglob("SKILL.md"):
            skill_dir = skill_file.parent
            if skill_dir.name == skill_name and skill_dir.parent.name == "skills":
                candidates.add(os.path.realpath(skill_dir))
    return sorted(candidates)


def _skill_environment_before(
    cwd: str,
    skill_name: str,
    expected_skill_dir: str | None,
    expected_fingerprint: str | None,
    expect_skill_absent: bool,
) -> dict:
    known = _known_skill_directories(cwd, skill_name)
    if expect_skill_absent:
        return {
            "mode": "absent",
            "expected_path": None,
            "expected_fingerprint": None,
            "actual_fingerprint_before": None,
            "actual_fingerprint_after": None,
            "competing_paths": known,
            "valid": not known,
        }

    expected_path = os.path.realpath(expected_skill_dir or "")
    required_path = os.path.realpath(
        os.path.join(cwd, ".claude", "skills", skill_name)
    )
    actual = None
    with contextlib.suppress(OSError, ValueError):
        actual = skill_directory_fingerprint(expected_path)
    competing = [path for path in known if path != expected_path]
    return {
        "mode": "expected",
        "expected_path": expected_path,
        "required_path": required_path,
        "expected_fingerprint": expected_fingerprint,
        "actual_fingerprint_before": actual,
        "actual_fingerprint_after": None,
        "competing_paths": competing,
        "valid": bool(expected_fingerprint)
        and expected_path == required_path
        and actual == expected_fingerprint
        and not competing,
    }


def _skill_environment_after(
    before: dict,
    cwd: str,
    skill_name: str,
) -> dict:
    environment = dict(before)
    known = _known_skill_directories(cwd, skill_name)
    if before["mode"] == "absent":
        environment["competing_paths"] = known
        environment["valid"] = before["valid"] and not known
        return environment

    expected_path = before["expected_path"]
    actual = None
    with contextlib.suppress(OSError, ValueError):
        actual = skill_directory_fingerprint(expected_path)
    competing = [path for path in known if path != expected_path]
    environment["actual_fingerprint_after"] = actual
    environment["competing_paths"] = sorted(
        set(before["competing_paths"]) | set(competing)
    )
    environment["valid"] = (
        before["valid"]
        and actual == before["expected_fingerprint"]
        and not environment["competing_paths"]
    )
    return environment


def _git_snapshot(cwd: str) -> dict:
    head = subprocess.run(
        ["git", "-C", cwd, "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    head_value = head.stdout.strip() if head.returncode == 0 else ""

    groups = {
        "worktree": _git_paths(cwd, ["diff", "--name-only", "-z", "--no-renames"]),
        "index": _git_paths(cwd, ["diff", "--cached", "--name-only", "-z", "--no-renames"]),
        "untracked": _git_paths(cwd, ["ls-files", "--others", "--exclude-standard", "-z"]),
    }
    paths = set().union(*groups.values())
    entries = {}
    for path in paths:
        categories = tuple(name for name, values in groups.items() if path in values)
        entries[path] = (categories, _fingerprint(os.path.join(cwd, path)))
    return {"head": head_value, "entries": entries}


def _git_changes(cwd: str, before: dict, after: dict) -> list[str]:
    before_entries = before.get("entries", {})
    after_entries = after.get("entries", {})
    changed = {
        path
        for path in before_entries.keys() | after_entries.keys()
        if before_entries.get(path) != after_entries.get(path)
    }

    before_head = before.get("head", "")
    after_head = after.get("head", "")
    if before_head and after_head and before_head != after_head:
        changed.update(
            _git_paths(cwd, ["diff", "--name-only", "-z", "--no-renames", before_head, after_head])
        )
    return sorted(changed)


def _process_output(stdout: str, processor: StreamProcessor) -> None:
    for line in stdout.splitlines():
        processor.process_line(line)


def _finish_output(
    processor: StreamProcessor, cwd: str, before: dict,
    skill_environment_before: dict,
    exit_code: int, status: str, error: str | None = None,
) -> dict:
    processor.files_modified = _git_changes(cwd, before, _git_snapshot(cwd))
    skill_environment = _skill_environment_after(
        skill_environment_before, cwd, processor.target_skill
    )
    if skill_environment["mode"] == "absent" and (
        processor.skill_discovered or processor.skill_usage_evidence
    ):
        skill_environment["valid"] = False
    if processor.namespaced_skill_invocations:
        skill_environment["valid"] = False
    if not skill_environment["valid"]:
        status = "partial" if processor.result_json else "error"
        environment_error = "Skill environment changed or violated the expected identity"
        error = f"{error}; {environment_error}" if error else environment_error
    output = processor.build_output(skill_environment, before.get("head", ""))
    output["exit_code"] = exit_code
    output["status"] = status
    if error:
        output["error"] = error
    return output


def execute(
    prompt: str, cwd: str, skill_name: str,
    allowed_tools: str, timeout_ms: int = 600000,
    expected_skill_dir: str | None = None,
    expected_skill_fingerprint: str | None = None,
    expect_skill_absent: bool = False,
) -> dict:
    args = [
        "claude",
        "-p", prompt,
        "--output-format", "stream-json",
        "--verbose",
        "--setting-sources", "project,local",
    ]
    if allowed_tools:
        args.extend(["--allowedTools", allowed_tools])
    process_env = os.environ.copy()
    process_env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"

    timeout_sec = timeout_ms / 1000
    before = _git_snapshot(cwd)
    skill_environment = _skill_environment_before(
        cwd,
        skill_name,
        expected_skill_dir,
        expected_skill_fingerprint,
        expect_skill_absent,
    )
    expected_skill_path = (
        os.path.join(skill_environment["expected_path"], "SKILL.md")
        if skill_environment["mode"] == "expected"
        else None
    )
    processor = StreamProcessor(
        target_skill=skill_name,
        cwd=cwd,
        expected_skill_path=expected_skill_path,
    )

    if not skill_environment["valid"]:
        output = processor.build_output(skill_environment, before.get("head", ""))
        output["exit_code"] = 2
        output["status"] = "error"
        output["error"] = "Skill environment validation failed before execution"
        return output

    try:
        process = subprocess.Popen(
            args, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, env=process_env,
        )
    except FileNotFoundError:
        return _error_output(127, "error", "CLI not found: claude")

    try:
        try:
            stdout, stderr = process.communicate(timeout=timeout_sec)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            remaining_stdout, _ = process.communicate()
            timeout_stdout = remaining_stdout or exc.stdout or ""
            if isinstance(timeout_stdout, bytes):
                timeout_stdout = timeout_stdout.decode(errors="replace")
            _process_output(timeout_stdout, processor)
            status = "partial" if processor.result_json else "error"
            return _finish_output(
                processor, cwd, before, skill_environment, 124, status,
                f"Timeout after {timeout_ms}ms",
            )

        _process_output(stdout, processor)
        exit_code = process.returncode or 0
        if (
            exit_code == 0
            and processor.result_json
            and not processor.result_json.get("is_error", False)
        ):
            status = "success"
        elif processor.result_json:
            status = "partial"
        else:
            status = "error"

        error = None
        if status in ("error", "partial"):
            error = f"CLI exited with code {exit_code}"
            if stderr and stderr.strip():
                error += f": {stderr.strip()}"
        return _finish_output(
            processor, cwd, before, skill_environment, exit_code, status, error
        )

    except Exception as e:
        process.kill()
        process.communicate()
        return _finish_output(
            processor, cwd, before, skill_environment, 1, "error", str(e)
        )


def main():
    parser = argparse.ArgumentParser(description="Execute prompt via claude -p with skill tracking")
    parser.add_argument("--prompt")
    parser.add_argument("--cwd", help="Absolute path to working directory")
    parser.add_argument("--skill-name", help="Target skill name to track")
    parser.add_argument("--allowed-tools", default=DEFAULT_TOOLS)
    parser.add_argument("--timeout", type=int, default=600000, help="Timeout in ms")
    parser.add_argument(
        "--expected-skill-dir",
        help="Absolute installed skill directory expected to be the only target copy",
    )
    parser.add_argument(
        "--expected-skill-fingerprint",
        help="Fingerprint recorded from the approved source or old snapshot",
    )
    parser.add_argument("--expect-skill-absent", action="store_true")
    parser.add_argument(
        "--fingerprint-skill-dir",
        help="Print a skill directory fingerprint and exit",
    )

    args = parser.parse_args()

    if args.fingerprint_skill_dir:
        try:
            fingerprint = skill_directory_fingerprint(args.fingerprint_skill_dir)
        except (OSError, ValueError) as exc:
            print(json.dumps({"error": str(exc)}))
            sys.exit(1)
        print(json.dumps({
            "path": os.path.realpath(args.fingerprint_skill_dir),
            "fingerprint": fingerprint,
        }))
        sys.exit(0)

    if not args.prompt or not args.cwd or not args.skill_name:
        parser.error("--prompt, --cwd, and --skill-name are required for execution")

    expected_mode = bool(args.expected_skill_dir or args.expected_skill_fingerprint)
    if expected_mode == args.expect_skill_absent:
        parser.error(
            "choose exactly one mode: expected skill dir+fingerprint or --expect-skill-absent"
        )
    if expected_mode and not (
        args.expected_skill_dir and args.expected_skill_fingerprint
    ):
        parser.error(
            "--expected-skill-dir and --expected-skill-fingerprint must be provided together"
        )

    if not os.path.isabs(args.cwd):
        print(json.dumps(_error_output(1, "error", "cwd must be absolute")))
        sys.exit(1)

    if not os.path.isdir(args.cwd):
        print(json.dumps(_error_output(1, "error", f"cwd does not exist: {args.cwd}")))
        sys.exit(1)

    result = execute(
        prompt=args.prompt, cwd=args.cwd, skill_name=args.skill_name,
        allowed_tools=args.allowed_tools, timeout_ms=args.timeout,
        expected_skill_dir=args.expected_skill_dir,
        expected_skill_fingerprint=args.expected_skill_fingerprint,
        expect_skill_absent=args.expect_skill_absent,
    )
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
