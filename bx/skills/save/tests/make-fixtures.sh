#!/usr/bin/env bash
# make-fixtures.sh - build the ten doc-schema fixture repos.
# Usage: make-fixtures.sh <dest-dir>
# Each fixture is a real git repo so the clean-tree guard can be exercised.
# bash 3.2 compatible.

set -uo pipefail
DEST="${1:?usage: make-fixtures.sh <dest-dir>}"
mkdir -p "$DEST"

init_repo() {   # <path>
    mkdir -p "$1" && git -C "$1" init -q .
    git -C "$1" config user.email fixture@example.com
    git -C "$1" config user.name Fixture
}

commit_all() {  # <path> <message>
    git -C "$1" add -A && git -C "$1" commit -q -m "$2"
}

write_v1_claude_md() {  # <path>
    cat > "$1/CLAUDE.md" <<'MD'
# CLAUDE.md

Last Updated: 2026-08-01 (Session 1)

## Project Overview

Fixture project for doc-schema migration tests.

## Current Status

| Area | Status |
|------|--------|
| Widgets | Complete |

## Completed

2 tasks completed. See [docs/completed-work.md](docs/completed-work.md) for full checklist.

## In Progress

**Widget refactor** — halfway through, see `src/widget.py`.

## Next Steps

1. Finish the widget refactor
2. Add tests

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Use widgets | They compose better than gadgets. |

> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)

## Architecture Summary

```
project/
├── src/
└── docs/
```

## Known Issues / Blockers

None currently.

## Environment Variables

None required.

## Session History

> Full history: [docs/session-history.md](docs/session-history.md)

### Last Session (Session 1) - 2026-08-01
- Built the widget
MD
}

write_v1_envvars_claude_md() {  # <path>
    # Identical to write_v1_claude_md, except ## Environment Variables is
    # POPULATED (real vars in bullet form). The schema drops that section
    # only when it's empty and keeps it verbatim otherwise -- this fixture
    # exercises the "keep" path, which none of the other fixtures do since
    # they all carry "None required." (reads as empty).
    cat > "$1/CLAUDE.md" <<'MD'
# CLAUDE.md

Last Updated: 2026-08-01 (Session 1)

## Project Overview

Fixture project for doc-schema migration tests.

## Current Status

| Area | Status |
|------|--------|
| Widgets | Complete |

## Completed

2 tasks completed. See [docs/completed-work.md](docs/completed-work.md) for full checklist.

## In Progress

**Widget refactor** — halfway through, see `src/widget.py`.

## Next Steps

1. Finish the widget refactor
2. Add tests

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Use widgets | They compose better than gadgets. |

> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)

## Architecture Summary

```
project/
├── src/
└── docs/
```

## Known Issues / Blockers

None currently.

## Environment Variables

- `DATABASE_URL` — Postgres connection string
- `API_KEY` — third-party service key

## Session History

> Full history: [docs/session-history.md](docs/session-history.md)

### Last Session (Session 1) - 2026-08-01
- Built the widget
MD
}

write_v2_pair() {  # <path>
    # STATUS.md's links here are the golden output of the link-rewriting rules in
    # agents/doc-migrator.md -- see its "Link text" table for which of the two shapes
    # (path-as-text vs prose-as-text) rewrites the text as well as the target.
    mkdir -p "$1/docs"
    cat > "$1/CLAUDE.md" <<'MD'
<!-- bx-doc-schema: 2 -->
# CLAUDE.md

Last Updated: 2026-08-01 (Session 1)

## Project Overview

Fixture project, already migrated.

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Use widgets | They compose better than gadgets. |

> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)

## Known Issues / Blockers

None currently.

> Session state: [docs/STATUS.md](docs/STATUS.md)
MD
    cat > "$1/docs/STATUS.md" <<'MD'
# Project Status

> Session state for `/bx:resume`. Instructions live in [CLAUDE.md](../CLAUDE.md).

Last Updated: 2026-08-01 (Session 1)

## Current Status

| Area | Status |
|------|--------|
| Widgets | Complete |

## Completed

2 tasks completed. See [completed-work.md](completed-work.md) for full checklist.

## In Progress

**Widget refactor** — halfway through, see `src/widget.py`.

## Next Steps

1. Finish the widget refactor
2. Add tests

## Session History

> Full history: [session-history.md](session-history.md)

### Last Session (Session 1) - 2026-08-01
- Built the widget
MD
}

write_architecture_md() {  # <path>
    # The golden docs/architecture.md a correct migration of write_v1_claude_md's
    # ## Architecture Summary body produces (doc-migrator.md Step 4: the header
    # block, then the section's body -- not its header -- with no link rewriting
    # needed since the body has no links). Shared by fx-v2 (the golden migration
    # output of fx-v1) and fx-arch-preexisting (whose whole point is that this
    # file already exists, byte-identical, before migration ever runs).
    mkdir -p "$1/docs"
    cat > "$1/docs/architecture.md" <<'MD'
# Architecture

> Full architecture detail. Referenced from [CLAUDE.md](../CLAUDE.md).

---

```
project/
├── src/
└── docs/
```
MD
}

