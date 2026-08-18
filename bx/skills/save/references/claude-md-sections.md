# Required Sections (doc schema v2)

**`/bx:resume` depends on these exact headers.** The canonical layout and detection
predicate live in [doc-schema.md](doc-schema.md) — this file lists the sections; that file
defines the schema. If they ever disagree, `doc-schema.md` wins.

## CLAUDE.md — instructions only

Always loaded, every session. **Target ~7k chars.** Contains only facts Claude should hold
all the time.

1. `## Project Overview` — name, repo, one-line description, key doc links
2. `## Key Decisions` — condensed table, ~20 rows, + link to `docs/key-decisions.md`
3. `## Known Issues / Blockers` — current blockers
4. `## Environment Variables` — **only when populated** (see doc-schema.md)

Plus the marker as line 1, a `Last Updated:` line, and the pointer line
`> Session state: [docs/STATUS.md](docs/STATUS.md)`.

**Never put session state here.** Current Status, Completed, In Progress, Next Steps and
Session History all changed frequently, and CLAUDE.md is paid for on every request of every
session.

## docs/STATUS.md — session state

Read on demand by `/bx:resume`. **Target ~10k chars.** Sections in this order:

1. `## Current Status` — status table
2. `## Completed` — 1-2 line summary + link to `docs/completed-work.md`
3. `## In Progress` — current work
4. `## Next Steps` — numbered priority list
5. `## Session History` — last session only, 3-5 bullets, + link to `docs/session-history.md`

Plus its own `Last Updated:` line. The staleness signal must follow the state.

## Reference files (overflow archives)

- `docs/completed-work.md` — full completed checklist
- `docs/key-decisions.md` — full decision log
- `docs/session-history.md` — detailed session archive
- `docs/architecture.md` — architecture detail moved out of CLAUDE.md

All optional; created as needed when content is offloaded.

**Do not rename, remove, or reorder these sections.**
