# Test Smell Catalog — T-prefix entries

Each entry follows the same schema as the S-prefix simplification catalog in `bx:arch/references/refactor-catalog.md`. The `test-quality` subagent must cite an entry by ID in `smell_id`. Entries marked `--fix-eligible: true` may be auto-applied in `--fix` mode (still gated by per-finding diff preview).

## Rules for the catalog

- **Languages tag is binding.** Detection patterns are language-aware. Don't fire a Jest matcher rule on a pytest file.
- **`deletable_lines` is honest.** Only T01 (every line) and confirmed-T05 (overlap minus parameter overhead) and snapshot-heavy (in test-economics) contribute to the report's deletion headline. T02/T03/T04 are *rewritable*, not deletable — report `deletable_lines: 0`.
- **False-positive guards are mandatory.** Test smells over-fire easily; every entry below includes a guard the subagent must run first.

---

## T01 — Assertion-free test

- **Languages:** all
- **Detect when:** a test function body contains zero assertion-shaped calls.
  - JS/TS (jest/vitest/mocha/jasmine): no `expect(`, no `assert.`, no `chai.expect`, no `should`, no `t.is`/`t.deepEqual` (ava), no `chai.assert`
  - Python (pytest/unittest): no `assert ` statement, no `self.assert*` method call, no `pytest.raises` context, no `pytest.warns`
  - Rust: no `assert!` / `assert_eq!` / `assert_ne!` / `debug_assert*` / `panic!`-in-error-path
  - Go: no `t.Error*` / `t.Fatal*` / `t.Fail*` / `require.*` / `assert.*` (testify)
  - JVM (JUnit): no `Assertions.*` / `Assert.*` / `assertThat`
- **Replace with:** delete the test entirely. Greenness from a no-op test is a lie.
- **Lines deletable:** entire test body LOC, including the `it(...)` / `def test_...` wrapper. If the surrounding `describe`/`context` becomes empty after deletion, the orchestrator's `--fix` flow prompts about parent-block removal.
- **`--fix-eligible:`** **true** — the only T-entry that is. Deletion is provably safe: a test that asserts nothing cannot fail meaningfully.
- **Min certainty floor to surface:** 0.7
- **False-positive guards (the subagent MUST run these first):**
  1. **Project-defined assertion helpers.** Grep the entire codebase for definitions matching `^(function |def |fn |const )\s*(assert|should|expect|check|verify|ensure|require|must)\w*`. Any test body calling one of these matched names is **not** assertion-free.
  2. **Custom matcher extensions.** Grep for `expect.extend({...})` (Jest), `expect_extends` (vitest), `pytest_plugins` definitions adding assertion helpers, `chai.use(...)` plugin loads. Treat their exported names as assertion calls.
  3. **Hook-based assertions.** Some setups assert in `afterEach` / `tearDown`. If the test file's setup hooks contain assertions and the body just sets up state for the hook to check, do not flag.
  4. **Property-based generators.** `fast-check`, `hypothesis`, `proptest` — bodies often look bare because the assertion is in the generator callback. Check for these imports before flagging.

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
