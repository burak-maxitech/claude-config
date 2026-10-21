#!/usr/bin/env python3
"""Regenerates the phase-4 rehearsal fixture: changelog-lane pagination, anchor comparison,
gap recording and gap closing. Run from the repo root: python -I <this file>. Writes
page-1..10.json (what `gh api ...releases?per_page=50&page=N` returns; page-11.json is the
empty array), four scenario input files, and expected.md beside this script. Release
bodies are deliberately boring: the rehearsal exercises Step 1 and the footer, not Step 5.
One version (2.1.960) is deliberately absent from page 1 to model a yanked tag."""
import io, json
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
PER_PAGE = 50
PAGES = 10
NEWEST_PATCH = 999          # 2.1.999 is the newest release; versions count down to the 2.1.49x range
YANKED = "2.1.960"
TODAY = date(2026, 10, 20)


def all_versions():
    v = NEWEST_PATCH
    out = []
    while len(out) < PER_PAGE * PAGES:
        s = f"2.1.{v}"
        if s != YANKED:
            out.append(s)
        v -= 1
    return out


VERSIONS = all_versions()               # 500 versions, newest first, 2.1.960 skipped


def release(i, v):
    return {"tag_name": "v" + v,
            "published_at": (TODAY - timedelta(days=i)).isoformat() + "T12:00:00Z",
            "body": f"## {v}\n\n- Routine fix #{i}. No bx-relevant change."}


pages = [[release(i, v) for i, v in list(enumerate(VERSIONS))[p * PER_PAGE:(p + 1) * PER_PAGE]] for p in range(PAGES)]
for n, page in enumerate(pages, 1):
    io.open(HERE / f"page-{n}.json", "w", encoding="utf-8", newline="").write(json.dumps(page, indent=1) + "\n")
io.open(HERE / f"page-{PAGES + 1}.json", "w", encoding="utf-8", newline="").write("[]\n")

p2 = pages[1]; p3 = pages[2]; p10 = pages[9]
oldest = p10[-1]["tag_name"][1:]
anchor_A = p2[25]["tag_name"][1:]        # 26th release on page 2
gap_after_C = p3[20]["tag_name"][1:]     # on page 3
gap_before_C = p2[-1]["tag_name"][1:]    # last release of page 2
wm_C = pages[0][10]["tag_name"][1:]      # 11th release on page 1

scenarios = {
    "A": {"last_changelog_version": anchor_A, "changelog_gap": None, "note": "anchor sits on page 2"},
    "B": {"last_changelog_version": "2.1.0", "changelog_gap": None, "note": "anchor is older than every release in the ten-page cap"},
    "C": {"last_changelog_version": wm_C, "changelog_gap": {"after": gap_after_C, "before": gap_before_C, "recorded": "2026-10-01"},
          "note": "a gap recorded on an earlier run; its `after` version sits on page 3"},
    "D": {"last_changelog_version": YANKED, "changelog_gap": None, "note": "the anchor tag was yanked; it falls between two page-1 releases"},
}
for k, v in scenarios.items():
    io.open(HERE / f"inputs-{k}.json", "w", encoding="utf-8", newline="").write(json.dumps(
        {"scenario": k, **v, "capability_inventory": ["bx:evolve/changelog-window"], "pain_point_list": [],
         "how_to_fetch": "`gh api \"repos/anthropics/claude-code/releases?per_page=50&page=N\"` returns the contents of page-N.json in this directory; page-11.json is the empty array (end of history)."},
        indent=2) + "\n")


def idx(v):
    return VERSIONS.index(v)


n_A = idx(anchor_A)                         # releases newer than the anchor
n_D = sum(1 for v in VERSIONS if tuple(map(int, v.split("."))) > (2, 1, 960))
first_older_D = next(v for v in VERSIONS if tuple(map(int, v.split("."))) < (2, 1, 960))
delta_C = idx(wm_C)
fill_C = idx(gap_after_C) - idx(gap_before_C) - 1

