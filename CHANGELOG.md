# Changelog

All notable changes to the `bx` plugin, newest first. Versioning follows [semver](https://semver.org). The `version` field in `bx/.claude-plugin/plugin.json` is the plugin's **update cache key**: users receive an update only when it changes, so every change under `bx/` must bump it (automated by `/bx:save`'s commit checkpoint).

## 2.15.1 — 2026-10-28

`/bx:save`: a smaller everyday save, and a commit window that no longer repeats earlier saves.

### Changed
- `mode-update.md` is split. The default save now loads only Step 0, the Save Path, Part 0, Part 1.0–1.8 and Part 8 (28 KB). The Full Path, Step 0.3, Part 0.5, Parts 1.9–1.10 and Parts 2–7 moved to the new `mode-update-full.md` (47 KB), loaded only with `--full`. Part numbers are unchanged. `doc-structure-rules.md` is also skipped on the default path. Together that is about 51 KB (~13k tokens) less to read on every save without `--full`.
- Step 0 finds this session's commits from the **save anchor**, the last commit that wrote `docs/STATUS.md`, not from the `Last Updated` date. With a date cutoff, a second save on the same day picked up the first save's commits again. Replayed on S65's second save of 2026-10-26: the date cutoff took 3 commits (two from the earlier save), the anchor takes 1. One `git log --name-only` call replaces `git log` + `git diff --stat HEAD~5`.

## 2.15.0 — 2026-10-28

`/bx:tests` accuracy: the five remaining problems from the first session that acted on its output
(horowell S257). Each was reproduced on a clone of horowell at the commit before that session's
edits, then checked against maxitech-concierge.

### Added

- **`indirect` coverage status.** A symbol no test calls, but whose production caller a test does
  call without mocking it, is reached through that caller: `reached_via`, `reached_by_tests`,
  `indirect_depth` (up to 2 public levels, following private helpers in between), gap 0. A caller's
  test does not count when it mocks anything in the symbol's module (a `patch("…factory")` string
  target or a `vi.mock`) or mentions the symbol (mock configuration). horowell: 256 symbols, gap lines
  7,615 → 3,359, including `withTodaysDialChoice` (was mock_only) and the private `stuckLeadSql`.
  maxitech: 20, including `build_reply_recipients` through its Slack handler. Security-dense
  indirect symbols are still read by the coverage scanner, which reports a gap when the caller's
  tests never take the calling branch.
- **Twin detection on life support.** `successor_twin` (a query-language twin, by name suffix or a
  comment), the new `private_twin` successor kind for a non-exported twin in the same file, and
  `successor_reached_via`. The scanner offers two options (render-test the twin, or keep the JS
  twin as the spec plus an agreement test) instead of "move the tests, then delete".
- **`matcher_variants` on non-mechanical clusters.** These are the members that assert different
  relations (`toBe` vs `toBeGreaterThanOrEqual`), so the table gets a per-row matcher column. On
  horowell this flags the verified-row case S257 found by hand in both merge-policy clusters.
- **`siblings[]`.** Two clusters in one file that are one table on two fields, split only because
  their setup differs: found by pairwise member shape match. On horowell it found S257's
  `dial_finishes` / `straps` pair, plus 15 others.
- **Worthwhile consolidation leads the headline.** `totals.worthwhile` counts clusters that save at
  least 20 lines, or mechanical ones that save at least 10. On horowell that is 56 merges saving
  1,663 lines, ahead of the raw 249 clusters. All six S257 hand merges are in the set.

### Fixed

- **Multi-line generic return types cut a function's extent at its signature.** `js_extent` ended
  `extractWatchFromUrl` (476 lines) at line 3 on `): Promise<`. 14 horowell symbols had wrong extents,
  which understated their gap lines and hid every call inside them.

## 2.14.1 — 2026-10-28

`/bx:tests` fixes from the first session that acted on its output (horowell S257: six hand merges
and six life-support deletions from a `--plan` brief). Each fix guards against something that broke
or misled there. Spec addendum: `docs/superpowers/specs/2026-10-26-bx-tests-upkeep-design.md`,
"First use of the output".

### Fixed

- **`--fix` now type-checks.** Step 0 records a type-check command that includes test files (`tsc
  --noEmit --incremental false`, or a configured mypy/pyright). `--fix` records its error count as a
  baseline, which need not be zero, and reverts any item that raises it. vitest strips types, so a
  merged table that widened a union to `string` passed the suite and added two tsc errors.
- **Tests are found by anchor, not line number.** `consolidate.json` rows carry
  `anchor` (`file :: describe > … > name`) and `describe[]`, and each cluster carries a stable `key`.
  `--fix` locates every test and symbol by name and skips an item whose anchor is gone. After the
  first merge in a file, later clusters had moved 50–300 lines.
- **Reports persist.** `run.py --save-to <repo>/.bx/tests/<date>/` copies the outputs into the repo,
  with a manifest pointing at the copies, and excludes `.bx/` through `.git/info/exclude`, so the tree
  stays clean. The report is also written there as `report.md`. `--plan` briefs list each cluster's
  file and member anchors instead of a bare `C###` id, which was resumable only by grepping another
  session's temp scratchpad.
- **Test-support code is never life support.** A symbol defined in a test path
  (`src/lib/e2e/`, `src/lib/testing/`) is skipped. A production symbol that a test-support file
  references gets `used_as_test_helper_in` and 0 deletable lines. On horowell with those folders in
  scope, this drops 225 falsely deletable lines (`stubResponseFor`, `neonApiGatewayHost`,
  `stripComments`).

## 2.14.0 — 2026-10-26

`/bx:tests` measures with committed scripts and can now shrink a suite. This is release 2 of the S65
design (`docs/superpowers/specs/2026-10-26-bx-tests-upkeep-design.md`). Built against two real repos
(a Next.js app with ~6,600 tests, and a pytest service), with eight scanner runs from the new files
and a `--fix` dogfood on a throwaway clone.

### Added

- **Scripts measure, scanners judge.** `bx/skills/tests/scripts/` (stdlib Python, read-only, writes
  only to an OS-temp dir; `run.py` runs all four and writes a manifest):
  - `test_bodies.py` — one row per test (JS/TS incl. expression-bodied arrows, `.each` and generics;
    pytest/unittest; Go; Rust; JUnit; bats/shell; Pester): assertion counts by kind, T01a/T01b, the
    T02 weak-only, T03 and T06 candidate flags, the helper allowlist with its evidence, and token
    shapes. Recall check on the Next.js repo: 0 tests missed.
  - `leverage.py` — churn, fan-in resolved to paths (tsconfig/vite aliases, Python dotted and
    relative imports), entry points, security density on identifier sub-words, the bug-fix lane
    (`^fix` over the last 200 commits), the flake lane (word-bounded, must name a test), and the
    growth trend.
  - `references.py` — per public symbol: production references (code only, `/bx:clean`'s local-use
    rule), and test references classed as **call / mock / mention** (a `vi.mock`ed or `patch`ed name is
    a mock, never coverage), routes a test client reaches by URL, the `life_support` lane with
    successor detection (caller-switched commit, doc comment, thin wrapper, name stem), and test:code
    ratios per module attributed by what the tests call.
  - `consolidate.py` — clusters of tests that differ only in literals (multiset Jaccard ≥ 0.9, same
    setup, ≥ 4 lines saved; calibrated on the Next.js repo), with a computed **merge table** for the
    mechanical ones.
  A failed or timed-out script becomes a `coverage_partial` entry instead of a silent zero.
- **The reduction lane and a third headline.** `life_support` (production code only its tests call:
  15 symbols on the Next.js repo, matching a backlog list the repo's own `/bx:clean` run had made) and
  `consolidate` (774 → 251 tests there). The headline is now "Coverage gaps | Tests we can delete |
  Tests we can consolidate: N → M". The footer carries the growth trend (0.06 → 0.91 test/source
  LOC in six months).
