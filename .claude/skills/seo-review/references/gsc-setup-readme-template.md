# GSC Setup README Template

This is the **template content** that the `/seo-review` orchestrator auto-writes to `.seo-data/gsc/README.md` on first detection (when `.seo-data/gsc/` exists but `README.md` inside it doesn't).

It's written verbatim — no variable substitution. The target audience is the **human user** who's about to drop CSV exports into the folder, not Claude.

---

## Template content (begin)

```markdown
# Google Search Console — Data Drop Zone

This folder feeds traffic-aware audit data into `/seo-review`. There are
**three supported paths** — pick whichever fits your setup (Path 1 recommended
for new users):

| Path | Covers | Setup effort | Data freshness |
|---|---|---|---|
| **Path 1: Search Console API** (RECOMMENDED) | Performance + Indexing in one auth | gcloud SDK install + OAuth (~5 min) | Real-time (~2-day GSC pipeline lag) |
| **Path 1b: BigQuery Bulk Data Export** (ALTERNATIVE) | Performance only (full history) | gcloud SDK install + GCP project + 2-day export wait (~10 min + waiting) | Daily, ~2-day lag |
| **Path 2: CSV exports** (FALLBACK) | Performance + Indexing (manual) | No install — manual exports per run (~5 min for 13 CSVs) | Whatever you last exported |

You can mix Path 1b with Path 2 (BigQuery for Performance + CSVs for Indexing,
since BigQuery doesn't include indexing data). Path 1 alone covers both signals.

## What does the skill do with this data?

- Identifies high-impressions, low-CTR pages (title/meta rewrite targets)
- Surfaces queries where you rank at position 5-20 (highest-leverage band
  for on-page optimization)
- Catalogs pages Google crawled-but-didn't-index (content quality signals)
- Detects 404 clusters that match recent code renames (auto-flags bulk
  redirect opportunities)
- Reranks all findings by traffic impact (impressions-weighted)

The /100 score does **not** change based on this data — GSC is informational.
Your `docs/seo-history.md` stays comparable across runs regardless of path
(API / BigQuery / CSV).

---

## Path 1 (RECOMMENDED): Search Console API

The Search Console API covers both Performance AND Indexing through a single
auth surface. Simplest setup; richest signal (per-URL indexing diagnostics
that aren't available via CSV exports).

### Prerequisites

1. **A GCP project.** Any GCP project will do — the API is free within
   quota (1,200 QPM Performance / 2,000 URLs/day per property for
   Inspection). Create one at https://console.cloud.google.com/ if you
   don't have one.
2. **`gcloud` CLI installed.** Install: https://cloud.google.com/sdk/docs/install.
   On Windows, the installer adds `gcloud` (and `bq`, `gsutil`) to PATH.
3. **Google account with verified GSC property access.** The Google
   account you sign in with during `gcloud auth` must be the same one
   that has the GSC property registered + verified.

### Authenticate

4. Run once, opens browser for OAuth:
   ```
   gcloud auth application-default login \
     --scopes=https://www.googleapis.com/auth/webmasters.readonly,https://www.googleapis.com/auth/cloud-platform
   ```
   The explicit `--scopes` flag is important — Search Console API often
   accepts the default `cloud-platform` scope but this is undocumented and
   has broken in the past. Explicit `webmasters.readonly` is durable.

5. Set quota project (mandatory for some account/project combinations):
   ```
   gcloud auth application-default set-quota-project <your-gcp-project-id>
   ```

### Configure `/seo-review` for API

6. Create `.seo-data/gsc/config.yaml`:

   ```yaml
   site_url: sc-domain:example.com    # or "https://example.com/" for URL-prefix properties

   # Optional:
   # lookback_days: 90                # 7-365, default 90
   ```

   The exact `site_url` format must match what's registered in GSC.
   Check at https://search.google.com/search-console > Settings.

7. Run `/seo-review`. The "Detected:" line should say
   `Mode: heuristic + GSC (Search Console API — ...)`.

### Verify the first run

- API auth probe: `gcloud auth application-default print-access-token` should print a token. The skill calls `GET /webmasters/v3/sites` at start of each run to verify access; failures surface in footer with specific remediation.
- Performance: 3 `searchanalytics.query` calls per run (Q1 queries digest, Q2 pages digest, Q3 url_impressions_map).
- Indexing: up to 100 `urlInspection.index.inspect` calls per run, prioritizing high-impression URLs + sitemap probe failures + recently-changed paths. Well under the 2,000/day per-property quota.

---

## Path 1b (ALTERNATIVE for unlimited history): BigQuery Bulk Data Export

Use this path when you specifically want **unlimited Performance history**
(the API caps at 16 months rolling). BigQuery's export accumulates daily
and never expires. You'll still need CSVs for Page Indexing — BigQuery
doesn't include indexing data.

### Prerequisites

1. **A GCP project with BigQuery API enabled.** Free tier includes 1 TB
   of query processing per month — far more than this skill ever uses
   (~1-10 MB per run).
2. **`gcloud` CLI installed** with the `bq` component (ships with gcloud
   SDK). Same setup as Path 1.
3. **Application Default Credentials.** Same as Path 1 — the `--scopes`
   flag covers both API and BQ.
4. **IAM** (if you don't already own the project): at least
   `roles/bigquery.dataViewer` on the dataset + `roles/bigquery.jobUser`
   on the project.

### Enable the GSC export

5. In Google Search Console: open your property → **Settings** →
   **Bulk data export** → **Configure**.
6. Set destination project + dataset name. Conventional dataset name:
   `searchconsole`. **The dataset must not already exist** — GSC creates
   it on first export.
7. **Wait ~2 days.** First export takes 24-48 hours. Subsequent exports
   run daily and lag ~2 days behind real-time.
8. Verify: `bq ls <your-project>:searchconsole` should list
   `searchdata_url_impression`, `searchdata_site_impression`, and
   `ExportLog`.

### Configure `/seo-review` for BigQuery

9. Create `.seo-data/gsc/config.yaml`:

   ```yaml
   project_id: <your-gcp-project>
   dataset_id: searchconsole
   location: US

   # Optional:
   # site_url: sc-domain:example.com    # ALSO add this to enable Path 1 (API) alongside
   # lookback_days: 90                  # 7-365, default 90
   ```

10. Drop indexing CSVs in `.seo-data/gsc/indexing/` (Path 2 below).
11. Run `/seo-review`. The "Detected:" line should say
    `Mode: heuristic + GSC (hybrid — Performance: BigQuery; ...)`.

**Note**: if you add `site_url` to config.yaml AND BQ keys, **the API
path wins per precedence**. To force BQ-only, omit `site_url`.

---

## Path 2 (FALLBACK or REQUIRED for indexing when using Path 1b): CSV exports

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

### Performance CSVs (only if NOT using Path 1 API or Path 1b BigQuery)

Navigate to **Performance** > **Search results**.

| GSC click path | Canonical filename |
|---|---|
| **Queries tab** → ⬇ Export → Download CSV | `performance/queries.csv` |
| **Pages tab** → ⬇ Export → Download CSV | `performance/pages.csv` |

**Path precedence**: if `config.yaml` is configured for API (site_url) or
BigQuery (project_id+dataset_id+location) and the path is reachable, these
Performance CSVs are ignored. Path 1 (API) wins over Path 1b (BQ) over Path
2 (CSV) for Performance. Drop the Performance CSVs ONLY if you don't have
API or BigQuery set up. The 11 indexing CSVs above are read when API isn't
available for indexing (Path 1b + Path 2 hybrid).

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
├── config.yaml                            (API or BigQuery config — Path 1 or 1b)
├── performance/                           (Path 2 — only if NOT using API or BQ)
│   ├── queries.csv
│   └── pages.csv
├── indexing/                              (Path 2 — REQUIRED with Path 1b, optional with Path 1)
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

## Mode labels — what state you'll see

The skill computes which paths are reachable (API + BQ + CSV) and collapses
to one of four user-facing modes:

| Mode label | Condition | What happens |
|---|---|---|
| **Full GSC (API)** | API reachable for both Performance + Indexing | best state — most signal, no warnings |
| **Full GSC (hybrid)** | Both signals present but mixed sources (e.g., API + CSV indexing; BQ + CSV indexing; CSV+CSV) | footer note showing source per signal |
| **Partial GSC** | Exactly one signal present, one missing | footer note + upgrade hint |
| **Heuristic-only** | No API, no BQ, no CSVs | Section 1 banner fires; report runs heuristic-only |

The precedence order per signal:
- **Performance**: Search Console API > BigQuery > CSV > none
- **Indexing**: Search Console API > CSV > none

(BigQuery doesn't cover Indexing — Google's product limitation.)

## Troubleshooting

### CSV-related

| Symptom | Likely cause | Fix |
|---|---|---|
| Skill says "unknown CSV ignored" | Filename doesn't match canonical | Rename to the canonical name from the table above |
| Skill says "expected headers X; detected Y" | GSC exported in non-English UI | Switch GSC to English, re-export |
| Skill says "malformed rows: N" | CSV has truncated rows or quoting issues | Re-export; if persists, open an issue |
| Footer says "freshness: queries.csv is 47 days old" | Time to re-export | Re-export and replace the file |
| Mode says "Heuristic-only" despite files present | Folder structure wrong | Check files are in `performance/` and `indexing/` subfolders, not the root |

### Search Console API-related (Path 1)

| Symptom | Likely cause | Fix |
|---|---|---|
| Mode falls back to BQ/CSV despite `site_url` set | `gcloud` CLI not installed | Install gcloud SDK: https://cloud.google.com/sdk/docs/install |
| Same, with `gcloud` available | ADC not configured | Run `gcloud auth application-default login --scopes=...` (see Path 1 setup above) |
| Footer says `Search Console API auth failed: 401 UNAUTHENTICATED` | OAuth scope insufficient | Re-run `gcloud auth application-default login` with the `--scopes=https://www.googleapis.com/auth/webmasters.readonly,...` flag |
| Footer says `Search Console API access denied: 403 PERMISSION_DENIED` | The Google account isn't verified on this GSC property | Verify property ownership in https://search.google.com/search-console > Settings, or switch ADC to an account that owns the property |
| Footer says `site_url '<X>' not found in your verified properties` | `site_url` value doesn't match what's registered in GSC | Check exact format at https://search.google.com/search-console > Settings > Property settings. `sc-domain:example.com` for Domain properties; `https://example.com/` (with trailing slash) for URL-prefix |
| Footer says `URL Inspection quota exhausted` | Hit 2,000/day per-property cap | Re-run tomorrow, OR lower the inspection budget in `gsc-api-queries.md`, OR upgrade GCP project quota |
| Mode says "Partial GSC (perf: api, indexing: none)" | API auth works but quota for URL Inspection was hit | Same as above — graceful degrade |

### BigQuery-related (Path 1b)

| Symptom | Likely cause | Fix |
|---|---|---|
| Mode falls back to CSV despite BQ keys filled in | `bq` CLI not installed | Install gcloud SDK: https://cloud.google.com/sdk/docs/install (includes `bq`) |
| Same, with `gcloud` available | ADC not configured | Run `gcloud auth application-default login` |
| Footer says `Config error: nested keys not supported` | `config.yaml` has indented keys | Use flat single-level keys only (`project_id: x` not `bigquery:\n  project_id: x`) |
| Footer says `Access Denied` on dataset | Missing IAM | Grant `roles/bigquery.dataViewer` on the dataset + `roles/bigquery.jobUser` on the project |
| Footer says `Column 'X' not found` | Google changed the BQ schema | Open an issue — `bigquery-schema.md` needs updating |
| Footer says `Query exceeded maximum_bytes_billed (1 GB)` | Site too large for default cap | Lower `lookback_days` in `config.yaml` (e.g., `lookback_days: 30`) |
| Mode says "BigQuery Performance only" | Indexing CSVs missing AND API not configured | Either add `site_url` to use Path 1 for indexing OR export the 11 indexing CSVs (Path 2) |
| First export shows 0 rows | Export just started, < 2 days ago | Wait — first BigQuery export takes 24-48 hours after enabling |

## Removing GSC integration

To go back to heuristic-only mode: delete or empty the `.seo-data/gsc/`
folder (CSVs + `config.yaml` both). The next `/seo-review` will note
"Mode: heuristic" and behave exactly as it did before any GSC data was added.

To switch between paths:
- **API → CSV-only**: remove `site_url` from `config.yaml` (API deactivates). Indexing CSVs become primary.
- **API → BigQuery**: replace `site_url` with `project_id`+`dataset_id`+`location`. BQ becomes primary for Performance; CSV still required for Indexing.
- **BigQuery → API**: replace BQ keys with `site_url`. API becomes primary for both signals. Indexing CSVs become optional.
- **Any → heuristic**: delete `config.yaml` and `.seo-data/gsc/` folder entirely.
```

## Template content (end)

---

## Implementation note for the orchestrator

The orchestrator writes this content **once**, on the first detection of `.seo-data/gsc/` without a `README.md` inside it. Subsequent runs do NOT overwrite the README — the user may have edited it (e.g., added project-specific notes). Idempotency check: `Read` the file; if it exists, skip the write.

The template above is the canonical baseline. If this reference file is updated, existing `.seo-data/gsc/README.md` files in user projects do NOT auto-update — they're treated as user-owned content. To force a refresh, the user can delete their README and re-run.
