---
name: save
description: "Saves session state for the next /bx:resume — drains the task tracker, updates CLAUDE.md + docs/session-history.md, and commits. Fast by default (UPDATE mode via a save-writer subagent); --full adds README/docs sync + rollups. Also runs CREATE/REFACTOR for first-time or monolithic docs. Use at end of a session to save progress, or to create/refactor docs. Migrates repos on the older doc layout to schema v2 on first run, with consent."
disable-model-invocation: true
effort: low
allowed-tools: Read, Edit, Write, Grep, Glob, Bash(git:*), Bash(ls:*), Bash(find:*), Bash(wc:*), Bash(awk:*), Bash(sort:*), Bash(bash:*), TaskList, TaskGet, AskUserQuestion, Agent
argument-hint: "[scope] [--full] [--fast] [--silent] [--skip-memory] [--skip-tasks] [--skip-commit] [--skip-rollup] [--skip-decisions-rollup] [--skip-caps] [--skip-migrate]"
---

# /bx:save - Session Save & Documentation Skill

Save the current session's state so the next `/bx:resume` picks up cleanly, and keep project documentation current. Act as a senior engineer who values clear, maintainable documentation. The common case (UPDATE mode, no flags) is **fast by default**: it drains the task tracker, updates CLAUDE.md + `docs/session-history.md` via the `save-writer` subagent, and commits — without the heavy README/docs sweep. Use `--full` for the periodic deep sweep (README + `docs/*.md` sync + rollups). Use `--silent` for a zero-prompt run: the commit checkpoint auto-commits with the suggested message, and every consent prompt resolves to its safe default (decline/skip) without asking.

**Companion command:** `/bx:resume` - Use at the start of sessions to get up to speed.

---

## Step 1: Detect Documentation State

First, analyze the current documentation state:

| State | Condition | Action |
|-------|-----------|--------|
| **REFACTOR** | Only README.md exists (monolithic) | Split into the v2 structure |
| **CREATE** | No documentation exists | Create the v2 structure from scratch |
| **MIGRATE** | CLAUDE.md exists on doc schema **v1** or **partial** | Migrate to v2, then fall through to UPDATE |
| **UPDATE** | CLAUDE.md exists on doc schema **v2** | Update to reflect current state |

**Detection logic** — the predicate lives in `references/doc-schema.md`; read it and apply
it rather than reimplementing it here:

```
IF README.md exists AND CLAUDE.md missing:
    -> REFACTOR
ELSE IF README.md missing AND CLAUDE.md missing:
    -> CREATE
ELSE:
    layout = doc-schema.md detection predicate
    IF layout is v1 or partial -> MIGRATE
    ELSE                       -> UPDATE
```

The final `ELSE` deliberately swallows the `v0`-with-a-CLAUDE.md case (a hand-written or
`/init` file: no marker, no `docs/STATUS.md`, no state headers). `doc-schema.md`'s "v0 mode
routing" rule is the authority there and requires UPDATE, never CREATE — CREATE would risk
overwriting an existing CLAUDE.md, while UPDATE degrades loudly via `save-writer`'s v1
fallback and its unmatched-delta warnings.

**Announce the mode** at the start of your response:
> "Documentation Mode: [REFACTOR/CREATE/MIGRATE/UPDATE]"

---

## Step 2: Load Shared References

Read these reference files from this skill's `references/` directory:
1. `references/doc-schema.md` — the layout contract and detection predicate (read FIRST; Step 1's mode depends on it)
2. `references/doc-structure-rules.md` — target structure and context preservation rules
3. `references/claude-md-sections.md` — required CLAUDE.md sections contract

---

## Step 3: Load Mode-Specific Reference and Execute

Based on the detected mode, read **only** the relevant reference file and follow its instructions:

| Mode | Reference File |
|------|---------------|
| **REFACTOR** | `references/mode-refactor.md` |
| **CREATE** | `references/mode-create.md` |
| **MIGRATE** | `references/mode-migrate.md` |
| **UPDATE** | `references/mode-update.md` |

**UPDATE mode dispatches the `save-writer` subagent** (Sonnet) to apply the file edits off the main thread — see `references/mode-update.md` (Save Path / Dispatch). CREATE and REFACTOR run inline on the orchestrator. MIGRATE runs on both the fast path and --full, then falls through to UPDATE in the same run.

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
