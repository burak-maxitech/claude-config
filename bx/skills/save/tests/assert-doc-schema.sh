#!/usr/bin/env bash
# assert-doc-schema.sh - verify a repo satisfies the bx doc schema invariants.
#
# Usage: assert-doc-schema.sh <repo> [--expect v0|v1|v2|partial] [--before <file>]
#   --expect  assert the detected layout equals this value
#   --before  path to a copy of the pre-migration CLAUDE.md, enabling the
#             header-conservation and no-content-loss invariants
#
# Exit 0 = every assertion passed. Exit 1 = at least one failed.
# bash 3.2 compatible.

set -uo pipefail

REPO=""; EXPECT=""; BEFORE=""
while [ $# -gt 0 ]; do
    case "$1" in
        --expect) EXPECT="${2:-}"; shift 2 ;;
        --before) BEFORE="${2:-}"; shift 2 ;;
        *) REPO="$1"; shift ;;
    esac
done
[ -n "$REPO" ] || { echo "usage: assert-doc-schema.sh <repo> [--expect V] [--before F]"; exit 2; }

MARKER='<!-- bx-doc-schema: 2 -->'
CLAUDE_MD="$REPO/CLAUDE.md"
STATUS_MD="$REPO/docs/STATUS.md"
STATE_SECTIONS="Current Status|Completed|In Progress|Next Steps|Session History"

FAILURES=0
pass() { echo "  PASS  $1"; }
fail() { echo "  FAIL  $1"; FAILURES=$((FAILURES + 1)); }
skip() { echo "  SKIP  $1"; }

detect() {
    if [ ! -f "$CLAUDE_MD" ]; then echo v0; return; fi
    if grep -qF "$MARKER" "$CLAUDE_MD"; then echo v2; return; fi
    if [ -f "$STATUS_MD" ]; then echo partial; return; fi
    if grep -qE "^## ($STATE_SECTIONS)" "$CLAUDE_MD"; then echo v1; return; fi
    echo v0
}

LAYOUT="$(detect)"
echo "detected layout: $LAYOUT"

if [ -n "$EXPECT" ]; then
    if [ "$LAYOUT" = "$EXPECT" ]; then pass "layout is $EXPECT"
    else fail "layout is $LAYOUT, expected $EXPECT"; fi
fi

# --- Invariant 3: no @path imports (applies to every layout) ---
for f in "$CLAUDE_MD" "$STATUS_MD"; do
    [ -f "$f" ] || continue
    # strip fenced code blocks and inline code spans before scanning
    stripped="$(awk '/^```/{inb=!inb; next} !inb' "$f" | sed 's/`[^`]*`//g')"
    if printf '%s' "$stripped" | grep -qE '(^|[[:space:]])@[A-Za-z0-9_./~-]+'; then
        fail "$(basename "$f") contains an @path import (would force eager load)"
    else
        pass "$(basename "$f") has no @path imports"
    fi
done

