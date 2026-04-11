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
| Document MCP scopes explicitly in README | Session 13: MCP config lives in three places — local scope in `~/.claude.json` (personal, per-project, default), project scope in `.mcp.json` at repo root (team-shared, version-controlled), user scope in `~/.claude.json` (all your projects). Add servers via `claude mcp add --transport {http\|sse\|stdio}`. Documented in README interop so future sessions don't guess. |
| Generalize the `/compact` habit to mid-session | Session 13: both `/resume-work` and `/update-docs` already suggest `/compact` at their completion, but long development sessions benefit from proactive compaction mid-task too. Documented in `workflow.md` "Mid-Session Context Hygiene" subsection. **No percentage threshold cited** — the "50%" figure from an external repo was not verified against Anthropic docs. Framed as "earlier rather than later." |
| Reference built-in `/loop` skill, do not reimplement | Session 13: Claude Code ships `/loop` as a built-in for session-scoped recurring prompts/commands. Documented in `workflow.md` Tips section with the session-scope + 3-day auto-expire caveats. Explicit non-goal: do NOT build a custom `/loop` skill in `.claude/skills/`. |
| Verify external-repo claims by direct-fetch, not just catalog | Session 13: an Explore agent's catalog of the external shanraisshan/claude-code-best-practice repo mixed real observations with documentation-speculation. Spot-fetching two specific files (`agent-browser/SKILL.md` and `weather-agent.md`) during Phase 3 collapsed the plan's Tier 2 from two candidates to zero. Generalized rule: before adopting a pattern from an external repo's catalog, fetch the actual file from that repo to confirm the pattern is real and matches the claim. |

---

## Considered and Skipped in Session 13

From the review of https://github.com/shanraisshan/claude-code-best-practice. These are recorded so a future session doesn't re-litigate the same decisions. Order follows the plan's "Verdict by Finding" table.

| # | Pattern | Skip reason (one sentence) |
|---|---|---|
| 1 | hooks.py Python dispatcher (27-event audio/notification system) | High setup cost, no symlinked home for `~/.claude/settings.json` in this repo, and the pending Session 12 `defer` dogfood is the correct first hook experiment — bundling would create a verification confound. |
| 2 | Agent-scoped hooks in subagent frontmatter (`hooks: {PreToolUse, ...}`) | Depends on #1; no hooks infrastructure today. Pattern is confirmed real in the external `weather-agent.md`. |
| 3 | Agent-preloaded skills (`skills: [name]` on agent + `user-invocable: false` on skill) | Pattern confirmed real via direct fetch but inapplicable without creating new skills, which violates the "no new skills" constraint. |
| 4 | Command → Agent → Skill orchestration labeling | Pure terminology; `code-cleanup` already dispatches 3 subagents and `plan-feature` already uses Plan Mode. Adding a "Command" layer label is zero behavioral delta. |
| 5 | Skills `paths:` frontmatter | **Verified by direct fetch: the external repo's own `agent-browser/SKILL.md` uses only `name`, `description`, `allowed-tools`.** The claim was a fabrication of the research pass. (Note: `.claude/rules/*.md` DO support `paths:` per docs.claude.com memory page — different feature, different file type. Flagged for future consideration.) |
| 6 | Skills `effort:` frontmatter | Same reason as #5; not observed in the external repo's own skill files. No evidence this is a valid field in the current Claude Code skill schema. Premature tuning anyway — no cost complaints today. |
| 7 | Skills `context: fork` | Same reason as #5; not observed in practice. Code-cleanup already achieves isolation via subagents. |
| 8 | Subagent `memory: {user\|project\|local}` scoping | Our 3 cleanup subagents are stateless scanners that emit structured findings and return. Nothing to persist between runs. |
| 9 | Multiple CLAUDE.md / CLAUDE.local.md hierarchy | claude-config is a single-repo, single-owner project. The three-file system (README + CLAUDE.md + docs/*.md) was re-validated in Session 12 and intentionally kept simple. |
| 12 | Deny-first `settings.local.json` model | Current allow-list is ~20 lines and machine-local. Inverting to deny-first adds maintenance burden with no safety gain in a solo context. |
| 14 | Hooks-as-sound-notification | Same hook-infrastructure blocker as #1. Terminal bell / OS notifications are machine-local preferences, not repo-level. |
| — | Agent frontmatter field imports (`allowedTools`, `maxTurns`, `permissionMode`) | The external repo uses camelCase for these; our agents use kebab-case `tools`. Copying without verifying casing against docs.claude.com subagent schema would be unsafe, and the verification effort exceeds the value for solo use. |

**Also noted during verification (not in the original research, not adopted, flagged for future):**

- **`.claude/rules/` with path-scoped `paths:` frontmatter** — real documented feature in the memory page. Rules load into context when Claude reads files matching the glob. **Supports symlinks for cross-project sharing**, which fits our symlink model cleanly. Not shipped this session because there's nothing urgent to put in it; revisit if a cross-project repo-convention file becomes useful.
- **`@path/to/file` imports in CLAUDE.md** — documented syntax for importing additional files into CLAUDE.md context at launch. Max recursion depth 5. Not needed today (our CLAUDE.md is at 7.6k chars, well under limits) but a clean way to split if CLAUDE.md ever grows past target.
- **`claudeMdExcludes` setting** — useful in monorepos for skipping other teams' CLAUDE.md files. Not applicable here (single-repo).
- **`InstructionsLoaded` hook** — useful for debugging which instruction files are loaded, when, and why. Worth knowing about if/when we ever need to debug CLAUDE.md loading behavior.
