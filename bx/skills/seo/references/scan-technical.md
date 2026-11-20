# Scan: Technical SEO + Performance Signals

Loaded by the orchestrator and passed to the `seo-technical` subagent. Detailed scanning instructions follow.

## Inputs from the orchestrator

- `Detected stack` — framework, build target, i18n config
- `Best-practices brief` — passed verbatim (your primary source of truth when it diverges from heuristics below)
- `Scope file list` — source files in scope
- `Sitemap URL probe results` — list of `{url, status, redirect_hops, response_seconds, response_bucket}` records; or skip-reason note
- `Rendered HTML excerpt` (only if `--url` provided)
- `Page audit:` — `gsc-parse-helper page-audit` records from Step 3.4 (raw HTML as a non-rendering crawler sees it), plus `Rendered:` records when a browser was available; or a skip-reason note
- `Render compare:` — `gsc-parse-helper render-compare` results from Step 3.4 (2.20.0), one per page that had both a raw and a rendered copy: `{url, raw:{robots_meta, canonical, jsonld_count, main_text_chars}, rendered:{...}, rendered_only_directive, directive_changes, raw_html_gap}`; or a skip-reason note
- `UTM survival:` — `bot-probe` `utm_survival: {tested_url, final_url, kept, hops}` from Step 3.5 (2.20.0); or a skip-reason note
- `IndexNow:` — `bot-probe` `indexnow: {key_candidates, key_file_ok}` from Step 3.5 (2.20.0); `key_file_ok: null` when no key was known to check
- `Field CWV:` — CrUX p75 records from Step 3.3; or a skip-reason note
- `Exports:` — the Core Web Vitals export digest from Step 1.6.15, when the user dropped one
- `Site profile:` — `markets`, `money_pages`, `site_type` (Step 0.5); since 2.20.0 also `cdn` and `bing_verified` when known
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

**When `Render compare:` covers the same URL** (2.20.0), skip this sub-scan's canonical comparison for it — sub-scan 14 judges canonicals from the raw-vs-rendered pair, which is the comparison that matters to crawlers. Title and description drift stay here.

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
- **Boundary with sub-scan 14 (2.20.0):** this sub-scan owns *missing in raw, present after JS* (content, title, a canonical absent from raw HTML, JSON-LD). Sub-scan 14 owns *directives whose value differs* between raw and rendered (robots `noindex`/`nofollow` added, removed or changed; a canonical that points somewhere else after JS). One URL × tag is judged by one sub-scan only. Main-content and JSON-LD gaps for AI crawlers are geo-generative's `geo_raw_html_gap` — do not emit a GEO finding here; the `rendering` finding above still stands for search crawlers.

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

## Sub-scan 14: Rendered-only directives (`rendered_only_directive` — consumes `Render compare:`)

