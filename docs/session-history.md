# Session History Archive

> Auto-managed by `/update-docs`. Last session summary is in [CLAUDE.md](../CLAUDE.md).

---

### Session 1 - 2026-03-10
**What happened:**
- Created CLAUDE.md with all 10 required sections per claude-md-sections.md
- Created docs/ folder with session-history.md, key-decisions.md, completed-work.md
- Added Documentation section to README.md with links to CLAUDE.md and docs/
- No content removed from existing files — REFACTOR mode (additive only)

**Files created/modified:**
- `CLAUDE.md` - Created with all 10 required sections
- `docs/session-history.md` - Created (this file)
- `docs/key-decisions.md` - Created with architectural decisions
- `docs/completed-work.md` - Created with full completed task checklist
- `README.md` - Added Documentation section with links

**Next session should:**
- Run `/resume-work` to verify the new doc structure loads correctly
- Consider adding more skills as workflow needs emerge

### Session 2 - 2026-03-12
**What happened:**
- Reviewed uncommitted changes across 5 files in the code-cleanup skill
- Enhanced `/code-cleanup` SKILL.md: added `--dry-run` mode, clarified `--aggressive` behavior, added `Bash(gh:*)` permission, improved description
- Added Python package→import name lookup table (30+ entries) to scan-deps-config.md
- Optimized one-off script detection in scan-files-code.md (batch git log)
- Made media query dead code detection more conservative in scan-styles-tests.md
- Added find command permissions to settings.local.json for update-docs and resume-work skills
- Ran `/update-docs` to capture all changes

**Files created/modified:**
- `.claude/skills/code-cleanup/SKILL.md` - Added --dry-run mode, --aggressive clarification, gh permission
- `.claude/skills/code-cleanup/references/scan-deps-config.md` - Python import name lookup table
- `.claude/skills/code-cleanup/references/scan-files-code.md` - Batch git log optimization
- `.claude/skills/code-cleanup/references/scan-styles-tests.md` - Conservative media query flagging
- `.claude/settings.local.json` - Added find command permissions
- `CLAUDE.md` - Updated timestamp, session history
- `docs/completed-work.md` - Added 4 new completed items
- `docs/key-decisions.md` - Added 5 new decisions
- `docs/session-history.md` - Added Session 2 entry

**Next session should:**
- Commit all pending changes
- Continue improving skills based on real-world usage patterns

### Session 3 - 2026-03-12
**What happened:**
- Improved `/plan-feature` skill with 5 enhancements from Claude Code best practices:
  - Phase gating with verification (tests must pass before next phase)
  - Explicit test types per phase (unit/integration/e2e)
  - Commit after each phase for rollback-friendly checkpoints
  - Context management reminder (`/compact` before implementation)
  - Rollback strategy required in both greenfield and existing mode plans
- Improved `/code-review` skill with 5 enhancements from community + official Claude docs:
  - `--verify` mode: run tests/lint to validate findings
  - `--security` mode: OWASP Top 10 deep-dive checklist
  - `--fix` mode: auto-fix simple issues (unused imports, formatting)
  - Git blame context for Critical/Important findings
  - Large diff guard (warn at 500+, suggest chunking at 1000+ lines)
- Created new `references/security-deep-dive.md` with full OWASP Top 10 checklist
- Updated allowed-tools for code-review to support verify/fix modes
- Ran `/update-docs` to capture all changes

**Files created/modified:**
- `.claude/skills/plan-feature/references/plan-and-tasks.md` - Phase gating, commit rules, context management
- `.claude/skills/plan-feature/references/mode-greenfield.md` - Test types, rollback in interview + summary
- `.claude/skills/plan-feature/references/mode-existing.md` - Test types, rollback section, summary update
- `.claude/skills/code-review/SKILL.md` - New flags, large diff guard, git blame step, verify/fix steps
- `.claude/skills/code-review/references/review-checklist.md` - Enhanced security + testing sections
- `.claude/skills/code-review/references/output-format.md` - Verification + auto-fix output templates
- `.claude/skills/code-review/references/security-deep-dive.md` - NEW: OWASP Top 10 checklist
- `CLAUDE.md` - Updated timestamp, key decisions, session history
- `docs/completed-work.md` - Added 3 new completed items
- `docs/key-decisions.md` - Added 11 new decisions
- `docs/session-history.md` - Added Session 3 entry

**Next session should:**
- Commit all pending changes (sessions 2 + 3)
- Test improved skills on a real codebase
- Consider improving `/resume-work` skill next

