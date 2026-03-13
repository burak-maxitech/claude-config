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
