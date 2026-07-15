#!/bin/bash
#
# Remove registered Rashomon worktrees. Orphan cleanup skips locked worktrees so
# an active long-running evaluation is never selected by age alone.

set -o pipefail

ORPHAN_AGE_MINUTES=60
MALFORMED_LOCK_AGE_MINUTES=1440

ORPHANS_ONLY=false
if [[ "${1:-}" == "--orphans" ]]; then
    ORPHANS_ONLY=true
    shift
fi

REPO_ROOT="${1:-$(pwd)}"
shift || true

if ! git -C "$REPO_ROOT" rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not a git repository: $REPO_ROOT" >&2
    exit 1
fi

REPO_ROOT=$(cd "$REPO_ROOT" && git rev-parse --show-toplevel)
BASE_PATH="${TMPDIR:-/tmp}"
BASE_PATH=$(cd "$BASE_PATH" && pwd -P)

registered_worktrees() {
    git -C "$REPO_ROOT" worktree list --porcelain |
        while IFS= read -r line; do
            case "$line" in
                "worktree "*) printf '%s\n' "${line#worktree }" ;;
            esac
        done
}

is_registered() {
    local target="$1"
    local registered
    while IFS= read -r registered; do
        [[ "$registered" == "$target" ]] && return 0
    done < <(registered_worktrees)
    return 1
}

is_locked() {
    local target="$1"
    git -C "$REPO_ROOT" worktree list --porcelain |
        awk -v target="$target" '
            /^worktree / { current = substr($0, 10); next }
            current == target && /^locked([[:space:]]|$)/ { found = 1 }
            END { exit(found ? 0 : 1) }
        '
}

lock_reason() {
    local target="$1"
    git -C "$REPO_ROOT" worktree list --porcelain |
        awk -v target="$target" '
            /^worktree / { current = substr($0, 10); next }
            current == target && /^locked([[:space:]]|$)/ {
                print substr($0, 8)
                exit
            }
        '
}

lock_field() {
    local reason="$1"
    local key="$2"
    local field
    for field in $reason; do
        case "$field" in
            "$key"=*) printf '%s\n' "${field#*=}"; return 0 ;;
        esac
    done
    return 1
}

process_is_alive() {
    local pid="$1"
    [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" > /dev/null 2>&1
}

validated_path() {
    local requested="$1"
    local parent
    local name
    local resolved_parent
    local resolved

    name="${requested##*/}"
    parent="${requested%/*}"
    [[ "$parent" == "$requested" ]] && parent="."

    case "$name" in
        worktree-rashomon-*) ;;
        *)
            echo "Error: Refusing non-Rashomon path: $requested" >&2
            return 1
            ;;
    esac

    if [[ ! -d "$parent" ]]; then
        echo "Error: Worktree parent does not exist: $parent" >&2
        return 1
    fi
    resolved_parent=$(cd "$parent" && pwd -P)

    if [[ "$resolved_parent" != "$BASE_PATH" ]]; then
        echo "Error: Refusing path outside temp root: $requested" >&2
        return 1
    fi

    resolved="$resolved_parent/$name"
    printf '%s\n' "$resolved"
}

is_orphaned() {
    local path="$1"
    local mtime
    local now
    local age_minutes
    local reason
    local owner_pid
    local lease_until

    [[ -d "$path" ]] || return 1
    if [[ "$(uname)" == "Darwin" ]]; then
        mtime=$(stat -f %m "$path")
    else
        mtime=$(stat -c %Y "$path")
    fi
    now=$(date +%s)
    age_minutes=$(( (now - mtime) / 60 ))

    if ! is_locked "$path"; then
        [[ $age_minutes -ge $ORPHAN_AGE_MINUTES ]]
        return
    fi

    reason=$(lock_reason "$path")
    case "$reason" in
        rashomon*) ;;
        *) return 1 ;;
    esac

    owner_pid=$(lock_field "$reason" "owner_pid" || true)
    lease_until=$(lock_field "$reason" "lease_until" || true)

    if [[ "$owner_pid" =~ ^[0-9]+$ ]] &&
       ! process_is_alive "$owner_pid" &&
       [[ $age_minutes -ge $ORPHAN_AGE_MINUTES ]]; then
        return 0
    fi

    if [[ "$lease_until" =~ ^[0-9]+$ ]] && [[ $now -ge $lease_until ]]; then
        return 0
    fi

    if [[ ! "$lease_until" =~ ^[0-9]+$ ]] &&
       [[ $age_minutes -ge $MALFORMED_LOCK_AGE_MINUTES ]]; then
        return 0
    fi
    return 1
}

remove_worktree() {
    local requested="$1"
    local path

    if ! path=$(validated_path "$requested"); then
        return 1
    fi

    if ! is_registered "$path"; then
        echo "Worktree is not registered; nothing removed: $path" >&2
        return 0
    fi

    git -C "$REPO_ROOT" worktree unlock "$path" > /dev/null 2>&1 || true
    echo "Removing worktree: $path" >&2
    if git -C "$REPO_ROOT" worktree remove --force "$path" 2>&1; then
        return 0
    fi

    # Manual fallback remains bounded to a validated, registered Rashomon path.
    if is_registered "$path"; then
        echo "Warning: git removal failed; removing validated worktree directory" >&2
        rm -rf "$path" 2>/dev/null || return 1
        git -C "$REPO_ROOT" worktree prune > /dev/null 2>&1 || true
        return 0
    fi
    return 1
}

WORKTREES_TO_REMOVE=()
ERRORS=0

if [[ $# -gt 0 ]]; then
    for requested in "$@"; do
        if path=$(validated_path "$requested"); then
            WORKTREES_TO_REMOVE+=("$path")
        else
            ERRORS=$((ERRORS + 1))
        fi
    done
elif [[ "$ORPHANS_ONLY" == "true" ]]; then
    while IFS= read -r path; do
        if validated_path "$path" > /dev/null 2>&1 && is_orphaned "$path"; then
            echo "Found expired or orphaned Rashomon worktree: $path" >&2
            WORKTREES_TO_REMOVE+=("$path")
        fi
    done < <(registered_worktrees)
else
    while IFS= read -r path; do
        if validated_path "$path" > /dev/null 2>&1; then
            WORKTREES_TO_REMOVE+=("$path")
        fi
    done < <(registered_worktrees)
fi

for worktree in "${WORKTREES_TO_REMOVE[@]}"; do
    if ! remove_worktree "$worktree"; then
        ERRORS=$((ERRORS + 1))
    fi
done

git -C "$REPO_ROOT" worktree prune > /dev/null 2>&1 || true

if [[ ${#WORKTREES_TO_REMOVE[@]} -eq 0 ]]; then
    echo "No worktrees to clean up." >&2
else
    echo "Cleanup complete. Selected ${#WORKTREES_TO_REMOVE[@]} worktree(s)." >&2
fi

if [[ $ERRORS -gt 0 ]]; then
    echo "Warning: $ERRORS cleanup error(s) occurred." >&2
    exit 2
fi

exit 0