### Session 4 - 2026-03-12
**What happened:**
- Planned and implemented 5 improvements to `/resume-work` and `/update-docs` skills:
  1. Bidirectional task integrity check (pre-hydration stale check + post-drain validation)
  2. Context freshness detection (compare CLAUDE.md date vs git commits)
  3. Commit checkpoint reminder (Part 5 in update-docs, --skip-commit flag)
  4. Compact guidance after both skills (free context before real work)
  5. Quick health check in deep mode (detect and run test/build commands)
- Committed and pushed all session 3+4 changes together (639cfb3)
- Ran `/update-docs` to capture session 4 changes

**Files created/modified:**
- `.claude/skills/resume-work/SKILL.md` - Added Step 2.5 (health check), Step 3.0 (freshness), compact tip, expanded allowed-tools
- `.claude/skills/resume-work/references/summary-template.md` - Added staleness warning, uncommitted changes check, health check section
- `.claude/skills/resume-work/references/task-hydration.md` - Added pre-hydration stale task check
- `.claude/skills/update-docs/SKILL.md` - Added --skip-commit to argument-hint
- `.claude/skills/update-docs/references/mode-update.md` - Added drain validation, Part 5 commit checkpoint
- `.claude/skills/update-docs/references/verification-checklists.md` - Added commit checkpoint checklist item, post-verification compact tip
- `CLAUDE.md` - Updated timestamp, key decisions, session history
- `docs/completed-work.md` - Added 2 new completed items
- `docs/key-decisions.md` - Added 5 new decisions
- `docs/session-history.md` - Added Session 4 entry

**Next session should:**
- Test improved skills on a real codebase
- Add more skills as new workflow needs emerge
- Consider adding hooks for automated pre-commit workflows

### Session 5 - 2026-03-12
**What happened:**
- Added startup scripts (`start-claude.sh` for Mac/Linux, `start-claude.ps1` for Windows) to `.claude/scripts/`
- Scripts automate 5-step session startup: sync config, verify symlinks, pull project, update Claude, launch with `/resume-work`
- Updated Workflow.md: added scripts as "Quick Start" alternative alongside existing manual steps, added shell alias tips
- Updated README.md: added scripts to directory tree, added Quick Start section
- Updated CLAUDE.md architecture tree to include scripts directory
- Fixed Workflow.md: restored manual startup steps after initially replacing them (user feedback: keep both methods visible)
- Ran `/update-docs` to capture session 5 changes

**Files created/modified:**
- `.claude/scripts/start-claude.sh` - NEW: Mac/Linux session startup script
- `.claude/scripts/start-claude.ps1` - NEW: Windows PowerShell session startup script
- `Workflow.md` - Added Quick Start scripts section below manual steps, added alias tips, updated version history
- `README.md` - Added scripts to tree, added Quick Start section
- `CLAUDE.md` - Updated timestamp, architecture tree, key decisions, session history
- `docs/key-decisions.md` - Added startup scripts decision
- `docs/completed-work.md` - Added startup scripts to Infrastructure section
- `docs/session-history.md` - Added Session 5 entry

**Next session should:**
- Test startup scripts on Mac/Linux
- Add more skills as new workflow needs emerge
- Consider adding hooks for automated pre-commit workflows

### Session 6 - 2026-03-12
**What happened:**
- Fixed PowerShell script filename bug in Workflow.md and README.md — both referenced `Start-ClaudeSession.ps1` instead of the actual filename `start-claude.ps1`
- Added `Unblock-File` note for Windows first-run setup in Workflow.md

**Files created/modified:**
- `Workflow.md` - Fixed PowerShell alias filename, added Unblock-File note
- `README.md` - Fixed Quick Start PowerShell filename

**Next session should:**
- Test startup scripts on Mac/Linux
- Add more skills as new workflow needs emerge
- Consider adding hooks for automated pre-commit workflows

### Session 7 - 2026-03-12
**What happened:**
- Changed startup scripts to no longer auto-run `/resume-work` — scripts now launch `claude` and show a tip message instead
- Fixed remaining PowerShell filename references in Workflow.md (`Start-ClaudeSession.ps1` → `start-claude.ps1`)
- Updated README.md, Workflow.md, and CLAUDE.md to reflect new script behavior

