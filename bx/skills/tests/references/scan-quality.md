# Scan: Quality (T-prefix test smells)

Loaded by the orchestrator and passed to the `test-quality` subagent. Detailed scanning instructions follow.

## Inputs you receive in your task prompt

- `Detected stack` — language(s)
- `Test framework` — jest / vitest / pytest / cargo test / go test / etc.
- `Tier` — full | bounded | sample
- `Test scope` — exact test paths to evaluate (source files NOT in scope here)
- `Script manifest` — path to `manifest.json` from `scripts/run.py` (SKILL.md Step 3.5)
- `Testing-Intent Summary` — 3-5 bullets
- `Test Smell Catalog` — full content of `test-smell-catalog.md`. Use T01a, T01b, T02, T03, T04, T06.

## The script decides; you judge

`test_bodies.jsonl` (path in the manifest) holds one row per test in scope. It implements the
catalog's assertion definition, so **never count assertions yourself and never write a parser.**
Two real runs (S65) showed what hand counting does: a literal T01 reading offered 12 real pytest
tests for deletion, and a `{…}`-only parser reported 18 expression-bodied arrows as empty. Run-to-run
variance on T03 went 5 → 1 between two identical runs. A row you disagree with goes in `RUN NOTES`
with what you read; you do not re-derive it.

Fields you use: `file`, `line`, `end_line`, `name`, `describe`, `body_lines`, `assertions` (counts
by kind: `value`, `weak`, `presence`, `mock_verify`, `mock_absent`, `snapshot`, `raises`, `query`,
`playwright`, `helper`, `assert`), `assertion_total`, `weak_only`, `t03_candidate`,
`mock_setup_lines`, `calls`, `t01` (`{kind: a|b, signals}` when `assertion_total == 0`),
`todo_assert`, `skipped`, `param_rows`. `test_bodies.summary.json` holds the helper-allowlist
evidence and the per-file flags (`hook_asserts`, `property_based`).

## Approach

### Helper allowlist — copy the evidence, do not rebuild it

The summary's `helper_allowlist_size`, `helper_allowlist`, `helper_allowlist_patterns` and
`helper_allowlist_files_searched` are the catalog's allowlist, already run over every tracked file
with each kept name's body confirmed to assert or raise. Copy all four into your addendum. A zero
with `files_searched > 0` is a legitimate result. `--fix` refuses to run without them.

### T01a / T01b — rows with `t01` set

1. Take every row with `t01 != null` and `skipped == false`.
2. **Read each body before emitting it.** The row's zero is a hypothesis, not a finding.
3. Keep the script's `kind` unless reading shows it wrong. `kind: b` means the body calls code
   (`calls`), or a guard fired (`hook_asserts`, `property_based`, parameterized). Upgrading b → a is
   allowed only when every call is to a mock or a fixture, and you say which in `evidence`. When in
   doubt, it stays T01b.
4. Certainty: start at 0.85. Raise to 0.95 only for T01a with ≥3 statements and nothing under test
   called. Set 0.5 when `todo_assert` is true or the file's `hook_asserts` is true (both fall below
   the 0.7 floor).
5. Emit `evidence_body` (the full body, verbatim) on every T01a and T01b finding.

### T02 — rows with `weak_only: true`

The script already counts a `getBy*` inside `expect(..)` as `presence` and a positive `toBeNull()`
as `value`, so those never reach this list. Read each candidate. Apply the catalog's guards
(existence-is-the-test names → certainty 0.4). Severity: medium. Effort: small.

### T03 — rows with `t03_candidate: true`

The script's rule counts verification assertions only (`mock_verify`), never setup lines, and leaves
"never called" checks (`mock_absent`) out of both sides. Read each candidate and apply the
catalog's T03 guards, which are canonical there (including the orchestrator guard: a function whose
job is to call injected dependencies in order). A guarded candidate goes in `suppressed`.

### T04 — mystery guest (judgment; no script row)

Read the test files with the most `body_lines` first. Look for:
- File paths not imported in the test file (`readFileSync('fixtures/x.json')`, `open('data/y.csv')`)
- Env var reads with no setup that sets them (`process.env.X`, `os.environ['X']`)
- Hardcoded record IDs against a DB with no visible seeding

If the file has setup that loads or seeds these, it is not T04. A documented fixture-directory
convention lowers severity to low.

