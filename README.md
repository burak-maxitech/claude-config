# Claude Config

My personal Claude Code configuration: custom commands, skills, subagents, and workflow guide.

## Contents
```
claude-config/
├── .claude/                           # Single symlink → ~/.claude
│   ├── agents/                        # Subagent definitions (Sonnet-routed)
│   │   ├── cleanup-files-code.md
│   │   ├── cleanup-deps-config.md
│   │   └── cleanup-styles-tests.md
│   ├── commands/                      # Custom slash commands
│   │   ├── resume-work.md
│   │   ├── update-docs.md
│   │   ├── plan-feature.md
│   │   └── code-review.md
│   └── skills/                        # Skills (commands + bundled references)
│       └── code-cleanup/
│           ├── SKILL.md
│           └── references/
│               ├── scan-files-code.md
│               ├── scan-deps-config.md
│               └── scan-styles-tests.md
├── workflow.md                        # Personal workflow guide
└── README.md
```

## Setup on a New Machine
```bash
# 1. Clone this repo
cd ~
git clone git@github.com:Burkico/claude-config.git

# 2. Symlink the entire .claude directory
ln -s ~/Development/projects/claude-config/.claude ~/.claude
```

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

See `workflow.md` for full usage guide.