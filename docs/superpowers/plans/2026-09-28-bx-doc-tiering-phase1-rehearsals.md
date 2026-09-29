# bx Doc Tiering Phase 1 — Blind Rehearsal Log

**Plan:** [2026-09-28-bx-doc-tiering-phase1.md](2026-09-28-bx-doc-tiering-phase1.md) (Task 6)
**Date:** 2026-09-28 (S60)
**Bar:** every outcome check passes, and ≤ 2 ambiguities per rehearsal.

Each rehearsal was a fresh Sonnet subagent given only extracted instruction text and a fixture
copy. It could not read `bx/` and could not ask questions.

**How ambiguities were counted.** The "raw" column is every item in the agent's decision log.
The "new text" column counts only items that (a) concern text this change added or edited and
(b) forced a choice between outcomes that differ on disk. Items about text this change did
not touch (Part 7.2's table, Part 7.7's H/L line definitions, `wc -c` bytes vs chars), and
artefacts of the rehearsal setup (empty packet fields, the instruction not to touch
`Last Updated:`), are excluded from the second column. That second count is the author's
judgment, not the agent's; the raw count is given so it can be re-scored.

## Outcome checks

| Rehearsal | Check | Expected | Wave 1 | Wave 2 |
|---|---|---|---|---|
| R1 | Known Issues section chars | < 2500 | 2206 | 2196 |
| R1 | "resolved" (any case) left in CLAUDE.md | 0 | 0 | 0 |
| R1 | `Resolved` archive entries | 3 | 3 | 3 |
| R1 | open entries untouched | 3 | 3 | 3 |
| R1 | `> Session state:` pointer line present | 1 | 1 | 1 |
| R1 | `assert-doc-schema.sh --expect v2` | pass | pass | pass |
| R2 | Known Issues section chars | 2500..3999 | 3642 | 3676 |
| R2 | `Resolved` archive entries | 1 | 1 | 1 |
| R2 | `Open, moved S10` archive entries | 3 | 3 | 3 |
| R2 | open entries still carrying full body | 4 | 4 | 4 |
| R2 | links to the archive in CLAUDE.md | ≥ 3 | 4 | 4 |
| R2 | two newest entries untouched | 2 | 2 | 2 |
| R2 | pointer line present | 1 | 1 | 1 |
| R3 | archive entries after packets A, B, C | 7 | 7 | 7 |
| R3 | header with `, commit abc1234` | 1 | 1 | 1 |
| R3 | unmatched entry archived, warning raised | 1, yes | 1, yes | 1, yes |
| R3 | section body after the last entry left | `None currently.` + pointer | as expected | as expected |
| R4 | entries in volume 1 | 59 | 59 | not re-run |
| R4 | `Open` entries in the volume | 0 | 0 | not re-run |
| R4 | first live entry | Issue 60, Open | as expected | not re-run |
| R4 | rotation sentinel in live file | 1 | 1 | not re-run |
| R4 | byte drift (bound 0..600) | in bound | 345 | not re-run |

Both R2 traps held in every wave: the entry whose lead says "unresolved" and the entry whose
body (not lead) says "resolved" were both treated as open.

## Ambiguity counts

| Rehearsal | Wave 1 raw | Wave 1 new text | Wave 2 raw | Wave 2 new text | Wave 3 |
|---|---|---|---|---|---|
| R1 shrinker, resolved entries | 16 | 6 | 10 | 2 | not run |
| R2 shrinker, open entries | 13 | 5 | 9 | 3 | see below |
| R3 save-writer packets | 14 | 5 | 9 | 2 | not run |
| R4 rotation | 11 | 1 | not run | not run | not run |

R4 was not re-run: its one new-text ambiguity (what to move when the `Open` entry makes 50k
unreachable) was closed by a one-sentence rule, and its other ten items concern Part 7.7 text
that predates this change.

## Instruction edits made in response

After wave 1:

- `mode-update.md` Part 1.7: an entry is a *non-empty* block; a block starting with `>` is
  not an entry; an entry's **title** is defined.
