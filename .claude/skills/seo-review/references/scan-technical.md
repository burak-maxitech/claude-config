# Scan: Technical SEO + Performance Signals

Loaded by the orchestrator and passed to the `seo-technical` subagent. Detailed scanning instructions follow.

## Inputs from the orchestrator

- `Detected stack` — framework, build target, i18n config
- `Best-practices brief` — passed verbatim (your primary source of truth when it diverges from heuristics below)
- `Scope file list` — source files in scope
- `Sitemap URL probe results` — list of `{url, status, redirect_hops, response_seconds, response_bucket}` records; or skip-reason note
- `Rendered HTML excerpt` (only if `--url` provided)
- `Weight adjustments` — per-dimension deltas from brief, capped at ±5 each, sum=0

## Approach

Run each sub-scan against the scoped files. For each finding, emit JSON per the output shape in `seo-technical.md` agent definition.

---

## Sub-scan 1: Crawlability — robots.txt + sitemap.xml

**robots.txt presence:**
- `Glob` for `robots.txt` and `public/robots.txt`, `static/robots.txt`, `app/robots.{ts,js}` (Next.js app-router metadata route).
- Missing entirely → finding, `severity: medium`, `score_impact: 2`, `is_fix_eligible: true` (allowlist scaffold).
- Present but no sitemap reference → finding, `severity: low`, `score_impact: 1`.

**robots.txt syntax:**
- Orphan `Disallow:` lines (no preceding `User-agent:`) → invalid syntax, `severity: medium`.
- `Disallow: /` under `User-agent: *` → catastrophic, `severity: high`, `score_impact: 4`.

**sitemap.xml presence:**
- Same locations as above, plus `public/sitemap.xml`, `app/sitemap.{ts,js}`.
- Missing entirely → finding, `severity: medium`, `score_impact: 2`, `is_fix_eligible: true` (empty `<urlset>` stub).

**sitemap.xml freshness:**
- Read the file. Count entries. Flag if zero URLs.
- For each entry with `<lastmod>`, parse the date. If >12 months old AND the entry is not for a known evergreen page, flag as `severity: low`, `score_impact: 0.25`.

---

## Sub-scan 2: Sitemap URL Health (consume orchestrator probe results)

**Critical: this scan does NOT make HTTP requests.** It only classifies the probe results passed in via shared context.

For each record in the probe-results list:

```python
if status in [404, 410]:
    severity = "high" if status == 404 else "medium"
    score_impact = 1.5 if status == 404 else 1.0
elif status == 403:
    severity = "high"
    score_impact = 1.5
elif 500 <= status < 600:
    severity = "high"
    score_impact = 2.0
elif redirect_hops > 1:
    severity = "medium"
    score_impact = 0.5
elif response_bucket == "slow":
    # Goes to Performance dimension, not Technical SEO
    dimension = "performance"
    sub_dimension = "response_time"
    severity = "low"
    score_impact = 0.25
elif status == "error":
    severity = "low"
    score_impact = 0  # don't penalize on network errors
else:
    skip
```

**Aggregation cap:** sum of `score_impact` across all url_health findings MUST NOT exceed 8. If the raw sum exceeds 8, scale all url_health findings proportionally (e.g., raw sum is 16 → multiply each by 0.5).

**Output format example:**
```json
{
  "dimension": "technical_seo",
  "sub_dimension": "url_health",
  "location": "https://example.com/products/v1",
  "title": "404 Not Found on sitemap URL",
  "severity": "high",
  "certainty": 1.0,
  "effort_estimate": "small",
  "score_impact": 1.5,
  "is_fix_eligible": false,
  "recommended_action": "Either restore the page at /products/v1 or remove it from sitemap.xml. URLs in the sitemap that return 404 dilute crawl budget and signal an outdated site map.",
  "evidence": "HTTP 200 expected; returned 404."
}
```

**If probe-results is empty AND a skip-reason note was passed:** emit a single informational finding (`severity: low`, `score_impact: 0`) explaining why the probe didn't run. No score impact.

---

## Sub-scan 3: Canonicals

`Grep` patterns:
- `<link\s+rel=["']canonical["']` in HTML/JSX/TSX/Vue/Svelte files

