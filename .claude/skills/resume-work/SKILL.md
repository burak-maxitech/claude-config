---
name: resume-work
description: "Resumes development on a project after a break. Reads docs, scans git state, identifies next task, and hydrates live task tracker. Use at the start of every coding session."
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(git:*), Bash(ls:*), TaskCreate, TaskGet, TaskList
argument-hint: "[deep]"
---

# /resume-work - Resume Development Session

Get up to speed on this project and continue development from where we left off.

**Companion command:** `/update-docs` - Use at the end of sessions to save progress.

---

## Your Task

You are resuming work on this project after a break (hours, days, or weeks). Your goal is to:

1. **Understand the project** - What it does, how it works
2. **Know current state** - What's done, what's in progress, what's next
3. **Be ready to code** - Have full context to continue immediately

---

## Step 0: Check Auto-Memory

Claude Code's auto-memory (`~/.claude/projects/<project-path>/memory/MEMORY.md`) is **automatically loaded** into your context at session start. Before reading project docs:

1. **Check if auto-memory already has project context** -- it may contain tech stack, key paths, common commands, and architecture patterns synced by `/update-docs`
2. **If auto-memory has good coverage**, you can skim README.md rather than deep-reading it -- focus your attention on CLAUDE.md for evolving state
3. **If auto-memory is empty or missing**, proceed normally and note that `/update-docs` should be run at end of session to populate it

---

## Step 1: Read Documentation (Parallel)

**Read all core documentation files in a single parallel call:**

Use parallel tool calls to read these simultaneously:
- `CLAUDE.md` -- primary context file (project overview, status, session history, next steps, decisions, blockers, architecture)
- `README.md` -- project purpose, tech stack, structure, setup instructions (skim if auto-memory already covers this)
- `docs/` folder listing -- identify what documentation files exist

This is a single turn -- do NOT read these sequentially.

### After the parallel read:
- If CLAUDE.md references specific docs/ files in "Key Documentation," read those next
- PRD files (contain detailed requirements) -- read if present
- `docs/session-history.md` -- archived session logs (only read if you need context older than 3 sessions)
- Skip sample/example data files unless needed

---

## Step 2: Analyze Current Codebase (Parallel)

**Run all git commands and structure scan in a single parallel call:**

Execute these simultaneously (all are independent):
- `git log --oneline -10` -- recent commits
- `git diff --stat HEAD~5` -- what files changed recently
- `git status` -- any uncommitted changes
- `ls -la` and `ls -la */` -- verify project structure matches docs

This is a single turn -- do NOT run these sequentially.

### After the parallel scan:
Based on CLAUDE.md "In Progress" and "Next Steps," identify and briefly review:
- Files currently being worked on
- Files that need modification next
- Entry points (main.py, index.js, etc.)

---

## Step 3: Identify Continuation Point

Based on your analysis, determine:

### 3.1 What Was Last Worked On
From CLAUDE.md session history:
- Last session's accomplishments
- Files that were modified
- Any incomplete work

### 3.2 What's Next
From CLAUDE.md "Next Steps":
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

Read `references/task-hydration.md` and follow its rules to load CLAUDE.md tasks into the live task tracker.

---

## Step 6: Validate CLAUDE.md Structure

Cross-reference CLAUDE.md against the section contract at `../update-docs/references/claude-md-sections.md`. If sections are missing or malformed, note this in the summary and suggest running `/update-docs` to fix it.

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

**Recommendation:** Run `/update-docs` first to establish documentation structure, then `/resume-work` again.

**Or:** I can analyze the codebase directly and create a status summary. Would you like me to proceed?
```

---

## Optional: Deep Dive Mode

If user runs `/resume-work deep` or `/resume-work --verbose`:

Provide additional details:
- Full architecture diagram
- Complete file tree
- All environment variables needed
- Detailed breakdown of each component's state
- Full session history -- read `docs/session-history.md` if it exists, combined with CLAUDE.md sessions

---

## After Resuming

Once you've presented the summary and user confirms direction:

1. **Start working** on the agreed task
2. **Reference docs** as needed during development
3. **At end of session**, remind user: "Run `/update-docs` to save progress"

---

## Quick Reference

| If... | Then... |
|-------|---------|
| CLAUDE.md exists | Read it first, it has everything you need |
| CLAUDE.md missing | Suggest running `/update-docs` first |
| Last session was recent | Focus on "In Progress" and "Next Steps" |
| Last session was weeks ago | Read more thoroughly, verify code state |
| User specifies task | Skip recommendation, focus on their request |
| Blockers exist | Surface them immediately before starting work |
| Need older context | Check `docs/session-history.md` for archived sessions |

---

## Scope

$ARGUMENTS