- **T06 — name/assertion mismatch** (report-only).
- **`--fix` became a suite-verified reducer** for three kinds of item — T01a deletions,
  successor-less life-support deletions, mechanical merges — each with a **count check**: a deletion
  drops the case count by exactly what it removed, a merge leaves it unchanged. Proven on the clone:
  a merge that dropped one of three rows left the file green, and only the count check reverted it.

### Changed

- The scan files and agents consume the script output; T03 counts verification assertions only
  (setup lines and "never called" checks are not coupling); a positive `toBeNull()` and a
  `getBy*` inside `expect` are no longer weak; `bug_fix_no_test` carries 0 gap lines and stays out of
  the headline; T05 is reported once, as `consolidate`; sampling limits judgment reads, never script
  sweeps; monorepos run one script pass and scanner trio per workspace.
- **`/bx:clean` hands test-only functions to `/bx:tests`** (D6): they appear in a non-finding
  "Test-only symbols — see /bx:tests" block, never as dead code, so the two skills never delete the
  same symbol.

### Fixed (found by running)

- Thirteen script defects the scanner runs reported, each fixed in the script: successor and
  helper-use deletable counts, life-support tests double-counted as merges, fixture imports
  outvoting the code under test, migrations and `types/` counted as code, `toBeInstanceOf(<Class>)`
  read as weak, URL-routed handlers read as untested, ORM model classes read as gaps, priority-0
  ties, and successor detection by name stem alone (it named a sibling for one symbol and missed
  three replacements). The dogfood found two more: Python test names hid every mechanical cluster
  (the `def` name now fills the name slot), and the draft revert (`git checkout -- <file>`) would
  have undone earlier verified items in the same file (reverts now restore a per-item snapshot).

## 2.13.3 — 2026-10-26

`/bx:tests` deletion safety and finding contract. This is release 1 of the S65 design
(`docs/superpowers/specs/2026-10-26-bx-tests-upkeep-design.md`). Report-only runs on two real repos
(a Next.js app with 603 test files, and a pytest service) showed that `--fix` could delete real
tests, and that the scanners produced good results only by overriding their instructions.

### Fixed

- **`--fix` could offer real tests for deletion.** The assertion-free check did not count mock
  verification (`assert_called*`, `assert_awaited*`), Testing Library `getBy*` queries, or
  Playwright actions as assertions. Applied literally to the pytest repo, it flagged 13 tests, and
  12 of them were real tests (~220 lines at certainty 0.95). The catalog now defines an assertion as
  anything that fails the test on a regression, in one canonical place that the scan file and agent
  cite.
- **"Assertion-free" split into two smells.** **T01a (no-op)** calls nothing under test and is the
  only `--fix`-eligible smell. **T01b (implicit no-raise)** calls code under test and fails if it
  raises, so it routes to a rewrite and is never deleted. The one genuine candidate on the pytest
  repo was a deliberate `# Should not raise` test that the old premise ("cannot fail meaningfully")
  would have deleted.
- **The helper-allowlist guard was written three ways, all too narrow.** There is now one pattern
  per language, allowing indentation, `async`, `export` and test-local forms. The scan must report
  its evidence (patterns, files searched) even at zero. Missing evidence aborts `--fix`; zero *with*
  evidence continues with a warning. The two rules had previously contradicted each other.
- **`--fix` never verified anything.** It now requires a feature branch and a clean tree, a green
  baseline run of the project's own test command, and a per-file rerun after each deletion. An edit
  whose rerun fails or changes the count unexpectedly is reverted automatically. Step 0 records the
  test command.
- **In-flight tests.** The "TODO assert" rule that fix mode cited at scan time now exists in the
  scan.
- **Empty and partial results were lost.** `coverage_negatives` sat outside the dispatched block, so
  no scanner received it; six of six scans improvised prose. Both it and a new `coverage_partial`
  (for a sweep that crashed or could not handle the layout) are now in the dispatched block and in
  every addendum. The orchestrator records an unreported zero as partial, never as clean.
- **`respects_documented_decision` had no definition.** It is `false` only when a document states
  an intent the finding contradicts; a known gap is not a decision. The name is unchanged because
  `/bx:arch` shares the field.
- **The report template taught tolerating a wrong sum** (`14 + 0 + 705 = 719` against 819, called
  "rounding"). The subtotal check must now match exactly.
- **Findings fell through `--plan`.** Phase 1 filtered by effort, so medium-effort snapshot
  deletions belonged to no phase, and a T02 at its default effort could never be a rewrite. Phases
  now select by deletable vs. rewrite at any effort. The unrendered Step 5.7 grouping is removed.
- **Agent files restated their scan files and had drifted** (churn command, neighbor list, snapshot
  floor, severity table). The three `test-*` agents now hold only their role and hard rules, and cite
  the scan files as canonical. `test-coverage` loses the runtime tools it was forbidden to use.
- **The sample-tier read cap blocked mechanical sweeps.** It now limits full reads used to verify
  candidates, not grep or script sweeps.

## 2.13.2 — 2026-10-23

Second real `/bx:clean` run — the first on a JS/TS codebase (a Next.js 16 app, 1,780 files,
report-only) — found six defects. All fixed; no new categories.

### Fixed

- **A live symbol could be offered for deletion.** Exports used inside their own file but nowhere
  else arrived as `unused_export`, `risk: safe` — and Safe to Delete says "only the symbol goes",
  which breaks the file. They are now `export_only`, reported in a `## De-export candidates` block,
  never a finding and never a `--fix` action.
- **`lines: unknown`.** Function findings came back without an end line, leaving holes in the
  `--dry-run` impact table. Extent is now measured from the file, never estimated.
- **Count-only summaries outside the contract.** About 180 exports arrived as one-line counts; the
  de-export block gives them a defined, capped shape.
- **An unlisted command wrote to a report-only repo.** The scanner ran `tsc --noEmit
  --noUnusedLocals`, which with `incremental: true` rewrote `tsconfig.tsbuildinfo`. `tsc` is now the
  named TypeScript unused-import method with `--incremental false` mandatory; nothing else may run.
- **Fixture-named trees hid real references.** `e2e/fixtures/*.ts` was real Playwright support code.
  `scan-exclusions.md` (shared with `/bx:arch` and `/bx:tests`) now says exclusion removes
  candidates, not evidence: references from an excluded tree still count.
- **Doc mentions hid dead functions.** One verification run counted markdown as references, so two dead functions named in the project's session log read as live. A code symbol's reference must be in code; doc mentions are named in the finding instead.
- **Comments kept dead functions alive, and a scanner wrote and ran its own scripts.** A dead function mentioned in its own file's doc comment was classed `export_only`; local uses are now counted with comments stripped. The same run wrote `.mjs` helpers to a temp directory and ran them with node; no interpreter may run, nothing may be written inside the repo, and scratch files are allowed only in the OS temp directory, deleted before the agent returns (a stricter no-write rule failed four runs in a row on a 1,780-file repo). Test-only references now always rate `needs_investigation` (two runs had disagreed).
- **Local-use detection is now a pinned command.** Prose rules for "used in its own file" did not converge across runs, so the scan file gives the exact `git grep` pipeline. Its first version dropped every `export` line and called ~48 types live only in another export's signature dead at `risk: safe`; it now drops only the definition line (verified on 3 dead and 8 live symbols).
- **shadcn/ui kit exports were flagged.** `components/ui/*` with a `components.json` joins the
  framework-convention never-flag list.

## 2.13.1 — 2026-10-23

First real `/bx:clean` run (on a Python/FastAPI service, report-only) found four defects the fixtures
could not reach. All fixed in the scan references; no new categories.

### Fixed

