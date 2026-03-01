# /update-docs - Documentation Management Command

Analyze this codebase and manage documentation. Act as a senior engineer who values clear, maintainable documentation.

**Companion command:** `/resume-work` - Use at the start of sessions to get up to speed.

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

## Documentation Structure (Target State)

All projects should have this documentation system:

| File | Location | Purpose | Audience |
|------|----------|---------|----------|
| **README.md** | Root | Public overview, setup guide, quick reference | Developers, new team members |
| **CLAUDE.md** | Root | Session context, progress tracking, working notes | AI coding assistants |
| **docs/*.md** | docs/ | PRD, specifications, detailed documentation | Detailed implementation reference |

### Handling docs/ Folder

The `docs/` folder may contain **one or more** documentation files:
- `docs/PRD.md` - Single PRD file
- `docs/[project-name]-prd.md` - Project-specific PRD
- `docs/architecture.md`, `docs/api.md`, etc. - Multiple spec files
- `docs/sample-*.md`, `docs/examples-*.md` - Supporting documents

**Rules for docs/ folder:**
1. **Scan all .md files** in docs/ folder
2. **Identify PRD files** (contain "PRD", "requirements", "specifications" in name or content)
3. **Update relevant files** based on what changed in codebase
4. **Preserve project-specific files** - don't rename or restructure existing docs
5. **Reference by actual filename** in README.md and CLAUDE.md links

---

## CRITICAL: Context Preservation Rule

**These files serve as the primary context source for AI coding assistants in future sessions.**

Therefore:
- **NEVER remove existing information unless it's factually incorrect or obsolete**
- **ALWAYS preserve context that helps an AI understand the project**
- **ADD new information, don't replace unless necessary**
- **When in doubt, keep it - more context is better than less**
- **Expand and enrich existing sections rather than condensing them**
- **During REFACTOR: Move content to appropriate files, don't delete it**
- **Preserve existing file names in docs/ - don't rename project-specific files**

---

## CRITICAL: CLAUDE.md Required Sections

**The `/resume-work` command depends on these exact section headers in CLAUDE.md.**

CLAUDE.md **MUST** contain these sections (in this order):
1. `## Project Overview` - Name, repo, description, key docs links
2. `## Current Status` - Status table with Complete/In Progress/Not Started indicators
3. `## Completed` - Checkbox list of done items
4. `## In Progress` - Checkbox list of current work
5. `## Next Steps` - Numbered priority list
6. `## Key Decisions` - Decision/rationale table
7. `## Architecture Summary` - Brief architecture description
8. `## Known Issues / Blockers` - Current blockers
9. `## Environment Variables` - Required env vars
10. `## Session History` - Chronological session logs

**Do not rename, remove, or reorder these sections.**

---

# MODE: REFACTOR (Split Existing README.md)

When README.md contains everything, split it intelligently:

## What Goes Where

### -> Move to CLAUDE.md (Session Context)
- Current status / progress tracking
- TODO lists and next steps
- Work in progress notes
- Session history (if any)
- Known issues and blockers
- Recent decisions and their rationale
- "Current state" sections
- Development notes
- Anything that changes frequently

### -> Move to docs/PRD.md (Full Specifications)
- Detailed architecture documentation
- Complete API specifications
- Data models and schemas
- Sequence diagrams
- Detailed configuration specs
- Integration details
- Security specifications
- Detailed technical decisions (ADRs)
- Anything comprehensive/reference-like

### -> Keep in README.md (Public Overview)
- Project description (concise)
- Feature list (bullet points)
- Quick start / installation
- Basic usage examples
- Project structure (brief)
- Tech stack summary
- Links to other docs
- Contributing guidelines
- License

## Refactor Process

1. **Analyze existing README.md** - Identify all sections
2. **Check if docs/ exists** - Scan for existing documentation files
3. **Categorize each section** - Determine which file it belongs to
4. **Create CLAUDE.md** - With ALL required sections + moved content
5. **Create/Update docs/PRD.md** - With full specifications + moved content (use existing PRD if present)
6. **Slim down README.md** - Keep overview, add links to actual doc files
7. **Verify no content lost** - All information preserved somewhere

---

# MODE: CREATE (Generate From Scratch)

When no documentation exists, generate all files from codebase analysis.

## Analysis Steps

1. **Scan project structure** - Identify all folders, key files
2. **Identify tech stack** - Languages, frameworks, dependencies
3. **Find entry points** - main.py, index.js, etc.
4. **Analyze configuration** - .env files, config folders
5. **Identify patterns** - Architecture, design patterns used
6. **Extract purpose** - From code comments, file names, structure
7. **Check for existing docs/** - Don't overwrite existing files

## Create: README.md Template

```markdown
# [Project Name]

[One-line description based on codebase analysis]

## Overview

[2-3 sentences about what this project does]

## Features

- [Feature 1 based on code analysis]
- [Feature 2]
- [Feature 3]

## Quick Start

### Prerequisites
- [Detected requirements]

### Installation
[Based on package.json, requirements.txt, etc.]

### Running
[Based on detected entry points]

## Project Structure

[Based on actual folder analysis]

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| [Layer] | [Tech] | [Purpose] |

## Documentation

- [CLAUDE.md](CLAUDE.md) - Development context and session notes
- [docs/PRD.md](docs/PRD.md) - Full specifications and architecture

## License

[Detected or "See LICENSE file"]
```

## Create: CLAUDE.md Template

**IMPORTANT:** This template contains ALL required sections for `/resume-work` compatibility.

```markdown
# Claude Code Context

> **Purpose:** Maintains context across AI coding sessions.
> **Update:** Run `/update-docs` at the end of each coding session.
> **Resume:** Run `/resume-work` at the start of each coding session.

**Last Updated:** [DATE AND TIME]

---

## Project Overview

**Project:** [Name]
**Repository:** [repo-name]
**Description:** [One-liner]

**Key Documentation:**
- [List all docs/*.md files found or created with descriptions]

---

## Current Status

| Component | Status | Description |
|-----------|--------|-------------|
| [Component 1] | Complete | [Status note] |
| [Component 2] | In Progress | [Status note] |
| [Component 3] | Not Started | [Status note] |

**Legend:** Complete | In Progress | Not Started

---

## Completed

- [x] [Detected completed features]
- [x] [Another completed item]

---

## In Progress

- [ ] [Current work item]
- [ ] [Another in-progress item]

---

## Next Steps

1. **[Priority 1]** - [Description and relevant files]
2. **[Priority 2]** - [Description and relevant files]
3. **[Priority 3]** - [Description and relevant files]

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| [Detected pattern/choice] | [Inferred or documented reason] |
| [Another decision] | [Reason] |

---

## Architecture Summary

[Brief architecture based on code analysis - 2-4 sentences or small diagram]

---

## Known Issues / Blockers

- [ ] [Any detected TODOs, FIXMEs, or issues]
- [ ] [Blockers preventing progress]

*None currently* - if no issues detected

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| [VAR_NAME] | Yes/No | [Purpose] |

[Extracted from .env.example or code analysis]

---

## Session History

### Session 1 - [DATE]
**What happened:**
- Initial documentation created from codebase analysis

**Files created/modified:**
- CLAUDE.md (created)
- README.md (created)
- docs/PRD.md (created)

**Next session should:**
- Review and verify generated documentation
- Add missing context
- Begin development on [suggested area]
```

## Create: docs/PRD.md Template

```markdown
# Project Requirements Document (PRD)
# [Project Name]

**Version:** 1.0
**Last Updated:** [DATE]
**Generated:** From codebase analysis

---

## 1. Overview

[Detailed description based on code analysis]

---

## 2. Architecture

### 2.1 High-Level Architecture

[Mermaid diagram based on detected structure]

### 2.2 Tech Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| [Layer] | [Tech] | [Version from package files] | [Purpose] |

### 2.3 Project Structure

[Detailed folder structure with explanations]

---

## 3. Components

[Document each major component/service detected]

---

## 4. Data Models

[If database/models detected, document them]

---

## 5. API Endpoints

[If API routes detected, document them]

---

## 6. Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| [VAR] | [Yes/No] | [Purpose] |

---

## 7. Dependencies

[From package.json, requirements.txt, etc.]

---

## 8. Development

### Setup
[Detailed setup instructions]

### Testing
[If tests detected, document how to run]

### Deployment
[If deployment config detected, document it]
```

---

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

---

# Output Format

## For All Modes

### 1. Summary (in response, not in docs)

```markdown
## Documentation Mode: [REFACTOR/CREATE/UPDATE]

### Documentation Structure Detected

**docs/ folder contents:**
- [List all files found in docs/]

### Actions Taken

**[REFACTOR only] Content Migration:**
| Section | From | To |
|---------|------|-----|
| ... | ... | ... |

**Files Created:**
- [List new files]

**Files Modified:**
- [List modified files with change summary]

**Files Preserved (unchanged):**
- [List files that didn't need changes]

**Discrepancies Found:**
- [Any mismatches between docs and code]

**Verification:**
- [ ] All content preserved (REFACTOR)
- [ ] All files created (CREATE)
- [ ] All files consistent (UPDATE)
- [ ] Links in README.md point to actual files
- [ ] Links in CLAUDE.md point to actual files
- [ ] CLAUDE.md has all required sections for /resume-work
```

### 2. Full File Contents

Provide complete content for each file created or significantly modified.

---

# Verification Checklist

## REFACTOR Mode
- [ ] All README.md content accounted for
- [ ] Nothing deleted, only moved
- [ ] CLAUDE.md has ALL required sections (see list above)
- [ ] CLAUDE.md has "Last Updated" timestamp
- [ ] docs/ folder has specifications
- [ ] README.md links to actual files in docs/
- [ ] Existing docs/ files preserved

## CREATE Mode
- [ ] All required files generated
- [ ] Content based on actual codebase
- [ ] Tech stack accurately detected
- [ ] Project structure matches reality
- [ ] Environment variables documented
- [ ] CLAUDE.md has ALL required sections
- [ ] CLAUDE.md has "Last Updated" timestamp
- [ ] Templates ready for future updates
- [ ] Didn't overwrite existing docs/ files

## UPDATE Mode
- [ ] CLAUDE.md "Last Updated" timestamp refreshed
- [ ] CLAUDE.md session history has new entry
- [ ] CLAUDE.md status reflects current state
- [ ] CLAUDE.md links to actual docs/ files
- [ ] CLAUDE.md has all required sections intact
- [ ] README.md matches current features
- [ ] README.md links to actual docs/ files
- [ ] Relevant docs/*.md files updated
- [ ] All files consistent with each other
- [ ] No valuable context removed
- [ ] Session history archived if more than 3 entries (old sessions moved to docs/session-history.md)
- [ ] Auto-memory synced with stable project facts (if changed)
- [ ] Task list drained — completed/in-progress/pending tasks synced back to CLAUDE.md
- [ ] Project-specific files preserved

---

## Scope

$ARGUMENTS
