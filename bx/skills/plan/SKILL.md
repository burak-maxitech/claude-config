---
name: plan
description: "Interviews the user exhaustively about a feature before implementation. Detects GREENFIELD vs EXISTING project state, runs a structured interview, then enters plan mode and hydrates tasks."
disable-model-invocation: false
effort: high
allowed-tools: Read, Glob, Grep, Bash(git:*), Bash(ls:*), EnterPlanMode, ExitPlanMode, AskUserQuestion, TaskCreate, TaskUpdate, Edit, Write
argument-hint: "[plan-file-path]"
---

# /bx:plan - Feature Planning Interview

Interview me exhaustively about a feature before any implementation begins.

**Companion skills:**
- `/bx:resume` - Start of session context
- `/bx:save` - End of session documentation

---

## Step 0: Triviality Check

Before anything else, gauge the size of the request. If the user's description fits in **one sentence and one or two files** — typo fixes, log-line additions, variable renames, single-function tweaks — the planning interview is overhead, not value.

In that case, respond:
> "This sounds small enough to do directly without the planning interview. Want me to just make the change? Re-run `/bx:plan` if it turns out larger than expected."

Then stop the skill. Only continue to Step 1 if the user confirms they want the full interview, or if the request is clearly multi-file / architecture-touching / introduces a new pattern.

Per the official best-practices guidance: *"For tasks where the scope is clear and the fix is small (typo, log line, rename) ask Claude to do it directly... If you could describe the diff in one sentence, skip the plan."*

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
3. Drive the interview per `references/interview-rules.md`
4. **Wait for answers before continuing**
5. Probe deeper on vague answers — re-ask with refined options
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

1. **Triviality check** — if the request fits in one sentence and 1-2 files, suggest skipping the skill and stop
2. Check auto-memory for existing project context
3. Detect project state (GREENFIELD vs EXISTING)
4. Read CLAUDE.md, README.md, docs/*.md, and plan file (if provided) **in parallel**
5. Announce planning mode
6. Read `references/interview-rules.md`
7. Read mode-specific reference (`references/mode-greenfield.md` or `references/mode-existing.md`)
8. Begin interview with first batch of questions (via `AskUserQuestion` when available)
9. After interview → `EnterPlanMode` → write implementation plan → `ExitPlanMode` for approval
10. After approval → read `references/plan-and-tasks.md` → hydrate tasks with `TaskCreate` → begin implementation

$ARGUMENTS
