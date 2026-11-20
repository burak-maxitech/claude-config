#!/usr/bin/env bash
# check-known-issues-governance.sh - verify the Known Issues governor's contract
# strings are present in the bx/ plugin source (doc tiering phase 1, v2.10.0),
# and the file-level size budget's (v2.18.0, checks B01-B14).
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
FULL="$REF/mode-update-full.md"
RULES="$REF/doc-structure-rules.md"
CHECKLISTS="$REF/verification-checklists.md"
WRITER="$BX_DIR/agents/save-writer.md"
RESUME="$BX_DIR/skills/resume/SKILL.md"
ARCHIVE='docs/known-issues.md'
ROW_ISSUES='| CLAUDE.md `## Known Issues / Blockers` — issues |'
ROW_RULES='| CLAUDE.md `## Known Issues / Blockers` — standing rules |'
BUDGET_SH="$BX_DIR/skills/save/scripts/size-budget.sh"
ARCHIVE_SH="$BX_DIR/skills/save/scripts/archive-lines.sh"

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
region_has K02 "$FULL" '^### 3[.]0 ' '^### For Each' "$ARCHIVE" "Part 3.0 excludes the archive from the read set"
region_has K03 "$RESUME" '^[*][*]Do NOT read by default' '^---' "$ARCHIVE" "/bx:resume do-not-read list names the archive"
region_has K13 "$FULL" '^### 7[.]7 ' '^### 7[.]8 ' "$ARCHIVE" "Part 7.7 rotation covers the archive"
has K16 "$SECTIONS" "$ARCHIVE" "claude-md-sections.md cites the archive"

echo "--- D2: relocate, never delete ---"
lacks K04 "$UPDATE" 'Remove resolved issues' "Part 1.7 no longer deletes resolved issues"
lacks K04 "$FULL" 'Remove resolved issues' "Part 1.7 no longer deletes resolved issues"
has K05 "$UPDATE" 'never inferred from' "Part 1.7 forbids inferring resolution from silence"
has K09 "$UPDATE" 'known_issue_moves' "update packet defines known_issue_moves"
has K09 "$WRITER" 'known_issue_moves' "save-writer consumes known_issue_moves"
has K10 "$WRITER" 'archive first, remove second' "save-writer archives before removing"
region_has K15 "$UPDATE" '^### 1[.]7 ' '^### 1[.]8 ' 'pointer line' "Part 1.7 exempts the Session state pointer line"
has K15 "$WRITER" '> Session state:' "save-writer exempts the Session state pointer line"
has K16 "$CHECKLISTS" 'known-issues.md' "change report carries a known-issues.md line"

echo "--- D3: the shrinker row ---"
has K06 "$FULL" "$ROW_ISSUES" "Part 7.3 has the Known Issues row for issues"
has K07 "$FULL" "$ROW_RULES" "Part 7.3 has the Known Issues row for standing rules"
has K08 "$FULL" 'covers project-specific sections only' "unshrinkable-by-design clause is narrowed"

echo "--- D7 / D8: derivable content, advisory rung ---"
has K11 "$RULES" 'Derivable facts are recoverable' "doc-structure-rules.md carries the derivable-content clause"
has K12 "$FULL" 'advisory rung 9k' "Part 1.9 names the 9k advisory rung"

echo "--- final-review fixes: classification, entry shape, progress, liveness ---"
has K17 "$FULL" 'status form' "resolved test requires a status form, not the bare word"
has K17 "$FULL" 'When in doubt, the entry is open' "doubtful entries default to open"
has K18 "$FULL" 'lists the titles' "7.4 consent for Known Issues lists the titles per class"
has K23 "$FULL" 'candidates in neither phase' "7.3 leaves packet-owned entries to the writer"
has K23 "$FULL" 'before the writer dispatch' "the --full sweep runs before the writer dispatch"
has K19 "$UPDATE" 'runs to just before the next lead' "an entry spans lead to next lead"
has K19 "$WRITER" 'runs to just before the next lead' "save-writer uses the same entry span"
has K20 "$FULL" 'at least 500 chars longer than its replacement line' "open phase only moves entries whose saving is real"
has K21 "$FULL" 'no longer live' "7.7 treats an Open entry absent from CLAUDE.md as resolved"
has K22 "$UPDATE" 'never the block-replace form' "Known Issues deltas may not block-replace"
has K22 "$WRITER" 'refuse a block-replace' "save-writer refuses a Known Issues block-replace"

