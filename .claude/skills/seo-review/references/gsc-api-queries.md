# Google Search Console API Queries — Canonical Templates

Loaded by the orchestrator (Step 1.6) when the Search Console API is the active Performance + Indexing path. Provides:

- 3 parametrized `curl` templates for `searchanalytics.query` (Q1 queries digest, Q2 pages digest, Q3 `url_impressions_map`)
- 1 parametrized `curl` template for `urlInspection.index.inspect` (one URL per call)
- URL Inspection **selection algorithm** for the 100-URL/run budget
- `coverageState` + `pageFetchState` → 9-reason **lookup table** (full)
- Quota degradation rules

For endpoint inventory, auth, quota model, and enum reference, see `gsc-api-schema.md`. For digest field translation and integration with the 12 sub-dim catalog, see `gsc-ingestion.md` "API ingestion" subsection.


---

## Invocation contract

### Token acquisition (once per run, cached)

At the start of Step 1.6.6 Turn 2, before any API call:

```
TOKEN=$(gcloud auth application-default print-access-token)
```

Single fetch per run. Pass via shared context to all subsequent curl invocations.

### Search Analytics call shape

```
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '<JSON_BODY>' \
  "https://www.googleapis.com/webmasters/v3/sites/<SITE_URL_ENCODED>/searchAnalytics/query"
```

Where `<SITE_URL_ENCODED>` is the `site_url` from config.yaml with `:` → `%3A` and `/` → `%2F`. See `gsc-api-schema.md` "Site URL encoding".

### URL Inspection call shape

```
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"inspectionUrl":"<URL>","siteUrl":"<SITE_URL_RAW>"}' \
  "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
```

**Note**: URL Inspection uses `siteUrl` as a **request body field** (raw, no encoding). Search Analytics uses it as a **path parameter** (encoded). Don't confuse them.

### Parameter substitution

Templates use placeholders:
- `<<LOOKBACK_DAYS>>` — from `config.yaml.lookback_days` (default 90)
- `<<SITE_URL_ENCODED>>` — `site_url` URL-encoded for path
- `<<SITE_URL_RAW>>` — raw `site_url` for request body
- `<<INSPECTION_URL>>` — single URL to inspect

The orchestrator computes substitutions in-context before each curl call.

### Per-call failure handling

Per-call failure is non-fatal. Failed call's signal is skipped; other calls proceed. See `gsc-api-schema.md` "Error response shape" for the failure code table.

---

## Q1 — Queries digest (top-50, position 5-20, imps ≥ 100)

Emits queries where the site ranks in the "page 2 / low page 1" band — the high-leverage band for on-page optimization.

### Request body

```json
{
  "startDate": "<CURRENT_DATE - <<LOOKBACK_DAYS>> days, YYYY-MM-DD>",
  "endDate": "<CURRENT_DATE, YYYY-MM-DD>",
  "dimensions": ["query"],
  "rowLimit": 25000,
  "type": "web"
}
```

### Client-side post-processing

The API does not support a `position`-range filter via `dimensionFilterGroups`. The skill applies the HAVING-equivalent filter after receiving the response:

```
filter rows where:
  impressions >= 100
  AND position BETWEEN 5.0 AND 20.0
sort by impressions desc
take top 50
```

### Digest field-mapping

| API row field | Digest field | Coercion |
|---|---|---|
| `keys[0]` | `query` | passthrough |
| `impressions` | `impressions` | passthrough (JSON number, no cast) |
| `clicks` | `clicks` | passthrough |
| `ctr` | `ctr` (decimal 0-1) | passthrough |
| `position` | `position` (1-based) | passthrough |

Consumed by sub-dim 11 `position_band_opportunity` (trigger: rows with `impressions >= 100` AND `position` BETWEEN 5-20; already filtered by Q1 client-side).

---

## Q2 — Pages digest (top-50 by impressions)

Emits the highest-traffic pages with their aggregate CTR + position. Feeds the median-CTR baseline for sub-dim 10 `ctr_opportunity`.

### Request body

```json
{
  "startDate": "<CURRENT_DATE - <<LOOKBACK_DAYS>> days>",
  "endDate": "<CURRENT_DATE>",
  "dimensions": ["page"],
  "rowLimit": 25000,
  "type": "web"
}
```

### Client-side post-processing

```
filter rows where:
  impressions >= 10
sort by impressions desc
take top 50
```

### Digest field-mapping