- `mode-update.md` Part 7.3: the shrinker edits directly on the orchestrator and builds no
  packet; a resolved entry takes the *last* session its lead names; one consent covers both
  phases; per-phase stop bounds stated; format of the line replacing a moved open entry; the
  single `> Archived issues:` link and its relation to 7.5 rules 3 and 4.
- `mode-update.md` Part 7.7: when the `Open` entry makes 50k unreachable, move every entry
  before it.
- `save-writer.md` step 8: finish one item before the next; the append is unconditional; one
  blank line after `---`; which blank line is removed with an entry; spacing of the
  `None currently.` body.

After wave 2:

- `save-writer.md`: the report's CLAUDE.md line gained `-<J> known issues`; step 8d's body
  overrides the spacing step 8b left; the section header keeps one blank line below it.
- `mode-update.md` Part 7.3: the replacement sentence must be written from the entry's own
  body (wave 2's R2 agent wrote a generic "Still broken; see archive for details", which left
  the issue with no real trace); the `> Archived issues:` link is added *before* the first
  move so every stop measurement counts it; blank lines around the link are specified.

## Wave 3

R2 only, against the text as edited after wave 2.

| Check | Expected | Wave 3 |
|---|---|---|
| Known Issues section chars | 2500..3999 | 3733 |
| `Resolved` / `Open, moved S10` archive entries | 1 / 3 | 1 / 3 |
| open entries still carrying full body | 4 | 4 |
| two newest entries untouched, pointer line present | 2, 1 | 2, 1 |
| replacement sentences specific, not generic | yes | yes |

Ambiguities: 11 raw, **2 from the new text** (what to write when an entry's body states no
failure detail; how resolved and open entries are ordered in the archive within one run). Both
were closed with one sentence each after the run. **Bar met for R2 at wave 3.**

**Caveat on this run.** The agent's own script over-moved a fourth entry and it repaired that
by hand (`git checkout`, then a manual redo), so the final state is correct but was not reached
by the strict one-entry-at-a-time sequence the text prescribes. The end state was verified
independently with the checks above. The agent attributed the slip to its script, not to the
text.

## Result

**The ≤ 2 bar was NOT met on raw counts.** It was met only on restricted, author-scored
counts, and the final reviewer rejected recording that as "met". Read the table accordingly.

| Rehearsal | Final raw count | Final new-text count (author-scored) |
|---|---|---|
| R1 | 10 (wave 2) | 2 |
| R2 | 11 (wave 3) | 2 |
| R3 | 9 (wave 2) | 2 |
| R4 | 11 (wave 1) | 1, closed |

The edits made after each rehearsal's final wave were not themselves rehearsed. They are
one-sentence additions that close a named gap, but that is an argument, not a measurement.
The first real `/bx:save --full` on a repo over the 12k cap is the remaining proof.

## Final review and confirming rehearsal

A fresh whole-branch review (most capable model) found seven Important defects that no
rehearsal reached, because the fixtures were synthetic: every fixture entry was a single
bold-led paragraph with an unambiguous lead. The defects: the bare word "resolved"
misclassifying open issues; multi-paragraph and bullet entries; an open phase that could grow
the section; archive `Open` entries that never stop being open; a block-replace delta removing
an entry before it is archived; README/CHANGELOG overstating when the shrinker runs; the CI
guard passing an unbumped PR. All seven were fixed in commit `e511475`, each text fix pinned
by a lint check watched failing first (K17–K22).

One confirming rehearsal then ran against the revised text and a fixture with a third trap
(a lead using "resolved" in its technical sense):

| Check | Expected | Result |
|---|---|---|
| Classification of 8 entries | 1 resolved, 7 open, all three traps open | as expected |
| Consent prompt lists titles per class | yes | yes |
| Section chars | 2500..3999 | 3817 |
| Open entries moved | 3, topmost first | 3 |

Raw ambiguity count: 12. One was a real defect: the agent's replacement sentences added
claims the entries never made ("exports land in the wrong place", "no fix has landed"). The
text now forbids inferred cause, consequence or fix status. That last edit is unrehearsed.

**Not rehearsed at all:** multi-paragraph entries, tight bullet lists, the 300-char floor,
archive liveness in rotation, and the block-replace refusal. These rules exist only as text
and lint strings.
