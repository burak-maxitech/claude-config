# Scan: Technical SEO + Performance Signals

Loaded by the orchestrator and passed to the `seo-technical` subagent. Detailed scanning instructions follow.

## Inputs from the orchestrator

- `Detected stack` — framework, build target, i18n config
- `Best-practices brief` — passed verbatim (your primary source of truth when it diverges from heuristics below)
- `Scope file list` — source files in scope
- `Sitemap URL probe results` — list of `{url, status, redirect_hops, response_seconds, response_bucket}` records; or skip-reason note
- `Rendered HTML excerpt` (only if `--url` provided)
- `Page audit:` — `gsc-parse-helper page-audit` records from Step 3.4 (raw HTML as a non-rendering crawler sees it), plus `Rendered:` records when a browser was available; or a skip-reason note
- `Field CWV:` — CrUX p75 records from Step 3.3; or a skip-reason note
- `Exports:` — the Core Web Vitals export digest from Step 1.6.15, when the user dropped one
- `Site profile:` — `markets`, `money_pages`, `site_type` (Step 0.5)
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

**Aggregation cap:** sum of `score_impact` across all url_health findings MUST NOT exceed 5. If the raw sum exceeds 5, scale all url_health findings proportionally (e.g., raw sum is 10 → multiply each by 0.5).

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
- **Against `Site profile: markets`** (when not `unknown`): a market whose language has no locale/hreflang → `severity: medium`, `score_impact: 0.5`; a locale outside `markets` → info (`score_impact: 0` — may be deliberate). A single-locale site whose `<html lang>` differs from the only market's language → `severity: low`, `score_impact: 0.25`. When `markets` lists several languages but Step 0 found no i18n, emit one info finding (the hreflang points still redistribute per `rubric.md`).

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

## Sub-scan 11: Field Core Web Vitals (Performance dim — consumes `Field CWV:` and the CWV export)

Field data is what users experienced; static signals are guesses about it. When they disagree, field data wins.

**From `Field CWV:` records** (`origin=` or `url=` lines with `lcp_p75=<ms>(<rate>)`, `inp_p75`, `cls_p75`, `ttfb_p75`):

| Field result (PHONE first; DESKTOP only if PHONE has no data) | Sub-dim | Severity | score_impact |
|---|---|---|---|
| LCP `poor` | `image_perf` (hero image / render path) — `response_time` instead when TTFB p75 > 1800 ms (the server is the bottleneck) | high | 2 |
| LCP `needs_improvement` | same routing | medium | 1 |
| CLS `poor` / `needs_improvement` | `image_perf` (unsized media, late-injected embeds) | high / medium | 1.5 / 0.75 |
| INP `poor` / `needs_improvement` | `font_script_perf` (long JS tasks, heavy third-party scripts) | high / medium | 1.5 / 0.75 |
| TTFB p75 > 1800 ms | `response_time` | medium | 1 |

- Emit **one finding per metric**, located at the origin (or the URL when only URL-level data exists). List the URLs that share the rating in `evidence` — no per-URL findings.
- A `url=` record on a **money page** (`Site profile: money_pages`) rated `poor` gets its own finding, `severity: high`.
- **When field data exists, it replaces the probe for `response_time`**: score from TTFB p75, and drop the `response_bucket: slow` deductions (one-location lab timing). Keep those probe records as evidence only.
- **Static findings meet field data:** a static `image_perf` / `font_script_perf` finding that names a likely cause of a `poor` field metric → `certainty` +0.2 (cap 1.0) and cite the field metric in `evidence`. When the matching field metric is `good` on PHONE, cap that static finding at `severity: low` and `score_impact: 0.25` — the page already passes for real users.
- `status=no_data` → never a finding (too little Chrome traffic, not a defect). If every record is `no_data`, emit one info finding (`score_impact: 0`) saying field data is unavailable and static signals are all the audit has.
- Sub-dim caps still hold (`image_perf` 4, `font_script_perf` 3, `response_time` 3).

