# Scan: Economics (suite-level cost vs value, and the reduction lane)

Loaded by the orchestrator and passed to the `test-economics` subagent. Detailed scanning instructions follow.

## Inputs you receive in your task prompt

- `Detected stack` — language(s)
- `Test framework` — jest / vitest / pytest / cargo test / go test / etc.
- `Tier` — full | bounded | sample
- `Source scope` — source paths (for ratio calculation)
- `Test scope` — test paths (for snapshot/flakiness scans)
- `Script manifest` — path to `manifest.json` from `scripts/run.py` (SKILL.md Step 3.5)
- `Testing-Intent Summary` — 3-5 bullets

## The scripts decide; you judge

A test suite that only grows is the failure this lane exists for (S65: horowell's test/source LOC
went 0.06 → 0.91 in six months, with almost no parameterization, and maxitech kept a dead method
alive with five tests while its live replacement had none). The two reduction categories below come
entirely from script output. **Do not compute references, shapes or module attribution by hand.**
A row you disagree with goes in `RUN NOTES` with what you read.

## Category 1: Life support — `economic_signal: life_support`

`references.json` `life_support[]`: production symbols with **zero production references** (code
only; strings count as possible dynamic use and exclude a symbol) that tests still call. Framework
exports (Next.js `default`/`GET`/`metadata` in an entry file), decorated Python functions and
`_`-prefixed seams are already excluded.

The entry's `deletable_lines` already applies the rules below; use it. Override it only with a
reason from reading, keep the script's value in `metrics.script_deletable_lines`, and say why in
`RUN NOTES`.

For each entry:
1. **Verify by reading.** Open the symbol and search the repo for its name once, including
   non-code callers the index cannot see: a config file, a job registry, a CLI table, a docs page that
   says it is public API. Any live production caller drops the finding.
2. **Test-support use** (`used_as_test_helper_in` non-empty): another module's test imports it as a
   helper (a guard test using `scripts/lib/record.ts`). It is test-support code living in the
   production tree, not dead code: `deletable_lines` 0, action "move it to a test-support file", and
   certainty 0.4.
3. **With a `successor`**, by `successor_kind` (strongest first):
   - `caller_switched` — a commit replaced the last production call with the successor. Read the
     successor's call site in that commit's file to confirm it does the symbol's job. Action:
     **"move these tests to `<successor>`, then delete the symbol"**. Only the symbol is deletable;
     the moved tests survive.
   - `doc_comment` — the symbol's own comment names the successor. Often a **reference twin**: a
     JS predicate kept as the executable spec of a live SQL twin. If the successor is untested, its
     tests are the rule's only spec: the action is "test the successor, then delete", certainty 0.5.
   - `wrapper` — the symbol is a thin wrapper over a live function, so its tests exercise live code.
     Action: "re-point the tests at the live function, then delete the wrapper". Never delete them.
   - `stem` — shared name stem only. The weakest signal: read the candidate and confirm it replaces
     the symbol. A wrong successor (a sibling like `listResolved…` for `listOpen…`) is replaced by the
     right one you found, or removed; say which in `RUN NOTES`.
   Say whether the successor is untested (`successor_status`); if so, the finding also closes a
   coverage gap. A twin the script missed (the symbol's own comment names one that is not an exported
   symbol) is applied as `doc_comment` by you; say so in `RUN NOTES`.
4. **Without a successor**: the symbol plus its `exclusive_rows` (tests that call nothing else under
   test) are deletable. Non-exclusive rows lose only their calls to the symbol; say how many.
5. Severity: medium. Certainty: 0.8 after reading; 0.6 when `prod_import_refs > 0` (imported
   somewhere but never used, which deserves a second look).
6. Whole-file deletion is never this lane's: a file whose every symbol is life support routes to
   `/bx:clean`.

## Category 2: Consolidate — `economic_signal: consolidate`

