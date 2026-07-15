---
name: worktree-execution
description: Git worktree management for isolated parallel prompt execution. Use when creating isolated environments for prompt comparison or managing worktree lifecycle. Provides creation, cleanup, and orphan detection scripts.
user-invocable: false
---

# Worktree Execution Skill

## Architecture

Two isolated worktrees enable parallel prompt execution.

```
Orchestrator
    │
    ├── Create Worktrees (in ${TMPDIR:-/tmp}/)
    │       ├── worktree-rashomon-original-{timestamp}
    │       └── worktree-rashomon-optimized-{timestamp}
    │
    ├── Parallel Execution (Task tool)
    │       ├── Execution 1 → worktree-rashomon-original
    │       └── Execution 2 → worktree-rashomon-optimized
    │
    ├── Collect Results (await both)
    │
    └── Cleanup Worktrees (always)
```

## Worktree Management

### Creation

**Script**: `scripts/worktree-create.sh`

```bash
# Default labels (original/optimized) for prompt eval
./scripts/worktree-create.sh [repo_root]

# Custom labels for skill eval
./scripts/worktree-create.sh [repo_root] baseline with-skill
./scripts/worktree-create.sh [repo_root] old-version new-version

# Pin every pair in an evaluation run to the same commit
./scripts/worktree-create.sh [repo_root] trial-a trial-b [base_sha]
```

**Output** (stdout):
```
/tmp/worktree-rashomon-{label_a}-20260114-123456
/tmp/worktree-rashomon-{label_b}-20260114-123456
```

**Properties**:
- Location: `${TMPDIR:-/tmp}/`
- Naming: `worktree-rashomon-{label}-{timestamp}`
- Branch: Detached HEAD at the pinned base commit
- Base commit: Caller-supplied SHA, resolved once per evaluation
- Active marker: Git worktree lock containing run ID, owner PID, start time, and lease expiry
- Labels default to `original` / `optimized` if not specified

### Cleanup

**Script**: `scripts/worktree-cleanup.sh`

```bash
# Remove all rashomon worktrees
./scripts/worktree-cleanup.sh [repo_root]

# Remove specific worktrees
./scripts/worktree-cleanup.sh [repo_root] path1 path2

# Remove registered orphaned worktrees, including expired Rashomon locks
./scripts/worktree-cleanup.sh --orphans [repo_root]
```

**Cleanup Triggers**:
- After successful report generation
- In finally block on any failure
- On timeout
- On startup (orphan detection)

## Parallel Execution Principle

**Key**: To achieve true parallel execution, spawn both Task calls in a single message.

The calling command determines which agents to invoke and how to structure the Task calls. This skill provides only the worktree infrastructure.

## Error Handling (Worktree Operations)

| Scenario | Behavior |
|----------|----------|
| Creation fails | Report git error, suggest checking repository state |
| Cleanup fails | Log warning, attempt orphan cleanup on next run |
| Unlocked orphan | Remove registered Rashomon worktree after 1 hour |
| Crashed locked run | Remove after owner disappearance plus orphan age, or after lease expiry |
| Active long run | Set `RASHOMON_LEASE_SECONDS` before creation so the lease covers the run |

## Scripts Reference

### worktree-create.sh

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success |
| 1 | Not a git repository |
| 2 | Creation failed |

### worktree-cleanup.sh

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success (or nothing to clean) |
| 1 | Not a git repository |
| 2 | Cleanup partially failed |

## Constraints

- **No concurrent comparisons**: One rashomon execution per repository
- **Git required**: A version supporting `git worktree lock`
- **Disk space**: Sufficient space for worktree copies