write_v1_sparse_claude_md() {  # <path>
    # All three instruction sections, but only ## Next Steps of the five state
    # sections. The eligibility pre-flight (mode-migrate.md Step 0) allows this:
    # v1 detection fires on ANY ONE state section, and doc-migrator scaffolds the
    # four absent ones as "_None recorded._" placeholders (doc-migrator.md Step 3).
    cat > "$1/CLAUDE.md" <<'MD'
# CLAUDE.md

Last Updated: 2026-08-01 (Session 1)

## Project Overview

Fixture project for doc-schema migration tests (sparse state coverage).

## Next Steps

1. Finish the widget refactor

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Use widgets | They compose better than gadgets. |

> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)

## Known Issues / Blockers

None currently.
MD
}

write_v1_ineligible_claude_md() {  # <path>
    # State sections present, but missing ## Key Decisions -- one of the three
    # instruction sections the eligibility pre-flight (mode-migrate.md Step 0)
    # requires. Migration must decline without prompting.
    cat > "$1/CLAUDE.md" <<'MD'
# CLAUDE.md

Last Updated: 2026-08-01 (Session 1)

## Project Overview

Fixture project for doc-schema migration tests (missing Key Decisions -- ineligible).

## Current Status

| Area | Status |
|------|--------|
| Widgets | Complete |

## Completed

2 tasks completed. See [docs/completed-work.md](docs/completed-work.md) for full checklist.

## In Progress

**Widget refactor** — halfway through, see `src/widget.py`.

## Next Steps

1. Finish the widget refactor
2. Add tests

## Known Issues / Blockers

None currently.

## Session History

> Full history: [docs/session-history.md](docs/session-history.md)

### Last Session (Session 1) - 2026-08-01
- Built the widget
MD
}

write_partial_conflict_pair() {  # <path>
    # docs/STATUS.md exists (marker absent -> detects `partial`), but its
    # ## Current Status body is a TRUNCATED variant of CLAUDE.md's (missing the
    # "Gadgets" row). This is the removal gate's second tier (doc-migrator.md
    # Step 5, "Already there when the run began"): a destination present before
    # the run must be compared against CLAUDE.md's current body, and a genuine
    # content mismatch must BLOCK -- never merge, never overwrite.
    mkdir -p "$1/docs"
    cat > "$1/CLAUDE.md" <<'MD'
# CLAUDE.md

Last Updated: 2026-08-01 (Session 1)

## Project Overview

Fixture project simulating an interrupted migration with a conflicting STATUS.md.

## Current Status

| Area | Status |
|------|--------|
| Widgets | Complete |
| Gadgets | In progress |

## Completed

2 tasks completed. See [docs/completed-work.md](docs/completed-work.md) for full checklist.

## In Progress

**Widget refactor** — halfway through, see `src/widget.py`.

## Next Steps

1. Finish the widget refactor

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Use widgets | They compose better than gadgets. |

> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)

## Architecture Summary

```
project/
├── src/
└── docs/
```

## Known Issues / Blockers

None currently.

## Session History

> Full history: [docs/session-history.md](docs/session-history.md)

### Last Session (Session 1) - 2026-08-01
- Built the widget
MD
    cat > "$1/docs/STATUS.md" <<'MD'
# Project Status

> Session state for `/bx:resume`. Instructions live in [CLAUDE.md](../CLAUDE.md).

Last Updated: 2026-08-01 (Session 1)

## Current Status

| Area | Status |
|------|--------|
| Widgets | Complete |
MD
}

# fx-v0: a git repo with no CLAUDE.md at all
init_repo "$DEST/fx-v0"
echo "# Readme" > "$DEST/fx-v0/README.md"
commit_all "$DEST/fx-v0" "init"
echo "fx-v0          (no CLAUDE.md)"

# fx-v1: the legacy layout, clean tree
init_repo "$DEST/fx-v1"
write_v1_claude_md "$DEST/fx-v1"
mkdir -p "$DEST/fx-v1/docs"
echo "# Completed Work" > "$DEST/fx-v1/docs/completed-work.md"
echo "# Key Decisions" > "$DEST/fx-v1/docs/key-decisions.md"
echo "# Session History Archive" > "$DEST/fx-v1/docs/session-history.md"
commit_all "$DEST/fx-v1" "init"
echo "fx-v1          (legacy layout, clean)"

# fx-v1-envvars: legacy layout, clean tree, but ## Environment Variables is
# POPULATED -- exercises the env_vars_disposition: keep migration path, which
# no other fixture reaches (they all carry "None required.", which reads as
# empty under the populated-token rule).
init_repo "$DEST/fx-v1-envvars"
write_v1_envvars_claude_md "$DEST/fx-v1-envvars"
mkdir -p "$DEST/fx-v1-envvars/docs"
echo "# Completed Work" > "$DEST/fx-v1-envvars/docs/completed-work.md"
echo "# Key Decisions" > "$DEST/fx-v1-envvars/docs/key-decisions.md"
echo "# Session History Archive" > "$DEST/fx-v1-envvars/docs/session-history.md"
commit_all "$DEST/fx-v1-envvars" "init"
echo "fx-v1-envvars  (legacy layout, POPULATED Environment Variables, clean)"

