# Report Template — /bx:tests

Render the final report exactly in this order. Every section appears even if empty (with "None found" as content) so the output structure is predictable across runs.

## Section 0 — Triple Headline

Render this **first**, before anything else. Gaps, deletions and merges are equally visible:

```
## /bx:tests — <project name>

**Coverage gaps in critical code: <coverage_gap_total> lines across <coverage_files_affected> files.**
**Tests we can delete: <deletable_total> lines across <deletable_files_affected> files.**
**Tests we can consolidate: <consolidate_worthwhile_clusters> merges worth doing (<consolidate_worthwhile_tests_before> tests, saves <consolidate_worthwhile_saved_lines> lines); all clusters: <consolidate_tests_before> → <consolidate_tests_after>, saves <consolidate_saved_lines>.**
```

Line 3 leads with the worthwhile merges (`saved_lines >= 20`, or mechanical and `>= 10`). The raw
total comes second. S257: "774 → 251 consolidable" set an expectation the brief then cut by ~240
clusters; the six merges actually worth doing were all in the worthwhile set.

Numbers from Step 5 aggregation. Special cases:

- If `coverage_gap_total == 0`: render line 1 as "**No critical-code coverage gaps detected** — every ranked symbol has a test that calls it."
- If `deletable_total == 0`: render line 2 as "**No safely-deletable test waste detected** — no-op / life-support / snapshot-heavy categories are empty."
- If there are no clusters: render line 3 as "**No consolidation candidates** — no two tests differ only in their literals."
- If all three are zero: render a single line "**Test suite passes baseline checks on all three axes.**"

The three-line format is non-negotiable: a single number on any axis is misleading on its own.

---

## Section 1 — Testing Posture

```
## Testing Posture

**Intended testing posture** (from CLAUDE.md / tests-README / ADRs):
- <bullet 1>
- <bullet 2>
- ...

**Detected framework(s):** <list, e.g. "vitest 1.4, supertest, msw">
**Coverage mode this run:** heuristic | report (--coverage)
**Source files in scope:** <int>
**Test files in scope:** <int>
```

If no testing docs existed in Step 1, prefix the bullets with "*Inferred from deps/conventions — no testing docs found*" so the user knows it's inferred.

---

## Section 2 — Findings

Three subsections in order: **Coverage** (under-tested critical paths), **Quality** (smells), **Economics** (waste/cost).

### Coverage

```
### Coverage Gaps (— total: <coverage_gap_total> lines across <files> files)

| Rank | Location                            | Title                              | Sev | Cert | Effort | Gap (LOC) | Priority |
|------|-------------------------------------|------------------------------------|-----|------|--------|-----------|----------|
| 1    | src/auth/verifySession.ts:14-62     | No test coverage on session verify | H   | 0.85 | small  | 48        | 14.2     |
| 2    | src/billing/refundOrder.ts:1-90     | Refund flow untested               | H   | 0.9  | medium | 88        | 11.4     |
| ...  | ...                                 | ...                                | ... | ...  | ...    | ...       | ...      |
```

Below the table, render a "Top finding detail" block expanding the #1 ranked finding (the priority score is what the user wants to understand):

```
**#1 — No test coverage on session verify (`src/auth/verifySession.ts:14-62`)**

Current state: function `verifySession` has 48 LOC, 9 security lines (auth, token, verify), churn 22 commits/year, fan_in 9 importers, reached from an entry point. test_status: untested — no test file imports `src/auth/verifySession.ts` (or `mock_only`: two test files `vi.mock` it and never run it).

Recommendation: add unit tests covering session expiry, tampered tokens, and valid happy path. Priority score 14.2 — high blast radius on uncovered branches.

Conflict with documented testing posture? No.
```

For bug-fix-without-regression findings, render them as a separate row block at the end of Coverage. They carry no gap lines and are never in the headline. The heading names the manifest's window:

```
### Bug-Fixes Without Regression Tests (last 200 commits, then fix subjects)

| Commit  | Subject                          | Files touched (source only) |
|---------|----------------------------------|-----------------------------|
| abc1234 | fix: token expiry boundary       | src/auth/token.ts           |
| def5678 | fix: refund double-charge        | src/billing/refundOrder.ts  |
| ...     | ...                              | ...                         |
```