### T06 — name/assertion mismatch — rows with `t06_candidate: true`

The script flags a name that promises a visible outcome ("shows", "returns", "sends", "records")
with no negation ("nothing", "not", "never") whose only assertions are `weak` or `mock_absent`.
Read each body. A weak-only row that is a better T02 is reported as T02, not both. Report-only. You
may add a T06 the flag missed (a name promising one outcome while the assertions check another);
say so in `evidence`.

### T05 — not yours

Redundant tests are reported by `test-economics` from `consolidate.json`. Do not emit T05.

## Sampling

The tier's deep-read cap limits the candidates you **read in full**. It never limits the rows: every
row in `test_bodies.jsonl` was produced from the whole scope. When candidates exceed the cap, read in
order of `body_lines` descending and report the rest in `coverage_partial` as
`{category: "<smell>_verification", scanned, total, reason: "read cap"}`.

## Per-finding output shape

```
{
  "dimension": "quality",
  "smell_id": "T01a" | "T01b" | "T02" | "T03" | "T04" | "T06",
  "location": "tests/auth/session.test.ts:142-156",
  "title": "<one-line>",
  "severity": "low" | "medium" | "high",
  "certainty": 0.0-1.0,
  "effort_estimate": "trivial" | "small" | "medium" | "large",
  "coverage_gap_lines": 0,
  "deletable_lines": <int>,
  "respects_documented_decision": true | false,
  "recommended_action": "<prose>",
  "evidence": "<the row's assertion kinds plus what you read>",
  "evidence_body": "<T01a/T01b only: the full test body, verbatim>"
}
```

`deletable_lines` rules per smell are owned by the catalog:
- T01a: the row's `body_lines` (the whole test). T01b: **0**.
- T02, T03, T04, T06: **0**

Severity defaults:
- T01a: medium (high if the file has several, suggesting a pattern)
- T01b: low (the test does check something, just implicitly)
- T02: medium
- T03: medium
- T04: low
- T06: medium

Starting certainty after reading (guards lower it; T01 has its own rule above):
- T02: 0.7
- T03: 0.65
- T04: 0.6
- T06: 0.75

Min certainty floors before surfacing:
- T01a, T01b: 0.7
- T02: 0.6
- T03: 0.55
- T04: 0.5
- T06: 0.6

## Hard rules

- **Every finding must have a `smell_id` from T01a, T01b, T02, T03, T04, T06.** Catalog gaps → `catalog_gap_proposals` at end of output.
- **`respects_documented_decision: false` means a *document* states an intent the finding contradicts.** A tests README, an ADR, or a CLAUDE.md testing section counts. A known gap, a history note, or the inferred posture never makes a finding `false`.
- **Scope is computed by the orchestrator, not by you.** Scan exactly the file list in your task prompt. Its exclusions are owned by the arch skill's `references/scan-exclusions.md`. **Never widen your own scope.**
- **Cap output at 30 findings.** Order by severity, then `certainty × (1 + log10(deletable_lines + 1))` descending.
- **`respects_documented_decision` defaults to `true`.**
- **Defer to /bx:clean** for: orphaned test files, >3mo skipped tests, unused test helpers, stale snapshots. If detected in passing, note in `recommended_action` and DO NOT emit a separate finding.
- Never run the tests or the scripts. Never write inside the scanned repo.

## Final output addendum

```
total_deletable_lines: <sum of T01a deletable lines>
files_affected: <distinct test files with deletable findings>
catalog_gap_proposals: [<list of unmatched-smell descriptions, each with a justification>]
tests_in_rows: <summary.tests>
t01a_count: <script> / <reported>     (script = the summary's count, reported = your findings)
t01b_count: <script> / <reported>
t02_count: <script weak_only> / <reported>
t03_count: <script t03_candidates> / <reported>
t04_count: <reported>
t06_count: <script t06_candidates> / <reported>
helper_allowlist_size: <int>
helper_allowlist_patterns: <the summary's object, copied as-is>
helper_allowlist_files_searched: <int>
suppressed: [<{location, smell, reason} for candidates read and dropped by a guard or a floor>]
coverage_negatives: [<per SKILL.md Step 4 — one entry per T-smell that produced nothing>]
coverage_partial: [<the manifest's test_bodies entries, plus any read-cap entries>]
RUN NOTES: [<every row you disagreed with: file:line, the row's value, what you read>]
```
