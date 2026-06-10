# Scan: Coverage (missing tests on critical paths)

Loaded by the orchestrator and passed to the `test-coverage` subagent. Detailed scanning instructions follow.

## Inputs you receive in your task prompt

- `Detected stack` — language(s), framework(s)
- `Test framework` — jest / vitest / pytest / cargo test / go test / etc.
- `Coverage mode` — `heuristic` (default) | `report` (`--coverage` opt-in)
- `Coverage report path` — populated only in `report` mode
- `Tier` — full | bounded | sample
- `Source scope` — exact source paths to evaluate
- `Test scope` — exact test paths (for neighbor lookups)
- `Testing-Intent Summary` — 3-5 bullets from CLAUDE.md/tests-README/ADRs

## Approach

For each source file in scope, compute a **priority score**, take the top 50 by priority, and drill into each. Drill-down is mode-dependent.

### Priority scoring (run for every source file in scope)

```
priority = security_keyword_density × (1 + log10(churn + 1)) × (1 + log10(fan_in + 1))
```

where:

- **`security_keyword_density`** — `Grep -i -c -w '(auth|password|token|session|crypto|permission|role|payment|charge|refund|secret|key|validate|sanitize|escape|csrf|xss|sql|migrate|encrypt|decrypt|hash|sign|verify)'` ÷ file LOC. Cap at 1.0.
- **`churn`** — `git log --since='1 year ago' --pretty=format:%H -- <file> | wc -l`.
- **`fan_in`** — for each file, count importers using one batched grep across the test+source scope: pattern `from\s+['"][^'"]*${basename}['"]` or `require\(['"][^'"]*${basename}['"]\)` or `import\s+["][^"]*${basename}["]` etc. depending on stack.

Take the **top 50** files by priority. If `--full-scan` was set, take all.

### Heuristic mode (default — Coverage mode = heuristic)

For each top-priority source file:

**Step 1: Test-neighbor lookup.** Look for a sibling test file. Conventions (try in order, stop at first match):
- JS/TS: `<base>.test.<ext>`, `<base>.spec.<ext>`, `__tests__/<base>.<ext>`, `__tests__/<base>.test.<ext>`
- Python: `tests/test_<base>.py`, `test_<base>.py`, `tests/<dir>/test_<base>.py`
- Rust: `tests/<base>.rs`, `<file>` itself with `#[cfg(test)] mod tests` (inline tests)
- Go: `<base>_test.go`
- JVM: `src/test/java/<package>/<Base>Test.java` mirroring `src/main/java/...`

If **no neighbor exists** at all: surface a finding with `coverage_gap_lines = file_LOC`, severity from priority score, `recommended_action = "Add a test file at <expected_path> covering exported symbols X, Y, Z."`

**Step 2: Public-symbol enumeration.** Parse exported / public symbols. Conventions:
- JS/TS: lines matching `^export (function|const|class|async function|default function)` — capture name
- Python: top-level `def \w+` and `class \w+` (skip leading-underscore — convention for private)
- Rust: `pub fn \w+` and `pub struct \w+` and `pub enum \w+`
- Go: function/method declarations starting with capital letter
- JVM: `public` method/class declarations

**Step 3: Symbol-level coverage probe.** For each exported symbol, grep the neighbor test file for the symbol's name. A symbol with zero string-match references is uncovered.
- `coverage_gap_lines` per symbol = symbol body LOC (approximated by counting lines between the declaration and the next sibling declaration / file end).

**Step 4: Bug-fix-without-regression scan.** Run:
```
git log -50 --pretty='%H|%s' --regexp-ignore-case --grep='^fix:' --grep='^bugfix' --grep='closes #' --grep='fixes #'
```
For each matched commit, `git show --stat --name-only <hash>` and check whether any path matching the test-scope patterns was modified. If only source paths were touched, surface a `smell_id: bug_fix_no_test` finding referencing the commit. **Cap at top 10** to avoid noise.

### Report mode (Coverage mode = report — only when `--coverage` opted in)

Read the coverage report at the orchestrator-provided path:

