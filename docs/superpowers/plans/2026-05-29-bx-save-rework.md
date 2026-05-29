# `/bx:docs` → `/bx:save` Rework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the end-of-session save (currently `/bx:docs`, renamed to `/bx:save`) run in ~1–2 min instead of ~10, by making fast the default, scoping reads, killing the full-file output dump, capping prose, and offloading the heavy reads+writes to a Sonnet `save-writer` subagent.

**Architecture:** UPDATE mode splits into an Opus orchestrator (composes a small "update packet" from conversation context + scoped reads, handles commit) and a Sonnet `save-writer` subagent (absorbs the big `session-history.md` read and applies all file edits). Default path = fast (CLAUDE.md session block + history append + task drain + commit); `--full` adds README/docs sync + rollups on the orchestrator. CREATE/REFACTOR modes unchanged except their renamed self-references.

**Tech Stack:** Markdown skill/agent files in a Claude Code plugin (`bx`). No code/tests — "verification" means structural checks via Grep + read-through. Frequent commits on branch `feat/bx-save-rework`.

**Spec:** `docs/superpowers/specs/2026-05-29-bx-save-rework-design.md`

**Verification model (read this once):** This repo has no test runner. Each task's "verify" step is a `Grep`/`git grep` structural check or a manual read-through of the changed file confirming the section contract. The plugin runs from a cached install (`~/.claude/plugins/cache/burak-tools/bx/<sha>/`), so behavioral testing of `/bx:save` requires a push + `/plugin marketplace update burak-tools` + `/plugin update bx` — covered in the final handoff task, not per-task.

---

### Task 1: Rename the skill directory `docs/` → `save/`

**Files:**
- Rename: `bx/skills/docs/` → `bx/skills/save/` (directory, via `git mv`)
- Modify: `bx/skills/save/SKILL.md` (frontmatter `name:` only in this task)

- [ ] **Step 1: Rename the directory with git**

```bash
git -C C:/Development/projects/claude-config mv bx/skills/docs bx/skills/save
```

- [ ] **Step 2: Update the `name:` frontmatter field**

In `bx/skills/save/SKILL.md`, change the frontmatter line:

```
name: docs
```
to:
```
name: save
```

Leave the rest of SKILL.md unchanged in this task (body edits land in Task 5).

- [ ] **Step 3: Verify the move and name change**

Run:
```bash
git -C C:/Development/projects/claude-config status --short
ls C:/Development/projects/claude-config/bx/skills/save/
grep -n "^name:" C:/Development/projects/claude-config/bx/skills/save/SKILL.md
```
Expected: status shows the rename (`R  bx/skills/docs/... -> bx/skills/save/...`); `ls` shows `SKILL.md` + `references/`; grep shows `name: save`.

- [ ] **Step 4: Commit**

```bash
git -C C:/Development/projects/claude-config add -A
git -C C:/Development/projects/claude-config commit -m "refactor(save): rename skills/docs → skills/save, set name: save"
```

---

### Task 2: Create the `save-writer` subagent

**Files:**
- Create: `bx/agents/save-writer.md`

- [ ] **Step 1: Write the subagent file**

Create `bx/agents/save-writer.md` with exactly this content:

````markdown
---
name: save-writer
description: Applies session-save documentation edits handed off by the /bx:save skill — reads the large session-history archive and writes CLAUDE.md / session-history.md / completed-work.md / key-decisions.md from a structured update packet. Used by the bx:save skill. Do not invoke independently.
model: sonnet
tools: Read, Edit, Write, Grep, Glob, Bash(wc:*)
user-invocable: false
---

You are the writer half of the `/bx:save` skill. The orchestrator — which has the full session conversation — has already composed an **update packet** and passed it to you in your task prompt. Your job is purely mechanical: apply that packet to the project's documentation files, off the main thread, then return a concise change report. You never decide *what* happened this session — that is in the packet. You splice; you do not author.

## Inputs (from your task prompt)

