# bx Doc Tiering, Phase 1 (Known Issues Governor) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give CLAUDE.md's `## Known Issues / Blockers` a destination archive, a relocate-don't-delete lifecycle, and a size shrinker; add the derivable-content clause and a 9k advisory rung. Ships as bx v2.10.0.

**Architecture:** All behavior lives in instruction files (markdown) that `/bx:save` and its `save-writer` subagent execute. Resolved issues travel in a new packet field (`known_issue_moves`) and are archived first, removed second. A deterministic lint script pins every contract string; three new fixtures plus blind rehearsals prove the instructions are executable.

**Tech Stack:** Markdown instruction files, bash 3.2-compatible test scripts (run under Git Bash on Windows), the `claude plugin validate` CLI.

**Spec:** `docs/superpowers/specs/2026-08-24-bx-doc-tiering-design.md` (Status: Decided 2026-09-28). This plan implements D1, D2, D3, D7, D8. D4, D5, D6 are phase 2 and out of scope.

## Global Constraints

- Known Issues threshold is **4000 chars**; resolved-entry shrink target is **2500 chars**. Open entries are moved only while the section is still over **4000**, never to reach 2500.
- An issue is resolved only when the session that resolved it says so. Never inferred from absence of mention.
- Archive first, remove second. No step may remove an entry from CLAUDE.md before its archive append succeeded.
- An open issue moved to the archive always leaves a one-line summary + link in CLAUDE.md.
- The `> Session state: [docs/STATUS.md](docs/STATUS.md)` pointer line is not a Known Issues entry and never moves.
- No automatic path reads an archive in full. Appends use an anchored tail read (Grep for line numbers, then offset-Read).
- No marker bump: this is schema v2 machinery. `<!-- bx-doc-schema: 2 -->` is unchanged.
- The 12k CLAUDE.md soft cap and every existing Part 7 trigger are unchanged. Part 7.1's gate stays: section shrinkers run only when the file is over its soft cap.
- The derivable-content clause applies to `## Project Overview` only, and is advisory: nothing is auto-removed.
- Scripts are bash 3.2 compatible and must not use tools outside coreutils, grep, awk, sed, git.
- `bx/.claude-plugin/plugin.json` `version` must be `2.10.0` and `CHANGELOG.md` must carry a `2.10.0` entry before the branch merges. Intermediate commits on the feature branch do not bump.
- Use `git -C /c/Development/projects/claude-config ...` for every git command. Never `cd && git`.
- Commit messages end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

## Deviations from the spec (flagged for review)

1. **Archive layout.** Spec D2 says resolved issues land "under a `## Resolved` heading". This plan uses one chronological list of `### ` entries whose header carries the status (`Resolved S<N>` or `Open, moved S<N>`). Reason: the archive holds both kinds (decision pass, open question 2), and two `## ` sections would make every append to the first section a mid-file insert, breaking the anchored-tail-append rule and Part 7.7's oldest-from-the-top cut.
2. **Rotation protects open entries.** Part 7.7 rotation of `docs/known-issues.md` never cuts past the first `Open` entry, because CLAUDE.md links to it and volumes are read by nothing.
3. **D7 wording.** The spec's clause says "may leave T1". The tier vocabulary (T1/T2/T3) is phase 2, so the clause says "may leave CLAUDE.md".

## Review Focus

1. **Pointer line inside the measured section.** The `> Session state:` line sits physically after Known Issues, so awk counts it in the section. Expected: it is never treated as an entry, never moved, never deleted. Pinned by K15 (Task 1) and the rehearsal checks in Task 6.
2. **The word "resolved" outside the lead.** An open entry whose body says "was resolved upstream but regressed", or whose lead says "still unresolved". Expected: both stay open. Pinned by the `fx-ki-unresolved` fixture (Task 1) and rehearsal R2 (Task 6).
3. **Section body is `None currently.`** Expected: zero entries, shrinker is a no-op, and the line is replaced when the first issue arrives and restored when the last one leaves. Pinned by rehearsal R3's second packet (Task 6).
4. **`docs/known-issues.md` does not exist yet.** Expected: created with its header, first entry appended after the `---` line. Pinned by rehearsal R3 (Task 6), which starts with no archive.
5. **Entry text drifted since Step 0.** The removal `old_string` no longer matches. Expected: archive copy stays, CLAUDE.md untouched, a `warnings:` line, no fuzzy match. Pinned by rehearsal R3's third packet (Task 6).

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `bx/skills/save/tests/check-known-issues-governance.sh` | Create | Lint: every contract string of this feature is present in the plugin source |
| `bx/skills/save/tests/test-known-issues-fixtures.sh` | Create | Builds fixtures and asserts their sizes make the rehearsal cases valid |
| `bx/skills/save/tests/make-fixtures.sh` | Modify | Three new fixtures: `fx-ki-resolved`, `fx-ki-unresolved`, `fx-ki-rotate` |
| `bx/skills/save/references/doc-schema.md` | Modify | Owner: archive set gains `docs/known-issues.md`; owns its format |
| `bx/skills/save/references/claude-md-sections.md` | Modify | Section list cites the archive |
| `bx/skills/save/references/mode-update.md` | Modify | Owner: Part 1.7 lifecycle, packet field, Part 1.9 rung, Part 7.3 row, Part 7.7 rotation, drift lines |
| `bx/agents/save-writer.md` | Modify | New step 8: archive first, remove second |
| `bx/skills/save/references/verification-checklists.md` | Modify | Change-report line and checklist item |
| `bx/skills/save/references/doc-structure-rules.md` | Modify | Derivable-content clause |
| `bx/skills/resume/SKILL.md` | Modify | Do-not-read list and Quick Reference row |
| `README.md`, `CHANGELOG.md`, `bx/.claude-plugin/plugin.json` | Modify | Release |

---

### Task 1: Test infrastructure (lint, fixtures, fixture test)

**Files:**
- Create: `bx/skills/save/tests/check-known-issues-governance.sh`
- Create: `bx/skills/save/tests/test-known-issues-fixtures.sh`
- Modify: `bx/skills/save/tests/make-fixtures.sh` (header comment line 2; new functions before the `# fx-v0` block at line 413; new fixture blocks before the final `echo ""` at line 499)

**Interfaces:**
- Produces: lint check ids `K01`..`K16`, each printed as `  PASS  K<nn> ...` or `  FAIL  K<nn> ...`. Later tasks name the ids they turn green.
- Produces: fixtures `fx-ki-resolved`, `fx-ki-unresolved`, `fx-ki-rotate` under `<dest>/`.

- [ ] **Step 1: Create the feature branch**

```bash
git -C /c/Development/projects/claude-config checkout -b feat/doc-tiering-phase1
```

- [ ] **Step 2: Write the lint script**

Create `bx/skills/save/tests/check-known-issues-governance.sh`:

```bash
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
region_has K02 "$UPDATE" '^### 3\.0 ' '^### For Each' "$ARCHIVE" "Part 3.0 excludes the archive from the read set"
region_has K03 "$RESUME" '^\*\*Do NOT read by default' '^---' "$ARCHIVE" "/bx:resume do-not-read list names the archive"
region_has K13 "$UPDATE" '^### 7\.7 ' '^### 7\.8 ' "$ARCHIVE" "Part 7.7 rotation covers the archive"
has K16 "$SECTIONS" "$ARCHIVE" "claude-md-sections.md cites the archive"

echo "--- D2: relocate, never delete ---"
lacks K04 "$UPDATE" 'Remove resolved issues' "Part 1.7 no longer deletes resolved issues"
has K05 "$UPDATE" 'never inferred from' "Part 1.7 forbids inferring resolution from silence"
has K09 "$UPDATE" 'known_issue_moves' "update packet defines known_issue_moves"
has K09 "$WRITER" 'known_issue_moves' "save-writer consumes known_issue_moves"
has K10 "$WRITER" 'archive first, remove second' "save-writer archives before removing"
region_has K15 "$UPDATE" '^### 1\.7 ' '^### 1\.8 ' 'pointer line' "Part 1.7 exempts the Session state pointer line"
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
done < <(grep -rnF 'Known Issues' "$BX_DIR" --include='*.md' 2>/dev/null)
[ "$drift" -eq 0 ] && pass "K14 no Known Issues threshold drift under ${BX_DIR##*/}/"

echo ""
if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES governance check(s) failed."; exit 1; fi
echo "All Known Issues governance checks passed."
```

- [ ] **Step 3: Run the lint to verify it fails**

Run: `bash bx/skills/save/tests/check-known-issues-governance.sh; echo "exit=$?"`
Expected: `exit=1`. Every check FAILs except `K14` (PASS: no thresholds exist yet to drift). `K04` FAILs with `'Remove resolved issues' still present`.

- [ ] **Step 4: Add the fixture builders to make-fixtures.sh**

Change line 2 from `# make-fixtures.sh - build the ten doc-schema fixture repos.` to:

```bash
# make-fixtures.sh - build the thirteen doc-schema fixture repos.
```

Insert these functions immediately before the line `# fx-v0: a git repo with no CLAUDE.md at all`:

```bash
filler() {  # <count> -- <count> 50-char sentences on one line, no trailing newline
    _i=1; _out=""
    while [ "$_i" -le "$1" ]; do
        _out="${_out}Detail $(printf '%02d' "$_i") of this issue, kept for fixture weight. "
        _i=$((_i + 1))
    done
    printf '%s' "$_out"
}

ki_head() {  # <path> -- v2 CLAUDE.md up to and including the Known Issues header
    cat > "$1/CLAUDE.md" <<'MD'
<!-- bx-doc-schema: 2 -->
# CLAUDE.md

Last Updated: 2026-08-01 (Session 9)

## Project Overview

Fixture project for the Known Issues governor.

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Use widgets | They compose better than gadgets. |

> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)

## Known Issues / Blockers

MD
}

ki_entry() {  # <path> <lead> <filler-count> [extra-sentence]
    printf '**%s** %s%s\n\n' "$2" "$(filler "$3")" "${4:-}" >> "$1/CLAUDE.md"
}

ki_tail() {  # <path> -- the pointer line, then a v2 STATUS.md
    printf '%s\n' '> Session state: [docs/STATUS.md](docs/STATUS.md)' >> "$1/CLAUDE.md"
    mkdir -p "$1/docs"
    cat > "$1/docs/STATUS.md" <<'MD'
# Project Status

> Session state for `/bx:resume`. Instructions live in [CLAUDE.md](../CLAUDE.md).

Last Updated: 2026-08-01 (Session 9)

## Current Status

| Area | Status |
|------|--------|
| Widgets | Complete |

## Completed

2 tasks completed. See [completed-work.md](completed-work.md) for full checklist.

## In Progress

**Widget refactor** — halfway through, see `src/widget.py`.

## Next Steps

1. Finish the widget refactor

## Session History

> Full history: [session-history.md](session-history.md)

### Last Session (Session 9) - 2026-08-01
- Built the widget
MD
}

write_ki_rotate_archive() {  # <path> -- a >100k docs/known-issues.md, Open entry at #60
    mkdir -p "$1/docs"
    cat > "$1/docs/known-issues.md" <<'MD'
# Known Issues Archive

> Issues moved out of [CLAUDE.md](../CLAUDE.md) by `/bx:save`. `Resolved` entries are
> history; `Open` entries are still live and linked from CLAUDE.md.

---
MD
    _n=1
    while [ "$_n" -le 160 ]; do
        if [ "$_n" -eq 60 ]; then _hdr="### Issue $_n — Open, moved S$_n (2026-01-01)"
        else _hdr="### Issue $_n — Resolved S$_n (2026-01-01)"; fi
        printf '\n%s\n\n**Issue %s (S%s).** %s\n' "$_hdr" "$_n" "$_n" "$(filler 13)" >> "$1/docs/known-issues.md"
        _n=$((_n + 1))
    done
}
```

Insert these fixture blocks immediately before the final `echo ""` / `echo "Fixtures built in $DEST"` pair:

```bash
# fx-ki-resolved: v2, Known Issues ~6k with three RESOLVED entries (~3.9k) and
# three open ones (~2.1k). The 7.3 shrinker must get under 2500 by moving the
# resolved entries ONLY.
init_repo "$DEST/fx-ki-resolved"
ki_head  "$DEST/fx-ki-resolved"
ki_entry "$DEST/fx-ki-resolved" "Widget cache corruption is RESOLVED (S3)." 25
ki_entry "$DEST/fx-ki-resolved" "Gadget sync stalls on large batches (S4)." 13
ki_entry "$DEST/fx-ki-resolved" "The S5 import deadlock is resolved (S6)." 25
ki_entry "$DEST/fx-ki-resolved" "Exporter drops the final row (S7)." 13
ki_entry "$DEST/fx-ki-resolved" "Flaky auth refresh: RESOLVED by retry (S8)." 25
ki_entry "$DEST/fx-ki-resolved" "Report totals are off by one (S9)." 13
ki_tail  "$DEST/fx-ki-resolved"
stub_docs "$DEST/fx-ki-resolved" completed-work key-decisions session-history
commit_all "$DEST/fx-ki-resolved" "init"
echo "fx-ki-resolved (v2, Known Issues ~6k, three resolved entries)"

# fx-ki-unresolved: v2, Known Issues ~6k with ONE small resolved entry and seven
# open ones. After the resolved entry moves the section is still over 4000, so
# the shrinker moves the oldest OPEN entries until it is under 4000 -- not 2500.
# Two traps: entry 2's lead says "unresolved", entry 3's BODY says "resolved".
# Both are open.
init_repo "$DEST/fx-ki-unresolved"
ki_head  "$DEST/fx-ki-unresolved"
ki_entry "$DEST/fx-ki-unresolved" "Widget cache corruption is RESOLVED (S3)." 7
ki_entry "$DEST/fx-ki-unresolved" "Gadget sync stall is still unresolved (S4)." 15
ki_entry "$DEST/fx-ki-unresolved" "Importer deadlock under load (S5)." 15 "It was resolved upstream once, then regressed."
ki_entry "$DEST/fx-ki-unresolved" "Exporter drops the final row (S6)." 15
ki_entry "$DEST/fx-ki-unresolved" "Report totals are off by one (S7)." 15
ki_entry "$DEST/fx-ki-unresolved" "Auth refresh is flaky on cold start (S8)." 15
ki_entry "$DEST/fx-ki-unresolved" "Scheduler skips the DST hour (S9)." 15
ki_entry "$DEST/fx-ki-unresolved" "Uploads over 2GB time out (S9)." 15
ki_tail  "$DEST/fx-ki-unresolved"
stub_docs "$DEST/fx-ki-unresolved" completed-work key-decisions session-history
commit_all "$DEST/fx-ki-unresolved" "init"
echo "fx-ki-unresolved (v2, Known Issues ~6k, one resolved entry, two lead/body traps)"

# fx-ki-rotate: v2 with a >100k docs/known-issues.md whose 60th entry is Open.
# Part 7.7 must cut entries 1-59 only: the cut never extends past the first
# Open entry, even though the live file then stays over the 50k target.
init_repo "$DEST/fx-ki-rotate"
write_v2_pair "$DEST/fx-ki-rotate"
write_ki_rotate_archive "$DEST/fx-ki-rotate"
commit_all "$DEST/fx-ki-rotate" "init"
echo "fx-ki-rotate   (v2, docs/known-issues.md >100k, Open entry at #60)"
```