**From the CWV export digest** (`Exports:` block — Search Console's own URL groups): same severity table per Poor / Needs-improvement group, `source: "gsc"`. When CrUX records exist too, merge — one finding per metric, citing both — never deduct twice. The export alone (no CrUX key) scores the same way; it is real-user data too.

---

## Sub-scan 12: Rendering integrity (`rendering` — consumes `Page audit:`)

Most AI crawlers (GPTBot, ClaudeBot, PerplexityBot) do not run JavaScript, and Googlebot renders later than it crawls. Content that exists only after JS is invisible to the first group and delayed for the second.

**From `Page audit:` records** (raw HTML, no JS):

| Signal | Finding | Severity | score_impact |
|---|---|---|---|
| `words` < 50 AND (`empty_root=yes` OR a `Rendered:` record for the same URL has ≥ 200 words) | "Main content is rendered client-side only" | high (medium when the page is not a money page and not the homepage) | 1.5 |
| `Rendered:` words ≥ 3 × raw `words` (and rendered ≥ 200) | "Most of the content needs JavaScript" | medium | 1 |
| `title=no`, `canonical=none`, or `jsonld=0` in raw while the `Rendered:` record (or the source template) has it | "<tag> is injected by JavaScript" — one finding per tag type, listing URLs | medium | 0.5 each |
| `over_2mb=yes` | "HTML exceeds Googlebot's 2 MB limit — content past it is not indexed" ([Googlebot docs](https://developers.google.com/search/docs/crawling-indexing/googlebot): first 2 MB of uncompressed HTML) | high | 1.5 |
| `bytes` between 1.5 MB and 2 MB | "HTML within 25% of the 2 MB limit" | low | 0.25 |
| `robots` or `x_robots` contains `noindex` on a URL that the sitemap lists or that is a money page | (route to `robots_sitemap`, sub-scan 6 rules) | high | 2 |

- **No `Rendered:` records** (no browser available): judge only from the raw record + source. `empty_root=yes` with `words` < 50 is enough for the first row at `certainty: 0.75`. Without `empty_root` and without rendered data, a low word count alone is not a rendering finding (the page may simply be short — that is `content_depth`, owned by `seo-content`).
- **No `Page audit:` at all** (no base URL resolvable): static-only check — a client-only SPA stack (CRA, Vite/React or Vue without an SSR/SSG framework, `ssr: false` in Nuxt/SvelteKit config, Angular without `@angular/ssr`) → one finding "Site is client-rendered", `severity: high`, `certainty: 0.7`, `score_impact: 1.5`. SSR/SSG frameworks (Next.js, Nuxt default, Astro, SvelteKit default, Remix, Gatsby, Hugo, Jekyll, Eleventy, Rails/Django templates) → no finding.
- `status=error:ssl` / `error:network` / `error:timeout` → never a finding about the site (it is usually the local machine's TLS store or network). Footer note only.
- Cap `rendering` at its sub-dim max (3).

---

## Sub-scan 13: Back-button hijacking (`spam_policy`)

Google's [spam policies](https://developers.google.com/search/docs/essentials/spam-policies) list back-button hijacking under "Malicious practices" — interfering with the browser's back button — sending the user somewhere they did not come from, or trapping them on the page — as spam that can draw a manual action. Detect it in two places:

**Source (always):** `Grep` the scoped files (not `node_modules` / vendored routers) for a `popstate` listener (`addEventListener('popstate'` / `onpopstate =` / `useEffect` that subscribes to `popstate`) whose handler **navigates or re-pushes history** (`location.href =`, `location.replace(`, `location.assign(`, `router.push(`, `history.pushState(`, `window.open(`). Also flag `history.pushState` calls that run **on load with no user action** (module top level, `DOMContentLoaded` / `load` handler, mount-only `useEffect(..., [])`) pushing the current URL or a dummy state — the "extra history entry" trap.
**Live (`Page audit:`):** `hijack_suspect=yes` means an inline script both listens for `popstate` and navigates / re-pushes.

| Evidence | Severity | certainty |
|---|---|---|
| popstate handler that navigates to a **different URL / external domain** or opens an ad / interstitial | high | 0.9 |
| popstate handler that re-pushes state (user cannot leave) | high | 0.8 |
| on-load `pushState` of the current URL with no handler evidence | medium | 0.6 |
| `hijack_suspect=yes` with no matching source (third-party / CMS / tag-manager script) | high | 0.7 — name the inline script's first 80 chars in `evidence` |

`score_impact: 0` — a spam-policy risk is not a points question. **Every `spam_policy` finding with `certainty ≥ 0.7` is forced to priority 1** by Step 6.6 (same rule as a manual action): no on-page work matters if the site is demoted for spam. Legitimate patterns — SPA routers pushing on link clicks, modals closing on back, filter state in the URL — are **not** findings; when unsure, set `certainty` ≤ 0.5 and say what to check.

---

## Output addendum

After all findings, append:

```
technical_seo_score: <int 0-25>
performance_score: <int 0-10>
url_health_findings_count: <int>
url_health_total_score_impact: <float, capped at 5>
sub_dimension_breakdown: {
  "robots_sitemap": <points deducted>,
  "canonicals": <points deducted>,
  "mobile": <points deducted>,
  "rendering": <points deducted>,
  ...
}
field_cwv_used: true | false
spam_policy_findings: <int>
files_scanned: <int>
```

The orchestrator's Step 6 reads these to compute the report's Section 1 breakdown.

---

## Hard rules (repeat of agent definition for in-prompt clarity)

- **Never make HTTP requests.** No `Bash(curl:*)`, no `WebFetch`.
- **URL-health score cap: 5 points.** Scale findings if raw sum exceeds.
- **Skip vendored / generated dirs**: `node_modules`, `venv`, `.git`, `dist`, `build`, `.next`, `.nuxt`, `out`, `_site`, `public/build`, `__generated__/`, `*.generated.*`, `*.d.ts`.
- **Cap output at 30 findings**, ordered by `score_impact × certainty` desc.