**Files created/modified:**
- `.claude/scripts/start-claude.ps1` - Removed `-p "/resume-work"`, added tip message
- `.claude/scripts/start-claude.sh` - Removed `-p "/resume-work"`, added tip message
- `Workflow.md` - Fixed PS1 filenames, updated step 5 description, updated version history
- `README.md` - Updated Quick Start description
- `CLAUDE.md` - Updated timestamp, session history, key decisions
- `docs/session-history.md` - Added Session 7 entry
- `docs/key-decisions.md` - Added script launch behavior decision
- `docs/completed-work.md` - Added script update entry

**Next session should:**
- Test startup scripts on Mac/Linux
- Add more skills as new workflow needs emerge
- Consider adding hooks for automated pre-commit workflows

### Session 8 - 2026-03-13
**What happened:**
- Fixed incorrect symlink fix suggestions in `start-claude.sh` — referenced non-existent `commands/` dir and wrong paths; corrected to `.claude/skills` and `.claude/agents`
- Added `chmod +x` first-run note for Mac/Linux in Workflow.md (alongside existing Windows `Unblock-File` note)
- Changed `disable-model-invocation` from `true` to `false` in update-docs SKILL.md to allow programmatic invocation via Skill tool

**Files created/modified:**
- `.claude/scripts/start-claude.sh` - Fixed symlink fix suggestion paths (lines 68-69)
- `Workflow.md` - Added Mac/Linux first-run `chmod +x` note
- `.claude/skills/update-docs/SKILL.md` - Changed disable-model-invocation to false

**Next session should:**
- Consider changing disable-model-invocation to false on remaining 4 skills
- Add more skills as new workflow needs emerge
- Consider adding hooks for automated pre-commit workflows

### Session 9 - 2026-03-13
**What happened:**
- Clarified shell alias instructions in Workflow.md — made it explicit that the alias line must be pasted into the shell config file (e.g., `~/.zshrc`), not run directly in the terminal
- Added `source ~/.zshrc` reload hint for Mac/Linux and `notepad $PROFILE` hint for Windows

**Files created/modified:**
- `Workflow.md` - Clarified alias persistence instructions (lines 97-105)

**Next session should:**
- Consider changing disable-model-invocation to false on remaining 4 skills
- Add more skills as new workflow needs emerge
- Consider adding hooks for automated pre-commit workflows

### Session 10 - 2026-03-13
**What happened:**
- Removed duplicated "New Machine Setup" section from Workflow.md — replaced 60-line duplicate with one-line link to README.md
- Fixed alias name from `claude-start` to `cc` in both Workflow.md (Mac + Windows examples)
- Reordered Workflow.md Daily Workflow section: Quick Start with `cc` first, detailed manual steps collapsed in `<details>` blocks
- Moved alias setup one-liners from Workflow.md to README.md Quick Start section (one-time setup belongs in README)
- Simplified Workflow.md Quick Start to just `cc my-project` with link to README for alias setup
- Removed `claude-config` filter from interactive project picker in both `start-claude.sh` and `start-claude.ps1`

**Files created/modified:**
- `Workflow.md` - Removed duplicate setup section, fixed alias names, reordered Quick Start first, simplified to `cc` usage
- `README.md` - Added alias setup one-liners (Mac + Windows) and first-run notes to Quick Start section
- `.claude/scripts/start-claude.sh` - Removed `! -name "claude-config"` filter from project picker
- `.claude/scripts/start-claude.ps1` - Removed `$_.Name -ne "claude-config"` filter from project picker

**Next session should:**
- Add more skills as new workflow needs emerge
- Consider adding hooks for automated pre-commit workflows
- Consider changing disable-model-invocation to false on remaining 4 skills

### Session 11 - 2026-03-17
**What happened:**
- Resumed work after 4-day break using `/resume-work`
- Reviewed plan-feature skill's `disable-model-invocation` setting (currently `true`)
- User initiated change to enable model invocation but cancelled before applying
- No code changes made this session

**Files created/modified:**
- None (documentation-only update via `/update-docs`)

**Next session should:**
- Change `disable-model-invocation` to `false` on plan-feature skill (user intention from this session)
- Add more skills as new workflow needs emerge
- Consider adding hooks for automated pre-commit workflows

