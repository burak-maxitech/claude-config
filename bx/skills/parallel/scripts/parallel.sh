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

# Rewrite members through a temp file + mv. Args: <ref> [<folder> <branch>]
# Drops any row for <ref>; appends the new row when folder/branch are given.
write_member() {
    local ref="$1" folder="${2:-}" branch="${3:-}" tmp="$MEMBERS.tmp.$$"
    { [ -f "$MEMBERS" ] && awk -F'\t' -v r="$ref" '$1 != r' "$MEMBERS"; true; } > "$tmp"
    [ -n "$folder" ] && printf '%s\t%s\t%s\n' "$ref" "$folder" "$branch" >> "$tmp"
    mv "$tmp" "$MEMBERS"
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

sub="${1:-}"
[ $# -gt 0 ] && shift
case "$sub" in
    on)     cmd_on "$@" ;;
    join)   cmd_join "$@" ;;
    leave)  cmd_leave "$@" ;;
    off)    cmd_off "$@" ;;
    status) cmd_status "$@" ;;
    member) cmd_member "$@" ;;
    *) echo "usage: parallel.sh <on|join|leave|off|status|member> [args]"; exit 2 ;;
esac
