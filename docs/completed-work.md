# Completed Work

> Full checklist of completed tasks. Referenced from [CLAUDE.md](../CLAUDE.md).

---

## Skills
- [x] `/resume-work` — Session startup with parallel doc reads, git scans, auto-memory, task hydration
- [x] `/plan-feature` — Feature interview with greenfield/existing modes, Plan Mode, task hydration
- [x] `/update-docs` — Session end with task drain, session archiving, auto-memory sync, CREATE/REFACTOR/UPDATE modes
- [x] `/code-review` — Code review with auto-detect (uncommitted/staged/PR/last-commit), convention scanning, file:line refs
- [x] `/code-cleanup` — Parallel subagent scanning with summary dashboard, Quick Wins, scope filters
- [x] `/code-cleanup` enhancements — Added `--dry-run` mode, clarified `--aggressive` behavior, added `Bash(gh:*)` permission, improved description to distinguish from `/simplify`
- [x] `scan-deps-config` subagent — Added Python package→import name lookup table (30+ common mismatches)
- [x] `scan-files-code` subagent — Optimized one-off script detection to batch `git log` instead of per-file
- [x] `scan-styles-tests` subagent — Made media query dead code detection more conservative (default risk: needs_investigation)
- [x] `/plan-feature` enhancements — Phase gating with verification, test types per phase, commit after each phase, context management reminder, rollback strategy in plan template
- [x] `/code-review` enhancements — Added `--verify` (run tests/lint), `--security` (OWASP Top 10 deep dive), `--fix` (auto-fix simple issues), git blame context for findings, large diff guard (500/1000 line thresholds)
- [x] `security-deep-dive.md` — New reference file with full OWASP Top 10 checklist for `/code-review --security`
- [x] `/resume-work` enhancements — Context freshness detection, quick health check (deep mode), bidirectional task integrity pre-check, uncommitted changes warning in summary, compact tip, expanded allowed-tools for build/test commands
- [x] `/update-docs` enhancements — Drain validation after Part 0, commit checkpoint (Part 5), `--skip-commit` flag, post-verification compact suggestion
- [x] `/code-cleanup` CI gating recipe — Documented PreToolUse `defer` hook integration in Fix Mode; explains the single-tool-call constraint and resume-via-`claude -p --resume` flow (SKILL.md)
- [x] `/code-review` CI gating + MCP `maxResultSizeChars` notes — Step 1 sampling notes the MCP `_meta["anthropic/maxResultSizeChars"]` knob (up to 500K) for larger file returns; Step 6 Auto-Fix mirrors the PreToolUse defer recipe from code-cleanup (SKILL.md)
- [x] `/resume-work` plugin `bin/` detection — Step 2.5 deep-mode health check now prefers `bin/check`, `bin/test`, `bin/ci` helpers shipped by enabled plugins (CC 2.1.91+) over the generic `package.json → Makefile → pyproject.toml → Cargo.toml` ladder (SKILL.md)

## Subagents
- [x] `cleanup-files-code` — Scans for unused files and dead code
- [x] `cleanup-deps-config` — Scans for unused dependencies and config cruft
- [x] `cleanup-styles-tests` — Scans for unused CSS and stale test artifacts

## Infrastructure
- [x] Mac/Linux setup instructions with symlink approach
- [x] Windows setup instructions (PowerShell as Administrator)
- [x] GitHub sync workflow (push/pull across machines)
- [x] Workflow.md — Detailed personal workflow guide
- [x] Startup scripts (`start-claude.sh`, `start-claude.ps1`) — Single-command session startup with interactive project picker
- [x] Fixed PowerShell script filename bug in Workflow.md and README.md, added Unblock-File first-run note
- [x] Changed startup scripts to show tip instead of auto-running `/resume-work`; fixed remaining PS1 filename refs in Workflow.md
- [x] Clarified shell alias instructions in Workflow.md — explicit "paste into config file" wording with reload/open hints
- [x] Deduplicated setup instructions — removed from Workflow.md, consolidated in README.md with alias setup
- [x] Reordered Workflow.md — Quick Start (`cc`) first, manual steps collapsed in `<details>` blocks
- [x] Removed claude-config filter from startup script project pickers

## Documentation
- [x] README.md — Public project overview with setup, commands table, subagents table
- [x] Workflow.md — Personal workflow guide with scenarios, tips, troubleshooting
- [x] CLAUDE.md — AI session context with all 10 required sections
- [x] docs/session-history.md — Session archive
- [x] docs/key-decisions.md — Architectural decisions log
- [x] docs/completed-work.md — This file
- [x] README.md "Interop with Claude Code 2.1 features" section — Documents `disableSkillShellExecution`, plugin `bin/` PATH injection, MCP `maxResultSizeChars` up to 500K, the `PreToolUse defer` recipe for CI gating, and @-mentioned subagents; explicitly notes that standalone skills and installed marketplace plugins coexist per official docs
- [x] README.md MCP server setup bullet — Added to the interop section documenting the three MCP scopes (local/project/user), `.mcp.json` at repo root for project scope, the `claude mcp add --transport {http\|sse\|stdio}` CLI, and tool-search context deferral (Session 13)
- [x] `workflow.md` Mid-Session Context Hygiene subsection — Generalizes the `/compact` habit from the existing resume-work/update-docs suggestions to mid-session use. Softened wording ("earlier rather than later") after verification showed no percentage threshold is in Anthropic docs. Includes the CLAUDE.md-survives-compaction note (Session 13)
- [x] `workflow.md` Recurring tasks `/loop` reference — Documents the built-in `/loop` skill with session-scope + 3-day auto-expire caveats. Explicit non-goal: do not reimplement as a custom skill (Session 13)
