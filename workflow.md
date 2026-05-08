# My Claude Code Workflow

> Personal guide for using Claude Code effectively with my custom command system.

---

## Quick Reference

| Phase | Command | Purpose |
|-------|---------|---------|
| **Start Session** | `/resume-work` | Get up to speed, see what's next |
| **Plan Feature** | `/plan-feature` | Interview before building |
| **During Development** | `/code-review` | Review code quality |
| **During Development** | `/code-cleanup` | Find dead code & cruft |
| **Architecture Audit** | `/architecture-review` | Repo-wide complexity + refactor + perf review |
| **End Session** | `/update-docs` | Save progress & context |

---

## Daily Workflow

### Quick Start

```bash
cc my-project    # launch directly
cc               # interactive project picker
```

> No `cc` alias? See [README.md](README.md#quick-start) for one-time setup.

**What the script does (5 steps):**
1. Pulls latest claude-config (syncs skills/agents across machines)
2. Verifies `~/.claude` symlinks are in place
3. Navigates to project and pulls latest changes
4. Checks for Claude Code updates
5. Launches Claude Code (tip: run `/resume-work` to get up to speed)

**What `/resume-work` does:**
- Checks auto-memory for stable project facts already in context
- Reads CLAUDE.md, README.md, and docs/ in parallel (single turn)
- Runs all git commands in parallel (log, diff, status)
- Shows current status + recommends next task
- Hydrates a live task list from CLAUDE.md using TaskCreate

### Manual Steps (what the script does under the hood)

<details>
<summary>Mac</summary>

```bash
# 1. Pull latest commands (in case you updated from another machine)
cd ~/Development/projects/claude-config && git pull && cd -

# 2. Verify config symlinks are in place
ls -d ~/.claude/skills ~/.claude/agents 2>/dev/null || echo "MISSING SYMLINKS — see Setup section"

# 3. Navigate to project
cd ~/projects/[project-name]

# 4. (Optional) Pull latest project changes
git pull

# 5. Check for Claude updates
claude update

# 6. Launch Claude Code
claude

# 7. Get up to speed
/resume-work
```

</details>

<details>
<summary>Windows (PowerShell)</summary>

```powershell
# 1. Pull latest commands (in case you updated from another machine)
cd C:\Development\projects\claude-config; git pull; cd -

# 2. Verify config symlinks are in place
Get-ChildItem ~\.claude | Where-Object { $_.LinkType -eq "SymbolicLink" } | Format-Table Name, Target

# 3. Navigate to project
cd C:\Development\projects\[project-name]

# 4. (Optional) Pull latest project changes
git pull

# 5. Check for Claude updates
claude update

# 6. Launch Claude Code
claude

# 7. Get up to speed
/resume-work
```

</details>

---

### During Development

#### Adding a New Feature

```bash
# 1. First, add feature to PRD
"Add a new feature section to the PRD for [feature name]: [brief description]"

# 2. Then plan it with interview
/plan-feature docs/[project]-prd.md

# Or if you have a separate feature doc:
/plan-feature docs/new-feature-spec.md
```

**What `/plan-feature` does:**
- Checks auto-memory, then reads all docs in parallel
- Auto-detects if greenfield or existing project
- Asks 3-5 questions at a time, covers all edge cases
- Enters Plan Mode → writes formal implementation plan → requires approval via ExitPlanMode
- Hydrates approved plan into live tasks with TaskCreate (with dependencies)
- Updates CLAUDE.md with decisions

#### Code Quality Checks

```bash
# Review uncommitted changes (default - most common)
/code-review

# Review specific files
/code-review src/services/gmail_service.py

# Review staged changes before commit
/code-review --staged

# Review a pull request
/code-review 123

# Find dead code and cleanup opportunities (parallel scan)
/code-cleanup

# Focus on specific area or category
/code-cleanup src/services/
/code-cleanup --deps --code
```

**What `/code-review` does:**
- Auto-detects review target (uncommitted changes, staged, PR, or specified files)
- Scans codebase conventions before reviewing (error handling, naming, imports, test patterns)
- Checks correctness, security, performance, maintainability
- Outputs severity summary (Critical/Important/Suggestions count) with mandatory `file:line` references
- Flags convention violations against project patterns

**What `/code-cleanup` does:**
- Scans multiple categories in parallel using subagents
- Produces a summary dashboard (item counts, removable lines, risk levels)
- Lists "Quick Wins" for zero-risk bulk deletions
- Categorizes findings by safety (Safe to Delete / Likely Safe / Needs Investigation)
- Supports filters (`--code`, `--deps`, `--css`, `--tests`, `--aggressive`)

---

### Mid-Session Context Hygiene

Long sessions bloat the context window with tool results, scan outputs, and early exploration that's no longer load-bearing. `/compact` rewrites the conversation into a terse summary while preserving loaded CLAUDE.md, which lets a long session keep going without token exhaustion.

**Run `/compact` proactively — earlier rather than later.** Once the context bar is visibly consumed and the main task ahead is well-defined, compacting immediately is cheaper than waiting until the context is full. A useful form is `/compact focus on <next task>` — Claude keeps the carry-forward summary pointed at what's about to happen next.

This generalizes the compact hints already emitted by `/resume-work` and `/update-docs`. Those two skills suggest compacting after their own substantial work; the same habit applies mid-session whenever a chunk of context (failed approach, large file read, long grep) is no longer needed.

Project-root `CLAUDE.md` survives compaction — Claude re-reads it from disk after `/compact` — so project-wide context is not lost. Nested CLAUDE.md files in subdirectories reload lazily the next time Claude reads a file there. Instructions given only in conversation (not in any CLAUDE.md) may not survive: put anything you want to persist into CLAUDE.md or a `.claude/rules/` file.

---

### Ending a Session

```bash
# Save your progress
/update-docs

# Commit your project work
git add .
git commit -m "feat: [description]"
git push

# If Claude modified any commands or workflow, sync those too
cd ~/Development/projects/claude-config
git status
# If changes exist:
git add .
git commit -m "Updated [what changed]"
git push
cd -
```

**What `/update-docs` does:**
- Drains live task list — syncs completed/in-progress/pending tasks back to CLAUDE.md
- Updates CLAUDE.md with session history, status, and next steps
- Archives old sessions (>3) to `docs/session-history.md` to keep CLAUDE.md lean
- Syncs stable project facts to auto-memory for instant context in future sessions
- Updates README.md and docs/*.md as needed

---

## Command Reference

### /resume-work

**When:** Start of every session

**Usage:**
- `/resume-work` - Standard summary (parallel doc reads + git scan)
- `/resume-work deep` - Verbose mode (includes full session history from archive, complete file tree, all env vars)

**Features:**
- Checks auto-memory for pre-loaded project context
- Reads all docs and runs all git commands in parallel (2 turns total)
- Hydrates CLAUDE.md tasks into live task tracker via TaskCreate

**Output:** Status summary + recommended next task + live task list

---

### /plan-feature

**When:** Before building any new feature

**Usage:**
```bash
/plan-feature                           # Interactive, asks what you're building
/plan-feature docs/feature-spec.md      # Uses specific plan file
```

**Modes:**
- **GREENFIELD** - Full architecture interview (new projects)
- **EXISTING** - Integration-focused interview (adding to existing code)

**Flow:** Interview → EnterPlanMode → implementation plan → ExitPlanMode (approval) → TaskCreate (hydrate tasks) → begin coding

**Output:** Exhaustive requirements gathered, formal plan approved, live task list created

---

### /update-docs

**When:** End of every session (or after major milestones)

**Modes:**
- **CREATE** - Generates all docs from scratch
- **REFACTOR** - Splits monolithic README into three files
- **UPDATE** - Refreshes existing documentation

**Updates:**
- Drains live task list back into CLAUDE.md (completed → Completed, pending → Next Steps)
- CLAUDE.md - Session history, status, next steps
- Archives sessions >3 to `docs/session-history.md`
- Syncs stable facts to auto-memory (`~/.claude/projects/.../memory/MEMORY.md`)
- README.md - Project overview, setup
- docs/*.md - PRD and specifications

---

### /code-review

**When:** Before committing, or to check specific code

**Usage:**
```bash
/code-review                             # Review uncommitted changes (default)
/code-review src/file.py                 # Review specific file
/code-review src/services/               # Review directory
/code-review 123                         # Review PR #123 via gh
/code-review --staged                    # Review only staged changes
/code-review --last-commit               # Review the last commit
```

**Features:**
- Auto-detects review target from arguments
- Scans codebase conventions first (error handling, naming, imports, test patterns)
- Flags convention violations alongside standard issues
- Every finding includes mandatory `file_path:line_number` reference

**Checks:**
- Correctness & bugs
- Security vulnerabilities
- Performance issues
- Maintainability & convention consistency
- Error handling
- Test coverage gaps

**Output:** Severity summary table (counts) → Critical / Important / Suggestions / Convention Violations / What's Good

---

### /architecture-review

**When:** First-time exploring an unfamiliar repo, quarterly architecture health check, or before proposing a major refactor

**Usage:**
```bash
/architecture-review                     # Default review-only report
/architecture-review src/api/            # Scope to a path
/architecture-review --plan              # Also emit a phased refactor brief with /plan-feature hand-offs
/architecture-review --fix               # Apply mechanical refactors with per-finding diff preview
/architecture-review --map               # Heavier architecture-map section with full module-dep ASCII graph
/architecture-review --full-scan         # Force full scan even on >500-file repos
```

**Three guardrails distinguish this from "apply GoF patterns" tools:**
1. **Refactor catalog over GoF patterns.** The catalog (in `references/refactor-catalog.md`) leans toward complexity-reducing techniques (guard clauses, pure-function extraction, flag-argument removal, discriminated unions, table-lookup dispatch). Patterns appear only when the *problem* matches.
2. **Reads intended architecture first.** Step 1 reads CLAUDE.md, README.md, `docs/architecture/`, and ADRs to summarize what the project's architecture is *supposed* to be. Findings that conflict with documented decisions are surfaced separately for user confirmation, not applied automatically.
3. **CCN delta sanity gate.** Each finding includes `ccn_current` (from detected linter) and `ccn_projected`. Findings whose projected ≥ current are filtered before report.

**Decomposition:** Three parallel Sonnet subagents — `arch-structure` (complexity, coupling, layering), `arch-refactors` (catalog-driven), `arch-performance` (high-precision categories only).

**Scale tiers:** <100 files = full scan, 100-500 = bounded, >500 = smart sampling (LOC × churn × import fan-in priority) + drill-down on hotspots.

**Output:** Architecture Map → Findings (Structure / Refactors / Performance, ranked) → Documented-Decision Conflicts (separate, requires confirmation) → Suggested Next Actions (chained skill recommendations + copy-pasteable `/plan-feature` snippets).

**`--fix` is restricted to single-file, non-API-breaking refactors.** Anything cross-file or API-touching auto-routes to `--plan` instead. Each edit is gated by per-finding diff preview. Use `Esc Esc` or `/rewind` to undo.

**Useful chain:** `/code-cleanup` → `/architecture-review` → `/architecture-review --plan` → `/plan-feature` per phase.

---

### /code-cleanup

**When:** Periodic maintenance, before major releases

**Usage:**
```bash
/code-cleanup                            # Full codebase scan (parallel agents)
/code-cleanup src/                       # Specific directory
/code-cleanup --code                     # Dead code only
/code-cleanup --deps                     # Unused dependencies only
/code-cleanup --css                      # Unused CSS only
/code-cleanup --tests                    # Test cleanup only
/code-cleanup --files                    # Unused files only
/code-cleanup --aggressive               # Move "Likely Safe" into "Safe to Delete"
/code-cleanup src/ --code --deps         # Combined: scoped + filtered
```

**Features:**
- Launches parallel subagents to scan multiple categories simultaneously
- Produces a summary dashboard (item counts, removable lines, risk levels)
- Lists "Quick Wins" for zero-risk bulk-approvable deletions

**Finds:**
- Unused files and dead code
- Unused CSS classes
- Unused dependencies
- Obsolete patterns
- Configuration cruft
- Stale tests

**Output:** Summary dashboard → Quick Wins → Safe to Delete / Likely Safe / Needs Investigation

---

## Workflow Scenarios

### Scenario 1: Starting a New Project

```bash
# 1. Create project folder
mkdir ~/projects/new-project
cd ~/projects/new-project
git init

# 2. Create initial docs
# (manually create README.md with basic description)

# 3. Launch Claude
claude

# 4. Generate full documentation
/update-docs

# 5. Plan the first feature
/plan-feature

# 6. Build it!

# 7. End session
/update-docs
```

---

### Scenario 2: Continuing Existing Project

```bash
# 1. Navigate & launch
cd ~/projects/existing-project
claude update
claude

# 2. Get context
/resume-work

# 3. Continue recommended task (or pick your own)

# 4. Periodic code review
/code-review [files you modified]

# 5. End session
/update-docs
```

---

### Scenario 3: Adding a Feature to Existing Project

```bash
# 1. Start session
/resume-work

# 2. Add feature to PRD
"Add a new feature section to the PRD: [Feature Name]
- Purpose: [what it does]
- Requirements: [key requirements]
- Integration: [what it touches]"

# 3. Plan the feature
/plan-feature docs/[project]-prd.md

# 4. Build it

# 5. Review before committing
/code-review [new files]

# 6. End session
/update-docs
```

---

### Scenario 4: Maintenance / Tech Debt Session

```bash
# 1. Start session
/resume-work

# 2. Find cleanup opportunities
/code-cleanup

# 3. Review and fix issues

# 4. Verify changes
/code-review [modified files]

# 5. End session
/update-docs
```

---

### Scenario 5: First Time in an Unfamiliar Repo / Architecture Health Check

```bash
# 1. Start session
/resume-work

# 2. Strip the easy stuff first (dead code is noise for architecture review)
/code-cleanup

# 3. Repo-wide architecture audit
/architecture-review

# 4. Convert top findings into a phased refactor brief
/architecture-review --plan

# 5. Drop each phase into a fresh /plan-feature session as you tackle it
#    (the brief is self-contained — paste and go)

# 6. End session
/update-docs
```

For mechanical refactors only (single-file, non-API-breaking) you can skip step 4 and run `/architecture-review --fix` directly — it gates per finding with a diff preview. Anything cross-file or API-touching gets auto-routed to `--plan` regardless.

---

## Documentation Structure

Every project should have:

```
project/
├── README.md                  # Public overview, setup guide
├── CLAUDE.md                  # Session context (AI reads this first)
└── docs/
    ├── [project]-prd.md       # Full specifications
    ├── session-history.md     # Archived sessions (auto-managed by /update-docs)
    └── [other docs].md        # Supporting documentation
```

Additionally, Claude Code maintains auto-memory at:
```
~/.claude/projects/<project-path>/memory/
├── MEMORY.md                  # Stable project facts (auto-synced by /update-docs)
└── [topic].md                 # Detailed topic notes (optional)
```

| File | Purpose | Updated |
|------|---------|---------|
| **README.md** | Quick start, public docs | When features ship |
| **CLAUDE.md** | AI context, session tracking | Every session |
| **docs/*.md** | Detailed specs, PRD | When requirements change |
| **docs/session-history.md** | Archived session logs (>3 sessions) | Automatically by `/update-docs` |
| **auto-memory MEMORY.md** | Stable facts (tech stack, commands, paths) | When project fundamentals change |

---

## Tips & Best Practices

### Do's

- Always start with `/resume-work`
- Always end with `/update-docs`
- Plan features before building (`/plan-feature`)
- Review code before committing (`/code-review`)
- Keep CLAUDE.md updated - it's your project memory
- Commit frequently with descriptive messages

### Don'ts

- Don't skip `/resume-work` - context matters
- Don't forget `/update-docs` - you'll lose session context
- Don't start coding without planning complex features
- Don't let CLAUDE.md get stale
- Don't ignore code review suggestions

### Recurring tasks: `/loop`

Claude Code ships a built-in `/loop` skill for running a prompt or slash command on a recurring interval within the current session. Handy for polling a long-running process or running a periodic sanity check without manually re-triggering.

```bash
/loop 5m /code-cleanup --dry-run   # dry-run cleanup every 5 minutes
/loop 2m "check deploy status"     # poll a deploy every 2 minutes
/loop /code-review                 # omit interval — model self-paces
```

Two important caveats: `/loop` is **session-scoped** — it dies when the Claude Code session closes — and recurring jobs **auto-expire after 3 days** even if the session lives longer. Don't use it as a replacement for a real cron job or scheduled remote agent (see `/schedule` for persistent scheduling).

**Do not build a custom `/loop` skill in this repo.** The built-in already covers this use case; re-implementing it in `.claude/skills/` would be waste.

---

## New Machine Setup

See [README.md](README.md#setup-on-a-new-machine) for clone, symlink, and sync instructions.

---

## Keyboard Shortcuts & Tips

```bash
# Quick navigation
cd ~/projects && ls              # See all projects
cd ~/projects/[tab]              # Tab completion

# Git shortcuts
git status                       # What's changed
git diff                         # See changes
git log --oneline -5             # Recent commits

# Claude
claude update                    # Check for updates
claude                           # Launch
Ctrl+C                           # Exit Claude
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Claude doesn't know project context | Run `/resume-work` first |
| Lost track of what was done | Check CLAUDE.md Session History or `docs/session-history.md` for older sessions |
| Starting fresh on old project | Run `/update-docs` to rebuild context |
| Too many questions in `/plan-feature` | Say "let's skip that" or "good enough" |
| `/code-cleanup` too aggressive | Only delete "Safe to Delete" items, or avoid `--aggressive` flag |
| `/code-review` reviewing too much | Use `--staged` or specify files instead of running with no args |
| Auto-memory out of date | Run `/update-docs` — it syncs stable facts automatically |
| CLAUDE.md too long | `/update-docs` auto-archives sessions >3 to `docs/session-history.md` |

---

## My Custom Commands Location

Commands are stored in:
```
~/Development/projects/claude-config/
├── .claude/
│   ├── agents/              # Subagent definitions
│   ├── scripts/             # Session startup scripts
│   │   ├── start-claude.sh          # Mac/Linux startup
│   │   └── start-claude.ps1        # Windows startup
│   ├── settings.local.json  # Shared Claude Code settings
│   └── skills/              # Skills (commands + references)
│       ├── architecture-review/
│       ├── code-cleanup/
│       ├── code-review/
│       ├── plan-feature/
│       ├── resume-work/
│       └── update-docs/
├── .gitignore
├── Workflow.md              # This file
└── README.md
```

GitHub repo: `burak-maxitech/claude-config` (private)

Symlinked to: `~/.claude/skills`, `~/.claude/agents` (individual subdirectories)

---

## Version History

| Date | Changes |
|------|---------|
| Jan 2025 | Initial workflow created |
| | Added three-file documentation system (README, CLAUDE.md, docs/) |
| | Merged plan-feature and plan-feature-addon commands |
| | Integrated code-review and code-cleanup |
| | Set up GitHub sync across machines |
| Feb 2026 | Optimized all commands for Claude Opus 4.6 capabilities |
| | `/resume-work` — parallel doc reads, parallel git scans, auto-memory awareness, task hydration |
| | `/update-docs` — task list drain, session history archiving, auto-memory sync |
| | `/plan-feature` — parallel context loading, Plan Mode integration, task hydration from plan |
| | `/code-review` — git-aware diffing (uncommitted/staged/PR/last-commit), convention detection, enforced file:line refs |
| | `/code-cleanup` — parallel subagent scanning, summary dashboard, Quick Wins, scope filters (--code/--deps/--css/--aggressive) |
| | Added `docs/session-history.md` auto-archiving across all commands |
| | Added auto-memory integration across all commands |
| | Added TaskCreate/TaskUpdate live task tracking across workflow |
| Mar 2026 | Added startup scripts (`start-claude.sh`, `start-claude.ps1`) to automate session startup |
| | Replaced manual 8-step startup with single-command script (5 automated steps); shows tip to run `/resume-work` |
| Apr 2026 | Aligned with Opus 4.7 release (CC 2.1.111): added `effort: high` frontmatter to `/code-review` and `/plan-feature` for stronger reasoning on review/synthesis work |
| | Documented when to reach for built-in `/ultrareview` (high-risk pre-merge) vs custom `/code-review` (daily driver) in README |
| May 2026 | New `/architecture-review` skill — repo-wide complexity + refactor + perf audit, distinct from diff-scoped reviewers. Three guardrails: catalog-driven complexity-reducing refactors (not GoF pattern-mongering), reads intended architecture from CLAUDE.md/ADRs first, CCN delta sanity gate. Three new subagents (`arch-structure`, `arch-refactors`, `arch-performance`). |

---

*Last updated: May 2026*
