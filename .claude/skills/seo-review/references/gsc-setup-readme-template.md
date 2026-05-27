# GSC Setup README Template

This is the **template content** that the `/seo-review` orchestrator auto-writes to `.seo-data/gsc/README.md` on first detection (when `.seo-data/gsc/` exists but `README.md` inside it doesn't).

It's written verbatim — no variable substitution. The target audience is the **human user** who's about to configure GSC API access, not Claude.

---

## Template content (begin)

```markdown
# Google Search Console — API Configuration

This folder configures `/seo-review`'s Search Console API integration.
Drop a `config.yaml` here (template below) and the next `/seo-review` run
will produce traffic-aware recommendations from your GSC data.

## What does the skill do with this data?

- Identifies high-impressions, low-CTR pages (title/meta rewrite targets)
- Surfaces queries where you rank at position 5-20 (highest-leverage band
  for on-page optimization)
- Catalogs pages Google crawled-but-didn't-index (content quality signals)
- Detects 404 clusters that match recent code renames (auto-flags bulk
  redirect opportunities)
- Reranks all findings by traffic impact (impressions-weighted)

The /100 score does **not** change based on this data — GSC is informational.
Your `docs/seo-history.md` stays comparable across runs whether GSC is
configured or not.

## Setup (one-time, ~5 minutes)

### Prerequisites

1. **A GCP project.** Any GCP project will do — the Search Console API is
   free within quota (1,200 QPM Performance / 2,000 URLs/day for URL
   Inspection). List existing projects with `gcloud projects list`, or
   create one at https://console.cloud.google.com/ if you don't have one.
2. **`gcloud` CLI installed.** Install: https://cloud.google.com/sdk/docs/install.
   On Windows, the installer adds `gcloud` to PATH.
3. **Google account with verified GSC property access.** The Google
   account you sign in with during `gcloud auth` must be the same one
   that has the GSC property registered + verified.

### Enable the API on your project

4. Enable Search Console API on the project that will track quota:
   ```
   gcloud services enable searchconsole.googleapis.com --project=<your-gcp-project-id>
   ```

   This is required even though Search Console API is free — Google Cloud's
   quota infrastructure needs the API explicitly enabled on the billable
   project. Skipping this step returns HTTP 403 SERVICE_DISABLED on first call.

### Authenticate

5. Run once (opens browser for OAuth):
   ```
   gcloud auth application-default login \
     --scopes=https://www.googleapis.com/auth/webmasters.readonly,https://www.googleapis.com/auth/cloud-platform
   ```

   The explicit `--scopes` flag is important — Search Console API often
   accepts default `cloud-platform` scope, but this is undocumented and
   has broken in the past. Explicit `webmasters.readonly` is durable.

6. **Set quota project (required, not optional):**
   ```
   gcloud auth application-default set-quota-project <your-gcp-project-id>
   ```

   Google Cloud APIs called via user-credential ADC require a quota project
   to bill against. The skill reads this value and sends it on every API call
   via the `x-goog-user-project` header. Without it, all calls return
   HTTP 403 SERVICE_DISABLED — even when auth is otherwise valid.

### Configure `/seo-review`

7. Create `.seo-data/gsc/config.yaml`:

   ```yaml
   site_url: sc-domain:example.com    # or "https://example.com/" for URL-prefix properties

   # Optional:
   # lookback_days: 90                # 7-365, default 90
   ```

   The exact `site_url` format must match what's registered in GSC.
   Check at https://search.google.com/search-console > Settings > Property settings.
   - Domain properties look like: `sc-domain:example.com`
   - URL-prefix properties look like: `https://example.com/` (with trailing slash)

8. Run `/seo-review`. The "Detected:" line should now say
   `Mode: heuristic + GSC (Search Console API — ...)`.

### Quick verification (optional)

You can sanity-check auth + quota project before running the skill. PowerShell:

```powershell
$TOKEN = gcloud auth application-default print-access-token
$QUOTA = (Get-Content "$env:APPDATA\gcloud\application_default_credentials.json" | ConvertFrom-Json).quota_project_id
Invoke-RestMethod -Method Get `
  -Uri "https://www.googleapis.com/webmasters/v3/sites" `
  -Headers @{Authorization = "Bearer $TOKEN"; "x-goog-user-project" = $QUOTA} | `
  ConvertTo-Json -Depth 5
```

Bash (works without `jq` — uses bash core grep + sed for JSON-flat-field extraction):

```bash
TOKEN=$(gcloud auth application-default print-access-token)
ADC_DIR=$(gcloud info --format="value(config.paths.global_config_dir)")
QUOTA=$(grep -oE '"quota_project_id"[[:space:]]*:[[:space:]]*"[^"]+"' "$ADC_DIR/application_default_credentials.json" | head -1 | sed -E 's/.*"([^"]+)"$/\1/')
curl -s -H "Authorization: Bearer $TOKEN" \
     -H "x-goog-user-project: $QUOTA" \
     "https://www.googleapis.com/webmasters/v3/sites"
```

(If you have `jq` installed, pipe the curl output through `| jq` for pretty-printed JSON. Plain output is fine for verifying.)

Expected: a JSON object with a `siteEntry` array listing every GSC property
your account can read. Empty array means no properties on this account.

### Verify the first run

- API auth probe: `gcloud auth application-default print-access-token` should print a token. The skill calls `GET /webmasters/v3/sites` at start of each run to verify access; failures surface in footer with specific remediation.
- Performance: 3 `searchanalytics.query` calls per run (queries digest, pages digest, url_impressions_map).
- Indexing: up to 200 `urlInspection.index.inspect` calls per run (4-slice mix: 80 high-impression URLs + 20 recently-changed paths + up to 100 user-supplied URLs from `known-bad-urls.txt` + sitemap-orphan URLs filling the rest of the shared 100-slot bucket — sitemap-orphan catches deindex risks early, before Google emails; user-supplied catches URLs no longer in your sitemap that Google still remembers). Well under the 2,000/day per-property quota.
- Index Coverage snapshots: one `.json` written to `.seo-data/gsc/snapshots/` per run, retained 30 days. Next run diffs against the prior snapshot to surface URLs that flipped from indexed → not-indexed (sub-dim 14 `deindex_regression` — the early-warning loop catching Google's "Validation failed" emails before they hit your inbox).

## Privacy

This folder is **automatically added to `.gitignore`** the first time the
skill detects it. `config.yaml` contains `site_url` which is property-
identifying (not secret, but worth keeping private by default). If you
want to commit anyway (e.g., team-shared config), remove the
`.seo-data/gsc/` line from `.gitignore`.

## Folder layout

```
.seo-data/gsc/
├── README.md            (this file)
├── config.yaml          (API configuration — site_url + optional lookback_days)
├── known-bad-urls.txt   (optional, user-authored — paste problem URLs from GSC export)
├── cache/               (auto-managed API response cache; 24h TTL — safe to delete)
└── snapshots/           (auto-managed coverage-state history; 30d retention — needed for regression detection)
```

The `cache/` and `snapshots/` subdirectories are created by the skill on first GSC-enabled run. **Cache** holds JSON responses from `searchanalytics.query` (Q1/Q2/Q3) and `urlInspection.index.inspect` so reruns within 24 hours don't burn API quota; pruned at 7 days. **Snapshots** record `{url → coverageState}` per run for sub-dim 14 regression detection; pruned at 30 days. You don't need to manage either — both are skill-managed and reproducible from the API on demand (snapshots regenerate from cache on the same run; cache regenerates from API on next run).

### Optional: `known-bad-urls.txt` — fallback for URLs the algorithmic slices can't see

#### Important context: the Search Console API does NOT expose the Page Indexing report

The GSC web UI lists URLs affected by each coverage reason ("Page with redirect", "Not found (404)", "Crawled - currently not indexed", etc.). But **the Search Console API has no endpoint that returns this list**. The only API endpoints are:

| Endpoint | What it returns | What it does NOT return |
|---|---|---|
| `searchanalytics.query` | Performance metrics (impressions/clicks/CTR/position) per query/page | Anything about indexing state |
| `urlInspection.index.inspect` | Per-URL indexing diagnostics (`coverageState`, `pageFetchState`, canonicals, last crawl, etc.) — **for a URL you provide** | A list of URLs to inspect |
| `sites.list` | Your verified properties | URLs within a property |
| `sitemaps.list` / `sitemaps.get` | Submitted sitemap metadata | URLs inside a sitemap |

There is **no `pageIndexing.list`** endpoint or equivalent, despite long-standing community feature requests. This is a Google product decision, not a skill limitation. The Page Indexing report's URL lists in the web UI are rendered from internal Google systems Google chose not to expose publicly.

#### How the skill works around this — 4-slice URL Inspection

For `urlInspection.index.inspect` to tell us "this URL is 404/redirect/etc.", we must already know the URL exists. The skill's URL Inspection budget (200/run) draws from four sources in `Step 1.6` of the orchestrator:

| Source | Budget | Catches |
|---|---|---|
| **Impressions map** (`searchanalytics.query` Q3) | up to 80 | URLs with any search traffic in the lookback window |
| **35-day git scan** (resolves rename old_path AND new_path) | up to 20 | URLs from files renamed/touched in the last 35 days |
| **Sitemap-orphan slice** (URLs in sitemap.xml but NOT in impressions) | up to 100 (shared) | URLs your sitemap declares but Google didn't surface as performant — but ONLY URLs **still in your current sitemap**. URLs your codebase has already removed from sitemap (typical for properly-handled deindexed content) are NOT caught by this slice. |
| **`known-bad-urls.txt`** (this file) | up to 100 (shared with sitemap-orphan) | URLs **not in your current sitemap** (codebase removed them) AND not in impressions AND not git-changed recently — typically deindexed URLs from GSC's "Page Indexing" reports that Google still remembers but your codebase no longer serves |

The "shared 100-slot bucket" means user-supplied URLs take precedence over sitemap-orphan within their bucket — paste 30 user URLs, sitemap-orphan gets 70; paste 100 user URLs, sitemap-orphan gets 0; paste 0 user URLs, sitemap-orphan gets 100. Dedup precedence: `impressions > git > user-supplied > sitemap-orphan`.

**Important nuance on sitemap-orphan's coverage of redirects.** Earlier guidance said "redirects are covered by sitemap-orphan automatically — only paste 404s into known-bad-urls.txt." That's only true if your codebase keeps deindexed/redirected URLs in `sitemap.xml`. If your codebase actively rotates them out (the cleaner approach for sitemap hygiene), sitemap-orphan can't see them either — those URLs are in NONE of the four sources except `known-bad-urls.txt`. Rule of thumb: if a GSC validation-failed email references URLs that aren't in your current sitemap, paste them here regardless of whether the reason is "404" or "Page with redirect".

#### When you need `known-bad-urls.txt`

The file is a **fallback for the gap**, not the primary workflow. You need it when a problem URL **is NOT in any of the three algorithmic sources**:

- "Not found (404)" URLs that are NOT in your current sitemap (Google remembers them from a previous indexing cycle, the codebase no longer serves them, and the rename happened >35 days ago so git scan misses them)
- URLs orphaned via CMS edits not visible in git history (e.g., content unpublished in Sanity, slug renamed in Contentful)
- Specific URLs flagged in a GSC "Validation failed" email that don't appear in any of the three algorithmic sources

#### When you DON'T need it

- **URLs in your current sitemap** → sitemap-orphan slice handles them automatically. This includes most "Page with redirect" cases (URL is in sitemap, server redirects it) and "Submitted URL not found (404)" cases (URL was submitted via sitemap, server returns 404).
- **URLs with any search impressions** in the lookback window → impressions-top slice handles them
- **URLs from files renamed in the last 35 days** → git-changed slice handles both old and new paths

#### Recommended workflow: try without the file first

Run `/seo-review` once with empty (or missing) `known-bad-urls.txt`. Review the URL Inspection budget log in the report footer — it shows the source breakdown and how many URLs each slice contributed. If specific problem URLs (e.g., from a GSC validation-failed email) did NOT appear in the inspected set, only THEN paste those specific URLs into the file for the next run.

**Don't paste your entire GSC export blindly** — the file is for the gap, not the bulk. The algorithmic slices already cover most cases; pasting redundantly just consumes the user-supplied budget on URLs that would be inspected anyway.

#### Format

```
# Comments (lines starting with #) are ignored.
# Blank lines are ignored.
# One URL per line.

https://example.com/article/old-slug
https://example.com/en/article/another-old-slug
https://example.com/tr/gallery/legacy-page
```

#### You don't need to tag URLs by reason — the skill discovers it automatically

The file is a **flat URL list**, intentionally. You don't separate URLs by `coverageState` (404 vs. redirect vs. canonical-conflict vs. soft-404 etc.) — paste them all together in any order. Here's why:

1. **You provide the URL list** (the API can't generate it — see the "API does NOT expose Page Indexing" section above).
2. **The API discovers the reason** — `urlInspection.index.inspect` returns each URL's current `coverageState` directly. The skill maps that to the right sub-dimension via the 9-reason lookup table in `references/gsc-api-queries.md`.
3. **Findings get clustered by reason automatically** — URLs returning "Page with redirect" land in sub-dim 5 (`redirect_hygiene`); "Not found (404)" lands in sub-dim 4 (`not_found_404`); "Crawled - currently not indexed" lands in sub-dim 2 (`crawled_not_indexed`); etc. across all 9 reason buckets.

So the workflow is: **you provide URLs, the API tells the skill the reason, the skill clusters by reason.** A URL from your "Page with redirect" GSC export and a URL from your "Not found (404)" GSC export can sit in the same file with no metadata — when the skill inspects them, the API will return their current states and the cluster sorting happens automatically.

**Mixed-source example** (comments are purely for your own bookkeeping — the parser strips them):

```
# From "Page with redirect" GSC export (5/26/26)
https://example.com/en/photo/granada-sokaklari
https://example.com/tr/gallery/slovenia

# From "Not found (404)" GSC export (5/26/26)
https://example.com/article/cep-telefon-mu-aynasiz-kamera-mi-2026

# From validation-failed email (5/25/26)
https://example.com/some-other-affected-page
```

In the resulting report, each URL appears under whichever sub-dim its **current** `coverageState` maps to. A URL you pasted under "# Page with redirect" might come back as `"Submitted and indexed"` if it's already been fixed since you pasted it — in which case it generates no finding (you can delete it from the file). A URL pasted under "# Not found (404)" might come back as `"Page with redirect"` if you added a redirect in the meantime — it'll surface under sub-dim 5 in the report, not sub-dim 4, reflecting Google's current view, not what you originally pasted it under.

The `#` comments help **you** track what you pasted, what's resolved, what's still pending. They're for your bookkeeping; the skill ignores them entirely.

#### How to populate (when needed)

1. Run `/seo-review` first WITHOUT this file — review the URL Inspection budget log + Section 3 findings.
2. Identify URLs from your GSC coverage reports that did NOT appear in the inspected set.
3. Open Google Search Console → **Indexing** → **Pages** report.
4. Click the reason of interest (e.g., "Not found (404)", "Page with redirect").
5. Use the **Export** button (top-right) to download as CSV/Google Sheets.
6. Copy ONLY the URLs that weren't already caught by the algorithmic slices into `.seo-data/gsc/known-bad-urls.txt`, one URL per line.
7. Run `/seo-review` again.

#### Caps & behavior

- First 100 entries are inspected per run (the 4th URL Inspection slice — see `references/gsc-api-queries.md`). If your file has >100 URLs, the rest are skipped this run; remove inspected URLs from the file (or wait a day) to inspect the next batch. The skill emits a banner in the report's Suggested Next Actions section when paste size exceeds the cap — you won't miss it.
- Daily quota (2,000 URL Inspections per property, Google-enforced) is the hard cap; the skill's per-run budget is 200.
- URLs in this file take precedence over the sitemap-orphan slice within their shared 100-slot bucket. Pasting 100 URLs claims the entire shared bucket and skips sitemap-orphan for that run — appropriate when triaging a hot deindex incident; suboptimal as a steady-state because sub-dim 14 (`deindex_regression`) needs sitemap-orphan to surface NEW deindex events. Keep the file small once the incident is resolved.
- Findings derived from these URLs will be tagged in the report so you can see which user-pasted URLs surfaced specific coverage states.

#### When to delete entries

Once you've fixed an issue (added a redirect, restored a page, updated content, requested validation), remove the URL from the file. The skill will not inspect it again on subsequent runs unless re-added. Treat the file as a moving target — short list of URLs currently under investigation, not an accumulating log.

## Cache + quota preservation

The 2,000-calls/day URL Inspection quota is the scarce resource. To preserve it across iterative runs:

- **Default behavior:** Every API call is wrapped in a 24h disk cache. Same-day reruns hit cache → zero quota consumed.
- **Force refresh:** `/seo-review --no-cache` bypasses the cache lookup and refetches everything. Fresh responses still get written to cache for the next run. Use when you've pushed a fix and want Google's current view, or when you suspect cached data is wrong.
- **Manual cache reset:** `rm -rf .seo-data/gsc/cache/` — safe; the cache is reproducible from the API on demand.
- **Inspect cache:** `ls -la .seo-data/gsc/cache/` — shows per-call files with timestamps.

The footer of each run reports cache hit/miss stats so you can see how much quota was actually consumed.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Mode says "heuristic-only" despite `config.yaml` filled in | `gcloud` CLI not installed | Install gcloud SDK: https://cloud.google.com/sdk/docs/install |
| Same, with `gcloud` available | ADC not configured | Run `gcloud auth application-default login --scopes=...` (see Authenticate above) |
| Footer says `ADC quota project not set` | Skipped step 6 above | Run `gcloud auth application-default set-quota-project <your-gcp-project>` |
| Footer says `Search Console API not enabled on quota project '<X>'` | Skipped step 4 above | Run `gcloud services enable searchconsole.googleapis.com --project=<X>` |
| Footer says `Search Console API auth failed: 401 UNAUTHENTICATED` | OAuth scope insufficient | Re-run `gcloud auth application-default login` with the `--scopes=https://www.googleapis.com/auth/webmasters.readonly,...` flag |
| Footer says `403 PERMISSION_DENIED` with `SERVICE_DISABLED` in details | API not enabled OR `x-goog-user-project` header missing (skill bug) | Run `gcloud services enable searchconsole.googleapis.com --project=<your-gcp-project>` and `gcloud auth application-default set-quota-project <your-gcp-project>` |
| Footer says `Search Console API access denied: 403 PERMISSION_DENIED` (no SERVICE_DISABLED) | The Google account isn't verified on this GSC property | Verify property ownership in https://search.google.com/search-console > Settings, or switch ADC to an account that owns the property |
| Footer says `site_url '<X>' not in your verified properties` | `site_url` value doesn't match what's registered in GSC | Check exact format at https://search.google.com/search-console > Settings > Property settings. `sc-domain:example.com` for Domain properties; `https://example.com/` (with trailing slash) for URL-prefix |
| Footer says `Config error: nested keys not supported` | `config.yaml` has indented keys | Use flat single-level keys only (`site_url: x` not `gsc:\n  site_url: x`) |
| Footer says `URL Inspection quota exhausted` | Hit 2,000/day per-property cap | Re-run tomorrow — graceful degrade kept the run going. Future reruns within 24h will hit the disk cache and won't consume more quota. |
| First run takes 15-25 seconds | Normal — up to 200 parallel URL inspections + 3 Performance queries | No action needed. Subsequent same-day reruns finish in 1-2 seconds (cache hits, no network). |
| Worried about quota when iterating on a fix | The default 24h disk cache handles this — reruns within the day are free | Just rerun. Use `--no-cache` only when you genuinely need Google's current view (e.g., after pushing a fix and waiting for recrawl). |
| Want to clear cache without running with `--no-cache` | Cache is plain JSON files in `.seo-data/gsc/cache/` | `rm -rf .seo-data/gsc/cache/` — next run starts fresh |

## Removing GSC integration

To go back to heuristic-only mode: delete the `.seo-data/gsc/` folder
(or just `config.yaml`). The next `/seo-review` will note "Mode:
heuristic" and behave exactly as it did before any GSC config was
added.
```

## Template content (end)

---

## Implementation note for the orchestrator

The orchestrator writes this content **once**, on the first detection of `.seo-data/gsc/` without a `README.md` inside it. Subsequent runs do NOT overwrite the README — the user may have edited it (e.g., added project-specific notes). Idempotency check: `Read` the file; if it exists, skip the write.

The template above is the canonical baseline. If this reference file is updated, existing `.seo-data/gsc/README.md` files in user projects do NOT auto-update — they're treated as user-owned content. To force a refresh, the user can delete their README and re-run.
