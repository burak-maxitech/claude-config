# Claude Config

My personal Claude Code configuration: custom commands, skills, subagents, and workflow guide.

## Contents
```
claude-config/
├── .claude/                           # Subdirs symlinked into ~/.claude
│   ├── agents/                        # Subagent definitions (Sonnet-routed)
│   │   ├── cleanup-deps-config.md
│   │   ├── cleanup-files-code.md
│   │   └── cleanup-styles-tests.md
│   ├── commands/                      # Custom slash commands
│   │   ├── code-review.md
│   │   ├── plan-feature.md
│   │   ├── resume-work.md
│   │   └── update-docs.md
│   ├── settings.local.json            # Shared Claude Code settings
│   └── skills/                        # Skills (commands + bundled references)
│       └── code-cleanup/
│           ├── SKILL.md
│           └── references/
│               ├── scan-deps-config.md
│               ├── scan-files-code.md
│               └── scan-styles-tests.md
├── .gitignore
├── Workflow.md                        # Personal workflow guide
└── README.md
```

## Setup on a New Machine

> **Why individual symlinks?** Claude Code stores config files in `~/.claude` (like `settings.local.json`, credentials, etc.) that would get overwritten if you symlinked the entire folder. Symlinking the three subdirectories keeps your local config intact.

### Mac/Linux

```bash
# 1. Clone this repo
cd ~/Development/projects  # or wherever you keep repos
git clone https://github.com/burak-maxitech/claude-config.git

# 2. Remove existing subdirectories (if they exist)
rm -rf ~/.claude/commands ~/.claude/skills ~/.claude/agents

# 3. Symlink subdirectories individually
ln -s ~/Development/projects/claude-config/.claude/commands ~/.claude/commands
ln -s ~/Development/projects/claude-config/.claude/skills ~/.claude/skills
ln -s ~/Development/projects/claude-config/.claude/agents ~/.claude/agents

# 4. Verify
ls -la ~/.claude/ | grep "^l"
```

### Windows (PowerShell 7+ as Administrator)

```powershell
# 1. Clone the repo
cd $env:USERPROFILE\Development\projects
git clone https://github.com/burak-maxitech/claude-config.git

# 2. Remove old symlinks (if they exist)
Remove-Item "$env:USERPROFILE\.claude\commands" -Force -ErrorAction SilentlyContinue
Remove-Item "$env:USERPROFILE\.claude\skills" -Force -ErrorAction SilentlyContinue
Remove-Item "$env:USERPROFILE\.claude\agents" -Force -ErrorAction SilentlyContinue

# 3. Create symlinks
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.claude\commands" -Target "$env:USERPROFILE\Development\projects\claude-config\.claude\commands"
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.claude\skills" -Target "$env:USERPROFILE\Development\projects\claude-config\.claude\skills"
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.claude\agents" -Target "$env:USERPROFILE\Development\projects\claude-config\.claude\agents"

# 4. Verify
Get-ChildItem "$env:USERPROFILE\.claude" | Where-Object { $_.LinkType -eq "SymbolicLink" } | Format-Table Name, Target
```

**Windows Notes:**
- Must run PowerShell as Administrator to create symlinks
- Do NOT symlink the entire `~/.claude` folder — it contains local config and credentials

## Syncing Changes

After Claude or you edit any files:
```bash
cd ~/Development/projects/claude-config
git add .
git commit -m "Updated [what changed]"
git push
```

On other machines:
```bash
cd ~/Development/projects/claude-config
git pull
```

## Commands

| Command | Purpose | Format |
|---------|---------|--------|
| `/resume-work` | Start session - get up to speed | Command |
| `/plan-feature` | Interview before building features | Command |
| `/code-review` | Review code quality | Command |
| `/code-cleanup` | Find dead code & cruft (parallel subagents) | Skill |
| `/update-docs` | End session - save progress | Command |

**Commands** are single markdown files in `.claude/commands/`. **Skills** are directories in `.claude/skills/` that can bundle reference files, use YAML frontmatter for tool permissions, and dispatch subagents.

## Subagents

The `.claude/agents/` folder contains subagent definitions used by skills. These run on Sonnet for cost efficiency and have scoped tool permissions. They are not user-invocable — skills dispatch them automatically via the Task tool.

| Agent | Used By | Purpose |
|-------|---------|---------|
| `cleanup-files-code` | `/code-cleanup` | Scans for unused files and dead code |
| `cleanup-deps-config` | `/code-cleanup` | Scans for unused deps and config cruft |
| `cleanup-styles-tests` | `/code-cleanup` | Scans for unused CSS and stale tests |

See `Workflow.md` for full usage guide.