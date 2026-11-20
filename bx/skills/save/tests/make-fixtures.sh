#!/usr/bin/env bash
# make-fixtures.sh - build the fourteen doc-schema fixture repos.
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

stub_docs() {   # <path> <name>...  -- create docs/ with one-line stub files.
    # Each fixture names ONLY the stubs it intends to have: a name absent from a
    # call is a deliberate omission (e.g. fx-v1-ineligible carries no
    # key-decisions stub), not drift.
    _p="$1"; shift
    mkdir -p "$_p/docs"
    for _n in "$@"; do
        case "$_n" in
            completed-work)  echo "# Completed Work"          > "$_p/docs/completed-work.md" ;;
            key-decisions)   echo "# Key Decisions"           > "$_p/docs/key-decisions.md" ;;
            session-history) echo "# Session History Archive" > "$_p/docs/session-history.md" ;;
            *) echo "stub_docs: unknown stub '$_n'" >&2; exit 2 ;;
        esac
    done
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
    # POPULATED: its body contains a token matching [A-Z][A-Z0-9_]{2,}, which is
    # the rule doc-schema.md defines. Populated means keep verbatim; unpopulated
    # means drop, whether or not the body has text in it -- so this is NOT an
    # "empty section" rule. This fixture exercises the "keep" path, which none of
    # the other fixtures do: they all carry "None required.", which names no
    # variable and is therefore dropped.
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

Fixture project for doc-schema migration tests.

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

> Full architecture detail, moved out of CLAUDE.md (doc schema v2). Read on demand.

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
    # "Gadgets" row). The CLAUDE.md here is itself a deliberate variant of
    # write_v1_claude_md's body (different Project Overview sentence, the extra
    # Gadgets row, one-item Next Steps) -- intentional deltas, not drift. This is the removal gate's second tier (doc-migrator.md
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

filler() {  # <count> -- <count> 50-char sentences on one line, no trailing newline
    _i=1; _out=""
    while [ "$_i" -le "$1" ]; do
        _out="${_out}Detail $(printf '%02d' "$_i") of this issue, kept for fixture weight. "
        _i=$((_i + 1))
    done
    printf '%s' "$_out"
}

ki_head() {  # <path> -- v2 CLAUDE.md up to and including the Known Issues header
    cat > "$1/CLAUDE.md" <<'MD'
<!-- bx-doc-schema: 2 -->
# CLAUDE.md

Last Updated: 2026-08-01 (Session 9)

## Project Overview

Fixture project for the Known Issues governor.

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Use widgets | They compose better than gadgets. |

> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)

## Known Issues / Blockers

MD
}

ki_entry() {  # <path> <lead> <filler-count> [extra-sentence]
    printf '**%s** %s%s\n\n' "$2" "$(filler "$3")" "${4:-}" >> "$1/CLAUDE.md"
}

ki_tail() {  # <path> -- the pointer line, then a v2 STATUS.md
    printf '%s\n' '> Session state: [docs/STATUS.md](docs/STATUS.md)' >> "$1/CLAUDE.md"
    mkdir -p "$1/docs"
    cat > "$1/docs/STATUS.md" <<'MD'
# Project Status

> Session state for `/bx:resume`. Instructions live in [CLAUDE.md](../CLAUDE.md).

Last Updated: 2026-08-01 (Session 9)

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

### Last Session (Session 9) - 2026-08-01
- Built the widget
MD
}

write_ki_rotate_archive() {  # <path> -- a >100k docs/known-issues.md, Open entry at #60
    mkdir -p "$1/docs"
    cat > "$1/docs/known-issues.md" <<'MD'
# Known Issues Archive

> Issues moved out of [CLAUDE.md](../CLAUDE.md) by `/bx:save`. `Resolved` entries are
> history; `Open` entries are still live and linked from CLAUDE.md.

---
MD
    _n=1
    while [ "$_n" -le 160 ]; do
        if [ "$_n" -eq 60 ]; then _hdr="### Issue $_n — Open, moved S$_n (2026-01-01)"
        else _hdr="### Issue $_n — Resolved S$_n (2026-01-01)"; fi
        printf '\n%s\n\n**Issue %s (S%s).** %s\n' "$_hdr" "$_n" "$_n" "$(filler 13)" >> "$1/docs/known-issues.md"
        _n=$((_n + 1))
    done
}

