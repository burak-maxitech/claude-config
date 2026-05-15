# GSC Setup README Template

This is the **template content** that the `/seo-review` orchestrator auto-writes to `.seo-data/gsc/README.md` on first detection (when `.seo-data/gsc/` exists but `README.md` inside it doesn't).

It's written verbatim — no variable substitution. The target audience is the **human user** who's about to drop CSV exports into the folder, not Claude.

---

## Template content (begin)

```markdown
# Google Search Console — Data Drop Zone

This folder feeds traffic-aware audit data into `/seo-review`. There are
**two supported paths**, both first-class — you can use either or both:

| Path | Best for | Setup effort | Data freshness |
|---|---|---|---|
| **BigQuery Bulk Data Export** | Performance (queries, pages, impressions) | One-time GCP setup (~10 min) | Daily, ~2-day lag |
| **CSV exports** | Page indexing (9-reason report — REQUIRED for indexing signal) and Performance fallback | Manual export per run (~5 min for 13 CSVs) | Whatever you last exported |

Page Indexing data is **CSV-only** — Google's BigQuery export doesn't
include it. So even if you use BigQuery for Performance (recommended),
you'll still drop the 11 indexing CSVs here for the 9-reason cluster
findings.

## What does the skill do with this data?

- Identifies high-impressions, low-CTR pages (title/meta rewrite targets)
- Surfaces queries where you rank at position 5-20 (highest-leverage band
  for on-page optimization)
- Catalogs pages Google crawled-but-didn't-index (content quality signals)
- Detects 404 clusters that match recent code renames (auto-flags bulk
  redirect opportunities)
- Reranks all findings by traffic impact (impressions-weighted)

The /100 score does **not** change based on this data — GSC is informational.
Your `docs/seo-history.md` stays comparable across runs whether GSC data
is present or not, and whether it came from BigQuery or CSVs.

---

## Path 1 (RECOMMENDED): BigQuery Bulk Data Export — Performance

BigQuery gives you the full Performance dataset: no ~1,000-row CSV cap,
full history (not just the 16-month UI window), daily-fresh, and the 28
rich-appearance booleans (is_video, is_review_snippet, is_faq, etc.) that
CSVs don't expose.

### Prerequisites

1. **A GCP project with BigQuery API enabled.** Create one at
   https://console.cloud.google.com/ if you don't have one. Free tier
   includes 1 TB of query processing per month — far more than this
   skill ever uses (~1-10 MB per run).
2. **`gcloud` CLI installed** with the `bq` component. Install:
   https://cloud.google.com/sdk/docs/install. On Windows, the installer
   adds both `gcloud` and `bq` (as `gcloud.cmd` / `bq.cmd`) to PATH.
3. **Application Default Credentials.** Run once:
   `gcloud auth application-default login` — opens a browser, completes
   OAuth, writes credentials to `~/.config/gcloud/`.
4. **IAM** (if you don't already own the project): you need at least
   `roles/bigquery.dataViewer` on the dataset + `roles/bigquery.jobUser`
   on the project.

### Enable the GSC export

5. In Google Search Console: open your property → **Settings** →
   **Bulk data export** → **Configure**.
6. Set destination project + dataset name. Conventional dataset name:
   `searchconsole`. **The dataset must not already exist** — GSC creates
   it on first export. (If it exists, GSC refuses.)
7. **Wait ~2 days.** First export takes 24-48 hours. Subsequent exports
   run daily and lag ~2 days behind real-time.
8. Verify: `bq ls <your-project>:searchconsole` should list
   `searchdata_url_impression`, `searchdata_site_impression`, and
   `ExportLog`.

### Configure `/seo-review` for BigQuery

9. Create `.seo-data/gsc/config.yaml` (the next `/seo-review` run will
   auto-create an unfilled template if you skip this):

   ```yaml
   project_id: <your-gcp-project>
   dataset_id: searchconsole
   location: US

   # Optional:
   # site_url: sc-domain:example.com    # only if dataset has multiple properties
   # lookback_days: 90                  # 7-365, default 90
   ```

10. Run `/seo-review`. The "Detected:" line should say
    `Mode: heuristic + GSC (BigQuery: ...)`.

---

## Path 2 (REQUIRED for Page Indexing — even when using BigQuery): CSV exports

Page indexing reports (the 9-reason breakdown of why pages aren't indexed)
are **only available via CSV export** — Google's BigQuery export doesn't
include them. So whether or not you set up BigQuery, drop these 11 CSVs
into `indexing/` to unlock the indexing-cluster findings.

### Page indexing reports (Tier 1)

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

### Performance CSVs (only if NOT using BigQuery)

Navigate to **Performance** > **Search results**.

| GSC click path | Canonical filename |
|---|---|
| **Queries tab** → ⬇ Export → Download CSV | `performance/queries.csv` |
| **Pages tab** → ⬇ Export → Download CSV | `performance/pages.csv` |

**If `config.yaml` is configured and BigQuery is reachable, these Performance
CSVs are ignored** — BigQuery wins. Drop the Performance CSVs ONLY if you
don't have BigQuery set up. The 11 indexing CSVs above are always read.

## GSC export quirks (CSVs)

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
├── config.yaml                            (BigQuery connection — Path 1)
├── performance/                           (Path 2 — only if NOT using BigQuery)
│   ├── queries.csv
│   └── pages.csv
├── indexing/                              (Path 2 — REQUIRED, even with BigQuery)
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

## 4-state matrix — what mode you'll see

| BigQuery configured? | Indexing CSVs present? | Performance CSVs present? | Mode label |
|---|---|---|---|
| ✓ | ✓ | (ignored) | **Full GSC** (best) |
| ✓ | ✗ | (ignored) | BigQuery Performance only |
| ✗ | ✓ | ✓ | CSV-only (v2 path) |
| ✗ | ✓ | ✗ | Indexing-only |
| ✗ | ✗ | ✓ | Performance-CSV-only |
| ✗ | ✗ | ✗ | Heuristic-only (Section 1 banner fires) |

## Troubleshooting

### CSV-related

| Symptom | Likely cause | Fix |
|---|---|---|
| Skill says "unknown CSV ignored" | Filename doesn't match canonical | Rename to the canonical name from the table above |
| Skill says "expected headers X; detected Y" | GSC exported in non-English UI | Switch GSC to English, re-export |
| Skill says "malformed rows: N" | CSV has truncated rows or quoting issues | Re-export; if persists, open an issue |
| Footer says "freshness: queries.csv is 47 days old" | Time to re-export | Re-export and replace the file |
| Mode says "Heuristic-only" despite files present | Folder structure wrong | Check files are in `performance/` and `indexing/` subfolders, not the root |

### BigQuery-related

| Symptom | Likely cause | Fix |
|---|---|---|
| Mode falls back to CSV despite `config.yaml` filled in | `bq` CLI not installed | Install gcloud SDK: https://cloud.google.com/sdk/docs/install |
| Same, with `gcloud` available | ADC not configured | Run `gcloud auth application-default login` |
| Footer says `Config error: nested keys not supported` | `config.yaml` has indented keys | Use flat single-level keys only (`project_id: x` not `bigquery:\n  project_id: x`) |
| Footer says `Access Denied` on dataset | Missing IAM | Grant `roles/bigquery.dataViewer` on the dataset + `roles/bigquery.jobUser` on the project |
| Footer says `Column 'X' not found` | Google changed the schema | Open an issue — `bigquery-schema.md` needs updating |
| Footer says `Query exceeded maximum_bytes_billed (1 GB)` | Site too large for default cap | Lower `lookback_days` in `config.yaml` (e.g., `lookback_days: 30`) |
| Mode says "BigQuery Performance only" | Indexing CSVs missing | Export the 11 indexing CSVs into `indexing/` |
| First export shows 0 rows | Export just started, < 2 days ago | Wait — first BigQuery export takes 24-48 hours after enabling |

## Removing GSC integration

To go back to heuristic-only mode: delete or empty the `.seo-data/gsc/`
folder (CSVs + `config.yaml` both). The next `/seo-review` will note
"Mode: heuristic" and behave exactly as it did before any GSC data was added.

To switch from BigQuery back to CSV-only: delete `config.yaml` (the BQ
path's activation depends on it). Indexing CSVs stay; add Performance
CSVs if you want full coverage.
```

## Template content (end)

---

## Implementation note for the orchestrator

The orchestrator writes this content **once**, on the first detection of `.seo-data/gsc/` without a `README.md` inside it. Subsequent runs do NOT overwrite the README — the user may have edited it (e.g., added project-specific notes). Idempotency check: `Read` the file; if it exists, skip the write.

The template above is the canonical baseline. If this reference file is updated, existing `.seo-data/gsc/README.md` files in user projects do NOT auto-update — they're treated as user-owned content. To force a refresh, the user can delete their README and re-run.