- **Dead config keys: false positive on a read key.** A key read through an accessor
  (`self.config.assistant.get("sign_off")`) was reported as having no reader, at `likely_safe`,
  because the whole-dict pass-through rule let the scanner stop at "passed around". A quoted-key
  grep across all source is now mandatory before reporting, accessors are traced to their call
  sites, and `likely_safe` is reserved for objects that leave the repo or are consumed wholesale.
- **Dependencies used without an import were reported as findings.** `uvicorn` (Procfile),
  `asyncpg` (driver URL), `requests`/`aiohttp` (transitive runtime needs) and `pytest-asyncio`
  arrived as `likely_safe` findings annotated "do NOT remove" — deletion candidates under
  `--aggressive --fix`. A confirmed mechanism now means "used": listed under `## Used without import`,
  never ranked.
- **Unavailable checks absorbed skipped and clean ones.** An orchestrator-skipped section and checks
  with zero candidates ("no issue-linked TODOs to look up") were listed as unavailable. All three scan
  files now separate skipped, clean and unavailable (precondition or tool absent).
- **Settings fields doubled as unused exports, and `quick_win` coexisted with a hedge.** An unread
  `Settings` field arrived from two scanners under two types; it now belongs to §6 only, and the
  orchestrator keeps that entry. A `quick_win: true` finding must be `risk: safe` (scanner rule and
  Step 2.4 downgrade).
- **Deliberately kept env vars were still findings.** A `Settings` field commented "unused in code; kept
  so .env var isn't rejected" arrived as a finding marked "not a deletion candidate". A repo comment
  marking a variable as kept now moves it to a `## Kept deliberately` line, never ranked.
- **Unavailable checks varied run to run; doc-described config keys reached `safe`.** Three reruns of
  one scan file produced three different unavailable blocks, so SKILL.md Step 2.5 now normalises the
  block in the orchestrator (drop clean entries, add the preconditions Step 0 found absent). A dead
  config key is now checked against `*.md`/`docs/**`/`README*` in the same grep, and any doc mention
  caps it at `needs_investigation` — one run had rated a PRD-documented key `safe`.

## 2.13.0 — 2026-10-21

Content review of `/bx:clean` (SKILL.md, three scan references, three `cleanup-*` agents) — the
S46 treatment, repeated after a year of sibling skills learning rules this one never received.
Four high, six medium, four low findings; all fixed. Verified by re-running the committed eval
suite against this version and the 2.12.2 snapshot.

### Added

- **Seven detection categories**, each with a planted hit and a precision trap in the eval fixtures:
  unused exports (one barrel hop followed; framework-convention exports never flagged), orphaned
  assets (CSS `url()`, HTML and web-manifest references count; glob-imported folders cap at
  likely-safe), lockfile drift (direct entries the manifest dropped, two lockfiles side by side,
  orphaned `@types/*`), dead i18n keys (source locale only; dynamic prefixes exclude their subtree)
  and dead config keys (framework-consumed keys never flagged), stale hard-coded feature flags
  (git-dated, env- and service-driven flags excluded), trivial directories (`.gitkeep`, empty
  `__init__.py`, `export {}` barrels), and unused type definitions (ambient augmentations
  excluded). All roll into the existing eight dashboard rows and none is a Quick Win.

### Fixed

- **Directory scope no longer turns the whole dependency list into false positives.** `/bx:clean
  src/payments/` greps for references repo-wide and reports only items inside the scope; the
  manifest-level categories (unused deps, vulns, config cruft) run under a directory scope only when
  that directory is a workspace root, and the dashboard says why they were skipped otherwise. The
  scope was never passed to the agents before.
- **Migrations are never one-off scripts.** The age heuristic excluded nothing, so an applied
  Django/Alembic/Rails/Prisma migration — one old commit by design — was a deletion candidate. The
  `git log` it prescribed also lacked `--name-only` and returned no filenames.
- **Unused-import quick wins carve out side-effect imports, barrel/`__init__.py` re-exports,
  lint-suppressed lines and type/pragma imports.** `--fix` auto-removed every import with no
  in-file reference; these four forms have none by design.
- **`/bx:clean` cites `scan-exclusions.md`** (Step 0.1, all three agents) instead of a private skip
  list, and excludes fixture trees from stack detection — the very hazard that file documents using
  this skill's own fixtures as the example. `cleanup-files-code` leaves the "still to be swept" list.
- **`--dry-run` touches nothing.** It staged removals on a throwaway branch and relied on
  `git reset --hard` to undo them — a destructive-git form auto mode may deny, and the S46 bug was
  this same dance carrying staged deletions back onto the user's branch. It now confirms file
  removals with `git rm -n`, takes in-file counts from the findings, and renders the same impact
  table. `--fix` records the starting branch instead of assuming `main`.
- Node dependency search allows a subpath after the package name (`lodash/debounce`, `swiper/css`),
  covers `.vue/.svelte/.astro/.mdx` and stylesheet imports, names the config files where
  plugins appear as bare strings, and escapes `.` in package names (the old example escaped nothing).
- Python requirement lines are parsed (extras, specifiers, markers), the import search is batched,
  and runtime-loaded packages (`uvicorn` in a `CMD`, `psycopg2` in a URL, pytest plugins) cap at
  `likely_safe`. Unused env vars are also searched in compose/CI/Dockerfiles and capped for
  bundler-prefixed, library-convention and platform variables.
- **Three states on the dashboard.** Every agent returns an `## Unavailable checks` block (no git
  history for age rules, `gh` absent for TODO lookups, audit tool missing) and the report shows
  "unavailable" rather than a 0 that reads as clean — the v2.8.0 rule, applied here.
- **`quick_win` is a closed set** (empty file, backup-suffixed file, 5+ line commented block, carve-out-clean
  unused import), defined in every scan file and reconciled in Step 2. Found by the eval re-run, not the
  review: the tag had no definition, so scanners marked whole modules and CSS rules `quick_win: true` and
  both orchestrators had to override them by hand before `--fix` — one loose tag away from an unconfirmed
  deletion. Opt-in sections not requested are "not scanned", never "unavailable".
- Step 1 states that agent `tools:` lists declare intent and the scan instructions are the boundary
  (S61), passes scan files by absolute path instead of inlining ~640 lines, and defines what two
  filter flags do (dispatch only the owning agents). "5 or more" commented lines everywhere.

## 2.12.2 — 2026-10-21

The third and fourth `/bx:evolve` runs of the day (delta on 5 of 23 pages, then `--fix` with every
lane current). One doc fix.

### Fixed

- **`task-tools.md` states the documented allowlist rule** (tools reference, v2.1.268+): task
  tools are on by default only on Opus 4.7 / Sonnet 4.6 / Haiku 4.5 and earlier; every other
  model opts in via `CLAUDE_CODE_ENABLE_TODO_TOOLS=1`, `--allowedTools` or `--tools`; background and
  cloud sessions always have them; subagents follow the session; `CLAUDE_CODE_ENABLE_TASKS=0` swaps
  in `TodoWrite`. The presence check is unchanged. (Was a v2.1.233 denylist.)

### Known

- A changed inventory hash forces a full page re-read even when the delta is one renamed token;
  this run narrowed the scan by hand (new page + pages mentioning the token). The probe should
  compute the delta from the last committed `capabilities.json` and do this itself.

## 2.12.1 — 2026-10-21

The first two `/bx:evolve` runs on 2.12.0 (delta with all 22 pages, then `--fix` with every lane
current) and what they found.

### Fixed

- **Pain-registry matching threshold is `min(3, lead word count)`.** A two-word lead such as
  `Dogfood /bx:health` could never share three words with its own entry and spawned a duplicate id.
- **State validator accepts the pinned vocabulary.** The capability pattern rejected
  `tool:KillShell` and `builtin:code-review-ultra` (`:` and tool-name case); widened to
  `^bx:[a-z0-9-]+/[A-Za-z0-9:/_.-]+$`, schema normalization text aligned.
