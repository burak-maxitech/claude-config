# --fix Mode (bx:tests)

Apply **T01a (no-op test)** deletions, one finding at a time, each previewed, approved and checked
against the suite. **This mode is deliberately narrow: only one smell type is eligible.** Everything
else routes to `--plan`.

## Why T01a only

A no-op test calls nothing under test, so it cannot fail on a regression. Deleting it loses no
check. Every other finding needs judgment:

- **T01b (implicit no-raise)**: the body calls code under test and fails if that call starts
  raising, so it is a real, weak check. Make the contract explicit; never delete it. An earlier
  version of this mode treated every assertion-free test as deletable, and on a real repo (S65) the
  only genuine candidate was a deliberate `# Should not raise` test.
- T02 (weak assertion): deleting removes coverage. It needs a stronger assertion.
- T03 (mock-heavy): the right behavior assertion depends on domain knowledge.
- T04 (mystery guest): the fix *adds* explicit setup.
- T05 (redundant): boundary-value coverage is invisible to static analysis.
- snapshot_heavy: replacement assertions are domain-specific.
- Coverage gaps: the fix is *writing* tests.
- Flakiness: the fix is investigation. Deleting a flaky test hides the race.

## Eligibility — every condition must hold

1. `smell_id == "T01a"`
2. `respects_documented_decision: true`
3. `certainty >= 0.7`
4. `evidence_body` is present, and **you re-read the current body from the file and confirm, by
   the catalog's assertion definition, that it still has zero assertions and calls nothing under
   test.** Mock verification (`assert_called*`, `toHaveBeenCalled*`), throwing queries (`getBy*`)
   and Playwright actions are assertions. If the body calls code under test, it is T01b: route it to
   `--plan`.
5. The body has no `TODO`/`FIXME` comment about asserting. That marks an in-flight test.
6. The body is not inside a `describe.each` / `it.each` / `@pytest.mark.parametrize` block.

Anything failing a condition auto-routes to `--plan` with a one-line note:

> Auto-routed N findings to --plan (T01b / not T01a, low certainty, in-flight, parameterized, or conflicts with documented posture).

## Pre-flight — all must pass, or abort the pass

```
1. Allowlist evidence. test-quality's addendum must contain helper_allowlist_size,
   helper_allowlist_patterns and helper_allowlist_files_searched.
   - Any field missing → ABORT: "The assertion-helper guard did not run. Not deleting anything."
   - Present with size 0 → continue, with a warning:
     "0 project assertion helpers found (searched <files> files with <patterns>). Normal for
      repos using only framework matchers. Review each body carefully."

2. Branch and tree. `git rev-parse --abbrev-ref HEAD` must not be the default branch, and
   `git status --porcelain` must be empty.
   - Otherwise → ABORT: "Run --fix on a fresh branch with a clean tree:
     git checkout -b bx-tests-fix". Multi-file deletions are undone with git, not checkpoints.

3. Green baseline. Run the test command recorded in Step 0 once, over the whole suite.
   Record the pass/fail state and the test count.
   - Red, or no runnable command → ABORT: "The suite is not green before any edit
     (<summary>). Fix that first; a deletion cannot be verified against a red baseline."

4. Confirm once:
   "About to walk N T01a findings (M auto-routed to --plan). Baseline: <count> tests passing.
    Continue? [y/n]"
```

## Per-finding gate flow

For each eligible finding, in rank order (files with several findings: bottom to top, so
`old_string` edits never collide):

```
─────────────────────────────────────────────────────
[Finding 1 of 3] T01a — No-op test
tests/auth/login.test.ts:142-156

Test name: "renders without props"

Current test body (re-read from the file just now):
  it('renders without props', () => {
    const props = {};
    // nothing asserted, nothing under test called
  });

Evidence:
  - 2 statements, 0 assertions by the catalog definition
  - Calls nothing under test (only local literals)
  - No allowlisted helper, no hook assertions, not parameterized, no TODO-assert comment

Proposed change (diff):
  --- tests/auth/login.test.ts
  +++ tests/auth/login.test.ts
  @@ -142,4 +142,0 @@
  -  it('renders without props', () => {
  -    const props = {};
  -  });

After this deletion:
  - Surrounding describe('login', ...) still has 4 tests → no parent prompt.
  - File still has 11 tests → no file prompt.

Apply? [y / n / skip / abort]
```

