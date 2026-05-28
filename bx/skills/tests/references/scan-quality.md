# Scan: Quality (T-prefix test smells)

Loaded by the orchestrator and passed to the `test-quality` subagent. Detailed scanning instructions follow.

## Inputs you receive in your task prompt

- `Detected stack` — language(s)
- `Test framework` — jest / vitest / pytest / cargo test / go test / etc.
- `Tier` — full | bounded | sample
- `Test scope` — exact test paths to evaluate (source files NOT in scope here)
- `Testing-Intent Summary` — 3-5 bullets
- `Test Smell Catalog` — full content of `test-smell-catalog.md`. Use only T01-T05.

## Approach

**Run this once at the start.** Build a catalog of project-defined assertion helpers — this is the critical false-positive guard for T01. Without it, you will delete real tests.

### Step 0: Build the assertion-helper allowlist

```
# Grep across ALL paths (including non-test) for helper definitions
Grep -n -E "^(export )?(function |const |async function )(assert|should|expect|check|verify|ensure|require|must)\w*\b" --type ts --type js
Grep -n -E "^def (assert|should|expect|check|verify|ensure|require|must)\w*\(" --type py
Grep -n -E "^(pub )?fn (assert|should|expect|check|verify|ensure|require|must)\w*\(" --type rust

# Custom matcher extensions
Grep -n -E "expect\.extend\s*\(" --type ts --type js
Grep -n -E "chai\.use\s*\(" --type ts --type js
Grep -n -E "@pytest\.fixture[^)]*assert" --type py
```

Record helper names. Pass this allowlist to all T01 detection steps.

### Per-entry detection

#### T01 — Assertion-free test

For each test in scope:
1. Identify test bodies by framework:
   - Jest/vitest/jasmine: `it(...)` / `test(...)` / `specify(...)` / `it.only(...)` etc. callbacks
   - Mocha: same plus `.skip`/`.only` variants
   - pytest: top-level `def test_*` and methods on `class Test*`
   - unittest: `def test_*` methods on `class *(unittest.TestCase)`
   - Rust: `#[test]` annotated functions
   - Go: `func Test*(t *testing.T)` and `func Benchmark*` (not subject — skip)
   - JUnit: `@Test`-annotated methods
2. For each body, count assertion calls. An assertion is:
   - Framework matchers: `expect(*)` with `.toBe`/`.toEqual`/`.toMatch`/`.toHaveLength`/`.toThrow`/`.rejects.toThrow` etc.; `chai.expect(*).to.*`; `should.*`; `assert.*`; `t.is/t.deepEqual/t.truthy` (ava)
   - Pytest: `assert <expr>`, `pytest.raises(...)`, `pytest.warns(...)`, `np.testing.assert_*`
   - Unittest: `self.assert*`, `self.assertRaises`, `self.assertWarns`
   - Rust: `assert!`/`assert_eq!`/`assert_ne!`/`debug_assert!*`/`panic!` (in error-path test)
   - Go: `t.Error`/`t.Errorf`/`t.Fatal`/`t.Fatalf`/`t.Fail`; testify `assert.*` / `require.*`
   - JUnit: `Assertions.*`, `Assert.*`, `assertThat`
   - **Project-defined helpers** from your Step 0 allowlist
3. If count == 0 AND the body has ≥1 non-comment statement, surface a T01 finding.
4. Boost certainty to 0.95 if body has ≥3 lines AND zero matches; lower to 0.75 if body is short (≤3 lines) — short might be intentional smoke test.

Setup-hook check: if file uses `beforeEach`/`afterEach`/`setUp`/`tearDown` and those hooks contain assertions, lower certainty to 0.5 for any T01 in this file (the assertions may live in hooks).

#### T02 — Weak assertion

For each test body with assertions:
1. Categorize each assertion as:
   - **Weak**: `toBeTruthy`/`toBeFalsy`/`toBeDefined`/`not.toBeNull`/`not.toBeUndefined`/`>= 0`/`<= max`/`!= null`/`is not None`/`expect(typeof x).toBe('string')`/`expect(x).toBeInstanceOf(Object)`
   - **Tautological**: `expect(x).toBe(x)`, `expect(x).toEqual(x)`, comparing literal to itself
   - **Strong**: specific value match, deep object compare, exception type+message match
2. If ALL assertions in the body are Weak or Tautological → T02.
3. Severity: medium. Effort: small (rewrite one or two assertions).

False-positive guard: parse test name for hints. Names containing `does not throw`, `is defined`, `returns truthy`, `does not return null`, `is callable` legitimize weak assertions. Lower certainty to 0.4.

#### T03 — Implementation-coupled / mock-heavy

