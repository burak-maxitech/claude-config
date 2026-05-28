# Scan: Economics (suite-level cost vs value)

Loaded by the orchestrator and passed to the `test-economics` subagent. Detailed scanning instructions follow.

## Inputs you receive in your task prompt

- `Detected stack` — language(s)
- `Test framework` — jest / vitest / pytest / cargo test / go test / etc.
- `Tier` — full | bounded | sample
- `Source scope` — source paths (for ratio calculation)
- `Test scope` — test paths (for snapshot/flakiness scans)
- `Testing-Intent Summary` — 3-5 bullets

## Approach

Three independent scan categories. Each emits its own findings.

### Category 1: Snapshot-heavy tests

**Step 1: Find snapshot files.**
- Jest/vitest: `__snapshots__/**/*.snap`
- jest inline: `.test.ts` files with `toMatchInlineSnapshot(...)` (snapshot embedded in source)
- pytest-snapshot: `__snapshots__/**.ambr` / `**.json`
- insta (Rust): `*.snap` files under `tests/snapshots/`

**Step 2: Pair each snapshot with its test file.** Convention: `__snapshots__/Foo.test.ts.snap` ↔ `Foo.test.ts`.

**Step 3: Compute the ratio.**
- `snapshot_line_count` = LOC of the .snap file (use `wc -l` via Bash, or count lines via Read).
- `test_line_count` = LOC of the test file.
- For inline snapshots: count snapshot string literal lines within the test file, subtract from `test_line_count`.
- `snapshot_ratio = snapshot_line_count / (snapshot_line_count + test_line_count)`.

**Step 4: Flag** when `snapshot_ratio >= 0.5` AND `snapshot_line_count >= 50` (low absolute threshold avoids flagging tiny test files with 5-line snapshots).

**Step 5: Estimate deletable_lines.** Reserve 5 lines per converted assertion × 3 top assertions per file (15 lines). `deletable_lines = snapshot_line_count - 15`. Floor at 0; cap at `snapshot_line_count`.

### Category 2: Flakiness signals

**Sub-scan A — Retry/flake markers in test code:**
- JS/TS: `it.retry(`, `test.retry(`, `vi.retry(`, `it.skip.if(`, plus `it.skip(...)` immediately preceded or annotated by a comment containing `flaky` (case-insensitive)
- Python: `@pytest.mark.flaky`, `@flaky`, `@retry` (from flaky lib or tenacity-test)
- Rust: `#[ignore]` with surrounding comment containing `flaky`, custom `#[flaky]` proc-macros if seen
- Java: `@Flaky`, `@RetryingTest`, `@Retry`
- Go: comments matching `(?i)//\s*flaky` immediately above `func Test*`

