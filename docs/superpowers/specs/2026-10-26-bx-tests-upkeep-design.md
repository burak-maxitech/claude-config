# Design: `/bx:tests` v2 — mechanism over prose, and a reduction lane

**Date:** 2026-10-26
**Status:** Implemented (S65). Release 1 shipped as 2.13.3, release 2 as 2.14.0. Deviations from this design are listed in [Implementation notes](#implementation-notes-2140).
**Author:** Session 65 with Claude
**Ships as:** two releases. See [Release split](#release-split).

## Release split

Agreed S65: ship safety and contract first, accuracy and reduction second.

| Release | Scope | Problems |
|---|---|---|
| **2.13.3** (PATCH) | Deletion safety and the shared contract: D2 (assertion definition, one allowlist), D3 (T01a/T01b), D5 rules 1, 2 and 4 applied to T01a deletions, `coverage_negatives` + `coverage_partial` in the dispatch block and every addendum, Step 5.7 groups removed, `--plan` phase gaps closed, the subtotal check made exact, agent files reduced to citations, sampling cap limited to judgment reads | 1–4, 10, 11, 12, 13, 18, 23, 26, 29 |
| **2.14.0** (MINOR) | D1 scripts, the accuracy fixes, the reduction lane (D4), the rest of D5, D6, monorepo and shell dialects | 5–9, 14–17, 19–22, 24, 25, 27, 28, 30–33 |

**Two corrections made while scoping 2.13.3:**
- **D3, zero allowlist.** Aborting on a zero-helper allowlist would block `--fix` forever on repos
  that legitimately have no helpers (maxitech). Missing allowlist *evidence* aborts; zero *with*
  evidence that the scan ran (patterns used, files searched) continues with the existing warning.
- **Problem 23, no rename.** `respects_documented_decision` is shared with `/bx:arch` (rubrics,
  catalogs, plan mode, five agents). Renaming it in one skill would fork the contract. 2.13.3 keeps
  the name and pins its meaning: `false` only when a *document* states an intent the finding
  contradicts. A known gap, a history note or an inferred posture is never a decision. The rename,
  if wanted, is a separate cross-skill change.

---

## Problem

`/bx:tests` claims to audit a suite "in both directions": coverage gaps on one side, waste on the
other, with a twin headline so neither hides. Session 65 read the whole surface (SKILL.md, seven
references, three agents; ~1,770 lines) and then ran it report-only on two real repos:
**horowell** (Next.js 16 / vitest 4 + Playwright, 866 source + 603 test files) and
**maxitech-concierge** (Python / pytest, 32 + 15). It had run on horowell four times before
(S56, S109, S149b, S182, driven from horowell sessions), and none of those runs' lessons had reached
the skill.

Three findings frame the design.

### 1. The results were good only because the scanners overrode the spec

Every Sonnet scanner, in both runs, wrote its own tooling for the same job and deviated from the
letter of its scan file to avoid false output. Three different T01 body parsers, two fan-in
methods, two module-attribution schemes, improvised prose for `coverage_negatives` in all six
scans. Applied literally, the spec would have produced:

| Spec rule, literally | Result | What the scanner did instead |
|---|---|---|
| T01 Python detector (no `mock.assert_*`) | **13 T01s on maxitech, 12 of them real tests** (~220 lines offered to `--fix` at certainty 0.95) | Counted mock-verification as assertions; emitted 1 |
| T01 on horowell | The scanner's own first parser: **18 false T01s**, then 4, then 0 | Iterated its parser until 0 |
| Neighbor-only coverage lookup | maxitech: 4 of 32 files matched; **~30,000 false gap lines** | Grepped symbols across the whole test scope |
| T03 formula (setup lines count as implementation) | horowell: **~130 findings**, nearly all false | Emitted 3 |
| T02 on `expect(getByText(..)).toBeTruthy()` in a repo without jest-dom | horowell: ~160 findings; `getBy*` throws, so these are real checks | Moved to `catalog_gap_proposals` |
| Ratio scan with a flat `tests/` dir | maxitech: every module 0 test lines → 4 false `ratio_under` | Attributed by import evidence |

This is the S64 `/bx:clean` lesson again: prose rules do not converge across runs, so the parts
that decide a deletion or a headline must be mechanism (a committed script or an exact command),
with judgment applied to its output.

### 2. `--fix` is not safe, and its premise is false

`--fix` deletes T01 (assertion-free) tests because "a test that asserts nothing cannot fail
meaningfully." Both halves fail:

- **Detection** misses assertions that throw: Python `mock.assert_called*`/`assert_awaited*`,
  Testing Library `getBy*`, Playwright locator actions. The allowlist regex that guards it is written
  three different ways and misses indented, `async` and test-local helpers. maxitech's allowlist
  came back **0**, and `fix-mode-test.md` contradicts itself on what 0 means (abort, line 26; warn
  and continue, line 38).
- **Premise.** maxitech's one genuine T01, `test_stop_when_no_task`, is `# Should not raise` then
  `await stop_watch_renewal()`. It fails if the call raises. A no-raise test is a weak test to
  strengthen, not a fake one to delete.

### 3. The skill only grows suites; it never shrinks them

The user's concern: test counts only ever go up. Measured:

| horowell | Jun | Aug | Sep | Oct 26 |
|---|---|---|---|---|
| Test LOC / source LOC | 0.49 | 0.67 | 0.85 | 0.88 |
| Test cases | 877 | 2,265 | 4,307 | 6,487 |

- **File-level orphans do not happen.** horowell deleted 59 source files; all 11 that had a
  same-name test lost it in the same commit, and no test imports or `vi.mock`s a missing module.
  maxitech's 23 `patch()` targets all resolve. The compiler and import system enforce this.
- **The inverse does happen: tests keep dead code alive.** maxitech `Email.build_reply_all_recipients`
  (`models/email.py:59`) was superseded by `services/scheduling_utils.py:build_reply_recipients`. It
  has zero production callers and **5 tests**. The live replacement has **none**. `/bx:tests` today
  scores the dead function as covered and the live one as a gap, and never connects them. (S64's
  `/bx:clean` found 15 such test-only symbols in horowell; this one is not in what S64 recorded for
  maxitech.)
- **Nothing consolidates.** 281 of horowell's 604 test files cite a session ID (incident-driven
  regression tests, added one at a time). There are 76 `.each` tables against 6,487 cases. Both
  quality scans found parameterize candidates. The skill's reduction side is only T01 (unsafe), T05
  (defaults to 0 deletable, no merge action) and snapshots (neither repo has any).

---

## Problems

Numbered as reported in session. **R** = found by reading, **H** = confirmed or found on horowell,
**M** = confirmed or found on maxitech.

### A. Deletion safety (`--fix`)
1. **T01 misses throwing assertions** — `mock.assert_*`, `getBy*`, locator actions. R, M (12 tests).
2. **Helper-allowlist regex written three ways, all too narrow** (`scan-quality.md:22`, agent file,
   catalog). R, H, M.
3. **`fix-mode-test.md` contradicts itself on a missing or zero allowlist** (26 vs 38). R.
4. **`fix-mode-test.md:27` cites a scan-time "TODO assert" rule that `scan-quality.md` lacks.** R.
29. **T01's "provably safe" premise is false for no-raise tests.** M.

### B. Headline and finding accuracy
5. **Neighbor-only lookup** turns centralized or feature-named suites into whole-file gaps. R, H, M.
6. **Bug-fix grep `^fix:` misses `fix(scope):`**; `-50` is "50 matching", not "last 50". R, H.
7. **Ratio scan breaks on root-level and flat-`tests/` layouts.** R, H, M.
8. **`--coverage` mode reads every file in the report**, not the critical subset the headline
   names. R.
9. **Fan-in is JS-quote-only and matches on basename** (`page`, `route`, `index`, `database`). R, H, M.
10. **Report template teaches tolerating a wrong sum** (`14 + 0 + 705 = 719` vs 819). R.
16. **Framework-invoked files (pages, routes, middleware) read fan-in 0.** H (S149b `proxy.ts`).
17. **A symbol that is only mocked counts as covered.** H (S149b, this run), M (`820c2076`).
19. **Flake grep matches substrings** ("Snowflake"). H.
20. **Security keyword list ranks enum keys; `-w sign` misses `signature`.** Divided by LOC, so tiny
    files top the list. maxitech's Slack HMAC check scored 0.03, last place. H, M.
21. **Export-form coverage** misses `export { }`, `export default`, `export type`. H.
22. **Headline sum undefined for `bug_fix_no_test`**, which also passes Step 5's `>= 50` exception at
    certainty 0.3. H, M.
24. **T03 counts setup lines** (`mockResolvedValue`, `vi.mock`, `patch`) as implementation. H, M.
25. **T02 flags `getBy*` + `toBeTruthy` in repos without jest-dom.** H.
27. **`coverage_gap_lines >= 1` forces invented numbers** for dependency-only or one-line fixes. M.
28. **A class or factory name in a mock patch counts as covering every method.** M.

### C. Contract and plumbing
11. **`coverage_negatives` never reaches the scanners** — it sits outside the dispatched block and in
    no scan file or addendum. Six of six scans improvised prose. R, H, M.
12. **Step 5.7 groups are never rendered by the template**; T02 at default `small` effort can never be
    a strategic rewrite; `snapshot_heavy` at `medium` falls into no `--plan` phase. R.
13. **Agent files restate scan files and have drifted** (churn command, neighbor list, snapshot
    threshold, `log`/`log10`, severity table missing). R, H, M.
14. **Monorepo half-specified** — "per-workspace" detection, single dispatch. R.
15. **Shell/PowerShell harness accepted in Step 0 but no scanner has rules for it.** R.
18. **Sample-tier "cap deep-reads at 50" does not fit scriptable checks**; horowell's quality scanner
    swept all 603 by script and did better. H.
23. **`respects_documented_decision` polarity undefined**; a known gap got marked as a decision. H, M.
26. **No partial-coverage disclosure** — horowell's T05 sweep crashed partway through and the report
    would have said "1 finding". H.
— **Minor:** orchestrator and coverage agent are granted `npx`/`npm`/`python`/`cargo`/`go` they are
  forbidden to use.

### D. Reduction (new)
30. **No detection of life-support tests** — test-only production symbols kept alive by their tests. M.
31. **No consolidation action or headline** — T05 is within-file only, defaults to 0, routes to prose.
    H, M.
32. **No growth signal** — nothing tells the reader the suite is outgrowing the code.
33. **`--fix` cannot reduce safely** — it never runs the suite, so any reduction beyond T01 would be
    unverified.

---

## Decisions (proposed — to lock with user)

**D1. Mechanism for everything that decides a deletion or a headline.** Commit
`bx/skills/tests/scripts/` (Python, stdlib only, read-only, writes only to an OS-temp out-dir given on
the command line):
- `test_bodies.py` — extracts every test body (JS/TS `it`/`test` incl. expression-bodied arrows and
  `.each`; pytest `def test_*` incl. class methods; unittest; Go; Rust `#[test]`; JUnit), counts
  assertions with the per-language list (D2), and emits one JSON row per test: location, name, body
  lines, assertion counts by kind, setup-vs-verification mock lines, weak-matcher-only flag.
- `leverage.py` — one `git log --name-only` for churn; import-graph fan-in resolved to **paths**
  (relative, `@/` aliases from `tsconfig`/`vitest` config, Python dotted modules), not basenames.
  Framework entry points (`app/**/page|layout|route.*`, `middleware`/`proxy.*`, FastAPI route
  decorators) are tagged `entry_point: true`.
- `references.py` — for each public symbol: production references, test references, and whether
  each test reference is a **call**, a **mock target** or a **name mention**. Feeds coverage (problems
  5, 17, 28) and the life-support lane (30). It reuses the pinned local-use `git grep` command from
  `/bx:clean` (S64) as its reference search, so the two skills agree.

Scanners read the JSON and apply judgment. They do not write parsers. A scanner that disagrees with
a row says so in `RUN NOTES`; it does not re-derive it.

**D2. An assertion is anything that fails the test on a regression.** This covers framework matchers;
mock verification (`assert_called*`, `assert_awaited*`, `toHaveBeenCalled*`, `verify(`); throwing
queries (`getBy*`, `findBy*`); Playwright `expect`/locator actions; `pytest.raises`; and project
helpers. One allowlist pattern lives in `test-smell-catalog.md` and is cited, not restated, by the
scan file and agent. It must match indented, `async`, test-local and `export` forms.

**D3. T01 splits into two smells, and neither is a blind delete.**
- **T01a — No-op test**: no assertions, *and* the body cannot raise in a way that tests anything (only
  literals, setup, or `pass`). Eligible for `--fix` deletion.
- **T01b — Implicit no-raise test**: no assertions, but the body calls code under test. Route to a
  rewrite ("make the contract explicit": assert the post-state, or use
  `expect(..).not.toThrow()` / a no-raise helper). **Not deletable.**
A missing or zero `helper_allowlist_size` **aborts** `--fix` (problem 3 resolved toward safety).

**D4. Add a reduction lane, with a third headline.** The twin headline becomes:

> **Coverage gaps in critical code: X lines across Y files | Tests we can delete: Z lines | Tests we
> can consolidate: N → M**

New finding classes, all `dimension: economics` and all from D1 script output:
- **`life_support`** (problem 30): a production symbol with zero production references and ≥1 test
  call. One finding covers the symbol and its tests. `deletable_lines` = symbol lines + its test
  lines. If `references.py` finds a likely successor (a same-name stem or a shared caller that moved),
  the recommendation is **"move these tests to `<successor>`, then delete both"**. That turns
  maxitech's pair into one finding, and it closes the successor's coverage gap.
- **`consolidate`** (problem 31): ≥2 tests whose `test_bodies.py` shapes match after literal
  stripping (Jaccard ≥ 0.9 on token multisets), within a file **or across files testing the same
  symbol**. Reports N tests → 1 parameterized test. Every distinct input survives as a table row;
  boundary-literal and different-setup guards stay. This replaces T05's deletable accounting: T05
  becomes the within-file special case, and its lines move to the consolidate headline, not to
  "delete".
- **Growth trend** (problem 32): footer line from `git log` sampling: test/source LOC ratio at 4–6
  monthly points and the case count. Informational, never a finding.

**D5. `--fix` becomes a gated, suite-verified reducer.** Eligible: T01a deletions, `life_support`
(when no successor is named), and `consolidate` merges. Each finding is shown and approved per item,
as now. New rules:
1. **Baseline first.** Run the project's test command once (Step 0 already detects it) and record
   pass/fail and test count. A red baseline aborts.
2. **After each applied item, rerun the affected test files.** Any new failure reverts that item
   (`git checkout -- <files>`) and records it as "reverted: suite failed".
3. **Count check.** For `consolidate`, the post-merge parameterized case count must equal the
   pre-merge test count. Fewer cases means an input was dropped, so revert.
4. **Branch required.** `--fix` refuses to run on the default branch or a dirty tree (checkpoints are
   per prompt and git is the only undo for multi-file reductions).
5. `life_support` source deletion is applied here only for symbols, never whole files. Whole-file
   deletion still routes to `/bx:clean`.

**D6. Ownership with `/bx:clean`.** `/bx:clean` keeps *unused test helpers* and orphaned test files.
`/bx:tests` owns *test-only production code* (`life_support`), because the action is about the tests
and the successor. `/bx:clean`'s files-code scan stops reporting those symbols as dead (it reports
them as "test-only, see `/bx:tests`"), so the two never double-count. Both use one reference-search
command.

