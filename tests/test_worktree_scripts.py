"""Integration tests for pinned worktree creation and lease recovery."""

import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
CREATE = ROOT / "skills" / "worktree-execution" / "scripts" / "worktree-create.sh"
CLEANUP = ROOT / "skills" / "worktree-execution" / "scripts" / "worktree-cleanup.sh"


def run(*args, env=None):
    return subprocess.run(
        [str(arg) for arg in args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def make_repo(path: Path) -> tuple[str, str]:
    run("git", "init", path)
    run("git", "-C", path, "config", "user.email", "rashomon@example.test")
    run("git", "-C", path, "config", "user.name", "Rashomon Test")
    tracked = path / "tracked.txt"
    tracked.write_text("base")
    run("git", "-C", path, "add", "tracked.txt")
    run("git", "-C", path, "commit", "-m", "base")
    base = run("git", "-C", path, "rev-parse", "HEAD").stdout.strip()
    tracked.write_text("later")
    run("git", "-C", path, "commit", "-am", "later")
    head = run("git", "-C", path, "rev-parse", "HEAD").stdout.strip()
    return base, head


def test_creation_pins_both_worktrees_and_records_lease(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base, head = make_repo(repo)
    assert base != head
    temp_root = tmp_path / "worktrees"
    temp_root.mkdir()
    env = os.environ | {
        "TMPDIR": str(temp_root),
        "RASHOMON_RUN_ID": "test-run",
        "RASHOMON_OWNER_PID": str(os.getpid()),
        "RASHOMON_LEASE_SECONDS": "600",
    }

    created = run(CREATE, repo, "left", "right", base, env=env)
    paths = [Path(line) for line in created.stdout.splitlines() if line]
    assert len(paths) == 2
    try:
        for path in paths:
            assert run("git", "-C", path, "rev-parse", "HEAD").stdout.strip() == base
        porcelain = run("git", "-C", repo, "worktree", "list", "--porcelain").stdout
        assert porcelain.count("locked rashomon") == 2
        assert "run_id=test-run" in porcelain
        assert f"owner_pid={os.getpid()}" in porcelain
        assert "lease_until=" in porcelain
    finally:
        run(CLEANUP, repo, *paths, env=env)


def test_orphan_cleanup_reclaims_dead_owner_lock(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base, _ = make_repo(repo)
    temp_root = tmp_path / "worktrees"
    temp_root.mkdir()
    env = os.environ | {
        "TMPDIR": str(temp_root),
        "RASHOMON_RUN_ID": "crashed-run",
        "RASHOMON_OWNER_PID": "99999999",
        "RASHOMON_LEASE_SECONDS": "3600",
    }

    created = run(CREATE, repo, "crashed-a", "crashed-b", base, env=env)
    paths = [Path(line) for line in created.stdout.splitlines() if line]
    old = time.time() - 7200
    for path in paths:
        os.utime(path, (old, old))

    run(CLEANUP, "--orphans", repo, env=env)

    assert all(not path.exists() for path in paths)
    porcelain = run("git", "-C", repo, "worktree", "list", "--porcelain").stdout
    assert "crashed-run" not in porcelain
