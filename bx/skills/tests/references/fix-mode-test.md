# --fix Mode (bx:tests)

`--fix` is a **gated, suite-verified reducer**. It applies three kinds of item, one at a time, each
previewed, approved and checked against the suite:

| Kind | What it does | Source |
|---|---|---|
| **A. T01a deletion** | Deletes a no-op test | test-quality finding, `smell_id: T01a` |
| **B. Life-support deletion** | Deletes a production symbol nothing calls, and the tests that test only it | economics finding, `economic_signal: life_support` |
| **C. Consolidate merge** | Replaces N tests that differ only in literals with one table test of N cases | economics finding, `economic_signal: consolidate` |

Everything else routes to `--plan`. Each kind has its own count check, because a reduction that
quietly changes the number of cases is how a check disappears.

## Why only these three

- **T01a** calls nothing under test, so it cannot fail on a regression. Deleting it loses no check.
- **Life support without a successor** is code no production path runs, kept alive only by its own
  tests. Deleting both loses no check of anything that ships.
- **A mechanical consolidate merge** keeps every case: one table row per original test, with that
  test's literals. Nothing is deleted except repetition.

Everything else needs judgment:

- **T01b (implicit no-raise)**: the body calls code under test and fails if that call starts
  raising, so it is a real, weak check. Make the contract explicit; never delete it. An earlier
  version of this mode treated every assertion-free test as deletable, and on a real repo (S65) the
  only genuine candidate was a deliberate `# Should not raise` test.
- **Life support with a successor**: the tests move to the successor first. That is a rewrite.
- **Non-mechanical clusters**: the members differ in more than literals (a different matcher, a
  different setup), so a table needs an expected-effects column someone has to design.
- T02/T03/T04/T06, snapshot_heavy, coverage gaps, flakiness: judgment rewrites, new tests, or
  investigation.

## Eligibility — every condition for the item's kind must hold

**All kinds:** `respects_documented_decision: true` and `certainty >= 0.7`. The finding is
re-read against the current files (another session may have changed them since the scan).

**A. T01a**
1. `smell_id == "T01a"`, and `evidence_body` is present.
2. **Re-read the current body and confirm, by the catalog's assertion definition, that it still has
   zero assertions and calls nothing under test.** Mock verification (`assert_called*`,
   `toHaveBeenCalled*`), throwing queries (`getBy*`) and Playwright actions are assertions. If the
   body calls code under test, it is T01b: route it to `--plan`.
3. No `TODO`/`FIXME` comment about asserting (an in-flight test), and not inside a
   `describe.each` / `it.each` / `@pytest.mark.parametrize` block.

**B. Life support** (fields from the finding's `metrics` and `references.json`)
1. `successor` is null, and `used_as_test_helper_in` is empty. That list includes every
   test-support file (a test path that is not a test file by name: `src/lib/e2e/stubs.ts`,
   fixtures, `conftest.py`) referencing the symbol; such a symbol is live test infrastructure.
2. **Every** test row is exclusive (`exclusive_rows` == `test_rows`). A test that also checks other
   code would need its assertions edited, which is a rewrite.
3. `prod_refs == 0`, `prod_string_refs == 0`, `prod_import_refs == 0`, re-confirmed now with one
   repo-wide word search for the name outside the test files. Any hit routes it to `--plan`.
4. The symbol is a function or method, not a whole file. A file whose every symbol is life support
   routes to `/bx:clean`.

**C. Consolidate**
1. `mechanical: true` and `merge_table` present. The table is the script's, not yours: one row per
   member, one column per literal slot that differs, the name slot first.
2. `merge_table.comment_lines == 0`, or each comment is carried into its row as a row comment.
3. All members in one file, and that file has no other edits pending in this pass.

Anything failing a condition auto-routes to `--plan` with a one-line note:

> Auto-routed N findings to --plan (not eligible: <reason counts>).

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
     git checkout -b bx-tests-fix". Multi-file reductions are undone with git, not checkpoints.

3. Green baseline. Run the test command recorded in Step 0 once, over the whole suite.
   Record the pass/fail state and the test count (cases, so a table test counts each row).
   - Red, or no runnable command → ABORT: "The suite is not green before any edit
     (<summary>). Fix that first; a reduction cannot be verified against a red baseline."
   - Red only in tests that need something the machine lacks (an API token, a service): say which,
     and offer a scoped command that excludes exactly those files (`--ignore=<file>`). Use it only if
     the user accepts, and print it in the summary. Never set a credential to make a test pass. (S65
     dogfood: 6 maxitech tests sent real Calendly requests with an empty token.)

4. Type baseline. If Step 0 recorded a type-check command, run it once and record its error
   count, test files included. It does not have to be zero: a repo whose CI checks only
   non-test files can carry test-file errors (S257: 47 on main, hidden by a "0 non-test errors"
   gate), and the check below compares against this number, not against zero.
   - No type-check command for this stack → say so once ("no type check: <stack>") and continue.
   - The command cannot run (missing tsconfig, the tool not installed) → ABORT: "Cannot record
     a type baseline (<reason>). A merge can pass the suite and still break types."

5. Confirm once:
   "About to walk A T01a deletions, B life-support deletions and C merges (M auto-routed to
    --plan). Baseline: <count> tests passing, <n> type errors. Continue? [y/n]"
