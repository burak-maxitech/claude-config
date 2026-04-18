# CLAUDE.md

Last Updated: 2026-04-17 (Session 16)

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
| `plan-feature` Step 0 triviality check + `AskUserQuestion`-driven interview | Session 14 audit against code.claude.com/docs/en/best-practices. Doc explicitly recommends `AskUserQuestion` for the interview pattern and explicitly tells users to skip planning for one-sentence changes ("typo, log line, rename"). Step 0 returns control to the user before the interview overhead; interview itself uses multi-choice prompts with an "Other / explain" escape. Falls back to numbered Q&A when `AskUserQuestion` is unavailable. |
| Surface `/rewind` in destructive `--fix` output | Same Session 14 audit. Doc treats checkpointing as a core safety net for risky operations. Both `code-cleanup --fix` and `code-review --fix` now end with a one-liner pointing the user at `Esc Esc` / `/rewind`. For `code-cleanup`, the existing `git branch -D` instruction stays as the coarse-grained option and `/rewind` is added for finer-grained per-edit undo. |
| Per-skill `effort:` frontmatter tuning | Sessions 15-16. Reasoning-heavy skills on `effort: high`: `/code-review`, `/plan-feature`. Mechanical skills on `effort: low`: `/update-docs`, `/resume-work` (added Session 16 after ~20min real-project run). `/code-cleanup` orchestrator stays at session default — heavy work lives in its Sonnet-pinned subagents. Frontmatter scope is per-invocation; auto-reverts to session default when the skill returns. |
| Parallel batch reads + single `git log` in `/update-docs` Parts 3 and 6 | Session 16. Part 3 now pre-loads all `docs/*.md` in a single parallel-Read turn before editing; Part 6 rollup uses one pre-fetched `git log` across the full compressible date range instead of per-session calls. Pure wins — no functionality change, only faster. Addresses the ~20min user-reported run. |
| Keep custom `/code-review`; position `/ultrareview` as complementary | Session 15. Built-in `/ultrareview` (CC 2.1.111) runs 5-20 verifying subagents in cloud, 10-20min — best for high-risk pre-merge (auth, payments, migrations). Custom skill is faster, in-session, and has `--security`/`--verify`/`--fix` modes that `/ultrareview` lacks. Documented the when-to-use-which split in README. |
| Dropped Session 12 `defer` hook dogfood | Session 15. Carried forward 12→13→14→15. Recipe in README:177 remains untested but documented; user accepted the small risk that it's subtly wrong rather than spend a session verifying. Removed the carry-forward bullet from CLAUDE.md so it stops surfacing in `/resume-work`. |
| Session-history rollup pattern | Session 15. `docs/session-history.md` auto-compresses sessions older than the 5 most recent into one-liners with commit hashes; full prose preserved in git. Implemented as Part 6 in `update-docs/mode-update.md` with `--skip-rollup` escape and a Step 6.2 first-run confirmation prompt (rollup-format note acts as per-project sentinel). Keeps the file bounded across all projects without surprising legacy ones. |

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

### Last Session (Session 16) - 2026-04-17
- **User reported `/update-docs` taking ~20 min on a real project** — audited the skill for perf wins without losing functionality.
- **Added `effort: low` to `/update-docs` and `/resume-work`.** Mechanical work (text shuffling, git queries, template filling) doesn't need Opus-level reasoning. Frontmatter-scoped: auto-reverts when the skill returns, so no in-skill toggling needed.
- **Parallelized `mode-update.md` Parts 3 and 6.** New Part 3.0 preamble batch-reads all `docs/*.md` in a single parallel turn before edits; Part 6.3 step 2 pre-fetches one `git log` across the full compressible date range instead of one per session.
- **Kept `/code-cleanup` orchestrator at session default** per user — heavy work is in its Sonnet subagents.
- **Updated Key Decisions** — prior "mechanical skills keep session default" guidance superseded by the two new `effort: low` pins; added a row for the Part 3/Part 6 parallelization.