if [ "$LAYOUT" = "v2" ]; then
    # --- CLAUDE.md holds instructions only ---
    if grep -qE "^## ($STATE_SECTIONS)" "$CLAUDE_MD"; then
        fail "CLAUDE.md still contains state sections: $(grep -oE "^## ($STATE_SECTIONS)" "$CLAUDE_MD" | tr '\n' ' ')"
    else
        pass "CLAUDE.md contains no state sections"
    fi
    for s in "Project Overview" "Key Decisions" "Known Issues / Blockers"; do
        if grep -qF "## $s" "$CLAUDE_MD"; then pass "CLAUDE.md has ## $s"
        else fail "CLAUDE.md missing ## $s"; fi
    done
    if grep -qF '> Session state: [docs/STATUS.md](docs/STATUS.md)' "$CLAUDE_MD"; then
        pass "CLAUDE.md has the STATUS.md pointer"
    else
        fail "CLAUDE.md missing the '> Session state:' pointer line"
    fi

    # --- STATUS.md holds state ---
    if [ -f "$STATUS_MD" ]; then
        pass "docs/STATUS.md exists"
        for s in "Current Status" "Completed" "In Progress" "Next Steps" "Session History"; do
            if grep -qF "## $s" "$STATUS_MD"; then pass "STATUS.md has ## $s"
            else fail "STATUS.md missing ## $s"; fi
        done
        if grep -qE '^Last Updated' "$STATUS_MD"; then pass "STATUS.md has a Last Updated line"
        else fail "STATUS.md missing Last Updated (staleness signal must follow the state)"; fi
    else
        fail "docs/STATUS.md missing in a v2 repo"
    fi

    # --- Invariant 1: no header appears in both files ---
    if [ -f "$STATUS_MD" ]; then
        dupes="$(comm -12 \
            <(grep -oE '^## .*' "$CLAUDE_MD" | sort -u) \
            <(grep -oE '^## .*' "$STATUS_MD" | sort -u))"
        if [ -z "$dupes" ]; then pass "no header appears in both files"
        else fail "headers duplicated across files: $(printf '%s' "$dupes" | tr '\n' ' ')"; fi
    fi

    # --- STATUS.md section order: the five canonical headers, in file order,
    # must be a SUBSEQUENCE in canonical relative order (Current Status,
    # Completed, In Progress, Next Steps, Session History). Non-canonical
    # headers a real repo may add (e.g. "## Deployment") are simply skipped,
    # not required to sort anywhere -- exact-equality with the canonical five
    # would turn a correct migration of a repo with its own extra STATUS.md
    # section into a verification failure.
    # The comparison is -le, not -lt, so a REPEATED canonical header (equal rank)
    # also fails: an append-instead-of-insert on a resumed run duplicates a
    # section, and a valid file has each rank exactly once (strictly increasing),
    # so legitimate sequences still pass. ---
    if [ -f "$STATUS_MD" ]; then
        order_bad=""
        last_rank=0
        while IFS= read -r h; do
            case "$h" in
                "## Current Status")  rank=1 ;;
                "## Completed")       rank=2 ;;
                "## In Progress")     rank=3 ;;
                "## Next Steps")      rank=4 ;;
                "## Session History") rank=5 ;;
                *) rank=0 ;;
            esac
            [ "$rank" -eq 0 ] && continue
            if [ -z "$order_bad" ] && [ "$rank" -le "$last_rank" ]; then
                order_bad="$h"
            fi
            [ "$rank" -gt "$last_rank" ] && last_rank="$rank"
        done < <(grep -oE '^## .*' "$STATUS_MD")
        if [ -z "$order_bad" ]; then
            pass "STATUS.md canonical sections in relative order"
        else
            fail "STATUS.md section order violated: '$order_bad' is out of position or duplicated"
        fi
    fi
fi

