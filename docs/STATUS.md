# Project Status

> Session state for `/bx:resume`. Instructions live in [CLAUDE.md](../CLAUDE.md).

Last Updated: 2026-08-18 (Session 55)

## Current Status

| Area | Status |
|------|--------|
| Skills (11) | Complete |
| Subagents (18) | Complete |
| Plugin packaging (`bx`) | Core complete (S37); explicit semver **v1.0.0** + CHANGELOG.md (S54) — pending install smoke-test + symlink retirement |
| Startup scripts | Complete — per-project session name + color added S55, pending live verification |
| Cross-platform setup | Complete |
| GitHub sync | Complete |
| Documentation | Complete |

## Completed

All 11 skills, 18 subagents, cross-platform setup, and documentation system are complete.

See [completed-work.md](completed-work.md) for full checklist.

**`/seo-review` hardened across 4 improvement groups + 15 code-review fixes (S35, 2026-05-26).** Same-day continuation of S34 burakarik.com dogfood. User ran the skill with new `known-bad-urls.txt`; orchestrator wrote a 396-line `_inspect_batch.py` into `.seo-data/gsc/` (third disk-write boundary violation across S31 cont.² + S34 + S35) + only inspected 50 of 100 pasted URLs. Shipped 4 groups + ran `/code-review` extra-high effort surfacing 15 findings, then fixed all 15 same-session (+1105/-71 LOC across 7 files, uncommitted). **Group A:** new `inspect-batch` helper subcommand (parallel HTTP via ThreadPoolExecutor + per-URL cache + atomic write + 429/5xx retry); broader disk-write boundary rule forbidding ALL orchestrator-written scripts under `.seo-data/gsc/`. **Group B:** subagent-skip rule codified (new Step 4.5) with 4 gating conditions + audit-trail marking + `--force-dispatch` escape hatch. **Group C:** cache TTL split — sa-* stays 24h, ui-* becomes 7d (coverageState is weeks-stable; fixes the 0/197 cache-hit problem from S34). **Group D:** finding lifecycle infrastructure — `finding-history.json` (run_count tracker with same-commit guard + ESCALATE marker at run_count>=3) + `watchpoints.json` (auto-emitted on `code_changed_since_gsc_window=true` + 21-day recheck + 90-day evict). Three new helper subcommands. **Top correctness fixes:** `head -1 sa-q2-*.json` race → deterministic hash recomputation; DST off-by-one via `time.mktime` → `datetime.date.fromisoformat()`; null-metric TypeError; operator precedence in `classify_transition`; bare `.tmp` race → PID suffix; 20-worker rate-limit burst → 6 workers + retries.

## In Progress

**Per-project `cc` session naming + coloring — built, 2 items open (S55).** `cc <project>` now launches `claude -n "<project>" "/color <color>"`, so every session carries the project name (prompt box, `/resume` picker, terminal tab title) and a distinct prompt-bar color. Colors are auto-assigned on a project's first launch and remembered in `~/.claude/cc-session-colors`. Built brainstorm → spec → plan → subagent-driven (4 tasks, 1 fix round, all reviewed); whole-branch review verdict **Ready to ship**, with cross-shell parity verified empirically in bash 5.3, pwsh 7.6.4, and Windows PowerShell 5.1 (plus a 20-case adversarial parse differential — identical verdicts). **Open item 1: the human live gate** — run `cc claude-config` and confirm the prompt bar is actually colored, the name chip/tab title reads the project, and no model turn is consumed. `/color` as a prompt argument is proven for `-p` only; the interactive path needs a TTY. If it fails, do NOT patch the launcher — fall back to the spec's `statusLine` alternative as a fresh decision. **Open item 2: one fix wave**, deferred until the gate reports because README wording is part of it: ASCII-sweep `start-claude.ps1` (Windows PowerShell 5.1 parse fix), `try/catch` around the helper call, `ToLowerInvariant()`, treat a 0-byte registry as missing when writing the header, a case-insensitivity assertion in the PS suite, and sweep the stale case-sensitive code out of the checked-in plan + spec. Spec: `docs/superpowers/specs/2026-08-12-cc-session-naming-design.md`; plan: `docs/superpowers/plans/2026-08-12-cc-session-naming.md`.

