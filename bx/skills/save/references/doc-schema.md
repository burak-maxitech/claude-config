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
      Last Updated: <date>
      ## Project Overview
      ## Key Decisions            ~20 rows + link to docs/key-decisions.md
      ## Known Issues / Blockers
      ## Environment Variables    ONLY when populated
      > Session state: [docs/STATUS.md](docs/STATUS.md)

    docs/STATUS.md               read on demand by /bx:resume
      Last Updated: <date>
      ## Current Status
      ## Completed                summary + link to docs/completed-work.md
      ## In Progress
      ## Next Steps
      ## Session History          last session + link to docs/session-history.md

    docs/architecture.md         former ## Architecture Summary
    docs/completed-work.md       unchanged archive
    docs/key-decisions.md        unchanged archive
    docs/session-history.md      unchanged archive

`Last Updated:` is deliberately present in BOTH files. After the split CLAUDE.md may sit
untouched for weeks while state churns daily; the staleness signal must follow the state or
`/bx:resume` and the SessionStart hook report false freshness.

`## Environment Variables` is **conditional**. It is empty iff its body contains no line
matching `^[A-Z_][A-Z0-9_]*`. Empty means drop; anything else means keep verbatim.

## v1 layout (legacy)

All ten sections in CLAUDE.md, no marker, no `docs/STATUS.md`. This is what every repo
looked like before schema v2.

## Detection predicate

Evaluate in order:

1. CLAUDE.md contains the marker -> **v2**. Proceed normally.
2. No marker, `docs/STATUS.md` absent, CLAUDE.md has any of `## In Progress`,
   `## Next Steps`, `## Session History` -> **v1**. Offer migration.
3. No CLAUDE.md -> **v0**. CREATE mode, which emits v2 directly.
4. `docs/STATUS.md` present but no marker -> **partial**. A prior migration was
   interrupted; resume it idempotently rather than starting over.

## Invariants

Any migration or save must preserve all four:

1. Every `## ` header present before appears in exactly ONE file after — no silent drops,
   no duplication.
2. No content loss: concatenated body bytes >= original, minus only a dropped empty stub.
3. No `@path` imports in CLAUDE.md or STATUS.md. `@` imports load at launch and would
   invert the whole design; offload links stay lazy markdown links.
4. The marker is written last.

`bx/skills/save/tests/assert-doc-schema.sh <repo>` checks all four mechanically.
