# --plan Mode (seo-review)

Transform `/seo-review` findings into a phased improvement brief. Each phase becomes a self-contained `/plan-feature <brief>` payload the user can drop into a fresh session.

## Phase grouping

After the report is built, group findings into 6 phases (indexing & crawl hygiene comes first because it directly damages search-engine trust and crawl budget):

1. **Phase 1: Indexing & Crawl Hygiene** (sitemap probe 4xx/5xx + GSC `not_found_404` + `redirect_hygiene` + `server_errors` + `soft_404` clusters)
2. **Phase 2: Quick wins** (allowlist-eligible mechanical scaffolds)
3. **Phase 3: Structural improvements** (heading hierarchy, internal linking, redirect chains)
4. **Phase 4: Content rewrites** (titles, meta descriptions, alt text — human judgment required, GSC-prioritized when API is configured)
5. **Phase 5: Structured data buildout** (JSON-LD per content type)
6. **Phase 6: Generative-engine optimization** (llms.txt + E-E-A-T + AI-citability)

## Phase 1 — Indexing & Crawl Hygiene

Surface findings from **both** the sitemap URL probe (Step 3.2) and the GSC URL Inspection clusters (`seo-gsc-insights` subagent when GSC mode enabled). Order by severity, then by traffic impact when GSC data is present (`impressions × certainty / effort_weight` for GSC findings; URL-health probe findings stay at the top because they have direct score impact).

