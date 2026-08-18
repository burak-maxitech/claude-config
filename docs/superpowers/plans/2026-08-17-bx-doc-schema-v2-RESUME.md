# bx Doc Schema v2 — Resume Point

**Paused:** 2026-08-17, mid-execution. **Branch:** `feat/doc-schema-v2` (28 commits, tree clean, all tests green).

This file is committed on purpose. The detailed coordination ledger lives at
`.superpowers/sdd/2026-08-17-bx-doc-schema-v2/progress.md`, which is **git-ignored** — a
`git clean -fdx` destroys it. This file is the durable minimum needed to pick the work back up.

## How to resume

1. `git checkout feat/doc-schema-v2`
2. Read the ledger if it still exists (45 rulings, full reasoning). If it's gone, this file plus
   `git log` is enough to continue.
3. Re-invoke `superpowers:subagent-driven-development` with the plan below. It resumes at the
   first task with no `complete` line.

**Plan:** `docs/superpowers/plans/2026-08-17-bx-doc-schema-v2.md`
**Spec:** `docs/superpowers/specs/2026-08-17-bx-doc-schema-v2-design.md`
**Workspace:** `.superpowers/sdd/2026-08-17-bx-doc-schema-v2/` (ledger, briefs, reports, review packages)

## Status

| Task | State |
|---|---|
| 1 — schema contract + checker | complete (`7ed079a..79b2411`), 2 fix rounds |
| 2 — fixture repos | complete (`..33d6980`) |
| 3 — SessionStart hook | complete (`..a4cfd3f`) |
| 4 — doc-migrator + MIGRATE mode | complete (`..242bb34`), **5 fix rounds**, SHIP verdict, 3 parked |
| 5 — contract references | complete (`..5f4ba48`), 1 fix round |
| **6 — packet split** | **implemented (`0148113`), REVIEW NOT YET RUN ← resume here** |
| 7 — SKILL.md mode wiring | not started |
| 8 — resume dual-layout read | not started |
| 9 — v2.0.0 + CHANGELOG + README | not started |
| 10 — fixtures + dogfood | not started |

## Immediate next action

Dispatch the Task 6 review. `BASE=5f4ba48`, `HEAD=0148113`.
Generate the package with
`bash <sdd-skill>/scripts/review-package docs/superpowers/plans/2026-08-17-bx-doc-schema-v2.md 5f4ba48 0148113`.

Ask it specifically to verify: both halves of the packet renamed in ONE commit
(`claude_md_session_block` must be 0 in both files — currently confirmed 0/0); the
`notes:`/`warnings:` split keeps the **unmatched-delta** case on a channel that still compels
the orchestrator to re-dispatch (density caps are advisory, an unmatched delta is not); the
`docs/docs/…` link-depth fix; and that `verification-checklists.md`'s `35k` Part 7 trigger was
updated in the same commit as the threshold conversion.

## Carried into later tasks — all verified present in their briefs

- **T7** — `allowed-tools` needs `Bash(bash:*)`. Verified gap: `Bash(git:*)`, `Agent` and
  `AskUserQuestion` already cover everything else; `bash <path>/assert-doc-schema.sh` is not
  covered, and an unpermitted command means a permission prompt mid-migration with nobody to
  answer it on `--silent`.
- **T9** — README documents the SessionStart hooks at `.claude/scripts/…`, a path that has not
  existed since the S37 plugin migration moved them to `bx/scripts/`. Also an open decision:
  wire the `.ps1` into `hooks.json` or delete it (recommendation: keep and document).
- **T10** — ten fixtures incl. `fx-arch-preexisting`; the `--before` assertion (that code path
  had never executed until round 5); the delete-path rehearsal pinned as an acceptance item.

## Parked from Task 4 — route into the final whole-branch fix wave

- **P1** — the Write tool's own output says "no need to Read it back", contradicting
  `doc-migrator.md`'s mandatory read-back before removal. A rehearsal complied only because the
  instruction pre-empts the shortcut by name. Harden it to say to ignore that tool output.
- **P2** — `doc-migrator.md` row 2: on a resume, a scaffolded `_None recorded._` destination
  compared against an empty CLAUDE.md body can read as a mismatch and block every retry.
  Blocks rather than deletes; the printed recovery clears it.
