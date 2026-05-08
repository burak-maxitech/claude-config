# Claude Config

My personal Claude Code configuration: custom commands, skills, subagents, and workflow guide.

## Contents
```
claude-config/
├── .claude/                           # Subdirs symlinked into ~/.claude
│   ├── agents/                        # Subagent definitions (Sonnet-routed)
│   │   ├── arch-performance.md
│   │   ├── arch-refactors.md
│   │   ├── arch-structure.md
│   │   ├── cleanup-deps-config.md
│   │   ├── cleanup-files-code.md
│   │   └── cleanup-styles-tests.md
│   ├── scripts/                       # Session startup scripts
│   │   ├── start-claude.sh            # Mac/Linux startup
│   │   └── start-claude.ps1           # Windows startup (PowerShell)
│   ├── settings.local.json            # Shared Claude Code settings
│   └── skills/                        # Skills (commands + bundled references)
│       ├── architecture-review/
│       │   ├── SKILL.md
│       │   └── references/
│       │       ├── fix-mode.md
│       │       ├── plan-mode.md
│       │       ├── refactor-catalog.md
│       │       ├── report-template.md
│       │       ├── scale-strategy.md
│       │       ├── scan-performance.md
│       │       ├── scan-refactors.md
│       │       └── scan-structure.md
│       ├── code-cleanup/
│       │   ├── SKILL.md
│       │   └── references/
│       │       ├── scan-deps-config.md
│       │       ├── scan-files-code.md
│       │       └── scan-styles-tests.md
│       ├── code-review/
│       │   ├── SKILL.md
│       │   └── references/
│       │       ├── output-format.md
│       │       ├── review-checklist.md
│       │       └── security-deep-dive.md
│       ├── plan-feature/
│       │   ├── SKILL.md
│       │   └── references/
│       │       ├── interview-rules.md
│       │       ├── mode-greenfield.md
│       │       ├── mode-existing.md
│       │       └── plan-and-tasks.md
│       ├── resume-work/
│       │   ├── SKILL.md
│       │   └── references/
│       │       ├── summary-template.md
│       │       └── task-hydration.md
│       └── update-docs/
│           ├── SKILL.md
│           └── references/
│               ├── claude-md-sections.md
│               ├── doc-structure-rules.md
│               ├── mode-create.md
│               ├── mode-refactor.md
│               ├── mode-update.md
│               └── verification-checklists.md
├── docs/                              # Reference files (overflow from CLAUDE.md)
│   ├── completed-work.md
│   ├── key-decisions.md
│   └── session-history.md
├── .gitignore
├── CLAUDE.md                          # AI session context
├── README.md                          # This file
└── Workflow.md                        # Personal workflow guide
```

## Setup on a New Machine

> **Why individual symlinks?** Claude Code stores config files in `~/.claude` (like `settings.local.json`, credentials, etc.) that would get overwritten if you symlinked the entire folder. Symlinking the subdirectories keeps your local config intact.

### Mac/Linux