- `--fix` applied three findings: `/bx:clean` step 10 no longer promises `/rewind` for `git rm`
  deletions (checkpointing docs); `/bx:webdesign` names `TaskStop`, not `KillShell`
  (tools reference); ultrareview wording follows the docs (fleet, 15–25 min, cost note,
  `/ultrareview` is an alias). `env-vars` pinned on the docs allowlist; inventory regenerated.

### Known

- Allowlist candidates are not persisted between a delta run and its `--fix`; this run carried
  one by hand. A `source_url` match with two stored candidates has no tie-break rule (larger
  file overlap was used). A regenerated inventory hash triggers a full 22-page re-read next run.

## 2.12.0 — 2026-10-21

The two `/bx:save --full` defects found by v2.10.0's first real run (S61), the three `/bx:evolve`
defects found by 2.11.0's first runs, and the four S61 `/bx:evolve` improvements: the shared lane
contract, the docs-lane page-hash map, the pinned capability inventory, and the community lane
re-scoped to an official-source discovery feed.

### Added

- **Pinned capability inventory** — `bx/skills/evolve/capabilities.json`, generated by
  `bx/skills/evolve/scripts/build-capabilities.py --write` from frontmatter keys and their tools,
  backticked built-in commands, a fixed idiom table and hooks.json (435 entries at pin time). It is
  the only legal vocabulary for `affected_capability`, so `finding_id` no longer drifts with a
  lane's wording. Step 0.2 runs `--check`; drift is reported in the footer and offered as a
  regeneration item in `--fix`. The docs lane's `inventory_hash` is derived from the same file.
- **Community lane is a discovery feed.** `scan-community.md` rewritten: it searches only official
  domains and `anthropics/*` maintainer posts for pages the docs allowlist lacks, returns them as
  `allowlist_candidates` with the contract they own and the bx token that depends on it, and emits
  no findings (`findings: []`). Report Section 3 renders the candidates; the advisory table is
  gone. Rationale: degraded in 5 of 6 runs, never fix-eligible, and its real value was the official
  pages it found.

- **`bx/skills/evolve/references/lane-contract.md`** — the named owner of what the three scan lanes
  share: inputs, relevance filter, `affected_files` via Grep, the finding schema with a per-lane
  value table, the sentinel, `lane_status` consequences, the shared hard rules and footer keys. The
  three scan files now cite it by section and keep only their method; the restated copies had
  drifted (the `allowlist_candidates` definition existed in three wordings). SKILL.md Step 2 tells
  every lane agent to read it after its scan file.
- **Docs lane reads only changed pages.** `bx/skills/evolve/scripts/docs-page-hashes.py` (read-only)
  fetches each allowlisted page's markdown rendering (`<url>.md`, which code.claude.com serves as
  text/markdown — verified for all 22 pinned pages, hash stable across fetches), hashes it, and
  compares with the new `watermark.docs_pages` map; `watermark.inventory_hash` forces a full
  re-read when the capability inventory itself changed. The orchestrator passes `pages_to_scan`
  to the lane, marks the lane `current` when the list is empty, and stores hashes at Step 6 only
  for pages fetched successfully. The validator checks both fields; state.json migrated to the
  six-key watermark with an empty map, so the first 2.12.0 run reads every page once.

### Fixed

- **The `--full` sweep now runs before the writer dispatch.** Parts 0.5/2/3/4/1.10/5/6/7 ran after
  `save-writer` had already written the session entry, so a run's own rollups, moves and rotations
  could never be recorded in the session that produced them (S61 wrote them by hand). The Full
  Path is now a nine-step sequence: drain, sweep reads, settle the packet's three content lists,
  sweep, compose the packet from the post-sweep files, dispatch, re-measured drift probes, one
  commit, report. The session entry carries a `Full sweep:` bullet when anything changed. Part 5's
  window, Part 6's count and 7.7's cut now account for the entry the writer has not appended yet,
  and Part 7.3 leaves packet-owned Known Issues entries (resolved or reworded this session) to the
  writer.
- **Known Issues open phase qualifies by the saving, not a 300-char floor.** The replacement line
  itself runs 200–280 chars, so the floor let a 350-char entry be moved to save 70 chars. An entry
  now qualifies only when it is at least 500 chars longer than its composed replacement line. The
  7.4 prompt gains a *looks resolved — confirm* heading for open-classified entries the orchestrator
  can see are fixed (conversation, or a named commit in `git log`); the S60 status-form test is
  unchanged — the user reclassifies, not the classifier.
- Lint: K20 pins the new rule; new K23 pins the sweep order and the packet-owned exclusion.
  `verification-checklists.md`'s `--full` item inverted to match.
- **`/bx:evolve` skips lanes whose watermark equals their head** (Step 1.5). The changelog head
  comes from `git ls-remote --tags` on anthropics/claude-code; docs and community are current when
  checked today. A current lane is not dispatched, reports `lane_status: current`, and leaves its
  watermark field as is; `--full` dispatches all three regardless. A `--fix` run minutes after a
  delta run had re-fetched 15 docs pages (~180k tokens) to re-emit stored entries.
- **`--fix` staleness re-grep classifies the edit's shape first.** A replacement probes for the old
  token (absent = done); an additive edit probes for the new text with the sense inverted
  (present = done); an ambiguous edit gates on all its files instead of being parked as
  `[no re-grep token]`. The old rule read an additive edit's untouched file as "no token" and
  would have narrowed it away.
- **Pain-id match joins same-concern findings across releases** (Step 3.4, third lookup). A live
  `bx:pain/<id>` finding with no `finding_id` or `source_url` match adopts a stored entry with the
  same pain id, appending the new release to its `citation`; the hash comparison is skipped
  because a different release is not "the source changed". `dadac845`/`6712a71e` were this case.

## 2.11.1 — 2026-10-20

The first two real `/bx:evolve` runs on 2.11.0 (delta 2.1.284 → 2.1.306, then `--fix`), applied
through the new carry-forward gate. Doc and instruction fixes only; no behaviour change in any skill.

### Fixed

- **`/plugin update bx` has no session form.** `update` is a shell-only subcommand; typing it after
  `/plugin` just opens the Discover tab (observed: the cache stayed at 2.10.0). README, workflow.md,
  fix-mode-evolve.md and mode-update.md now say `/plugin marketplace update burak-tools` (session),
  `claude plugin update bx` (shell), `/reload-plugins` (session). `/reload-skills` is named for
  SKILL.md-only refreshes.
- **Agent `tools:` specifiers are not enforced.** Verified live: an agent declared `Bash(gh:*)` ran
  `echo` and `git`. The 17 scoped lists stay as declared intent; the S43 rule in evolve SKILL.md,
  README's agents paragraph and docs/architecture.md now say the in-Bash discipline is prompt-enforced.
- `/bx:webdesign` Phase 3e asks the user before its destructive-git rollback and stops on an auto-mode
  denial (closes findings `dadac845` + `6712a71e`; live verification on the kaanarik run still owed).
- `/bx:evolve` docs and community lanes handle WebFetch truncation (re-fetch with `offset`, else
  `pages_failed: truncated`) — this run's docs lane had read the hooks page to ~100k of 270k chars.
- workflow.md's `/bx:review` rationale reflects v2.1.290 (`/code-review` at medium effort reports
  CLAUDE.md-convention findings).
- Seven doc pages pinned in the docs-lane allowlist (`code-review-local`, `ultrareview`,
  `plugins/manifest-reference`, `plugins/marketplace-reference`, `plugins/components`,
  `permission-modes`, `tools-reference`); `install`, `scheduled-tasks`, `settings-reference` declined.
- `session-start-context.sh` comment on CLAUDE_ENV_FILE plain assignments (CC 2.1.296).

### Known (recorded in CLAUDE.md Known Issues)

- `--fix` re-runs all three lanes even when the watermark is current; the re-grep misreads additive
  edits; same-concern findings from different release URLs are not joined.

## 2.11.0 — 2026-10-20

