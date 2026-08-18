# bx Doc Schema v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split always-loaded instructions from session state — CLAUDE.md keeps instructions, `docs/STATUS.md` holds state — and migrate every existing repo forward automatically, safely, and reversibly.

**Architecture:** A shared reference file (`doc-schema.md`) defines both layouts and the detection predicate exactly once; both skills read it. `/bx:save` gains a fourth mode (MIGRATE) that detects the v1 layout, guards on a clean tree, asks for consent, dispatches a `doc-migrator` subagent to do mechanical file surgery, verifies invariants, commits in isolation, then falls through to a normal UPDATE. `/bx:resume` reads whichever layout it finds and never writes.

**Tech Stack:** Markdown skill/agent definitions, bash 3.2-compatible shell scripts, PowerShell 5.1-compatible scripts. No new dependencies — no jq, no test framework.

**Spec:** `docs/superpowers/specs/2026-08-17-bx-doc-schema-v2-design.md`

## Global Constraints

- **Schema marker, verbatim:** `<!-- bx-doc-schema: 2 -->` — an HTML comment, because block-level HTML comments are stripped before CLAUDE.md enters context, making it free at runtime and greppable on disk. Written **last** during migration so an interrupted run reads as `partial`.
- **State file path, verbatim:** `docs/STATUS.md`. Pointer line left in CLAUDE.md, verbatim: `> Session state: [docs/STATUS.md](docs/STATUS.md)`
- **CLAUDE.md (v2) sections:** `## Project Overview`, `## Key Decisions`, `## Known Issues / Blockers`, and `## Environment Variables` *only when populated*.
- **STATUS.md sections, in this order:** `## Current Status`, `## Completed`, `## In Progress`, `## Next Steps`, `## Session History`.
- **"Populated" is mechanical, not judgmental:** `## Environment Variables` is **populated iff its body contains a token matching `[A-Z][A-Z0-9_]{2,}` anywhere** (three or more consecutive uppercase/digit/underscore characters, unanchored). Populated means keep verbatim; otherwise drop. State this rule textually identically everywhere it appears, like the marker string. *(Corrected mid-execution — the original line-anchored `^[A-Z_][A-Z0-9_]*` was wrong in both directions: it classified `None required.` as populated, and classified a real bullet/table section such as ``- `DATABASE_URL` — …`` as empty, which would have silently dropped it. The rule deliberately errs toward keeping content: `None required. See README.` reads as populated, and that is the safe failure.)*
- **Never introduce `@path` imports** into CLAUDE.md or STATUS.md. `@` imports load at launch and would invert the entire design. Offload links stay lazy markdown links.
- **One version bump only, in Task 9** — `bx/.claude-plugin/plugin.json` goes `1.0.0` → `2.0.0` once at the end, not per-commit. The S54 bump-on-`bx/**`-change rule is satisfied by the branch's final state.
- **Shell scripts must be LF.** Enforced by `.gitattributes` (`*.sh text eol=lf`); do not fight it.
- **`.ps1` files must be pure ASCII.** Windows PowerShell 5.1 decodes a BOM-less `.ps1` as the ANSI codepage, so a UTF-8 em-dash becomes bytes ending in a quote that terminates any string it sits inside (S55). Applies to `bx/scripts/session-start-context.ps1`.
- **bash 3.2 compatible** (macOS ships 3.2): no `mapfile`, no `${var,,}`, no associative arrays. Never expand a possibly-empty array as `"${arr[@]}"` under `set -u`.
- **PowerShell: never rely on `try/catch` to catch a native executable's failure** — check `$LASTEXITCODE` (S40).
- **Subagents cannot prompt the user.** All consent gates stay on the orchestrator (`mode-update.md:108`).
- **Cross-skill reference reads resolve as `../save/references/...` against the skill base directory** Claude Code announces at skill load — never repo-rooted paths (S48).
- **Repo commit convention:** end every commit message with the trailer `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.
- **Migration is opportunistic, never blocking.** A dirty tree, a declined consent, or `--skip-migrate` must all still allow the session's normal save to complete.

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `bx/skills/save/references/doc-schema.md` | Create | The single contract: both layouts, detection predicate, marker semantics, invariants. Read by BOTH skills. |
| `bx/skills/save/references/mode-migrate.md` | Create | MIGRATE mode: clean-tree guard, consent copy, packet spec, dispatch, verify, commit, fall-through. |
| `bx/agents/doc-migrator.md` | Create | Sonnet subagent. Mechanical file surgery only; no judgment, no rewriting. |
| `bx/skills/save/tests/assert-doc-schema.sh` | Create | Deterministic post-condition checker. Runs against any repo. |
| `bx/skills/save/tests/make-fixtures.sh` | Create | Builds the five fixture repos. |
| `bx/skills/save/tests/test-hook-layout.sh` | Create | Asserts the SessionStart hook reads the right file and stops at the right header. |
| `bx/skills/save/SKILL.md` | Modify | 4-state mode table; loads `doc-schema.md`; `--skip-migrate`. |
| `bx/skills/save/references/mode-update.md` | Modify | Step 0 reads STATUS.md; packet split; Parts 1.2–1.8 re-homed; Part 3 glob widened; Part 4 rewritten. |
| `bx/skills/save/references/claude-md-sections.md` | Modify | Defines BOTH files' required sections. |
| `bx/skills/save/references/doc-structure-rules.md` | Modify | Target-state table + preservation clause for v1→v2. |
| `bx/skills/save/references/verification-checklists.md` | Modify | MIGRATE checklist + invariants. |
| `bx/skills/save/references/mode-create.md` | Modify | Emits v2 directly. |
| `bx/skills/save/references/mode-refactor.md` | Modify | Emits v2 directly. |
| `bx/agents/save-writer.md` | Modify | Writes STATUS.md; packet field renames. |
| `bx/skills/resume/SKILL.md` | Modify | Dual-layout read; stop re-reading CLAUDE.md; read-only. |
| `bx/skills/resume/references/summary-template.md` | Modify | Layout + migration-pending lines. |
| `bx/skills/resume/references/task-hydration.md` | Modify | Hydrates from STATUS.md. |
| `bx/scripts/session-start-context.sh` | Modify | Dual-layout + single-section extractor fix. |
| `bx/scripts/session-start-context.ps1` | Modify | Same, mirrored. ASCII-only. |
| `bx/.claude-plugin/plugin.json` | Modify | `2.0.0`. |
| `CHANGELOG.md` | Modify | v2.0.0 entry with migration note. |
| `README.md` | Modify | Document v2 layout + migration. |

---

### Task 1: Schema contract + post-condition checker

**Files:**
- Create: `bx/skills/save/references/doc-schema.md`
- Create: `bx/skills/save/tests/assert-doc-schema.sh`
- Test: `bx/skills/save/tests/assert-doc-schema.sh` is itself the test harness; exercised in Task 2.

**Interfaces:**
- Consumes: nothing.
- Produces: `assert-doc-schema.sh <repo-path> [--expect v0|v1|v2|partial] [--before <old-claude-md>]` — prints `PASS`/`FAIL` lines, exits 0 on all-pass and 1 otherwise. Also defines the canonical marker string `<!-- bx-doc-schema: 2 -->` and the detection order. Tasks 2, 4, and 10 call this script; Tasks 4–8 cite `doc-schema.md`.

- [ ] **Step 1: Write the failing test**

Create a throwaway v2-shaped repo and run the not-yet-written checker against it:

```bash
cd "$(mktemp -d)" && git init -q .
mkdir -p docs
printf '%s\n' '<!-- bx-doc-schema: 2 -->' 'Last Updated: 2026-08-17' '' '## Project Overview' 'x' '' '## Key Decisions' 'x' '' '## Known Issues / Blockers' 'x' '' '> Session state: [docs/STATUS.md](docs/STATUS.md)' > CLAUDE.md
printf '%s\n' 'Last Updated: 2026-08-17' '' '## Current Status' 'x' '' '## Completed' 'x' '' '## In Progress' 'x' '' '## Next Steps' 'x' '' '## Session History' 'x' > docs/STATUS.md
bash /c/Development/projects/claude-config/bx/skills/save/tests/assert-doc-schema.sh . --expect v2
```

- [ ] **Step 2: Run it to verify it fails**

Expected: `bash: ...assert-doc-schema.sh: No such file or directory`, exit 127.

- [ ] **Step 3: Write `bx/skills/save/tests/assert-doc-schema.sh`**

```bash
#!/usr/bin/env bash
# assert-doc-schema.sh - verify a repo satisfies the bx doc schema invariants.
#
# Usage: assert-doc-schema.sh <repo> [--expect v0|v1|v2|partial] [--before <file>]
#   --expect  assert the detected layout equals this value
#   --before  path to a copy of the pre-migration CLAUDE.md, enabling the
#             header-conservation and no-content-loss invariants
#
# Exit 0 = every assertion passed. Exit 1 = at least one failed.
# bash 3.2 compatible.

