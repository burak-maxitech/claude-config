# Test Smell Catalog — T-prefix entries

Each entry follows the same schema as the arch catalogs, whose canonical rules live in `../arch/references/catalog-rules.md` — resolve that against **this skill's base directory** (`bx/skills/tests/`), not against this file's directory. The S-prefix entries this catalog was modelled on are in the sibling `catalog-simplification.md`. The `test-quality` subagent must cite an entry by ID in `smell_id`. Of these entries only `T01a` is `--fix`-eligible, and only through the gated flow in `fix-mode-test.md`.

## Rules for the catalog

- **The detection is a script.** `../scripts/test_bodies.py` implements this catalog's assertion
  definition, the T01a/T01b split and the T02/T03 rules, and emits one row per test. Scanners judge
  its rows; they never count assertions by hand. **Change the catalog and the script together.**
- **Languages tag is binding.** Detection patterns are language-aware. Don't fire a Jest matcher rule on a pytest file.
- **`deletable_lines` is honest.** Only T01a (every line), the economics `life_support` lane and `snapshot_heavy` contribute to the deletion headline. T05's lines go to the consolidate headline instead, because a merge keeps every case. T01b/T02/T03/T04/T06 are *rewritable*, not deletable — report `deletable_lines: 0`.
- **False-positive guards are mandatory.** Test smells over-fire easily; every entry below includes a guard the subagent must run first.

---

## What counts as an assertion

**This section is canonical.** `scan-quality.md`, `fix-mode-test.md` and the `test-quality` agent cite
it; none of them restates it.

**An assertion is any call that fails the test when the code under test regresses.** That includes
calls that throw, not only calls named `assert` or `expect`. Two real runs (S65) showed what a
narrower list does: it classed 12 real pytest tests whose only checks were `mock.assert_called_once()`
as assertion-free, and offered them for deletion at certainty 0.95.

| Language | Counts as an assertion |
|---|---|
| JS/TS | `expect(` (incl. `expect.soft`, `expect.poll`, `.resolves`/`.rejects`); `assert.*` / `assert(`; `chai.expect`/`chai.assert`/`should`; ava `t.*`; mock verification (`toHaveBeenCalled*`, `toHaveBeenNthCalledWith`, `verify(`); **Testing Library queries that throw on a miss** (`getBy*`, `getAllBy*`, `findBy*`, `findAllBy*`, called bare or on `screen`/a render result); **Playwright locator actions and `expect`** (`page.click`, `locator.click/fill/check`, `waitForSelector`, `waitForURL`); `expectTypeOf`/`assertType` |
| Python | `assert` statements; `self.assert*`; `pytest.raises` / `pytest.warns`; `np.testing.assert_*`; **mock verification** (`.assert_called*`, `.assert_awaited*`, `.assert_not_called`, `.assert_not_awaited`, `.assert_has_calls`, `.assert_any_call`) |
| Rust | `assert!`, `assert_eq!`, `assert_ne!`, `debug_assert*`, `panic!` in an error-path test, `#[should_panic]` on the function |
| Go | `t.Error*`, `t.Fatal*`, `t.Fail*`; testify `assert.*`, `require.*` |
| JVM | `Assertions.*`, `Assert.*`, `assertThat`, mockito `verify(` |
| Shell / PowerShell | a call to the harness's `fail`/`pass`/`assert_*` helper, `exit 1` on a failed comparison, Pester `Should` |
| All | a call to a **project-defined assertion helper** from the allowlist below |

**Project-defined assertion helpers (the allowlist).** Search *every* path, test and non-test, with
one pattern per language. Leading whitespace is allowed, so class methods and nested helpers match,
and so do `export`, `async` and test-local `const` forms:

```
JS/TS:  ^\s*(export\s+)?(default\s+)?(async\s+)?(function\s+|const\s+|let\s+)(assert|should|expect|check|verify|ensure|require|must)\w*
Python: ^\s*(async\s+)?def\s+(assert|should|expect|check|verify|ensure|require|must)\w*\s*\(
Rust:   ^\s*(pub(\([a-z]+\))?\s+)?fn\s+(assert|should|expect|check|verify|ensure|require|must)\w*
Go:     ^func\s+(\([^)]*\)\s*)?(assert|should|expect|check|verify|ensure|require|must)\w*\(
```