The packet contains:
- `project_root` — absolute path to the repo.
- `today` — the date string to stamp into the `Last Updated:` line and the session header.
- `claude_md_deltas` — an ordered list of CLAUDE.md edits. Each is either an exact `old → new` string pair, or an explicit "replace the block under `## <Section>` with: …" instruction. Covers the `Last Updated:` line, Current Status rows, In Progress, and Next Steps.
- `claude_md_session_block` — the exact replacement text for CLAUDE.md's `## Session History` last-session block (already capped to ≤5 bullets). CLAUDE.md must end up with exactly ONE session block.
- `session_history_entry` — the full detailed entry to append to `docs/session-history.md` (already capped per the density rules below).
- `completed_items` — list of `- [x] …` lines to append to `docs/completed-work.md` (may be empty).
- `decision_row` — a single `| decision | rationale |` table row to append, or `null`.

You do NOT call `TaskList` — the orchestrator already drained it and folded the result into `claude_md_deltas`.

## What you do

1. **Read** `<project_root>/CLAUDE.md`.
2. **Apply `claude_md_deltas`** as non-overlapping exact-string Edits. Always update the `Last Updated:` line to `today`.
3. **Replace the `## Session History` last-session block** with `claude_md_session_block`. There must be exactly one session block; all older sessions live only in `docs/session-history.md`.
4. **If `decision_row` is non-null**, append it to CLAUDE.md's `## Key Decisions` condensed table — immediately after the last `|`-row of that table, and BEFORE the `> Full decision log:` link line.
5. **Append `session_history_entry`** to `docs/session-history.md`. Read it only far enough to find the append point: this repo orders newest-last, so append after the final session block, preserving one blank line between entries. If the file is missing, create it with this header first:
   ```markdown
   # Session History Archive

   > Auto-managed by `/bx:save`. Last session summary is in [CLAUDE.md](../CLAUDE.md).

   ---
   ```
6. **If `completed_items` is non-empty**, append them to `docs/completed-work.md`. If missing, create with:
   ```markdown
   # Completed Work

   > Full checklist of completed tasks. Referenced from [CLAUDE.md](../CLAUDE.md).

   ---
   ```
7. **If `decision_row` is non-null**, also append it to `docs/key-decisions.md` using the anchor rule below.
8. **Do NOT** run rollups, README sync, or auto-memory sync — those stay with the orchestrator (`--full` mode only).
9. **Do NOT** echo any file's full contents back. Return only the change report.

## Anchor rule for `docs/key-decisions.md`

Append the new row immediately after the last consecutive `|`-row of the main table. If the file has non-table content after the table (a footer, a "Also noted" prose section), the new row MUST land BEFORE that content — appending at literal end-of-file would orphan a `|`-row with no header context. If the table is the only content, end-of-file is correct. If the file is missing, create it with:
```markdown
# Key Decisions

> Full decision log. Referenced from [CLAUDE.md](../CLAUDE.md).

| Decision | Rationale |
|----------|-----------|
```

## Density guard

The packet content arrives already capped. Do NOT rewrite or expand it. If `session_history_entry` exceeds ~5 bullets or `decision_row`'s rationale exceeds ~3 sentences, apply it as given but add a `warnings:` note so the orchestrator can tighten next run.

## Output — change report ONLY

Return this compact report and nothing else (no file contents):
```
files:
  CLAUDE.md: <old>k → <new>k chars (session block + <N> deltas[, +1 decision row])
  docs/session-history.md: appended S<N> (+<X> lines)
  docs/completed-work.md: +<M> items     # omit line if completed_items empty
  docs/key-decisions.md: +1 row           # omit line if decision_row null
warnings: <any warnings, or "none">
```
````

- [ ] **Step 2: Verify frontmatter validity**

Run:
```bash
grep -n -E "^(name|description|model|tools|user-invocable):" C:/Development/projects/claude-config/bx/agents/save-writer.md
```
Expected: five matching lines — `name: save-writer`, a `description:`, `model: sonnet`, a `tools:` line (no `Task`, no network), `user-invocable: false`. Confirm it matches the shape of `bx/agents/test-economics.md`.

