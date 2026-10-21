# Expected outcome — phase 4 fixture (changelog lane Step 1 + footer; orchestrator Step 6 + Section 1)

Pages: page-1 = 2.1.999 … 2.1.949 (2.1.960 is absent — yanked), page-2 = 2.1.948 … 2.1.899, … page-10 = 2.1.548 … 2.1.499, page-11 = `[]`. Today 2026-10-20.

## Scenario A — anchor on page 2 (`last_changelog_version` = 2.1.923)
- Page 1: oldest 2.1.949 is newer than the anchor → page 2 → contains 2.1.923 (equal) → STOP. pages_fetched 2.
- In scope: 2.1.999 … 2.1.924 = 75 releases.
- Footer: `releases_scanned: 75`, `newest_version_seen: 2.1.999`, `pages_fetched: 2`, `oldest_version_seen: 2.1.899`, `gap_fill_scanned: 0`, `gap_after: null`, `gap_before: null`, `gap_closed: false`, `lane_status: ok`, scan_note = the zero-findings note only.
- Step 6: watermark → 2.1.999; `changelog_gap` null. Section 1 cell: `2.1.923 → 2.1.999 (75 releases) · 2 page(s)`. No headline qualifier.

## Scenario B — cap reached (`last_changelog_version` = 2.1.0)
- Pages 1–10 all have an oldest release newer than 2.1.0; cap reached (page 11 is NOT fetched). pages_fetched 10.
- All 500 releases processed. `lane_status: degraded`. `gap_after: 2.1.0`, `gap_before: 2.1.499`, `gap_closed: false`, `gap_fill_scanned: 0`, scan_note includes "anchor 2.1.0 not reached in 10 pages (500 releases); gap recorded" and the zero-findings note, joined by ` | `.
- Step 6: watermark → 2.1.999; `changelog_gap` ← {"after": "2.1.0", "before": "2.1.499", "recorded": "2026-10-20"}.
- Section 1 cell: `2.1.0 → 2.1.999 (500 releases) · 10 page(s) (gap: 2.1.0 → 2.1.499 unscanned)`; headline gains ` — changelog gap 2.1.0 → 2.1.499 unscanned`.

## Scenario C — closing a recorded gap (watermark 2.1.989; gap after=2.1.878 before=2.1.899)
- Anchor is the gap's `after` (2.1.878): pages 1, 2, 3 fetched; page 3 contains 2.1.878 → STOP. pages_fetched 3.
- Input: 10 releases newer than the watermark (2.1.999 … 2.1.990) + 20 gap-fill releases strictly between 2.1.878 and 2.1.899 (2.1.898 … 2.1.879); releases from 2.1.899 up to 2.1.989 are not re-processed.
- Footer: `releases_scanned: 30`, `gap_fill_scanned: 20`, `gap_closed: true`, `gap_after: null`, `gap_before: null`, `lane_status: ok`, `newest_version_seen: 2.1.999`, `oldest_version_seen: 2.1.849` (oldest fetched).
- Step 6: watermark → 2.1.999; `changelog_gap` → null. Section 1 cell: `2.1.989 → 2.1.999 (30 releases: 10 new + 20 gap fill) · 3 page(s) (gap 2.1.878 → 2.1.899 closed)`. No headline qualifier.

## Scenario D — yanked anchor (`last_changelog_version` = 2.1.960, absent from page 1)
- Page 1: walking newest → oldest, 2.1.961 is newer, then 2.1.959 is LESS than the anchor → STOP there (anchor treated as found). pages_fetched 1.
- In scope: 2.1.999 … 2.1.961 = 39 releases. `lane_status: ok`, no gap, `gap_fill_scanned: 0`, scan_note includes "watermark anchor 2.1.960 not present; sliced at 2.1.959" and the zero-findings note.
- Step 6: watermark → 2.1.999; `changelog_gap` null. Section 1 cell: `2.1.960 → 2.1.999 (39 releases) · 1 page(s) (anchor tag absent; sliced at 2.1.959)`.

Every scenario: zero findings (bodies are routine), so each run also emits the zero-findings scan_note; `discarded_findings: 0`.
