#!/usr/bin/env bash
# check-doc-rule-consistency.sh - verify the bx doc schema marker string and the
# Environment Variables "populated" rule regex are stated byte-identically
# everywhere they appear in the bx/ plugin source tree.
#
# This is a meta-lint of the PLUGIN'S OWN definition files (doc-schema.md,
# assert-doc-schema.sh, make-fixtures.sh, doc-migrator.md, mode-migrate.md, ...) --
# NOT a check against a migrated target repo, which is assert-doc-schema.sh's job.
# The two scripts stay separate because they scan different trees: this one always
# scans the bx/ plugin source; assert-doc-schema.sh always scans a target repo
# passed as its first argument. Six independent restatements of one rule is
# drift-prone, and drift here means silent content loss during a real migration --
# same hazard class as the marker string itself.
#
# Usage: check-doc-rule-consistency.sh [bx-dir]
#   bx-dir  path to the bx/ plugin tree (default: resolved from this script's own
#           location, three levels up from bx/skills/save/tests/)
#
# Exit 0 = every restatement is byte-identical to the canonical string.
# Exit 1 = a required site lost the rule entirely, or a near-variant of either
#          canonical string was found anywhere under bx-dir.
# bash 3.2 compatible.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BX_DIR="${1:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"
[ -d "$BX_DIR" ] || { echo "bx directory not found: $BX_DIR"; exit 2; }

MARKER='<!-- bx-doc-schema: 2 -->'
RULE='[A-Z][A-Z0-9_]{2,}'

FAILURES=0
pass() { echo "  PASS  $1"; }
fail() { echo "  FAIL  $1"; FAILURES=$((FAILURES + 1)); }
relpath() { printf '%s\n' "${1#"$BX_DIR"/}"; }

# --- Required restatement sites: each MUST contain the canonical string ------
# Catches a site being silently edited away from the rule, or dropped entirely.
# (Not every site restates BOTH strings -- doc-migrator.md restates the marker
# in its "write the marker last" step but never restates the populated-rule
# regex, since it only consumes an already-decided env_vars_disposition.)
MARKER_SITES="$BX_DIR/skills/save/references/doc-schema.md
$BX_DIR/skills/save/tests/assert-doc-schema.sh
$BX_DIR/skills/save/tests/make-fixtures.sh
$BX_DIR/agents/doc-migrator.md"

RULE_SITES="$BX_DIR/skills/save/references/doc-schema.md
$BX_DIR/skills/save/tests/assert-doc-schema.sh
$BX_DIR/skills/save/references/mode-migrate.md"

echo "--- required sites: schema marker ---"
while IFS= read -r f; do
    [ -n "$f" ] || continue
    if [ ! -f "$f" ]; then fail "$(relpath "$f") does not exist"; continue; fi
    if grep -qF "$MARKER" "$f"; then pass "$(relpath "$f") states the canonical marker"
    else fail "$(relpath "$f") is missing the canonical marker '$MARKER'"; fi
done <<EOF
$MARKER_SITES
EOF

echo "--- required sites: populated-rule regex ---"
while IFS= read -r f; do
    [ -n "$f" ] || continue
    if [ ! -f "$f" ]; then fail "$(relpath "$f") does not exist"; continue; fi
    if grep -qF "$RULE" "$f"; then pass "$(relpath "$f") states the canonical regex"
    else fail "$(relpath "$f") is missing the canonical regex '$RULE'"; fi
done <<EOF
$RULE_SITES
EOF

# --- Drift sweep: catch a NEAR-VARIANT anywhere in bx/, not just known sites --
# The required-site checks above only prove the canonical string occurs (or is
# absent) in a fixed list of files. They cannot see a DIFFERENT string sitting
# in a file not on that list, and "absent" alone doesn't show what replaced it.
# This sweep matches the general SHAPE of each pattern anywhere under bx-dir and
# diffs every hit against the canonical string, so a changed quantifier, a
# dropped underscore, or an extra space fails loudly with the offending text
# instead of silently passing as "not found".
echo "--- drift sweep: schema marker shape ---"
drift=0
while IFS= read -r hit; do
    [ -n "$hit" ] || continue
    file="${hit%%:*}"; rest="${hit#*:}"; line="${rest%%:*}"; matched="${rest#*:}"
    if [ "$matched" != "$MARKER" ]; then
        fail "marker drift in $(relpath "$file"):$line -> '$matched' (expected '$MARKER')"
        drift=1
    fi
done < <(grep -rnoE '<!--[[:space:]]*bx-doc-schema:[[:space:]]*[0-9]+[[:space:]]*-->' \
    "$BX_DIR" --include='*.md' --include='*.sh' 2>/dev/null)
[ "$drift" -eq 0 ] && pass "no marker shape-drift found under $(relpath "$BX_DIR")"

echo "--- drift sweep: populated-rule regex shape ---"
drift=0
while IFS= read -r hit; do
    [ -n "$hit" ] || continue
    file="${hit%%:*}"; rest="${hit#*:}"; line="${rest%%:*}"; matched="${rest#*:}"
    if [ "$matched" != "$RULE" ]; then
        fail "regex drift in $(relpath "$file"):$line -> '$matched' (expected '$RULE')"
        drift=1
    fi
done < <(grep -rnoE '\[A-Z\]\[[^]]*\]\{[^}]*\}' \
    "$BX_DIR" --include='*.md' --include='*.sh' 2>/dev/null)
[ "$drift" -eq 0 ] && pass "no regex shape-drift found under $(relpath "$BX_DIR")"

echo ""
if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES consistency failure(s)."; exit 1; fi
echo "All restatements are byte-identical."
