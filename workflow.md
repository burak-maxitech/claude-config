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
| **End Session** | `/update-docs` | Save progress & context |

---

## Daily Workflow

### Starting a Session on Mac

```bash
# 1. Open Terminal

# 2. Pull latest commands (in case you updated from another machine)
cd ~/Development/projects/claude-config && git pull && cd -

# 3. Verify config symlinks are in place
ls -d ~/.claude/skills ~/.claude/agents 2>/dev/null || echo "MISSING SYMLINKS — see Setup section"

# 4. Navigate to project
cd ~/projects/[project-name]

# 5. (Optional) Pull latest project changes
git pull

# 6. Check for Claude updates
claude update

# 7. Launch Claude Code
claude

# 8. Get up to speed
/resume-work
```

### Starting a Session on PC

```powershell
# 1. Open PowerShell or Terminal

# 2. Pull latest commands (in case you updated from another machine)
cd C:\Development\projects\claude-config; git pull; cd -

# 3. Verify config symlinks are in place
Get-ChildItem ~\.claude | Where-Object { $_.LinkType -eq "SymbolicLink" } | Format-Table Name, Target

# 4. Navigate to project
cd C:\Development\projects\[project-name]

# 5. (Optional) Pull latest project changes
git pull

# 6. Check for Claude updates
claude update

# 7. Launch Claude Code
claude

# 8. Get up to speed
/resume-work
```

### Quick Start with Startup Scripts

The startup scripts automate all the manual steps above into a single command:

**Mac/Linux:**
```bash
# With project name:
~/Development/projects/claude-config/.claude/scripts/start-claude.sh my-project

# Or interactive project picker:
~/Development/projects/claude-config/.claude/scripts/start-claude.sh
```

**Windows (PowerShell):**
```powershell
# With project name:
~\Development\projects\claude-config\.claude\scripts\start-claude.ps1 my-project

# Or interactive project picker:
~\Development\projects\claude-config\.claude\scripts\start-claude.ps1
```

**Tip:** Create a shell alias for even quicker access:
```bash
# Mac/Linux — add to ~/.bashrc or ~/.zshrc
alias claude-start="~/Development/projects/claude-config/.claude/scripts/start-claude.sh"
```
```powershell
# Windows — add to $PROFILE
function claude-start { & "$env:USERPROFILE\Development\projects\claude-config\.claude\scripts\start-claude.ps1" @args }
```

> **Windows first run:** You may need to unblock the script first:
> `Unblock-File "$env:USERPROFILE\Development\projects\claude-config\.claude\scripts\start-claude.ps1"`

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

---

## New Machine Setup

> **Why individual symlinks?** Claude Code stores config files in `~/.claude` (like `settings.local.json`, credentials, etc.) that would get overwritten if you symlinked the entire folder. Symlinking the subdirectories keeps your local config intact.

### Mac/Linux Setup

```bash
# 1. Clone the repo
cd ~/Development/projects  # or wherever you keep repos
git clone https://github.com/burak-maxitech/claude-config.git

# 2. Remove existing subdirectories (if they exist)
rm -rf ~/.claude/skills ~/.claude/agents

# 3. Symlink subdirectories individually
ln -s ~/Development/projects/claude-config/.claude/skills ~/.claude/skills
ln -s ~/Development/projects/claude-config/.claude/agents ~/.claude/agents

# 4. Verify
ls -la ~/.claude/ | grep "^l"
```

### Windows Setup (PowerShell 7+ as Administrator)

```powershell
# 1. Clone the repo
cd $env:USERPROFILE\Development\projects
git clone https://github.com/burak-maxitech/claude-config.git

# 2. Remove old symlinks (if they exist)
Remove-Item "$env:USERPROFILE\.claude\skills" -Force -ErrorAction SilentlyContinue
Remove-Item "$env:USERPROFILE\.claude\agents" -Force -ErrorAction SilentlyContinue

# 3. Create symlinks
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.claude\skills" -Target "$env:USERPROFILE\Development\projects\claude-config\.claude\skills"
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.claude\agents" -Target "$env:USERPROFILE\Development\projects\claude-config\.claude\agents"

# 4. Verify
Get-ChildItem "$env:USERPROFILE\.claude" | Where-Object { $_.LinkType -eq "SymbolicLink" } | Format-Table Name, Target
```

**Windows Notes:**
- Must run PowerShell as Administrator to create symlinks
- Do NOT symlink the entire `~/.claude` folder — it contains local config and credentials

### Syncing Changes

After Claude or you edit any files:
```bash
cd ~/Development/projects/claude-config   # Mac/Linux
cd $env:USERPROFILE\Development\projects\claude-config   # Windows (PowerShell)

git add .
git commit -m "Updated [what changed]"
git push
```

On other machines:
```bash
cd ~/Development/projects/claude-config   # Mac/Linux
cd $env:USERPROFILE\Development\projects\claude-config   # Windows (PowerShell)

git pull
```

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

---

*Last updated: March 2026*
