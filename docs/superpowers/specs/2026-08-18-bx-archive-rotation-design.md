# bx Archive Rotation — Design

**Date:** 2026-08-18 · **Status:** Approved (interview 2026-08-18) · **Target version:** bx 2.1.0 (MINOR — new mechanism + layout)

## Problem

Doc schema v2 capped the two live files (CLAUDE.md ~7k/12k, docs/STATUS.md ~10k/20k, enforced
by Parts 1.9/5/6/7) and v2.0.1 closed the three read paths that paid costs linear in project
age. What remains unbounded are the three history archives, which grow forever by design:

| File | Growth | Measured on this repo (57 sessions) |
|---|---|---|
| `docs/key-decisions.md` | +1 table row per decision | 96k chars |
| `docs/completed-work.md` | +several lines per session | 62k chars |
| `docs/session-history.md` | +1 one-liner per rolled-up session, +5 full entries | 39k chars |

After v2.0.1 **no automatic path reads these files in full**, so their growth is disk-only —
not a performance problem. Rotation exists for the *deliberate* reads: `/bx:resume deep`, a
human opening the file, an agent's Read tool paging a 2000-line file. Past ~100k chars those
reads get slow and clumsy; rotation keeps the live file a sane size while every byte of
history stays on disk, verbatim.

`docs/next-steps-backlog.md` is explicitly **excluded**: it grows only when a Part 7.3
shrinker fires and shrinks when items ship. If it ever crosses 100k, that is a symptom to
surface to the user, not a file to rotate — rotating it would bury still-live backlog detail.

## Decisions (all approved in the design interview)

1. **Trigger: size, ~100k chars per file.** Checked by extending Part 1.9's existing
   `wc -c` probe with the three archive paths (the fast path then also gains an advisory
   drift line, e.g. "docs/key-decisions.md at 96k — rotation fires at 100k on `--full`").
   Size is what hurts reads; counts drift per project.
2. **Layout: numbered volumes under `docs/archive/`.**
   `docs/archive/session-history-1.md`, `-2.md`, … (same pattern for `key-decisions` and
   `completed-work`). The live file keeps its current path. `docs/` listings — which
   `/bx:resume` reads every session — stop growing.
3. **Consent: first-run + sentinel, matching Parts 5/6.** The first rotation on a project
   asks once (naming the file, its size, and the new `docs/archive/` directory). The
   sentinel is the rotation note in the live file's header; subsequent rotations run
   silently. `--silent` treats first-run as declined **without** writing the sentinel, so
   the next interactive run asks as usual.
4. **Scope: the three history archives only** (session-history, key-decisions,
   completed-work). Backlog excluded per above.
5. **No volume-count cap.** Volumes are inert (see Read-path guarantee): 5 and 50 cost the
   same at runtime, and a cap could only be enforced by deleting history — breaking the
   schema's "nothing is deleted, content moves" promise to reclaim nothing. **Manual
   pruning is the documented escape hatch:** `git rm` the oldest volume; its content still
   survives in git history, so even manual pruning is recoverable. Deletion stays a human
   act, never the skill's.

## Mechanics — new Part 7.7 in `mode-update.md`

Runs on `--full` only, **after** Part 7's shrinkers (they are what append to archives), per
over-threshold file independently:

1. **Consent** per decision 3. Declined → skip this file, re-check next `--full` run.
2. **Create `docs/archive/`** if missing.
3. **Next volume number** = max existing volume for this archive + 1, found by Glob on
   `docs/archive/<name>-*.md` — **filenames only; volume contents are never read.**
4. **Move the oldest entries, byte-verbatim** — never compress or reword (compression is
   Part 5's job and has already run) — until the live file is **≤50k** (half the threshold,
   hysteresis so rotation does not re-fire every run). The protected tail never moves:
   - session-history: the 5 most recent sessions (matching Part 5's window)
   - key-decisions: the newest 20 rows (matching the Part 6 target)
   - completed-work: the current session's items
   The moved slice is contiguous from the top of the entry region (oldest-first ordering in
   all three files), so the cut point is a whole entry/row boundary, never mid-entry.
5. **Volume header**, written above the moved content:

   ```markdown
   # <Title> — Archive Volume <K>

   > Rotated from [<live-name>.md](../<live-name>.md) by `/bx:save` on <date>.
   > Previous volume: [<name>-<K-1>.md](<name>-<K-1>.md) — omit line when K = 1.
   > Newer content: [<live-name>.md](../<live-name>.md).
   ```

   For key-decisions volumes, repeat the `| Decision | Rationale |` table header before the
   moved rows so each volume renders standalone.
6. **Live-file rotation note** (the sentinel), inserted after the existing header note or
   updated in place to point at the newest volume:

   ```markdown
   > **Note:** Entries are rotated to [docs/archive/<name>-<K>.md](archive/<name>-<K>.md)
   > when this file exceeds 100k chars. Older volumes chain from there.
   ```
7. **Report:** `"<file>: rotated <N>k chars → docs/archive/<name>-<K>.md; live file now
   <M>k (<V> volumes total)."`
8. **Invariant — byte conservation:** `wc -c` the live file before, and live + new volume
   after. Rotation only adds header bytes, so the after-sum must be **≥ the before count and
   ≤ before + ~400 bytes** (the volume header + sentinel). Below the floor means content was
   lost, above the ceiling means content was rewritten — either way, report loudly and do
   not rotate further files this run.

## Read-path guarantee (why volumes are performance-free)

| Path | Touches volumes? |
|---|---|
| Session start (CLAUDE.md auto-load, SessionStart hook) | No |
| `/bx:resume` default | No |
| `/bx:resume deep` | No — live archives only; one added sentence documents volumes as grep-on-demand |
| `/bx:save` fast path (save-writer tail appends) | No |
| `/bx:save --full` Part 3.0 sweep | No — **its exclusion list extends to `docs/archive/**`** (required; without this the sweep would read every volume and undo v2.0.1) |
| Rotation itself | Filenames only (Glob for numbering) |

## File changes

| File | Change |
|---|---|
| `bx/skills/save/references/mode-update.md` | New Part 7.7; Part 1.9 probe + drift line gains the three archive paths; Part 3.0 exclusion extends to `docs/archive/**` |
| `bx/skills/resume/SKILL.md` | One sentence in Deep Dive Mode: volumes under `docs/archive/` are not read by default — grep on demand |
| `bx/skills/save/references/doc-structure-rules.md` | Target-state table gains a `docs/archive/` row |
| `bx/.claude-plugin/plugin.json` | 2.0.1 → 2.1.0 |
| `CHANGELOG.md` | 2.1.0 entry |

## Verification

- Existing 13-invocation gate stays green (rotation touches no schema-governed file).
- `check-doc-rule-consistency.sh` stays green (no canonical string is restated).
- **Acceptance: one blind-agent rehearsal** on a synthetic >100k archive in a scratch repo —
  the agent gets only the Part 7.7 text and a packet, and must produce: correct volume
  number, byte conservation within slack, protected tail intact in the live file, sentinel
  written, chain links resolving. (Rehearsals found what seven reviews could not throughout
  the v2 branch; this is the one instrument that tests followability.)

## Out of scope (YAGNI)

Un-rotation and volume merging; checker assertions on archives; backlog rotation; automatic
pruning (manual `git rm` is the escape hatch, per decision 5); any compression during
rotation (Part 5 owns compression, and only for session-history).
