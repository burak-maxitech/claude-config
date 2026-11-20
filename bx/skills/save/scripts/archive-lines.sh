#!/usr/bin/env bash
# archive-lines.sh - copy lines from a live doc into an archive, byte for byte,
# skipping every line the archive already holds.
#
# The "archive first" half of every Part 7 line move (mode-update-full.md 7.5).
# The orchestrator names source lines by number, so no text passes through the
# model on its way to the archive, and a line already archived by an earlier
# trim is never archived twice (the cause of a 441k next-steps-backlog.md).
# It never edits the source: removing the lines is the caller's second step.
#
# Usage: archive-lines.sh <repo> <src> <dest> <heading> <range>... [--prefix STR]
#   <src> <dest>  repo-relative paths
#   <heading>     heading line the new lines go under ("" for none). Written once:
#                 a second call with the same heading appends beneath it.
#   <range>       N or N-M, 1-based source line numbers. Blank lines are skipped.
#   --prefix STR  put STR before each line (e.g. '- [x] ' for completed-work.md)
#
# Output: one "have <n>" line per source line already in the archive, then
#         "archived <new> skipped <have> -> <dest>".
# Exit 0 on success, 2 on a bad argument, 1 if a range lies outside the source.
# bash 3.2 compatible.

set -uo pipefail

[ "$#" -ge 5 ] || { echo "usage: archive-lines.sh <repo> <src> <dest> <heading> <range>... [--prefix STR]" >&2; exit 2; }
REPO="$1"; SRC="$1/$2"; SRC_REL="$2"; DEST="$1/$3"; DEST_REL="$3"; HEADING="$4"; shift 4
PREFIX=""; RANGES=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --prefix) [ "$#" -ge 2 ] || { echo "--prefix needs a value" >&2; exit 2; }; PREFIX="$2"; shift 2 ;;
        *[!0-9-]*|"") echo "bad range: $1" >&2; exit 2 ;;
        *) RANGES="$RANGES $1"; shift ;;
    esac
done
[ -d "$REPO" ] || { echo "not a directory: $REPO" >&2; exit 2; }
[ -f "$SRC" ] || { echo "no such source: $SRC" >&2; exit 2; }
[ -n "$RANGES" ] || { echo "no ranges given" >&2; exit 2; }

src_lines="$(awk 'END{print NR}' "$SRC")"
# Validate every range before anything is created or written.
for r in $RANGES; do
    a="${r%%-*}"; b="${r##*-}"
    [ -n "$a" ] && [ -n "$b" ] && [ "$a" -ge 1 ] && [ "$b" -ge "$a" ] && [ "$b" -le "$src_lines" ] || {
        echo "range $r is outside $SRC_REL (1-$src_lines)" >&2; exit 1; }
done

if [ ! -f "$DEST" ]; then
    mkdir -p "$(dirname "$DEST")"
    case "$(basename "$DEST")" in
        next-steps-backlog.md)
            printf '%s\n' '# Next Steps — Backlog Detail' '' \
                '> Detail rolled off [STATUS.md](STATUS.md) by `/bx:save --full`. Nothing here is loaded automatically.' '' '---' > "$DEST" ;;
        completed-work.md)
            printf '%s\n' '# Completed Work' '' \
                '> Full checklist of completed tasks. Referenced from [STATUS.md](STATUS.md).' '' '---' > "$DEST" ;;
        session-history.md)
            printf '%s\n' '# Session History Archive' '' \
                '> Auto-managed by `/bx:save`. Last session summary is in [STATUS.md](STATUS.md).' '' '---' > "$DEST" ;;
        architecture.md)
            printf '%s\n' '# Architecture' '' \
                '> Full architecture detail, moved out of CLAUDE.md (doc schema v2). Read on demand.' '' '---' > "$DEST" ;;
        *)
            printf '%s\n' "# $(basename "$DEST" .md)" '' \
                '> Detail moved out of CLAUDE.md by `/bx:save --full`. Read on demand.' '' '---' > "$DEST" ;;
    esac
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
new=0; have=0
for r in $RANGES; do
    a="${r%%-*}"; b="${r##*-}"
    n="$a"
    while IFS= read -r line || [ -n "$line" ]; do
        if [ -n "$(printf '%s' "$line" | tr -d '[:space:]')" ]; then
            cand="$PREFIX$line"
            if grep -qxF -- "$cand" "$DEST" || grep -qxF -- "$cand" "$TMP"; then
                echo "have $n"; have=$((have + 1))
            else
                printf '%s\n' "$cand" >> "$TMP"; new=$((new + 1))
            fi
        fi
        n=$((n + 1))
    done < <(sed -n "${a},${b}p" "$SRC")
done

if [ "$new" -gt 0 ]; then
    # End the archive with exactly one newline before appending.
    [ -n "$(tail -c 1 "$DEST")" ] && printf '\n' >> "$DEST"
    if [ -n "$HEADING" ] && ! grep -qxF -- "$HEADING" "$DEST"; then
        printf '\n%s\n\n' "$HEADING" >> "$DEST"
    fi
    cat "$TMP" >> "$DEST"
fi
echo "archived $new skipped $have -> $DEST_REL"
