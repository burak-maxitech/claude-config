# Session History Archive

> Auto-managed by `/update-docs`. Last session summary is in [CLAUDE.md](../CLAUDE.md).
> **Note:** Sessions older than the 5 most recent are compressed to one-liners with commit hashes. Full prose for compressed sessions lives in git history (`git show <hash>`).

---

### Session 1 - 2026-03-10: REFACTOR mode — created CLAUDE.md (10 required sections), `docs/` folder with session-history/key-decisions/completed-work, added Documentation section to README. (commits: 246c001, 9981d1e)

### Session 2 - 2026-03-12: `/code-cleanup` polish — `--dry-run`, `--aggressive` clarification, `Bash(gh:*)` permission; Python package→import-name lookup table (30+); batched `git log` for one-off script detection; conservative media-query flagging. (bundled in 639cfb3)

### Session 3 - 2026-03-12: Major skill overhaul — `/plan-feature` phase gating + test types + commit-per-phase + rollback strategy; `/code-review` `--verify`/`--security`/`--fix` modes + git blame context + large diff guard; new `references/security-deep-dive.md` with OWASP Top 10. (commit: 639cfb3)

### Session 4 - 2026-03-12: `/resume-work` + `/update-docs` robustness — bidirectional task integrity (pre-hydration stale check + post-drain validation), context freshness detection vs git, commit checkpoint with `--skip-commit`, compact tip, deep-mode health check. (commits: 639cfb3, f616e0d)

### Session 5 - 2026-03-12: Startup scripts — `start-claude.sh` (Mac/Linux) and `start-claude.ps1` (Windows) automating 5-step session startup; Workflow.md and README.md updated with Quick Start; manual steps preserved alongside. (commits: acfc2b9, f24fd37, f7d3342)

### Session 6 - 2026-03-12: PowerShell script filename fix (`Start-ClaudeSession.ps1` → `start-claude.ps1`) in Workflow.md and README.md; added `Unblock-File` Windows first-run note. (commit: e0c6a49)

### Session 7 - 2026-03-12: Startup scripts no longer auto-run `/resume-work` — show a tip message instead so user controls when to load context; remaining PS1 filename refs cleaned up. (commit: f58e5eb)

### Session 8 - 2026-03-13: Fixed wrong symlink-fix paths in `start-claude.sh` (referenced non-existent `commands/`); added `chmod +x` Mac/Linux first-run note; flipped `update-docs` `disable-model-invocation` to `false` for programmatic invocation. (commits: dc01f2d, 4a6cea4)

### Session 9 - 2026-03-13: Clarified shell-alias instructions in Workflow.md — explicit "paste into config file" wording with `source ~/.zshrc` and `notepad $PROFILE` reload hints. (commit: 0233b79)

### Session 10 - 2026-03-13: Workflow.md cleanup — removed 60-line duplicate setup section (replaced with link to README); alias name fix `claude-start` → `cc`; reordered Quick Start first with manual steps in `<details>`; moved alias setup one-liners to README; removed `claude-config` filter from project picker in both startup scripts. (commits: 7c99471, 777ab86)

### Session 11 - 2026-03-17: Enabled model invocation on plan-feature skill (`disable-model-invocation: false`). (commits: 734b13b, 1cffa6b)

### Session 12 - 2026-04-11: CC 2.1 feature audit — killed `--gated` skill flag after verifying `defer` PreToolUse only works on single-tool-call turns for external SDK callers; shipped README interop section + skill doc notes for CI gating / MCP `maxResultSizeChars` / plugin `bin/` detection. (commits: 56a5513, dd6a7ce, 644fb0c, 83f9bb1)

### Session 13 - 2026-04-11: External best-practice repo review — direct-fetch verification killed 2 of plan's Tier 2 candidates (`paths:`/`effort:` were doc-extrapolation, not observed in actual external skills); shipped 3 doc bullets (MCP setup in README, mid-session `/compact` in workflow, `/loop` reference); flagged `.claude/rules/` symlink-friendly rule files as future option. (commits: adf634e, 5f61209, 445c357)

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

**Post-commit polish (same-day, post `4d444b0`):**
- `/simplify` flagged that the new Step 5 item 3 in `plan-feature/SKILL.md` duplicated ~70 words of `references/interview-rules.md` content. Collapsed item 3 to a one-line pointer and stripped the leaked `"Other"` qualifier from item 5 — net –2 lines, restores the SKILL.md ↔ references/ separation the skill was designed around. Confirmed clean by a follow-up `/code-review`. `/code-cleanup` was invoked but declined to run — this repo has no code stack, so 6 of 7 cleanup categories don't apply; surfaced the judgment to the user instead of burning subagents.

