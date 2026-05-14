# --plan Mode (seo-review)

Transform `/seo-review` findings into a phased improvement brief. Each phase becomes a self-contained `/plan-feature <brief>` payload the user can drop into a fresh session.

## Phase grouping

After the report is built, group findings into 6 phases (broken-URL triage comes first because it directly damages search-engine trust and crawl budget):

1. **Phase 1: Broken URL triage** (if any 4xx / 5xx surfaced from sitemap probe)
2. **Phase 2: Quick wins** (allowlist-eligible mechanical scaffolds)
3. **Phase 3: Structural improvements** (heading hierarchy, internal linking, redirect chains)
4. **Phase 4: Content rewrites** (titles, meta descriptions, alt text — human judgment required)
5. **Phase 5: Structured data buildout** (JSON-LD per content type)
6. **Phase 6: Generative-engine optimization** (llms.txt + E-E-A-T + AI-citability)

## Phase 1 — Broken URL Triage

Surface every `dimension: technical_seo, sub_dimension: url_health` finding with `status` in {4xx, 5xx}. Order by status severity (5xx first, then 404, then 403, then 410).

Per finding emit a `/plan-feature` snippet that names the broken URL + likely cause + recommended action:

```
**1.1** 404 on https://example.com/products/v1 (sitemap entry)

Hand-off:
\`\`\`
/plan-feature "Investigate the 404 on https://example.com/products/v1 listed in public/sitemap.xml. Check (a) whether the page should still exist — review git history for src/app/products/v1/ or equivalent route, (b) whether it was renamed — search for similar paths like /products/version-1 or /products/v2, (c) whether a redirect should be added. If page was deliberately removed, also remove the URL from sitemap.xml. If renamed, add a 301 in next.config.js redirects() and update the sitemap. Verify with curl -I https://example.com/products/v1 after."
\`\`\`
```

If many broken URLs share a pattern (e.g., all under `/blog/2023/*`), batch them in one `/plan-feature` snippet:

```
**1.X** 12 × 404s under /blog/2023/* (likely deleted year folder)

Hand-off:
\`\`\`
/plan-feature "12 blog posts under /blog/2023/* return 404 but are listed in sitemap.xml. Investigate whether (a) the year-2023 folder was deliberately retired — if so, remove all 12 entries from sitemap.xml, (b) they were moved to a new structure (e.g., /blog/<slug> flat) — if so, add 301 redirects in bulk via the framework redirects config and update sitemap entries, (c) they should be restored from a backup. Sample URLs: /blog/2023/jan-update, /blog/2023/feb-update, /blog/2023/march-roundup. Verify all 12 with a parallel curl after fix."
\`\`\`
```

Estimated effort: depends on count + cause. Often the highest-leverage phase per hour spent.

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

## Phase 4 — Content Rewrites (Human Judgment)

Findings where the fix requires writing or rewriting copy:
- Weak / missing titles
- Missing or boilerplate meta descriptions
- Missing or filename-based alt text on content images
- Anchor text quality issues (`click here`, `read more`)

These cluster by file or by content domain. Example:

```
**4.1** Write meta descriptions for 12 pages missing them

Hand-off:
\`\`\`
/plan-feature "Write meta descriptions for 12 pages currently missing them. Pages: src/app/about/page.tsx, src/app/pricing/page.tsx, src/app/blog/foo/page.tsx, [... list from findings]. Each description should be 150-160 chars, summarize the page's value to the visitor, and use action-oriented language. Reference the page's H1 and first paragraph for context. After writing, verify in /seo-review re-run that On-Page SEO score recovers ~3 points."
\`\`\`
```

```
**4.2** Rewrite weak alt text on 8 content images

Hand-off:
\`\`\`
/plan-feature "Rewrite alt text on 8 content images currently using filename-as-alt or generic 'image' patterns. Images: src/components/Hero/hero.jpg, src/app/blog/foo/diagram.png, [... list]. For each, write descriptive alt that conveys the image's information value (not appearance). Goal: alt text accessible to screen readers AND useful as SEO image context."
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