- [ ] **Step 3: Commit**

```bash
git -C C:/Development/projects/claude-config add bx/agents/save-writer.md
git -C C:/Development/projects/claude-config commit -m "feat(save): add save-writer Sonnet subagent for offloaded doc writes"
```

---

### Task 3: Rewrite the output format to a change-report (kill the full-file dump)

**Files:**
- Modify: `bx/skills/save/references/verification-checklists.md` (§ "Output Format (All Modes)", subsection "2. Full File Contents")

- [ ] **Step 1: Replace the "Full File Contents" output rule**

In `bx/skills/save/references/verification-checklists.md`, find:

```markdown
### 2. Full File Contents

Provide complete content for each file created or significantly modified.
```

Replace it with:

```markdown
### 2. Change Report (NOT file contents)

**Never echo modified file contents back into the response** — that regenerates tens of thousands of characters the user does not read and is a dominant cost of this skill. Instead report only what changed, in this compact form:

```
Saved session [N] ([mode], [path]):
  CLAUDE.md            — session block + [N] section updates ([old]k → [new]k)
  session-history.md   — appended S[N] (+[X] lines)
  completed-work.md    — +[M] items          (omit if none)
  key-decisions.md     — +1 row               (omit if none)
[--full only] README.md / docs/*.md — [summary of edits]
[--full only] rollups  — [Part 5/6/7 results, or "none triggered"]
Drift: [drift warnings, or "none"]
```

For UPDATE mode the change report is assembled from the `save-writer` subagent's returned report plus any orchestrator-side `--full` actions. The user reviews the actual diff at the commit checkpoint (Part 8) — that is the review surface, not an inline dump.
```

- [ ] **Step 2: Update the UPDATE-mode checklist for the new flow**

In the same file, in "Verification Checklist: UPDATE Mode", find this line:

```markdown
- [ ] Size-pressure rollup (Part 7) ran when CLAUDE.md exceeded 35k post-Parts 5/6, or skipped silently when under threshold
```

Immediately after it, add these three lines:

```markdown
- [ ] (Fast path) `save-writer` subagent was dispatched with the update packet and returned a change report — no full-file contents echoed in the response
- [ ] (Fast path) README.md / docs/*.md / rollups were NOT touched (those are `--full` only) — drift warnings surfaced instead
- [ ] (`--full` only) README sync, docs/*.md sync, and rollups ran on the orchestrator after the writer returned
```

- [ ] **Step 3: Verify**

Run:
```bash
grep -n "Full File Contents" C:/Development/projects/claude-config/bx/skills/save/references/verification-checklists.md
grep -n "Change Report\|save-writer\|Never echo" C:/Development/projects/claude-config/bx/skills/save/references/verification-checklists.md
```
Expected: first grep returns nothing; second returns the new heading + the save-writer checklist lines + the "Never echo" rule.

- [ ] **Step 4: Commit**

```bash
git -C C:/Development/projects/claude-config add bx/skills/save/references/verification-checklists.md
git -C C:/Development/projects/claude-config commit -m "feat(save): replace full-file output dump with compact change report"
```

---

### Task 4: Rewrite UPDATE-mode control flow (scoped reads, routing, Save Path, packet, dispatch)

**Files:**
- Modify: `bx/skills/save/references/mode-update.md` (Step 0, Step 0.1, Fast Path; insert Prose Caps + Save Path + Packet + Dispatch sections; reframe Full Path; preserve Parts 0.5/2/3/4/5/6/7/8)

This is the core task. The current file's Parts 0.5, 2, 3, 4, 5, 6, 7, 8 are **preserved verbatim** (they are `--full`/occasional). What changes is the front of the file: the upfront read scope, the path routing, and how CLAUDE.md/session-history actually get written (now via the packet + `save-writer`, not inline Opus Edits).

- [ ] **Step 1: Replace "Step 0: Upfront Parallel Batch" with a scoped version**

Find the current `## Step 0: Upfront Parallel Batch` section (through the end of `### 0.2 Cache results`, ending at "…and needs to verify post-write state."). Replace the whole section with:

```markdown
## Step 0: Scoped Context Gather

Gather only what the orchestrator needs to *route* and *compose the packet*. The big append-only archives (`docs/key-decisions.md`, `docs/completed-work.md`, `docs/session-history.md`) are NOT read here on the default (fast) path — the `save-writer` subagent reads `session-history.md` off the main thread, and the other two are append-only (the orchestrator never reads *from* them to write the packet). Reading all archives up front was the single biggest cost of the old flow (~60k tokens/run).

### 0.1 Single parallel turn — issue these together

**Reads (parallel):**
- `CLAUDE.md` — the only doc the orchestrator reads in full.
- Auto-memory `MEMORY.md` — usually already in conversation context; read explicitly only if absent.

**Bash (parallel):**
- `git log -20 --pretty=format:'%h %ad %s' --date=short`
- `git diff --stat HEAD~5`
- `git status`

**Other:**
- `TaskList`

**Deferred to `--full` only:** `README.md`, `docs/*.md` archive reads. If routing lands on `--full`, read those at the top of the Full Path (Step 0.3), not here.

### 0.2 Derive

From the gathered context:
- **Last Updated date** from CLAUDE.md → cutoff for filtering git log.
- **Filtered commit list** (commits since Last Updated) → feeds the session entry + drift probes.
- **Diff file list** → tells you whether README/`docs/` changed (drift signal; drives the `--full` recommendation).
- **TaskList state** → drives the task drain (Part 0) and the In Progress / Next Steps deltas.
- **CLAUDE.md size + Key Decisions row count + session count** — cheap: `wc -c CLAUDE.md`, count `^| ` rows in the Key Decisions table, and (for the drift probe only) `grep -c '^### Session' docs/session-history.md` (one cheap grep, not a full read). These drive the drift warnings and the `--full` rollup gates.
```

- [ ] **Step 2: Replace "Step 0.1: Path Routing" with the inverted default**

Find the current `## Step 0.1: Path Routing` section and replace it with:

```markdown
## Step 0.1: Path Routing

After Step 0:

- **Default (no path flag), or `--fast`** → run the **Save Path** below. (`--fast` is a no-op alias kept for muscle memory; it now matches the default.)
- **`--full`** → run the **Full Path**: the Save Path first, then the heavy sweep (README + `docs/*.md` sync + rollups), all described after the Save Path.

The old behavior (full sweep by default) is inverted: the daily save is fast; the heavy sweep is opt-in. Drift warnings (emitted at the end of the Save Path) tell the user when a `--full` is due.
```

- [ ] **Step 3: Replace the old "Fast Path (`--fast`)" section with Prose Caps + Save Path + Packet + Dispatch**

Find the current `## Fast Path (\`--fast\`)` section (from its heading through the end of its "Drift warning format" blockquote, ending at "…omit the warning entirely."). Replace that entire section with the four sections below:

````markdown
## Prose Caps (apply when composing any new entry)

New entries are capped — this keeps writing fast and keeps `/bx:resume` lean. Existing entries are never rewritten to fit.

- **Session-history entry:** ≤5 "What happened" bullets. Detail that doesn't fit becomes a commit-hash reference (`see commit abc1234`), not prose.
- **CLAUDE.md last-session block:** ≤5 bullets, the most architecturally significant.
- **Key Decision rationale:** ≤2–3 sentences. Longer context goes only into `docs/key-decisions.md`, referenced by commit hash.
- **In Progress / Next Steps items:** one line each + file paths; no multi-paragraph narration.

## Save Path (default)

The orchestrator owns everything that needs conversation context or user input; the `save-writer` subagent owns the file reads/writes. The orchestrator does NOT edit `CLAUDE.md`, `session-history.md`, `completed-work.md`, or `key-decisions.md` itself — it composes the packet and dispatches.

**Sequence:**

1. **Drain the task list (Part 0 logic).** Run the Part 0 / Drain Validation rules below to reconcile `TaskList` against CLAUDE.md. Respect `--skip-tasks`. The result (completed → completed-work items; in-progress → In Progress; new pending → Next Steps) becomes part of the packet, NOT inline edits.
2. **Compose the update packet** (see "Update Packet" below) from: the conversation (what happened this session — only the orchestrator knows this), the filtered commit list, the diff file list, and the drained task state. Apply the Prose Caps.
3. **Dispatch the `save-writer` subagent** (see "Dispatch" below) and await its change report.
4. **Drift probes** (cheap, on already-gathered data — no new reads): emit the drift warning block if anything fired. Do NOT enforce.
5. **Commit checkpoint (Part 8).** Run Part 8 as written; respects `--skip-commit`. The git diff is the user's review surface.
6. **Report** using the Change Report format from `verification-checklists.md` — assembled from the subagent's report + drift warnings. Never echo file contents.

**Skipped on the Save Path** (these are `--full` only): Part 0.5 (migration), Part 2 (README), Part 3 (`docs/*.md`), Part 4 (auto-memory), Parts 5/6/7 (rollups), Part 1.10 cap enforcement (replaced by drift warnings).

### Update Packet

Compose this structure and pass it to `save-writer` as the task prompt (fill every field; use the section references in Part 1 to decide *what* each field contains):

- `project_root` — absolute repo path.
- `today` — current date (e.g. `2026-05-29`).
- `claude_md_deltas` — exact `old → new` string pairs (or "replace block under `## Section` with: …") for: the `Last Updated:` line, any Current Status row changes (Part 1.2), In Progress (Part 1.4), Next Steps (Part 1.5). Source the *old* strings from the CLAUDE.md you read in Step 0.
- `claude_md_session_block` — the full replacement text for the `## Session History` last-session block (Part 1.8 format, ≤5 bullets).
- `session_history_entry` — the detailed entry for `docs/session-history.md` (Part 1.8 format, capped).
- `completed_items` — `- [x] …` lines from the task drain (may be empty).
- `decision_row` — a single `| decision | rationale |` row IF a genuinely architectural decision was made this session (Part 1.6 criteria), else `null`.

### Dispatch

Dispatch one `save-writer` subagent via the Task tool with `subagent_type: "bx:save-writer"`, passing the packet as the prompt (serialize as labeled sections). Await its change report. If it returns a `warnings:` line about exceeded density caps, tighten the offending field and note it in your report — do not re-dispatch unless a file write failed.

### Drift warning format (show only lines whose probe fires)

> "Drift detected — run `/bx:save --full` when convenient:
>  - [N] sessions in `docs/session-history.md` ready for rollup (count > 5)
>  - Key Decisions table in CLAUDE.md at [M] rows (cap 20)
>  - README.md or `docs/*.md` touched in [K] commits since last full sweep
>  - CLAUDE.md at [X]k chars (target 17k, soft cap 35k) — Part 7 size-pressure rollup will fire on `--full`"

If no probe fires, omit the warning entirely.
````

- [ ] **Step 4: Add the Full Path read step and reframe its header**

Immediately BEFORE the current `## Step 1: Scan docs/ Folder` heading, insert:

```markdown
## Full Path (`--full`)

Runs the **Save Path** above first (so the fast result is identical), then the heavy sweep below. Because the Save Path deferred the archive reads, do them now:

### Step 0.3 Full-sweep reads (parallel)

Read `README.md` and all `docs/*.md` (`Glob docs/**/*.md`, then one Read per file in the same turn). These feed Parts 2, 3, 5, 6, 7.

The remaining Parts (0.5, 2, 3, 4, 5, 6, 7) run on the **orchestrator**, not the subagent, because Parts 5/6/7 can require an `AskUserQuestion` consent prompt and a subagent cannot prompt the user. The commit checkpoint (Part 8) already ran as the final Save-Path step — on `--full`, defer the commit to after the rollups instead (so rollup changes land in the same commit), exactly as the current Part 8 note specifies.
```