### Session 15 - 2026-04-16
**What happened:**
- User asked whether the Opus 4.7 launch (same day) warranted any repo changes. **Refused to speculate** without verified docs — fetched the Anthropic news post (anthropic.com/news/claude-opus-4-7), the Claude Code CHANGELOG (raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md), and the skills-frontmatter docs page (code.claude.com/docs/en/skills) before recommending anything. Confirmed: 4.7 is GA, same pricing as 4.6 ($5/$25), `xhigh` effort level new, `/ultrareview` shipped in CC 2.1.111, `effort:` skill frontmatter field accepts `low|medium|high|xhigh|max`.
- **Discussed retiring `/code-review` in favor of built-in `/ultrareview`.** Read both surfaces before recommending. Concluded they're complementary: `/code-review` keeps `--security`/`--verify`/`--fix` + in-session speed + convention detection; `/ultrareview` is multi-agent cloud verification for high-stakes pre-merge (10-20min). Decision: keep both, document the split.
- **Shipped 5-file alignment edit (no commit yet — left for user):**
  1. `.claude/skills/code-review/SKILL.md` — added `effort: high` to frontmatter; description now positions skill vs `/ultrareview`.
  2. `.claude/skills/plan-feature/SKILL.md` — added `effort: high` to frontmatter.
  3. `README.md` — updated commands table row for `/code-review`; added blockquote explaining when to use `/ultrareview` instead.
  4. `docs/key-decisions.md:45` — Sonnet-pin row updated to note 4.7 re-evaluation with verified pricing parity.
  5. `workflow.md` — added Apr 2026 version-history row; bumped "Last updated" stamp.
- **Dropped the Session 12 `defer` hook dogfood task entirely.** Carried 12→13→14→15. User chose retirement over verification. Pre-shipment: removed the "still pending" carry-forward bullet from Session 14's CLAUDE.md summary; deleted task #1 from the live tracker. README recipe at line 177 left in place untested.
- Used `AskUserQuestion`-style confirmation pattern from `/plan-feature` Session 14 work (verified what to ship before editing). Saved a round-trip vs the old "edit first, ask later" pattern.
- **Designed and shipped a session-history rollup pattern.** User flagged that `session-history.md` grows unboundedly and asked for a strategy. Picked the "compress sessions older than the 5 most recent into one-liners with commit hashes" approach (Option A from a 3-option discussion). Implemented in two parts:
  1. Added Part 6 to `mode-update.md` that auto-rolls-up on every `/update-docs` run (with `--skip-rollup` escape). Updated `update-docs/SKILL.md` argument-hint and `verification-checklists.md`.
  2. One-time pass on Sessions 1-10: replaced ~215 lines of full-prose entries with 10 one-liners, each carrying the architectural headline + commit hashes. File shrank from 27.7KB → 22.0KB (-21%). Future runs will compress more as new sessions push older ones past the 5-session window.
  3. **Added Step 6.2 first-run confirmation gate** after user asked whether the skill would auto-compress other projects' session-history files (it would). Now: on the first rollup pass per-project, the user is prompted before compression; the rollup-format note added in Step 6.4 serves as the per-project sentinel so subsequent runs skip the prompt. `AskUserQuestion` added to `update-docs` allowed-tools (mirrors the `plan-feature` Session 14 pattern).

**Files created/modified:**
- `.claude/skills/code-review/SKILL.md` — added `effort: high`; description rewritten to position vs `/ultrareview` (+1 line, ~2 lines reworded)
- `.claude/skills/plan-feature/SKILL.md` — added `effort: high` (+1 line)
- `README.md` — `/code-review` table row expanded; new blockquote on `/ultrareview` (+3 lines)
- `docs/key-decisions.md` — Sonnet-pin row reworded for 4.7 re-evaluation (~2 lines)
- `workflow.md` — Apr 2026 version row + "Last updated" bump (+3 lines)
- `CLAUDE.md` — removed defer-hook carry-forward bullet from Session 14 summary (-1 line); will be updated again by this `/update-docs` run with Session 15 summary + 3 new key decisions
- `docs/completed-work.md` — appended Session 15 entries (this run)
- `docs/session-history.md` — this entry + one-time rollup of Sessions 1-10 to one-liners + new "compressed format" note in header (this run)
- `docs/key-decisions.md` — appended 4 Session 15 decision rows + 1 row for the rollup pattern (this run)
- `.claude/skills/update-docs/SKILL.md` — added `--skip-rollup` to argument-hint
- `.claude/skills/update-docs/references/mode-update.md` — appended Part 6 (Roll Up Old Sessions) after Part 5
- `.claude/skills/update-docs/references/verification-checklists.md` — added rollup checkbox to UPDATE mode checklist

