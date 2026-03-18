---
name: plan-feature
description: "Interviews the user exhaustively about a feature before implementation. Detects GREENFIELD vs EXISTING project state, runs a structured interview, then enters plan mode and hydrates tasks."
disable-model-invocation: false
allowed-tools: Read, Glob, Grep, Bash(git:*), Bash(ls:*), EnterPlanMode, ExitPlanMode, TaskCreate, TaskUpdate, Edit, Write
argument-hint: "[plan-file-path]"
---

# /plan-feature - Feature Planning Interview

Interview me exhaustively about a feature before any implementation begins.

**Companion skills:**
- `/resume-work` - Start of session context
- `/update-docs` - End of session documentation

---

## Step 1: Detect Project State

First, analyze the current project state:

| State | Condition | Interview Mode |
|-------|-----------|----------------|
| **GREENFIELD** | No code exists, or CLAUDE.md shows "Not Started" for most components | Full architecture interview |
| **EXISTING** | Working codebase exists, CLAUDE.md shows progress | Integration-focused interview |

**Detection logic:**
```
IF no source code files exist (only docs):
    -> GREENFIELD mode
ELSE IF CLAUDE.md exists AND shows completed components:
    -> EXISTING mode (integration focus)
ELSE:
    -> GREENFIELD mode
```

**Announce the mode:**
> "Planning Mode: [GREENFIELD/EXISTING PROJECT]"

---

## Step 2: Read Project Context (Parallel)

### Check Auto-Memory First
Claude Code's auto-memory (`~/.claude/projects/<project-path>/memory/MEMORY.md`) is automatically loaded into your context. If it contains tech stack, architecture, and key paths — you already have stable project facts. Focus your reading on evolving state in CLAUDE.md.

### Read all context in a single parallel call:
- `CLAUDE.md` — current status, completed components, architecture decisions, tech stack, known issues/blockers
- `README.md` — project overview, structure (skim if auto-memory covers this)
- `docs/` folder listing — identify PRD files, architecture docs, API specs
- Plan file from `$ARGUMENTS` (if provided)

This is a single turn — do NOT read these sequentially.

### After the parallel read:
- Read any PRD/spec files referenced in CLAUDE.md "Key Documentation"
- Note existing data models, API specs, configuration patterns, integration details

### Use this context to:
- Skip questions already answered by existing docs
- Reference existing patterns in questions
- Identify integration points
- Understand constraints

---

## Step 3: Identify Feature Scope

If `$ARGUMENTS` provided:
- Read the specified plan file
- Identify NEW FEATURE sections vs existing documentation
- Focus interview on the new/changed parts

If no arguments:
- Ask: "What feature are you planning? Describe it briefly."
- Then proceed with interview

---

## Step 4: Load Interview Rules

Read `references/interview-rules.md` for shared rules, question types, and quick reference tables that apply to both modes.

---

## Step 5: Conduct Interview

Based on the detected mode, read the relevant reference file:

| Mode | Reference File |
|------|---------------|
| **GREENFIELD** | `references/mode-greenfield.md` |
| **EXISTING** | `references/mode-existing.md` |

Follow the interview process:
1. Read all available context (CLAUDE.md, PRD, plan file)
2. Analyze what's specified vs what's ambiguous or missing
3. **Ask questions in batches of 3-5 at a time**
4. **Wait for my answers before continuing**
5. Probe deeper on vague answers
6. Continue until all relevant categories are covered
7. Summarize understanding and confirm before proceeding

**Do NOT start coding until the interview is complete.**

Follow the "Finishing Up" section in the loaded mode reference to present findings and get confirmation.

---

## Step 6: Plan Mode & Task Hydration

After the user confirms ready to proceed, read `references/plan-and-tasks.md` and follow its workflow:
1. Enter Plan Mode → write implementation plan → Exit Plan Mode for approval
2. After approval → hydrate tasks with TaskCreate → begin implementation

---

## Start Now

1. Check auto-memory for existing project context
2. Detect project state (GREENFIELD vs EXISTING)
3. Read CLAUDE.md, README.md, docs/*.md, and plan file (if provided) **in parallel**
4. Announce planning mode
5. Read `references/interview-rules.md`
6. Read mode-specific reference (`references/mode-greenfield.md` or `references/mode-existing.md`)
7. Begin interview with first batch of questions
8. After interview → `EnterPlanMode` → write implementation plan → `ExitPlanMode` for approval
9. After approval → read `references/plan-and-tasks.md` → hydrate tasks with `TaskCreate` → begin implementation

$ARGUMENTS
