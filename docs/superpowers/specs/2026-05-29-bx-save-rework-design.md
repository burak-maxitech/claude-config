# Design: Rework `/bx:docs` → `/bx:save` (fast-default + Sonnet offload)

**Date:** 2026-05-29
**Status:** Approved (design), pending implementation plan
**Author:** Session with Claude

---

## Problem

`/bx:docs` (the end-of-session save that pairs with `/bx:resume`) routinely takes **>10 minutes**, to the point the user has stopped using it. It is the cross-session handoff mechanism: it drains the live task tracker, updates `CLAUDE.md`, appends a session-history entry, and commits — so `/bx:resume` can rehydrate next session.

### Root causes (measured on this repo)

Doc tree sizes:

| File | Size | Role |
|------|------|------|
| CLAUDE.md | 25k chars | the thing being updated |
| README.md | 25k | rarely changes per session |
| docs/completed-work.md | 53k | append-only archive |
| docs/key-decisions.md | 70k | append-only archive |
| docs/session-history.md | 53k (39 sessions) | append-only archive |
| **total** | **~243k chars ≈ 60k tokens** | |

UPDATE mode runs an **8-part sequential pipeline inline on Opus**. Ranked by impact:

1. **Step 0 reads *all* docs every run — even `--fast`.** The upfront parallel batch loads ~60k tokens, including the two big append-only archives (`key-decisions.md` 70k + `completed-work.md` 53k) that a routine update never reads *from*. `--fast` doesn't skip this because Step 0 runs *before* path routing. ~30k tokens of pure overhead per run.
2. **Verification dumps full file contents back as output.** `verification-checklists.md` §2 mandates "provide complete content for each file created or significantly modified" — so it regenerates the entire 25k CLAUDE.md (and others) into the response. Minutes of useless output generation.
3. **Verbose prose + Part 5 rollup.** Session entries and decision rationales run 300–600 words (the S35 row is ~600). Part 5 re-analyzes all 39 session entries for rollup each Full Path run.

Not the bottleneck on this repo: consent prompts (rollup notes already present → silent), Parts 6/7 (17 decision rows < 20 cap; CLAUDE.md 25k < 35k → skip).

### Why not an out-of-box replacement

No built-in covers the structured session-handoff this pair does. Auto-memory (`MEMORY.md`) holds only *stable facts* (no task drain, no "what was I mid-doing"); native compaction is *intra-session*; `/init` is one-shot create. The fix is to slim the skill, not drop it.

---

## Decisions (locked with user)

1. **Approach:** surgical fixes **+** Sonnet subagent offload (deepest option).
2. **Default mode:** **fast by default**, heavy sweep becomes `--full` opt-in.
3. **Prose density:** **tight caps** on new entries (session entries ≤5 bullets; decision rationales ≤2–3 sentences; overflow → commit-hash refs). Existing entries untouched.
4. **Rename:** `/bx:docs` → **`/bx:save`** (pairs with `/bx:resume`: save at end, resume at start).

Scope is **UPDATE mode only**. CREATE and REFACTOR modes (rare, one-time, need full codebase analysis) are left functionally unchanged — only their `/bx:docs` self-references get renamed.

---

## Architecture

### The core split

The constraint that shapes everything: **a subagent cannot see the conversation** (only the main thread knows what happened this session) and **a subagent cannot prompt the user**. So:

**Orchestrator (Opus, main thread)** — only what needs conversation context or user input:
- Detect mode; run a **scoped Step 0**: read `CLAUDE.md` + `git log/diff/status` + `TaskList`. **Does not read** `key-decisions.md`, `completed-work.md`, or `session-history.md` on the fast path.
- Drain `TaskList` into a compact text digest.
- Compose a small **update packet** (~1–2k): capped session summary (≤5 bullets), the detailed session-history entry (capped, commit-hash refs for overflow), In Progress / Next Steps deltas, any new Key Decision row (≤2–3 sentences), the **exact replacement text** for CLAUDE.md's session block, and the drained task digest.
- Dispatch the `save-writer` subagent with that packet.
- On return: run the **commit checkpoint** (needs user confirmation) and emit a one-line change report. Emit **drift warnings** (cheap counts on already-loaded data) when a `--full` is due.

