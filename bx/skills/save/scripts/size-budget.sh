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

CLAUDE_BUDGET=12000; CLAUDE_STOP=10000
STATUS_BUDGET=15000; STATUS_STOP=13000
LAST_UPDATED_MAX=250
ARCHIVE_THRESHOLD=100000
SKIP_ESCALATE=3
# Everything Claude Code loads before the first prompt: CLAUDE.md, rules files
# with no paths: frontmatter, the auto-memory index, the SessionStart hook block.
LOADED_WARN=25000
MEMORY_WARN=12000        # half of Claude Code's 25KB MEMORY.md load limit
RULES_WARN=8000          # per path-scoped rules file; Claude Code truncates at 40,000
LINES_TARGET=200         # Anthropic's own target for a CLAUDE.md, in lines
LONG_LINE=400            # a line over this is a dense paragraph, not an instruction

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

memory_index() {   # -- path of this repo's auto-memory MEMORY.md, empty if not found
    # Claude Code keys the project folder on the absolute path with every
    # non-alphanumeric character turned into "-". Best effort: a miss is silent.
    _abs="$(cd "$REPO" && { pwd -W 2>/dev/null || pwd; })"
    _slug="$(printf '%s' "$_abs" | sed 's/[^A-Za-z0-9]/-/g')"
    _f="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects/$_slug/memory/MEMORY.md"
    [ -f "$_f" ] && printf '%s' "$_f"
}
hook_chars() {     # -- chars the plugin's SessionStart hook emits for this repo, 0 if absent
    _h="$(cd "$(dirname "$0")/../../.." 2>/dev/null && pwd)/scripts/session-start-context.sh"
    [ -f "$_h" ] || { echo 0; return; }
    (cd "$REPO" && BX_HOOK_NO_NETWORK=1 CLAUDE_ENV_FILE="" bash "$_h" 2>/dev/null | awk '{n+=length($0)+1} END{print n+0}')
}

# The always-loaded total. Computed in both modes: --line reports it when over.
loaded_total=0; loaded_records=""
add_loaded() {     # <label> <chars>
    loaded_total=$((loaded_total + $2))
    loaded_records="$loaded_records
loaded $1 $2"
}
[ -f "$REPO/CLAUDE.md" ] && add_loaded CLAUDE.md "$(total "$REPO/CLAUDE.md")"
rules_records=""
for rf in "$REPO"/.claude/rules/*.md; do
    [ -f "$rf" ] || continue
    rc="$(total "$rf")"
    if head -8 "$rf" | grep -q '^paths:'; then
        if [ "$rc" -gt "$RULES_WARN" ]; then rs=over; else rs=ok; fi
        rules_records="$rules_records
rules .claude/rules/$(basename "$rf") $rc $RULES_WARN $rs"
    else
        add_loaded ".claude/rules/$(basename "$rf")(unscoped)" "$rc"
    fi
done
mem="$(memory_index)"; mem_chars=0
if [ -n "$mem" ]; then mem_chars="$(total "$mem")"; add_loaded MEMORY.md "$mem_chars"; fi
hk="$(hook_chars)"
[ "$hk" -gt 0 ] && add_loaded session-start-hook "$hk"
if [ "$loaded_total" -gt "$LOADED_WARN" ]; then loaded_state=over; else loaded_state=ok; fi

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
        if [ "$rel" = "CLAUDE.md" ]; then
            awk -v t="$LINES_TARGET" -v w="$LONG_LINE" '
                {if (length($0) > w) lg++; if (length($0) > mx) mx = length($0)}
                END {printf "lines CLAUDE.md %d %d %s\n", NR, t, (NR > t ? "over" : "ok")
                     printf "long_lines CLAUDE.md %d %d %d\n", lg + 0, w, mx + 0}' "$f"
        fi
    fi
done

if [ "$MODE" = "line" ]; then
    [ -n "$line_out" ] || { echo "Size budget: no CLAUDE.md or docs/STATUS.md here"; exit 0; }
    [ "$loaded_state" = "over" ] && line_out="$line_out · loaded at session start $(kfmt "$loaded_total") / $((LOADED_WARN / 1000))k"
    if [ "$any_over" -eq 1 ]; then
        tail_msg="→ run /bx:save --full"
        [ "$skips" -ge "$SKIP_ESCALATE" ] && tail_msg="→ OVER BUDGET, shrink skipped $skips runs in a row: run /bx:save --full and apply"
        echo "Size budget: $line_out $tail_msg"
    elif [ "$loaded_state" = "over" ]; then
        echo "Size budget: $line_out → run /bx:save --full"
    else
        echo "Size budget: $line_out — within budget"
    fi
    exit 0
fi

printf '%s\n' "$loaded_records" | sed '/^$/d'
echo "loaded_total $loaded_total $LOADED_WARN $loaded_state"
if [ -n "$mem" ]; then
    if [ "$mem_chars" -gt "$MEMORY_WARN" ]; then echo "memory MEMORY.md $mem_chars $MEMORY_WARN over"
    else echo "memory MEMORY.md $mem_chars $MEMORY_WARN ok"; fi
fi
printf '%s\n' "$rules_records" | sed '/^$/d'

for a in session-history key-decisions completed-work known-issues next-steps-backlog; do
    f="$REPO/docs/$a.md"
    [ -f "$f" ] || continue
    bytes="$(wc -c < "$f" | tr -d ' ')"
    if [ "$bytes" -gt "$ARCHIVE_THRESHOLD" ]; then echo "archive docs/$a.md $bytes $ARCHIVE_THRESHOLD rotate"
    else echo "archive docs/$a.md $bytes $ARCHIVE_THRESHOLD ok"; fi
done
echo "skips $skips"
