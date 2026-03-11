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