pad() {  # <count> <phrase> -- <phrase> repeated <count> times on one line, no trailing newline
    _i=1; _out=""
    while [ "$_i" -le "$1" ]; do _out="${_out}$2"; _i=$((_i + 1)); done
    printf '%s' "$_out"
}

write_size_budget_fixture() {  # <path>
    # Shaped like a real 300-session project measured over budget after a --full
    # save (the 2.18.0 evidence): standing-rule Known Issues, a Current Status
    # table of finished rows, scaffolded In Progress / Next Steps, and a
    # Last Updated line that strings three sessions together. Every string the
    # verifier greps for (R01..R24, FIXVAR_01.., "Item 1NN", "Owed NN") is
    # stable: test-size-budget-fixture.sh depends on them.
    _d="$1"; mkdir -p "$_d/docs"
    _c="$_d/CLAUDE.md"; _s="$_d/docs/STATUS.md"; _b="$_d/docs/next-steps-backlog.md"

    # ---------------- CLAUDE.md ----------------
    {
        printf '%s\n' '<!-- bx-doc-schema: 2 -->' '# Sizefix — CLAUDE.md' ''
        printf '%s' '**Last Updated:** 2026-11-19 (Session 321 — **an invite link assigns a username (`04448b2b`); the About page is rewritten (`3262427d`); no migration.** '
        printf '%s' "Earlier, Session 320 — $(pad 5 'accepting an invite assigns a username; wrist size moved to Settings; ')"
        printf '%s\n' "Earlier, Session 319 — $(pad 5 'friends and three visibility levels went live behind the switch; '))"
        printf '%s\n' '' '> This file holds instructions and standing rules only. Session state lives in [docs/STATUS.md](docs/STATUS.md).' ''
        printf '%s\n' '## Project Overview' '' '| Field | Value |' '|-------|-------|' \
            '| **Name** | Sizefix |' \
            '| **Description** | Fixture project shaped like a long-running product repo, for the size-budget shrinkers |' \
            '| **Stack** | Next.js 16, React 19, TypeScript 5.9, Drizzle ORM, Postgres, vitest, Playwright (all pinned in `package.json`) |' \
            '| **Repository** | github.com/example/sizefix, default branch `main` (`git remote -v`) |' \
            '| **Package manager** | npm 11; scripts are `dev`, `build`, `test`, `lint`, `e2e` (`npm run` lists them) |' \
            '| **Hosting** | One region, one database; a deploy is a push to `main` and nothing else triggers one |' ''
        printf '%s\n' '**Key Documentation** (a flow map must change in the same commit as the code it describes):'
        _n=1
        while [ "$_n" -le 11 ]; do
            _k="$(printf '%02d' "$_n")"
            printf '%s\n' "- [docs/flow-$_k.md](docs/flow-$_k.md) — flow map $_k: $(pad 3 'entrances, guards and the rollback switch; ')"
            _n=$((_n + 1))
        done
        printf '%s\n' '' '## Key Decisions' '' '| Decision | Rationale |' '|----------|-----------|'
        _n=1
        while [ "$_n" -le 14 ]; do
            _k="$(printf '%02d' "$_n")"
            printf '%s\n' "| Decision D$_k: the widget pipeline uses approach $_k | $(pad 3 'It measured better on the real catalog than the alternative. ')(S3$_k, \`d0c0de$_k\`) |"
            _n=$((_n + 1))
        done
        printf '%s\n' '' '> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)' ''
        printf '%s\n' '## Known Issues / Blockers' '' \
            '> Standing rules only, one line each. The detail behind every line is in [docs/known-issues.md](docs/known-issues.md).' ''
        _n=1
        for _g in 'Deploys and rollbacks' 'Before pushing or running anything billed' 'Do not re-open, re-run or override' 'Database migrations (`src/db/migrations/`)'; do
            printf '%s\n' "**$_g**" ''
            _j=1
            while [ "$_j" -le 6 ]; do
                _k="$(printf '%02d' "$_n")"
                if [ "$_g" = 'Database migrations (`src/db/migrations/`)' ]; then
                    _lead="In \`src/db/migrations/\`, never edit an applied migration (R$_k)."
                else
                    _lead="Never skip check R$_k before the step it guards."
                fi
                printf '%s\n' "- **$_lead** $(pad 4 'Skipping it broke production once and cost a day. ')"
                _n=$((_n + 1)); _j=$((_j + 1))
            done
            printf '\n'
        done
        printf '%s\n' '## Environment Variables' ''
        _n=1
        while [ "$_n" -le 12 ]; do
            _k="$(printf '%02d' "$_n")"
            printf '%s\n' "- \`FIXVAR_$_k\` — $(pad 3 'read at boot; a wrong value fails closed and logs once. ')"
            _n=$((_n + 1))
        done
        printf '%s\n' '' '> Session state: [docs/STATUS.md](docs/STATUS.md)'
    } > "$_c"

    # ---------------- docs/STATUS.md ----------------
    {
        printf '%s\n' '# Project Status' '' '> Session state for `/bx:resume`. Instructions live in [CLAUDE.md](../CLAUDE.md).' ''
        printf '%s' 'Last Updated: 2026-11-19 (Session 321 — **an invite link assigns a username instead of asking (`04448b2b`); the About page is rewritten in three languages (`3262427d`); no migration.** '
        printf '%s' "Earlier, Session 320 — $(pad 5 'accepting an invite assigns a username; wrist size moved to Settings; ')"
        printf '%s\n' "Earlier, Session 319 — $(pad 5 'friends and three visibility levels went live behind the switch; '))"
        printf '%s\n' '' '## Current Status' '' '| Component | Status | Notes |' '|-----------|--------|-------|'
        printf '%s\n' "| **Everything through S291: 10 collapsed rows** ($(pad 9 'the core platform, the finder, the gallery, the add flow; ')) | ✅ | see [completed-work.md](completed-work.md) |"
        printf '%s\n' "| **S295–S308: 7 collapsed rows** ($(pad 9 'release detection, two languages, lug width, page recomposition; ')) | ✅ | see [completed-work.md](completed-work.md) |"
        _n=1
        while [ "$_n" -le 12 ]; do
            _k="$(printf '%02d' "$_n")"
            printf '%s\n' "| Feature F$_k ($(pad 7 'messages, label tables, sentence builders, the alert email; ')) | ✅ LIVE 2026-11-$_k (S3$_k, \`feed00$_k\`) | $(pad 2 'Walked signed in and signed out by the owner. ') |"
            _n=$((_n + 1))
        done
        printf '%s\n' '| Personal release email | 🔧 In progress | the next build |' '| Photo AI | 🔲 Not started | Phase 2+ |' ''
        printf '%s\n' '## Completed' '' '412 tasks completed across the platform. See [completed-work.md](completed-work.md) for full checklist.' ''
        printf '%s\n' '## In Progress' ''
        _n=1
        while [ "$_n" -le 14 ]; do
            _k="$(printf '%02d' "$_n")"
            printf '%s\n' "- **Workstream W$_k LIVE (S3$_k, \`c0ffee$_k\`, deployment \`dpl_fixture$_k\`).** Owed $_k: one read of production data and one owner walk. Owed items → [detail](next-steps-backlog.md#ip-s319-full)"
            _n=$((_n + 1))
        done
        printf '%s\n' '' '> Full detail of finished items: [completed-work.md](completed-work.md)'
        printf '%s\n' '> Full In Progress detail (verbatim, by trim): [S319](next-steps-backlog.md#ip-s319-full) · [S317](next-steps-backlog.md#ip-s317-full) · [S315](next-steps-backlog.md#ip-s315-full) · [S312](next-steps-backlog.md#ip-s312-full) · [S308](next-steps-backlog.md#ip-s308-full) · [S307](next-steps-backlog.md#ip-s307-full)'
        printf '%s\n' '' "_**Watermarks:** \`/simplify\` S317 (\`92d1ebc7\`); $(pad 20 'skipped by the owner: a shared wrapper and a rename; ')_" ''
        printf '%s\n' '## Next Steps' '' 'Flat priority order — one line each; detail lives in [next-steps-backlog.md](next-steps-backlog.md).' ''
        _n=138
        while [ "$_n" -ge 123 ]; do
            case "$_n" in
                134) _t="**Item 134: catalog price fill — DONE S311 (\`d947e5f2\`).** $(pad 3 'Every listed brand now has a store price. ')" ;;
                131) _t="**Item 131: harden the public-message guard — DONE S315 (\`fe8383d9\`).** $(pad 3 'An alias or a re-export now fails the pin. ')" ;;
                135) _t="**Item 135: /simplify skips — DONE S318 (\`a9b3cd01\`)** except the label wording for failed reads (owner). $(pad 2 'The wording call is still open. ')" ;;
                *)   _t="**Item $_n: follow-up $_n** — $(pad 4 'confirm the copy call, then read the result in production; ')" ;;
            esac
            printf '%s\n' "$_n. $_t → [detail](next-steps-backlog.md#ns-s317-full)" ''
            _n=$((_n - 1))
        done
        printf '%s\n' '> Items #122, #121, #120, #119, #118, #117, #116, #115, #114, #111, #112, #113, #110, #108, #109, #107, #106, #105, #104, #103, #100, #99, #97 moved **verbatim** to [next-steps-backlog.md](next-steps-backlog.md#ns-s308-full) in the S308 `--full` sweep.' ''
        printf '%s\n' '> Items #102, #101, #98, #95, #96, #89, #90, #91, #92, #93, #94, #88, #86, #87, #85, #84, #83, #82, #78, #79, #80, #81, #77, #76, #75 moved **verbatim** to [next-steps-backlog.md](next-steps-backlog.md#ns-s299-full) in the S299 `--full` sweep.' ''
        printf '%s\n' '> Full Next Steps detail (S317 trim, verbatim): [next-steps-backlog.md](next-steps-backlog.md#ns-s317-full)' ''
        printf '%s\n' '> Full Next Steps detail (S307 trim, verbatim): [next-steps-backlog.md](next-steps-backlog.md#ns-s307-full)' ''
        printf '%s\n' '> Full Next Steps detail (S299 trim, verbatim): [next-steps-backlog.md](next-steps-backlog.md#ns-s299-full)' ''
        printf '%s\n' '## Session History' '' '> Full history: [session-history.md](session-history.md)' '' '### Last Session (Session 321) - 2026-11-19'
        _n=1
        while [ "$_n" -le 5 ]; do
            printf '%s\n' "- Shipped part $_n of the invite work: $(pad 2 'a username is assigned on confirm; ')"
            _n=$((_n + 1))
        done
    } > "$_s"

    # ---------------- archives ----------------
    printf '%s\n' '# Completed Work' '' '> Full checklist of completed tasks. Referenced from [STATUS.md](STATUS.md).' '' '---' '' '- [x] Built the first widget - `src/widget.ts`' > "$_d/docs/completed-work.md"
    printf '%s\n' '# Key Decisions' '' '> Full decision log. Referenced from [CLAUDE.md](../CLAUDE.md).' '' '| Decision | Rationale |' '|----------|-----------|' '| Use widgets | They compose better than gadgets. |' > "$_d/docs/key-decisions.md"
    printf '%s\n' '# Session History Archive' '' '> Auto-managed by `/bx:save`. Last session summary is in [STATUS.md](STATUS.md).' '' '---' '' '### Session 320 - 2026-11-18: accepting an invite assigns a username (commit: 8262e120)' '' '### Session 321 - 2026-11-19' '**What happened:**' '- An invite link assigns a username' > "$_d/docs/session-history.md"
    printf '%s\n' '# Known Issues Archive' '' '> Issues moved out of [CLAUDE.md](../CLAUDE.md) by `/bx:save`. `Resolved` entries are' '> history; `Open` entries are still live and linked from CLAUDE.md.' '' '---' '' '### Widget cache corruption is RESOLVED (S3) — Resolved S3 (2026-01-01)' '' '**Widget cache corruption is RESOLVED (S3).** Fixed by a rebuild.' > "$_d/docs/known-issues.md"

    # The backlog already holds, byte for byte, some of the lines a trim would
    # archive: Next Steps items 124 and 123, and In Progress items W10..W14.
    # A de-duplicating trim appends none of them a second time.
    {
        printf '%s\n' '# Next Steps — Backlog Detail' '' '> Detail rolled off [STATUS.md](STATUS.md) by `/bx:save --full`.' '' '---' ''
        printf '%s\n' '## Next Steps detail rolled off STATUS.md (S317 --full)' '' '<a id="ns-s317-full"></a>' ''
        for _n in 124 123; do
            printf '%s\n' "$_n. **Item $_n: follow-up $_n** — $(pad 4 'confirm the copy call, then read the result in production; ') → [detail](next-steps-backlog.md#ns-s317-full)" ''
        done
        printf '%s\n' '## In Progress detail rolled off STATUS.md (S319 --full)' '' '<a id="ip-s319-full"></a>' ''
        _n=10
        while [ "$_n" -le 14 ]; do
            _k="$(printf '%02d' "$_n")"
            printf '%s\n' "- **Workstream W$_k LIVE (S3$_k, \`c0ffee$_k\`, deployment \`dpl_fixture$_k\`).** Owed $_k: one read of production data and one owner walk. Owed items → [detail](next-steps-backlog.md#ip-s319-full)"
            _n=$((_n + 1))
        done
    } > "$_b"
}

