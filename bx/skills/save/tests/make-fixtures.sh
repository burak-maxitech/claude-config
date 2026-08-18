#!/usr/bin/env bash
# make-fixtures.sh - build the six doc-schema fixture repos.
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

## Session History

> Full history: [session-history.md](session-history.md)

### Last Session (Session 1) - 2026-08-01
- Built the widget
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

# fx-v2: already migrated - MIGRATE must no-op here
init_repo "$DEST/fx-v2"
write_v2_pair "$DEST/fx-v2"
commit_all "$DEST/fx-v2" "init"
echo "fx-v2          (already migrated)"

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

echo ""
echo "Fixtures built in $DEST"
