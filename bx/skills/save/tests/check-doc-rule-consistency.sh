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
# passed as its first argument. Several independent restatements of one rule is
# drift-prone, and drift here means silent content loss during a real migration --
# same hazard class as the marker string itself.
#
# Usage: check-doc-rule-consistency.sh [bx-dir]
#   bx-dir  path to the bx/ plugin tree (default: resolved from this script's own
#           location, three levels up from bx/skills/save/tests/)
#
# Exit 0 = every restatement is byte-identical to the canonical string.
# Exit 1 = a required site lost the rule entirely, or a near-variant of either
#          canonical string (or the prose phrase, or the old deprecated regex
#          shape) was found anywhere under bx-dir.
#
# KNOWN GAPS -- what this script does NOT catch (read before trusting a clean
# run more than it warrants):
#   - Prose drift beyond the one anchor phrase checked below. Only the exact
#     substring "three or more consecutive uppercase/digit/underscore" is
#     verified; a rewording anywhere else in the English description (e.g.
#     "erring toward keeping content" changed to something else) is invisible
#     to this script. A human must still read prose diffs to doc-schema.md.
#   - Any restatement that abandons the `[A-Z][A-Z0-9_]{2,}`-shaped regex or
#     the `<!-- key: N -->`-shaped marker entirely (e.g. a plain-English-only
#     restatement, or a differently-punctuated marker) will simply produce no
#     shape-sweep hit and pass silently. The shape sweeps below catch variants
#     of the two established forms, not arbitrary new forms.
#   - A file outside the `*.md`/`*.sh`/`*.ps1` include patterns.
#   - The deprecated star-form sweep flags ANY occurrence of that shape under
#     bx/, including one that legitimately DOCUMENTS the old form in prose
#     (a historical note referencing 79b2411's fix, or this very comment
#     block if it ever quotes the shape directly) -- it cannot distinguish
#     "this is the rule, restated wrong" from "this is prose describing what
#     used to be wrong". A false positive here is an accepted cost of
#     catching the real regression; read a FAIL from this sweep before
#     treating it as a bug.
# bash 3.2 compatible.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BX_DIR="${1:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"
[ -d "$BX_DIR" ] || { echo "bx directory not found: $BX_DIR"; exit 2; }

MARKER='<!-- bx-doc-schema: 2 -->'
RULE='[A-Z][A-Z0-9_]{2,}'
PROSE='three or more consecutive uppercase/digit/underscore'

FAILURES=0
pass() { echo "  PASS  $1"; }
fail() { echo "  FAIL  $1"; FAILURES=$((FAILURES + 1)); }
relpath() { printf '%s\n' "${1#"$BX_DIR"/}"; }

# --- Required restatement sites: each MUST contain the canonical string ------
# Catches a site being silently edited away from the rule, or dropped entirely.
# (Not every site restates every string -- doc-migrator.md restates the marker
# in its "write the marker last" step but never restates the populated-rule
# regex or its prose rationale, since it only consumes an already-decided
# env_vars_disposition.)
MARKER_SITES="$BX_DIR/skills/save/references/doc-schema.md
$BX_DIR/skills/save/tests/assert-doc-schema.sh
$BX_DIR/skills/save/tests/make-fixtures.sh
$BX_DIR/agents/doc-migrator.md"

RULE_SITES="$BX_DIR/skills/save/references/doc-schema.md
$BX_DIR/skills/save/tests/assert-doc-schema.sh
$BX_DIR/skills/save/references/mode-migrate.md"

# Prose rationale is only carried by the two files that explain WHY the rule is
# shaped this way (Ruling 6's history); mode-migrate.md/doc-migrator.md merely
# apply the rule and don't restate the rationale sentence.
PROSE_SITES="$BX_DIR/skills/save/references/doc-schema.md
$BX_DIR/skills/save/tests/assert-doc-schema.sh"

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

echo "--- required sites: prose rationale phrase ---"
while IFS= read -r f; do
    [ -n "$f" ] || continue
    if [ ! -f "$f" ]; then fail "$(relpath "$f") does not exist"; continue; fi
    if grep -qF "$PROSE" "$f"; then pass "$(relpath "$f") states the canonical prose phrase"
    else fail "$(relpath "$f") is missing the canonical prose phrase '$PROSE'"; fi
done <<EOF
$PROSE_SITES
EOF

# --- Drift sweep: catch a NEAR-VARIANT anywhere in bx/, not just known sites --
# The required-site checks above only prove the canonical string occurs (or is
# absent) SOMEWHERE in a fixed list of files -- grep -F is a substring test, so
# it is satisfied even if the canonical text sits inside a larger, DIFFERENT
# string (e.g. wrapped in regex anchors). It cannot see a different string
# sitting in a file not on the list either. This sweep matches the general
# SHAPE of each pattern anywhere under bx-dir and diffs the FULL match against
# the canonical string, so a changed quantifier, a dropped underscore, added
# anchors, or an extra space fails loudly with the offending text instead of
# silently passing as "not found" or "canonical text is in there somewhere".
echo "--- drift sweep: schema marker shape (any '<!-- key: N -->' comment) ---"
drift=0
while IFS= read -r hit; do
    [ -n "$hit" ] || continue
    file="${hit%%:*}"; rest="${hit#*:}"; line="${rest%%:*}"; matched="${rest#*:}"
    if [ "$matched" != "$MARKER" ]; then
        fail "marker drift in $(relpath "$file"):$line -> '$matched' (expected '$MARKER')"
        drift=1
    fi
done < <(grep -rnoE '<!--[[:space:]]*[a-z][a-z0-9-]*:[[:space:]]*[0-9]+[[:space:]]*-->' \
    "$BX_DIR" --include='*.md' --include='*.sh' --include='*.ps1' 2>/dev/null)
[ "$drift" -eq 0 ] && pass "no marker shape-drift found under $(relpath "$BX_DIR")"

echo "--- drift sweep: populated-rule regex shape (anchors included, if present) ---"
drift=0
while IFS= read -r hit; do
    [ -n "$hit" ] || continue
    file="${hit%%:*}"; rest="${hit#*:}"; line="${rest%%:*}"; matched="${rest#*:}"
    if [ "$matched" != "$RULE" ]; then
        fail "regex drift in $(relpath "$file"):$line -> '$matched' (expected '$RULE')"
        drift=1
    fi
done < <(grep -rnoE '\^?\[A-Z\]\[[^]]*\]\{[^}]*\}\$?' \
    "$BX_DIR" --include='*.md' --include='*.sh' --include='*.ps1' 2>/dev/null)
[ "$drift" -eq 0 ] && pass "no regex shape-drift found under $(relpath "$BX_DIR")"

echo "--- drift sweep: deprecated star-form regex (fixed in 79b2411, must not return) ---"
drift=0
while IFS= read -r hit; do
    [ -n "$hit" ] || continue
    file="${hit%%:*}"; rest="${hit#*:}"; line="${rest%%:*}"
    fail "deprecated star-form regex found in $(relpath "$file"):$line -- this exact shape was replaced in 79b2411 because it false-positives/negatives on real env sections; see doc-schema.md"
    drift=1
done < <(grep -rnoE '\^?\[A-Z_\]\[A-Z0-9_\]\*\$?' \
    "$BX_DIR" --include='*.md' --include='*.sh' --include='*.ps1' 2>/dev/null)
[ "$drift" -eq 0 ] && pass "no deprecated star-form regex found under $(relpath "$BX_DIR")"

echo ""
if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES consistency failure(s)."; exit 1; fi
echo "All restatements are byte-identical."
