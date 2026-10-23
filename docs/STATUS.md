# Project Status

> Session state for `/bx:resume`. Instructions live in [CLAUDE.md](../CLAUDE.md).

Last Updated: 2026-10-23 (Session 64)

## Current Status

| Area | Status |
|------|--------|
| Skills (11) | Complete — `/bx:clean` content-reviewed and extended with seven categories S63 (bx 2.13.0; 60/60 on fixtures) and run for real S64 on maxitech-concierge (Python; 6 defects fixed in 2.13.1); `/bx:save --full` run three times on the reordered sweep (S62 ×2, S63); `/bx:evolve` 2.12.x run four times S62; only `/bx:health` never run |
| Subagents (20) | Complete — `arch-robustness` added S58 |
| Plugin packaging (`bx`) | **v2.13.1** pushed S64 (`8e964eb`); install pending (cache at 2.13.0). Refresh is `/plugin marketplace update burak-tools` + shell `claude plugin update bx` + `/reload-plugins`. Version-bump guard: `scripts/check-plugin-version-bump.sh`, `.githooks/pre-push` (enabled on this clone), CI workflow. Symlink retirement still pending |
| Doc schema v2 | Complete — shipped S56; this repo migrated |
| Startup scripts | Complete — S55 live gate passed and fix wave shipped in `7ed079a` (2026-08-17), recorded S61 |
| Cross-platform setup | Complete |
| GitHub sync | Complete — main pushed through v2.13.1 (S64, `8e964eb`) |
| Documentation | Complete — schema v2 |

## Completed

All 11 skills, 20 subagents, cross-platform setup, and documentation system are complete.

See [completed-work.md](completed-work.md) for full checklist.

**`/seo-review` hardened across 4 improvement groups + 15 code-review fixes (S35, 2026-05-26).** Same-day continuation of S34 burakarik.com dogfood. User ran the skill with new `known-bad-urls.txt`; orchestrator wrote a 396-line `_inspect_batch.py` into `.seo-data/gsc/` (third disk-write boundary violation across S31 cont.² + S34 + S35) + only inspected 50 of 100 pasted URLs. Shipped 4 groups + ran `/code-review` extra-high effort surfacing 15 findings, then fixed all 15 same-session (+1105/-71 LOC across 7 files, uncommitted). **Group A:** new `inspect-batch` helper subcommand (parallel HTTP via ThreadPoolExecutor + per-URL cache + atomic write + 429/5xx retry); broader disk-write boundary rule forbidding ALL orchestrator-written scripts under `.seo-data/gsc/`. **Group B:** subagent-skip rule codified (new Step 4.5) with 4 gating conditions + audit-trail marking + `--force-dispatch` escape hatch. **Group C:** cache TTL split — sa-* stays 24h, ui-* becomes 7d (coverageState is weeks-stable; fixes the 0/197 cache-hit problem from S34). **Group D:** finding lifecycle infrastructure — `finding-history.json` (run_count tracker with same-commit guard + ESCALATE marker at run_count>=3) + `watchpoints.json` (auto-emitted on `code_changed_since_gsc_window=true` + 21-day recheck + 90-day evict). Three new helper subcommands. **Top correctness fixes:** `head -1 sa-q2-*.json` race → deterministic hash recomputation; DST off-by-one via `time.mktime` → `datetime.date.fromisoformat()`; null-metric TypeError; operator precedence in `classify_transition`; bare `.tmp` race → PID suffix; 20-worker rate-limit burst → 6 workers + retries.

## In Progress

**`/bx:evolve` 2.12.x — shipped, run four times, three run-found defects fixed (S62).** 2.12.0 delivered the three 2.11.0 defects and improvements 7–10 (`lane-contract.md`, `scripts/docs-page-hashes.py` + `watermark.docs_pages`/`inventory_hash`, pinned `capabilities.json` via `scripts/build-capabilities.py`, community lane as a discovery feed). Four real runs: delta 22/22 pages (5 findings), `--fix` with all lanes current (3 applied + `env-vars` pinned), delta 5/23 (1 finding), `--fix` all-current (1 applied). Fixed in 2.12.1: registry threshold `min(3, n)`, validator pattern for the pinned vocabulary. **Open:** the probe's delta-aware scan (narrowed by hand once), candidates persisting into `--fix`, a `source_url` tie-break rule, the plugin-eval design `69ef485d` (needs `bx/evals/` + `claude plugin eval init`).

