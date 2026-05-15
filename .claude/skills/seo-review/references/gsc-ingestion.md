# GSC Ingestion — Canonical Reference

Loaded by the orchestrator in **Step 1.6** of `SKILL.md`. This file is the source of truth for:
- Folder layout under `.seo-data/gsc/`
- Expected CSV filenames + their canonical column headers
- Per-CSV parsing rules + graceful-fail behavior
- Per-CSV finding-type catalog (12 sub-dims, thresholds, severity/certainty defaults)
- Digest caps + ranking inputs
- Setup banner content
- `.gitignore` auto-append rules
- Freshness policy

For the **finding output shape**, ranking formulas, and `score_impact: 0` invariant, see `rubric.md` — that file is the contract; this file is the implementation reference.

---

## Folder layout

```
.seo-data/gsc/
├── README.md                              (auto-created on first detection)
├── performance/
│   ├── queries.csv                        GSC: Performance > Search results > Queries tab > Export
│   ├── pages.csv                          GSC: Performance > Search results > Pages tab > Export
│   ├── countries.csv                      (optional — not used in v1)
│   └── devices.csv                        (optional — not used in v1)
├── indexing/
│   ├── summary.csv                        GSC: Page indexing > Export the top-level "Why pages aren't indexed" table
│   ├── crawled-not-indexed.csv            GSC: Page indexing > click "Crawled - currently not indexed" > Export
│   ├── discovered-not-indexed.csv         GSC: Page indexing > click "Discovered - currently not indexed" > Export
│   ├── not-found-404.csv                  GSC: Page indexing > click "Not found (404)" > Export
│   ├── page-with-redirect.csv             GSC: Page indexing > click "Page with redirect" > Export
│   ├── alternate-canonical.csv            GSC: Page indexing > click "Alternate page with proper canonical tag" > Export
│   ├── duplicate-google-chose-different.csv  GSC: Page indexing > click "Duplicate, Google chose different canonical than user" > Export
│   ├── blocked-4xx.csv                    GSC: Page indexing > click "Blocked due to other 4xx issue" > Export
│   ├── blocked-403.csv                    GSC: Page indexing > click "Blocked due to access forbidden (403)" > Export
│   ├── soft-404.csv                       GSC: Page indexing > click "Soft 404" > Export
│   └── server-error-5xx.csv               GSC: Page indexing > click "Server error (5xx)" > Export
├── core-web-vitals/                       (Tier 2 — not parsed in v1, skip with footer note)
├── enhancements/                          (Tier 2 — not parsed in v1, skip with footer note)
└── sitemaps.csv                           (Tier 2 — not parsed in v1, skip with footer note)
```

**Tier 1 CSVs in v1:** the 2 under `performance/` + the 11 under `indexing/`. Tier 2 (CWV, Enhancements, Sitemaps status) is recognized but skipped with a footer note "found N Tier 2 CSVs — not parsed in v1; will be supported in a future version." Users can still export them now without breaking anything.

**File naming convention:** GSC's "Export → CSV" produces files named `Table.csv` or `<property>_Insights_<dates>.csv` (the exact name varies by tab + property + locale). The user manually renames each download to the canonical filename and drops it into the matching subfolder. The skill never inspects the originally-downloaded filename.

**Unknown files:** any CSV in `.seo-data/gsc/` whose path doesn't match the canonical inventory above is logged in the report footer as `unknown CSV ignored: <path>` and otherwise ignored — does not block ingestion of recognized files.

---

## Per-CSV header expectations (English only — v1)

GSC's interface language determines the exported header names. v1 supports English headers only. Non-English headers cause a per-CSV failure with detected headers logged: `gsc-ingestion: expected headers {X,Y,Z} for <file>; detected {Α,Β,Γ}. CSV skipped — re-export from a GSC session in English, or wait for v2 locale support.`

Header matching is **case-insensitive** and tolerates leading/trailing whitespace.

| CSV | Required headers (case-insensitive) | Optional headers | Notes |
|---|---|---|---|
| `performance/queries.csv` | `Top queries`, `Clicks`, `Impressions`, `CTR`, `Position` | — | CTR exported as `"5.4%"`-style string; parse as `float / 100`. Position as decimal. |
| `performance/pages.csv` | `Top pages`, `Clicks`, `Impressions`, `CTR`, `Position` | — | Same parsing rules. URL is in the first column. |
| `indexing/summary.csv` | `Reason`, `Pages` | `Source`, `Validation`, `Trend` | The summary is a 1-row-per-reason table; only `Reason` + `Pages` count are used. |
| `indexing/crawled-not-indexed.csv` | `URL`, `Last crawled` | — | URL list; date column optional in older exports. |
| `indexing/discovered-not-indexed.csv` | `URL`, `Last crawled` | — | Same shape. |
| `indexing/not-found-404.csv` | `URL`, `Last crawled` | — | Same shape. |
| `indexing/page-with-redirect.csv` | `URL`, `Last crawled` | — | Same shape. |
| `indexing/alternate-canonical.csv` | `URL` | `Last crawled`, `Google-selected canonical` | When present, capture the Google-chosen canonical for cross-reference. |
| `indexing/duplicate-google-chose-different.csv` | `URL` | `Last crawled`, `Google-selected canonical` | Capture Google-chosen canonical — central to the finding's evidence. |
| `indexing/blocked-4xx.csv` | `URL` | `Last crawled` | URL list. |
| `indexing/blocked-403.csv` | `URL` | `Last crawled` | URL list. |
| `indexing/soft-404.csv` | `URL`, `Last crawled` | — | Same shape. |
| `indexing/server-error-5xx.csv` | `URL`, `Last crawled` | — | Same shape. |

If a CSV has the required headers plus extra columns, ignore the extras silently. If a CSV is missing a required header, skip it with footer log + continue with the rest.

---

## Parsing rules

