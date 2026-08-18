# MODE: UPDATE (Refresh Existing Docs)

When documentation structure exists, update to reflect current state.

## Step 0: Scoped Context Gather

Gather only what the orchestrator needs to *route* and *compose the packet*. The big append-only archives (`docs/key-decisions.md`, `docs/completed-work.md`, `docs/session-history.md`) are NOT read here on the default (fast) path — the `save-writer` subagent reads `session-history.md` off the main thread, and the other two are append-only (the orchestrator never reads *from* them to write the packet). Reading all archives up front was the single biggest cost of the old flow (~60k tokens/run).

### 0.1 Single parallel turn — issue these together

**Reads (parallel):**
- `CLAUDE.md` — read in full.
- `docs/STATUS.md` — the session-state file (schema v2). On a v1 repo this does not exist;
  MIGRATE runs first, so by the time UPDATE executes the repo is always v2 unless migration
  was skipped or declined. Handle both: if STATUS.md is absent, target CLAUDE.md's state
  sections exactly as v1 did.
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
- **CLAUDE.md size + docs/STATUS.md size + Key Decisions row count + session count** — cheap: `wc -c CLAUDE.md docs/STATUS.md` for size (omit `docs/STATUS.md` from the command on a v1 repo where it does not exist); count the Key Decisions table rows with the **Grep tool** (`output_mode: count`, pattern `^\| `); and (for the drift probe only) count sessions with the **Grep tool** (`output_mode: count`, pattern `^### Session`) on `docs/session-history.md` — not a full read. Use the Grep tool (not shell `grep`) for the two counts so no extra Bash permission is needed; `wc`/`awk`/`sort` are declared in `allowed-tools`. These drive the drift warnings and the `--full` rollup gates.

## Step 0.1: Path Routing

After Step 0:

- **Default (no path flag), or `--fast`** → run the **Save Path** below. (`--fast` is a no-op alias kept for muscle memory; it now matches the default.)
- **`--full`** → run the **Full Path**: the Save Path first, then the heavy sweep (README + `docs/*.md` sync + rollups), all described after the Save Path.

The old behavior (full sweep by default) is inverted: the daily save is fast; the heavy sweep is opt-in. Drift warnings (emitted at the end of the Save Path) tell the user when a `--full` is due.

**`--silent` (combinable with any path):** zero user prompts for the entire run. Part 8 auto-commits with the suggested message instead of asking; every consent prompt in Parts 5/6/7 resolves to its safe default — first-run rollup consent (5.2, 6.2) is treated as *declined* (the Part is skipped and no sentinel note is written, so the next interactive run asks as usual), and the Part 7.4 consent gate is treated as *skip-all*. `--silent` never answers "yes" on the user's behalf to anything except the commit, which is the one prompt the flag exists to bypass.

## Prose Caps (apply when composing any new entry)

New entries are capped — this keeps writing fast and keeps `/bx:resume` lean. Existing entries are never rewritten to fit.

- **Session-history entry:** ≤5 "What happened" bullets. Detail that doesn't fit becomes a commit-hash reference (`see commit abc1234`), not prose.
- **docs/STATUS.md last-session block:** ≤5 bullets, the most architecturally significant.
- **Key Decision rationale:** ≤2–3 sentences. Longer context goes only into `docs/key-decisions.md`, referenced by commit hash.
- **In Progress / Next Steps items:** one line each + file paths; no multi-paragraph narration.

## Save Path (default)

The orchestrator owns everything that needs conversation context or user input; the `save-writer` subagent owns the file reads/writes. The orchestrator does NOT edit `CLAUDE.md`, `docs/STATUS.md`, `session-history.md`, `completed-work.md`, or `key-decisions.md` itself — it composes the packet and dispatches.

**Sequence:**