### Quality

```
### Quality Smells (— deletable subset: <T01a deletable_lines> lines)

| Rank | Location                            | Title                              | Smell | Sev | Cert | Effort | Lines Δ |
|------|-------------------------------------|------------------------------------|-------|-----|------|--------|---------|
| 1    | tests/auth/login.test.ts:142-156    | No-op test                         | T01a  | M   | 0.95 | trivial| -14     |
| 2    | tests/api/users.test.ts:80-220      | Mock-heavy, no behavior assertion  | T03   | M   | 0.75 | medium | 0       |
| ...  | ...                                 | ...                                | ...   | ... | ...  | ...    | ...     |
```

The `Lines Δ` column shows deletable lines (negative = lines removed). T01b/T02/T03/T04/T06 always show `0` (rewritable, not deletable).

Top-finding detail block as in Coverage.

### Reduction

Two tables, both from the economics scanner. Life support first, because each row deletes production
code as well as tests:

```
### Tests Keeping Dead Code Alive (— deletable: <life_support_deletable_lines> lines)

| Rank | Symbol                                   | Prod refs | Tests | Successor (status)                         | Action                          | Lines Δ |
|------|------------------------------------------|-----------|-------|--------------------------------------------|---------------------------------|---------|
| 1    | models/email.py:59-95 Email.build_reply_all_recipients | 0 | 5 | services/scheduling_utils.py:build_reply_recipients (untested) | Move the 5 tests to the successor, then delete the method | -37 |
| 2    | src/lib/scoring/axes.ts:12-20 axisDescription | 0      | 1     | —                                          | Delete the function and its test | -9      |

### Tests We Can Consolidate (— <consolidate_worthwhile_clusters> worth doing, saves <consolidate_worthwhile_saved_lines> lines; top 15 shown)

| Rank | Cluster (key) | Location                                  | Tests | Saved | Mechanical | Action                              |
|------|---------------|-------------------------------------------|-------|-------|------------|-------------------------------------|
| 1    | C173 (`3f2a9c10`) | src/lib/db/watch-references.test.ts › upsertWatchReferenceFromExtraction | 5 → 1 | 112 | no | One `it.each` table with a matcher column (row 3 asserts `>= 1`); shares a runner with C177 (straps) |
```

`Mechanical: yes` clusters are a pure table rewrite and `--fix`-eligible; the rest route to `--plan`.
Name the rows whose matcher differs (`matcher_variants`) and the sibling cluster (`siblings`) in
the Action cell.

### Economics

```
### Cost Signals (— snapshot deletable: <snapshot_deletable_lines> lines)

| Rank | Location                            | Title                              | Signal           | Sev | Cert | Effort | Lines Δ |
|------|-------------------------------------|------------------------------------|------------------|-----|------|--------|---------|
| 1    | tests/components/Page.test.tsx      | Snapshot-heavy (82% snapshot)      | snapshot_heavy   | M   | 0.85 | small  | -705    |
| 2    | tests/api/*                         | Module ratio 4.2 (over-tested)     | ratio_over       | L   | 0.7  | medium | 0       |
| 3    | tests/scheduler.test.ts             | 3 flake-fix commits in history     | flakiness_history| H   | 0.9  | medium | 0       |
| ...  | ...                                 | ...                                | ...              | ... | ...  | ...    | ...     |
```

Top-finding detail block as in Coverage.

---

## Section 3 — Documented-Decision Conflicts

If any findings have `respects_documented_decision: false`:

```
## ⚠ Documented-Decision Conflicts

**Confirm intent before action.** These findings recommend changes that conflict with your documented testing posture.

| Location                        | Finding                              | Documented posture conflicting             |
|---------------------------------|--------------------------------------|--------------------------------------------|
| tests/repositories/userRepo.t.ts| T03 (mock-heavy)                     | "Repository unit tests are mock-heavy by design — integration tests verify behavior" |
| tests/components/Page.test.tsx  | snapshot_heavy                       | "Snapshots are our visual-regression boundary in components/" |
| ...                             | ...                                  | ...                                        |
```

If empty: render `## ⚠ Documented-Decision Conflicts\n\nNone — all findings respect documented testing posture.`

---

## Section 4 — Suggested Next Actions

