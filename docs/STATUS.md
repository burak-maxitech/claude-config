# Project Status

> Session state for `/bx:resume`. Instructions live in [CLAUDE.md](../CLAUDE.md).

Last Updated: 2026-10-26 (Session 65, cont.)

## Current Status

| Area | Status |
|------|--------|
| Skills (11) | Complete — `/bx:clean` content-reviewed and extended with seven categories S63 (bx 2.13.0; 60/60 on fixtures) and run for real S64 on maxitech-concierge (Python; 6 defects → 2.13.1) and horowell (Next.js; 10 defects → 2.13.2); `/bx:save --full` run three times on the reordered sweep (S62 ×2, S63); `/bx:evolve` 2.12.x run four times S62; `/bx:tests` run for real S65 on horowell + maxitech-concierge (29 defects; 2.13.3 safety, 2.14.0 scripts + reduction lane + suite-verified `--fix`); only `/bx:health` never run |
| Subagents (20) | Complete — `arch-robustness` added S58 |
| Plugin packaging (`bx`) | **v2.14.0** pushed S65 (`9f7624a`); install pending (cache at 2.13.2). Refresh is `/plugin marketplace update burak-tools` + shell `claude plugin update bx` + `/reload-plugins`. Version-bump guard: `scripts/check-plugin-version-bump.sh`, `.githooks/pre-push` (enabled on this clone), CI workflow. Symlink retirement still pending |
| Doc schema v2 | Complete — shipped S56; this repo migrated |
| Startup scripts | Complete — S55 live gate passed and fix wave shipped in `7ed079a` (2026-08-17), recorded S61 |
| Cross-platform setup | Complete |
| GitHub sync | Complete — main pushed through v2.14.0 (S65, `9f7624a`) |
| Documentation | Complete — schema v2 |

## Completed

All 11 skills, 20 subagents, cross-platform setup, and documentation system are complete.

See [completed-work.md](completed-work.md) for full checklist.

**`/seo-review` hardened across 4 improvement groups + 15 code-review fixes (S35, 2026-05-26).** Same-day continuation of S34 burakarik.com dogfood. User ran the skill with new `known-bad-urls.txt`; orchestrator wrote a 396-line `_inspect_batch.py` into `.seo-data/gsc/` (third disk-write boundary violation across S31 cont.² + S34 + S35) + only inspected 50 of 100 pasted URLs. Shipped 4 groups + ran `/code-review` extra-high effort surfacing 15 findings, then fixed all 15 same-session (+1105/-71 LOC across 7 files, uncommitted). **Group A:** new `inspect-batch` helper subcommand (parallel HTTP via ThreadPoolExecutor + per-URL cache + atomic write + 429/5xx retry); broader disk-write boundary rule forbidding ALL orchestrator-written scripts under `.seo-data/gsc/`. **Group B:** subagent-skip rule codified (new Step 4.5) with 4 gating conditions + audit-trail marking + `--force-dispatch` escape hatch. **Group C:** cache TTL split — sa-* stays 24h, ui-* becomes 7d (coverageState is weeks-stable; fixes the 0/197 cache-hit problem from S34). **Group D:** finding lifecycle infrastructure — `finding-history.json` (run_count tracker with same-commit guard + ESCALATE marker at run_count>=3) + `watchpoints.json` (auto-emitted on `code_changed_since_gsc_window=true` + 21-day recheck + 90-day evict). Three new helper subcommands. **Top correctness fixes:** `head -1 sa-q2-*.json` race → deterministic hash recomputation; DST off-by-one via `time.mktime` → `datetime.date.fromisoformat()`; null-metric TypeError; operator precedence in `classify_transition`; bare `.tmp` race → PID suffix; 20-worker rate-limit burst → 6 workers + retries.

## In Progress