Each match surfaces a finding with:
- `economic_signal: "flakiness_marker"`
- `deletable_lines: 0` (fix the test, don't delete)
- Severity: medium
- `recommended_action`: investigate root cause; remove retry decorator once stable

**Sub-scan B — Git-log flake history:**

```
git log --since='1 year ago' --pretty='%H|%s' --regexp-ignore-case \
  --grep='flaky' --grep='flake' --grep='intermittent' --grep='unreliable test' --grep='retry test'
```

For each commit hash, `git show --stat --name-only <hash>` (one call per commit) and record test files touched. Files appearing in ≥2 flake-fix commits surface as `economic_signal: "flakiness_history"`, severity high (this is a chronic-pain signal), `deletable_lines: 0`. `metrics.flake_fix_commits` lists up to 5 example commits with hash + subject.

### Category 3: Test:code LOC ratio extremes

**Step 1: Group files by module.** "Module" definition:
- Monorepo: each workspace root is a module.
- Else: each top-level directory under `src/` (or repo root if no `src/`) is a module. Cap depth at 1.
- Tests are grouped to the same module via path stem matching (`tests/auth/` matches `src/auth/`; `__tests__/` siblings match the parent dir).

**Step 2: Compute per-module totals.**
- `module_code_lines`: sum of LOC of source files in module (exclude tests).
- `module_test_lines`: sum of LOC of test files in module.
- `ratio = module_test_lines / max(module_code_lines, 1)`.

**Step 3: Flag extremes.**
- `ratio > 3.0` → `economic_signal: "ratio_over"`. Severity: low. Certainty: 0.75. `deletable_lines: 0` (we can't honestly attribute deletable lines without per-test inspection — `test-quality` owns that).
- `ratio < 0.1` AND `module_code_lines > 100` → `economic_signal: "ratio_under"`. Severity: medium. **Certainty: 0.55 cap** (the orchestrator's deduplicator favors test-coverage's file-level findings; this is a secondary signal). `deletable_lines: 0`.

## Per-finding output shape

```
{
  "dimension": "economics",
  "economic_signal": "snapshot_heavy" | "flakiness_marker" | "flakiness_history" | "ratio_over" | "ratio_under",
  "location": "<file or module path>",
  "title": "<one-line>",
  "severity": "low" | "medium" | "high",
  "certainty": 0.0-1.0,
  "effort_estimate": "trivial" | "small" | "medium" | "large",
  "coverage_gap_lines": 0,
  "deletable_lines": <int — only > 0 for snapshot_heavy>,
  "respects_documented_decision": true | false,
  "recommended_action": "<prose>",
  "metrics": { ... per-signal ... }
}
```

`metrics` per signal:
- `snapshot_heavy`: `{ "snapshot_line_count": int, "test_line_count": int, "snapshot_ratio": float, "snapshot_path": str }`
- `flakiness_marker`: `{ "marker_kind": str, "count_in_file": int }`
- `flakiness_history`: `{ "flake_fix_commits": [{"hash": str, "subject": str}], "total_flake_fix_commits": int }`
- `ratio_over` / `ratio_under`: `{ "module": str, "module_code_lines": int, "module_test_lines": int, "ratio": float }`

## Hard rules

- **`deletable_lines >= 1` ONLY for `economic_signal == "snapshot_heavy"`.** Other signals always report 0 — the twin-headline math depends on this.
- **Honor `respects_documented_decision`.** Snapshots in paths the intent summary marks as "visual-regression boundary" (e.g. `components/`) → mark `respects_documented_decision: false`.
- **Skip vendored/generated/build dirs**: `node_modules`, `venv`, `.git`, `dist`, `build`, `__pycache__`, `.next`, `.cache`, `vendor`, `target/`, `coverage/`, `__generated__/`.
- **Cap output at 25 findings**, ordered by `severity_weight × certainty × (1 + log10(deletable_lines + 1))` desc.

## False-positive guards

- **Small-snapshot files**: skip when the snapshot file has fewer than 50 lines total. Tiny snapshots aren't a cost.
- **Property tests / generators**: scopes using `fast-check`, `hypothesis`, `proptest`, `quickcheck` have legitimately higher LOC. Detect these from imports/deps and lower certainty for `ratio_over` to 0.4 in those modules.
- **E2E modules**: detect by directory naming (`e2e/`, `playwright/`, `cypress/`, `acceptance/`) and dep presence; suppress `ratio_over` for these.
- **Modules dominated by config**: when `module_code_lines` includes large config dumps (TS interface dumps, schema files), the ratio is misleading. Skip files matching `*.config.*`, `*schema.*`, `*types.ts` from `module_code_lines` calculation.

## Don't double up

- **`test-coverage` owns "module is under-tested at file level".** When `ratio_under` and a `test-coverage` finding point at the same module, the orchestrator drops yours. That's expected — keep the finding but accept the dedup.
- **`test-quality` owns per-test smells.** You scan suite/module/file scale — never reach into individual test bodies.
- **`/bx-clean`'s `cleanup-styles-tests` owns orphaned snapshots** (snap exists, test deleted). Only flag snapshots where the test still exists.

## Final output addendum

```
snapshot_findings_count: <int>
snapshot_deletable_lines: <sum across snapshot_heavy findings>
flakiness_findings_count: <int>
ratio_findings_count: <int>
total_deletable_lines: <same as snapshot_deletable_lines — economics only contributes via snapshots>
files_affected: <distinct test files with snapshot_heavy>
```
