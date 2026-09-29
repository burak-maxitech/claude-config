# Project Status

> Session state for `/bx:resume`. Instructions live in [CLAUDE.md](../CLAUDE.md).

Last Updated: 2026-09-28 (Session 60)

## Current Status

| Area | Status |
|------|--------|
| Skills (11) | Complete — `/bx:save` model-invocable S59; `/bx:evolve --full --fix` dogfooded S59; only `/bx:health` never run |
| Subagents (20) | Complete — `arch-robustness` added S58 |
| Plugin packaging (`bx`) | **v2.10.0 built S60 on branch `feat/doc-tiering-phase1`, NOT merged, pushed or installed.** v2.9.0 pushed and installed S59 (`511b197`); Part 8 step 2b judges `claude plugin validate --json` on its `success` field. Local cache on 2.9.0; `/bx:save` confirmed visible to Claude after `/reload-plugins`. Symlink retirement still pending |
| Doc schema v2 | Complete — shipped S56; this repo migrated |
| Startup scripts | Complete — S55 live gate still pending |
| Cross-platform setup | Complete |
| GitHub sync | Complete — main pushed through v2.9.0 (`511b197`) |
| Documentation | Complete — schema v2 |

## Completed

All 11 skills, 19 subagents, cross-platform setup, and documentation system are complete.

See [completed-work.md](completed-work.md) for full checklist.

**`/seo-review` hardened across 4 improvement groups + 15 code-review fixes (S35, 2026-05-26).** Same-day continuation of S34 burakarik.com dogfood. User ran the skill with new `known-bad-urls.txt`; orchestrator wrote a 396-line `_inspect_batch.py` into `.seo-data/gsc/` (third disk-write boundary violation across S31 cont.² + S34 + S35) + only inspected 50 of 100 pasted URLs. Shipped 4 groups + ran `/code-review` extra-high effort surfacing 15 findings, then fixed all 15 same-session (+1105/-71 LOC across 7 files, uncommitted). **Group A:** new `inspect-batch` helper subcommand (parallel HTTP via ThreadPoolExecutor + per-URL cache + atomic write + 429/5xx retry); broader disk-write boundary rule forbidding ALL orchestrator-written scripts under `.seo-data/gsc/`. **Group B:** subagent-skip rule codified (new Step 4.5) with 4 gating conditions + audit-trail marking + `--force-dispatch` escape hatch. **Group C:** cache TTL split — sa-* stays 24h, ui-* becomes 7d (coverageState is weeks-stable; fixes the 0/197 cache-hit problem from S34). **Group D:** finding lifecycle infrastructure — `finding-history.json` (run_count tracker with same-commit guard + ESCALATE marker at run_count>=3) + `watchpoints.json` (auto-emitted on `code_changed_since_gsc_window=true` + 21-day recheck + 90-day evict). Three new helper subcommands. **Top correctness fixes:** `head -1 sa-q2-*.json` race → deterministic hash recomputation; DST off-by-one via `time.mktime` → `datetime.date.fromisoformat()`; null-metric TypeError; operator precedence in `classify_transition`; bare `.tmp` race → PID suffix; 20-worker rate-limit burst → 6 workers + retries.

## In Progress

**Doc tiering phase 1 — built on `feat/doc-tiering-phase1`, awaiting merge decision (S60).** v2.10.0: `docs/known-issues.md` archive, relocate-don't-delete, Known Issues shrinker (4000/2500), 9k advisory rung, derivable-content clause, version-bump guard, six `/bx:evolve` findings. Open with the user: narrow `omitClaudeMd` to the three `upstream-*` agents; fix `/bx:health`'s v1 state read; clean eight stale-text sites; merge + push; enable the pre-push hook. Plan: `docs/superpowers/plans/2026-09-28-bx-doc-tiering-phase1.md`.

