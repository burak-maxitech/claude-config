#!/usr/bin/env bash
# check-skill-commands.sh - every `parallel.sh <word>` named in the skill prose must be a
# subcommand parallel.sh accepts.
#
# Scans bx/skills/parallel/SKILL.md (required) and bx/skills/save/SKILL.md plus
# bx/skills/save/references/*.md. The accepted list comes from `parallel.sh help`.
# Rule for prose: a word written directly after "parallel.sh ", "`P " or "<script> " is read
# as a subcommand, so write `parallel.sh` in backticks when a sentence goes on after it.
#
# Usage: bash bx/skills/parallel/tests/check-skill-commands.sh
# Exit 0 = every named subcommand exists. Exit 1 = something is missing or unknown.
# bash 3.2 compatible.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$HERE/.." && pwd)"
SKILLS="$(cd "$SKILL_DIR/.." && pwd)"
SCRIPT="$SKILL_DIR/scripts/parallel.sh"

FAILURES=0
fail() { echo "  FAIL  $1"; FAILURES=$((FAILURES + 1)); }

subs="$(bash "$SCRIPT" help 2>/dev/null)"
rc=$?
if [ "$rc" -ne 0 ] || [ -z "$subs" ]; then
    fail "parallel.sh help printed no subcommand list (exit $rc)"
    subs=""
fi

files=""
if [ -f "$SKILL_DIR/SKILL.md" ]; then
    files="$SKILL_DIR/SKILL.md"
else
    fail "missing $SKILL_DIR/SKILL.md"
fi
for f in "$SKILLS/save/SKILL.md" "$SKILLS"/save/references/*.md; do
    [ -f "$f" ] && files="$files
$f"
done

# A subcommand is the word after "parallel.sh ", after the skill's shorthand "`P " (P is
# `bash <skill-dir>/scripts/parallel.sh`), or after "<script> " in the setup-message template.
PATTERN='(parallel\.sh|`P|<script>)[[:space:]]+[a-z][a-z-]*'

checked=0
while IFS= read -r f; do
    [ -n "$f" ] || continue
    words="$(grep -oE "$PATTERN" "$f" | sed -E 's/^(parallel\.sh|`P|<script>)[[:space:]]+//' | sort -u)"
    for w in $words; do
        checked=$((checked + 1))
        if [ -z "$subs" ] || ! printf '%s\n' "$subs" | grep -qx -- "$w"; then
            fail "${f#$SKILLS/}: parallel.sh $w is not a subcommand"
        fi
    done
done <<EOF
$files
EOF

echo ""
if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES problem(s); $checked command name(s) checked."; exit 1; fi
echo "All $checked command name(s) are parallel.sh subcommands."