```bash
# 1. Clone this repo
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

### Windows (PowerShell 7+ as Administrator)

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

## Quick Start

After setup, create a shell alias for quick access:

```bash
# Mac/Linux — run once, then restart terminal (or run: source ~/.zshrc)
echo 'alias cc="~/Development/projects/claude-config/.claude/scripts/start-claude.sh"' >> ~/.zshrc
```
```powershell
# Windows — run once, then restart PowerShell
Add-Content $PROFILE 'function cc { & "$env:USERPROFILE\Development\projects\claude-config\.claude\scripts\start-claude.ps1" @args }'
```

> **Mac/Linux first run:** Make the script executable first:
> `chmod +x ~/Development/projects/claude-config/.claude/scripts/start-claude.sh`

> **Windows first run:** You may need to unblock the script first:
> `Unblock-File "$env:USERPROFILE\Development\projects\claude-config\.claude\scripts\start-claude.ps1"`

Then start any session with:
```bash
cc my-project    # launch directly
cc               # interactive project picker
```

The script syncs config, verifies symlinks, pulls project changes, checks for Claude updates, and launches Claude Code.

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
| `/resume-work` | Start session - get up to speed | Skill |
| `/plan-feature` | Interview before building features | Skill |
| `/code-review` | Review code quality (lightweight, in-session, with `--security`/`--verify`/`--fix`) | Skill |
| `/code-cleanup` | Find dead code & cruft (parallel subagents) | Skill |
| `/architecture-review` | Repo-wide architecture audit — complexity hotspots, refactor opportunities, perf suspects (parallel subagents, with `--plan`/`--fix`/`--map`/`--full-scan`) | Skill |
| `/update-docs` | End session - save progress | Skill |

**Skills** are directories in `.claude/skills/` that bundle reference files, use YAML frontmatter for tool permissions, and can dispatch subagents.

> **When to reach for `/ultrareview` instead of `/code-review`.** Claude Code 2.1.111 ships a built-in `/ultrareview` that runs 5+ verifying subagents in the cloud (10–20 min, scales to 20 agents). Use it for high-risk pre-merge reviews — auth rewrites, payment flows, database migrations. The custom `/code-review` skill is the lighter daily-driver: in-session, fast, with `--security` (OWASP), `--verify` (run tests), and `--fix` (auto-fix simple findings) modes that `/ultrareview` doesn't have.

> **Picking among the review skills.** All five operate on different scopes:
>
> | Skill | Scope | When |
> |-------|-------|------|
> | `/code-review` | diff or commit | per-commit / per-PR quality, daily driver |
> | `/simplify` | recent changes | post-hoc cleanup of work just done |
> | `/ultrareview` | PR (cloud) | high-risk pre-merge verification (auth, payments, migrations) |
> | `/code-cleanup` | whole repo | deletion-focused — dead code, unused deps, stale config |
> | `/architecture-review` | whole repo | structural audit — complexity hotspots, refactor opportunities, perf suspects |
>
> Useful chain on an unfamiliar repo: `/code-cleanup` → `/architecture-review` → `/architecture-review --plan` → `/plan-feature` per phase.

## Subagents

The `.claude/agents/` folder contains subagent definitions used by skills. These run on Sonnet for cost efficiency and have scoped tool permissions. Skills dispatch them automatically via the Task tool, and you can also reference them by name in `@`-mention typeahead inside the REPL (added in Claude Code 2.1.89).

| Agent | Used By | Purpose |
|-------|---------|---------|
| `cleanup-files-code` | `/code-cleanup` | Scans for unused files and dead code |
| `cleanup-deps-config` | `/code-cleanup` | Scans for unused deps and config cruft |
| `cleanup-styles-tests` | `/code-cleanup` | Scans for unused CSS and stale tests |
| `arch-structure` | `/architecture-review` | Cyclomatic + cognitive complexity hotspots, coupling, layering violations, circular deps |
| `arch-refactors` | `/architecture-review` | Catalog-driven complexity-reducing refactor opportunities (cites entry IDs) |
| `arch-performance` | `/architecture-review` | High-precision performance findings (N+1, sync I/O in async, accidental O(n²), hot-loop invariants) |

## Interop with Claude Code 2.1 features

These skills are standalone `.claude/` configuration, which is the approach [the official docs recommend](https://code.claude.com/docs/en/plugins#when-to-use-plugins-vs-standalone-configuration) for personal workflows. They coexist happily with installed marketplace plugins — no migration needed.

A few harness-level features worth knowing about when using these skills:

- **Gating destructive `--fix` runs in CI.** `code-cleanup --fix` and `code-review --fix` are intentionally not self-gating (see the note in each SKILL.md). If you run them headlessly via `claude -p` and want an external approval step, configure a `PreToolUse` hook in `~/.claude/settings.json` scoped via the `if` field (added in 2.1.85) to the patterns you want to guard — e.g. `"if": "Bash(rm:*)"` or `"if": "Edit(*)"` — and return `"permissionDecision": "defer"`. The session exits with `stop_reason: "tool_deferred"`; resume via `claude -p --resume <session-id>`. Note: `defer` only works when the turn makes a single tool call — useful for a `rm` guard, not for orchestrating a multi-step `--fix` run. See [hooks docs](https://code.claude.com/docs/en/hooks) for the full decision flow and the `if` field spec.
- **Auto mode compatibility** (requires 2.1.83+; Max/Team/Enterprise/API plan; Opus 4.6/4.7 or Sonnet 4.6; not available on Pro). Auto mode (`defaultMode: "auto"`) uses a classifier to auto-approve actions without prompts. On entering auto mode, broad allow rules like `Bash(*)` or `Bash(python*)` are dropped, but narrow patterns like `Bash(npm test)` carry over. The 5 skills in this repo all declare narrow `allowed-tools` (`Bash(git:*)`, `Bash(npm:*)`, `Bash(find:*)`, etc.), so `--fix`, `--verify`, and `deep` all work under auto mode. If the classifier denies something unexpectedly, configure a `PermissionDenied` hook (added 2.1.89) that returns `{"retry": true}` to tell the model it may retry. See [permission modes](https://code.claude.com/docs/en/permission-modes) for the full spec.
- **`disableSkillShellExecution`** (added 2.1.91). Hardens the harness by blocking inline shell from skills and slash commands. **Do not enable this here** — `code-cleanup --fix`, `code-review --verify`, and `resume-work deep` all depend on shell execution and will break. Leave OFF. (The `start-claude` scripts warn if this flag is on in `~/.claude/settings.json`.)
- **Plugin `bin/` on PATH** (added 2.1.91). If you install a marketplace plugin that ships `bin/check` or `bin/test`, `resume-work deep` picks it up automatically in the health check detection ladder.
- **MCP `maxResultSizeChars`** (added 2.1.91). If a future `code-review` run hits an MCP-backed file reader that truncates, the MCP server can set `_meta["anthropic/maxResultSizeChars"]` up to 500K per tool to return fuller context in one call.
- **MCP server setup.** Add servers via `claude mcp add --transport {http|sse|stdio} <name> <target>`. Three scopes are available: **local** (default, personal-to-this-project, stored in `~/.claude.json`), **project** (team-shared via `.mcp.json` at repo root), and **user** (all your projects, stored in `~/.claude.json`). Project scope is the one to use when a server should travel with the repo. Tool-search deferral keeps context cost low even with multiple servers, so the practical ceiling is tool-menu clarity and permission-prompt volume, not token budget. See the [MCP docs](https://code.claude.com/docs/en/mcp) for transport-specific setup.

## Documentation

| File | Purpose |
|------|---------|
| [README.md](README.md) | Public overview, setup instructions (this file) |
| [CLAUDE.md](CLAUDE.md) | AI session context, status tracking, architecture |
| [Workflow.md](Workflow.md) | Detailed personal workflow guide |
| [docs/](docs/) | Reference files (session history, decisions, completed work) |

See `Workflow.md` for full usage guide.