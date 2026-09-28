#!/usr/bin/env bash
# check-known-issues-governance.sh - verify the Known Issues governor's contract
# strings are present in the bx/ plugin source (doc tiering phase 1, v2.10.0).
#
# A meta-lint of the plugin's own instruction files, like
# check-doc-rule-consistency.sh. It proves the rules are STATED; only a blind
# rehearsal or a real run proves they are executable.
#
# Usage: check-known-issues-governance.sh [bx-dir]
# Exit 0 = every check passed. Exit 1 = at least one failed.
# bash 3.2 compatible.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BX_DIR="${1:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"
[ -d "$BX_DIR" ] || { echo "bx directory not found: $BX_DIR"; exit 2; }

REF="$BX_DIR/skills/save/references"
SCHEMA="$REF/doc-schema.md"
SECTIONS="$REF/claude-md-sections.md"
UPDATE="$REF/mode-update.md"
RULES="$REF/doc-structure-rules.md"
CHECKLISTS="$REF/verification-checklists.md"
WRITER="$BX_DIR/agents/save-writer.md"
RESUME="$BX_DIR/skills/resume/SKILL.md"
ARCHIVE='docs/known-issues.md'
ROW='| CLAUDE.md `## Known Issues / Blockers` | 4000 chars |'

FAILURES=0
pass() { echo "  PASS  $1"; }
fail() { echo "  FAIL  $1"; FAILURES=$((FAILURES + 1)); }

has() {     # <id> <file> <fixed-string> <description>
    if [ -f "$2" ] && grep -qF -- "$3" "$2"; then pass "$1 $4"
    else fail "$1 $4 -- '$3' not found in ${2#"$BX_DIR"/}"; fi
}
lacks() {   # <id> <file> <fixed-string> <description>
    if [ -f "$2" ] && ! grep -qF -- "$3" "$2"; then pass "$1 $4"
    else fail "$1 $4 -- '$3' still present in ${2#"$BX_DIR"/}"; fi
}
region() {  # <file> <start-regex> <end-regex> -- lines from start up to (not incl.) end
    awk -v s="$2" -v e="$3" '$0 ~ s {f=1} f && $0 ~ e && $0 !~ s {exit} f' "$1"
}
region_has() {  # <id> <file> <start> <end> <fixed-string> <description>
    if [ -f "$2" ] && region "$2" "$3" "$4" | grep -qF -- "$5"; then pass "$1 $6"
    else fail "$1 $6 -- '$5' not found in that region of ${2#"$BX_DIR"/}"; fi
}

echo "--- D1: docs/known-issues.md joins the archive set ---"
n=0; [ -f "$SCHEMA" ] && n="$(grep -cF -- "$ARCHIVE" "$SCHEMA")"
if [ "$n" -ge 3 ]; then pass "K01 doc-schema.md names the archive in layout, set and format ($n lines)"
else fail "K01 doc-schema.md names the archive on $n lines, expected >= 3"; fi
region_has K02 "$UPDATE" '^### 3[.]0 ' '^### For Each' "$ARCHIVE" "Part 3.0 excludes the archive from the read set"
region_has K03 "$RESUME" '^[*][*]Do NOT read by default' '^---' "$ARCHIVE" "/bx:resume do-not-read list names the archive"
region_has K13 "$UPDATE" '^### 7[.]7 ' '^### 7[.]8 ' "$ARCHIVE" "Part 7.7 rotation covers the archive"
has K16 "$SECTIONS" "$ARCHIVE" "claude-md-sections.md cites the archive"

echo "--- D2: relocate, never delete ---"
lacks K04 "$UPDATE" 'Remove resolved issues' "Part 1.7 no longer deletes resolved issues"
has K05 "$UPDATE" 'never inferred from' "Part 1.7 forbids inferring resolution from silence"
has K09 "$UPDATE" 'known_issue_moves' "update packet defines known_issue_moves"
has K09 "$WRITER" 'known_issue_moves' "save-writer consumes known_issue_moves"
has K10 "$WRITER" 'archive first, remove second' "save-writer archives before removing"
region_has K15 "$UPDATE" '^### 1[.]7 ' '^### 1[.]8 ' 'pointer line' "Part 1.7 exempts the Session state pointer line"
has K15 "$WRITER" '> Session state:' "save-writer exempts the Session state pointer line"
has K16 "$CHECKLISTS" 'known-issues.md' "change report carries a known-issues.md line"

echo "--- D3: the shrinker row ---"
has K06 "$UPDATE" "$ROW" "Part 7.3 has the Known Issues row at 4000 chars"
if [ -f "$UPDATE" ] && grep -F -- "$ROW" "$UPDATE" | grep -qF '2500 chars'; then
    pass "K07 the row names the 2500-char resolved target"
else fail "K07 the Known Issues row does not name '2500 chars'"; fi
has K08 "$UPDATE" 'covers project-specific sections only' "tolerated-as-is clause is narrowed"

echo "--- D7 / D8: derivable content, advisory rung ---"
has K11 "$RULES" 'Derivable facts are recoverable' "doc-structure-rules.md carries the derivable-content clause"
has K12 "$UPDATE" 'advisory rung 9k' "Part 1.9 names the 9k advisory rung"

echo "--- drift sweep: Known Issues thresholds ---"
drift=0
while IFS= read -r hit; do
    [ -n "$hit" ] || continue
    file="${hit%%:*}"; rest="${hit#*:}"; line="${rest%%:*}"; text="${rest#*:}"
    for num in $(printf '%s\n' "$text" | grep -oE '[0-9]{4,5} chars' | grep -oE '[0-9]+'); do
        case "$num" in
            4000|2500) ;;
            *) fail "K14 threshold drift in ${file#"$BX_DIR"/}:$line -> '$num chars' beside 'Known Issues' (expected 4000 or 2500)"
               drift=1 ;;
        esac
    done
done < <(cd "$BX_DIR" && grep -rnF 'Known Issues' . --include='*.md' 2>/dev/null)
[ "$drift" -eq 0 ] && pass "K14 no Known Issues threshold drift under ${BX_DIR##*/}/"

echo ""
if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES governance check(s) failed."; exit 1; fi
echo "All Known Issues governance checks passed."
