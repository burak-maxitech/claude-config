# CLAUDE.md

Last Updated: 2026-05-08 (Session 22)

## Project Overview

**claude-config** — Personal Claude Code configuration repo containing custom skills, subagents, and workflow documentation.

- **Repo:** [burak-maxitech/claude-config](https://github.com/burak-maxitech/claude-config) (private)
- **README.md** — Public overview, setup instructions, command reference
- **Workflow.md** — Detailed personal workflow guide (daily workflow, scenarios, tips)
- **docs/** — Reference files (session history, key decisions, completed work)

## Current Status

| Area | Status |
|------|--------|
| Skills (7) | Complete |
| Subagents (7) | Complete |
| Startup scripts | Complete |
| Cross-platform setup | Complete |
| GitHub sync | Complete |
| Documentation | Complete |

## Completed

All 7 skills, 7 subagents, cross-platform setup, and documentation system are complete.

See [docs/completed-work.md](docs/completed-work.md) for full checklist.

## In Progress

Nothing currently in progress.

## Next Steps

1. **Dogfood `/architecture-review` on a non-trivial real project** — never run end-to-end yet. Watch for linter-detection accuracy, intended-architecture summary quality, CCN-delta filter behavior, simplification false-positive rate
2. **Dogfood `/code-health-advice`** — built S22 but never invoked end-to-end. Watch for: bucket misclassification rate, freshness-mismatch detection accuracy, cases where a 6th bucket would help
3. Add more skills as new workflow needs emerge
4. Improve existing skill reference files based on usage patterns
5. Consider adding hooks for automated pre-commit workflows
6. Explore MCP server integration for external tool access

## Key Decisions

| Decision | Rationale |
|----------|-----------|
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
| Active CLAUDE.md cap enforcement (Session 17) | `/update-docs` now runs Part 1.10 every UPDATE: Current Status ≤10 (collapses `Complete` runs), Next Steps ≤10 (warn), In Progress ≤5 (warn). Replaces passive 35k-char warning with active per-section caps. Gated by `--skip-caps`. Root-cause fix for CLAUDE.md growing unboundedly across sessions despite "keep ~20 max" guidance — adding was mechanical, pruning required judgment the model deferred on. |
| Key Decisions rollup + commit-last ordering (Session 17) | Mirrors the session-history rollup. New Part 6 in `update-docs/mode-update.md`: when CLAUDE.md's Key Decisions table > 20 rows, oldest (topmost = FIFO) rows move to `docs/key-decisions.md`. First-run `AskUserQuestion` consent gate with sentinel note in the reference file for silent subsequent runs. Gated by `--skip-decisions-rollup`. Commit checkpoint moved to Part 7 (last) so both rollups land in the same commit. "Pruning is preservation" codified in `doc-structure-rules.md` as canonical backing. |
| `/update-docs --fast` + Step 0 upfront batch + plan-then-batch (Session 18) | Daily `/update-docs` was still 12-14 min despite Session 16's `effort: low`. Fast Path runs the daily subset (drain → CLAUDE.md updates → drift probes → commit) and skips Parts 0.5/2/3/4/5/6/1.10. Step 0 collapses 5-6 sequential read turns into 1 parallel turn (benefits both paths). Plan-then-batch turns 10 per-section Edits in Part 1 into one Write. **No functionality trimmed from `--full`.** Drift warnings are the safety valve: Fast Path surfaces accumulated debt instead of enforcing. Verified by dogfooding `/update-docs --fast` this session. |
| Interop polish (commit `14546ff`, 2026-04-22; backfilled S19) | Modernized README defer recipe to use the 2.1.85 `if` field (e.g. `"if": "Bash(rm:*)"`) so PreToolUse `defer` only fires for matching tool calls, refining the existing CI-gating recipe. Added README auto mode compatibility paragraph (2.1.83+ classifier behavior + `PermissionDenied` hook fallback added 2.1.89). Startup scripts now warn when `disableSkillShellExecution=true` in user settings (would silently break `--fix`/`--verify`/`deep`). |
| Parallelize `/code-review --verify` (commit `ff89cbb`, 2026-04-22; backfilled S19) | Step 1.5 launches test/lint with `run_in_background` so they complete during review work (Steps 2-4); Step 5 collects output instead of running synchronously. Saves ~10-60s per `--verify` invocation on projects with non-trivial test suites. Mirrors the parallelization pattern from `/update-docs` Part 3.0 (Session 16). |
| `/code-cleanup` references — git ls-files + batched Grep + monorepo workspaces (Session 20) | Usage-pattern improvements per Next Steps #2. (1) **Perf:** `git ls-files` over `find` (honors `.gitignore` natively); per-item grep loops collapse into single batched `Grep` calls with regex alternation (`\b(name1\|name2\|...)\b` + `output_mode: count`). (2) **Coverage:** `scan-deps-config.md` detects npm/yarn/pnpm/Cargo workspaces, scans each child manifest separately, tags findings with workspace name; new "Misplaced Dependencies" output section. SKILL.md Step 0 surfaces monorepo state in the "Detected:" line. (3) **Mid-edit correctness fix:** literal `rg ...` shell-command examples → `Grep` tool syntax — the cleanup-* agents have `Bash(grep:*)` not `Bash(rg:*)`, and runtime guidance pins use of the `Grep` tool. |
| New `/architecture-review` skill — three guardrails against pattern-mongering (Session 21) | Acted on Next Steps #1 (add new skills). Distinct from existing diff-scoped reviewers (`/code-review`, `/simplify`, `/ultrareview`) and deletion-focused `/code-cleanup`. Three guardrails came out of the planning interview: (1) **Reframe patterns as complexity-reducing refactors.** GoF patterns often *hide* complexity behind indirection (Strategy = switch + class hierarchy + registry). Catalog (`refactor-catalog.md`) is technique-driven (guard clauses, pure-function extraction, flag-arg removal, discriminated unions, table lookup); GoF patterns appear only with strict "detect when" gates (R13 Strategy requires 4 conditions). (2) **Read intended architecture first.** Step 1 reads CLAUDE.md / README / `docs/architecture/` / ADRs to summarize project's *intended* arch; subagents flag findings conflicting with documented decisions as `respects_documented_decision: false` and surface them in a separate report section requiring user confirmation. Prevents "you should have a domain layer" against projects that chose flat structure. (3) **CCN delta sanity gate.** Each finding has `ccn_current` (from detected linter — eslint/ruff/radon/lizard, fall back to Grep heuristic) and `ccn_projected`; orchestrator drops findings where projected ≥ current. Decomposition: 3 parallel Sonnet subagents (arch-structure / arch-refactors / arch-performance). Scale tiers: <100=full, 100-500=bounded, >500=smart sample (LOC × churn × import fan-in). `--fix` restricted to single-file non-API-breaking; cross-file auto-routes to `--plan`. Skill count 5→6, subagent count 3→6. |
| 4th dimension: `arch-simplification` over-engineering scanner (Session 21 mid-session extension) | Audit against user's three real goals (optimized / maintainable / least-code-possible) found a gap — original 3 dimensions covered maintainability and partially optimization, but the refactor catalog *trades* complexity (decompose god function = readability ↑, LOC flat) and didn't have a deletion bias. New `arch-simplification` subagent (4th parallel dispatch) targets *almost-dead* and *speculatively-built* code at sub-file granularity (vs `/code-cleanup` which targets whole-file deletion): single-impl interfaces (S01), pass-through wrappers (S02), always-same parameters (S03), unread/same-value config (S04/S05), defensive code for impossible static states (S06), speculative generics (S07), near-duplicate functions (S08), unused exported symbols (S09). Every finding mandatorily reports `lines_deletable >= 1`. Report renders **Code we can delete: N lines across M files** as the first line, before the architecture map — making "least code possible" a primary signal. Rank score factors `log(lines_deletable + 1)` so big deletions float up. Quick-wins phase puts simplification findings ahead of refactors. `--fix` eligible: S04 (single-file), S06 (always single-file), S09 (when symbol body in one file, no importers); rest auto-route to `--plan`. False-positive guards built into the catalog: test seams (mocks legitimize abstractions), boundary types (Adapter/Mapper wrappers legitimate), recently-added abstractions (<30 days, second impl may be in flight). Subagent count 6→7. |
| New `/code-health-advice` skill — read-only routing advisor (Session 22) | Gap surfaced when user asked for a skill-ordering guide: existing skills cover specific scopes (`/simplify` = recent changes, `/code-review` = diff, `/code-cleanup` = deletion, `/architecture-review` = structure), but nothing helps decide *which* to reach for given current repo state. Built `/code-health-advice` as a pure router. Reads `git status`, branch, recent commits, ahead/behind counts, `gh pr view`, `CLAUDE.md` `In Progress`/`Next Steps`/`Last Updated` in a single parallel turn; classifies into one of 5 buckets (A. pre-commit cleanup / B. pre-merge verification / C. post-ship audit / D. orient + audit / E. ambient improvement); prints a ~10-line report with state summary + bucket name + recommended flow + one alternative + optional notes. **Three deliberate non-features:** never invokes other skills (no "want me to run it?"), never edits files (no `--fix` mode and never will), exactly one Recommended + one Alternative (more is noise). Tie-breakers codified in `state-buckets.md`: uncommitted changes always wins; open PR beats main-branch; long staleness beats recent shipping; no `CLAUDE.md` always escalates to bucket D. Skill count 6→7. |
| `/code-cleanup --vulns` flag for dep CVE scanning (Session 22 mid-session extension) | Audit of code-health coverage across the 5 review skills (`/simplify`, `/code-review`, `/ultrareview`, `/code-cleanup`, `/architecture-review`) found `/code-cleanup --deps` finds *unused* deps but nothing scans for CVEs in deps the user actually uses. Picked `--vulns` flag on existing skill over a new `/audit-deps` skill — semantically identical scan path (audit the deps tree), zero carrying cost, fits the `--code` / `--deps` / `--tests` flag pattern. **Three deliberate design choices:** (1) **Opt-in only.** Default scan never calls `npm audit` / `pip-audit` / etc. — those hit network registries, can fail offline, and slow the audit. The skill mentions the flag once; user opts in. (2) **Multi-stack coverage** — Node (npm/yarn/pnpm pick by lockfile), Python (pip-audit preferred, safety fallback), Rust (`cargo audit`), Go (`govulncheck`), PHP (`composer audit`), Ruby (`bundle audit`). Tool-missing case emits an "install hint" finding rather than silently emitting zero results. (3) **Never auto-fixed by `--fix`.** Version bumps can break the app, transitive constraints get rewritten, and lockfile churn is project-policy. Vulnerable deps are report-only — user runs the suggested `fix_command` themselves after reviewing. Severity → risk mapping: critical/high → safe (high-confidence finding), moderate → likely_safe, low → needs_investigation. |

> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)

## Architecture Summary

```
claude-config/
├── .claude/
│   ├── agents/              # Subagent definitions (Sonnet-routed)
│   │   ├── arch-performance.md
│   │   ├── arch-refactors.md
│   │   ├── arch-simplification.md
│   │   ├── arch-structure.md
│   │   ├── cleanup-deps-config.md
│   │   ├── cleanup-files-code.md
│   │   └── cleanup-styles-tests.md
│   ├── scripts/             # Session startup scripts
│   │   ├── start-claude.sh          # Mac/Linux
│   │   └── start-claude.ps1        # Windows (PowerShell)
│   ├── settings.local.json  # Shared Claude Code settings
│   └── skills/              # Skills (SKILL.md + references/)
│       ├── architecture-review/
│       ├── code-cleanup/
│       ├── code-health-advice/
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

### Last Session (Session 22) - 2026-05-08
- **Mechanical fix on Next Steps #2.** `/plan-feature` `interview-rules.md:11` and `workflow.md:123` both said "Batch 3-5 questions per call" — the `AskUserQuestion` tool's `questions` array is capped at 4, so passing 5 errored with `too_big maximum: 4` during S21. Changed both to "3-4 questions per call" and added the cap explanation inline so the reason persists.
- **New `/code-health-advice` skill — read-only routing advisor.** Came from a discussion about skill ordering. User asked for a guide explaining which skills to run in what order for two scenarios (finished feature with local changes / just shipped to prod). I sketched the orderings in chat, then proposed a small skill that classifies repo state and prints the recommended sequence; user agreed, picked the `-advice` suffix to signal "report only, never invokes."
- **Three deliberate non-features.** (1) Never invokes other skills — output is text only, user runs the suggested flow themselves. (2) Never edits files — there is no `--fix` mode and there will not be one. (3) Exactly one Recommended flow + one Alternative flow per report — more is noise. Codified all three in `SKILL.md` Step 3 rules and Step 4 (explicit "stop, do not ask 'want me to run X for you?'").
- **Five state buckets** (full catalog in `references/state-buckets.md`): A. Pre-commit cleanup (uncommitted changes on feature branch), B. Pre-merge verification (clean tree + open PR), C. Post-ship audit (clean tree on main, recent ship), D. Orient + audit (long since last commit, or no `CLAUDE.md`), E. Ambient improvement (clean tree, no urgent task). Each has a recommended flow and an alternative flow with a one-line "use this if…" qualifier (e.g., Bucket A's alternative: *"if this touches auth/payments/migrations"* → adds `--security` + `/ultrareview`).
- **Tie-breaker rules** (when multiple buckets match): (1) uncommitted changes always wins, (2) open PR beats main-branch state, (3) long staleness beats recent shipping, (4) no `CLAUDE.md` always escalates to bucket D. Codified in `state-buckets.md` so the orchestrator's choice is deterministic.
- **What it deliberately doesn't cover** (also in `state-buckets.md`): active debugging/incident response (assumes calm-water decision-making), greenfield feature work (that's `/plan-feature` directly), doc-only sessions (that's `/update-docs` directly). The advisor's job is the gray zone: "I have time, the repo is in some state, what's the best use of my next hour?"
- **Files created (2):** `code-health-advice/SKILL.md`, `code-health-advice/references/state-buckets.md`.
- **Doc updates:** README.md (new commands-table row, new "Not sure where to start?" callout under the review-skills picker, file tree), workflow.md (new "Not Sure Where to Start" Quick Reference row, new `/code-health-advice` Command Reference section, new Scenario 6, file tree, version history row), CLAUDE.md (skills 6→7, dogfood Next Steps row #2, new key-decision row, architecture tree, this session bullets).
- **Mid-session extension — `/code-cleanup --vulns` flag for dep CVE scanning.** Honest audit of code-health coverage across the 5 review skills found dep vulns weren't covered: `/code-cleanup --deps` finds *unused* deps; nothing audits installed deps for known CVEs. Picked a flag on the existing skill over a new `/audit-deps` skill — same scan path, zero new carrying cost.
- **Three design choices:** (1) opt-in only (no implicit network calls), (2) multi-stack: Node (`npm`/`yarn`/`pnpm audit` picked by lockfile), Python (`pip-audit` preferred, `safety` fallback), Rust (`cargo audit`), Go (`govulncheck`), PHP (`composer audit`), Ruby (`bundle audit`); tool-missing emits an install hint, not silent zero, (3) never auto-fixed by `--fix` — version bumps can break the app and lockfile churn is project policy. User runs the suggested `fix_command` after reviewing.
- **Files modified for `--vulns`:** `code-cleanup/SKILL.md` (frontmatter tools, dispatch logic, dashboard row, fix-mode carve-out, scope table), `code-cleanup/references/scan-deps-config.md` (new Section 4.5: per-stack commands, severity→risk mapping, output format, what-to-skip), `agents/cleanup-deps-config.md` (added audit-tool Bash perms + opt-in rule), `README.md` + `workflow.md` (commands table, Quick Reference, Command Reference detail).

### Session 21 - 2026-05-07
- **Acted on Next Steps #1** ("Add more skills as new workflow needs emerge"). User identified gap: existing review skills (`/code-review`, `/simplify`, `/ultrareview`) all operate on diffs/commits; nothing audits whole-repo architecture. Built new `/architecture-review` skill via `/plan-feature` interview.
- **Three guardrails came out of the interview** (user surfaced them when asked for improvement suggestions before plan finalization). (1) **Patterns reframed.** Subagent renamed `arch-patterns` → `arch-refactors`; catalog is complexity-reducing techniques (guard clauses, pure-function extraction, flag-arg removal, discriminated unions, table-lookup dispatch), not GoF patterns. R13 Strategy / R14 Command are present but with strict "detect when" gates (4 conditions for R13). (2) **Read intended architecture first.** Step 1 reads CLAUDE.md / README / `docs/architecture/` / ADRs and summarizes the project's *intended* architecture in 3-5 bullets, which gets passed to all subagents as shared context. Findings conflicting with documented decisions get `respects_documented_decision: false` and surface in a separate report section. (3) **CCN delta sanity gate.** Each finding has `ccn_current` (from detected linter — eslint with `complexity` rule / ruff `C901` / radon / lizard, fall back to Grep heuristic) and `ccn_projected`. Orchestrator filters findings where projected ≥ current.
- **Decomposition mirrors `/code-cleanup`:** three parallel Sonnet subagents — `arch-structure` (complexity, coupling, cohesion, layering violations, circular deps), `arch-refactors` (catalog-driven, must cite catalog entry by ID), `arch-performance` (high-precision categories: N+1, sync I/O in async paths, accidental O(n²), missing memoization, hot-loop invariants; lower-confidence framed as "suspects to measure" not fixes).
- **Scale tiers** (smart sampling, not random): <100=full, 100-500=bounded, >500=sample by `log(LOC) × churn × import-fan-in` priority + drill-down on hotspots. `--full-scan` escapes; "what was sampled vs skipped" in report footer.
- **Modes:** default (review-only) / `--plan` (phased TaskCreate-ready brief with copy-pasteable `/plan-feature` snippets per phase) / `--fix` (per-finding diff preview, **single-file non-API-breaking only**; cross-file auto-routes to `--plan`). `/rewind` reminder at end of `--fix`. `--map` for heavier ASCII module-dep graph; `--full-scan` for forced full tier.
- **Files created (12):** `architecture-review/SKILL.md`, 8 reference files (`scale-strategy.md`, `refactor-catalog.md`, `report-template.md`, `fix-mode.md`, `plan-mode.md`, `scan-structure.md`, `scan-refactors.md`, `scan-performance.md`), 3 agent definitions (`arch-structure.md`, `arch-refactors.md`, `arch-performance.md`).
- **Doc updates:** CLAUDE.md (skills 5→6, agents 3→6, new key-decision row, architecture tree, this session bullets), README.md (skill list, complement table positioning vs `/code-review`/`/simplify`/`/ultrareview`/`/code-cleanup`, agent table, file tree), Workflow.md (new command reference section, new Scenario 5 "First time in unfamiliar repo / architecture health check," version history row), MEMORY.md (counts).
- **Mid-session extension** — when asked "do you think this addresses optimized / maintainable / least-code-possible?", honest audit found `least-code-possible` was the weak dimension: refactor catalog *trades* complexity, not deletes it. Built 4th subagent `arch-simplification` covering 9 over-engineering categories (S01-S09 in catalog), with `lines_deletable` as a mandatory finding field and a top-line "Code we can delete: N lines across M files" report metric. False-positive guards include test seams, boundary types, and recency check (<30 days). Skill count stays 6; subagent count 6→7.
