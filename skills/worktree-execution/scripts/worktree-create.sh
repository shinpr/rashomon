#!/bin/bash
#
# worktree-create.sh
# Creates two git worktrees for parallel execution
#
# Usage: worktree-create.sh [repo_root] [label_a] [label_b] [base_sha]
#   repo_root: Repository root path (default: current directory)
#   label_a:   Label for first worktree (default: original)
#   label_b:   Label for second worktree (default: optimized)
#   base_sha:  Commit used by both worktrees (default: HEAD)
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
BASE_SHA_INPUT="${4:-HEAD}"

# Verify we're in a git repository
if ! git -C "$REPO_ROOT" rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not a git repository: $REPO_ROOT" >&2
    exit 1
fi

# Get absolute path to repo root
REPO_ROOT=$(cd "$REPO_ROOT" && git rev-parse --show-toplevel)
if ! BASE_SHA=$(git -C "$REPO_ROOT" rev-parse --verify "${BASE_SHA_INPUT}^{commit}" 2>/dev/null); then
    echo "Error: Invalid base commit: $BASE_SHA_INPUT" >&2
    exit 1
fi

for label in "$LABEL_A" "$LABEL_B"; do
    case "$label" in
        ""|*[!A-Za-z0-9._-]*)
            echo "Error: Labels may contain only letters, numbers, dot, underscore, and hyphen" >&2
            exit 1
            ;;
    esac
done

# Define lease metadata before creating anything so validation failures leave no worktrees.
STARTED_AT=$(date +%s)
LEASE_SECONDS="${RASHOMON_LEASE_SECONDS:-21600}"
if [[ ! "$LEASE_SECONDS" =~ ^[0-9]+$ ]] || [[ "$LEASE_SECONDS" -lt 60 ]]; then
    echo "Error: RASHOMON_LEASE_SECONDS must be an integer of at least 60" >&2
    exit 1
fi
LEASE_UNTIL=$((STARTED_AT + LEASE_SECONDS))
OWNER_PID="${RASHOMON_OWNER_PID:-$PPID}"
RUN_ID="${RASHOMON_RUN_ID:-$TIMESTAMP-$$}"
LOCK_REASON="rashomon run_id=$RUN_ID owner_pid=$OWNER_PID started_at=$STARTED_AT lease_until=$LEASE_UNTIL"

# Define paths
BASE_PATH="${TMPDIR:-/tmp}"
BASE_PATH=$(cd "$BASE_PATH" && pwd -P)
WORKTREE_A="$BASE_PATH/worktree-rashomon-${LABEL_A}-$TIMESTAMP"
WORKTREE_B="$BASE_PATH/worktree-rashomon-${LABEL_B}-$TIMESTAMP"

# Function to create worktree
create_worktree() {
    local path="$1"
    local name="$2"

    # Create detached worktree at the Phase B pinned commit.
    if git -C "$REPO_ROOT" worktree add --detach "$path" "$BASE_SHA" >&2; then
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

# Protect active evaluations from orphan cleanup while retaining crash-recovery metadata.
if ! git -C "$REPO_ROOT" worktree lock --reason "$LOCK_REASON" "$WORKTREE_A" 2>&1; then
    git -C "$REPO_ROOT" worktree remove --force "$WORKTREE_A" 2>/dev/null || true
    git -C "$REPO_ROOT" worktree remove --force "$WORKTREE_B" 2>/dev/null || true
    echo "Error: Failed to lock first worktree" >&2
    exit 2
fi

if ! git -C "$REPO_ROOT" worktree lock --reason "$LOCK_REASON" "$WORKTREE_B" 2>&1; then
    git -C "$REPO_ROOT" worktree unlock "$WORKTREE_A" 2>/dev/null || true
    git -C "$REPO_ROOT" worktree remove --force "$WORKTREE_A" 2>/dev/null || true
    git -C "$REPO_ROOT" worktree remove --force "$WORKTREE_B" 2>/dev/null || true
    echo "Error: Failed to lock second worktree" >&2
    exit 2
fi

# Output the paths (stdout, for capture by caller)
echo "$WORKTREE_A"
echo "$WORKTREE_B"

echo "Worktree creation complete." >&2