# fx-v0: a git repo with no CLAUDE.md at all
init_repo "$DEST/fx-v0"
echo "# Readme" > "$DEST/fx-v0/README.md"
commit_all "$DEST/fx-v0" "init"
echo "fx-v0          (no CLAUDE.md)"

# fx-v1: the legacy layout, clean tree
init_repo "$DEST/fx-v1"
write_v1_claude_md "$DEST/fx-v1"
stub_docs "$DEST/fx-v1" completed-work key-decisions session-history
commit_all "$DEST/fx-v1" "init"
echo "fx-v1          (legacy layout, clean)"

# fx-v1-envvars: legacy layout, clean tree, but ## Environment Variables is
# POPULATED -- exercises the env_vars_disposition: keep migration path, which
# no other fixture reaches (they all carry "None required.", which reads as
# empty under the populated-token rule).
init_repo "$DEST/fx-v1-envvars"
write_v1_envvars_claude_md "$DEST/fx-v1-envvars"
stub_docs "$DEST/fx-v1-envvars" completed-work key-decisions session-history
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
stub_docs "$DEST/fx-v1-sparse" key-decisions
commit_all "$DEST/fx-v1-sparse" "init"
echo "fx-v1-sparse   (legacy layout, only Next Steps present, clean)"

# fx-v1-ineligible: state sections present, but ## Key Decisions is missing --
# the eligibility pre-flight must decline without prompting.
init_repo "$DEST/fx-v1-ineligible"
write_v1_ineligible_claude_md "$DEST/fx-v1-ineligible"
stub_docs "$DEST/fx-v1-ineligible" completed-work session-history
commit_all "$DEST/fx-v1-ineligible" "init"
echo "fx-v1-ineligible (legacy layout, missing Key Decisions, clean)"

