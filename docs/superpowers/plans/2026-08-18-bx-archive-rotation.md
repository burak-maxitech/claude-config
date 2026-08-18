# bx Archive Rotation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Size-triggered rotation of the three history archives into numbered volumes under `docs/archive/`, byte-verbatim, so live archives stay under ~100k chars while every byte of history stays on disk and no automatic path ever reads a volume.

**Architecture:** One new sub-part (7.7) in `mode-update.md` owns the whole mechanism; the drift probe gains three `wc -c` paths; Part 3.0's exclusion list gains `docs/archive/**`; resume and doc-structure-rules each gain one registration line. No new scripts, no checker changes.

**Tech Stack:** Markdown skill instructions only. Verification via the existing `check-doc-rule-consistency.sh`, the 13-invocation fixture gate, and one blind-agent rehearsal.

**Spec:** `docs/superpowers/specs/2026-08-18-bx-archive-rotation-design.md`

## Global Constraints

- **Threshold values, verbatim everywhere they appear:** rotation fires at **over 100k chars**; the live file is reduced to **at or under 50k chars**; byte conservation requires **B ≤ A ≤ B + 600** (B = live-file bytes before, A = live-after + volume-after).
- **Rotation never compresses, rewords, or reorders content** — byte-verbatim moves at whole-entry boundaries only. Compression is Part 5's job and has already run.
- **Volumes are read by no automatic path.** Part 3.0's exclusion must cover `docs/archive/**`; volume numbering uses Glob on filenames only.
- **Never shell out to `mkdir`** — it is not in `save/SKILL.md`'s `allowed-tools`. The Write tool creates `docs/archive/` implicitly when writing the first volume; Part 7.7's text says so explicitly to prevent improvisation (S42/S45/Ruling-45 lesson class).
- **Canonical strings untouched:** the schema marker, pointer line, and populated-rule regex appear nowhere in this plan's edits; `bash bx/skills/save/tests/check-doc-rule-consistency.sh` must stay green after every task.
- **One version bump only, in Task 4:** `bx/.claude-plugin/plugin.json` `2.0.1` → `2.1.0` (MINOR — new mechanism + layout).
- **Line numbers cited are as-of authoring — anchor every edit to the quoted content, re-reading the region first.**
- **Repo commit convention:** end every commit message with the trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: Part 7.7 + probe + exclusions in `mode-update.md`

**Files:**
- Modify: `bx/skills/save/references/mode-update.md` (five regions: the fast-path drift probe ~:36, the drift-warning block ~:99-103, Part 3.0's exclusion item ~:447-455, Part 7.1's early exit ~:632, and a new Part 7.7 inserted between the end of 7.6 and `## Part 8`)

**Interfaces:**
- Consumes: nothing new.
- Produces: the Part 7.7 section text — Task 3's rehearsal hands exactly this text (and nothing else from the file) to a blind agent, so it must be self-contained.

- [ ] **Step 1: Extend the fast-path drift probe**

Find the Save-Path probe bullet beginning `**CLAUDE.md size + docs/STATUS.md size + Key Decisions row count + session count**` (~line 36). Change its `wc -c CLAUDE.md docs/STATUS.md` command to:

```
wc -c CLAUDE.md docs/STATUS.md docs/session-history.md docs/key-decisions.md docs/completed-work.md
```

and extend its parenthetical so it reads: `(omit docs/STATUS.md — and any archive — from the command when the file does not exist)`. Leave the Grep-count sentences unchanged.

- [ ] **Step 2: Add the archive line to the drift warning**

Find the drift-warning blockquote (~lines 99-103) whose last line is:

```
>  - docs/STATUS.md at [Y]k chars (target ~10k, soft cap 20k) — Part 7 size-pressure rollup will fire on `--full`"
```

Append one more line inside the quote (shown only for each archive at 90k chars or more):

```
>  - docs/[archive].md at [Z]k chars (rotation threshold 100k) — Part 7.7 archive rotation will fire on `--full`"
```

Move the closing `"` to the new final line and add, after the blockquote, the sentence: `Show the archive line only for an archive at ≥90k chars (approaching or over the 100k rotation threshold).`

- [ ] **Step 3: Extend Part 3.0's exclusion item**

Find Part 3.0's item 2, which begins `**Exclude the auto-managed archives from the read set:**` and ends `(At 57 sessions this repo's archives already total ~196k chars.)`. Append to it:

```
   Also exclude **everything under `docs/archive/`** — rotated archive volumes (Part 7.7)
   are read by no automatic path, ever; reading them here would reintroduce the exact
   linear cost this exclusion exists to remove.
