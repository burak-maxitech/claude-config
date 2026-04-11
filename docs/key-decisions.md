# Key Decisions

> Full decision log. Referenced from [CLAUDE.md](../CLAUDE.md).

| Decision | Rationale |
|----------|-----------|
| Symlink subdirectories (not entire ~/.claude folder) | Claude Code stores credentials and local config in ~/.claude that would be overwritten by a full symlink |
| Skills format (SKILL.md + references/) | Bundles command logic with supporting docs; YAML frontmatter controls tool permissions |
| Subagents run on Sonnet | Cost efficiency — subagents do scanning work that doesn't need Opus reasoning |
| Parallel scanning in /code-cleanup | Launch 3 subagents simultaneously to scan deps, files, and styles in parallel |
| Lean CLAUDE.md with overflow to reference files | Keep CLAUDE.md under ~17k chars; detailed lists go to docs/*.md reference files |
| Three-file doc structure (README + CLAUDE.md + docs/) | README for public overview, CLAUDE.md for AI session context, docs/ for detailed references |
| Auto-memory sync via /update-docs | Stable project facts synced to ~/.claude/projects/.../memory/ for instant context in future sessions |
| Task hydration via TaskCreate | /resume-work and /plan-feature hydrate CLAUDE.md tasks into live task tracker |
| Plan Mode integration in /plan-feature | Uses EnterPlanMode/ExitPlanMode for formal plan approval before coding begins |
| Session history archiving (>3 sessions) | /update-docs auto-archives old sessions to docs/session-history.md to keep CLAUDE.md lean |
| Python import-name lookup table in scan-deps-config | Many PyPI packages have different import names (e.g., Pillow→PIL); hardcoded table reduces false positives |
| Batch git log for one-off script detection | Per-file git log is too slow on large repos; single batch command for scripts/tools/migrations |
| Conservative media query flagging | Media queries are easy to misjudge statically; default to needs_investigation risk level |
| --dry-run mode for /code-cleanup | Let users preview cleanup impact without deleting anything; builds trust before destructive operations |
| --aggressive only deletes with --fix | Prevent accidental deletions; --aggressive alone is cosmetic reclassification in the report |
| Phase gating in /plan-feature | Each phase must pass tests and commit before next phase starts; creates rollback-friendly checkpoints |
| Test types per phase (unit/integration/e2e) | Explicit test type expectations per phase prevent gaps in coverage and over-testing |
| Commit per phase in /plan-feature | Descriptive commits at phase boundaries enable clean rollback if later phases fail |
| Context management reminder before implementation | Long interviews bloat context; /compact before coding preserves plan while freeing space |
| Rollback strategy required in all plans | Both greenfield and existing modes must specify rollback approach per phase |
| --verify mode for /code-review | Run tests/lint after review to validate findings; reduces false positives (official Claude docs #1 recommendation) |
| --security deep dive via OWASP Top 10 | Standard security scan is surface-level; dedicated checklist for thorough security audits |
| Git blame context for critical findings | Understanding intent behind code prevents flagging deliberate tradeoffs as bugs |
| Large diff guard (500/1000 lines) | Large reviews exhaust context; warn and suggest chunking to maintain review quality |
| --fix auto-fix in /code-review | Simple findings (unused imports, formatting) can be safely auto-fixed; never auto-fix logic or security issues |
| Bidirectional task integrity check | Pre-hydration stale task check in /resume-work + post-drain validation in /update-docs prevents silent task data loss between sessions |
| Context freshness detection in /resume-work | Compare CLAUDE.md "Last Updated" date vs latest git commit; warn user if docs are stale and suggest /update-docs |
| Commit checkpoint in /update-docs (Part 5) | Prompt to commit after all docs are updated; never auto-commit; --skip-commit flag to suppress for scripted workflows |
| Compact guidance after resume-work and update-docs | Both skills consume significant context; suggest /compact afterward to free space before real work |
| Quick health check in /resume-work deep mode | Detect and run test/build commands (package.json, Makefile, etc.) to catch broken state before starting to code; only in deep mode to keep default fast |
| Startup scripts in .claude/scripts/ | Single-command session startup replacing 8 manual steps; cross-platform (bash + PowerShell); includes interactive project picker |
| Scripts don't auto-run /resume-work | User controls when to run /resume-work; avoids forced context load on every launch; tip message shown instead |
| Setup instructions in README.md only | One-time setup (clone, symlinks, alias) belongs in README.md; Workflow.md links to it to avoid duplication between files |
| Alias name `cc` for startup script | Short, memorable alias; user preference over longer `claude-start` |
| Don't filter claude-config from project picker | User may want to work on the config repo itself; no reason to hide it |
| CI gating documented, not implemented in-skill | Researched `--gated` flag for code-cleanup and code-review during CC 2.1 adoption. Discovered (from the official hooks doc) that `defer` PermissionDecision only works when the turn makes a single tool call, and is specifically designed for external SDK/subprocess callers that run `claude -p` and resume via `claude -p --resume`. A skill cannot self-emit defer. Correct integration is a harness-level `PreToolUse` hook in `~/.claude/settings.json` matching destructive bash patterns. Documented as a recipe in README instead of adding a flag. |
| Plugin `bin/` helpers in resume-work deep-mode health check | Claude Code 2.1.91 puts enabled plugins' `bin/` directories on `$PATH` as bare commands. resume-work's deep-mode health check now prefers plugin-shipped `bin/check`, `bin/test`, or `bin/ci` scripts over the generic `package.json → Makefile → pyproject.toml → Cargo.toml` detection ladder when available, since plugin authors have chosen the canonical command for their project. |
| Standalone `.claude/` skills and installed marketplace plugins coexist | User already has `frontend-design@claude-code-plugins` and `feature-dev@claude-code-plugins` installed at `~/.claude/plugins/`. The official plugins doc explicitly says standalone `.claude/` is the recommended approach for personal customizations and plugins are for sharing — so the symlink model is not legacy, it's the documented personal-workflow pattern. No migration needed. |
| Kept subagents on Sonnet despite Opus 4.6 availability | CC 2.1 shipped expanded Opus 4.6 subagent capacity with 1M context, which was considered as a candidate upgrade during Session 12 feature adoption. Rejected because it reverses the existing "Subagents on Sonnet — cost efficiency" decision. Only revisit if a real cleanup scan hits Sonnet context limits. |
| Drop speculative agent "decline markers" | The Session 12 plan proposed adding machine-readable "category declined" markers to the three cleanup-*.md subagents. Dropped during implementation because the current agents return structured findings, not status envelopes — there's no clean decline path in the existing agent model, and adding instructions the agents don't follow would be dead weight. |
| Verify web-sourced feature claims before editing | Session 12 research agent reported 11 candidate features from CC 2.1 releases. Before any skill edit, each claim was verified against the official hooks doc, plugins doc, and GitHub CHANGELOG. Two claims (`showThinkingSummaries`, subagent MCP inheritance fix) could not be verified and were dropped. Adopted as a general rule: any feature sourced from web research gets verified against primary sources before becoming a skill edit. |
