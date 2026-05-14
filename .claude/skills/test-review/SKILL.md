---
name: test-review
description: Repo-wide test suite audit. Surfaces missing coverage on critical code paths AND wasteful/redundant tests in a single report. Twin headline metric ("Coverage gaps in critical code: X lines | Tests we can delete: Y lines"). Three parallel Sonnet subagents (test-coverage / test-quality / test-economics). Use when user mentions test coverage audit, test smell detection, test debt at the repo level, "are our tests any good", "what tests can we delete", or "what's untested that matters". Different from /code-review §7 (diff-scoped checkbox) and /code-cleanup's cleanup-styles-tests (artifact-level cruft only).
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Edit, Bash(git:*), Bash(find:*), Bash(wc:*), Bash(jq:*), Bash(npx:*), Bash(npm:*), Bash(yarn:*), Bash(pnpm:*), Bash(python:*), Bash(python3:*), Bash(pytest:*), Bash(cargo:*), Bash(go:*), Bash(cat:*), Bash(head:*), Task
effort: high
argument-hint: "[path] [--plan] [--fix] [--coverage] [--full-scan]"
---

# Test Review — Repo-Wide Test Suite Audit

Audit this codebase's test suite like a staff engineer doing a quarterly test-health check. Surface missing coverage on critical paths in one direction; surface wasteful, redundant, and untrustworthy tests in the other. Report a **twin headline metric** so both gaps and over-investment are equally visible.

This skill is distinct from existing test-touching paths in this repo:

- **`/code-review` §7 testing** — a 4-bullet diff-scoped checkbox during diff review
- **`/code-cleanup`'s `cleanup-styles-tests` §7** — artifact-level cruft only (orphaned files, >3mo skips, unused helpers, stale snapshots)
- **`/architecture-review`** — code structure, not test suite
- **`/test-review` (this)** — *repo-wide test suite health*, both directions (coverage + cost)

`/test-review` **defers entirely** to `cleanup-styles-tests` for orphans, long-stale skips, unused helpers, and stale snapshots. If the user reports the cleanup categories, point them at `/code-cleanup`. Bidirectional pointers in the report footer cross-reference.

---

## Step 0 — Detect Project Context

Mirror `/architecture-review` Step 0. Gather stack, test framework, coverage-tool availability, workspaces, and repo size before any heavy work.

**Stack + test-framework auto-detect** (read each, skip silently if missing):

| Stack signal | Test framework hints | Coverage tool |
|---|---|---|
| `package.json` | `jest` / `vitest` / `mocha` / `ava` / `playwright` in deps | `jest --coverage` / `vitest run --coverage` / `c8` / `nyc` |
| `pyproject.toml` / `requirements*.txt` / `Pipfile` | `pytest` / `unittest` (stdlib) | `pytest-cov` / `coverage.py` |
| `Cargo.toml` | `cargo test` (built-in) | `cargo tarpaulin` / `cargo llvm-cov` |
| `go.mod` | `go test` (built-in) | `go test -coverprofile` |
| `composer.json` | `phpunit` / `pest` | `phpunit --coverage` (Xdebug/PCOV) |
| `Gemfile` | `rspec` / `minitest` | `simplecov` |
| `pom.xml` / `build.gradle` | JUnit | JaCoCo |

For monorepos, check `workspaces` (npm/yarn/pnpm), `pnpm-workspace.yaml`, `[workspace] members = [...]` (Cargo), `go.work`. Each workspace may have its own framework — handle per-workspace.

**Coverage-tool availability** — record whether the tool is on `$PATH` or in deps. **Do NOT run it yet.** Default mode is heuristic-only; running coverage is opt-in via `--coverage`.

**Repo size tier** (`git ls-files | wc -l` for source + test files):

| Files | Tier | Behavior |
|---|---|---|
| <100 | full | Subagents read every file in scope |
| 100-500 | bounded | Read all, cap deep-reads |
| >500 | sample | Smart sampling (see `architecture-review/references/scale-strategy.md`) |

Override with `--full-scan`.

**Tell the user what you detected in one line**, e.g.:

> Detected: TypeScript/Jest project, 87 source files, 64 test files, vitest available. Tier: full. Mode: heuristic (use `--coverage` for report-based coverage gap analysis).

If **no test framework detected at all**, output:
> No test framework detected. /test-review needs at least one of: jest/vitest/pytest/cargo test/go test/phpunit/rspec/junit. Exiting.

