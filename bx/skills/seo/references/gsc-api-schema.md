# Google Search Console API Schema — Canonical Reference

Loaded by the orchestrator (Step 1.6) when the Search Console API is the configured Performance + Indexing ingestion path. This file is the **source-of-truth endpoint inventory + auth contract + enum reference** that `gsc-api-queries.md` and the SKILL.md dispatcher reference.

For ingestion behaviour, digest shape, and the 14 sub-dim catalog, see `gsc-ingestion.md` (the "API ingestion contract" section is the digest contract). For call templates, see `gsc-api-queries.md`. The skill's config layout is documented in `gsc-setup-readme-template.md` — `site_url` is the single required key in `config.yaml`.

**Schema source:** Google's published API references — [Search Analytics: searchanalytics.query](https://developers.google.com/webmaster-tools/v1/searchanalytics/query) + [URL Inspection: urlInspection.index.inspect](https://developers.google.com/webmaster-tools/v1/urlInspection/index/inspect) + [Sites: list](https://developers.google.com/webmaster-tools/v1/sites/list). Verified against documentation as of 2026-05-15.

---

## Endpoints in scope

The Search Console API exposes three endpoints used by `/bx:seo`:

| Endpoint | Purpose | Queried by the skill? |
|---|---|---|
| `POST https://www.googleapis.com/webmasters/v3/sites/{siteUrl}/searchAnalytics/query` | Performance — queries/pages/impressions/CTR/position | **Yes** (Q1, Q2, Q3) |
| `POST https://searchconsole.googleapis.com/v1/urlInspection/index:inspect` | Per-URL indexing diagnostics — `coverageState`, `pageFetchState`, canonicals, last crawl, mobile usability, rich results | **Yes** (one call per inspected URL, up to 200/run — 4-slice mix of impressions-top + git-changed + user-supplied (`known-bad-urls.txt`) + sitemap-orphan; see `gsc-api-queries.md` selection algorithm) |
| `GET https://www.googleapis.com/webmasters/v3/sites` | List user's verified properties | **Yes** (active auth probe — Step 1.6.1 activation condition 5) |

**Note two different base hosts**: `www.googleapis.com/webmasters/v3` for Search Analytics + Sites; `searchconsole.googleapis.com/v1` for URL Inspection. Same OAuth scope; same ADC token; different quota tracking (see "Quota model" below).

---

## Authentication

### OAuth scope

Single scope required: `https://www.googleapis.com/auth/webmasters.readonly`

This scope provides read-only access to all three endpoints. No write permissions required — the skill never modifies GSC state.

### ADC setup (gcloud SDK)

The skill uses Application Default Credentials (ADC) via the `gcloud` CLI. One-time user setup (4 commands):

```
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/webmasters.readonly,https://www.googleapis.com/auth/cloud-platform

gcloud services enable searchconsole.googleapis.com --project=<your-gcp-project-id>

gcloud auth application-default set-quota-project <your-gcp-project-id>
```

**Why `--scopes` flag is required:** Default ADC scope is `cloud-platform`. Search Console API accepts cloud-platform-scoped tokens for some property/account combinations but this is undocumented behavior and has broken in the past. Explicit `webmasters.readonly` is the durable choice.

**Why `services enable searchconsole.googleapis.com` is required:** Even though Search Console API is free, Google Cloud's quota infrastructure requires the API to be explicitly enabled on the project that will be billed for quota usage. Skipping this step returns HTTP 403 with `reason: SERVICE_DISABLED` on first call.

**Why `set-quota-project` is required:** Google Cloud APIs called via user-credential ADC (as opposed to service-account auth) require a quota project to bill against. The skill reads this value from ADC's stored credentials file and passes it as the `x-goog-user-project` header on every request. Without `set-quota-project`, the header is empty and all API calls return 403 SERVICE_DISABLED.

