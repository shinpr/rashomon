#!/bin/bash
#
# worktree-create.sh
# Creates two git worktrees for parallel execution
#
# Usage: worktree-create.sh [repo_root] [label_a] [label_b]
#   repo_root: Repository root path (default: current directory)
#   label_a:   Label for first worktree (default: original)
#   label_b:   Label for second worktree (default: optimized)
#
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
LABEL_A="${2:-original}"
LABEL_B="${3:-optimized}"

# Verify we're in a git repository
if ! git -C "$REPO_ROOT" rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not a git repository: $REPO_ROOT" >&2
    exit 1
fi

# Get absolute path to repo root
REPO_ROOT=$(cd "$REPO_ROOT" && git rev-parse --show-toplevel)

# Define paths
BASE_PATH="${TMPDIR:-/tmp}"
WORKTREE_A="$BASE_PATH/worktree-rashomon-${LABEL_A}-$TIMESTAMP"
WORKTREE_B="$BASE_PATH/worktree-rashomon-${LABEL_B}-$TIMESTAMP"

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

if ! create_worktree "$WORKTREE_A" "$LABEL_A"; then
    exit 2
fi

if ! create_worktree "$WORKTREE_B" "$LABEL_B"; then
    # Cleanup the first worktree if second fails
    git -C "$REPO_ROOT" worktree remove --force "$WORKTREE_A" 2>/dev/null || true
    exit 2
fi

# Output the paths (stdout, for capture by caller)
echo "$WORKTREE_A"
echo "$WORKTREE_B"

echo "Worktree creation complete." >&2
