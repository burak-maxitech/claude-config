# bx Documentation Schema

The single definition of the bx doc layout. **Both `/bx:save` and `/bx:resume` read this
file.** Detection logic must never be duplicated into either SKILL.md — that is how the two
drift apart.

## Schema marker

`<!-- bx-doc-schema: 2 -->` — first line of CLAUDE.md.

It is an HTML comment because Claude Code strips block-level HTML comments before CLAUDE.md
enters context: the marker costs zero tokens per session while staying greppable on disk.
It is versioned (`2`, not a boolean) so a future v3 reuses this machinery.

**The marker is written LAST during migration.** An interrupted run must read as `partial`
and resume idempotently, never as complete.

## v2 layout

    CLAUDE.md                    always loaded   ~7k target
      <!-- bx-doc-schema: 2 -->
      Last Updated: <date> [(Session N)]
      ## Project Overview
      ## Key Decisions            ~20 rows + link to docs/key-decisions.md
      ## Known Issues / Blockers
      ## Environment Variables    ONLY when populated
      > Session state: [docs/STATUS.md](docs/STATUS.md)

    docs/STATUS.md               read on demand by /bx:resume
      Last Updated: <date> [(Session N)]
      ## Current Status
      ## Completed                summary + link to docs/completed-work.md
      ## In Progress
      ## Next Steps
      ## Session History          last session + link to docs/session-history.md

    docs/architecture.md         former ## Architecture Summary
    docs/completed-work.md       unchanged archive
    docs/key-decisions.md        unchanged archive
    docs/session-history.md      unchanged archive
    docs/archive/                rotated volumes — see Archives below

`Last Updated:` is deliberately present in BOTH files. After the split CLAUDE.md may sit
untouched for weeks while state churns daily; the staleness signal must follow the state or
`/bx:resume` and the SessionStart hook report false freshness.

`## Environment Variables` is **conditional**. It is populated iff its body contains a token
matching `[A-Z][A-Z0-9_]{2,}` anywhere — three or more consecutive uppercase/digit/underscore
characters, erring toward keeping content when ambiguous (Invariant 2). Populated means keep
verbatim. **Unpopulated means drop, whether or not the body has text in it** — a body reading
`None required. This is a pure configuration repo.` names no variable and is dropped, so this
is not an "empty section" rule and must never be restated as one. That deletion is the single
exception to *content moves, nothing is deleted*: it is named and quoted in the migration's
consent prompt, and quoted verbatim again in the run's report.

## Archives

The canonical set of **auto-managed archives**: `docs/session-history.md`,
`docs/key-decisions.md`, `docs/completed-work.md`, plus `docs/next-steps-backlog.md`
(created on demand by a size-pressure shrinker). Exclusion lists elsewhere — `mode-update.md`
Steps 0.3/3.0, the resume skill's do-not-read list — follow this set; extend it here first.

Access rule: archives are append-only outputs, never sync inputs. Writers append via
anchored tail reads (Grep the anchor's line number, then offset-Read a window); **no
automatic path reads an archive in full**, so growth is disk-only. Rotation — procedure and
thresholds owned by `mode-update.md` Part 7.7 — moves the oldest entries of an oversized
archive byte-verbatim into numbered volumes under `docs/archive/`; volumes are read by
nothing automatic, ever — they are grep-on-demand history.

## v1 layout (legacy)

All ten sections in CLAUDE.md, no marker, no `docs/STATUS.md`. This is what every repo
looked like before schema v2.

## Detection predicate

Evaluate in order — this is the exact branch order `assert-doc-schema.sh` implements; a
reader of this prose alone must be able to predict the script's answer for any input:

1. No CLAUDE.md -> **v0**. CREATE mode, which emits v2 directly.
2. CLAUDE.md contains the marker -> **v2**. Proceed normally.
3. `docs/STATUS.md` present (marker absent) -> **partial**. A prior migration was
   interrupted; resume it idempotently rather than starting over.
4. CLAUDE.md has any of `## Current Status`, `## Completed`, `## In Progress`,
   `## Next Steps`, `## Session History` -> **v1**. Offer migration.
5. None of the above -> **v0**. A CLAUDE.md exists but carries no schema signal at all; see
   the v0 mode-routing rule below — it routes to UPDATE, not CREATE.

### v0 mode routing (this file is the authority)

Cases 1 and 5 both **detect** as `v0` — that is what `assert-doc-schema.sh` reports for
either — but they must not **route** the same way:

- **No CLAUDE.md at all** (case 1) -> **CREATE**. There is nothing on disk to overwrite, and
  CREATE emits v2 directly.
- **CLAUDE.md present, matching no other case** (case 5 — a hand-written or `/init`-generated
  CLAUDE.md: no marker, no `docs/STATUS.md`, none of the five state headers) -> **UPDATE,
  never CREATE**. CREATE against an existing CLAUDE.md risks overwriting a file somebody wrote
  by hand. UPDATE degrades *loudly* instead: `save-writer`'s v1 fallback routes the state
  deltas at CLAUDE.md, and any delta whose `old_string` does not match is reported as an
  unmatched-delta warning rather than guessed at — so the run ends with a visible warning, not
  a silent overwrite.

`/bx:save`'s SKILL.md pseudocode implements this: its final `ELSE` lands on UPDATE.

## Invariants

Any migration or save must preserve all four:

1. Every `## ` header present before appears in exactly ONE file after — no silent drops,
   no duplication.
2. No content loss: concatenated body bytes >= original, minus only a dropped unpopulated
   `## Environment Variables` section (which is prose more often than it is empty).
3. No `@path` imports in CLAUDE.md or STATUS.md. `@` imports load at launch and would
   invert the whole design; offload links stay lazy markdown links.
4. The marker is written last.

`bx/skills/save/tests/assert-doc-schema.sh <repo>` checks all four mechanically.
