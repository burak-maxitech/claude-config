---
name: tests
description: 'Repo-wide test suite audit. Surfaces missing coverage on critical code paths, wasteful tests, tests keeping dead code alive, and tests that should be one table test, in a single report. Triple headline ("Coverage gaps in critical code: X lines | Tests we can delete: Y lines | Tests we can consolidate: N → M"). Committed scripts measure; three parallel Sonnet subagents (test-coverage / test-quality / test-economics) judge.'
when_to_use: When user mentions test coverage audit, test smell detection, test debt at the repo level, "are our tests any good", "what tests can we delete", or "what's untested that matters". Different from `/bx:review` §7 (diff-scoped checkbox) and `/bx:clean`'s `cleanup-styles-tests` (artifact-level cruft only).
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Edit, Bash(git:*), Bash(find:*), Bash(wc:*), Bash(sort:*), Bash(uniq:*), Bash(jq:*), Bash(npx:*), Bash(npm:*), Bash(yarn:*), Bash(pnpm:*), Bash(python:*), Bash(python3:*), Bash(cargo:*), Bash(go:*), Bash(pytest:*), Bash(cat:*), Bash(head:*), Agent
effort: high
argument-hint: "[path] [--plan] [--fix] [--coverage] [--full-scan]"
---

# Test Review — Repo-Wide Test Suite Audit

Audit this codebase's test suite like a staff engineer doing a quarterly test-health check. Surface missing coverage on critical paths in one direction; surface wasteful, redundant, and untrustworthy tests in the other — and give the suite a way to **shrink**: tests that keep dead production code alive, and groups of tests that should be one table test. Report a **triple headline** so gaps, deletions and consolidation are equally visible.

**Scripts measure, scanners judge.** Everything that decides a deletion or a headline number comes from the committed scripts in `scripts/` (Step 3.5), not from a scanner's grep: prose rules did not converge across reruns (S64, S65), and run-to-run variance on one smell went 5 → 1 between identical runs.

This skill is distinct from existing test-touching paths in this repo:

- **`/bx:review` §7 testing** — a 4-bullet diff-scoped checkbox during diff review (or built-in `/code-review` for the lightweight pass)
- **`/bx:clean`'s `cleanup-styles-tests` §7** — artifact-level cruft only (orphaned files, >3mo skips, unused helpers, stale snapshots)
- **`/bx:arch`** — code structure, not test suite
- **`/bx:tests` (this)** — *repo-wide test suite health*, both directions (coverage + cost)

`/bx:tests` **defers entirely** to `cleanup-styles-tests` for orphans, long-stale skips, unused helpers, and stale snapshots. If the user reports the cleanup categories, point them at `/bx:clean`. Bidirectional pointers in the report footer cross-reference.

---

## Step 0 — Detect Project Context

Mirror `/bx:arch` Step 0. Gather stack, test framework, coverage-tool availability, workspaces, and repo size before any heavy work.