---

## Architecture

### Contract changes (problems 11, 22, 23, 26, 27)
- The dispatched shared-context block gains `coverage_negatives` (three states) **and**
  `coverage_partial: [{category, scanned, total, reason}]`. Every scan file's output addendum lists
  both. Step 5 renders partial coverage in the footer next to the negatives.
- `respects_documented_decision` is renamed **`conflicts_with_documented_decision: bool`**, `true`
  only when a *document* states the opposite intent. A known gap is not a decision.
- `bug_fix_no_test` findings carry `coverage_gap_lines: 0`, never enter the coverage headline, and
  render only in their own table. The `>= 1` rule exempts them.
- Step 5.6: `deletable_total` = T01a + `life_support` + `snapshot_heavy`; `consolidate_total` is
  separate. The template's subtotal check must equal exactly. Delete the "rounding" wording.

### Scanner changes
- **Coverage:** priority keeps `security_density × churn × fan_in`, but density uses an expanded
  word-bounded list (`signature`, `hmac`, `webhook`, `jwt`, `oauth`, `nonce`, `replay`), drops the
  generic `key`/`role`/`hash` unless paired with a crypto/auth token on the same line, and is floored
  by file size (no division blow-up under ~20 LOC). `entry_point: true` gets a fan-in floor so
  middleware and routes rank. Symbol coverage = "has a test **call**" from `references.py`. A
  mock-only reference is an explicit `mock_only` gap (problem 17). Bug-fix grep becomes `^fix\b`,
  window "last 200 commits, then matching", with the heading stating the window.
