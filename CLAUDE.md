# CLAUDE.md

Last Updated: 2026-03-17 (Session 11)

## Project Overview

**claude-config** — Personal Claude Code configuration repo containing custom skills, subagents, and workflow documentation.

- **Repo:** [burak-maxitech/claude-config](https://github.com/burak-maxitech/claude-config) (private)
- **README.md** — Public overview, setup instructions, command reference
- **Workflow.md** — Detailed personal workflow guide (daily workflow, scenarios, tips)
- **docs/** — Reference files (session history, key decisions, completed work)

## Current Status

| Area | Status |
|------|--------|
| Skills (5) | Complete |
| Subagents (3) | Complete |
| Startup scripts | Complete |
| Mac/Linux setup | Complete |
| Windows setup | Complete |
| GitHub sync | Complete |
| Documentation | Complete |

## Completed

All 5 skills, 3 subagents, cross-platform setup, and documentation system are complete.

See [docs/completed-work.md](docs/completed-work.md) for full checklist.

## In Progress

Nothing currently in progress.

## Next Steps

1. Add more skills as new workflow needs emerge
2. Improve existing skill reference files based on usage patterns
3. Consider adding hooks for automated pre-commit workflows
4. Explore MCP server integration for external tool access

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Symlink subdirectories, not entire ~/.claude | Preserves local credentials and config |
| Skills format (SKILL.md + references/) | Bundles logic with docs; YAML frontmatter for permissions |
| Subagents on Sonnet | Cost efficiency for scanning work |
| Parallel scanning in /code-cleanup | 3 simultaneous subagents for speed |
| Lean CLAUDE.md with reference file overflow | Keep under ~17k chars; details in docs/*.md |
| Three-file doc structure | README (public), CLAUDE.md (AI context), docs/ (references) |
| Auto-memory sync via /update-docs | Stable facts persist across sessions |
| Task hydration via TaskCreate | Live task tracking from CLAUDE.md content |
| Plan Mode in /plan-feature | Formal approval before coding begins |
| Session archiving (>3 sessions) | Auto-archive to docs/session-history.md |
| --dry-run mode in /code-cleanup | Preview cleanup impact without deleting; builds user trust |
| --aggressive requires --fix to delete | Cosmetic reclassification only without --fix; prevents accidental deletions |
| Phase gating in /plan-feature | Tests + commit per phase; rollback-friendly checkpoints |
| --verify/--security/--fix in /code-review | Verification, OWASP deep dive, and auto-fix as opt-in modes |
| Git blame context for review findings | Understand intent before flagging; prevents false positives |
| Large diff guard in /code-review | Warn at 500+ lines, suggest chunking at 1000+ to preserve review quality |
| Bidirectional task integrity | Pre-hydration stale check + post-drain validation prevents silent task data loss |
| Context freshness detection in /resume-work | Compare CLAUDE.md date vs git commits; warn if docs are stale |
| Commit checkpoint in /update-docs | Prompt to commit after docs update; never auto-commit; --skip-commit to suppress |
| Compact guidance after both skills | Suggest /compact after resume-work and update-docs to free context |
| Health check in /resume-work deep mode | Run tests/build in deep mode to catch broken state before coding |
| Startup scripts (.claude/scripts/) | Single-command session startup replacing 8 manual steps; cross-platform |
| Scripts don't auto-run /resume-work | User controls when to run /resume-work; avoids forced context load on every launch |
| Setup instructions in README.md only | One-time setup (clone, symlinks, alias) belongs in README; Workflow.md links to it to avoid duplication |
| Don't filter claude-config from project picker | User may want to work on the config repo itself |

> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)

## Architecture Summary

```
claude-config/
├── .claude/
│   ├── agents/              # Subagent definitions (Sonnet-routed)
│   │   ├── cleanup-deps-config.md
│   │   ├── cleanup-files-code.md
│   │   └── cleanup-styles-tests.md
│   ├── scripts/             # Session startup scripts
│   │   ├── start-claude.sh          # Mac/Linux
│   │   └── start-claude.ps1        # Windows (PowerShell)
│   ├── settings.local.json  # Shared Claude Code settings
│   └── skills/              # Skills (SKILL.md + references/)
│       ├── code-cleanup/
│       ├── code-review/
│       ├── plan-feature/
│       ├── resume-work/
│       └── update-docs/
├── docs/                    # Reference files (overflow from CLAUDE.md)
│   ├── completed-work.md
│   ├── key-decisions.md
│   └── session-history.md
├── .gitignore
├── CLAUDE.md                # This file — AI session context
├── README.md                # Public overview
└── Workflow.md              # Personal workflow guide
```

**Symlink approach:** Only `.claude/skills/` and `.claude/agents/` are symlinked into `~/.claude/` on each machine. This preserves local credentials and settings while sharing skills and agents across machines via Git.

**Skills** are directories containing `SKILL.md` (main logic with YAML frontmatter) and a `references/` folder with supporting documents. They are user-invocable via `/skill-name`.

**Subagents** are markdown files in `.claude/agents/` dispatched by skills (not user-invocable). They run on Sonnet for cost efficiency and have scoped tool permissions.

## Known Issues / Blockers

None currently.

## Environment Variables

None required. This is a pure configuration repo — no runtime dependencies or secrets.

## Session History

> Full history: [docs/session-history.md](docs/session-history.md)

### Last Session (Session 11) - 2026-03-17
- Resumed work after 4-day break, reviewed current state
- Reviewed plan-feature skill's `disable-model-invocation` setting (currently `true`)
- No code changes made this session
