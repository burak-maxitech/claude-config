# GSC Ingestion — Canonical Reference

Loaded by the orchestrator in **Step 1.6** of `SKILL.md`. This file is the source of truth for:
- Activation conditions (when GSC mode is active vs heuristic-only)
- API ingestion contract — digest shape consumed by subagents
- Setup banner (one-time, sentinel-gated)
- `.gitignore` auto-append rules
- Finding-type catalog (12 sub-dims) populated from Search Console API output

For the **finding output shape**, ranking formulas, and `score_impact: 0` invariant, see `rubric.md` — that file is the contract; this file is the implementation reference. For endpoint inventory + auth setup, see `gsc-api-schema.md`. For SQL-equivalent call templates + URL Inspection selection + `coverageState` → 9-reason lookup table, see `gsc-api-queries.md`.

---

## Activation

GSC mode is **enabled** when all of these conditions hold:

1. `.seo-data/gsc/config.yaml` exists with non-empty `site_url:` key
2. `gcloud` SDK installed (`gcloud --version` returns)
3. ADC authenticated (`gcloud auth application-default print-access-token` returns a token)
4. ADC quota project set (`jq -r .quota_project_id` on `application_default_credentials.json` returns a non-empty project ID — written by `gcloud auth application-default set-quota-project <id>`). The skill sends this value as the `x-goog-user-project` header on every API call.
5. Active probe: `curl GET https://www.googleapis.com/webmasters/v3/sites` with both the ADC token AND `x-goog-user-project` header returns HTTP 200 + valid JSON
6. The configured `site_url` appears in the returned `siteEntry[*].siteUrl` list with a non-`siteUnverifiedUser` `permissionLevel`

Otherwise → **heuristic-only mode**. The skill runs normally; subagents get an empty GSC block; Section 1 banner fires if it's a first encounter (sentinel-gated).

---

## API ingestion contract

When GSC mode is enabled, ingest data from the Search Console API per `gsc-api-queries.md`:

- **Performance**: 3 parallel `searchanalytics.query` calls (Q1 queries digest, Q2 pages digest, Q3 `url_impressions_map`)
- **Indexing**: up to 100 parallel `urlInspection.index.inspect` calls (per-URL; URL selection algorithm picks high-leverage candidates)

### Query execution

All Performance calls dispatch in one parallel Bash turn. URL Inspection calls dispatch in a second parallel turn after Performance (URL selection uses Q3's `url_impressions_map`).

**Token + quota-project caching**: Turn 1's probe already fetched both the ADC token (`gcloud auth application-default print-access-token`) and the ADC quota project (`jq -r .quota_project_id` on `application_default_credentials.json`). Both are reused as shared context across all Turn 2 curl invocations — every call must include `Authorization: Bearer $TOKEN` AND `x-goog-user-project: $QUOTA_PROJECT` headers. Tokens have a 1-hour TTL; a single Step 1.6 dispatch finishes in seconds, so one Turn 1 fetch is reused.

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

## Finding-type catalog (12 sub-dims)

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

**Cluster + routing-rename match** (the bulk-redirect detection):

1. Parse all matched URLs, derive path patterns (e.g., `/blog/2023/post-1`, `/blog/2023/post-2` → cluster `/blog/2023/*`).
2. Cross-reference with Step 1.5's git-changes digest: any commits in the 35-day window touching source paths that *generated* these URLs?
3. If routing-rename match found: emit single bulk-cluster finding with the routing-rename signal in evidence.

- `severity`: `high` (broken URLs at Google's view dilute crawl budget)
- `certainty`: `1.0`
- `effort_estimate`: `small` (bulk 301 redirect or sitemap cleanup)
- `affected_urls`: top 10
- `title`: `"<N> of <total_inspected> inspected URLs return 404 at Google's view"`
- `evidence`: includes `"Routing rename in window: <commit-msg> on YYYY-MM-DD touching <paths>"` when detected
- `recommended_action`: when routing-rename detected: `"Bulk 301 redirects mapping <old-pattern> → <new-pattern> in <framework-config-file>. Plus remove 404 entries from sitemap.xml. Confirm the mapping is 1:1 before bulk-applying."` Otherwise: `"Either restore the affected pages or remove these entries from sitemap.xml."`

### 5. `redirect_hygiene` (URL Inspection: `coverageState == "Page with redirect"`)

**Trigger:** ≥1 matched.

**Cluster:**

- `severity`: `medium`
- `certainty`: `1.0`
- `effort_estimate`: `small`
- `title`: `"<N> sitemap URLs point to redirect destinations (sitemap hygiene)"`
- `recommended_action`: `"Replace these sitemap entries with their final destinations. Redirect-chain URLs in sitemap waste crawl budget. Sample: <list>."`

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

**Trigger:** rows with `impressions >= 500 AND ctr < (median_ctr * 0.5)`.

**Per-URL findings** (cap 5):

- `severity`: `medium`
- `certainty`: `0.7`
- `effort_estimate`: `small`
- `impressions`, `clicks`, `ctr` populated
- `title`: `"CTR opportunity on <URL> (<X>K impressions, <Y>% CTR vs <Z>% median)"`
- `recommended_action`: `"Rewrite <title> + <meta name='description'> to be more compelling. Test against top SERP results for the page's primary queries. Target CTR: at least median (<Z>%)."`

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
- **URL Inspection budget is 100/run hard cap** — well under the 2,000/day per-property quota.
- **Score impact stays heuristic.** GSC findings carry `score_impact: 0` (see `rubric.md` for the orchestrator-side enforcement).
