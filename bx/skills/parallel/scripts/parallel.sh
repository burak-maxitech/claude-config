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
# Retries ~5 s, then assumes the holder died and takes over.
MEMBERS_LOCK="$STATE/members.lock"
members_lock() {
    local i=0
    mkdir -p "$STATE"
    while ! mkdir "$MEMBERS_LOCK" 2>/dev/null; do
        i=$((i + 1))
        if [ "$i" -ge 100 ]; then rm -rf "$MEMBERS_LOCK"; mkdir "$MEMBERS_LOCK" 2>/dev/null; break; fi
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

print_held() {
    local since; since="$(lock_field since)"
    echo "lock=held owner=$(lock_field ref) age=$(( $(now) - ${since:-0} )) step=$(lock_field step)"
}

wait_owner() { # give a just-created lock dir a moment to get its owner file
    local i=0
    while [ ! -f "$LOCK_DIR/owner" ] && [ "$i" -lt 20 ]; do
        i=$((i + 1)); sleep 0.05 2>/dev/null || sleep 1
    done
}

cmd_lock() {
    local usage="usage: parallel.sh lock <ref> <step> [--live-refs a,b,c]"
    [ $# -ge 2 ] || { echo "$usage"; exit 2; }
    local ref="$1" step="$2" live="" have_live=0
    shift 2
    while [ $# -gt 0 ]; do
        case "$1" in
            --live-refs) have_live=1; live="${2:-}"; shift; [ $# -gt 0 ] && shift ;;
            *) echo "$usage"; exit 2 ;;
        esac
    done
    if ! is_on; then echo "mode=off"; exit 2; fi
    if mkdir "$LOCK_DIR" 2>/dev/null; then
        write_owner "$ref" "$step"; echo "lock=acquired"; return 0
    fi
    wait_owner
    local owner since reason=""
    owner="$(lock_field ref)"; since="$(lock_field since)"
    if [ -n "$owner" ] && [ "$owner" = "$ref" ]; then
        write_owner "$ref" "$step"; echo "lock=acquired"; return 0
    fi
    if [ ! -f "$LOCK_DIR/owner" ] || [ $(( $(now) - ${since:-0} )) -ge 900 ]; then
        reason=stale
    elif [ "$have_live" -eq 1 ]; then
        case ",$live," in *",$owner,"*) ;; *) reason=gone ;; esac
    fi
    if [ -z "$reason" ]; then print_held; exit 4; fi
    rm -rf "$LOCK_DIR"
    if mkdir "$LOCK_DIR" 2>/dev/null; then
        write_owner "$ref" "$step"
        log_line "lock-broken prev_owner=$owner reason=$reason by=$ref"
        echo "lock=broken prev_owner=$owner reason=$reason"
        echo "lock=acquired"
        return 0
    fi
    wait_owner   # lost the single retry to another session
    print_held; exit 4
}

cmd_touch_lock() {
    [ $# -eq 2 ] || { echo "usage: parallel.sh touch-lock <ref> <step>"; exit 2; }
    if [ -f "$LOCK_DIR/owner" ] && [ "$(lock_field ref)" = "$1" ]; then
        write_owner "$1" "$2"; echo "lock=touched"; return 0
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
    *) echo "usage: parallel.sh <on|join|leave|off|status|member|lock|touch-lock|unlock> [args]"; exit 2 ;;
esac