set -uo pipefail

REPO=""; EXPECT=""; BEFORE=""
while [ $# -gt 0 ]; do
    case "$1" in
        --expect) EXPECT="${2:-}"; shift 2 ;;
        --before) BEFORE="${2:-}"; shift 2 ;;
        *) REPO="$1"; shift ;;
    esac
done
[ -n "$REPO" ] || { echo "usage: assert-doc-schema.sh <repo> [--expect V] [--before F]"; exit 2; }

MARKER='<!-- bx-doc-schema: 2 -->'
CLAUDE_MD="$REPO/CLAUDE.md"
STATUS_MD="$REPO/docs/STATUS.md"
STATE_SECTIONS="Current Status|Completed|In Progress|Next Steps|Session History"
INSTR_SECTIONS="Project Overview|Key Decisions|Known Issues / Blockers"

FAILURES=0
pass() { echo "  PASS  $1"; }
fail() { echo "  FAIL  $1"; FAILURES=$((FAILURES + 1)); }

detect() {
    if [ ! -f "$CLAUDE_MD" ]; then echo v0; return; fi
    if grep -qF "$MARKER" "$CLAUDE_MD"; then echo v2; return; fi
    if [ -f "$STATUS_MD" ]; then echo partial; return; fi
    if grep -qE "^## ($STATE_SECTIONS)" "$CLAUDE_MD"; then echo v1; return; fi
    echo v0
}

LAYOUT="$(detect)"
echo "detected layout: $LAYOUT"

if [ -n "$EXPECT" ]; then
    if [ "$LAYOUT" = "$EXPECT" ]; then pass "layout is $EXPECT"
    else fail "layout is $LAYOUT, expected $EXPECT"; fi
fi

# --- Invariant 3: no @path imports (applies to every layout) ---
for f in "$CLAUDE_MD" "$STATUS_MD"; do
    [ -f "$f" ] || continue
    # strip fenced code blocks and inline code spans before scanning
    stripped="$(awk '/^```/{inb=!inb; next} !inb' "$f" | sed 's/`[^`]*`//g')"
    if printf '%s' "$stripped" | grep -qE '(^|[[:space:]])@[A-Za-z0-9_./~-]+'; then
        fail "$(basename "$f") contains an @path import (would force eager load)"
    else
        pass "$(basename "$f") has no @path imports"
    fi
done

if [ "$LAYOUT" = "v2" ]; then
    # --- CLAUDE.md holds instructions only ---
    if grep -qE "^## ($STATE_SECTIONS)" "$CLAUDE_MD"; then
        fail "CLAUDE.md still contains state sections: $(grep -oE "^## ($STATE_SECTIONS)" "$CLAUDE_MD" | tr '\n' ' ')"
    else
        pass "CLAUDE.md contains no state sections"
    fi
    for s in "Project Overview" "Key Decisions" "Known Issues / Blockers"; do
        if grep -qF "## $s" "$CLAUDE_MD"; then pass "CLAUDE.md has ## $s"
        else fail "CLAUDE.md missing ## $s"; fi
    done
    if grep -qF '> Session state: [docs/STATUS.md](docs/STATUS.md)' "$CLAUDE_MD"; then
        pass "CLAUDE.md has the STATUS.md pointer"
    else
        fail "CLAUDE.md missing the '> Session state:' pointer line"
    fi

    # --- STATUS.md holds state ---
    if [ -f "$STATUS_MD" ]; then
        pass "docs/STATUS.md exists"
        for s in "Current Status" "Completed" "In Progress" "Next Steps" "Session History"; do
            if grep -qF "## $s" "$STATUS_MD"; then pass "STATUS.md has ## $s"
            else fail "STATUS.md missing ## $s"; fi
        done
        if grep -qE '^Last Updated' "$STATUS_MD"; then pass "STATUS.md has a Last Updated line"
        else fail "STATUS.md missing Last Updated (staleness signal must follow the state)"; fi
    else
        fail "docs/STATUS.md missing in a v2 repo"
    fi

    # --- Invariant 1: no header appears in both files ---
    if [ -f "$STATUS_MD" ]; then
        dupes="$(comm -12 \
            <(grep -oE '^## .*' "$CLAUDE_MD" | sort -u) \
            <(grep -oE '^## .*' "$STATUS_MD" | sort -u))"
        if [ -z "$dupes" ]; then pass "no header appears in both files"
        else fail "headers duplicated across files: $(printf '%s' "$dupes" | tr '\n' ' ')"; fi
    fi
fi

# --- Invariants 1 & 2 against the pre-migration snapshot ---
if [ -n "$BEFORE" ] && [ -f "$BEFORE" ]; then
    missing=""
    while IFS= read -r h; do
        # ## Architecture Summary relocates to docs/architecture.md;
        # ## Environment Variables is dropped only when empty.
        case "$h" in
            "## Architecture Summary")
                [ -f "$REPO/docs/architecture.md" ] || missing="$missing '$h'"
                continue ;;
            "## Environment Variables")
                continue ;;
        esac
        found=0
        for f in "$CLAUDE_MD" "$STATUS_MD"; do
            [ -f "$f" ] || continue
            grep -qxF "$h" "$f" && found=$((found + 1))
        done
        [ "$found" -eq 1 ] || missing="$missing '$h'(x$found)"
    done < <(grep -oE '^## .*' "$BEFORE" | sort -u)
    if [ -z "$missing" ]; then pass "header conservation: every pre-migration header lands exactly once"
    else fail "header conservation violated:$missing"; fi

    before_bytes="$(wc -c < "$BEFORE" | tr -d ' ')"
    after_bytes=0
    for f in "$CLAUDE_MD" "$STATUS_MD" "$REPO/docs/architecture.md"; do
        [ -f "$f" ] && after_bytes=$((after_bytes + $(wc -c < "$f" | tr -d ' ')))
    done
    # v2 adds a marker, a pointer line and a second Last Updated, so after >= before
    # minus a possible empty Environment Variables stub (generously, 200 bytes).
    if [ "$after_bytes" -ge $((before_bytes - 200)) ]; then
        pass "no content loss ($before_bytes -> $after_bytes bytes across files)"
    else
        fail "content loss: $before_bytes -> $after_bytes bytes"
    fi
fi

echo ""
if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES assertion(s) failed."; exit 1; fi
echo "All assertions passed."
```

- [ ] **Step 4: Run the test to verify it passes**

Re-run the Step 1 command.
Expected: `detected layout: v2`, all `PASS` lines, `All assertions passed.`, exit 0.

- [ ] **Step 5: Write `bx/skills/save/references/doc-schema.md`**

Content, verbatim structure:

```markdown
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

`## Environment Variables` is **conditional**. It is **populated iff its body contains a
token matching `[A-Z][A-Z0-9_]{2,}` anywhere** — three or more consecutive uppercase, digit
or underscore characters, unanchored, so variable names are found inside bullets, tables and
backticks as well as at line start. Populated means keep verbatim; otherwise drop. The rule
errs toward keeping: prose containing any acronym reads as populated, and retaining a noise
section is strictly safer than dropping a real one.

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
```

- [ ] **Step 6: Verify the contract and the checker agree**

Run:
```bash
grep -c 'bx-doc-schema: 2' bx/skills/save/references/doc-schema.md bx/skills/save/tests/assert-doc-schema.sh
```
Expected: both files report at least 1. If the marker strings differ by even a space, detection silently fails everywhere.

- [ ] **Step 7: Commit**

```bash
git add bx/skills/save/references/doc-schema.md bx/skills/save/tests/assert-doc-schema.sh
git commit -m "feat(save): doc schema v2 contract + post-condition checker

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Fixture repo builder