- [ ] **Step 5: Write the fixture test**

Create `bx/skills/save/tests/test-known-issues-fixtures.sh`:

```bash
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
resolved_size() {  # <CLAUDE.md> -- chars in entries whose bold lead holds the word "resolved"
    awk '/^## /{f=($0=="## Known Issues / Blockers"); next}
         f && /^\*\*/ { lead=$0; sub(/\*\* .*/, "", lead)
                        if (tolower(lead) ~ /(^|[^a-z])resolved([^a-z]|$)/) n+=length($0)+2 }
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
between "Open entries" "$(grep -c '^### .* — Open, moved ' "$a")" 1 1
between "line number of the Open header's entry index" \
    "$(grep -n '^### ' "$a" | grep -n 'Open, moved' | cut -d: -f1)" 60 60

echo ""
if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES fixture assertion(s) failed."; exit 1; fi
echo "All Known Issues fixtures are valid."
```

- [ ] **Step 6: Run the fixture test to verify it passes**

Run: `bash bx/skills/save/tests/test-known-issues-fixtures.sh; echo "exit=$?"`
Expected: `exit=0`, every line PASS. If a `between` fails, adjust the `filler` counts in Step 4 (each unit is 50 chars) until it passes. Do not widen the ranges.

- [ ] **Step 7: Confirm the existing suites are unaffected**

Run: `bash bx/skills/save/tests/check-doc-rule-consistency.sh; echo "exit=$?"`
Expected: `exit=0`, `All restatements are byte-identical.`

Run: `bash bx/skills/save/tests/test-hook-layout.sh; echo "exit=$?"`
Record the exit code as the baseline. This plan changes nothing that script covers, so Task 7 expects the same code.

- [ ] **Step 8: Commit**

```bash
git -C /c/Development/projects/claude-config add bx/skills/save/tests/
git -C /c/Development/projects/claude-config commit -m "test(save): Known Issues governance lint + three fixtures

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: D1, `docs/known-issues.md` joins the archive set

**Files:**
- Modify: `bx/skills/save/references/doc-schema.md` (v2 layout block; `## Archives`)
- Modify: `bx/skills/save/references/claude-md-sections.md` (item 3; reference files list)
- Modify: `bx/skills/save/references/mode-update.md` (Step 0.2; Save Path intro; Part 3.0; Part 7.5; Part 7.7)
- Modify: `bx/skills/resume/SKILL.md` (do-not-read list; Quick Reference table)

**Interfaces:**
- Produces: the archive path `docs/known-issues.md` and its entry-header format, which Tasks 3 and 4 write to:
  `### <title> — Resolved S<N> (<date>)[, commit <hash>]` and `### <title> — Open, moved S<N> (<date>)`.
- Turns green: K01, K02, K03, K13, K16 (the `claude-md-sections.md` half).

- [ ] **Step 1: Verify the target checks fail**

Run: `bash bx/skills/save/tests/check-known-issues-governance.sh | grep -E 'K0[123]|K13|K16'`
Expected: all FAIL.

- [ ] **Step 2: Edit doc-schema.md, layout block**

Replace:

```
    docs/session-history.md      unchanged archive
```

with:

```
    docs/session-history.md      unchanged archive
    docs/known-issues.md         issues moved out of CLAUDE.md; created on demand
```

- [ ] **Step 3: Edit doc-schema.md, Archives section**

Replace:

```
The canonical set of **auto-managed archives**: `docs/session-history.md`,
`docs/key-decisions.md`, `docs/completed-work.md`, plus `docs/next-steps-backlog.md`
(created on demand by a size-pressure shrinker). Exclusion lists elsewhere — `mode-update.md`
```

with:

```
The canonical set of **auto-managed archives**: `docs/session-history.md`,
`docs/key-decisions.md`, `docs/completed-work.md`, `docs/known-issues.md` (created on
demand, the first time an issue leaves CLAUDE.md), plus `docs/next-steps-backlog.md`
(created on demand by a size-pressure shrinker). Exclusion lists elsewhere — `mode-update.md`
```

Then append this paragraph at the end of the `## Archives` section (after the paragraph ending `they are grep-on-demand history.`):

```

`docs/known-issues.md` holds every issue that has left CLAUDE.md's
`## Known Issues / Blockers`, oldest first, one `### ` entry each. The entry header carries
the status: `### <title> — Resolved S<N> (<date>)`, optionally `, commit <hash>`, or
`### <title> — Open, moved S<N> (<date>)`. The entry body is the issue's text, verbatim. A
`Resolved` entry leaves nothing behind in CLAUDE.md; an `Open` entry always leaves a one-line
summary + link there. This section owns the file's existence and format. Its lifecycle is
owned by `mode-update.md`: Part 1.7 (relocation) and Part 7.3 (size threshold).
```

- [ ] **Step 4: Edit claude-md-sections.md**

Replace:

```
3. `## Known Issues / Blockers` — current blockers
```

with:

```
3. `## Known Issues / Blockers` — current blockers; resolved ones move to
   `docs/known-issues.md` (`mode-update.md` Part 1.7), never deleted
```

Replace:

```
- `docs/session-history.md` — detailed session archive
```

with:

```
- `docs/session-history.md` — detailed session archive
- `docs/known-issues.md` — issues moved out of CLAUDE.md (resolved, or open under size pressure)
```

- [ ] **Step 5: Edit mode-update.md, Step 0.2 and the Save Path intro**

In the Step 0.2 bullet that begins `**CLAUDE.md size + docs/STATUS.md size`, replace:

```
`wc -c CLAUDE.md docs/STATUS.md docs/session-history.md docs/key-decisions.md docs/completed-work.md`
```

with:

```
`wc -c CLAUDE.md docs/STATUS.md docs/session-history.md docs/key-decisions.md docs/completed-work.md docs/known-issues.md`
```

In the Save Path intro paragraph, replace:

```
The orchestrator does NOT edit `CLAUDE.md`, `docs/STATUS.md`, `session-history.md`, `completed-work.md`, or `key-decisions.md` itself
```

with:

```
The orchestrator does NOT edit `CLAUDE.md`, `docs/STATUS.md`, `session-history.md`, `completed-work.md`, `key-decisions.md`, or `known-issues.md` itself
```

- [ ] **Step 6: Edit mode-update.md, Part 3.0 exclusion list**

Replace:

```
2. **Exclude the auto-managed archives from the read set:** `docs/session-history.md`,
   `docs/key-decisions.md`, `docs/completed-work.md`, `docs/next-steps-backlog.md` — the
   canonical set is defined in `doc-schema.md`'s Archives section; this list follows it.
