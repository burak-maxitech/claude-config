# CLAUDE.md

Last Updated: 2026-04-11 (Session 13)

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
| CI gating documented, not implemented in-skill | `defer` PermissionDecision only works for single-tool-call turns and is meant for SDK/subprocess callers; skills can't self-gate. Document the PreToolUse recipe in README instead of adding a `--gated` flag. |
| Plugin `bin/` helpers in resume-work health check | CC 2.1.91 puts enabled plugins' `bin/` on `$PATH`; prefer plugin-provided smoke tests over the generic `package.json → Makefile → pyproject.toml → Cargo.toml` ladder. |
| Standalone skills + installed marketplace plugins coexist | Claude Code docs explicitly recommend standalone `.claude/` for personal config and plugins for sharing. No migration needed; the symlink model is the recommended personal-workflow pattern. |
| Verify every external-repo claim before shipping | Session 13 research on shanraisshan/claude-code-best-practice surfaced 14 candidate patterns. Spot-verification via direct raw.githubusercontent.com fetches found the catalog had conflated skills `paths:` with `.claude/rules/` `paths:`, and that "curation/start narrow" and "/compact at 50%" were community wisdom, not Anthropic guidance. Ship only what docs.claude.com confirms; soften or drop the rest. |

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

### Last Session (Session 13) - 2026-04-11
- Reviewed external best-practice repo (shanraisshan/claude-code-best-practice, actively maintained) and catalogued 14 candidate patterns via an Explore agent.
- Spot-verified load-bearing claims by direct raw.githubusercontent.com fetches + docs.claude.com; two claims were fabricated (skills `paths:` frontmatter; "/compact at 50%" as Anthropic guidance) and were dropped or softened before shipping.
- Shipped 3 documentation commits: README MCP server setup bullet (verified scopes: local/project/user; `.mcp.json` for project scope; `claude mcp add` CLI); workflow mid-session context hygiene subsection (general "compact earlier rather than later" guidance); workflow `/loop` reference with the 3-day auto-expire caveat.
- Skipped 11 patterns with reasons recorded in `docs/key-decisions.md`: full hooks.py dispatcher, agent-scoped hooks, Command→Agent→Skill labeling, skills `paths:`/`effort:`/`context:`, subagent `memory:`, multiple CLAUDE.md hierarchy, deny-first settings, etc.
- **Session 12 `defer` hook dogfood still pending** — explicitly deferred from this session so it runs as its own isolated test, unbundled from any new hook infrastructure.