**Files:**
- Create: `bx/skills/save/tests/make-fixtures.sh`

**Interfaces:**
- Consumes: `assert-doc-schema.sh` from Task 1.
- Produces: `make-fixtures.sh <dest-dir>` — creates five git repos named `fx-v0`, `fx-v1`, `fx-v2`, `fx-partial`, `fx-dirty` under `<dest-dir>`, and prints one line per fixture. Tasks 4 and 8 run the skills against these.

- [ ] **Step 1: Write the failing test**

```bash
DEST="$(mktemp -d)"
bash bx/skills/save/tests/make-fixtures.sh "$DEST"
for fx in fx-v0:v0 fx-v1:v1 fx-v2:v2 fx-partial:partial fx-dirty:v1; do
  name="${fx%%:*}"; want="${fx##*:}"
  bash bx/skills/save/tests/assert-doc-schema.sh "$DEST/$name" --expect "$want" || echo "MISMATCH $name"
done
```

- [ ] **Step 2: Run it to verify it fails**

Expected: `No such file or directory` for `make-fixtures.sh`, exit 127.

- [ ] **Step 3: Write `bx/skills/save/tests/make-fixtures.sh`**

```bash
#!/usr/bin/env bash
# make-fixtures.sh - build the five doc-schema fixture repos.
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

write_v2_pair() {  # <path>
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

Last Updated: 2026-08-01 (Session 1)

## Current Status

| Area | Status |
|------|--------|
| Widgets | Complete |

## Completed

2 tasks completed. See [docs/completed-work.md](completed-work.md) for full checklist.

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
echo "fx-v0       (no CLAUDE.md)"

# fx-v1: the legacy layout, clean tree
init_repo "$DEST/fx-v1"
write_v1_claude_md "$DEST/fx-v1"
mkdir -p "$DEST/fx-v1/docs"
echo "# Completed Work" > "$DEST/fx-v1/docs/completed-work.md"
echo "# Key Decisions" > "$DEST/fx-v1/docs/key-decisions.md"
echo "# Session History Archive" > "$DEST/fx-v1/docs/session-history.md"
commit_all "$DEST/fx-v1" "init"
echo "fx-v1       (legacy layout, clean)"

# fx-v2: already migrated - MIGRATE must no-op here
init_repo "$DEST/fx-v2"
write_v2_pair "$DEST/fx-v2"
commit_all "$DEST/fx-v2" "init"
echo "fx-v2       (already migrated)"

# fx-partial: STATUS.md exists but the marker was never written
init_repo "$DEST/fx-partial"
write_v2_pair "$DEST/fx-partial"
# strip the marker to simulate an interrupted run
sed -i.bak '/bx-doc-schema/d' "$DEST/fx-partial/CLAUDE.md" && rm -f "$DEST/fx-partial/CLAUDE.md.bak"
commit_all "$DEST/fx-partial" "init"
echo "fx-partial  (interrupted migration)"

# fx-dirty: legacy layout with an uncommitted change
init_repo "$DEST/fx-dirty"
write_v1_claude_md "$DEST/fx-dirty"
commit_all "$DEST/fx-dirty" "init"
echo "scratch" > "$DEST/fx-dirty/uncommitted.txt"
echo "fx-dirty    (legacy layout, DIRTY tree)"

echo ""
echo "Fixtures built in $DEST"
```

- [ ] **Step 4: Run the test to verify it passes**

Re-run the Step 1 command.
Expected: five `assert-doc-schema.sh` runs, each printing its expected layout and `All assertions passed.`, and **no** `MISMATCH` lines.

- [ ] **Step 5: Verify the dirty fixture is actually dirty**

```bash
git -C "$DEST/fx-dirty" status --porcelain
```
Expected: one line, `?? uncommitted.txt`. If empty, the clean-tree guard can never be exercised.

- [ ] **Step 6: Commit**

```bash
git add bx/skills/save/tests/make-fixtures.sh
git commit -m "test(save): fixture repos for doc-schema migration

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: SessionStart hook — dual-layout read + single-section extractor fix

**Files:**
- Modify: `bx/scripts/session-start-context.sh:53-69`
- Modify: `bx/scripts/session-start-context.ps1` (the equivalent block)
- Create: `bx/skills/save/tests/test-hook-layout.sh`

**Interfaces:**
- Consumes: `make-fixtures.sh` from Task 2.
- Produces: nothing other tasks call. Independently shippable.

**Why this task exists:** the current extractor is `awk '/^## Current Status/,/^## [^C]/'`. `[^C]` cannot match `## Completed`, so the range runs past it to `## In Progress`; only `head -12` hides the bug today. v2's STATUS.md reproduces the trap exactly, since `## Completed` again follows `## Current Status`.

- [ ] **Step 1: Write the failing test**

Create `bx/skills/save/tests/test-hook-layout.sh`:

```bash
#!/usr/bin/env bash
# test-hook-layout.sh - the SessionStart hook must read the state file that
# actually holds the state, and must stop at the next header.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
HOOK="$REPO_ROOT/bx/scripts/session-start-context.sh"
FAILURES=0
pass() { echo "  PASS  $1"; }
fail() { echo "  FAIL  $1"; FAILURES=$((FAILURES + 1)); }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
bash "$REPO_ROOT/bx/skills/save/tests/make-fixtures.sh" "$TMP" > /dev/null

# --- v1: reads Current Status from CLAUDE.md, stops before ## Completed ---
out="$(cd "$TMP/fx-v1" && bash "$HOOK" 2>/dev/null)"
case "$out" in *"## Current Status"*) pass "v1: emits Current Status" ;;
                *) fail "v1: no Current Status block emitted" ;; esac
case "$out" in *"## Completed"*) fail "v1: leaked into ## Completed (range bug)" ;;
                *) pass "v1: stops before ## Completed" ;; esac

# --- v2: reads Current Status from docs/STATUS.md ---
out="$(cd "$TMP/fx-v2" && bash "$HOOK" 2>/dev/null)"
case "$out" in *"## Current Status"*) pass "v2: emits Current Status from STATUS.md" ;;
                *) fail "v2: no Current Status block (still reading CLAUDE.md?)" ;; esac
case "$out" in *"## Completed"*) fail "v2: leaked into ## Completed (range bug)" ;;
                *) pass "v2: stops before ## Completed" ;; esac
case "$out" in *"Widget refactor"*) fail "v2: leaked into ## In Progress" ;;
                *) pass "v2: stops before ## In Progress" ;; esac

if [ "$FAILURES" -gt 0 ]; then echo ""; echo "$FAILURES check(s) failed."; exit 1; fi
echo ""; echo "All checks passed."
```

- [ ] **Step 2: Run it to verify it fails**

Run: `bash bx/skills/save/tests/test-hook-layout.sh`
Expected: the two `v2:` "emits Current Status" / "stops before" checks FAIL (the hook only reads CLAUDE.md), and `v1: stops before ## Completed` FAILS if the status table ever exceeds the `head -12` cut. At minimum the v2 checks must fail.

- [ ] **Step 3: Fix `bx/scripts/session-start-context.sh`**

Replace lines 52–69 (the `# CLAUDE.md Current Status table (if present)` block) with:

```bash
# Current Status + freshness. Schema v2 keeps state in docs/STATUS.md; v1 keeps
# it in CLAUDE.md. Read whichever holds it, or the banner goes silently empty.
state_file=""
if [ -f "$repo_root/docs/STATUS.md" ]; then
  state_file="docs/STATUS.md"
elif [ -f "$repo_root/CLAUDE.md" ]; then
  state_file="CLAUDE.md"
fi

if [ -n "$state_file" ]; then
  echo ""
  echo "**Project status** (from \`$state_file\`):"
  grep -i "^Last Updated" "$repo_root/$state_file" | head -1
  # Single-section extractor. The old range /^## Current Status/,/^## [^C]/
  # could not stop at "## Completed" and ran on into "## In Progress".
  awk '/^## Current Status/{f=1; print; next} /^## /{f=0} f' \
      "$repo_root/$state_file" 2>/dev/null | head -12 || true

  # Stale-doc check against the file that actually carries the state.
  state_mtime="$(git log -1 --format=%ct -- "$state_file" 2>/dev/null || echo 0)"
  head_commit_mtime="$(git log -1 --format=%ct 2>/dev/null || echo 0)"
  if [ "$state_mtime" -gt 0 ] && [ "$head_commit_mtime" -gt "$state_mtime" ]; then
    age_days=$(( (head_commit_mtime - state_mtime) / 86400 ))
    if [ "$age_days" -gt 2 ]; then
      echo ""
      echo "_($state_file last updated $age_days days before the latest commit - may be stale. Run \`/bx:resume\` to verify.)_"
    fi
  fi
fi
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `bash bx/skills/save/tests/test-hook-layout.sh`
Expected: 5 `PASS` lines, `All checks passed.`, exit 0.

- [ ] **Step 5: Mirror the change in `bx/scripts/session-start-context.ps1`**

Apply the same three changes: pick `docs/STATUS.md` over `CLAUDE.md`; extract exactly one section (in PowerShell, iterate lines with a flag rather than a range match); point the staleness `git log` at `$stateFile`. Keep the file **pure ASCII** — no em-dashes, no arrows.

- [ ] **Step 6: Verify the PowerShell file parses on both hosts and is ASCII**

```bash
powershell.exe -NoProfile -Command "\$e=\$null; [void][System.Management.Automation.Language.Parser]::ParseFile('C:\Development\projects\claude-config\bx\scripts\session-start-context.ps1',[ref]\$null,[ref]\$e); if(\$e){\$e.Count.ToString() + ' PARSE ERRORS'}else{'OK'}"
grep -cP '[^\x00-\x7F]' bx/scripts/session-start-context.ps1
```
Expected: `OK`, and a non-ASCII count of `0`.

- [ ] **Step 7: Commit**

```bash
git add bx/scripts/session-start-context.sh bx/scripts/session-start-context.ps1 bx/skills/save/tests/test-hook-layout.sh
git commit -m "fix(hooks): read state from STATUS.md or CLAUDE.md; stop at next header

The old range /^## Current Status/,/^## [^C]/ could not terminate on
'## Completed' and ran into '## In Progress'; head -12 hid it.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `doc-migrator` subagent + MIGRATE mode

**Files:**
- Create: `bx/agents/doc-migrator.md`
- Create: `bx/skills/save/references/mode-migrate.md`

**Interfaces:**
- Consumes: `doc-schema.md` (Task 1) for layouts and invariants; `assert-doc-schema.sh` (Task 1) and `make-fixtures.sh` (Task 2) for verification.
- Produces: subagent type `bx:doc-migrator`, dispatched with a **migration packet** containing `project_root`, `today`, `claude_md_path`, `status_md_path`, `architecture_md_path`, `env_vars_disposition` (`keep` | `drop`). Returns a change report with a `warnings:` line. Task 7 wires MIGRATE into `SKILL.md`.

- [ ] **Step 1: Write `bx/agents/doc-migrator.md`**

```markdown
---
name: doc-migrator
description: Applies the bx doc schema v1 -> v2 migration handed off by the /bx:save skill — moves session-state sections from CLAUDE.md into docs/STATUS.md and the architecture tree into docs/architecture.md. Used by the bx:save skill. Do not invoke independently.
model: sonnet
tools: Read, Write, Edit, Grep, Glob
---

You are the migration half of `/bx:save`. The orchestrator has already detected the v1
layout, verified the working tree is clean, and obtained the user's consent. Your job is
**purely mechanical**: relocate sections between files byte-for-byte. You never rewrite,
summarize, compress, or improve prose. You splice; you do not author.

Read `../skills/save/references/doc-schema.md` (resolved against your skill base directory)
for the canonical layouts and invariants before you begin.

## Inputs (from your task prompt)

- `project_root` — absolute repo path.
- `today` — date string for the `Last Updated:` lines.
- `env_vars_disposition` — `keep` or `drop`, already decided by the orchestrator.

## What you do, in this order

1. **Read** `<project_root>/CLAUDE.md`.
2. **Create `<project_root>/docs/STATUS.md`** with this header, then append the five state
   sections **verbatim, in this order**: `## Current Status`, `## Completed`,
   `## In Progress`, `## Next Steps`, `## Session History`.

       # Project Status

       > Session state for `/bx:resume`. Instructions live in [CLAUDE.md](../CLAUDE.md).

       Last Updated: <today>

   Copy each section body byte-for-byte, including tables, links and code fences. Adjust
   only relative links that break by moving one directory deeper: a CLAUDE.md link written
   as `docs/foo.md` becomes `foo.md` in STATUS.md. Do not touch any other text.
3. **If CLAUDE.md has `## Architecture Summary`**, create
   `<project_root>/docs/architecture.md` with this header and append that section's body
   verbatim:

       # Architecture

       > Full architecture detail. Referenced from [CLAUDE.md](../CLAUDE.md).

       ---

4. **Remove** the five state sections and `## Architecture Summary` from CLAUDE.md. If
   `env_vars_disposition` is `drop`, remove `## Environment Variables` too; if `keep`,
   leave it exactly where it is.
5. **Insert the pointer line** into CLAUDE.md as the **last** element, matching
   `doc-schema.md`'s v2 diagram: after `## Environment Variables` when that section is
   kept, otherwise after `## Known Issues / Blockers`, otherwise at end of file.

       > Session state: [docs/STATUS.md](docs/STATUS.md)

   (An earlier draft said "immediately after `## Known Issues / Blockers`" unconditionally,
   which puts the pointer *above* a kept `## Environment Variables` and contradicts the
   canonical layout. `doc-schema.md` is authoritative.)

6. **Update CLAUDE.md's `Last Updated:` line** to `today`.
7. **Write the marker LAST.** Prepend `<!-- bx-doc-schema: 2 -->` as the very first line of
   CLAUDE.md. This is the final write of the entire migration — if anything above failed,
   the marker must not exist, so the run reads as `partial` and can be resumed.

## Idempotency

If CLAUDE.md already contains the marker, change nothing and return
`status: already-v2`. If `docs/STATUS.md` already exists but the marker does not, this is
a resumed `partial` run: **do not recreate STATUS.md**. Determine which of steps 3-7 are
outstanding by inspecting the files, complete only those, and say so in your report.

## Hard rules

- **Never delete content.** Every section you remove from CLAUDE.md must already have been
  written into STATUS.md or architecture.md. If a write failed, stop and report — do not
  continue to the removal step.
- **Never introduce an `@path` import.** Links stay as markdown links.
- **Never compress or reword.** Rationale compression is a separate, separately-consented
  pass that is not your job.
- **Never run git commands.** The orchestrator owns staging and committing.

## Output — change report ONLY

    status: migrated | already-v2 | resumed-partial | failed
    files:
      CLAUDE.md: <old>k -> <new>k chars (<N> sections removed)
      docs/STATUS.md: created (<M> sections, <X> lines)
      docs/architecture.md: created            # omit if no Architecture Summary
    env_vars: kept | dropped
    warnings: <any warnings, or "none">
```

- [ ] **Step 2: Write `bx/skills/save/references/mode-migrate.md`**

```markdown
# MODE: MIGRATE (doc schema v1 -> v2)

Runs when `references/doc-schema.md`'s detection predicate returns **v1** or **partial**.
Unlike Part 0.5, this mode runs on **both** the fast path and `--full` — it is a
precondition for a correct save, not a periodic sweep.

**If `--skip-migrate` is in `$ARGUMENTS`, skip this mode entirely** and run UPDATE against
the v1 layout.

## Step 1: Clean-tree guard

Run `git status --porcelain`. If it emits **any** line:

> "This repo is on the v1 doc layout, but the working tree has [N] uncommitted files.
>  Migration needs a clean tree so it can land as one revertible commit. Commit or stash,
>  then run `/bx:save` again. Continuing with a normal save for now."

Then **skip the rest of this mode and run UPDATE against the v1 layout**. Migration is
opportunistic and must never block the work the user came to do.

## Step 2: Consent gate

Reuses the Part 5.2 / 6.2 sentinel semantics exactly. **If `--silent` is in `$ARGUMENTS`,
treat as declined without asking** — skip the mode, write no marker, and let the next
interactive run ask again.

Otherwise ask via `AskUserQuestion` (numbered fallback if unavailable). State the concrete
delta, computed from the CLAUDE.md already read in Step 0:

> "This repo uses doc schema v1. Migrating moves 5 state sections from CLAUDE.md into
>  `docs/STATUS.md`, and the architecture tree into `docs/architecture.md`. CLAUDE.md
>  drops from [X]k to ~[Y]k chars of always-loaded context. **Nothing is deleted — content
>  moves**, and it lands as one commit you can `git revert`. Migrate now?"

- **Declines** -> skip the rest of this mode, write no marker, run UPDATE on v1. Re-ask next run.
- **Accepts** -> continue.

## Step 3: Snapshot for verification

Copy the current CLAUDE.md to a scratch path (outside the repo) so Step 5 can check header
conservation against it. Use the session scratchpad, never a path inside `project_root` —
a stray file in the repo would defeat the clean-tree guard on the next run.

## Step 4: Dispatch `doc-migrator`

Dispatch one subagent via the Agent tool with `subagent_type: "bx:doc-migrator"`, passing:

- `project_root` — absolute repo path
- `today` — resolved as in `mode-update.md` Step 0.2
- `env_vars_disposition` — `keep` if the `## Environment Variables` body contains a token
  matching `[A-Z][A-Z0-9_]{2,}` anywhere (unanchored), else `drop`. See Global Constraints;
  the rule must read identically here, in `doc-schema.md`, and in `assert-doc-schema.sh`.

Await its change report.

- `status: failed`, or a non-empty `warnings:` line -> go to Step 6 (failure handling).
- `status: already-v2` -> detection was wrong; log it and fall through to UPDATE.
- `status: migrated` or `resumed-partial` -> continue to Step 5.

## Step 5: Verify invariants

Run the checker:

    bash <skill_dir>/tests/assert-doc-schema.sh <project_root> --expect v2 --before <snapshot>

- Exit 0 -> continue to Step 6.
- Exit 1 -> failure handling below.

## Step 6: Commit, or fail cleanly

**On success**, commit the migration **on its own**, separate from the session save, so it
stays independently revertible:

    git add CLAUDE.md docs/STATUS.md docs/architecture.md
    git commit -m "docs: migrate to bx doc schema v2 (CLAUDE.md -> STATUS.md split)"

(Include `docs/architecture.md` only if it was created.)

**On failure — no automatic rollback.** Report what failed, name the files left modified,
and print the exact recovery command:

> "Migration failed at [step]: [what]. The working tree was clean before this ran, so
>  `git restore . && git clean -fd docs/` restores it exactly. Nothing was committed."

Do NOT run those commands yourself. Auto-running `git clean -fd` is precisely the trap the
S42 `/bx:webdesign` review caught.

Then run UPDATE against whatever layout the repo is now in.

## Step 7: Offer the compression pass (optional, separate)

Migration is mechanical. Rationale compression is authored and lossy, so it is a **separate
consented pass** — never bundled, because mixing them makes the diff unreviewable.

If CLAUDE.md's `## Key Decisions` section still exceeds 8000 chars after migration, offer:

> "CLAUDE.md is now [Y]k chars; `## Key Decisions` is [Z]k of that, and every row is already
>  duplicated in `docs/key-decisions.md`. Compressing each rationale to a one-liner would
>  bring CLAUDE.md to roughly [W]k. This rewrites prose (the only lossy step), so it lands as
>  its own commit. Run it now?"

Declining is free and re-offered next run. If `--silent`, treat as declined.

## Step 8: Fall through to UPDATE

Continue into `mode-update.md` against the now-v2 layout. The session's actual save proceeds
normally.
```

- [ ] **Step 3: Verify the agent frontmatter is well-formed and discoverable**

```bash
head -6 bx/agents/doc-migrator.md
grep -c 'model: sonnet' bx/agents/doc-migrator.md
```
Expected: valid YAML frontmatter with `name: doc-migrator`, and `model: sonnet` present once — without it the agent runs on the orchestrator's Opus, the exact S43 bug.

- [ ] **Step 4: Verify no forbidden tool is granted**

```bash
grep '^tools:' bx/agents/doc-migrator.md
```
Expected: `tools: Read, Write, Edit, Grep, Glob` — **no Bash**. The agent must not be able to run git; the orchestrator owns staging and committing.

- [ ] **Step 5: Commit**

```bash
git add bx/agents/doc-migrator.md bx/skills/save/references/mode-migrate.md
git commit -m "feat(save): doc-migrator subagent + MIGRATE mode

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: `/bx:save` contract references

**Files:**
- Modify: `bx/skills/save/references/claude-md-sections.md` (full rewrite)
- Modify: `bx/skills/save/references/doc-structure-rules.md:5-16, 35-56`
- Modify: `bx/skills/save/references/verification-checklists.md`
- Modify: `bx/skills/save/references/mode-create.md`
- Modify: `bx/skills/save/references/mode-refactor.md`

**Interfaces:**
- Consumes: `doc-schema.md` (Task 1).
- Produces: the section contract `/bx:resume` Step 6 validates against. No code symbols.

- [ ] **Step 1: Rewrite `claude-md-sections.md`**

Replace the whole file with:

```markdown
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
```

- [ ] **Step 2: Update `doc-structure-rules.md`**

In the Target State table (lines 5–16), add two rows and change CLAUDE.md's purpose:

| Row | New value |
|---|---|
| **CLAUDE.md** | Purpose becomes `Always-loaded instructions (~7k chars): overview, decisions, blockers` |
| **docs/STATUS.md** | New row — `Session state read on demand by /bx:resume (~10k chars)` / Audience `AI coding assistants` |
| **docs/architecture.md** | New row — `Architecture detail moved out of CLAUDE.md` / Audience `Reference` |

Change the "Size targets" line to: `CLAUDE.md ~7k chars; docs/STATUS.md ~10k chars. When either grows, offload detail to the reference files and keep summaries + links.`

Then append to the "Pruning Is Preservation" section (after line 56):

```markdown
- **Moving session state from CLAUDE.md to `docs/STATUS.md` is preservation.** The v1 -> v2
  migration relocates five sections byte-for-byte; nothing is deleted. CLAUDE.md keeps a
  `> Session state:` pointer so the content is one hop away, and `/bx:resume` reads it
  on demand. This is the same rule as the Key Decisions rollup, applied to state instead
  of decisions.
```

- [ ] **Step 3: Add the MIGRATE checklist to `verification-checklists.md`**

Append a new section:

```markdown
## MIGRATE mode checklist

- [ ] Working tree was clean before migrating (or migration was correctly skipped)
- [ ] User consented, or `--silent`/`--skip-migrate` correctly skipped without writing the marker
- [ ] `docs/STATUS.md` exists with all five state sections in order
- [ ] CLAUDE.md contains none of the five state sections
- [ ] CLAUDE.md line 1 is `<!-- bx-doc-schema: 2 -->`
- [ ] CLAUDE.md contains `> Session state: [docs/STATUS.md](docs/STATUS.md)`
- [ ] `## Architecture Summary` landed in `docs/architecture.md` (if it existed)
- [ ] Both CLAUDE.md and STATUS.md carry a `Last Updated:` line
- [ ] No `@path` imports were introduced
- [ ] `assert-doc-schema.sh <repo> --expect v2 --before <snapshot>` exits 0
- [ ] Migration is its own commit, separate from the session save
```

- [ ] **Step 4: Update `mode-create.md` to emit v2**

The CLAUDE.md template lives at `mode-create.md:63-167`, with its sections at these exact
lines: Project Overview 78, Current Status 89, Completed 101, In Progress 107, Next Steps
114, Key Decisions 122, Architecture Summary 133, Known Issues 139, Environment Variables
148, Session History 158.

Split that one template into two:

- **`## Create: CLAUDE.md Template`** keeps only Project Overview (78), Key Decisions (122),
  Known Issues / Blockers (139), and Environment Variables (148) — the last with the note
  `omit this section entirely when the project needs no env vars`. Prepend
  `<!-- bx-doc-schema: 2 -->` as template line 1 and append the pointer line
  `> Session state: [docs/STATUS.md](docs/STATUS.md)`.
