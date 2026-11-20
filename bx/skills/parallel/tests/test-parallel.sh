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
    local before; before="$(wc -l < "$r/.git/bx-parallel/log" | tr -d ' ')"
    px "$r" off
    expect_has "off prints mode=off" "$OUT" "mode=off"
    px "$r" status
    expect_has "status after off" "$OUT" "mode=off"
    local after; after="$(wc -l < "$r/.git/bx-parallel/log" | tr -d ' ')"
    expect_eq "off appends exactly one log line" "$((after - before))" 1
    expect_eq "last log line is the off entry" "$(tail -n 1 "$r/.git/bx-parallel/log" | cut -d' ' -f2-)" "off"
}

test_leave_releases_lock_and_last_turns_off() {
    echo "test_leave_releases_lock_and_last_turns_off"
    local r; r="$(make_repo leave_lock)"
    px "$r" on s70 "$r"
    px "$r" join s71 /x/one s/s71
    px "$r" lock s71 land
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

test_join_concurrent_no_lost_rows() {
    echo "test_join_concurrent_no_lost_rows"
    local r; r="$(make_repo join_race)"
    px "$r" on s70 "$r"
    local i
    for i in 1 2 3 4 5 6 7 8 9 10; do
        ( cd "$r" && bash "$SCRIPT" join "p$i" "/x/p$i" "s/p$i" >/dev/null 2>&1 ) &
    done
    wait
    px "$r" status
    expect_eq "10 concurrent joins + on = 11 member rows" "$(printf '%s\n' "$OUT" | grep -c '^member ')" 11
    expect_eq "no members lock left behind" "$([ -e "$r/.git/bx-parallel/members.lock" ] && echo yes || echo no)" no
}

# lock_setup <name>: repo with mode on; prints path.
lock_setup() {
    local r; r="$(make_repo "$1")"
    px "$r" on s70 "$r"
    echo "$r"
}

test_lock_acquire_and_held() {
    echo "test_lock_acquire_and_held"
    local r; r="$(lock_setup lock_held)"
    BXP_NOW=1000 px "$r" lock s70 land
    expect_eq "first lock exits 0" "$RC" 0
    expect_has "first lock acquired" "$OUT" "lock=acquired"
    expect_eq "owner file has ref/since/step" "$(cat "$r/.git/bx-parallel/land.lock/owner")" "$(printf 'ref=s70\nsince=1000\nstep=land')"
    BXP_NOW=1042 px "$r" lock s71 land
    expect_eq "other ref exits 4" "$RC" 4
    expect_has "held output" "$OUT" "lock=held owner=s70 age=42 step=land"
    BXP_NOW=1050 px "$r" lock s70 ff-main
    expect_eq "owner relock exits 0" "$RC" 0
    expect_has "owner relock acquired" "$OUT" "lock=acquired"
    expect_eq "owner relock refreshed step" "$(grep '^step=' "$r/.git/bx-parallel/land.lock/owner")" "step=ff-main"
}

test_lock_stale_broken() {
    echo "test_lock_stale_broken"
    local r; r="$(lock_setup lock_stale)"
    BXP_NOW=1000 px "$r" lock s70 land
    BXP_NOW=1899 px "$r" lock s71 land
    expect_eq "since+899 still held (exit 4)" "$RC" 4
    BXP_NOW=1900 px "$r" lock s71 land
    expect_eq "since+900 breaks (exit 0)" "$RC" 0
    expect_has "broken stale output" "$OUT" "lock=broken prev_owner=s70 reason=stale"
    expect_has "then acquired" "$OUT" "lock=acquired"
    expect_eq "new owner is s71" "$(grep '^ref=' "$r/.git/bx-parallel/land.lock/owner")" "ref=s71"
    expect_has "break is logged" "$(cat "$r/.git/bx-parallel/log")" "lock-broken"
}

test_lock_gone_broken() {
    echo "test_lock_gone_broken"
    local r; r="$(lock_setup lock_gone)"
    BXP_NOW=1000 px "$r" lock s70 land
    BXP_NOW=1001 px "$r" lock s71 land --live-refs s71,s72
    expect_eq "owner absent from live refs exits 0" "$RC" 0
    expect_has "broken gone output" "$OUT" "lock=broken prev_owner=s70 reason=gone"
    BXP_NOW=1002 px "$r" lock s73 land --live-refs s71,s73
    expect_eq "owner present in live refs stays held" "$RC" 4
}

test_touch_extends() {
    echo "test_touch_extends"
    local r; r="$(lock_setup lock_touch)"
    BXP_NOW=1000 px "$r" lock s70 land
    BXP_NOW=1800 px "$r" touch-lock s70 push
    expect_eq "touch by owner exits 0" "$RC" 0
    BXP_NOW=2600 px "$r" lock s71 land
    expect_eq "still held at +1600 after touch at +800" "$RC" 4
    expect_has "held shows new step" "$OUT" "step=push"
    BXP_NOW=1800 px "$r" touch-lock s71 push
    expect_eq "touch by non-owner exits 4" "$RC" 4
}

test_unlock_not_owner() {
    echo "test_unlock_not_owner"
    local r; r="$(lock_setup lock_unlock)"
    px "$r" lock s70 land
    px "$r" unlock s71
    expect_eq "unlock by non-owner exits 4" "$RC" 4
    [ -d "$r/.git/bx-parallel/land.lock" ] && pass "lock survives" || fail "lock wrongly removed"
    px "$r" unlock s70
    expect_eq "unlock by owner exits 0" "$RC" 0
    expect_has "released" "$OUT" "lock=released"
    px "$r" status
    expect_has "free afterwards" "$OUT" "lock=free"
}

test_unlock_force() {
    echo "test_unlock_force"
    local r; r="$(lock_setup lock_force)"
    px "$r" lock s70 land
    px "$r" unlock s71 --force
    expect_eq "force exits 0" "$RC" 0
    expect_has "force prints prev_owner" "$OUT" "prev_owner=s70"
    expect_has "force released" "$OUT" "lock=released"
    [ -e "$r/.git/bx-parallel/land.lock" ] && fail "lock still there" || pass "lock removed"
}

test_lock_race() {
    echo "test_lock_race"
    local r; r="$(lock_setup lock_race)"
    local i bad=0 d="$TMP_ROOT/race_out"
    mkdir -p "$d"
    for i in $(seq 1 20); do
        rm -rf "$r/.git/bx-parallel/land.lock"
        ( cd "$r" && bash "$SCRIPT" lock a land >"$d/a.out" 2>&1; echo $? > "$d/a.rc" ) &
        ( cd "$r" && bash "$SCRIPT" lock b land >"$d/b.out" 2>&1; echo $? > "$d/b.rc" ) &
        wait
        local ra rb; ra="$(cat "$d/a.rc")"; rb="$(cat "$d/b.rc")"
        if [ "$ra" = 0 ] && [ "$rb" = 4 ] && grep -q 'lock=held' "$d/b.out" && grep -q 'lock=acquired' "$d/a.out"; then :
        elif [ "$ra" = 4 ] && [ "$rb" = 0 ] && grep -q 'lock=held' "$d/a.out" && grep -q 'lock=acquired' "$d/b.out"; then :
        else bad=$((bad + 1)); echo "    iteration $i: a=$ra b=$rb"; fi
    done
    expect_eq "20 iterations: exactly one winner each time" "$bad" 0
}

# --- Task 1 + 2 tests (later tasks append their tests above the runner) ---
TESTS="test_on_status test_on_twice test_join_requires_on test_join_replace test_member test_state_shared_across_worktrees test_leave_and_off test_leave_releases_lock_and_last_turns_off test_leave_hand_written_lock test_join_concurrent_no_lost_rows test_lock_acquire_and_held test_lock_stale_broken test_lock_gone_broken test_touch_extends test_unlock_not_owner test_unlock_force test_lock_race"

for t in $TESTS; do "$t"; done

echo ""
if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES assertion(s) failed."; exit 1; fi
echo "All tests passed."