# --- Invariants 1 & 2 against the pre-migration snapshot ---
if [ -n "$BEFORE" ] && [ -f "$BEFORE" ]; then
    # ## Environment Variables is populated iff its body contains a token matching
    # [A-Z][A-Z0-9_]{2,} anywhere -- three or more consecutive uppercase/digit/underscore
    # characters, erring toward keeping content when ambiguous (Invariant 2). This is the
    # same "populated" test doc-schema.md defines; unanchored so a variable name inside a
    # bullet, a table cell, or a KEY=value line still counts. Compute it once against the
    # snapshot so the per-header loop below can enforce it.
    env_body="$(awk '/^## Environment Variables/{f=1; next} /^## /{f=0} f' "$BEFORE")"
    env_populated=0
    if printf '%s\n' "$env_body" | grep -qE '[A-Z][A-Z0-9_]{2,}'; then
        env_populated=1
    fi

    missing=""
    while IFS= read -r h; do
        # ## Architecture Summary relocates to docs/architecture.md;
        # ## Environment Variables is dropped whenever it is UNPOPULATED (env_populated,
        # above) -- which is not the same as empty: an unpopulated body is usually prose
        # that simply names no variable, e.g. "None required." It is still dropped.
        case "$h" in
            "## Architecture Summary")
                [ -f "$REPO/docs/architecture.md" ] || missing="$missing '$h'"
                continue ;;
            "## Environment Variables")
                if [ "$env_populated" -eq 1 ]; then
                    if [ -f "$CLAUDE_MD" ] && grep -qxF "$h" "$CLAUDE_MD"; then
                        :
                    else
                        missing="$missing '$h'"
                    fi
                fi
                continue ;;
        esac
        found=0
        for f in "$CLAUDE_MD" "$STATUS_MD"; do
            [ -f "$f" ] || continue
            grep -qxF "$h" "$f" && found=$((found + 1))
        done
        [ "$found" -eq 1 ] || missing="$missing '$h'(x$found)"
    done < <(grep -oE '^## .*' "$BEFORE" | sort -u)
    if [ -z "$missing" ]; then pass "header conservation: every pre-migration header lands exactly once"
    else fail "header conservation violated:$missing"; fi

    before_bytes="$(wc -c < "$BEFORE" | tr -d ' ')"
    after_bytes=0
    for f in "$CLAUDE_MD" "$STATUS_MD" "$REPO/docs/architecture.md"; do
        [ -f "$f" ] && after_bytes=$((after_bytes + $(wc -c < "$f" | tr -d ' ')))
    done
    # v2 adds a marker, a pointer line and a second Last Updated, so after >= before
    # minus a possibly-dropped UNPOPULATED Environment Variables section (generously,
    # 200 bytes -- such a section is normally a sentence of prose, not an empty stub).
    if [ "$after_bytes" -ge $((before_bytes - 200)) ]; then
        pass "no content loss ($before_bytes -> $after_bytes bytes across files)"
    else
        fail "content loss: $before_bytes -> $after_bytes bytes"
    fi

    # --- Last Updated: value agreement -- ONLY under --before, where the two
    # values ARE equal by construction (Step 3 derives STATUS.md's value from
    # CLAUDE.md's, Step 7 stamps CLAUDE.md with the same date). This must NEVER
    # run outside --before: doc-schema.md gives CLAUDE.md and STATUS.md separate
    # Last Updated lines precisely because they diverge in steady state (CLAUDE.md
    # may sit untouched for weeks while state churns daily). Skip -- do not fail --
    # when CLAUDE.md carries no Last Updated: line at all AND the snapshot had
    # none either -- that is the migrator's defined template-fallback case. If
    # the snapshot DID carry one, its absence afterwards is a migration
    # regression (Step 7 lost the line), and that must FAIL rather than skip. ---
    claude_lu="$([ -f "$CLAUDE_MD" ] && grep -m1 -E '^Last Updated:' "$CLAUDE_MD")"
    status_lu="$([ -f "$STATUS_MD" ] && grep -m1 -E '^Last Updated:' "$STATUS_MD")"
    if [ -z "$claude_lu" ]; then
        if grep -qE '^Last Updated:' "$BEFORE"; then
            fail "Last Updated lost in migration: the --before snapshot carries a 'Last Updated:' line but CLAUDE.md no longer has one"
        else
            skip "Last Updated agreement (neither the snapshot nor CLAUDE.md has a Last Updated: line; migrator's template fallback applies)"
        fi
    elif [ -z "$status_lu" ]; then
        skip "Last Updated agreement (docs/STATUS.md has no Last Updated: line to compare)"
    elif [ "$claude_lu" = "$status_lu" ]; then
        pass "Last Updated agrees between CLAUDE.md and STATUS.md ($claude_lu)"
    else
        fail "Last Updated mismatch: CLAUDE.md has '$claude_lu', STATUS.md has '$status_lu'"
    fi
fi

echo ""
if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES assertion(s) failed."; exit 1; fi
echo "All assertions passed."