**Exclude fixture trees from detection FIRST.** Read `../arch/references/scan-exclusions.md`
(resolve against **this skill's base directory**) and apply it before reading any manifest. A
fixture tree carries its own `package.json` / `requirements.txt`, and resolving the stack from one
makes the whole run audit fabricated code — the eval fixtures under `evals/fixtures/` hold
*deliberately* planted dead tests and unused exports, so every finding would be false by
construction while the run looked successful. **If the only manifest in the repo sits inside an
excluded tree, the correct conclusion is "no stack detected", not that fixture's stack.**

**Stack + test-framework auto-detect** (read each *outside the excluded trees*, skip silently if missing):

| Stack signal | Test framework hints | Coverage tool |
|---|---|---|
| `package.json` | `jest` / `vitest` / `mocha` / `ava` / `playwright` in deps | `jest --coverage` / `vitest run --coverage` / `c8` / `nyc` |
| `pyproject.toml` / `requirements*.txt` / `Pipfile` | `pytest` / `unittest` (stdlib) | `pytest-cov` / `coverage.py` |
| `Cargo.toml` | `cargo test` (built-in) | `cargo tarpaulin` / `cargo llvm-cov` |
| `go.mod` | `go test` (built-in) | `go test -coverprofile` |
| `composer.json` | `phpunit` / `pest` | `phpunit --coverage` (Xdebug/PCOV) |
| `Gemfile` | `rspec` / `minitest` | `simplecov` |
| `pom.xml` / `build.gradle` | JUnit | JaCoCo |
| `tests/*.sh`, `test-*.sh`, `*.bats` | hand-rolled shell harness / `bats` | none — heuristic only |
| `tests/*.ps1`, `test-*.ps1`, `*.Tests.ps1` | hand-rolled PowerShell harness / Pester | none — heuristic only |

**Shell and PowerShell harnesses count as a test framework.** A suite of scripts with a `pass`/`fail`
discipline (or `exit 1` on failure) is a real suite even with no runner in a manifest — it has
assertions, it gates commits, and its coverage and quality are auditable. Detect by finding
executable test-named scripts that define or call a pass/fail helper. Coverage tooling is `none`, so
these run heuristic-only; `--coverage` reports "no coverage tool for a shell harness" rather than
failing. Do not exit as "no framework detected" when a repo's suite is shell-based.

For monorepos, check `workspaces` (npm/yarn/pnpm), `pnpm-workspace.yaml`, `[workspace] members = [...]` (Cargo), `go.work`. Each workspace may have its own framework. **A monorepo runs Step 3.5 and Step 4 once per workspace** (one script run and one scanner trio each, with that workspace's scope and framework), and Step 5 aggregates the trios: findings are concatenated, headline totals are summed, and each workspace's negatives and partials keep a `workspace` field. A workspace with no test framework is reported in the footer, not scanned.

**Test command** — record the project's own command for running the suite, and for running a
single file. Take it from `package.json` `scripts.test` (vitest: `npx vitest run <file>`; jest:
`npx jest <file>`), from `pytest` (`pytest <file>`), `cargo test`, `go test ./<pkg>`, or the shell
harness's runner, and a way to read the case count it reports (vitest/jest summary line, pytest's
`N passed`). Report it in the detection line. Only `--fix` runs it (baseline, then once per
applied item, for the count check). Report-only and `--plan` runs never execute tests.

**Coverage-tool availability** — record whether the tool appears in deps/devDependencies, the lockfile, or tool config (e.g. a `coverage` script, `pytest-cov` in requirements). Deps detection only — don't probe `$PATH` (not cross-platform, needs no extra permission). **Do NOT run it.** Default mode is heuristic-only; running coverage is opt-in via `--coverage`.

**Repo size tier** (`git ls-files | wc -l` for source + test files):

| Files | Tier | Behavior |
|---|---|---|
| <100 | full | Subagents read every file in scope |
| 100-500 | bounded | Read all, cap deep-reads |
| >500 | sample | Smart sampling (see the sibling arch skill's `scale-strategy.md` — resolve as `../arch/references/scale-strategy.md` relative to this skill's base directory) |

Override with `--full-scan`.

**Tell the user what you detected in one line**, e.g.:

> Detected: TypeScript/Jest project, 87 source files, 64 test files, vitest available. Tier: full. Mode: heuristic (use `--coverage` for report-based coverage gap analysis).

If **no test framework detected at all** — no manifest outside the excluded trees, AND no shell or
PowerShell harness — output:
> No test framework detected. /bx:tests needs one of: jest/vitest/pytest/cargo test/go test/phpunit/rspec/junit, or a shell/PowerShell test harness (`tests/*.sh`, `test-*.ps1`). Exiting.

Then stop the skill cleanly — do not dispatch subagents.

**Say which trees were excluded when you exit this way.** "No framework detected" on a repo that
visibly contains a `package.json` reads as a bug unless the message names the exclusion that
suppressed it — e.g. "the only manifests found were inside `evals/fixtures/`, which is excluded as a
planted-fixture tree."

---

## Step 1 — Read Intended Testing Posture

**Guardrail against imposing an opinion.** Before subagents evaluate anything, summarize what *this* project's testing approach is supposed to look like.

Read in parallel (single turn, multiple Read calls):

- `CLAUDE.md` — usually has Testing/Conventions section
- `README.md` — testing instructions, framework rationale
- `tests/README*` / `test/README*` / `__tests__/README*` (Glob)
- `docs/testing/*.md` (Glob)
- `docs/decisions/*.md` and `ADR-*.md` filtered for `test|coverage|mock|fixture` (Glob + Grep)
- Coverage config: `jest.config.*`, `vitest.config.*`, `pyproject.toml [tool.coverage]`, `.coveragerc`, `codecov.yml`, `coverage.toml`

From these, write a 3-5 bullet **Testing-Intent Summary**:

- Test-pyramid posture (e.g. "unit-heavy" / "e2e-heavy" / "explicit no-unit policy for thin controllers")
- Framework conventions (e.g. "vitest + react-testing-library, no enzyme, no shallow rendering")
- Mocking policy (e.g. "real DB in integration tests — see Session 19 incident", or "msw for all HTTP")
- Snapshot policy (e.g. "snapshots for visual-regression only in `components/`")
- Coverage targets if any (e.g. "85% lines, no gate", or "no formal target")

If no testing docs exist, say so and infer from `package.json`/`pyproject.toml` deps — but flag in the report that findings are evaluated against an *inferred* testing posture.

**Pass this summary verbatim to all three subagents** in their task prompts. Subagents mark conflicting findings as `respects_documented_decision: false`; those surface in a separate report section.

---

## Step 2 — Mode Dispatch

Interpret `$ARGUMENTS`:

| Argument | Effect |
|----------|--------|
| (none) | Default review-only: produce report and stop |
| path (e.g. `src/auth/`, `tests/api/`) | Scope subagents to that path (filtering both source and test scope to match) |
| `--plan` | After report, transform top findings into a phased brief ready to hand off to `/bx:plan` (read `references/plan-mode-test.md`) |
| `--fix` | After report, apply the safe reductions — T01a deletions, successor-less life-support deletions, mechanical merges — with a per-item diff gate, on a feature branch, each verified by rerunning the suite with a count check (read `references/fix-mode-test.md`). |
| `--coverage` | Opt into reading coverage tool reports (jest `coverage-summary.json` / pytest `coverage.json` / etc.). Never auto-invoked. |
| `--full-scan` | Force `full` tier regardless of repo size |

`--plan` and `--fix` are mutually exclusive. If both supplied, error: "Pick one — `--plan` emits a brief, `--fix` applies edits."

For `--coverage`: detect whether a coverage report exists at the per-stack expected path. **Never run the coverage tool yourself** — that hits network/runtime and the user opted into reading, not generating.

Per-stack expected report paths (check first match per stack):

| Stack | Report path | Generator command (suggest in install_hint) |
|---|---|---|
| Jest | `coverage/coverage-summary.json` | `npx jest --coverage --coverageReporters=json-summary` |
| Vitest | `coverage/coverage-summary.json` (same shape) or `coverage/coverage-final.json` | `npx vitest run --coverage --coverage.reporter=json-summary` |
| pytest-cov | `coverage.json` | `pytest --cov=. --cov-report=json` |
| coverage.py | `.coverage.json` or `coverage.json` | `coverage run -m pytest && coverage json` |
| cargo-tarpaulin | `tarpaulin-report.json` | `cargo tarpaulin --out Json` |
| cargo-llvm-cov | `target/llvm-cov-target/llvm-cov.json` | `cargo llvm-cov --json --output-path target/llvm-cov-target/llvm-cov.json` |
| go test -cover | `coverage.out` (text profile, not JSON) | `go test -coverprofile=coverage.out ./...` |
| phpunit | `coverage/coverage.xml` (Clover) or `coverage.json` | `phpunit --coverage-clover=coverage/coverage.xml` |
| JaCoCo | `target/site/jacoco/jacoco.xml` (XML — agent parses) | `mvn test jacoco:report` |

If a report file exists at any expected path, pass it to `test-coverage` with `coverage_mode: report` and `coverage_report_path: <found-path>`. If none exist, the agent surfaces a single `install_hint` finding with the appropriate generator command and exits — do not silently fall back to heuristic mode (the user explicitly asked for report-based coverage).

If `--coverage` is **not** passed, default `coverage_mode: heuristic` and `coverage_report_path: null`. The test-coverage agent uses test-neighbor + symbol enumeration heuristics only.

---

## Step 3 — Scope Selection

- If a path argument was given, scope subagents to that path. **Both** source files (for `test-coverage`) and test files (for `test-quality` / `test-economics`) are scoped — e.g. path `src/auth/` includes source under `src/auth/` AND test files matching `tests/auth/*`, `__tests__/auth/*`, `src/auth/**/*.test.*`.
- Else apply the tier from Step 0:
  - `full` → all source + test files
  - `bounded` → read all but cap deep-reads
  - `sample` → read the sibling arch skill's scale strategy (`../arch/references/scale-strategy.md` relative to this skill's base directory) and apply smart sampling. For bx:tests specifically, weight test files by `import_fan_in` of the source they test, not just churn.

