# CLAUDE.md

Last Updated: 2026-05-14 (Session 26)

## Project Overview

**claude-config** — Personal Claude Code configuration repo containing custom skills, subagents, and workflow documentation.

- **Repo:** [burak-maxitech/claude-config](https://github.com/burak-maxitech/claude-config) (private)
- **README.md** — Public overview, setup instructions, command reference
- **Workflow.md** — Detailed personal workflow guide (daily workflow, scenarios, tips)
- **docs/** — Reference files (session history, key decisions, completed work)

## Current Status

| Area | Status |
|------|--------|
| Skills (9) | Complete |
| Subagents (13) | Complete |
| Startup scripts | Complete |
| Cross-platform setup | Complete |
| GitHub sync | Complete |
| Documentation | Complete |

## Completed

All 9 skills, 13 subagents, cross-platform setup, and documentation system are complete.

See [docs/completed-work.md](docs/completed-work.md) for full checklist.

## In Progress

None currently. `/seo-review` shipped in S25 + 2 correctness fixes in S26 (`Write` tool in `allowed-tools`; sub-dimension clamp made canonical in `rubric.md` + enforced in orchestrator Step 6.1). Four dogfood debts + one doc-rollup fix open under Next Steps.

## Next Steps

1. **Dogfood `/seo-review` on a real Next.js / Astro / Rails web project** — built S25 but never invoked end-to-end. S26 applied two correctness fixes from a fresh-context `/code-review` (`Write` tool to allowed-tools so first-run `docs/seo-history.md` can be created; sub-dim deduction clamp made canonical in `rubric.md` + enforced in orchestrator Step 6.1 so the Section 1 score breakdown stays internally consistent). 8 lower-priority `/code-review` suggestions captured in S26 session-history entry, not addressed (sitemap example.com URL, sitemap_index.xml cap ambiguity, 100-parallel-WebFetch turn behavior, `--fix` branch-delete advice, conditional `--fix` line in Section 4, is_web SPA `--url` hint, scan/agent boilerplate duplication (overlaps Next Steps #5), vocabulary drift). Watch for: (a) Step 1 fetch latency on a real run (target <60s for the WebSearch + WebFetch parallel turn — S25's /simplify pass tightened the parallelism guarantee but real wall-clock is unmeasured); (b) sitemap URL probe behavior on a sitemap_index.xml (cap-100, 8-point score-impact cap, response-time bucketing); (c) `--fix` allowlist gate flow on a real project — verify no fabricated content leaks past the TODO-placeholder rule; (d) rubric weight-tuning when the fetched brief proposes adjustments — ±5 cap and sum=0 validation gate (added in S25 /simplify pass); (e) `/code-health-advice` is_web detection accuracy on the same project (does it correctly route to /seo-review in Bucket C/E?).
2. **Dogfood `/test-review` on a real Node/Jest or Python/pytest project** — built S24 but never invoked end-to-end. Watch for: T01 false-positive rate (project-defined assertion-helper scan should be the gate), twin-headline math correctness on real subagent output (subtotal-check line should reconcile), `--coverage` opt-in path against an actual jest `coverage-summary.json` / pytest `coverage.json`, scan-economics ratio thresholds (>3.0 over, <0.1 under) on a real module structure, non-overlap with `/code-cleanup` (no orphans/skips/helpers/snapshots surfaced).
3. **Dogfood `/architecture-review` on a non-trivial real project** — never run end-to-end yet. Watch for linter-detection accuracy, intended-architecture summary quality, CCN-delta filter behavior, simplification false-positive rate.
4. **Dogfood `/code-health-advice`** — built S22 but never invoked end-to-end. Watch for: bucket misclassification rate, freshness-mismatch detection accuracy, cases where a 6th bucket would help.
5. **Address /seo-review deferred refactors** (captured in /simplify pass S25, not blocking): batched-Grep alternation across scan-technical/content/geo (biggest runtime win — 30 Greps → 3-6 per scan on real projects); fix-mode harness extraction from architecture-review/references/fix-mode.md; plan-mode scaffolding extraction across the 3 plan-mode-*.md files; cross-file boilerplate consolidation into a shared-rules ref file (~25-40 lines saveable). Best done after the dogfood pass surfaces which refactor is most needed.
6. Improve existing skill reference files based on usage patterns.
7. Consider adding hooks for automated pre-commit workflows.
8. Explore MCP server integration for external tool access.
9. **Fix orphan table row at `docs/key-decisions.md:129` + investigate `/update-docs` Part 6 regression.** S25's Part 6 rollup appended the new "Standalone skills + installed marketplace plugins coexist" row at end-of-file, but the file at that location is in a bulleted "Also noted during verification" section (added post-S22) — the row renders as a structurally-broken orphan table fragment with no header context. S22 + S23 rollups landed correctly; S25 did not. Hypothesis: `mode-update.md` Part 6 Step 6.3's "append to file" logic assumes the table block is always at end-of-file. Fix the orphan row first (move into the actual table block at top of file), then audit Step 6.3 for the case where non-table content follows the table.

## Key Decisions

| Decision | Rationale |
|----------|-----------|
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
| New `/seo-review` skill — SEO + Generative Engine Optimization audit for web projects (S25 built, 6 build commits + 1 /simplify-pass commit) | Web-only audit closing a deliberate workflow gap (no prior review skill covers SEO/GEO). **Three new skill patterns:** (1) fetch-current-best-practices-every-run — Step 1 single parallel turn of WebSearch + WebFetch across 4 source categories (Google Search Central + web.dev, Schema.org + JSON-LD, GEO sources + llms.txt spec + Anthropic/OpenAI/Perplexity guidance, third-party authority blogs); ~50-line brief passed verbatim to all 3 subagents as source of truth; handles fast-evolving SEO/GEO field without skill staleness debt; (2) orchestrator-only HTTP boundary (subagents have no network tools); sitemap URL probe in Step 3.2 (cap 100 URLs, 8-point score-impact cap so fully broken sitemap can't zero Technical SEO, classifies 4xx/5xx/redirect-chains/slow); (3) in-repo `docs/seo-history.md` score history with delta in headline (auto-created, append-only, write gated to default mode post-/simplify-pass). **3 Sonnet subagents** (`seo-technical` / `seo-content` / `geo-generative`). **Rubric:** Technical SEO 25 / On-Page 25 / Structured Data 20 / Generative Engine 20 / Performance 10 = 100, with ±5-per-dim weight tuning + sum=0 validation gate. **`--fix` strict allowlist (11 patterns) NEVER fabricates content** — only TODO-placeholder scaffolds. **`/code-health-advice` integration:** is_web detection in Step 1 + conditional Bucket C/E routing. Full prose: [docs/session-history.md S25](docs/session-history.md). |
| New `/test-review` skill — repo-wide test health audit (S23 plan → S24 built, 8 phase commits) | Closes the biggest code-health coverage gap surfaced by an honest audit in Session 23 against 14 dimensions. Existing coverage: `cleanup-styles-tests` §7 catches artifact-level cruft only (orphaned files, >3mo skips, unused helpers, stale snapshots); `/code-review` §7 testing is a 4-bullet diff-scoped checkbox. Nothing examines suite health at scale in either direction (missing coverage on critical paths + wasteful/redundant tests). Runner-up gap was whole-repo SAST + secrets in committed code, but that is *partially* serviced by `/code-review --security` accepting dir args + built-in `/security-review`. **Design (settled via 12-question `/plan-feature` interview):** 3-way subagent decomposition mirroring `/architecture-review` — `test-coverage` (gap ranking via `security_keyword_density × churn × import_fan_in`; bug-fix-without-regression-test scan over last 50 commits with `^fix:`/`bugfix`/`closes #`), `test-quality` (Tier 2 smell catalog: T01 assertion-free, T02 weak assertions like `toBeTruthy`/`not.toBeNull`/`>= 0`, T03 implementation-coupled mock-heavy with `toHaveBeenCalledWith`, T04 mystery guests, T05 redundant), `test-economics` (snapshot-heavy ≥50% threshold, flakiness via `git log --grep=flaky` + retry decorators like `it.retry`/`pytest.mark.flaky`/`#[ignore]`, test:code LOC ratio per module). **Coverage tool integration opt-in only** via `--coverage` flag — mirrors `/code-cleanup --vulns` pattern; default scan is heuristic-only (test-neighbor ratio, AST). Multi-stack: jest/vitest, pytest-cov, cargo-tarpaulin, go test -coverprofile. **Twin headline metric** (twin, not single): `Coverage gaps in critical code: X lines across Y files | Tests we can delete: Z lines across W files`. Deletable aggregation = T01 + T05 + snapshot-heavy reductions only (T02/T03/T04 are *rewritable*, not deletable, so including them would mislead the headline). **Non-overlap with `/code-cleanup`:** `/test-review` defers entirely to `cleanup-styles-tests` §7 for orphans/skips/helpers/snapshots; bidirectional footer pointers cross-reference. **`--fix` scope T01-only** (assertion-free deletion is provably safe — a test with zero `expect`/`assert` cannot fail meaningfully); everything else auto-routes to `--plan`. False-positive guard for T01: detect project-defined assertion helpers (`assert*`/`should*`/`expect*` imports) before flagging. Snapshot policy default risk `needs_investigation`. Phases 1-8, est. ~4.5h. `/code-health-advice` updated this session to reference `/test-review` in Buckets C (post-ship audit), D (orient + audit), and E (ambient improvement); Buckets A/B intentionally skipped (diff/PR-scoped, mismatch with whole-repo audit). |

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
│   │   ├── cleanup-styles-tests.md
│   │   ├── geo-generative.md
│   │   ├── seo-content.md
│   │   ├── seo-technical.md
│   │   ├── test-coverage.md
│   │   ├── test-economics.md
│   │   └── test-quality.md
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
│       ├── seo-review/
│       ├── test-review/
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

### Last Session (Session 26) - 2026-05-14
- **Same-day follow-up to S25 — fresh-context `/code-review` on the full S25 build span** (`dbcb820~1..HEAD`, 8 commits, 20 files, +2476 lines). Surfaced 3 Important findings: **I1** — `seo-review/SKILL.md` allowed-tools listed `Edit` but not `Write`, so first-run `docs/seo-history.md` creation would fail (Edit requires the file to exist). **I2** — sub-dimension score caps in `rubric.md` weren't enforced anywhere; per-finding `score_impact` sums could legitimately push a 3-point sub-dim's reported deduction to `-4.5` in Section 1's breakdown (traced 3 concrete overshoot paths: image_perf, robots_sitemap, mobile). **I3** — orphan table row at `docs/key-decisions.md:129` from S25's `/update-docs` Part 6 rollup landed outside the table block.
- **User asked to fix I1 + I2 only.** I3 deferred to next session (now Next Steps #9). 8 lower-priority `/code-review` suggestions captured in session-history full prose, not addressed.
- **I1 fix:** added `Write` to `allowed-tools` in `seo-review/SKILL.md` frontmatter. Edit stays for append on subsequent runs; Write handles first-run create.
- **I2 fix (clamp made canonical):** updated `references/rubric.md` "Scoring computation" with explicit `min(sum(score_impact for findings in this sub_dim), sub_dim_max)` formula + note that enforcement lives once, in the orchestrator. Updated `SKILL.md` Step 6.1 from "Aggregate sub-dimension scores" to "Aggregate + clamp sub-dimension deductions" with explicit `clamped[sub_dim] = min(raw[sub_dim], sub_dim_max)` rule + divergence-flag fallback if a subagent's emitted dimension_total disagrees with the recomputed one. Step 6.2 clarified that sub-dim caps stay at base values when weight adjustments shift dimension maxes. Subagent and scan files left untouched — they emit raw findings; orchestrator is the single point of enforcement. Rejected alternative (per-subagent clamp) because each scan-*.md would need to embed the cap table from rubric.md, risking drift.
- **Dogfood debts and the I3 fix** carried into Next Steps. No new architectural decisions; no README/workflow changes (fixes are internal to `/seo-review`'s behavior, not visible at the command surface).