- **Quality:** T01a/T01b/T02/T03 come from `test_bodies.py` rows. T03 counts only *verification*
  lines (`toHaveBeenCalled*`, `assert_called*`, `call_args`), not setup. T02 treats `getBy*` inside
  `expect(..)` as a strong presence check. A catalog entry **T06 — Name/assertion mismatch** is added
  from maxitech's `test_calendar_failure_shows_error` (report-only, never deletable).
- **Economics:** module attribution comes from `references.py` import evidence, not path stems,
  which fixes flat `tests/` and root layouts. The flake grep is word-bounded and needs the subject to
  name a test or a flake. `life_support` and `consolidate` are emitted here.
- **Sampling (problem 18):** script-backed checks run on every tier. The 50-file cap applies only to
  judgment reads (verifying candidates), not to sweeps.

### Drift removal (problem 13)
The three `test-*` agent files shrink to role, inputs, hard rules and "your scan file is canonical".
Every detection detail lives once, in the scan file or catalog. This is the S62 `lane-contract.md`
pattern.

### Smaller fixes
Monorepo dispatch runs one trio per workspace and aggregates (problem 14). Shell/PowerShell gets a
`test_bodies.py` dialect: a `pass`/`fail`/`assert_*` helper call counts as an assertion, and the
neighbor is a `test-<name>.sh` (problem 15). `--coverage` restricts the headline to the priority set
and reports the full-report total separately (problem 8). `allowed-tools` drops the runtimes, except
for running the detected test command, which D5 now needs. Step 5.7 groups are either rendered by
the template or deleted (problem 12; preference: delete, since the template's per-dimension sections
are what the runs used).

