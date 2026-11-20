#!/usr/bin/env bash
# test-size-budget-fixture.sh - the size-budget fixture, its scripts, and the
# verifier for a rehearsed `/bx:save --full` run on it (Part 7, v2.18.0).
#
# Usage:
#   test-size-budget-fixture.sh
#       Build fx-size-budget and assert (1) it has the shape that makes the
#       rehearsal meaningful, (2) size-budget.sh and archive-lines.sh behave,
#       (3) the control: assert-size-budget.sh FAILS on the untouched fixture.
#   test-size-budget-fixture.sh --verify <run-dir> <before-dir> [--expect-clean]
#       After a rehearsal: <run-dir> is the fixture a `--full` run with
#       "apply all" was executed on, <before-dir> a copy taken before it. Runs
#       assert-size-budget.sh, then the fixture-specific checks: every rule lead
#       and variable name still loads, the right items moved, nothing twice.
#
# What this cannot do: execute the shrinkers. Part 7 is instructions for a model.
# The rehearsal is run by an agent (or a real session) and judged here.
# bash 3.2 compatible.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUDGET_SH="$SCRIPT_DIR/../scripts/size-budget.sh"
ARCHIVE_SH="$SCRIPT_DIR/../scripts/archive-lines.sh"

FAILURES=0
pass() { echo "  PASS  $1"; }
fail() { echo "  FAIL  $1"; FAILURES=$((FAILURES + 1)); }
between() {  # <label> <value> <min> <max>
    if [ "$2" -ge "$3" ] && [ "$2" -le "$4" ]; then pass "$1 = $2 (want $3..$4)"
    else fail "$1 = $2 (want $3..$4)"; fi
}
count_in() {  # <fixed-string> <file> -- lines containing it, 0 when the file is missing
    if [ -f "$2" ]; then grep -cF -- "$1" "$2" || true; else echo 0; fi
}
finish() {
    echo ""
    if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES check(s) failed."; exit 1; fi
    echo "$1"; exit 0
}

