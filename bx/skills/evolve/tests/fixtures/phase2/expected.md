# Expected outcome — phase 2 fixture (Step 3 only)

Inputs: `state.json` (5 stored entries, one legacy 9-key), `lane-output.json` (7 changelog + 2 docs findings, community skipped), `inputs.json`.

## Step 3.2 same-source dedup
- The two changelog findings on https://github.com/anthropics/claude-code/releases/tag/v2.1.304 share a URL and `scan-changelog.md` -> ONE finding, capability `bx:evolve/changelog-window` (same class breakage; higher severity x certainty: 3x0.9 > 2x0.5), `affected_files` = both files, citation stays one URL (identical), kept `upstream_delta` gains `(also addresses bx:pain/changelog-window-gap)`. Footer: 1 same-source collapse.
- https://github.com/anthropics/claude-code/releases/tag/v2.1.303 vs docs `code-review`: different URLs -> NOT merged (3.5's capability rule does not merge them either: different capabilities).
- After dedup: 8 findings to hash.

## Step 3.4 decision-log filter
| live finding | match | branch | result |
|---|---|---|---|
| v2.1.300 plugin-validate | exact id, applied, hash == stored | applied unchanged | suppressed |
| docs hooks session-start-hook | exact id, applied, hash != stored | applied changed | surfaced `[re-raised — source changed since application]`; stored -> open, new hash 64bcac6e…, date 2026-10-20, note "was applied: hooks.json already lists startup|resume|clear", title <- "SessionStart gained a compact matcher", edit fields refreshed, class unchanged |
| v2.1.301 health/routing | exact id, rejected, hash == stored | rejected unchanged | suppressed |
| v2.1.302 plan/task-tools | exact id, applied, stored hash is the sentinel | applied + sentinel | suppressed; stored hash <- live hash bf765ae9…, source_excerpt <- live excerpt |
| v2.1.233 task-tracker-tools-v2 | no exact id; same source_url as the legacy entry (affected_files absent, same class); passes 3.3 by that match | matched by source_url -> applied, hash == stored | suppressed; legacy entry upgraded to 13 keys from the live finding (decision/date/note untouched); NO new entry appended; footer "1 matched to a stored entry by source_url" |
| v2.1.303 review/report-findings | none | new | surfaced, written open |
| v2.1.304 evolve/changelog-window (merged) | none | new | surfaced, written open with union affected_files |
| docs code-review review/output-format | none | new | surfaced, written open |

## Expected footer block
```
Decision-log filters applied this run:
  1 rejected findings suppressed (source_content_hash unchanged — source not rewritten since rejection)
  0 rejected finding re-raised (source_content_hash changed → transitioned to open)
  3 applied findings suppressed (source_content_hash unchanged — includes 1 sentinel entry whose live hash is now stored)
  1 applied finding re-raised (source_content_hash changed → transitioned to open)
  1 matched to a stored entry by source_url (capability string differed from the stored one)
  1 same-source collapse at Step 3.2 (two lane findings merged before hashing)
```
Headline: Breakage 1 (v2.1.304 merged) · Best-practice 1 (re-raised hooks) · Opportunities 2 (v2.1.303, docs code-review) · Advisory 0.
Open entries written this run: 4 (3 new + 1 re-raised). Decisions array after Checkpoint 1: 8 entries (5 + 3), no duplicates; the former legacy entry now has 13 keys (same hash, decision, date, note); `check-state.py` passes on the written state with no legacy warning.
