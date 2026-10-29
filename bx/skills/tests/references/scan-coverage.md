# Scan: Coverage (missing tests on critical paths)

Loaded by the orchestrator and passed to the `test-coverage` subagent. Detailed scanning instructions follow.

## Inputs you receive in your task prompt

- `Detected stack` — language(s), framework(s)
- `Test framework` — jest / vitest / pytest / cargo test / go test / etc.
- `Coverage mode` — `heuristic` (default) | `report` (`--coverage` opt-in)
- `Coverage report path` — populated only in `report` mode
- `Tier` — full | bounded | sample
- `Source scope` / `Test scope` — exact paths
- `Script manifest` — path to `manifest.json` from `scripts/run.py` (SKILL.md Step 3.5)
- `Testing-Intent Summary` — 3-5 bullets from CLAUDE.md/tests-README/ADRs

## The scripts decide; you judge

Every number below comes from the manifest's files. **Do not recompute churn, fan-in, keyword
density, symbol lists or test references by grep, and do not write a parser.** Two real runs (S65)
showed what hand computation does: a basename fan-in, a neighbor-only lookup that produced ~30,000
false gap lines, and mock-only references counted as coverage. If a row looks wrong, read the code,
say so in `RUN NOTES` with the row and the reason, and judge the finding on what you read. Never
silently re-derive it.

| File | What it gives you |
|---|---|
| `leverage.json` `files[]` | per source file: `loc`, `churn` (commits in a year), `fan_in` (production importers, **resolved to paths**), `test_importers` (the test files that import it — this replaces the neighbor lookup), `test_mockers`, `entry_point` + `entry_reason`, `security_density`, `priority` |
| `leverage.json` `bugfix_commits[]` | the last 200 commits filtered to fix subjects (`^fix\b`, so `fix(scope):` matches), with `files` and `touched_tests` |
| `references.json` `symbols[]` | per public symbol: `kind`, extent (`line`–`end_line`, `lines`), `prod_refs`, `test_status`, `test_call_rows`, `test_mock_rows`, `security_lines`, `priority`, `gap_lines` |

`test_status` is one of:
- `covered` — at least one test **calls** it, from a file that imports its module (or its class), without mocking it.
- `indirect` — no test calls it, but a test calls a production caller of it without mocking it
  (`reached_via` names the caller; `indirect_depth` 1 or 2 public levels, private helpers in between
  followed; `direct_status` keeps what it would have been). **Not a gap**: `gap_lines` is 0. S257:
  `withTodaysDialChoice` read mock_only because one route test mocks it, while `extract.test.ts`
  ran it through `extractWatchFromUrl`; a private SQL builder read untested while its callers' tests
  rendered it. It is reachability, not proof the caller's tests take the branch that calls it, so
  read the ones with `security_lines > 0` (up to 10, highest `priority` first): when the caller's
  tests never reach the call (it sits in a branch none of them enters), report a gap at certainty
  0.6 with `coverage_gap_lines` = the symbol's `lines`, and say which branch.
- `mock_only` — tests reach it only as a mock (`vi.mock` of its module, `vi.mocked`, `spyOn`, `patch("…name")`). **This is a gap** (problem 17): say "tests mock it but never run it".
- `name_only` — a call of the same name in a test that does not import it. Read one before deciding; usually a name collision, so a gap.
- `mention_only` — referenced (passed, typed, asserted on) but never called. A gap unless the reference is itself the test (a constant checked by value).
- `untested` — no test references at all.

Declarative symbols (`kind: value | type | interface | enum` — tables, config objects, types) carry
`gap_lines: 0` and are never gap findings.

## Approach (heuristic mode)

1. **Rank.** Take `references.json` symbols with `gap_lines > 0`, in the file's order: by
   `priority` (symbol security density × file churn × file fan-in, with an entry-point floor so
   routes and middleware rank), then — for the many symbols with no security words, which tie at 0 —
   by `leverage × log(gap_lines)`. Read the top 50 in that order (all of them under `--full-scan`).
   `symbols_read` counts the candidate symbols you opened.
2. **Group per file.** A file whose every non-declarative symbol is a gap **and** whose
   `test_importers` is empty is a whole-file gap: one finding, `coverage_gap_lines` = the sum of its
   symbols' `gap_lines`. A container class with `gap_lines: 0` does not block the rule. Otherwise
   emit one finding per gap symbol, or per run of gap symbols in one file that lie within ~20 lines
   of each other. A grouped finding's `priority_score` is its highest member's; a whole-file finding uses the file's
   `leverage.json` `priority`. Subtract the symbols you suppress (factories, accessors) from a grouped
   or whole-file `coverage_gap_lines`. Findings that tie keep `references.json`'s order. Never use file LOC: it
   counts imports, types and blank lines.
3. **Verify by reading.** Open each candidate symbol and confirm it has logic worth testing. A
   one-line delegation, a re-export, a framework stub or a declarative class the script missed (an
   ORM model with only column fields) drops out; record it under `suppressed`. A SQL-fragment builder
   whose callers' tests render the SQL is `indirect` when the script saw the call; when it did not
   (a call through a variable or a table of builders), keep it at certainty 0.6 and say so.
4. **Entry points.** A file with `entry_point: true` and no `test_importers` is a gap even at low
   density (S182: `(dashboard)/layout.tsx` held the only auth redirect). Name the `entry_reason`.
   Entry files whose gap symbols total under 10 lines (thin page wrappers) are counted in the
   addendum as `entry_wrappers_skipped`, not read.