Then stop the skill cleanly — do not dispatch subagents.

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
| `--plan` | After report, transform top findings into a phased TaskCreate-ready brief (read `references/plan-mode-test.md`) |
| `--fix` | After report, apply T01 deletions with per-finding diff preview gate (read `references/fix-mode-test.md`). Restricted to T01 only. |
| `--coverage` | Opt into reading coverage tool reports (jest `coverage-summary.json` / pytest `coverage.json` / etc.). Never auto-invoked. |
| `--full-scan` | Force `full` tier regardless of repo size |

`--plan` and `--fix` are mutually exclusive. If both supplied, error: "Pick one — `--plan` emits a brief, `--fix` applies edits."

For `--coverage`: detect whether a coverage report exists at the expected path. If yes, pass path to `test-coverage` agent with `coverage_mode: report`. If no, the agent surfaces a single `install_hint` finding telling the user how to generate one (e.g. `npx jest --coverage --coverageReporters=json-summary`); do not run the coverage tool yourself.

---

## Step 3 — Scope Selection

- If a path argument was given, scope subagents to that path. **Both** source files (for `test-coverage`) and test files (for `test-quality` / `test-economics`) are scoped — e.g. path `src/auth/` includes source under `src/auth/` AND test files matching `tests/auth/*`, `__tests__/auth/*`, `src/auth/**/*.test.*`.
- Else apply the tier from Step 0:
  - `full` → all source + test files
  - `bounded` → read all but cap deep-reads
  - `sample` → read `architecture-review/references/scale-strategy.md` and apply smart sampling. For test-review specifically, weight test files by `import_fan_in` of the source they test, not just churn.

Compute file lists once and pass to all subagents.

---

## Step 4 — Parallel Subagent Dispatch

Launch all three Task subagents in a single turn (three Task tool calls in one message). Mirror `/architecture-review` Step 4.

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
  coverage_gap_lines: <int>   (mandatory for coverage; default 0 elsewhere)
  deletable_lines: <int>      (mandatory aggregation field; only > 0 for T01 / confirmed-T05 / snapshot_heavy)
  respects_documented_decision: true | false
  recommended_action: <prose>
  smell_id: T01..T05 | bug_fix_no_test | install_hint | null   (test-quality only requires this)
  economic_signal: snapshot_heavy | flakiness_marker | flakiness_history | ratio_over | ratio_under   (test-economics only)