### Session 12 - 2026-04-11
**What happened:**
- User asked for a thorough analysis of Claude Code improvements released since the last session (2.1.88 → 2.1.101) and which would make sense to incorporate into the 5 skills.
- Used plan mode with two parallel Explore agents (skill audit + feature research) plus one Plan agent to produce a tiered implementation blueprint. Plan written to `C:\Users\burak\.claude\plans\toasty-sleeping-charm.md`.
- Verified 11 candidate features against docs.claude.com (hooks page, plugins page) and the official CHANGELOG at github.com/anthropics/claude-code. `PermissionDenied` hook, `defer` PreToolUse decision, `disableSkillShellExecution`, MCP `maxResultSizeChars`, plugin `bin/` on PATH, and named subagents in @-mention all confirmed. `showThinkingSummaries` and subagent MCP inheritance fix couldn't be verified and were dropped.
- **Killed the `--gated` flag design** after discovering two blocking constraints in the hooks doc: `defer` only works when Claude makes a single tool call in the turn (quoted verbatim from docs), and it's specifically designed for external SDK/subprocess callers that run `claude -p` and resume via `claude -p --resume`. Skills cannot self-emit defer; only a `PreToolUse` hook can. The correct integration is harness-level config documented in README, not a new skill flag.
- Shipped 5 commits total (2 original commits 5+6 dropped, commit 7 was a no-op grep):
  1. `docs: note Claude Code 2.1 features and CI gating recipe` (56a5513) — README interop section added
  2. `code-cleanup: document CI gating via PreToolUse defer hook` (dd6a7ce) — Fix Mode note
  3. `code-review: document CI gating and MCP maxResultSizeChars` (644fb0c) — Step 1 + Step 6 notes
  4. `resume-work: detect plugin bin/ scripts in deep-mode health check` (83f9bb1) — extends the detection ladder
  5. (this commit) `docs: record session 12 and CC 2.1 adoption decisions`
- Unexpected findings worth remembering: the user already has `frontend-design` and `feature-dev` plugins installed via the official marketplace; the plugins doc explicitly calls out standalone `.claude/` as the recommended approach for personal workflows, vindicating the symlink model.
- Did **not** upgrade cleanup subagents to Opus 4.6 — reverses the existing "Subagents on Sonnet" key decision.

**Files created/modified:**
- `README.md` - Added "Interop with Claude Code 2.1 features" section (+12 lines), updated Subagents section to mention @-mention typeahead
- `.claude/skills/code-cleanup/SKILL.md` - Added CI gating note in Fix Mode (+2 lines)
- `.claude/skills/code-review/SKILL.md` - Added MCP maxResultSizeChars tip in Step 1 + CI gating note in Step 6 Auto-Fix (+4 lines)
- `.claude/skills/resume-work/SKILL.md` - Added plugin bin/ detection to health check ladder in Step 2.5 (+1 line)
- `CLAUDE.md` - Bumped Last Updated to 2026-04-11, added 3 Key Decisions rows, replaced Session 11 summary with Session 12
- `docs/session-history.md` - Added Session 12 entry (this entry)

**Files NOT modified (and why):**
- `.claude/agents/cleanup-*.md` - Planned decline markers were speculative and don't fit the current return-structured-findings agent model
- `.claude/skills/plan-feature/` - Grep confirmed no stale MCP inheritance caveat to remove; commit 7 was a no-op
- `.claude/skills/update-docs/` - None of the verified features address its rough edges
- `docs/completed-work.md`, `docs/key-decisions.md` - Not updated this session; Key Decisions condensed table in CLAUDE.md is the primary landing spot for this round

**Next session should:**
- Dogfood the `--fix` CI gating recipe: build a minimal PreToolUse defer hook in `~/.claude/settings.json` that matches `Bash(rm:*)`, run `/code-cleanup --fix` on a throwaway scratch repo, and verify the session exits with `stop_reason: "tool_deferred"` and resumes cleanly via `claude -p --resume`. If resume works, consider writing a reference file documenting the exact hook config.
- Revisit `update-docs` rough edges (partial-mode selection, rollback) independently — none of this round's CC 2.1 features addressed them.
- Consider the 2.1.98 Monitor tool for streaming background script events — could be useful for watching long-running commands inside `code-cleanup --fix` or `code-review --verify`.