For each test body:
1. Count `implementation_lines`:
   - JS/TS: `toHaveBeenCalledWith`, `toHaveBeenCalledTimes`, `toHaveBeenLastCalledWith`, `toHaveBeenCalled`, lines containing `.mockReturnValue`, `.mockImplementation`, `.mockResolvedValue`, `vi.mock(`, `jest.mock(`
   - Python: `mock.assert_called*`, `mock.call_args`, `MagicMock(...)`, `patch(...)` decorator lines
   - JVM (mockito): `verify(`, `when(...).thenReturn`, `Mockito.mock(`
2. Count `behavior_lines`: assertions that check return values, persisted state, observable side effects.
3. Flag if `impl / max(behavior, 1) > 2.0` AND `impl >= 4`.

False-positive guard: scan class/file name for boundary indicators (Publisher, Emitter, Dispatcher, Logger, Tracer, Notifier, Repository, Adapter). For tests on these, interaction *is* behavior — lower severity to low.

#### T04 — Mystery guest

For each test body:
1. Look for references to external data:
   - File paths not imported in the test file (`readFileSync('fixtures/x.json')`, `open('data/y.csv')`)
   - Env var reads with no setup that sets them (`process.env.X`, `os.environ['X']`)
   - Database queries returning hardcoded IDs (`User.find(1)`, `db.query('SELECT * FROM users WHERE id=1')`) without seeding visible
2. Check if the file has setup that loads/seeds these. If not → T04.

False-positive guard: if `tests/README` or CLAUDE.md describes a fixture-directory convention, lower severity to low.

#### T05 — Redundant test

Within each test file (do NOT cross files for T05):
1. Tokenize each test body: strip whitespace, normalize variable names (replace identifiers with positional tokens by first-occurrence order), drop literals.
2. For each pair of tests in the same `describe`/`context`, compute Jaccard similarity of token multisets.
3. If similarity ≥ 0.8 AND inputs are **not** boundary values (check for `0`, `-1`, `null`, `''`, `MAX_INT`, `MIN_INT` literals in either) → T05.
4. **Conservative deletable accounting:** report `deletable_lines: 0` unless `certainty >= 0.85` AND duplicates are demonstrably identical (Jaccard >= 0.95).

False-positive guards:
- Skip `describe.each` / `it.each` / `@pytest.parametrize` / `func Test_table_*` blocks entirely.
- Boundary-value coverage: if differing inputs include known boundary literals, don't flag.
- Different `beforeEach`/`setUp` per nested describe → different setup paths → not redundant.

## Per-finding output shape

```
{
  "dimension": "quality",
  "smell_id": "T01" | "T02" | "T03" | "T04" | "T05",
  "location": "tests/auth/session.test.ts:142-156",
  "title": "<one-line>",
  "severity": "low" | "medium" | "high",
  "certainty": 0.0-1.0,
  "effort_estimate": "trivial" | "small" | "medium" | "large",
  "coverage_gap_lines": 0,
  "deletable_lines": <int>,
  "respects_documented_decision": true | false,
  "recommended_action": "<prose>",
  "evidence": "<one or two lines naming the specific assertions/lines/mocks observed>"
}
```

`deletable_lines` rules per smell (already in the catalog, repeated here for the subagent's quick reference):
- T01: test body LOC
- T02, T03, T04: **0**
- T05: 0 unless `certainty >= 0.85`, then `(body_lines × (n_duplicates - 1)) - parameterization_overhead`, floor at 1

Severity defaults:
- T01: medium (high if file has multiple T01s suggesting a pattern)
- T02: medium
- T03: medium
- T04: low
- T05: low

Min certainty floors before surfacing:
- T01: 0.7
- T02: 0.6
- T03: 0.55
- T04: 0.5
- T05: 0.75

## Hard rules

- **Every finding must have a `smell_id` from T01-T05.** Catalog gaps → `catalog_gap_proposals` at end of output.
- **Skip non-test paths.** Only files matching common test conventions (`*.test.*`, `*.spec.*`, `_test.go`, `_test.rs`, `test_*.py`, files under `tests/`, `__tests__/`, `spec/`).
- **Skip vendored/generated/build dirs**: `node_modules`, `venv`, `.git`, `dist`, `build`, `__pycache__`, `.next`, `.cache`, `vendor`, `target/`, `coverage/`, `__generated__/`.
- **Cap output at 30 findings.** Order by `severity_weight × certainty × (1 + log10(deletable_lines + 1))` descending.
- **Defer to /bx:clean** for: orphaned test files, >3mo skipped tests, unused test helpers, stale snapshots. If detected in passing, note in `recommended_action` and DO NOT emit a separate finding.

## Final output addendum

```
total_deletable_lines: <sum of T01 + qualifying-T05 deletable lines>
files_affected: <distinct test files with deletable findings>
catalog_gap_proposals: [<list of unmatched-smell descriptions, each with a justification>]
t01_count: <int>
t02_count: <int>
t03_count: <int>
t04_count: <int>
t05_count: <int>
helper_allowlist_size: <int>
```