- **`## Create: docs/STATUS.md Template`** — a new sibling section holding Current Status
  (89), Completed (101), In Progress (107), Next Steps (114) and Session History (158),
  in that order, under the header from `doc-schema.md`, with its own `Last Updated:` line.
- Delete the Architecture Summary block (133); the PRD template at `mode-create.md:186`
  already covers architecture for new projects, so nothing is lost.

Add to the Analysis Steps section: `New projects are created at schema v2 directly — they
never pass through v1, so MIGRATE never runs on them.`

- [ ] **Step 4b: Update `mode-refactor.md` to emit v2**

Two edits:

- `mode-refactor.md:7-17` — the `### -> Move to CLAUDE.md (Session Context)` list. Retitle it
  `### -> Move to CLAUDE.md (Instructions)` and keep only overview, decisions and blockers;
  add a sibling `### -> Move to docs/STATUS.md (Session State)` listing status, completed,
  in progress, next steps and session history.
- `mode-refactor.md:47-48` — the Refactor Process bullets. Keep the Key Decisions bullet on
  CLAUDE.md; move the `## Session History` bullet under a new STATUS.md step, and add a step
  that writes the marker **last**, matching `doc-schema.md`'s invariant 4.

- [ ] **Step 5: Verify the contract files agree with each other**

```bash
for s in "Current Status" "Completed" "In Progress" "Next Steps" "Session History"; do
  printf '%-16s doc-schema:%s  claude-md-sections:%s\n' "$s" \
    "$(grep -c "## $s" bx/skills/save/references/doc-schema.md)" \
    "$(grep -c "## $s" bx/skills/save/references/claude-md-sections.md)"
done
grep -c 'Architecture Summary' bx/skills/save/references/claude-md-sections.md
```
Expected: every state section appears in both files; `Architecture Summary` appears **0** times in `claude-md-sections.md` (it is no longer a CLAUDE.md section).

- [ ] **Step 6: Commit**

```bash
git add bx/skills/save/references/
git commit -m "docs(save): section contract for doc schema v2

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: `/bx:save` packet split — `mode-update.md` + `save-writer.md`

**Files:**
- Modify: `bx/skills/save/references/mode-update.md:9-23, 69-88, 217-375, 405-470`
- Modify: `bx/agents/save-writer.md:10-21, 23-47, 65-75`

**Interfaces:**
- Consumes: `doc-schema.md` (Task 1), the section contract (Task 5).
- Produces: the revised **update packet**. Field names, exactly:
  `project_root`, `today`, `claude_md_deltas`, `status_md_deltas`, `status_md_session_block`,
  `session_history_entry`, `completed_items`, `decision_rows`.
  `claude_md_session_block` is **renamed** to `status_md_session_block` — Task 7 and the agent
  must use the new name.

**These two files must change in the same commit.** `save-writer` refuses to fuzzy-match a
missing `old_string` and emits `warnings:` instead, so a half-updated contract surfaces as a
warning on every save rather than losing data — but it still breaks every save until both sides agree.

- [ ] **Step 1: Update `mode-update.md` Step 0.1 reads**

In the "Reads (parallel)" list, add below the CLAUDE.md line:

```markdown
- `docs/STATUS.md` — the session-state file (schema v2). On a v1 repo this does not exist;
  MIGRATE runs first, so by the time UPDATE executes the repo is always v2 unless migration
  was skipped or declined. Handle both: if STATUS.md is absent, target CLAUDE.md's state
  sections exactly as v1 did.
```

- [ ] **Step 2: Update the Update Packet definition**

Replace the `claude_md_deltas` and `claude_md_session_block` bullets with:

```markdown
- `claude_md_deltas` — exact `old -> new` string pairs for CLAUDE.md sections the session
  changed: the `Last Updated:` line, `## Key Decisions` (Part 1.6) and
  `## Known Issues / Blockers` (Part 1.7). **Instructions only** — no state sections.
- `status_md_deltas` — the same, for `docs/STATUS.md`: its `Last Updated:` line, Current
  Status rows (Part 1.2), the `## Completed` summary line (Part 0 / 1.3), In Progress
  (Part 1.4) and Next Steps (Part 1.5).
- `status_md_session_block` — the full replacement text for STATUS.md's `## Session History`
  last-session block (Part 1.8 format, <=5 bullets). Renamed from `claude_md_session_block`
  in schema v2; the block lives in STATUS.md now.
```

- [ ] **Step 3: Re-home the Part 1 sub-sections**

Add this routing table immediately under the Part 1 "Plan-then-batch" note:

```markdown
**Target file per sub-section (schema v2):**

| Sub-section | Target |
|---|---|
| 1.0 Last Updated | **both** CLAUDE.md and docs/STATUS.md |
| 1.2 Current Status | docs/STATUS.md |
| 1.3 Completed | docs/STATUS.md (+ append to docs/completed-work.md) |
| 1.4 In Progress | docs/STATUS.md |
| 1.5 Next Steps | docs/STATUS.md |
| 1.6 Key Decisions | CLAUDE.md (+ append to docs/key-decisions.md) |
| 1.7 Known Issues / Blockers | CLAUDE.md |
| 1.8 Session History | docs/STATUS.md (+ append to docs/session-history.md) |
```

Delete sub-section **1.1 Documentation Links** (it duplicates the pointer line) and
**1.9's** CLAUDE.md-only size check, replacing 1.9 with:

```markdown
### 1.9 Size Check (early advisory)

Measure both files. CLAUDE.md target ~7k, soft cap 12k. docs/STATUS.md target ~10k, soft
cap 20k. Warn per file when over its soft cap and name which Part 7 shrinker will fire.
```

- [ ] **Step 4: Re-home the Part 7 thresholds**

In the Part 7.3 table, change the `Section` column entries to name their file, and delete
the `## Architecture Summary` row entirely (that section no longer exists in CLAUDE.md — it
lives in `docs/architecture.md`, which is not size-managed). Update 7.1's re-measure to
check CLAUDE.md against 12k and STATUS.md against 20k independently.

- [ ] **Step 5: Widen Part 3's glob and rewrite Part 4**

In Part 3.0 step 1, change `Glob docs/**/*.md` to:

```markdown
1. List docs with `Glob docs/**/*.md` **and** root-level docs with `Glob *.md` (single turn,
   two calls). Root docs other than README.md and CLAUDE.md — `workflow.md`, contributor
   guides — are otherwise maintained by nothing and drift silently.
```

Replace Part 4 (Sync Auto-Memory) sections 4.1–4.3 with:

```markdown
### 4.1 What auto-memory is for

Auto memory is written **by Claude**, from its own corrections and learnings, and is loaded
into every session (first 200 lines **or 25KB, whichever comes first**). CLAUDE.md is
written by you. Do not use `/bx:save` to author memory entries that Claude did not learn.

### 4.2 What this step actually does

Only two things:

1. **Prune contradictions.** If a memory file states something this session proved wrong,
   correct or delete that file. A stale memory is worse than a missing one.
2. **Check the index budget.** If `MEMORY.md` is near 200 lines or 25KB, move detail into
   topic files and keep one line per entry in the index. Over either limit, everything past
   it is silently dropped at next load.

### 4.3 What NOT to write

Do not sync tech stack, common commands, key paths, architecture patterns or env var names.
That content is derivable from the repo, duplicates CLAUDE.md and README, and is exactly
what `/doctor`'s trim check removes. Do not sync session state — that is STATUS.md's job.
```

- [ ] **Step 6: Update `save-writer.md` to match**

