#!/usr/bin/env bash
# session-start-context.sh — emit cheap project orientation context for Claude
#
# Wired to Claude Code's SessionStart hook. Stdout is injected into the session
# as system context before the user's first prompt. Stderr is shown to the user.
#
# Design rules:
#   - Cheap: must complete in < 1 second on a typical repo
#   - Read-only on the repo: no writes anywhere except the harness-provided
#     $CLAUDE_ENV_FILE side-channel (session env persistence, CC 2.1.152+)
#   - Silent on non-repo dirs: emit nothing rather than errors
#   - Bounded: never emit more than ~50 lines (Claude reads this on every start)
#   - Manual /bx:resume still works for deep orientation (deliberate dual-path)

set -e

# Persist session-wide env vars (CC 2.1.152+): UTF-8 Python defaults retire the
# per-call PYTHONIOENCODING/PYTHONUTF8 prefixes (the S31 Windows-charmap lesson).
# No-op on older Claude Code versions where CLAUDE_ENV_FILE is unset.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo 'export PYTHONIOENCODING=utf-8'
    echo 'export PYTHONUTF8=1'
  } >> "$CLAUDE_ENV_FILE"
fi

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

# Current Status + freshness. Schema v2 keeps state in docs/STATUS.md; v1 keeps
# it in CLAUDE.md. Read whichever holds it, or the banner goes silently empty.
state_file=""
if [ -f "$repo_root/docs/STATUS.md" ]; then
  state_file="docs/STATUS.md"
elif [ -f "$repo_root/CLAUDE.md" ]; then
  state_file="CLAUDE.md"
fi

if [ -n "$state_file" ]; then
  echo ""
  echo "**Project status** (from \`$state_file\`):"
  grep -i "^Last Updated" "$repo_root/$state_file" | head -1
  # Single-section extractor. The old range /^## Current Status/,/^## [^C]/
  # could not stop at "## Completed" and ran on into "## In Progress".
  awk '/^## Current Status/{f=1; print; next} /^## /{f=0} f' \
      "$repo_root/$state_file" 2>/dev/null | head -12 || true

  # Stale-doc check against the file that actually carries the state.
  # Run git from the repo root: $state_file is a repo-root-relative pathspec, so
  # from a subdirectory git resolves it against CWD, matches nothing, and prints
  # nothing -- while still exiting 0, so `|| echo 0` never fires and the empty
  # string reaches `[ -gt ]` as "integer expression expected" on user-visible
  # stderr. The -C plus the defaults below close both halves.
  state_mtime="$(git -C "$repo_root" log -1 --format=%ct -- "$state_file" 2>/dev/null || echo 0)"
  head_commit_mtime="$(git -C "$repo_root" log -1 --format=%ct 2>/dev/null || echo 0)"
  : "${state_mtime:=0}"
  : "${head_commit_mtime:=0}"
  if [ "$state_mtime" -gt 0 ] && [ "$head_commit_mtime" -gt "$state_mtime" ]; then
    age_days=$(( (head_commit_mtime - state_mtime) / 86400 ))
    if [ "$age_days" -gt 2 ]; then
      echo ""
      echo "_($state_file last updated $age_days days before the latest commit - may be stale. Run \`/bx:resume\` to verify.)_"
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