```

- [ ] **Step 4: Fix Part 7.1's early exit so it cannot skip rotation**

Find in Part 7.1 (~line 632):

```
- If `claude_md_size <= 12000` **and** `status_md_size <= 20000` → skip the rest of Part 7 silently. The count-based rollups did the job.
```

Replace with:

```
- If `claude_md_size <= 12000` **and** `status_md_size <= 20000` → skip 7.2-7.6 silently (the count-based rollups did the job) and go directly to **7.7 (archive rotation)**, which runs regardless: its trigger is archive size, not live-file size.
```

- [ ] **Step 5: Insert Part 7.7**

Insert the following section between the end of the 7.6 report blockquote (`> "CLAUDE.md: [old-size]k → [new-size]k chars. …"`) and the `## Part 8` header, verbatim:

````markdown
### 7.7 Archive rotation

The three history archives grow forever by design — `docs/session-history.md` (one line per
rolled-up session plus 5 full entries), `docs/key-decisions.md` (one row per decision),
`docs/completed-work.md` (several lines per session). No automatic path reads them in full
(Part 3.0 excludes them; save-writer appends via tail reads), so growth is disk-only — but
deliberate reads (deep resume, a human opening the file, a 2000-line Read page) get clumsy
past ~100k chars. Rotation moves the oldest entries, byte-verbatim, into numbered volumes
under `docs/archive/`. `docs/next-steps-backlog.md` is NOT rotated: it grows only when a
7.3 shrinker fires and shrinks when items ship — if it exceeds 100k, report that as a
symptom and take no action.