| API row field | Digest field | Coercion |
|---|---|---|
| `keys[0]` | `url` | passthrough |
| `impressions` | `impressions` | passthrough |
| `clicks` | `clicks` | passthrough |
| `ctr` | `ctr` (decimal 0-1) | passthrough |
| `position` | `position` (1-based) | passthrough |

### Median CTR computation

After Q2's 50 rows are translated, compute `median_ctr` across all rows' `ctr` field. Sub-dim 10 fires on rows where `impressions >= 500 AND ctr < (median_ctr * 0.5)`.

Edge case (all-zero CTR): `median_ctr = 0` → threshold = 0 → no sub-dim 10 findings emitted. Correct — no false positives for new sites.

---

## Q3 — `url_impressions_map` (all-URL → impressions, for traffic_weight)

Uncapped attempt — all URLs with impressions ≥ 1 in the window. Result becomes the `url_impressions_map` consumed by Step 6.6 `traffic_weight` formula.

### Request body

```json
{
  "startDate": "<CURRENT_DATE - <<LOOKBACK_DAYS>> days>",
  "endDate": "<CURRENT_DATE>",
  "dimensions": ["page"],
  "rowLimit": 25000,
  "type": "web"
}
```

(Same request shape as Q2 — they could collapse to a single call. Kept separate to allow independent failure handling: Q2 captures the top-50 digest; Q3 captures the full impressions map for `traffic_weight` lookups across the whole audit.)

### Client-side post-processing

```
filter rows where:
  impressions >= 1
build map: row.keys[0] → row.impressions
```

No client-side cap on rows kept. **Silent truncation at rowLimit=25000** for sites with >25k URLs — see `gsc-api-schema.md` rowLimit cap section.

### Output shape

```
url_impressions_map: {
  "https://example.com/popular-page": 1234,
  "https://example.com/another-page": 567,
  ...
}
```

Passed to all dispatched subagents. Used at finding-emission time:

```
traffic_weight = max(1.0, log10(url_impressions_map[<finding.affected_url>] + 1))
```

URLs not in the map → `traffic_weight = 1.0` (formula collapses to legacy `score_impact × certainty / effort_weight`).

---

## URL Inspection — per-URL call template

One call per URL inspected. The orchestrator dispatches N parallel calls in a single tool-use block (N capped at 100 — see selection algorithm below).

### Request body

```json
{
  "inspectionUrl": "<<INSPECTION_URL>>",
  "siteUrl": "<<SITE_URL_RAW>>",
  "languageCode": "en"
}
```

### Response → 9-reason cluster

After receiving response, apply the **`coverageState` + `pageFetchState` joint lookup table** (below) to determine which of v2's 9 sub-dim clusters (or "Other" / "no finding") this URL belongs to.

### Per-URL evidence carried into findings

Extract from `inspectionResult.indexStatusResult`:

| API field | Carried as | Used by sub-dim |
|---|---|---|
| `lastCrawlTime` | `evidence.last_crawl_time` | All sub-dims (sort key for `affected_urls`) |
| `googleCanonical` | `evidence.google_canonical` | Sub-dim 6 `canonical_conflict`  |
| `userCanonical` | `evidence.user_canonical` | Sub-dim 6 `canonical_conflict` |
| `crawledAs` | `evidence.crawled_as` | Sub-dim 6 evidence context |
| `indexingState` | `evidence.indexing_state` | Sub-dim 7 `blocked_access` (distinguishes meta-tag vs HTTP-header vs robots blocking) |
| `robotsTxtState` | `evidence.robots_txt_state` | Cross-check for robots-related findings |

---

## URL Inspection — selection algorithm

Hard budget: **100 URLs per run**. Well under the 2,000/day per-property quota; leaves headroom for multi-run usage same day.

### Source allocation

| Source | Count | Selection rule |
|---|---|---|
| **Top 80 from `url_impressions_map`** | 80 | Highest impressions across the lookback window. URLs that drive traffic deserve depth-of-diagnostic priority. |
| **Recent git changes resolved to URLs** | 20 | File paths from Step 1.5's 35-day git scan, resolved to URLs via `page_type_map` heuristics OR direct match in `url_impressions_map`. Git emits file paths, not URLs — only candidates that resolve cleanly are included. |