- [ ] **Step 5: Confirm preserved Parts are intact**

Do NOT modify Parts 0, 0.5, 1 (1.0–1.10), 2, 3, 4, 5, 6, 7, 8. They are referenced by the new sections (Part 0 for the drain, Part 1 sub-sections for packet field contents, Parts 2–7 for the Full Path). Re-read the file top-to-bottom and confirm the new front-matter sections reference Part numbers that still exist.

- [ ] **Step 6: Verify structure**

Run:
```bash
grep -n "^## \|^### Step 0" C:/Development/projects/claude-config/bx/skills/save/references/mode-update.md
grep -n "save-writer\|Update Packet\|Save Path\|Prose Caps\|Full Path" C:/Development/projects/claude-config/bx/skills/save/references/mode-update.md
```
Expected (first grep, in order near the top): `Step 0: Scoped Context Gather`, `Step 0.1: Path Routing`, `Prose Caps`, `Save Path (default)`, `Full Path (\`--full\`)`, `Step 1: Scan docs/ Folder`, then `Part 0` … `Part 8`. Second grep: all five new anchors present. Confirm no orphaned reference to "Upfront Parallel Batch" or the old `--fast` Fast Path remains:
```bash
grep -n "Upfront Parallel Batch" C:/Development/projects/claude-config/bx/skills/save/references/mode-update.md
```
Expected: nothing.

