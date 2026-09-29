#!/usr/bin/env bash
# test-known-issues-fixtures.sh - build the Known Issues fixtures and assert
# their sizes make the rehearsal cases valid. A fixture that drifts under a
# threshold silently turns its rehearsal into a no-op.
# Usage: test-known-issues-fixtures.sh
# bash 3.2 compatible.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

FAILURES=0
pass() { echo "  PASS  $1"; }
fail() { echo "  FAIL  $1"; FAILURES=$((FAILURES + 1)); }

bash "$SCRIPT_DIR/make-fixtures.sh" "$TMP" > /dev/null || { echo "make-fixtures.sh failed"; exit 2; }

section_size() {   # <CLAUDE.md> -- chars in ## Known Issues / Blockers (mode-update.md 7.2's count)
    awk '/^## /{f=($0=="## Known Issues / Blockers"); next} f{n+=length($0)+1} END{print n+0}' "$1"
}
resolved_size() {  # <CLAUDE.md> -- chars in entries whose bold lead carries a resolved STATUS FORM (mode-update.md 7.3)
    awk '/^## /{f=($0=="## Known Issues / Blockers"); next}
         f && /^[*][*]/ { lead=$0; sub(/[*][*] .*/, "", lead)
                          low=tolower(lead)
                          if (lead ~ /(^|[^A-Za-z])RESOLVED([^A-Za-z]|$)/ ||
                              low ~ /(^|[^a-z])(is|was|now) resolved( *[(]| by | in |[.:;,]|$)/) n+=length($0)+2 }
         END{print n+0}' "$1"
}
between() {  # <label> <value> <min> <max>
    if [ "$2" -ge "$3" ] && [ "$2" -le "$4" ]; then pass "$1 = $2 (want $3..$4)"
    else fail "$1 = $2 (want $3..$4)"; fi
}

for fx in fx-ki-resolved fx-ki-unresolved fx-ki-rotate; do
    if bash "$SCRIPT_DIR/assert-doc-schema.sh" "$TMP/$fx" --expect v2 > /dev/null; then
        pass "$fx satisfies the v2 schema"
    else fail "$fx fails assert-doc-schema.sh --expect v2"; fi
done

echo "--- fx-ki-resolved: resolved entries alone reach the 2500 target ---"
f="$TMP/fx-ki-resolved/CLAUDE.md"
s="$(section_size "$f")"; r="$(resolved_size "$f")"
between "section size" "$s" 5500 6500
between "resolved chars" "$r" 3600 4200
between "section after moving resolved" "$((s - r))" 1500 2499

echo "--- fx-ki-unresolved: still over 4000 after the resolved entry moves ---"
f="$TMP/fx-ki-unresolved/CLAUDE.md"
s="$(section_size "$f")"; r="$(resolved_size "$f")"
between "section size" "$s" 5500 6800
between "resolved chars (one small entry; traps excluded)" "$r" 300 500
between "section after moving resolved" "$((s - r))" 4001 6500

echo "--- fx-ki-rotate: archive is over the 100k rotation threshold ---"
a="$TMP/fx-ki-rotate/docs/known-issues.md"
between "archive bytes" "$(wc -c < "$a" | tr -d ' ')" 100001 140000
between "entry headers" "$(grep -c '^### ' "$a")" 160 160
between "Open entries" "$(grep -c '^### .* Open, moved ' "$a")" 1 1
between "index of the Open entry" \
    "$(grep '^### ' "$a" | grep -n 'Open, moved' | cut -d: -f1)" 60 60

echo ""
if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES fixture assertion(s) failed."; exit 1; fi
echo "All Known Issues fixtures are valid."