Also record names exported through `expect.extend(...)`, `chai.use(...)` and `pytest_plugins`. A
matching name is a production function as often as a helper (`should_process_email`, `verify_request`).
Keep a name only if a test calls it **and** its body asserts or raises. Record what was rejected and
why.

**Evidence the allowlist ran** is mandatory output, even when zero helpers survive:
`helper_allowlist_size`, `helper_allowlist_patterns` (the patterns actually used) and
`helper_allowlist_files_searched` (the number of files the patterns ran over, not the number that
matched). A zero with evidence is a legitimate result. A missing field means
the guard did not run.

---

## T01 — Assertion-free test (two kinds)

- **Languages:** all
- **Detect when:** a test body contains **zero assertions** as defined above, after the guards below.
  Then classify it, because the two kinds call for opposite actions:
  - **T01a — No-op test.** The body calls nothing under test. It holds only literals, local setup,
    `pass`, logging, or calls to mocks and fixtures. It cannot fail on a regression.
  - **T01b — Implicit no-raise test.** The body calls code under test and relies on "no exception
    propagated" as its check. It *does* fail if that call starts raising, so it is a weak test, not a
    fake one. Signals include a `# should not raise` / `// does not throw` comment, a test name
    containing `does not raise|does not throw|handles|gracefully|no error|is safe`, or any call into
    a module under test. **When in doubt, it is T01b.** The cost of the error is one-sided: a
    wrongly-kept T01a costs a few lines, and a wrongly-deleted T01b removes a real check.
- **Replace with:**
  - T01a: delete the test.
  - T01b: make the contract explicit. Assert the post-state (`assert wr._renewal_task is None`), or
    use an explicit no-raise form (`expect(() => f()).not.toThrow()`, `await expect(p).resolves...`,
    or a call plus a value assertion). **Never delete.**
- **Lines deletable:** T01a: the whole test including its `it(...)` / `def test_...` wrapper. T01b:
  **0**.
- **`--fix-eligible:`** **T01a only.** T01b routes to `--plan` as a rewrite.
- **Min certainty floor to surface:** 0.7 for both.
- **In-flight tests:** a body with a `TODO`/`FIXME` comment that mentions asserting
  (`# TODO assert`, `// TODO: check`) is unfinished, not fake. Lower certainty to 0.5, which drops
  it below the floor and out of `--fix`.
- **False-positive guards (the subagent MUST run these first):**
  1. **The assertion definition above**, including mock verification, throwing queries and the
     project-helper allowlist.
  2. **Hook-based assertions.** If the file's `afterEach`/`tearDown`/fixture teardown asserts, the
     body may only set up state for it. Lower certainty to 0.5.
  3. **Property-based generators.** `fast-check`, `hypothesis`, `proptest`: the assertion lives in
     the generator callback. Check for these imports before flagging.
  4. **Parameterized wrappers.** A body inside `describe.each`/`it.each`/`@pytest.mark.parametrize`
     whose assertion lives in a shared helper. Read the helper before flagging.

---

## T02 — Weak assertion

- **Languages:** all
- **Detect when:** the only assertions in a test body are tautological or near-tautological:
  - `toBeTruthy()` / `toBeFalsy()` on values whose type guarantees the polarity (e.g. `expect(arr.length > 0).toBeTruthy()` when `arr.length` is non-negative integer always)
  - `not.toBeNull()` / `not.toBeUndefined()` / `toBeDefined()` standing alone (asserts existence, not value). A **positive** `toBeNull()` / `toBeUndefined()` pins a value and is not weak: on horowell, counting it as weak inflated weak-only tests from 17 to 359 (S65)
  - **Not weak:** `expect(getBy…(…)).toBeTruthy()` / `.toBeInTheDocument()`. The query throws on a miss, so the matcher is a presence check (`test_bodies.py` kind `presence`)
  - `expect(x).toBe(x)` / `expect(x).toEqual(x)` (compares value to itself)
  - Python: `assert x` where `x` is a non-empty literal, `assert x is not None` standing alone
  - Numeric "softening": `>= 0`, `<= maxInt`, `!= null` without value range check
  - Go: `if got == nil { t.Error(...) }` standing alone with no value comparison
  - Type-only: `expect(typeof x).toBe('string')` without checking value
