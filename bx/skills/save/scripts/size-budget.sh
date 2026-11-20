#!/usr/bin/env bash
# size-budget.sh - measure CLAUDE.md and docs/STATUS.md against the bx size budget.
#
# The one place the budget numbers live as code. mode-update-full.md Part 7 and
# /bx:resume run this instead of restating the arithmetic; doc-schema.md's
# "Size budget" section states the same numbers in prose. Read-only.
#
# Usage: size-budget.sh [repo-dir] [--line]
#   (default)  machine-readable report, one record per line:
#                file <path> <chars> <budget> <stop> <over|band|ok> <need>
#                section <path> <chars> <header line, or HEADER>
#                last_updated <path> <chars> <max> <over|ok>
#                archive <path> <bytes> <threshold> <rotate|ok>
#                skips <n>
#   --line     one human-readable line for /bx:resume and the drift report
#
# <need> is chars to remove to reach <stop>; 0 unless the file is over budget.
# "band" means over <stop> but not over <budget>: nothing fires (hysteresis).
# Sizes are awk's length(), so they are characters in a UTF-8 locale and bytes
# in the C locale; the difference is the file's non-ASCII share.
# Exit 0 always when the repo is readable; 2 on a bad argument.
# bash 3.2 compatible.

set -uo pipefail

CLAUDE_BUDGET=10000; CLAUDE_STOP=9000
STATUS_BUDGET=15000; STATUS_STOP=13000
LAST_UPDATED_MAX=250
ARCHIVE_THRESHOLD=100000
SKIP_ESCALATE=3

REPO="."; MODE="report"
for arg in "$@"; do
    case "$arg" in
        --line) MODE="line" ;;
        -*) echo "unknown flag: $arg" >&2; exit 2 ;;
        *) REPO="$arg" ;;
    esac
done
[ -d "$REPO" ] || { echo "not a directory: $REPO" >&2; exit 2; }

sections() {   # <file> -- "<chars>\t<section>" per section, file order
    awk 'BEGIN{section="HEADER"; size=0}
         /^## /{printf "%d\t%s\n", size, section; section=$0; size=0; next}
         {size+=length($0)+1}
         END{printf "%d\t%s\n", size, section}' "$1"
}
total() {      # <file> -- chars, counted the way sections() counts them
    awk '{n+=length($0)+1} END{print n+0}' "$1"
}
last_updated_len() {   # <file> -- length of the first Last Updated line, 0 if none
    awk '/^## /{exit} /^[*]*Last Updated/{print length($0); f=1; exit} END{if(!f)print 0}' "$1"
}
kfmt() {       # <chars> -- 16653 -> 16.7k
    awk -v n="$1" 'BEGIN{printf "%.1fk", n/1000}'
}
state_of() {   # <size> <budget> <stop>
    if [ "$1" -gt "$2" ]; then echo over
    elif [ "$1" -gt "$3" ]; then echo band
    else echo ok; fi
}

skips=0
if [ -f "$REPO/docs/STATUS.md" ]; then
    s="$(grep -oE 'bx-size-skips=[0-9]+' "$REPO/docs/STATUS.md" | head -1 | grep -oE '[0-9]+' || true)"
    [ -n "$s" ] && skips="$s"
fi

line_out=""; any_over=0
for spec in "CLAUDE.md:$CLAUDE_BUDGET:$CLAUDE_STOP" "docs/STATUS.md:$STATUS_BUDGET:$STATUS_STOP"; do
    rel="${spec%%:*}"; rest="${spec#*:}"; budget="${rest%%:*}"; stop="${rest#*:}"
    f="$REPO/$rel"
    [ -f "$f" ] || continue
    size="$(total "$f")"
    state="$(state_of "$size" "$budget" "$stop")"
    need=0
    if [ "$state" = "over" ]; then need=$((size - stop)); any_over=1; fi
    if [ "$MODE" = "line" ]; then
        [ -n "$line_out" ] && line_out="$line_out, "
        line_out="$line_out${rel##*/} $(kfmt "$size") / $((budget / 1000))k"
    else
        echo "file $rel $size $budget $stop $state $need"
        sections "$f" | sort -t "$(printf '\t')" -k1,1nr | while IFS="$(printf '\t')" read -r n name; do
            echo "section $rel $n $name"
        done
        lu="$(last_updated_len "$f")"
        if [ "$lu" -gt "$LAST_UPDATED_MAX" ]; then echo "last_updated $rel $lu $LAST_UPDATED_MAX over"
        else echo "last_updated $rel $lu $LAST_UPDATED_MAX ok"; fi
    fi
done

if [ "$MODE" = "line" ]; then
    [ -n "$line_out" ] || { echo "Size budget: no CLAUDE.md or docs/STATUS.md here"; exit 0; }
    if [ "$any_over" -eq 1 ]; then
        tail_msg="→ run /bx:save --full"
        [ "$skips" -ge "$SKIP_ESCALATE" ] && tail_msg="→ OVER BUDGET, shrink skipped $skips runs in a row: run /bx:save --full and apply"
        echo "Size budget: $line_out $tail_msg"
    else
        echo "Size budget: $line_out — within budget"
    fi
    exit 0
fi

for a in session-history key-decisions completed-work known-issues next-steps-backlog; do
    f="$REPO/docs/$a.md"
    [ -f "$f" ] || continue
    bytes="$(wc -c < "$f" | tr -d ' ')"
    if [ "$bytes" -gt "$ARCHIVE_THRESHOLD" ]; then echo "archive docs/$a.md $bytes $ARCHIVE_THRESHOLD rotate"
    else echo "archive docs/$a.md $bytes $ARCHIVE_THRESHOLD ok"; fi
done
echo "skips $skips"