Both sources are available within Step 1.6 (Q3 from Turn 2a + Step 1.5's digest from Turn 1). Sitemap probe failures (Step 3.2) are intentionally NOT used as a source — Step 3.2 runs after Step 1.6, and waiting for it would push GSC ingestion into 60+ seconds wall time. The probe's URL-health findings already cover broken-sitemap-URL signals; URL Inspection adds Google's view on the URLs that matter most by traffic.

### Deduplication

A URL appearing in both sources counts **once**. Dedup precedence: `url_impressions_map` source wins.

After dedup, hard cap at 100. If fewer than 100 candidates after dedup, the budget shrinks accordingly (no padding).

### Source unavailable

- `url_impressions_map` empty (Q3 failed or no traffic): skip the 80-URL bucket; budget falls to whatever git resolves (typically 0-20)
- Step 1.5 git-history shallow or scan failed: skip the 20-URL bucket

When both sources are empty: skip URL Inspection batch entirely. Footer notes "0 URLs to inspect — no high-priority candidates this run." No indexing findings emitted this run.

### Pre-flight budget log

Before dispatching the batch, log to footer:

```
URL Inspection budget: 73 by impressions + 18 git-changed (resolved 18/24) = 91 URLs. Quota remaining: ~1909/2000 today.
```

Remaining-quota figure is approximate — the API doesn't expose a precise counter; back-of-envelope from "2000/day total minus inspections this run."

---

## `coverageState` + `pageFetchState` → 9-reason lookup table

Joint key for reliable classification. Disambiguates ambiguous `coverageState` values via `pageFetchState` (e.g., "Not found" alone is ambiguous; `pageFetchState == NOT_FOUND` vs `SOFT_404` distinguishes).

| `coverageState` | `pageFetchState` | Cluster sub-dim | Notes |
|---|---|---|---|
| Submitted and indexed | SUCCESSFUL | — (no finding) | Healthy state |
| Indexed, not submitted in sitemap | SUCCESSFUL | — (info-only footer) | Page indexed despite not being in sitemap; surfaces as footer count |
| Indexed, though blocked by robots.txt | * | — (info footer) | robots.txt conflict with indexed page |
| Crawled - currently not indexed | SUCCESSFUL | **sub-dim 2** `crawled_not_indexed` | Content quality / E-E-A-T signal |
| Crawled - currently not indexed | (other) | sub-dim 2 | Same finding regardless of fetch state |
| Discovered - currently not indexed | * | **sub-dim 3** `discovered_not_indexed` | Crawl budget / internal linking signal |
| Not found (404) | NOT_FOUND | **sub-dim 4** `not_found_404` | Standard 404 |
| Submitted URL not found (404) | NOT_FOUND | **sub-dim 4** `not_found_404` | Variant — URL was submitted via sitemap |
| Page with redirect | REDIRECT_ERROR | **sub-dim 5** `redirect_hygiene` | Redirect chain issue |
| Page with redirect | SUCCESSFUL | sub-dim 5 | Successful redirect — sitemap hygiene only |
| Alternate page with proper canonical tag | * | **sub-dim 7** `blocked_access` (alt-canonical variant) | Intentional — alternate page |
| Duplicate, Google chose different canonical than user | * | **sub-dim 6** `canonical_conflict` | Google disagrees with declared canonical |
| Duplicate without user-selected canonical | * | **sub-dim 6** `canonical_conflict` (variant) | No declared canonical at all |
| Excluded by 'noindex' tag | * | **sub-dim 7** `blocked_access` (noindex variant) | Intentional — noindex |
| Blocked by robots.txt | BLOCKED_ROBOTS_TXT | **sub-dim 7** `blocked_access` (robots variant) | Intentional in most cases |
| Blocked due to access forbidden (403) | ACCESS_FORBIDDEN | **sub-dim 7** `blocked_access` (403 variant) | Often intentional |
| Blocked due to other 4xx issue | BLOCKED_4XX | **sub-dim 7** `blocked_access` (4xx variant) | Usually intentional |
| Server error (5xx) | SERVER_ERROR | **sub-dim 9** `server_errors` | Site reliability signal |
| Soft 404 | SOFT_404 | **sub-dim 8** `soft_404` | Page returns 200 but Google detected empty/error content |
| URL is unknown to Google | * | — (info footer) | Google hasn't seen the URL yet |
| (any value not above) | * | — ("Other" bucket, info footer) | Unmapped — surface in footer for catalog update |

### Cluster aggregation

For each sub-dim 2-9, group all URLs whose lookup result matches. Emit one finding per cluster (NOT one per URL — matches v2 catalog behavior):

```
finding = {
  sub_dimension: "<name from sub-dims 2-9>",
  total_count: <count of inspected URLs in this cluster>,
  affected_urls: <top 10 by lastCrawlTime desc>,
  severity: <per gsc-ingestion.md catalog>,
  certainty: <per catalog>,
  effort_estimate: <per catalog>,
  title: "<N inspected pages match <reason> ...>",
  recommended_action: "<per catalog>",
  evidence: {
    per_url_diagnostics: [
      {url, last_crawl_time, indexing_state, google_canonical?, user_canonical?, crawled_as?},
      ...
    ],
    inspection_budget: <total inspections this run>,
    inspected_count: <count for this cluster>
  },
  source: "gsc",
  score_impact: 0
}
```

**Important `total_count` semantics**: `total_count` is the **inspected-URL-count**, not site-wide truth. If 100 URLs were inspected and 12 matched `crawled_not_indexed`, the finding says "12 of 100 inspected pages...". The finding title surfaces this explicitly:

> "12 of 100 inspected pages crawled-not-indexed (content quality signal — sampled from highest-impression + sitemap-failure + recent-change URLs)"

---

## Sub-dim 1 (`indexing_coverage`) — informational only

Sub-dim 1's site-wide non-index rate **cannot be computed reliably from per-URL inspection results** (URL Inspection is per-URL; you'd need the full sitemap inspected to extrapolate to a site-wide rate).

