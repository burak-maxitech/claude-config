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
    git -C "$dir" config core.autocrlf false
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

test_lock_break_race() {
    echo "test_lock_break_race"
    local r; r="$(lock_setup lock_break_race)"
    local i bad=0 d="$TMP_ROOT/brk_out" k
    mkdir -p "$d"
    for i in $(seq 1 20); do
        rm -rf "$r/.git/bx-parallel/land.lock" "$r/.git/bx-parallel/land.lock.break" "$d"/*
        mkdir "$r/.git/bx-parallel/land.lock"
        printf 'ref=dead\nsince=1\nstep=land\n' > "$r/.git/bx-parallel/land.lock/owner"
        for k in a b c; do
            ( cd "$r" && bash "$SCRIPT" lock "$k" land >"$d/$k.out" 2>&1; echo $? > "$d/$k.rc" ) &
        done
        wait
        local zeros; zeros="$(cat "$d"/*.rc | grep -c '^0$')"
        [ "$zeros" = 1 ] || { bad=$((bad + 1)); echo "    iteration $i: $zeros winners"; }
    done
    expect_eq "20 iterations: exactly one breaker wins" "$bad" 0
}

test_lock_ownerless_held() {
    echo "test_lock_ownerless_held"
    local r; r="$(lock_setup lock_ownerless)"
    mkdir "$r/.git/bx-parallel/land.lock"
    px "$r" lock s71 land
    expect_eq "owner-less fresh lock is held (exit 4)" "$RC" 4
    expect_has "held with unknown owner" "$OUT" "lock=held owner= age=?"
    touch -d '2 hours ago' "$r/.git/bx-parallel/land.lock"
    px "$r" lock s71 land
    expect_eq "owner-less lock 900 s old is broken" "$RC" 0
    expect_has "broken stale" "$OUT" "reason=stale"
}

test_live_refs_empty_rejected() {
    echo "test_live_refs_empty_rejected"
    local r; r="$(lock_setup lock_emptylive)"
    px "$r" lock s70 land
    px "$r" lock s71 land --live-refs ""
    expect_eq "empty --live-refs exits 2" "$RC" 2
    px "$r" lock s71 land --live-refs
    expect_eq "missing --live-refs value exits 2" "$RC" 2
    expect_eq "lock untouched" "$(grep '^ref=' "$r/.git/bx-parallel/land.lock/owner")" "ref=s70"
}

test_members_lock_stale_takeover() {
    echo "test_members_lock_stale_takeover"
    local r; r="$(lock_setup members_stale)"
    mkdir "$r/.git/bx-parallel/members.lock"
    touch -d '1 minute ago' "$r/.git/bx-parallel/members.lock"
    px "$r" join s71 /x/one s/s71
    expect_eq "join takes over dead members lock" "$RC" 0
    px "$r" status
    expect_has "row written" "$OUT" "member ref=s71 "
}

# --- Task 3: git steps ---
commit_file() { # <repo> <file> <content> <msg>
    echo "$3" > "$1/$2"
    git -C "$1" add "$2"
    git -C "$1" commit -q -m "$4"
}

test_ensure_ignore_idempotent() {
    echo "test_ensure_ignore_idempotent"
    local r; r="$(make_repo ign)"
    px "$r" ensure-ignore
    expect_eq "first run exits 0" "$RC" 0
    expect_has "first run adds" "$OUT" "ignore=added"
    px "$r" ensure-ignore
    expect_has "second run present" "$OUT" "ignore=present"
    expect_eq "entry written once" "$(grep -c '^\.claude/worktrees/$' "$r/.gitignore")" 1
    expect_eq "nothing committed" "$(git -C "$r" rev-list --count HEAD)" 1
}

test_worktree_requires_ignore() {
    echo "test_worktree_requires_ignore"
    local r; r="$(make_repo wt_noignore)"
    px "$r" worktree s71
    expect_eq "exit 9" "$RC" 9
    expect_has "ignore=missing" "$OUT" "ignore=missing"
    [ ! -d "$r/.claude/worktrees/s71" ] && pass "no worktree created" || fail "worktree created"
}

test_worktree_based_on_local_main() {
    echo "test_worktree_based_on_local_main"
    local r; r="$(make_repo wt_base)"
    px "$r" ensure-ignore
    git -C "$r" add .gitignore; git -C "$r" commit -q -m ignore
    git -C "$r" update-ref refs/remotes/origin/main "$(git -C "$r" rev-parse HEAD~1)"
    px "$r" worktree s71
    expect_eq "exit 0" "$RC" 0
    expect_has "branch printed" "$OUT" "branch=s/s71"
    expect_has "path printed" "$OUT" "path="
    expect_eq "branch base is local main" "$(git -C "$r" rev-parse s/s71)" "$(git -C "$r" rev-parse main)"
    [ -d "$r/.claude/worktrees/s71" ] && pass "folder exists" || fail "folder missing"
    px "$r" worktree s71
    expect_eq "existing exits 0" "$RC" 0
    expect_has "existing=yes" "$OUT" "existing=yes"
}

# branch_setup <name>: repo with ignore committed and a worktree on s/a; sets WT.
# Call as: r="$(make_repo x)"; branch_setup "$r"
branch_setup() {
    px "$1" ensure-ignore
    git -C "$1" add .gitignore; git -C "$1" commit -q -m ignore
    px "$1" worktree a
    WT="$1/.claude/worktrees/a"
}

test_catch_up_dirty() {
    echo "test_catch_up_dirty"
    local r; r="$(make_repo cu_dirty)"; branch_setup "$r"
    commit_file "$WT" a.txt a "a work"
    echo changed >> "$WT/a.txt"
    local before; before="$(git -C "$WT" rev-parse HEAD)"
    px "$WT" catch-up
    expect_eq "exit 6" "$RC" 6
    expect_has "tree=dirty" "$OUT" "tree=dirty"
    expect_eq "branch unchanged" "$(git -C "$WT" rev-parse HEAD)" "$before"
    expect_eq "no auto-stash" "$(git -C "$WT" stash list | wc -l | tr -d ' ')" 0
    expect_has "edit kept" "$(cat "$WT/a.txt")" "changed"
}

test_catch_up_conflict_aborts() {
    echo "test_catch_up_conflict_aborts"
    local r; r="$(make_repo cu_conf)"; branch_setup "$r"
    commit_file "$WT" README.md "branch side" "branch edit"
    commit_file "$r" README.md "main side" "main edit"
    local before; before="$(git -C "$WT" rev-parse HEAD)"
    px "$WT" catch-up
    expect_eq "exit 7" "$RC" 7
    expect_has "conflict files" "$OUT" "conflict files=README.md"
    expect_eq "branch unchanged" "$(git -C "$WT" rev-parse HEAD)" "$before"
    [ ! -d "$(cd "$WT" && git rev-parse --git-path rebase-merge)" ] && pass "no rebase-merge dir" || fail "rebase-merge left behind"
}

test_catch_up_interrupted() {
    echo "test_catch_up_interrupted"
    local r; r="$(make_repo cu_int)"; branch_setup "$r"
    commit_file "$WT" README.md "branch side" "branch edit"
    commit_file "$r" README.md "main side" "main edit"
    git -C "$WT" rebase main >/dev/null 2>&1
    px "$WT" catch-up
    expect_eq "exit 5" "$RC" 5
    expect_has "rebase=interrupted" "$OUT" "rebase=interrupted"
    git -C "$WT" rebase --abort >/dev/null 2>&1
}

test_catch_up_nonconflict_failure() {
    echo "test_catch_up_nonconflict_failure"
    local r; r="$(make_repo cu_fail)"; branch_setup "$r"
    commit_file "$WT" a.txt a "a work"
    commit_file "$r" new.txt main "main adds new.txt"
    echo untracked > "$WT/new.txt"
    local before; before="$(git -C "$WT" rev-parse HEAD)"
    px "$WT" catch-up
    expect_eq "exit 7" "$RC" 7
    expect_has "distinct failure line" "$OUT" "rebase=failed reason="
    case "$OUT" in *"conflict files="*) fail "must not claim a conflict" ;; *) pass "no conflict line" ;; esac
    expect_eq "branch unchanged" "$(git -C "$WT" rev-parse HEAD)" "$before"
    expect_eq "untracked file kept" "$(cat "$WT/new.txt")" untracked
}

test_catch_up_success() {
    echo "test_catch_up_success"
    local r; r="$(make_repo cu_ok)"; branch_setup "$r"
    commit_file "$WT" a.txt a "a work"
    commit_file "$r" m1.txt 1 m1
    commit_file "$r" m2.txt 2 m2
    px "$WT" catch-up
    expect_eq "exit 0" "$RC" 0
    expect_has "two commits from main" "$OUT" "caught_up=2"
    expect_eq "main is ancestor" "$(git -C "$WT" merge-base --is-ancestor main HEAD && echo y)" y
}

test_ff_main_refuses_checked_out() {
    echo "test_ff_main_refuses_checked_out"
    local r; r="$(make_repo ff_co)"; branch_setup "$r"
    commit_file "$WT" a.txt a "a work"
    local before; before="$(git -C "$r" rev-parse main)"
    px "$WT" ff-main
    expect_eq "exit 8" "$RC" 8
    expect_has "names checked-out" "$OUT" "main=checked-out path="
    expect_has "names the main folder" "$OUT" "ff_co"
    expect_eq "main unchanged" "$(git -C "$r" rev-parse main)" "$before"
}

test_ff_main_success() {
    echo "test_ff_main_success"
    local r; r="$(make_repo ff_ok)"; branch_setup "$r"
    commit_file "$WT" a.txt a "a work"
    git -C "$r" checkout -q -b parked
    px "$WT" ff-main
    expect_eq "exit 0" "$RC" 0
    expect_has "landed sha" "$OUT" "landed=$(git -C "$WT" rev-parse --short HEAD)"
    expect_eq "main == branch head" "$(git -C "$r" rev-parse main)" "$(git -C "$WT" rev-parse HEAD)"
}

test_ff_main_not_ff() {
    echo "test_ff_main_not_ff"
    local r; r="$(make_repo ff_nff)"; branch_setup "$r"
    commit_file "$WT" a.txt a "a work"
    commit_file "$r" m.txt m "main moves"
    git -C "$r" checkout -q -b parked
    local before; before="$(git -C "$r" rev-parse main)"
    px "$WT" ff-main
    expect_eq "exit 7" "$RC" 7
    expect_has "main=not-ff" "$OUT" "main=not-ff"
    expect_eq "main unchanged" "$(git -C "$r" rev-parse main)" "$before"
}

test_two_branches_land_in_turn() {
    echo "test_two_branches_land_in_turn"
    local r; r="$(make_repo two)"; branch_setup "$r"
    local wa="$WT"
    px "$r" worktree b
    local wb="$r/.claude/worktrees/b"
    commit_file "$wa" a.txt a "A"
    commit_file "$wb" b.txt b "B"
    git -C "$r" checkout -q -b parked
    px "$wa" catch-up; expect_eq "A catch-up" "$RC" 0
    px "$wa" ff-main;  expect_eq "A lands" "$RC" 0
    px "$wb" catch-up; expect_eq "B catch-up" "$RC" 0
    expect_has "B caught up 1" "$OUT" "caught_up=1"
    px "$wb" ff-main;  expect_eq "B lands" "$RC" 0
    expect_eq "main has A" "$(git -C "$r" show main:a.txt)" a
    expect_eq "main has B" "$(git -C "$r" show main:b.txt)" b
}

# --- Task 4: save helpers ---
# put_main <repo> <path> <content> <msg>: commit a file on the current branch (LF, no CRLF noise).
put_main() {
    git -C "$1" config core.autocrlf false
    mkdir -p "$(dirname "$1/$2")"
    printf '%s
' "$3" > "$1/$2"
    git -C "$1" add "$2"
    git -C "$1" commit -q -m "$4"
}

test_next_session_forms() {
    echo "test_next_session_forms"
    local r; r="$(make_repo ns1)"
    put_main "$r" docs/STATUS.md "Last Updated: 2026-11-20 (Session 70)" status
    px "$r" next-session
    expect_eq "plain Session 70" "$OUT" "current=70 next=71 source=docs/STATUS.md"
    r="$(make_repo ns2)"
    put_main "$r" docs/STATUS.md "**Last Updated:** 2026-11-20 (Session 70 (cont.))" status
    px "$r" next-session
    expect_has "cont. form" "$OUT" "current=70 next=71"
    r="$(make_repo ns3)"
    put_main "$r" docs/STATUS.md "Last Updated: 2026-11-20" status
    px "$r" next-session
    expect_eq "no number" "$OUT" "next=unknown"
    expect_eq "no number exits 0" "$RC" 0
    r="$(make_repo ns4)"
    put_main "$r" CLAUDE.md "Last Updated: 2026-11-20 (Session 12)" claude
    px "$r" next-session
    expect_eq "STATUS.md absent reads CLAUDE.md" "$OUT" "current=12 next=13 source=CLAUDE.md"
    r="$(make_repo ns5)"
    px "$r" next-session
    expect_eq "neither file" "$OUT" "next=unknown"
    # reads committed main, not the working tree
    r="$(make_repo ns6)"
    put_main "$r" docs/STATUS.md "Last Updated: 2026-11-20 (Session 70)" status
    git -C "$r" checkout -q -b feat
    put_main "$r" docs/STATUS.md "Last Updated: 2026-11-21 (Session 99)" branch
    px "$r" next-session
    expect_has "reads main, not branch" "$OUT" "current=70 next=71"
}

# plugin_json <version>
plugin_json() { printf '{
  "name": "bx",
  "version": "%s",
  "x": 1
}' "$1"; }
PJ="bx/.claude-plugin/plugin.json"

test_version_check() {
    echo "test_version_check"
    local r; r="$(make_repo vc1)"
    px "$r" version-check
    expect_eq "no plugin.json" "$OUT" "version=n/a"
    expect_eq "n/a exits 0" "$RC" 0
    # branch ahead of main
    put_main "$r" "$PJ" "$(plugin_json 2.20.0)" base
    git -C "$r" checkout -q -b feat
    put_main "$r" "$PJ" "$(plugin_json 2.21.0)" minor
    px "$r" version-check
    expect_eq "branch ahead" "$OUT" "main=2.20.0 branch=2.21.0 ok=yes suggest=2.21.0"
    # another session landed 2.21.0 on main
    git -C "$r" checkout -q main
    put_main "$r" "$PJ" "$(plugin_json 2.21.0)" "other session"
    git -C "$r" checkout -q feat
    px "$r" version-check
    expect_eq "same version, minor bump" "$OUT" "main=2.21.0 branch=2.21.0 ok=no suggest=2.22.0"
    # patch-level base bump
    r="$(make_repo vc2)"
    put_main "$r" "$PJ" "$(plugin_json 2.20.0)" base
    git -C "$r" checkout -q -b feat
    put_main "$r" "$PJ" "$(plugin_json 2.20.1)" patch
    git -C "$r" checkout -q main
    put_main "$r" "$PJ" "$(plugin_json 2.21.0)" "other session"
    git -C "$r" checkout -q feat
    px "$r" version-check
    expect_eq "patch bump" "$OUT" "main=2.21.0 branch=2.20.1 ok=no suggest=2.21.1"
    # major bump, and numeric (not string) comparison
    r="$(make_repo vc3)"
    put_main "$r" "$PJ" "$(plugin_json 2.9.0)" base
    git -C "$r" checkout -q -b feat
    put_main "$r" "$PJ" "$(plugin_json 3.0.0)" major
    git -C "$r" checkout -q main
    put_main "$r" "$PJ" "$(plugin_json 2.10.0)" "other session"
    git -C "$r" checkout -q feat
    px "$r" version-check
    expect_eq "major, 3.0.0 > 2.10.0" "$OUT" "main=2.10.0 branch=3.0.0 ok=yes suggest=3.0.0"
    # branch made no bump: suggest patch
    r="$(make_repo vc4)"
    put_main "$r" "$PJ" "$(plugin_json 2.20.0)" base
    git -C "$r" checkout -q -b feat
    commit_file "$r" f.txt f work
    px "$r" version-check
    expect_eq "no bump equal to main" "$OUT" "main=2.20.0 branch=2.20.0 ok=no suggest=2.20.1"
}

# --- Task 1 + 2 tests (later tasks append their tests above the runner) ---
TESTS="test_on_status test_on_twice test_join_requires_on test_join_replace test_member test_state_shared_across_worktrees test_leave_and_off test_leave_releases_lock_and_last_turns_off test_leave_hand_written_lock test_join_concurrent_no_lost_rows test_lock_acquire_and_held test_lock_stale_broken test_lock_gone_broken test_touch_extends test_unlock_not_owner test_unlock_force test_lock_race test_lock_break_race test_lock_ownerless_held test_live_refs_empty_rejected test_members_lock_stale_takeover test_ensure_ignore_idempotent test_worktree_requires_ignore test_worktree_based_on_local_main test_catch_up_dirty test_catch_up_conflict_aborts test_catch_up_interrupted test_catch_up_nonconflict_failure test_catch_up_success test_ff_main_refuses_checked_out test_ff_main_success test_ff_main_not_ff test_two_branches_land_in_turn test_next_session_forms test_version_check"
[ $# -gt 0 ] && TESTS="$*"

for t in $TESTS; do "$t"; done

echo ""
if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES assertion(s) failed."; exit 1; fi
echo "All tests passed."
