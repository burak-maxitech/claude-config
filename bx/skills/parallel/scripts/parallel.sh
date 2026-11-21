#!/usr/bin/env bash
# parallel.sh - shared state for coordinating several Claude Code sessions on one repo.
#
# Usage: parallel.sh <subcommand> [args]
#   on <ref> <folder>             turn the mode on; caller becomes first member
#   join <ref> <folder> <branch>  add or replace a member row
#   leave <ref>                   remove a member (releases its lock; last one turns mode off)
#   off                           turn the mode off and delete the state
#   status                        mode, members, lock
#   member <ref>                  exit 0 if member, 1 if not (no output)
#   lock <ref> <step> [--live-refs a,b,c]   take the land lock (exit 4 if held)
#   touch-lock <ref> <step>       refresh the lock heartbeat (exit 4 if not owner)
#   unlock <ref> [--force]        release the lock (exit 4 if not owner)
#   ensure-ignore                 add .claude/worktrees/ to .gitignore (never commits)
#   worktree <ref>                create .claude/worktrees/<ref> on s/<ref> from local main
#   catch-up                      rebase current branch onto main (exit 5/6/7)
#   ff-main                       fast-forward main to current branch (exit 7/8)
#
# State lives under $(git rev-parse --git-common-dir)/bx-parallel/ so every worktree
# sees the same files. Output is key=value lines. BXP_NOW overrides epoch "now" (tests).
# bash 3.2 compatible.

set -uo pipefail

TAB="$(printf '\t')"

common_dir="$(git rev-parse --git-common-dir 2>/dev/null)" || { echo "error=not-a-git-repo"; exit 4; }
common_dir="$(cd "$common_dir" && pwd)"
STATE="$common_dir/bx-parallel"
MODE_FILE="$STATE/mode"
MEMBERS="$STATE/members"
LOCK_DIR="$STATE/land.lock"
LOG="$STATE/log"

now() { echo "${BXP_NOW:-$(date +%s)}"; }

log_line() { mkdir -p "$STATE"; echo "$(now) $*" >> "$LOG"; }

is_on() { [ -f "$MODE_FILE" ] && grep -qx 'mode=on' "$MODE_FILE"; }

# Short-lived mkdir lock guarding the members read-modify-write (separate from land.lock).
# A holder that has not released within 10 s (by directory age) is presumed dead.
MEMBERS_LOCK="$STATE/members.lock"
# Age in seconds of a directory's own mtime (real clock, not BXP_NOW).
dir_age() {
    local m
    m="$(stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null)" || m=""
    [ -n "$m" ] || { echo 0; return; }
    echo $(( $(date +%s) - m ))
}

# Takeover is judged by the lock directory's age (held for milliseconds, so 10 s = dead holder),
# never by the retry count; after a takeover we loop back to mkdir.
members_lock() {
    mkdir -p "$STATE"
    while ! mkdir "$MEMBERS_LOCK" 2>/dev/null; do
        if [ -d "$MEMBERS_LOCK" ] && [ "$(dir_age "$MEMBERS_LOCK")" -ge 10 ]; then
            rm -rf "$MEMBERS_LOCK"
            continue
        fi
        sleep 0.05 2>/dev/null || sleep 1
    done
}
members_unlock() { rmdir "$MEMBERS_LOCK" 2>/dev/null; }

# Rewrite members through a temp file + mv. Args: <ref> [<folder> <branch>]
# Drops any row for <ref>; appends the new row when folder/branch are given.
write_member() {
    local ref="$1" folder="${2:-}" branch="${3:-}" tmp="$MEMBERS.tmp.$$"
    members_lock
    { [ -f "$MEMBERS" ] && awk -F'\t' -v r="$ref" '$1 != r' "$MEMBERS"; true; } > "$tmp"
    [ -n "$folder" ] && printf '%s\t%s\t%s\n' "$ref" "$folder" "$branch" >> "$tmp"
    mv "$tmp" "$MEMBERS"
    members_unlock
}

lock_field() { sed -n "s/^$1=//p" "$LOCK_DIR/owner" 2>/dev/null | head -n 1; }

# Delete mode, members and the lock; keep the log.
wipe_state() {
    rm -f "$MODE_FILE" "$MEMBERS"
    rm -rf "$LOCK_DIR"
}