`/bx:evolve` revision, phases 1–7 of `docs/superpowers/plans` S61 (plan file: Revise /bx:evolve). Every
phase was gated by a blind rehearsal on a committed fixture under `bx/skills/evolve/tests/fixtures/`
and by the new state validator; the first real run after install is the acceptance test.

### Added

- **Carried-forward findings are actionable.** Every `open` decision-log entry stores
  `proposed_edit`, `affected_files`, `source_excerpt` and `citation`, so `--fix` gates
  Section 4 entries too. A staleness re-grep runs first: token absent from every affected
  file → the entry auto-closes as `applied` with a dated note and is listed in the pre-pass
  summary; partial hits narrow `affected_files`; prose-only edits are display-only.
- **Pain registry** `docs/upstream/pain-points.json`: pain points get stable ids that survive
  rewording (eight pre-2.11.0 slugs covered five concerns). `/bx:evolve` is the only writer;
  Step 0.3 now reads Known Issues from CLAUDE.md and Next Steps from `docs/STATUS.md`, where
  schema v2 moved them in S56. Lanes receive `{id, text}` and copy the id into `bx:pain/<id>`.
- **`applied` branch in Step 3.4** (state-schema Rule 6): unchanged → suppressed with a footer
  count; changed → `[re-raised — source changed since application]`. A finding with no exact
  `finding_id` match is matched to a stored entry by `source_url` + overlapping files, so a
  reworded capability string no longer re-enters the log beside its own applied twin.
  Same-class, same-URL, overlapping-files findings collapse before hashing.
- **Changelog pagination with a recorded gap.** The lane paginates (≤10 pages) to the
  watermark, comparing versions numerically so a yanked tag slices at the next older release;
  cap before the anchor records `watermark.changelog_gap`, rendered in Section 1 and the
  headline until a later run or `--full` closes it. End of history before the anchor is not a gap.
- **`allowlist_candidates`** footer field in all three lanes (replaces the community lane's
  unactioned `official_source_found:` scan note), rendered in the report and offered in
  `--fix` as a one-row edit to the docs-lane allowlist. `auto-mode-config` pinned.
- `bx/skills/evolve/tests/check-state.py` + `test-check-state.sh`: mechanical validator for
  `state.json` and the registry (schema order, 40-hex hashes, `finding_id` recompute, enum,
  registry cross-check), wired into the `plugin version bump` CI workflow.

### Changed

- `docs/upstream/state.json` migrated: 13 keys per entry, `changelog_gap: null`, sentinel
  hash `000…0` replaces five empty hashes, 18 pain-slug entries re-keyed to registry ids
  (`161ae182 → fe90acdf`, `55ba40ea → 5b91feb3`, `7e849e74 → 727810cc` among them). The 18
  open findings were hand-triaged: 10 rejected, 1 applied, 5 deferred, 2 kept open with edits.
  Script kept at `bx/skills/evolve/tests/fixtures/migrate-2-11-0.py`.
- Default-mode closing line is an honest upper bound (`up to N fix-eligible … K legacy, D deferred`).
- Report Section 4 gains an `Edit?` column; the footer's decision-log block has six fixed lines.
- Community lane's slot-3 query uses the first active pain point (pain points carry no severity).

### Fixed

- Step 0.3 read `## Next Steps` from CLAUDE.md, a section schema v2 had moved to STATUS.md.
- Delta runs lost everything older than the 50-release window and still advanced the watermark.
- Five stored `source_content_hash` values were empty strings; the validator now rejects that.

## 2.10.0 — 2026-09-28

### Added

- **`docs/known-issues.md`, a fifth auto-managed archive.** `## Known Issues / Blockers` was the
  one required CLAUDE.md section with no cap, no shrinker and no archive destination; a field
  `/doctor` run found it at 14.9k chars, 48% of a 31.1k CLAUDE.md. Issues that leave CLAUDE.md
  now land here, one `### ` entry each, tagged `Resolved` or `Open, moved`. Rotates at 100k like
  the other archives; rotation never cuts past the first `Open` entry that CLAUDE.md still
  links to.

- **Known Issues shrinker (Part 7.3).** Threshold 4000 chars. Resolved entries move first, until
  the section is under 2500 or none remain. Open entries move only while the section is still
  over 4000, and each leaves a one-line summary + link behind. It runs on `--full` only, only
  when CLAUDE.md is over its 12k soft cap, and only with consent (never under `--silent`); the
  consent prompt lists which entries it classified as resolved and which as open. "Resolved"
  needs a status form in the entry's lead (`RESOLVED`, `is resolved`, a checked box): the bare
  word does not count, so "paths are resolved against cwd" stays open.

- **9k advisory rung (Part 1.9).** Nothing acted between the ~7k target and the 12k soft cap.
  Between 9k and 12k the save now names the largest section. No shrinker fires below 12k.

- **Derivable-content clause.** A fact one command recovers (stack, remote, cwd) may leave
  `## Project Overview`. Advisory only: `/bx:save` names candidates and removes nothing.

- **`omitClaudeMd: true` on the three `upstream-*` subagents** (Claude Code 2.1.271+). They run
  only in this repo and take everything from the dispatch prompt, so they no longer load
  CLAUDE.md. Every scanner that reads a target repo (arch, test, cleanup, seo, geo) keeps it:
  that repo's recorded decisions are what stop a scanner flagging deliberate design.
  (`/bx:evolve` finding `c0379ca1`.)

- **`/bx:health` declares `disallowed-tools: Edit, Write, NotebookEdit, Agent`**, enforcing the
  read-only invariant its prose already stated. (`/bx:evolve` finding `10294db5`.)

- **Version-bump guard outside the skill.** `scripts/check-plugin-version-bump.sh`, an opt-in
  `.githooks/pre-push`, and a GitHub Actions workflow fail when `bx/` changed but `version` did
  not. Until now only `/bx:save` Part 8 checked, so a hand-made push had no guard.

### Changed

- **Resolved issues are relocated, not deleted.** Part 1.7 said "Remove resolved issues", the one
  place `/bx:save` contradicted its own *content moves, it does not disappear* rule. They now
  travel in a new `known_issue_moves` packet field, and `save-writer` archives first and removes
  second. An issue is resolved only when the session says so, never because it went unmentioned.

- **Part 7.3's tolerated-as-is clause covers project-specific sections only.** A required section
  falling through it is now a reportable bug.

- **Size is measured in chars, not lines.** doc-schema.md says so explicitly, and names
  `/doctor prompt-audit` (2.1.283+) beside the `/doctor` trim check. Anthropic's 200-line
  guidance passes a 62-line CLAUDE.md that measures 13.6k chars. (`/bx:evolve` finding `55ba40ea`,
  partially applied; the `.claude/rules/` tier stays gated.)

- **`/bx:evolve`'s docs lane watches three more pages:** `plugins/loading`,
  `plugins/cli-reference` and `plugin-evals`, which now own contracts the older `plugins` and
  `plugins-reference` URLs no longer carry.

### Fixed

- **`/bx:resume` and `/bx:health` injected commands their `allowed-tools` did not list.** Inline
  `!` injections used `echo` and `head`; since Claude Code 2.1.271 auto mode applies
  default-mode permission rules to them, and 2.1.284 made auto mode the default. Both lists now
  name what the injections run. (`/bx:evolve` finding `2e4e9a8b`.)

- **`/bx:health` read session state from CLAUDE.md**, where doc schema v2 no longer keeps it, so
  on a migrated repo it saw empty `In Progress` and `Next Steps`. It now reads
  `docs/STATUS.md` when that file exists and names the file it read.

- **Doc notes:** fix-mode-evolve.md lists v2.1.268 as a third unverified data point on
  `/reload-plugins`; setup-stitch-mcp.md names `claude mcp login stitch`. (Findings `ee81fa43`,
  `7e849e74`.)

## 2.9.0 — 2026-09-08

### Changed

