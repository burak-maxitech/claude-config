# Project Status

> Session state for `/bx:resume`. Instructions live in [CLAUDE.md](../CLAUDE.md).

Last Updated: 2026-08-18 (Session 57)

## Current Status

| Area | Status |
|------|--------|
| Skills (11) | Complete |
| Subagents (19) | Complete — `doc-migrator` added S56 |
| Plugin packaging (`bx`) | **v2.1.1 ready S57** (simplify cleanup wave over v2.0.0–v2.1.0); push + install smoke-test + symlink retirement still pending |
| Doc schema v2 | Complete — shipped S56; this repo migrated |
| Startup scripts | Complete — S55 live gate still pending |
| Cross-platform setup | Complete |
| GitHub sync | Complete — main pushed through v2.1.0 |
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

## Next Steps

1. **First real archive rotation** — `docs/key-decisions.md` is ~98k chars; upcoming decision rows cross the 100k trigger, so a near-future `/bx:save --full` fires the first Part 7.7 rotation into `docs/archive/`. Review its diff carefully.
2. **Finish the `cc` session naming/coloring rollout (S55)** — run the live gate, then dispatch the single fix wave listed in `## In Progress`.
3. **Doc-schema v2 fixture verification** — the deferred live `/bx:save` runs against the six fixture cases (see `## In Progress`), plus the post-merge minors batch from both plans.
4. **/simplify follow-up: move Part 7.7 rotation out of Part 7** into its own sibling Part — deletes the five "except 7.7" carve-outs; requires a blind rehearsal before shipping (deliberately skipped S57).
5. **Resume the `/bx:webdesign` kaanarik run past review** — push through Phase 3 inject+verify; verify finding `dadac845`.
6. **Real `/bx:seo` run against burakarik.com** — auth fixed S39, content-review-hardened S45.
7. **Dogfood `/bx:tests`, `/bx:arch`, `/bx:health`** — hardened S46, never run end-to-end.
8. **S37 plugin-packaging leftovers** — install smoke-test, symlink retirement, `Skill(bx-*)` → `Skill(bx:*)`.
9. **`/bx:evolve` follow-ups** — scan-docs allowlist candidate (`auto-mode-config`); 14 open findings; v2 ideas (shared `references/lane-contract.md`).
10. **`/bx:seo` deferred items** — code-review leftovers (#5/#6/#7) + S25/S27/S29 refactors.

## Session History

> Full history: [session-history.md](session-history.md)

### Last Session (Session 57) - 2026-08-18
- **`/simplify` over the v2.0.0→v2.1.0 diff (17 commits):** 4 parallel reviewers (reuse / simplification / efficiency / altitude) → 17 fixes across 13 files; 6 findings deliberately skipped (biggest: the 7.7-out-of-Part-7 restructure, deferred behind a blind rehearsal).
- **Efficiency wins:** save-writer anchor Greps no longer echo ~98% of the archives back (`-o` + `head_limit: 0`); Part 7.7 moves bytes via a byte-exact shell split instead of Read→Write; `--full` stops reading dated planning records (~356KB); Part 5.1's full-archive read deleted.
- **Ownership consolidation:** doc-schema.md gains the canonical Archives section; `--silent` promoted to a normative default rule; satellites (save/resume SKILL.md, README) now cite owners instead of restating; assert-doc-schema.sh derives all section checks from one constant; make-fixtures.sh `stub_docs` helper (fixtures verified byte-identical).
- **v2.1.1** bumped + CHANGELOG entry; all checkers pass (assert-doc-schema against repo + fixtures incl. negative order tests, check-doc-rule-consistency).
- **Next:** first real key-decisions rotation (~98k, near the 100k trigger); fixture live runs; `cc` live gate.