After setup, the skill mints an OAuth bearer token (valid ~1 hour) from this ADC file. **It does NOT shell out to `gcloud` per call** — `gsc-parse-helper` reads the `authorized_user` credential and performs a refresh-token grant with Python stdlib (no `google-auth` dependency, no `gcloud` spawn). Tokens are **minted in the same Bash call that uses them, never cached or reused across calls** — shell state doesn't persist across Bash tool invocations, so there is no "token reused across the run."

### Use ADC (login as yourself), NOT a service account

Authenticate as your own Google account via ADC (`type: authorized_user`) — you already own your GSC properties, so nothing needs to be "added" in GSC. **Do not use a service account:** adding a service-account email under GSC *Users and permissions* is blocked by an open Google bug ("Failed to add user: email not found", since ~2026-04-23, unfixed), and the usual bypass (domain-wide delegation) requires Google Workspace, which personal `@gmail.com` accounts lack.

### Multi-machine: configure once, run everywhere

The ADC `application_default_credentials.json` holds a refresh token that is **not machine-locked**. To avoid logging in on every PC/Mac: run the login once, put the file in a synced folder (Drive/OneDrive/Dropbox), and set `adc_credentials_path` in `.seo-data/gsc/config.yaml` to that path (e.g. `adc_credentials_path: ~/Dropbox/bx-seo/adc.json`). `~` and `$VARS` are expanded, so the same config value resolves on every machine. Optionally set `quota_project` there too. The file is a secret (a refresh token) — keep it in private synced storage, never in a repo; revoke from your Google account permissions if it ever leaks.

### HTTP request headers

All three endpoints require **two** headers on every request:

```
Authorization: Bearer ya29.xxx...
x-goog-user-project: <ADC quota project ID>
```

