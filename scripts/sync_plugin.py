#!/usr/bin/env python3
"""Sync canonical skills into the Codex plugin directory."""

from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_SKILLS_DIR = REPO_ROOT / "skills"
PLUGIN_SKILLS_DIR = REPO_ROOT / "plugins" / "rashomon" / "skills"

SKILLS = [
    "prompt-optimization",
]


def compare_dirs(left: Path, right: Path) -> list[str]:
    comparison = filecmp.dircmp(left, right)
    differences: list[str] = []

    for name in comparison.left_only:
        differences.append(f"missing from plugin copy: {left / name}")
    for name in comparison.right_only:
        differences.append(f"extra in plugin copy: {right / name}")
    for name in comparison.diff_files:
        differences.append(f"content differs: {left / name}")

    for subdir in comparison.common_dirs:
        differences.extend(compare_dirs(left / subdir, right / subdir))

    return differences


def sync() -> None:
    for skill_name in SKILLS:
        canonical = CANONICAL_SKILLS_DIR / skill_name
        plugin_copy = PLUGIN_SKILLS_DIR / skill_name

        if not canonical.is_dir():
            raise SystemExit(f"canonical skill not found: {canonical}")

        if plugin_copy.exists():
            shutil.rmtree(plugin_copy)

        plugin_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(canonical, plugin_copy)


def check() -> None:
    differences: list[str] = []

    for skill_name in SKILLS:
        canonical = CANONICAL_SKILLS_DIR / skill_name
        plugin_copy = PLUGIN_SKILLS_DIR / skill_name

        if not canonical.is_dir():
            raise SystemExit(f"canonical skill not found: {canonical}")
        if not plugin_copy.is_dir():
            differences.append(f"plugin skill copy not found: {plugin_copy}")
            continue

        differences.extend(compare_dirs(canonical, plugin_copy))

    if differences:
        for difference in differences:
            print(difference)
        raise SystemExit("plugin skill copy is out of sync; run scripts/sync_plugin.py")

    print("Plugin skill copy is in sync.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="check for drift without writing")
    args = parser.parse_args()

    if args.check:
        check()
    else:
        sync()


if __name__ == "__main__":
    main()