**Files NOT modified (and why):**
- `.claude/agents/cleanup-*.md` — Sonnet pin still cost-justified at 4.7 (same pricing as 4.6).
- README.md `defer` hook recipe at line 177 — left untested per the drop-defer-dogfood decision; user accepted the small risk it's subtly wrong.
- No actual `/ultrareview` adoption work — that's a runtime tool, not config; nothing to ship in the repo.

**Next session should:**
- Pick up Next Steps #3 (pre-commit hooks) or #4 (MCP integration) — both still pending in task tracker.
- Consider whether the `/effort` slider (CC 2.1.111) being interactive means the per-skill `effort: high` should ever be downgraded — probably no, because the frontmatter is the deliberate per-skill override and the slider is a session-level convenience.
- If a real high-risk PR comes up, actually try `/ultrareview` and compare with custom `/code-review --security --verify` to see whether the README positioning blockquote needs refining.
- Watch for the next `/update-docs` run to confirm Part 6 fires correctly: as Session 16 is added, Session 11 (currently the 5th-most-recent) should get auto-compressed to a one-liner. If Part 6 misfires (e.g., picks bad commit hashes), refine the heuristic in `mode-update.md` Step 6.2.

### Session 16 - 2026-04-17
**What happened:**
- User reported a real `/update-docs` run taking ~20 minutes on one of their other projects. Asked how to improve perf without losing functionality.
- Audited `update-docs/SKILL.md` and `mode-update.md` to identify hotspots. Three main drivers: (1) skill had no `effort` pin so it ran at session default (Opus 4.7 for the user), (2) Part 3 walks `docs/*.md` sequentially, (3) Part 6 rollup runs one `git log --since/--until` per compressible session.
- Recommended fixes; user said "do all." Confirmed that `effort:` in skill frontmatter is invocation-scoped — the harness applies it for the skill duration and reverts to session default on return, so no programmatic toggling is needed.
- **Shipped three edits in `/update-docs`:**
  1. `.claude/skills/update-docs/SKILL.md` — added `effort: low` to frontmatter (mirrors the `effort: high` pattern from Session 15's `/code-review` and `/plan-feature`).
  2. `.claude/skills/update-docs/references/mode-update.md` — new **Part 3.0 "Batch Read All Doc Files in Parallel"** preamble directing a single `Glob docs/**/*.md` + parallel `Read` (one tool call per file, same turn) + batched Edits. Replaces sequential read-analyze-edit.
  3. `.claude/skills/update-docs/references/mode-update.md` — rewrote **Part 6.3 step 2** to pre-fetch one `git log --since="<earliest>" --until="<latest>+1d" --pretty=format:'%h %ad %s' --date=short` across the full compressible date range, then slice per-session in memory. Replaces N sequential git calls with 1.
- User then asked to sweep the other 4 skills. Presented a table with recommendations:
  - `/code-review` keeps `effort: high` (reasoning-heavy, Session 15).
  - `/plan-feature` keeps `effort: high` (interview synthesis, Session 15).
  - `/update-docs` keeps just-added `effort: low`.
  - Recommended `/resume-work` → `low` (read docs + git + hydrate tasks = mechanical).
  - Recommended `/code-cleanup` orchestrator → `low` (real work in Sonnet subagents).
- User approved `/resume-work` only. `/code-cleanup` left at session default per explicit instruction. Shipped `effort: low` on `resume-work/SKILL.md:5`.
- Flagged to user that the CLAUDE.md Key Decisions row stating "Mechanical skills keep session default" was now partially outdated and would be refreshed by this `/update-docs` run.
- **Dogfood note:** this `/update-docs` run is the first one exercising the new Part 3.0 parallel batch-read and Part 6.3 batched `git log`. Part 6 correctly identified Session 11 as the now-5th-oldest and compressed it using the two `2026-03-17` commits from the pre-fetched log. Subjective sense: run felt noticeably faster than Session 15's despite comparable scope (multi-file doc updates + one rollup).

**Files created/modified:**
- `.claude/skills/update-docs/SKILL.md` — `effort: low` added to frontmatter (+1 line)
- `.claude/skills/update-docs/references/mode-update.md` — Part 3.0 preamble added before 3.1-3.4 (+10 lines); Part 6.3 step 2 rewritten to use a single batched `git log` (~5 lines changed)
- `.claude/skills/resume-work/SKILL.md` — `effort: low` added to frontmatter (+1 line)
- `CLAUDE.md` — bumped Last Updated to 2026-04-17, rewrote the Session 15 `effort: high` Key Decisions row to reflect current pins, added a new row for the Part 3/Part 6 parallelization, replaced Session 15 last-session summary with Session 16 (this run)
- `docs/session-history.md` — Part 6 auto-rollup compressed Session 11 to one-liner; this entry appended (this run)
- `docs/completed-work.md` — Session 16 entries appended (this run)
- `docs/key-decisions.md` — 2 Session 16 decision rows appended (this run)

**Files NOT modified (and why):**
- `.claude/skills/code-cleanup/SKILL.md` — user explicitly declined the `effort: low` pin for the orchestrator. Stays at session default.
- `.claude/skills/code-review/SKILL.md`, `.claude/skills/plan-feature/SKILL.md` — `effort: high` from Session 15 confirmed still correct (reasoning-heavy work).
- `README.md`, `workflow.md` — skill behavior is unchanged from the user's perspective (same commands, same outputs, just faster). No user-facing doc change warranted.
- `.claude/agents/cleanup-*.md` — no subagent changes this session.

**Next session should:**
- If anyone runs `/update-docs` on a real project again, observe actual wall-clock delta vs the 20-min baseline. If still slow, consider scoping Part 3 to `git diff --name-only` (small functionality trim — won't catch drift in untouched docs).
- Pick up Next Steps #3 (pre-commit hooks) or #4 (MCP integration) — both still pending in task tracker from prior sessions.
- Session 12 becomes the 6th-most-recent when Session 17 arrives → it'll be the next compressible entry. Watch the Part 6.3 batched `git log` path on that run to confirm the new approach picks correct commit hashes.

### Session 17 - 2026-04-21
**What happened:**
- User asked for a review of the `/resume-work` + `/update-docs` skill pair and specifically how to stop CLAUDE.md from growing unboundedly every session-end cycle. User reported Claude Code was starting to warn about CLAUDE.md size on real projects.
- Audited both skills end-to-end (SKILL.md + all references). Root-cause diagnosis: the existing rules said "keep ~20 Key Decisions, 17k char target, 3-5 bullets for last-session" but `update-docs` only emitted *passive warnings* at thresholds. Adding a row is mechanical; pruning requires judgment ("which is least important?") that the model defers on under `doc-structure-rules.md`'s "NEVER remove... when in doubt, keep it" rule. Evidence: this very CLAUDE.md had drifted to ~36 Key Decisions rows despite the ~20 cap documented since Session 1.
- Also caught a pre-existing structural issue: the old Part 5 (commit checkpoint) was not actually last — the Session 15 rollup was appended as Part 6 *after* the commit checkpoint, so rollup changes landed uncommitted until next run.
- **Proposed and shipped two features in one commit (`a8c99ba`):**
  1. **Part 1.10 Cap Enforcement** — active per-section caps. Current Status ≤10 (collapses consecutive `Complete` runs into a summary row, with the individual rows landing in `docs/completed-work.md` first). Next Steps ≤10 (warn only — accretion is a signal, not a storage problem). In Progress ≤5 (warn only — fragmented work means stalled tasks). Gated by `--skip-caps`.
  2. **Part 6 Key Decisions Rollup** — mirrors the Part 5 session-history rollup exactly. FIFO move of oldest CLAUDE.md table rows (topmost in the table) into `docs/key-decisions.md` when count > 20. First-run gated by `AskUserQuestion` consent, with a sentinel note (`Entries older than the 20 most recent in CLAUDE.md are rolled up here`) added to the reference file for silent subsequent runs. Chose FIFO over "least important" explicitly — the judgment-avoidance of "least important" is what caused the bloat in the first place. Gated by `--skip-decisions-rollup`.
- Reordered the Parts so the commit checkpoint is truly last: old Part 6 (session-history rollup) → Part 5; new Part 6 = Key Decisions rollup; old Part 5 (commit checkpoint) → Part 7. This closes the Session 15 bug where rollup changes ended up uncommitted.
- Strengthened `doc-structure-rules.md` with a new "Pruning Is Preservation" subsection. Explicit doctrine: when CLAUDE.md would otherwise exceed targets, moving content to its designated reference file *is* the correct preservation action, not an exception to it. Prevents the model from interpreting "NEVER remove" to mean "never prune from CLAUDE.md" next time around.
- **Dogfood this same session** — this `/update-docs` run is the first exercise of the new Part 6. CLAUDE.md's Key Decisions table had 38 rows after Session 17's additions; Part 6 detected the overflow, fired the first-run `AskUserQuestion` consent prompt (no sentinel note in `docs/key-decisions.md` yet), user accepted, moved the oldest 18 rows to the reference file via FIFO. Added the sentinel note so future runs go silent. CLAUDE.md's Key Decisions table now back to the 20-row target. Duplicate-with-existing-detail-rows tradeoff accepted per the contract ("do not deduplicate — harmless").
- **Part 5 (session-history rollup) also fired** — after Session 17 was appended, Session 12 (2026-04-11) became the 6th-most-recent. Compressed to a one-liner using the batched `git log --since="2026-04-11" --until="2026-04-12"` path from Session 16; picked the two Session 12 commits. Confirmed the batched `git log` approach works as designed for first-time compression of a single session.

**Files created/modified:**
- `.claude/skills/update-docs/references/mode-update.md` — added Part 1.10 (cap enforcement) after Part 1.9; inserted new Part 6 (Key Decisions rollup) mirroring Part 5's structure; renamed old Part 6 (session-history rollup) to Part 5 and updated internal references; renamed old Part 5 (commit checkpoint) to Part 7 and added the explicit "runs last so rollups are in the same commit" note (+110 insertions, -29 removals)
- `.claude/skills/update-docs/SKILL.md` — extended `argument-hint` with `--skip-caps` and `--skip-decisions-rollup` (+1 line)
- `.claude/skills/update-docs/references/verification-checklists.md` — added 3 UPDATE-mode checklist items (cap enforcement, key-decisions rollup, commit-last ordering) (+3 lines)
- `.claude/skills/update-docs/references/doc-structure-rules.md` — new "Pruning Is Preservation" subsection with explicit doctrine for cap enforcement and rollups (+10 lines)
- `CLAUDE.md` — bumped Last Updated to 2026-04-21 (Session 17); added 2 new Key Decisions rows (cap enforcement + rollup); replaced Session 16 last-session block with Session 17; then Part 6 rolled up the oldest 18 rows to `docs/key-decisions.md`
- `docs/session-history.md` — this entry; Part 5 rollup compressed Session 12 to a one-liner
- `docs/key-decisions.md` — received the 18 rolled-up rows from CLAUDE.md (appended via FIFO, no dedup) + the sentinel note added to the header block
- `docs/completed-work.md` — 4 Session 17 completion entries

**Files NOT modified (and why):**
- `README.md`, `Workflow.md` — no user-visible command or workflow change. The new `--skip-caps` and `--skip-decisions-rollup` flags are documented in the skill's `argument-hint`, which is surfaced inline by the harness when the skill is invoked. README's commands table already says "see the skill" for flag detail.
- `.claude/skills/resume-work/` — user asked for a review of both skills; the actual shipped changes were all in `/update-docs`. Recommended `/resume-work` improvements (git window since CLAUDE.md Last Updated, auto-memory diff-before-write, task hydration stricter filter, Step 6 cross-skill path fragility) were explicitly deferred — bloat was the primary problem, everything else is polish.
- `.claude/agents/cleanup-*.md` — no subagent changes this session.
- Auto-memory MEMORY.md — no stable-facts changed (no new skills, no structural shifts, no tech stack change). Rule 4.3.4 skip condition met.

**Next session should:**
- Observe the dogfood outcome — specifically, whether `docs/key-decisions.md` has become unwieldy with the 18 rolled-up condensed rows alongside the pre-existing detailed versions. The contract explicitly says "do not dedupe" because dedup requires judgment, but if the reference file is now cosmetically messy, a future session could add a one-time manual pass. Not worth automating.
- Pick up any of the four remaining Next Steps items if they become concrete: pre-commit hooks (#3) or MCP integration (#4) are the most actionable; #1 ("add more skills as needs emerge") and #2 ("improve reference files based on usage patterns") are aspirational.
- Consider whether Part 0.5's one-time migration is now redundant with Part 1.10 + Part 6 and can be simplified or removed. It would only trigger on a truly legacy project, but the heuristics overlap meaningfully.
- If `/resume-work` polish becomes a priority, the four items flagged in Session 17's review still apply: (a) git log window scaled by CLAUDE.md Last Updated date rather than fixed `-10`, (b) auto-memory diff-before-write in update-docs Part 4, (c) stricter aspirational-task filter in task-hydration.md, (d) Step 6 cross-skill path is fragile (works via symlink today, should either copy or hardcode the section contract).

### Session 18 - 2026-05-04
**What happened:**
- User reported `/update-docs` runs taking 12-14 min on real projects despite Session 16's `effort: low` + Part 3.0 (parallel doc reads) + Part 6.3 (batched `git log`) perf work. Asked how to optimize without sacrificing functionality.
- Audited `mode-update.md` (488 lines, 7 Parts plus pre-steps). Diagnosis: every run walks all parts sequentially regardless of need; reference reads scatter across 5-6 turns; no fast path for the daily-cycle case where only Parts 0, 1, and 7 actually have work. Most parts no-op on a daily cycle: 0.5 (migration, one-time per project), 4 (memory, only if facts change), 5/6 (rollups, only past thresholds), 1.10 (caps, only if over).
- Discussed levers ranked by impact, then narrowed to the user-approved set:
  1. **`--fast` mode** for the daily-cycle case (drain → CLAUDE.md updates → drift probes → commit; skips Parts 0.5/2/3/4/5/6/1.10). Surfaces drift via warnings, doesn't enforce.
  2. **Step 0 upfront parallel batch** — single parallel turn reads CLAUDE.md, README, all `docs/*.md`, MEMORY.md, plus runs `git log -20`, `git diff --stat HEAD~5`, `git status`, and `TaskList`. Drives every downstream decision. Replaces 5-6 sequential read turns. Benefits both paths.
  3. **Plan-then-batch CLAUDE.md edits** — gather all changes from Parts 1.0–1.10 (and Part 6 row removals) from Step 0 evidence, then apply as one Write or non-overlapping parallel Edits. Fast Path uses this by definition; Full Path opts in via the new Part 1 preamble.
  - Deferred levers (revisit if measurement shows insufficient): #4 lazy-load heavy parts of `mode-update.md` (split rollups/migration into separate ref files), #5 evidence-driven Part 1 sub-sections (skip 1.X if no relevant evidence).
- Confirmed in writing that nothing trims `--full`: every Part 0–7 still runs, every probe still fires, both first-run consent gates (Parts 5 and 6) intact, caps enforcement intact, auto-memory sync intact, README/`docs/*.md` sweep intact. Optimizations are pure orchestration — same data, same final state, fewer turns.
- **Shipped (uncommitted, this session):**
  1. `update-docs/SKILL.md` — added `--fast` to `argument-hint` (1-line change).
  2. `update-docs/references/mode-update.md` — prepended Step 0 (Upfront Parallel Batch), Step 0.1 (Path Routing), Fast Path block (+77 lines) before existing Step 1.
  3. `update-docs/references/mode-update.md` — added plan-then-batch preamble at start of Part 1 (+2 lines).
- **Dogfooded `/update-docs --fast`** as the session-end run for Session 18 itself — this entry is the output. The Fast Path correctly: (a) ran Step 0 batch (parallel reads + git + TaskList in one turn), (b) routed to Fast Path on the `--fast` flag, (c) found empty TaskList → skipped Part 0 work, (d) identified evidence for Parts 1.0/1.6/1.8 only, (e) ran drift probes against the cached file contents (no extra reads), (f) batched the 3 CLAUDE.md edits + 2 reference-file appends into a single parallel-Edit turn. Subjective: noticeably faster than Session 17's run, dominated by the upfront parallel-batch turn. Real measurement requires a side-by-side comparison on a non-trivial project.
- **Drift surfaced by Fast Path probes (the safety valve in action — these are exactly what `--fast` is designed to flag rather than enforce):**
  - **1 multi-line session ready for Part 5 rollup**: after Session 18 lands, Session 13 becomes the 6th-most-recent multi-line entry → compressible.
  - **Key Decisions table at 21 rows** (cap 20): 1 over after this session's append.
  - **2 prior-session commits undocumented**: `14546ff` (2026-04-22, "interop polish: if-scoped defer hook, auto mode doc, startup guardrail") and `ff89cbb` (2026-04-22, "code-review: parallelize --verify via early background kickoff"). Real feature work that touched README, `start-claude.{sh,ps1}`, and `code-review/SKILL.md`. Was flagged by `/resume-work` at session start; not handled by Fast Path by design.
  - **CLAUDE.md size**: still well under the 35k soft cap, no warning needed.
  - All four items will clear on the next `--full` sweep.

**Files created/modified:**
- `.claude/skills/update-docs/SKILL.md` — added `--fast` to argument-hint (~+10 chars within the existing line)
- `.claude/skills/update-docs/references/mode-update.md` — prepended Step 0 + Step 0.1 + Fast Path block (+77 lines); added plan-then-batch preamble at start of Part 1 (+2 lines)
- `CLAUDE.md` — bumped Last Updated to 2026-05-04 (Session 18); added 1 Key Decisions row covering Fast Path + Step 0 batch + plan-then-batch; replaced Session 17 last-session block with Session 18 (this run)
- `docs/session-history.md` — this entry (this run)
- `docs/key-decisions.md` — appended 1 detailed Session 18 decision row (this run)

**Files NOT modified (and why):**
- `README.md`, `Workflow.md` — no user-visible command or workflow change beyond `--fast` which lives in the skill's `argument-hint` (surfaced inline by the harness on invocation). README's commands table already says "see the skill" for flag detail. The 2 undocumented prior-session commits will pull README/Workflow.md into the next `--full` sweep if they need updates there.
- `docs/completed-work.md` — Fast Path skips Part 1.3 by spec. Drift warning didn't include this because completed-work churn is captured by session-history.md anyway. **Possible Fast Path spec refinement (defer for now):** if the divergence between session-history.md and completed-work.md becomes annoying after a few cycles, add Part 1.3 to the Fast Path subset (a single Edit per completed item — cheap).
- The 2 undocumented commits (`14546ff`, `ff89cbb`) — flagged in drift warning, deferred to `--full` sweep per Fast Path's design intent. Documenting them in Fast Path would conflate "current session's work" with "backfill from prior unlogged sessions" — that conflation is exactly what `--full` is for.
- `.claude/agents/cleanup-*.md` — no subagent changes this session.
- Auto-memory `MEMORY.md` — no stable-facts changed (no new skills, no structural shifts, no tech stack change). Part 4 is anyway skipped in Fast Path; rule 4.3.4 skip condition would have applied in Full Path too.

**Next session should:**
- Run `/update-docs` (no flag, full path) when convenient to (a) sweep the 2 undocumented commits `14546ff` + `ff89cbb` into `docs/`, (b) trigger Part 5 rollup of Session 13 to a one-liner, (c) trigger Part 6 Key Decisions rollup of the 1-over-cap row to `docs/key-decisions.md`, (d) verify README/Workflow.md don't have other un-swept drift from prior commits.
- Measure actual wall-clock of `/update-docs --fast` on a real project against the 12-14 min baseline. If still slow, consider implementing the deferred levers: #4 (split `mode-update.md` so Parts 5/6/0.5 only load when their probes trigger) and #5 (evidence-driven Part 1 sub-sections in Full Path — skip 1.X when no commits/tasks/user-input touch that section).
- If drift accumulates faster than weekly `--full` runs can keep up in practice, refine the Fast Path subset: add Part 1.3 (completed-work append) as the most likely candidate. Low-cost amendment to `mode-update.md` Fast Path block.
- Pick up Next Steps #3 (pre-commit hooks) or #4 (MCP integration) — both still pending from prior sessions, both more concrete than the aspirational #1/#2.

### Session 19 - 2026-05-04
**What happened:**
- Ran `/update-docs` (Full Path, no flag) immediately after Session 18's `--fast` run as a back-to-back dogfood: validate that the new Step 0 upfront batch + Part 1 plan-then-batch directive also speed up the comprehensive sweep, and clear the 4 drift items `--fast` had surfaced.
- Drift to clear:
  1. **Backfill 2 undocumented commits from 2026-04-22** — `14546ff` (interop polish: `if`-scoped defer hook example, README auto mode compatibility paragraph, startup-script `disableSkillShellExecution` guardrail, CI gating prose trim) and `ff89cbb` (code-review --verify parallelization via `run_in_background` in Step 1.5).
  2. **Part 5 session-history rollup** — Session 13 became the 6th-most-recent multi-line entry after Session 18 landed.
  3. **Part 6 Key Decisions rollup** — CLAUDE.md table at 21 rows after Session 18's add (cap 20).
  4. **Part 1 sub-section caps** — none triggered; Current Status, Next Steps, In Progress all under cap.
- Step 0 batch: 1 parallel turn for `git show 14546ff --stat` + `git show ff89cbb --stat` + `git status` + `TaskList`. Reads were already cached from Session 18's run earlier in this same conversation, so no re-reads needed (per the "hold all results in working memory for the rest of this run" rule). On a fresh session the Step 0 batch would also include reads of CLAUDE.md, README.md, all `docs/*.md`, MEMORY.md.
- Inspected the 2 backfill commits before writing Key Decisions rows: confirmed they're architecturally distinct (one is interop refinement across multiple files, one is a perf optimization on a single skill) and warrant separate rows. README's interop section already reflects `14546ff`'s changes (it's the same commit that wrote them), so Part 2 verifies-and-no-ops.
- **Plan-then-batch execution:** all 8 file edits batched into a single parallel-Edit turn:
  1. `CLAUDE.md` — Last Updated S18 → S19
  2. `CLAUDE.md` — Part 6 FIFO removal of 3 oldest Key Decisions rows
  3. `CLAUDE.md` — Part 1.6 add 2 backfill rows after Session 18 row
  4. `CLAUDE.md` — Part 1.8 replace Session 18 last-session block with Session 19
  5. `docs/session-history.md` — Part 5 compress Session 13 multi-line block to one-liner
  6. `docs/session-history.md` — Part 1.8 append Session 19 detailed entry (this entry)
  7. `docs/key-decisions.md` — append 3 rolled-up rows + 2 detailed new rows
  8. `docs/completed-work.md` — append entries for the 2 backfilled commits + Session 19 sweep
- **Both first-run consent gates skipped silently.** Sentinel notes were added to `docs/session-history.md` (Session 15) and `docs/key-decisions.md` (Session 17), so Parts 5.2 and 6.2 detected the per-project consent and proceeded without prompting. Confirmed the sentinel pattern works as designed across multiple runs.
- **Part 4 (auto-memory)** — skipped per rule 4.3.4: no stable-fact change since Session 18 (no new tech stack, no structural shifts, no architecture change). MEMORY.md content unchanged.
- **Performance observation:** the entire Full Path run (Step 0 batch + plan + 8 batched Edits + commit prep) completed in ~3 turns of substantive tool calls. This is far below the 12-14 min baseline the user reported on real projects, but this is a small project running back-to-back with `--fast` (most reference reads were cached), so it's a best-case measurement. A side-by-side run on a non-trivial project still owed for a real comparison.

**Files created/modified:**
- `CLAUDE.md` — Last Updated 2026-05-04 (Session 19); Part 6 removed 3 oldest Key Decisions rows; Part 1.6 added 2 backfill rows for `14546ff` and `ff89cbb`; Part 1.8 replaced Session 18 last-session block with Session 19. Net table size: 21 - 3 + 2 = 20 rows (back at cap).
- `docs/session-history.md` — Part 5 compressed Session 13 multi-line block (~35 lines) to one-liner with commit hashes; appended this Session 19 detailed entry.
- `docs/key-decisions.md` — appended 3 rolled-up rows from CLAUDE.md (no dedup per spec) + 2 detailed rows for `14546ff` interop polish and `ff89cbb` --verify parallelization.
- `docs/completed-work.md` — 6 new entries: 4 for `14546ff` (README defer/auto mode docs, startup-script guardrail, code-cleanup/code-review CI prose trim), 1 for `ff89cbb` (--verify parallelization), 1 for the Session 19 Full Path validation run itself.

**Files NOT modified (and why):**
- `README.md` — interop section is already current; `14546ff` was the commit that wrote the modernized defer recipe + auto mode paragraph + startup-script guardrail note. Part 2 verifies and no-ops.
- `Workflow.md` — no user-visible workflow change.
- `.claude/skills/*/SKILL.md` — no skill-behavior change this session; the changes from `14546ff`/`ff89cbb` were already in the skill files (committed at the time).
- `.claude/agents/cleanup-*.md` — no subagent changes this session.
- Auto-memory `MEMORY.md` — Part 4 skipped per rule 4.3.4 (no stable-fact change since Session 18).

**Next session should:**
- Run `/update-docs --fast` on a non-trivial real project (one that actually takes 12-14 min today) and measure the wall-clock delta. That's the only test that proves the perf claims at scale. If still slow, implement the deferred levers from Session 18: split `mode-update.md` so Parts 5/6/0.5 lazy-load (only when their probes trigger) and gate Part 1 sub-sections on evidence (skip 1.X if no commits/tasks/user-input touch that section).
- Watch the next `/update-docs --fast` run for completed-work.md drift. Session 18's spec deferred Part 1.3 from Fast Path, which means completed-work.md only updates on `--full` runs. If the divergence between session-history.md and completed-work.md becomes annoying after a few cycles, add Part 1.3 to the Fast Path subset (single Edit per item, cheap).
- Pick up Next Steps #3 (pre-commit hooks) or #4 (MCP integration) — both still pending from prior sessions and more concrete than the aspirational items.
- Consider whether the back-to-back `--fast` then `--full` pattern is itself worth documenting in Workflow.md as the recommended cadence (`--fast` daily, `--full` end-of-week). Currently implicit in the design but not surfaced to the user.