```

## Finding the code — anchors, not line numbers

Every line number in the scripts' output is a hint from scan time. After the first applied item
in a file, every later item in that file has moved (S257: 50–300 lines after one merge in
`watch-references.test.ts`). Locate each test by its **anchor** — `file :: describe > … > test name`
(`consolidate.json` rows carry it; a life-support or T01a row gives `file` and `name`) — and a
symbol by its name and kind in its file. Read the current file, find the block whose title and
enclosing describes match, and build `old_string` from what is there now.

- Exactly one match → use it, whatever its line number.
- No match → skip: "skipped (anchor not found: <anchor>)". The test was renamed or removed since
  the scan; never fall back to the line number.
- More than one match (the same title in the same describe) → use the line hint to choose, and
  say so in the item preview.

## Per-item gate flow

Order: A, then B, then C. Within a file, bottom to top, so `old_string` edits never collide. Each
item shows what it changes and waits:

```
─────────────────────────────────────────────────────
[Item 4 of 9] C. Consolidate merge — cluster C109
src/lib/canary/search-check.test.ts:122-171 — 4 tests → 1 table test of 4 cases (saves 49 lines)

Merge table (from consolidate.json; one row per original test):
  name                                             | url                         | title     | conf | ...
  "a top candidate whose url/title carry no ..."   | "https://www.junghans.de/…" | "Max Bill…" | 0.9  | ...
  "partial-ref agreement (url slug '6119g' ...)"   | "https://www.patek.com/…"   | "Calatrava…"| 0.93 | ...
  ...

Proposed change (diff):
  - the 4 it(...) blocks
  + it.each([ { name: "...", url: "...", ... }, ... ])("$name", ({ url, title, ... }) => { <body> });

Count check after the edit: this file must still run exactly <n> tests (4 removed, 4 cases added).

Apply? [y / n / skip / abort]
```

User responses:
- `y`: apply with `Edit`, then **verify** (below).
- `n`: record "rejected"; do not re-show it this run. Advance.
- `skip`: record "skipped (revisit later)". Advance.
- `abort`: stop the pass. Applied and verified edits stay; the branch is the undo.

### Building each edit

- **A.** Delete the whole test block, from `it(...)` / `def test_` through its end.
- **B.** Delete the symbol's definition (found by name, plus its own doc comment), every
  exclusive test row, and the symbol's name from each import statement that imported it (drop the
  statement if it becomes empty). Touch nothing else in production files.
- **C.** Replace the member tests with one table test that uses the framework's own form —
  `it.each` / `test.each` with an object per row and `"$name"` as the title, or
  `@pytest.mark.parametrize` with one `pytest.param(..., id="<original test name>")` per row. Row *k*
  holds exactly `merge_table.rows[k]`; the body is the first member's body with each differing slot
  replaced by its column and every other literal left inline. Never add, drop or reorder a row.
  - **Slot 0 is the name**: it becomes the row's id or title, so every original test name survives
    in the runner's output.
  - **A docstring or title-like string slot** (scenario IDs such as "S1: …", "SE-1 variant") is
    documentation, not an input: keep it as that row's comment, and give the merged test a docstring
    that names the cases.
  - Add the import the table form needs (`import pytest`) if the file lacks it.

### Verify after each applied item — the count check

Run the test command on the files the item touched: for B, the edited test files **and** every test
file that imports the symbol's module (`leverage.json` `test_importers`), so a dangling import shows
up as a collection error.

| Kind | Must hold | Otherwise |
|---|---|---|
| A | The edited file passes, and its test count dropped by exactly the number of tests deleted | revert |
| B | Every file run passes, and the total count dropped by exactly the number of exclusive rows (cases, so a parameterized row counts each case) | revert |
| C | The file passes, and its test count is **unchanged**: the table produced exactly one case per original test | revert |

**Then the type check**, when the pass has a type baseline: run the type-check command and count
its errors. The count must not exceed the last verified count (the baseline, or the count after
the last item that passed). A rise reverts the item, with the new errors quoted in the reason:
"reverted: +2 type errors (TS2322 at watch-references.test.ts:412: string is not assignable to
Status)". A drop is fine and becomes the new verified count. The test runner cannot catch this
itself: vitest and jest-with-babel strip types, and a table row literal widened to `string`
passes every case (S257).

**Revert** = restore the snapshot. Before applying each item, copy every file it will touch to the
run's temp dir; on a failed check, copy them back, record "reverted: <one-line reason>", and continue
with the next item. Never `git checkout -- <file>`: earlier verified items in the same file are
uncommitted, and checkout would silently undo them too (found in the S65 dogfood, where three items
shared one file). A count that moved the wrong way is the signal that a case was lost
(a dropped table row) or that a "no-op" was not one. **The count check is the guard, not your
reading of the diff**: a merge that drops one row passes every visual review and still loses a check,
and the count catches it. Proven in the S65 dogfood: a merge that dropped one of three rows left
the file **green** (5 passed, 0 failed) and only the count check (6 expected, 5 found) reverted it.

## Cascading prompts (after each verified item)

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

An applied parent deletion is verified the same way (count unchanged).

### 2. File now has zero tests?

```
─────────────────────────────────────────────────────
Cascade: file has zero tests

