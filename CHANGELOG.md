# Changelog

All notable changes to the `bx` plugin, newest first. Versioning follows [semver](https://semver.org). The `version` field in `bx/.claude-plugin/plugin.json` is the plugin's **update cache key**: users receive an update only when it changes, so every change under `bx/` must bump it (automated by `/bx:save`'s commit checkpoint).

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
