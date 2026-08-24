# Project Status

> Session state for `/bx:resume`. Instructions live in [CLAUDE.md](../CLAUDE.md).

Last Updated: 2026-08-24 (Session 58)

## Current Status

| Area | Status |
|------|--------|
| Skills (11) | Complete — `/bx:arch` and `/bx:evolve` dogfooded end-to-end S58 |
| Subagents (20) | Complete — `arch-robustness` added S58 |
| Plugin packaging (`bx`) | **v2.6.0 pushed S58**; install smoke-test now automated (Part 8 step 2b, `claude plugin validate --strict`). Local cache on 2.5.1 — `/plugin update bx` needed. Symlink retirement still pending |
| Doc schema v2 | Complete — shipped S56; this repo migrated |
| Startup scripts | Complete — S55 live gate still pending |
| Cross-platform setup | Complete |
| GitHub sync | Complete — main pushed through v2.6.0 (`db1f3b5`) |
| Documentation | Complete — schema v2 |

## Completed

All 11 skills, 19 subagents, cross-platform setup, and documentation system are complete.

See [completed-work.md](completed-work.md) for full checklist.

**`/seo-review` hardened across 4 improvement groups + 15 code-review fixes (S35, 2026-05-26).** Same-day continuation of S34 burakarik.com dogfood. User ran the skill with new `known-bad-urls.txt`; orchestrator wrote a 396-line `_inspect_batch.py` into `.seo-data/gsc/` (third disk-write boundary violation across S31 cont.² + S34 + S35) + only inspected 50 of 100 pasted URLs. Shipped 4 groups + ran `/code-review` extra-high effort surfacing 15 findings, then fixed all 15 same-session (+1105/-71 LOC across 7 files, uncommitted). **Group A:** new `inspect-batch` helper subcommand (parallel HTTP via ThreadPoolExecutor + per-URL cache + atomic write + 429/5xx retry); broader disk-write boundary rule forbidding ALL orchestrator-written scripts under `.seo-data/gsc/`. **Group B:** subagent-skip rule codified (new Step 4.5) with 4 gating conditions + audit-trail marking + `--force-dispatch` escape hatch. **Group C:** cache TTL split — sa-* stays 24h, ui-* becomes 7d (coverageState is weeks-stable; fixes the 0/197 cache-hit problem from S34). **Group D:** finding lifecycle infrastructure — `finding-history.json` (run_count tracker with same-commit guard + ESCALATE marker at run_count>=3) + `watchpoints.json` (auto-emitted on `code_changed_since_gsc_window=true` + 21-day recheck + 90-day evict). Three new helper subcommands. **Top correctness fixes:** `head -1 sa-q2-*.json` race → deterministic hash recomputation; DST off-by-one via `time.mktime` → `datetime.date.fromisoformat()`; null-metric TypeError; operator precedence in `classify_transition`; bare `.tmp` race → PID suffix; 20-worker rate-limit burst → 6 workers + retries.

## In Progress

