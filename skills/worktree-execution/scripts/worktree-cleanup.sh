#!/bin/bash
#
# worktree-cleanup.sh
# Removes specified worktrees or all rashomon worktrees
#
# Usage:
#   worktree-cleanup.sh [repo_root]                    # Remove all rashomon worktrees
#   worktree-cleanup.sh [repo_root] path1 path2 ...   # Remove specific worktrees
#   worktree-cleanup.sh --orphans [repo_root]          # Remove orphaned worktrees only
#
# Exit codes:
#   0 - Success (or nothing to clean)
#   1 - Not a git repository
#   2 - Cleanup failed (but best effort was made)

set -uo pipefail

# Configuration
ORPHAN_AGE_MINUTES=60

# Parse arguments
ORPHANS_ONLY=false
if [[ "${1:-}" == "--orphans" ]]; then
    ORPHANS_ONLY=true
    shift
fi

# Get repository root
REPO_ROOT="${1:-$(pwd)}"
shift || true

# Verify we're in a git repository
if ! git -C "$REPO_ROOT" rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not a git repository: $REPO_ROOT" >&2
    exit 1
fi

# Get absolute path to repo root
REPO_ROOT=$(cd "$REPO_ROOT" && git rev-parse --show-toplevel)
BASE_PATH="${TMPDIR:-/tmp}"

# Function to remove a worktree
remove_worktree() {
    local path="$1"

    if [[ -d "$path" ]]; then
        echo "Removing worktree: $path" >&2
        if git -C "$REPO_ROOT" worktree remove --force "$path" 2>&1; then
            return 0
        else
            # If git worktree remove fails, try manual removal
            echo "Warning: git worktree remove failed, attempting manual cleanup" >&2
            rm -rf "$path" 2>/dev/null || true
            return 0
        fi
    else
        echo "Worktree not found: $path" >&2
        return 0
    fi
}

# Function to check if worktree is orphaned (older than threshold)
is_orphaned() {
    local path="$1"

    if [[ ! -d "$path" ]]; then
        return 1
    fi

    # Get directory modification time
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS
        local mtime=$(stat -f %m "$path")
    else
        # Linux
        local mtime=$(stat -c %Y "$path")
    fi

    local now=$(date +%s)
    local age_minutes=$(( (now - mtime) / 60 ))

    if [[ $age_minutes -ge $ORPHAN_AGE_MINUTES ]]; then
        return 0
    else
        return 1
    fi
}

# Collect worktrees to remove
WORKTREES_TO_REMOVE=()

if [[ $# -gt 0 ]]; then
    # Specific worktrees provided as arguments
    WORKTREES_TO_REMOVE=("$@")
elif [[ "$ORPHANS_ONLY" == "true" ]]; then
    # Only orphaned worktrees
    for dir in "$BASE_PATH"/worktree-rashomon-*; do
        if [[ -d "$dir" ]] && is_orphaned "$dir"; then
            echo "Found orphaned worktree: $dir (age > ${ORPHAN_AGE_MINUTES} minutes)" >&2
            WORKTREES_TO_REMOVE+=("$dir")
        fi
    done
else
    # All rashomon worktrees
    for dir in "$BASE_PATH"/worktree-rashomon-*; do
        if [[ -d "$dir" ]]; then
            WORKTREES_TO_REMOVE+=("$dir")
        fi
    done
fi

# Remove collected worktrees
ERRORS=0
for wt in "${WORKTREES_TO_REMOVE[@]}"; do
    if ! remove_worktree "$wt"; then
        ERRORS=$((ERRORS + 1))
    fi
done

# Prune worktree list
echo "Pruning worktree list..." >&2
git -C "$REPO_ROOT" worktree prune 2>&1 || true

# Report result
if [[ ${#WORKTREES_TO_REMOVE[@]} -eq 0 ]]; then
    echo "No worktrees to clean up." >&2
else
    echo "Cleanup complete. Removed ${#WORKTREES_TO_REMOVE[@]} worktree(s)." >&2
fi

if [[ $ERRORS -gt 0 ]]; then
    echo "Warning: $ERRORS error(s) occurred during cleanup." >&2
    exit 2
fi

exit 0