# fx-partial-conflict: docs/STATUS.md exists with a TRUNCATED ## Current Status
# vs. CLAUDE.md's -- migration must detect `partial` and, on the delete-path
# rehearsal (Step 0b, not this script), block rather than merge or overwrite.
init_repo "$DEST/fx-partial-conflict"
write_partial_conflict_pair "$DEST/fx-partial-conflict"
stub_docs "$DEST/fx-partial-conflict" completed-work key-decisions session-history
commit_all "$DEST/fx-partial-conflict" "init"
echo "fx-partial-conflict (interrupted migration, conflicting STATUS.md)"

# fx-arch-preexisting: v1 layout, but docs/architecture.md already exists and
# matches ## Architecture Summary's body byte-for-byte -- migration must proceed
# and leave that file untouched. This is the one gate path where a mistake
# DELETES rather than blocks; the delete-path rehearsal against it is Step 0b,
# not this script -- this fixture is only the substrate.
init_repo "$DEST/fx-arch-preexisting"
write_v1_claude_md "$DEST/fx-arch-preexisting"
stub_docs "$DEST/fx-arch-preexisting" completed-work key-decisions session-history
write_architecture_md "$DEST/fx-arch-preexisting"
commit_all "$DEST/fx-arch-preexisting" "init"
echo "fx-arch-preexisting (legacy layout, docs/architecture.md pre-existing & matching)"