User responses:
- `y`: apply with `Edit` (the whole test block in `old_string`). Then **verify** (below).
- `n`: record "rejected"; do not re-show it this run. Advance.
- `skip`: record "skipped (revisit later)". Advance.
- `abort`: stop the pass. Applied and verified edits stay; the branch is the undo.

### Verify after each applied edit

Run the test command recorded in Step 0 on **the edited file only**.

- It passes, with the test count down by exactly the number of tests deleted: record it as applied.
- Anything else (a new failure, a collection error, an unexpected count): **revert that one edit**
  (`git checkout -- <file>`), record "reverted: <one-line reason>", and continue with the next
  finding. A no-op test whose removal changes the outcome was not a no-op.

## Cascading prompts (after each verified deletion)

### 1. Parent block empty?

If the surrounding `describe(...)` / `context(...)` / `class Test*:` / `mod tests {...}` now has
zero tests, prompt separately:

```
─────────────────────────────────────────────────────
Cascade: parent block now empty

Block: describe('login', () => { ... })  at tests/auth/login.test.ts:140
Was wrapping 1 test, now wrapping 0.

Delete the empty parent block? [y / n / skip]
```

An applied parent deletion is verified the same way.

### 2. File now has zero tests?

```
─────────────────────────────────────────────────────
Cascade: file has zero tests

File: tests/auth/login.test.ts
After deletions, 0 tests remain.

This is /bx:clean territory (orphaned test file). Not deleting it here.
Re-run /bx:clean after this pass; cleanup-styles-tests will catch it.

Continue with next finding? [y/n]
```

`/bx:clean` owns whole-file deletions.

## After all findings processed

Run the full suite once more and compare it with the baseline: same pass state, count down by
exactly the number of tests applied. If not, say so plainly and name the last applied edits.

```
--fix pass complete.

Applied (verified): 3 T01a deletions
Reverted (suite changed): 0
Rejected: 1
Skipped: 1
Auto-routed to --plan: 7
Cascade-deleted empty parent blocks: 1
Files flagged for /bx:clean follow-up: 0
Final suite: <count> passing (baseline <count>, −3 as expected)

Undo: everything is on branch <branch>. `git diff <default>...` reviews it;
`git checkout <default> && git branch -D <branch>` discards it.

Suggested follow-up:
- Re-run /bx:tests --plan for T01b/T02/T03/T04 rewrite briefs.
- Run /bx:clean if any file-level cascades pointed there.
```

## Tool usage

- Use `Edit` with the full test block (from `it(...)` / `def test_` through its end) as `old_string`.
- Always show the diff before applying. Never apply first and ask afterwards.
- One `Edit` per finding, then its verification run, before the next finding.
- The only commands this mode runs: `git rev-parse`, `git status`, `git checkout -- <file>`, and the
  test command recorded in Step 0.

## Edge cases

- **`Edit` fails (non-unique `old_string`):** skip that finding, mark it "skipped (could not apply
  mechanically)", continue.
- **Comment lines** above the test: include them only if they refer to the deleted test.
- **The test command cannot target one file:** run the full suite per edit, and say so once in
  pre-flight.

## What this mode does NOT do

- Delete anything but T01a (T01b–T05 always route to `--plan`)
- Delete whole files (routed to `/bx:clean`)
- Delete imports left orphaned by a deletion (linter / formatter / `/bx:clean`)
- Update snapshot files (snapshot_heavy is `--plan`-only)
- Run on the default branch or a dirty tree
