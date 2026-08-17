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
INSTR_SECTIONS="Project Overview|Key Decisions|Known Issues / Blockers"

FAILURES=0
pass() { echo "  PASS  $1"; }
fail() { echo "  FAIL  $1"; FAILURES=$((FAILURES + 1)); }

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
fi

# --- Invariants 1 & 2 against the pre-migration snapshot ---
if [ -n "$BEFORE" ] && [ -f "$BEFORE" ]; then
    missing=""
    while IFS= read -r h; do
        # ## Architecture Summary relocates to docs/architecture.md;
        # ## Environment Variables is dropped only when empty.
        case "$h" in
            "## Architecture Summary")
                [ -f "$REPO/docs/architecture.md" ] || missing="$missing '$h'"
                continue ;;
            "## Environment Variables")
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
    # minus a possible empty Environment Variables stub (generously, 200 bytes).
    if [ "$after_bytes" -ge $((before_bytes - 200)) ]; then
        pass "no content loss ($before_bytes -> $after_bytes bytes across files)"
    else
        fail "content loss: $before_bytes -> $after_bytes bytes"
    fi
fi

echo ""
if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES assertion(s) failed."; exit 1; fi
echo "All assertions passed."
