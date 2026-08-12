#!/usr/bin/env bash
# test-session-color.sh — unit checks for cc_session_color.
# Run: bash .claude/scripts/tests/test-session-color.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "$SCRIPT_DIR/../session-color.sh"

FAILURES=0
assert_equal() {  # expected, actual, message
    if [ "$1" = "$2" ]; then
        echo "  PASS  $3"
    else
        echo "  FAIL  $3 (expected '$1', got '$2')"
        FAILURES=$((FAILURES + 1))
    fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --- Fresh registry: sequential assignment, stable re-reads ---
REG1="$TMP/registry-1"
assert_equal "cyan"  "$(cc_session_color alpha "$REG1")" "first project gets cyan"
assert_equal "green" "$(cc_session_color beta  "$REG1")" "second project gets green"
assert_equal "cyan"  "$(cc_session_color alpha "$REG1")" "known project keeps its color"
assert_equal "1" "$(grep -c '^alpha=' "$REG1")" "known project is not appended twice"
assert_equal "1" "$(head -n 1 "$REG1" | grep -c '^#')" "registry gets a header comment"

# --- Malformed lines are ignored, not fatal ---
REG2="$TMP/registry-2"
printf '%s\n' '# header' '' 'garbage-no-separator' 'weird=notacolor' 'a=b=c' 'alpha=cyan' > "$REG2"
assert_equal "cyan"  "$(cc_session_color alpha "$REG2")" "valid entry survives malformed neighbours"
assert_equal "green" "$(cc_session_color beta  "$REG2")" "malformed lines do not consume colors"

# --- Palette exhausted: least-used wins, ties broken by palette order ---
REG3="$TMP/registry-3"
printf '%s\n' '# header' 'p1=cyan' 'p2=green' 'p3=blue' 'p4=purple' \
              'p5=orange' 'p6=pink' 'p7=yellow' 'p8=red' 'p9=cyan' > "$REG3"
assert_equal "green" "$(cc_session_color p10 "$REG3")" "ninth project reuses the least-used color"

# --- Unwritable registry degrades to no color ---
BLOCKER="$TMP/blocker"
echo "this is a file, not a directory" > "$BLOCKER"
assert_equal "" "$(cc_session_color alpha "$BLOCKER/registry")" "unwritable registry prints nothing"

if [ "$FAILURES" -gt 0 ]; then echo ""; echo "$FAILURES check(s) failed."; exit 1; fi
echo ""; echo "All checks passed."