- **Jest / Vitest** — `coverage/coverage-summary.json` shape:
  ```json
  { "path/to/file.ts": { "lines": { "pct": 42.3, "total": 80, "covered": 34 } } }
  ```
  `coverage_gap_lines = total - covered`.
- **pytest-cov** — `coverage.json` shape:
  ```json
  { "files": { "path": { "executed_lines": [12, 13, ...], "missing_lines": [25, 26, 30] } } }
  ```
  `coverage_gap_lines = len(missing_lines)`.
- **cargo-tarpaulin** — `tarpaulin-report.json`.
- **go test -coverprofile** — parse `coverage.out` lines `<file>:<start>.<col>,<end>.<col> <stmts> <count>`; sum `stmts` where `count == 0` per file.
- **phpunit (Clover XML)** — `coverage/coverage.xml`: per `<file>` element, `coverage_gap_lines = statements - coveredstatements` from its `<metrics>` attributes (or count `<line ... count="0">` entries).
- **JaCoCo XML** — `target/site/jacoco/jacoco.xml`: per `<sourcefile>`, read `<counter type="LINE" missed="M" covered="C"/>`; `coverage_gap_lines = M`.

In `report` mode, do **not** mix heuristic gaps — would double-count. The numbers come straight from the report.

If the report file is missing in `report` mode, surface a single finding:
```
{
  "smell_id": "install_hint",
  "dimension": "coverage",
  "location": "<expected report path>",
  "title": "Coverage report not found",
  "severity": "low",
  "certainty": 1.0,
  "coverage_gap_lines": 0,
  "deletable_lines": 0,
  "recommended_action": "Generate the coverage report with: <per-stack-command>. Then re-run /bx:tests --coverage."
}
```
Per-stack commands to suggest:
- Jest: `npx jest --coverage --coverageReporters=json-summary`
- Vitest: `npx vitest run --coverage --coverage.reporter=json-summary`
- Pytest: `pytest --cov=. --cov-report=json`
- Cargo: `cargo tarpaulin --out Json`
- Go: `go test -coverprofile=coverage.out ./...`

Stop after the install_hint finding; do not fall back to heuristic mode.

## Per-finding output shape

```
{
  "dimension": "coverage",
  "location": "src/auth/verifySession.ts:14-62",
  "title": "Critical-path function `verifySession` has no test coverage",
  "severity": "high" | "medium" | "low",
  "certainty": 0.0-1.0,
  "effort_estimate": "trivial" | "small" | "medium" | "large",
  "coverage_gap_lines": <int>,
  "deletable_lines": 0,
  "priority_score": <float>,
  "priority_factors": { "security_density": <float>, "churn": <int>, "fan_in": <int> },
  "respects_documented_decision": true | false,
  "recommended_action": "<prose>",
  "smell_id": null | "bug_fix_no_test" | "install_hint"
}
```

Severity mapping:
- `priority_score >= 5.0` → high
- `priority_score >= 2.0` → medium
- otherwise → low

Effort estimate from gap size:
- `coverage_gap_lines <= 20` → trivial
- `coverage_gap_lines <= 60` → small
- `coverage_gap_lines <= 200` → medium
- else → large

## Hard rules

- **`coverage_gap_lines >= 1` mandatory.** Drop zero-gap findings.
- **Order by `priority_score × certainty` descending.** Cap at 30.
- **Skip vendored/generated/build dirs**: `node_modules`, `venv`, `.git`, `dist`, `build`, `__pycache__`, `.next`, `.cache`, `vendor`, `target/`, `coverage/`, `__generated__/`, `*.generated.*`, `*.d.ts`.
- **Skip trivial files**: pure type/interface declaration files, single-line constant export files, framework-generated barrel files (`index.ts` that only re-exports).

## Final output addendum

At the end of your findings, append:

```
coverage_gap_total: <sum of all flagged findings' coverage_gap_lines>
files_affected: <count of distinct source files with gaps>
heuristic_files_scanned: <int>
heuristic_files_skipped: <int>
report_mode: heuristic | report
report_path_consumed: <path or null>
```

These power the report's twin headline and footer disclosure.