- **`/bx:save` is model-invocable again.** S42 flipped `disable-model-invocation` to `true` to
  make the skill explicit-only. Per the official skills reference, that flag also removes the
  skill's description from Claude's context, so Claude could not run the end-of-session save
  itself and always asked the user to. Flipped back to `false` (`/bx:plan` already was), and
  `/bx:resume`'s wrap-up step now says to invoke `/bx:save` via the Skill tool rather than
  "remind user". The save's own consent gates (migration, commit) still apply when Claude
  invokes it. workflow.md's `/loop` caveat no longer claims every bx skill is explicit-only.

- **`/bx:save` Part 8 step 2b judges `claude plugin validate` by its `--json` report.** Both
  invocations (`./bx --strict` and the marketplace `.`) now pass `--json` (Claude Code 2.1.259+)
  and the pass/fail verdict comes from the top-level `success` field plus `manifest.errors` /
  `manifest.warnings`, not from reading prose. Older CLIs that reject the flag fall back to the
  prose path. (`/bx:evolve` finding `83d36fa2`.)

- **`/reload-plugins` headless note.** Both places that tell the user to refresh the plugin cache
  (fix-mode-evolve.md post-pass steps, setup-stitch-mcp.md) now note the command also works in
  headless `-p` / SDK sessions since Claude Code 2.1.260. (`/bx:evolve` finding `e6fab951`.)

- **doc-schema.md names `/doctor`'s trim check.** The owner of the CLAUDE.md contract now states
  the derivable-content rule and cross-references mode-update.md Part 4.3, so a `/doctor` trim
  proposal (Claude Code 2.1.206+) reads as input to the size target rather than licence to drop a
  required section. (`/bx:evolve --full --fix` finding `c0a336b6`.)

### Removed

- **`bx/scripts/session-start-context.ps1`.** Never wired: `hooks.json` registered only the `.sh`
  from the day the `.ps1` was added, and the official hooks reference lists no per-OS command
  field, so the file could only ever run behind a dispatcher wrapper that cannot be verified from
  a Mac. The `.sh` already runs on Windows via Git Bash. `.sh`-only is now the deliberate scope;
  README tree, CLAUDE.md Known Issues and STATUS.md updated. (`/bx:evolve` finding `7b54fbc1`.)

## 2.8.0 — 2026-08-24

### Fixed

- **`/bx:tests` severity was uncalibrated for small repos.** Found by the first full `/bx:tests`
  run. `priority = density × (1+log10(churn+1)) × (1+log10(fan_in+1))` is a density ≤1.0 times two
  log terms, so it only reaches the mapped thresholds of 2.0/5.0 on repos with churn and fan-in in
  the dozens-to-hundreds. This repo's own audit scored **0.08–0.18 across all 7 source files** — a
  literal mapping labels everything `low`, including a same-day concurrency fix shipped with no
  regression test. `priority_score` now **ranks but does not grade**: severity comes from a
  blast-radius table (auth/credential path or a behaviour-changing `bug_fix_no_test` → high; runs on
  every invocation → medium; leaf or unconfirmed-reachable → low). The score and factors are still
  emitted verbatim as the ranking's audit trail.

- **`coverage_gap_total` double-counted overlapping findings.** A whole-file finding and a range
  finding inside that same file both summed into the headline — the audit reported 2,461 where the
  unique figure was 2,382. Each source line now counts once; both findings still surface separately.

### Added

- **`coverage_negatives`** — the channel `/bx:tests` lacked for "I swept this and found nothing",
  mirroring the `/bx:arch` fix in v2.4.0. Without it a scanner told to report empty categories
  honestly has nowhere to put that and encodes it as a `severity: low` finding with no action, which
  then ranks.

  This version is sharper than `/bx:arch`'s: it distinguishes **three** states, not two.
  `unavailable` means the precondition is absent (no snapshot mechanism, no CI, no mocking layer);
  `clean` means the category applies and was genuinely checked. Reporting `unavailable` as `clean`
  claims coverage the scan never had. Declared in Step 4, collected at Step 5, rendered in the
  footer. The distinction came from the run itself — the economics scanner produced it only because
  the dispatch prompt asked for it by hand.

## 2.7.0 — 2026-08-24

### Fixed

- **`/bx:tests` resolved its stack from a planted eval fixture.** Found by the first `/bx:tests`
  dogfood, which halted at Step 0 before dispatching anything. The only `package.json` in this repo
  is `bx/skills/clean/evals/fixtures/node-react-app/package.json` — a synthetic project the
  `/bx:clean` eval suite grades against, declaring `"test": "vitest run"`. Executed literally, Step 0
  detects Vitest from it and audits fabricated code, reporting *deliberately* planted dead tests as
  real findings while the run looks successful. The charitable reading is no better: exiting with
  "no test framework detected" on a repo whose 5 shell scripts carry **68 working assertions**.

- **Shell and PowerShell harnesses are now a recognised test framework.** The detection table had no
  row for them, so a suite with a `pass`/`fail` discipline was invisible even though it has
  assertions and gates commits. Coverage tooling is `none`, so they run heuristic-only. The exit
  message now also names the exclusion that suppressed a manifest, since "no framework detected" on
  a repo containing a visible `package.json` otherwise reads as a bug.

### Added

- **`bx/skills/arch/references/scan-exclusions.md`** — canonical owner for what a repo-wide scanner
  must never read: synthetic/fixture trees, vendored and generated dirs, immutable history. It
  governs **stack detection as well as file scope**, which is the half that was missing: a fixture
  tree carries its own manifests, so excluding it from scanning but not from detection still poisons
  the run.

  `/bx:arch` (Step 3 + 5 agents + `scan-robustness.md`) and `/bx:tests` (Step 0 + Step 3 + 3 agents
  + 3 scan files) now cite it — 14 sites that previously carried their own copy of the vendored list.
  13 further restatements in `/bx:seo`, `/bx:webdesign` and `/bx:clean` are listed in the owner file
  as pending rather than silently tolerated.

  Until now the fixture guard existed only as a hand-written exclusion in the `/bx:arch` dogfood's
  dispatch prompt — which meant it protected exactly one run and nothing else.

## 2.6.0 — 2026-08-24

### Added

- **`/bx:save` Part 8 now runs the official plugin smoke test** (`/bx:evolve` finding `b5659902`,
  docs lane). After the version bump and before the commit, step 2b runs
  `claude plugin validate ./bx --strict` plus `claude plugin validate .` for the root marketplace
  manifest. `--strict` is deliberate at a commit checkpoint: unrecognized frontmatter keys and
  missing metadata are tolerated by the runtime but are exactly the drift this catches.

  A validation warning is **information, not a veto** — a failure surfaces the output verbatim and
  asks fix-now-or-commit-anyway rather than blocking on the skill's own judgement. `--silent`
  reports and commits anyway (its contract is zero prompts, and silently skipping a commit would be
  worse than committing something that warns). A missing `claude` binary skips silently, so an older
  harness never fails a save.

  `bx/skills/save/SKILL.md` `allowed-tools` gained `Bash(claude:*)` — without it the new step would
  prompt on every save, which is the S45 enumeration rule. Dogfooded on itself: bx and the
  marketplace manifest both pass plain and `--strict`.

  This closes the "install smoke-test" half of the S37 plugin-packaging leftovers, open since
  Session 37.

## 2.5.1 — 2026-08-24

### Fixed

