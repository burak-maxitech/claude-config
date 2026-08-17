# bx Doc Schema v2 — Splitting Instructions from State

**Date:** 2026-08-17 (Session 56)
**Status:** Approved design, pending implementation
**Affects:** `/bx:save`, `/bx:resume`, `bx:save-writer`, `session-start-context.{sh,ps1}`, plugin version

## Problem

`/bx:save` uses `CLAUDE.md` as a session journal. Claude Code loads `CLAUDE.md` in full at
the start of every session and re-injects it after `/compact`. The result is that
frequently-changing session state is paid for on every request of every session, forever.

Anthropic's guidance is explicit that this is the wrong home for it. The
[best-practices exclude list](https://code.claude.com/docs/en/best-practices) names
"Information that changes frequently" and "Long explanations or tutorials"; the
[steering guide](https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more)
states "CLAUDE.md is for facts Claude should hold all the time" and recommends treating it as
"an index pointing to other files where Claude can find more information as needed."
Five of the ten sections mandated by `claude-md-sections.md` — Current Status, Completed,
In Progress, Next Steps, Session History — are by definition frequently-changing state.

### Measured evidence (this repo, 2026-08-17)

`CLAUDE.md` is 28,700 chars / 144 lines. Section breakdown:

| Section | Chars | Share |
|---|---:|---:|
| Key Decisions | 13,190 | 45% |
| In Progress | 3,375 | 12% |
| Architecture Summary | 2,669 | 9% |
| Next Steps | 2,582 | 9% |
| Known Issues / Blockers | 2,275 | 8% |
| Completed | 1,827 | 6% |
| Session History | 1,473 | 5% |
| Project Overview | 531 | 2% |
| Current Status | 443 | 2% |
| Environment Variables | 91 | 0% |

Three findings drove this design:

1. **Key Decisions is 45% of the file and fully redundant.** All **19 of 19** rows are present
   verbatim in `docs/key-decisions.md` (verified by whitespace-normalized exact full-row
   matching: 19 exact, 0 partial, 0 absent). Rationale lengths run mean 580 / median 514 /
   max 1,216 chars against the skill's own "≤2–3 sentences" cap.

2. **The rollups cannot fire at this shape.** Part 6 rolls up at >20 rows (there are 19);
   Part 7 fires only above 35k total (the file is 28.7k). The file is permanently stranded in
   a dead zone between the 17k target and the 35k trigger.

3. **`## Architecture Summary` is exactly what `/doctor` removes.** Per the
   [memory docs](https://code.claude.com/docs/en/memory), the trim check "cuts content Claude
   can derive from the codebase, such as directory layouts, dependency lists, and architecture
   overviews, and keeps pitfalls, rationale, and conventions that differ from tool defaults."
   The section is a directory tree, 8 lines of which are duplicated in `README.md`.

### Secondary findings (addressed here)

- `/bx:resume` Step 1 re-reads `CLAUDE.md`, which the platform has already loaded in full —
  roughly 7.2k tokens of pure duplication per resume.
- `session-start-context.sh:58` extracts `## Current Status` from `CLAUDE.md` with the range
  `/^## Current Status/,/^## [^C]/`. `[^C]` cannot match `## Completed`, so the range runs on
  to `## In Progress`; only `head -12` hides it today. **v2 reproduces the trap**, since
  STATUS.md also places `## Completed` directly after `## Current Status`.
- Part 0.5 (the existing v0→v1 migration) is listed under "Skipped on the Save Path" in
  `mode-update.md:67`, so it only runs on `--full`. Any new migration must run on both paths.
- `workflow.md` (55,539 chars) is maintained by nothing: Part 2 covers README only, Part 3
  covers `docs/*.md` only.
- Part 4 (auto-memory sync) instructs the orchestrator to write tech stack, commands, and key
  paths into `MEMORY.md` — derivable content, a third copy of facts already in CLAUDE.md and
  README, and contrary to the documented division where auto memory is written *by Claude*
  from its own learnings. It also states the limit as "200 lines" when the actual limit is
  **200 lines or 25KB, whichever comes first**.

## Goals

- Reduce always-loaded context from 28.7k to **~16k** chars without losing any information.
  (The follow-on compression pass, specified separately, takes it to ~7k. This spec's
  migration is mechanical only — see "Deliberate exclusion".)
- Give `/bx:save` and `/bx:resume` a single shared definition of the layout so they cannot drift.
- Migrate every existing repo forward automatically, safely, and reversibly.
- Keep `/bx:resume` read-only.

## Non-goals

- A v2→v1 downgrade path. The migration lands as one isolated commit; `git revert <sha>` is
  the downgrade.
- Compressing Key Decisions rationales as part of the migration (see "Deliberate exclusion").
- Restructuring the three append-only archives.

## The v2 schema

```
CLAUDE.md                    always loaded   ~7k target
  <!-- bx-doc-schema: 2 -->
  Last Updated: <date>
  ## Project Overview
  ## Key Decisions            ~20 compressed rows + link to docs/key-decisions.md
  ## Known Issues / Blockers
  ## Environment Variables    ONLY when non-empty
  > Session state: docs/STATUS.md

docs/STATUS.md               read on demand by /bx:resume
  Last Updated: <date>
  ## Current Status
  ## Completed                summary + link to docs/completed-work.md
  ## In Progress
  ## Next Steps
  ## Session History          last session + link to docs/session-history.md

docs/architecture.md         former ## Architecture Summary
docs/completed-work.md       unchanged
docs/key-decisions.md        unchanged
docs/session-history.md      unchanged
```

**`Last Updated:` is deliberately duplicated into STATUS.md.** After the split, CLAUDE.md may
sit untouched for weeks while state churns daily. The staleness signal must follow the state,
or `/bx:resume` and the SessionStart hook both report false freshness.

**`## Environment Variables` becomes conditional.** Anthropic's include-list covers "developer
environment quirks (required env vars)", so it earns its place when populated and is noise
when it reads "None required". *Empty* is defined mechanically, to keep the migration
non-judgmental: the section body contains no line matching `^[A-Z_][A-Z0-9_]*` (i.e. names no
variable). Anything else is treated as populated and kept verbatim.

**The marker is versioned** (`2`, not a boolean) so a future v3 reuses this machinery.
It is an HTML comment because
[block-level HTML comments are stripped before CLAUDE.md enters context](https://code.claude.com/docs/en/memory),
making the marker free at runtime while remaining greppable on disk.

## Detection predicate

Evaluated in order. Lives once, in `references/doc-schema.md`, read by both skills. (An
earlier draft of this predicate matched v1 on a 3-header subset — `## In Progress`,
`## Next Steps`, `## Session History`; that list was illustrative only. The 5-header set
below, matching `assert-doc-schema.sh`, is authoritative: it is a strict superset that also
catches a CLAUDE.md holding only `## Current Status` / `## Completed`, so it detects more
genuine v1 repos.)

1. No CLAUDE.md → **v0**; existing CREATE mode, which now emits v2 directly.
2. CLAUDE.md contains `<!-- bx-doc-schema: 2 -->` → **v2**; proceed normally.
3. `docs/STATUS.md` present (marker absent) → **partial**; a prior migration was interrupted.
   Resume it idempotently rather than starting over.
4. No marker, CLAUDE.md contains any of `## Current Status`, `## Completed`,
   `## In Progress`, `## Next Steps`, `## Session History` → **v1**; offer migration.
5. None of the above → **v0**; treat as CREATE mode.

## Migration flow

`SKILL.md` Step 1's mode table gains a fourth state. Unlike Part 0.5, MIGRATE runs on **both**
the fast path and `--full` — it is a precondition, not a sweep.

| State | Condition | Action |
|---|---|---|
| REFACTOR | only README.md | split; emits v2 |
| CREATE | no docs | create from scratch; emits v2 |
| MIGRATE | v1 per `doc-schema.md` | migrate, then fall through to UPDATE |
| UPDATE | v2 | normal save |

1. **Detect.** Free — Step 0 already reads CLAUDE.md; adds one Glob for `docs/STATUS.md`.

2. **Clean-tree guard.** If `git status --porcelain` is non-empty, **skip migration and
   continue with a normal v1 save.** Migration is opportunistic and must never block the work
   the user came to do. Report once; re-offer next run.

3. **Consent gate**, reusing Part 5.2/6.2 sentinel semantics exactly — including
   `--silent` ⇒ *declined*, no marker written, re-asked on the next interactive run. The
   prompt states the concrete delta: sections moved, chars before/after, "nothing is deleted,
   content moves", "lands as one revertible commit". Honors `--skip-migrate`.

4. **Dispatch `doc-migrator`** (Sonnet) with a migration packet. Mechanical surgery only.

5. **Verify invariants, then commit** as one docs-only commit, separate from the session save:
   `docs: migrate to bx doc schema v2 (CLAUDE.md → STATUS.md split)`.

6. **Fall through to UPDATE** on the v2 layout.

### Deliberate exclusion: rationale compression

Migration does **not** compress Key Decisions rationales. Moving sections is mechanical and
verifiable by diff — bytes relocate unchanged. Compressing 19 rationales from ~580 chars to
one-liners is authored, judgment-heavy, and the only lossy step; bundling the two makes the
diff unreviewable.

Compression is a **second, separately-consented pass** offered immediately after migration.
The split matters: migration alone takes CLAUDE.md 28.7k → **~16k** (already inside the 17k
target); compression buys the remaining ~9k down to ~7k. The larger lever is opt-in and
reviewable on its own.

### Invariants

The agent satisfies these; the orchestrator verifies them before committing.

1. Every `## ` header present before appears in exactly **one** file after — no silent drops,
   no duplication.
2. Concatenated body bytes ≥ original, minus only the dropped empty stub.
3. No `@path` imports introduced. `@` imports load at launch and would invert the entire
   design; offload links stay lazy markdown links.
4. **The schema marker is written last**, so an interrupted run reads as `partial` and
   resumes idempotently rather than appearing complete.

### Failure handling

No automatic rollback. Report what failed, leave the tree for inspection, print the exact
recovery command. Auto-running `git clean -fd` is the trap the S42 webdesign review caught;
the clean-tree guard means `git restore . && git clean -fd docs/` is always sufficient by hand.

## Per-skill changes

### `/bx:save` — 3 new files, 8 modified

| File | Change |
|---|---|
| `references/doc-schema.md` | **new** — layouts, detection predicate, marker semantics, invariants |
| `references/mode-migrate.md` | **new** — the migration flow above |
| `agents/doc-migrator.md` | **new** — Sonnet; `Read, Write, Edit, Grep, Glob`; mechanical only |
| `SKILL.md` | 4-state mode table; loads `doc-schema.md`; `--skip-migrate` in `argument-hint` |
| `references/mode-update.md` | Step 0 reads STATUS.md; packet split; Parts 1.2/1.3/1.4/1.5/1.8 re-home to STATUS.md; 1.6/1.7 stay on CLAUDE.md; per-file size targets; Part 3 glob widened to root `*.md`; Part 4 rewritten |
| `references/claude-md-sections.md` | rewritten to define **both** files' required sections |
| `references/doc-structure-rules.md` | target-state table gains STATUS.md + architecture.md; preservation rule gains an explicit v1→v2 clause |
| `references/verification-checklists.md` | MIGRATE checklist + invariant assertions |
| `references/mode-create.md` | emits v2 directly |
| `references/mode-refactor.md` | emits v2 directly |
| `agents/save-writer.md` | writes STATUS.md; `claude_md_session_block` → `status_md_session_block`; "exactly one session block" moves to STATUS.md |

The packet rename is the sharp edge: orchestrator and agent must change in the same commit.
`save-writer` already refuses to fuzzy-match a missing `old_string` and emits `warnings:`
instead, so a half-updated contract surfaces loudly rather than losing data silently.

### `/bx:resume` — 3 modified, all read-only

| File | Change |
|---|---|
| `SKILL.md` | Step 0 extends its existing "already in context, don't re-read" logic from MEMORY.md to **CLAUDE.md**; Step 1 reads STATUS.md (v2) or falls back to CLAUDE.md's state sections (v1); README becomes conditional; Step 3.0 staleness reads STATUS.md's date; Step 6 validates against `doc-schema.md` and reports migration-pending **without writing** |
| `references/summary-template.md` | layout line + migration-pending notice |
| `references/task-hydration.md` | hydrates from STATUS.md |

Resume's cross-skill read is an established idiom — Step 6 already reads
`../save/references/claude-md-sections.md`, and the S48 rule covers resolving it against the
skill base directory rather than a repo-rooted path. `doc-schema.md` rides the same mechanism.

## Hook, back-compat, versioning

### SessionStart hook (`session-start-context.sh` and `.ps1`, in lockstep)

- Read `docs/STATUS.md` when present, else CLAUDE.md.
- Replace the broken range with a single-section extractor:
  `awk '/^## Current Status/{f=1;print;next} /^## /{f=0} f'`
- Point the staleness check at whichever file holds the state
  (`git log -1 --format=%ct -- docs/STATUS.md` in v2), or it compares against a CLAUDE.md that
  no longer changes and reports false freshness forever.

### Back-compat

| Plugin | Repo | Outcome |
|---|---|---|
| new | v1 | migration offered |
| new | v2 | normal |
| old | v1 | unchanged |
| old | v2 | **degraded, not corrupting** |

The last cell: migrating on one machine and pulling on another with a stale plugin. Old
`save-writer` deltas fail to match and surface as `warnings:` rather than corrupting content.
Two mitigations, both free: the `> Session state: docs/STATUS.md` pointer left in CLAUDE.md
tells any reader where state went, and the `cc` launcher runs `claude plugin update bx` on
every launch. Documented; no machinery built for it.

### Versioning

`1.0.0` → **`2.0.0`**. A breaking change to a contract other repos depend on, matching the
S54 MAJOR criterion. CHANGELOG entry carries the migration note; README documents the v2
layout and the migration.

## Verification

The migration is executed by an LLM agent following instructions, not by deterministic code,
so testing means running the skill against fixture repos and asserting post-conditions. The
assertions are deterministic and reusable.

**Post-condition checker** — `bx/skills/save/tests/assert-doc-schema.sh <repo>`, runnable
against any repo, fixture or real. Asserts the four invariants plus idempotency (a second run
is a clean no-op with no second commit).

**Fixture repos**, each a real git repo:

| Fixture | Shape | Must do |
|---|---|---|
| `fx-v0` | no CLAUDE.md | CREATE emits v2 directly |
| `fx-v1` | copy of this repo's current docs | migrate; exactly one commit |
| `fx-v2` | already migrated | no prompt, no changes |
| `fx-partial` | STATUS.md present, no marker | resume without duplicating |
| `fx-dirty` | v1 + uncommitted file | skip migration, still complete the save |

`fx-v2` and `fx-partial` are the cases a single dogfood run would never exercise.

**Hook assertion**, reusing the `.claude/scripts/tests/` idiom: `session-start-context.sh`
must emit a correct Current Status block from CLAUDE.md in v1 and from STATUS.md in v2, and
must stop at the next header.

**Then dogfood on `claude-config`** and review the real diff.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Migration consent | Detect + prompt once, then migrate | Reuses the Part 5.2/6.2 first-run gate already proven in this codebase; git diff is the review surface |
| Section split | Full split; architecture → `docs/architecture.md` | Largest win (−76% always-loaded) while the preservation rule holds — content relocates, nothing is deleted |
| `/bx:resume` role | Reads both layouts, never writes | Keeps resume read-only; migration belongs at session end where doc writing already happens, not at session start before any work is done |
| Safety model | Clean-tree guard + isolated single commit | `git revert <sha>` is the recovery path; subagent edits are outside session checkpoints (S53), so `/rewind` cannot help |
| Approach | MIGRATE mode + shared schema ref + `doc-migrator` subagent | The only option where the detection predicate exists exactly once; reuses the orchestrator-consents/subagent-writes split from `save-writer` |
| Verification | Fixtures first, then dogfood | `fx-v2` (no-op) and `fx-partial` (resume) ship untested otherwise |

## Out of scope

- `.claude/rules/` adoption for path-scoped conventions (PowerShell, shell, skill-authoring).
  A real opportunity surfaced during research, but independent of this refactor.
- Key Decisions rationale compression — designed here as a follow-on consented pass, specified
  separately.
- Reverse migration.