**`/bx:webdesign` first dogfood + third hardening pass (S52), pending re-run.** The 10th skill had its **first real end-to-end run** (on `kaanarik`): the whole pipeline ran — setup → detection → branch → inventory → before-shots → Stitch seeding → direction interview → quota pre-flight → 3-screen generation → mandatory review → palette iteration — and **paused cleanly at `review_pending`** on `webdesign/2026-07-23`, **no app code touched**. The safety architecture held; every failure was in the delegation surface (Google's skills + Stitch platform + Windows env). The run surfaced **15 findings, all applied S52** across 7 files: `stitch::`→`stitch-design:` naming; latent Phase-3 clean-tree traps (`.gitignore` now committed, `.playwright-mcp/` gitignored); Tailwind-v4 detection + `@theme` merge; setup-doc rewrite; Stitch platform gotchas + lossy-palette "verify-one-then-batch" pass. Then self-reviewed the fixes: `/bx:review` caught 2 more (`allowed-tools` `mv`/`cp`; a 2.1a↔2.2 double-generation) and a 4-agent `/simplify` pass applied 11 dedup/altitude refinements (incl. the missed Phase-3 after-shot site and a Step-4 self-contradiction). Earlier hardening: S42 (16) + S48 (13/12, `9b9c703`). **The 15-fix batch is pushed (`62d3461`); the review+simplify fixes land in the S52 re-save — `/plugin update bx` to pick everything up.** Kickoff prompt: `docs/webdesign-first-run-prompt.md`; dogfood checklist: `docs/superpowers/plans/2026-06-06-bx-webdesign-dogfood.md`.

**S37 plugin packaging — remaining:** install smoke-test, retire `~/.claude` symlinks, `settings.local.json` `Skill(bx-*)` → `Skill(bx:*)`, launcher-script symlink-check retirement. (GSC MCP migration #1 declined; Playwright #2 deferred.)

## Next Steps

1. **Finish the `cc` session naming/coloring rollout (S55, in flight)** — run the live gate (`cc claude-config`: prompt bar colored? name chip + tab title? no model turn consumed?), then dispatch the single fix wave listed in `## In Progress`. Ledger: `.superpowers/sdd/2026-08-12-cc-session-naming/progress.md` (git-ignored).
2. **Smoke-test batch (quick):** `/loop /bx:review` (docs now confirm the disable-model-invocation plain-text behavior for *scheduled tasks*; whether `/loop` shares it is the open half — workflow.md caveat is now "partially confirmed"); `/plugin update bx` without `/reload-plugins` (v2.1.221 "when safe", finding `fab78c6a`); a few `2>/dev/null` commands watching for new prompts (v2.1.214 fail-closed, finding `093df977`); `CLAUDE_ENV_FILE` UTF-8 persistence.
3. **Design session: a verification pass for `/bx:review`** — still single-pass at `effort: high` with no false-positive filter; Anthropic's reviewer runs parallel agents + verification. Brainstorm → spec → skill-creator eval (finding `d1480670`, deliberately half-fixed in S53).
4. **Resume the `/bx:webdesign` kaanarik run past review** — `/plugin update bx` first (picks up v1.0.0), re-run `/bx:webdesign` (resumes at `review_pending`), push through **Phase 3 inject+verify**. While there, VERIFY open finding `dadac845`: auto-mode blocks destructive git and Phase-3's rollback is exactly `git restore .` + `git clean -fd` — S54's community lane surfaced Anthropic's official auto-mode post confirming the premise.
5. **Real `/bx:seo` run against burakarik.com** — auth fixed S39, content-review-hardened S45.
6. **Dogfood `/bx:tests`, `/bx:arch`, `/bx:health`** — all content-review-hardened in S46, never run end-to-end.
7. **S37 plugin-packaging leftovers** — install smoke-test, retire `~/.claude` symlinks, `settings.local.json` `Skill(bx-*)` → `Skill(bx:*)`, launcher-script symlink-check retirement.
8. **`/bx:evolve` follow-ups** — evaluate adding `auto-mode-config` to the scan-docs allowlist (owns the auto-mode classifier contract; flagged S54); act on the 14 `open` findings (top: the skills-dir/activation-gap cluster, now 5 distinct sources); v2 ideas: extract shared `references/lane-contract.md` (three scan files share ~50% mass), treat lane digest one-liners as non-citation-grade.
9. **`/bx:seo` deferred items** — code-review leftovers (#5 redundant per-call token mints; #6 `_read_skill_config` CWD assumption; #7 `fetch-sa` subcommand) plus the S25/S27/S29 refactors (batched-Grep alternation; fix-mode + plan-mode scaffolding extraction).

## Session History

> Full history: [session-history.md](session-history.md)

### Last Session (Session 55) - 2026-08-12
- **Built per-project session naming + coloring for the `cc` launcher** — `claude -n "<project>" "/color <color>"`, with colors auto-assigned on first launch and remembered in `~/.claude/cc-session-colors`. Brainstorm → spec → plan → subagent-driven (4 tasks, 6 commits, 1 fix round, every task reviewed).
- **Verified the upstream surface before designing:** `-n/--name` is officially supported (name + terminal tab title), but there is **no launch-time color flag or settings key** — Anthropic closed those requests `not_planned`. `/color` as the initial prompt argument is handled locally with no model turn.
- **Rejected hashing for color assignment with measured evidence:** 8 palette colors vs 8 project folders means any hash collides (4 distinct of 8 measured); sticky auto-assign gives distinct *and* stable colors.
- **Whole-branch review: Ready to ship.** Parity verified empirically across bash 5.3 / pwsh 7.6.4 / WinPS 5.1 plus a 20-case adversarial parse differential. It also surfaced a **pre-existing** defect: `start-claude.ps1` fails to parse under Windows PowerShell 5.1 (non-ASCII in a BOM-less file).
- **Two items still open:** the human live gate (does `/color` apply in an interactive launch?) and one batched fix wave held until the gate reports.

> Full session detail: [session-history.md](session-history.md) S55