Google renders JavaScript but may not render a page whose raw HTML says `noindex`, and it documented noindex and canonical behaviour on JS-rendered pages in December 2025 ([Search Central changelog](https://developers.google.com/search/updates); [JavaScript SEO basics](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)). Non-Google AI crawlers do not run JavaScript at all (Vercel/MERJ, December 2024). A robots or canonical directive that JS adds or changes therefore means different crawlers obey different instructions. Screaming Frog flags the same class as "rendered-only" issues.

**From each `Render compare:` record with `rendered_only_directive: true`**, read `directive_changes` (each names the directive and its raw and rendered values):

| Change | Why it matters | sub_dimension | Severity | score_impact | certainty |
|---|---|---|---|---|---|
| raw has `noindex`, rendered removes it | Google may skip rendering, so the page stays out of the index; the JS "fix" never runs for it | `robots_sitemap` | high | 2 | 0.85 |
| raw indexable, rendered adds `noindex` | Google drops the page after rendering while non-rendering crawlers index it — usually an accidental client-side default | `robots_sitemap` | high (medium when the URL is not a money page, not the homepage and not in the sitemap) | 2 (1 for medium) | 0.85 |
| `nofollow` added or removed by JS | link discovery differs by crawler | `robots_sitemap` | low | 0.25 | 0.8 |
| raw canonical A, rendered canonical B (both present, different after normalising trailing slash and scheme) | crawlers receive conflicting canonical signals; Google may pick either | `canonicals` | medium (high on a money page) | 1 | 0.8 |

- Emit **one finding per change type**, listing the URLs in `evidence` with both values (`raw: <v> → rendered: <v>`); `location` is the first URL, or the source file that sets the directive client-side when a `Grep` for the rendered value (e.g. `noindex` inside a `useEffect`, `document.head`, `next/head` in a client component, `react-helmet`, `vue-meta`) finds it — then `location` is that file and `certainty` +0.05.
- Mark each finding with `"finding_id": "rendered_only_directive"`.
- `recommended_action`: put the final directive in the server-sent HTML (SSR/SSG metadata API, server template, or an `X-Robots-Tag` header) and remove the client-side override. Never fix it by adding a second directive in JS.
- `rendered_only_directive: false` or no `Render compare:` → nothing here. A Playwright render is not Googlebot's renderer: say "as rendered by a headless browser" in `evidence`, never "as Google sees it".
- Points count against the existing `robots_sitemap` (4) and `canonicals` (4) caps; sub-scan 6's noindex findings and these never deduct twice for one URL — keep the one with the higher `score_impact`.

---

## Sub-scan 15: ChatGPT attribution survival (`utm_stripped` — consumes `UTM survival:` + source)

ChatGPT adds `utm_source=chatgpt.com` to the links it cites ([OpenAI publishers FAQ](https://help.openai.com/en/articles/12627856-publishers-and-developers-faq)). A redirect or middleware that rebuilds the URL from its path alone drops that parameter, so AI referrals land in analytics as Direct. This is an **attribution** defect, not a ranking one: `score_impact: 0`, `sub_dimension: "redirects"`, `"finding_id": "utm_stripped"`.

**Live (`UTM survival:`):** `kept: false` → finding, `severity: medium`, `certainty: 0.9`, evidence `tested_url → final_url` and `hops`. `kept: true` → no live finding (only the base URL was tested; static suspects below still apply to other routes). Skip-reason note → static only.

**Source (always):** `Grep` the scope (not vendored dirs) for redirect code that rebuilds the target without the query string:

| Pattern (examples, not exhaustive) | Keeps the query? |
|---|---|
| Next.js middleware / proxy: `NextResponse.redirect(new URL(<pathname>, req.url))` or a target built from `nextUrl.pathname` with no `.search` / `searchParams` | no — flag |
| `url.search = ''`, `searchParams.delete(` over all keys, "strip query params" helpers applied before a redirect or canonical rewrite | no — flag |
| Express/Koa: `res.redirect(req.path)` / `ctx.redirect(ctx.path)` (`req.originalUrl` / `ctx.url` keep it) | no — flag |
| nginx `return 301 https://$host$uri;` or `rewrite ... ?` with a trailing `?` (`$request_uri` / `$is_args$args` keep it) | no — flag |
| Apache `RewriteRule ... [QSD]` | no — flag |
| Framework config redirects (Next.js `redirects()`, `vercel.json`, Netlify `_redirects`) without an explicit query-dropping option | yes by default — do not flag |

- Static match only → `severity: low` (medium when the redirect sits on every request, e.g. trailing-slash, locale or www normalisation middleware), `certainty: 0.6`; `0.4` when the live check reported `kept: true`. One finding per file, `location` = `<path>:<line>`.
- Live `kept: false` + a static match → one finding at the static location, `certainty: 0.95`, citing both.
- `recommended_action`: carry `search` (or `request_uri`) into the redirect target; never strip `utm_*` parameters in middleware. If analytics should not store them, remove them client-side after the analytics tag reads them. Plan item (not this agent's finding): a GA4 custom channel for AI referrers, noting the October 2026 reports of ChatGPT traffic arriving with no referrer or UTM.

---

## Sub-scan 16: IndexNow readiness (`indexnow_missing` — consumes `IndexNow:` + source)

IndexNow lets a site tell participating engines (Bing, Yandex, Seznam, Naver and others; **not Google**) that a URL changed. Bing positions it, as of 2026-02, as the way to keep AI answers referencing the current version of a page ([Bing Webmaster blog](https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview)). It is near-free for sites that publish often and adds little for a site that rarely changes. Every finding here is `score_impact: 0`, `sub_dimension: "robots_sitemap"`, `"finding_id": "indexnow_missing"`.

**What to look for in source:**
1. **Key file** — `Glob {public,static,_site,dist,out}/*.txt` (and the repo root for plain static sites): a file named `<key>.txt` where `<key>` is 8–128 characters of letters, digits or dashes and the file's only content equals `<key>`. A route that serves the key (e.g. `app/[key].txt/route.ts`, an `indexnow` API route reading an env var) also counts.
2. **Ping on publish** — `Grep -i` for `indexnow`, `api.indexnow.org`, `bing.com/indexnow` in source, CI workflows (`.github/workflows/`, `.gitlab-ci.yml`), deploy scripts, sitemap generators, CMS webhooks, and `package.json` dependencies (IndexNow plugins for the framework or CMS).

**`IndexNow:` (live, only when the orchestrator knew a key):** `key_file_ok: true` — the key file is served; `false` — it is not served or its content differs; `null` — not checked.

| State | Severity | certainty | is_fix_eligible |
|---|---|---|---|
| no key file and no ping | low | 0.8 | true — key-file scaffold only (`fix-allowlist.md` #12); the ping is `--plan` work |
| key file present, no ping found | low | 0.6 (a CMS or hosting integration may ping outside the repo — say so) | false |
| ping found, no key file or key route | medium (pings fail verification) | 0.6 | false |
| live `key_file_ok: false` while a key is known | medium | 0.85 | false |
| key served (`key_file_ok: true` or file present) and ping found | no finding | — | — |
| the `--fix` placeholder (`indexnow-key.txt` still containing `TODO-replace-this-line-with-your-IndexNow-key`) | low — "IndexNow key placeholder not filled in" | 0.9 | false |

The placeholder file is neither a key nor a ping: exclude it from the ping `Grep`.

- `site_type` that rarely changes (portfolio, brochure) → cap at `low` and say "optional".
- `Site profile: bing_verified: no` → add to the advice that Bing Webmaster Tools verification is what shows whether submissions arrive.
- `recommended_action`: generate a key yourself (Bing's IndexNow page, or 32+ random hex characters from your own tooling — the skill never writes a real key), serve it as `<key>.txt` at the site root, and submit changed URLs to `https://api.indexnow.org/indexnow` from the deploy step or sitemap regeneration. Keep sitemaps with accurate `lastmod` as well — IndexNow complements them.

---

## Sub-scan 17: Soft-navigation Core Web Vitals note (info — client-routed sites)

As of 2026-11, CrUX publishes **experimental** LCP, INP and CLS variants that include soft navigations (client-side route changes), and its release notes say soft navigations are planned to be included in the standard metrics **from May 2027** ([CrUX release notes](https://developer.chrome.com/docs/crux/release-notes); [web.dev](https://web.dev/blog/crux-experimental-soft-navs/)). Today's standard metrics count only hard navigations as page views: a client-side route change gets no LCP of its own, and its interactions and shifts are attributed to the landing URL. Sites that navigate client-side may see their field numbers shift when the change lands.

- **Trigger:** the detected stack routes client-side after the first load — a client-only SPA (sub-scan 12's list), or Next.js / Nuxt / SvelteKit / Remix / Gatsby / Astro with view transitions or a client router — **and** `Field CWV:` has data for the origin (with `no_data` or no CrUX at all there is nothing to shift; skip). Plain MPAs → nothing.
- **One finding**, `dimension: "performance"`, `sub_dimension: "font_script_perf"`, `severity: low`, `certainty: 0.5`, `score_impact: 0`, `"finding_id": "soft_nav_cwv_note"`, `location` = the router or root layout file.
- `recommended_action`: "Info only. Look up the site's experimental soft-navigation metrics in CrUX Vis or the CrUX API and compare them with the standard ones; if the soft-navigation INP or CLS is worse, fix route-change work (heavy client transitions, layout shift on navigation) before the planned change. No score impact until the metrics become standard."
- Never deduct and never re-rate a field CWV finding on this basis. If the brief reports the plan has changed, follow the brief.

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
rendered_only_directives: <int — URLs with a directive changed by JS; 0 when Render compare was skipped>
render_compare_used: true | false
utm_source_survives: true | false | null   // live result; null when not probed
utm_static_suspects: <int>
indexnow_state: "ok" | "key_only" | "ping_only" | "missing" | "key_not_served"
soft_nav_note: true | false
files_scanned: <int>
```

The orchestrator's Step 6 reads these to compute the report's Section 1 breakdown.

---

## Hard rules (repeat of agent definition for in-prompt clarity)

- **Never make HTTP requests.** No `Bash(curl:*)`, no `WebFetch`.
- **URL-health score cap: 5 points.** Scale findings if raw sum exceeds.
- **Skip vendored / generated dirs**: `node_modules`, `venv`, `.git`, `dist`, `build`, `.next`, `.nuxt`, `out`, `_site`, `public/build`, `__generated__/`, `*.generated.*`, `*.d.ts`.
- **Cap output at 30 findings**, ordered by `score_impact × certainty` desc. The 2.20.0 info findings (`utm_stripped`, `indexnow_missing`, `soft_nav_cwv_note`) have `score_impact: 0`; when the cap bites, they go before other zero-impact info notes but after every deducting finding.
- **Never write or guess an IndexNow key** — keys are user-generated. Findings may cite a key the repo already serves (it is public by design), never propose one.