**`save-writer` subagent (Sonnet, off main thread)** — mechanical heavy lifting:
- Reads `session-history.md` (the big 53k read happens *here*).
- Applies all edits: CLAUDE.md (timestamp, session-block splice, status/In-Progress/Next-Steps deltas, append decision row if provided); append detailed entry to `session-history.md`; append completed items to `completed-work.md`; append new decision to `key-decisions.md` if provided.
- Returns a concise "files touched + before→after sizes" report. **Does not** dump file contents.

Net effect: the ~60k-token read load and all file writes move off the Opus main thread. Opus ingests only the 25k CLAUDE.md + composes a ~2k packet.

### The two paths

- **`/bx:save` (default = fast):** the flow above. Drain tasks → CLAUDE.md session block → session-history append → commit. Emits drift warnings (`README touched in N commits since last --full`, `M sessions ready for rollup`, `CLAUDE.md at Xk`).
- **`/bx:save --full` (opt-in, occasional):** adds README + `docs/*.md` sync and the rollups (current Parts 5/6/7). Rollups **stay on the orchestrator** because they can require a consent prompt (subagents can't prompt). README/`docs/*.md` sync may be delegated to `save-writer` (no consent needed) or kept on the orchestrator — implementation detail, decide in plan. `--full` is the rare heavy run, not the daily save.

### Surgical fixes folded in

- **Kill the full-file output dump** (`verification-checklists.md` §2) → replace with a change-report-only format (files touched + sizes + what changed).
- **Tight prose caps** baked into both the orchestrator's packet-composition rules and the `save-writer` template.
- **Scoped Step 0** as described (the single biggest read-overhead win).

### Safety

- CLAUDE.md edits are low-risk: the orchestrator hands the subagent the **exact replacement content** for the session block (clean splice, not freeform rewriting); the subagent receives the CLAUDE.md section contract (`claude-md-sections.md`); the **commit checkpoint is the review gate** (user sees the git diff before committing); `/bx:resume` re-validates CLAUDE.md structure next session.
- All existing flags preserved (`--skip-memory`, `--skip-tasks`, `--skip-commit`, `--skip-rollup`, `--skip-decisions-rollup`, `--skip-caps`). `--fast` becomes a **no-op alias** for the new default (back-compat for muscle memory); `--full` is new.

---

## Rename plan: `/bx:docs` → `/bx:save`

64 occurrences across 15 tracked files. New subagent named **`save-writer`** (matches the `<skill-area>-<function>` agent convention: arch-*, seo-*, test-*).

**Rename (active files):**
- `bx/skills/docs/` → `bx/skills/save/` via `git mv` (SKILL.md + all 6 reference files). Update `name:` frontmatter `docs` → `save`.
- `bx/skills/resume/` — SKILL.md (8), `references/summary-template.md` (1), `references/task-hydration.md` (2): companion-command references.
- `bx/skills/plan/` — SKILL.md (1), `references/plan-and-tasks.md` (1).
- `bx/skills/health/` — SKILL.md (1), `references/state-buckets.md` (10): routing references.
- `README.md` (2), `workflow.md` (23), `CLAUDE.md` (1 — rewritten anyway).
- New: `bx/agents/save-writer.md`.

**Leave untouched (historical records, per S32 records-of-past-state convention):**
- `docs/session-history.md`, `docs/completed-work.md`, `docs/key-decisions.md` — archives of past state.
- `docs/modernization-roadmap.md` (3 refs) — decide in plan; lean toward updating since it's a living plan-of-record, but low priority.

**No change needed:**
- `.claude/settings.local.json` — machine-local, gitignored, absent from repo (each machine rebuilds its own allowlist).
- `bx/hooks/` and `bx/scripts/` — no `docs` references.

Built-in references (`/init`, `/code-review`, etc.) are unrelated and untouched.

---

## Out of scope

- CREATE / REFACTOR mode logic (only their self-references are renamed).
- The rollup algorithms themselves (Parts 5/6/7) — moved, not rewritten.
- Any change to `/bx:resume`'s read flow beyond the companion-name update.
- The other open project tasks (`/bx:seo` fix, plugin smoke-test, dogfooding).

## Success criteria

- A routine `/bx:save` (UPDATE, no flags) completes in ~1–2 min vs ~10 min, producing the same CLAUDE.md session-block + session-history-append + task-drain result.
- The Opus main thread no longer reads `key-decisions.md` / `completed-work.md` / `session-history.md` on the fast path.
- No full-file content dump in the response.
- New session-history entries respect the density caps.
- `/bx:resume` still finds all required CLAUDE.md sections and rehydrates tasks after a `/bx:save`.
- `git grep 'bx:docs'` returns only historical-archive files.
