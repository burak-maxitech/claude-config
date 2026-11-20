# MODE: UPDATE — Full Sweep (`--full` only)

Loaded only when `/bx:save` runs with `--full`, after `mode-update.md`. The Save Path, Step 0, Part 0, Part 1.1–1.8 and Part 8 live in `mode-update.md`; Part numbers are shared across both files.

## Full Path (`--full`)

The Full Path is the Save Path with the heavy sweep spliced in **before the writer dispatch**, not after it. The order matters: the session entry and the STATUS.md last-session block are composed by the orchestrator and written once by `save-writer`, so a sweep that runs after the dispatch can never be recorded in the session that produced it (observed S61: the first real `--full` rolled up sessions and moved three issues, and the session entry had to be written by hand). Running the sweep first also means every `old` string in the packet is sourced from files the sweep has finished editing, so the writer's exact-string Edits match.

The sweep Parts (0.5, 2, 3, 4, 1.10, 5, 6, 7) run on the **orchestrator**, not the subagent, because Parts 5/6/7 can require an `AskUserQuestion` consent prompt and a subagent cannot prompt the user.

**Sequence:**

1. **Drain the task list** — Save Path step 1, unchanged.
2. **Step 0.3 full-sweep reads** (below).
3. **Fix the packet's content, not yet its text.** From the conversation, settle three lists: the decisions this session made (`decision_rows`), the issues it resolved (`known_issue_moves`), and the Known Issues entries it will add or reword. The sweep reads these (Part 6.1 counts the pending rows; Part 7.3 leaves packet-owned entries alone). Nothing else in the packet is needed yet.
4. **Run the sweep:** Part 0.5, Part 2, Part 3, Part 4, Part 1.10, then Parts 5, 6, 7 (7.7 included). Keep each Part's report line as it completes.
5. **Compose the update packet** — Save Path step 2, with two additions. (a) Source every `old` string in `claude_md_deltas` and `status_md_deltas` from the files **as the sweep left them**: when any of Parts 1.10, 6 or 7 wrote to CLAUDE.md or docs/STATUS.md, re-read that file first — the Step 0 copy is stale, and a stale `old` string costs a re-dispatch. (b) Fold the sweep's results into `session_history_entry` as one "What happened" bullet (it counts toward the ≤5 cap), e.g. `Full sweep: rolled up 6 sessions, moved 3 resolved issues to docs/known-issues.md, rotated docs/key-decisions.md → docs/archive/key-decisions-1.md`; when the sweep moved or rotated anything, mirror that bullet in `status_md_session_block`. A sweep that triggered nothing gets no bullet.
6. **Dispatch `save-writer`** — Save Path step 3, unchanged.
7. **Drift probes** — Save Path step 4, but re-measure first: one `wc -c` over the live files and archives, because the Step 0 figures predate the sweep and the write.
8. **Commit checkpoint (Part 8)** — once, here. The sweep's edits and the writer's edits land in one commit, as Part 8 specifies.
9. **Report** — Save Path step 6, plus the `[--full only]` lines of the Change Report.

**What the sweep cannot see.** This session's own additions — the session entry, decision rows, completed items, new Known Issues entries — reach the files only at step 6, after the sweep has measured them. Part 5's window, Part 6's count and 7.7's cut account for the pending entry as each Part notes; whatever remains is a one-session lag that the next `--full` closes. The alternative, sweeping after the write, loses the sweep's record every time.

### Step 0.3 Full-sweep reads (parallel)

