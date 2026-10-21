# Project Status

> Session state for `/bx:resume`. Instructions live in [CLAUDE.md](../CLAUDE.md).

Last Updated: 2026-10-21 (Session 62)

## Current Status

| Area | Status |
|------|--------|
| Skills (11) | Complete — `/bx:save --full` reordered sweep first-run S62 (2.12.0); `/bx:evolve` 2.12.0 lanes dispatched once each (docs, community); only `/bx:health` never run |
| Subagents (20) | Complete — `arch-robustness` added S58 |
| Plugin packaging (`bx`) | **v2.11.1** pushed (S61); **2.12.0 committed S62, push + cache refresh owed** (cache still 2.11.1). Refresh is `/plugin marketplace update burak-tools` + shell `claude plugin update bx` + `/reload-plugins`. Version-bump guard: `scripts/check-plugin-version-bump.sh`, `.githooks/pre-push` (enabled on this clone), CI workflow. Symlink retirement still pending |
| Doc schema v2 | Complete — shipped S56; this repo migrated |
| Startup scripts | Complete — S55 live gate passed and fix wave shipped in `7ed079a` (2026-08-17), recorded S61 |
| Cross-platform setup | Complete |
| GitHub sync | Complete — main pushed through v2.11.1 (S61); 2.12.0 push owed |
| Documentation | Complete — schema v2 |

## Completed

All 11 skills, 20 subagents, cross-platform setup, and documentation system are complete.

See [completed-work.md](completed-work.md) for full checklist.

**`/seo-review` hardened across 4 improvement groups + 15 code-review fixes (S35, 2026-05-26).** Same-day continuation of S34 burakarik.com dogfood. User ran the skill with new `known-bad-urls.txt`; orchestrator wrote a 396-line `_inspect_batch.py` into `.seo-data/gsc/` (third disk-write boundary violation across S31 cont.² + S34 + S35) + only inspected 50 of 100 pasted URLs. Shipped 4 groups + ran `/code-review` extra-high effort surfacing 15 findings, then fixed all 15 same-session (+1105/-71 LOC across 7 files, uncommitted). **Group A:** new `inspect-batch` helper subcommand (parallel HTTP via ThreadPoolExecutor + per-URL cache + atomic write + 429/5xx retry); broader disk-write boundary rule forbidding ALL orchestrator-written scripts under `.seo-data/gsc/`. **Group B:** subagent-skip rule codified (new Step 4.5) with 4 gating conditions + audit-trail marking + `--force-dispatch` escape hatch. **Group C:** cache TTL split — sa-* stays 24h, ui-* becomes 7d (coverageState is weeks-stable; fixes the 0/197 cache-hit problem from S34). **Group D:** finding lifecycle infrastructure — `finding-history.json` (run_count tracker with same-commit guard + ESCALATE marker at run_count>=3) + `watchpoints.json` (auto-emitted on `code_changed_since_gsc_window=true` + 21-day recheck + 90-day evict). Three new helper subcommands. **Top correctness fixes:** `head -1 sa-q2-*.json` race → deterministic hash recomputation; DST off-by-one via `time.mktime` → `datetime.date.fromisoformat()`; null-metric TypeError; operator precedence in `classify_transition`; bare `.tmp` race → PID suffix; 20-worker rate-limit burst → 6 workers + retries.

## In Progress

**`/bx:evolve` 2.12.0 — all S61 follow-ups shipped, first real run owed (S62).** The three 2.11.0 run-found defects (lane-freshness skip via `git ls-remote`, edit-shape re-grep, pain-id match) and improvements 7–10: `lane-contract.md` (named owner of the shared lane text; scan files cite it), `scripts/docs-page-hashes.py` + `watermark.docs_pages`/`inventory_hash` (docs lane reads only changed pages — the `.md` endpoint hashes with zero tokens), `scripts/build-capabilities.py` → pinned `capabilities.json` (434 entries, the only legal `affected_capability` vocabulary), community lane rewritten as an official-source discovery feed (`findings: []`). Docs and community lanes each verified by one live dispatch. **Owed:** push + cache refresh, then the first `/bx:evolve` run (seeds the hash map; exercises Step 1.5, 3.4 pain-id, `--check` drift, the changelog lane under the contract); the plugin-eval design item `69ef485d`.