| Header | Required? | Source |
|---|---|---|
| `Authorization: Bearer <token>` | Always | `gcloud auth application-default print-access-token` |
| `x-goog-user-project: <project_id>` | Always | `grep -oE '"quota_project_id"[[:space:]]*:[[:space:]]*"[^"]+"' "$ADC_DIR/application_default_credentials.json" \| head -1 \| sed -E 's/.*"([^"]+)"$/\1/'` where `ADC_DIR` comes from `gcloud info --format="value(config.paths.global_config_dir)"`. (grep+sed used instead of `jq` since `jq` is not on PATH in many bash environments including claude-code's on Windows.) |
| `Content-Type: application/json` | POST only | static |

**Omitting `x-goog-user-project`** returns HTTP 403 with `error.status: PERMISSION_DENIED` and `details[*].reason: SERVICE_DISABLED`, even when the token is otherwise valid. The error message references the default consumer project (e.g., `projects/764086051850` — gcloud's shared client project) rather than the user's project. Diagnosis: this header is missing.

No alternative auth (API keys, service-account inline auth) supported — ADC only.

### Quota project resolution

The orchestrator reads the ADC quota project from `application_default_credentials.json` cross-platform via `gcloud info`:

```
ADC_DIR=$(gcloud info --format="value(config.paths.global_config_dir)")
QUOTA_PROJECT=$(grep -oE '"quota_project_id"[[:space:]]*:[[:space:]]*"[^"]+"' "$ADC_DIR/application_default_credentials.json" 2>/dev/null | head -1 | sed -E 's/.*"([^"]+)"$/\1/')
```

`gcloud info` resolves the platform-specific config dir (Windows: `%APPDATA%\gcloud\`; macOS/Linux: `~/.config/gcloud/`). If the field is absent (i.e., user hasn't run `set-quota-project`), grep returns no match → `QUOTA_PROJECT` ends up empty → Step 1.6.3 catches this and surfaces remediation in the footer. Using `grep -oE` + `sed -E` instead of `jq` since `jq` is not on PATH in many bash environments — `application_default_credentials.json` is flat JSON where the field is a top-level string, so regex extraction is safe here.

---

## Site URL encoding (path parameter)

The `siteUrl` path parameter appears in `searchAnalytics/query` and `sites.get` endpoints. **Manual percent-encoding required** — `curl --data-urlencode` operates on request body, not path params.

| Property type | Raw `site_url` | Encoded path segment |
|---|---|---|
| Domain property | `sc-domain:example.com` | `sc-domain%3Aexample.com` |
| Domain property with hyphen | `sc-domain:my-site.com` | `sc-domain%3Amy-site.com` |
| URL-prefix property | `https://example.com/` | `https%3A%2F%2Fexample.com%2F` |
| URL-prefix with subdomain | `https://www.example.com/` | `https%3A%2F%2Fwww.example.com%2F` |
| URL-prefix with subdirectory | `https://example.com/blog/` | `https%3A%2F%2Fexample.com%2Fblog%2F` |

The orchestrator builds the encoded URL in-context before passing to `curl`. Recommended substitution (manual or via `[uri]::EscapeDataString` on PowerShell):

```
encoded = site_url.replace(":", "%3A").replace("/", "%2F")
```

`sites.list` (no path param) is not affected.

---

## `searchanalytics.query` — Search Analytics

### Request

```
POST https://www.googleapis.com/webmasters/v3/sites/{siteUrl_encoded}/searchAnalytics/query
Authorization: Bearer <ADC_TOKEN>
x-goog-user-project: <ADC_QUOTA_PROJECT>
Content-Type: application/json

{
  "startDate": "YYYY-MM-DD",
  "endDate": "YYYY-MM-DD",
  "dimensions": ["query" | "page" | "country" | "device" | "date" | "searchAppearance"],
  "rowLimit": <int, max 25000>,
  "startRow": <int, default 0>,
  "type": "web" | "image" | "video" | "news" | "discover" | "googleNews",
  "dimensionFilterGroups": [optional filters],
  "dataState": "all" | "final"
}
```

**Required**: `startDate`, `endDate`. Date format: `YYYY-MM-DD`.

**Defaults**:
- `dimensions`: `[]` (returns single aggregate row)
- `rowLimit`: `1000`
- `startRow`: `0`
- `type`: `web`
- `dataState`: `all` (includes fresh data; `final` excludes recent partial)

**Date range**: rolling 16 months. `startDate` cannot be more than 16 months before `endDate`. Older dates return empty result silently (no error).

**Search type filter**: defaults to `type: "web"` only (matches GSC UI's default behavior). Future versions may aggregate across image/video/news/discover types.

### Response

```json
{
  "rows": [
    {
      "keys": ["dimension-value-1", "dimension-value-2"],
      "clicks": 123,
      "impressions": 456,
      "ctr": 0.27,
      "position": 5.43
    }
  ],
  "responseAggregationType": "byProperty"
}
```

**Field types**:

| Field | JSON type | Translation |
|---|---|---|
| `keys[*]` | string array | passthrough |
| `clicks` | JSON number (not quoted) | passthrough — no cast needed |
| `impressions` | JSON number | passthrough |
| `ctr` | JSON number (decimal 0-1) | passthrough |
| `position` | JSON number (1-based decimal) | passthrough |

All numeric fields are native JSON numbers — no string-to-number cast needed during translation.

**Empty rows**: when no data matches, `rows` is omitted from the response entirely. Treat absence of `rows` as `rows: []`.

### rowLimit cap

`rowLimit` is capped server-side at **25,000 per call**. Higher values are silently clamped to 25,000. For Q3 (`url_impressions_map`) on >25k-URL sites, the map silently truncates — URLs not in the top-25k get `traffic_weight = 1.0` fallback in Step 6.6.

Pagination via `startRow` is supported (`startRow + rowLimit` retrieves the next batch), but the skill doesn't paginate — single call, accept the cap.

### Position-band filter (Q1 — client-side)

The API's `dimensionFilterGroups` supports filters on dimensions (query/page/country/device) but **NOT** on `position`. The skill applies the position-band filter (5-20) and impression-floor filter (≥100) client-side after the response is received.

---

## `urlInspection.index.inspect` — URL Inspection

### Request

```
POST https://searchconsole.googleapis.com/v1/urlInspection/index:inspect
Authorization: Bearer <ADC_TOKEN>
x-goog-user-project: <ADC_QUOTA_PROJECT>
Content-Type: application/json

{
  "inspectionUrl": "https://example.com/specific-page",
  "siteUrl": "sc-domain:example.com",
  "languageCode": "en"
}
```

**Required**: `inspectionUrl`, `siteUrl`. **Note**: `siteUrl` here is a **request body field** (not a path parameter — no URL encoding needed). Use the raw string format.

**Optional**: `languageCode` for localized issue messages. The skill doesn't use issue messages, so this is left default.

**Constraint**: `inspectionUrl` MUST belong to the property identified by `siteUrl`. Cross-property inspection returns HTTP 400.

### Response

```json
{
  "inspectionResult": {
    "inspectionResultLink": "https://search.google.com/search-console/inspect?...",
    "indexStatusResult": {
      "verdict": "PASS",
      "coverageState": "Submitted and indexed",
      "robotsTxtState": "ALLOWED",
      "indexingState": "INDEXING_ALLOWED",
      "lastCrawlTime": "2026-05-13T10:30:00Z",
      "pageFetchState": "SUCCESSFUL",
      "googleCanonical": "https://example.com/canonical-page",
      "userCanonical": "https://example.com/canonical-page",
      "sitemap": ["https://example.com/sitemap.xml"],
      "referringUrls": ["https://example.com/", "https://example.com/blog"],
      "crawledAs": "MOBILE"
    },
    "mobileUsabilityResult": {
      "verdict": "PASS",
      "issues": []
    },
    "richResultsResult": {
      "verdict": "PASS",
      "detectedItems": []
    }
  }
}
```

`indexStatusResult` is the primary block consumed by the skill. `mobileUsabilityResult` and `richResultsResult` are present in response but not aggregated (deferred — would add mobile-usability + rich-result-validation sub-dims; each needs rubric weight allocation).

### `indexStatusResult` fields used by the skill

| Field | Type | Used for |
|---|---|---|
| `verdict` | enum | High-level pass/partial/fail/neutral (informational only) |
| `coverageState` | string | Primary key in 9-reason lookup table (`gsc-api-queries.md`) |
| `pageFetchState` | enum | Joint key with `coverageState` for ambiguous mappings |
| `robotsTxtState` | enum | Cross-check for sub-dim 7 `blocked_access` (robots variant) |
| `indexingState` | enum | Surface in evidence for sub-dim 7 findings (`BLOCKED_BY_META_TAG` vs `BLOCKED_BY_HTTP_HEADER`) |
| `lastCrawlTime` | ISO-8601 string | Sort key for `affected_urls` (descending — most-recent first); evidence on time-sensitive findings |
| `googleCanonical` | URL string | Sub-dim 6 `canonical_conflict` evidence  |
| `userCanonical` | URL string | Sub-dim 6 `canonical_conflict` evidence  |
| `crawledAs` | enum | Evidence on sub-dim 6 (canonical conflict context) |
| `sitemap` | URL string array | Cross-reference with local sitemap to detect "sitemap conflict" cases (informational) |

### Enums

**`verdict`** — overall index status:
- `PASS` — URL is indexed cleanly
- `PARTIAL` — URL is indexed with caveats (e.g., missing some sitemap)
- `FAIL` — URL is not indexed
- `NEUTRAL` — no opinion (e.g., URL unknown to Google)

**`coverageState`** — primary diagnostic string. ~50 documented values. Most-relevant subset for the 9-reason mapping:

```
Submitted and indexed
Indexed, not submitted in sitemap
Indexed, though blocked by robots.txt
Crawled - currently not indexed
Discovered - currently not indexed
Page with redirect
Not found (404)
Submitted URL not found (404)
Alternate page with proper canonical tag
Duplicate, Google chose different canonical than user
Duplicate without user-selected canonical
Excluded by 'noindex' tag
Blocked by robots.txt
Blocked due to access forbidden (403)
Blocked due to other 4xx issue
Server error (5xx)
Soft 404
URL is unknown to Google
```

Plus less common values (refresh notes, sitemap-specific variants). Full lookup table → `gsc-api-queries.md`.

**`pageFetchState`** — what happened when Google last fetched the page:

```
SUCCESSFUL
SOFT_404
BLOCKED_ROBOTS_TXT
NOT_FOUND
ACCESS_DENIED
SERVER_ERROR
REDIRECT_ERROR
ACCESS_FORBIDDEN
BLOCKED_4XX
```

Joint key with `coverageState` for the lookup table. When `coverageState` is ambiguous (e.g., generic "Not found"), `pageFetchState` disambiguates (`NOT_FOUND` vs `SOFT_404`).

**`robotsTxtState`** — robots.txt allowance:
```
ALLOWED
DISALLOWED
```

**`indexingState`** — explicit reason for blocked indexing (when applicable):
```
INDEXING_ALLOWED
BLOCKED_BY_META_TAG
BLOCKED_BY_HTTP_HEADER
BLOCKED_BY_ROBOTS_TXT
```

**`crawledAs`** — user agent:
```
DESKTOP
MOBILE
```

---

## `sites.list` — Sites list (auth probe)

### Request

```
GET https://www.googleapis.com/webmasters/v3/sites
Authorization: Bearer <ADC_TOKEN>
x-goog-user-project: <ADC_QUOTA_PROJECT>
```

No body. No path params. No query params required.

### Response

```json
{
  "siteEntry": [
    {
      "siteUrl": "sc-domain:example.com",
      "permissionLevel": "siteOwner"
    },
    {
      "siteUrl": "https://other-example.com/",
      "permissionLevel": "siteFullUser"
    }
  ]
}
```

**`permissionLevel`** enum:
- `siteOwner` — full ownership; verified
- `siteFullUser` — full user; verified by owner
- `siteRestrictedUser` — restricted user; verified by owner
- `siteUnverifiedUser` — invited but not verified (cannot query data)

For activation condition 6 (site_url verification), the orchestrator checks:
1. Response is HTTP 200 (probe succeeded — ADC token works for Search Console API)
2. `siteEntry` array contains an element where `siteUrl == config.site_url`
3. That element's `permissionLevel` is one of `siteOwner` / `siteFullUser` / `siteRestrictedUser` (not `siteUnverifiedUser`)

If condition 1 fails: ADC scope issue → surface `--scopes` remediation.
If condition 2 fails: surface "site_url not in your verified properties — check the value or verify the property in GSC."
If condition 3 fails: surface "you have invite-only access; ask the owner to verify your account on this property."

**Empty `siteEntry` array** (response 200 with no properties): the authenticated account has zero GSC properties. Surface "no GSC properties found — verify a property in Google Search Console first."

---

## Quota model

| Endpoint | Quota | Scope |
|---|---|---|
| `searchanalytics.query` | 1,200 QPM (queries per minute) | Per Search Console account |
| `searchanalytics.query` | 100,000 QPD (queries per day) | Per project |
| `urlInspection.index.inspect` | **2,000 URLs/day** | Per property |
| `urlInspection.index.inspect` | **600 QPM** | Per project |
| `sites.list` | 1,200 QPM | Per account |

The 600 QPM on URL Inspection per-project is the binding constraint, not 1,200 QPM general.

**Usage profile per `/bx:seo` run:**
- Search Analytics: 3 calls (Q1, Q2, Q3) — well under any limit
- URL Inspection: ≤100 calls in a single parallel batch — burst fits in <1 minute (100 / 600 QPM ≈ 10 seconds wall time worst case)
- Sites list: 1 call (auth probe)

Total: ≤104 calls per run. Multiple runs per day on the same property: still well under 2,000/day. Multi-property concerns deferred to future.

---

## Error response shape

All endpoints return errors via a consistent envelope:

```json
{
  "error": {
    "code": 429,
    "message": "Quota exceeded for quota metric 'Inspections per day'...",
    "status": "RESOURCE_EXHAUSTED",
    "errors": [
      {
        "message": "Quota exceeded...",
        "domain": "global",
        "reason": "rateLimitExceeded"
      }
    ],
    "details": [...]
  }
}
```

**Stable parsing rule**: parse on `error.code` (HTTP status) + `error.status` (gRPC-style canonical name). The `message` text is human-readable and varies between per-minute/per-day quota exhaustion.

### Error codes used by the skill

| `error.code` | `error.status` | `details[*].reason` | Meaning | Skill behavior |
|---|---|---|---|---|
| 200 | (success) | — | Request succeeded | Continue |
| 400 | `INVALID_ARGUMENT` | — | Malformed request (encoding, invalid date, etc.) | Footer error; skip signal |
| 401 | `UNAUTHENTICATED` | — | Token expired or scope insufficient | Surface `--scopes` remediation; skip signal |
| 403 | `PERMISSION_DENIED` | `SERVICE_DISABLED` | Search Console API not enabled on quota project, OR `x-goog-user-project` header missing | Surface remediation: run `gcloud services enable searchconsole.googleapis.com --project=<id>` + `gcloud auth application-default set-quota-project <id>`. Skill bug if header is missing — file a bug. |
| 403 | `PERMISSION_DENIED` | (other) | Property ACL — user lacks access to the configured `site_url` | Surface property-verification check; skip signal |
| 404 | `NOT_FOUND` | — | URL/property not found | URL Inspection: log "unknown to Google" + skip from cluster. Sites list: surface verify-property remediation. |
| 429 | `RESOURCE_EXHAUSTED` | — | Quota exhausted (per-minute or per-day) | Graceful degrade (decision 10): stop sending, surface footer |
| 5xx | (varies) | — | Transient server error | Print error + skip signal + DON'T retry (re-run skill) |

---

## Schema drift handling

When an endpoint returns an error mentioning an unknown field, or when a `coverageState` value is not in our lookup table:

1. Surface the exact error verbatim in the report footer
2. Log: `Search Console API schema drift detected — field/enum '<X>' missing or new. Schema was validated against Google API docs as of 2026-05-15. Re-validate against current docs: https://developers.google.com/webmaster-tools/v1/`
3. Skip the affected signal for this run (no silent fallback)
4. Continue with other API signals + other paths if applicable

For unmapped `coverageState`: use "Other" bucket in `gsc-api-queries.md` lookup table. Footer notes the unmapped value count.

DO NOT auto-retry with different params. DO NOT mark run partial-success silently — degraded signal is surfaced loudly.

---

## What's NOT done (deferred)

| Capability | Why deferred |
|---|---|
| Multi-property dispatch (multiple `site_url` entries) | the skill is single-property. Multi-property deferred (matrix complexity + property-selection UX). |
| Image/Video/News/Discover search type queries | Skill queries `type: "web"` only. Other types deferred — most SEO/GEO findings target web search. |
| Country/device dimension splits | Adds dimensional noise without v1 finding emission. Deferred. |
| Mobile usability findings (`mobileUsabilityResult` block from URL Inspection) | New sub-dim category — needs rubric weight allocation. future. |
| Rich-result validation findings (`richResultsResult` block) | Same as above — new sub-dim. future. |
| `dataState: "final"` vs `"all"` toggle | the skill uses default (`all` — includes fresh partial data). future may expose as config option. |
| Custom date range (vs `lookback_days`) | the skill uses `lookback_days` (default 90) from config.yaml. Custom date range = future. |
| Pagination beyond rowLimit=25000 | Accept silent truncation on >25k-URL sites; `traffic_weight` falls through to 1.0 for URLs not in the top-25k. |
| `sitemaps.list` / `sitemaps.get` (sitemap submission status) | Tier 2 — sitemap probe in Step 3.2 already covers URL health. future for submission-status integration. |
