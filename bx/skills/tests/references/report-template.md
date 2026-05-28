# Report Template — /bx:tests

Render the final report exactly in this order. Every section appears even if empty (with "None found" as content) so the output structure is predictable across runs.

## Section 0 — Twin Headline

Render this **first**, before anything else. The twin headline makes both directions of test debt equally visible:

```
## /bx:tests — <project name>

**Coverage gaps in critical code: <coverage_gap_total> lines across <coverage_files_affected> files.**
**Tests we can delete: <deletable_total> lines across <deletable_files_affected> files.**
```

Numbers from Step 5 aggregation. Special cases:

- If `coverage_gap_total == 0`: render line 1 as "**No critical-code coverage gaps detected** — high-priority paths all have test neighbors and assertions."
- If `deletable_total == 0`: render line 2 as "**No safely-deletable test waste detected** — assertion-free / confirmed-duplicate / snapshot-heavy categories are empty."
- If both are zero: render a single line "**Test suite passes baseline checks on both axes** — no critical-path gaps and no waste hotspots."

The twin format is non-negotiable: a single number on either axis is misleading on its own.

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

Current state: function `verifySession` has 48 LOC, security_density 0.18 (matches: auth, token, session, verify), churn 22 commits/year, fan_in 9 importers. No test neighbor found at `src/auth/verifySession.test.ts` or `__tests__/auth/verifySession.test.ts`.

Recommendation: add unit tests covering session expiry, tampered tokens, and valid happy path. Priority score 14.2 — high blast radius on uncovered branches.

Conflict with documented testing posture? No.
```

For bug-fix-without-regression findings, render them as a separate row block at the end of Coverage:

```
### Bug-Fixes Without Regression Tests (last 50 commits)

| Commit  | Subject                          | Files touched (source only) |
|---------|----------------------------------|-----------------------------|
| abc1234 | fix: token expiry boundary       | src/auth/token.ts           |
| def5678 | fix: refund double-charge        | src/billing/refundOrder.ts  |
| ...     | ...                              | ...                         |
```

### Quality

```
### Quality Smells (— deletable subset: <T01+T05 deletable_lines> lines)

| Rank | Location                            | Title                              | Smell | Sev | Cert | Effort | Lines Δ |
|------|-------------------------------------|------------------------------------|-------|-----|------|--------|---------|
| 1    | tests/auth/login.test.ts:142-156    | Assertion-free test                | T01   | M   | 0.95 | trivial| -14     |
| 2    | tests/api/users.test.ts:80-220      | Mock-heavy, no behavior assertion  | T03   | M   | 0.75 | medium | 0       |
| ...  | ...                                 | ...                                | ...   | ... | ...  | ...    | ...     |
```

The `Lines Δ` column shows deletable lines (negative = lines removed). T02/T03/T04 always show `0` (rewritable, not deletable).

Top-finding detail block as in Coverage.

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
If `--fix` flag is set, this section is replaced by the per-finding T01 gate flow (see Step 7 in SKILL.md).

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

Twin-headline math:
- coverage_gap_total: 312 lines across 18 files (from test-coverage)
- deletable_total: 819 lines across 4 files
  - T01 (assertion-free): 1 finding, 14 lines
  - T05 (confirmed duplicate): 0 findings, 0 lines
  - snapshot_heavy: 1 finding, 705 lines
  - Subtotal-check: 14 + 0 + 705 = 719 — discrepancy means rounding or near-duplicate adjustment

T-catalog hit counts:
- T01: 1
- T02: 4
- T03: 6
- T04: 2
- T05: 0

Findings filtered:
- Dropped 3 ratio_under findings overlapping with test-coverage's file-level gaps (deduplicator)
- Dropped 2 findings with certainty < 0.5 and impact below threshold

Defer to /bx:clean for: orphaned test files, stale snapshots, >3mo skipped tests, unused test helpers.
Defer to /code-review or /bx:review for: per-commit / per-PR test quality.
```

The footer's "subtotal-check" line is intentionally surfaced — if the orchestrator's arithmetic doesn't add up, the user sees it immediately rather than the headline silently lying. If subtotals do match exactly, render the line as "Subtotal-check: <a> + <b> + <c> = <total> ✓".