For each match:
- **Absolute URL check:** the `href` should start with `https://` (or `http://` for non-production), not a relative path. Relative canonicals are technically valid but conflict-prone.
- **HTTPS check:** http:// canonical on a project that otherwise serves HTTPS = downgrade signal.
- **Self-referencing check:** when source-determinable (the page's expected URL pattern from filename matches the canonical href).
- **Duplicate canonicals:** more than one `<link rel="canonical">` in the same page-template = critical, `severity: high`.

Pages **missing** canonicals entirely → flag `severity: medium`, `score_impact: 1.5`, `is_fix_eligible: true` (insert self-referencing canonical template).

---

## Sub-scan 4: Mobile Viewport

`Grep` pattern: `<meta\s+name=["']viewport["']`

For each page-shell / layout file:
- **Missing entirely** → finding, `severity: high`, `score_impact: 1.5`, `is_fix_eligible: true` (standard insert).
- **Legacy patterns** — `user-scalable=no`, `maximum-scale=1.0`, `maximum-scale=1` → accessibility regression, `severity: medium`, `score_impact: 0.5`.

---

## Sub-scan 5: Hreflang (only if i18n detected)

Skip entirely if Step 0 detected no i18n.

`Grep` pattern: `<link\s+rel=["']alternate["']\s+hreflang=`

- For multi-locale projects: each locale should be represented. Detect locales from i18n config (e.g., `next-i18next` `locales` array, `nuxt-i18n` `locales:`, file-based `pages/<locale>/`).
- **Missing hreflang entirely** on multi-locale project → `severity: high`, `score_impact: 1.5`.
- **Self-referencing missing** — each locale's pages must list themselves in hreflang.
- **Missing `x-default`** → `severity: medium`, `score_impact: 0.5`.

---

## Sub-scan 6: Indexability Gotchas

**Findings here emit under `sub_dimension: "robots_sitemap"`** — indexability is part of the crawl-control rubric bucket. Don't introduce a separate `indexability` sub_dim (it has no rubric allocation).

- `Grep` for `<meta\s+name=["']robots["']\s+content=["'][^"']*noindex` in page templates.
- Cross-reference with the page's path. If the path looks important (homepage `/`, blog index `/blog`, product roots `/products`, common service-page patterns), flag `severity: high`, `score_impact: 2`.
- For obviously-not-indexable pages (login, admin, password-reset), `noindex` is correct — do not flag.

- `Grep` `robots.txt` for `Disallow:` patterns blocking CSS/JS asset directories (`/*.css`, `/static/*`, `/_next/static/*`). Blocking critical resources breaks rendering → `severity: high`, `score_impact: 1.5`.

---

## Sub-scan 7: Redirect Config (Static)

Framework-specific config files:

| Framework | Config file | Pattern |
|---|---|---|
| Next.js | `next.config.{js,ts,mjs}` | `redirects()` function |
| Nuxt | `nuxt.config.{js,ts}` | `routeRules:` with `redirect:` |
| Astro | `astro.config.{mjs,ts}` | `redirects:` |
| Vercel | `vercel.json` | `redirects:` array |
| Netlify | `_redirects` file OR `netlify.toml` `[[redirects]]` | line-based or TOML array |
| Rails | `config/routes.rb` | `get '...' => redirect('...')` |

For each config file found, parse (heuristic — pattern match, don't try to execute JS):
- **Chains**: redirect target's destination is itself in the redirects list → finding, `severity: medium`, `score_impact: 0.5`.
- **302 instead of 301**: explicit `permanent: false` or `statusCode: 302` for redirects that look permanent (`/old-page` → `/new-page`) → finding, `severity: low`, `score_impact: 0.25`.
- **Missing common patterns** — no trailing-slash normalization, no www↔apex handling (when domain context suggests both should be normalized) → informational only, `severity: low`.

---

## Sub-scan 8: Image Performance Signals (Performance dim)

`Grep` pattern: `<img\b[^>]*>` (HTML/JSX `<img>` tags)

For each match:
- **Missing `width` or `height`** → finding, `severity: medium`, `score_impact: 0.5`, `is_fix_eligible: true` only when adjacent context provides values (e.g., a sibling Next.js `Image` component with the same source has dimensions).
- **Below-fold heuristic**: image appears after the first 200 lines of source / after a `<main>` element / after specific class-name patterns suggesting "below the fold." If below-fold AND missing `loading="lazy"` → `severity: low`, `score_impact: 0.25`, `is_fix_eligible: true`.

Skip framework-managed image components (`next/image`, `Astro <Image>`, `nuxt-img`, etc.) — they handle dimensions and lazy-loading automatically.

---

## Sub-scan 9: Font + Script Performance (Performance dim)

- **Render-blocking `<script>`**: `Grep` for `<script\b[^>]*>` patterns not in `<head>` JSON-LD; flag those missing `async` or `defer`. `severity: low`, `score_impact: 0.5`.
- **Missing font preload**: detect self-hosted fonts via `@font-face` rules in CSS or `next/font` usage. If self-hosted AND no `<link rel="preload" as="font" ...>` in `<head>` → `severity: low`, `score_impact: 0.25`.
- **Inline base64 images**: `Grep` for `src=["']data:image` patterns in source. Inline base64 images >10KB are a build-step regression signal. `severity: low`, `score_impact: 0.25`.

---

## Sub-scan 10: Live Source-vs-Rendered Diff (only when `--url` provided)

If shared context includes rendered HTML excerpt:
- Compare source `<title>` to rendered `<title>`. Drift → finding, `severity: medium`, `score_impact: 0.5` (suggests runtime override may be unintended).
- Compare source `<link rel="canonical">` to rendered canonical. Drift → same.
- Compare source `<meta name="description">` to rendered.

Findings should clearly note which side (source / rendered) is treated as canonical.

---

## Output addendum

After all findings, append:

```
technical_seo_score: <int 0-25>
performance_score: <int 0-10>
url_health_findings_count: <int>
url_health_total_score_impact: <float, capped at 8>
sub_dimension_breakdown: {
  "robots_sitemap": <points deducted>,
  "canonicals": <points deducted>,
  "mobile": <points deducted>,
  ...
}
files_scanned: <int>
```

The orchestrator's Step 6 reads these to compute the report's Section 1 breakdown.

---

## Hard rules (repeat of agent definition for in-prompt clarity)

- **Never make HTTP requests.** No `Bash(curl:*)`, no `WebFetch`.
- **URL-health score cap: 8 points.** Scale findings if raw sum exceeds.
- **Skip vendored / generated dirs**: `node_modules`, `venv`, `.git`, `dist`, `build`, `.next`, `.nuxt`, `out`, `_site`, `public/build`, `__generated__/`, `*.generated.*`, `*.d.ts`.
- **Cap output at 30 findings**, ordered by `score_impact × certainty` desc.