- **Replace with:** rewrite with a specific value / shape / structural match. E.g. `expect(user).toEqual({ id: 1, name: 'Ada' })` instead of `expect(user).toBeTruthy()`.
- **Lines deletable:** **0** (rewritable, not deletable).
- **`--fix-eligible:`** **false** — routes to `--plan`. Choosing the right strong assertion requires human judgment.
- **Min certainty floor:** 0.6
- **False-positive guards:**
  1. **Existence-is-the-test scenarios.** Some tests legitimately assert "this didn't crash and returned something." Check the test name — names like `does not throw`, `returns a value`, `is callable` justify weak assertions. Lower certainty to 0.4 for those.
  2. **Setup verification.** A `toBeDefined` immediately after a setup factory call that itself has assertions is fine.

---

## T03 — Implementation-coupled / mock-heavy

- **Languages:** all (especially common in JS/TS)
- **Detect when:** the test body's assertions are dominated by interaction verification rather than behavior verification. `test_bodies.py` computes it as `t03_candidate`:
  - **Implementation assertions** (kind `mock_verify`): `toHaveBeenCalled*`, `toHaveBeenNthCalledWith`, assertions on `fn.mock.calls`, `assert_called*` / `assert_awaited*` / `assert_has_calls`, `assert m.call_args == …`, mockito `verify(`.
  - **Behavior assertions**: every other non-weak kind — values, presence, raises, snapshots, throwing queries, helpers.
  - Flag when `mock_verify >= 4` AND `mock_verify / max(behavior, 1) > 2.0`.
  - **Setup lines never count** (`vi.mock`, `mockReturnValue`, `patch(`): building a mock is not coupling, and counting it flagged ~130 horowell tests on a literal reading (S65).
  - **"Never called" checks count on neither side** (kind `mock_absent`: `not.toHaveBeenCalled`, `assert_not_called`). Asserting that a billed call or a DB write did *not* happen is an observable-effect check, not coupling to implementation order.
- **Replace with:** rewrite to test observable behavior — the function's return value, persisted state, emitted events. Mock only at the system boundary (network, time, RNG, filesystem).
- **Lines deletable:** **0** (rewritable).
- **`--fix-eligible:`** **false** — judgment-heavy rewrite.
- **Min certainty floor:** 0.55
- **False-positive guards:**
  1. **Interaction is the contract.** Interaction verification *is* behavior verification when the unit under test is (a) an event publisher, dispatcher, notifier, logger or tracer wrapper (names: Publisher, Emitter, Dispatcher, Logger, Tracer, Notifier), or (b) an **orchestrator** whose job is to call injected dependencies in a given order and whose outputs are those calls (a pipeline phase, a cron route, a server action that only sequences writes). Lower certainty to 0.4, which drops it below the floor. On horowell (S65 rerun) six of nine candidates were orchestrators of kind (b).
  2. **Test seam at the boundary.** Tests in an `adapters/`, `infrastructure/` or repository folder are often verifying boundary contracts; lower certainty to 0.5.
  3. **TDD-scaffolding scenario.** If `tests/README` or CLAUDE.md says "we use mock-heavy unit tests intentionally as a TDD scaffold, integration tests verify behavior" — mark `respects_documented_decision: false`.

---

## T04 — Mystery guest

- **Languages:** all
- **Detect when:** the test depends on data that isn't visible in the test file or its imports:
  - References a fixture file by path with no import / setup loading it (`readFileSync('fixtures/user.json')` mid-test)
  - Reads an env var without resetting/setting it in setup
  - Depends on global module state set elsewhere
  - Uses a "magic" record (`User.find(1)` against a seeded DB without showing the seed)