```

with:

```
2. **Exclude the auto-managed archives from the read set:** `docs/session-history.md`,
   `docs/key-decisions.md`, `docs/completed-work.md`, `docs/known-issues.md`,
   `docs/next-steps-backlog.md` — the
   canonical set is defined in `doc-schema.md`'s Archives section; this list follows it.
```

- [ ] **Step 7: Edit mode-update.md, Part 7.5 rule 1**

Replace:

```
The `docs/architecture.md`, `docs/next-steps-backlog.md`, and `docs/completed-work.md` files are the destinations.
```

with:

```
The `docs/architecture.md`, `docs/next-steps-backlog.md`, `docs/completed-work.md`, `docs/key-decisions.md`, and `docs/known-issues.md` files are the destinations.
```

- [ ] **Step 8: Edit mode-update.md, Part 7.7**

Replace:

```
The three history archives grow forever by design — `docs/session-history.md` (one line per
rolled-up session plus 5 full entries), `docs/key-decisions.md` (one row per decision),
`docs/completed-work.md` (several lines per session). No automatic path reads them in full
```

with:

```
The four history archives grow forever by design — `docs/session-history.md` (one line per
rolled-up session plus 5 full entries), `docs/key-decisions.md` (one row per decision),
`docs/completed-work.md` (several lines per session), `docs/known-issues.md` (one `### `
entry per issue that left CLAUDE.md). No automatic path reads them in full
```

Replace:

```
Measure the three archives (`wc -c`, omitting any that do not exist). For each file over
```

with:

```
Measure the four archives (`wc -c`, omitting any that do not exist). For each file over
```

Replace:

```
   (all three archives order oldest-first), cutting only at whole-entry
   boundaries — a `### Session` header line, a complete `|` table row, a whole checklist
   line — until the live file would be at or under **50k chars** — the minimum number of
```

with:

```
   (all four archives order oldest-first), cutting only at whole-entry
   boundaries — a `### Session` header line, a complete `|` table row, a whole checklist
   line, a `### ` entry header (known-issues) — until the live file would be at or under
   **50k chars** — the minimum number of
```

Replace:

```
   Part 6's target), this session's just-appended items (completed-work). Never compress,
```

with:

```
   Part 6's target), this session's just-appended items (completed-work), and in
   known-issues every entry from the first `Open`-tagged header onward — the cut never
   extends past the first `Open` entry, even when that leaves the live file over 50k,
   because CLAUDE.md links to `Open` entries and a volume is read by nothing. If the first
   entry is `Open`, nothing moves: report that and take no action. Never compress,
```

- [ ] **Step 9: Edit resume SKILL.md**

Replace:

```
**Do NOT read by default:** `docs/session-history.md`, `docs/completed-work.md`,
`docs/key-decisions.md`, `docs/architecture.md`. These are archives; `deep` mode reads them.
```

with:

```
**Do NOT read by default:** `docs/session-history.md`, `docs/completed-work.md`,
`docs/key-decisions.md`, `docs/architecture.md`, `docs/known-issues.md`. These are archives;
`deep` mode reads them, except `docs/known-issues.md`, which is grep-on-demand in every mode.
```

In the Quick Reference table, replace:

```
| Need full decision log | Check `docs/key-decisions.md` |
```

with:

```
| Need full decision log | Check `docs/key-decisions.md` |
| Need a resolved or moved issue | Grep `docs/known-issues.md` |
```

- [ ] **Step 10: Run the lint**

Run: `bash bx/skills/save/tests/check-known-issues-governance.sh | grep -E 'K0[123]|K13|K16'`
Expected: `K01`, `K02`, `K03`, `K13` PASS; `K16 claude-md-sections.md cites the archive` PASS; `K16 change report carries a known-issues.md line` still FAIL (Task 3).

Run: `bash bx/skills/save/tests/check-doc-rule-consistency.sh; echo "exit=$?"`
Expected: `exit=0`.

- [ ] **Step 11: Commit**

```bash
git -C /c/Development/projects/claude-config add bx/skills/save/references/doc-schema.md bx/skills/save/references/claude-md-sections.md bx/skills/save/references/mode-update.md bx/skills/resume/SKILL.md
git -C /c/Development/projects/claude-config commit -m "feat(save): docs/known-issues.md joins the canonical archive set (D1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: D2, Part 1.7 relocates instead of deleting

**Files:**
- Modify: `bx/skills/save/references/mode-update.md` (Update Packet; Dispatch; Part 1 routing table; Part 1.7)
- Modify: `bx/agents/save-writer.md` (frontmatter description; Inputs; new step 8; renumber; Output)
- Modify: `bx/skills/save/references/verification-checklists.md` (change report; UPDATE checklist)

**Interfaces:**
- Consumes: the archive path and header format from Task 2.
- Produces: packet field `known_issue_moves`, a list of items with fields `entry` (string, verbatim), `title` (string, ≤10 words), `status` (`resolved` | `open`), `session` (string, e.g. `S60`), `commit` (short hash or `none`).
- Produces: `save-writer.md` step 8a (the append procedure), which Task 4's shrinker cites.
- Turns green: K04, K05, K09, K10, K15, K16 (the checklist half).

- [ ] **Step 1: Verify the target checks fail**

Run: `bash bx/skills/save/tests/check-known-issues-governance.sh | grep -E 'K04|K05|K09|K10|K15|K16'`
Expected: all FAIL except `K16 claude-md-sections.md cites the archive`.

- [ ] **Step 2: Edit mode-update.md, Update Packet**

In the `claude_md_deltas` bullet, replace:

```
and `## Known Issues / Blockers` (Part 1.7 — a blocker resolved or added this session).
```

with:

```
and `## Known Issues / Blockers` (Part 1.7 — a blocker added or reworded this session; a blocker **resolved** this session goes in `known_issue_moves`, never here).
```

After the `decision_rows` bullet, add:

```
- `known_issue_moves` — a list, **one item per** issue this session resolved (Part 1.7); empty list if none. Each item carries: `entry` (the entry's full text, verbatim from the CLAUDE.md you read in Step 0 — it is both the archive body and the removal `old_string`), `title` (≤10 words, taken from the entry's lead), `status` (`resolved`), `session` (e.g. `S60`), and `commit` (the short hash that resolved it, or `none`).
```

- [ ] **Step 3: Edit mode-update.md, Dispatch**

After the bullet that begins `- **\`warnings:\` non-\`none\`, unmatched delta**`, add:

```
- **`warnings:` non-`none`, unmatched known-issue removal** (the entry was archived, but its text was not found verbatim in CLAUDE.md, so it was not removed) → re-read the affected lines of CLAUDE.md and re-dispatch **only** a `claude_md_deltas` removal for that entry. Do NOT re-send the `known_issue_moves` item — the archive copy already exists.
```