**Doc tiering phase 1 — the two S61 defects fixed in 2.12.0 and run twice (S62).** The `--full` sweep (Parts 2–7) runs before the writer dispatch; the second run exercised the Part 7.3 size-based Key Decisions rollup for real (8 rows moved, CLAUDE.md 12.7k → 9.3k). The open-phase floor is saving-based with a *looks resolved — confirm* heading; lint K20/K23 pin both. Still open: deferred minors (guard checks inequality not increase; guard tests not hermetic against `commit.gpgsign`; lint and fixture tests not in CI; `save-writer`'s unreachable `status: open` path); Phase 2 (`.claude/rules/` tier) is now unblocked — the memory docs confirm `paths:` is the only rule frontmatter field (deferred finding `5b91feb3` carries the edit). Plan: `docs/superpowers/plans/2026-09-28-bx-doc-tiering-phase1.md`.

**Doc schema v2 post-merge verification (S56–57).** The first `/bx:save --full` on schema v2 ran S57: Part 5 found all older sessions already compressed, Parts 6/7 under caps, and rotation did not fire then. It has since fired: `docs/archive/key-decisions-1.md` exists and the live `docs/key-decisions.md` measured 53k on 2026-09-28 (S60). Still owed from the deferred Task 10 skill-steps: live `/bx:save` runs against the fixtures (fx-v2 no-op, fx-partial resume, fx-dirty skip, fx-v1-envvars keep path, fx-v1-sparse scaffold, fx-v1-ineligible decline). Post-merge minors parked in both plans: backlog symptom measurement (7.7's clause is unreachable), checker fence-strip/CR robustness, mode-migrate declines-bullet v1-only phrasing, resume Quick Reference partial row, structure-rules cell wording.

**`/bx:webdesign` kaanarik run paused at `review_pending` (S52).** Resume via `/bx:webdesign` (plugin is current), push through Phase 3 inject+verify. Phase 3e now asks the user before the destructive-git rollback (`dadac845` + `6712a71e` applied S61); verify live there that auto mode accepts the confirmed rollback.

**S37 plugin packaging leftovers.** Retire `~/.claude` symlinks and the launcher-script symlink check. (Install smoke-test closed v2.6.0; the `Skill(bx-*)` → `Skill(bx:*)` sweep is moot — S59 found no `Skill(bx-*)` anywhere in the repo, and the stale local `Skill(bx:docs)` allow entry was renamed to `Skill(bx:save)`.)

**`/bx:arch` review depth v2 shipped and dogfooded (S58).** Eight phases took the skill from a function-level refactor scanner to a six-dimension architecture review: catalog 23 → 54 entries (D design/SOLID, C concurrency, E error safety, X scalability), a fifth scanner `arch-robustness`, a calibrated finding contract (`finding-rubrics.md` — anchored severity, certainty by evidence class, mandatory `evidence` + `why_this_might_be_wrong`), thesis-first report with theme synthesis, and churn × fan-in in the rank score. Spec: `docs/superpowers/specs/2026-08-24-bx-arch-review-depth-design.md`. **Owed:** `/plugin update bx`, then the first end-to-end run — rehearsals prove the instructions are unambiguous, only a real run proves the scanners find anything useful.

## Next Steps

1. **`/bx:evolve` 2.12.x follow-ups** — make `docs-page-hashes.py` delta-aware (diff the live inventory against the last committed `capabilities.json`; scan only pages whose markdown contains an added or removed token, instead of all 23 on any change), persist `allowlist_candidates` from a delta run into its `--fix`, add a `source_url` tie-break rule (larger file overlap) to Step 3.4; PATCH bump.
2. **Doc tiering Phase 2** (`.claude/rules/` tier, spec D4–D6) — unblocked S62: the memory docs confirm `paths:` is the only rule frontmatter field (YAML list or comma string; unparseable YAML loads the rule unconditionally); the edit is stored on deferred finding `5b91feb3`. Plus the deferred minors listed in `## In Progress`.
3. **Doc-schema v2 fixture verification** — the deferred live `/bx:save` runs against the six fixture cases (fx-v2 no-op, fx-partial resume, fx-dirty skip, fx-v1-envvars keep path, fx-v1-sparse scaffold, fx-v1-ineligible decline), plus the post-merge minors batch from both plans.
4. **/simplify follow-up: move Part 7.7 rotation out of Part 7** into its own sibling Part — deletes the five "except 7.7" carve-outs; requires a blind rehearsal before shipping. The S59 spec's D4 proposes a Part 7.9 sibling on the same reasoning — do these together.
5. **Resume the `/bx:webdesign` kaanarik run past review** — push through Phase 3 inject+verify; verify finding `dadac845` live (Phase 3e asks before the destructive-git rollback).
6. **Real `/bx:seo` run against burakarik.com** — auth fixed S39, content-review-hardened S45; code-review leftovers (#5/#6/#7) + S25/S27/S29 refactors still deferred.
7. **Dogfood `/bx:health`** — the last skill never run end-to-end; every first run so far produced defects.
8. **Design the plugin-eval suite** (`69ef485d`, deferred in `docs/upstream/state.json`) — `claude plugin eval` is pinned on the docs allowlist.
9. **S37 plugin-packaging leftovers** — symlink retirement and the launcher-script symlink check.
10. **Commit regression tests for S58's two concurrency fixes** (session-color mutex, GSC `_rmw_lock`) and **sweep the 12 remaining exclusion-list restatements** in `/bx:seo`, `/bx:webdesign` (owner: `arch/references/scan-exclusions.md`; `/bx:clean` repointed S63).
11. **Install bx 2.13.1, then run `/bx:clean` on a real JS/TS repo** (e.g. horowell or kaanarik). The S64 Python run found six defects, fixed in 2.13.1. Still never exercised: the JS categories, the directory-scope rule (`/bx:clean <dir> --deps` should skip), `--dry-run`, and the files-code/styles-tests scanners after the 2.13.1 edits. Optional: apply the five unused-import quick wins in maxitech-concierge, and decide whether its `title_template`/`personality` keys get wired in or deleted (the PRD calls them configurable, but no code reads them).

## Session History

> Full history: [session-history.md](session-history.md)

### Last Session (Session 64) - 2026-10-23
- **First real `/bx:clean` run** on maxitech-concierge (Python/FastAPI, report-only). The codebase came out clean: 5 unused test imports, `datetime.utcnow()` at about 25 call sites, and 3 unread `assistant.json` keys, two of which the PRD documents. No files were changed in that repo.
- **Six skill defects found and fixed in bx 2.13.1** (scan-deps-config/files-code/styles-tests + SKILL.md):
  - The `sign_off` dead-key false positive. Accessors are now traced, and a quoted-key grep plus a docs grep is mandatory.
  - Runtime-consumed deps now go under `## Used without import`.
  - Kept-deliberately env vars now go under `## Kept deliberately`.
  - Skipped, clean and unavailable checks are now separated.
  - Settings fields are owned by §6 only.
  - `quick_win` now implies `safe`.
- **Scanner output varied from run to run.** Three reruns of one scan file produced three different unavailable blocks, so SKILL.md Step 2.5 now normalises the block in the orchestrator. One run also rated a PRD-documented key `safe`, so any doc mention now caps a key at `needs_investigation`.
- **Verification:** five reruns of the deps-config scanner. The final two independent runs both passed every check. The files-code and styles-tests scanners were not re-run.
- Committed and pushed v2.13.1 (`8e964eb`). Install is still pending.