- **P3** — row 3 does not say what to do when a pre-existing `architecture.md` has no `---`.
  Every reading fails safe.
- Task 3 minor, pre-specified: the SessionStart staleness check passes a repo-relative pathspec
  to `git log` without anchoring to the repo root, so firing from a subdirectory silently
  no-ops and prints `integer expression expected` to stderr (which the hook shows the user).
  Fix: `git -C "$repo_root"` plus an empty-var guard, both scripts.

## Task 6 landed after the pause — findings folded in here

Task 6's report arrived after this file was first written. Its implementation is commit
`0148113` (already recorded above); **its review is still the resume point**. Four things from
its report:

1. **The brief contradicted itself.** Step 2's suggested wording said "Renamed from
   `claude_md_session_block`" while Step 7's done-check required 0 occurrences of that string.
   The implementer resolved toward the done-check and reworded to describe the rename without
   naming the old identifier. Correct call — my defect, not its.
2. **Deferred, verified, needs routing (see below).**
3. It extended the v1-fallback line to cover `status_md_session_block` as well as
   `status_md_deltas`, since on a repo with no STATUS.md the session block would otherwise have
   nowhere to go. Deliberate, disclosed, correct.
4. Several beyond-brief internal-consistency fixes once Part 1/Part 7 became per-file (Part 0's
   heading, the Sequence's TaskList line, the "orchestrator does NOT edit" file list, the Prose
   Caps bullet, the Drift warning's stale 17k/35k target).

### Route into the final whole-branch fix wave — Task 6 correctly declined both as out of scope

- **Archive-file header text still points at CLAUDE.md — 10 occurrences across 3 files.**
  `bx/agents/save-writer.md:37,45,61`, `bx/skills/save/references/mode-update.md:175,191,206,274,307,332`,
  `bx/agents/doc-migrator.md:163`.
  **This is NOT a blanket find-and-replace, and a `sed` over it would be wrong:**
  - `docs/key-decisions.md` -> "Referenced from CLAUDE.md" is **still correct**;
    `## Key Decisions` stays in CLAUDE.md under v2.
  - `docs/completed-work.md` -> should say `docs/STATUS.md`; `## Completed` moved there.
  - `docs/session-history.md` -> "Last session summary is in CLAUDE.md" should say
    `docs/STATUS.md`; the session block moved there.
  - `docs/architecture.md` -> "Referenced from CLAUDE.md" is now questionable: under v2
    CLAUDE.md has no `## Architecture Summary`, so nothing points at that file. Decide whether
    STATUS.md, CLAUDE.md, or neither should carry the reference.
  Also note the relative depth stays `../CLAUDE.md` for archives in `docs/`, but a pointer to
  `docs/STATUS.md` from a file already inside `docs/` is `STATUS.md`, not `docs/STATUS.md`.
- **Part 0.5's legacy pre-v2 migration block** (`mode-update.md:157`) still describes CLAUDE.md
  as holding the state sections, and its trigger at `:165` is a stale "CLAUDE.md is over 25k
  characters". That block handles the old v0->v1 migration and is now the only place in the file
  still written in v1 terms.

## Two decisions waiting on the user

1. **Ruling 2 — Task 10's skill-invocation steps are deferred to post-merge**, because
   `/bx:save` and `/bx:resume` execute from `~/.claude/plugins/cache/burak-tools/bx/<version>/`,
   which `/plugin update bx` populates from the marketplace's **main** branch — a feature
   branch's skills are never loaded. The shell-based verification all runs on-branch. The
   alternative (re-pointing the marketplace at a local path) mutates the real plugin install,
   so I did not do it unasked.
2. **The orphaned `.ps1`** (see T9 above).

## Verification state

All green at pause: 6 fixtures, hook-layout, rule-consistency. 18 files changed, +1840/-250.

The migration itself has been executed end-to-end **five times** by fresh agents given only
`doc-migrator.md` and a fixture — fresh v1 (drop and keep paths), an interrupted resume, and a
pre-existing `architecture.md`. All passed every invariant. Ambiguities encountered fell from 5
to 2 across the rounds.