- **Lost update in `gsc-parse-helper.py`'s finding-history / watchpoints writes** (dogfood
  finding C02). `_atomic_write_json` made the final `os.replace` atomic — its own docstring says
  the PID-suffixed tmp exists so "two concurrent /bx:seo processes writing the same target don't
  interleave content" — but that only closes half the race. Two runs could still read the same
  pre-mutation state and have the second replace silently discard the first's additions: a
  `run_count` increment reverts, a watchpoint refresh vanishes, and the escalation threshold
  downstream then misses a regression because the increment never persisted.

  `history_update`, `watchpoint_emit` and `watchpoint_check` now hold an `O_EXCL` advisory lock
  across the whole read-modify-write, degrading to unlocked after ~10s so a run is never blocked.
  Measured, not assumed: 12 concurrent processes without the lock lost **10 of 12** updates; with
  it, 12/12 survive and no stale lock remains.

  The lock deliberately does not age-check inside its retry loop, for the reason documented in
  v2.5.0's shell fix — a check that fails for any reason reads as "stale", unlinks a live lock,
  and admits several writers at once.

## 2.5.0 — 2026-08-24

### Fixed

- **Session-color registry race** (`session-color.sh` / `.ps1`, dogfood finding C02). The
  read-decide-append had no lock, so two launches in the same window both observed the same
  registry state and claimed the same color — defeating the "distinct AND stable" goal the
  registry exists for. Both twins now take a `mkdir`-based mutex (atomic on every platform) with
  a ~10s budget, after which they proceed unlocked: the worst case is the old behaviour, never
  worse. Verified with real concurrency, not by inspection — 5/5 trials of 8 simultaneous
  launches now yield 8 distinct colors and no duplicate rows, on both bash and PowerShell.

  Two bugs were found *in the fix itself*, both only by running it:
  a 100ms backoff let 8 racers take ~4.1s against a 5s cap, so late processes fell through to
  the unlocked path and collided anyway (now 20ms/10s); and an age check inside the retry loop
  ran `find` on every iteration where any failure read as "stale" and `rmdir`'d a **live** lock,
  admitting several processes to the critical section at once — worse than no lock. Reaping now
  happens once, only after the budget is exhausted. Both hazards are documented in the code so
  they are not reintroduced.

- **SessionStart hook: 3 `git rev-parse` spawns collapsed to 1** in both twins. The hook runs on
  every session launch against a stated `<1s` budget, so three processes to learn three values
  was two too many. Output order verified (`true` / toplevel / branch) and the out-of-repo path
  still exits 0.

- **`doc-structure-rules.md` no longer restates `doc-schema.md`.** Its Target State table
  independently duplicated the file layout, size targets and rotation mechanics with no citation,
  violating this project's own named-owner decision — and `check-doc-rule-consistency.sh` does not
  cover that file, so the drift checker could not see it. Collapsed to a pointer plus the two rows
  the schema genuinely does not own (16 lines).

## 2.4.1 — 2026-08-24

### Fixed

- **`/bx:arch --fix` pass over its own dogfood findings** (behavior-preserving refactors,
  verified rather than assumed):
  - `gsc-parse-helper.py`: extracted `_threshold_status(b, c, invert=False)` from
    `_watchpoint_status`'s three near-identical threshold blocks (CCN 18 → 7, cognitive
    20 → 8) and `_median_ctr(rows)` from its two verbatim copies; `detect_brand_anomaly`'s
    two filter loops became comprehensions (CCN 5 → 3, cognitive 6 → 1). Equivalence proven
    against the pre-refactor semantics across 162 threshold cases (both `invert` directions,
    including every `b <= 0` edge) and 11 median sizes: 0 mismatches.
  - `assert-doc-schema.sh`: flattened a 4-level nested guard in the `## Environment Variables`
    arm (CCN 3 → 3 unchanged, cognitive 8 → 4) — the R01 shape the dual-metric gate exists to
    preserve. The De Morgan inversion was exercised in all three directions with a purpose-built
    fixture: populated+present passes, populated+missing fails correctly, unpopulated+missing
    passes (the deliberate drop exception). All 10 doc-schema fixtures still pass.

## 2.4.0 — 2026-08-24

### Fixed

- **`respects_documented_decision` was being set backwards, and the exclusivity rule buried the
  result.** Found in the first end-to-end `/bx:arch` dogfood: all five robustness findings — the
  most valuable in the run — came back `false`, though nothing documented opposes adding a lock or
  a timeout. The scanner read the flag as "this code violates a decision" instead of "my
  *recommendation* collides with one", and because Step 5.8 makes that group exclusive, all five
  left the actionable lists. `finding-rubrics.md` now states the rule as a two-question decision
  procedure with a worked table (including the row that trips scanners: a finding whose fix
  *restores* a documented goal is `true`), and Step 5.7 gained the inverse check — an unsubstantiated
  `false` is treated as `true` for grouping and named in the report, with a majority-`false` sanity
  check for whole-scanner inversion.

### Added

- **`coverage_negatives`** — a channel for "I swept this category and it was genuinely empty".
  Scanners were told to report empty categories honestly but had nowhere to put them, so they
  encoded negatives as `severity: low` findings with `recommended_refactor: "None"`, which then
  ranked and polluted the tables. Declared in the finding contract, collected at Step 5.6, rendered
  in the report footer.
- **Notable pairs** — a two-finding cluster sharing one concrete root mechanism does not qualify as
  a theme and is no longer silently dropped either; it renders as a single line under the themes.
  The dogfood surfaced two: unlocked read-modify-write across `session-color` and the GSC helper's
  history writes, and the SessionStart hook's timeout + subprocess pair.

### Changed

- Step 4 passes reference files to subagents **by absolute path** rather than inlining their
  contents — the documented approach required the orchestrator to hold ~95k chars to compose five
  prompts, for text the agent reads itself either way.

## 2.3.0 — 2026-08-24

### Fixed

- **Three `/bx:arch` rules that made the architecture worse.** `S01` recommended deleting
  Dependency Inversion — a port has exactly one adapter by design — and is now hard-suppressed
  at any layer boundary named in the Intended Architecture summary. `S06` deleted validation at
  trust boundaries, where a type annotation is a compile-time claim about a runtime the compiler
  never sees; it is now suppressed within one hop of deserialization, env reads, FFI, ORM row
  mapping, or an entry point. Both report suppressions rather than discarding them.
- **The complexity gate deleted the catalog's own quick wins.** `R01` and `R09` state "CCN
  direction: unchanged", so a CCN-only gate dropped every finding citing them. Root cause was a
  metric mismatch: the catalog reasons about *cognitive* complexity, the skill only measured
  *cyclomatic*. Cognitive complexity is now measured (`eslint-plugin-sonarjs` where present, a
  nesting-weighted heuristic everywhere else — no other linter reports it), and the gate drops a
  finding only when it reduces neither metric.

### Added

- **Three dimensions that had zero coverage**, as 31 new catalog entries:
  `catalog-design.md` (D01–D08 — LSP, ISP, DIP, Law of Demeter, anemic domain model, feature envy,
  primitive obsession, god class) and `catalog-robustness.md` (C01–C08 concurrency and thread
  safety, E01–E08 error safety and resource lifecycle, X01–X07 architectural scalability). Every
  entry carries language tags, a greppable trigger, a severity signal naming what actually fails,
  and false-positive guards. None is `--fix`-eligible: adding an `await`, a timeout or a lock
  changes runtime behavior a diff preview cannot show, and `--fix` runs no tests.
- **A fifth scanner, `arch-robustness`**, owning C/E/X. It asks a different question from the
  other four — not "is this hard to read?" but "what happens when this runs twice at once, when
  the network hangs, or when the table has ten million rows?" It builds an entry-point map before
  scoring, and reports findings whose dependencies it could not resolve rather than staying silent.