5. **Fan-in 0, not an entry point** — may be dead. Lower certainty to 0.5 and point at `/bx:clean`
   (or at the `life_support` lane when `references.json` lists it there).
6. **Private helpers** (`_`-prefixed) are not ranked symbols. When a bug fix or a gap touches one,
   name it inside the public caller's finding.

`test_status: covered` includes decorated routes a test client reaches by URL (`test_route_files`):
a FastAPI `@router.post("/webhook")` called as `client.post("/gmail/webhook")` is covered.

### Bug fixes without a regression test

From `leverage.json` `bugfix_commits`, take the commits with `touched_tests: false`. For each,
`git show -U0 <sha>` once and read the subject. Keep the ones whose fix changed runtime behaviour, and
map each hunk to the symbol whose `line`–`end_line` contains it: that symbol's gap finding gets the
`high` row of the severity table only when a behaviour-changing fix landed inside it, not merely in
its file.
`mention_only` rows list where the mention is (`test_mention_rows`).

Emit `smell_id: bug_fix_no_test` with **`coverage_gap_lines: 0`**: a commit is not a measurable
line count, and the headline never includes it (problem 22). It carries no `priority_score`; order
these newest first, after the gap findings. Cap at 10, separate from the 30-finding cap for gaps. Title the section with the window the
manifest states ("last 200 commits, then fix subjects").

## Report mode (Coverage mode = report — only when `--coverage` opted in)

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

**Restrict findings to the priority set** — the top 50 files by `leverage.json` `priority` — so the
headline stays about critical code (problem 8). Report the whole report's uncovered total
separately in the addendum as `report_total_uncovered_lines`. Do **not** mix heuristic gaps in
report mode; that double-counts.

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
  "coverage_gap_lines": <int — the symbols' gap_lines; 0 for bug_fix_no_test / install_hint>,
  "deletable_lines": 0,
  "test_status": "untested" | "mock_only" | "name_only" | "mention_only",
  "priority_score": <the symbol's priority, verbatim>,
  "priority_factors": { "security_lines": <int>, "churn": <int>, "fan_in": <int>, "entry_point": <bool> },
  "respects_documented_decision": true | false,
  "recommended_action": "<prose>",
  "smell_id": null | "bug_fix_no_test" | "install_hint"
}
```

### Severity — from blast radius, not from the score

**`priority_score` ranks; it does not grade.** It is a *relative* measure, so order findings by it,
but never map it to severity through absolute thresholds: on a small repo every file scores
0.05–0.5, and a literal mapping labels *everything* low.

Set `severity` from what breaks, using the first row that matches:

| Severity | The code is… |
|----------|--------------|
| `high` | On an auth/credential/payment/signature path (a request verifier, a webhook signature check, a session or token check); **or** carries a `bug_fix_no_test` finding whose fix changed runtime behaviour (a lock, a timeout, a retry, a state transition, a swallowed exception); **or** is the single largest untested unit in the repo by a wide margin |
| `medium` | Reachable from an entry point that runs on every invocation (a route, middleware, a hook, a CLI dispatcher); **or** has real churn and no test importer at all |
| `low` | A leaf utility, a one-off script, or a path you could not confirm is even reachable |

Always emit `priority_score` and `priority_factors` verbatim — they are the audit trail for the
ranking. When the score and the table disagree, the table wins and the finding says so in one clause.

Effort estimate from gap size:
- `coverage_gap_lines <= 20` → trivial
- `coverage_gap_lines <= 60` → small
- `coverage_gap_lines <= 200` → medium
- else → large

## Hard rules

- **`coverage_gap_lines >= 1` on every gap finding**, taken from `gap_lines`, never estimated.
  `bug_fix_no_test` and `install_hint` carry 0 and stay out of the headline.
- **`respects_documented_decision: false` means a *document* states an intent the finding contradicts** (for example "we don't unit-test thin controllers"). A known gap, a history note, or the inferred posture never makes a finding `false`.
- **Order by severity, then `priority_score × certainty` descending** (SKILL.md's shared block defines the weights). Cap at 30.
- **`respects_documented_decision` defaults to `true`.**
- **Scope is computed by the orchestrator, not by you.** Scan exactly the file list in your task prompt. Its exclusions are owned by the arch skill's `references/scan-exclusions.md`. **Never widen your own scope.**
- Never run the test suite, a coverage tool or the scripts yourself. Never write inside the scanned repo.

## Final output addendum

```
coverage_gap_total: <sum of gap findings' coverage_gap_lines, each source line once>
files_affected: <distinct source files with gap findings>
symbols_ranked: <int — symbols with gap_lines > 0 in references.json>
symbols_read: <int — candidate symbols you opened>
entry_wrappers_skipped: <int>
suppressed: [<{location, smell_or_signal, reason} for candidates read and dropped>]
status_counts: <references.json status_counts, verbatim>
report_mode: heuristic | report
report_path_consumed: <path or null>
report_total_uncovered_lines: <report mode only>
coverage_negatives: [<per SKILL.md Step 4 — e.g. bug_fix_no_test clean/unavailable>]
coverage_partial: [<the manifest's entries for import_graph / reference_index, plus your own>]
RUN NOTES: [<every script row you disagreed with: row, what you read, why>]
```

These power the report's headline and footer disclosure.
