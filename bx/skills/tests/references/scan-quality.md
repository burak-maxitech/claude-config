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

**Run this once at the start.** Build the project's assertion-helper allowlist. It is the critical false-positive guard for T01: without it, you will delete real tests.

### Step 0: Build the assertion-helper allowlist

Use the per-language patterns in the catalog's **What counts as an assertion** section exactly as
written, across *all* paths. Do not substitute your own anchors. Narrower patterns are how earlier
runs missed indented, `async` and test-local helpers. Keep a matched name only if a test calls it and
its body asserts or raises, and record the rejected names with a reason.

Report the three evidence fields (`helper_allowlist_size`, `helper_allowlist_patterns`,
`helper_allowlist_files_searched`) in your addendum **even when the size is zero**. `--fix` refuses
to run without them.

### Per-entry detection

#### T01 — Assertion-free test (T01a / T01b)

For each test in scope:
1. Identify test bodies by framework:
   - Jest/vitest/jasmine/mocha/Playwright: `it(...)` / `test(...)` / `specify(...)` and their
     `.only`/`.skip`/`.concurrent`/`.each(...)` variants. **This includes expression-bodied arrows**
     (`it("x", () => expect(f()).toBe(1))`), whose body is the expression itself. A parser that only
     reads `{ ... }` blocks reports every one of them as empty. That bug produced 18 false T01s on a
     real run (S65).
   - pytest: top-level `def test_*` and methods on `class Test*` (including `async def`)
   - unittest: `def test_*` methods on `class *(unittest.TestCase)`
   - Rust: `#[test]` annotated functions
   - Go: `func Test*(t *testing.T)` (skip `func Benchmark*`)
   - JUnit: `@Test`-annotated methods
2. Count assertions using the catalog's definition: mock verification, throwing queries (`getBy*`),
   Playwright actions, and allowlisted helpers all count.
3. If the count is 0 and the body has ≥1 non-comment statement, it is a T01 candidate. **Read the
   candidate body before emitting it.** A script's zero is a hypothesis, not a finding.
4. Classify it as **T01a** (no-op) or **T01b** (implicit no-raise) per the catalog. When in doubt,
   use T01b.
5. Certainty: start at 0.85. Raise it to 0.95 only for T01a bodies of ≥3 statements with nothing
   under test called. Lower it to 0.5 for an in-flight `TODO assert` comment or for assertions in
   setup or teardown hooks (both drop below the 0.7 floor).

Emit `evidence_body` (the full test body, verbatim) on every T01a and T01b finding. `--fix` shows it
to the user and re-checks it.

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
  "smell_id": "T01a" | "T01b" | "T02" | "T03" | "T04" | "T05",
  "location": "tests/auth/session.test.ts:142-156",
  "title": "<one-line>",
  "severity": "low" | "medium" | "high",
  "certainty": 0.0-1.0,
  "effort_estimate": "trivial" | "small" | "medium" | "large",
  "coverage_gap_lines": 0,
  "deletable_lines": <int>,
  "respects_documented_decision": true | false,
  "recommended_action": "<prose>",
  "evidence": "<one or two lines naming the specific assertions/lines/mocks observed>",
  "evidence_body": "<T01a/T01b only: the full test body, verbatim>"
}
```

`deletable_lines` rules per smell are owned by the catalog:
- T01a: the whole test. T01b: **0**.
- T02, T03, T04: **0**
- T05: 0 unless `certainty >= 0.85`, then `(body_lines × (n_duplicates - 1)) - parameterization_overhead`, floor at 1

Severity defaults:
- T01a: medium (high if the file has several, suggesting a pattern)
- T01b: low (the test does check something, just implicitly)
- T02: medium
- T03: medium
- T04: low
- T05: low

Min certainty floors before surfacing:
- T01a, T01b: 0.7
- T02: 0.6
- T03: 0.55
- T04: 0.5
- T05: 0.75

## Hard rules

- **Every finding must have a `smell_id` from T01a, T01b, T02–T05.** Catalog gaps → `catalog_gap_proposals` at end of output.
- **`respects_documented_decision: false` means a *document* states an intent the finding contradicts.** A tests README, an ADR, or a CLAUDE.md testing section counts. A known gap, a history note, or the inferred posture never makes a finding `false`.
- **Skip non-test paths.** Only files matching common test conventions (`*.test.*`, `*.spec.*`, `_test.go`, `_test.rs`, `test_*.py`, files under `tests/`, `__tests__/`, `spec/`).
- **Scope is computed by the orchestrator, not by you.** Scan exactly the file list in your task prompt. Its exclusions — synthetic/fixture trees, vendored and generated dirs, immutable history — are owned by the arch skill's `references/scan-exclusions.md`. **Never widen your own scope**; if something outside the list looks relevant, say so as a note rather than reading it. The fixture rule matters most: planted eval fixtures produce true-shaped findings that are false by construction.
- **Cap output at 30 findings.** Order by `severity_weight × certainty × (1 + log10(deletable_lines + 1))` descending.
- **Defer to /bx:clean** for: orphaned test files, >3mo skipped tests, unused test helpers, stale snapshots. If detected in passing, note in `recommended_action` and DO NOT emit a separate finding.

## Final output addendum

```
total_deletable_lines: <sum of T01a + qualifying-T05 deletable lines>
files_affected: <distinct test files with deletable findings>
catalog_gap_proposals: [<list of unmatched-smell descriptions, each with a justification>]
t01a_count: <int>
t01b_count: <int>
t02_count: <int>
t03_count: <int>
t04_count: <int>
t05_count: <int>
helper_allowlist_size: <int>
helper_allowlist_patterns: [<the patterns actually run>]
helper_allowlist_files_searched: <int>
coverage_negatives: [<per SKILL.md Step 4 — one entry per T-smell that produced nothing>]
coverage_partial: [<per SKILL.md Step 4 — any check that did not cover its whole scope>]
```