**`/bx:tests` upkeep — release 1 shipped (2.13.3), release 2 specced (S65).** Spec: `docs/superpowers/specs/2026-10-26-bx-tests-upkeep-design.md` (33 problems, decisions D1–D6, acceptance controls from both repos). 2.13.3: assertion definition in one place, T01a/T01b split, gated suite-verified `--fix`, `coverage_negatives` + `coverage_partial` in the dispatch block, agents reduced to citations. 2.14.0: committed scripts (`test_bodies.py`, `leverage.py`, `references.py`), accuracy fixes, reduction lane (`life_support`, `consolidate`, growth trend), `/bx:clean` ownership split.

**`/bx:evolve` 2.12.x — shipped, run four times, three run-found defects fixed (S62).** 2.12.0 delivered the three 2.11.0 defects and improvements 7–10 (`lane-contract.md`, `scripts/docs-page-hashes.py` + `watermark.docs_pages`/`inventory_hash`, pinned `capabilities.json` via `scripts/build-capabilities.py`, community lane as a discovery feed). Four real runs: delta 22/22 pages (5 findings), `--fix` with all lanes current (3 applied + `env-vars` pinned), delta 5/23 (1 finding), `--fix` all-current (1 applied). Fixed in 2.12.1: registry threshold `min(3, n)`, validator pattern for the pinned vocabulary. **Open:** the probe's delta-aware scan (narrowed by hand once), candidates persisting into `--fix`, a `source_url` tie-break rule, the plugin-eval design `69ef485d` (needs `bx/evals/` + `claude plugin eval init`).