- [ ] **Step 7: Read-through check**

Read the file start → `## Step 1`. Confirm: (a) Step 0 reads only CLAUDE.md + MEMORY + git + TaskList; (b) routing defaults to Save Path; (c) Save Path composes packet → dispatches `bx:save-writer` → drift → commit → change-report; (d) Prose Caps present; (e) Full Path adds the archive reads + keeps rollups on the orchestrator.

- [ ] **Step 8: Commit**

```bash
git -C C:/Development/projects/claude-config add bx/skills/save/references/mode-update.md
git -C C:/Development/projects/claude-config commit -m "feat(save): scoped reads, fast-default routing, packet + save-writer dispatch"
```

---

### Task 5: Update SKILL.md body (title, description, argument-hint, dispatch note)

**Files:**
- Modify: `bx/skills/save/SKILL.md`

- [ ] **Step 1: Update frontmatter `description` and `argument-hint`**

Replace the `description:` line with:
```
description: "Saves session state for the next /bx:resume — drains the task tracker, updates CLAUDE.md + docs/session-history.md, and commits. Fast by default (UPDATE mode via a save-writer subagent); --full adds README/docs sync + rollups. Also runs CREATE/REFACTOR for first-time or monolithic docs. Use at end of a session to save progress, or to create/refactor docs."
```