Behavior: emit an informational footer note when ≥1 inspected URL has `coverageState != "Submitted and indexed"`:

```
Of N inspected pages, M ({M/N*100}%) are not indexed cleanly. See sub-dims 2-9 for per-reason breakdown.
```

No score-headline finding emitted. Sub-dims 2-9 carry the cluster-level signals; the site-wide umbrella rate isn't reliably computable from a sampled subset.

---

## Quota degradation rules

Per locked decision 10 — never block runs.

### Mid-batch URL Inspection 429

If an `urlInspection` call returns HTTP 429:
1. Stop sending further inspection calls (drop the remaining batch)
2. Aggregate findings from URLs that did succeed
3. Footer captures: `URL Inspection: N/M succeeded, M-N skipped (quota exhausted at HH:MM). Re-run tomorrow for remaining.`
4. Indexing findings emit from the inspected subset only; `total_count` reflects N

### Search Analytics 429

Far less likely (1,200 QPM is generous). Per-call:
1. Skip that signal (Q1 / Q2 / Q3)
2. Footer captures: `searchanalytics.query Q<N> failed: quota exhausted.`
3. Other Q* calls proceed

If Q3 fails: `url_impressions_map` empty → `traffic_weight = 1.0` everywhere → formula collapses to legacy heuristic-only ranking.

### Auth probe 429

Highly unlikely on a 1-call probe. If it happens: surface "GSC API quota exhausted on probe — retry later" + fall through to heuristic-only mode.

---

## Parallel dispatch

All Q1-Q3 fire in a **single parallel Bash turn**. URL Inspection batch fires in a **second parallel Bash turn** after Q3 returns (since Q3's output feeds the URL Inspection selection algorithm). Total wall time: ~5-15 seconds typical (3 fast searchanalytics + 100 parallel inspections).

Schematically:

```
Turn 2a (single parallel batch):
  - curl Q1 (queries digest)
  - curl Q2 (pages digest)
  - curl Q3 (url_impressions_map)

Turn 2b (single parallel batch, after Turn 2a):
  - curl inspect URL_1
  - curl inspect URL_2
  - ...
  - curl inspect URL_100
```

(Turn 1 detection batch covered in `SKILL.md` Step 1.6.1 + parallel-batch note.)

If both Performance + Indexing signals are needed, the Step 1.6 dispatcher fires both turns. If only one signal source is active, only the relevant turn fires.

---

## What's NOT done in queries (deferred)

| Capability | Why deferred |
|---|---|
| Country/device dimension splits in Q1-Q3 | Dimensional explosion without v1 finding emission. future. |
| Pagination beyond rowLimit=25000 | Accept silent truncation; `traffic_weight = 1.0` fallback covers URLs not in the top-25k. |
| Discover impressions (`type: "discover"`) | v1 catalog scope is web/image/video. future. |
| Rich-result aggregation queries | URL Inspection's `richResultsResult` block exists but not aggregated. future. |
| `mobileUsabilityResult` aggregation | Same — new sub-dim category. future. |
| Custom inspection URL list (user-supplied via config) | Skill uses algorithmic selection only. May add `inspection_urls:` config key later. |
| Per-day time-series (`dimensions: ["date"]`) | Trend findings need separate digest shape. future. |
| Sitemap submission status (`sitemaps.list`) | Sitemap probe in Step 3.2 covers URL health. future for submission-status integration. |