Apply `../arch/references/scan-exclusions.md` (resolved against this skill's base directory) when
computing scope, exactly as Step 0 applied it to detection. Compute file lists once and pass to all
subagents; agents never widen their own scope. Record excluded/sampled/skipped counts for the footer.

The tier limits what scanners **read in full**. It never limits the script sweep in Step 3.5, which
always covers the whole scope (problem 18: a sampled sweep reported a sample's zero as the repo's).

---

## Step 3.5 — Run the scripts

Write the two scope lists (repo-relative, one path per line) to a fresh directory under the OS temp
dir — never inside the repo — and run, once per workspace:

```
python -I <this skill's base directory>/scripts/run.py --repo <workspace root> --out <temp dir> \
    --test-files <temp dir>/tests.txt --source-files <temp dir>/sources.txt
```

`run.py` runs `test_bodies.py`, `leverage.py`, `references.py` and `consolidate.py` in that order
(stdlib Python, read-only, a few seconds on a 1,800-file repo) and writes `manifest.json` with each
output's path. Each script's docstring is its contract. A script that fails or runs out of time
becomes a `coverage_partial` entry in the manifest rather than an error, so the report discloses it.
Pass the manifest path to every scanner. **Scanners never run the scripts and never re-derive
their numbers**; a scanner that disagrees with a row says so in `RUN NOTES`. If `python` is not
available, stop and say so: without the scripts the run has no mechanism behind its numbers.

---

## Step 4 — Parallel Subagent Dispatch

Launch all three subagents in a single turn (three Agent tool calls in one message). Mirror `/bx:arch` Step 4.

For each subagent, **read its corresponding reference file** (it contains the detailed scan instructions) and pass the contents in the task prompt along with shared context.

### Shared context passed to all three subagents:

```
Detected stack: <from Step 0>
Test framework: <from Step 0>
Workspaces: <list or none>
Coverage mode: heuristic | report
Coverage report path: <path or null>
Tier: <full|bounded|sample>
Source scope: <paths>
Test scope: <paths>
Script manifest: <path to manifest.json from Step 3.5 — your numbers come from its files>

Testing-Intent Summary:
<3-5 bullets from Step 1>

Findings format: structured JSON-like blocks. Do NOT format a final report — return raw findings only.

Each finding includes (subset depending on dimension):
  dimension: coverage | quality | economics
  location: <path>:<line-range>
  title: <one-line>
  severity: low | medium | high
  certainty: 0.0–1.0
  effort_estimate: trivial | small | medium | large
  coverage_gap_lines: <int>   (mandatory for coverage gaps, from the scripts' gap_lines; 0 for
                               bug_fix_no_test and install_hint, which never enter the headline)
  deletable_lines: <int>      (mandatory aggregation field; only > 0 for T01a / life_support /
                               snapshot_heavy. consolidate saves lines but deletes no case: it
                               reports saved_lines in metrics instead)
  respects_documented_decision: true | false   (default true. false ONLY when a document — tests
                                                README, ADR, CLAUDE.md testing section — states an
                                                intent the finding contradicts; a known gap or the
                                                inferred posture is never a decision)
  recommended_action: <prose>
  smell_id: T01a | T01b | T02 | T03 | T04 | T06 | bug_fix_no_test | install_hint | null   (test-quality only requires this)
  economic_signal: life_support | consolidate | snapshot_heavy | flakiness_marker | flakiness_history | ratio_over | ratio_under   (test-economics only)

Alongside findings, ALWAYS return:
  coverage_negatives:   one entry per category you swept that produced nothing:
                        {category, state: unavailable | clean, evidence}
                          unavailable = the precondition does not exist here (no snapshot mechanism, no CI)
                          clean       = the category applies, was checked, and found nothing
  coverage_partial:     one entry per check that did not cover its whole scope:
                        {category, scanned, total, reason}   (a crash, a timeout, a sample, a layout
                                                              the method cannot handle)
A category goes in exactly one place: findings, a negative, or partial. If it was only partly
checked, it is partial, not unavailable or clean. A category with findings needs no negative.
A judgment sweep you could not read in full (T04, T06) is partial with scanned/total.
Findings cut by your output cap are counted in your addendum and listed in coverage_partial as
{category: "<smell or signal>_findings", scanned: <reported>, total: <found>, reason: "finding cap"}.
Candidates you read and dropped below a floor or by a guard go in your addendum's `suppressed:`
list ({location, smell_or_signal, reason}), not in RUN NOTES and not in negatives.
Never encode either as a finding. Never report clean for something you could not check.

Ordering: severity_weight {low: 1, medium: 2, high: 4}. Order your findings by severity first,
then by the ordering key your scan file names.

Sampling: the tier's deep-read cap limits files you READ IN FULL to verify candidates. It does not
limit the script sweeps, which already cover the whole scope.

Scripts: never run them, never write your own parser, never recompute a number the manifest's files
give you. If a row is wrong, say so in RUN NOTES (file:line, the row's value, what you read) and judge
the finding on what you read.
```

The block above is dispatched verbatim. It is the only place scanners learn about the two lists
below, so keep it in the code block.

**`coverage_negatives`** — a list, alongside the findings, of categories each subagent swept that
produced nothing. These are **not findings**: they never rank, never group, never
reach a headline. Without this channel a scanner told to "report honestly when a category is empty"
has nowhere to put that, so it encodes it as a `severity: low` finding with no action — which then
ranks and pollutes the report.

Each entry states one of **three** states, and the distinction is the whole point:

```
coverage_negatives:
  - category: "snapshot_heavy"
    state: unavailable          # the mechanism does not exist here at all
    evidence: "Searched repo for toMatchSnapshot() and __snapshots__/: 0 hits outside docs describing the check."
  - category: "flakiness_marker"
    state: clean                # the mechanism exists, was checked, found nothing
    evidence: "Grepped all 6 test files for retry/skip/flaky markers: none."
  - category: "flakiness_history"
    state: unavailable          # the signal cannot be produced here
    evidence: "No CI, so no flake-fix commits exist to mine. 2 git-log matches inspected, both false positives."
```

- **`unavailable`** — the precondition is absent (no snapshot mechanism, no CI, no mocking layer).
  Reporting this as "clean" is a lie of omission: it claims coverage the scan never had.
- **`clean`** — the category applies, was genuinely checked, and found nothing.
- Never report `clean` for something you could not check. A reader distinguishes a healthy suite
  from an unscanned one only if the scan says which.

**`coverage_partial`** is the same idea for a check that ran but did not finish. On a real run (S65)
the near-duplicate (T05) sweep crashed partway through. The only record was a note in the scanner's
own output, and the report would have shown "1 finding" as if the sweep were complete. A partial
check is reported with `scanned`/`total` and a reason. Its zero count must never read as clean.

### Agent 1: test-coverage
Read `references/scan-coverage.md`, then dispatch the `test-coverage` subagent with those instructions + shared context. Targets: untested, mock-only and mention-only symbols ranked by `references.json` priority; bug-fixes-without-regression-tests from the manifest's commit window. Heuristic by default; reads coverage report only in `--coverage` mode.

### Agent 2: test-quality
Read `references/scan-quality.md` AND `references/test-smell-catalog.md`, then dispatch the `test-quality` subagent with both + shared context. Catalog is mandatory context — every finding must cite a `smell_id` from T01a, T01b, T02, T03, T04, T06 (T05 is reported by economics as `consolidate`).

### Agent 3: test-economics
Read `references/scan-economics.md`, then dispatch the `test-economics` subagent with those instructions + shared context. Targets: the reduction lane (`life_support`, `consolidate`), snapshot-heavy files (≥50% threshold), flakiness signals (markers + git log), test:code ratio extremes, and the growth trend for the footer.

---

## Step 5 — Consolidate, Filter, Score

After all three subagents return:

1. **Certainty gate.** Drop findings with `certainty < 0.5` unless `severity = high` OR `deletable_lines >= 20` OR `coverage_gap_lines >= 50`. Big wins on either axis earn a pass through the filter so the user can review uncertain-but-impactful candidates.
2. **Deduplicate.**
   - `test-economics` `ratio_under` overlaps with `test-coverage` file-level gaps — when both point at the same module, drop the economics finding (it had certainty 0.55 by design).
   - Within `test-quality`, if a single test triggers both T02 and T03, keep the higher-severity one and append the other's evidence.
   - A `life_support` finding whose `successor` is also a coverage gap keeps both findings and
     cross-references them ("closing this gap is the life-support move"). Never sum the successor's
     gap into `deletable_total`.
   - A `consolidate` cluster that contains a T01a/T02/T03 test keeps both; the quality fix comes first.
3. **Honor `respects_documented_decision: false`.** Route those to a separate report section regardless of dimension.
4. **Rank score.** `severity_weight × certainty / effort_weight × (1 + log(impact + 1))` where:
   - severity {low: 1, medium: 2, high: 4}
   - effort {trivial: 1, small: 2, medium: 4, large: 8}
   - impact = `coverage_gap_lines + deletable_lines`
5. **Collect `coverage_negatives` and `coverage_partial`.** Gather every subagent's lists,
   deduplicate by category, and hand them to the report footer. These never enter ranking or the
   headline. If a subagent returned a negative encoded as a `severity: low` finding with an empty
   `recommended_action`, move it here rather than ranking it. If a subagent's addendum shows a 0
   count with no matching negative, or reports a crash or a truncated sweep only in prose, record it
   as `coverage_partial` with `reason: "not reported by scanner"`. Never treat it as clean.

6. **Triple-headline aggregation.**
   - `coverage_gap_total = sum(coverage_gap_lines)` across coverage gap findings, **counting each
     source line once**. A whole-file finding and a range finding inside that same file overlap — add
     the whole-file figure and drop the nested range from the sum, keeping both as separate findings.
     `bug_fix_no_test` and `install_hint` carry 0 and are never in the sum; they render in their own
     table. Distinct files affected = unique source paths.
   - `deletable_total = sum(deletable_lines)` across **only** these contributing finding types:
     `smell_id == T01a`, `economic_signal == life_support`, `economic_signal == snapshot_heavy`.
     Distinct files affected = unique paths.
   - **Never include T01b/T02/T03/T04/T06, consolidate or the other economics signals in
     `deletable_total`.** Those are rewrites or merges, not deletions.
   - `consolidate_total`: from the economics addendum, **all** clusters (not only the ones reported
     as findings): `consolidate_tests_before → consolidate_tests_after` tests, saving
     `consolidate_saved_lines` lines.
   - All totals are integer sums. The footer's subtotal check must match exactly. A mismatch is
     an arithmetic error to fix before rendering, never "rounding".
7. **Order** findings within each report section by rank score. The report template's sections
   (Coverage / Quality / Economics, then Documented-Decision Conflicts) are the only grouping. Any
   finding with `respects_documented_decision: false` renders in the conflicts section, not in its
   dimension.

---

## Step 6 — Output

Read `references/report-template.md` for exact formatting. The shape:

**Section 0 — Triple headline** (this is the *first* line of the report, before everything else):

> **Coverage gaps in critical code: X lines across Y files | Tests we can delete: Z lines across W files | Tests we can consolidate: N → M (saves S lines)**

Gaps, deletions and merges are equally visible, so a suite that only ever grows shows it.

**Sections 1-5** as in `references/report-template.md`:

1. Testing-Intent Summary echo + detected framework(s) + scope counts
2. Findings — three subsections (Coverage / Quality / Economics) ordered by rank score
3. Documented-Decision Conflicts (separate, "**Confirm intent before action:**")
4. Suggested Next Actions — skill chains (`/bx:clean` for orphans, `/code-review` or `/bx:review` for diff-scoped follow-up); copy-pasteable `/bx:plan <brief>` snippets for top 3 strategic rewrites
5. Footer disclosure — framework detected, coverage tool used (or "heuristic"), files scanned vs sampled vs skipped, T01a/T01b/T02/T03/T04/T06 hit counts, headline totals with the subtotal check, the growth trend line, the script manifest's step timings, coverage negatives and partial coverage

---

## Step 7 — Mode-Specific Tail

### If `--plan` in $ARGUMENTS:
Read `references/plan-mode-test.md` (the test-specific port of `/bx:arch`'s plan mode — the phase mapping lives there). Transform top findings into a phased brief. Each phase emits a self-contained `/bx:plan <brief>` payload the user can drop into another session.

### If `--fix` in $ARGUMENTS:
Read `references/fix-mode-test.md` and follow it exactly. It walks three kinds of item: **T01a**
no-op deletions, **successor-less `life_support`** deletions (the dead symbol plus the tests that
test only it), and **mechanical `consolidate`** merges (one table test with one row per original
test, built from the script's `merge_table`). T01b, successor moves, non-mechanical merges and
everything else route to `--plan`.

The flow, in summary (the reference is canonical):
1. Pre-flight: a feature branch and a clean tree, allowlist evidence present, and the project's test
   command run once as a green baseline. Any failure aborts.
2. Per item: show the change and the diff, wait for y / n / skip / abort, apply with `Edit`, then
   rerun the affected test files and apply the **count check**: a deletion drops the count by
   exactly the tests it removed; a merge leaves the count unchanged. A new failure or a count that
   moved the wrong way reverts that item.
3. Cascades: an emptied parent block gets a separate prompt. An emptied file is routed to
   `/bx:clean`, never deleted here.

If user invoked `--fix` and no eligible item surfaced, output:
> Nothing `--fix` can apply safely (no T01a, no successor-less life support with exclusive tests, no mechanical merge). The rest needs judgment — re-run with `--plan` for a phased brief.

End with the summary block from `references/fix-mode-test.md`.

---

## Step 8 — Closing

If running default mode, end with one line:
> Run `/bx:tests --plan` to convert top findings into a phased rewrite brief, or `/bx:tests --fix` on a branch for the suite-verified reductions (no-op tests, dead code kept alive by tests, mechanical merges). Run `/bx:clean` first if orphaned-test / stale-snapshot findings appeared above.

---

## Quick Reference

| Want... | Use... |
|---------|--------|
| Per-commit / diff test check | `/code-review` (quick) or `/bx:review` (thorough) |
| Dead test files, stale snapshots, >3mo skipped tests | `/bx:clean` |
| **Repo-wide test coverage + quality audit** | **`/bx:tests` (this)** |
| Plan a test-refactor effort | `/bx:tests --plan` |
| Shrink the suite (no-op tests, test-only dead code, mechanical merges), suite-verified, on a branch | `/bx:tests --fix` |
| Coverage report-based gap analysis | `/bx:tests --coverage` |
| Architecture-level health | `/bx:arch` |
| Not sure which to run | `/bx:health` |
