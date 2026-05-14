# GSC Setup README Template

This is the **template content** that the `/seo-review` orchestrator auto-writes to `.seo-data/gsc/README.md` on first detection (when `.seo-data/gsc/` exists but `README.md` inside it doesn't).

It's written verbatim — no variable substitution. The target audience is the **human user** who's about to drop CSV exports into the folder, not Claude.

---

## Template content (begin)

```markdown
# Google Search Console — Export Drop Zone

This folder feeds traffic-aware audit data into `/seo-review`. Drop your
Google Search Console CSV exports here, renamed to the canonical filenames
below, and the next `/seo-review` run will produce traffic-prioritized
recommendations instead of static-only heuristics.

## What does the skill do with this data?

- Identifies high-impressions, low-CTR pages (title/meta rewrite targets)
- Surfaces queries where you rank at position 5-20 (highest-leverage band
  for on-page optimization)
- Catalogs pages Google crawled-but-didn't-index (content quality signals)
- Detects 404 clusters that match recent code renames (auto-flags bulk
  redirect opportunities)
- Reranks all findings by traffic impact (impressions-weighted)

The /100 score does **not** change based on this data — GSC is informational.
Your `docs/seo-history.md` stays comparable across runs whether CSVs are
present or not.

## Quick start

1. Open https://search.google.com/search-console for your property.
2. Export each of the CSVs below (Performance + Page indexing).
3. Rename each downloaded file to the canonical name shown.
4. Drop it into the matching subfolder here.
5. Re-run `/seo-review`.

## Required exports (Tier 1)

### Performance reports

Navigate to **Performance** > **Search results**. The "Date range" defaults
to the last 3 months — leave that, or extend to capture more data.

| GSC click path | Canonical filename |
|---|---|
| **Queries tab** → ⬇ Export → Download CSV | `performance/queries.csv` |
| **Pages tab** → ⬇ Export → Download CSV | `performance/pages.csv` |

### Page indexing reports

Navigate to **Indexing** > **Pages**.

| GSC click path | Canonical filename |
|---|---|
| Top-level "Why pages aren't indexed" table → ⬇ Export → CSV | `indexing/summary.csv` |
| Click "Crawled - currently not indexed" row → ⬇ Export → CSV | `indexing/crawled-not-indexed.csv` |
| Click "Discovered - currently not indexed" row → ⬇ Export → CSV | `indexing/discovered-not-indexed.csv` |
| Click "Not found (404)" row → ⬇ Export → CSV | `indexing/not-found-404.csv` |
| Click "Page with redirect" row → ⬇ Export → CSV | `indexing/page-with-redirect.csv` |
| Click "Alternate page with proper canonical tag" row → ⬇ Export → CSV | `indexing/alternate-canonical.csv` |
| Click "Duplicate, Google chose different canonical than user" row → ⬇ Export → CSV | `indexing/duplicate-google-chose-different.csv` |
| Click "Blocked due to other 4xx issue" row → ⬇ Export → CSV | `indexing/blocked-4xx.csv` |
| Click "Blocked due to access forbidden (403)" row → ⬇ Export → CSV | `indexing/blocked-403.csv` |
| Click "Soft 404" row → ⬇ Export → CSV | `indexing/soft-404.csv` |
| Click "Server error (5xx)" row → ⬇ Export → CSV | `indexing/server-error-5xx.csv` |

Skip any reason row that's empty (count = 0) — no need to export an empty CSV.

## GSC export quirks

- **Filename collision:** GSC names every export `Table.csv` or
  `<property>_Insights_<dates>.csv`. You must rename each one. The skill
  recognizes only the canonical filenames above.
- **Language:** export in English. v1 only supports English headers (`Top
  queries`, `Clicks`, `Impressions`, `CTR`, `Position`). Use a GSC session
  in English if your default UI is another language.
- **Date range:** default 3 months is fine. The skill cares about freshness
  (file mtime), not the data range — but a longer range gives better
  signal stability.

## Privacy

This folder is **automatically added to `.gitignore`** the first time the
skill detects it. Search queries can include brand-internal product names
and the occasional accidentally-PII-adjacent string, so the default is
"don't commit." If you want to commit anyway (e.g., team-shared
prioritization), remove the `.seo-data/gsc/` line from `.gitignore`.

## Freshness

- Files < 30 days old: treated as fresh.
- 30-90 days old: footer warning ("consider re-export").
- > 90 days: stronger warning, but the run continues.

GSC's data itself lags real-world events by 2-3 days. Re-export when you've
made significant changes and want updated signal — typically every 4-6
weeks matches Google's recrawl + position-stabilization cycle.

## Folder layout reference

```
.seo-data/gsc/
├── README.md                              (this file)
├── performance/
│   ├── queries.csv
│   └── pages.csv
├── indexing/
│   ├── summary.csv
│   ├── crawled-not-indexed.csv
│   ├── discovered-not-indexed.csv
│   ├── not-found-404.csv
│   ├── page-with-redirect.csv
│   ├── alternate-canonical.csv
│   ├── duplicate-google-chose-different.csv
│   ├── blocked-4xx.csv
│   ├── blocked-403.csv
│   ├── soft-404.csv
│   └── server-error-5xx.csv
├── core-web-vitals/                       (Tier 2 — recognized, not parsed in v1)
├── enhancements/                          (Tier 2 — recognized, not parsed in v1)
└── sitemaps.csv                           (Tier 2 — recognized, not parsed in v1)
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Skill says "unknown CSV ignored" | Filename doesn't match canonical | Rename to the canonical name from the table above |
| Skill says "expected headers X; detected Y" | GSC exported in non-English UI | Switch GSC to English, re-export |
| Skill says "malformed rows: N" | CSV has truncated rows or quoting issues | Re-export; if persists, open an issue |
| Footer says "freshness: queries.csv is 47 days old" | Time to re-export | Re-export and replace the file |
| Footer says "GSC Mode: disabled" despite files present | Folder structure wrong | Check files are in `performance/` and `indexing/` subfolders, not the root |

## Removing GSC integration

To go back to heuristic-only mode: just delete or empty the `.seo-data/gsc/`
folder. The next `/seo-review` will note "GSC Mode: disabled" in the footer
and behave exactly as it did before any CSVs were added.
```

## Template content (end)

---

## Implementation note for the orchestrator

The orchestrator writes this content **once**, on the first detection of `.seo-data/gsc/` without a `README.md` inside it. Subsequent runs do NOT overwrite the README — the user may have edited it (e.g., added project-specific notes). Idempotency check: `Read` the file; if it exists, skip the write.

The template above is the canonical baseline. If this reference file is updated, existing `.seo-data/gsc/README.md` files in user projects do NOT auto-update — they're treated as user-owned content. To force a refresh, the user can delete their README and re-run.
