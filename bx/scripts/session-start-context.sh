#!/usr/bin/env bash
# session-start-context.sh — emit cheap project orientation context for Claude
#
# Wired to Claude Code's SessionStart hook. Stdout is injected into the session
# as system context before the user's first prompt. Stderr is shown to the user.
#
# Design rules:
#   - Cheap: must complete in < 1 second on a typical repo
#   - Read-only: no writes anywhere
#   - Silent on non-repo dirs: emit nothing rather than errors
#   - Bounded: never emit more than ~50 lines (Claude reads this on every start)
#   - Manual /bx:resume still works for deep orientation (deliberate dual-path)

set -e

# Only emit context inside a git repo. If we're not in one, the user is probably
# in their home dir or a one-off chat — no project orientation to emit.
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

repo_root="$(git rev-parse --show-toplevel)"
repo_name="$(basename "$repo_root")"

echo "## Project orientation: $repo_name"
echo ""

# Branch + uncommitted files
branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
dirty_count="$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
last_commit_age="$(git log -1 --format=%cr 2>/dev/null || echo unknown)"
echo "- Branch: \`$branch\` · $dirty_count uncommitted files · last commit $last_commit_age"

# Recent commits (3 lines max — keep it cheap)
echo ""
echo "**Recent commits:**"
echo '```'
git log --oneline -5 2>/dev/null || echo "(no commits)"
echo '```'

# CLAUDE.md Current Status table (if present)
if [ -f "$repo_root/CLAUDE.md" ]; then
  echo ""
  echo "**CLAUDE.md status:**"
  # Extract Last Updated line + Current Status table (capped at 12 lines)
  grep -i "^Last Updated" "$repo_root/CLAUDE.md" | head -1
  awk '/^## Current Status/,/^## [^C]/' "$repo_root/CLAUDE.md" 2>/dev/null | head -12 || true

  # Stale-doc check: warn if commits exist newer than CLAUDE.md
  claude_md_mtime="$(git log -1 --format=%ct -- CLAUDE.md 2>/dev/null || echo 0)"
  head_commit_mtime="$(git log -1 --format=%ct 2>/dev/null || echo 0)"
  if [ "$claude_md_mtime" -gt 0 ] && [ "$head_commit_mtime" -gt "$claude_md_mtime" ]; then
    age_days=$(( (head_commit_mtime - claude_md_mtime) / 86400 ))
    if [ "$age_days" -gt 2 ]; then
      echo ""
      echo "_(CLAUDE.md last updated $age_days days before the latest commit — may be stale. Run \`/bx:resume\` to verify.)_"
    fi
  fi
fi

# Open PR for this branch (best-effort via gh)
if command -v gh >/dev/null 2>&1; then
  pr_info="$(gh pr view --json number,state,title 2>/dev/null || true)"
  if [ -n "$pr_info" ]; then
    echo ""
    pr_num="$(echo "$pr_info" | grep -oE '"number":[0-9]+' | head -1 | grep -oE '[0-9]+')"
    pr_title="$(echo "$pr_info" | grep -oE '"title":"[^"]*"' | head -1 | sed 's/"title":"//;s/"$//')"
    echo "- Open PR: #$pr_num — $pr_title"
  fi
fi

echo ""
echo "_(Orientation auto-injected by \`session-start-context.sh\`. For full task hydration + docs scan, run \`/bx:resume\` explicitly.)_"