**Doc schema v2 post-merge verification (S56–57).** The first `/bx:save --full` on schema v2 ran S57: Part 5 found all older sessions already compressed, Parts 6/7 under caps, and rotation did NOT fire — `docs/key-decisions.md` sits at ~98k, just under the 100k trigger, so the first real rotation lands on an upcoming `--full`. Still owed from the deferred Task 10 skill-steps: live `/bx:save` runs against the fixtures (fx-v2 no-op, fx-partial resume, fx-dirty skip, fx-v1-envvars keep path, fx-v1-sparse scaffold, fx-v1-ineligible decline). Post-merge minors parked in both plans: backlog symptom measurement (7.7's clause is unreachable), checker fence-strip/CR robustness, mode-migrate declines-bullet v1-only phrasing, resume Quick Reference partial row, structure-rules cell wording.

**Per-project `cc` session naming + coloring — built, 2 items open (S55).** Unchanged from S55: the human live gate (`cc claude-config`: prompt bar colored? name chip + tab title? no model turn?) and one batched fix wave held until the gate reports (ASCII-sweep `start-claude.ps1`, `try/catch` guard, `ToLowerInvariant()`, 0-byte registry handling, case-insensitivity assertion, stale plan/spec sweep). Spec: `docs/superpowers/specs/2026-08-12-cc-session-naming-design.md`.

**`/bx:webdesign` kaanarik run paused at `review_pending` (S52).** Unchanged: resume via `/bx:webdesign` after `/plugin update bx`, push through Phase 3 inject+verify; verify open finding `dadac845` while there.

**S37 plugin packaging leftovers.** Install smoke-test, retire `~/.claude` symlinks, `settings.local.json` `Skill(bx-*)` → `Skill(bx:*)`, launcher-script symlink-check retirement.

**`/bx:arch` review depth v2 shipped and dogfooded (S58).** Eight phases took the skill from a function-level refactor scanner to a six-dimension architecture review: catalog 23 → 54 entries (D design/SOLID, C concurrency, E error safety, X scalability), a fifth scanner `arch-robustness`, a calibrated finding contract (`finding-rubrics.md` — anchored severity, certainty by evidence class, mandatory `evidence` + `why_this_might_be_wrong`), thesis-first report with theme synthesis, and churn × fan-in in the rank score. Spec: `docs/superpowers/specs/2026-08-24-bx-arch-review-depth-design.md`. **Owed:** `/plugin update bx`, then the first end-to-end run — rehearsals prove the instructions are unambiguous, only a real run proves the scanners find anything useful.

## Next Steps

1. **`/plugin update bx`** — main is on v2.6.0, the local cache on 2.5.1, so Part 8's new `claude plugin validate` step is not live yet.
2. **Doc tiering — decision pass on the `/doctor` findings (S59)** — spec drafted at [superpowers/specs/2026-08-24-bx-doc-tiering-design.md](superpowers/specs/2026-08-24-bx-doc-tiering-design.md); status Draft, 8 decisions open, nothing implemented. Field evidence from a `/doctor` run on a repo that uses `/bx:save` every session: CLAUDE.md at 31.1k chars (2.6× the 12k soft cap) with `## Known Issues / Blockers` at 48% of it — the one required section with no cap, no shrinker and no archive destination. Recommended split: ship the Known Issues governor + relocate-don't-delete + the derivable-content clause first; hold the `.claude/rules/` path-scoped tier behind a second gate. Pairs with #5.
3. **Finish the `cc` session naming/coloring rollout (S55)** — run the live gate, then dispatch the single fix wave listed in `## In Progress`.
4. **Doc-schema v2 fixture verification** — the deferred live `/bx:save` runs against the six fixture cases (see `## In Progress`), plus the post-merge minors batch from both plans.
5. **/simplify follow-up: move Part 7.7 rotation out of Part 7** into its own sibling Part — deletes the five "except 7.7" carve-outs; requires a blind rehearsal before shipping (deliberately skipped S57). The S59 spec's D4 proposes a Part 7.9 sibling on the same reasoning — do these together.
6. **Resume the `/bx:webdesign` kaanarik run past review** — push through Phase 3 inject+verify; verify finding `dadac845`.
7. **Real `/bx:seo` run against burakarik.com** — auth fixed S39, content-review-hardened S45.
8. **Dogfood `/bx:tests` and `/bx:health`** — hardened S46, still never run end-to-end. `/bx:arch` and `/bx:evolve` were dogfooded S58 and each produced real skill defects on the first run; expect the same here.
9. **S37 plugin-packaging leftovers** — install smoke-test, symlink retirement, `Skill(bx-*)` → `Skill(bx:*)`.
10. **`/bx:evolve` follow-ups** — fix Step 3.4's missing `applied` branch and store `source_excerpt` alongside the hash; stabilise the `bx:pain/<slug>` derivation. 18 open findings, incl. three fresh: `df34007f` (`/plugin install` auto-refresh — check whether `update` behaves the same before touching docs), `59d3bdac` (background-by-default dispatch — this run corroborated bx's fan-outs still block, so it is a documentation gap not a break), `3dd5decb` (`/code-review` ladder, predicted to reject as already-covered). Also: scan-docs allowlist candidate (`auto-mode-config`); shared `references/lane-contract.md`.
11. **`/bx:seo` deferred items** — code-review leftovers (#5/#6/#7) + S25/S27/S29 refactors.

## Session History

> Full history: [session-history.md](session-history.md)

### Last Session (Session 58) - 2026-08-24
- **Recovered an outage-truncated session**, then swept the class its `/bx:evolve` run had flagged and left open: v2.1.233 removed the task-tracker tools from the default toolset and five skills promised behaviour that could not run. Canonical owner `task-tools.md` + a degraded path per skill (**v2.2.0**).
- **`/bx:arch` review depth v2 (v2.3.0)** — 8 phases via `/bx:plan`. Fixed three rules that made architecture *worse* (S01 deleting Dependency Inversion, S06 deleting trust-boundary validation, a CCN-only gate deleting its own catalog's quick wins), then added the dimensions with zero coverage. Catalog 23 → 54; fifth scanner `arch-robustness`; calibrated finding contract; report opens with a thesis.
- **First end-to-end dogfood found four skill defects** (**v2.4.0**) that six rehearsal waves could not — rehearsals feed scanners synthetic findings, so an empty category and an inverted trust flag are structurally invisible. Applied its four fix-eligible code findings (**v2.4.1**), then the remaining four (**v2.5.0–v2.5.1**).
- **Both concurrency fixes were wrong until executed.** A 100ms backoff let 8 racers exceed a 5s cap and collide anyway; a defensive stale-reap destroyed *live* locks. Verified by measurement: 5/5 trials 8-way distinct, and 10-of-12 lost updates without the Python lock vs 12/12 with it.
- **`/bx:evolve` full run released the watermark** (2.1.228 → 2.1.241, frozen since S53) and applied `claude plugin validate` into `/bx:save` Part 8 (**v2.6.0**), closing the S37 install-smoke-test leftover. Its own first run exposed a Step 3.4 branch that does not exist.