# fx-ki-resolved: v2, Known Issues ~6k with three RESOLVED entries (~3.9k) and
# three open ones (~2.1k). The 7.3 shrinker must get under 2500 by moving the
# resolved entries ONLY.
init_repo "$DEST/fx-ki-resolved"
ki_head  "$DEST/fx-ki-resolved"
ki_entry "$DEST/fx-ki-resolved" "Widget cache corruption is RESOLVED (S3)." 25
ki_entry "$DEST/fx-ki-resolved" "Gadget sync stalls on large batches (S4)." 13
ki_entry "$DEST/fx-ki-resolved" "The S5 import deadlock is resolved (S6)." 25
ki_entry "$DEST/fx-ki-resolved" "Exporter drops the final row (S7)." 13
ki_entry "$DEST/fx-ki-resolved" "Flaky auth refresh: RESOLVED by retry (S8)." 25
ki_entry "$DEST/fx-ki-resolved" "Report totals are off by one (S9)." 13
ki_tail  "$DEST/fx-ki-resolved"
stub_docs "$DEST/fx-ki-resolved" completed-work key-decisions session-history
commit_all "$DEST/fx-ki-resolved" "init"
echo "fx-ki-resolved (v2, Known Issues ~6k, three resolved entries)"

# fx-ki-unresolved: v2, Known Issues ~6k with ONE small resolved entry and seven
# open ones. After the resolved entry moves the section is still over 4000, so
# the shrinker moves the oldest OPEN entries until it is under 4000 -- not 2500.
# Three traps: entry 2's lead says "unresolved", entry 3's BODY says "resolved",
# entry 4's lead uses "resolved" in its technical sense. All three are open.
init_repo "$DEST/fx-ki-unresolved"
ki_head  "$DEST/fx-ki-unresolved"
ki_entry "$DEST/fx-ki-unresolved" "Widget cache corruption is RESOLVED (S3)." 7
ki_entry "$DEST/fx-ki-unresolved" "Gadget sync stall is still unresolved (S4)." 15
ki_entry "$DEST/fx-ki-unresolved" "Importer deadlock under load (S5)." 15 "It was resolved upstream once, then regressed."
ki_entry "$DEST/fx-ki-unresolved" "Export paths are resolved against cwd (S6)." 15
ki_entry "$DEST/fx-ki-unresolved" "Report totals are off by one (S7)." 15
ki_entry "$DEST/fx-ki-unresolved" "Auth refresh is flaky on cold start (S8)." 15
ki_entry "$DEST/fx-ki-unresolved" "Scheduler skips the DST hour (S9)." 15
ki_entry "$DEST/fx-ki-unresolved" "Uploads over 2GB time out (S9)." 15
ki_tail  "$DEST/fx-ki-unresolved"
stub_docs "$DEST/fx-ki-unresolved" completed-work key-decisions session-history
commit_all "$DEST/fx-ki-unresolved" "init"
echo "fx-ki-unresolved (v2, Known Issues ~6k, one resolved entry, three lead/body traps)"

# fx-ki-rotate: v2 with a >100k docs/known-issues.md whose 60th entry is Open.
# Part 7.7 must cut entries 1-59 only: the cut never extends past the first
# Open entry, even though the live file then stays over the 50k target.
init_repo "$DEST/fx-ki-rotate"
write_v2_pair "$DEST/fx-ki-rotate"
write_ki_rotate_archive "$DEST/fx-ki-rotate"
commit_all "$DEST/fx-ki-rotate" "init"
echo "fx-ki-rotate   (v2, docs/known-issues.md >100k, Open entry at #60)"

# fx-size-budget: v2, both live files over their size budget in the shape a
# long-running project reaches (Part 7). One --full run with "apply all" must
# bring both under budget; a second run must change nothing.
init_repo "$DEST/fx-size-budget"
write_size_budget_fixture "$DEST/fx-size-budget"
commit_all "$DEST/fx-size-budget" "init"
echo "fx-size-budget (v2, CLAUDE.md ~16k and STATUS.md ~21k, standing rules + scaffolding)"

echo ""
echo "Fixtures built in $DEST"
