---
name: resume
description: "Resumes development on a project after a break. Reads docs, scans git state, identifies next task, and hydrates live task tracker. Use at the start of every coding session."
disable-model-invocation: true
effort: low
allowed-tools: Read, Grep, Glob, Bash(git:*), Bash(ls:*), Bash(npm:*), Bash(npx:*), Bash(python:*), Bash(make:*), Bash(cargo:*), TaskCreate, TaskGet, TaskList
argument-hint: "[deep]"
---

# /bx:resume - Resume Development Session

Get up to speed on this project and continue development from where we left off.

**Companion command:** `/bx:save` - Use at the end of sessions to save progress.

---

## Your Task

You are resuming work on this project after a break (hours, days, or weeks). Your goal is to:

1. **Understand the project** - What it does, how it works
2. **Know current state** - What's done, what's in progress, what's next
3. **Be ready to code** - Have full context to continue immediately

---

## Step 0: What Is Already In Context

Claude Code loads two things into your context automatically, **before this skill runs**:

- **CLAUDE.md** — loaded in full at session start, and re-injected from disk after `/compact`
- **Auto-memory `MEMORY.md`** — first 200 lines or 25KB, whichever comes first

**Do not re-read either one.** They are already in your context; reading them again
duplicates roughly 7k tokens per resume for zero new information. Read them explicitly only
if they are genuinely absent from your context.

What is NOT auto-loaded, and is therefore this skill's actual job to read:
`docs/STATUS.md`, the `docs/` reference archives, and README.md.

---

## Step 1: Read Session State (Parallel)

First determine the layout using the detection predicate in
`../save/references/doc-schema.md` (resolve against this skill's base directory, not a
repo-rooted path).

**Schema v2** — read in a single parallel turn:
- `docs/STATUS.md` — the session state. This is the primary read.
- `docs/` folder listing.

**Schema v1** — the state sections are still inside CLAUDE.md, which is already in your
context. Read nothing extra; use what you have, and surface the migration notice in Step 4.

**Schema partial** (an interrupted migration) — read `docs/STATUS.md` for whatever it
already holds; CLAUDE.md, already in your
context, still carries any state sections that were not moved yet. Expect the same section to
appear in neither file or in both, and prefer `docs/STATUS.md` where they disagree. Surface
the interrupted-migration notice in Step 4.

**README.md is conditional in both layouts.** Read it only when CLAUDE.md's Project Overview
leaves the tech stack or setup genuinely unclear. It is typically the largest doc in the
repo and rarely changes; re-reading it every session is the single most expensive habit
this skill can have.

**Do NOT read by default:** `docs/session-history.md`, `docs/completed-work.md`,
`docs/key-decisions.md`, `docs/architecture.md`. These are archives; `deep` mode reads them.

---

## Step 2: Codebase state (pre-injected git state)

The git state below was captured by Claude Code's shell-injection layer **before** this skill content was loaded. Use it directly — no need to invoke Bash for these.

**Recent commits:**
```!
git log --oneline -10 2>/dev/null || echo "(no commits)"
```

**Files changed in last 5 commits:**
```!
git diff --stat HEAD~5 2>/dev/null || echo "(fewer than 5 commits)"
```

**Working-tree status:**
```!
git status --short 2>/dev/null || echo "(not a git repo)"
```

**Top-level structure:**
```!
ls -1 2>/dev/null | head -30
```

### After reading the snapshots above:
Based on the state file's "In Progress" and "Next Steps" (`docs/STATUS.md` in v2, CLAUDE.md
in v1), identify and briefly review:
- Files currently being worked on
- Files that need modification next
- Entry points (main.py, index.js, etc.)

If a deeper directory tour is warranted, you may still issue follow-up `Glob`/`ls` calls — the pre-injection covers the routine 4-command opening turn, not every possible follow-up.

---

## Step 2.5: Quick Health Check (deep mode only)

**Only run this step when `/bx:resume deep` is used. Skip entirely in default mode.**

Verify the project actually works before starting to code:

1. **Detect test/build commands** by checking for:
   - `package.json` → look for `scripts.test`, `scripts.build`
   - `Makefile` → look for `test` or `check` targets
   - `pyproject.toml` → look for `[tool.pytest]` or test scripts
   - `Cargo.toml` → Rust project (use `cargo test`, `cargo build`)
   - Plugin `bin/` helpers on `$PATH` (Claude Code 2.1.91+) → if an enabled plugin ships a `bin/check`, `bin/test`, or `bin/ci` script, it will already be on `$PATH` as a bare command. Prefer it over the ladder above when present, since the plugin author has chosen the canonical command for this project.
2. **If a quick test command exists**, run it and report pass/fail
3. **If a quick build command exists**, run it and report pass/fail
4. **If no commands found**, skip silently — do not warn about missing commands

Keep this fast: use `--no-build` or equivalent flags where possible. The goal is a quick smoke test, not a full CI run.

---

## Step 3: Identify Continuation Point

Based on your analysis, determine:

### 3.0 Context Freshness Check
Compare the **state file's** `Last Updated` date with the latest commit — `docs/STATUS.md`
in schema v2, `CLAUDE.md` in v1. After the split CLAUDE.md may legitimately sit untouched
for weeks while state churns daily, so comparing against CLAUDE.md reports false freshness.

- Run `git log -1 --format=%ci` for the latest commit date
- Parse `Last Updated` from the state file
- If commits are newer, warn: "docs/STATUS.md was last updated [date], but there are [N]
  commits since then."

### 3.1 What Was Last Worked On
From the state file's last session summary (3-5 bullet points) — `## Session History` in
`docs/STATUS.md` for v2, the last-session section of CLAUDE.md for v1:
- Last session's accomplishments
- Any incomplete work
- If more detail is needed, read `docs/session-history.md`

### 3.2 What's Next
From the state file's "Next Steps" (`docs/STATUS.md` in v2, CLAUDE.md in v1):
- Priority 1 task (immediate)
- Priority 2-3 tasks (upcoming)
- Any blockers to address first

### 3.3 Current State Assessment
- Is there incomplete work to finish first?
- Are there any failing tests or broken code?
- Any blockers that need resolution?

---

## Step 4: Present Summary

Read `references/summary-template.md` and present the summary to the user using that template.

---

## Step 5: Hydrate Task List

Read `references/task-hydration.md` and follow its rules to load the state file's tasks into the live task tracker.

---

## Step 6: Validate Structure

Read `../save/references/doc-schema.md` and `../save/references/claude-md-sections.md`
(resolved against this skill's base directory).

- **Schema v2** — check CLAUDE.md and `docs/STATUS.md` carry their required sections. Note
  any missing ones in the summary and suggest `/bx:save`.
- **Schema v1** — report, in the summary:

  > "This repo uses doc schema v1. `/bx:save` will offer to migrate it to v2, which moves
  >  session state out of CLAUDE.md into `docs/STATUS.md` and cuts always-loaded context.
  >  Nothing is deleted."

- **Schema partial** — report, in the summary:

  > "A previous migration to doc schema v2 was interrupted; `/bx:save` will resume it
  >  idempotently. Nothing is deleted."

**`/bx:resume` never migrates and never writes.** Migration belongs at session end, where
doc writing already happens and the diff can be reviewed before committing — not at session
start, before any work has been done.

---

## Guidelines

### Be Concise
- Don't dump entire documentation back at user
- Summarize key points only
- Focus on actionable information

### Be Accurate
- Only state what's actually in the documentation
- If something is unclear, say so
- Don't assume - verify from docs/code

### Be Proactive
- Identify the most logical next step
- Flag any issues or blockers upfront
- Suggest files that will likely need changes

### Handle Missing Documentation
If CLAUDE.md or other docs are missing/incomplete:
```markdown
## Documentation Gap Detected

**Missing:** CLAUDE.md (session context file)

**Recommendation:** Run `/bx:save` first to establish documentation structure, then `/bx:resume` again.

**Or:** I can analyze the codebase directly and create a status summary. Would you like me to proceed?
```

---

## Optional: Deep Dive Mode

If user runs `/bx:resume deep` or `/bx:resume --verbose`:

Read the reference files for full context:
- `docs/session-history.md` -- full session history archive
- `docs/completed-work.md` -- complete task checklist
- `docs/key-decisions.md` -- full decision log

Rotated archive volumes under `docs/archive/` are NOT read even in deep mode — they are
grep-on-demand history; open one only when chasing a specific old session or decision.

Provide additional details:
- Full architecture diagram
- Complete file tree
- All environment variables needed
- Detailed breakdown of each component's state
- Full session history from `docs/session-history.md` combined with the state file's last session

---

## Context Management Tip

After presenting the summary and before starting work, suggest:
> "To free up context consumed by this resume scan, consider running `/compact focus on [recommended task]` before starting work."

Only suggest this if the summary was substantial (deep mode, or multiple reference files were read).

---

## After Resuming

Once you've presented the summary and user confirms direction:

1. **Start working** on the agreed task
2. **Reference docs** as needed during development
3. **At end of session**, remind user: "Run `/bx:save` to save progress"

---

## Quick Reference

| If... | Then... |
|-------|---------|
| Doc schema v2 (marker present) | State lives in `docs/STATUS.md`; CLAUDE.md is already in context, don't re-read it |
| Doc schema v1 (no marker) | State is still inside CLAUDE.md, already in context; note migration is available via `/bx:save` |
| CLAUDE.md missing | Suggest running `/bx:save` first |
| Last session was recent | Focus on the state file's "In Progress" and "Next Steps" |
| Last session was weeks ago | Read more thoroughly, verify code state |
| User specifies task | Skip recommendation, focus on their request |
| Blockers exist | Surface them immediately before starting work |
| Need older context | Check `docs/session-history.md` for archived sessions |
| Need full completed list | Check `docs/completed-work.md` |
| Need full decision log | Check `docs/key-decisions.md` |

---

## Scope

$ARGUMENTS
