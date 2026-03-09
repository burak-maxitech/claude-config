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
   - Add it to CLAUDE.md's `## Completed` section as `- [x] [task subject] - [files modified]`
   - Remove it from `## In Progress` or `## Next Steps` if it appears there
3. **For each in-progress task:**
   - Ensure it's listed in `## In Progress` with current state
4. **For pending tasks that were created during the session:**
   - Add them to `## Next Steps` in priority order
5. **Skip tasks that already exist in CLAUDE.md** — don't duplicate

This ensures work tracked via TaskCreate/TaskUpdate during the session is persisted back to CLAUDE.md for the next session's `/resume-work`.

**If `--skip-tasks` is in `$ARGUMENTS`, skip this step entirely.**

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
Move items from "In Progress" to "Completed" when done:
```markdown
- [x] [What was finished] - [files modified]
```

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
Add any new decisions:
```markdown
| [New decision] | [Why we chose this] |
```

### 1.7 Known Issues / Blockers
Update with any new issues found:
- Add new issues discovered
- Remove resolved issues
- Mark "None currently" if empty

### 1.8 Session History
**Add new session entry at the end:**
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

### 1.9 Archive Old Sessions
After adding the new session entry, manage CLAUDE.md file size:

1. **Count session entries** under `## Session History`
2. **If more than 3 entries exist:**
   a. Identify all session entries except the **last 3** (most recent)
   b. Create or update `docs/session-history.md`:
      - If the file doesn't exist, create it with this header:
        ```markdown
        # Session History Archive

        > Auto-managed by `/update-docs`. Recent sessions are in [CLAUDE.md](../CLAUDE.md).

        ---
        ```
      - Append the older sessions to the archive file in chronological order
      - Do NOT duplicate sessions already in the archive — only move sessions not yet archived
   c. Remove the archived session entries from CLAUDE.md
   d. Add or update a reference line at the top of `## Session History`:
      ```markdown
      > Full history: [docs/session-history.md](docs/session-history.md) (Sessions 1–N)
      ```
      Where N is the last archived session number.
3. **Keep the archive file in chronological order** (oldest first)
4. **Update the session range** in the reference link each time new sessions are archived

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