**Doc schema v2 post-merge verification (S56–57).** The first `/bx:save --full` on schema v2 ran S57: Part 5 found all older sessions already compressed, Parts 6/7 under caps, and rotation did not fire then. It has since fired: `docs/archive/key-decisions-1.md` exists and the live `docs/key-decisions.md` measured 53k on 2026-09-28 (S60). Still owed from the deferred Task 10 skill-steps: live `/bx:save` runs against the fixtures (fx-v2 no-op, fx-partial resume, fx-dirty skip, fx-v1-envvars keep path, fx-v1-sparse scaffold, fx-v1-ineligible decline). Post-merge minors parked in both plans: backlog symptom measurement (7.7's clause is unreachable), checker fence-strip/CR robustness, mode-migrate declines-bullet v1-only phrasing, resume Quick Reference partial row, structure-rules cell wording.

**Per-project `cc` session naming + coloring — built, 2 items open (S55).** Unchanged from S55: the human live gate (`cc claude-config`: prompt bar colored? name chip + tab title? no model turn?) and one batched fix wave held until the gate reports (ASCII-sweep `start-claude.ps1`, `try/catch` guard, `ToLowerInvariant()`, 0-byte registry handling, case-insensitivity assertion, stale plan/spec sweep). Spec: `docs/superpowers/specs/2026-08-12-cc-session-naming-design.md`.

**`/bx:webdesign` kaanarik run paused at `review_pending` (S52).** Unchanged: resume via `/bx:webdesign` after `/plugin update bx`, push through Phase 3 inject+verify; verify open finding `dadac845` while there.

**S37 plugin packaging leftovers.** Retire `~/.claude` symlinks and the launcher-script symlink check. (Install smoke-test closed v2.6.0; the `Skill(bx-*)` → `Skill(bx:*)` sweep is moot — S59 found no `Skill(bx-*)` anywhere in the repo, and the stale local `Skill(bx:docs)` allow entry was renamed to `Skill(bx:save)`.)

**`/bx:arch` review depth v2 shipped and dogfooded (S58).** Eight phases took the skill from a function-level refactor scanner to a six-dimension architecture review: catalog 23 → 54 entries (D design/SOLID, C concurrency, E error safety, X scalability), a fifth scanner `arch-robustness`, a calibrated finding contract (`finding-rubrics.md` — anchored severity, certainty by evidence class, mandatory `evidence` + `why_this_might_be_wrong`), thesis-first report with theme synthesis, and churn × fan-in in the rank score. Spec: `docs/superpowers/specs/2026-08-24-bx-arch-review-depth-design.md`. **Owed:** `/plugin update bx`, then the first end-to-end run — rehearsals prove the instructions are unambiguous, only a real run proves the scanners find anything useful.

## Next Steps

1. **Land and dogfood v2.10.0 (S60)** — settle the five open decisions in `## In Progress`, merge `feat/doc-tiering-phase1`, push, `/plugin update bx` + `/reload-plugins`, then run `/bx:save --full` here: CLAUDE.md is over 12k with Known Issues over 4000, so the new shrinker fires. Expect defects; five rules have never executed. Phase 2 (`.claude/rules/` tier, spec D4–D6) stays gated; re-verify `paths:` against the memory docs first. Pairs with #4.
2. **Finish the `cc` session naming/coloring rollout (S55)** — run the live gate, then dispatch the single fix wave listed in `## In Progress`.
3. **Doc-schema v2 fixture verification** — the deferred live `/bx:save` runs against the six fixture cases (see `## In Progress`), plus the post-merge minors batch from both plans.
4. **/simplify follow-up: move Part 7.7 rotation out of Part 7** into its own sibling Part — deletes the five "except 7.7" carve-outs; requires a blind rehearsal before shipping (deliberately skipped S57). The S59 spec's D4 proposes a Part 7.9 sibling on the same reasoning — do these together.
5. **Resume the `/bx:webdesign` kaanarik run past review** — push through Phase 3 inject+verify; verify finding `dadac845`.
6. **Real `/bx:seo` run against burakarik.com** — auth fixed S39, content-review-hardened S45.
7. **Dogfood `/bx:health`** — the last skill never run end-to-end. Five skills were dogfooded S58 and every one produced defects on its first run; expect the same.
8. **S37 plugin-packaging leftovers** — symlink retirement and the launcher-script symlink check (install smoke-test and the `Skill(bx-*)` sweep are closed).
9. **`/bx:evolve` follow-ups** — (a) hand-triage the 18 carried-forward open findings from their stored titles; S59 proved neither a follow-up `--fix` nor `--full --fix` can reach them (fix mode gates same-run findings only; the changelog window floors at v2.1.203; the lanes drop already-implemented deltas); (b) store `source_excerpt` in state.json so carried-forward entries become fix-eligible; (c) add an `applied` branch and a same-`source_url` dedup to Step 3.4 — v2.1.233 re-entered as `e1e67d43` beside applied `5d1459d5`; (d) reword the default-mode closing line, which oversells a second pass; (e) stabilise the `bx:pain/<slug>` derivation. Also: scan-docs allowlist candidate (`auto-mode-config`); shared `references/lane-contract.md`.
10. **`/bx:seo` deferred items** — code-review leftovers (#5/#6/#7) + S25/S27/S29 refactors.
11. **Commit regression tests for S58's two concurrency fixes** — `/bx:tests`' top-ranked finding. Both v2.5.0 (session-color mutex) and v2.5.1 (GSC `_rmw_lock`) were verified with throwaway controls that were never committed, so the evidence of correctness lives in commit messages rather than the repo. Port both harnesses: N racing processes, assert distinct results, no lost updates, no orphaned lock.
12. **Sweep the 13 remaining exclusion-list restatements** — `/bx:seo`, `/bx:webdesign` and `/bx:clean` still carry their own copies; the owner file `arch/references/scan-exclusions.md` lists them.

## Session History

> Full history: [session-history.md](session-history.md)

### Last Session (Session 60) - 2026-09-28
- **Doc tiering decided and phase 1 built (v2.10.0, unmerged).** All 8 spec decisions accepted with two amendments; Known Issues gets an archive (`docs/known-issues.md`), relocate-don't-delete, and a resolved-first shrinker. Branch `feat/doc-tiering-phase1`, 13 commits.
- **`/bx:evolve` delta run** (2.1.263 → 2.1.284, 19 releases): 5 findings, 4 applied by hand plus 2 from the backlog; 18 remain open.
- **Version-bump guard added outside the skill:** script, opt-in pre-push hook, GitHub Actions workflow (9/9 tests; workflow never run).
- **Rehearsals passed outcomes but not the ambiguity bar** (raw 9–16 vs ≤2); a fresh whole-branch review found seven defects synthetic fixtures could not reach, all fixed (`e511475`).
- **Not done:** merge, push, install, dogfood; `/bx:health` still reads state from CLAUDE.md.
