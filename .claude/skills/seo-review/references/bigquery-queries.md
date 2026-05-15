# BigQuery Queries — Canonical SQL Templates

Loaded by the orchestrator (Step 1.6) when BigQuery is the configured Performance ingestion path. Provides 5 parametrized SQL templates that produce digests **byte-identical to v2's CSV-sourced digests** (modulo row count — BigQuery isn't capped at GSC's ~1,000-row UI limit).

For column types + JSON output shape, see `bigquery-schema.md`. For digest field names + downstream consumers, see `gsc-ingestion.md`.

**All queries assume the BigQuery dataset has `searchdata_url_impression` populated.** If it doesn't, the orchestrator fails Phase 1 detection per `bigquery-schema.md`'s "Tables in scope" section.

---

## Invocation contract

The orchestrator invokes each template via Bash:

```
bq query \
  --use_legacy_sql=false \
  --maximum_bytes_billed=1000000000 \
  --format=json \
  --location=<location_from_config> \
  '<SQL>'
```

**Per-query failure handling**: a single template failing (auth, schema, scan-cap) is logged + that signal is skipped. Other templates still run. The orchestrator collects results across all 5 in a single parallel-Bash turn.

**Parameter substitution**: templates use `<<PROJECT>>`, `<<DATASET>>`, `<<LOOKBACK_DAYS>>` as placeholders. Orchestrator replaces them before passing the SQL. Use backticks around the table reference: `` `<<PROJECT>>.<<DATASET>>.searchdata_url_impression` ``.

**Lookback default**: `<<LOOKBACK_DAYS>> = 90` (configurable in `.seo-data/gsc/config.yaml` via `lookback_days:`). The 90-day window matches GSC UI's default and the typical SEO-feedback horizon.

---

## Q1 — Queries digest (top-50 position 5-20)

**Replaces v2's `performance/queries.csv` digest.** Emits queries where the site ranks in the "page 2 / low page 1" band — the high-leverage band where small wins move pages up.

```sql
SELECT
  query,
  SUM(impressions) AS impressions,
  SUM(clicks) AS clicks,
  SAFE_DIVIDE(SUM(clicks), SUM(impressions)) AS ctr,
  1 + SAFE_DIVIDE(SUM(sum_position), SUM(impressions)) AS avg_position
FROM `<<PROJECT>>.<<DATASET>>.searchdata_url_impression`
WHERE data_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL <<LOOKBACK_DAYS>> DAY) AND CURRENT_DATE()
  AND query IS NOT NULL
  AND is_anonymized_query = FALSE
GROUP BY query
HAVING SUM(impressions) >= 100
  AND 1 + SAFE_DIVIDE(SUM(sum_position), SUM(impressions)) BETWEEN 5 AND 20
ORDER BY impressions DESC
LIMIT 50
```

**Digest field-mapping (output → v2 shape):**

| BQ row field | Digest field | Coercion |
|---|---|---|
| `query` | `query` | passthrough |
| `impressions` | `impressions` | string → number |
| `clicks` | `clicks` | string → number |
| `ctr` | `ctr` (decimal 0-1) | string → number; ×100 for display |
| `avg_position` | `position` (1-based decimal) | string → number; 2dp display |

---

## Q2 — Pages digest (top-50 by impressions)

**Replaces v2's `performance/pages.csv` digest.** Emits the highest-traffic pages with their aggregate CTR + position. Feeds the median-CTR baseline used to flag CTR-underperformer findings.

```sql
SELECT
  url,
  SUM(impressions) AS impressions,
  SUM(clicks) AS clicks,
  SAFE_DIVIDE(SUM(clicks), SUM(impressions)) AS ctr,
  1 + SAFE_DIVIDE(SUM(sum_position), SUM(impressions)) AS avg_position
FROM `<<PROJECT>>.<<DATASET>>.searchdata_url_impression`
WHERE data_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL <<LOOKBACK_DAYS>> DAY) AND CURRENT_DATE()
  AND url IS NOT NULL
  AND url != ''
GROUP BY url
HAVING SUM(impressions) >= 10
ORDER BY impressions DESC
LIMIT 50
```

**Note:** no `is_anonymized_query` filter here — we want page-level aggregates including anonymized-query impressions (the URL is still known when the query is anonymized).

---

## Q3 — `url_impressions_map` (all-URL → impressions, for traffic_weight)

