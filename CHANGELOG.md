# Changelog

All notable changes to the `bx` plugin, newest first. Versioning follows [semver](https://semver.org). The `version` field in `bx/.claude-plugin/plugin.json` is the plugin's **update cache key**: users receive an update only when it changes, so every change under `bx/` must bump it (automated by `/bx:save`'s commit checkpoint).

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