# ------------------------------------------------------------------ --verify
if [ "${1:-}" = "--verify" ]; then
    RUN="${2:?--verify needs <run-dir> <before-dir>}"; BEFORE="${3:?--verify needs <before-dir>}"
    CLEAN=""; [ "${4:-}" = "--expect-clean" ] && CLEAN="--expect-clean"
    C="$RUN/CLAUDE.md"; S="$RUN/docs/STATUS.md"
    BL="$RUN/docs/next-steps-backlog.md"; CW="$RUN/docs/completed-work.md"

    # shellcheck disable=SC2086
    if bash "$SCRIPT_DIR/assert-size-budget.sh" "$RUN" --before "$BEFORE" $CLEAN; then
        pass "assert-size-budget.sh passed"
    else fail "assert-size-budget.sh failed (see above)"; fi

    echo "--- every standing rule still loads: its lead in CLAUDE.md, or a scoped rules file plus a trace ---"
    n=1; missing=0
    while [ "$n" -le 24 ]; do
        id="R$(printf '%02d' "$n")"
        if grep -qF "$id" "$C"; then :
        else
            rf="$(grep -rlF "$id" "$RUN/.claude/rules" 2>/dev/null | head -1)"
            if [ -z "$rf" ]; then fail "rule $id is in neither CLAUDE.md nor .claude/rules/"; missing=1
            elif ! grep -qF ".claude/rules/$(basename "$rf")" "$C"; then
                fail "rule $id moved to $(basename "$rf") but CLAUDE.md has no trace line linking it"; missing=1
            fi
        fi
        n=$((n + 1))
    done
    [ "$missing" -eq 0 ] && pass "all 24 rules are loaded or traced"
    for rf in "$RUN"/.claude/rules/*.md; do
        [ -f "$rf" ] || continue
        if head -6 "$rf" | grep -q '^paths:'; then pass "$(basename "$rf") carries paths: frontmatter"
        else fail "$(basename "$rf") has no paths: frontmatter, so it loads every session"; fi
    done
    n=1; gone=0
    while [ "$n" -le 18 ]; do
        id="R$(printf '%02d' "$n")"
        grep -qF "check $id before the step it guards.**" "$C" || { fail "global rule $id lost its lead in CLAUDE.md"; gone=1; }
        n=$((n + 1))
    done
    [ "$gone" -eq 0 ] && pass "all 18 global rules keep their lead sentence, byte for byte"

    echo "--- floors held ---"
    n=1; gone=0
    while [ "$n" -le 12 ]; do
        grep -qF "FIXVAR_$(printf '%02d' "$n")" "$C" || { fail "FIXVAR_$(printf '%02d' "$n") left CLAUDE.md"; gone=1; }
        n=$((n + 1))
    done
    [ "$gone" -eq 0 ] && pass "all 12 variable names are still in CLAUDE.md"
    n=7; gone=0
    while [ "$n" -le 14 ]; do
        grep -qF "Decision D$(printf '%02d' "$n"):" "$C" || { fail "decision D$(printf '%02d' "$n") (one of the newest 8) left CLAUDE.md"; gone=1; }
        n=$((n + 1))
    done
    [ "$gone" -eq 0 ] && pass "the newest 8 Key Decisions rows are still in CLAUDE.md"
    grep -qF 'docs/flow-11.md' "$C" && grep -qF '| **Name** | Sizefix |' "$C" \
        && pass "Project Overview keeps the name and the Key Documentation links" \
        || fail "Project Overview lost the name row or a Key Documentation link"
    grep -qF 'Personal release email' "$S" && grep -qF 'Photo AI' "$S" \
        && pass "both unfinished Current Status rows stay" || fail "an unfinished Current Status row left STATUS.md"
    for k in 10 11 12; do
        grep -qF "Feature F$k (" "$S" || fail "finished row F$k (one of the newest 3) left STATUS.md"
    done
    between "Current Status summary rows" "$(count_in 'finished rows collapsed' "$S")" 1 1
    between "hand-collapsed rows left in STATUS.md" "$(count_in 'collapsed rows**' "$S")" 0 0
    grep -qF '_**Watermarks:**' "$S" && pass "the project-authored Watermarks paragraph was not moved" \
        || fail "the Watermarks paragraph left STATUS.md"

    echo "--- finished items, and the DONE-except trap ---"
    for k in 134 131; do
        if grep -q "^$k\. " "$S"; then fail "finished item $k is still in Next Steps"
        elif [ "$(count_in "Item $k:" "$CW")" -ge 1 ]; then pass "finished item $k moved to completed-work.md"
        else fail "finished item $k is in neither STATUS.md nor completed-work.md"; fi
    done
    if grep -q '^135\. ' "$S" && [ "$(count_in 'Item 135:' "$CW")" -eq 0 ]; then
        pass "item 135 (DONE ... except) stayed open"
    else fail "item 135 (DONE ... except) was treated as finished"; fi

    echo "--- items past the cap: folded once, never archived twice ---"
    for k in 138 137 136 133 132 130 129 128 127; do
        grep -q "^$k\. " "$S" || fail "item $k (one of the first 10) left Next Steps"
    done
    # Folding items past the cap is a relocate move: it is planned only when the
    # tidy moves and larger sections did not cover the need. So an item past the
    # cap is either still in STATUS.md (not needed this run) or archived once.
    folded=0
    for k in 126 125 124 123; do
        if grep -q "^$k\. " "$S"; then continue; fi
        folded=$((folded + 1))
        between "copies of folded item $k in the backlog" "$(grep -c "^$k\. " "$BL" || true)" 1 1
    done
    case "$folded" in 0|4) pass "Next Steps items past the cap: $folded of 4 folded (all or none)" ;;
                      *) fail "Next Steps items past the cap were folded in part: $folded of 4" ;; esac
    for k in 01 02 03 04 05; do
        grep -qF "Workstream W$k LIVE" "$S" || fail "In Progress item W$k (one of the first 5) left STATUS.md"
    done
    folded=0
    for k in 06 07 08 09 10 11 12 13 14; do
        if grep -qF "Workstream W$k LIVE" "$S"; then continue; fi
        folded=$((folded + 1))
        between "copies of folded W$k in the backlog" "$(count_in "Workstream W$k LIVE" "$BL")" 1 1
    done
    case "$folded" in 0|9) pass "In Progress items past the cap: $folded of 9 folded (all or none)" ;;
                      *) fail "In Progress items past the cap were folded in part: $folded of 9" ;; esac
    between "scaffolding lines left in Next Steps/In Progress" \
        "$(grep -cE '^> (Items #|Full (Next Steps|In Progress) detail)' "$S" || true)" 0 0

    finish "The rehearsed run meets every fixture check."
fi

# ------------------------------------------------------------------ default
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
bash "$SCRIPT_DIR/make-fixtures.sh" "$TMP" > /dev/null 2>&1 || { echo "make-fixtures.sh failed"; exit 2; }
FX="$TMP/fx-size-budget"

if bash "$SCRIPT_DIR/assert-doc-schema.sh" "$FX" --expect v2 > /dev/null; then pass "fx-size-budget satisfies the v2 schema"
else fail "fx-size-budget fails assert-doc-schema.sh --expect v2"; fi

echo "--- shape: both files over budget, in the proportions of the evidence ---"
rep="$(bash "$BUDGET_SH" "$FX")"
field() {  # <record-prefix> <field-number>
    printf '%s\n' "$rep" | grep -F -- "$1" | head -1 | awk -v f="$2" '{print $f}'
}
between "CLAUDE.md chars" "$(field 'file CLAUDE.md ' 3)" 15000 18000
between "STATUS.md chars" "$(field 'file docs/STATUS.md ' 3)" 19000 23000
[ "$(field 'file CLAUDE.md ' 6)" = "over" ] && pass "CLAUDE.md is over budget" || fail "CLAUDE.md is not over budget"
[ "$(field 'file docs/STATUS.md ' 6)" = "over" ] && pass "STATUS.md is over budget" || fail "STATUS.md is not over budget"
between "Known Issues chars" "$(field 'section CLAUDE.md' 3)" 5500 7000
[ "$(printf '%s\n' "$rep" | grep '^section CLAUDE.md' | head -1 | cut -d' ' -f4-)" = "## Known Issues / Blockers" ] \
    && pass "Known Issues is CLAUDE.md's largest section" || fail "Known Issues is not CLAUDE.md's largest section"
[ "$(printf '%s\n' "$rep" | grep '^section docs/STATUS.md' | head -1 | cut -d' ' -f4-)" = "## Current Status" ] \
    && pass "Current Status is STATUS.md's largest section" || fail "Current Status is not STATUS.md's largest section"
between "CLAUDE.md Last Updated chars" "$(field 'last_updated CLAUDE.md ' 3)" 700 1000
between "STATUS.md Last Updated chars" "$(field 'last_updated docs/STATUS.md ' 3)" 700 1000
between "resolved-status leads in Known Issues (rules are never resolved)" \
    "$(awk '/^## /{f=($0=="## Known Issues / Blockers"); next} f' "$FX/CLAUDE.md" | grep -cE 'RESOLVED|(is|was|now) resolved' || true)" 0 0
between "standing rules" "$(grep -cE '^- \*\*.*\(?R[0-9]{2}' "$FX/CLAUDE.md" || true)" 24 24
between "finished Current Status rows" "$(grep -c '^| .*| ✅' "$FX/docs/STATUS.md" || true)" 14 14
between "Next Steps items" "$(grep -cE '^[0-9]+\. ' "$FX/docs/STATUS.md" || true)" 16 16
between "In Progress items" "$(grep -c '^- \*\*Workstream' "$FX/docs/STATUS.md" || true)" 14 14
between "scaffolding lines" "$(grep -cE '^> (Items #|Full (Next Steps|In Progress) detail)' "$FX/docs/STATUS.md" || true)" 6 6

echo "--- feasibility: the floors alone fit under the budget ---"
# What must stay if every shrinker goes to its floor, measured the crude way:
# drop the lines a shrinker may take, count what is left.
status_floor="$(awk '
    /^Last Updated/ { n += 40; next }
    /^\| .*\| ✅/ { fin++; if (fin <= 11) next }
    /^> (Items #|Full (Next Steps|In Progress) detail)/ { next }
    /^[0-9]+\. / { ns++; if (ns > 12) next }
    /^- \*\*Workstream/ { ip++; if (ip > 5) next }
    { n += length($0) + 1 } END { print n + 0 }' "$FX/docs/STATUS.md")"
between "STATUS.md at its floors" "$status_floor" 5000 13000
claude_floor="$(awk '
    /^\*\*Last Updated/ { n += 50; next }
    /^\| Decision D0[1-6]:/ { next }
    /^- \*\*In `src\/db\/migrations/ { next }
    /^- \*\*Never skip check/ { n += index($0, ".**") + 3; next }
    /^- `FIXVAR_/ { n += 14; next }
    { n += length($0) + 1 } END { print n + 0 }' "$FX/CLAUDE.md")"
between "CLAUDE.md at its floors" "$claude_floor" 4000 9000

echo "--- control: the untouched fixture must fail the budget assertion ---"
if bash "$SCRIPT_DIR/assert-size-budget.sh" "$FX" > /dev/null 2>&1; then
    fail "assert-size-budget.sh passed on the untouched fixture: the assertion checks nothing"
else pass "assert-size-budget.sh fails on the untouched fixture"; fi

echo "--- size-budget.sh --line, and the skip escalation ---"
line="$(bash "$BUDGET_SH" "$FX" --line)"
case "$line" in "Size budget: CLAUDE.md "*" / 10k, STATUS.md "*" / 15k → run /bx:save --full") pass "--line: $line" ;;
                *) fail "--line has the wrong shape: $line" ;; esac
cp -r "$FX" "$TMP/skips"
awk '{print} /^Last Updated/{print "<!-- bx-size-skips=3 -->"}' "$FX/docs/STATUS.md" > "$TMP/skips/docs/STATUS.md"
line="$(bash "$BUDGET_SH" "$TMP/skips" --line)"
case "$line" in *"shrink skipped 3 runs in a row"*) pass "three skips escalate the line" ;;
                *) fail "three skips did not escalate: $line" ;; esac
line="$(bash "$BUDGET_SH" "$TMP/fx-v2" --line)"
case "$line" in *"within budget") pass "an under-budget repo reads 'within budget'" ;;
                *) fail "fx-v2 does not read within budget: $line" ;; esac

echo "--- archive-lines.sh: byte-verbatim, de-duplicating, repeatable ---"
cp -r "$FX" "$TMP/arch"; A="$TMP/arch"
first="$(grep -n '^126\. ' "$A/docs/STATUS.md" | cut -d: -f1)"
last="$(grep -n '^123\. ' "$A/docs/STATUS.md" | cut -d: -f1)"
before_bytes="$(wc -c < "$A/docs/STATUS.md" | tr -d ' ')"
out="$(bash "$ARCHIVE_SH" "$A" docs/STATUS.md docs/next-steps-backlog.md "## Rolled off STATUS.md (S322 --full)" "$first-$last")"
case "$out" in *"archived 2 skipped 2 -> docs/next-steps-backlog.md") pass "first call archives the 2 new items and skips the 2 already there" ;;
               *) fail "first call: $(printf '%s' "$out" | tail -1)" ;; esac
out="$(bash "$ARCHIVE_SH" "$A" docs/STATUS.md docs/next-steps-backlog.md "## Rolled off STATUS.md (S322 --full)" "$first-$last")"
case "$out" in *"archived 0 skipped 4 -> docs/next-steps-backlog.md") pass "second call archives nothing" ;;
               *) fail "second call: $(printf '%s' "$out" | tail -1)" ;; esac
for k in 126 125 124 123; do
    between "copies of item $k in the backlog" "$(grep -c "^$k\. " "$A/docs/next-steps-backlog.md" || true)" 1 1
done
grep -qxF -- "$(sed -n "${first}p" "$A/docs/STATUS.md")" "$A/docs/next-steps-backlog.md" \
    && pass "an archived line is byte-identical to its source" || fail "the archived line differs from its source"
between "copies of the block heading" "$(grep -cxF '## Rolled off STATUS.md (S322 --full)' "$A/docs/next-steps-backlog.md" || true)" 1 1
[ "$(wc -c < "$A/docs/STATUS.md" | tr -d ' ')" = "$before_bytes" ] && pass "the source file is untouched" || fail "archive-lines.sh changed its source"
out="$(bash "$ARCHIVE_SH" "$A" docs/STATUS.md docs/completed-work.md "" "$first" --prefix '- [x] ')"
grep -qF -- "- [x] 126. " "$A/docs/completed-work.md" && pass "--prefix lands before the line" || fail "--prefix did not apply"
if bash "$ARCHIVE_SH" "$A" docs/STATUS.md docs/brand-new.md "## H" 9999 > /dev/null 2>&1; then
    fail "an out-of-range line number was accepted"
elif [ -e "$A/docs/brand-new.md" ]; then fail "a refused call still created its destination"
else pass "an out-of-range line number is refused before anything is written"; fi

finish "The size-budget fixture and scripts are valid."