Read `README.md` and all `docs/*.md` **except the auto-managed archives and everything under `docs/archive/`** (Part 3.0's exclusion list, which applies to this read too — rotated volumes are read by no automatic path, ever; via `Glob docs/**/*.md`, then one Read per file in the same turn). These feed Parts 2, 3, 5, 6, 7.

## Step 1: Scan docs/ Folder

1. **List all .md files** in docs/
2. **Identify file purposes:**
   - PRD files (requirements, specifications)
   - Architecture docs
   - API documentation
   - Sample/example files
   - Other supporting docs
3. **Update relevant files** based on code changes

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
- The un-split CLAUDE.md is over 27k characters — the v1-layout equivalent of the two
  size budgets (CLAUDE.md 12k + `docs/STATUS.md` 15k), which a v1 CLAUDE.md carries
  together in one file

**Split steps:**

### Split the Completed Section
1. Extract all `- [x]` items from CLAUDE.md's `## Completed`
2. Create `docs/completed-work.md` (if it doesn't exist) with header:
   ```markdown
   # Completed Work

   > Full checklist of completed tasks. Referenced from [CLAUDE.md](../CLAUDE.md).

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

   > Auto-managed by `/bx:save`. Last session summary is in [CLAUDE.md](../CLAUDE.md).

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

### 1.9 Size Check (early advisory)

Measure both files with `size-budget.sh` (Part 7 describes it). CLAUDE.md target ~7k,
advisory rung 10k, budget 12k. docs/STATUS.md target ~10k, budget 15k. Warn per file when it
is over its budget, and say that Part 7 will plan it.

**CLAUDE.md over 10k and at or under 12k — the advisory rung.** Nothing fires in this
band (it is Part 7's stop point), so say so instead of staying silent. Name the largest
section from the script's `section` records and take no action:

> "CLAUDE.md is [X]k chars — over the 10k advisory rung, under the 12k budget. Largest
>  section: `## [name]` ([N] chars). Nothing is shrunk below 12k."

The same script reports two things about CLAUDE.md's shape, both advisory and never a trigger: `lines` (Anthropic's own target is under 200 lines per CLAUDE.md) and `long_lines` (lines over 400 chars). A file can pass the line target and still be hard to follow: organized bullets are followed better than dense paragraphs, and a 600-char table row is a paragraph. Name the count and the longest line when `long_lines` is above 5.

If `## Project Overview` states derivable facts (`doc-structure-rules.md`, Pruning Is
Preservation), list them in the same advisory as trim candidates. Do not remove them here:
over budget, Part 7.3's Project Overview shrinker proposes the move, with consent.

Two optional checks the user can run themselves, named here so the advisory can point at
them: `/doctor`'s trim check (Claude Code 2.1.206+) proposes cuts of derivable content, and
`/doctor prompt-audit` (2.1.283+) reports stale or contradictory instructions across
CLAUDE.md, rules, skills and subagents. Both only propose; `/bx:save` runs neither.

This is the early advisory only — active enforcement happens in **Part 7 (Size Budget)** after Parts 5/6 have had a chance to bring the files under budget via count-based rollups. If the budget warning fires for a file, expect Part 7 to plan that file; the 10k advisory rung on its own means Part 7 will not.

### 1.10 Cap Enforcement

Active per-section caps on docs/STATUS.md (Current Status, Next Steps, In Progress — 1.10.1-1.10.3 below) and CLAUDE.md (Key Decisions, handled separately by Part 6, not here). Part 1.9 warns; this step enforces. Runs every UPDATE.

The biggest source of bloat — CLAUDE.md's Key Decisions table — is handled by the rollup in Part 6 because it requires moving rows to a reference file with a first-run consent gate. Part 1.10 handles the smaller docs/STATUS.md sections only.

**If `--skip-caps` is in `$ARGUMENTS`, skip this step entirely.**

#### 1.10.1 Current Status Table
Target: ≤10 rows. If >10 rows AND more than 3 are finished, run Part 7.3's **Current Status** shrinker on the finished rows beyond the newest 3 — the same definition of a finished row, the same archive step, the same single summary row. There is one collapse procedure, with two triggers: this row count, and Part 7's file budget.

- Every unfinished row stays verbatim.
- The rows are archived byte for byte before they leave, so a unique note on a row is never a reason to skip the collapse.
- **Under `--silent`, warn and move nothing:** "Current Status has [N] rows (target ≤10)."

#### 1.10.2 Next Steps
Target: ≤10 items. If over cap, warn only — do not move:
> "Next Steps has [N] items (target ≤10). Consider pruning low-priority ones or completing the top few."

Next Steps is short-lived by design — accretion is a signal that items aren't being completed or reprioritized, not a storage problem. The count alone moves nothing; when docs/STATUS.md is over its budget, Part 7.3 folds the items past the tenth.

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
2. **Exclude the auto-managed archives from the read set:** `docs/session-history.md`,
   `docs/key-decisions.md`, `docs/completed-work.md`, `docs/known-issues.md`,
   `docs/next-steps-backlog.md` — the
   canonical set is defined in `doc-schema.md`'s Archives section; this list follows it.
   They are this skill's own append-only outputs (save-writer and Parts 5-7 maintain them),
   never sync inputs, and Part 3 never edits them — but they grow with project age, so
   reading them costs tokens linear in project history for zero benefit. (At 57 sessions
   this repo's archives already total ~196k chars.)
   Also exclude **everything under `docs/archive/`** — rotated archive volumes (Part 7.7)
   are read by no automatic path, ever; reading them here would reintroduce the exact
   linear cost this exclusion exists to remove.
   Also exclude **dated planning records** — files whose names carry a date stamp
   (`YYYY-MM-DD-…`, e.g. anything under `docs/superpowers/`): they are immutable history of
   past plans and specs, they can outweigh the archives combined, and Part 3 never rewrites
   them as a matter of course. Opt one in explicitly only when this run's sweep must touch
   it.
3. Issue one `Read` tool call per remaining file — **all in the same turn** — so they execute in parallel rather than sequentially
4. Analyze all files in a single pass and plan the Edits
5. Apply all Edits in batched parallel calls where the targets don't conflict

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
2. **Check the index budget.** `MEMORY.md` loads into every session, so it counts toward
   the always-loaded total (`doc-schema.md`, Size budget). When `size-budget.sh` reports
   `memory … over` (more than 12k chars, half of Claude Code's 25KB load limit), or the file
   is near 200 lines, move detail into topic files and keep one line per entry in the index.
   Over 200 lines or 25KB, everything past the limit is silently dropped at next load.

### 4.3 What NOT to write

Do not sync tech stack, common commands, key paths, architecture patterns or env var names.
That content is derivable from the repo, duplicates CLAUDE.md and README, and is exactly
what `/doctor`'s trim check removes. Do not sync session state — that is STATUS.md's job.

## Part 5: Roll Up Old Sessions in session-history.md

Keep `docs/session-history.md` bounded by compressing sessions older than the 5 most recent into one-line summaries. The full prose still lives in git history at the linked commit hashes.

**If `--skip-rollup` is in `$ARGUMENTS`, skip this step entirely.**

### 5.1 Detect Compressible Sessions

1. Count `^### Session` headers with one Grep tool call (`output_mode: count`) on `docs/session-history.md` — do NOT read the file; 5.3 locates and reads only the compressible window
2. **If count ≤ 5, skip silently** — nothing to compress
3. The 5 highest-numbered sessions stay in full prose; everything older is a candidate for compression. This session's entry is not in the file yet — the writer appends it after Part 5 (Full Path step 6) — so count it as one of the 5: when it carries a new session number, the 4 highest-numbered sessions in the file stay; when it continues the newest session (`cont.`), the window is unchanged
4. Identify which older entries are still in multi-line "What happened / Files / Next session" format via 5.3's header Grep. Skip any already in one-line format (idempotent — running this part repeatedly is safe)

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

**Locate the compressible window without reading the whole archive.** One Grep tool call on
`docs/session-history.md` (pattern `^### Session`, `output_mode: content`, `-n: true`)
returns every session header with its line number. Already-compressed sessions are single
lines (header and summary are the same line); the compressible ones are the full-prose
entries older than the 5 most recent. Read only that line range (offset/limit) — the archive
grows with project age, and a full read makes every rollup pay for the whole history.

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

1. Read CLAUDE.md's `## Key Decisions` table; count data rows (exclude the header and separator), then add the rows the packet will append (`decision_rows`, settled at Full Path step 3) — the writer appends them after Part 6 has run.
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
   - **Anchor at the end of the table block, NOT at end-of-file.** Before appending, find the last consecutive `|`-row in the main table — without a full read: the same Grep (`^\|`, `-n`) + offset-Read technique as `save-writer.md`'s anchor rule. Insert the new row(s) immediately after that line. If the file has non-table content after the table (e.g., a bulleted "Also noted during verification" section, a footer, or any other prose), the new rows MUST land BEFORE that content — appending at literal end-of-file would create an orphan table fragment (a `|`-row with no header context). Implementation: Edit using `(last existing table row)\n\n(first line of trailing non-table content)` as `old_string`, splice the new rows in between. If the table is the only content in the file, end-of-file is the correct anchor.
2. **Remove the row from CLAUDE.md's `## Key Decisions` table.**
3. **Skip a row the archive already holds byte for byte.** `save-writer` mirrors every decision row into `docs/key-decisions.md` when it is created, so most rows are already there: check each with one whole-line fixed-string match (`bash -c 'grep -cxF -f <rows-file> docs/key-decisions.md'`, or one Grep per row) and append only the rows that are missing. Never match on anything looser than the whole line: a row that was reworded since is a different row and is appended. (Earlier versions appended unconditionally; the first real 2.18.0 run would have written 7 duplicates.)
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

## Part 7: Size Budget

Parts 5 and 6 trigger on **counts** (sessions, decision rows). Part 7 works from the **file total down**: a file over its budget is brought back under it by moving content out, largest section first, until the file fits. It replaced a table of per-section thresholds that could all be satisfied while the file stayed over its cap (a real project sat at 16.6k / 12k for 40 saves with every shrinker reporting nothing to do).

**If `--skip-size-pressure` is in `$ARGUMENTS`, skip this Part entirely** (7.7 included).

The numbers are owned by `doc-schema.md` (Size budget) and coded in `scripts/size-budget.sh`:

| File | Budget — act above this | Stop — shrink to this |
|---|---|---|
| CLAUDE.md | 12k | 10k |
| docs/STATUS.md | 15k | 13k |

The gap between the two is deliberate: a file that has just been shrunk does not trip the budget again on the next small edit.

Two scripts do the mechanical work. Both live in this skill's `scripts/` directory; resolve the path against **this skill's base directory**, not the repo.

- `bash <skill-dir>/scripts/size-budget.sh .` — measures both files, every section, both `Last Updated` lines, CLAUDE.md's line count and long lines, everything loaded at session start (`loaded` records and `loaded_total`), the auto-memory index, each path-scoped rules file, the five archives and the skip counter.
- `bash <skill-dir>/scripts/archive-lines.sh . <src> <dest> "<heading>" <line-ranges> [--prefix STR]` — copies source lines into an archive byte for byte and skips every line the archive already holds. It never edits the source.

### 7.1 Measure

Run `size-budget.sh` once, after Parts 5 and 6. Each `file` record ends in a state and a need:

- `ok` or `band` (at or under budget) → that file is left alone: not planned, not shrunk, not mentioned. `band` means over the stop point but under the budget, where nothing fires.
- `over` → plan that file in 7.2. `need` is the number of chars to remove to reach the stop point.

Each file is judged on its own. When neither is `over`, Part 7.2–7.6 print nothing and ask nothing: go directly to **7.7 (archive rotation)**, which runs regardless.

### 7.2 Plan the moves

Planning reads and measures; it changes nothing. For each `over` file, build a list of moves from the shrinkers in 7.3, in two passes:

1. **Tidy pass — every section, always.** Plan every *tidy* move the section offers. Tidy moves take out only what is finished, duplicated, or scaffolding an earlier trim left behind, so they are proposed whenever the file is over budget, whatever the need.
2. **Relocation pass — only if the tidy pass does not cover the need.** Walk the sections **largest first** (the `section` records are already in that order) and plan each section's *relocate* move down to its floor. Stop adding moves once the planned savings reach the need. Standing rules in `## Known Issues / Blockers` are planned **last**, after every other section in the file, whatever their size: they are the content CLAUDE.md exists to carry. Among them, path-scoped rules come before global ones. A move is planned whole (one group of rules, one run of rows), so the last move may overshoot the need; that is accepted.

**Optional moves.** Stripping the reasons from global standing rules is planned as an **optional** move: it is listed in the table, marked `optional`, with its saving, but it is not counted toward the need and **Apply all** does not run it. Anthropic's own trim guidance keeps "pitfalls, rationale, and conventions" and cuts what is derivable, and a rule without its reason is followed less reliably than one with it; so this move happens only when the user picks it under **Choose**. If the required moves do not reach the need, say how far the optional ones would take the file.

A move's **saving** is the size of the lines that leave minus the size of the lines that replace them, blank lines included, in the unit `size-budget.sh` reports (it counts what `awk` counts, which is bytes in some locales). Compose the replacement lines while planning, so the saving is measured and not guessed. Drop a relocate move that saves under 200 chars.

Every section of an `over` file ends the plan in exactly one of three states: it has at least one move; it has a relocate move that was not needed this run (say so in one line under the table); or it is listed as **unshrinkable by design** with its size and the reason from 7.3. No section is silently skipped. If the planned savings do not reach the need, say so now, with the projected size: the run still applies what it has.

Packet-owned content is planned around, never moved: a Known Issues entry this session resolved or will reword, and the decision rows the packet will append (all settled at Full Path step 3). The writer handles those after Part 7 has run.

### 7.3 Shrinkers

Every shrinker triggers on **what the section contains now**. None is switched off by a link or note an earlier run left behind: a section is re-examined on every run in which its file is over budget.

| Section | Tidy move | Relocate move | Floor — never goes below | Destination |
|---|---|---|---|---|
| HEADER (both files) | A `Last Updated:` line over 250 chars is cut to one session | — | title, intro notes, one `Last Updated:` line | `docs/completed-work.md` |
| CLAUDE.md `## Key Decisions` (any variant: `(condensed)` etc.) | — | Rows over 400 chars are shortened; then oldest rows leave, top first | newest 8 rows + the `> Full decision log:` link | `docs/key-decisions.md` |
| CLAUDE.md `## Known Issues / Blockers` — issues | Resolved entries leave entirely | Open entries become a one-line summary + link | every open issue keeps a trace | `docs/known-issues.md` |
| CLAUDE.md `## Known Issues / Blockers` — standing rules | — | Path-scoped rules move to a rules file; optionally, global rules keep their lead and lose their reason | every rule keeps its lead sentence or a trace line | `.claude/rules/<topic>.md`, `docs/known-issues.md` |
| CLAUDE.md `## Project Overview` | — | Derivable facts leave | name, description, Key Documentation links, every constraint | `docs/architecture.md` |
| CLAUDE.md `## Environment Variables` | — | Descriptions leave, names stay | every variable name | the project's env doc |
| docs/STATUS.md `## Current Status` | — | Oldest finished rows merge into one summary row | header rows, every unfinished row, newest 3 finished rows | `docs/completed-work.md` |
| docs/STATUS.md `## In Progress` | Finished items leave; scaffolding folds to one line | Items past the first 5 fold into a count line; long items are trimmed | first 5 items | `docs/completed-work.md`, `docs/next-steps-backlog.md` |
| docs/STATUS.md `## Next Steps` | Finished items leave; scaffolding folds to one line | Items past the first 10 fold into a count line; long items are trimmed | first 10 items | same |
| docs/STATUS.md `## Session History` | — | Bullets past the fifth leave | one block, 5 bullets, the `> Full history:` link | `docs/session-history.md` |
| docs/STATUS.md `## Completed` | — | Everything except the summary line leaves | the count summary line + link | `docs/completed-work.md` |
| Any other section | — | — | all of it | — |

A section in the last row is **unshrinkable by design**: it is project-authored (`## Quick Commands`, `## Working Principles`, `## Don't Modify`) and no archive is its designated home. So is a section already at its floor, HEADER included. Report each by name, with its size and its own reason (`project-authored`, or `at its floor:` plus what the floor holds). This clause covers project-specific sections only: every section `claude-md-sections.md` lists as required has its own row above.

The paragraphs below define each row. S`<N>` is this session's number throughout.

**HEADER — the `Last Updated:` line.** The line states one session: `Last Updated: <date> (Session <N>)`, optionally followed by ` — ` and one clause about that session, 250 chars at most in total. It names no earlier session; earlier sessions are in `docs/session-history.md`. When an existing line is over 250 chars: archive it with `archive-lines.sh . <file> docs/completed-work.md "" <line> --prefix '- [x] Last Updated line of <file> before the S<N> trim (verbatim): '` (`<file>` is `CLAUDE.md` or `docs/STATUS.md`), then replace it with `<label as it stood> <date> (Session <number>)`, keeping the date and the session number **the line already carried** and any bold markers around the label; the writer stamps this session's date and number later in the same save. The header is exempt from 7.5 rule 4: the line carries no link. Other header lines (the title, `>` notes, project-authored lines) are never moved; when the header is still over 400 chars afterwards, report it as project-authored preamble.

**Key Decisions.** Two steps, in this order. *Shorten:* a row over 400 chars carries its session's story, not just the decision. Oldest first, until the need is met: make sure the row is in `docs/key-decisions.md` byte for byte (Part 6.3's check; append it if it is missing), then rewrite it in CLAUDE.md as the decision cell unchanged plus a rationale of one or two sentences, 300 chars at most for the whole row, keeping the version tag and any commit hash. A row at or under 400 chars is never shortened, so a shortened row is not touched again. *Move:* if shortening does not cover the need, move the oldest rows (FIFO from the top, the Part 6.3 procedure and anchor rule) until the need is met or 8 rows remain; the rows the packet will append count toward the 8. Rows move byte for byte: nothing is appended to a moved row. This move uses Part 6.3's anchored append, not `archive-lines.sh`, because the rows must land inside the archive's table and not at the end of the file.

**Known Issues — entries, and which kind each is.** Entry boundaries are Part 1.7's; the `> Session state:` pointer line is not an entry. A bold-only line that sits above a run of bullet entries is a **group heading**: it is not an entry, and it travels with its group. A group ends at the next bold-only line or the end of the section; blank lines do not end it. A bullet whose link points into `.claude/rules/` is a **trace line** an earlier run wrote: it is not an entry, it is never stripped or moved, and it is not counted as a rule. Classify every entry as one of three kinds:

- **resolved** iff its lead carries a resolved **status form**: the whole word `RESOLVED` in capitals; or `is resolved`, `was resolved` or `now resolved` followed by the end of the lead, punctuation, `(`, `by` or `in`; or a checked `[x]` box. The bare word is not enough: `unresolved`, `not resolved`, `partially resolved`, and the technical sense (`paths are resolved against cwd`) do not count, and the word appearing later in the body does not count.
- **standing rule** when it tells the reader what to do or not do (`Never…`, `Always…`, `Run … before …`, `Only … may …`, `Keep …`) and reports no defect waiting for a fix. Nothing will ever resolve it. A section whose opening `>` note says `Standing rules` declares every entry a rule.
- **open** otherwise: a defect, limitation or blocker that a fix would close. When in doubt, the entry is open, never resolved: an open entry keeps a trace in CLAUDE.md, a wrongly resolved one leaves none. When the doubt is between open and standing rule, it is a standing rule: the lead then stays byte for byte.

Topmost = oldest, the same FIFO convention as Part 6.1. Entries the packet owns are candidates in neither phase: an entry this session resolved (a `known_issue_moves` item) or one a `claude_md_deltas` pair will reword. The writer moves the first and edits the second after this shrinker has run; moving them here would leave the packet's `entry` text and `old` strings with nothing to match.

Part 7 runs on the orchestrator, so the Known Issues moves edit the files directly: they build no packet and dispatch no `save-writer`. They borrow only the append procedure and header format of `save-writer.md` step 8a, with `<title>` being the entry's title as Part 1.7 defines it. Handle one entry or group completely — **archive first, remove second** — before starting the next. A verbatim archive body must not break the archive's own structure, which keys on `### `: write any body line that starts with `#` with a leading backslash (`\###`). That is the only change ever made to an archived body.

- *Resolved entries (tidy).* All of them move, topmost first, and leave nothing behind. A resolved entry takes the **last** session its lead names (`The S5 deadlock is resolved (S6)` → `S6`), or this session when it names none. A title that repeats the status word (`… is RESOLVED (S3) — Resolved S3`) is fine; do not reword it. An open-classified entry the orchestrator has evidence is fixed (this session's conversation, or a commit the entry names that `git log` shows) is offered in 7.4 under *looks resolved — confirm*: the status-form test is not overridden — the user is. On confirmation the entry goes into `known_issue_moves` as resolved with that commit, and the writer moves it; declined, it stays an open candidate.
- *Open entries (relocate).* Topmost first, until the need is met. An entry qualifies only when it is at least 500 chars longer than its replacement line; a shorter one would lose its detail to save almost nothing, so it stays. The replacement, in the entry's original position, is `**<lead>** <one sentence, 25 words at most, saying what is still broken> → [docs/known-issues.md](docs/known-issues.md)`. `**<lead>**` is the entry's opening bold phrase exactly as it stood, punctuation included; when the lead was not bold, bold it here. The sentence is written from the entry's own body and names the specific failure; a generic placeholder ("still broken, see archive") is not allowed. State only what the entry itself says: no inferred cause, consequence or fix status. The archive header is `Open, moved S<N>`. A line already in this replacement form is never moved or trimmed again.
- *Standing rules, path-scoped (relocate).* A rule is **path-scoped** when its own text, or its group heading, confines it to named directories, globs or file types, and following it matters only while reading or editing those files. A rule about deploys, billing, process or people is global whatever paths it mentions; when in doubt it is global. Path-scoped rules move, byte for byte, to `.claude/rules/<topic>.md`: an existing rules file whose `paths:` already cover them, otherwise a new file. Write the new file's top with the Write tool — `---`, `paths:`, one `  - "<glob>"` line per glob, `---`, a blank line, `# <Topic> rules` — then copy the rule lines with `archive-lines.sh . CLAUDE.md .claude/rules/<topic>.md "## Moved from CLAUDE.md in S<N>" <ranges>`. `<topic>` is the group heading in lower-case kebab form without any parenthetical (`Database migrations (…)` → `database-migrations`). The group heading line itself is not copied: the file's title names it, and it stays in CLAUDE.md above the trace line. Claude Code loads such a file only when a matching file is read, which is the whole saving. In CLAUDE.md the moved rules are replaced by **one trace line per rules file**: `- **<K> rules** load with matching files → [.claude/rules/<topic>.md](.claude/rules/<topic>.md)`, as the only bullet under the group heading. Keep each rules file under 8k chars (`size-budget.sh` reports them as `rules` records; Claude Code delivers only the start of one over 40,000): when an append would pass 8k, start a second file for the topic. Never move a rule into a rules file that has no `paths:`: such a file loads every session, so the move would lower the CLAUDE.md count and save nothing.
- *Standing rules, global (optional — see 7.2; never part of **Apply all**).* The rule stays in CLAUDE.md; only its reason leaves. A rule's **lead** is its opening bold phrase (its first sentence when nothing is bold). Work one group at a time, topmost first (a flat list with no group headings is one group titled `Standing rules`), and only on a group where stripping saves at least 500 chars. Archive the group first: one `docs/known-issues.md` entry headed `### <group heading> — Open, moved S<N> (<today>)` whose body is the heading line, a blank line, and every rule in the group, verbatim (step 8a's Edit append; diff the body against the source lines before removing anything). A group saves what its rule lines lose minus the suffix added to its heading. Then reduce each rule line to its lead alone (`- **<lead>**`, byte for byte) and append ` → [reasons](docs/known-issues.md)` to the group heading line. A rule that is already lead-only has nothing to strip.

For this section the 7.4 table lists the titles it will touch, under headings: *resolved — leaves CLAUDE.md entirely*, *open — replaced by a one-line summary*, *looks resolved — confirm*, *path-scoped rule — moves to a rules file, trace line stays*, *global rule — lead stays, reason moves*. The user is approving a classification, so they must see it.

7.5 rule 3 is met in this section by one link, never duplicated: `> Archived issues: [docs/known-issues.md](docs/known-issues.md)` as the last block of the section, with one blank line above it (and one blank line between it and the `> Session state:` pointer line, where that line follows this section). Add it before the first move, so that every measurement already counts it. A section whose opening note already links `docs/known-issues.md` needs no second link.

**Project Overview.** A line or table row is **derivable** when one command recovers everything it says: the stack from the manifest, the remote from `git remote -v`, the scripts from the package manager, the tree from `ls`. It is not derivable when it states a constraint, a reason, or a fact about something outside the repo (hosting, DNS, accounts), or when any part of it would be lost to that command. When in doubt the line stays. The project name, the one-line description and the Key Documentation list always stay. Archive derivable lines with `archive-lines.sh … docs/architecture.md "## Moved from CLAUDE.md Project Overview (S<N>)" <ranges>`, then remove them. If nothing in the section links `docs/architecture.md` yet, add one line after the table or list they left: `> Moved detail: [docs/architecture.md](docs/architecture.md)`; count it in the saving. The 7.4 table names each line with the command that recovers it.

**Environment Variables.** Only when the move saves at least 500 chars. Archive the section's variable lines (not its header, and not a `>` block such as the `> Session state:` pointer when that sits in this section) with `archive-lines.sh` into the project's environment doc — the one `## Project Overview` links, else `docs/environment-variables.md` — under `## Moved from CLAUDE.md (S<N>)`, then replace those variable lines with one line: every variable name in backticks, comma-separated, then `→ [<doc path>](<doc path>)`. Any `>` block stays where it was. Every name stays, so the section stays populated under `doc-schema.md`'s rule.

**Current Status.** A row is **finished** when its status cell (in a two-column table, the second cell) opens with `✅` or carries the whole word `Complete`, `Completed`, `Done`, `Shipped` or `LIVE`, and carries no `In progress`, `Partial`, `🔧` or `⏳` marker. A row an earlier collapse wrote (its first cell says `collapsed rows`) is finished whatever else it says. When in doubt the row is unfinished and stays. Take finished rows oldest first (topmost) until the need is met, never the newest 3. Archive them with `archive-lines.sh … docs/completed-work.md "### Current Status rows collapsed from STATUS.md (S<N>)" <ranges>`, then replace them all with **one** summary row at the top of the table body, one cell per column: `| **<K> finished rows collapsed (S<N>)** | ✅ | [completed-work.md](completed-work.md) |`. `<K>` counts each moved row once, and an earlier collapse row as the number written directly before the words `collapsed rows` or `finished rows collapsed`. The rows land in the archive as bare table rows under that heading; that is intended. The summary row never lists what it collapsed: the names are in the archive, and listing them is how hand-collapsed rows grew back to 900 chars each.

**In Progress and Next Steps.** An **item** is a top-level bullet or numbered line with its continuation lines.

- *Finished items (tidy).* An item is finished when it is marked done as a whole — `✅`, `DONE`, `Done`, `Shipped`, a checked box, or struck through — and carries no qualifier after the mark (`except`, `left`, `owed`, `remaining`, `still`). `DONE S318 except the label wording` is open. Archive with `archive-lines.sh … docs/completed-work.md "" <ranges> --prefix '- [x] '`, then remove.
- *Scaffolding (tidy).* Lines an earlier trim wrote and that carry no work of their own: `> Full …:` link lines, `> Items #… moved …` notes, a line made only of links into the archives. Archive every such line with `archive-lines.sh … docs/next-steps-backlog.md "## Rolled off STATUS.md (S<N> --full)" <ranges>` (the notes map old item numbers to archive anchors, so they are kept, just not loaded), then replace them all with one line directly after the section's last item: `> Earlier items and full detail: [next-steps-backlog.md](next-steps-backlog.md) · finished: [completed-work.md](completed-work.md)`. A section that already has exactly that line and no other scaffolding has nothing to fold. Both sections archive under the same `## Rolled off…` heading; the script writes it once. When a removed line had a blank line after it, remove that blank line too.
- *Items past the cap (relocate).* The first 10 items of Next Steps and the first 5 of In Progress stay, in their listed order: the list is priority-ordered, so the first items are the live ones. Archive the rest with `archive-lines.sh … docs/next-steps-backlog.md "## Rolled off STATUS.md (S<N> --full)" <ranges>`, then replace them with one count line after the last kept item: `- **<M> more items** → [next-steps-backlog.md](next-steps-backlog.md)`. An existing count line is not an item; fold its number into the new one.
- *Long items (relocate).* A kept item over 400 chars that does not already end in a `→ [...](...)` link: archive it the same way, then trim it to two sentences at most, keeping every commit hash and file path, and end it with `→ [detail](next-steps-backlog.md)`. An item that already ends in such a link is a summary and is never trimmed again.

A project-authored paragraph inside either section that is not an item (a watermark note, an intro sentence) is never moved; when it is over 400 chars, report it by its first words as unshrinkable.

**Session History.** When the last-session block has more than 5 bullets, archive bullets 6 onward with `archive-lines.sh … docs/session-history.md "" <ranges>` (the full entry is normally there already, so most lines report `have`) and remove them.

**Completed.** Archive every line except the count summary line with `archive-lines.sh … docs/completed-work.md "" <ranges>` and remove them.

### 7.4 One consent for the whole run

**If `--silent` is in `$ARGUMENTS`, treat as `skip` without asking**: nothing moves, the plan still prints, the skip counter is left alone, and the run continues to 7.7.

When the plan has no moves, there is nothing to ask: print the 7.6 report (the unshrinkable sections, if a file is still over) and continue to 7.7.

Otherwise print the plan as **one table covering both files**, then ask once:

> | # | File | Section | Move | Leaves the always-loaded tier? | Saves |
> |---|---|---|---|---|---|
> | 1 | CLAUDE.md | HEADER | `Last Updated` line cut to S321 | old line → completed-work.md | 630 |
> | 2 | CLAUDE.md | Key Decisions | 6 oldest rows → key-decisions.md | yes, link stays | 1,610 |
> | 3 | docs/STATUS.md | Next Steps | 2 finished items → completed-work.md; 5 scaffolding lines folded | n/a (read on demand) | 1,480 |
>
> CLAUDE.md 16.4k → about 9.8k (budget 12k). docs/STATUS.md 20.3k → about 12.8k (budget 15k).
> Unshrinkable by design: `## Working Principles` (916 chars, project-authored).

Known Issues rows are followed by the titles per class (7.3). Then one `AskUserQuestion` (numbered fallback), whose text repeats the two projected sizes and the number of moves, because the dialog may be all the user sees:

- **Apply all** → execute every planned move that is not marked `optional`.
- **Choose** → ask which moves to apply, optional ones included: `AskUserQuestion` with `multiSelect`, the moves as options, 4 options per question and 4 questions per turn; with more than 16 moves, ask in chat for the row numbers instead. Execute the chosen ones.
- **Skip** → apply nothing this run.

A dismissed prompt is **Skip**: no move runs without consent. This one prompt replaces the per-section questions of earlier versions; 7.7 keeps its own first-rotation consent, which is asked once per archive, ever.

**Skips are counted.** After **Skip** or a dismissal, write the counter line `<!-- bx-size-skips=<n> -->` directly under docs/STATUS.md's `Last Updated:` line, `<n>` being the old value plus one (`size-budget.sh` reports the old value as `skips`). After **Apply all**, or **Choose** with at least one move, delete that line if there is one. From the third consecutive skip on, the prompt opens with `Skipped <n> runs in a row.`, the 7.6 report leads the Change Report instead of sitting among the rollups, and `size-budget.sh --line` says so on every later save and resume.

### 7.5 Execution invariants

1. **Move, never delete — archive first, remove second.** Every move writes the content to its destination before it leaves the source, and one move finishes before the next starts. Line moves go through `archive-lines.sh`, which copies by line number: do not retype moved text into an archive. Two destinations keep their own anchored procedures instead, because their entries have structure the script does not know: `docs/key-decisions.md` (Part 6.3) and `docs/known-issues.md` (`save-writer.md` step 8a). In the commands above, `…` stands for the repo and source arguments (`. docs/STATUS.md`, `. CLAUDE.md`). The script skips blank lines, reuses a heading it already wrote, and creates a missing destination with a standard header.
2. **Never archive twice.** `archive-lines.sh` skips a line the archive already holds, so a trim adds only what is new. Do not work around a `have` result: the earlier copy is the archive copy. Archiving a whole section again on every trim is what grew one project's backlog to 441k.
3. **Preserve commit refs.** Commit hashes, file paths and links survive in either the line that stays or the line that was archived.
4. **Surface the destination.** Whatever leaves a section leaves a link to where it went: the replacement line's own link, or one `> Full …:` line per section. One link per destination, never a stack of them.
5. **A summary is trimmed once.** A line that is already a summary with a link (an open-issue replacement line, a trimmed item, a count line, a collapse row, a lead-only rule) is never shortened again. This protects the line, not its section: everything else in the section is examined on every run.
6. **A rule or an open blocker never leaves the always-loaded tier without a trace** — its lead, or a one-line trace with a link, stays in CLAUDE.md.

### 7.6 Report

Run `size-budget.sh` again and report each file that was planned:

> "CLAUDE.md: 16.4k → 9.9k (budget 12k). docs/STATUS.md: 20.3k → 12.6k (budget 15k). 11 moves applied: [list]. Archived [N] lines, skipped [M] already archived." (`[N]` and `[M]` are the `archive-lines.sh` totals.)

When a file is still over its budget, follow that line (or replace it, when no move was applied) with what is left, largest first, each with its reason, instead of a generic warning:

> "CLAUDE.md is 13.2k, 1.2k over budget. What remains is unshrinkable by design: `## Known Issues / Blockers` 4.1k (24 standing rules, leads only); `## Project Overview` 2.7k (Key Documentation links); `## Working Principles` 0.9k (project-authored). Moving more is a decision about the project, not a rollup."

Moves the user declined, and optional moves nobody picked, are listed with their savings. Never block the commit.

**The always-loaded total.** Close the report with what Claude Code loads before the first prompt, from the script's `loaded` records, whenever `loaded_total` is `over` (more than 25k chars) or `memory` is `over`:

> "Loaded at session start: 36.6k chars (CLAUDE.md 16.5k, MEMORY.md 17.4k, SessionStart hook 2.6k) against a 25k guide. Largest: MEMORY.md, which is Claude's own file — Part 4.2 moves detail into topic files."

Part 7 shrinks only CLAUDE.md and docs/STATUS.md. The total is a report, not a trigger: its other parts have their own owners (Part 4.2 for `MEMORY.md`, the hook's own 3,000-char cap, the user for an unscoped rules file). An unscoped rules file is named here every time, because it loads exactly like CLAUDE.md while escaping its budget.

### 7.7 Archive rotation

The five archives grow forever by design — `docs/session-history.md` (one line per
rolled-up session plus 5 full entries), `docs/key-decisions.md` (one row per decision),
`docs/completed-work.md` (several lines per session), `docs/known-issues.md` (one `### `
entry per issue that left CLAUDE.md), `docs/next-steps-backlog.md` (one `## ` block per
trim, plus whatever the project filed there by hand). No automatic path reads them in full
(Part 3.0 excludes them; save-writer appends via tail reads), so growth is disk-only — but
deliberate reads (deep resume, a human opening the file, a 2000-line Read page) get clumsy
past ~100k chars. Rotation moves the oldest entries, byte-verbatim, into numbered volumes
under `docs/archive/`. The backlog used to be exempt, on the theory that it shrinks when
items ship. It does not: nothing ever removes a block from it, and one project's reached
441k. It rotates like the others.

**If `--skip-rotation` is in `$ARGUMENTS`, skip this step entirely.** (Note `--skip-size-pressure`
skips all of Part 7, this step included; 7.1's early exit does NOT skip this step.)

Take the five archives' sizes from `size-budget.sh`'s `archive` records (7.1's run, or a
fresh one when Part 7 moved anything). For each file marked `rotate` (over **100k chars**),
independently:

1. **Consent (first rotation of each archive).** The sentinel is the rotation note in
   the live file's header region (the lines before the first entry) — search only that region for the literal substring `Entries are rotated to`. If
   present, proceed silently. If absent: **if `--silent` is in `$ARGUMENTS`, treat as
   declined without asking** (skip this file, write no sentinel — the next interactive
   `--full` run asks as usual). Otherwise ask via `AskUserQuestion` (numbered fallback):

   > "`docs/<name>.md` is [N]k chars. Rotating moves its oldest entries, byte-for-byte,
   >  into `docs/archive/<name>-1.md` (a new `docs/archive/` directory), leaving the
   >  newest content where it is. Nothing is deleted or reworded, and volumes are read by
   >  nothing automatic — they are grep-on-demand history. Rotate now? (y/n)"

   Declined → skip this file, write no sentinel, re-offer next `--full` run.

   When more than one archive needs consent, batch the prompts into a single
   `AskUserQuestion` turn (4 questions per turn at most); rotation itself stays one file at a
   time — step 7 verifies each file before the next is touched.

2. **Ensure `docs/archive/` exists — implicitly.** The Write tool creates the directory
   when writing the volume file in step 5. Do NOT shell out to `mkdir`; it is not in this
   skill's `allowed-tools`.

3. **Volume number:** `Glob docs/archive/<name>-*.md`; K = highest existing number + 1, or
   1 if none. **Filenames only — never read a volume's contents.**

4. **Choose the cut.** The oldest entries move from the top of the file's entry region
   (all five archives order oldest-first), cutting only at whole-entry
   boundaries — a `### Session` header line, a complete `|` table row, a whole checklist
   line, a `### ` entry header (known-issues), a `## ` block header (next-steps-backlog) —
   until the live file would be at or under
   **50k chars** — the minimum number of
   whole entries needed to reach that target (half the threshold, so rotation
   does not re-fire every run). The protected tail never moves: the 5 most recent sessions
   (session-history, matching Part 5's window, pending entry included), the newest 20 rows
   (key-decisions, matching Part 6's target), whatever the 50k target leaves at the bottom
   (completed-work — this session's items are appended by the writer after rotation, so no
   cut can reach them), and in
   known-issues every entry from the first **live** `Open`-tagged header onward — the cut
   never extends past the first live `Open` entry, even when that leaves the live file over
   50k, because CLAUDE.md links to it and a volume is read by nothing. An `Open` entry is
   live while a line in CLAUDE.md's `## Known Issues / Blockers` still starts with its title
   (one Grep per `Open` header, on CLAUDE.md only). Once the issue is fixed and its summary
   line has left CLAUDE.md, the entry is no longer live and rotates like a resolved one; its
   header is never rewritten, because archives are append-only. When a live `Open` entry
   makes 50k unreachable, move every entry before it. If the first entry is a live `Open`
   one, nothing moves: report that and take no action. In next-steps-backlog the
   protected tail starts at the first `## ` block a link in docs/STATUS.md still lands in,
   and always includes the block this run appended. Find the live anchors with one Grep on
   docs/STATUS.md (pattern `next-steps-backlog\.md#[A-Za-z0-9_-]+`, `-o`), then locate each
   in the backlog with one Grep for `id="<anchor>"` or `{#<anchor>}`; an anchor with no such
   line is matched against the `## ` headers that contain its last hyphen-separated word
   (`…-s277` → headers containing `S277`). An anchor found nowhere is a dead link: name it
   in the report and ignore it for the cut. Links inside the backlog itself protect
   nothing. Never compress,
   reword, or reorder anything — Part 5 owns compression and has already run. Locate the
   boundaries by line number with Grep (`-n`); call **H** the last line of the live file's
   header region and **L** the last line of the final entry being moved.

5. **Write the volume header** (Write tool — this also creates `docs/archive/`, per
   step 2) — omit the previous-volume line when K = 1; for key-decisions, repeat the
   `| Decision | Rationale |` and `|----------|-----------|` table-header lines at the end
   so the moved rows render standalone:

   ```markdown
   # <Title> — Archive Volume <K>

   > Rotated from [<name>.md](../<name>.md) by `/bx:save` on <date>.
   > Previous volume: [<name>-<K-1>.md](<name>-<K-1>.md)
   > Newer content: [<name>.md](../<name>.md)

   ---
   ```

   Then move the bytes with one `bash -c` call (a compound pipeline genuinely needs a
   shell; covered by the `Bash(bash:*)` grant), substituting H, L, and both paths as
   literals:

       bash -c 'sed -n "<H+1>,<L>p" <live> >> <volume> && { head -n <H> <live>; tail -n +<L+1> <live>; } > <live>.tmp && mv <live>.tmp <live>'

   This is byte-verbatim by construction — the shell re-partitions the same bytes. Never
   move the content through a Read→Write round trip: re-encoding drift is exactly what
   step 7's bound exists to catch, and shuttling ~50k chars through context is the
   expensive way to fail it.

6. **Write or update the live file's rotation note** (the consent sentinel), inserted
   after the file's existing header note(s) or updated in place to point at the newest
   volume:

   ```markdown
   > **Note:** Entries are rotated to [docs/archive/<name>-<K>.md](archive/<name>-<K>.md)
   > when this file exceeds 100k chars. Older volumes chain from there.
   ```

   The first line of this note is the consent sentinel step 1 greps for (`Entries are
   rotated to`) — never reword that phrase.

7. **Verify byte conservation before touching the next file.** With B = the live file's
   `wc -c` before rotation and A = live-file-after + volume-after: require
   **B ≤ A ≤ B + 600** (rotation only adds bytes — volume header ~250, sentinel ~160,
   key-decisions table-header repeat ~45, plus margin). A below B means content was lost;
   A above the ceiling means content was rewritten. On violation: report loudly, leave both
   files exactly as they stand for inspection, and do NOT rotate any further files this run.

8. **Report:** `"docs/<name>.md: rotated [N]k chars → docs/archive/<name>-<K>.md; live
   file now [M]k ([V] volumes total)."`

Volumes are permanent — there is no count cap. Rotated volumes cost nothing at runtime
(nothing automatic reads them), and deleting history to reclaim ~100KB would break the
schema's "nothing is deleted — content moves" promise. If a user wants to prune, the
escape hatch is manual: `git rm docs/archive/<name>-1.md` — the content still survives in
git history.

### 7.8 Idempotency

A second `--full` run straight after a first changes nothing. Which of two reasons applies depends on where the first run left the file:

- **A file at or under its budget is not planned at all** (7.1). When the first run brought both files under budget, Part 7 exits before 7.2.
- **Every shrinker is state-based and leaves a state it does not match.** After a run there are no finished items, no scaffolding beyond the one fold line, no items past the cap, no finished rows beyond the summary row and the newest 3, no rule with a reason left in a stripped group, no `Last Updated:` line over 250 chars, and `archive-lines.sh` re-archives nothing. So a file that is still over budget because what remains is unshrinkable plans zero moves, asks nothing, and prints the same remainder report.

No shrinker keys on a sentinel link. Earlier versions skipped any section that carried a `> Full …:` link, which froze a section the first time it was trimmed while it kept growing new pointer lines; 7.5 rule 5 now protects single summary lines only.

---