- **Replace with:** inline the fixture inline (`const user = { id: 1, name: 'Ada' }`) or add an explicit setup function that constructs it. Boundary at "everything this test needs is in this file."
- **Lines deletable:** **0** (the fix adds 3-5 lines, not removes).
- **`--fix-eligible:`** **false** — rewriting requires understanding the dependency.
- **Min certainty floor:** 0.5
- **False-positive guards:**
  1. **Documented test data conventions.** If `tests/README` defines a "fixtures convention" describing where to look for data, lower severity to low (the convention makes the "guest" not actually mysterious).
  2. **Snapshot files.** `.snap` references next to the test file are not mystery guests — that's a framework convention.

---

## T05 — Redundant test (reported by the consolidate lane)

- **Languages:** all
- **Detect when:** ≥2 tests whose literal-stripped token shapes match (multiset Jaccard ≥ 0.9), with
  the same setup (fixtures, mock-setup line count, top-level `describe`), in one file or calling the
  same production symbol across files. `../scripts/consolidate.py` finds them; **`test-quality` does
  not emit T05.** The `test-economics` scanner reports each cluster as `economic_signal: consolidate`
  (`scan-economics.md`), so a cluster is counted once.
- **Replace with:** one parameterized test (`it.each` / `describe.each`, `@pytest.mark.parametrize`,
  a Go table) with **one row per original test**, each row holding that test's literals. Boundary
  inputs stay as their own rows; that is what the row is for.
- **Lines deletable:** **0.** The saved lines (`saved_lines` = lines before − one body − one row per
  case) go to the consolidate headline ("N tests → M"), never to "delete": no case disappears.
- **`--fix-eligible:`** only `mechanical: true` clusters (every member has the identical token
  sequence, so the merge is a pure table rewrite), and only through `fix-mode-test.md`'s count
  check: the merged test's case count must equal the number of tests it replaced.
- **Min certainty floor:** 0.75
- **Calibration (S65, horowell):** at 0.9, 458 clusters, 207 of which saved under 4 lines;
  `consolidate.py` reports only clusters saving ≥4 lines (251 clusters, 774 → 251 tests). 0.85 grew
  the set by 27% with visibly looser matches; 0.95 cut it 28% and dropped real five-member clusters.
- **False-positive guards:**
  1. **Different setup paths.** The script groups only tests with matching setup; a cluster whose
     members still differ in a `beforeEach` you can see is not redundant.
  2. **Table tests already.** Already-parameterized tests (`param_rows`) are never merge inputs.
  3. **Comments that explain a case.** A merge keeps each one as a row comment.

---

## T06 — Name/assertion mismatch

- **Languages:** all
- **Detect when:** the test's name promises an outcome its assertions never check. Example (S65,
  maxitech): `test_calendar_failure_shows_error` asserts only that a mock was not called; nothing
  checks that an error is shown. Candidates come from `test_bodies.py` rows: read the `name` against
  the `assertions` kinds and the body.
- **Replace with:** assert the named outcome, or rename the test to what it actually checks.
- **Lines deletable:** **0.**
- **`--fix-eligible:`** **false** — report-only.
- **Min certainty floor:** 0.6
- **False-positive guards:**
  1. **Vague names** (`works`, `handles input`) promise nothing specific. Skip them.
  2. **The outcome is asserted through a helper.** Read an allowlisted helper's body before flagging.

---

## What's deliberately NOT in this catalog

- **Slow tests** — wall-clock cost without an obvious smell. Surface to user via `/bx:health` recommendation, but not as a finding here.
- **Brittle tests by feel** — needs run data, not static analysis.
- **Tests that mirror production code structure 1:1** — sometimes appropriate (e.g. table-driven validators).
- **Coverage-percentage findings** — those are `test-coverage`'s job, not `test-quality`'s.
- **Orphaned tests, >3mo skipped tests, unused helpers, stale snapshots** — `/bx:clean`'s `cleanup-styles-tests` covers these.

If the subagent encounters a smell it cannot match to T01–T06, it should propose a catalog addition at the end of its output under `catalog_gap_proposals` with a justification — do not surface it as a regular finding.
