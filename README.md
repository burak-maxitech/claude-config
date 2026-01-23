# Claude Config

My personal Claude Code configuration: custom commands and workflow guide.

## Contents
```
claude-config/
├── commands/           # Custom slash commands
│   ├── resume-work.md
│   ├── update-docs.md
│   ├── plan-feature.md
│   ├── code-review.md
│   └── code-cleanup.md
├── workflow.md         # Personal workflow guide
└── README.md
```

## Setup on a New Machine
```bash
# 1. Clone this repo
cd ~
git clone git@github.com:Burkico/claude-config.git

# 2. Symlink commands to Claude's directory
ln -s ~/claude-config/commands ~/.claude/commands
```

## Syncing Changes

After Claude or you edit any files:
```bash
cd ~/claude-config
git add .
git commit -m "Updated [what changed]"
git push
```

On other machines:
```bash
cd ~/claude-config
git pull
```

## Commands

| Command | Purpose |
|---------|---------|
| `/resume-work` | Start session - get up to speed |
| `/plan-feature` | Interview before building features |
| `/code-review` | Review code quality |
| `/code-cleanup` | Find dead code & cruft |
| `/update-docs` | End session - save progress |

See `workflow.md` for full usage guide.