---

## Interfaces changed outside the skill

| File | Change |
|---|---|
| `bx/skills/clean/references/scan-files-code.md` | Test-only symbols are reported as "test-only → `/bx:tests` `life_support`", not as dead code (D6) |
| `bx/agents/test-*.md` (3) | Shrink to role + citations (problem 13) |
| `bx/skills/arch/references/scale-strategy.md` | Note that script sweeps are tier-independent (problem 18) |
| `README.md`, `docs/architecture.md` | Triple headline, reduction lane, `--fix` gating |
| `bx/.claude-plugin/plugin.json`, `CHANGELOG.md` | 2.14.0 |

---

## Acceptance

Verify-by-running, with fixed controls from this session's real repos. Each must hold on a rerun
from the shipped files, with **no scanner-authored parsers** (`RUN NOTES` must report zero deviations
of the D1 kind):

| Control | Repo | Expected |
|---|---|---|
| The 12 mock-assert tests (B–M in the S65 report) | maxitech | Not T01; ≤3 surface as T03 |
| `test_stop_when_no_task` | maxitech | T01b rewrite, not deletable, not `--fix`-eligible |
| `build_reply_all_recipients` + its 5 tests | maxitech | One `life_support` finding naming `build_reply_recipients` as successor |
| `SlackService.verify_request` | maxitech | Coverage finding, severity high, **top 3 by rank** |
| `820c2076` | maxitech | `bug_fix_no_test`, `coverage_gap_lines: 0`, outside the headline |
| Neighbor misses | maxitech | ≤3 false whole-file gaps (was ~30,000 lines) |
| T01 | horowell | 0, from `test_bodies.py`, first pass |
| T03 | horowell | ≤10 (was ~130 literal) |
| `getBy*`+`toBeTruthy` | horowell | Not T02 |
| `(dashboard)/layout.tsx` | horowell | Still surfaces (S182's open question) |
| Partial sweep | either | A forced script timeout shows in `coverage_partial` |
| `--fix` on a throwaway branch | maxitech | One T01a or `life_support` applied, suite rerun green, count check holds. A deliberately bad merge is reverted automatically |

Plus a failing control for D5: apply a `consolidate` merge that drops one input row, and show the
count check reverts it.

## Open questions
- **D4 thresholds:** Jaccard 0.9 for `consolidate` is a guess. Calibrate on horowell's sweep before
  locking.
- **Successor detection (D4):** a same-stem match is cheap but will miss renames. Is "a shared caller
  switched from A to B in one commit" (`git log -S`) worth the cost?
- **D5 runtime:** horowell's suite is ~25s, which is fine per item. A slow suite needs "rerun the
  affected files only", and for vitest/pytest that is a path argument. Is that enough, or does `--fix`
  need a batch mode?
- **Scope of this release:** all of A–D in 2.14.0, or A + C first (safety + contract, PATCH) and
  B + D in 2.14.0?

---

## Implementation notes (2.14.0)

- **`references.py` implements `/bx:clean`'s local-use rule as an identifier index**, not one
  `git grep` per name: it has to classify every hit (call / mock / mention / string) and covers
  ~2,700 symbols in seconds. `/bx:clean` now cites it (D6) rather than the reverse.
- **`respects_documented_decision` kept its name** (shared with `/bx:arch`); 2.13.3 pinned its
  semantics instead.
- **Successor detection** uses four signals, strongest first: a commit that switched the last caller
  (`git log -S` on code paths, the candidate newly *called* and sharing a name stem), the symbol's
  doc comment, a thin wrapper over a non-plumbing live function, and a name stem ≥ 0.6. Stem alone at
  0.5 named a sibling on the Next.js repo.
- **Consolidate calibration:** 0.9 Jaccard kept; a ≥ 4-saved-lines floor added (207 of 458 clusters
  saved 1–3 lines). Mechanical = identical raw token sequence outside literals, with a computed merge
  table; only those are `--fix`-eligible.
- **Module ratios** attribute a test file by the symbols its tests call, then by imports. Imports alone
  sent pipeline tests to the models module they import for fixtures.
- **`--fix` reverts restore a per-item snapshot**, not `git checkout -- <file>` (which undoes earlier
  verified items in the same file).
- **Acceptance:** every control in the table above held on scanner reruns from the shipped files,
  except that the agent definitions themselves were not exercised (the runs used general-purpose
  agents reading the scan files; the installed plugin cache was 2.13.2). The `--fix` controls ran on a
  throwaway clone of the pytest repo with planted no-op, life-support and cluster controls plus two
  real clusters: 210 → 207 cases, as computed; the deliberately bad merge was reverted by the count
  check alone.

## First use of the output (S66, 2026-10-28) — 2.14.1 and 2.15.0

A horowell session (its S257) acted on a `/bx:tests --plan` brief: six hand merges and six
life-support deletions. Its report named nine problems with acting on the output. Each was checked
against the 2.14.0 source:

| # | Problem | Verdict | Release |
|---|---|---|---|
| 1 | The brief cites cluster ids whose only definition is a temp scratchpad | Confirmed: scripts write only to `--out` (OS temp) | 2.14.1 |
| 2 | Line numbers go stale after the first edit in a file | Confirmed: rows were `{file, line, end_line, name}`; `--fix` B deleted by `line`–`end_line` | 2.14.1 |
| 3 | Mock-only ignores coverage through another export of the same module | Plausible (status is per symbol name) | 2.15.0 |
| 4 | Private SQL twins reached only through callers count as untested; the twin recipe downgrades behavioural tests to SQL-text checks | Plausible | 2.15.0 |
| 5 | Cluster similarity ignores matcher differences (`toBe(n)` vs `≥ 1`) | Plausible: shape Jaccard strips literals but not intent | 2.15.0 |
| 6 | No cross-cluster pairing (same policy, two fields) | Plausible | 2.15.0 |
| 7 | `--fix` never type-checks; vitest strips types | Confirmed: no type-check step anywhere; the S257 `tsc-before/after` files were improvised | 2.14.1 |
| 8 | "774 → 251" headline overstates the worthwhile work | Report-template change | 2.15.0 |
| 9 | Life-support false positives on test helpers inside `src/` | Confirmed when the source list includes them: horowell 246 → 21 deletable lines | 2.14.1 |

**2.14.1 decisions**
- **Persist under `<repo>/.bx/tests/<date>/`, excluded through `.git/info/exclude`.** `.gitignore`
  would dirty the tree, and `--fix` requires a clean one. The scripts still write to temp (their
  in-repo guard stays). `run.py --save-to` copies the outputs and rewrites the saved manifest's paths.
- **Anchor = `file :: describe > … > name`**, plus a stable cluster `key` (hash of the anchors),
  because `C###` is positional per run. On horowell, all 739 clustered rows have unique anchors.
  `--fix` skips an item whose anchor is gone and never falls back to the line number.
- **The type check compares against a baseline, not zero.** Horowell carries 47 test-file tsc
  errors on main behind a "0 non-test" gate. A rise reverts the item.
- **Test-support code is never life support**, by two rules: a symbol defined in a test path is
  skipped, and a production symbol that any test-support file references (a test path that is not a
  test file by name) gets `used_as_test_helper_in` and 0 deletable lines. The definition rule alone
  missed nothing on horowell. The reference rule covers production helpers that e2e stubs import.
  The proposed "never delete" allowlist was not added: both rules address the cause.

**Verified by running (2.14.1):** old and new scripts on horowell and maxitech-concierge. With
horowell's `e2e/` and `testing/` files in the source list, 2.14.0 lists `stubResponseFor` (168
lines), `neonApiGatewayHost` (26) and `stripComments` (31) as deletable, and 2.14.1 drops all
three. maxitech's life support is unchanged (`build_reply_all_recipients`, 37). `--save-to` was run
twice on a throwaway repo: the tree stayed clean, the exclude line was written once, and a path
outside the repo was refused. **Text-only until a real `--fix` run:** the type-check gate and
finding items by anchor.