**If `--skip-rotation` is in `$ARGUMENTS`, skip this step entirely.** (Note `--skip-size-pressure`
skips all of Part 7, this step included; 7.1's early exit does NOT skip this step.)

Measure the three archives (`wc -c`, omitting any that do not exist). For each file over
**100k chars**, independently:

1. **Consent (first rotation on this project only).** The sentinel is the rotation note in
   the live file's header — search for the literal substring `Entries are rotated to`. If
   present, proceed silently. If absent: **if `--silent` is in `$ARGUMENTS`, treat as
   declined without asking** (skip this file, write no sentinel — the next interactive
   `--full` run asks as usual). Otherwise ask via `AskUserQuestion` (numbered fallback):

   > "`docs/<name>.md` is [N]k chars. Rotating moves its oldest entries, byte-for-byte,
   >  into `docs/archive/<name>-1.md` (a new `docs/archive/` directory), leaving the
   >  newest content where it is. Nothing is deleted or reworded, and volumes are read by
   >  nothing automatic — they are grep-on-demand history. Rotate now? (y/n)"

   Declined → skip this file, write no sentinel, re-offer next `--full` run.

2. **Ensure `docs/archive/` exists — implicitly.** The Write tool creates the directory
   when writing the volume file in step 5. Do NOT shell out to `mkdir`; it is not in this
   skill's `allowed-tools`.

3. **Volume number:** `Glob docs/archive/<name>-*.md`; K = highest existing number + 1, or
   1 if none. **Filenames only — never read a volume's contents.**

4. **Move the oldest entries, byte-verbatim,** from the top of the file's entry region
   (all three archives order oldest-first) into the new volume, cutting only at whole-entry
   boundaries — a `### Session` header line, a complete `|` table row, a whole checklist
   line — until the live file is at or under **50k chars** (half the threshold, so rotation
   does not re-fire every run). The protected tail never moves: the 5 most recent sessions
   (session-history, matching Part 5's window), the newest 20 rows (key-decisions, matching
   Part 6's target), this session's just-appended items (completed-work). Never compress,
   reword, or reorder anything — Part 5 owns compression and has already run.

5. **Write the volume** with this header above the moved content — omit the
   previous-volume line when K = 1; for key-decisions, repeat the
   `| Decision | Rationale |` and `|----------|-----------|` table-header lines before the
   moved rows so the volume renders standalone:

   ```markdown
   # <Title> — Archive Volume <K>

   > Rotated from [<name>.md](../<name>.md) by `/bx:save` on <date>.
   > Previous volume: [<name>-<K-1>.md](<name>-<K-1>.md)
   > Newer content: [<name>.md](../<name>.md)

   ---
   ```

6. **Write or update the live file's rotation note** (the consent sentinel), inserted
   after the file's existing header note(s) or updated in place to point at the newest
   volume:

   ```markdown
   > **Note:** Entries are rotated to [docs/archive/<name>-<K>.md](archive/<name>-<K>.md)
   > when this file exceeds 100k chars. Older volumes chain from there.
   ```

7. **Verify byte conservation before touching the next file.** With B = the live file's
   `wc -c` before rotation and A = live-file-after + volume-after: require
   **B ≤ A ≤ B + 600** (rotation only adds bytes — volume header ~250, sentinel ~160,
   key-decisions table-header repeat ~45, plus margin). A below B means content was lost;
   A above the ceiling means content was rewritten. On violation: report loudly, leave both
   files exactly as they stand for inspection, and do NOT rotate any further files this run.

8. **Report:** `"docs/<name>.md: rotated [N]k chars → docs/archive/<name>-<K>.md; live
   file now [M]k ([V] volumes total)."`

Volumes are permanent — there is no count cap. Rotated volumes cost nothing at runtime
(nothing automatic reads them), and deleting history to reclaim ~100KB would break the
schema's "nothing is deleted — content moves" promise. If a user wants to prune, the
escape hatch is manual: `git rm docs/archive/<name>-1.md` — the content still survives in
git history.
````

- [ ] **Step 6: Verify**

```bash
grep -c 'skip-rotation' bx/skills/save/references/mode-update.md
grep -c 'docs/archive' bx/skills/save/references/mode-update.md
grep -n 'skip 7.2-7.6 silently' bx/skills/save/references/mode-update.md
bash bx/skills/save/tests/check-doc-rule-consistency.sh
```

Expected: `skip-rotation` ≥ 1; `docs/archive` ≥ 5 (Part 3.0 exclusion + 7.7's uses); the 7.1 early-exit line found once; lint exits 0 with all PASS.

- [ ] **Step 7: Commit**

```bash
git add bx/skills/save/references/mode-update.md
git commit -m "feat(save): Part 7.7 archive rotation — 100k-triggered, byte-verbatim volumes

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Registration — flags, resume, structure rules

**Files:**
- Modify: `bx/skills/save/SKILL.md:7` (argument-hint)
- Modify: `bx/skills/resume/SKILL.md` (Deep Dive Mode section)
- Modify: `bx/skills/save/references/doc-structure-rules.md` (Target State table)

**Interfaces:**
- Consumes: Part 7.7's existence (Task 1) — the texts below name it.
- Produces: nothing downstream.

- [ ] **Step 1: Add `--skip-rotation` to the argument-hint**

In `bx/skills/save/SKILL.md`'s frontmatter `argument-hint`, append ` [--skip-rotation]` inside the quoted string, after `[--skip-migrate]`.

- [ ] **Step 2: Register volumes in resume's Deep Dive Mode**

In `bx/skills/resume/SKILL.md`, find the Deep Dive Mode section (the block describing what `deep` reads — `docs/session-history.md`, `docs/completed-work.md`, `docs/key-decisions.md`). Append this sentence to that list's intro or as a closing line of the list:

```markdown
Rotated archive volumes under `docs/archive/` are NOT read even in deep mode — they are
grep-on-demand history; open one only when chasing a specific old session or decision.
```

- [ ] **Step 3: Register `docs/archive/` in the structure rules**

In `bx/skills/save/references/doc-structure-rules.md`'s Target State table (the one that gained `docs/STATUS.md` and `docs/architecture.md` rows in the v2 migration), add a row:

```markdown
| **docs/archive/** | Rotated archive volumes (`<name>-<K>.md`) written by `/bx:save` Part 7.7 when a history archive exceeds 100k chars. Read by nothing automatic — grep on demand. | Reference |
```

Match the table's actual column count when inserting — re-read the table header first; if it has two columns (File / Purpose), merge the audience note into the purpose cell.

- [ ] **Step 4: Verify**

```bash
grep -c 'skip-rotation' bx/skills/save/SKILL.md
grep -c 'docs/archive' bx/skills/resume/SKILL.md bx/skills/save/references/doc-structure-rules.md
bash bx/skills/save/tests/check-doc-rule-consistency.sh
```

Expected: 1; 1 in each file; lint exits 0.

- [ ] **Step 5: Commit**

```bash
git add bx/skills/save/SKILL.md bx/skills/resume/SKILL.md bx/skills/save/references/doc-structure-rules.md
git commit -m "feat(save): register archive rotation — flag, resume note, structure rule

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Acceptance rehearsal (blind agent) + regression gate

**Files:**
- No source changes. Produces a scratch fixture and a rehearsal verdict.

**Interfaces:**
- Consumes: Part 7.7's final text (Task 1).
- Produces: the acceptance evidence; a rehearsal failure is a Task 1 finding and re-enters Task 1's fix loop.

- [ ] **Step 1: Build a synthetic >100k session-history repo in the scratchpad**

In a scratch directory (never inside this repo), create `fx-rotate/` as a git repo containing `docs/session-history.md` with: the standard header (`# Session History Archive`, the `> Auto-managed…` line, the Part 5 rollup note, `---`), then 60 one-line compressed sessions (S1-S60) followed by 5 full-prose sessions (S61-S65, ~10 bullets each), padded so the file totals 110,000-120,000 bytes (pad by making the one-liners realistically long, ~1.5k bytes each — never by non-entry filler). Commit it. Record `wc -c` as B and `md5sum` of the 5 full entries' region.

- [ ] **Step 2: Dispatch the blind rehearsal agent**

Dispatch ONE fresh general-purpose subagent whose prompt contains: (a) the full text of Part 7.7 ONLY (paste the section — not the rest of mode-update.md, not this plan, not the spec); (b) the packet: `project_root` = the fixture path, `today` = the real date, consent = "already granted by the user — proceed as if the Step 1 prompt returned yes"; (c) tool constraints: Read/Write/Edit/Grep/Glob plus `wc` and `ls` only — no other shell, no git; (d) the instruction to return inline (no report file): its execution log, every `wc -c` it ran, and a DECISION LOG quoting each point where the text left it a genuine choice. Do not tell it the expected outcome.

- [ ] **Step 3: Verify the rehearsal result mechanically**

```bash
# in the fixture repo:
ls docs/archive/                                  # expect exactly session-history-1.md
wc -c docs/session-history.md docs/archive/session-history-1.md
# expect: live ≤ 50000; sum within [B, B+600]
grep -c 'Entries are rotated to' docs/session-history.md    # expect 1 (sentinel)
grep -c '^### Session' docs/session-history.md              # expect exactly 5 full + N one-liners ≥ the protected tail; S61-S65 present
grep -c 'Archive Volume 1' docs/archive/session-history-1.md # expect 1
grep -c 'Previous volume' docs/archive/session-history-1.md  # expect 0 (K=1 omits the line)
```

Also confirm the 5 full entries' region in the live file is byte-identical to the Step 1 md5, and that the volume's first moved entry is S1 (oldest-first cut). Any failure is a Task 1 finding: fix Part 7.7's text, re-dispatch a fresh blind agent on a fresh fixture copy, and do not weaken a check to pass.

- [ ] **Step 4: Regression gate**

```bash
DEST="$(mktemp -d)"
bash bx/skills/save/tests/make-fixtures.sh "$DEST"
for spec in fx-v0:v0 fx-v1:v1 fx-v1-envvars:v1 fx-v2:v2 fx-partial:partial fx-dirty:v1 fx-v1-sparse:v1 fx-v1-ineligible:v1 fx-partial-conflict:partial fx-arch-preexisting:v1; do
  bash bx/skills/save/tests/assert-doc-schema.sh "$DEST/${spec%%:*}" --expect "${spec##*:}" || echo "MISMATCH ${spec%%:*}"
done
bash bx/skills/save/tests/test-hook-layout.sh
bash bx/skills/save/tests/check-doc-rule-consistency.sh
bash bx/skills/save/tests/assert-doc-schema.sh "$DEST/fx-v2" --expect v2 --before "$DEST/fx-v1/CLAUDE.md"
```

Expected: no MISMATCH lines, all suites pass — rotation touched no schema-governed file, so anything red here is a Task 1 regression.

- [ ] **Step 5: Record the verdict**

No commit (no source changed). Record in the executor's ledger: rehearsal PASSED/FAILED, B and A byte counts, and the agent's decision-log ambiguity count (the regression metric — the v2 branch drove doc-migrator's from 5 to 2; Part 7.7 should start ≤ 2).

---

### Task 4: Version bump + CHANGELOG

**Files:**
- Modify: `bx/.claude-plugin/plugin.json:5`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: everything above.
- Produces: the published 2.1.0.

- [ ] **Step 1: Bump the version**

In `bx/.claude-plugin/plugin.json`, change `"version": "2.0.1"` to `"version": "2.1.0"`. MINOR: a new mechanism and a new on-disk layout, no breaking change.

- [ ] **Step 2: Add the CHANGELOG entry**

At the top of `CHANGELOG.md`, above `## 2.0.1 — <date>`:

```markdown
## 2.1.0 — <today's date>

### Added

- **Archive rotation** (`/bx:save` Part 7.7, `--full` only): when a history archive
  (`session-history.md`, `key-decisions.md`, `completed-work.md`) exceeds 100k chars, its
  oldest entries move byte-verbatim into numbered volumes under `docs/archive/`, leaving
  the live file at ≤50k with the newest content intact. First rotation asks for consent;
  a header note is the sentinel. Volumes are read by nothing automatic — not deep resume,
  not the `--full` doc sweep — they are grep-on-demand history. No volume-count cap:
  pruning is a manual `git rm` (content survives in git history). `--skip-rotation` skips
  the Part.
```

- [ ] **Step 3: Verify**

```bash
grep -n '"version"' bx/.claude-plugin/plugin.json
head -3 CHANGELOG.md
```

Expected: exactly one `"version": "2.1.0"` line; CHANGELOG's first heading is `## 2.1.0`.

- [ ] **Step 4: Commit**

```bash
git add bx/.claude-plugin/plugin.json CHANGELOG.md
git commit -m "chore: v2.1.0 — archive rotation

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```
