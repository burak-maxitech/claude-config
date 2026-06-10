# Google Search Console API Queries — Canonical Templates

Loaded by the orchestrator (Step 1.6) when the Search Console API is the active Performance + Indexing path. Provides:

- 3 parametrized `curl` templates for `searchanalytics.query` (Q1 queries digest, Q2 pages digest, Q3 `url_impressions_map`)
- 1 parametrized `curl` template for `urlInspection.index.inspect` (one URL per call)
- URL Inspection **selection algorithm** for the 200-URL/run budget (4-slice mix: impressions-top + git-changed + user-supplied (`known-bad-urls.txt`) + sitemap-orphan)
- `coverageState` + `pageFetchState` → 9-reason **lookup table** (full)
- Quota degradation rules

For endpoint inventory, auth, quota model, and enum reference, see `gsc-api-schema.md`. For digest field translation and integration with the **14 sub-dim catalog**, see `gsc-ingestion.md` "API ingestion" subsection. **For the disk-cache contract (split TTL: 24h on sa-*, 7d on ui-*; atomic write; skip-on-non-200), see `gsc-cache.md`. The Search Analytics curl shapes in this file are the fresh-path body inside that file's bash cache wrapper; the URL Inspection cache logic is helper-resident in `gsc-parse-helper inspect-batch` (same key + TTL contract).**


---

## Invocation contract

### Token + quota-project acquisition (minted in-call, NOT reused)

**Do not carry a token between Bash calls.** Shell state does not persist across Bash tool calls, so a `TOKEN` minted in one call is gone in the next. Every API-hitting call mints its own via the helper:

```
# Search Analytics curl path — at the top of the cache-miss branch:
_CREDS=$(gsc-parse-helper auth-token)      # line 1 = token, line 2 = quota project
TOKEN=$(printf '%s' "$_CREDS" | sed -n 1p)
QUOTA_PROJECT=$(printf '%s' "$_CREDS" | sed -n 2p)
```

(URL Inspection does NOT do this — `gsc-parse-helper inspect-batch` mints internally so the token never leaves the helper process.)

`gsc-parse-helper auth-token` resolves credentials in this order: `GCLOUD_TOKEN`/`GCLOUD_QUOTA_PROJECT` env → `GOOGLE_APPLICATION_CREDENTIALS` → `config.yaml adc_credentials_path` (a synced ADC file, for multi-machine use) → gcloud's default ADC path; then mints the token with Python stdlib (a refresh-token grant — no `gcloud` spawn, no `jq`). `QUOTA_PROJECT` comes from `config.yaml quota_project` or the credential file's `quota_project_id`. **Required on every Search Console API call** — without the `x-goog-user-project` header, all calls return HTTP 403 with `reason: SERVICE_DISABLED` (Google Cloud APIs need a billable project even though Search Console API itself is free). **Capture the token into a shell var and never echo it** — keep it out of the model transcript.

### Search Analytics call shape

The orchestrator wraps every call in the `gsc-cache.md` "Cache wrapper" pattern (24h TTL by default, bypassed when `--no-cache` flag is set). Inside the wrapper, the fresh-path curl is:

```
curl -s -w '%{http_code}' -o "$TMP" -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-goog-user-project: $QUOTA_PROJECT" \
  -H "Content-Type: application/json" \
  -d '<JSON_BODY>' \
  "https://www.googleapis.com/webmasters/v3/sites/<SITE_URL_ENCODED>/searchAnalytics/query"
```

`$TMP` is the per-call temp file (`$CACHE_FILE.tmp.$$`) — atomic rename to `$CACHE_FILE` on HTTP 200, discarded on non-200. Cache filename uses the `sa-q1`/`sa-q2`/`sa-q3` prefix per call. Cache key inputs documented in `gsc-cache.md` "Search Analytics" section.

Where `<SITE_URL_ENCODED>` is the `site_url` from config.yaml with `:` → `%3A` and `/` → `%2F`. See `gsc-api-schema.md` "Site URL encoding".

### URL Inspection call shape

Same cache wrapper. Fresh-path curl:

```
curl -s -w '%{http_code}' -o "$TMP" -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-goog-user-project: $QUOTA_PROJECT" \
  -H "Content-Type: application/json" \
  -d '{"inspectionUrl":"<URL>","siteUrl":"<SITE_URL_RAW>"}' \
  "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
```

Cache filename uses the `ui-<sha1(site_url|inspection_url)>` prefix — one slot per inspected URL, so partial cache hits across a 200-URL batch are common after the first run of the day.

**Note**: URL Inspection uses `siteUrl` as a **request body field** (raw, no encoding). Search Analytics uses it as a **path parameter** (encoded). Don't confuse them.

### Parameter substitution

Templates use placeholders:
- `<<TOKEN>>` — ADC access token minted in-call via `gsc-parse-helper auth-token` (stdlib refresh-token grant; line 1 of its output — see "Token + quota-project acquisition" above; NOT `gcloud ... print-access-token`, which is only the helper's internal fallback)
- `<<QUOTA_PROJECT>>` — quota project (line 2 of `gsc-parse-helper auth-token` output — resolved from `config.yaml quota_project` or the credential file's `quota_project_id`)
- `<<LOOKBACK_DAYS>>` — from `config.yaml.lookback_days` (default 90)
- `<<SITE_URL_ENCODED>>` — `site_url` URL-encoded for path
- `<<SITE_URL_RAW>>` — raw `site_url` for request body
- `<<INSPECTION_URL>>` — single URL to inspect

The orchestrator computes substitutions in-context before each curl call.

### Per-call failure handling

Per-call failure is non-fatal. Failed call's signal is skipped; other calls proceed. See `gsc-api-schema.md` "Error response shape" for the failure code table.

### Cap-hit detection (per-call)

After each Q1/Q2/Q3 response (cache hit OR fresh fetch — applies to both), capture:

```
rows_received = len(response.rows or [])
rowLimit_requested = <the rowLimit value sent in the request body, default 25000 per spec>
cap_hit = (rows_received == rowLimit_requested)
```

`cap_hit = true` signals **likely truncation** — either the site has >rowLimit unique candidates and we lost data past the cap, OR the site genuinely has exactly rowLimit candidates (false-positive). Either way the user wants to know. **Cap-hit detection runs on the response body regardless of cache state** — a cached response stays as-truncated as when it was originally fetched, so the warning is still accurate.

Stash `{q1: {received, limit, cap_hit}, q2: {...}, q3: {...}}` in shared context for SKILL.md Step 1.6.12 footer rendering. The orchestrator emits the cap-hit summary line and (if any cap was hit) a truncation warning recommending raised rowLimit or startRow pagination.

**Why this matters per-call:**
- **Q1 (queries digest):** cap-hit means top-50 by impressions may exclude lower-position-band winners. Less critical since position 5-20 filter is what matters most.
- **Q2 (pages digest):** cap-hit means top-50 by impressions may be incomplete. Real impact: median_ctr baseline (used by sub-dim 10 `ctr_opportunity`) drifts toward higher-traffic pages.
- **Q3 (url_impressions_map):** cap-hit is the **highest-impact case** — every URL outside the top-25k by impressions falls through to `traffic_weight = 1.0` in Step 6.6 ranking. The skill still works (heuristic-only fallback for those URLs) but loses GSC traffic-weighting signal for long-tail pages.

**Pagination NOT implemented yet** — for sites where Q3 cap-hits matter, the spec deliberately defers. Add when a dogfood surfaces the failure on a real site (e.g., a Wikipedia-class property). For now, the footer warning surfaces the gap so it's visible.

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

One API call per URL inspected, but the orchestrator does NOT issue these as individual Bash curl calls — the canonical dispatch is a **single invocation of `gsc-parse-helper inspect-batch`**, which parallelizes internally (6 workers + 429/5xx retry) and applies the request shape below per URL (N capped at 200 — see selection algorithm below). The template documents the wire format the helper sends.

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

Hard budget: **200 URLs per run**. Well under the 2,000/day per-property quota; reruns within the 7-day `ui-*` TTL are mostly cache hits.

### Source allocation (4 slices)

| Source | Count | Selection rule |
|---|---|---|
| **Top 80 from `url_impressions_map`** | up to 80 | Take the **literal top 80 URLs by impressions desc** from Q3's full uncapped map. Apply **no additional minimum impression threshold** — even URLs with 1 impression count. If fewer than 80 URLs have any impressions, take all available. **Do not add subjective filters** ("only high-quality URLs", "skip thin pages", etc.). The point is depth-of-diagnostic on the URLs that drive traffic at any level. |
| **Recent git changes resolved to URLs** | up to 20 | File paths from Step 1.5's 35-day git scan, resolved to URLs via `page_type_map` heuristics OR direct match in `url_impressions_map`. Git emits file paths, not URLs — only candidates that resolve cleanly are included. **Resolves BOTH `old_path` AND `new_path` from rename commits** (Step 1.5's `renames` aggregate) — the old_path resolution is what links a 404 URL to the rename that orphaned it. Without this, sub-dim 4 (`not_found_404`) misses the routing-rename signal for URLs that exist as 404s precisely because their source file moved. Take all that resolve, capped at 20. |
| **User-supplied URLs** (`.seo-data/gsc/known-bad-urls.txt`) | up to 100 | **One URL per line; `#`-prefixed lines and blank lines skipped; whitespace trimmed; duplicates removed; cap 100** (raised from 50 after the S34 burakarik6 dogfood — user routinely pasted ~100-URL batches from GSC validation-failed emails; the 50-cap forced splitting across runs and silent loss of the second half. 100 fits the shared bucket cleanly: a hot-deindex user can claim the entire user/orphan bucket without bookkeeping). User pastes URLs they want inspected — typically from GSC's "All known pages" coverage report export or from validation-failure emails. **Always inspected when present** — explicit user signal. Targets URLs that are NOT in current sitemap, NOT in impressions, AND NOT git-changed in the 35-day window — e.g., 404'd URLs from older renames (>35d ago), URLs orphaned via CMS edits not visible in git history, or specific URLs flagged in a GSC "Validation failed" email. **Why this slice exists (S34 burakarik6 dogfood):** the second screenshot showed 663 URLs with `coverageState: "Not found (404)"` — URLs Google still remembers from past indexing but that no longer exist in sitemap, codebase, or impressions. **Root-cause is a Search Console API limitation:** the API does NOT expose the GSC "Page indexing" report's URL lists (no `pageIndexing.list` endpoint, despite long-standing community feature requests). `urlInspection.index.inspect` requires you to already know the URL. Without algorithmic discovery (impressions/git/sitemap) or user input (this file), these URLs are invisible to the skill. This slice closes that gap. **Use as fallback, not primary workflow:** the three algorithmic slices cover most cases; only paste URLs into this file that demonstrably didn't appear in the inspected set on a prior run. See `gsc-setup-readme-template.md` "When you need / DON'T need it" + "Recommended workflow: try without the file first" for the consumer-facing guidance. |
| **Sitemap orphans (URLs not in `url_impressions_map`)** | up to (100 − user-supplied count) | URLs from the LIVE sitemap (fetched + filtered by `gsc-parse-helper sitemap-urls` in Step 1.6.6a — GSC `sitemaps.list` → robots.txt → `<base>/sitemap.xml`, NOT a repo file) that do NOT appear in Q3's `url_impressions_map`. The helper emits this pre-filtered list under `--- orphans ---`. **Sort: document order.** Tiebreak: `<priority>` desc when present. **Do NOT use `<lastmod>` desc** — the burakarik6 dogfood (838 URLs flipped to "Page with redirect" over 5 weeks) shows the failure pattern is *stable pages suddenly broken*, not *new pages*. Document order is also **deterministic** across runs — required for sub-dim 14 (`deindex_regression`) snapshot diff to compare the same URLs run-over-run. **Why this slice exists:** URLs that Google has deindexed fall out of `url_impressions_map` (no impressions → not in Q3) → never get inspected without this slice → user only learns about the deindex when Google emails. **Bucket-sharing with user-supplied:** sitemap-orphan and user-supplied share a 100-slot bucket. User-supplied takes precedence (explicit user intent); sitemap-orphan fills the remainder. So if user pastes 100 URLs, sitemap-orphan slot count drops from 100 → 0 (user has fully claimed the bucket). If user pastes 30, sitemap-orphan gets 70. If user pastes 0, sitemap-orphan stays at 100. **Critical limitation (S34 burakarik6 cont.):** sitemap-orphan only catches URLs **still in your sitemap**. URLs that the codebase has already removed from `sitemap.xml` (the right thing to do as content is unpublished/redirected) are invisible to this slice — they're not in sitemap AND not in impressions. Those need explicit `known-bad-urls.txt` paste. Don't tell users "redirects are covered by sitemap-orphan" without checking whether their codebase rotates deindexed URLs out of sitemap. |

All four sources are available within Step 1.6: Q3 from Turn 2a + Step 1.5's digest from Turn 1 + sitemap.xml parsed in Step 1.6.1's Turn 1 batch + `.seo-data/gsc/known-bad-urls.txt` read optimistically in Step 1.6.1's Turn 1 batch (file may not exist — `Read` errors silently → user_supplied_urls stays empty).

### Deduplication

A URL appearing in multiple sources counts **once**. Dedup precedence: `url_impressions_map` (impressions-top) > `git-changed` > `user-supplied` > `sitemap-orphan`.

Rationale for the order:
- **impressions-top** wins because the traffic data is the highest-value diagnostic context (`traffic_weight` for ranking).
- **git-changed** wins over user-supplied because Google's recrawl behavior tracks code changes — these URLs are the most likely to have changed state recently.
- **user-supplied** wins over sitemap-orphan because the user pasted them deliberately — they're high-signal even when they don't appear in any algorithmic source.
- **sitemap-orphan** is last because it's the broad sweep — URLs there are inspected when no higher-priority source claims them.

After dedup, hard cap at 200. If fewer than 200 candidates after dedup, the budget shrinks accordingly (no padding with arbitrary URLs).

**The 200-URL cap is the ceiling, not the target.** Per the `SKILL.md` "Ingestion conventions → Budget utilization" contract, the orchestrator MUST attempt to fill the budget when candidates are available. Cutting to 40 URLs when 1,300+ URLs are in the impressions map AND 2,800+ URLs are sitemap-orphan candidates (S30 dogfood failure mode) violates the spec. The URLs that don't drive massive traffic still provide diagnostic value for indexing/canonical decisions — and the sitemap-orphan slice specifically catches URLs that ARE the deindex risk.

### Source unavailable

- `url_impressions_map` empty (Q3 failed or no traffic): skip the 80-URL impressions slice
- Step 1.5 git-history shallow or scan failed: skip the 20-URL git-changed slice
- `.seo-data/gsc/known-bad-urls.txt` absent or empty (after stripping comments/blanks): skip the user-supplied slice; sitemap-orphan claims the full 100-slot bucket
- Sitemap missing OR all sitemap URLs already in `url_impressions_map`: skip the sitemap-orphan portion of the 100-slot bucket; user-supplied fills only its own portion
- All four empty (rare — usually sitemap-orphan has candidates): skip URL Inspection batch entirely. Footer notes "0 URLs to inspect — no high-priority candidates this run." No indexing findings emitted this run.

### Pre-flight budget log

Before dispatching the batch, log to footer. Include the source breakdown so under-utilization is auditable:

```
URL Inspection budget: 80 by impressions (from 1,304 URLs in url_impressions_map) + 17 git-resolved (resolved 17/22 git-changed paths via page_type_map; includes 8 rename old_paths) + 0 user-supplied (no known-bad-urls.txt) + 100 sitemap-orphan (from 2,795 sitemap URLs not in url_impressions_map); dedup removed 3 → 194/200 attempted. Quota remaining: ~1806/2000 today.
```

When user supplied known-bad-urls.txt (partial bucket — paste size < 100):

```
URL Inspection budget: 80 by impressions + 17 git-resolved + 50 user-supplied (from .seo-data/gsc/known-bad-urls.txt — 50 of 663 URLs pasted by user from GSC "Not found (404)" export; first 50 by file order) + 50 sitemap-orphan (slot count reduced from 100 → 50 by user-supplied bucket share); dedup removed 5 → 192/200 attempted. Quota remaining: ~1808/2000 today.
```

When user fills the entire user/orphan bucket (paste size ≥ 100):

```
URL Inspection budget: 80 by impressions + 17 git-resolved + 100 user-supplied (from .seo-data/gsc/known-bad-urls.txt — 100 of 663 URLs pasted; user-supplied claimed the full shared bucket; sitemap-orphan slice skipped this run) + 0 sitemap-orphan; dedup removed 6 → 191/200 attempted. Quota remaining: ~1809/2000 today.
```

If under-utilizing the 200-URL cap (because candidate pool is smaller across all 4 slices), surface the reason explicitly:

```
URL Inspection budget: 30 by impressions + 8 git-resolved + 0 user-supplied + 47 sitemap-orphan (small sitemap, few orphans) → 85/200 attempted. Reason: low-traffic property with compact sitemap. Quota remaining: ~1915/2000.
```

If user pasted more URLs than the 100-slot cap can take, surface as a top-level Suggested Next Actions banner AND in the footer:

```
URL Inspection budget: ... + 100 user-supplied (of 663 in known-bad-urls.txt — first 100 by file order this run; 563 remaining. Consider removing inspected URLs from the file or re-running over multiple days to inspect the remainder under daily quota limits) + ...
```

**Dedup-backfill (deferred — S34 surfaced):** when dedup drops cross-slice overlaps (e.g., 6 URLs appear in both impressions and sitemap), the current spec leaves the bucket short (194/200 instead of 200). A future revision could backfill the dropped slots from the next slice (impressions URLs #81-86 in the example). Trade-off: marginal coverage gain (~3% budget) vs slice-purity confusion in the footer log. Decision deferred until a dogfood shows the gap mattering on a real run.

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

**Important `total_count` semantics**: `total_count` is the **inspected-URL-count**, not site-wide truth. If 194 URLs were inspected and 12 matched `crawled_not_indexed`, the finding says "12 of 194 inspected pages...". The finding title surfaces this explicitly:

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

429s are handled **inside `gsc-parse-helper inspect-batch`**, per URL — there is no orchestrator-side batch abort:
1. The helper retries each 429/5xx-failing URL up to 3× with exponential backoff (2s/4s/8s + jitter); other URLs in the pool continue unaffected
2. URLs that exhaust retries surface under the helper's `--- errors ---` section with their HTTP code
3. The orchestrator aggregates findings from URLs that succeeded; footer captures: `URL Inspection: N/M succeeded, M-N errored (429 after retries — likely daily quota exhausted). Re-run tomorrow for remaining.`
4. Indexing findings emit from the succeeded subset only; `total_count` reflects N

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

All Q1-Q3 fire in a **single parallel Bash turn** (each call cache-wrapped per `gsc-cache.md`). URL Inspection fires as a **single `gsc-parse-helper inspect-batch` Bash invocation** after Q3 returns (since Q3's output feeds the URL Inspection selection algorithm); the helper parallelizes the up-to-200 calls internally (6 workers + retry). Total wall time: ~15-25 seconds typical on a fresh run. Cache hits are served from disk inside each path — a full-cache-hit rerun completes Turn 2 in ~1-2 seconds (no network).

Schematically:

```
Turn 2a (single parallel Bash batch):
  - curl Q1 (queries digest)        [cache-wrapped]
  - curl Q2 (pages digest)          [cache-wrapped]
  - curl Q3 (url_impressions_map)   [cache-wrapped]

Turn 2b (single Bash call, after Turn 2a):
  - gsc-parse-helper inspect-batch .seo-data/gsc/cache "$SITE_URL" "$TMPFILE_URLS"
    (helper inspects up to 200 URLs internally — 6 workers, per-URL 7d cache)
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
| Sitemap submission-status *findings* from `sitemaps.list` (errors/warnings/isPending per submitted sitemap) | `sitemaps.list` IS already called for sitemap *discovery* (Step 1.6.6a via `gsc-parse-helper sitemaps-list`, S39); emitting findings from its submission-status fields is the deferred part. |