In the Inputs list, rename `claude_md_session_block` to `status_md_session_block` and add
`status_md_deltas`. In "What you do", change step 2 to apply `claude_md_deltas` to CLAUDE.md
and `status_md_deltas` to `docs/STATUS.md`; change step 3 so the session block is replaced in
**`docs/STATUS.md`**, preserving its `> Full history:` link line, with the "exactly ONE
session block" rule now applying to STATUS.md. Add to the change report format:

```
  docs/STATUS.md: <old>k -> <new>k chars (session block + <N> deltas)
```

Add a fallback line: `If docs/STATUS.md does not exist, the repo is still v1 — apply
status_md_deltas to CLAUDE.md instead and note it under warnings:.`

- [ ] **Step 7: Verify orchestrator and agent agree on every packet field**

```bash
for f in project_root today claude_md_deltas status_md_deltas status_md_session_block session_history_entry completed_items decision_rows; do
  printf '%-26s mode-update:%s  save-writer:%s\n' "$f" \
    "$(grep -c "$f" bx/skills/save/references/mode-update.md)" \
    "$(grep -c "$f" bx/agents/save-writer.md)"
done
grep -c 'claude_md_session_block' bx/skills/save/references/mode-update.md bx/agents/save-writer.md
```
Expected: every field appears at least once in **both** files, and `claude_md_session_block`
appears **0** times in both — a leftover old name means the agent silently skips the session block.

- [ ] **Step 8: Commit**

```bash
git add bx/skills/save/references/mode-update.md bx/agents/save-writer.md
git commit -m "feat(save): split update packet across CLAUDE.md and STATUS.md

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: `/bx:save` SKILL.md mode wiring

**Files:**
- Modify: `bx/skills/save/SKILL.md:3-7, 18-63`

**Interfaces:**
- Consumes: `doc-schema.md` (Task 1), `mode-migrate.md` (Task 4).
- Produces: the four-state mode dispatch. Nothing downstream.

- [ ] **Step 1: Update the frontmatter**

Add `--skip-migrate` to `argument-hint`. Update `description` to mention the migration:
append ` Migrates repos on the older doc layout to schema v2 on first run, with consent.`

- [ ] **Step 2: Replace the Step 1 detection table and logic**

```markdown
| State | Condition | Action |
|-------|-----------|--------|
| **REFACTOR** | Only README.md exists (monolithic) | Split into the v2 structure |
| **CREATE** | No documentation exists | Create the v2 structure from scratch |
| **MIGRATE** | CLAUDE.md exists on doc schema **v1** or **partial** | Migrate to v2, then fall through to UPDATE |
| **UPDATE** | CLAUDE.md exists on doc schema **v2** | Update to reflect current state |

**Detection logic** — the predicate lives in `references/doc-schema.md`; read it and apply
it rather than reimplementing it here:

```
IF README.md exists AND CLAUDE.md missing:
    -> REFACTOR
ELSE IF README.md missing AND CLAUDE.md missing:
    -> CREATE
ELSE:
    layout = doc-schema.md detection predicate
    IF layout is v1 or partial -> MIGRATE
    ELSE                       -> UPDATE
```
```

- [ ] **Step 3: Add `doc-schema.md` to the Step 2 shared reads**

Make it item 1 in the "Load Shared References" list, ahead of `doc-structure-rules.md`:
`1. references/doc-schema.md — the layout contract and detection predicate (read FIRST; Step 1's mode depends on it)`

- [ ] **Step 4: Add MIGRATE to the Step 3 mode table**

Add the row `| **MIGRATE** | references/mode-migrate.md |` and a note:
`MIGRATE runs on both the fast path and --full, then falls through to UPDATE in the same run.`

- [ ] **Step 5: Verify every mode has a reference file that exists**

```bash
for m in migrate update create refactor; do
  printf '%-10s %s\n' "$m" "$([ -f "bx/skills/save/references/mode-$m.md" ] && echo OK || echo MISSING)"
done
grep -c 'skip-migrate' bx/skills/save/SKILL.md
```
Expected: four `OK` lines, and `--skip-migrate` present at least once.

- [ ] **Step 6: Commit**

```bash
git add bx/skills/save/SKILL.md
git commit -m "feat(save): wire MIGRATE mode into detection

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: `/bx:resume` dual-layout read

**Files:**
- Modify: `bx/skills/resume/SKILL.md` (Steps 0, 1, 3.0, 6)
- Modify: `bx/skills/resume/references/summary-template.md`
- Modify: `bx/skills/resume/references/task-hydration.md`

**Interfaces:**
- Consumes: `doc-schema.md` (Task 1) via `../save/references/doc-schema.md`, resolved against
  the skill base directory (S48) — the same mechanism Step 6 already uses for
  `claude-md-sections.md`.
- Produces: nothing. **`/bx:resume` writes nothing to disk in any layout.**

- [ ] **Step 1: Rewrite Step 0 to cover CLAUDE.md**

Replace Step 0's body with:

```markdown
Claude Code loads two things into your context automatically, **before this skill runs**:

- **CLAUDE.md** — loaded in full at session start, and re-injected from disk after `/compact`
- **Auto-memory `MEMORY.md`** — first 200 lines or 25KB, whichever comes first

**Do not re-read either one.** They are already in your context; reading them again
duplicates roughly 7k tokens per resume for zero new information. Read them explicitly only
if they are genuinely absent from your context.

What is NOT auto-loaded, and is therefore this skill's actual job to read:
`docs/STATUS.md`, the `docs/` reference archives, and README.md.
```

- [ ] **Step 2: Rewrite Step 1 for dual-layout reads**

```markdown
## Step 1: Read Session State (Parallel)

First determine the layout using the detection predicate in
`../save/references/doc-schema.md` (resolve against this skill's base directory, not a
repo-rooted path).

**Schema v2** — read in a single parallel turn:
- `docs/STATUS.md` — the session state. This is the primary read.
- `docs/` folder listing.

**Schema v1** (no marker, no STATUS.md) — the state sections are still inside CLAUDE.md,
which is already in your context. Read nothing extra; use what you have, and surface the
migration notice in Step 4.

**README.md is conditional in both layouts.** Read it only when CLAUDE.md's Project Overview
leaves the tech stack or setup genuinely unclear. It is typically the largest doc in the
repo and rarely changes; re-reading it every session is the single most expensive habit
this skill can have.

**Do NOT read by default:** `docs/session-history.md`, `docs/completed-work.md`,
`docs/key-decisions.md`, `docs/architecture.md`. These are archives; `deep` mode reads them.
```

- [ ] **Step 3: Point the staleness check at the state file**

In Step 3.0, replace the CLAUDE.md reference:

```markdown
Compare the **state file's** `Last Updated` date with the latest commit — `docs/STATUS.md`
in schema v2, `CLAUDE.md` in v1. After the split CLAUDE.md may legitimately sit untouched
for weeks while state churns daily, so comparing against CLAUDE.md reports false freshness.

- Run `git log -1 --format=%ci` for the latest commit date
- Parse `Last Updated` from the state file
- If commits are newer, warn: "docs/STATUS.md was last updated [date], but there are [N]
  commits since then."
```

- [ ] **Step 4: Make Step 6 layout-aware and explicitly read-only**

```markdown
## Step 6: Validate Structure

Read `../save/references/doc-schema.md` and `../save/references/claude-md-sections.md`
(resolved against this skill's base directory).

- **Schema v2** — check CLAUDE.md and `docs/STATUS.md` carry their required sections. Note
  any missing ones in the summary and suggest `/bx:save`.
- **Schema v1 or partial** — report, in the summary:

  > "This repo uses doc schema v1. `/bx:save` will offer to migrate it to v2, which moves
  >  session state out of CLAUDE.md into `docs/STATUS.md` and cuts always-loaded context.
  >  Nothing is deleted."

**`/bx:resume` never migrates and never writes.** Migration belongs at session end, where
doc writing already happens and the diff can be reviewed before committing — not at session
start, before any work has been done.
```

- [ ] **Step 5: Update `summary-template.md`**

Add to the Quick Checks block:
```markdown
- Doc schema: [v2 / v1 — migration available via `/bx:save`]
```
And change the Staleness Warning line to name `docs/STATUS.md` in v2.

- [ ] **Step 6: Update `task-hydration.md`**

Change the two source headings from `CLAUDE.md's ## In Progress` / `## Next Steps` to
`the state file's` (`docs/STATUS.md` in v2, `CLAUDE.md` in v1), and the drain reference to
`/bx:save Part 0`. Add: `Known Issues / Blockers remains in CLAUDE.md in both layouts.`

- [ ] **Step 7: Verify resume grants no write tools and reads the schema correctly**

```bash
grep -E '^allowed-tools' bx/skills/resume/SKILL.md
grep -c 'save/references/doc-schema.md' bx/skills/resume/SKILL.md
grep -cE '\bWrite\b|\bEdit\b' bx/skills/resume/SKILL.md
```
Expected: `allowed-tools` contains no `Write` or `Edit`; `doc-schema.md` referenced at least
twice (Steps 1 and 6); the Write/Edit count is 0 outside prose disclaimers — if non-zero,
confirm each hit is the phrase "never writes" and not a granted tool.

- [ ] **Step 8: Commit**

```bash
git add bx/skills/resume/
git commit -m "feat(resume): read both doc layouts; stop re-reading CLAUDE.md

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Version bump, CHANGELOG, README

**Files:**
- Modify: `bx/.claude-plugin/plugin.json`
- Modify: `CHANGELOG.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: everything above.
- Produces: the published `2.0.0` release.

- [ ] **Step 1: Bump the version**

In `bx/.claude-plugin/plugin.json`, set `"version": "2.0.0"`. MAJOR because this breaks a
contract other repos depend on (S54 criterion). The version is the plugin's update cache
key — without this bump, no user ever receives the change.

- [ ] **Step 2: Add the CHANGELOG entry**

Newest-first, at the top of `CHANGELOG.md`:

```markdown
## 2.0.0 — 2026-08-17

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
```

- [ ] **Step 3: Document the layout in README.md**

Add a subsection under the docs/workflow area:

```markdown
### Documentation layout (schema v2)

`CLAUDE.md` holds instructions Claude should have in every session — overview, key
decisions, known blockers. It is loaded in full on every session, so it stays small.

`docs/STATUS.md` holds session state — current status, in progress, next steps, last
session. `/bx:resume` reads it on demand; it is not auto-loaded.

Repos created before v2.0.0 keep working. The first `/bx:save` after updating detects the
old layout and offers to migrate: it needs a clean working tree, asks before changing
anything, and lands the move as a single commit you can `git revert`. Decline and it asks
again next time; `--skip-migrate` skips it permanently.

**Working across machines:** if you migrate a repo on one machine and then open it on
another whose `bx` plugin is still on 1.x, the old skill will not find the sections it
expects. It degrades safely — `save-writer` refuses to guess at a missing anchor and reports
a warning instead of writing to the wrong place — but that session's save will be
incomplete. Update the plugin (`/plugin update bx`) on the second machine. The `cc` launcher
does this automatically on every launch.
```

- [ ] **Step 4: Verify the version is the only one and is well-formed**

```bash
grep -n '"version"' bx/.claude-plugin/plugin.json
head -3 CHANGELOG.md
```
Expected: exactly one `"version": "2.0.0"` line, and CHANGELOG's first heading is `## 2.0.0`.

- [ ] **Step 5: Commit**

```bash
git add bx/.claude-plugin/plugin.json CHANGELOG.md README.md
git commit -m "chore: v2.0.0 — doc schema v2

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Fixture verification, then dogfood on this repo

**Files:**
- No source changes. Produces `CLAUDE.md`, `docs/STATUS.md`, `docs/architecture.md` in this repo.

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Run every fixture through the checker**

```bash
DEST="$(mktemp -d)"
bash bx/skills/save/tests/make-fixtures.sh "$DEST"
bash bx/skills/save/tests/assert-doc-schema.sh "$DEST/fx-v0"          --expect v0
bash bx/skills/save/tests/assert-doc-schema.sh "$DEST/fx-v1"          --expect v1
bash bx/skills/save/tests/assert-doc-schema.sh "$DEST/fx-v1-envvars"  --expect v1
bash bx/skills/save/tests/assert-doc-schema.sh "$DEST/fx-v2"          --expect v2
bash bx/skills/save/tests/assert-doc-schema.sh "$DEST/fx-partial"     --expect partial
bash bx/skills/save/tests/assert-doc-schema.sh "$DEST/fx-dirty"       --expect v1
bash bx/skills/save/tests/test-hook-layout.sh
```
Expected: all seven exit 0.

- [ ] **Step 2: Run `/bx:save` against `fx-v1` and verify the migration**

```bash
cp "$DEST/fx-v1/CLAUDE.md" "$DEST/fx-v1-before.md"
```
Then run `/bx:save` with the repo as scope, accept the migration prompt, and check:
```bash
bash bx/skills/save/tests/assert-doc-schema.sh "$DEST/fx-v1" --expect v2 --before "$DEST/fx-v1-before.md"
git -C "$DEST/fx-v1" log --oneline -2
```
Expected: checker exits 0; the migration is its own commit, message beginning `docs: migrate to bx doc schema v2`.

- [ ] **Step 3: Verify the three negative cases**

| Fixture | Run | Must observe |
|---|---|---|
| `fx-v2` | `/bx:save` | **No** migration prompt; no new migration commit |
| `fx-partial` | `/bx:save`, accept | Marker added; `docs/STATUS.md` **not** recreated or duplicated; checker `--expect v2` exits 0 |
| `fx-dirty` | `/bx:save` | Migration **skipped** with the dirty-tree message; the save still completes; layout still v1 |
| `fx-v1-envvars` | `/bx:save`, accept | `## Environment Variables` **survives into CLAUDE.md** — the section lists real variables, so `env_vars_disposition` must resolve to `keep`. Verify with `assert-doc-schema.sh --expect v2 --before <snapshot>`, which now fails if a populated section is dropped |

These four are the cases a single dogfood run would never exercise. The last one guards the
only path where migration can silently lose content, so it is not optional.

- [ ] **Step 4: Verify idempotency**

Run `/bx:save` on `fx-v1` a second time.
Expected: no migration prompt, no second migration commit, checker still exits 0.

- [ ] **Step 5: Dogfood on `claude-config`**

Ensure the tree is clean, then run `/bx:save` and accept the migration.

```bash
cp CLAUDE.md /tmp/claude-config-before.md   # before running
# after:
bash bx/skills/save/tests/assert-doc-schema.sh . --expect v2 --before /tmp/claude-config-before.md
wc -c CLAUDE.md docs/STATUS.md docs/architecture.md
git log --oneline -3
git show --stat HEAD
```
Expected: checker exits 0; CLAUDE.md around **16k** chars (down from 28,700 — compression is
the separate follow-on pass, not this migration); STATUS.md around 10k; migration is its own
commit touching only `CLAUDE.md`, `docs/STATUS.md`, `docs/architecture.md`.

- [ ] **Step 6: Verify the hook against the real migrated repo**

```bash
bash bx/scripts/session-start-context.sh | head -20
```
Expected: a `**Project status** (from docs/STATUS.md):` block containing the Current Status
table and **nothing** from `## Completed` or `## In Progress`.

- [ ] **Step 7: Run `/bx:resume` and confirm it reads the new layout**

Expected: the summary reports `Doc schema: v2`, reads `docs/STATUS.md`, does **not** re-read
CLAUDE.md, and produces the same continuation picture as before the migration.

- [ ] **Step 8: Commit any remaining doc updates**

```bash
git status --porcelain
git add -A && git commit -m "docs: migrate claude-config to doc schema v2

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Deferred (not in this plan)

- **Key Decisions rationale compression** — offered by `mode-migrate.md` Step 7 as a
  separate consented pass; the mechanics of *how* to compress warrant their own spec.
  This is the remaining ~9k of the 28.7k.
- **`.claude/rules/` adoption** for path-scoped conventions (PowerShell, shell,
  skill-authoring). Surfaced during research; independent of this refactor.
- **Reverse migration.** `git revert <migration-sha>` is the downgrade path.