- [ ] **Step 4: Edit mode-update.md, Part 1 routing table**

Replace:

```
| 1.7 Known Issues / Blockers | CLAUDE.md |
```

with:

```
| 1.7 Known Issues / Blockers | CLAUDE.md (+ append to docs/known-issues.md) |
```

- [ ] **Step 5: Edit mode-update.md, Part 1.7**

Replace:

```
### 1.7 Known Issues / Blockers
Target: **CLAUDE.md's `## Known Issues / Blockers` section** (unchanged from v1). Update with any new issues found:
- Add new issues discovered
- Remove resolved issues
- Mark "None currently" if empty
```

with:

```
### 1.7 Known Issues / Blockers
Target: **CLAUDE.md's `## Known Issues / Blockers` section** (unchanged from v1), plus the
`docs/known-issues.md` archive (format owned by `doc-schema.md`'s Archives section).

An **entry** is one blank-line-separated block inside the section: a paragraph, or a
top-level bullet with its continuation lines. The `> Session state:` pointer line that
follows the section is not an entry and never moves.

- **Add** new issues discovered this session, as new entries at the end of the section.
- **Relocate resolved issues; do not delete them.** Put each issue this session resolved in
  the packet's `known_issue_moves` with `status: resolved`, the resolving session, and the
  commit hash where one exists. Do not also write a `claude_md_deltas` removal for it:
  `save-writer` archives the entry first and removes it second, so a failed append can
  never lose it.
- **An issue is resolved when the session that resolved it says so — never inferred from
  absence of mention.** A blocker nobody discussed this session is still a blocker.
- An entry an earlier session marked resolved in place stays where it is on the Save Path.
  Part 7.3's shrinker moves it on `--full`.
- Write `None currently.` when the last entry leaves; replace that line when the first
  entry arrives.
```

- [ ] **Step 6: Edit save-writer.md, frontmatter and Inputs**

In the frontmatter `description`, replace:

```
appends to the session-history / completed-work / key-decisions archives
```

with:

```
appends to the session-history / completed-work / key-decisions / known-issues archives
```

After the `decision_rows` input bullet, add:

```
- `known_issue_moves` — a list of issues leaving CLAUDE.md's `## Known Issues / Blockers` (may be empty). Each item has `entry` (full text, verbatim), `title`, `status` (`resolved` or `open`), `session`, and `commit` (a short hash, or `none`). An item with `status: open` also carries `summary` — the one-line summary + link that replaces the entry in CLAUDE.md.
```

- [ ] **Step 7: Edit save-writer.md, insert step 8 and renumber**

Replace:

```
8. **Do NOT** run rollups, README sync, or auto-memory sync — those stay with the orchestrator (`--full` mode only).
9. **Do NOT** echo any file's full contents back. Return only the change report.

(Steps 4-9 are unaffected by the schema-v1 fallback: `decision_rows` always targets CLAUDE.md and `docs/key-decisions.md`, `session_history_entry` always targets `docs/session-history.md`, and `completed_items` always targets `docs/completed-work.md`, regardless of which schema version steps 2-3 wrote to.)
```

with:

````
8. **If `known_issue_moves` is non-empty**, handle each item in order — **archive first, remove second**:

   a. **Append to `docs/known-issues.md`.** Find the last entry header's line number with one Grep tool call (pattern `^### `, `output_mode: content`, `-n: true`, `-o: true`, `head_limit: 0`; take the final match), offset-Read from that line to the end of the file as your Edit anchor, and append after it with one blank line between entries. Never read the file in full. The appended block, for `status: resolved`:
      ```markdown
      ### <title> — Resolved <session> (<today>), commit <commit>

      <entry, verbatim>
      ```
      Omit `, commit <commit>` when `commit` is `none`. For `status: open` the header is `### <title> — Open, moved <session> (<today>)`. If the file is missing, create it with this header first, and append the first entry after the `---` line:
      ```markdown
      # Known Issues Archive

      > Issues moved out of [CLAUDE.md](../CLAUDE.md) by `/bx:save`. `Resolved` entries are
      > history; `Open` entries are still live and linked from CLAUDE.md.

      ---
      ```
   b. **Only after the append succeeded, remove `entry` from CLAUDE.md** with an exact-string Edit covering the entry and one adjacent blank line. If `entry` is not found verbatim, do NOT fuzzy-match: leave CLAUDE.md unchanged and record an unmatched known-issue removal under `warnings:` (quote the item's `title`). The archive copy stays. A duplicate is harmless; a loss is not.
   c. **For `status: open`**, the removal in (b) is a replacement instead: put the item's `summary` line in the entry's place. An open issue never leaves CLAUDE.md without one.
   d. If the section is left with no entries, write `None currently.` as its body. Never edit or move the `> Session state:` pointer line that follows the section.
9. **Do NOT** run rollups, README sync, or auto-memory sync — those stay with the orchestrator (`--full` mode only).
10. **Do NOT** echo any file's full contents back. Return only the change report.

(Steps 4-10 are unaffected by the schema-v1 fallback: `decision_rows` always targets CLAUDE.md and `docs/key-decisions.md`, `session_history_entry` always targets `docs/session-history.md`, `completed_items` always targets `docs/completed-work.md`, and `known_issue_moves` always targets CLAUDE.md and `docs/known-issues.md`, regardless of which schema version steps 2-3 wrote to.)
````

- [ ] **Step 8: Edit save-writer.md, Output**

Replace:

```
- **`warnings:` compels the orchestrator to act.** An unmatched delta (steps 2-3 above — the orchestrator re-sources the exact string and re-dispatches just that delta), or the schema-v1
```

with:

```
- **`warnings:` compels the orchestrator to act.** An unmatched delta (steps 2-3 above — the orchestrator re-sources the exact string and re-dispatches just that delta), an unmatched known-issue removal (step 8b — the entry is archived but still in CLAUDE.md), or the schema-v1
```

Replace:

```
  docs/key-decisions.md: +<K> rows        # omit line if decision_rows empty
```

with:

```
  docs/key-decisions.md: +<K> rows        # omit line if decision_rows empty
  docs/known-issues.md: +<J> entries      # omit line if known_issue_moves empty
```

- [ ] **Step 9: Edit verification-checklists.md**

Replace:

```
  key-decisions.md     — +N rows              (omit if none)
```

with:

```
  key-decisions.md     — +N rows              (omit if none)
  known-issues.md      — +J entries           (omit if none)
```

Replace:

```
- [ ] New key decisions appended to docs/key-decisions.md
```

with:

```
- [ ] New key decisions appended to docs/key-decisions.md
- [ ] Issues resolved this session were moved to docs/known-issues.md, not deleted; no issue was treated as resolved because it went unmentioned
```

- [ ] **Step 10: Run the lint**

Run: `bash bx/skills/save/tests/check-known-issues-governance.sh | grep -E 'K04|K05|K09|K10|K15|K16'`
Expected: all PASS.

- [ ] **Step 11: Commit**

```bash
git -C /c/Development/projects/claude-config add bx/skills/save/references/mode-update.md bx/skills/save/references/verification-checklists.md bx/agents/save-writer.md
git -C /c/Development/projects/claude-config commit -m "feat(save): resolved issues relocate to docs/known-issues.md, never deleted (D2)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: D3, Known Issues enters the Part 7.3 shrinker table

**Files:**
- Modify: `bx/skills/save/references/mode-update.md` (Step 0.2; drift warning format; Part 7.3)

**Interfaces:**
- Consumes: Part 1.7's entry definition (Task 3); `save-writer.md` step 8a's append procedure and header format (Task 3).
- Turns green: K06, K07, K08. K14 must stay green.

- [ ] **Step 1: Verify the target checks fail**

Run: `bash bx/skills/save/tests/check-known-issues-governance.sh | grep -E 'K06|K07|K08|K14'`
Expected: K06, K07, K08 FAIL; K14 PASS.

- [ ] **Step 2: Add the row to the Part 7.3 table**

Immediately after the table row that begins `| CLAUDE.md \`## Key Decisions\` (any variant`, insert this row (one line):

```
| CLAUDE.md `## Known Issues / Blockers` | 4000 chars | **Resolved-first rollup** — entries and the resolved test are defined under this table. Move resolved entries (topmost first) to `docs/known-issues.md` until the section is under 2500 chars or no resolved entry remains. Only if the section is then still over 4000 chars, move open entries (topmost first) until it is under 4000 chars, leaving in place of each a one-line summary + `→ [docs/known-issues.md](docs/known-issues.md)` link. Never leave an open issue with no trace in CLAUDE.md. |
```

- [ ] **Step 3: Add the definitions and narrow the tolerated clause**

Replace:

```
Sections not in this table (project-specific like `## Quick Commands`, `## Don't Modify`, `## Environment Variables` in CLAUDE.md) are **tolerated as-is** — Part 7 only acts on known shrinkable sections. If a project-specific section is the dominant bloat source, Part 7 reports it but takes no action, deferring to user judgment.
```

with:

```
Sections not in this table (project-specific like `## Quick Commands`, `## Don't Modify`, `## Environment Variables` in CLAUDE.md) are **tolerated as-is** — Part 7 only acts on known shrinkable sections. If a project-specific section is the dominant bloat source, Part 7 reports it but takes no action, deferring to user judgment.
This clause covers project-specific sections only. Every section `claude-md-sections.md` lists as required has a row above, except `## Project Overview`, which has no threshold (7.2 shows `—`; its only governor is Part 1.9's derivable-facts advisory). A required section reaching this clause any other way is a bug in this table: report it as one.

**Known Issues entries.** Entry boundaries are Part 1.7's; the `> Session state:` pointer line is not an entry. An entry is **resolved** iff its lead — the opening bold phrase, or the first sentence when there is none — contains the whole word `resolved`, in any case. `unresolved` is not a match, and the word appearing later in the body does not count. Every other entry is **open**. Topmost = oldest, the same FIFO convention as Part 6.1. Archive each moved entry with the append procedure and header format of `save-writer.md` step 8a — a resolved entry takes the session its lead names, or this session when it names none; an open entry takes `Open, moved S<N>` for this session — and **archive first, remove second**. An open entry already reduced to a one-line summary + link is never moved again (7.5 rule 4). Re-measure the section after each move; stop as soon as the stated bound is met.
```

- [ ] **Step 4: Add the Known Issues drift probe**

In Step 0.2, at the end of the bullet that begins `**CLAUDE.md size + docs/STATUS.md size`, append:

```
 Also measure CLAUDE.md's per-section sizes with Part 7.2's `awk` command (no `sort` needed); the `## Known Issues / Blockers` figure and the largest section's name feed two drift lines below.
```

In the drift warning format block, after the line that begins `>  - CLAUDE.md at [X]k chars (target ~7k, soft cap 12k)`, add:

```
>  - `## Known Issues / Blockers` at [N] chars (threshold 4000) — the resolved-first rollup fires on `--full` once CLAUDE.md is over its soft cap
```

- [ ] **Step 5: Run the lint**

Run: `bash bx/skills/save/tests/check-known-issues-governance.sh | grep -E 'K06|K07|K08|K14'`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git -C /c/Development/projects/claude-config add bx/skills/save/references/mode-update.md
git -C /c/Development/projects/claude-config commit -m "feat(save): Known Issues shrinker, resolved-first, 4000/2500 (D3)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: D7 + D8, derivable-content clause and the 9k advisory rung

**Files:**
- Modify: `bx/skills/save/references/doc-structure-rules.md` (Pruning Is Preservation)
- Modify: `bx/skills/save/references/mode-update.md` (Part 1.9; drift warning format)

**Interfaces:**
- Consumes: the per-section measurement added to Step 0.2 in Task 4.
- Turns green: K11, K12. After this task the whole lint exits 0.

- [ ] **Step 1: Verify the target checks fail**

Run: `bash bx/skills/save/tests/check-known-issues-governance.sh | grep -E 'K11|K12'`
Expected: both FAIL.

- [ ] **Step 2: Edit doc-structure-rules.md**

Replace:

```
- **Compressing a session history block to a one-liner with commit hashes is preservation** — the full prose is recoverable via `git show <hash>`.
```

with:

```
- **Compressing a session history block to a one-liner with commit hashes is preservation** — the full prose is recoverable via `git show <hash>`.
- **Derivable facts are recoverable, and recoverable content may leave CLAUDE.md.** A fact a session can obtain in one command — the stack from `package.json`, the remote from `git remote -v`, the project path from the cwd — is preserved by that command, not by CLAUDE.md. This is the same rule as the session-history one-liner, applied to `## Project Overview`. It does **not** extend to `## Key Decisions` or `## Known Issues / Blockers`, whose content is *why*, and is derivable from nothing. `/bx:save` only names such facts as trim candidates (`mode-update.md` Part 1.9); the user decides whether they go.
```

- [ ] **Step 3: Edit mode-update.md, Part 1.9**

Replace:

```
Measure both files. CLAUDE.md target ~7k, soft cap 12k. docs/STATUS.md target ~10k, soft
cap 20k. Warn per file when over its soft cap and name which Part 7 shrinker will fire.
```

with:

```
Measure both files. CLAUDE.md target ~7k, advisory rung 9k, soft cap 12k. docs/STATUS.md
target ~10k, soft cap 20k. Warn per file when over its soft cap and name which Part 7
shrinker will fire.

**CLAUDE.md over 9k and at or under 12k — the advisory rung.** No shrinker fires in this
band, so say so instead of staying silent. Run Part 7.2's `awk` command on CLAUDE.md, name
the largest section, and take no action:

> "CLAUDE.md is [X]k chars — over the 9k advisory rung, under the 12k soft cap. Largest
>  section: `## [name]` ([N] chars). No shrinker fires below 12k."

If `## Project Overview` states derivable facts (`doc-structure-rules.md`, Pruning Is
Preservation), list them in the same advisory as trim candidates. Do not remove them.
```

- [ ] **Step 4: Edit mode-update.md, drift warning format**

Replace:

```
>  - CLAUDE.md at [X]k chars (target ~7k, soft cap 12k) — Part 7 size-pressure rollup will fire on `--full`
```

with:

```
>  - CLAUDE.md at [X]k chars (target ~7k, soft cap 12k) — Part 7 size-pressure rollup will fire on `--full`
>  - CLAUDE.md at [X]k chars — over the 9k advisory rung; largest section `## [name]` ([N] chars); no shrinker fires below 12k
```

Replace:

```
Show the archive line only for an archive at ≥90k chars (approaching or over the 100k rotation threshold).
```

with:

```
Show the archive line only for an archive at ≥90k chars (approaching or over the 100k rotation threshold). Show the soft-cap line when CLAUDE.md is over 12k and the advisory-rung line when it is over 9k and at or under 12k — never both. Show the Known Issues line when that section is over 4000 chars, whatever the file size.
```

- [ ] **Step 5: Run the full lint**

Run: `bash bx/skills/save/tests/check-known-issues-governance.sh; echo "exit=$?"`
Expected: `exit=0`, `All Known Issues governance checks passed.`

Run: `bash bx/skills/save/tests/check-doc-rule-consistency.sh; echo "exit=$?"`
Expected: `exit=0`.

- [ ] **Step 6: Commit**

```bash
git -C /c/Development/projects/claude-config add bx/skills/save/references/doc-structure-rules.md bx/skills/save/references/mode-update.md
git -C /c/Development/projects/claude-config commit -m "feat(save): derivable-content clause + 9k advisory rung (D7, D8)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: Blind rehearsals (acceptance instrument)

Rehearsals find ambiguity; the lint cannot. Each rehearsal is a fresh `general-purpose` subagent that receives only instruction text and a fixture path, executes, and returns a decision log. **Bar: every outcome check passes and the decision log lists ≤ 2 ambiguities per rehearsal.**

**Files:**
- Modify (only if a rehearsal fails): the instruction file the ambiguity points at.
- Create: `docs/superpowers/plans/2026-09-28-bx-doc-tiering-phase1-rehearsals.md` (results log)

**Interfaces:**
- Consumes: everything from Tasks 1–5.

- [ ] **Step 1: Build the fixtures in the scratchpad**

```bash
bash bx/skills/save/tests/make-fixtures.sh "$SCRATCH/ki-fixtures" > /dev/null
```

`$SCRATCH` is the session scratchpad directory. Each rehearsal gets its own copy of its fixture (`cp -r`), because subagent edits are not checkpointed.

- [ ] **Step 2: Dispatch the four rehearsals in one message (parallel)**

Every prompt starts with this preamble, verbatim:

```
You are rehearsing an instruction file. You will be given instruction text and a repo path.
Execute the instructions exactly as written against that repo. Use ONLY the text given here:
do not read any file under bx/, do not use prior knowledge of this skill. You cannot ask
questions; where the text leaves a choice open, choose, and record it.
Return: (1) a decision log — a numbered list of every point where the text was ambiguous,
silent, or contradictory, with the choice you made; (2) the list of files you changed.
Treat every consent prompt in the text as answered "yes". This session is S10, today is
2026-09-28.
```

Then, per rehearsal:

| Id | Repo | Instruction text pasted into the prompt | Task line |
|---|---|---|---|
| R1 | copy of `fx-ki-resolved` | `mode-update.md` Part 1.7, Parts 7.1–7.5; `save-writer.md` step 8; `doc-schema.md` Archives section | "CLAUDE.md is over its soft cap for the purpose of this rehearsal: skip 7.1's gate and run 7.2–7.5 for CLAUDE.md." |
| R2 | copy of `fx-ki-unresolved` | same as R1 | same as R1 |
| R3 | copy of `fx-ki-resolved` | `save-writer.md`, whole file | Three packets, applied in order, each with only `project_root`, `today`, `known_issue_moves` filled and every other field empty. Packet A: one item, the `Gadget sync stalls on large batches (S4).` entry copied verbatim from the fixture, `status: resolved`, `session: S10`, `commit: abc1234`. Packet B: the five remaining entries, `status: resolved`, `commit: none`. Packet C: one item whose `entry` is `**This entry does not exist.** Nothing.` |
| R4 | copy of `fx-ki-rotate` | `mode-update.md` Part 7.7; `doc-schema.md` Archives section | "Run Part 7.7." |

- [ ] **Step 3: Check R1's outcome**

Run, with `R=$SCRATCH/r1`:

```bash
awk '/^## /{f=($0=="## Known Issues / Blockers"); next} f{n+=length($0)+1} END{print n+0}' "$R/CLAUDE.md"
grep -ci 'resolved' "$R/CLAUDE.md"
grep -c '^### .* — Resolved ' "$R/docs/known-issues.md"
grep -cF -e 'Gadget sync stalls on large batches (S4).' -e 'Exporter drops the final row (S7).' -e 'Report totals are off by one (S9).' "$R/CLAUDE.md"
grep -cF '> Session state: [docs/STATUS.md](docs/STATUS.md)' "$R/CLAUDE.md"
bash bx/skills/save/tests/assert-doc-schema.sh "$R" --expect v2 | tail -1
```

Expected, in order: a number under `2500`; `0`; `3`; `3`; `1`; `All assertions passed.`

- [ ] **Step 4: Check R2's outcome**

Run, with `R=$SCRATCH/r2`:

```bash
awk '/^## /{f=($0=="## Known Issues / Blockers"); next} f{n+=length($0)+1} END{print n+0}' "$R/CLAUDE.md"
grep -c '^### .* — Resolved ' "$R/docs/known-issues.md"
grep -c '^### .* — Open, moved S10 ' "$R/docs/known-issues.md"
grep -c 'Detail 15 of this issue' "$R/CLAUDE.md"
grep -c 'docs/known-issues.md' "$R/CLAUDE.md"
grep -cF -e 'Scheduler skips the DST hour (S9).' -e 'Uploads over 2GB time out (S9).' "$R/CLAUDE.md"
```

Expected, in order: a number from `2500` to `3999` (under 4000, and NOT chased to 2500); `1`; `3` (the three oldest open entries, including both traps); `4` (four open entries still carry their full body); `3` or more (one link per moved open entry); `2` (the newest entries untouched).

- [ ] **Step 5: Check R3's outcome**

Run, with `R=$SCRATCH/r3`:

```bash
head -1 "$R/docs/known-issues.md"
grep -c '^### ' "$R/docs/known-issues.md"
grep -c '^### .* — Resolved S10 (2026-09-28), commit abc1234$' "$R/docs/known-issues.md"
grep -c 'This entry does not exist' "$R/docs/known-issues.md"
awk '/^## Known Issues/{f=1; next} /^## /{f=0} f && NF' "$R/CLAUDE.md"
```

Expected, in order: `# Known Issues Archive`; `7` (six real entries plus Packet C's, which is archived before its removal fails); `1`; `1`; exactly two lines, `None currently.` and the `> Session state:` pointer line. The subagent's report for Packet C must carry a `warnings:` line naming the unmatched removal.

- [ ] **Step 6: Check R4's outcome**

Run, with `R=$SCRATCH/r4`, and `B` = the fixture's original `wc -c` of `docs/known-issues.md`:

```bash
grep -c '^### ' "$R/docs/archive/known-issues-1.md"
grep -c 'Open, moved' "$R/docs/archive/known-issues-1.md"
grep -m1 '^### ' "$R/docs/known-issues.md"
grep -c 'Entries are rotated to' "$R/docs/known-issues.md"
echo $(( $(wc -c < "$R/docs/known-issues.md") + $(wc -c < "$R/docs/archive/known-issues-1.md") - B ))
```

Expected, in order: `59`; `0`; `### Issue 60 — Open, moved S60 (2026-01-01)`; `1`; a number from `0` to `600`.

- [ ] **Step 7: Score the decision logs and fix**

For each rehearsal, count decision-log items that describe a real ambiguity in the text (not a fixture quirk, not a tool limitation). If any rehearsal has more than 2, or any outcome check failed:

1. Edit the instruction text at the point the log names. Add the missing rule; do not add an example that merely happens to cover the case.
2. Re-run the lint (`check-known-issues-governance.sh`, expect exit 0).
3. Re-dispatch that rehearsal only, against a fresh fixture copy.
4. Stop after three waves per rehearsal. If the bar is still unmet, record the residual count and the remaining items in the results log and carry on: the release notes must then say the bar was not met.

- [ ] **Step 8: Write the results log**

Create `docs/superpowers/plans/2026-09-28-bx-doc-tiering-phase1-rehearsals.md` with one section per rehearsal: waves run, ambiguity count per wave, each outcome check's actual value, and each instruction edit made in response. Record actual numbers only.

- [ ] **Step 9: Commit**

```bash
git -C /c/Development/projects/claude-config add bx/ docs/superpowers/plans/2026-09-28-bx-doc-tiering-phase1-rehearsals.md
git -C /c/Development/projects/claude-config commit -m "test(save): blind rehearsals R1-R4 for the Known Issues governor

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: Release v2.10.0

**Files:**
- Modify: `bx/.claude-plugin/plugin.json:5`
- Modify: `CHANGELOG.md` (new entry above `## 2.9.0 — 2026-09-08`)
- Modify: `README.md:397` and a new row after `README.md:401`

- [ ] **Step 1: Bump the version**

In `bx/.claude-plugin/plugin.json`, replace `"version": "2.9.0",` with `"version": "2.10.0",`.

- [ ] **Step 2: Add the CHANGELOG entry**

Insert above `## 2.9.0 — 2026-09-08`, using the release date of the day this step runs:

```markdown
## 2.10.0 — <release date>

### Added

- **`docs/known-issues.md`, a fifth auto-managed archive.** `## Known Issues / Blockers` was the
  one required CLAUDE.md section with no cap, no shrinker and no archive destination; a field
  `/doctor` run found it at 14.9k chars, 48% of a 31.1k CLAUDE.md. Issues that leave CLAUDE.md
  now land here, one `### ` entry each, tagged `Resolved` or `Open, moved`. Rotates at 100k like
  the other archives; rotation never cuts past the first `Open` entry.

- **Known Issues shrinker (Part 7.3).** Threshold 4000 chars. Resolved entries move first, until
  the section is under 2500 or none remain. Open entries move only while the section is still
  over 4000, and each leaves a one-line summary + link behind.

- **9k advisory rung (Part 1.9).** Nothing acted between the ~7k target and the 12k soft cap.
  Between 9k and 12k the save now names the largest section. No shrinker fires below 12k.

- **Derivable-content clause.** A fact one command recovers (stack, remote, cwd) may leave
  `## Project Overview`. Advisory only: `/bx:save` names candidates and removes nothing.

### Changed

- **Resolved issues are relocated, not deleted.** Part 1.7 said "Remove resolved issues", the one
  place `/bx:save` contradicted its own *content moves, it does not disappear* rule. They now
  travel in a new `known_issue_moves` packet field, and `save-writer` archives first and removes
  second. An issue is resolved only when the session says so, never because it went unmentioned.

- **Part 7.3's tolerated-as-is clause covers project-specific sections only.** A required section
  falling through it is now a reportable bug.
```

If Task 6 recorded an unmet rehearsal bar, add a final line to the entry stating the residual ambiguity count per rehearsal.

- [ ] **Step 3: Update the README file table**

In the `CLAUDE.md` row (line 397), replace:

```
Every save: the `Last Updated` line, new Key Decision rows, Known Issues changes. On `--full`, rows past 20 move out to `docs/key-decisions.md`.
```

with:

```
Every save: the `Last Updated` line, new Key Decision rows, Known Issues changes (resolved issues move to `docs/known-issues.md`). On `--full`, rows past 20 move out to `docs/key-decisions.md`, and a Known Issues section over 4000 chars is shrunk, resolved entries first.
```

After the `docs/key-decisions.md` row (line 401), insert:

```
| `docs/known-issues.md` | Every issue that has left CLAUDE.md's Known Issues: resolved ones as history, and open ones moved under size pressure (each still summarized and linked in CLAUDE.md). Created on demand. | Appends each issue the session resolved, archive first, removal second; `--full` also moves entries when the section is over 4000 chars. | **Never automatically — not even in `deep` mode.** Grep it when chasing an old issue. |
```

- [ ] **Step 4: Run every check**

```bash
bash bx/skills/save/tests/check-known-issues-governance.sh; echo "exit=$?"
bash bx/skills/save/tests/check-doc-rule-consistency.sh; echo "exit=$?"
bash bx/skills/save/tests/test-known-issues-fixtures.sh; echo "exit=$?"
bash bx/skills/save/tests/test-hook-layout.sh; echo "exit=$?"
claude plugin validate ./bx --strict --json
claude plugin validate . --json
```

Expected: `exit=0` for the first three, and for `test-hook-layout.sh` the baseline code recorded in Task 1 Step 7; both validate reports show `"success": true` with empty `manifest.errors` and `manifest.warnings`. If `claude` is not on PATH, record that the validate step was skipped.

- [ ] **Step 5: Commit**

```bash
git -C /c/Development/projects/claude-config add bx/.claude-plugin/plugin.json CHANGELOG.md README.md
git -C /c/Development/projects/claude-config commit -m "feat(save): v2.10.0 — Known Issues governor, 9k rung, derivable-content clause

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

- [ ] **Step 6: Stop and hand back**

Do not merge or push. Report the branch name, the four check results, and the rehearsal ambiguity counts. Merge, push, `/plugin update bx` and `/reload-plugins` are the user's call.

---

## After the merge (not part of this plan's execution)

These need the installed plugin and the user, so they are recorded here rather than tasked:

1. **Dogfood on this repo:** `/bx:save --full`. CLAUDE.md is 13,606 chars with Known Issues at 4,611, so Part 7 fires. Expected: the two entries whose leads say RESOLVED (the S37 `/bx:seo` entry and the `session-start-context.ps1` entry, about 920 chars together) move to a new `docs/known-issues.md`; the section lands near 3,700; no open entry is touched, because 3,700 is under 4000.
2. **Field check (spec acceptance 5):** re-run `/doctor` on the external repo after a `--full` save there and confirm CLAUDE.md moved toward the target.
3. **Phase 2 gate:** D4, D5, D6 (the `.claude/rules/` tier) stay gated. Re-verify the `paths:` frontmatter against the official memory page before planning them.
