#!/usr/bin/env bash
# test-check-plugin-version-bump.sh - exercise check-plugin-version-bump.sh
# against throwaway git repos. bash 3.2 compatible.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GUARD="$SCRIPT_DIR/check-plugin-version-bump.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

FAILURES=0
pass() { echo "  PASS  $1"; }
fail() { echo "  FAIL  $1"; FAILURES=$((FAILURES + 1)); }

new_repo() {  # <name> -- repo with bx at version 1.0.0, one commit, tagged "base"
    R="$TMP/$1"
    mkdir -p "$R/bx/.claude-plugin" "$R/bx/skills" "$R/docs"
    git -C "$R" init -q .
    git -C "$R" config user.email t@example.com
    git -C "$R" config user.name T
    printf '{\n  "name": "bx",\n  "version": "1.0.0"\n}\n' > "$R/bx/.claude-plugin/plugin.json"
    echo "skill v1" > "$R/bx/skills/a.md"
    echo "doc v1" > "$R/docs/a.md"
    git -C "$R" add -A && git -C "$R" commit -q -m init
    git -C "$R" tag base
}
commit() { git -C "$R" add -A && git -C "$R" commit -q -m "$1"; }
expect() {  # <label> <want-exit> <base> [head]
    ( cd "$R" && bash "$GUARD" "$3" "${4:-HEAD}" > "$TMP/out.txt" 2>&1 ); got=$?
    if [ "$got" -eq "$2" ]; then pass "$1 (exit $got)"
    else fail "$1 -- exit $got, want $2: $(tr '\n' ' ' < "$TMP/out.txt")"; fi
}

new_repo changed-no-bump
echo "skill v2" > "$R/bx/skills/a.md"; commit "edit skill"
expect "bx changed, version unchanged -> blocked" 1 base
if grep -q '1.0.0' "$TMP/out.txt"; then pass "failure message names the stuck version"
else fail "failure message does not name the version"; fi

new_repo changed-with-bump
echo "skill v2" > "$R/bx/skills/a.md"
printf '{\n  "name": "bx",\n  "version": "1.0.1"\n}\n' > "$R/bx/.claude-plugin/plugin.json"
commit "edit skill + bump"
expect "bx changed, version bumped -> allowed" 0 base

new_repo docs-only
echo "doc v2" > "$R/docs/a.md"; commit "edit docs"
expect "only docs changed -> allowed" 0 base

new_repo no-change
expect "nothing changed -> allowed" 0 base

new_repo missing-base
echo "skill v2" > "$R/bx/skills/a.md"; commit "edit skill"
expect "base ref does not exist -> skipped, not blocked" 0 no-such-ref

new_repo zero-base
echo "skill v2" > "$R/bx/skills/a.md"; commit "edit skill"
expect "all-zero base sha (new branch push) -> skipped" 0 0000000000000000000000000000000000000000

new_repo bump-only
printf '{\n  "name": "bx",\n  "version": "1.1.0"\n}\n' > "$R/bx/.claude-plugin/plugin.json"
commit "bump only"
expect "only the version changed -> allowed" 0 base

new_repo plugin-json-removed
git -C "$R" rm -q bx/.claude-plugin/plugin.json; commit "remove manifest"
expect "manifest missing at head -> blocked" 1 base

echo ""
if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES guard test(s) failed."; exit 1; fi
echo "All version-bump guard tests passed."