**Doc tiering phase 1 — the two S61 defects fixed in 2.12.0 and run twice (S62).** The `--full` sweep (Parts 2–7) runs before the writer dispatch; the second run exercised the Part 7.3 size-based Key Decisions rollup for real (8 rows moved, CLAUDE.md 12.7k → 9.3k). The open-phase floor is saving-based with a *looks resolved — confirm* heading; lint K20/K23 pin both. Still open: deferred minors (guard checks inequality not increase; guard tests not hermetic against `commit.gpgsign`; lint and fixture tests not in CI; `save-writer`'s unreachable `status: open` path); Phase 2 (`.claude/rules/` tier) is now unblocked — the memory docs confirm `paths:` is the only rule frontmatter field (deferred finding `5b91feb3` carries the edit). Plan: `docs/superpowers/plans/2026-09-28-bx-doc-tiering-phase1.md`.

**Doc schema v2 post-merge verification (S56–57).** The first `/bx:save --full` on schema v2 ran S57: Part 5 found all older sessions already compressed, Parts 6/7 under caps, and rotation did not fire then. It has since fired: `docs/archive/key-decisions-1.md` exists and the live `docs/key-decisions.md` measured 53k on 2026-09-28 (S60). Still owed from the deferred Task 10 skill-steps: live `/bx:save` runs against the fixtures (fx-v2 no-op, fx-partial resume, fx-dirty skip, fx-v1-envvars keep path, fx-v1-sparse scaffold, fx-v1-ineligible decline). Post-merge minors parked in both plans: backlog symptom measurement (7.7's clause is unreachable), checker fence-strip/CR robustness, mode-migrate declines-bullet v1-only phrasing, resume Quick Reference partial row, structure-rules cell wording.

**`/bx:webdesign` kaanarik run paused at `review_pending` (S52).** Resume via `/bx:webdesign` (plugin is current), push through Phase 3 inject+verify. Phase 3e now asks the user before the destructive-git rollback (`dadac845` + `6712a71e` applied S61); verify live there that auto mode accepts the confirmed rollback.

**S37 plugin packaging leftovers.** Retire `~/.claude` symlinks and the launcher-script symlink check. (Install smoke-test closed v2.6.0; the `Skill(bx-*)` → `Skill(bx:*)` sweep is moot — S59 found no `Skill(bx-*)` anywhere in the repo, and the stale local `Skill(bx:docs)` allow entry was renamed to `Skill(bx:save)`.)

**`/bx:arch` review depth v2 shipped and dogfooded (S58).** Eight phases took the skill from a function-level refactor scanner to a six-dimension architecture review: catalog 23 → 54 entries (D design/SOLID, C concurrency, E error safety, X scalability), a fifth scanner `arch-robustness`, a calibrated finding contract (`finding-rubrics.md` — anchored severity, certainty by evidence class, mandatory `evidence` + `why_this_might_be_wrong`), thesis-first report with theme synthesis, and churn × fan-in in the rank score. Spec: `docs/superpowers/specs/2026-08-24-bx-arch-review-depth-design.md`. **Owed:** `/plugin update bx`, then the first end-to-end run — rehearsals prove the instructions are unambiguous, only a real run proves the scanners find anything useful.

## Next Steps

1. **Install bx 2.14.0** (`/plugin marketplace update burak-tools` + shell `claude plugin update bx` + `/reload-plugins`) and run `/bx:tests` once on horowell with the installed `test-*` agents (never exercised); then `/bx:tests --fix` on a horowell branch for one mechanical JS merge (89 available) once the other session's edits there are committed.
2. **`/bx:clean` rerun** to confirm the new "Test-only symbols — see /bx:tests" block (D6) replaces the S240-style test-only dead-code items.
3. **maxitech-concierge follow-ups (in that repo):** add tests for `SlackService.verify_request` (the only auth on `POST /slack/interactions`, zero tests) and a regression test for `820c2076`; move `build_reply_all_recipients`'s 5 tests to the live `build_reply_recipients` and delete the dead method. 2.14.0 also found three mechanical merges there (C007, C014 in the S65 clone).
4. **`/bx:evolve` 2.12.x follow-ups** — make `docs-page-hashes.py` delta-aware, persist `allowlist_candidates` into `--fix`, add the `source_url` tie-break to Step 3.4; regenerate `capabilities.json` (pre-existing `bx:clean/idiom:bin-path-helper` drift); PATCH bump.
5. **Doc tiering Phase 2** (`.claude/rules/` tier, spec D4–D6) — unblocked S62; edit stored on deferred finding `5b91feb3`. Plus the deferred minors listed in `## In Progress`.
6. **Doc-schema v2 fixture verification** — the six deferred live `/bx:save` fixture runs plus the post-merge minors batch.
7. **/simplify follow-up: move Part 7.7 rotation into its own sibling Part** (with S59 D4's Part 7.9); blind rehearsal before shipping.
8. **Resume the `/bx:webdesign` kaanarik run past review**; verify finding `dadac845` live.
9. **Real `/bx:seo` run against burakarik.com**; code-review leftovers still deferred.
10. **Dogfood `/bx:health`**; then the `/bx:clean` untested paths (`--dry-run`, `--fix`, directory scope), the plugin-eval design `69ef485d`, S37 symlink retirement, and S58 concurrency regression tests + the 12 exclusion-list restatements.

## Session History

> Full history: [session-history.md](session-history.md)

### Last Session (Session 65, cont.) - 2026-10-26
- **`/bx:tests` 2.14.0 shipped (`9f7624a`):** four stdlib scripts + `run.py` measure every number (test bodies/assertions, path-resolved leverage + git lanes, call/mock/mention references + life support with successor detection, consolidate clusters with merge tables); scanners judge.
- **Reduction lane + triple headline:** horowell 15 test-only production symbols (matching its own backlog list) and 774 -> 251 tests consolidable; maxitech `build_reply_all_recipients` -> `build_reply_recipients`.
- **Verified by running:** eight scanner runs passed every acceptance control and surfaced 13 script defects, all fixed in the scripts; `--fix` dogfood on a maxitech clone: 210 -> 207 exactly, bad merge green but reverted by the count check.
- **`--fix` is a reducer** (T01a, successor-less life support, mechanical merges) with per-item snapshot reverts; `/bx:clean` hands test-only symbols to `/bx:tests` (D6).
- Not exercised: the agent definitions (cache 2.13.2), a JS merge under `--fix`.