**Source signals folded into Phase 1:**
- `technical_seo.url_health` findings from sitemap probe (Step 3.2): 4xx, 5xx, redirect-chain
- `gsc_insights.not_found_404` cluster from GSC (often a superset of the probe-sample, since GSC sees URLs the probe didn't reach)
- `gsc_insights.redirect_hygiene` cluster (sitemap entries pointing to redirected URLs — from GSC URL Inspection)
- `gsc_insights.server_errors` cluster
- `gsc_insights.soft_404` cluster

**Probe + GSC dedup already happened** in Step 6.0b — the orchestrator merged URL-level overlaps, keeping the probe finding (with score impact) and tagging it `gsc_corroborated: true`. So Phase 1 sees each URL at most once.

### 1.1 — Per-URL probe findings (when count <10)

Per finding emit a `/plan-feature` snippet:

```
**1.1** 404 on https://example.com/products/v1 (sitemap entry; GSC corroborates)

Hand-off:
\`\`\`
/plan-feature "Investigate the 404 on https://example.com/products/v1 listed in public/sitemap.xml. Google also reports this URL as 'Not found (404)' in indexing/not-found-404.csv. Check (a) whether the page should still exist — review git history for src/app/products/v1/ or equivalent route, (b) whether it was renamed — search for similar paths like /products/version-1 or /products/v2, (c) whether a redirect should be added. If page was deliberately removed, also remove the URL from sitemap.xml. If renamed, add a 301 in next.config.js redirects() and update the sitemap. Verify with curl -I https://example.com/products/v1 after."
\`\`\`
```

### 1.2 — Bulk-cluster + routing-rename detection (the highest-leverage signal)

When a GSC `not_found_404` cluster carries `routing_rename_match: true` (Phase 4 subagent detected the cluster's URL pattern overlaps a rename in the 35-day git-history window), emit a **bulk-redirect snippet** that names the rename + asks the user to confirm the mapping before any 301 is written. **The snippet does NOT fabricate target URLs** — that's the hard rule from `fix-allowlist.md` (never fabricate content). The skill surfaces the cluster + likely cause; the user specifies the mapping.

```
**1.2** Bulk 404 cluster: /blog/2023/* (12 URLs) — matches recent routing rename

Detection:
- 12 URLs under /blog/2023/* return 404 at Google's view (from GSC URL Inspection — not_found_404 cluster).
- Git history (last 35 days) shows a rename: src/content/posts/* → src/app/blog/* on 2026-04-10 (commit ghi789, "restructure blog routing").
- Affected URL pattern: /blog/2023/<slug> — derived from old paths src/content/posts/2023/<slug>.md.

Hand-off:
\`\`\`
/plan-feature "12 URLs under /blog/2023/* now return 404 at Google's view (from GSC URL Inspection — not_found_404 cluster). Git history shows commit ghi789 on 2026-04-10 ('restructure blog routing') renamed src/content/posts/2023/* → src/app/blog/*. Investigate whether the renamed paths map 1:1 to new URLs:

1. Pick 3 sample URLs from the 404 list. For each, find the corresponding new URL by searching src/app/blog/ for matching slug.
2. If 1:1 mapping confirmed (3 of 3 samples found) → write bulk 301 redirects in next.config.js redirects() function mapping /blog/2023/<slug> → /blog/<slug>. Also remove 404 entries from public/sitemap.xml.
3. If mapping is NOT 1:1 (some slugs missing, restructured) → for each missing URL, decide per-URL: redirect to closest match, redirect to /blog/ index, or accept as gone (remove from sitemap).
4. Verify all 12 with parallel curl after deploy. Re-run /seo-review in 2-3 weeks to confirm GSC has caught up.

Sample affected URLs: <list 5 from the cluster>. Full list: see GSC URL Inspection — not_found_404 cluster."
\`\`\`
```

When `routing_rename_match: false` on a `not_found_404` cluster, fall back to the standard bulk pattern (no rename context):

```
**1.X** 12 × 404s under /blog/2023/* (no matching git rename detected)

Hand-off:
\`\`\`
/plan-feature "12 blog posts under /blog/2023/* return 404 at Google's view (from GSC URL Inspection — not_found_404 cluster). No matching rename detected in the last 35 days of git history. Investigate whether (a) the year-2023 folder was deliberately retired — if so, remove all 12 entries from sitemap.xml, (b) they were moved to a new structure (e.g., /blog/<slug> flat) — if so, add 301 redirects in bulk via the framework redirects config and update sitemap entries, (c) they should be restored from a backup. Sample URLs: /blog/2023/jan-update, /blog/2023/feb-update, /blog/2023/march-roundup. Verify all 12 with a parallel curl after fix."
\`\`\`
```

### 1.3 — Server errors (5xx)

GSC `server_errors` findings indicate Google encountered 5xx during crawl. These are often transient (deployment windows, timeouts) but can also be persistent infrastructure issues. Surface as a single phase-snippet:

```
**1.3** 3 URLs returned 5xx errors at Google's crawl (server reliability signal)

Hand-off:
\`\`\`
/plan-feature "3 URLs returned 5xx errors when Google crawled (from GSC URL Inspection — server_errors cluster): /api/legacy-export (2026-04-18), /products/large-catalog (2026-04-22), /search?q=<long-query> (2026-04-25). Cross-reference server logs around those timestamps. Common causes: deployment-window errors, timeouts on heavy pages, dependency outages. If errors persist, harden the endpoints; if transient, no fix needed but worth knowing."
\`\`\`
```

### 1.4 — Soft 404s

Soft 404s (Google detected empty/error content despite 200 status) need rendering fixes, not redirect fixes:

```
**1.4** Soft 404 cluster (N URLs return 200 but Google detected empty content)

Hand-off:
\`\`\`
/plan-feature "N URLs return 200 OK but Google detected empty/error content (from GSC URL Inspection — soft_404 cluster): <list>. Visit each URL in a browser — pages may be loading stub/placeholder/error content that returns 200. Either fix the rendering so real content loads (preferred — these URLs may have legitimate intent), or set proper 404 status when content is missing. Common SPA pattern: client-side router renders 'not found' message but the HTML response is 200."
\`\`\`
```

Estimated effort for Phase 1: depends on count + cause. Often the highest-leverage phase per hour spent — broken URLs at Google's view are a direct trust-and-crawl-budget hit.

## Phase 2 — Quick Wins (Allowlist-Eligible)

Findings where `is_fix_eligible: true`. These can be applied via `/seo-review --fix` directly with the per-finding diff gate — no full plan-feature session needed for each.

```
### Phase 2 — Quick Wins (N allowlist-eligible findings)

Run `/seo-review --fix` to walk these with per-finding diff preview:

- Missing viewport meta — src/app/layout.tsx
- Missing self-referencing canonical — src/app/about/page.tsx, src/app/contact/page.tsx
- Missing OG/Twitter Card scaffolds — 4 pages
- Missing JSON-LD Article scaffold — 8 blog posts
- Missing llms.txt
- Missing alt="" on decorative logo images — 3 occurrences

Estimated total score recovery if all applied: +6 points.
Caveat: every applied scaffold contains TODO placeholders. Fill them in to capture the full score gain.
```

Don't emit `/plan-feature` snippets here — `--fix` is the right tool.

## Phase 3 — Structural Improvements

Findings touching markup structure but not content:
- Heading hierarchy violations
- Multiple H1s per page
- Redirect chains (>1 hop)
- Orphan pages (need internal links added)
- 302 used where 301 was intended

Each cluster gets one `/plan-feature` snippet. Example:

```
**3.1** Fix heading hierarchy on 6 product pages (currently jump H1 → H3)

Hand-off:
\`\`\`
/plan-feature "Fix heading hierarchy on 6 product pages (src/app/products/foo/page.tsx, ... — list from /seo-review). Each currently jumps from H1 directly to H3, skipping H2. Insert H2 wrappers for logical sections (Description / Features / Specifications), making sure H2s are descriptive and not generic. Goal: every page passes the 'no level skips' check; H1 count remains exactly 1 per page."
\`\`\`
```

## Phase 4 — Content Rewrites (Human Judgment, traffic-prioritized when GSC available)

Findings where the fix requires writing or rewriting copy:
- Weak / missing titles
- Missing or boilerplate meta descriptions
- Missing or filename-based alt text on content images
- Anchor text quality issues (`click here`, `read more`)
- **GSC `ctr_opportunity` findings** (high-impressions, low-CTR pages — title/meta rewrite targets)

**Traffic prioritization:** when `gsc_mode: enabled` AND a heuristic content finding's affected URL appears in `url_impressions_map`, sort the per-cluster URL list by impressions descending. High-traffic missing-meta pages first; low-traffic last. Surface the impression count inline in the hand-off so the receiving `/plan-feature` session can prioritize correctly.

When `gsc_mode: disabled`, fall back to alphabetical-by-path sort (existing behavior). Phase 4 hand-off snippets adapt as follows:

### 4.1 — Meta description rewrites (traffic-prioritized when GSC enabled)

```
**4.1** Write meta descriptions for 12 pages missing them (sorted by impressions desc)

Hand-off (GSC enabled — traffic visible):
\`\`\`
/plan-feature "Write meta descriptions for 12 pages currently missing them, prioritized by traffic. Pages (in priority order):

1. src/app/pricing/page.tsx (12,420 impressions/28d, CTR 0.4% — also a ctr_opportunity)
2. src/app/products/api/page.tsx (4,800 impressions, CTR 0.6%)
3. src/app/blog/llms-explained/page.tsx (3,200 impressions, CTR 0.5%)
4. src/app/about/page.tsx (1,800 impressions, CTR 0.8%)
5-12. [lower-traffic pages, full list from findings]

Each description should be 150-160 chars, summarize the page's value, use action-oriented language. Reference the page's H1, first paragraph, AND the top 3-5 queries from GSC Search Analytics Q1 queries digest filtered by this URL when writing — those are the actual search intents driving impressions. Goal: recover ~3 points on On-Page SEO + lift CTR on the top-traffic pages toward the site median."
\`\`\`

Hand-off (GSC disabled — alphabetical):
\`\`\`
/plan-feature "Write meta descriptions for 12 pages currently missing them. Pages: src/app/about/page.tsx, src/app/blog/foo/page.tsx, src/app/pricing/page.tsx, [... alphabetical list from findings]. Each description should be 150-160 chars, summarize the page's value, use action-oriented language. Reference the page's H1 and first paragraph for context. Goal: recover ~3 points on On-Page SEO dimension."
\`\`\`
```

### 4.2 — Weak alt text rewrites

```
**4.2** Rewrite weak alt text on 8 content images

Hand-off:
\`\`\`
/plan-feature "Rewrite alt text on 8 content images currently using filename-as-alt or generic 'image' patterns. Images: src/components/Hero/hero.jpg, src/app/blog/foo/diagram.png, [... list]. For each, write descriptive alt that conveys the image's information value (not appearance). Goal: alt text accessible to screen readers AND useful as SEO image context."
\`\`\`
```

(Image alt text is rarely traffic-prioritized — alt text impact on page-level CTR is indirect. Keep alphabetical sort regardless of GSC mode.)

### 4.3 — CTR opportunities (GSC-only, only when GSC enabled)

When `gsc_mode: enabled` AND the GSC scan emitted `ctr_opportunity` findings:

```
**4.3** Rewrite titles + metas on N high-impressions / low-CTR pages

Hand-off:
\`\`\`
/plan-feature "Rewrite <title> and <meta name='description'> for N pages identified as high-impressions / low-CTR by GSC (from GSC Search Analytics Q2 pages digest):

1. /pricing (12,420 imps, 0.4% CTR vs 1.8% median, position 4.2)
2. /docs/getting-started (8,100 imps, 0.9% CTR, position 5.7)
3. /blog/llms-explained (6,400 imps, 1.1% CTR, position 6.1)
[...]

For each, pull the top 3-5 queries from GSC Search Analytics Q1 queries digest that drive impressions to this URL. Rewrite title + meta to address those specific search intents. Target: lift CTR to at least the median (1.8%). If half the pages reach median CTR, estimated +200-400 clicks/month."
\`\`\`
```

### 4.4 — Position-band query opportunities (GSC-only, only when GSC enabled)

```
**4.4** On-page optimization for N queries at position 5-20

Hand-off:
\`\`\`
/plan-feature "Improve on-page signals for N queries currently ranking at position 5-20 (from GSC Search Analytics Q1 queries digest):

1. 'best widgets' (4,200 imps, position 8.3, 2.1% CTR)
2. 'how to configure widgets' (2,100 imps, position 11.4, 1.5%)
[...]

For each query: identify the ranking page via GSC > Performance > Pages tab filtered by query. Improve on-page signals — H1/title alignment, content depth, internal links from related pages, schema markup, fresh dates if applicable. Moving from position 8-12 to position 3-5 typically 3-5x's clicks. Highest leverage: '<top query>' alone has potential for 100-400 additional clicks/month if it moves to top 5."
\`\`\`
```

## Phase 5 — Structured Data Buildout

Findings where JSON-LD scaffolds are needed beyond the allowlist (Phase 2 covers the scaffolds; this phase fills them in or adds judgment-heavy cases):

```
**5.1** Populate JSON-LD Article values across 8 blog posts

Hand-off:
\`\`\`
/plan-feature "Populate the JSON-LD Article values placed by /seo-review --fix in 8 blog posts (src/app/blog/*/page.tsx). For each: headline (use the post H1), datePublished (use frontmatter), dateModified (use file modified date or frontmatter), author.name (from frontmatter or site config), image (use the post's hero image URL — absolute path). Verify with Google Rich Results Test for each URL after."
\`\`\`
```

```
**5.2** Add Product schema to e-commerce pages (12 products)

Hand-off:
\`\`\`
/plan-feature "Add JSON-LD Product schema to 12 product pages (src/app/products/*/page.tsx). Each needs: name, image (array of product photos), description, offers.price, offers.priceCurrency, optional aggregateRating with reviewCount. Pull values from the CMS / product data source. Verify rich-result eligibility per product with Google Rich Results Test."
\`\`\`
```

## Phase 6 — Generative-Engine Optimization

The longest-horizon phase. Findings from `geo-generative` for E-E-A-T, semantic content patterns, and AI citation:

```
**6.1** Author bio pages for 4 contributors

Hand-off:
\`\`\`
/plan-feature "Create author bio pages for 4 contributors currently named in blog post bylines but without profile pages: Ada Lovelace, ... [list from findings]. Each bio: ≥200 words about expertise + credentials + photo + social/contact links. Place at /authors/<slug>. Link from each post byline. Goal: improve E-E-A-T (expertise + authoritativeness) signals — currently dropping ~3 points on Generative Engine readiness."
\`\`\`
```

```
**6.2** Add topic sentences + question-format headings to 6 long-form articles

Hand-off:
\`\`\`
/plan-feature "Improve AI-citability of 6 long-form articles (>1500 words) by (a) adding a clear topic sentence to the first paragraph of each major section, (b) rephrasing 30%+ of H2/H3 headings as questions (How / What / Why), (c) breaking dense factual paragraphs into bulleted lists or tables where it preserves meaning. Pages: src/content/blog/<8 paths from /seo-review findings>. Goal: increase citation likelihood in ChatGPT/Perplexity/Claude/Google AI Overviews."
\`\`\`
```

```
**6.3** Write llms.txt content (populate scaffold from --fix)

Hand-off:
\`\`\`
/plan-feature "Populate public/llms.txt scaffold (placed by /seo-review --fix). The site is a [type]. Sections should include: Documentation (link to /docs entries), Guides (link to /guides entries), API Reference (link to /api docs), About (link to /about). Each section has 3-8 markdown links to important pages with one-line descriptions. Reference the llmstxt.org spec. Goal: improve AI-engine discoverability of the site's important content."
\`\`\`
```

## Hand-off contract

Each `/plan-feature` snippet must be **fully self-contained**:
- Quote file paths
- For URL probes: quote the broken URL + status code
- For content rewrites: list the specific pages affected (don't say "fix all titles" — list which)
- State the success criterion: "+3 points on On-Page SEO" or "rich-result eligibility per Google Rich Results Test"
- Assume the receiver has no context from the SEO-review run

## What this mode does NOT do

- Apply edits (use `--fix` for the allowlist subset)
- Spawn subagents to refine briefs (the brief is the hand-off)
- Hydrate tasks directly (user runs `/plan-feature` per brief — that hydrates tasks via its own flow)
- Re-fetch best practices (the same brief from Step 1 of the parent `/seo-review` run is the basis)