echo "--- size budget (v2.18.0): file-level, one consent, every section reachable ---"
has B01 "$SCHEMA" '| CLAUDE.md | ~7k | 9k | 10k |' "doc-schema.md owns the CLAUDE.md budget row"
has B01 "$SCHEMA" '| docs/STATUS.md | ~10k | 13k | 15k |' "doc-schema.md owns the STATUS.md budget row"
has B02 "$BUDGET_SH" 'CLAUDE_BUDGET=10000; CLAUDE_STOP=9000' "size-budget.sh codes the CLAUDE.md numbers"
has B02 "$BUDGET_SH" 'STATUS_BUDGET=15000; STATUS_STOP=13000' "size-budget.sh codes the STATUS.md numbers"
has B03 "$FULL" '| CLAUDE.md | 10k | 9k |' "Part 7 states the CLAUDE.md budget and stop"
has B03 "$FULL" '| docs/STATUS.md | 15k | 13k |' "Part 7 states the STATUS.md budget and stop"
has B04 "$FULL" 'largest first' "relocation walks sections largest first"
has B04 "$FULL" 'unshrinkable by design' "a section with no move is named, not skipped"
for row in 'HEADER (both files)' 'CLAUDE.md `## Key Decisions`' 'CLAUDE.md `## Project Overview`' \
           'CLAUDE.md `## Environment Variables`' 'docs/STATUS.md `## Current Status`' \
           'docs/STATUS.md `## In Progress`' 'docs/STATUS.md `## Next Steps`' \
           'docs/STATUS.md `## Session History`' 'docs/STATUS.md `## Completed`'; do
    has B05 "$FULL" "| $row" "Part 7.3 has a row for $row"
done
has B06 "$FULL" 'One consent for the whole run' "7.4 asks once per run"
has B06 "$FULL" 'bx-size-skips=' "7.4 counts consecutive skips"
has B06 "$BUDGET_SH" 'bx-size-skips=' "size-budget.sh reads the skip counter"
has B07 "$FULL" 'A summary is trimmed once' "7.5 protects summary lines, not whole sections"
lacks B07 "$FULL" 'Part 7 does NOT trim further' "the section-freezing sentinel rule is gone"
has B08 "$FULL" 'Never archive twice' "7.5 forbids re-archiving"
has B08 "$ARCHIVE_SH" 'grep -qxF' "archive-lines.sh skips lines the archive already holds"
region_has B09 "$FULL" '^### 7[.]7 ' '^### 7[.]8 ' 'docs/next-steps-backlog.md' "Part 7.7 rotation covers the backlog"
lacks B09 "$FULL" 'is NOT rotated' "the backlog's rotation exemption is gone"
has B10 "$FULL" 'that has no `paths:`' "unscoped rules files are refused as a destination"
has B10 "$FULL" 'lead stays, reason moves' "global rules keep their lead"
has B11 "$WRITER" '250 chars at most' "save-writer caps the Last Updated line"
has B11 "$WRITER" 'Replace the old line whole' "save-writer never carries the old line forward"
has B11 "$UPDATE" 'are not deltas' "the packet no longer sends Last Updated as a delta"
has B12 "$RESUME" 'by section, never whole' "/bx:resume reads STATUS.md by section"
has B12 "$RESUME" 'Size budget:' "/bx:resume prints the size-budget line"
has B13 "$UPDATE" 'so no content moves' "--silent moves nothing in Part 7"

echo "--- drift sweep: retired caps and thresholds ---"
drift=0
while IFS= read -r hit; do
    [ -n "$hit" ] || continue
    fail "B14 retired number in ${hit%%:*}: ${hit#*:}"
    drift=1
done < <(cd "$BX_DIR" && grep -rnE 'soft cap|12k soft|20k soft|threshold 4000|\(8000\)|4000 chars|2500 chars' \
    skills/save/references skills/resume agents/save-writer.md 2>/dev/null | cut -c1-160)
[ "$drift" -eq 0 ] && pass "B14 no retired cap or per-section threshold under save/, resume/, save-writer"

echo ""
if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES governance check(s) failed."; exit 1; fi
echo "All Known Issues governance checks passed."