CSV parsing happens in the orchestrator using `Read` (no `awk`/`cut`/`sed` available — `allowed-tools` doesn't include them).

**The CSV regex pattern** must handle quoted commas (queries containing commas are common):

```
Field separator: ,
Field quoting: "..."   (double quotes; escape internal " as "")
Line terminator: \n or \r\n
Header row: first non-empty line
```

Per-row parsing pseudocode (executed by orchestrator in-context, line by line):

```
1. Read the file with Read.
2. Strip BOM if present (GSC exports often start with ﻿).
3. Split on \r?\n. First non-empty line is the header row.
4. Normalize headers (lowercase, trim) and validate against expected set.
5. For each subsequent non-empty line:
   - Walk the line character-by-character.
   - Maintain in_quote state.
   - Split fields on ',' only when not in_quote.
   - Strip outer quotes from each field; unescape "" to ".
   - Map field values to header columns.
6. For numeric columns: strip thousands separators (commas don't appear inside numbers in
   GSC exports, but be defensive — handle "1,234" → 1234 if encountered).
7. For CTR: strip trailing %, divide by 100.0. Empty/missing → null.
8. For Position: parse as float. Empty/missing → null.
9. For dates (Last crawled): keep as ISO date string; don't parse beyond that.
```

**Defensive parsing — never fail the whole skill on one bad row.** If a row can't be parsed (wrong column count, malformed quoting), skip it and accumulate to a `malformed_rows: <count>` footer note per CSV. Continue with the rest.

---

## BigQuery ingestion (primary path for Performance)

When `.seo-data/gsc/config.yaml` is present + filled + `bq` CLI works + ADC authenticated, **BigQuery replaces the CSV path for Performance only**. Indexing (the 9-reason report) remains CSV-only — Google's Bulk Data Export to BigQuery does not include indexing tables.

See `bigquery-config-template.md` for config schema, `bigquery-schema.md` for table inventory + JSON encoding rules, `bigquery-queries.md` for the 5 SQL templates (Q1-Q5).

### Activation conditions (4-state matrix interaction)

The matrix in `SKILL.md` Step 1.6 (built in Phase 2) governs which Performance source wins. BigQuery is active when **all** of:

1. `.seo-data/gsc/config.yaml` exists
2. Required keys (`project_id`, `dataset_id`, `location`) are non-empty
3. `bq --version` returns a version string (CLI installed; on Windows `bq.cmd` via gcloud SDK counts)
4. `gcloud auth application-default print-access-token` returns a non-empty token (ADC configured)

If any of these fails → fall through to CSV path (`.seo-data/gsc/performance/queries.csv` + `pages.csv`). Surface the specific blocker in the report footer.

### BQ-configured-and-failing — NO silent CSV fallback

When BQ is active per activation conditions BUT a Q1-Q5 query fails at runtime (auth revoked mid-run, schema drift, scan-cap exceeded, transient API error):

- Print the exact `bq` error to the report footer
- Skip the Performance signal entirely (digest empty for queries + pages)
- **Do NOT fall back to Perf CSVs** even if they exist. This is intentional (per locked decision 10): when BQ is configured, BQ is the Performance source. Silent fallback to a different data window or set of rows would mask the failure.
- Indexing CSVs still load and produce findings
- The 4-state matrix reads the resulting state as "Performance-missing" → footer note (matches matrix row 2: Performance-only with Performance failed = Indexing-only)

To restore Perf CSV behaviour, the user removes/empties `config.yaml`. The activation conditions then fail at step 1 and the CSV path takes over cleanly.

### Query execution

All 5 queries dispatch in a **single parallel Bash turn** (matches the existing Step 1.5/1.6 parallel-Read pattern for CSVs). Per-query Bash invocation:

```
bq query \
  --use_legacy_sql=false \
  --maximum_bytes_billed=1000000000 \
  --format=json \
  --location=<location_from_config> \
  '<SQL_with_substituted_params>'
```

Per-query failure is non-fatal — the other queries' results are still consumed. Partial-coverage is surfaced in the footer per query (e.g., "Q3 url_impressions_map: failed — traffic_weight degraded to 1.0 for all findings").

### Digest shape — byte-identical to CSV path

The translator produces digests with the **same field names + same value types + same value semantics** as the CSV parser. Sub-dim catalog code (sub-dims 10, 11, 12 in the section below) reads either path's digest identically.

**Queries digest** (replaces `performance/queries.csv` digest, consumed by sub-dim 11 `position_band_opportunity`):

```
[
  {
    query:       string,        // BQ row.query passthrough
    impressions: number,        // Number(BQ row.impressions) — INT64 returns as quoted string
    clicks:      number,        // Number(BQ row.clicks)
    ctr:         number,        // parseFloat(BQ row.ctr) — decimal 0-1, NOT percentage
    position:    number,        // parseFloat(BQ row.avg_position) — already 1-based per Q1 SQL
  },
  ... up to 50 rows, ordered by impressions desc, enforced by LIMIT 50 in Q1 SQL
]
```

**Pages digest** (replaces `performance/pages.csv` digest, consumed by sub-dim 10 `ctr_opportunity` + feeds `page_type_map` + feeds traffic-orphan computation):

```
[
  {
    url:         string,
    impressions: number,
    clicks:      number,
    ctr:         number,
    position:    number,
  },
  ... up to 50 rows, ordered by impressions desc, enforced by LIMIT 50 in Q2 SQL
]
```

**`url_impressions_map`** (replaces the URL→impressions mapping built from pages.csv; consumed by Step 6.6 `traffic_weight` computation + passed to all dispatched subagents):

```
{
  "<url>": <impressions number>,
  ...
}
// Uncapped (Q3 has no LIMIT). One row per URL with impressions >= 1.
// Translator: for each Q3 row, parsed_map[row.url] = Number(row.impressions)
```

**Traffic-orphan computation** (sub-dim 12 `traffic_orphan`): same set-diff logic as CSV path — `sitemap_urls - keys(url_impressions_map)`. Q4 exists as a documentation point; in practice the orchestrator reuses Q3's keys for the diff.

### JSON encoding rules (INT64 + FLOAT64 → string)

`bq query --format=json` quotes every numeric column. Verified with the Q1 worked example:

```json
{
  "query": "topkapi palace istanbul",
  "impressions": "1092",        // INT64 → quoted string
  "clicks": "0",                // INT64 → quoted string
  "ctr": "0.0",                 // FLOAT64 → quoted string
  "avg_position": "27.873626373626372"  // FLOAT64 → quoted string, 15-17dp precision
}
```

The translator MUST cast every numeric field to JavaScript `Number` on ingest. Arithmetic on raw row fields silently concatenates strings (`row.impressions / row.clicks` returns `"1092/0"` → `NaN`, not `Infinity`).

Display rounding: `position` and `ctr` are rounded to 2 decimal places for report rendering; full precision is preserved for arithmetic (median computation, ranking).

### Median CTR computation (Pages digest → sub-dim 10)

Same as v2 CSV path: after Q2's 50 rows are translated, compute `median_ctr` over all rows' `ctr` field. Sub-dim 10 fires on rows where `impressions >= 500 AND ctr < (median_ctr * 0.5)`.

Edge case (verified against user's Topkapi sample): if all rows have `ctr = 0` (new site, no clicks yet), `median_ctr = 0` → threshold = 0 → no row has `ctr < 0` → no findings emitted. Correct behaviour — zero-CTR site doesn't trigger false CTR-opportunity findings.

### page_type_map sources (BQ path)

Same composition as CSV path:

1. **Top-50 URLs from Q2 Pages digest** (matches CSV path's "URLs in performance/pages.csv top 50 by impressions") — NOT all URLs from Q3's uncapped url_impressions_map
2. URLs from indexing CSVs (unchanged from v2)
3. URLs from sitemap probe (Step 3.2)

Classification logic (path-pattern → page_type) is unchanged from the existing `page_type_map building` section below.

Why cap at top-50 instead of using Q3's uncapped set: the classification work is bounded, the subagent context size stays predictable, and Q3's uncapped result exists for traffic_weight lookups at finding-emission time (a different use case where misses gracefully fall through to `traffic_weight = 1.0`).

### Freshness policy (BQ-specific)

Q5 returns `latest_data_date`. Compute `days_old = (current_date - latest_data_date).days`. Thresholds match the CSV mtime policy:

| `days_old` | Behaviour |
|---|---|
| ≤ 30 | Fresh — no annotation. (Note: GSC's pipeline lags real-time by ~2 days, so a freshly-running export typically shows `days_old = 2` — still fresh.) |
| 30 - 90 | Footer warning: `BigQuery export stale — latest data_date YYYY-MM-DD (N days old). Verify export is still running in GSC Settings > Bulk data export.` |
| > 90 | Footer warning escalates: `BigQuery export significantly stale — latest data_date YYYY-MM-DD (N days old). Recommendations may not reflect recent GSC state.` |

Never blocks the run. `partition_count == 1` in Q5 output is normal for a freshly-enabled export (one day of data so far) — not an error.

### Edge cases

| Case | Behaviour |
|---|---|
| Q1 returns 0 rows (no queries pass HAVING — small site or strict filters) | Empty queries digest. Sub-dim 11 emits no findings. No error. |
| Q2 returns 0 rows (no URLs meet impression floor) | Empty pages digest. Sub-dim 10 emits no findings. `page_type_map` source #1 empty (sources #2 + #3 still feed). No error. |
| All Q2 rows have `ctr = 0` (new site) | Median = 0 → threshold = 0 → no sub-dim 10 findings emitted. Correct — no false positives. |
| Q3 returns >10k rows (large site) | Translator stores the full map; size scales to ~200KB JSON for 10k URLs. Subagent context budget can handle this; if a future site exceeds, cap with `LIMIT` in Q3 SQL (not yet needed). |
| Q5 reports `latest_data_date = NULL` (table empty) | Treat as max-staleness; surface footer warning `BigQuery dataset present but no data — wait ~2 days after enabling GSC export`. Skip Performance signal. Indexing CSVs still load. |
| Anonymized-query rows leak through (filter logic error) | Defense-in-depth: translator also drops rows where `query` is empty string. Should never happen given Q1's WHERE filter, but cheap to enforce. |

### Failure mode summary

| Stage | Failure | Effect |
|---|---|---|
| Pre-query | `bq` not installed | Fall through to CSV path (activation condition 3 fails) |
| Pre-query | ADC not authenticated | Fall through to CSV path (activation condition 4 fails) |
| Pre-query | `config.yaml` keys empty | Fall through to CSV path (activation condition 2 fails) |
| Query runtime | `Access Denied` on dataset | Print error + skip Performance, no silent CSV fallback |
| Query runtime | Schema drift (column not found) | Print error + skip Performance + footer note pointing to `bigquery-schema.md` |
| Query runtime | Scan-cap exceeded (>1 GB) | Print error + suggest reducing `lookback_days` + skip Performance |
| Query runtime | Transient API error (timeout, 5xx) | Print error + skip Performance (don't retry — re-run the skill) |
| Per-query partial | Q1 fails but Q2-Q5 succeed | Empty queries digest + footer note. Pages + url_impressions_map still produced. |

All failure modes are non-fatal to the run — `/seo-review` always produces a score + report.

---

## API ingestion (canonical path for Performance + Indexing)

When `.seo-data/gsc/config.yaml` has `site_url` filled + `gcloud` SDK installed + ADC authenticated + active API probe succeeds, **the Search Console API replaces both BigQuery (Performance) and indexing CSVs**. Single auth surface (gcloud ADC), three endpoints, both Performance + Indexing covered.

Activation precedence vs other paths: **API > BigQuery > CSV** for Performance signal; **API > CSV** for Indexing signal. When API is active, BQ Performance queries are not fired and indexing CSVs are not parsed (the API supersedes both).

See `gsc-api-schema.md` for endpoint inventory + auth + quota model + `coverageState` + `pageFetchState` enums. See `gsc-api-queries.md` for the 3 parametrized `curl` templates + URL Inspection selection algorithm + `coverageState`+`pageFetchState` → 9-reason lookup table.

> **Worked example status (Phase 0 deferred):** The API response shapes documented below are taken from Google's published API reference (https://developers.google.com/webmaster-tools/v1/searchanalytics + https://developers.google.com/webmaster-tools/v1/urlInspection). Live-verification against a real GSC property is deferred to Phase 4 real-world dogfood (requires gcloud SDK install on the user's machine). All documented shapes are stable per Google's public API contract.

### Activation conditions (4-state matrix interaction)

The matrix in `SKILL.md` Step 1.6 governs which path wins. The API path is active when **all** of:

1. `.seo-data/gsc/config.yaml` exists
2. `config.yaml.site_url` is non-empty (the property identifier — `sc-domain:example.com` for Domain properties, `https://example.com/` for URL-prefix properties)
3. `gcloud --version` returns (gcloud SDK installed; on Windows ships as `gcloud.cmd`)
4. `gcloud auth application-default print-access-token` returns a non-empty token (ADC configured)
5. `curl GET https://www.googleapis.com/webmasters/v3/sites` with the ADC token returns HTTP 200 + a JSON body containing a `siteEntry` array
6. The configured `site_url` appears in the returned list's `siteEntry[*].siteUrl` (per Plan-agent B11 — catches "ADC valid + GSC access exists but for a different property than configured")

If any of these fails → fall through to BQ path (if BQ keys configured), then CSV path, then heuristic-only. Surface the specific blocker in the report footer.

**OAuth scope note (Plan-agent B7):** ADC tokens issued by `gcloud auth application-default login` without explicit scopes default to `cloud-platform`. Search Console API often accepts cloud-platform-scoped tokens but this is undocumented behavior. The setup walkthrough instructs:

```
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/webmasters.readonly,https://www.googleapis.com/auth/cloud-platform
```

The active probe (condition 5) is what catches scope insufficiency at runtime — token returns 401 from `/sites` → footer surfaces the `--scopes` remediation.

**Quota project (Plan-agent B10):** After login, users should also run `gcloud auth application-default set-quota-project <project-id>`. Without this, API calls succeed but quota gets billed to a default consumer project that may rate-limit harder. Documented in `gsc-setup-readme-template.md`.

### API-configured-and-failing — NO silent CSV/BQ fallback

When API is active per activation conditions BUT a runtime call fails (auth revoked mid-run, scope insufficiency surfacing after probe, quota exhausted, transient API error):

- Print the exact API error to the report footer (parse on `error.code: 429` + `error.status: "RESOURCE_EXHAUSTED"` per Plan-agent B4)
- Skip the affected signal entirely. For Performance: digest empty. For Indexing: inspected URLs partial.
- **Do NOT silently fall back to BQ or CSV path** for the same signal. When API is configured, API is the source. Silent fallback would mask the failure across a different data window.
- The 4-state matrix reads the resulting state as the relevant signal missing → footer note

To restore BQ Performance behaviour, user removes `site_url` from `config.yaml`. Activation condition 2 then fails and BQ takes over cleanly.

### Query execution

#### Search Analytics (3 parallel calls per Plan-agent S4 — Q4 + Q5 dropped)

All 3 queries dispatch in a **single parallel Bash turn**. Per-query invocation:

```
curl -s -X POST \
  -H "Authorization: Bearer <ADC_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '<JSON_BODY>' \
  "https://www.googleapis.com/webmasters/v3/sites/<SITE_URL_ENCODED>/searchAnalytics/query"
```

Where `<SITE_URL_ENCODED>` is the `site_url` with `:` → `%3A` and `/` → `%2F` (per Plan-agent B5 — `curl --data-urlencode` only handles request body, not path params):
- `sc-domain:example.com` → `sc-domain%3Aexample.com`
- `https://example.com/` → `https%3A%2F%2Fexample.com%2F`

The orchestrator builds the encoded URL in-context before the curl call.

#### URL Inspection (N parallel calls — N ≤ 100/run per Plan-agent S3)

```
curl -s -X POST \
  -H "Authorization: Bearer <ADC_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"inspectionUrl":"<URL>","siteUrl":"<SITE_URL>"}' \
  "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
```

Note: URL Inspection uses a **different base host** (`searchconsole.googleapis.com/v1`) than Search Analytics (`www.googleapis.com/webmasters/v3`). Same OAuth scope; same ADC token. Per Plan-agent B2.

#### Token caching (Plan-agent S2)

**One** `gcloud auth application-default print-access-token` call per run, at the start of Turn 2 (Step 1.6.6). Token is cached in shared context and reused across all curl calls. ADC tokens have a 1-hour TTL; a single Step 1.6 dispatch finishes in seconds.

#### Per-query failure handling

A single failed call is non-fatal — other calls' results are still consumed. Failure mode codes:
- HTTP 401 → ADC scope issue (per B7) — surface `--scopes` remediation
- HTTP 403 → property ACL mismatch — user lacks Search Console access on the configured `site_url`
- HTTP 404 → `site_url` not registered in GSC OR encoding error
- HTTP 429 + `error.status: "RESOURCE_EXHAUSTED"` → quota exhausted (graceful degrade per decision 10)
- HTTP 5xx → transient — print error, skip signal, don't retry

### Digest shape — byte-identical to CSV + BQ paths

The translator produces digests with **identical field names + types + semantics** as the CSV parser and BQ translator. Subagents (12 sub-dim catalog) read API-sourced digests indistinguishably from other sources.

#### Performance digests

**Queries digest** (Q1 — replaces v2's `performance/queries.csv` + v3's BQ Q1):

API call:
```json
{
  "startDate": "<CURRENT_DATE - lookback_days>",
  "endDate": "<CURRENT_DATE>",
  "dimensions": ["query"],
  "rowLimit": 25000,
  "type": "web"
}
```

API response:
```json
{
  "rows": [
    {"keys": ["topkapi palace istanbul"], "clicks": 0, "impressions": 1092, "ctr": 0.0, "position": 27.87}
  ],
  "responseAggregationType": "byProperty"
}
```

Translation:

| API row field | Digest field | Coercion |
|---|---|---|
| `keys[0]` | `query` | passthrough (STRING) |
| `impressions` | `impressions` | passthrough (already JSON number — no cast needed) |
| `clicks` | `clicks` | passthrough (already JSON number) |
| `ctr` | `ctr` | passthrough (already decimal 0-1) |
| `position` | `position` | passthrough (already 1-based decimal) |

**Client-side filter** (the API doesn't support `position`-range filter via `dimensionFilterGroups`):

After receiving response, apply:
- `impressions >= 100` (HAVING-equivalent)
- `position BETWEEN 5.0 AND 20.0` (position-band)
- Sort descending by `impressions`
- Take top 50

**Pages digest** (Q2 — replaces `performance/pages.csv` + BQ Q2):

API call: same shape with `dimensions: ["page"]`, `rowLimit: 25000`. Client-side filter: `impressions >= 10`, top 50 by impressions desc.

**url_impressions_map** (Q3 — replaces BQ Q3):

API call: same shape with `dimensions: ["page"]`, `rowLimit: 25000`. **No client-side cap** — all returned rows go into the map.

**Plan-agent B1 — silent truncation on >25k URLs**: the API caps a single call at `rowLimit: 25000`. For sites with >25k URLs in the lookback window, `url_impressions_map` truncates at 25k. BQ remains uncapped for large sites. Affected behavior: `traffic_weight` on findings whose URL is not in the top-25k falls through to `1.0` (defensible — same as no-GSC behavior).

#### Indexing digests (from URL Inspection — replaces 11 indexing CSVs)

The 11 indexing CSVs (sub-dims 2-9) get rebuilt from per-URL inspection results. **Cluster into the existing 9-reason catalog** via the `coverageState` + `pageFetchState` joint lookup table.

URL Inspection response (per Google API reference):

```json
{
  "inspectionResult": {
    "inspectionResultLink": "https://search.google.com/search-console/inspect?...",
    "indexStatusResult": {
      "verdict": "PASS | PARTIAL | FAIL | NEUTRAL",
      "coverageState": "<one of ~50 enum strings, see gsc-api-schema.md>",
      "robotsTxtState": "ALLOWED | DISALLOWED",
      "indexingState": "INDEXING_ALLOWED | BLOCKED_BY_META_TAG | BLOCKED_BY_HTTP_HEADER | BLOCKED_BY_ROBOTS_TXT",
      "lastCrawlTime": "2026-05-13T10:30:00Z",
      "pageFetchState": "SUCCESSFUL | SOFT_404 | BLOCKED_ROBOTS_TXT | NOT_FOUND | ACCESS_DENIED | SERVER_ERROR | REDIRECT_ERROR | ACCESS_FORBIDDEN | BLOCKED_4XX",
      "googleCanonical": "<URL>",
      "userCanonical": "<URL>",
      "sitemap": ["<URL>"],
      "referringUrls": ["<URL>"],
      "crawledAs": "DESKTOP | MOBILE"
    },
    "mobileUsabilityResult": { "verdict": "...", "issues": [] },
    "richResultsResult": { "verdict": "...", "detectedItems": [] }
  }
}
```

**`coverageState` + `pageFetchState` → 9-reason lookup table** (Plan-agent B8 — full table in `gsc-api-queries.md`; summary below):

| `coverageState` | `pageFetchState` | 9-reason sub-dim |
|---|---|---|
| "Submitted and indexed" | SUCCESSFUL | (no finding — healthy state) |
| "Indexed, not submitted in sitemap" | SUCCESSFUL | (info-only — surface in footer) |
| "Indexed, though blocked by robots.txt" | * | (info — robots.txt conflict) |
| "Crawled - currently not indexed" | SUCCESSFUL | sub-dim 2 `crawled_not_indexed` |
| "Discovered - currently not indexed" | * | sub-dim 3 `discovered_not_indexed` |
| "Not found (404)" | NOT_FOUND | sub-dim 4 `not_found_404` |
| "Submitted URL not found (404)" | NOT_FOUND | sub-dim 4 `not_found_404` (variant) |
| "Page with redirect" | REDIRECT_ERROR | sub-dim 5 `redirect_hygiene` |
| "Alternate page with proper canonical tag" | * | sub-dim 7 `blocked_access` (alternate-canonical variant) |
| "Duplicate, Google chose different canonical than user" | * | sub-dim 6 `canonical_conflict` |
| "Duplicate without user-selected canonical" | * | sub-dim 6 `canonical_conflict` (variant) |
| "Excluded by 'noindex' tag" | * | sub-dim 7 `blocked_access` (intentional) |
| "Blocked by robots.txt" | BLOCKED_ROBOTS_TXT | sub-dim 7 `blocked_access` |
| "Blocked due to access forbidden (403)" | ACCESS_FORBIDDEN | sub-dim 7 `blocked_access` (403 variant) |
| "Blocked due to other 4xx issue" | BLOCKED_4XX | sub-dim 7 `blocked_access` (4xx variant) |
| "Server error (5xx)" | SERVER_ERROR | sub-dim 9 `server_errors` |
| "Soft 404" | SOFT_404 | sub-dim 8 `soft_404` |
| "URL is unknown to Google" | * | (no finding — Google hasn't seen the URL) |
| (any unmapped `coverageState`) | * | "Other" bucket — info-only footer note |

#### Indexing cluster aggregation

After all inspected URLs are classified via the lookup table, the orchestrator groups them by sub-dim and emits findings using the existing catalog (sub-dims 2-9). Each cluster's:
- `total_count` = number of inspected URLs matching that sub-dim
- `affected_urls` = top 10 by `lastCrawlTime` descending (matches CSV path)
- `evidence` carries per-URL diagnostic detail (Plan-agent B9):
  - `evidence.google_canonical` / `evidence.user_canonical` / `evidence.crawled_as` populated from inspection response when sub-dim 6 (`canonical_conflict`)
  - `evidence.last_crawl_time` for time-sensitive findings
  - `evidence.indexing_state` for blocked findings

**Critical**: `total_count` from API inspection is **inspected-URL-count**, NOT site-wide truth. If the skill inspected 100 URLs and 12 had `coverageState: "Crawled - currently not indexed"`, the finding says "12 inspected pages are crawled-not-indexed". This is more conservative than CSV path (which gives site-wide count). Footer notes the inspection budget explicitly so the user knows the scale.

### URL Inspection budget + selection algorithm

Per Plan-agent S3 — hard target **100 URLs/run**, split:

| Source | Count | Rationale |
|---|---|---|
| Top 50 from `url_impressions_map` (highest impressions) | 50 | Cover the URLs that actually matter for traffic. |
| Sitemap probe failures (4xx/5xx URLs from Step 3.2) | 30 | High-signal indexing failures Google sees as broken. |
| Git-changed paths (35-day window) resolved to URLs via `page_type_map` | 20 | Recently-touched URLs may have indexing changes pending. Plan-agent B6: only candidates that resolve via `page_type_map` heuristics OR appear in `url_impressions_map` — git emits paths, not URLs. |

Dedup across the three sources (a URL in both Performance top-50 and recent git changes counts once). Hard cap **100 URLs total** before dispatching inspection batch. Well under the 2,000/day per-property quota.

### Quota handling (Plan-agent B3)

- **Search Analytics**: 1,200 QPM per Search Console account. With 3 calls/run, won't hit limit.
- **URL Inspection**: 2,000/day per property + 600/min per project. The 100-URL budget per run stays well under both.

Mid-run quota exhaustion (rare with the 100-URL cap): per decision 10, graceful degrade. Stop sending inspection calls, surface in footer:

```
URL Inspection: 73/100 succeeded, 27 skipped (quota exhausted). Re-run tomorrow for remaining.
```

Indexing findings emit from the inspected subset only. Performance signal unaffected (uses Search Analytics which has separate quota).

### page_type_map sources (API path)

Same composition as CSV/BQ path:

1. **Top-50 URLs from Q2 Pages digest** (NOT Q3's uncapped url_impressions_map)
2. **Inspected URLs** from URL Inspection batch (replaces "URLs from indexing CSVs")
3. **Sitemap probe URLs** (Step 3.2)

Classification logic unchanged.

### Freshness policy (API-specific)

No `MAX(data_date)` equivalent — the API returns the live view of GSC's pipeline. Footer note:

```
GSC API path: real-time view of GSC's pipeline (typically ~2-day lag from real-world events).
```

Per Plan-agent S4 — Q5 (freshness probe) dropped entirely for API path; static footer line suffices.

### Edge cases

| Case | Behaviour |
|---|---|
| `searchanalytics.query` returns 0 rows (small site or no traffic in window) | Empty Performance digests. Sub-dims 10-12 emit no findings. No error. |
| `urlInspection.index.inspect` returns 404 for a candidate URL | URL not yet known to Google. Skip from cluster (no sub-dim assignment). Track as "URLs unknown to Google: N" in footer. |
| All inspected URLs return `coverageState: "Submitted and indexed"` | No indexing findings emitted. Healthy state — surface as footer "All N inspected pages are indexed cleanly". |
| `coverageState` returns an unmapped value (Google added a new enum) | Use "Other" bucket from lookup table. Footer note: "Unmapped coverageState: <value> on N URLs — update gsc-api-queries.md lookup table." |
| URL Inspection budget = 0 (no candidates from any source) | Skip URL Inspection batch entirely. No indexing findings. Footer note. |
| ADC token expires mid-run (>1 hour wall time) | Won't happen — Step 1.6 finishes in seconds. If it ever did: 401 on subsequent call → graceful degrade per decision 10. |
| `site_url` in config but not verified by user's Google account | Active probe (activation condition 6) fails → fall through. Footer surfaces "site_url not in your verified properties list". |
| Encoding error (special chars in URL) | Use `[uri]::EscapeDataString` equivalent in-context. Test in Phase 4 dogfood. |

### Failure mode summary

| Stage | Failure | Effect |
|---|---|---|
| Pre-query | `gcloud` not installed | Fall through to BQ/CSV path (activation condition 3 fails) |
| Pre-query | ADC not authenticated | Fall through (activation condition 4 fails); surface `gcloud auth application-default login` remediation |
| Pre-query | `site_url` empty in config.yaml | Fall through (activation condition 2 fails) |
| Pre-query | Active probe returns 401 | Surface `--scopes` remediation; fall through |
| Pre-query | Active probe returns 200 but `site_url` not in list | Surface "verify site_url is owned by your Google account"; fall through |
| Query runtime | `searchanalytics.query` returns 429 | Print error + skip Performance, no silent BQ/CSV fallback |
| Query runtime | `urlInspection` returns 429 mid-batch | Graceful degrade per decision 10: surface count succeeded/skipped |
| Query runtime | Single `urlInspection` returns 404 | URL unknown to Google — exclude from cluster, footer count |
| Per-query partial | Q1 fails but Q2 + Q3 succeed | Empty queries digest + footer note. Pages + url_impressions_map still produced. |

All failure modes are non-fatal — `/seo-review` always produces a score + report.

---

## Digest caps (per CSV)

Each CSV's parsed rows are reduced to a **digest** of at most **50 rows** before being passed to the `seo-gsc-insights` subagent. This keeps prompt size bounded.

| CSV | Sort key | Direction | Cap |
|---|---|---|---|
| `performance/queries.csv` | `impressions` | desc | 50 |
| `performance/pages.csv` | `impressions` | desc | 50 |
| `indexing/summary.csv` | n/a (full table, max 11 rows) | — | unbounded |
| `indexing/<reason>.csv` | `last_crawled` | desc (most-recent first) | 50 |

For indexing CSVs, the **count** of rows in the source CSV is preserved as `total_count` even if the digest is capped — that's what feeds the "1,146 crawled-not-indexed pages" cluster headline.

---

## page_type_map building

The orchestrator builds a single `page_type_map: {url → page_type}` once in Step 1.6 (replacing the duplication of detection logic across `geo-generative` and `seo-gsc-insights`).

**Sources of URLs to classify:**
- All URLs in `performance/pages.csv` (top 50 by impressions)
- All URLs in any `indexing/*.csv` (capped per file as above)
- All URLs from sitemap.xml entries (Step 3.2 probe results)

**Classification logic** mirrors `scan-geo.md:25-37` page-type heuristics. For each URL, derive a `page_type` from path patterns:

| URL path pattern | page_type |
|---|---|
| `/` exactly | `homepage` |
| `/blog/*`, `/posts/*`, `/news/*`, `/articles/*` | `article` |
| `/products/*`, `/product/*`, `/shop/*` | `product` |
| `*faq*`, `*frequently-asked*` | `faq` |
| `*how-to*`, `*tutorial*`, `*guide*` | `howto` |
| `*recipe*` | `recipe` |
| `*event*` | `event` |
| `/author/*`, `/team/*`, `/about/*` | `person` or `about` |
| `/docs/*`, `/documentation/*`, `/api/*` | `documentation` |
| `/category/*`, `/tag/*`, `/topic/*` | `taxonomy` |
| anything else | `unknown` |

The map is passed to **all dispatched subagents** (3 or 4 depending on `gsc_mode`) in shared context — `seo-gsc-insights` (primary consumer, only dispatched when enabled), `geo-generative` (uses it to short-circuit its own page-type detection), and the other 2 (informational, helps prioritize).

---

## Setup banner — Path 1 (API) / Path 1b (BQ) / Path 2 (CSV) (one-time, sentinel-gated)

When the orchestrator runs `/seo-review` and **no GSC data is detected** (no CSVs in `.seo-data/gsc/` AND no `config.yaml` — i.e., 4-state matrix resolves to heuristic-only):

1. **Sentinel check.** Look for `.seo-data/.gsc-banner-shown`. If it exists → suppress the banner; nothing to do.
2. **Print the banner** (text below). Then create the sentinel:
   - If `.seo-data/` doesn't exist yet, create it (single `Write` of `.seo-data/.gsc-banner-shown` with empty content — the parent directory is created implicitly on most platforms; if it errors, the banner will print again next run, which is acceptable degraded behavior).
   - If `.seo-data/` already exists (e.g., from another tool), just `Write` the sentinel file.
3. The sentinel is itself gitignored via the auto-`.gitignore` block — never committed.

**Banner content** (printed before Section 1 of the report):

```
─────────────────────────────────────────────────────────────────────────────
GSC INTEGRATION AVAILABLE — Make /seo-review traffic-aware

This run used static signals only. /seo-review can incorporate Google Search
Console data to surface traffic-prioritized findings (which pages get
impressions, which queries you rank for at position 5-20, which pages Google
considers crawled-but-not-indexed).

Three paths are supported. Pick one (Path 1 recommended for new users):

╭─ Path 1 (RECOMMENDED): Search Console API ──────────────────────────────╮
│ Covers Performance + Indexing in ONE auth surface. Simplest setup.       │
│                                                                          │
│ 1. Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install   │
│ 2. Run (one-time, opens browser for OAuth):                              │
│      gcloud auth application-default login \                             │
│        --scopes=https://www.googleapis.com/auth/webmasters.readonly,\    │
│                 https://www.googleapis.com/auth/cloud-platform           │
│      gcloud auth application-default set-quota-project <your-gcp-project>│
│ 3. Create .seo-data/gsc/config.yaml with your GSC property URL:          │
│      site_url: sc-domain:example.com   # or "https://example.com/"       │
│ 4. Re-run /seo-review.                                                   │
│                                                                          │
│ The skill calls Search Analytics (Performance) + URL Inspection          │
│ (per-URL indexing diagnostics) via the API. No CSVs needed.              │
╰──────────────────────────────────────────────────────────────────────────╯

╭─ Path 1b (ALTERNATIVE for unlimited history): BigQuery Bulk Export ─────╮
│ Use this when you want unlimited Performance history (vs API's 16-mo).   │
│ Indexing still uses CSVs (BigQuery export doesn't include indexing).     │
│                                                                          │
│ 1. GSC > Settings > Bulk data export > Configure → destination GCP       │
│    project + dataset name (conventional: "searchconsole"). Wait ~2 days. │
│ 2. Install gcloud SDK + same auth setup as Path 1.                       │
│ 3. Create .seo-data/gsc/config.yaml:                                     │
│      project_id: <your-gcp-project>                                      │
│      dataset_id: searchconsole                                           │
│      location: US                                                        │
│ 4. ALSO export indexing CSVs (Path 2, indexing-only).                    │
│ 5. Re-run /seo-review.                                                   │
╰──────────────────────────────────────────────────────────────────────────╯

╭─ Path 2 (FALLBACK): CSV exports ────────────────────────────────────────╮
│ Universal fallback — no gcloud SDK install required. Slower data         │
│ (manual export per run). REQUIRED for Indexing when using Path 1b.       │
│                                                                          │
│ 1. GSC > Indexing > Pages > Export the "Why pages aren't indexed" table  │
│    + click each reason row → Export → CSV (up to 9 reason CSVs)          │
│ 2. (Optional, if not using API or BigQuery) GSC > Performance >          │
│    Search results > Queries tab → Export → CSV; Pages tab → Export → CSV │
│ 3. Create .seo-data/gsc/{performance,indexing}/ in this repo.            │
│ 4. Drop each CSV into the matching subfolder with canonical filenames    │
│    (see .seo-data/gsc/README.md once the folder exists).                 │
│ 5. Re-run /seo-review.                                                   │
╰──────────────────────────────────────────────────────────────────────────╯

This folder will be auto-gitignored (search queries can include brand-internal
data — privacy default). You don't need to commit anything.

Score will stay /100 regardless of path — GSC enriches the *recommendations*,
not the score, so docs/seo-history.md stays comparable across runs.

(This banner shows once per project. Touch .seo-data/.gsc-banner-shown to
silence it manually.)
─────────────────────────────────────────────────────────────────────────────
```

Banner skipped silently when `.seo-data/gsc/` exists (any CSV, config.yaml, or sentinel present).

---

## .gitignore auto-append

When the orchestrator first detects `.seo-data/gsc/` (i.e., at least one CSV present), append to project-root `.gitignore` using a sentinel-marked block for idempotency:

```
# /seo-review managed — do not edit between markers
.seo-data/gsc/
.seo-data/.gsc-banner-shown
# /end /seo-review managed
```

**Idempotency check:** before appending, Grep `.gitignore` for the start marker (`# /seo-review managed`). If present, skip — block already exists.

**`.gitignore` doesn't exist yet:** create it with the block above as the only content.

The orchestrator prints a one-line notice on first append: `Added .seo-data/gsc/ to .gitignore (sentinel-marked block).` Subsequent runs are silent.

**Why ignore the sentinel file too:** the banner sentinel `.seo-data/.gsc-banner-shown` is per-machine. Committing it would suppress the banner for other team members on their first clone.

**Why not edit the user's existing .gitignore content:** the sentinel block is append-only. The orchestrator never modifies anything outside the markers. Users editing the block manually (e.g., adding `!.seo-data/gsc/notes.md` to selectively commit) is their call — the orchestrator's idempotency check only verifies the start marker is present, not its exact contents.

---

## Freshness policy

For each parsed CSV, capture `mtime`. Calculate `days_old = (today - mtime).days`.

| days_old | Behavior |
|---|---|
| < 30 | No warning; treated as fresh. |
| 30 - 90 | Footer warning: `freshness: <file> is <N> days old — re-export from GSC for fresher signal`. Run continues. |
| > 90 | Footer warning escalates to `⚠ freshness: <file> is <N> days old — over 90 days, data may be misleading`. Run still continues — never block. |

Aggregate freshness summary in the footer:

```
GSC CSVs: 7 present (queries, pages, 5/9 indexing reasons).
Freshness: 6 fresh (<30d), 1 stale (queries.csv at 47d ⚠ — consider re-export).
```

---

## Finding-type catalog (12 sub-dims)

Each CSV produces 0+ findings. Below is the per-CSV / per-sub-dim spec. All findings have `source: "gsc"`, `score_impact: 0` (enforced orchestrator-side in Step 6).

### 1. `indexing_coverage` (from `indexing/summary.csv`)

**Trigger:** summary.csv is parsed AND has ≥1 row. If summary.csv is present but empty (0 rows), skip the finding — there's nothing to report and the non-index rate divide-by-zero is undefined.

**Emit one finding total** — a headline informational finding:

- `severity`: `medium` if non-index rate >50%, `low` otherwise
- `certainty`: `1.0`
- `effort_estimate`: `medium` (umbrella for sub-cluster work)
- `title`: e.g., `"GSC reports <X> pages not indexed out of <Y> known (<Z>% non-index rate)"`
- `recommended_action`: `"See per-reason breakdown below — each indexing reason has a different remediation path."`
- `evidence`: full reason→count table from summary.csv

### 2. `crawled_not_indexed` (from `indexing/crawled-not-indexed.csv`)

**Trigger:** ≥1 row in the file.

**Cluster all rows into one finding** (not one per URL):

- `severity`: `medium` if count <100; `high` if ≥100
- `certainty`: `0.9` (Google's call, usually accurate)
- `effort_estimate`: `large` (content-quality work)
- `affected_urls`: top 10 by `last_crawled` descending
- `title`: `"<N> pages crawled by Google but not indexed (content quality signal)"`
- `recommended_action`: `"Audit content quality and E-E-A-T signals. Common causes: duplicate content, thin content, low authority signal, soft-quality issues. Sample affected URLs: <list>. Pick 3-5 representative URLs, compare against top-ranking competitors, identify what's missing (length, originality, expert authorship, citations)."`

### 3. `discovered_not_indexed` (from `indexing/discovered-not-indexed.csv`)

**Trigger:** ≥1 row.

**Cluster into one finding:**

- `severity`: `medium` if count <50; `high` if ≥50
- `certainty`: `0.9`
- `effort_estimate`: `medium`
- `affected_urls`: top 10
- `title`: `"<N> pages discovered but not crawled (crawl budget / internal linking signal)"`
- `recommended_action`: `"Google found these URLs but hasn't crawled them — usually crawl-budget or low-priority signal. Add internal links from high-authority pages, ensure they're in sitemap.xml, request indexing manually for the most important ones."`

### 4. `not_found_404` (from `indexing/not-found-404.csv`)

**Trigger:** ≥1 row.

**Cluster + routing-rename match** (this is the bulk-redirect detection):

1. Parse all URLs, derive path patterns (e.g., `/blog/2023/post-1`, `/blog/2023/post-2` → cluster `/blog/2023/*`).
2. Cross-reference with Step 1.5 git-changes digest: any commits in the 35-day window touching the source paths that *generated* these URLs?
3. If routing-rename match found: emit a single bulk-cluster finding with **the routing-rename signal in evidence**.

- `severity`: `high` (broken URLs at Google's view dilute crawl budget)
- `certainty`: `1.0` (Google saw them as 404)
- `effort_estimate`: `small` (bulk 301 redirect or sitemap cleanup)
- `affected_urls`: top 10 (or all if ≤10)
- `title`: `"<N> URLs return 404 at Google's view"`
- `evidence`: includes `"Routing rename in window: <commit-msg> on YYYY-MM-DD touching <paths>"` when detected
- `recommended_action`: when routing-rename detected: `"Bulk 301 redirects mapping <old-pattern> → <new-pattern> in <framework-config-file>. Plus remove 404 entries from sitemap.xml. Confirm the mapping is 1:1 before bulk-applying."` Otherwise: `"Either restore the affected pages or remove these entries from sitemap.xml."`

### 5. `redirect_hygiene` (from `indexing/page-with-redirect.csv`)

**Trigger:** ≥1 row.

**Cluster into one finding:**

- `severity`: `medium`
- `certainty`: `1.0`
- `effort_estimate`: `small`
- `title`: `"<N> sitemap URLs point to redirect destinations (sitemap hygiene)"`
- `recommended_action`: `"Replace these sitemap entries with their final destinations. Redirect-chain URLs in sitemap waste crawl budget. Sample: <list>."`

### 6. `canonical_conflict` (from `indexing/duplicate-google-chose-different.csv`)

**Trigger:** ≥1 row.

**Per-URL findings** (cap 5), or cluster if N >5:

- `severity`: `high`
- `certainty`: `0.85` (canonical handling is nuanced — sometimes Google's choice is fine)
- `effort_estimate`: `medium` (requires per-URL investigation)
- `title`: per-URL: `"Google chose different canonical for <URL>: <google-canonical>"`. Cluster: `"<N> URLs where Google rejected the declared canonical"`.
- `recommended_action`: `"Compare your declared <link rel='canonical'> against Google's selected canonical for each URL. Common causes: hreflang misconfig, duplicate-content cluster, soft-duplicate variations (trailing slash, params). Use the URL Inspection tool in GSC to see Google's full reasoning per URL."`

### 7. `blocked_access` (from `blocked-4xx.csv` + `blocked-403.csv` + `alternate-canonical.csv`)

**Trigger:** ≥1 row in any of these. Usually intentional.

**One finding per source CSV** (max 3):

- `severity`: `low`
- `certainty`: `0.6`
- `effort_estimate`: `small`
- `title`: e.g., `"<N> URLs blocked by 403 (likely intentional)"`
- `recommended_action`: `"Verify these are intentionally blocked. If any should be public, fix the access rule. Otherwise no action needed — these URLs are correctly excluded from Google's index."`

### 8. `soft_404` (from `indexing/soft-404.csv`)

**Trigger:** ≥1 row.

**Cluster into one finding:**

- `severity`: `medium`
- `certainty`: `0.9`
- `effort_estimate`: `medium`
- `title`: `"<N> URLs return 200 but Google detected empty/error content (soft 404)"`
- `recommended_action`: `"Visit each URL — pages may load with stub/placeholder/error content that returns 200. Fix the rendering or set proper 404 status. Sample: <list>."`

### 9. `server_errors` (from `indexing/server-error-5xx.csv`)

**Trigger:** ≥1 row.

**Cluster + always high-priority:**

- `severity`: `high`
- `certainty`: `1.0`
- `effort_estimate`: `medium` (depends on cause)
- `title`: `"<N> URLs returned 5xx errors when Google crawled (site reliability signal)"`
- `recommended_action`: `"Investigate server logs around the last-crawled timestamps. Common causes: deployment-window errors, timeouts on heavy pages, dependency outages. Sample: <list>."`

### 10. `ctr_opportunity` (from `performance/pages.csv`)

**Trigger:** rows with `impressions ≥ 500` AND `ctr < (median_ctr_in_file × 0.5)`.

**Per-URL findings** (cap 5):

- `severity`: `medium`
- `certainty`: `0.7` (CTR is affected by many factors; title/meta is a common one)
- `effort_estimate`: `small` (rewrite title + meta)
- `impressions`, `clicks`, `ctr` populated
- `title`: `"CTR opportunity on <URL> (<X>K impressions, <Y>% CTR vs <Z>% median)"`
- `recommended_action`: `"Rewrite <title> + <meta name='description'> to be more compelling. Test against top SERP results for the page's primary queries. Target CTR: at least median (<Z>%)."`

### 11. `position_band_opportunity` (from `performance/queries.csv`)

**Trigger:** rows with `position` between 5.0 and 20.0 inclusive AND `impressions ≥ 100`.

**Per-query findings** (cap 5):

- `severity`: `medium`
- `certainty`: `0.7`
- `effort_estimate`: `medium` (on-page optimization)
- `impressions`, `avg_position`, `clicks` populated
- `title`: `"Query '<query>' ranks at position <X.Y> with <N> impressions — position-band opportunity"`
- `recommended_action`: `"Identify which page ranks for this query (use GSC's Pages tab filtered by query). Improve on-page signals: H1/title alignment, content depth, internal links from related pages, schema markup. Moving from position 10 → 5 typically 3-5x's clicks."`

### 12. `traffic_orphan` (from `performance/pages.csv` ∩ sitemap)

**Trigger:** URLs in sitemap.xml that **do not appear** in pages.csv (i.e., 0 impressions in the GSC data window).

**Cluster into one finding** (only if count ≥5 — fewer is too noisy):

- `severity`: `low`
- `certainty`: `0.6` (some pages legitimately get 0 impressions but should stay)
- `effort_estimate`: `medium` (per-page audit)
- `affected_urls`: top 10 by some criterion (alphabetical for now; could use sitemap `<priority>` later)
- `title`: `"<N> sitemap URLs received 0 impressions in GSC's data window (traffic orphans)"`
- `recommended_action`: `"Audit these pages — they're indexed (in sitemap) but no one's finding them. Options: improve content + internal linking, remove from sitemap if they shouldn't rank, or accept as legitimate low-traffic pages (e.g., archived posts). Sample: <list>."`

---

## Output to shared context

After Step 1.6 completes, the orchestrator passes a structured GSC block to all dispatched subagents (3 when `gsc_mode: disabled`, 4 when enabled) as part of the Step 5 base shared-context. **See `SKILL.md` Step 1.6.7 for the canonical block format** — it's defined once there to avoid drift.

The `seo-gsc-insights` subagent is the primary consumer (uses everything). The other 3 subagents use `url_impressions_map` for traffic_weight when ranking their own findings; the rest is informational.

---

## Hard rules (orchestrator side)

- **Never block runs.** Every failure mode (missing folder, missing file, missing header, malformed row, stale freshness) logs to footer and continues.
- **Never modify .gitignore outside the sentinel block.** Idempotency check via start-marker Grep.
- **CSV parsing is single-pass.** Don't re-read files; cache parsed digest in shared context.
- **No HTTP.** All work is local file reads + git log + Grep.
- **Digest cap is 50 rows per CSV** — never bypass.
- **Score impact stays heuristic.** GSC findings carry `score_impact: 0` (see `rubric.md` for the orchestrator-side enforcement).
