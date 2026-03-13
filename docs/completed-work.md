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

## Documentation
- [x] README.md — Public project overview with setup, commands table, subagents table
- [x] Workflow.md — Personal workflow guide with scenarios, tips, troubleshooting
- [x] CLAUDE.md — AI session context with all 10 required sections
- [x] docs/session-history.md — Session archive
- [x] docs/key-decisions.md — Architectural decisions log
- [x] docs/completed-work.md — This file
