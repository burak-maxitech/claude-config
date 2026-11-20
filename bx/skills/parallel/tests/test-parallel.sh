#!/usr/bin/env bash
# test-parallel.sh - tests for bx/skills/parallel/scripts/parallel.sh
#
# Usage: bash bx/skills/parallel/tests/test-parallel.sh
# Exit 0 = every test passed (skips allowed). Exit 1 = at least one failed.
# bash 3.2 compatible. Each test builds a throwaway repo under a mktemp dir.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/../scripts/parallel.sh"

FAILURES=0
pass() { echo "  PASS  $1"; }
fail() { echo "  FAIL  $1"; FAILURES=$((FAILURES + 1)); }
skip() { echo "  SKIP  $1"; }

TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

# make_repo <name>: one commit on main; prints the repo path.
make_repo() {
    local dir="$TMP_ROOT/$1"
    mkdir -p "$dir"
    git -C "$dir" init -q -b main
    git -C "$dir" config user.email t@example.com
    git -C "$dir" config user.name tester
    echo hi > "$dir/README.md"
    git -C "$dir" add README.md
    git -C "$dir" commit -q -m init
    echo "$dir"
}

# px <dir> <args...>: run parallel.sh from <dir>; sets OUT and RC.
px() {
    local dir="$1"; shift
    OUT="$(cd "$dir" && bash "$SCRIPT" "$@" 2>&1)"
    RC=$?
}

# check <description> <condition-result>
expect_eq() { # <desc> <actual> <expected>
    if [ "$2" = "$3" ]; then pass "$1"; else fail "$1 (got '$2', want '$3')"; fi
}
expect_has() { # <desc> <text> <needle>
    case "$2" in *"$3"*) pass "$1" ;; *) fail "$1 (missing '$3' in: $2)" ;; esac
}

test_on_status() {
    echo "test_on_status"
    local r; r="$(make_repo on_status)"
    px "$r" status
    expect_has "status before on is mode=off" "$OUT" "mode=off"
    px "$r" on s70 "$r"
    expect_eq "on exits 0" "$RC" 0
    expect_has "on prints mode=on" "$OUT" "mode=on"
    px "$r" status
    expect_has "status mode=on" "$OUT" "mode=on"
    expect_has "status lists first member with branch" "$OUT" "member ref=s70 folder=$r branch=main"
    expect_has "status lock=free" "$OUT" "lock=free"
}

test_on_twice() {
    echo "test_on_twice"
    local r; r="$(make_repo on_twice)"
    px "$r" on s70 "$r"
    px "$r" on s71 "$r"
    expect_eq "second on exits 3" "$RC" 3
    expect_has "second on prints mode=already-on" "$OUT" "mode=already-on"
}

test_join_requires_on() {
    echo "test_join_requires_on"
    local r; r="$(make_repo join_off)"
    px "$r" join s71 "$r" s/s71
    expect_eq "join with mode off exits 2" "$RC" 2
}

test_join_replace() {
    echo "test_join_replace"
    local r; r="$(make_repo join_replace)"
    px "$r" on s70 "$r"
    px "$r" join s71 /x/one s/s71
    expect_has "join prints joined=s71" "$OUT" "joined=s71"
    px "$r" join s71 /x/two s/s71b
    px "$r" status
    expect_eq "re-join leaves one s71 row" "$(printf '%s\n' "$OUT" | grep -c 'member ref=s71 ')" 1
    expect_has "re-join replaced the row" "$OUT" "member ref=s71 folder=/x/two branch=s/s71b"
}

test_member() {
    echo "test_member"
    local r; r="$(make_repo member)"
    px "$r" member s70
    expect_eq "member with mode off exits 1" "$RC" 1
    px "$r" on s70 "$r"
    px "$r" member s70
    expect_eq "member of s70 exits 0" "$RC" 0
    expect_eq "member prints nothing" "$OUT" ""
    px "$r" member s99
    expect_eq "non-member exits 1" "$RC" 1
}

test_state_shared_across_worktrees() {
    echo "test_state_shared_across_worktrees"
    local r; r="$(make_repo shared)"
    local wt="$TMP_ROOT/shared-wt"
    git -C "$r" worktree add -q -b s/s71 "$wt"
    px "$r" on s70 "$r"
    px "$wt" join s71 "$wt" s/s71
    expect_eq "join from worktree exits 0" "$RC" 0
    px "$r" status
    expect_has "status in main folder sees worktree member" "$OUT" "member ref=s71 folder=$wt branch=s/s71"
}

test_leave_and_off() {
    echo "test_leave_and_off"
    local r; r="$(make_repo leave)"
    px "$r" on s70 "$r"
    px "$r" join s71 /x/one s/s71
    px "$r" leave s71
    expect_has "leave prints left=s71" "$OUT" "left=s71"
    case "$OUT" in *mode=off*) fail "leave with members remaining must not turn off" ;; *) pass "mode stays on while members remain" ;; esac
    px "$r" off
    expect_has "off prints mode=off" "$OUT" "mode=off"
    px "$r" status
    expect_has "status after off" "$OUT" "mode=off"
    expect_eq "off appends to log" "$([ -s "$r/.git/bx-parallel/log" ] && echo yes || echo no)" yes
}

test_leave_releases_lock_and_last_turns_off() {
    echo "test_leave_releases_lock_and_last_turns_off"
    # Needs Task 2's `lock`; stays skipped until the script has it.
    if ! grep -q 'lock)' "$SCRIPT" 2>/dev/null; then
        skip "needs Task 2 'lock' subcommand"
        return
    fi
    local r; r="$(make_repo leave_lock)"
    px "$r" on s70 "$r"
    px "$r" join s71 /x/one s/s71
    px "$r" lock s71 s70,s71
    expect_has "s71 acquired lock" "$OUT" "lock=acquired"
    px "$r" leave s71
    expect_has "leave releases the lock" "$OUT" "lock=released"
    px "$r" status
    expect_has "lock is free after leave" "$OUT" "lock=free"
    px "$r" leave s70
    expect_has "last leave turns mode off" "$OUT" "mode=off"
    expect_eq "state dir contents gone" "$([ -e "$r/.git/bx-parallel/members" ] && echo yes || echo no)" no
}

test_leave_hand_written_lock() {
    echo "test_leave_hand_written_lock"
    local r; r="$(make_repo leave_hand)"
    px "$r" on s70 "$r"
    px "$r" join s71 /x/one s/s71
    mkdir "$r/.git/bx-parallel/land.lock"
    printf 'ref=s71\nsince=1000\nstep=ff-main\n' > "$r/.git/bx-parallel/land.lock/owner"
    BXP_NOW=1042 px "$r" status
    expect_has "status shows held owner, age, step" "$OUT" "lock=held owner=s71 age=42 step=ff-main"
    px "$r" leave s70
    [ -d "$r/.git/bx-parallel/land.lock" ] && pass "another ref's leave keeps the lock" || fail "lock wrongly released"
    px "$r" leave s71
    expect_has "owner's leave releases lock" "$OUT" "lock=released"
    expect_has "last leave turns mode off" "$OUT" "mode=off"
    [ -e "$r/.git/bx-parallel/land.lock" ] && fail "land.lock left behind" || pass "land.lock removed"
}

# --- Task 1 tests (later tasks append their tests above the runner) ---
TESTS="test_on_status test_on_twice test_join_requires_on test_join_replace test_member test_state_shared_across_worktrees test_leave_and_off test_leave_releases_lock_and_last_turns_off test_leave_hand_written_lock"

for t in $TESTS; do "$t"; done

echo ""
if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES assertion(s) failed."; exit 1; fi
echo "All tests passed."
