# Test Smell Catalog — T-prefix entries

Each entry follows the same schema as the arch catalogs, whose canonical rules live in `../arch/references/catalog-rules.md` — resolve that against **this skill's base directory** (`bx/skills/tests/`), not against this file's directory. The S-prefix entries this catalog was modelled on are in the sibling `catalog-simplification.md`. The `test-quality` subagent must cite an entry by ID in `smell_id`. Only `T01a` is `--fix`-eligible, and only through the gated flow in `fix-mode-test.md`.

## Rules for the catalog

- **Languages tag is binding.** Detection patterns are language-aware. Don't fire a Jest matcher rule on a pytest file.
- **`deletable_lines` is honest.** Only T01a (every line) and confirmed-T05 (overlap minus parameter overhead) and snapshot-heavy (in test-economics) contribute to the report's deletion headline. T02/T03/T04 are *rewritable*, not deletable — report `deletable_lines: 0`.
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
  - `not.toBeNull()` / `not.toBeUndefined()` / `toBeDefined()` standing alone (asserts existence, not value)
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
- **Detect when:** the test body's assertion lines are dominated by interaction verification rather than behavior verification.
  - Count "implementation lines": `toHaveBeenCalledWith`, `toHaveBeenCalledTimes`, `toHaveBeenLastCalledWith`, mock-setup statements (`vi.mock`, `jest.mock`, `mockReturnValue`, `mockImplementation`), `unittest.mock.assert_called*`, `verify(mock).method(...)` (mockito).
  - Count "behavior lines": value/shape assertions (`toBe`, `toEqual`, `toMatchObject` on real return values), `assert == value`, real output checks.
  - Flag when `implementation_lines / max(behavior_lines, 1) > 2.0` AND `implementation_lines >= 4`.
- **Replace with:** rewrite to test observable behavior — the function's return value, persisted state, emitted events. Mock only at the system boundary (network, time, RNG, filesystem).
- **Lines deletable:** **0** (rewritable).
- **`--fix-eligible:`** **false** — judgment-heavy rewrite.
- **Min certainty floor:** 0.55
- **False-positive guards:**
  1. **Interaction is the contract.** If the unit under test is an event publisher / message dispatcher / logger wrapper, interaction verification *is* behavior verification. Skip if class name suggests this (Publisher, Emitter, Dispatcher, Logger, Tracer, Notifier).
  2. **Test seam at the boundary.** Tests in an `adapters/` or `infrastructure/` folder are often verifying boundary contracts; lower certainty.
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

## T05 — Redundant test

- **Languages:** all
- **Detect when:** within a single test file, ≥2 tests share ≥80% of body lines after normalization (strip whitespace, normalize variable names), differing only in input values that are **not** boundary cases (off-by-one, empty, max, null, negative).
  - Comparison is line-set similarity, not AST equivalence. Cheap approximation: tokenize → sort → Jaccard index of token multisets.
- **Replace with:** parameterize into a single test with a data table (`describe.each` / `it.each` in Jest, `@pytest.parametrize`, `table_test` pattern). If the inputs are identical and only the test name differs, delete the duplicates.
- **Lines deletable:** **conservative 0 by default.** Only when the subagent has certainty ≥0.85 AND the duplicates are demonstrably identical inputs (not boundary cases), report `deletable_lines = (test_body_lines × (n_duplicates - 1)) - parameterization_overhead`. Floor at 1.
- **`--fix-eligible:`** **false** — even high-confidence "redundant" tests sometimes encode coverage at different boundary conditions a reader can't see without domain context. Route to `--plan`.
- **Min certainty floor:** 0.75
- **False-positive guards:**
  1. **Boundary value coverage.** Inputs `[0, -1, MAX_INT, MIN_INT, '', null]` are testing edges, not duplication. Detect numeric / string-empty / null variants explicitly and skip.
  2. **Different setup paths.** If tests share body but differ in `beforeEach`/`fixture` setup, they're not redundant.
  3. **Table tests already.** Tests inside `describe.each`, `it.each`, `@pytest.parametrize`, table tests in Go are intentional parameterized variants. Skip the entire `each` block.

---

## What's deliberately NOT in this catalog

- **Slow tests** — wall-clock cost without an obvious smell. Surface to user via `/bx:health` recommendation, but not as a finding here.
- **Brittle tests by feel** — needs run data, not static analysis.
- **Tests that mirror production code structure 1:1** — sometimes appropriate (e.g. table-driven validators).
- **Coverage-percentage findings** — those are `test-coverage`'s job, not `test-quality`'s.
- **Orphaned tests, >3mo skipped tests, unused helpers, stale snapshots** — `/bx:clean`'s `cleanup-styles-tests` covers these.

If the subagent encounters a smell it cannot match to T01-T05, it should propose a catalog addition at the end of its output under `catalog_gap_proposals` with a justification — do not surface it as a regular finding.
