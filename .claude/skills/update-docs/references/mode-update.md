# MODE: UPDATE (Refresh Existing Docs)

When documentation structure exists, update to reflect current state.

## Step 1: Scan docs/ Folder

1. **List all .md files** in docs/
2. **Identify file purposes:**
   - PRD files (requirements, specifications)
   - Architecture docs
   - API documentation
   - Sample/example files
   - Other supporting docs
3. **Update relevant files** based on code changes

## Part 0: Drain Task List into CLAUDE.md

Before updating documentation, **capture any task progress from the current session's live task tracker:**

1. **Run `TaskList`** to get all tasks and their statuses
2. **For each completed task:**
   - Add it to `docs/completed-work.md` as `- [x] [task subject] - [files modified]`
   - Update CLAUDE.md's `## Completed` summary line (increment count)
   - Remove it from `## In Progress` or `## Next Steps` if it appears there
3. **For each in-progress task:**
   - Ensure it's listed in `## In Progress` with current state
4. **For pending tasks that were created during the session:**
   - Add them to `## Next Steps` in priority order
5. **Skip tasks that already exist in CLAUDE.md** — don't duplicate

This ensures work tracked via TaskCreate/TaskUpdate during the session is persisted back to CLAUDE.md for the next session's `/resume-work`.

**If `--skip-tasks` is in `$ARGUMENTS`, skip this step entirely.**

### Drain Validation

After draining, verify completeness:

1. **Run `TaskList`** again to confirm all tasks have been processed
2. **Ad-hoc tasks** (tasks created during the session that don't map to existing CLAUDE.md sections):
   - If completed → add to `docs/completed-work.md`
   - If pending/in-progress → add to `## Next Steps` in CLAUDE.md
3. **Report drain summary** to the user:
   > "Task drain complete: [N] completed, [M] in-progress, [K] pending synced to docs."

## Part 0.5: One-Time Migration (if needed)

**Check if CLAUDE.md still has the old bloated format.** This migration runs once per project to transition from the old structure (full checklists, full decision tables, multiple session entries) to the new lean structure.

**Detection:** Run this migration if ANY of these are true:
- `## Completed` section contains more than 2 `- [x]` checkbox lines
- `## Key Decisions` table has more than 25 rows
- `## Session History` contains more than 1 `### Session` entry
- CLAUDE.md is over 25k characters

**Migration steps:**

### Migrate Completed Section
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

### Migrate Key Decisions
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

### Migrate Session History
1. Extract all `### Session` entries from CLAUDE.md's `## Session History`
2. Create `docs/session-history.md` (if it doesn't exist) with header:
   ```markdown
   # Session History Archive

   > Auto-managed by `/update-docs`. Last session summary is in [CLAUDE.md](../CLAUDE.md).

   ---
   ```
3. Append ALL session entries to `docs/session-history.md` (in chronological order, skip duplicates)
4. Replace CLAUDE.md's `## Session History` with only the last session as a 3-5 bullet summary:
   ```markdown
   > Full history: [docs/session-history.md](docs/session-history.md)

   ### Last Session (Session [N]) - [DATE]
   - [3-5 bullet points from the most recent session]
   ```

**After migration, continue with the normal update process below.**

---

## Part 1: Update CLAUDE.md

### 1.0 Update Timestamp
**Always update the "Last Updated" field** at the top:
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
Update phase/task statuses based on code changes:
- Change Not Started -> In Progress when work starts
- Change In Progress -> Complete when work completes
- Add new rows for new components

### 1.3 Completed Section
When items are completed:
1. **Append the detailed entry to `docs/completed-work.md`:**
   - If the file doesn't exist, create it with header:
     ```markdown
     # Completed Work

     > Full checklist of completed tasks. Referenced from [CLAUDE.md](../CLAUDE.md).

     ---
     ```
   - Append: `- [x] [What was finished] - [files modified]`
2. **Keep CLAUDE.md's `## Completed` section as a brief summary:**
   ```markdown
   ## Completed

   [N] tasks completed across [areas]. See [docs/completed-work.md](docs/completed-work.md) for full checklist.
   ```
   Update the count and areas description as needed. Do NOT maintain a full checkbox list in CLAUDE.md.

### 1.4 In Progress Section
Update current work state:
```markdown
- [ ] [Current task] - [files being modified]
```

### 1.5 Next Steps Section
Refresh prioritized task list:
- Remove completed items
- Add new tasks discovered
- Reorder by priority
- Include relevant file paths

### 1.6 Key Decisions Made
When adding new decisions:
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
Update with any new issues found:
- Add new issues discovered
- Remove resolved issues
- Mark "None currently" if empty

### 1.8 Session History
Session history is split between CLAUDE.md (brief) and docs/session-history.md (detailed).

**1. Write the DETAILED session log to `docs/session-history.md`:**
   - If the file doesn't exist, create it with this header:
     ```markdown
     # Session History Archive

     > Auto-managed by `/update-docs`. Last session summary is in [CLAUDE.md](../CLAUDE.md).

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

**2. Write only a brief summary to CLAUDE.md's `## Session History`:**
   - Replace (not append) the previous last-session block with the new one:
     ```markdown
     ## Session History

     > Full history: [docs/session-history.md](docs/session-history.md)

     ### Last Session (Session [N]) - [DATE]
     - [3-5 bullet points summarizing key accomplishments and state]
     ```
   - CLAUDE.md should only ever contain ONE session block (the most recent).
   - All previous sessions live exclusively in `docs/session-history.md`.

### 1.9 Size Check
After all updates, check CLAUDE.md file size:
1. If CLAUDE.md exceeds **35k characters**, warn the user:
   > "CLAUDE.md is [X]k chars — approaching the 40k limit. Consider condensing sections or moving more content to reference files."
2. Target is ~17k chars. If significantly over, suggest specific sections to trim.

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

Claude Code maintains a persistent auto-memory directory (`~/.claude/projects/<project-path>/memory/`) that is automatically loaded into every conversation. Use it as a **stable quick-reference layer** alongside CLAUDE.md's evolving status.

**If `--skip-memory` is in `$ARGUMENTS`, skip this step entirely.**

### 4.1 What to Sync to Auto-Memory `MEMORY.md`
Extract **stable, slow-changing facts** from the project and write/update them:
- Project name, repo, one-line description
- Tech stack and key framework versions
- Common commands (build, test, run, lint)
- Key file paths and entry points
- Architecture pattern (e.g., "Next.js app router + Prisma + PostgreSQL")
- Environment variable names (not values)
- Project-specific conventions (naming, folder structure patterns)

### 4.2 What NOT to Sync
Do not duplicate evolving state — that stays in CLAUDE.md:
- Session history, in-progress items, next steps
- Blockers, decisions log, completion status
- Anything that changes every session

### 4.3 Sync Rules
1. **Read existing auto-memory first** — check `~/.claude/projects/` for this project's memory directory
2. **Update, don't overwrite** — merge new facts into existing memory, don't replace the whole file
3. **Keep it concise** — auto-memory MEMORY.md is truncated after 200 lines; prioritize density
4. **Only sync when facts change** — if tech stack, commands, or structure haven't changed, skip this step
5. **Create topic files** for detailed notes (e.g., `debugging.md`, `patterns.md`) and link from MEMORY.md

## Part 5: Commit Checkpoint

After all documentation updates are complete, remind the user to commit.

**If `--skip-commit` is in `$ARGUMENTS`, skip this step entirely.**

1. **Run `git status`** to show all uncommitted files (staged and unstaged)
2. **If there are uncommitted changes:**
   - Show the list of modified/untracked files
   - Suggest a conventional commit message based on what was done this session, e.g.:
     > Suggested commit: `docs: update session progress and documentation`
   - **Ask the user:** "Would you like to commit these changes?"
   - **Never auto-commit** — always wait for user confirmation
3. **If there are no uncommitted changes**, skip silently

## Part 6: Roll Up Old Sessions in session-history.md

Keep `docs/session-history.md` bounded by compressing sessions older than the 5 most recent into one-line summaries. The full prose still lives in git history at the linked commit hashes.

**If `--skip-rollup` is in `$ARGUMENTS`, skip this step entirely.**

### 6.1 Detect Compressible Sessions

1. Read `docs/session-history.md`
2. Grep for `^### Session` headers and count them
3. **If count ≤ 5, skip silently** — nothing to compress
4. The 5 highest-numbered sessions stay in full prose; everything older is a candidate for compression
5. Identify which older entries are still in multi-line "What happened / Files / Next session" format. Skip any already in one-line format (idempotent — running this part repeatedly is safe)

### 6.2 First-Run Confirmation (per-project)

The presence of the rollup-format note (see Step 6.4) acts as a "this project has consented to rollups before" sentinel. Use it to gate the first-run prompt:

1. **Check if the rollup note exists** in `session-history.md`'s header (search for the literal substring `Sessions older than the 5 most recent are compressed`)
2. **If the note IS present** → proceed silently to Step 6.3 (this project has been rolled up before)
3. **If the note is MISSING and there are entries to compress** → this is the first rollup pass on this project. Ask the user:
   > "First-time rollup detected for this project: `docs/session-history.md` has [N] sessions in full-prose format, [M] of which are older than the 5 most recent and would be compressed to one-line summaries with commit hashes. Full prose stays preserved in git history. Compress now? (y/n)"
   - **If user declines** → skip the rest of Part 6 entirely. Do NOT add the rollup note (so the user is asked again next run).
   - **If user accepts** → proceed to Step 6.3.
4. **Use `AskUserQuestion` if available** for a cleaner y/n/skip-this-time prompt; fall back to a numbered chat question otherwise.

### 6.3 Compress Each Older Session

For each session needing compression:

1. **Extract a one-line summary** from the existing entry — pull the most architecturally significant 1-3 bullets from "What happened" and condense. Keep skill names, flag names, and concrete artifacts (file names, decision names) since those are what future-readers grep for. Drop process narration ("ran /update-docs", "committed and pushed", "user asked").
2. **Find associated commit hashes** by running:
   ```
   git log --since="<session-date>" --until="<next-session-date or +1d>" --pretty=format:'%h %s'
   ```
   - If the session entry already lists commit hashes (`(commits ...)`, `(commit ...)`), prefer those — they were chosen during the original session
   - Otherwise pick commits whose subjects clearly correspond to the session's work; cap at 4 hashes
   - If no commits exist in the date window (rare — pure docs session?), omit the parenthetical
3. **Replace the multi-line block** with a single line in this format:
   ```
   ### Session N - YYYY-MM-DD: [one-line summary] (commits: hash1, hash2)
   ```
   For a single commit, use `(commit: hash)`. For "bundled" cases where multiple sessions share a commit, write `(bundled in hash)`.
4. Preserve a single blank line between session entries.

### 6.4 Add Rollup Note (First Run Only)

If `session-history.md` does not already contain the rollup note (i.e., this is the first run and the user said yes in Step 6.2), insert it after the existing `> Auto-managed by /update-docs...` line:

```markdown
> **Note:** Sessions older than the 5 most recent are compressed to one-liners with commit hashes. Full prose for compressed sessions lives in git history (`git show <hash>`).
```

This note is the gating sentinel: its presence tells future runs that the user has already consented to rollups for this project, and Step 6.2 will skip the prompt next time.

### 6.5 Report

Tell the user:
> "Rolled up [N] older sessions. session-history.md: [old-size]k → [new-size]k chars."

If 0 sessions were compressed, skip the report.