**Replaces v2's URL→impression mapping built from `pages.csv` for traffic-weighted ranking (Step 6.6).** This is uncapped (no `LIMIT 50`) because traffic_weight needs full coverage; but `WHERE` clauses bound it.

```sql
SELECT
  url,
  SUM(impressions) AS impressions
FROM `<<PROJECT>>.<<DATASET>>.searchdata_url_impression`
WHERE data_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL <<LOOKBACK_DAYS>> DAY) AND CURRENT_DATE()
  AND url IS NOT NULL
  AND url != ''
GROUP BY url
HAVING SUM(impressions) >= 1
ORDER BY impressions DESC
```

**Result becomes** `url_impressions_map: { "<url>": <impressions>, ... }` passed to all subagents and to Step 6.6's traffic_weight formula:

```
traffic_weight = max(1.0, log10(url_impressions_map[<finding.affected_url>] + 1))
```

When URL not in map → `traffic_weight = 1.0` (formula collapses to legacy `score_impact × certainty / effort_weight`).

**Size budget**: at 1 row per URL, even a 10k-URL site is < 200KB JSON. Well under any prompt-size concern.

---

## Q4 — Traffic-orphan candidates (sitemap URLs absent from impressions)

**Replaces v2's traffic-orphan computation.** Returns the set of impressed URLs as a basis for set-difference against the sitemap URL list (orchestrator does the set diff after both are loaded).

This is the same data as Q3 with `LIMIT 50` and a strict impression floor — keeps the comparison set bounded.

```sql
SELECT DISTINCT url
FROM `<<PROJECT>>.<<DATASET>>.searchdata_url_impression`
WHERE data_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL <<LOOKBACK_DAYS>> DAY) AND CURRENT_DATE()
  AND url IS NOT NULL
  AND url != ''
  AND impressions > 0
```

**Orchestrator behaviour**: load the sitemap URL list (from Step 3.2 sitemap probe), compute `sitemap_urls - impressed_urls = orphan_candidates`, cap orphan_candidates at top-50 by sitemap order. Q3's result can substitute for Q4 (same column shape) — Q4 exists as a documentation point; in practice the orchestrator reuses Q3's output.

---

## Q5 — Last-data-date freshness probe

**Replaces v2's CSV-file-mtime freshness check.** Single-row, ~zero-byte scan (BigQuery min-max scan on partition column is metadata-only).

```sql
SELECT
  MAX(data_date) AS latest_data_date,
  MIN(data_date) AS earliest_data_date,
  COUNT(DISTINCT data_date) AS partition_count
FROM `<<PROJECT>>.<<DATASET>>.searchdata_url_impression`
```

**Freshness policy** (matches v2 thresholds):

| `CURRENT_DATE() - latest_data_date` | Behaviour |
|---|---|
| ≤ 30 days | Fresh — no annotation |
| 30 - 90 days | Footer note: `BigQuery export stale — last data_date YYYY-MM-DD (N days old). Verify export is still running in GSC Settings > Bulk data export.` |
| > 90 days | Footer note: `BigQuery export significantly stale — last data_date YYYY-MM-DD (N days old). Recommendations may not reflect recent GSC state.` Performance signal still applied; user warned. |

**Never blocks the run.** GSC may legitimately fall behind during export pipeline incidents; v3 surfaces the staleness instead of suppressing the signal.

`partition_count == 1` is normal in a freshly-enabled export (one day's data). Don't treat single-partition as an error.

---

## Parallel dispatch

All 5 queries are independent — the orchestrator invokes them in a single parallel-Bash turn (matches the v2 parallel-Read pattern for CSVs in Step 1.5/1.6). Total wall time ≈ slowest single query, typically 2-5s for small properties.

If 4 of 5 succeed and 1 fails, the orchestrator surfaces the failure in the footer and proceeds — Performance signal is partial-coverage (e.g., url_impressions_map missing → all findings get `traffic_weight = 1.0` fallback; that's noisier but not wrong).

---

## What v3 does NOT query

| Query | Why deferred |
|---|---|
| Country/device split aggregates | v3.x — dimensional explosion without clear v1 finding emission |
| Discover impressions (`WHERE search_type = 'discover'`) | v3.x — Discover-specific catalog deferred |
| Rich-result aggregation (`SUM(IF(is_review_snippet, ...))`) | v3.x — rich-snippet underutilization is a new sub-dim |
| `searchdata_site_impression` reads | v3.x — site-wide query gap analysis |
| Time-series (per-day) impressions | v3.x — trend findings need a separate digest shape |
