# BigQuery Schema — Canonical Reference

Loaded by the orchestrator (Step 1.6) when BigQuery is the configured Performance ingestion path. This file is the **source-of-truth column inventory** that `bigquery-queries.md` references and that the v3 `--maximum_bytes_billed` failure-mode docs reference.

For ingestion behaviour, digest shape, and the 12 sub-dim catalog, see `gsc-ingestion.md`. For SQL templates that read these tables, see `bigquery-queries.md`. For config layout, see `bigquery-config-template.md`.

**Schema source:** [Google Search Console Bulk Data Export — Table guidelines](https://support.google.com/webmasters/answer/12918484). Verified 2026-05-15 against a live export (Table ID example: `burakarik.searchconsole.searchdata_url_impression`) via `INFORMATION_SCHEMA.COLUMNS` JSON dump — column-by-column match.

**Type-name aliases**: BigQuery accepts two names for the same type. UI Schema tab shows the **legacy** names (`BOOLEAN`, `INTEGER`); `INFORMATION_SCHEMA.COLUMNS` returns the **GoogleSQL canonical** names (`BOOL`, `INT64`). This doc uses legacy names (matches what users see clicking through the BigQuery Console). Templates in `bigquery-queries.md` work identically against either — type-name choice in DDL doesn't affect query syntax or JSON output encoding.

---

## Tables in scope

GSC's Bulk Data Export creates a BigQuery dataset (the user names it in GSC Settings; conventional name is `searchconsole`) with up to 3 tables:

| Table | Purpose | Queried by v3? |
|---|---|---|
| `searchdata_url_impression` | Per-URL × query impression rows. The primary table — every v3 query reads from this. | **Yes** |
| `searchdata_site_impression` | Site-aggregated (no URL column) impression rows. Useful for site-wide query rankings; **not used in v3**. | No |
| `ExportLog` | Bookkeeping (export agenda, namespace, data_date, epoch_version, publish_time). Created at first export. | No |

**`ExportLog` columns** (verified 2026-05-15): `agenda STRING`, `namespace STRING`, `data_date DATE`, `epoch_version INTEGER`, `publish_time TIMESTAMP`. v3 doesn't query it. Future use: an alternative freshness probe via `SELECT MAX(publish_time) FROM ExportLog` instead of `SELECT MAX(data_date) FROM searchdata_url_impression` (Q5).

If `searchdata_url_impression` is not present, fail Phase 1 detection with: `BigQuery dataset configured (project=<x> dataset=<y>) but searchdata_url_impression table is missing — wait for first export to complete (~2 days after enabling in GSC Settings) or re-check dataset name`.

---

## `searchdata_url_impression` — column inventory

42 columns. Partitioned daily on `data_date`. Partition filter **not required** (column-default), but every v3 query SHOULD filter on it for cost containment.

**Mode for every column: `NULLABLE`** (BigQuery nullable, but several columns are effectively required — see Notes).

### Date partition (1)

| Column | Type | Notes |
|---|---|---|
| `data_date` | `DATE` | Partition column. Every query MUST filter `WHERE data_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL <N> DAY) AND CURRENT_DATE()`. DO NOT use `_PARTITIONTIME` — it's the wrong pseudo-column for this table and a query using it scans the entire table. |

### Identity + dimensions (6)

| Column | Type | Notes |
|---|---|---|
| `site_url` | `STRING` | Property URL as registered in GSC. For domain properties: `sc-domain:example.com`. For URL-prefix properties: `https://www.example.com/`. |
| `url` | `STRING` | Specific page URL that received the impression. Empty string when the row aggregates over anonymized queries. |
| `query` | `STRING` | Search query string. Empty string when `is_anonymized_query = TRUE` (Google withholds the query for privacy when impressions are too low). |
| `country` | `STRING` | ISO-3166-1 alpha-3 code, lowercase (e.g., `usa`, `gbr`, `deu`). NOT alpha-2. |
| `search_type` | `STRING` | One of `web`, `image`, `video`, `news`, `discover`, `googleNews`. |
| `device` | `STRING` | One of `desktop`, `mobile`, `tablet`. |

### Privacy flags (2)

| Column | Type | Notes |
|---|---|---|
| `is_anonymized_query` | `BOOLEAN` | TRUE when Google anonymized the query (low-impression). Roughly 30-50% of rows on small sites. **Every v3 query that joins on `query` MUST filter `WHERE is_anonymized_query = FALSE AND query IS NOT NULL`** — anonymized rows have empty `query` and are useless for finding emission. |
| `is_anonymized_discover` | `BOOLEAN` | TRUE when Google anonymized the row in Discover. Independent of `is_anonymized_query`. Not filtered by v3 (we don't query Discover in v3). |

### Rich-appearance flags (30)

All `BOOLEAN`, all `NULLABLE`. TRUE when this impression appeared in the corresponding rich result type. v3 doesn't aggregate these in v1 (deferred to v3.x for rich-snippet underutilization detection), but they're documented for completeness.

```
is_amp_top_stories       is_amp_blue_link         is_amp_story             is_amp_image_result
is_job_listing           is_job_details           is_action                is_weblite
is_tpf_qa                is_tpf_faq               is_tpf_howto             is_events_listing
is_events_details        is_forums                is_search_appearance_android_app
is_video                 is_organic_shopping      is_review_snippet
is_special_announcement  is_recipe_feature        is_recipe_rich_snippet
is_subscribed_content    is_page_experience       is_practice_problems
is_math_solvers          is_translated_result     is_edu_q_and_a
is_product_snippets      is_merchant_listings     is_learning_videos
```

**Naming notes**: FAQ + HowTo + Q&A appear with the `is_tpf_` prefix (Templated Page Format) — NOT bare `is_faq` / `is_howto`. Plan documents written from older Google docs may use the bare names; the schema source-of-truth is this file.

### Metrics (3)

| Column | Type | Notes |
|---|---|---|
| `impressions` | `INTEGER` | Count of impressions for this row's URL × query × dimensions combo on `data_date`. |
| `clicks` | `INTEGER` | Count of clicks. CTR = `clicks / impressions`. |
| `sum_position` | `INTEGER` | Sum of **zero-based** ranks across impressions for this row. **Average position = `1 + (sum_position / impressions)`** — the `+1` converts zero-based to the one-based position users see in the GSC UI. |

---

## `searchdata_site_impression` — column inventory (reference only — not queried in v3)

10 columns. Same partition (`data_date`), no `url` column, no rich-appearance booleans.

```
data_date           DATE         (partition)
site_url            STRING
query               STRING
is_anonymized_query BOOLEAN
country             STRING
search_type         STRING
device              STRING
impressions         INTEGER
clicks              INTEGER
sum_top_position    INTEGER      ← note: NOT sum_position
```

The metric column is `sum_top_position` (sum of top-ranking position for that query across the site), not `sum_position`. **Average position = `1 + (sum_top_position / impressions)`** — same conversion formula. v3 does not query this table; v3.x may use it for site-wide query gap analysis.

---

## Hard query rules

Every SQL template in `bigquery-queries.md` MUST satisfy:

1. **Partition filter on `data_date`**: `WHERE data_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL <lookback_days> DAY) AND CURRENT_DATE()`. NOT `_PARTITIONTIME` — wrong pseudo-column triggers a full table scan.
2. **Anonymized-query filter when joining on query**: `AND query IS NOT NULL AND is_anonymized_query = FALSE`. Drops the ~30-50% of rows that carry empty `query` strings.
3. **Cost cap**: orchestrator invokes `bq query --maximum_bytes_billed=1000000000 --format=json '<sql>'`. BigQuery aborts server-side if estimated scan exceeds 1 GB. Per-call cap, not per-run.
4. **Result cap**: every digest-feeding query ends with `LIMIT 50` to match the v2 CSV digest cap. Subagent prompt size stays bounded.

---

## JSON output shape (`bq query --format=json`)

`bq query --format=json` returns a JSON array of objects. **Note BigQuery's encoding rules** — Phase 1's digest translator must handle these:

| BQ type | JSON encoding | Translation |
|---|---|---|
| `STRING` | JSON string | passthrough |
| `INTEGER` | **JSON string** (quoted), e.g. `"1234"` | `parseInt` / cast to number before arithmetic |
| `FLOAT64` / `NUMERIC` | JSON string (quoted) | `parseFloat` |
| `BOOLEAN` | JSON literal `true` / `false` | passthrough |
| `DATE` | JSON string `"YYYY-MM-DD"` | passthrough or `Date.parse` |
| `TIMESTAMP` | JSON string ISO-8601 | passthrough |
| `NULL` | JSON `null` | guard before arithmetic |

The INTEGER-as-string is the trap. `row.impressions / row.clicks` without casting silently concatenates strings. Phase 1's translator coerces all INTEGER columns to JS Number on ingest.

Example single row (shape only, redacted):

```json
{
  "data_date": "2026-05-13",
  "site_url": "sc-domain:example.com",
  "url": "https://example.com/some-page",
  "query": "an example query",
  "is_anonymized_query": false,
  "country": "usa",
  "search_type": "web",
  "device": "mobile",
  "impressions": "47",
  "clicks": "3",
  "sum_position": "234"
}
```

(Calculated: avg_position = 1 + 234/47 ≈ 5.98, ctr = 3/47 ≈ 6.4%.)

---

## Schema drift handling

When a query returns `Error in query string: Column 'X' not found in table` or equivalent, the orchestrator:

1. Surfaces the exact error verbatim in the report footer
2. Logs: `BigQuery schema drift detected — column <X> missing or renamed. v3 schema was validated against Google's docs as of 2026-05-15. Re-validate against current schema: https://support.google.com/webmasters/answer/12918484`
3. Skips the Performance signal for this run (no silent fallback to CSV — explicit per-Q10 decision)
4. Continues with indexing CSVs if present

DO NOT auto-retry with a different column name. DO NOT mark the run partial-success — Performance is degraded, surface it loudly.

---

## What v3 does NOT do (deferred)

| Capability | Why deferred |
|---|---|
| Discover-specific analysis (filter on `search_type = 'discover'`) | v1 scope — web/image/video only. v3.x. |
| Rich-snippet underutilization (aggregate by `is_*` flags) | v3.x. The columns are documented above so subagents can reference them when explaining a finding, but no query aggregates on them in v3. |
| Country / device splits (group by `country`, `device`) | v3.x. Adds dimensional noise without clear finding emission in v1. |
| Multi-property (multiple `site_url` values in same dataset) | v3 is single-property. Multi-property = future `.seo-data/gsc/<property>/`. |
| Querying `searchdata_site_impression` | Reserved for v3.x site-wide query gap analysis. |
| **Indexing data via URL Inspection API → custom BQ table** | v3 reads indexing from `.seo-data/gsc/indexing/*.csv` (the 9-reason report). Google's Bulk Export does NOT include indexing tables (verified 2026-05-15 via 5 official Google docs + live export). The URL Inspection API can populate a custom BQ table per-URL, but requires user-maintained ingestion infrastructure (Python script or Cloud Function), is rate-limited (2k URLs/day per property, 600/min per project), and produces per-URL records that need reshaping to fit the 9-reason cluster catalog (sub-dims 2-9). Deferred to v3.x as an alternative path; CSV path stays primary. |
| **Core Web Vitals via CrUX public BQ dataset** | The `chrome-ux-report.all.<YYYYMM>` public dataset exposes CWV at origin/URL granularity. v3 doesn't audit CWV at all (Performance dim is heuristic-based — image weight, font preload, render-blocking scripts). Adding CWV is a new signal stream + new sub-dim category requiring its own rubric weight allocation. v3.x design problem, not a v3 expansion. |