File: tests/auth/login.test.ts
After deletions, 0 tests remain.

This is /bx:clean territory (orphaned test file). Not deleting it here.
Re-run /bx:clean after this pass; cleanup-styles-tests will catch it.

Continue with next item? [y/n]
```

`/bx:clean` owns whole-file deletions, of tests and of production files.

## After all items processed

Run the full suite once more and compare it with the baseline: same pass state, and the count
changed by exactly −(A tests deleted) −(B exclusive cases deleted) +0 (C merges). If not, say so
plainly and name the last applied items.

```
--fix pass complete.

Applied (verified): 2 T01a deletions, 3 life-support deletions (5 tests), 4 merges (19 tests → 4 table tests, 19 cases)
Reverted (count check, type check or suite failure): 1  — C112: file count 41 → 40 (a row was dropped; the file was still green)
Rejected: 1
Skipped: 1
Auto-routed to --plan: 7
Cascade-deleted empty parent blocks: 1
Files flagged for /bx:clean follow-up: 0
Final suite: <count> passing (baseline <count>, −7 as expected)
Type errors: <n> (baseline <n>)
Lines removed: <git diff --stat total>

Undo: everything is on branch <branch>. `git diff <default>...` reviews it;
`git checkout <default> && git branch -D <branch>` discards it.

Suggested follow-up:
- Re-run /bx:tests --plan for successor moves, non-mechanical merges and T01b/T02/T03/T04/T06 rewrites.
- Run /bx:clean if any file-level cascades pointed there.
```

## Tool usage

- Use `Edit` for every change; the full block (test, symbol, or the member run) as `old_string`.
- Always show the diff before applying. Never apply first and ask afterwards.
- One item, then its verification run, before the next item.
- The only commands this mode runs: `git rev-parse`, `git status`, file copies to and from the run's
  temp dir (snapshots), one word search per life-support name, the test command recorded in
  Step 0 (with `--co` / `--collect-only` / `--list` to read a file's case count where the runner
  has one), and the type-check command recorded in Step 0.

## Edge cases

- **`Edit` fails (non-unique `old_string`):** skip that item, mark it "skipped (could not apply
  mechanically)", continue.
- **Comment lines** above a test or symbol: include them only if they refer to what is deleted.
- **The test command cannot target files:** run the full suite per item, and say so once in
  pre-flight.
- **The runner cannot report a per-file count** (some shell harnesses): A and B fall back to "passes
  and the total count dropped by the expected amount"; C is not applied (no count check, no merge).

## What this mode does NOT do

- Delete T01b, or apply any T02/T03/T04/T06, snapshot, coverage or flakiness finding (`--plan`)
- Move tests to a successor, or merge a non-mechanical cluster (`--plan`)
- Delete whole files, test or production (routed to `/bx:clean`)
- Update snapshot files
- Run on the default branch or a dirty tree