```
## Suggested Next Actions

**Skill chains:**
- <e.g. "Run `/bx:clean` first — 5 orphaned-test candidates likely exist (not surfaced here; deferred to cleanup-styles-tests).">
- <e.g. "Run `/bx:review src/auth/verifySession.ts --security` before adding tests — the file is security-critical.">
- <e.g. "Run `/bx:arch` if coverage gaps cluster in one module (current run: 7 of 12 in src/billing/).">

**Top strategic rewrites (copy-paste into a fresh session):**

\```bash
/bx:plan "Replace mock-heavy implementation assertions in tests/api/users.test.ts (currently T03 with impl/behavior ratio 5:1). Goal: verify observable behavior (return values, persisted state) instead of `toHaveBeenCalledWith` chains. Keep mocks only at the HTTP boundary (msw)."
\```

\```bash
/bx:plan "Convert snapshot-heavy tests/components/Page.test.tsx (720 of 880 lines are snapshot) to 3 focused property assertions (title, child count, aria-attrs). Delete the .snap file. Saves ~705 lines."
\```
```

If `--plan` flag is set, this section is replaced by the full phased brief (see Step 7 in SKILL.md).
If `--fix` flag is set, this section is replaced by the per-finding T01a gate flow (see Step 7 in SKILL.md).

---

## Footer — Disclosure

```
---

Test framework: vitest 1.4 (+ msw, supertest)
Coverage mode: heuristic   [or: report (consumed coverage/coverage-summary.json)]
Source files in scope: 87
Test files in scope: 64
Source files sampled (top by priority): 50
Source files skipped: 37   [reason: priority_score below cutoff or non-source]

Headline math:
- coverage_gap_total: 312 lines across 18 files (from test-coverage; bug_fix_no_test excluded)
- deletable_total: 765 lines across 3 files
  - T01a (no-op): 1 finding, 14 lines
  - life_support: 1 finding, 46 lines
  - snapshot_heavy: 1 finding, 705 lines
  - Subtotal-check: 14 + 46 + 705 = 765 ✓
- consolidate_worthwhile: 56 merges, 213 tests, saves 1,663 lines
- consolidate_total: 761 → 249 tests across 249 clusters, saves 3,092 lines (86 mechanical, 16 sibling pairs)

T-catalog hit counts:
- T01a (no-op, deletable): 1
- T01b (implicit no-raise, rewrite): 0
- T02: 4
- T03: 6
- T04: 2
- T06: 1
- T05: reported as consolidate clusters (above)

Growth trend (test/source LOC, test cases): 2026-05 0.06 (18) → 2026-07 0.66 (1,813) → 2026-09 0.89 (4,483) → 2026-10 0.91 (6,642)

Scripts: test_bodies 3.3s · leverage 2.7s · references 5.5s · consolidate 1.2s (manifest: <path>)
RUN NOTES: <count of script rows scanners disagreed with, each listed; "none" when none>

Findings filtered:
- Dropped 3 ratio_under findings overlapping with test-coverage's file-level gaps (deduplicator)
- Dropped 2 findings with certainty < 0.5 and impact below threshold

Coverage negatives (categories swept that produced nothing — evidence the scan ran, not that it
found nothing to say). `unavailable` means the precondition is absent; `clean` means it was
genuinely checked:
- snapshot_heavy — unavailable: no snapshot mechanism in the repo (0 hits for toMatchSnapshot / __snapshots__)
- flakiness_marker — clean: all 6 test files grepped for retry/skip/flaky markers, none found
- flakiness_history — unavailable: no CI, so no flake-fix commits exist to mine
- (render `none reported` when no subagent returned any)

Partial coverage (checks that ran but did not cover their whole scope — their counts above are
lower bounds, not results):
- test_bodies — 212 of 603 test files swept: time budget of 600s exhausted
- (render `none` when every check covered its scope)

Defer to /bx:clean for: orphaned test files, stale snapshots, >3mo skipped tests, unused test helpers.
Defer to /code-review or /bx:review for: per-commit / per-PR test quality.
```

The footer's "subtotal-check" line is intentionally surfaced. The totals are integer sums, so they must match exactly; render "Subtotal-check: <a> + <b> + <c> = <total> ✓". A mismatch is an arithmetic error: fix the aggregation before rendering, never explain it away as rounding.