`consolidate.json` `clusters[]`: groups of ≥2 tests whose literal-stripped shapes match (Jaccard ≥ the
manifest's threshold) with matching setup, each saving ≥4 lines when merged into one table test. This
is the catalog's T05, reported here once.

Tests of a life-support symbol are never cluster members: that lane moves or deletes them.

For each cluster, largest `saved_lines` first:
1. Read the first two member bodies in full (all members of a `mechanical` cluster). Confirm they
   differ only in literals (inputs and expected values) and that every member's case survives as a
   row. A cluster whose members assert different things (`toHaveLength(1)` vs `toEqual([])`) is
   still mergeable only if the table gets an "expected" column; say which. Certainty 0.8 when the
   members you read differ only in literals, 0.6 otherwise. A `mechanical` cluster whose members
   carry long per-case rationale comments or different setup you can see is routed to `--plan`
   anyway; say so.
2. `deletable_lines`: **0**. `consolidate_tests_before` = `tests_before`,
   `consolidate_tests_after` = 1, `consolidate_saved_lines` = `saved_lines`.
3. `mechanical: true` clusters are `--fix`-eligible (pure table rewrite); everything else routes to
   `--plan`. Copy `mechanical` and the cluster `id` into the finding.
4. Severity: low. Effort: trivial for mechanical clusters, else small.
5. Select the 15 clusters with the largest `saved_lines` (fewer if the cap leaves fewer slots), then
   order them by the ordering key. Report them as findings. Report the cluster totals for **all** clusters in the
   addendum: the headline uses the full totals, not the 15.

## Category 3: Snapshot-heavy tests — `economic_signal: snapshot_heavy`

**Step 1: Find snapshot files.**
- Jest/vitest: `__snapshots__/**/*.snap`
- inline: rows in `test_bodies.jsonl` with `assertions.snapshot > 0` (embedded in the test file)
- pytest-snapshot: `__snapshots__/**.ambr` / `**.json`
- insta (Rust): `*.snap` files under `tests/snapshots/`

**Step 2: Pair each snapshot with its test file.** Convention: `__snapshots__/Foo.test.ts.snap` ↔ `Foo.test.ts`.

**Step 3: Compute the ratio.** `snapshot_ratio = snapshot_line_count / (snapshot_line_count + test_line_count)`, using `wc -l`.

**Step 4: Flag** when `snapshot_ratio >= 0.5` AND `snapshot_line_count >= 50`. No snapshot files and no snapshot assertions anywhere is `unavailable` (the mechanism is unused), even when the framework supports snapshots.

**Step 5: Estimate deletable_lines.** `deletable_lines = snapshot_line_count - 15` (reserving three
converted assertions). Floor at 0; cap at `snapshot_line_count`.

## Category 4: Flakiness signals

**Sub-scan A — Retry/flake markers in test code** (grep the test scope):
- JS/TS: `it.retry(`, `test.retry(`, `{ retry: N }` options, `it.skip(...)` with a comment containing `flaky`
- Python: `@pytest.mark.flaky`, `@flaky`, `@retry`
- Rust: `#[ignore]` with a comment containing `flaky`
- Java: `@Flaky`, `@RetryingTest`, `@Retry`
- Go: comments matching `(?i)//\s*flaky` immediately above `func Test*`

Each match: `economic_signal: "flakiness_marker"`, `deletable_lines: 0`, severity medium.

**Sub-scan B — Git-log flake history:** `leverage.json` `flake_commits[]`. The script matches the
word-bounded vocabulary (`flaky`, `flake`, `deflake`, `intermittent`, `non-deterministic`) **and**
requires the commit to name a test or touch a test file, so "Snowflake" never matches (problem 19).
Read each subject. Test files appearing in ≥2 real flake-fix commits: `economic_signal:
"flakiness_history"`, severity high, `deletable_lines: 0`, up to 5 example commits.

## Category 5: Test:code ratio extremes — `ratio_over` / `ratio_under`

`references.json` `modules.rows[]`: per module, `code_loc`, `test_loc`, `test_files`, `ratio`. Each test
file counts toward the module whose symbols its tests call most, else the one it imports most — call
and import evidence, not path stems, so flat `tests/` and root layouts attribute correctly (problem 7). `unattributed_test_loc`
is test code that imports nothing local (usually e2e); report it, never assign it.

Compare `ratio` exactly as given (three decimals), never rounded further.

- `ratio > 3.0` → `ratio_over`. Severity low, certainty 0.75. Read the module's largest test file
  first: tests that import a module only to build fixtures inflate its ratio. Say so and lower
  certainty to 0.5 when that is what you see.
- `ratio < 0.1` AND `code_loc > 100` → `ratio_under`. Severity medium, **certainty 0.55 cap** (the
  orchestrator prefers coverage's findings for the same module).
- E2E modules and property-based suites: suppress `ratio_over` / lower certainty to 0.4.

## Growth trend (footer, never a finding)

Copy `leverage.json` `growth[]` into the addendum as `growth_trend` (date, test_loc, source_loc,
ratio, test_case_lines). The report prints it as one footer line. A shorter history shows up in
the manifest's `coverage_partial` as `growth_trend`.

## Per-finding output shape

```
{
  "dimension": "economics",
  "economic_signal": "life_support" | "consolidate" | "snapshot_heavy" | "flakiness_marker" | "flakiness_history" | "ratio_over" | "ratio_under",
  "location": "<file:lines, or module path>",
  "title": "<one-line>",
  "severity": "low" | "medium" | "high",
  "certainty": 0.0-1.0,
  "effort_estimate": "trivial" | "small" | "medium" | "large",
  "coverage_gap_lines": 0,
  "deletable_lines": <int — > 0 only for snapshot_heavy and life_support>,
  "respects_documented_decision": true | false,
  "recommended_action": "<prose>",
  "metrics": { ... per-signal ... }
}
```

`metrics` per signal:
- `life_support`: `{ "symbol": str, "symbol_lines": int, "test_rows": [..], "exclusive_rows": int, "successor": str|null, "successor_status": str|null, "successor_evidence": str|null }`
- `consolidate`: `{ "cluster_id": str, "tests_before": int, "tests_after": 1, "cases_after": int, "saved_lines": int, "jaccard_min": float, "mechanical": bool, "rows": [..] }`
- `snapshot_heavy`: `{ "snapshot_line_count": int, "test_line_count": int, "snapshot_ratio": float, "snapshot_path": str }`
- `flakiness_marker`: `{ "marker_kind": str, "count_in_file": int }`
- `flakiness_history`: `{ "flake_fix_commits": [{"hash": str, "subject": str}], "total_flake_fix_commits": int }`
- `ratio_over` / `ratio_under`: `{ "module": str, "code_loc": int, "test_loc": int, "test_files": int, "ratio": float }`

## Hard rules

- **`deletable_lines >= 1` ONLY for `snapshot_heavy` and `life_support`.** Consolidate saves lines but deletes no case; it has its own headline.
- **Honor `respects_documented_decision`.** `false` means a *document* states an intent the finding contradicts; a known gap or the inferred posture never makes a finding `false`.
- **Scope is computed by the orchestrator, not by you.** Scan exactly the file list in your task prompt. Its exclusions are owned by the arch skill's `references/scan-exclusions.md`. **Never widen your own scope.**
- **Cap output at 30 findings.** Life support first (all of it), then flakiness and snapshot findings, then ratio findings, then consolidate clusters to fill the remainder (at most 15). Within a signal, order by severity, then `certainty × (1 + log10(deletable_lines + saved_lines + 1))` desc. Cut findings follow SKILL.md's finding-cap rule.
- **`respects_documented_decision` defaults to `true`.**
- **Don't double up:** `test-coverage` owns under-tested files (the orchestrator drops a `ratio_under` that overlaps), `test-quality` owns per-test smells, `/bx:clean` owns orphaned snapshots, orphaned test files and unused test helpers. `/bx:clean` reports test-only production symbols as "see `/bx:tests` life_support" and never as dead code, so this lane is their only owner.
- Never run the tests or the scripts. Never write inside the scanned repo.

## Final output addendum

```
life_support_count: <int>
life_support_deletable_lines: <sum>
consolidate_clusters: <consolidate.json totals.clusters — all clusters, not only the 15 reported>
consolidate_tests_before: <totals.tests_before>
consolidate_tests_after: <totals.tests_after>
consolidate_saved_lines: <totals.saved_lines>
consolidate_mechanical: <totals.mechanical_clusters>
snapshot_findings_count: <int>
snapshot_deletable_lines: <sum across snapshot_heavy findings>
flakiness_findings_count: <int>
ratio_findings_count: <int>
total_deletable_lines: <snapshot_deletable_lines + life_support_deletable_lines>
files_affected: <distinct source and test files with deletable findings>
suppressed: [<{location, signal, reason} for entries read and dropped>]
growth_trend: [<leverage.json growth rows>]
coverage_negatives: [<one entry per category with a 0 count: life_support, consolidate, snapshot_heavy, flakiness_marker, flakiness_history, ratio_over, ratio_under>]
coverage_partial: [<the manifest's leverage/references/consolidate entries, plus your own>]
RUN NOTES: [<every script row you disagreed with>]
```

A count of 0 reads as "clean" to anyone skimming the addendum. **Every category with a 0 count
needs a matching `coverage_negatives` entry**, so that "unavailable" (no snapshot mechanism at all)
cannot be mistaken for "clean".