```

### Agent 1: test-coverage
Read `references/scan-coverage.md`, then dispatch the `test-coverage` subagent with those instructions + shared context. Targets: missing tests on critical-rank source files; bug-fixes-without-regression-tests in last 50 commits. Heuristic by default; reads coverage report only in `--coverage` mode.

### Agent 2: test-quality
Read `references/scan-quality.md` AND `references/test-smell-catalog.md`, then dispatch the `test-quality` subagent with both + shared context. Catalog is mandatory context — every finding must cite a `smell_id` from T01-T05.

### Agent 3: test-economics
Read `references/scan-economics.md`, then dispatch the `test-economics` subagent with those instructions + shared context. Targets: snapshot-heavy files (≥50% threshold), flakiness signals (markers + git log), test:code LOC ratio extremes.

---

## Step 5 — Consolidate, Filter, Score

After all three subagents return:

1. **Certainty gate.** Drop findings with `certainty < 0.5` unless `severity = high` OR `deletable_lines >= 20` OR `coverage_gap_lines >= 50`. Big wins on either axis earn a pass through the filter so the user can review uncertain-but-impactful candidates.
2. **Deduplicate.**
   - `test-economics` `ratio_under` overlaps with `test-coverage` file-level gaps — when both point at the same module, drop the economics finding (it had certainty 0.55 by design).
   - Within `test-quality`, if a single test triggers both T02 and T03, keep the higher-severity one and append the other's evidence.
3. **Honor `respects_documented_decision: false`.** Route those to a separate report section regardless of dimension.
4. **Rank score.** `severity_weight × certainty / effort_weight × (1 + log(impact + 1))` where:
   - severity {low: 1, medium: 2, high: 4}
   - effort {trivial: 1, small: 2, medium: 4, large: 8}
   - impact = `coverage_gap_lines + deletable_lines`
5. **Twin-headline aggregation.**
   - `coverage_gap_total = sum(coverage_gap_lines)` across coverage findings. Distinct files affected = unique source paths.
   - `deletable_total = sum(deletable_lines)` across **only** these contributing finding types: `smell_id == T01`, `smell_id == T05 AND certainty >= 0.85` (the deletable subset of T05), `economic_signal == snapshot_heavy`. Distinct files affected = unique paths.
   - **Never include T02/T03/T04 or non-snapshot economics in `deletable_total`** — those are rewritable, not deletable. Including them would mislead the headline.
6. **Group**:
   - **Quick wins** — top rank, effort ∈ {trivial, small}. Heavily favors T01 deletions and small snapshot reductions.
   - **Strategic rewrites** — `dimension == quality` AND `smell_id ∈ {T02, T03, T04}` AND effort ∈ {medium, large}.
   - **Coverage gaps** — `dimension == coverage`, ordered by `priority_score × certainty`.
   - **Cost reductions** — `dimension == economics` AND `economic_signal == snapshot_heavy`.
   - **Suspects to measure** — flakiness findings, framed as "investigate, don't delete blindly."
   - **Documented-decision conflicts** — `respects_documented_decision == false`. Separate section, requires user confirmation.

---

## Step 6 — Output

Read `references/report-template.md` for exact formatting. The shape:

**Section 0 — Twin headline** (this is the *first* line of the report, before everything else):

> **Coverage gaps in critical code: X lines across Y files | Tests we can delete: Z lines across W files**

This dual signal makes both directions (under-tested + over-invested) equally visible.

**Sections 1-5** as in `references/report-template.md`:

1. Testing-Intent Summary echo + framework heatmap
2. Findings — three subsections (Coverage / Quality / Economics) ordered by rank score
3. Documented-Decision Conflicts (separate, "**Confirm intent before action:**")
4. Suggested Next Actions — skill chains (`/code-cleanup` for orphans, `/code-review` for diff-scoped follow-up); copy-pasteable `/plan-feature <brief>` snippets for top 3 strategic rewrites
5. Footer disclosure — framework detected, coverage tool used (or "heuristic"), files scanned vs sampled vs skipped, T01-T05 hit counts, twin-headline totals

---

## Step 7 — Mode-Specific Tail

### If `--plan` in $ARGUMENTS:
Read `references/plan-mode-test.md` if it exists; otherwise read `architecture-review/references/plan-mode.md` and adapt phase labels mentally (Quick wins → Phase 1, Strategic rewrites → Phase 2, Coverage gaps → Phase 3, Cost reductions → Phase 4, Documented-decision conflicts → Phase 5 confirmation). Transform top findings into a phased brief. Each phase emits a self-contained `/plan-feature <brief>` payload the user can drop into another session.

### If `--fix` in $ARGUMENTS:
Read `references/fix-mode-test.md`. **Walk only findings where `smell_id == "T01"`** — assertion-free tests are the one provably-safe deletion. Everything else auto-routes to `--plan`.

For each qualifying T01 finding:
1. Show the current test body
2. Show the proposed diff (deletion)
3. Wait for user approval (y / n / skip / abort)
4. Apply via `Edit` if approved
5. After deletion, check if the surrounding `describe`/`context` block now has zero children — if so, prompt separately about deleting the parent block
6. Check if the file now has zero tests — if so, prompt about deleting the file and surface to `/code-cleanup` instead

If user invoked `--fix` and no T01 findings surfaced, output:
> No T01 (assertion-free) findings. Other test smells require human judgment — re-run with `--plan` for a phased rewrite brief.

End with:
> Done. Use `Esc Esc` or `/rewind` to undo any individual edit. Use `git branch -D <branch>` to discard the whole pass.

---

## Step 8 — Closing

If running default mode, end with one line:
> Run `/test-review --plan` to convert top findings into a phased rewrite brief, or `/test-review --fix` for safe T01 deletions. Run `/code-cleanup` first if orphaned-test / stale-snapshot findings appeared above.

---

## Quick Reference

| Want... | Use... |
|---------|--------|
| Per-commit / diff test check | `/code-review` |
| Dead test files, stale snapshots, >3mo skipped tests | `/code-cleanup` |
| **Repo-wide test coverage + quality audit** | **`/test-review` (this)** |
| Plan a test-refactor effort | `/test-review --plan` |
| Delete provably-safe assertion-free tests | `/test-review --fix` |
| Coverage report-based gap analysis | `/test-review --coverage` |
| Architecture-level health | `/architecture-review` |
| Not sure which to run | `/code-health-advice` |
