# MODE: UPDATE (Refresh Existing Docs)

When documentation structure exists, update to reflect current state.

## Step 0: Scoped Context Gather

Gather only what the orchestrator needs to *route* and *compose the packet*. The big append-only archives (`docs/key-decisions.md`, `docs/completed-work.md`, `docs/session-history.md`, `docs/known-issues.md`) are NOT read here on the default (fast) path — the `save-writer` subagent reads `session-history.md` off the main thread, and the other two are append-only (the orchestrator never reads *from* them to write the packet). Reading all archives up front was the single biggest cost of the old flow (~60k tokens/run).

### 0.1 Single parallel turn — issue these together

**Reads (parallel):**
- `CLAUDE.md` — read in full.
- `docs/STATUS.md` — the session-state file (schema v2). On a v1 repo this does not exist;
  MIGRATE runs first, so by the time UPDATE executes the repo is always v2 unless migration
  was skipped or declined. Handle both: if STATUS.md is absent, target CLAUDE.md's state
  sections exactly as v1 did.
- Auto-memory `MEMORY.md` — usually already in conversation context; read explicitly only if absent.

**Bash (parallel):**
- `git log -20 --name-only --pretty=format:'@%h %ad %s' --date=short` — commits and the files each touched, in one call
- `git log -1 --format=%h -- docs/STATUS.md` — the **save anchor**: the last commit that wrote the state file (on a v1 repo where STATUS.md does not exist, use `-- CLAUDE.md`)
- `git status`

**Other:**
- `TaskList` — only if the task tools are present (`references/task-tools.md`); skip silently if not.

**Deferred to `--full` only:** `README.md`, `docs/*.md` archive reads. If routing lands on `--full`, read those at the top of the Full Path (Step 0.3, which applies Part 3.0's exclusions), not here.

### 0.2 Derive

From the gathered context:
- **Filtered commit list** — the `@` lines above the save anchor in the 20-commit log (the anchor itself and everything older belong to earlier saves). Feeds the session entry + drift probes. Filter by commit, never by the `Last Updated` date: a date cutoff re-counts the earlier saves' commits whenever a day has more than one save (S65 saved three times on 2026-10-26). If the anchor is not among the 20 commits, run one more `git log --name-only --pretty=format:'@%h %ad %s' --date=short <anchor>..HEAD`; if there is no anchor (the state file was never committed), take all 20.
- **Diff file list** — the file names under those commits, plus `git status`'s uncommitted files → tells you whether README/`docs/` changed (drift signal; drives the `--full` recommendation).
- **TaskList state** → drives the task drain (Part 0) and the In Progress / Next Steps deltas.
- **CLAUDE.md size + docs/STATUS.md size + Key Decisions row count + session count** — cheap: `wc -c CLAUDE.md docs/STATUS.md docs/session-history.md docs/key-decisions.md docs/completed-work.md docs/known-issues.md` for size (omit docs/STATUS.md — and any archive — from the command when the file does not exist); count the Key Decisions table rows with the **Grep tool** (`output_mode: count`, pattern `^\| `); and (for the drift probe only) count sessions with the **Grep tool** (`output_mode: count`, pattern `^### Session`) on `docs/session-history.md` — not a full read. Use the Grep tool (not shell `grep`) for the two counts so no extra Bash permission is needed; `wc`/`awk`/`sort` are declared in `allowed-tools`. These drive the drift warnings and the `--full` rollup gates. Also measure CLAUDE.md's per-section sizes with this `awk` command (Part 7.2's, minus the `sort`):

  ```bash
  awk 'BEGIN{section="HEADER"; size=0} /^## /{if(section)printf "%6d  %s\n", size, section; section=$0; size=0; next} {size+=length($0)+1} END{printf "%6d  %s\n", size, section}' CLAUDE.md
  ```

   the `## Known Issues / Blockers` figure and the largest section's name feed two drift lines below.

## Step 0.1: Path Routing

After Step 0:

- **Default (no path flag), or `--fast`** → run the **Save Path** below. (`--fast` is a no-op alias kept for muscle memory; it now matches the default.)
- **`--full`** → run the **Full Path**: the Save Path with the heavy sweep (README + `docs/*.md` sync + rollups) spliced in **before** the writer dispatch, so the session entry records it. **Read `references/mode-update-full.md` now** — it holds the Full Path sequence, Step 0.3, Part 0.5, Parts 1.9–1.10 and Parts 2–7. The default path never loads it.

The old behavior (full sweep by default) is inverted: the daily save is fast; the heavy sweep is opt-in. Drift warnings (emitted at the end of the Save Path) tell the user when a `--full` is due.

**`--silent` (combinable with any path):** zero user prompts for the entire run. **The binding rule: every consent prompt anywhere in this skill — present or future — resolves to its safe default (declined / skip) with no sentinel written, so the next interactive run asks as usual. The Part 8 commit is the sole exception:** it auto-commits with the suggested message, the one prompt the flag exists to bypass. Concretely today: first-run rollup consent (5.2, 6.2) → declined; the Part 7.4 consent gate → skip-all; the Part 7.7 per-file rotation consent → declined. A consent gate added to any Part later inherits this rule without needing its own clause.

## Prose Caps (apply when composing any new entry)

New entries are capped — this keeps writing fast and keeps `/bx:resume` lean. Existing entries are never rewritten to fit.

- **Session-history entry:** ≤5 "What happened" bullets. Detail that doesn't fit becomes a commit-hash reference (`see commit abc1234`), not prose.
- **docs/STATUS.md last-session block:** ≤5 bullets, the most architecturally significant.
- **Key Decision rationale:** ≤2–3 sentences. Longer context goes only into `docs/key-decisions.md`, referenced by commit hash.
- **In Progress / Next Steps items:** one line each + file paths; no multi-paragraph narration.

## Save Path (default)

The orchestrator owns everything that needs conversation context or user input; the `save-writer` subagent owns the file reads/writes. The orchestrator does NOT edit `CLAUDE.md`, `docs/STATUS.md`, `session-history.md`, `completed-work.md`, `key-decisions.md`, or `known-issues.md` itself — it composes the packet and dispatches.

**Sequence:**