# fx-v2: already migrated - MIGRATE must no-op here. Also the exact golden
# output that migrating fx-v1 would produce (same Next Steps items, same
# docs/architecture.md derived from fx-v1's ## Architecture Summary) -- this is
# what makes the --before assertion against fx-v1/CLAUDE.md meaningful below.
init_repo "$DEST/fx-v2"
write_v2_pair "$DEST/fx-v2"
write_architecture_md "$DEST/fx-v2"
commit_all "$DEST/fx-v2" "init"
echo "fx-v2          (already migrated, golden output of fx-v1)"

# fx-partial: STATUS.md exists but the marker was never written
init_repo "$DEST/fx-partial"
write_v2_pair "$DEST/fx-partial"
# strip the marker to simulate an interrupted run
sed -i.bak '/bx-doc-schema/d' "$DEST/fx-partial/CLAUDE.md" && rm -f "$DEST/fx-partial/CLAUDE.md.bak"
commit_all "$DEST/fx-partial" "init"
echo "fx-partial     (interrupted migration)"

# fx-dirty: legacy layout with an uncommitted change
init_repo "$DEST/fx-dirty"
write_v1_claude_md "$DEST/fx-dirty"
commit_all "$DEST/fx-dirty" "init"
echo "scratch" > "$DEST/fx-dirty/uncommitted.txt"
echo "fx-dirty       (legacy layout, DIRTY tree)"

# fx-v1-sparse: three instruction sections, but only ## Next Steps of the five
# state sections -- the eligibility pre-flight must still allow migration, and
# doc-migrator must scaffold the four missing state sections.
init_repo "$DEST/fx-v1-sparse"
write_v1_sparse_claude_md "$DEST/fx-v1-sparse"
mkdir -p "$DEST/fx-v1-sparse/docs"
echo "# Key Decisions" > "$DEST/fx-v1-sparse/docs/key-decisions.md"
commit_all "$DEST/fx-v1-sparse" "init"
echo "fx-v1-sparse   (legacy layout, only Next Steps present, clean)"

# fx-v1-ineligible: state sections present, but ## Key Decisions is missing --
# the eligibility pre-flight must decline without prompting.
init_repo "$DEST/fx-v1-ineligible"
write_v1_ineligible_claude_md "$DEST/fx-v1-ineligible"
mkdir -p "$DEST/fx-v1-ineligible/docs"
echo "# Completed Work" > "$DEST/fx-v1-ineligible/docs/completed-work.md"
echo "# Session History Archive" > "$DEST/fx-v1-ineligible/docs/session-history.md"
commit_all "$DEST/fx-v1-ineligible" "init"
echo "fx-v1-ineligible (legacy layout, missing Key Decisions, clean)"

# fx-partial-conflict: docs/STATUS.md exists with a TRUNCATED ## Current Status
# vs. CLAUDE.md's -- migration must detect `partial` and, on the delete-path
# rehearsal (Step 0b, not this script), block rather than merge or overwrite.
init_repo "$DEST/fx-partial-conflict"
write_partial_conflict_pair "$DEST/fx-partial-conflict"
echo "# Completed Work" > "$DEST/fx-partial-conflict/docs/completed-work.md"
echo "# Key Decisions" > "$DEST/fx-partial-conflict/docs/key-decisions.md"
echo "# Session History Archive" > "$DEST/fx-partial-conflict/docs/session-history.md"
commit_all "$DEST/fx-partial-conflict" "init"
echo "fx-partial-conflict (interrupted migration, conflicting STATUS.md)"

# fx-arch-preexisting: v1 layout, but docs/architecture.md already exists and
# matches ## Architecture Summary's body byte-for-byte -- migration must proceed
# and leave that file untouched. This is the one gate path where a mistake
# DELETES rather than blocks; the delete-path rehearsal against it is Step 0b,
# not this script -- this fixture is only the substrate.
init_repo "$DEST/fx-arch-preexisting"
write_v1_claude_md "$DEST/fx-arch-preexisting"
mkdir -p "$DEST/fx-arch-preexisting/docs"
echo "# Completed Work" > "$DEST/fx-arch-preexisting/docs/completed-work.md"
echo "# Key Decisions" > "$DEST/fx-arch-preexisting/docs/key-decisions.md"
echo "# Session History Archive" > "$DEST/fx-arch-preexisting/docs/session-history.md"
write_architecture_md "$DEST/fx-arch-preexisting"
commit_all "$DEST/fx-arch-preexisting" "init"
echo "fx-arch-preexisting (legacy layout, docs/architecture.md pre-existing & matching)"

echo ""
echo "Fixtures built in $DEST"