expected = f"""# Expected outcome — phase 4 fixture (changelog lane Step 1 + footer; orchestrator Step 6 + Section 1)

Pages: page-1 = 2.1.999 … {pages[0][-1]['tag_name'][1:]} (2.1.960 is absent — yanked), page-2 = {p2[0]['tag_name'][1:]} … {gap_before_C}, … page-10 = {p10[0]['tag_name'][1:]} … {oldest}, page-11 = `[]`. Today 2026-10-20.

## Scenario A — anchor on page 2 (`last_changelog_version` = {anchor_A})
- Page 1: oldest {pages[0][-1]['tag_name'][1:]} is newer than the anchor → page 2 → contains {anchor_A} (equal) → STOP. pages_fetched 2.
- In scope: {VERSIONS[0]} … {VERSIONS[n_A - 1]} = {n_A} releases.
- Footer: `releases_scanned: {n_A}`, `newest_version_seen: 2.1.999`, `pages_fetched: 2`, `oldest_version_seen: {gap_before_C}`, `gap_fill_scanned: 0`, `gap_after: null`, `gap_before: null`, `gap_closed: false`, `lane_status: ok`, scan_note = the zero-findings note only.
- Step 6: watermark → 2.1.999; `changelog_gap` null. Section 1 cell: `{anchor_A} → 2.1.999 ({n_A} releases) · 2 page(s)`. No headline qualifier.

## Scenario B — cap reached (`last_changelog_version` = 2.1.0)
- Pages 1–10 all have an oldest release newer than 2.1.0; cap reached (page 11 is NOT fetched). pages_fetched 10.
- All 500 releases processed. `lane_status: degraded`. `gap_after: 2.1.0`, `gap_before: {oldest}`, `gap_closed: false`, `gap_fill_scanned: 0`, scan_note includes "anchor 2.1.0 not reached in 10 pages (500 releases); gap recorded" and the zero-findings note, joined by ` | `.
- Step 6: watermark → 2.1.999; `changelog_gap` ← {{"after": "2.1.0", "before": "{oldest}", "recorded": "2026-10-20"}}.
- Section 1 cell: `2.1.0 → 2.1.999 (500 releases) · 10 page(s) (gap: 2.1.0 → {oldest} unscanned)`; headline gains ` — changelog gap 2.1.0 → {oldest} unscanned`.

## Scenario C — closing a recorded gap (watermark {wm_C}; gap after={gap_after_C} before={gap_before_C})
- Anchor is the gap's `after` ({gap_after_C}): pages 1, 2, 3 fetched; page 3 contains {gap_after_C} → STOP. pages_fetched 3.
- Input: {delta_C} releases newer than the watermark ({VERSIONS[0]} … {VERSIONS[delta_C - 1]}) + {fill_C} gap-fill releases strictly between {gap_after_C} and {gap_before_C} ({VERSIONS[idx(gap_before_C) + 1]} … {VERSIONS[idx(gap_after_C) - 1]}); releases from {gap_before_C} up to {wm_C} are not re-processed.
- Footer: `releases_scanned: {delta_C + fill_C}`, `gap_fill_scanned: {fill_C}`, `gap_closed: true`, `gap_after: null`, `gap_before: null`, `lane_status: ok`, `newest_version_seen: 2.1.999`, `oldest_version_seen: {p3[-1]['tag_name'][1:]}` (oldest fetched).
- Step 6: watermark → 2.1.999; `changelog_gap` → null. Section 1 cell: `{wm_C} → 2.1.999 ({delta_C + fill_C} releases: {delta_C} new + {fill_C} gap fill) · 3 page(s) (gap {gap_after_C} → {gap_before_C} closed)`. No headline qualifier.

## Scenario D — yanked anchor (`last_changelog_version` = 2.1.960, absent from page 1)
- Page 1: walking newest → oldest, 2.1.961 is newer, then {first_older_D} is LESS than the anchor → STOP there (anchor treated as found). pages_fetched 1.
- In scope: {VERSIONS[0]} … 2.1.961 = {n_D} releases. `lane_status: ok`, no gap, `gap_fill_scanned: 0`, scan_note includes "watermark anchor 2.1.960 not present; sliced at {first_older_D}" and the zero-findings note.
- Step 6: watermark → 2.1.999; `changelog_gap` null. Section 1 cell: `2.1.960 → 2.1.999 ({n_D} releases) · 1 page(s) (anchor tag absent; sliced at {first_older_D})`.

Every scenario: zero findings (bodies are routine), so each run also emits the zero-findings scan_note; `discarded_findings: 0`.
"""
io.open(HERE / "expected.md", "w", encoding="utf-8", newline="").write(expected)
print("phase4 fixture written:", len(VERSIONS), "releases over", PAGES, "pages; A anchor", anchor_A, "| C gap", gap_after_C, "->", gap_before_C, "| D first older", first_older_D)
