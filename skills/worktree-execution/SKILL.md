---
name: worktree-execution
description: Git worktree management for isolated parallel prompt execution. Use when creating isolated environments for prompt comparison or managing worktree lifecycle. Provides creation, cleanup, and orphan detection scripts.
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
./scripts/worktree-create.sh [repo_root]
```

**Output** (stdout):
```
/tmp/worktree-rashomon-original-20260114-123456
/tmp/worktree-rashomon-optimized-20260114-123456
```

**Properties**:
- Location: `${TMPDIR:-/tmp}/`
- Naming: `worktree-rashomon-{type}-{timestamp}`
- Branch: Detached HEAD at current commit

### Cleanup

**Script**: `scripts/worktree-cleanup.sh`

```bash
# Remove all rashomon worktrees
./scripts/worktree-cleanup.sh [repo_root]

# Remove specific worktrees
./scripts/worktree-cleanup.sh [repo_root] path1 path2

# Remove only orphaned worktrees (age > 1 hour)
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
| Orphan detected | Force remove worktrees older than 1 hour |

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
- **Git required**: git 2.5+ for worktree support
- **Disk space**: Sufficient space for worktree copies