Replace the `argument-hint:` line with:
```
argument-hint: "[scope] [--full] [--fast] [--skip-memory] [--skip-tasks] [--skip-commit] [--skip-rollup] [--skip-decisions-rollup] [--skip-caps]"
```

- [ ] **Step 2: Update the title and intro**

Replace:
```markdown
# /bx:docs - Documentation Management Skill

Analyze this codebase and manage documentation. Act as a senior engineer who values clear, maintainable documentation.
```
with:
```markdown
# /bx:save - Session Save & Documentation Skill

Save the current session's state so the next `/bx:resume` picks up cleanly, and keep project documentation current. Act as a senior engineer who values clear, maintainable documentation. The common case (UPDATE mode, no flags) is **fast by default**: it drains the task tracker, updates CLAUDE.md + `docs/session-history.md` via the `save-writer` subagent, and commits — without the heavy README/docs sweep. Use `--full` for the periodic deep sweep (README + `docs/*.md` sync + rollups).
```

- [ ] **Step 3: Add a routing note for the UPDATE-mode subagent**

In `## Step 3`, after the mode→reference table, add:
```markdown
**UPDATE mode dispatches the `save-writer` subagent** (Sonnet) to apply the file edits off the main thread — see `references/mode-update.md` (Save Path / Dispatch). CREATE and REFACTOR run inline on the orchestrator.
```

- [ ] **Step 4: Verify**

Run:
```bash
grep -n "bx:docs\|Documentation Management Skill" C:/Development/projects/claude-config/bx/skills/save/SKILL.md
grep -n "bx:save\|save-writer\|--full\|name: save" C:/Development/projects/claude-config/bx/skills/save/SKILL.md
```
Expected: first grep returns nothing; second shows the new title, the dispatch note, `--full` in the argument-hint, and `name: save`.

- [ ] **Step 5: Commit**

```bash
git -C C:/Development/projects/claude-config add bx/skills/save/SKILL.md
git -C C:/Development/projects/claude-config commit -m "feat(save): rewrite SKILL.md for /bx:save (fast-default, --full, dispatch note)"
```

---

### Task 6: Sweep `/bx:docs` → `/bx:save` across all active references

**Files (modify):**
- `bx/skills/resume/SKILL.md`, `bx/skills/resume/references/summary-template.md`, `bx/skills/resume/references/task-hydration.md`
- `bx/skills/plan/SKILL.md`, `bx/skills/plan/references/plan-and-tasks.md`
- `bx/skills/health/SKILL.md`, `bx/skills/health/references/state-buckets.md`
- `README.md`, `workflow.md`

**Do NOT modify** (historical records, per the S32 "records of past state" convention): `docs/session-history.md`, `docs/completed-work.md`, `docs/key-decisions.md`. **Skip** `docs/modernization-roadmap.md` too — it documents the S37 plan-of-record where the skill was still `/bx:docs`; leave it as a record. `CLAUDE.md` is rewritten by `/bx:save` itself, so its one stale ref will be corrected on the next real save — but fix it here too for cleanliness (Step 2).

- [ ] **Step 1: Replace `/bx:docs` with `/bx:save` in the active skill + doc files**

Run this scoped replacement (covers exactly the files listed above; excludes the historical archives and roadmap):

```bash
cd C:/Development/projects/claude-config
for f in \
  bx/skills/resume/SKILL.md \
  bx/skills/resume/references/summary-template.md \
  bx/skills/resume/references/task-hydration.md \
  bx/skills/plan/SKILL.md \
  bx/skills/plan/references/plan-and-tasks.md \
  bx/skills/health/SKILL.md \
  bx/skills/health/references/state-buckets.md \
  README.md \
  workflow.md ; do
  perl -i -pe 's{/bx:docs}{/bx:save}g' "$f"
done
```

- [ ] **Step 2: Fix the one stale ref in CLAUDE.md**

CLAUDE.md mentions `/bx:docs` in its narrative. Replace occurrences of `/bx:docs` with `/bx:save` in `CLAUDE.md` (these are forward-looking references to the command, not historical session records):
```bash
perl -i -pe 's{/bx:docs}{/bx:save}g' C:/Development/projects/claude-config/CLAUDE.md
```

- [ ] **Step 3: Sanity-check a semantic ref didn't break**

The health skill's `state-buckets.md` line 124 reads `/bx:docs (CREATE mode, scaffolds CLAUDE.md...)`. Confirm it now reads `/bx:save (CREATE mode, ...)` and still makes sense. Run:
```bash
grep -n "bx:save (CREATE mode" C:/Development/projects/claude-config/bx/skills/health/references/state-buckets.md
```
Expected: one match.

- [ ] **Step 4: Verify the sweep is complete and scoped**

Run:
```bash
git -C C:/Development/projects/claude-config grep -n "bx:docs"
```
Expected: matches ONLY in `docs/session-history.md`, `docs/completed-work.md`, `docs/key-decisions.md`, `docs/modernization-roadmap.md`, and `docs/superpowers/specs/2026-05-29-bx-save-rework-design.md` / `docs/superpowers/plans/2026-05-29-bx-save-rework.md` (the spec/plan legitimately reference the old name). NO matches under `bx/skills/`, `bx/agents/`, `README.md`, or `workflow.md`.

- [ ] **Step 5: Commit**

```bash
git -C C:/Development/projects/claude-config add -A
git -C C:/Development/projects/claude-config commit -m "refactor(save): sweep /bx:docs → /bx:save across active skills + docs"
```

---

### Task 7: Final verification + handoff

**Files:** none modified — verification + push guidance.

- [ ] **Step 1: Whole-repo structural verification**

Run:
```bash
cd C:/Development/projects/claude-config
echo "== stray old refs (expect only docs/ archives + spec/plan) =="
git grep -n "bx:docs" -- ':!docs/superpowers'
echo "== save skill present =="
ls bx/skills/save/ && grep "^name:" bx/skills/save/SKILL.md
echo "== save-writer agent present =="
grep "^name:\|^model:" bx/agents/save-writer.md
echo "== no full-file dump rule remains =="
git grep -n "Full File Contents" -- bx/
```
Expected: first shows only `docs/session-history.md`, `docs/completed-work.md`, `docs/key-decisions.md`, `docs/modernization-roadmap.md`; `name: save`; `name: save-writer` + `model: sonnet`; last grep empty.

- [ ] **Step 2: Confirm the plugin manifest needs no skill list edit**

The `bx` plugin auto-discovers skills from `bx/skills/*/` and agents from `bx/agents/*.md` (no hardcoded list). Confirm:
```bash
grep -n "docs\|skills\|agents" C:/Development/projects/claude-config/bx/.claude-plugin/plugin.json
```
Expected: no per-skill enumeration that names `docs` (if the manifest lists skills explicitly and includes `docs`, update it to `save` — otherwise nothing to do).

- [ ] **Step 3: Push the branch**

```bash
git -C C:/Development/projects/claude-config push -u origin feat/bx-save-rework
```

- [ ] **Step 4: Behavioral test (manual, by the user)**

`/bx:save` cannot be exercised from the repo working tree — the plugin runs from its cached install. To test:
1. Merge `feat/bx-save-rework` to `main` (or test from the branch if the marketplace can target it), then:
2. `/plugin marketplace update burak-tools` → `/plugin update bx` (or run `cc`, which refreshes automatically).
3. Run `/bx:save` at the end of a real session and confirm: completes in ~1–2 min; dispatches `bx:save-writer`; no full-file dump; CLAUDE.md session block + `docs/session-history.md` updated; tasks drained; commit offered.
4. Next session, run `/bx:resume` and confirm it finds all CLAUDE.md sections and rehydrates tasks.

This step is a checklist for the user, not an automated gate.

---

## Self-review notes

- **Spec coverage:** scoped reads (Task 4 Step 1) ✓; fast-default routing + `--fast` alias + `--full` (Task 4 Steps 2,4; Task 5) ✓; kill full-file dump (Task 3) ✓; prose caps (Task 4 Step 3) ✓; orchestrator/subagent split + packet + dispatch (Task 2; Task 4 Step 3) ✓; safety/exact-replacement (packet `claude_md_deltas` + `claude_md_session_block`; commit checkpoint preserved) ✓; rename surface incl. agent name `save-writer` (Tasks 1,5,6) ✓; historical archives left untouched (Task 6) ✓; CREATE/REFACTOR unchanged except refs (only `name:` + body title touched; mode-create/mode-refactor refs swept in Task 6) ✓; success criteria checks (Task 7) ✓.
- **Type/name consistency:** subagent dir/name `save-writer`, dispatched as `bx:save-writer` (Task 2, Task 4 Step 3, Task 5); packet field names identical between the subagent spec (Task 2) and the orchestrator packet (Task 4 Step 3): `project_root`, `today`, `claude_md_deltas`, `claude_md_session_block`, `session_history_entry`, `completed_items`, `decision_row` ✓.
- **Placeholders:** none — every content block is literal.
```