cmd_on() {
    [ $# -eq 2 ] || { echo "usage: parallel.sh on <ref> <folder>"; exit 2; }
    if is_on; then echo "mode=already-on"; exit 3; fi
    local branch; branch="$(git -C "$2" branch --show-current 2>/dev/null)"
    mkdir -p "$STATE"
    echo "mode=on" > "$MODE_FILE"
    : > "$MEMBERS"
    write_member "$1" "$2" "$branch"
    log_line "on ref=$1"
    echo "mode=on"
}

cmd_join() {
    [ $# -eq 3 ] || { echo "usage: parallel.sh join <ref> <folder> <branch>"; exit 2; }
    if ! is_on; then echo "mode=off"; exit 2; fi
    write_member "$1" "$2" "$3"
    log_line "join ref=$1"
    echo "joined=$1"
}

cmd_leave() {
    [ $# -eq 1 ] || { echo "usage: parallel.sh leave <ref>"; exit 2; }
    local ref="$1" released=0
    if ! is_on; then echo "mode=off"; return 0; fi
    if [ -f "$LOCK_DIR/owner" ] && [ "$(lock_field ref)" = "$ref" ]; then
        rm -rf "$LOCK_DIR"; released=1
    fi
    write_member "$ref"
    log_line "leave ref=$ref"
    echo "left=$ref"
    [ "$released" -eq 1 ] && echo "lock=released"
    if [ ! -s "$MEMBERS" ]; then
        wipe_state
        log_line "off (last member left)"
        echo "mode=off"
    fi
    return 0
}

cmd_off() {
    if [ -d "$STATE" ]; then log_line "off"; wipe_state; fi
    echo "mode=off"
}

cmd_status() {
    if ! is_on; then echo "mode=off"; return 0; fi
    echo "mode=on"
    if [ -s "$MEMBERS" ]; then
        local ref folder branch
        while IFS="$TAB" read -r ref folder branch; do
            echo "member ref=$ref folder=$folder branch=$branch"
        done < "$MEMBERS"
    fi
    if [ -f "$LOCK_DIR/owner" ]; then
        local since; since="$(lock_field since)"
        echo "lock=held owner=$(lock_field ref) age=$(( $(now) - ${since:-0} )) step=$(lock_field step)"
    else
        echo "lock=free"
    fi
}

cmd_member() {
    [ $# -eq 1 ] || { echo "usage: parallel.sh member <ref>"; exit 2; }
    is_on && [ -f "$MEMBERS" ] && awk -F'\t' -v r="$1" '$1 == r {f=1} END {exit !f}' "$MEMBERS"
}

write_owner() { # <ref> <step>
    printf 'ref=%s\nsince=%s\nstep=%s\n' "$1" "$(now)" "$2" > "$LOCK_DIR/owner.tmp.$$" \
        && mv "$LOCK_DIR/owner.tmp.$$" "$LOCK_DIR/owner"
}

# Fresh acquisition: owner write must succeed or the new lock dir is removed and we fail.
acquire_fresh() { # <ref> <step>
    if ! write_owner "$1" "$2"; then
        rm -rf "$LOCK_DIR"; echo "lock=error reason=owner-write-failed"; exit 1
    fi
}

print_held() {
    if [ ! -f "$LOCK_DIR/owner" ]; then echo "lock=held owner= age=? step="; return; fi
    local since; since="$(lock_field since)"
    echo "lock=held owner=$(lock_field ref) age=$(( $(now) - ${since:-0} )) step=$(lock_field step)"
}

BREAK_DIR="$STATE/land.lock.break"

cmd_lock() {
    local usage="usage: parallel.sh lock <ref> <step> [--live-refs a,b,c]"
    [ $# -ge 2 ] || { echo "$usage"; exit 2; }
    local ref="$1" step="$2" live="" have_live=0
    shift 2
    while [ $# -gt 0 ]; do
        case "$1" in
            --live-refs)
                [ -n "${2:-}" ] || { echo "$usage (--live-refs needs a non-empty list)"; exit 2; }
                have_live=1; live="$2"; shift 2 ;;
            *) echo "$usage"; exit 2 ;;
        esac
    done
    if ! is_on; then echo "mode=off"; exit 2; fi
    local attempt=0 owner since reason
    while [ "$attempt" -lt 200 ]; do
        attempt=$((attempt + 1))
        if mkdir "$LOCK_DIR" 2>/dev/null; then
            acquire_fresh "$ref" "$step"; echo "lock=acquired"; return 0
        fi
        owner="$(lock_field ref)"; since="$(lock_field since)"
        if [ -n "$owner" ] && [ "$owner" = "$ref" ]; then
            write_owner "$ref" "$step" || { echo "lock=error reason=owner-write-failed"; exit 1; }
            echo "lock=acquired"; return 0
        fi
        reason=""
        if [ ! -f "$LOCK_DIR/owner" ]; then
            # Owner-less: the winner may still be between mkdir and its owner write.
            [ -d "$LOCK_DIR" ] && [ "$(dir_age "$LOCK_DIR")" -ge 900 ] && reason=stale
        elif [ $(( $(now) - ${since:-0} )) -ge 900 ]; then
            reason=stale
        elif [ "$have_live" -eq 1 ]; then
            case ",$live," in *",$owner,"*) ;; *) reason=gone ;; esac
        fi
        if [ -z "$reason" ]; then print_held; exit 4; fi
        # Dead lock: serialise breakers behind land.lock.break (held for milliseconds).
        if ! mkdir "$BREAK_DIR" 2>/dev/null; then
            if [ -d "$BREAK_DIR" ] && [ "$(dir_age "$BREAK_DIR")" -ge 10 ]; then rm -rf "$BREAK_DIR"; fi
            sleep 0.05 2>/dev/null || sleep 1
            continue
        fi
        # Re-read under the mutex; break only the exact lock we judged dead.
        if [ "$(lock_field ref)" != "$owner" ] || [ "$(lock_field since)" != "$since" ]; then
            rmdir "$BREAK_DIR" 2>/dev/null; continue
        fi
        rm -rf "$LOCK_DIR"
        if mkdir "$LOCK_DIR" 2>/dev/null; then
            if ! write_owner "$ref" "$step"; then
                rm -rf "$LOCK_DIR"; rmdir "$BREAK_DIR" 2>/dev/null
                echo "lock=error reason=owner-write-failed"; exit 1
            fi
            rmdir "$BREAK_DIR" 2>/dev/null
            log_line "lock-broken prev_owner=$owner reason=$reason by=$ref"
            echo "lock=broken prev_owner=$owner reason=$reason"
            echo "lock=acquired"
            return 0
        fi
        rmdir "$BREAK_DIR" 2>/dev/null
        # A plain acquirer slipped in between our rm and mkdir: report what it holds.
        sleep 0.05 2>/dev/null || sleep 1
        print_held; exit 4
    done
    print_held; exit 4
}

cmd_touch_lock() {
    [ $# -eq 2 ] || { echo "usage: parallel.sh touch-lock <ref> <step>"; exit 2; }
    if [ -f "$LOCK_DIR/owner" ] && [ "$(lock_field ref)" = "$1" ]; then
        write_owner "$1" "$2" || { echo "lock=error reason=owner-write-failed"; exit 1; }
        echo "lock=touched"; return 0
    fi
    echo "lock=not-owner"; exit 4
}

cmd_unlock() {
    [ $# -ge 1 ] || { echo "usage: parallel.sh unlock <ref> [--force]"; exit 2; }
    local ref="$1" force=0
    [ "${2:-}" = "--force" ] && force=1
    if [ ! -d "$LOCK_DIR" ]; then echo "lock=free"; return 0; fi
    local owner; owner="$(lock_field ref)"
    if [ "$owner" = "$ref" ]; then
        rm -rf "$LOCK_DIR"; echo "lock=released"; return 0
    fi
    if [ "$force" -eq 1 ]; then
        rm -rf "$LOCK_DIR"
        log_line "unlock-forced prev_owner=$owner by=$ref"
        echo "lock=released prev_owner=$owner"; return 0
    fi
    echo "lock=not-owner owner=$owner"; exit 4
}

# First entry of `git worktree list --porcelain` is the main worktree.
main_root() { git worktree list --porcelain | sed -n '1s/^worktree //p'; }

cmd_ensure_ignore() {
    local root; root="$(main_root)"
    local gi="$root/.gitignore"
    if [ -f "$gi" ] && grep -qxE '/?\.claude/worktrees/?' "$gi"; then
        echo "ignore=present"; return 0
    fi
    # keep the file's last line intact if it lacks a trailing newline
    [ -s "$gi" ] && [ -n "$(tail -c 1 "$gi")" ] && echo >> "$gi"
    echo ".claude/worktrees/" >> "$gi"
    echo "ignore=added"
}

cmd_worktree() {
    [ $# -eq 1 ] || { echo "usage: parallel.sh worktree <ref>"; exit 2; }
    local ref="$1" root path
    root="$(main_root)"
    path="$root/.claude/worktrees/$ref"
    if [ -d "$path" ]; then
        echo "path=$path"; echo "branch=s/$ref"; echo "existing=yes"; return 0
    fi
    if ! git -C "$root" check-ignore -q ".claude/worktrees/$ref" 2>/dev/null; then
        echo "ignore=missing"; exit 9
    fi
    if ! git -C "$root" worktree add -q -b "s/$ref" "$path" main >/dev/null 2>&1; then
        echo "worktree=failed"; exit 1
    fi
    echo "path=$path"; echo "branch=s/$ref"
}

# Rebase the current branch onto local main. Caller holds the land lock.
cmd_catch_up() {
    local d
    for d in rebase-merge rebase-apply; do
        if [ -e "$(git rev-parse --git-path $d)" ]; then echo "rebase=interrupted"; exit 5; fi
    done
    if [ -n "$(git status --porcelain --untracked-files=no)" ]; then echo "tree=dirty"; exit 6; fi
    local n; n="$(git rev-list --count HEAD..main 2>/dev/null || echo 0)"
    local err; err="$(git rebase main 2>&1 >/dev/null)"
    if [ $? -ne 0 ]; then
        local files; files="$(git diff --name-only --diff-filter=U | paste -sd, -)"
        local first; first="$(printf '%s\n' "$err" | sed -n '1p')"
        git rebase --abort >/dev/null 2>&1
        for d in rebase-merge rebase-apply; do
            if [ -e "$(git rev-parse --git-path $d)" ]; then echo "rebase=interrupted"; exit 5; fi
        done
        if [ -z "$files" ]; then echo "rebase=failed reason=$first"; exit 7; fi
        echo "conflict files=$files"; exit 7
    fi
    echo "caught_up=$n"
}

# Fast-forward local main to the current branch. Caller holds the land lock.
cmd_ff_main() {
    local br; br="$(git symbolic-ref --short -q HEAD)" || { echo "error=detached-head"; exit 2; }
    local co
    co="$(git worktree list --porcelain | awk '/^worktree /{p=substr($0,10)} /^branch refs\/heads\/main$/{print p; exit}')"
    if [ -n "$co" ]; then echo "main=checked-out path=$co"; exit 8; fi
    if ! git merge-base --is-ancestor main "$br" 2>/dev/null; then echo "main=not-ff"; exit 7; fi
    if ! git fetch -q . "$br:main" >/dev/null 2>&1; then echo "main=not-ff"; exit 7; fi
    echo "landed=$(git rev-parse --short main)"
}

sub="${1:-}"
[ $# -gt 0 ] && shift
case "$sub" in
    on)     cmd_on "$@" ;;
    join)   cmd_join "$@" ;;
    leave)  cmd_leave "$@" ;;
    off)    cmd_off "$@" ;;
    status) cmd_status "$@" ;;
    member) cmd_member "$@" ;;
    lock)   cmd_lock "$@" ;;
    touch-lock) cmd_touch_lock "$@" ;;
    unlock) cmd_unlock "$@" ;;
    ensure-ignore) cmd_ensure_ignore "$@" ;;
    worktree) cmd_worktree "$@" ;;
    catch-up) cmd_catch_up "$@" ;;
    ff-main) cmd_ff_main "$@" ;;
    *) echo "usage: parallel.sh <on|join|leave|off|status|member|lock|touch-lock|unlock|ensure-ignore|worktree|catch-up|ff-main> [args]"; exit 2 ;;
esac