1. **Drain the task list (Part 0 logic).** Run the Part 0 / Drain Validation rules below to reconcile `TaskList` against docs/STATUS.md (CLAUDE.md's state sections on a v1 repo). Respect `--skip-tasks`, and Part 0's availability gate (absent task tools ⇒ same behavior as `--skip-tasks`). The result (completed → completed-work items; in-progress → In Progress; new pending → Next Steps) becomes part of the packet, NOT inline edits.
2. **Compose the update packet** (see "Update Packet" below) from: the conversation (what happened this session — only the orchestrator knows this), the filtered commit list, the diff file list, and the drained task state. Apply the Prose Caps.
3. **Dispatch the `save-writer` subagent** (see "Dispatch" below) and await its change report.
4. **Drift probes** (cheap, on already-gathered data — no new reads): emit the drift warning block if anything fired. Do NOT enforce.
5. **Commit checkpoint (Part 8).** Run Part 8 as written; respects `--skip-commit` and `--silent` (auto-commit, no prompt). The git diff is the user's review surface.
6. **Report** using the Change Report format from `verification-checklists.md` — assembled from the subagent's report + drift warnings. Never echo file contents.

**Skipped on the Save Path** (these are `--full` only): Part 0.5 (legacy-layout archive split), Part 2 (README), Part 3 (`docs/*.md`), Part 4 (auto-memory), Parts 5/6/7 (rollups), Part 1.9 size advisory and Part 1.10 cap enforcement (replaced by drift warnings). All of these live in `mode-update-full.md`.

### Update Packet

Compose this structure and pass it to `save-writer` as the task prompt (fill every field; use the section references in Part 1 to decide *what* each field contains):

- `project_root` — absolute repo path.
- `today` — current date (e.g. `2026-05-29`). Resolve it from the session's current date supplied by the environment; if that's unavailable, fall back to the most recent commit date from the Step 0.1 `git log` (`git log -1 --date=short`). Do not invoke a bare `date` command — it isn't in `allowed-tools`.
- `claude_md_deltas` — exact `old → new` string pairs (or "replace block under `## Section` with: …") for CLAUDE.md sections the session changed: the `Last Updated:` line, `## Key Decisions` (Part 1.6) and `## Known Issues / Blockers` (Part 1.7 — a blocker added or reworded this session; a blocker **resolved** this session goes in `known_issue_moves`, not here). For `## Known Issues / Blockers` use exact `old → new` pairs only, never the block-replace form, and never a pair that touches an entry listed in `known_issue_moves`: deltas are applied before the archive step, so either would remove an issue before it is archived. **Instructions only** — no state sections. Source the *old* strings verbatim from the CLAUDE.md you read in Step 0.
- `status_md_deltas` — the same, for `docs/STATUS.md`: its `Last Updated:` line, Current Status rows (Part 1.2), the `## Completed` summary line if the drain changed the completed count (Part 0 / Part 1.3), In Progress (Part 1.4) and Next Steps (Part 1.5). Source the *old* strings verbatim from the docs/STATUS.md you read in Step 0 (or, on a v1 repo where STATUS.md is absent, from CLAUDE.md's state sections, per Step 0.1).
- `status_md_session_block` — the full replacement text for STATUS.md's `## Session History` last-session block (Part 1.8 format, ≤5 bullets). New field name under schema v2 — the block lives in STATUS.md now, not CLAUDE.md.
- `session_history_entry` — the detailed entry for `docs/session-history.md` (Part 1.8 format, capped).
- `completed_items` — `- [x] …` lines from the task drain (may be empty).
- `decision_rows` — a list of `| decision | rationale |` rows, **one per** genuinely architectural decision made this session (Part 1.6 criteria); empty list if none. Most sessions have 0–1, but a session that locks in several architectural decisions lists each as its own row (don't drop the extras).
- `known_issue_moves` — a list, **one item per** issue this session resolved (Part 1.7); empty list if none. Each item carries: `entry` (the entry's full text, verbatim from the CLAUDE.md you read in Step 0 — it is both the archive body and the removal `old_string`), `title` (≤10 words, taken from the entry's lead), `status` (`resolved`), `session` (e.g. `S60`), and `commit` (the short hash that resolved it, or `none`).

### Dispatch

Dispatch one `save-writer` subagent via the Agent tool with `subagent_type: "bx:save-writer"`, passing the packet as the prompt (serialize as labeled sections). Await its change report.

`save-writer` reports on two channels, matching `doc-migrator.md`'s convention: `notes:` is advisory, `warnings:` is the channel that compels action. `warnings:` itself carries three distinct sub-cases (see `save-writer.md`'s Output section) that call for different responses — do not treat every non-`none` `warnings:` as a re-dispatch trigger. Handle each:
- **`notes:` non-`none`** (a density-cap: a field exceeded the prose caps) → tighten the offending field, note it in your report, do NOT re-dispatch.
- **`warnings:` non-`none`, unmatched delta** (an `old_string` didn't match, so that CLAUDE.md or docs/STATUS.md section was left un-updated) → re-source the exact current string from the CLAUDE.md / docs/STATUS.md you read in Step 0 (or re-read the affected lines) and re-dispatch **only** those deltas. This is the one case where re-dispatch IS warranted — silently leaving a section stale is the failure mode this guards against.
- **`warnings:` non-`none`, unmatched known-issue removal** (the entry was archived, but its text was not found verbatim in CLAUDE.md, so it was not removed) → re-read the affected lines of CLAUDE.md and re-dispatch **only** a `claude_md_deltas` removal for that entry. This is the one case where a delta may remove a Known Issues entry, and it is safe because the archive copy already exists. Do NOT re-send the `known_issue_moves` item.
- **`warnings:` non-`none`, schema-v1 `docs/STATUS.md`-absent fallback** (save-writer routed `status_md_deltas` and `status_md_session_block` to CLAUDE.md because `docs/STATUS.md` doesn't exist yet) → confirm the v1 routing was expected (migration hasn't run on this repo), log it in your report, do NOT re-dispatch.
- Both `notes:` and `warnings:` read `none` → done, no re-dispatch.

### Drift warning format (show only lines whose probe fires)

> "Drift detected — run `/bx:save --full` when convenient:
>  - [N] sessions in `docs/session-history.md` ready for rollup (count > 5)
>  - Key Decisions table in CLAUDE.md at [M] rows (cap 20)
>  - README.md or `docs/*.md` touched in [K] commits since last full sweep
>  - CLAUDE.md at [X]k chars (target ~7k, soft cap 12k) — Part 7 size-pressure rollup will fire on `--full`
>  - CLAUDE.md at [X]k chars — over the 9k advisory rung; largest section `## [name]` ([N] chars); no shrinker fires below 12k
>  - `## Known Issues / Blockers` at [N] chars (threshold 4000) — the resolved-first rollup fires on `--full` once CLAUDE.md is over its soft cap
>  - docs/STATUS.md at [Y]k chars (target ~10k, soft cap 20k) — Part 7 size-pressure rollup will fire on `--full`
>  - docs/[archive].md at [Z]k chars — rotation fires at 100k on `--full` (Part 7.7)"

Show the archive line only for an archive at ≥90k chars (approaching or over the 100k rotation threshold). Show the soft-cap line when CLAUDE.md is over 12k and the advisory-rung line when it is over 9k and at or under 12k — never both. Show the Known Issues line when that section is over 4000 chars, whatever the file size.

If no probe fires, omit the warning entirely.

## Part 0: Drain Task List into docs/STATUS.md

Before updating documentation, **capture any task progress from the current session's live task tracker:**

**Availability gate.** The task tools are absent by default on current models — see
`references/task-tools.md` (this skill owns that file). If `TaskList` is not in your toolset,
treat this Part exactly as `--skip-tasks`: no drain, no stale-task warning. The In Progress /
Next Steps deltas then come from the conversation alone, which the orchestrator has either
way, and the drain summary line reports it once. Everything below is the tracker path.

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

## Part 1: Update CLAUDE.md and docs/STATUS.md

> **Who runs Part 1.** On both paths `save-writer` applies 1.0–1.8 from the packet; only 1.9–1.10 run on the orchestrator, during the `--full` sweep (both in `mode-update-full.md`). **Plan-then-batch (orchestrator-side edits on the Full Path — 1.10, Part 6 row removals, Part 7 shrinkers):** gather every change you intend to make from the evidence cached in Step 0 and Step 0.3. Then apply all changes to each file in a **single Write** of its full contents, or as non-overlapping parallel Edits in one turn — per the routing table below, some sub-sections target CLAUDE.md and some target docs/STATUS.md; batch each file's edits separately. Do NOT issue one Edit per sub-section — that's the dominant turn-count cost.

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
| 1.7 Known Issues / Blockers | CLAUDE.md (+ append to docs/known-issues.md) |
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
Target: **CLAUDE.md's `## Known Issues / Blockers` section** (unchanged from v1), plus the
`docs/known-issues.md` archive (format owned by `doc-schema.md`'s Archives section).

An **entry** starts at a **lead** and runs to just before the next lead, the next block
whose first line starts with `>`, or the end of the section. A lead is a line that opens with
a bold phrase (`**…**`) or a top-level bullet (`- `, `* `, `1. `, with or without a
`[ ]`/`[x]` checkbox). Everything under a lead belongs to that entry: continuation
paragraphs, code blocks, nested bullets, sub-headings. If the section has no bold or bullet
leads at all, each blank-line-separated paragraph is an entry and its first sentence is the
lead.

Not entries, and never moved: a block whose first line starts with `>` (the
`> Session state:` pointer line that follows the section, and the `> Archived issues:` link
Part 7.3 adds), and the placeholder `None currently.` in any emphasis or with any trailing
note. An entry's **title** is its lead without bold markers, bullet or checkbox, or trailing
punctuation.

- **Add** new issues discovered this session, as new entries after the last entry and above
  any `>` block.
- **Relocate resolved issues; do not delete them.** Put each issue this session resolved in
  the packet's `known_issue_moves` with `status: resolved`, the resolving session, and the
  commit hash where one exists. Do not also write a `claude_md_deltas` removal for it:
  `save-writer` archives the entry first and removes it second, so a failed append can
  never lose it.
- **An issue is resolved when the session that resolved it says so — never inferred from
  absence of mention.** A blocker nobody discussed this session is still a blocker.
- An entry an earlier session marked resolved in place stays where it is on the Save Path.
  Part 7.3's shrinker moves it on `--full`.
- Write `None currently.` when the last entry leaves; replace that line when the first
  entry arrives.

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

## Part 8: Commit Checkpoint

After all documentation updates **and rollups** are complete, remind the user to commit. This runs last so that Parts 5, 6, and 7 changes are included in the same commit as the session updates.

**If `--skip-commit` is in `$ARGUMENTS`, skip this step entirely.**

1. **Run `git status`** to show all uncommitted files (staged and unstaged)
2. **Plugin version bump (claude-config repo only — skip silently when `bx/.claude-plugin/plugin.json` doesn't exist).** If any uncommitted file is under `bx/`, the commit MUST also bump `version` in `bx/.claude-plugin/plugin.json` and add a matching entry to the repo-root `CHANGELOG.md` (newest first). The version is the plugin's update cache key: a pushed commit that doesn't bump it is never offered to users — `claude plugin update` reports "already at the latest version". Semver: PATCH for fixes and doc corrections, MINOR for a new skill/agent/flag, MAJOR for breaking renames or removed behavior. In `--silent` mode, default to PATCH and derive the CHANGELOG line from the suggested commit message.
2b. **Validate the plugin (same repo-only condition as step 2 — skip silently when
   `bx/.claude-plugin/plugin.json` doesn't exist).** After the version bump and before the commit,
   run the official local smoke test:

   ```
   claude plugin validate ./bx --strict --json
   ```

   `--strict` treats warnings as errors, which is what you want at a commit checkpoint: unrecognized
   frontmatter keys and missing metadata are tolerated by the runtime but are exactly the drift this
   step exists to catch. Also validate the marketplace manifest with `claude plugin validate . --json`
   when `.claude-plugin/marketplace.json` exists at the repo root.

   `--json` (Claude Code 2.1.259+) returns a machine-readable report. **Judge the outcome from its
   fields, not from prose:** the top-level `success` boolean is the verdict; `manifest.errors`,
   `manifest.warnings` and `contents` carry the specifics. If the CLI rejects `--json` (older Claude
   Code), re-run without the flag and read the prose output instead.

   - **Passes** (`"success": true`) → report one line (`plugin validate: passed`) and continue to step 3.
   - **Fails or warns** (`"success": false`, or any non-empty `manifest.errors` / `manifest.warnings`)
     → surface the `errors` and `warnings` entries verbatim and ask whether to fix now or commit anyway.
     Do NOT block the commit on your own judgement; a validation warning is information for the
     user, not a veto. In `--silent` mode, report the failure in the run summary and commit anyway —
     the flag's contract is zero prompts, and silently *skipping* the commit would be worse than
     committing something that warns.
   - **Command not found** (older Claude Code, or a non-interactive environment without the CLI on
     PATH) → skip silently. This step must never fail a save because the harness lacks the command.

   This is the "install smoke-test" half of the S37 plugin-packaging leftovers, closed by
   `/bx:evolve` finding `b5659902` (docs lane, 2026-08-24).

3. **If there are uncommitted changes:**
   - Show the list of modified/untracked files
   - Suggest a conventional commit message based on what was done this session, e.g.:
     > Suggested commit: `docs: update session progress and documentation`
   - **If `--silent` is in `$ARGUMENTS`:** commit immediately with the suggested message — no prompt. This is the only path that commits without confirmation; the user opted in explicitly via the flag. Do NOT push.
   - **Otherwise, ask the user:** "Would you like to commit these changes?"
   - **Never auto-commit without `--silent`** — always wait for user confirmation
4. **If there are no uncommitted changes**, skip silently
