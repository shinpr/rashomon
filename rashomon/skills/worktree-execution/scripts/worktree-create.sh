#!/bin/bash
#
# worktree-create.sh
# Creates two git worktrees for parallel prompt execution
#
# Usage: worktree-create.sh [repo_root]
# Output: Prints paths of created worktrees (one per line)
#
# Exit codes:
#   0 - Success
#   1 - Not a git repository
#   2 - Worktree creation failed

set -euo pipefail

# Configuration
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Get repository root (use argument or current directory)
REPO_ROOT="${1:-$(pwd)}"

# Verify we're in a git repository
if ! git -C "$REPO_ROOT" rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not a git repository: $REPO_ROOT" >&2
    exit 1
fi

# Get absolute path to repo root
REPO_ROOT=$(cd "$REPO_ROOT" && git rev-parse --show-toplevel)

# Define paths
BASE_PATH="${TMPDIR:-/tmp}"
WORKTREE_ORIGINAL="$BASE_PATH/worktree-rashomon-original-$TIMESTAMP"
WORKTREE_OPTIMIZED="$BASE_PATH/worktree-rashomon-optimized-$TIMESTAMP"

# Function to create worktree
create_worktree() {
    local path="$1"
    local name="$2"

    # Create detached HEAD worktree at current HEAD
    if git -C "$REPO_ROOT" worktree add --detach "$path" HEAD 2>&1; then
        echo "Created worktree: $path" >&2
        return 0
    else
        echo "Error: Failed to create worktree $name" >&2
        return 1
    fi
}

# Create both worktrees
echo "Creating worktrees in $BASE_PATH..." >&2

if ! create_worktree "$WORKTREE_ORIGINAL" "original"; then
    exit 2
fi

if ! create_worktree "$WORKTREE_OPTIMIZED" "optimized"; then
    # Cleanup the first worktree if second fails
    git -C "$REPO_ROOT" worktree remove --force "$WORKTREE_ORIGINAL" 2>/dev/null || true
    exit 2
fi

# Output the paths (stdout, for capture by caller)
echo "$WORKTREE_ORIGINAL"
echo "$WORKTREE_OPTIMIZED"

echo "Worktree creation complete." >&2