1. **Drain the task list (Part 0 logic).** Run the Part 0 / Drain Validation rules below to reconcile `TaskList` against docs/STATUS.md (CLAUDE.md's state sections on a v1 repo). Respect `--skip-tasks`. The result (completed → completed-work items; in-progress → In Progress; new pending → Next Steps) becomes part of the packet, NOT inline edits.
2. **Compose the update packet** (see "Update Packet" below) from: the conversation (what happened this session — only the orchestrator knows this), the filtered commit list, the diff file list, and the drained task state. Apply the Prose Caps.
3. **Dispatch the `save-writer` subagent** (see "Dispatch" below) and await its change report.
4. **Drift probes** (cheap, on already-gathered data — no new reads): emit the drift warning block if anything fired. Do NOT enforce.
5. **Commit checkpoint (Part 8).** Run Part 8 as written; respects `--skip-commit` and `--silent` (auto-commit, no prompt). The git diff is the user's review surface.
6. **Report** using the Change Report format from `verification-checklists.md` — assembled from the subagent's report + drift warnings. Never echo file contents.

**Skipped on the Save Path** (these are `--full` only): Part 0.5 (legacy-layout archive split), Part 2 (README), Part 3 (`docs/*.md`), Part 4 (auto-memory), Parts 5/6/7 (rollups), Part 1.10 cap enforcement (replaced by drift warnings).

### Update Packet

Compose this structure and pass it to `save-writer` as the task prompt (fill every field; use the section references in Part 1 to decide *what* each field contains):

- `project_root` — absolute repo path.
- `today` — current date (e.g. `2026-05-29`). Resolve it from the session's current date supplied by the environment; if that's unavailable, fall back to the most recent commit date from the Step 0.1 `git log` (`git log -1 --date=short`). Do not invoke a bare `date` command — it isn't in `allowed-tools`.
- `claude_md_deltas` — exact `old → new` string pairs (or "replace block under `## Section` with: …") for CLAUDE.md sections the session changed: the `Last Updated:` line, `## Key Decisions` (Part 1.6) and `## Known Issues / Blockers` (Part 1.7 — a blocker resolved or added this session). **Instructions only** — no state sections. Source the *old* strings verbatim from the CLAUDE.md you read in Step 0.
- `status_md_deltas` — the same, for `docs/STATUS.md`: its `Last Updated:` line, Current Status rows (Part 1.2), the `## Completed` summary line if the drain changed the completed count (Part 0 / Part 1.3), In Progress (Part 1.4) and Next Steps (Part 1.5). Source the *old* strings verbatim from the docs/STATUS.md you read in Step 0 (or, on a v1 repo where STATUS.md is absent, from CLAUDE.md's state sections, per Step 0.1).
- `status_md_session_block` — the full replacement text for STATUS.md's `## Session History` last-session block (Part 1.8 format, ≤5 bullets). New field name under schema v2 — the block lives in STATUS.md now, not CLAUDE.md.
- `session_history_entry` — the detailed entry for `docs/session-history.md` (Part 1.8 format, capped).
- `completed_items` — `- [x] …` lines from the task drain (may be empty).
- `decision_rows` — a list of `| decision | rationale |` rows, **one per** genuinely architectural decision made this session (Part 1.6 criteria); empty list if none. Most sessions have 0–1, but a session that locks in several architectural decisions lists each as its own row (don't drop the extras).

### Dispatch

Dispatch one `save-writer` subagent via the Agent tool with `subagent_type: "bx:save-writer"`, passing the packet as the prompt (serialize as labeled sections). Await its change report.

`save-writer` reports on two channels, matching `doc-migrator.md`'s convention: `notes:` is advisory, `warnings:` is the channel that compels action. `warnings:` itself carries two distinct sub-cases (see `save-writer.md`'s Output section) that call for different responses — do not treat every non-`none` `warnings:` as a re-dispatch trigger. Handle each:
- **`notes:` non-`none`** (a density-cap: a field exceeded the prose caps) → tighten the offending field, note it in your report, do NOT re-dispatch.
- **`warnings:` non-`none`, unmatched delta** (an `old_string` didn't match, so that CLAUDE.md or docs/STATUS.md section was left un-updated) → re-source the exact current string from the CLAUDE.md / docs/STATUS.md you read in Step 0 (or re-read the affected lines) and re-dispatch **only** those deltas. This is the one case where re-dispatch IS warranted — silently leaving a section stale is the failure mode this guards against.
- **`warnings:` non-`none`, schema-v1 `docs/STATUS.md`-absent fallback** (save-writer routed `status_md_deltas` and `status_md_session_block` to CLAUDE.md because `docs/STATUS.md` doesn't exist yet) → confirm the v1 routing was expected (migration hasn't run on this repo), log it in your report, do NOT re-dispatch.
- Both `notes:` and `warnings:` read `none` → done, no re-dispatch.

### Drift warning format (show only lines whose probe fires)

> "Drift detected — run `/bx:save --full` when convenient:
>  - [N] sessions in `docs/session-history.md` ready for rollup (count > 5)
>  - Key Decisions table in CLAUDE.md at [M] rows (cap 20)
>  - README.md or `docs/*.md` touched in [K] commits since last full sweep
>  - CLAUDE.md at [X]k chars (target ~7k, soft cap 12k) — Part 7 size-pressure rollup will fire on `--full`
>  - docs/STATUS.md at [Y]k chars (target ~10k, soft cap 20k) — Part 7 size-pressure rollup will fire on `--full`"

If no probe fires, omit the warning entirely.

## Full Path (`--full`)

Runs the **Save Path** above first (so the fast result is identical), then the heavy sweep below. Because the Save Path deferred the archive reads, do them now:

### Step 0.3 Full-sweep reads (parallel)

Read `README.md` and all `docs/*.md` (`Glob docs/**/*.md`, then one Read per file in the same turn). These feed Parts 2, 3, 5, 6, 7.

The remaining Parts (0.5, 2, 3, 4, 5, 6, 7) run on the **orchestrator**, not the subagent, because Parts 5/6/7 can require an `AskUserQuestion` consent prompt and a subagent cannot prompt the user. The commit checkpoint (Part 8) already ran as the final Save-Path step — on `--full`, defer the commit to after the rollups instead (so rollup changes land in the same commit), exactly as the current Part 8 note specifies.

## Step 1: Scan docs/ Folder

1. **List all .md files** in docs/
2. **Identify file purposes:**
   - PRD files (requirements, specifications)
   - Architecture docs
   - API documentation
   - Sample/example files
   - Other supporting docs
3. **Update relevant files** based on code changes

## Part 0: Drain Task List into docs/STATUS.md

Before updating documentation, **capture any task progress from the current session's live task tracker:**

1. **Run `TaskList`** to get all tasks and their statuses
2. **For each completed task:**
   - Add it to `docs/completed-work.md` as `- [x] [task subject] - [files modified]`
   - Update docs/STATUS.md's `## Completed` summary line (increment count)
   - Remove it from `## In Progress` or `## Next Steps` if it appears there
3. **For each in-progress task:**
   - Ensure it's listed in `## In Progress` with current state
4. **For pending tasks that were created during the session:**
   - Add them to `## Next Steps` in priority order
5. **Skip tasks that already exist in docs/STATUS.md** — don't duplicate

This ensures work tracked via TaskCreate/TaskUpdate during the session is persisted back to docs/STATUS.md for the next session's `/bx:resume`.

**If `--skip-tasks` is in `$ARGUMENTS`, skip this step entirely.**

### Drain Validation

After draining, verify completeness:

1. **Run `TaskList`** again to confirm all tasks have been processed
2. **Ad-hoc tasks** (tasks created during the session that don't map to existing docs/STATUS.md sections):
   - If completed → add to `docs/completed-work.md`
   - If pending/in-progress → add to `## Next Steps` in docs/STATUS.md
3. **Report drain summary** to the user:
   > "Task drain complete: [N] completed, [M] in-progress, [K] pending synced to docs."

## Part 0.5: Legacy-Layout Archive Split (v1 repos only)

**This is the maintenance path for a repo still on doc schema v1** — one whose migration to v2
was declined or skipped (`--skip-migrate`), so CLAUDE.md still carries the five state sections
itself. It never runs on a v2 repo: there the state lives in `docs/STATUS.md` and MIGRATE
(`mode-migrate.md`) has already done the split.

Its job is the older, coarser split: move the bulky archives (full checklists, full decision
tables, multiple session entries) out of the **un-split CLAUDE.md** and leave a summary + link
behind. Because the repo is on the legacy layout, every link written back into CLAUDE.md is
**repo-root-relative** (`docs/…`) — CLAUDE.md sits at the repo root, so a bare
`completed-work.md` there would resolve to a file that does not exist.

**Detection:** Run this split if ANY of these are true:
- `## Completed` section contains more than 2 `- [x]` checkbox lines
- `## Key Decisions` table has more than 25 rows
- `## Session History` contains more than 1 `### Session` entry
- The un-split CLAUDE.md is over 32k characters — the v1-layout equivalent of this file's
  per-file soft caps (CLAUDE.md 12k + `docs/STATUS.md` 20k), which a v1 CLAUDE.md carries
  together in one file

**Split steps:**

### Split the Completed Section
1. Extract all `- [x]` items from CLAUDE.md's `## Completed`
2. Create `docs/completed-work.md` (if it doesn't exist) with header:
   ```markdown
   # Completed Work

   > Full checklist of completed tasks. Referenced from [STATUS.md](STATUS.md).

   ---
   ```
3. Append all extracted items to `docs/completed-work.md`
4. Replace CLAUDE.md's `## Completed` content with:
   ```markdown
   [N] tasks completed across [areas]. See [docs/completed-work.md](docs/completed-work.md) for full checklist.
   ```

### Split the Key Decisions Table
1. Extract all rows from CLAUDE.md's `## Key Decisions` table
2. Create `docs/key-decisions.md` (if it doesn't exist) with header:
   ```markdown
   # Key Decisions

   > Full decision log. Referenced from [CLAUDE.md](../CLAUDE.md).

   | Decision | Rationale |
   |----------|-----------|
   ```
3. Append all rows to `docs/key-decisions.md`
4. Keep only the ~20 most important architectural decisions in CLAUDE.md (API gotchas, naming conventions, critical tech choices). Remove implementation details.
5. Add link: `> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)`

### Split the Session History
1. Extract all `### Session` entries from CLAUDE.md's `## Session History`
2. Create `docs/session-history.md` (if it doesn't exist) with header:
   ```markdown
   # Session History Archive

   > Auto-managed by `/bx:save`. Last session summary is in [STATUS.md](STATUS.md).

   ---
   ```
3. Append ALL session entries to `docs/session-history.md` (in chronological order, skip duplicates)
4. Replace CLAUDE.md's `## Session History` with only the last session as a 3-5 bullet summary:
   ```markdown
   > Full history: [docs/session-history.md](docs/session-history.md)

   ### Last Session (Session [N]) - [DATE]
   - [3-5 bullet points from the most recent session]
   ```

**After the split, continue with the normal update process below.**

---

## Part 1: Update CLAUDE.md and docs/STATUS.md

> **Plan-then-batch (applies to Full Path):** Walk through 1.0–1.10 (and Part 6 row removals, if Part 6 fires) and gather every change you intend to make from the evidence cached in Step 0. Then apply all changes to each file in a **single Write** of its full contents, or as non-overlapping parallel Edits in one turn — per the routing table below, some sub-sections target CLAUDE.md and some target docs/STATUS.md; batch each file's edits separately. Do NOT issue one Edit per sub-section — that's the dominant turn-count cost.

**Target file per sub-section (schema v2):**

| Sub-section | Target |
|---|---|
| 1.0 Last Updated | **both** CLAUDE.md and docs/STATUS.md |
| 1.1 Documentation Links | CLAUDE.md |
| 1.2 Current Status | docs/STATUS.md |
| 1.3 Completed | docs/STATUS.md (+ append to docs/completed-work.md) |
| 1.4 In Progress | docs/STATUS.md |
| 1.5 Next Steps | docs/STATUS.md |
| 1.6 Key Decisions | CLAUDE.md (+ append to docs/key-decisions.md) |
| 1.7 Known Issues / Blockers | CLAUDE.md |
| 1.8 Session History | docs/STATUS.md (+ append to docs/session-history.md) |

1.1 Documentation Links stays in CLAUDE.md and is unrelated to the `> Session state:` pointer
line: 1.1 maintains the **Key Documentation** list of PRD/spec/sample files inside CLAUDE.md's
Project Overview, which schema v2 still carries there; the pointer line only names
`docs/STATUS.md` itself. The two do not duplicate each other.

### 1.0 Update Timestamp
**Always update the "Last Updated" field at the top of BOTH files** — CLAUDE.md and docs/STATUS.md carry independent `Last Updated:` lines (doc-schema.md), and the staleness signal must follow the state:
```markdown
**Last Updated:** [CURRENT DATE AND TIME]
```

### 1.1 Documentation Links
Update the "Key Documentation" section with actual files:
```markdown
**Key Documentation:**
- [docs/PRD.md](docs/PRD.md) - Project requirements
- [docs/api-spec.md](docs/api-spec.md) - API documentation
- [docs/sample-emails.md](docs/sample-emails.md) - Example data
```

### 1.2 Current Status Table
Target: **docs/STATUS.md's `## Current Status` table.** Update phase/task statuses based on code changes:
- Change Not Started -> In Progress when work starts
- Change In Progress -> Complete when work completes
- Add new rows for new components

### 1.3 Completed Section
Target: **docs/STATUS.md's `## Completed` section**, plus the `docs/completed-work.md` archive. When items are completed:
1. **Append the detailed entry to `docs/completed-work.md`:**
   - If the file doesn't exist, create it with header:
     ```markdown
     # Completed Work

     > Full checklist of completed tasks. Referenced from [STATUS.md](STATUS.md).

     ---
     ```
   - Append: `- [x] [What was finished] - [files modified]`
2. **Keep docs/STATUS.md's `## Completed` section as a brief summary:**
   ```markdown
   ## Completed

   [N] tasks completed across [areas]. See [completed-work.md](completed-work.md) for full checklist.
   ```
   Update the count and areas description as needed. Do NOT maintain a full checkbox list in docs/STATUS.md.

### 1.4 In Progress Section
Target: **docs/STATUS.md's `## In Progress` section.** Update current work state:
```markdown
- [ ] [Current task] - [files being modified]
```

### 1.5 Next Steps Section
Target: **docs/STATUS.md's `## Next Steps` section.** Refresh prioritized task list:
- Remove completed items
- Add new tasks discovered
- Reorder by priority
- Include relevant file paths

### 1.6 Key Decisions Made
Target: **CLAUDE.md's `## Key Decisions` table** (unchanged from v1 — this stays in CLAUDE.md under schema v2), plus the `docs/key-decisions.md` archive. When adding new decisions:
1. **Always append to `docs/key-decisions.md`:**
   - If the file doesn't exist, create it with header:
     ```markdown
     # Key Decisions

     > Full decision log. Referenced from [CLAUDE.md](../CLAUDE.md).

     | Decision | Rationale |
     |----------|-----------|
     ```
   - Append: `| [New decision] | [Why we chose this] |`
2. **Only add to CLAUDE.md's condensed table if it's a truly important architectural decision** — API gotchas, naming conventions, critical tech choices, patterns that affect multiple files.
   - Do NOT add implementation details like "removed field X", "renamed method Y", or one-off fixes to CLAUDE.md.
   - Keep CLAUDE.md's Key Decisions table to ~20 rows max. If it grows beyond that, remove the least important entries (they're preserved in `docs/key-decisions.md`).
   - Include a link at the bottom: `> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)`

### 1.7 Known Issues / Blockers
Target: **CLAUDE.md's `## Known Issues / Blockers` section** (unchanged from v1). Update with any new issues found:
- Add new issues discovered
- Remove resolved issues
- Mark "None currently" if empty

### 1.8 Session History
Target: **docs/STATUS.md's `## Session History` section** (brief), plus the `docs/session-history.md` archive (detailed). Session history is split between docs/STATUS.md (brief) and docs/session-history.md (detailed).

**1. Write the DETAILED session log to `docs/session-history.md`:**
   - If the file doesn't exist, create it with this header:
     ```markdown
     # Session History Archive

     > Auto-managed by `/bx:save`. Last session summary is in [STATUS.md](STATUS.md).

     ---
     ```
   - Append the full detailed entry:
     ```markdown
     ### Session [N] - [DATE]
     **What happened:**
     - [Accomplishment 1]
     - [Accomplishment 2]
     - [Any issues encountered]

     **Files created/modified:**
     - `path/to/file.py` - [what changed]
     - `path/to/another.js` - [what changed]

     **Next session should:**
     - [Priority 1 for next time]
     - [Priority 2 for next time]
     ```

**2. Write only a brief summary to docs/STATUS.md's `## Session History`:**
   - Replace (not append) the previous last-session block with the new one:
     ```markdown
     ## Session History

     > Full history: [session-history.md](session-history.md)

     ### Last Session (Session [N]) - [DATE]
     - [3-5 bullet points summarizing key accomplishments and state]
     ```
   - docs/STATUS.md should only ever contain ONE session block (the most recent).
   - All previous sessions live exclusively in `docs/session-history.md`.

### 1.9 Size Check (early advisory)

Measure both files. CLAUDE.md target ~7k, soft cap 12k. docs/STATUS.md target ~10k, soft
cap 20k. Warn per file when over its soft cap and name which Part 7 shrinker will fire.

This is the early advisory only — active enforcement happens in **Part 7 (Size-Pressure Rollup)** after Parts 5/6 have had a chance to bring the files under threshold via count-based rollups. If 1.9 fires for a file, expect Part 7 to also fire for that file.

### 1.10 Cap Enforcement

Active per-section caps on docs/STATUS.md (Current Status, Next Steps, In Progress — 1.10.1-1.10.3 below) and CLAUDE.md (Key Decisions, handled separately by Part 6, not here). Part 1.9 warns; this step enforces. Runs every UPDATE.

The biggest source of bloat — CLAUDE.md's Key Decisions table — is handled by the rollup in Part 6 because it requires moving rows to a reference file with a first-run consent gate. Part 1.10 handles the smaller docs/STATUS.md sections only.

**If `--skip-caps` is in `$ARGUMENTS`, skip this step entirely.**

#### 1.10.1 Current Status Table
Target: ≤10 rows. If >10 rows AND ≥3 are `Complete`:
- Collapse runs of `Complete` rows into a single summary row in the same table:
  > `| [N] components complete | Complete | See docs/completed-work.md |`
- Keep all `In Progress` and `Not Started` rows verbatim.
- Do not collapse if it would lose information (e.g. each `Complete` row has a unique note worth preserving — in that case, move them individually to `docs/completed-work.md` with their notes).

#### 1.10.2 Next Steps
Target: ≤10 items. If over cap, warn only — do not move:
> "Next Steps has [N] items (target ≤10). Consider pruning low-priority ones or completing the top few."

Next Steps is short-lived by design — accretion is a signal that items aren't being completed or reprioritized, not a storage problem.

#### 1.10.3 In Progress
Target: ≤5 items. If over cap, warn only — do not move:
> "In Progress has [N] items (target ≤5). Fragmented work often means stalled tasks — consider consolidating before continuing."

#### 1.10.4 Pruning Is Preservation
When 1.10.1 collapses rows into a summary line, the collapsed rows must land in `docs/completed-work.md` (with any unique notes) before they leave docs/STATUS.md. This is the **pruning-as-preservation** rule: content moves, it does not disappear. See `doc-structure-rules.md` for the full statement.

## Part 2: Update README.md

### 2.1 Project Overview
- Update feature list
- Mark deprecated features

### 2.2 Quick Start / Setup
- Verify steps still work
- Update prerequisites

### 2.3 Project Structure
- Add new folders/files
- Remove deleted items

### 2.4 Tech Stack
- Update versions
- Add new technologies

### 2.5 Documentation Links
Update to reflect actual docs/ contents:
```markdown
## Documentation

- [CLAUDE.md](CLAUDE.md) - Development context
- [docs/PRD.md](docs/PRD.md) - Full specifications
- [docs/other-file.md](docs/other-file.md) - Description
```

## Part 3: Update docs/*.md Files

### 3.0 Batch Read All Doc Files in Parallel

Before iterating file-by-file, pre-load the whole `docs/` tree in one turn:

1. List docs with `Glob docs/**/*.md` **and** root-level docs with `Glob *.md` (single turn,
   two calls). Root docs other than README.md and CLAUDE.md — `workflow.md`, contributor
   guides — are otherwise maintained by nothing and drift silently.
2. Issue one `Read` tool call per file — **all in the same turn** — so they execute in parallel rather than sequentially
3. Analyze all files in a single pass and plan the Edits
4. Apply all Edits in batched parallel calls where the targets don't conflict

This replaces a sequential read-analyze-edit loop (N turns) with a single parallel gather + batched writes, which is the dominant runtime cost on projects with 5+ doc files.

### For Each PRD/Spec File:

#### 3.1 Architecture
- Update diagrams if structure changed
- Update component descriptions

#### 3.2 API/Interfaces
- Document new endpoints
- Update changed endpoints

#### 3.3 Data Models
- Add new models
- Update changed schemas

#### 3.4 Configuration
- Add new env vars
- Update config options

### Preserve Project-Specific Files
- Don't modify sample data files unless requested
- Don't rename existing files
- Keep project-specific naming conventions

## Part 4: Sync Auto-Memory

Claude Code maintains a persistent auto-memory directory (`~/.claude/projects/<project-path>/memory/`) that is automatically loaded into every conversation. It is **Claude's own corrections-and-learnings layer**, distinct from CLAUDE.md's instructions and docs/STATUS.md's evolving status. This Part prunes and budgets that layer; it never syncs facts derivable from the repo (see 4.3).

**If `--skip-memory` is in `$ARGUMENTS`, skip this step entirely.**

### 4.1 What auto-memory is for

Auto memory is written **by Claude**, from its own corrections and learnings, and is loaded
into every session (first 200 lines **or 25KB, whichever comes first**). CLAUDE.md is
written by you. Do not use `/bx:save` to author memory entries that Claude did not learn.

### 4.2 What this step actually does

Only two things:

1. **Prune contradictions.** If a memory file states something this session proved wrong,
   correct or delete that file. A stale memory is worse than a missing one.
2. **Check the index budget.** If `MEMORY.md` is near 200 lines or 25KB, move detail into
   topic files and keep one line per entry in the index. Over either limit, everything past
   it is silently dropped at next load.

### 4.3 What NOT to write

Do not sync tech stack, common commands, key paths, architecture patterns or env var names.
That content is derivable from the repo, duplicates CLAUDE.md and README, and is exactly
what `/doctor`'s trim check removes. Do not sync session state — that is STATUS.md's job.

## Part 5: Roll Up Old Sessions in session-history.md

Keep `docs/session-history.md` bounded by compressing sessions older than the 5 most recent into one-line summaries. The full prose still lives in git history at the linked commit hashes.

**If `--skip-rollup` is in `$ARGUMENTS`, skip this step entirely.**

### 5.1 Detect Compressible Sessions

1. Read `docs/session-history.md`
2. Grep for `^### Session` headers and count them
3. **If count ≤ 5, skip silently** — nothing to compress
4. The 5 highest-numbered sessions stay in full prose; everything older is a candidate for compression
5. Identify which older entries are still in multi-line "What happened / Files / Next session" format. Skip any already in one-line format (idempotent — running this part repeatedly is safe)

### 5.2 First-Run Confirmation (per-project)

The presence of the rollup-format note (see Step 5.4) acts as a "this project has consented to rollups before" sentinel. Use it to gate the first-run prompt:

1. **Check if the rollup note exists** in `session-history.md`'s header (search for the literal substring `Sessions older than the 5 most recent are compressed`)
2. **If the note IS present** → proceed silently to Step 5.3 (this project has been rolled up before)
3. **If the note is MISSING and there are entries to compress** → this is the first rollup pass on this project. **If `--silent` is in `$ARGUMENTS`, treat as declined without asking** (skip the rest of Part 5, do NOT add the rollup note — the next interactive run asks as usual). Otherwise ask the user:
   > "First-time rollup detected for this project: `docs/session-history.md` has [N] sessions in full-prose format, [M] of which are older than the 5 most recent and would be compressed to one-line summaries with commit hashes. Full prose stays preserved in git history. Compress now? (y/n)"
   - **If user declines** → skip the rest of Part 5 entirely. Do NOT add the rollup note (so the user is asked again next run).
   - **If user accepts** → proceed to Step 5.3.
4. **Use `AskUserQuestion` if available** for a cleaner y/n/skip-this-time prompt; fall back to a numbered chat question otherwise.

### 5.3 Compress Each Older Session

For each session needing compression:

1. **Extract a one-line summary** from the existing entry — pull the most architecturally significant 1-3 bullets from "What happened" and condense. Keep skill names, flag names, and concrete artifacts (file names, decision names) since those are what future-readers grep for. Drop process narration ("ran /bx:save", "committed and pushed", "user asked").
2. **Find associated commit hashes** using a single pre-fetched git log. Before the per-session compression loop, run ONCE:
   ```
   git log --since="<earliest-compressible-session-date>" --until="<latest-compressible-session-date +1d>" --pretty=format:'%h %ad %s' --date=short
   ```
   Then for each session being compressed, filter that pre-fetched output in memory by the session's date window. Do NOT run a separate `git log` per session — one command for the whole batch.
   - If the session entry already lists commit hashes (`(commits ...)`, `(commit ...)`), prefer those — they were chosen during the original session
   - Otherwise pick commits whose subjects clearly correspond to the session's work; cap at 4 hashes
   - If no commits exist in the date window (rare — pure docs session?), omit the parenthetical
3. **Replace the multi-line block** with a single line in this format:
   ```
   ### Session N - YYYY-MM-DD: [one-line summary] (commits: hash1, hash2)
   ```
   For a single commit, use `(commit: hash)`. For "bundled" cases where multiple sessions share a commit, write `(bundled in hash)`.
4. Preserve a single blank line between session entries.

### 5.4 Add Rollup Note (First Run Only)

If `session-history.md` does not already contain the rollup note (i.e., this is the first run and the user said yes in Step 5.2), insert it after the existing `> Auto-managed by /bx:save...` line:

```markdown
> **Note:** Sessions older than the 5 most recent are compressed to one-liners with commit hashes. Full prose for compressed sessions lives in git history (`git show <hash>`).
```

This note is the gating sentinel: its presence tells future runs that the user has already consented to rollups for this project, and Step 5.2 will skip the prompt next time.

### 5.5 Report

Tell the user:
> "Rolled up [N] older sessions. session-history.md: [old-size]k → [new-size]k chars."

If 0 sessions were compressed, skip the report.

## Part 6: Roll Up Old Key Decisions

Keep CLAUDE.md's `## Key Decisions` table bounded by moving older rows into `docs/key-decisions.md`. Mirrors the session-history rollup in Part 5: gated on a first-run sentinel, silent on subsequent runs.

**If `--skip-decisions-rollup` is in `$ARGUMENTS`, skip this step entirely.**

### 6.1 Detect Overflow

1. Read CLAUDE.md's `## Key Decisions` table; count data rows (exclude the header and separator).
2. **If count ≤ 20, skip silently** — nothing to roll up.
3. Rows to move: the oldest `(count - 20)` rows.
   - **Oldest = topmost in the table.** By convention, new decisions are appended at the bottom, so FIFO from the top is the mechanical rule. Using "least important" instead invites the same judgment-avoidance that caused the bloat — stick to FIFO unless the user overrides per-session.

### 6.2 First-Run Confirmation (per-project)

The presence of the rollup-format note in `docs/key-decisions.md` (see Step 6.4) acts as the "this project has consented to decision rollups before" sentinel:

1. **Check if the rollup note exists** in `docs/key-decisions.md`'s header (search for the literal substring `Entries older than the 20 most recent in CLAUDE.md are rolled up`)
2. **If the note IS present** → proceed silently to Step 6.3
3. **If the note is MISSING and there are rows to roll up** → this is the first decisions rollup pass on this project. **If `--silent` is in `$ARGUMENTS`, treat as declined without asking** (skip the rest of Part 6, do NOT add the rollup note — the next interactive run asks as usual). Otherwise ask the user via `AskUserQuestion` (or numbered Q&A fallback):
   > "First-time Key Decisions rollup: CLAUDE.md has [N] rows (target ≤20). The oldest [M] rows would move to `docs/key-decisions.md`. Full content is preserved — just relocated. Proceed? (y/n)"
   - **If user declines** → skip the rest of Part 6 entirely. Do NOT add the rollup note (re-asks next run).
   - **If user accepts** → proceed to Step 6.3.

### 6.3 Move Rows

For each row to roll up:

1. **Append to `docs/key-decisions.md`** preserving the existing row order (topmost row of the CLAUDE.md table becomes next row in the reference file).
   - If the file doesn't exist, create it first with the header block from `mode-update.md` Part 1.6 (`# Key Decisions` → `> Full decision log. Referenced from [CLAUDE.md](../CLAUDE.md).` → table header).
   - **Anchor at the end of the table block, NOT at end-of-file.** Before appending, scan `docs/key-decisions.md` and find the last consecutive `|`-row in the main table. Insert the new row(s) immediately after that line. If the file has non-table content after the table (e.g., a bulleted "Also noted during verification" section, a footer, or any other prose), the new rows MUST land BEFORE that content — appending at literal end-of-file would create an orphan table fragment (a `|`-row with no header context). Implementation: Edit using `(last existing table row)\n\n(first line of trailing non-table content)` as `old_string`, splice the new rows in between. If the table is the only content in the file, end-of-file is the correct anchor.
2. **Remove the row from CLAUDE.md's `## Key Decisions` table.**
3. **Do NOT deduplicate.** If the same row already exists in `docs/key-decisions.md` (because an earlier session mirrored it there), leave both — dedup requires judgment. The cost is a duplicate line in the reference file, which is harmless.
4. Preserve the trailing `> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)` link in CLAUDE.md; that link is the whole point of keeping the section lean.
5. **If an orphan table row is detected at end-of-file** (a `|`-row sitting alone after non-table content, leftover from a prior buggy run before this anchor rule was added), move it into the table block during this run as a one-time repair. The repair and the new rollup land in the same commit.

### 6.4 Add Rollup Note (First Run Only)

If `docs/key-decisions.md` does not already contain the rollup note, insert it after the existing `> Full decision log...` header line:

```markdown
> **Note:** Entries older than the 20 most recent in CLAUDE.md are rolled up here. CLAUDE.md keeps the freshest 20 as a quick-reference for AI sessions; the complete decision history lives in this file.
```

This note is the gating sentinel: its presence tells future runs that the user has already consented to decision rollups for this project, and Step 6.2 will skip the prompt next time.

### 6.5 Report

> "Rolled up [M] Key Decisions from CLAUDE.md → docs/key-decisions.md. CLAUDE.md: [old-size]k → [new-size]k chars."

If 0 rows were moved, skip the report.

## Part 7: Size-Pressure Rollup

After the count-based rollups in Parts 5 and 6 finish, re-measure CLAUDE.md and docs/STATUS.md, independently. If either is still over its soft cap, this part is the active-enforcement counterpart to Part 1.9's advisory. Where Parts 5/6 trigger on **row count** (≥5 sessions, ≥20 decisions), Part 7 triggers on **char size per section** — closes the gap where each row or item is at-cap-by-count but massive-by-content.

**If `--skip-size-pressure` is in `$ARGUMENTS`, skip this step entirely.**

### 7.1 Re-measure after Parts 5/6

Compute `claude_md_size` = char count of CLAUDE.md, and `status_md_size` = char count of docs/STATUS.md, both as they stand post-rollups.

- If `claude_md_size <= 12000` **and** `status_md_size <= 20000` → skip the rest of Part 7 silently. The count-based rollups did the job.
- Otherwise proceed — but **per file, independently**: a file under its own soft cap is neither diagnosed nor shrunk in 7.2-7.3, even when the other file is over.

### 7.2 Section size diagnostic

For each file that is over its own soft cap, compute its per-section char counts (sections delimited by `^## ` headers):

```bash
awk 'BEGIN{section="HEADER"; size=0} /^## /{if(section)printf "%6d  %s\n", size, section; section=$0; size=0; next} {size+=length($0)+1} END{printf "%6d  %s\n", size, section}' CLAUDE.md | sort -rn
awk 'BEGIN{section="HEADER"; size=0} /^## /{if(section)printf "%6d  %s\n", size, section; section=$0; size=0; next} {size+=length($0)+1} END{printf "%6d  %s\n", size, section}' docs/STATUS.md | sort -rn
```

Run only the command for whichever file(s) are over cap. Display the top-5 sections per over-cap file to the user as a single table each:

> CLAUDE.md is [X]k chars after Parts 5/6 rollups (over the 12k soft cap). Top sections:
> 
> | Section | Chars | % | Over threshold? |
> |---|---|---|---|
> | Key Decisions | 9,750 | 65% | YES (8000) |
>
> docs/STATUS.md is [Y]k chars after Parts 5/6 rollups (over the 20k soft cap). Top sections:
>
> | Section | Chars | % | Over threshold? |
> |---|---|---|---|
> | In Progress | 6,439 | 27% | YES (3000) |
> | Next Steps | 5,206 | 22% | YES (3000) |
> | Session History | 3,896 | 16% | — |

### 7.3 Per-section thresholds + shrinkers

For each section over its threshold, propose a specific shrinker. The thresholds and actions:

| Section | Threshold | Shrinker action |
|---|---|---|
| CLAUDE.md `## Key Decisions` (any variant: `(condensed)` etc.) | 8000 chars | **Size-based rollup** — move oldest rows (FIFO from top, same anchor rule as Part 6.3) to `docs/key-decisions.md` until section is under 6000 chars. Runs even when row count is ≤20. Adds `Rolled up from CLAUDE.md → docs/key-decisions.md in S<N> by size pressure` suffix to each moved row's rationale. |
| docs/STATUS.md `## In Progress` | 3000 chars | **Per-item collapse** — for each bullet, trim prose to 2-3 sentences + commit hash refs / file paths preserved. Move completed sub-bullets (`✅`, "Done", "Shipped", strikethrough) to `docs/completed-work.md`. Do NOT delete items entirely — collapse text only. |
| docs/STATUS.md `## Next Steps` | 3000 chars | **Flatten + extract detail** — collapse sub-section headers (`### High Priority`, `### Queued`, `### Nice to Have`) into a flat top-10 priority-ordered list. For items with 3+ sentences of detail, move detail to `docs/next-steps-backlog.md` (create if missing); keep 1-sentence summary + `→ next-steps-backlog.md#<anchor>` link (STATUS.md-relative — it already sits in `docs/`). |
| docs/STATUS.md `## Session History` (last-session block) | 2000 chars | **Bullet trim** — if the last-session block has >5 bullets, trim to top 3 (most architecturally significant) + append `> Full session detail: session-history.md S<N>` reference. |
| docs/STATUS.md `## Completed` (foregrounded feature paragraph) | 1500 chars | **Paragraph trim** — replace foregrounded multi-sentence paragraph with a single bullet pointing at `completed-work.md`. Keep the count summary line. |

`## Architecture Summary` is not in this table: that section no longer exists in CLAUDE.md under schema v2 — it lives in `docs/architecture.md`, which Part 7 does not size-manage. Sections not in this table (project-specific like `## Quick Commands`, `## Don't Modify`, `## Environment Variables` in CLAUDE.md) are **tolerated as-is** — Part 7 only acts on known shrinkable sections. If a project-specific section is the dominant bloat source, Part 7 reports it but takes no action, deferring to user judgment.

### 7.4 Per-section consent gate

**If `--silent` is in `$ARGUMENTS`, treat as `skip-all` without asking** — exit Part 7 after the 7.2 diagnostic report; no shrinkers run.

For each over-threshold section, ask via `AskUserQuestion` (or numbered fallback):

> "Section `## [name]` in [file] is [N] chars (threshold [T]). Proposed shrinker: [one-line action description]. Apply? (yes / no / skip-all)"

- **yes** → execute the shrinker for this section
- **no** → leave this section alone this run (re-ask next run if still over)
- **skip-all** → exit Part 7 entirely; the rest of the run proceeds to Part 8 unchanged

`AskUserQuestion` cap is 4 questions per turn. If 5+ sections (across both files) are over threshold, batch as: first 4 in one turn, remainder in a second turn after the first batch's actions complete.

Default action is `no` if user dismisses without explicit choice (don't apply destructive trims without consent).

### 7.5 Execution invariants

When executing any shrinker:

1. **Move, never delete.** Every shrinker writes the trimmed content to a reference file before removing from its source file (CLAUDE.md or docs/STATUS.md, per 7.3). The `docs/architecture.md`, `docs/next-steps-backlog.md`, and `docs/completed-work.md` files are the destinations. If a destination doesn't exist, create it with a standard header.
2. **Preserve commit refs.** Specific commit hashes (`abc1234`, `commit X`), file paths, and links MUST survive into either the trimmed summary or the extracted detail file — these are search anchors users rely on.
3. **Surface the destination.** Every shrinker's output gains a `> Full [thing]: [path.md](path.md)` link (relative to the file the shrinker ran on) so future `/bx:resume` sessions can chase the detail.
4. **Don't compound losses.** If a section was already shrunk to a summary in a prior run (detectable by the `> Full [thing]:` link), Part 7 does NOT trim further. Re-prompt only fires when the user has manually re-grown the section.

### 7.6 Report

After all consented shrinkers complete, re-measure each file that was diagnosed:

> "CLAUDE.md: [old-size]k → [new-size]k chars. docs/STATUS.md: [old-size]k → [new-size]k chars. (Omit either line for a file that was never over its soft cap.) [N] sections shrunk: [list]. [M] sections still over threshold (skipped per user choice)."

If a file is still over its soft cap after all consents: log a final warning for that file, do not block the commit.

### 7.7 Idempotency

Part 7 is safe to re-run. The shrinkers detect already-shrunk state via the `> Full [thing]:` sentinel link and skip those sections. The only way a re-shrunk section grows again is user editing — which is fine, and Part 7 will catch it next run.

---

## Part 8: Commit Checkpoint

After all documentation updates **and rollups** are complete, remind the user to commit. This runs last so that Parts 5, 6, and 7 changes are included in the same commit as the session updates.

**If `--skip-commit` is in `$ARGUMENTS`, skip this step entirely.**

1. **Run `git status`** to show all uncommitted files (staged and unstaged)
2. **Plugin version bump (claude-config repo only — skip silently when `bx/.claude-plugin/plugin.json` doesn't exist).** If any uncommitted file is under `bx/`, the commit MUST also bump `version` in `bx/.claude-plugin/plugin.json` and add a matching entry to the repo-root `CHANGELOG.md` (newest first). The version is the plugin's update cache key: a pushed commit that doesn't bump it is never offered to users — `/plugin update` reports "already at the latest version". Semver: PATCH for fixes and doc corrections, MINOR for a new skill/agent/flag, MAJOR for breaking renames or removed behavior. In `--silent` mode, default to PATCH and derive the CHANGELOG line from the suggested commit message.
3. **If there are uncommitted changes:**
   - Show the list of modified/untracked files
   - Suggest a conventional commit message based on what was done this session, e.g.:
     > Suggested commit: `docs: update session progress and documentation`
   - **If `--silent` is in `$ARGUMENTS`:** commit immediately with the suggested message — no prompt. This is the only path that commits without confirmation; the user opted in explicitly via the flag. Do NOT push.
   - **Otherwise, ask the user:** "Would you like to commit these changes?"
   - **Never auto-commit without `--silent`** — always wait for user confirmation
4. **If there are no uncommitted changes**, skip silently
