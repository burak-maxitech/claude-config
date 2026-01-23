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

### Starting a Session

```bash
# 1. Open Terminal

# 2. Pull latest commands (in case you updated from another machine)
cd ~/Development/projects/claude-config && git pull && cd -

# 3. Navigate to project
cd ~/projects/[project-name]

# 4. Check for Claude updates
claude update

# 5. Launch Claude Code
claude

# 6. Get up to speed
/resume-work
```

**What `/resume-work` does:**
- Reads CLAUDE.md for context
- Shows current status
- Identifies last session's work
- Recommends next task

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
- Auto-detects if greenfield or existing project
- Reads existing docs for context
- Asks 3-5 questions at a time
- Covers all edge cases before coding
- Updates CLAUDE.md with decisions

#### Code Quality Checks

```bash
# Review specific files
/code-review src/services/gmail_service.py

# Review recent changes
/code-review [files changed in this session]

# Find dead code and cleanup opportunities
/code-cleanup

# Or focus on specific area
/code-cleanup src/services/
```

**What `/code-review` does:**
- Checks correctness, security, performance
- Identifies bugs and edge cases
- Suggests improvements
- Acknowledges what's done well

**What `/code-cleanup` does:**
- Finds unused files and dead code
- Identifies unused dependencies
- Spots obsolete patterns
- Categorizes by safety (safe/likely safe/investigate)

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
- Updates CLAUDE.md with session history
- Records what was accomplished
- Updates status table
- Sets up context for next session

---

## Command Reference

### /resume-work

**When:** Start of every session

**Flags:**
- `/resume-work` - Standard summary
- `/resume-work deep` - Verbose mode, full details

**Output:** Status summary + recommended next task

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

**Output:** Exhaustive requirements gathered, then implementation

---

### /update-docs

**When:** End of every session (or after major milestones)

**Modes:**
- **CREATE** - Generates all docs from scratch
- **REFACTOR** - Splits monolithic README into three files
- **UPDATE** - Refreshes existing documentation

**Updates:**
- CLAUDE.md - Session history, status, next steps
- README.md - Project overview, setup
- docs/*.md - PRD and specifications

---

### /code-review

**When:** Before committing, or to check specific code

**Usage:**
```bash
/code-review src/file.py                 # Review specific file
/code-review src/services/               # Review directory
/code-review                             # Review recent changes
```

**Checks:**
- Correctness & bugs
- Security vulnerabilities
- Performance issues
- Maintainability
- Error handling
- Test coverage gaps

**Output:** Critical / Important / Suggestions / What's Good

---

### /code-cleanup

**When:** Periodic maintenance, before major releases

**Usage:**
```bash
/code-cleanup                            # Full codebase scan
/code-cleanup src/                       # Specific directory
```

**Finds:**
- Unused files and dead code
- Unused CSS classes
- Unused dependencies
- Obsolete patterns
- Configuration cruft
- Stale tests

**Output:** Safe to Delete / Likely Safe / Needs Investigation

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
├── README.md           # Public overview, setup guide
├── CLAUDE.md           # Session context (AI reads this first)
└── docs/
    ├── [project]-prd.md    # Full specifications
    └── [other docs].md     # Supporting documentation
```

| File | Purpose | Updated |
|------|---------|---------|
| **README.md** | Quick start, public docs | When features ship |
| **CLAUDE.md** | AI context, session tracking | Every session |
| **docs/*.md** | Detailed specs, PRD | When requirements change |

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

### Mac/Linux Setup

```bash
# 1. Clone the repo
cd ~/Development/projects  # or wherever you keep repos
git clone https://github.com/burak-maxitech/claude-config.git

# 2. Symlink to Claude's directory
ln -s ~/Development/projects/claude-config/commands ~/.claude/commands

# 3. Verify
ls ~/.claude/commands/
```

### Windows Setup

```cmd
# 1. Open Command Prompt or PowerShell as Administrator (required for symlinks)

# 2. Clone the repo (adjust path to where you keep projects)
cd %USERPROFILE%\Development\projects
git clone https://github.com/burak-maxitech/claude-config.git

# 3. Create symlink (note: link comes before target on Windows)
mklink /D "%USERPROFILE%\.claude\commands" "%USERPROFILE%\Development\projects\claude-config\commands"

# 4. Verify
dir "%USERPROFILE%\.claude\commands"
```

**Windows Notes:**
- Must run as Administrator to create symlinks
- Use `\` not `/` for paths
- Symlink syntax is reversed: `mklink /D [link] [target]`

### Syncing Changes

After Claude or you edit any files:
```bash
cd ~/Development/projects/claude-config   # Mac/Linux
cd %USERPROFILE%\Development\projects\claude-config   # Windows

git add .
git commit -m "Updated [what changed]"
git push
```

On other machines:
```bash
cd ~/Development/projects/claude-config   # Mac/Linux
cd %USERPROFILE%\Development\projects\claude-config   # Windows

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
| Lost track of what was done | Check CLAUDE.md Session History |
| Starting fresh on old project | Run `/update-docs` to rebuild context |
| Too many questions in `/plan-feature` | Say "let's skip that" or "good enough" |
| `/code-cleanup` too aggressive | Only delete "Safe to Delete" items |

---

## My Custom Commands Location

Commands are stored in:
```
~/Development/projects/claude-config/
├── commands/
│   ├── resume-work.md
│   ├── update-docs.md
│   ├── plan-feature.md
│   ├── code-review.md
│   └── code-cleanup.md
├── workflow.md          # This file
└── README.md
```

GitHub repo: `burak-maxitech/claude-config` (private)

Symlinked to: `~/.claude/commands`

---

## Version History

| Date | Changes |
|------|---------|
| Jan 2025 | Initial workflow created |
| | Added three-file documentation system (README, CLAUDE.md, docs/) |
| | Merged plan-feature and plan-feature-addon commands |
| | Integrated code-review and code-cleanup |
| | Set up GitHub sync across machines |

---

*Last updated: January 2025*
