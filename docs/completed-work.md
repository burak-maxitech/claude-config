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
- [x] `plan-feature` Step 0 triviality check — Skip the interview for one-sentence changes (typo, log line, rename) per official best-practices doc; new Step 0 in `SKILL.md` plus a renumbered "Start Now" list (Session 14)
- [x] `plan-feature` interview via `AskUserQuestion` — `interview-rules.md` rewritten around the tool with multi-choice + "Other / explain" escape; Step 5 of `SKILL.md` updated; `AskUserQuestion` added to `allowed-tools` frontmatter; falls back to numbered chat Q&A when the tool is unavailable (Session 14)
- [x] `code-review` fresh-session tip — One-line tip in the SKILL.md header recommending `/clear` or a fresh `claude` session for non-trivial reviews per the doc's Writer/Reviewer pattern (Session 14)
- [x] `code-review --fix` and `code-cleanup --fix` `/rewind` recovery footer — Both `--fix` modes now end output with `Esc Esc` / `/rewind` undo guidance per the doc's checkpointing emphasis. For `code-cleanup`, `/rewind` is offered alongside the existing `git branch -D` instruction (coarse vs fine-grained undo) (Session 14)
- [x] Opus 4.7 alignment — `effort: high` frontmatter added to `/code-review` and `/plan-feature` SKILL.md (verified `effort` field syntax against code.claude.com/docs/en/skills); other skills inherit session default (Session 15)
- [x] `/ultrareview` positioning — `/code-review` SKILL.md description and README commands table updated to position custom skill as lightweight in-session daily driver vs built-in `/ultrareview` for high-risk pre-merge. New README blockquote explains the split (Session 15)
- [x] `docs/key-decisions.md:45` Sonnet-pin row refreshed — Re-evaluated at Opus 4.7 launch; documented that pricing parity ($5/$25 per Mtok) keeps Sonnet rationale intact (Session 15)
- [x] `workflow.md` version history — Apr 2026 row added documenting the 4.7 alignment work; "Last updated" bumped from March → April 2026 (Session 15)
- [x] Dropped Session 12 `defer` hook dogfood task — Carried 12→13→14, formally retired in Session 15. Removed the carry-forward bullet from CLAUDE.md so future `/resume-work` sessions stop surfacing it. README recipe at line 177 left in place untested (Session 15)
- [x] Session-history rollup pattern — New Part 6 in `update-docs/references/mode-update.md` auto-compresses sessions older than the 5 most recent into one-liners with commit hashes. Added `--skip-rollup` flag to `update-docs/SKILL.md` argument-hint; new checklist item in `verification-checklists.md`. Step 6.2 first-run confirmation gate uses `AskUserQuestion` (added to allowed-tools) so legacy projects aren't surprised on first run; the rollup-format note acts as the per-project sentinel. One-time pass on Sessions 1-10 shrank `docs/session-history.md` from 27.7KB → 22.0KB (-21%) with full prose preserved in git history (Session 15)
- [x] `/update-docs` performance — `effort: low` frontmatter pin + Part 3.0 preamble directing a parallel batch-Read of all `docs/*.md` before edits + Part 6.3 single pre-fetched `git log` across the compressible date range. Addresses a real ~20-minute runtime the user hit on another project; no functionality changed (Session 16)
- [x] `/resume-work` performance — `effort: low` frontmatter pin. Mechanical work (read docs, run git in parallel, fill summary template, hydrate tasks) doesn't need Opus reasoning; frontmatter scope reverts to session default on skill return (Session 16)
- [x] Active CLAUDE.md cap enforcement — new Part 1.10 in `update-docs/references/mode-update.md`: Current Status ≤10 (collapses `Complete` runs), Next Steps ≤10 (warn), In Progress ≤5 (warn). Replaces the passive 35k-char warning with active per-section caps that run every UPDATE. Gated by `--skip-caps`. Root-cause fix for slow CLAUDE.md growth despite documented caps (Session 17)
- [x] Key Decisions rollup — new Part 6 in `update-docs/references/mode-update.md` mirrors Part 5's session-history rollup. FIFO move of oldest CLAUDE.md Key Decisions rows beyond 20 into `docs/key-decisions.md`, first-run `AskUserQuestion` consent gate with sentinel note, gated by `--skip-decisions-rollup` (Session 17)
- [x] Commit checkpoint moved to Part 7 — commit is now truly last so both rollups (Part 5 session-history, Part 6 key-decisions) land in the same commit. Closes a Session 15 bug where rollup changes could end up uncommitted (Session 17)
- [x] "Pruning is preservation" subsection in `update-docs/references/doc-structure-rules.md` — explicit doctrine giving Part 1.10 and Parts 5/6 canonical backing under the existing "when in doubt, keep it" rule. Moving a row CLAUDE.md → reference file is preservation, not removal (Session 17)
- [x] `update-docs/SKILL.md` argument-hint extended — added `--skip-caps` and `--skip-decisions-rollup` alongside the existing `--skip-memory`/`--skip-tasks`/`--skip-commit`/`--skip-rollup` (Session 17)
- [x] `update-docs/references/verification-checklists.md` — 3 new UPDATE-mode checklist items covering cap enforcement, key-decisions rollup, and commit-last ordering (Session 17)
- [x] `/update-docs --fast` mode — daily-cycle Fast Path with `--fast` flag in argument-hint; runs Parts 0/1.0/1.4-1.5/1.6/1.8/7 + drift probes; skips Parts 0.5/2/3/4/5/6/1.10; surfaces drift via warnings instead of enforcement (Session 18, commit 259f400)
- [x] `/update-docs` Step 0 upfront parallel batch — single parallel turn for all reads + `git log -20` + `git diff --stat HEAD~5` + `git status` + `TaskList`, replacing 5-6 sequential read turns across Parts 0.5/2/3/4/5/6; benefits both Fast and Full paths (Session 18, commit 259f400)
- [x] `/update-docs` Part 1 plan-then-batch preamble — directs the model to gather all CLAUDE.md sub-section changes from cached Step 0 evidence and apply as one Write or non-overlapping parallel Edits; Fast Path uses this by definition, Full Path opts in (Session 18, commit 259f400)
- [x] README defer-recipe `if`-field modernization — uses 2.1.85 `if` field (e.g. `"if": "Bash(rm:*)"`) so PreToolUse defer only fires for matching tool calls (commit `14546ff`, 2026-04-22; backfilled Session 19)
- [x] README auto mode compatibility paragraph — documents 2.1.83+ `defaultMode: "auto"` classifier behavior, plan-tier eligibility, narrow-vs-broad allow-rule retention, and `PermissionDenied` hook fallback added 2.1.89 (commit `14546ff`, 2026-04-22; backfilled Session 19)
- [x] `start-claude.{sh,ps1}` `disableSkillShellExecution` guardrail — warns when this setting is on in `~/.claude/settings.json`, since it would silently break `--fix`/`--verify`/`deep` modes (commit `14546ff`, 2026-04-22; backfilled Session 19)
- [x] `code-cleanup/SKILL.md` and `code-review/SKILL.md` CI-gating prose trim — duplicated text collapsed to one-liner pointer at README recipe (commit `14546ff`, 2026-04-22; backfilled Session 19)
- [x] `/code-review --verify` parallelization — Step 1.5 now launches test/lint with `run_in_background` so they complete during review work (Steps 2-4); Step 5 collects output instead of running synchronously; saves ~10-60s per invocation on non-trivial test suites (commit `ff89cbb`, 2026-04-22; backfilled Session 19)
- [x] Session 19 Full Path validation run — back-to-back `/update-docs` (no flag) immediately after Session 18's `--fast` run; cleared all 4 drift items (Part 5 compressed S13 to one-liner; Part 6 FIFO moved 3 oldest Key Decisions to docs/key-decisions.md; backfilled commits `14546ff` + `ff89cbb`); Full Path performance subjectively far below 12-14 min baseline though best-case (caches warm) (Session 19)
- [x] `/code-cleanup` reference files — perf rewrite: `git ls-files` over `find` (honors `.gitignore` natively, faster on large repos); per-item grep loops in unused-files, dead-functions, unused-classes, unused-CSS-variables, and unused-deps searches collapsed into single batched `Grep` calls with regex alternation (`\b(name1|name2|...)\b` + `output_mode: count`). Applied uniformly across `scan-files-code.md`, `scan-deps-config.md`, `scan-styles-tests.md` (Session 20)
- [x] `/code-cleanup` monorepo coverage — `scan-deps-config.md` §4.0 workspace detection: npm/yarn `package.json` `workspaces`, pnpm `pnpm-workspace.yaml` `packages:`, Cargo root `[workspace] members = [...]`. Per-workspace scan with sibling-doesn't-count rule; output gains `workspace:` field on Unused Dependencies; new "Misplaced Dependencies (monorepos only)" output section. `SKILL.md` Step 0 detection list updated; "Detected:" example expanded to surface monorepo state (Session 20)
- [x] `/code-cleanup` Grep-tool correctness — refactored literal `rg --type js -e "..."` shell-command examples in all three reference files to use the `Grep` tool's parameter shape (`pattern:`, `output_mode:`, `glob:`, `path:`); cleanup-* agents have `Bash(grep:*)` not `Bash(rg:*)`, and runtime guidance pins use of the `Grep` tool (Session 20)