- **A calibrated finding contract** (`finding-rubrics.md`, canonical owner): anchored severity,
  certainty defined by evidence class rather than confidence, effort anchors, and two mandatory
  fields — `evidence` (the work behind the certainty band) and `why_this_might_be_wrong` (the
  skill's only adversarial pressure).
- **A report that opens with a judgment**: the top 3 architectural themes, each a thesis naming a
  structural cause, its evidence set, and one highest-leverage first move. Findings outside a theme
  still render in full below. Ranking now multiplies by `churn × fan-in`, so findings are ordered
  by where change actually hurts.
- **Layering analysis when nothing is documented** — previously skipped entirely, which is the
  common case. The dominant import direction per module pair is inferred and minority-direction
  imports are reported as violations of the codebase's own convention, capped at 0.7 certainty.

### Changed

- `refactor-catalog.md` split per prefix (`catalog-rules.md` + `catalog-refactors.md` +
  `catalog-simplification.md` + the two new files); each agent receives only its own entries, so
  token cost stays flat while the catalog grows from 23 entries to 54.
- Per-agent finding caps 30 → 15 (performance 20 → 15).
- `/bx:tests --plan` no longer advertises a "TaskCreate-ready brief"; `/bx:health` describes the
  six dimensions and the thesis-first report.

## 2.2.0 — 2026-08-24

### Fixed

- **Task-tracker tools are no longer assumed present** (upstream finding `5d1459d5`,
  claude-code v2.1.233 removed `TaskCreate`/`TaskGet`/`TaskUpdate`/`TaskList`/`TodoWrite`
  from the default toolset on Opus 4.8, Sonnet 5, Fable 5, Mythos 5 and newer;
  `CLAUDE_CODE_ENABLE_TODO_TOOLS=1` restores them). Five skills promised behavior that
  silently could not run:
  - `/bx:arch --plan` and `/bx:tests --plan` no longer advertise a "TaskCreate-ready
    brief" — both hand off to `/bx:plan`.
  - `/bx:plan` Step 6, `/bx:resume` Step 5, and `/bx:save` Part 0 gate their tracker
    calls on an availability check.

### Added

- **`bx/skills/save/references/task-tools.md`** — canonical owner for the task-tool
  availability rule (the fact, the check, and a per-skill degraded path). The five
  satellites cite it; none restates the version, model list, or env-var name.
- **Degraded paths** so every affected skill still completes its job with the tools
  absent: `/bx:resume` folds the same task selection into its summary as a numbered
  list; `/bx:save` behaves as `--skip-tasks` and derives deltas from the conversation;
  `/bx:plan` treats the approved plan document as the tracker and keeps per-phase
  gating. Tracker paths are demoted, never deleted — they run whenever the tools exist.

## 2.1.1 — 2026-08-18

### Fixed

- **`/simplify` cleanup wave over the v2.0.0–v2.1.0 range** (reuse, simplification,
  efficiency, altitude — no behavior additions):
  - `save-writer`'s anchored tail reads now return line numbers only (`-o`, no
    `head_limit` truncation) instead of echoing ~98% of the archive content back; Part 5.1
    no longer full-reads `session-history.md` before the windowed rollup.
  - Part 7.7 rotation moves bytes with one byte-exact shell split instead of a
    Read→Write round trip through model context; consent prompts batch when several
    archives qualify; the sentinel phrase is explicitly marked un-rewordable.
  - Part 3.0's `--full` sweep also excludes dated planning records
    (`YYYY-MM-DD-*` plans/specs, e.g. `docs/superpowers/`) — immutable history it never
    rewrites (~356KB in this repo).
  - `--silent` is now a normative default rule (every consent gate, present or future,
    resolves to its safe default; the Part 8 commit is the sole exception) instead of a
    per-site enumeration.
  - `doc-schema.md` gains the canonical **Archives** section (archive set + access rule);
    Part 3.0, save/resume SKILL.md, and the README now point at their owners instead of
    restating them. `mode-migrate` Step 3 uses a declared `Bash(cp:*)` grant instead of a
    `bash -c` wrapper.
  - `assert-doc-schema.sh` derives all section checks from the single `STATE_SECTIONS`
    constant; `make-fixtures.sh` gains a `stub_docs` helper replacing five copy-pasted
    blocks (fixture output verified byte-identical); `session-start-context.sh` drops its
    redundant `|| echo 0` defaulting.

## 2.1.0 — 2026-08-18

### Added

- **Archive rotation** (`/bx:save` Part 7.7, `--full` only): when a history archive
  (`session-history.md`, `key-decisions.md`, `completed-work.md`) exceeds 100k chars, its
  oldest entries move byte-verbatim into numbered volumes under `docs/archive/`, leaving
  the live file at ≤50k with the newest content intact. First rotation asks for consent;
  a header note is the sentinel. Volumes are read by nothing automatic — not deep resume,
  not the `--full` doc sweep — they are grep-on-demand history. No volume-count cap:
  pruning is a manual `git rm` (content survives in git history). `--skip-rotation` skips
  the Part.

## 2.0.1 — 2026-08-18

### Fixed

- `/bx:save` no longer pays costs that grow with project age. The three linear read paths
  are closed: Part 3.0's `--full` doc sweep excludes the four auto-managed archives
  (`session-history.md`, `key-decisions.md`, `completed-work.md`, `next-steps-backlog.md` —
  the skill's own outputs, never sync inputs); `save-writer` appends to the archives via
  Grep-anchored tail reads instead of full-file reads; Part 5's rollup locates its
  compressible window by line number. Archive growth is now disk-only — no hot path reads
  an archive in full. (The live files were already capped: CLAUDE.md ~7k/12k,
  docs/STATUS.md ~10k/20k, enforced by Parts 1.9/5/6/7.)

## 2.0.0 — 2026-08-18

### Breaking

- **Doc schema v2.** Session state moves out of `CLAUDE.md` into `docs/STATUS.md`.
  CLAUDE.md now holds only always-loaded instructions: Project Overview, Key Decisions,
  Known Issues, and Environment Variables when populated. Repos on the old layout are
  migrated by `/bx:save` on first run, after an explicit prompt, on a clean tree, as one
  revertible commit. Nothing is deleted — content moves.
- `## Architecture Summary` relocates to `docs/architecture.md`.
- `## Environment Variables` is now conditional rather than mandatory.

### Added

- `MIGRATE` mode, `references/doc-schema.md` (the shared layout contract read by both
  skills), and the `bx:doc-migrator` subagent.
- `--skip-migrate` flag on `/bx:save`.
- `bx/skills/save/tests/` — post-condition checker, fixture builder, hook tests.

### Fixed

- SessionStart hook read `## Current Status` with a range that could not stop at
  `## Completed` and ran into `## In Progress`; only `head -12` hid it.
- `/bx:resume` re-read `CLAUDE.md`, which the platform already loads in full (~7k tokens
  per resume).
- `/bx:save` Part 3 maintained only `docs/*.md`, leaving root-level docs to drift.
- Part 4 instructed writing derivable facts into auto-memory, and stated its limit as
  200 lines rather than 200 lines **or 25KB**.

## 1.0.0 — 2026-08-11

First explicitly-versioned release. The plugin previously used commit-SHA versioning (no `version` field in the manifest), so users saw commit hashes as version identifiers.

- **Versioning:** added `version` + `displayName` to the plugin manifest; `/bx:save`'s commit checkpoint now enforces the bump; this changelog started.
- **/bx:evolve:** docs-lane pinned allowlist grown 9 → 11 pages (added `checkpointing` and `code-review`); full upstream audit run — watermark advanced 2.1.217 → 2.1.228, 4 new findings registered and applied.
- **Fixed (from the audit's `--fix` pass):**
  - Corrected the wrong "per-edit undo" checkpoint claim at 9 sites across 8 files (clean, arch, tests, seo, evolve skills + workflow.md): checkpoints are captured per user prompt, so one `/rewind` reverts a whole `--fix` batch, never a single edit.
  - README's review ladder now flags that bare `/review` is an alias of built-in `/code-review` (v2.1.223), not `/bx:review`.
  - `/bx:evolve` fix-mode notes carry the v2.1.221 "plugins activate immediately when safe" signal (hedged; manual refresh steps intact pending a smoke-test).
  - workflow.md's `/loop` + `disable-model-invocation` caveat upgraded from speculative to documented-for-scheduled-tasks, quoting Anthropic's code-review docs.
