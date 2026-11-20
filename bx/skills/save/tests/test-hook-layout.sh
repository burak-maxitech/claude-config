#!/usr/bin/env bash
# test-hook-layout.sh - the SessionStart hook must read the state file that
# actually holds the state, and must stop at the next header.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
HOOK="$REPO_ROOT/bx/scripts/session-start-context.sh"
FAILURES=0
pass() { echo "  PASS  $1"; }
fail() { echo "  FAIL  $1"; FAILURES=$((FAILURES + 1)); }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
bash "$REPO_ROOT/bx/skills/save/tests/make-fixtures.sh" "$TMP" > /dev/null

# --- v1: reads Current Status from CLAUDE.md, stops before ## Completed ---
out="$(cd "$TMP/fx-v1" && bash "$HOOK" 2>/dev/null)"
case "$out" in *"## Current Status"*) pass "v1: emits Current Status" ;;
                *) fail "v1: no Current Status block emitted" ;; esac
case "$out" in *"## Completed"*) fail "v1: leaked into ## Completed (range bug)" ;;
                *) pass "v1: stops before ## Completed" ;; esac

# --- v2: reads Current Status from docs/STATUS.md ---
out="$(cd "$TMP/fx-v2" && bash "$HOOK" 2>/dev/null)"
case "$out" in *"## Current Status"*) pass "v2: emits Current Status from STATUS.md" ;;
                *) fail "v2: no Current Status block (still reading CLAUDE.md?)" ;; esac
case "$out" in *"## Completed"*) fail "v2: leaked into ## Completed (range bug)" ;;
                *) pass "v2: stops before ## Completed" ;; esac
case "$out" in *"Widget refactor"*) fail "v2: leaked into ## In Progress" ;;
                *) pass "v2: stops before ## In Progress" ;; esac

# --- caps: a long status table and Last Updated line must not flood the session ---
out="$(cd "$TMP/fx-size-budget" && BX_HOOK_NO_NETWORK=1 bash "$HOOK" 2>/dev/null)"
n="$(printf '%s' "$out" | awk '{n+=length($0)+1} END{print n+0}')"
if [ "$n" -le 3200 ]; then pass "over-budget repo: hook output is $n chars (cap 3000 + notice)"
else fail "over-budget repo: hook output is $n chars"; fi
longest="$(printf '%s\n' "$out" | awk '{if(length($0)>m)m=length($0)} END{print m+0}')"
if [ "$longest" -le 250 ]; then pass "no hook line is longer than 250 chars ($longest)"
else fail "a hook line is $longest chars"; fi

if [ "$FAILURES" -gt 0 ]; then echo ""; echo "$FAILURES check(s) failed."; exit 1; fi
echo ""; echo "All checks passed."