### Session 13 - 2026-04-11
**What happened:**
- User asked for a thorough review of the external best-practice repo https://github.com/shanraisshan/claude-code-best-practice (actively maintained, daily commits as of April 2026) to identify patterns worth incorporating.
- Ran plan mode: single Explore agent produced a 40+ file catalog from the external repo; single Plan agent synthesized it against the existing 5 skills + 3 subagents into a tiered recommendation. Plan written to `C:\Users\burak\.claude\plans\toasty-sleeping-charm.md` (overwriting Session 12's plan).
- **Spot-verification during Phase 3 killed two claims:**
  1. Direct fetch of `.claude/skills/agent-browser/SKILL.md` from the external repo showed its frontmatter is only `name`, `description`, `allowed-tools` — the same minimal set we already use. The Explore agent's "13 skill frontmatter fields" claim was documentation extrapolation, not observed practice. **Dropped all Tier 2 skill-frontmatter adoptions** (no `paths:`, no `effort:`, no `context: fork`).
  2. WebFetch of docs.claude.com memory page had no mention of proactive `/compact` at any specific percentage. "50%" was one person's opinion. **Softened the workflow wording** to "earlier rather than later" with no number cited.
- Direct fetch of `.claude/agents/weather-agent.md` confirmed the external repo's rich agent frontmatter is real (`skills:`, `memory: project`, `hooks:`, camelCase `allowedTools`/`maxTurns`/`permissionMode`), validating the hooks.py dispatcher pattern exists. **Not adopted** — hook infrastructure is blocked on the pending Session 12 `defer` dogfood.
- WebFetch of docs.claude.com MCP page confirmed `.mcp.json` at repo root is the project-scope config file (quote: *"Project-scoped servers enable team collaboration by storing configurations in a `.mcp.json` file at your project's root directory"*). Local scope lives in `~/.claude.json`; `claude mcp add --transport {http|sse|stdio}` is the recommended add path. Tool-search deferral keeps context cost low, so the "curation/start narrow" community narrative is only partially true — the real ceilings are tool-menu clarity and permission-prompt volume.
- **Unexpected finding from memory doc (not in the original research):** `.claude/rules/` with `paths:` frontmatter is a real documented feature for path-scoped project rules, and `.claude/rules/` explicitly **supports symlinks for cross-project sharing**. This is different from skills and fits our symlink model cleanly — flagged as a potential future adoption but not shipped this session (would require deciding what rules to write, and nothing pressing).
- Shipped 3 doc commits (`adf634e`, `5f61209`, `445c357`) all direct to `main`:
  1. `docs: add MCP server setup bullet to README interop section` — one new bullet, verified scopes, CLI command, tool-search deferral note.
  2. `docs: add mid-session context hygiene subsection to workflow` — new subsection under Daily Workflow explaining when to `/compact` (earlier rather than later) and noting that project-root CLAUDE.md survives compaction.
  3. `docs: reference built-in /loop skill in workflow tips` — new subsection under Tips & Best Practices with examples, the session-scope + 3-day auto-expire caveat, and an explicit non-goal of reimplementing `/loop` as a custom skill.
- Cancelled Tier 2 from the plan entirely (0 commits). Verification removed both T2 candidates before they reached implementation.

**Files created/modified:**
- `README.md` — Added MCP server setup bullet to "Interop with Claude Code 2.1 features" section (+1 line, fifth bullet)
- `workflow.md` — Added `### Mid-Session Context Hygiene` subsection between "During Development" and "Ending a Session" (+12 lines); added `### Recurring tasks: /loop` subsection inside "Tips & Best Practices" after Don'ts list (+14 lines)
- `CLAUDE.md` — Bumped Last Updated to Session 13, added 1 Key Decisions row ("Verify every external-repo claim before shipping"), replaced Session 12 summary with Session 13 summary
- `docs/session-history.md` — This entry
- `docs/key-decisions.md` — Appended 11-item skip-list appendix from the plan (see "## Considered and Skipped in Session 13" section)
- `docs/completed-work.md` — Added 3 entries for the shipped docs
- `.claude/settings.local.json` — Harness auto-added `WebFetch(domain:raw.githubusercontent.com)` and `WebFetch(domain:api.github.com)` permissions from this session's verification fetches

**Files NOT modified (and why):**
- No skill `SKILL.md` files — Tier 2 was cancelled after verification
- No subagent `.md` files — no hook or memory adoption this session
- No `.claude/rules/` directory created — feature is compelling but there's nothing urgent to put in it; document in key-decisions as "considered, deferred"

**Next session should:**
- **Still owed: Session 12 `defer` hook dogfood.** This has now been explicitly deferred twice (Session 12 after-work + Session 13 scope decision). It's the correct next hook experiment and blocks any broader hook adoption.
- After the dogfood, consider whether `.claude/rules/` (symlink-compatible path-scoped rules) is worth adopting — e.g., a shared `.claude/rules/repo-conventions.md` that can be symlinked into other projects.
- Revisit `update-docs` rough edges (partial-mode selection, rollback) — still not addressed.

### Session 14 - 2026-04-14
**What happened:**
- User asked whether the official Claude Code best-practices doc (https://code.claude.com/docs/en/best-practices) revealed any discrepancies or improvements for the 5 custom skills.
- WebFetched the full doc and ran a verification pass against the skill files: `Grep` confirmed zero references to `AskUserQuestion`, `/clear`, `/btw`, `/rewind`, "fresh session", `auto mode`, `--permission-mode`, or `--allowedTools` anywhere in `~/.claude/skills/` or the repo. Also confirmed `plan-feature` had no triviality escape hatch.
- Reported the audit as 4 high-value gaps + 2 medium gaps + 3 already-aligned items + 1 considered-but-rejected change. User asked to implement the high-value gaps.
- **Shipped one commit (`a94fbda`) covering all 4 high-value gaps:**
  1. `plan-feature/SKILL.md` — new Step 0 triviality check that proposes skipping the skill if the request fits in one sentence and 1-2 files; cites the doc verbatim.
  2. `plan-feature/SKILL.md` + `plan-feature/references/interview-rules.md` — interview now driven by the `AskUserQuestion` tool with multi-choice options + "Other / explain" escape; numbered chat Q&A is the documented fallback. `AskUserQuestion` added to `allowed-tools` frontmatter. "Start Now" list renumbered (caught and fixed a duplicate `3.` before commit).
  3. `code-review/SKILL.md` — header tip recommending `/clear` or fresh `claude` session for non-trivial reviews, with carve-outs for `--last-commit` and quick passes.
  4. `code-review/SKILL.md` + `code-cleanup/SKILL.md` — `--fix` outputs end with `Esc Esc` / `/rewind` recovery line. For `code-cleanup`, kept the existing `git branch -D` instruction and added `/rewind` as the finer-grained option.
- The single audit commit replaced the typical 4-separate-commits pattern from Sessions 12-13 because all four changes share the same source citation (the official doc) and all touch skill behavior; one commit reads cleaner in `git log`.

**Files created/modified:**
- `.claude/skills/plan-feature/SKILL.md` — added Step 0 (triviality check), added `AskUserQuestion` to `allowed-tools`, updated Step 5 interview directive, renumbered "Start Now" (+18 lines net)
- `.claude/skills/plan-feature/references/interview-rules.md` — new "Tool: use `AskUserQuestion`" section, rewrote 8 rules into 9 rules around multi-choice prompting (+15 lines net)
- `.claude/skills/code-review/SKILL.md` — header fresh-session tip + `--fix` `/rewind` footer (+5 lines)
- `.claude/skills/code-cleanup/SKILL.md` — `/rewind` footer added to step 8 of Fix Mode alongside the existing `git branch -D` (+1 line net)
- `CLAUDE.md` — bumped Last Updated to Session 14, added 2 Key Decisions rows, replaced Session 13 summary with Session 14 summary
- `docs/session-history.md` — this entry
- `docs/key-decisions.md` — appended 5 detailed rows (4 shipped decisions + 1 considered-and-rejected for the `@import` choice)
- `docs/completed-work.md` — appended 5 entries

**Files NOT modified (and why):**
- `README.md` — Medium gap #5 (auto mode for headless `claude -p` runs) was identified but deferred. The existing `defer` recipe at line 177 is correct as far as it goes; adding `auto mode` as a complementary first-line option is worth doing but wasn't requested in this round.
- `update-docs` skill files — Medium gap #6 (CLAUDE.md compaction-preservation hints) also deferred; would add an optional `## Compaction Preferences` section to `claude-md-sections.md` contract. Not requested.
- The 3 cleanup-* subagent files — no audit findings touched them.

**Next session should:**
- **Still owed: Session 12 `defer` hook dogfood.** Three sessions deferred now. Build the minimal `~/.claude/settings.json` `PreToolUse` hook matching `Bash(rm:*)`, run `/code-cleanup --fix` on a throwaway repo, verify `stop_reason: "tool_deferred"` and resume via `claude -p --resume <session-id>`.
- Pick up the 2 deferred medium-value gaps if useful: README `auto mode` documentation, `update-docs` compaction-preservation section.
- Revisit `update-docs` rough edges (partial-mode selection, rollback) — still not addressed since Session 12.
