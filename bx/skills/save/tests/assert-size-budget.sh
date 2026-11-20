#!/usr/bin/env bash
# assert-size-budget.sh - check a repo after a `/bx:save --full` size-budget run
# (mode-update-full.md Part 7): both live files within budget, both Last Updated
# lines capped, and -- given a copy from before the run -- nothing lost and
# nothing archived twice.
#
# Usage: assert-size-budget.sh <repo> [--before <dir>] [--expect-clean] [--allow-over <file>]
#   --before <dir>     a copy of the repo taken before the run (needs CLAUDE.md and
#                      docs/STATUS.md). Enables the no-loss and no-duplicate checks.
#   --expect-clean     the working tree must be clean: use it after committing a
#                      first run and running a second, to prove the second was a no-op.
#   --allow-over FILE  FILE (CLAUDE.md or docs/STATUS.md) may stay over budget, for a
#                      repo whose remainder is unshrinkable by design. Repeatable.
#
# No-loss rule: every line of 25+ chars that was in a live file before and is not
# in that file now must appear, byte for byte, somewhere under CLAUDE.md, docs/
# or .claude/rules/. A shrinker that rewords what it archives fails here.
#
# Exit 0 = all checks passed. Exit 1 = at least one failed. Exit 2 = bad usage.
# bash 3.2 compatible.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUDGET_SH="$SCRIPT_DIR/../scripts/size-budget.sh"

REPO=""; BEFORE=""; EXPECT_CLEAN=0; ALLOW=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --before) BEFORE="${2:?--before needs a directory}"; shift 2 ;;
        --expect-clean) EXPECT_CLEAN=1; shift ;;
        --allow-over) ALLOW="$ALLOW ${2:?--allow-over needs a file}"; shift 2 ;;
        -*) echo "unknown flag: $1" >&2; exit 2 ;;
        *) REPO="$1"; shift ;;
    esac
done
[ -n "$REPO" ] && [ -d "$REPO" ] || { echo "usage: assert-size-budget.sh <repo> [--before <dir>] [--expect-clean] [--allow-over <file>]" >&2; exit 2; }
[ -z "$BEFORE" ] || [ -d "$BEFORE" ] || { echo "not a directory: $BEFORE" >&2; exit 2; }

FAILURES=0
pass() { echo "  PASS  $1"; }
fail() { echo "  FAIL  $1"; FAILURES=$((FAILURES + 1)); }

report="$(bash "$BUDGET_SH" "$REPO")" || { echo "size-budget.sh failed"; exit 2; }

echo "--- both live files within budget ---"
for rel in CLAUDE.md docs/STATUS.md; do
    rec="$(printf '%s\n' "$report" | grep "^file $rel " || true)"
    if [ -z "$rec" ]; then fail "$rel is missing"; continue; fi
    # shellcheck disable=SC2086
    set -- $rec
    size="$3"; budget="$4"; state="$6"
    if [ "$state" != "over" ]; then pass "$rel is $size chars (budget $budget, $state)"
    else
        case " $ALLOW " in
            *" $rel "*) pass "$rel is $size chars, over budget $budget (allowed: unshrinkable remainder)" ;;
            *) fail "$rel is $size chars, over its budget of $budget" ;;
        esac
    fi
done

echo "--- Last Updated lines hold one session ---"
for rel in CLAUDE.md docs/STATUS.md; do
    rec="$(printf '%s\n' "$report" | grep "^last_updated $rel " || true)"
    [ -n "$rec" ] || continue
    # shellcheck disable=SC2086
    set -- $rec
    if [ "$5" = "ok" ] && [ "$3" -gt 0 ]; then pass "$rel Last Updated line is $3 chars (cap $4)"
    elif [ "$3" -eq 0 ]; then fail "$rel has no Last Updated line"
    else fail "$rel Last Updated line is $3 chars (cap $4)"; fi
    if awk '/^## /{exit} /^[*]*Last Updated/{print; exit}' "$REPO/$rel" | grep -q 'Earlier'; then
        fail "$rel Last Updated line still names an earlier session"
    fi
done

if [ -n "$BEFORE" ]; then
    echo "--- nothing lost: every line that left a live file is archived verbatim ---"
    ROOTS=""
    for r in CLAUDE.md docs .claude/rules; do [ -e "$REPO/$r" ] && ROOTS="$ROOTS $REPO/$r"; done
    moved_file="$(mktemp)"; trap 'rm -f "$moved_file"' EXIT
    for rel in CLAUDE.md docs/STATUS.md; do
        [ -f "$BEFORE/$rel" ] || { fail "--before has no $rel"; continue; }
        lost=0; moved=0
        while IFS= read -r line || [ -n "$line" ]; do
            [ "${#line}" -ge 25 ] || continue
            grep -qxF -- "$line" "$REPO/$rel" && continue
            moved=$((moved + 1))
            printf '%s\n' "$line" >> "$moved_file"
            # shellcheck disable=SC2086
            if ! grep -rqF -- "$line" $ROOTS 2>/dev/null; then
                lost=$((lost + 1))
                [ "$lost" -le 8 ] && fail "$rel lost a line: $(printf '%s' "$line" | cut -c1-110)"
            fi
        done < "$BEFORE/$rel"
        if [ "$lost" -eq 0 ]; then pass "$rel: $moved lines left or changed, all found verbatim in an archive"
        elif [ "$lost" -gt 8 ]; then fail "$rel lost $lost lines in total"; fi
    done

    echo "--- nothing archived twice ---"
    dup=0
    for arch in docs/next-steps-backlog.md docs/completed-work.md; do
        [ -f "$REPO/$arch" ] || continue
        while IFS= read -r line || [ -n "$line" ]; do
            n="$(grep -cF -- "$line" "$REPO/$arch" || true)"
            if [ "$n" -gt 1 ]; then
                dup=$((dup + 1))
                [ "$dup" -le 5 ] && fail "$arch holds a moved line $n times: $(printf '%s' "$line" | cut -c1-90)"
            fi
        done < "$moved_file"
    done
    [ "$dup" -eq 0 ] && pass "no moved line appears more than once in the backlog or completed-work"
fi

if [ "$EXPECT_CLEAN" -eq 1 ]; then
    echo "--- second run was a no-op ---"
    dirty="$(git -C "$REPO" status --porcelain 2>/dev/null)"
    if [ -z "$dirty" ]; then pass "working tree is clean"
    else fail "working tree changed: $(printf '%s' "$dirty" | head -5 | tr '\n' ' ')"; fi
fi

echo ""
if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES size-budget assertion(s) failed."; exit 1; fi
echo "All size-budget assertions passed."
