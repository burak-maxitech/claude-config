---
name: save
description: "Saves session state for the next /bx:resume — drains the task tracker, updates CLAUDE.md + docs/session-history.md, and commits. Fast by default (UPDATE mode via a save-writer subagent); --full adds README/docs sync + rollups. Also runs CREATE/REFACTOR for first-time or monolithic docs. Use at end of a session to save progress, or to create/refactor docs."
disable-model-invocation: true
effort: low
allowed-tools: Read, Edit, Write, Grep, Glob, Bash(git:*), Bash(ls:*), Bash(find:*), Bash(wc:*), Bash(awk:*), Bash(sort:*), TaskList, TaskGet, AskUserQuestion, Task
argument-hint: "[scope] [--full] [--fast] [--skip-memory] [--skip-tasks] [--skip-commit] [--skip-rollup] [--skip-decisions-rollup] [--skip-caps]"
---

# /bx:save - Session Save & Documentation Skill

Save the current session's state so the next `/bx:resume` picks up cleanly, and keep project documentation current. Act as a senior engineer who values clear, maintainable documentation. The common case (UPDATE mode, no flags) is **fast by default**: it drains the task tracker, updates CLAUDE.md + `docs/session-history.md` via the `save-writer` subagent, and commits — without the heavy README/docs sweep. Use `--full` for the periodic deep sweep (README + `docs/*.md` sync + rollups).

**Companion command:** `/bx:resume` - Use at the start of sessions to get up to speed.

---

## Step 1: Detect Documentation State

First, analyze the current documentation state:

| State | Condition | Action |
|-------|-----------|--------|
| **REFACTOR** | Only README.md exists (monolithic) | Split into three files |
| **CREATE** | No documentation exists | Create all three files from scratch |
| **UPDATE** | README.md + CLAUDE.md + docs/*.md exist | Update to reflect current state |

**Detection logic:**
```
IF README.md exists AND CLAUDE.md missing:
    -> REFACTOR mode: Split README.md into proper structure
ELSE IF README.md missing:
    -> CREATE mode: Generate all documentation from codebase analysis
ELSE:
    -> UPDATE mode: Update existing documentation structure
```

**Announce the mode** at the start of your response:
> "Documentation Mode: [REFACTOR/CREATE/UPDATE]"

---

## Step 2: Load Shared References

Read these reference files from this skill's `references/` directory:
1. `references/doc-structure-rules.md` — target structure and context preservation rules
2. `references/claude-md-sections.md` — required CLAUDE.md sections contract

---

## Step 3: Load Mode-Specific Reference and Execute

Based on the detected mode, read **only** the relevant reference file and follow its instructions:

| Mode | Reference File |
|------|---------------|
| **REFACTOR** | `references/mode-refactor.md` |
| **CREATE** | `references/mode-create.md` |
| **UPDATE** | `references/mode-update.md` |

**UPDATE mode dispatches the `save-writer` subagent** (Sonnet) to apply the file edits off the main thread — see `references/mode-update.md` (Save Path / Dispatch). CREATE and REFACTOR run inline on the orchestrator.

Execute the instructions in the loaded reference file.

---

## Step 4: Verify

Read `references/verification-checklists.md` and:
1. Produce the output summary in the specified format
2. Run through the checklist for the active mode
3. Confirm all items pass

---

## Scope

$ARGUMENTS
