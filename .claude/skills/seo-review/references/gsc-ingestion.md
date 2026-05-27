# GSC Ingestion — Canonical Reference

Loaded by the orchestrator in **Step 1.6** of `SKILL.md`. This file is the source of truth for:
- Activation conditions (when GSC mode is active vs heuristic-only)
- API ingestion contract — digest shape consumed by subagents
- Setup banner (one-time, sentinel-gated)
- `.gitignore` auto-append rules
- Finding-type catalog (14 sub-dims) — sub-dims 1-13 populated from Search Console API output; sub-dim 14 (`deindex_regression`) is orchestrator-emitted in Step 1.6.13 from snapshot diff (not produced by the seo-gsc-insights subagent)

For the **finding output shape**, ranking formulas, and `score_impact: 0` invariant, see `rubric.md` — that file is the contract; this file is the implementation reference. For endpoint inventory + auth setup, see `gsc-api-schema.md`. For SQL-equivalent call templates + URL Inspection selection + `coverageState` → 9-reason lookup table, see `gsc-api-queries.md`.

---

## Activation

GSC mode is **enabled** when all of these conditions hold:

1. `.seo-data/gsc/config.yaml` exists with non-empty `site_url:` key
2. `gcloud` SDK installed (`gcloud --version` returns)
3. ADC authenticated (`gcloud auth application-default print-access-token` returns a token)
4. ADC quota project set (`grep -oE '"quota_project_id"...' | sed ...` on `application_default_credentials.json` returns a non-empty project ID — written by `gcloud auth application-default set-quota-project <id>`). The skill sends this value as the `x-goog-user-project` header on every API call. grep+sed used instead of `jq` since `jq` isn't on PATH in many bash environments.
5. Active probe: `curl GET https://www.googleapis.com/webmasters/v3/sites` with both the ADC token AND `x-goog-user-project` header returns HTTP 200 + valid JSON
6. The configured `site_url` appears in the returned `siteEntry[*].siteUrl` list with a non-`siteUnverifiedUser` `permissionLevel`

Otherwise → **heuristic-only mode**. The skill runs normally; subagents get an empty GSC block; Section 1 banner fires if it's a first encounter (sentinel-gated).

---

## API ingestion contract

When GSC mode is enabled, ingest data from the Search Console API per `gsc-api-queries.md`:

- **Performance**: 3 parallel `searchanalytics.query` calls (Q1 queries digest, Q2 pages digest, Q3 `url_impressions_map`)
- **Indexing**: up to 200 parallel `urlInspection.index.inspect` calls (per-URL; 4-slice URL selection algorithm: top 80 by impressions + 20 git-changed + up to 100 user-supplied (`known-bad-urls.txt`) + sitemap-orphan URLs not in `url_impressions_map` filling whatever the user-supplied slice doesn't claim of the shared 100-slot bucket)

### Query execution

All Performance calls dispatch in one parallel Bash turn. URL Inspection calls dispatch in a second parallel turn after Performance (URL selection uses Q3's `url_impressions_map`).

**Token + quota-project caching**: Turn 1's probe already fetched both the ADC token (`gcloud auth application-default print-access-token`) and the ADC quota project (extracted from `application_default_credentials.json` via `grep -oE '"quota_project_id"...' | sed -E '...'` — see Step 1.6.1 for the exact line). Both are reused as shared context across all Turn 2 curl invocations — every call must include `Authorization: Bearer $TOKEN` AND `x-goog-user-project: $QUOTA_PROJECT` headers. Tokens have a 1-hour TTL; a single Step 1.6 dispatch finishes in seconds, so one Turn 1 fetch is reused.

### Digest shape

Subagents consume a digest shape defined here; the translator maps API row fields to digest fields:

**Queries digest** (Q1 → consumed by sub-dim 11 `position_band_opportunity`):

```
[
  {
    query:       string,        // API row.keys[0] passthrough
    impressions: number,        // API row.impressions passthrough (native JSON number)
    clicks:      number,
    ctr:         number,        // decimal 0-1, passthrough
    position:    number,        // 1-based decimal, passthrough
  },
  ... up to 50 rows after client-side filter (impressions >= 100 AND position 5-20) + sort by impressions desc
]
```

**Pages digest** (Q2 → consumed by sub-dim 10 `ctr_opportunity` + feeds `page_type_map` + feeds traffic-orphan computation):

```
[
  {
    url:         string,
    impressions: number,
    clicks:      number,
    ctr:         number,
    position:    number,
  },
  ... up to 50 rows after client-side filter (impressions >= 10) + sort by impressions desc
]
```

**`url_impressions_map`** (Q3 → consumed by Step 6.6 `traffic_weight` computation):

```
{
  "<url>": <impressions number>,
  ...
}
// Uncapped; built from Q3's full result. Silent truncation at rowLimit=25000.
```

**Indexing clusters** (URL Inspection → consumed by sub-dims 2-9):

```
{
  cluster_2_crawled_not_indexed: { total_count, affected_urls, per_url_evidence },
  cluster_3_discovered_not_indexed: { ... },
  ...
  cluster_9_server_errors: { ... },
  cluster_other: { ... },         // unmapped coverageState bucket
}
```

The `coverageState` + `pageFetchState` joint lookup table (in `gsc-api-queries.md`) determines which cluster each inspected URL maps to.

### JSON encoding rules

The Search Console API returns numeric fields as **native JSON numbers** (not quoted strings). Translation is passthrough — no `Number()` cast needed:

```json
{
  "rows": [
    {
      "keys": ["topkapi palace istanbul"],
      "impressions": 1092,         // JSON number — passthrough
      "clicks": 0,                  // JSON number — passthrough
      "ctr": 0.0,                   // JSON number, decimal 0-1
      "position": 27.87             // JSON number, 1-based decimal
    }
  ]
}
```

### Median CTR computation (Pages digest → sub-dim 10)

After Q2's 50 rows are translated, compute `median_ctr` over all rows' `ctr` field. Sub-dim 10 fires on rows where `impressions >= 500 AND ctr < (median_ctr * 0.5)`.

Edge case: all-zero CTR → median = 0 → threshold = 0 → no sub-dim 10 findings emitted. Correct behaviour for new sites with no clicks yet.

### page_type_map sources

Composition (3 sources):

1. **Top-50 URLs from Q2 Pages digest** (NOT Q3's uncapped map — bounded classification scope)
2. **Inspected URLs from URL Inspection batch**
3. **Sitemap probe URLs** (Step 3.2)

Classification logic uses path-pattern heuristics (mirrors `scan-geo.md:25-37`):

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

The map is passed to **all dispatched subagents** in shared context.

### Freshness

API path is **real-time** — no `data_date` partition or file mtime to check. Static footer line:

```
GSC API path: real-time view of GSC's pipeline (typically ~2-day lag from real-world events).
```

The ~2-day lag is Google's pipeline delay, not the skill's. Recommendations may not reflect changes made in the last 2-3 days.

### Edge cases

| Case | Behaviour |
|---|---|
| Q1 returns 0 rows (no queries meet impressions/position threshold) | Empty queries digest. Sub-dim 11 emits no findings. No error. |
| Q2 returns 0 rows (no URLs meet impressions floor) | Empty pages digest. Sub-dim 10 + 12 emit no findings. `page_type_map` source #1 empty; sources #2 + #3 still feed. |
| All Q2 rows have `ctr = 0` (new site) | Median = 0 → threshold = 0 → no sub-dim 10 findings. Correct — no false positives. |
| Q3 returns >25k rows | Silent truncation at API's per-call cap. `url_impressions_map` covers top-25k; URLs not in map get `traffic_weight = 1.0` fallback. |
| URL Inspection returns 404 for a candidate URL | URL not known to Google. Skip from cluster (no sub-dim assignment). Track count in footer. |
| All inspected URLs return `coverageState: "Submitted and indexed"` | No indexing findings emitted. Healthy state — surface "All N inspected pages indexed cleanly" in footer. |
| `coverageState` returns an unmapped value | Use "Other" bucket from lookup table. Footer note: "Unmapped coverageState: <value> on N URLs — update gsc-api-queries.md lookup table." |
| URL Inspection budget = 0 (no candidates) | Skip URL Inspection batch entirely. No indexing findings. Footer notes the empty budget. |
| `site_url` in config but not verified by user's Google account | Activation condition 5 fails → fall through to heuristic-only. Footer surfaces specific error. |

### Failure mode summary

| Stage | Failure | Effect |
|---|---|---|
| Pre-query | `gcloud` not installed | Activation condition 2 fails → heuristic-only. Footer: install link |
| Pre-query | ADC not authenticated | Activation condition 3 fails → heuristic-only. Footer: `gcloud auth application-default login` remediation |
| Pre-query | ADC quota project not set | Activation condition 4 fails → heuristic-only. Footer: run `gcloud auth application-default set-quota-project <id>` + `gcloud services enable searchconsole.googleapis.com --project=<id>` |
| Pre-query | `site_url` empty in config.yaml | Activation condition 1 fails → heuristic-only |
| Pre-query | Active probe returns 401 | Activation condition 5 fails. Footer: `--scopes` remediation (per gsc-api-schema.md "Authentication") |
| Pre-query | Active probe returns 403 with `SERVICE_DISABLED` | Activation condition 5 fails. Footer: enable Search Console API on quota project — `gcloud services enable searchconsole.googleapis.com --project=<adc_quota_project>` |
| Pre-query | Active probe returns 200 but `site_url` not in list | Activation condition 6 fails. Footer: verify site_url is owned by your Google account |
| Query runtime | `searchanalytics.query` returns 429 | Print error + skip Performance signal |
| Query runtime | `urlInspection` returns 429 mid-batch | Graceful degrade: surface count succeeded/skipped in footer |
| Query runtime | Single `urlInspection` returns 404 | URL unknown to Google — exclude from cluster, footer count |
| Per-query partial | Q1 fails but Q2 + Q3 succeed | Empty queries digest + footer note. Pages + url_impressions_map still produced. |

All failure modes are non-fatal — `/seo-review` always produces a score + report.

---

## Setup banner — Search Console API (one-time, sentinel-gated)

When the orchestrator runs `/seo-review` and **no `.seo-data/gsc/config.yaml` is found**, and the sentinel `.seo-data/.gsc-banner-shown` is absent:

1. Print the banner (below).
2. Touch the sentinel (`Write` empty file at `.seo-data/.gsc-banner-shown`).
3. The sentinel is itself gitignored via the auto-`.gitignore` block — never committed.

**Banner content** (printed before Section 1 of the report):

```
─────────────────────────────────────────────────────────────────────────────
GSC INTEGRATION AVAILABLE — Make /seo-review traffic-aware

This run used static signals only. /seo-review can incorporate Google Search
Console data via the Search Console API to surface traffic-prioritized
findings (which pages get impressions, which queries you rank for at
position 5-20, which pages Google considers crawled-but-not-indexed).

Setup (one-time, ~5 minutes):

1. Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install
2. Pick or create a GCP project (any project works — Search Console API is
   free within quota). List with:  gcloud projects list
3. Enable Search Console API on the project:
     gcloud services enable searchconsole.googleapis.com \
       --project=<your-gcp-project>
4. Authenticate (opens browser for OAuth) + set quota project (required —
   Google Cloud APIs called via user-credential ADC need a billable project
   for quota tracking, even when the API itself is free):
     gcloud auth application-default login \
       --scopes=https://www.googleapis.com/auth/webmasters.readonly,\
                https://www.googleapis.com/auth/cloud-platform
     gcloud auth application-default set-quota-project <your-gcp-project>
5. Create .seo-data/gsc/config.yaml with your GSC property URL:
     site_url: sc-domain:example.com    # or "https://example.com/"
6. Re-run /seo-review.

The Google account you sign in with must be a verified user on the GSC
property — check at https://search.google.com/search-console > Settings.

This folder will be auto-gitignored. You don't need to commit anything.

Score will stay /100 regardless — GSC enriches the *recommendations*, not
the score, so docs/seo-history.md stays comparable across runs.

(This banner shows once per project. Touch .seo-data/.gsc-banner-shown to
silence it manually.)
─────────────────────────────────────────────────────────────────────────────
```

Banner skipped silently when `.seo-data/gsc/` exists (any config.yaml or sentinel present).

---

## `.gitignore` auto-append

When the orchestrator first detects `.seo-data/gsc/` (config.yaml present), append to project-root `.gitignore` using a sentinel-marked block for idempotency:

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

**Why not edit the user's existing .gitignore content:** the sentinel block is append-only. The orchestrator never modifies anything outside the markers.

---

## Finding-type catalog (14 sub-dims)

Each ingestion call (Search Analytics + URL Inspection) produces 0+ findings. All findings have `source: "gsc"`, `score_impact: 0` (enforced orchestrator-side in Step 6.0a).

### 1. `indexing_coverage` (site-wide non-index rate)

Site-wide non-index rate cannot be computed from per-URL URL Inspection results (you'd need full-sitemap coverage to extrapolate reliably). Emit only as an informational footer note when ≥1 inspected URL has `coverageState != "Submitted and indexed"`:

> `Of N inspected pages, M ({M/N*100}%) are not indexed cleanly. See per-reason breakdown in sub-dims 2-9 below.`

No score-headline finding emitted (the site-wide rate isn't reliably computable from a sample).

### 2. `crawled_not_indexed` (URL Inspection: `coverageState == "Crawled - currently not indexed"`)

**Trigger:** ≥1 inspected URL has this coverage state.

**Cluster all matched URLs into one finding:**

- `severity`: `medium` if count < 100; `high` if ≥100
- `certainty`: `0.9` (Google's call, usually accurate)
- `effort_estimate`: `large` (content-quality work)
- `affected_urls`: top 10 by `lastCrawlTime` descending
- `title`: `"<N> of <total_inspected> inspected pages crawled by Google but not indexed (content quality signal)"`
- `recommended_action`: `"Audit content quality and E-E-A-T signals. Common causes: duplicate content, thin content, low authority signal, soft-quality issues. Sample affected URLs: <list>. Pick 3-5 representative URLs, compare against top-ranking competitors, identify what's missing (length, originality, expert authorship, citations)."`

### 3. `discovered_not_indexed` (URL Inspection: `coverageState == "Discovered - currently not indexed"`)

**Trigger:** ≥1 matched.

**Cluster:**

- `severity`: `medium` if count < 50; `high` if ≥50
- `certainty`: `0.9`
- `effort_estimate`: `medium`
- `affected_urls`: top 10
- `title`: `"<N> of <total_inspected> inspected pages discovered but not crawled (crawl budget / internal linking signal)"`
- `recommended_action`: `"Google found these URLs but hasn't crawled them — usually crawl-budget or low-priority signal. Add internal links from high-authority pages, ensure they're in sitemap.xml, request indexing manually for the most important ones."`

### 4. `not_found_404` (URL Inspection: `coverageState` matches "Not found (404)" / "Submitted URL not found (404)", with `pageFetchState == NOT_FOUND`)

**Trigger:** ≥1 matched.

**Cluster + routing-rename match + locale-prefix cluster** (S34 burakarik6 dogfood: a 404 GSC email surfaced 663 affected URLs, sibling to the 838-URL sub-dim 5 redirect case — same i18n migration, two states):

1. Parse all matched URLs, derive path patterns (e.g., `/blog/2023/post-1`, `/blog/2023/post-2` → cluster `/blog/2023/*`).
2. Cross-reference with Step 1.5's git-changes digest, **including rename old_paths** — when `renames: [(old_path, new_path, ...)]` is present in the digest, resolve BOTH `old_path` and `new_path` to URLs via `page_type_map`. The old_path resolution is what links a 404 URL to the rename commit that orphaned it. Without resolving old_paths, sub-dim 4 misses the routing-rename signal for URLs that exist as 404s precisely because the source file moved.
3. **Locale-prefix cluster detection** (mirrors sub-dim 5 pattern): split each affected URL's path on `/`, take the first segment. When ≥2 distinct locale prefixes each account for ≥30% of the affected count (or one locale prefix accounts for ≥60% AND bare-prefix accounts for ≥20%), surface as `locale_prefix_clusters: {en: 287, tr: 198, bare: 178}` in evidence. Strong signal for the same i18n-migration root cause that drives sub-dim 5 in parallel.
4. **Cross-link with sub-dim 5** when both fire on overlapping path patterns: compute path-prefix overlap between sub-dim 4's affected URLs and sub-dim 5's affected URLs. When ≥3 path prefixes appear in BOTH findings' clusters, attach `co_occurrence_with_sub_dim_5: {<prefix>: {404_count: N, redirect_count: M}, ...}` evidence. Points to a single root cause (incomplete migration: some old URLs got proper redirects, others got dropped without).
5. If routing-rename match found: emit single bulk-cluster finding with the routing-rename signal in evidence.

- `severity`: `high` (broken URLs at Google's view dilute crawl budget)
- `certainty`: `1.0`
- `effort_estimate`: `small` (bulk 301 redirect or sitemap cleanup) or `medium` (when locale-prefix-cluster + sub-dim 5 co-occurrence detected — incomplete migration requires reasoning about which old URLs deserve redirects vs. removal)
- `affected_urls`: top 10
- `title`: `"<N> of <total_inspected> inspected URLs return 404 at Google's view"`. Append `" — likely i18n migration regression"` when locale-prefix clustering detected AND co_occurrence_with_sub_dim_5 has ≥3 shared prefixes.
- `evidence`: includes `"Routing rename in window: <commit-msg> on YYYY-MM-DD touching <paths>"` when detected. Also `locale_prefix_clusters` and `co_occurrence_with_sub_dim_5` per detection rules above.
- `recommended_action`:
  - **When routing-rename detected:** `"Bulk 301 redirects mapping <old-pattern> → <new-pattern> in <framework-config-file>. Plus remove 404 entries from sitemap.xml. Confirm the mapping is 1:1 before bulk-applying."`
  - **When sub-dim 5 co-occurrence detected (likely incomplete i18n migration):** `"This finding pairs with sub-dim 5 (redirect_hygiene) — same path patterns appear in both. Likely incomplete i18n migration where some old URLs got proper redirects (sub-dim 5) and others got dropped without (sub-dim 4 — this finding). If you've received a GSC 'Not found (404)' or 'Validation failed' email recently, this is the corresponding signal. Fix path: (1) audit the affected 404 URLs against the redirect rules in sub-dim 5's recommendation — add the missing 301 redirects (old-pattern → new canonical locale-prefixed URL); (2) verify no URL is BOTH redirected AND 404'd (would indicate a routing config conflict); (3) request validation in GSC after pushing the redirect rules. Affected URLs sample: <list>. Locale clusters: <locale_prefix_clusters>. Shared prefixes with redirect finding: <co_occurrence_with_sub_dim_5>."`
  - **When user supplied a known-bad-urls.txt file (Step 1.6 4th URL Inspection source):** Append to either branch: `"User-supplied URLs from .seo-data/gsc/known-bad-urls.txt contributed N of the affected URLs — confirming the user-pasted GSC export was inspected this run."`
  - **Default (no rename, no co-occurrence):** `"Either restore the affected pages or remove these entries from sitemap.xml. If these URLs are old content that's been deprecated, add 301 redirects to the appropriate new locations (canonical URL or category index page) — Google will continue crawling them for months otherwise, wasting crawl budget."`

### 5. `redirect_hygiene` (URL Inspection: `coverageState == "Page with redirect"`)

**Trigger:** ≥1 matched.

**Cluster:**

- `severity`: `medium` if count < 50; **`high`** if count ≥ 50 (matches sub-dim 2/3 tiering pattern). **Calibration evidence:** burakarik6 dogfood (2026-05-26) surfaced 838 affected URLs in this sub-dim, with Google sending a "New reason preventing your pages from being indexed: Page with redirect" email + a validation-failed notice. The original fixed-`medium` severity under-called that scale. When the user gets Google emails on this reason, count is almost always ≥50.
- `certainty`: `1.0`
- `effort_estimate`: `small` (pure sitemap regeneration) or `medium` (when canonical/hreflang config also needs fixing — see locale-prefix-cluster detection below)
- `title`: `"<N> sitemap URLs point to redirect destinations (sitemap hygiene)"`. Append `" — likely i18n canonical mismatch"` when locale-prefix clustering detected.
- `evidence`: in addition to standard per-URL diagnostics, when affected URLs cluster by locale prefix include `locale_prefix_clusters` map. Detect by splitting each affected URL's path on `/`, taking the first segment if it matches a 2-3-char locale code (`en`, `tr`, `fr`, `de`, `es`, `it`, `pt`, `ja`, `zh`, `ko`, `ar`, etc.) or empty (bare path). When **≥2 distinct locale prefixes each account for ≥30% of the affected count**, surface as `locale_prefix_clusters: {en: 312, tr: 287, bare: 239}` — strong signal for i18n canonical/redirect collision (same content reachable at multiple URL patterns; sitemap declares non-canonical variants).
- `recommended_action`:
  - **Default (no locale clustering):** `"Replace these sitemap entries with their final destinations. Redirect-chain URLs in sitemap waste crawl budget. Sample: <list>."`
  - **When locale-prefix clustering detected:** `"Affected URLs cluster by locale prefix — this is a classic i18n canonical/redirect collision. Same content is reachable at multiple URL patterns (e.g., /photo/foo, /en/photo/foo, /tr/photo/foo) and the server redirects between them, but sitemap.xml declares the non-canonical variants. If you recently received a GSC 'New reason preventing your pages from being indexed: Page with redirect' or 'Validation failed' email, this is the corresponding signal. Fix path: (1) pick ONE canonical URL pattern (usually locale-prefixed: /en/* + /tr/*, not bare /*); (2) drop non-canonical variants from sitemap.xml; (3) verify <link rel='canonical'> matches sitemap-declared URLs on every page; (4) verify <link rel='alternate' hreflang='...'> tags align with the canonical pattern; (5) resubmit sitemap.xml + request validation in GSC. Affected URLs sample: <list>. Locale-cluster breakdown: <locale_prefix_clusters>."`

### 6. `canonical_conflict` (URL Inspection: `coverageState` matches "Duplicate, Google chose different canonical" / "Duplicate without user-selected canonical")

**Trigger:** ≥1 matched. The API gives `googleCanonical` and `userCanonical` directly — strong signal for canonical disambiguation.

**Per-URL findings** (cap 5), or cluster if N > 5:

- `severity`: `high`
- `certainty`: `0.85`
- `effort_estimate`: `medium`
- `title`: per-URL: `"Google chose different canonical for <URL>: <googleCanonical>"`. Cluster: `"<N> URLs where Google rejected the declared canonical"`.
- `evidence`: `google_canonical`, `user_canonical`, `crawled_as` populated directly from `indexStatusResult` fields
- `recommended_action`: `"Compare <userCanonical> against <googleCanonical> for each URL. Common causes: hreflang misconfig, duplicate-content cluster, soft-duplicate variations (trailing slash, params). The per-URL evidence shows Google's pick directly — no need to use GSC's URL Inspection tool separately."`

### 7. `blocked_access` (URL Inspection: `coverageState` matches "Blocked..." / "Alternate page with proper canonical tag" / "Excluded by 'noindex' tag")

**Trigger:** ≥1 matched. Usually intentional.

**One finding per blocking subtype** (alt-canonical / robots / 403 / 4xx / noindex — max 5):

- `severity`: `low`
- `certainty`: `0.6`
- `effort_estimate`: `small`
- `title`: e.g., `"<N> inspected URLs blocked by 403 (likely intentional)"`
- `evidence`: `indexing_state` field (`INDEXING_ALLOWED`/`BLOCKED_BY_META_TAG`/`BLOCKED_BY_HTTP_HEADER`/`BLOCKED_BY_ROBOTS_TXT`) carried per-URL
- `recommended_action`: `"Verify these are intentionally blocked. If any should be public, fix the access rule. Otherwise no action needed — these URLs are correctly excluded from Google's index."`

### 8. `soft_404` (URL Inspection: `coverageState == "Soft 404"`, with `pageFetchState == SOFT_404`)

**Trigger:** ≥1 matched.

**Cluster:**

- `severity`: `medium`
- `certainty`: `0.9`
- `effort_estimate`: `medium`
- `title`: `"<N> of <total_inspected> inspected URLs return 200 but Google detected empty/error content (soft 404)"`
- `recommended_action`: `"Visit each URL — pages may load with stub/placeholder/error content that returns 200. Fix the rendering or set proper 404 status. Sample: <list>."`

### 9. `server_errors` (URL Inspection: `coverageState == "Server error (5xx)"`, with `pageFetchState == SERVER_ERROR`)

**Trigger:** ≥1 matched.

**Cluster + always high-priority:**

- `severity`: `high`
- `certainty`: `1.0`
- `effort_estimate`: `medium`
- `title`: `"<N> of <total_inspected> inspected URLs returned 5xx errors when Google crawled (site reliability signal)"`
- `recommended_action`: `"Investigate server logs around the lastCrawlTime timestamps. Common causes: deployment-window errors, timeouts on heavy pages, dependency outages. Sample: <list>."`

### 10. `ctr_opportunity` (from Q2 pages digest)

**Dual trigger (S31 dogfood fix):**

1. **Standard band:** rows with `impressions >= 500 AND ctr < (median_ctr * 0.5) AND 5.0 <= position <= 20.0`.
2. **High-volume override:** rows with `impressions >= 10000 AND ctr < 0.005` — regardless of position.

**Why the override.** The S31 dogfood surfaced `/en/article/smartphone-vs-mirrorless-2026` at 59,679 impressions, position 4.65, CTR 0.28%. The original trigger excluded it because position 4.65 is "above the 5-20 band" — but the orchestrator immediately overrode and flagged it as `#1 opportunity` manually. A page that generates 59,679 monthly impressions at 0.28% CTR is THE most actionable finding regardless of position. The override codifies this: at ≥10,000 impressions and <0.5% CTR, the title/meta is so misaligned with query intent that position doesn't matter.

**Per-URL findings** (cap 5; high-volume-override findings sort first):

- `severity`: `medium` for standard band, **`high`** for high-volume-override (the volume-weighted impact is much bigger)
- `certainty`: `0.7` for standard band, **`0.85`** for high-volume-override (catastrophic CTR is hard signal)
- `effort_estimate`: `small`
- `impressions`, `clicks`, `ctr`, `position` populated
- `trigger_reason`: `"position_band"` OR `"high_volume_anomaly"` (parseable field for the report's #1-opportunity ordering)
- `title`:
  - Standard: `"CTR opportunity on <URL> (<X>K impressions, <Y>% CTR vs <Z>% median, pos <P>)"`
  - High-volume-override: `"⚠ CTR CATASTROPHE on <URL> (<X>K impressions, <Y>% CTR @ pos <P> — title/meta misaligned with query intent)"`
- `recommended_action`: `"Rewrite <title> + <meta name='description'> to be more compelling. Audit top GSC queries for the page (Search Analytics → Queries tab filtered by Page) — front-load query intent in the title, mirror query phrasing in the meta description's first 110 chars (mobile SERP truncation). Target CTR: at least median (<Z>%) for standard-band; >1% for high-volume-override cases."`

### 11. `position_band_opportunity` (from Q1 queries digest)

**Trigger:** rows with `position` between 5.0 and 20.0 inclusive AND `impressions >= 100` (Q1 already filters server-side via client-side post-processing).

**Per-query findings** (cap 5):

- `severity`: `medium`
- `certainty`: `0.7`
- `effort_estimate`: `medium`
- `impressions`, `position`, `clicks` populated
- `title`: `"Query '<query>' ranks at position <X.Y> with <N> impressions — position-band opportunity"`
- `recommended_action`: `"Identify which page ranks for this query (use GSC's Pages tab filtered by query). Improve on-page signals: H1/title alignment, content depth, internal links from related pages, schema markup. Moving from position 10 → 5 typically 3-5x's clicks."`

### 12. `traffic_orphan` (Q2 pages digest ∩ sitemap)

**Trigger:** URLs in sitemap.xml that **do not appear** in Q3's `url_impressions_map` (i.e., 0 impressions in the lookback window).

**Cluster into one finding** (only if count >=5):

- `severity`: `low`
- `certainty`: `0.6`
- `effort_estimate`: `medium`
- `affected_urls`: top 10 by document order
- `title`: `"<N> sitemap URLs received 0 impressions in GSC's data window (traffic orphans)"`
- `recommended_action`: `"Audit these pages — they're indexed (in sitemap) but no one's finding them. Options: improve content + internal linking, remove from sitemap if they shouldn't rank, or accept as legitimate low-traffic pages. Sample: <list>."`

### 13. `brand_query_anomaly` (from Q1 queries digest — S31 dogfood fix)

**Codified after S31 dogfood** caught the orchestrator emergently detecting "burak arık" at pos 7.91 with 1.93% CTR as a brand-query displacement signal. Brand queries SHOULD rank at position 1 with CTR >30%; when they don't, it's a hard entity-recognition deficit — Google can't unambiguously identify your brand. Almost always traces to fragmented Schema (Person `@id` split across templates, missing `Person.sameAs` Wikidata link, no Organization schema).

**Brand-name resolution** (orchestrator runs at Step 1, passes to subagent):

1. **Primary:** parse `Person.name` / `Organization.name` from any JSON-LD in source files (Grep `"name"` within `<script type="application/ld+json">` blocks).
2. **Secondary:** parse the `## Project Overview` section of `CLAUDE.md` for first proper-noun phrase (e.g., "**burakarik6** — Photography portfolio site for Burak Arık").
3. **Tertiary:** infer from `package.json` `name` or repo name as last resort (lowest signal — repo names like `burakarik6` are weak brand matches).

Pass the brand name + 1-2 aliases (e.g., `"Burak Arık"` + `"burakarik"` + `"burak arik"` to catch diacritic-normalized search queries) to the helper script.

**Trigger:** Q1 query strings (case-insensitive) containing any brand alias as a substring AND (`position > 3.0` OR `ctr < 0.10`). The `>3.0` threshold is permissive — brand queries should ALWAYS be position 1; pos 2-3 is borderline (acceptable when competing brands share the name). CTR <10% on a brand query is catastrophic — searchers typing your name aren't clicking.

**Per-anomaly findings** (cap 3 — usually only 1-2 brand-name variants surface):

- `severity`: `high` (entity-recognition deficits compound across every GEO/SEO downstream signal)
- `certainty`: `0.95` (this is hard evidence — Google's own ranking + click data)
- `effort_estimate`: `medium`
- `impressions`, `position`, `clicks`, `ctr`, `query`, `matched_alias` populated
- `cross_link_findings`: array of related finding IDs from this run — populate with any `schema_validation` finding referencing `Person.@id` AND any `eeat` finding referencing `Person.sameAs` Wikidata. Surfaces the causal chain to the user.
- `title`: `"⚠ Brand query '<query>' ranks at pos <P> with <C>% CTR — entity-recognition deficit (Google can't unambiguously identify <brand>)"`
- `recommended_action`: `"Brand queries should rank at position 1 with CTR >30%. Three root causes, in order of impact: (1) Add Wikidata entity to Person.sameAs[] across ALL Person Schema blocks (homepage / about / article / guide / contact — same @id everywhere). Create a Wikidata Q-item if one doesn't exist yet. (2) Unify Person @id across all templates — split #photographer vs #author creates two distinct entity nodes Google can't stitch. (3) Add Organization Schema with logo + sameAs[] to the homepage publisher slot. Cross-link to findings: <cross_link_findings>."`

**Why this matters more than ranking band findings.** Sub-dims 10 (CTR opportunity) and 11 (position-band opportunity) target per-page on-page optimization. Sub-dim 13 targets entity-level recognition — the prerequisite signal that determines how AI Overviews + LLM retrievers attribute citations. The 2026 brief consistently flags entity disambiguation as the highest-leverage GEO investment; this sub-dim makes the symptom visible.

**No false-positive risk** when the brand name resolution is wrong. If the orchestrator picks the wrong brand name (e.g., resolves to "Photography" because it's the first proper noun in CLAUDE.md), Q1 queries matching "photography" would be common search-intent queries, NOT brand queries — they wouldn't trigger the anomaly threshold (CTR would be normal-low across the position band). Defensive design: the trigger only fires when both name-match AND ranking-anomaly conditions hold.

### 14. `deindex_regression` (snapshot diff — orchestrator-emitted)

**Codified after burakarik6 dogfood (Session 34, 2026-05-26):** the trigger that surfaces "URLs deindexed since last run" — the early-warning loop catching Google's "New reason preventing your pages from being indexed" / "Validation failed" emails BEFORE they hit the user's inbox. Distinct from sub-dims 2-9 which surface the *current* state per inspected URL; sub-dim 14 surfaces *state transitions* across runs.

**Source:** orchestrator-emitted in SKILL.md Step 1.6.13 (NOT the seo-gsc-insights subagent — the snapshot diff lives in the orchestrator since it spans runs, and the finding is emitted directly into the findings pool). The subagent's catalog stays at sub-dims 1-13; the catalog total of 14 reflects sub-dim 14 as the orchestrator-emitted addition.

**Mechanism:** every run writes a snapshot of `{url → coverageState}` for all inspected URLs to `.seo-data/gsc/snapshots/<YYYY-MM-DDTHHMMSS>-<commit_sha7>.json` (Step 1.6.13.1). On the next run, the orchestrator finds the most-recent prior snapshot (Step 1.6.13.2), diffs it against the current run's inspections (Step 1.6.13.3 via `gsc-parse-helper.py regression`), and emits sub-dim 14 findings for URLs whose coverageState flipped from indexed to non-indexed.

**Trigger transitions** (each emits as evidence in the sub-dim 14 finding):

| Previous state | Current state | Transition class | Default severity |
|---|---|---|---|
| `Submitted and indexed` | `Crawled - currently not indexed` | quality regression | high |
| `Submitted and indexed` | `Discovered - currently not indexed` | crawl-budget regression | high |
| `Submitted and indexed` | `Page with redirect` | canonical/i18n regression (burakarik6 pattern) | high |
| `Submitted and indexed` | `Soft 404` | rendering regression | high |
| `Submitted and indexed` | `Not found (404)` | broken-URL regression | high |
| `Submitted and indexed` | `Server error (5xx)` | availability regression | **critical (always)** |
| `Submitted and indexed` | `Duplicate, Google chose different canonical` | canonical regression | high |
| `Submitted and indexed` | `Blocked due to access forbidden (403)` | access regression (often intentional) | medium |
| (any non-indexed) | `Submitted and indexed` | RECOVERY | — (info footer line, NOT a finding) |
| (identical) | (identical) | no change | — |

**No-prior-snapshot case:** first run for this property has no previous snapshot. Emit no findings; footer line: `Index Coverage snapshots: first run for this property. Regression detection activates on next /seo-review run.`

**Finding shape** (when ≥1 negative transition detected — one finding per run, all transitions clustered):

- `severity`: starts from the highest-severity transition class. **Escalate to `critical`** if (a) any `Server error (5xx)` transition present, OR (b) transition count ≥ 20 URLs, OR (c) transition count ≥ 10% of inspected URLs.
- `certainty`: `0.95` (Google's own state — hard signal)
- `effort_estimate`: `medium` by default; `large` when path_clusters span ≥3 distinct prefix groups (suggests broader routing change requiring multi-area audit)
- `affected_urls`: top 10 by transition class priority (server errors first, then quality regressions, then redirect/canonical)
- `title`: `"⚠ <N> URLs deindexed since <previous-run-date> (<previous_commit_sha7>) — possible Google validation failure or quality-signal regression"`
- `evidence`:
  - `previous_snapshot`: `{date: "YYYY-MM-DD", commit_sha: "abc1234", url_count: N}`
  - `current_snapshot`: `{date: "YYYY-MM-DD", commit_sha: "def5678", url_count: M}`
  - `transitions`: array of `{url, previous_state, current_state, transition_class}` records (cap 20 inline; full set lives in the snapshot files)
  - `path_clusters`: when ≥3 transitions share a path prefix (split on `/` after domain; group by 1-3 leading segments), surface as `{prefix: count}` map — high-signal for routing-change root cause (S30 lesson: when transitions cluster, the cause is usually one commit)
  - `git_correlation`: when `path_clusters` prefixes match touched paths in Step 1.5's 35-day git digest, append the matching commits (max 3) with short subjects + dates. Bridges the regression to the likely-causal code change.
  - `recovery_count`: count of URLs that improved (any non-indexed → `Submitted and indexed`) since previous run — surfaces in the footer info line, not in the finding's main evidence
- `cross_link_findings`: array of related finding IDs from this run — populate with sub-dim 5 (`redirect_hygiene`) when `Page with redirect` transitions present, sub-dim 4 (`not_found_404`) when `Not found (404)` transitions present, sub-dim 9 (`server_errors`) when `Server error (5xx)` transitions present
- `recommended_action`: tiered by transition class (orchestrator picks the most severe applicable tier; multiple tiers can chain):
  - **Always include the framing line:** `"If you've seen a Google Search Console 'New reason preventing your pages from being indexed' or 'Validation failed' email recently, this is the corresponding signal. The snapshot diff shows what flipped state since <previous-run-date>."`
  - **Server error transitions (critical):** `"<N> URLs that were indexed are now returning 5xx — immediate investigation needed. Check server uptime + deploy logs around <previous-run-date>. Cross-reference: sub-dim 9 server_errors finding this run."`
  - **Page with redirect transitions:** `"Likely canonical/i18n config change. Cross-reference with sub-dim 5 (redirect_hygiene) finding in this run for locale-prefix-cluster diagnosis. Fix path: (1) identify routing/canonical change in git history around <previous-run-date> (cross-link: git_correlation evidence); (2) update sitemap.xml entries to canonical URLs; (3) verify <link rel='canonical'> and hreflang tags."`
  - **404 transitions:** `"<N> URLs that were indexed are now 404. Bulk redirect or restore. Cross-link: git_correlation evidence often points to the rename commit."`
  - **Quality regressions (crawled/discovered not indexed):** `"Recent content changes may have triggered Google's content-quality reassessment. Audit the affected URLs against top-ranking competitors — common causes: thin content additions, removed citations, removed author bylines, truncated articles."`
  - **Canonical regressions (Google chose different canonical):** `"Declared canonical no longer matches Google's pick. Verify <link rel='canonical'> attribute on affected pages — common causes: duplicate content variants, hreflang misconfig, params/trailing-slash variations."`

**Path-cluster detection algorithm:** group transitions by path prefix. Split each URL on `/` after domain, take prefixes of length 1, 2, and 3 segments. For each prefix length, count how many transitions share that prefix. Surface the **largest 3 clusters where count ≥ 3** as `path_clusters`. Cross-reference with Step 1.5's git digest: for each cluster prefix, check if any commit in the 35-day window touched source paths that map to URLs matching the prefix (via `page_type_map` reverse-lookup). When matched, append the commits to `git_correlation` (max 3 commits, short subjects + dates).

**Inflection-point footer line** (independent of sub-dim 14 finding emission, surfaces even when no transitions detected):

When prior snapshot exists, compute `coverageState` count deltas for the top-3 reason categories (e.g., crawled_not_indexed, redirect_hygiene, not_found_404). For each category, render a footer line:

```
Page-with-redirect count: 838 (delta +47 since previous run on 2026-05-13 [commit 5a441d1]). ⚠ Climbing fast — consider running /seo-review with --plan to triage.
Crawled-not-indexed count: 142 (delta -8 since previous run). Improving.
```

Threshold for ⚠ warning: absolute delta ≥ 20 URLs OR relative delta ≥ 10% of prior count. Otherwise render without warning.

When previous run was on the same commit (rare — usually means user ran `/seo-review` twice without code change), suppress the delta line entirely and surface a footer note: `Snapshot delta suppressed: previous run on same commit (<sha>).`

**Why this sub-dim matters more than the per-URL sub-dims 2-9.** Sub-dims 2-9 surface the *current* state; sub-dim 14 surfaces *what just changed*. The change is the actionable signal — pages stable in `Submitted and indexed` for months suddenly flipping is what triggers Google's validation-failure emails. Without sub-dim 14, the user only learns about the regression from Google's email; with it, `/seo-review` catches the regression at the next run after the breaking commit (typically 24-72 hours before Google emails).

---

## Output to shared context

After Step 1.6 completes, the orchestrator passes a structured GSC block to all dispatched subagents (3 when `gsc_mode: disabled`, 4 when enabled) as part of the Step 5 base shared-context. **See `SKILL.md` Step 1.6.11 for the canonical block format.**

The `seo-gsc-insights` subagent is the primary consumer. The other 3 subagents use `url_impressions_map` for traffic_weight when ranking their own findings; the rest is informational.

---

## Hard rules (orchestrator side)

- **Never block runs.** Every failure mode (missing config, gcloud absent, ADC missing, API 4xx/5xx, quota exhausted) logs to footer and continues.
- **Never modify .gitignore outside the sentinel block.** Idempotency check via start-marker Grep.
- **No silent fallback** to a different ingestion path when API fails — print the error loudly, skip the affected signal.
- **Digest cap is 50 rows per signal** — Q1 and Q2 enforce server-side via API rowLimit + client-side top-50 sort.
- **URL Inspection budget is 200/run hard cap** — well under the 2,000/day per-property quota. Budget split: 80 impressions-top + 20 git-changed + 100 (user-supplied + sitemap-orphan, shared bucket; user-supplied up to 100, sitemap-orphan fills remainder). See `gsc-api-queries.md` "URL Inspection — selection algorithm".
- **Snapshot retention 30 days.** `.seo-data/gsc/snapshots/<YYYY-MM-DDTHHMMSS>-<commit_sha7>.json` files are pruned by `find -mtime +30` at Step 1.6.1's Turn 1 batch (mirrors the cache prune pattern). Snapshots are skill-auto-managed; users shouldn't touch them. Reproducible from URL Inspection cache if deleted.
- **Score impact stays heuristic.** GSC findings carry `score_impact: 0` (see `rubric.md` for the orchestrator-side enforcement). Sub-dim 14 (`deindex_regression`) is no exception — the headline /100 score stays comparable across runs.