**Doc tiering phase 1 — the two S61 run-found defects fixed in 2.12.0; this save was the first run of the fix.** The `--full` sweep (Parts 2–7) now runs before the writer dispatch and the session entry carries a `Full sweep:` bullet; the open-phase 300-char floor became "entry at least 500 chars longer than its composed replacement line", with a *looks resolved — confirm* heading in the 7.4 prompt. Lint K20/K23 pin both. Still open: deferred minors (guard checks inequality not increase; guard tests not hermetic against `commit.gpgsign`; lint and fixture tests not in CI; `save-writer`'s unreachable `status: open` path); CLAUDE.md sits just over the 12k soft cap with no section over its shrinker threshold; Phase 2 (`.claude/rules/` tier) gated on re-verifying `paths:`. Plan: `docs/superpowers/plans/2026-09-28-bx-doc-tiering-phase1.md`.

**Doc schema v2 post-merge verification (S56–57).** The first `/bx:save --full` on schema v2 ran S57: Part 5 found all older sessions already compressed, Parts 6/7 under caps, and rotation did not fire then. It has since fired: `docs/archive/key-decisions-1.md` exists and the live `docs/key-decisions.md` measured 53k on 2026-09-28 (S60). Still owed from the deferred Task 10 skill-steps: live `/bx:save` runs against the fixtures (fx-v2 no-op, fx-partial resume, fx-dirty skip, fx-v1-envvars keep path, fx-v1-sparse scaffold, fx-v1-ineligible decline). Post-merge minors parked in both plans: backlog symptom measurement (7.7's clause is unreachable), checker fence-strip/CR robustness, mode-migrate declines-bullet v1-only phrasing, resume Quick Reference partial row, structure-rules cell wording.

**`/bx:webdesign` kaanarik run paused at `review_pending` (S52).** Resume via `/bx:webdesign` (plugin is current), push through Phase 3 inject+verify. Phase 3e now asks the user before the destructive-git rollback (`dadac845` + `6712a71e` applied S61); verify live there that auto mode accepts the confirmed rollback.

**S37 plugin packaging leftovers.** Retire `~/.claude` symlinks and the launcher-script symlink check. (Install smoke-test closed v2.6.0; the `Skill(bx-*)` → `Skill(bx:*)` sweep is moot — S59 found no `Skill(bx-*)` anywhere in the repo, and the stale local `Skill(bx:docs)` allow entry was renamed to `Skill(bx:save)`.)

**`/bx:arch` review depth v2 shipped and dogfooded (S58).** Eight phases took the skill from a function-level refactor scanner to a six-dimension architecture review: catalog 23 → 54 entries (D design/SOLID, C concurrency, E error safety, X scalability), a fifth scanner `arch-robustness`, a calibrated finding contract (`finding-rubrics.md` — anchored severity, certainty by evidence class, mandatory `evidence` + `why_this_might_be_wrong`), thesis-first report with theme synthesis, and churn × fan-in in the rank score. Spec: `docs/superpowers/specs/2026-08-24-bx-arch-review-depth-design.md`. **Owed:** `/plugin update bx`, then the first end-to-end run — rehearsals prove the instructions are unambiguous, only a real run proves the scanners find anything useful.

## Next Steps

1. **Push 2.12.0, refresh the cache, run the first `/bx:evolve` on it** — push main, `claude plugin update bx` + `/reload-plugins`; the run seeds `watermark.docs_pages` (all 22 pages once), and is the first execution of Step 1.5's freshness skip, the 3.4 pain-id match, the `--check` drift line and the changelog lane under `lane-contract.md`. Then a same-day `--fix` should show the changelog and docs lanes `current`.
2. **Doc tiering Phase 2** (`.claude/rules/` tier, spec D4–D6), gated on re-verifying `paths:` against the memory docs; plus the deferred minors listed in `## In Progress`.
3. **Doc-schema v2 fixture verification** — the deferred live `/bx:save` runs against the six fixture cases (fx-v2 no-op, fx-partial resume, fx-dirty skip, fx-v1-envvars keep path, fx-v1-sparse scaffold, fx-v1-ineligible decline), plus the post-merge minors batch from both plans.
4. **/simplify follow-up: move Part 7.7 rotation out of Part 7** into its own sibling Part — deletes the five "except 7.7" carve-outs; requires a blind rehearsal before shipping. The S59 spec's D4 proposes a Part 7.9 sibling on the same reasoning — do these together.
5. **Resume the `/bx:webdesign` kaanarik run past review** — push through Phase 3 inject+verify; verify finding `dadac845` live (Phase 3e asks before the destructive-git rollback).
6. **Real `/bx:seo` run against burakarik.com** — auth fixed S39, content-review-hardened S45; code-review leftovers (#5/#6/#7) + S25/S27/S29 refactors still deferred.
7. **Dogfood `/bx:health`** — the last skill never run end-to-end; every first run so far produced defects.
8. **Design the plugin-eval suite** (`69ef485d`, deferred in `docs/upstream/state.json`) — `claude plugin eval` is pinned on the docs allowlist.
9. **S37 plugin-packaging leftovers** — symlink retirement and the launcher-script symlink check.
10. **Commit regression tests for S58's two concurrency fixes** (session-color mutex, GSC `_rmw_lock`) and **sweep the 13 remaining exclusion-list restatements** in `/bx:seo`, `/bx:webdesign`, `/bx:clean` (owner: `arch/references/scan-exclusions.md`).

## Session History

> Full history: [session-history.md](session-history.md)

### Last Session (Session 62) - 2026-10-21
- **bx 2.12.0 (uncommitted → committed this save):** `/bx:save --full` fixed — the sweep (Parts 2–7) runs before the writer dispatch and the open-phase floor is saving-based; this save was the fix's first run (compressed S57–58, rolled up 6 Key Decisions rows, repaired a table gap).
- **`/bx:evolve` three run-found defects fixed:** lane-freshness skip (`git ls-remote` for the changelog head; probe for docs; same-day for community), edit-shape re-grep (additive edits probe the new text), pain-id match as a third 3.4 lookup.
- **Improvements 7–10 shipped:** `lane-contract.md` (scan files cite, never restate), docs lane reads only changed pages via a zero-token `.md` hash probe (`watermark.docs_pages`, `inventory_hash`), pinned `capabilities.json` (434 entries, generated), community lane re-scoped to an official-source discovery feed.
- Live dispatches of the rewritten docs and community lanes returned contract-conformant output; validator + planted-failure tests, both lints and `claude plugin validate --strict` pass.
- Full sweep: compressed sessions 57–58, moved 6 Key Decisions rows to `docs/key-decisions.md`, README/architecture trees updated, one memory added; CLAUDE.md 13.9k → ~12.2k, no shrinker threshold reached.
