# Report Template — /bx:seo

Render the final report exactly in this order. Every section appears even if empty so the output structure is predictable across runs.

## Section 0 — Single Headline

Render this **first**, before everything else. Format depends on whether `docs/seo-history.md` exists:

**With history (delta visible):**

```
## /bx:seo — <project name>

**SEO/GEO score: 72/100 (Δ +8 since 2026-04-30)** — Top 3 opportunities: missing meta descriptions (12 pages); no Article JSON-LD on blog posts; broken /products/v1 (404).
```

**Without history (first run):**

```
## /bx:seo — <project name>

**SEO/GEO score: 72/100** — Top 3 opportunities: missing meta descriptions (12 pages); no Article JSON-LD on blog posts; broken /products/v1 (404).
```

**Top-3 opportunities** are computed in Step 6.6:
- Without GSC: `rank_score = score_impact × certainty × traffic_weight / effort_weight` where `traffic_weight = 1.0` (heuristic-only behavior).
- With GSC: same formula, but `traffic_weight = max(1.0, log10(url_impressions + 1))` when the affected URL has GSC traffic data, and GSC findings rank via `effective_impact = log10(impressions + 1)` (so they can land in top-3 despite `score_impact: 0`).

When GSC findings land in top-3, prefix the priority string with `[gsc]`:

```
**SEO/GEO score: 72/100 (Δ +8 since 2026-04-30)** — Top 3 opportunities: [gsc] CTR opportunity on /pricing (12.4K imps, 0.4% CTR); no Article JSON-LD on blog posts; [gsc] 775 × 404 at Google's view (matches recent rename).
```

The headline stays single-line regardless of GSC mode — never render a separate "GSC top-3" line.

Special cases:
- Total score 90+: render line as `**SEO/GEO score: 92/100** — Top 3 opportunities: <list, but framed as polish>` so the user knows the site is already in good shape.
- Total score 0-30: prepend a warning line: `⚠ **SEO/GEO score: 22/100 — significant gaps.** Top 3 opportunities: ...`.

---

## Section 1 — Context

Render `## Context` heading, then — **conditionally** — the "No GSC data" banner, then the context block below.

### Section 1 banner — "No GSC data" variant (heuristic-only mode only)

When Step 1.6 resolves `gsc_mode == "disabled"` (no `.seo-data/gsc/config.yaml`, or API path failed), prepend this banner immediately under the `## Context` heading, before the **Detected stack** line:

```
> ⚠ **No GSC data — code-only review.** Recommendations cannot be
> traffic-prioritized. The /100 score is unaffected (GSC is informational),
> but with GSC data the top-3 priorities can be re-ranked by real impressions
> and 404 clusters can be auto-matched to recent code renames.
>
> See `.seo-data/gsc/README.md` to enable GSC API audit. The one-time
> setup banner at the top of this run covers the quickest path.
```

When `gsc_mode == "enabled"`, DO NOT render this banner — the GSC mode line in the context block is sufficient.

### Context block (always renders)

```
## Context

**Detected stack:** Next.js 14 app-router, TypeScript, next-i18next (en/fr/de)
**Sitemap:** public/sitemap.xml (47 URLs, probed)
**Best practices fetched:** 2026-05-14 from 5 sources (see footer for URLs)
**Coverage mode:** static + sitemap URL probe (use `--url <base>` for live HTML diff)
**GSC mode:** enabled (Search Console API — 194 URLs inspected, 3 perf queries)

### Score breakdown by dimension

| Dimension | Score | Max | Sub-dim breakdown |
|---|---|---|---|
| Technical SEO | 22 | 25 | url_health: -1.5; canonicals: -1; mobile: -0.5 |
| On-Page SEO | 18 | 25 | meta_descriptions: -3; alt_text: -2; internal_linking: -2 |
| Structured Data | 14 | 20 | jsonld_coverage: -4; schema_validation: -2 |
| Generative Engine | 9 | 20 | eeat: -5; ai_bot_access_declared: -2; ai_bot_access_delivered: -2; semantic_content: -2 |
| Performance | 8 | 10 | image_perf: -1; response_time: -1 |
| **Total** | **72** | **100** | |
```

The `**GSC mode:**` line uses the fragment string from Step 1.6.10 (one of two: enabled with summary, or omitted entirely). Omit the line in heuristic-only mode — the banner above already conveys the state.

If the brief proposed weight adjustments, add a line: `Weight adjustments applied: Generative Engine +3 / Performance -2 / Structured Data -1 (from fetched brief).`

**Probe-skipped rendering (S31 dogfood fix).** When the sitemap URL probe didn't run (dynamic sitemap.ts, no static output, no `--url` flag) and `url_health` is 0/0, the Technical SEO Sub-dim breakdown column MUST surface the redistribution explicitly. The dogfood report rendered `url_health: 0/0 (probe skipped)` without explaining that the missing 5 points elevated the other sub-dims' caps — users couldn't audit the score. Use Form A from `rubric.md` "Rendering the redistribution":

```
| Technical SEO | 16 | 25 | canonicals: -5.25; hreflang: -2; robots_sitemap: -1.5; redirects: -0.5; url_health: 0/0 (probe skipped, 8pts redistributed: canonicals +2, robots_sitemap +2, mobile +2, hreflang +1, redirects +1) |
```

When the hreflang sub-dim is also redistributed (non-i18n project), stack both: `(probe skipped + no-i18n, 11pts redistributed: ...)`.

---

## Section 2 — Findings

Five subsections, one per dimension, ordered by `total_score_impact_on_dim` descending across the report.

```
### Technical SEO Findings

| Rank | Location                            | Title                              | Sub-dim       | Sev | Cert | Effort | Impact | Fix? |
|------|-------------------------------------|------------------------------------|---------------|-----|------|--------|--------|------|
| 1    | https://example.com/products/v1     | 404 on sitemap URL                 | url_health    | H   | 1.0  | small  | -1.5   | no   |
| 2    | src/app/layout.tsx:14               | Missing self-referencing canonical | canonicals    | M   | 0.9  | trivial| -1.0   | yes  |
| 3    | public/robots.txt                   | No sitemap reference               | robots_sitemap| L   | 1.0  | trivial| -0.5   | yes  |
| ...  | ...                                 | ...                                | ...           | ... | ...  | ...    | ...    | ...  |
```

Below each table, render the #1-ranked finding's detail block:

```
**#1 — 404 on sitemap URL (`https://example.com/products/v1`)**

Status: 404 Not Found. The URL is listed in public/sitemap.xml but returns 404 on probe. This wastes crawl budget and signals an outdated sitemap.

Recommendation: either restore the page (if intended to exist) or remove the entry from sitemap.xml. If pages were moved, add a 301 redirect from /products/v1 to the new location and update the sitemap entry.

Fix mode: not eligible (requires judgment about whether to restore or remove).
```

Repeat per dimension. Don't render detail blocks for every finding — only #1 per dimension; the table covers the rest.

### Dimension add-on blocks (2.20.0)

Some checks are easier to read as a table than as finding rows. Render each block **below its dimension's findings table and #1 detail block**, only when its data exists; the findings themselves still appear in the table as usual.

**Generative Engine → AI crawler delivery** (from Step 3.5 `bot-probe`; omit when the probe was skipped — the footer says why):

```
#### AI crawler delivery (live probe — what each bot was served, not what robots.txt says)

| Bot              | Group    | robots.txt   | Served (base URL)              | Verdict      |
|------------------|----------|--------------|--------------------------------|--------------|
| (browser control)| —        | —            | 200, 48 KB                     | —            |
| OAI-SearchBot    | search   | allow        | 403 · cf-mitigated: challenge  | challenged ⚠ |
| Claude-SearchBot | search   | allow        | 200, 47 KB                     | ok           |
| PerplexityBot    | search   | allow        | 200, 9 KB                      | differs ⚠    |
| ChatGPT-User     | user     | unspecified  | 200, 48 KB                     | ok           |
| GPTBot           | training | disallow     | 403                            | blocked (matches policy) |
| Google-Extended  | training | disallow     | robots-only token — not fetched | —           |

Pages probed: /, /pricing, /blog/guide (worst verdict per bot shown; per-page detail in the finding evidence).
Policy (site profile): search_yes_training_no. CDN/WAF suspects: OAI-SearchBot.
Policy conflicts: Content-Signal `ai-input=no` while search bots are allowed.

A blocked or challenged spoofed user agent is not proof the real crawler is blocked — a WAF that verifies bot IPs rejects a spoofed UA too. Confirm in your CDN dashboard against the vendor's published IP list.
```

Mark a verdict with ⚠ only when it contradicts the declared `ai_policy` (a blocked training bot under `search_yes_training_no` is the policy working). `differs` = 200 but under half the control's bytes.

**Structured Data → Schema vs visible text** (from geo-generative's `schema_visible_mismatch`, built on page-audit `schema_visible_checks`; omit when no page had a mismatch or page-audit was skipped):

```
#### Schema vs visible text (raw HTML as crawlers receive it)

| URL       | Type         | Field     | JSON-LD value        | Visible text            |
|-----------|--------------|-----------|----------------------|-------------------------|
| /pricing  | Product      | price     | 49.00 USD            | not found               |
| /contact  | LocalBusiness| telephone | +1 555 0100          | not found               |

Only mismatches are listed; "not found" means the value does not appear in the normalised visible raw text — check whether the page shows a different value or none. Markup that contradicts the page can be repeated by AI answers, and Google requires structured data to match visible content.
```

**Technical SEO → rendered-only directives** need no add-on block: `rendered_only_directive` findings sit in the Technical table, and their evidence shows `raw: <value> → rendered: <value>` per URL. `utm_stripped`, `indexnow_missing` and the soft-navigation note are info rows (`Impact 0`) in the Technical and Performance tables.

---

## Section 3 — GSC Insights (only when `gsc_mode: enabled`)

Render this section between Findings (Section 2) and Score History (Section 4) **only when GSC API ingestion produced findings in Step 1.6**, or when Bing exports produced a `bing_ai_citations` finding (then render the heading, the info line and the Bing sub-block only). Skip entirely otherwise — no banner, no placeholder. The section has 10 sub-blocks (Indexing coverage / **Index Coverage regression** / Top-impact GSC findings / CTR opportunities / **AI Overview compression** / Position-band query opportunities / Traffic orphans / **Ranking-update windows** / **Bing AI citations** / Code-already-fixed annotations); render only those that have data.

```
## GSC Insights

Real-world signal from Google Search Console — informational, does NOT affect /100 score.

### Indexing coverage (from URL Inspection sample)

Of 95 inspected URLs, 67 (71%) are not indexed cleanly. Per-reason breakdown from the sample:

| Reason                                          | Inspected URLs | Most actionable |
|-------------------------------------------------|----------------|-----------------|
| Crawled - currently not indexed                 | 28 | ✓ content quality / E-E-A-T |
| Discovered - currently not indexed              | 14 | ✓ crawl budget / internal links |
| Not found (404)                                 | 12 | ✓ bulk redirect / sitemap clean |
| Page with redirect                              |  6 | ✓ sitemap hygiene |
| Blocked due to access forbidden (403)           |  3 | usually intentional |
| Duplicate, Google chose different canonical     |  2 | ✓ canonical investigation |
| Soft 404                                        |  2 | ✓ rendering fix |

(Counts reflect the inspected-URL sample, not site-wide truth. URL Inspection samples high-impression + git-changed + sitemap-orphan URLs — see `gsc-api-queries.md` "URL Inspection — selection algorithm".)

### Index Coverage regression (snapshot diff)

Render this sub-block **only when a prior snapshot exists** (i.e., this is not the first run for the property). Pulls from sub-dim 14 (`deindex_regression`) finding + Step 1.6.13.5 inflection-point footer lines.

When transitions detected (one finding emitted from Step 1.6.13.4):

```
⚠ 47 URLs deindexed since previous run on 2026-05-13 (commit 5a441d1)

Likely caused by recent changes:
- commit 7109213 (2026-05-15): "feat(bx:seo): 6 fixes from burakarik6 dogfood"
- (cross-reference Step 1.5's git digest for the routing change)

Transition breakdown:
| Transition class             | Count | Severity |
|------------------------------|-------|----------|
| Page with redirect (i18n)    | 38    | high     |
| Crawled - not indexed        | 7     | high     |
| Not found (404)              | 2     | high     |

Path clusters (≥3 URLs each):
- /en/photo/* (24 URLs)
- /tr/photo/* (12 URLs)
- /photo/* (8 URLs)

Sample transitions (top 5):
- https://burakarik.com/en/photo/granada-sokakları | Submitted and indexed → Page with redirect
- https://burakarik.com/tr/gallery/slovenia | Submitted and indexed → Page with redirect
- ... (full list in snapshot diff at .seo-data/gsc/snapshots/2026-05-26T143200-5a441d1.json)

**This may correspond to a Google Search Console "Validation failed" or "New reason preventing your pages from being indexed" email.** Cross-reference sub-dim 5 (redirect_hygiene) in this run's findings for the locale-prefix-cluster diagnosis. Recovery path: see the sub-dim 14 finding's recommended_action.

Count deltas since previous run:
- Page-with-redirect: 838 (delta +47). ⚠ Climbing fast.
- Crawled-not-indexed: 142 (delta -8). Improving.
- Submitted-and-indexed: 1,247 (delta -39). Net loss.
```

When no transitions detected but prior snapshot exists, render only the count deltas + recovery line:

```
Index Coverage regression: no negative transitions detected since previous run (2026-05-13). ✓

Count deltas since previous run:
- Submitted-and-indexed: 1,286 (delta +12). Improving.
- Crawled-not-indexed: 130 (delta -8). Improving.

Recoveries: 5 URLs returned to "Submitted and indexed" since previous run.
```

When this is the first run for the property (no prior snapshot), omit this sub-block entirely. Footer-only line from Step 1.6.13.2 covers the activation: `Index Coverage snapshots: first run for this property. Regression detection activates on next /bx:seo run.`

### Top-impact GSC findings

| Rank | Sub-dim                  | Title                                                           | Imps   | CTR  | Pos  | Code-changed? |
|------|--------------------------|-----------------------------------------------------------------|--------|------|------|---------------|
| 1    | not_found_404            | 775 URLs return 404 at Google's view (matches /blog/2023/* rename) | —      | —    | —    | YES (2026-04-10) |
| 2    | ctr_opportunity          | CTR opportunity on /pricing (12.4K imps, 0.4% CTR)             | 12,420 | 0.4% | 4.2  | YES (2026-04-22) |
| 3    | crawled_not_indexed      | 1,146 pages crawled but not indexed (content quality cluster)   | —      | —    | —    | NO              |
| 4    | position_band_opportunity| Query 'best widgets' at pos 8.3, 4,200 imps                    | 4,200  | 2.1% | 8.3  | NO              |
| 5    | discovered_not_indexed   | 726 pages discovered but not crawled (linking signal)           | —      | —    | —    | NO              |

(Top 5 from N total GSC findings. Full list ranked by impressions × certainty / effort_weight.)

### CTR opportunities (high impressions, low CTR — top 5 from Q2 pages digest)

| URL                          | Impressions | CTR   | Median CTR | Position |
|------------------------------|-------------|-------|------------|----------|
| /pricing                     | 12,420      | 0.4%  | 1.8%       | 4.2      |
| /docs/getting-started        |  8,100      | 0.9%  | 1.8%       | 5.7      |
| /blog/2025/llms-explained    |  6,400      | 1.1%  | 1.8%       | 6.1      |
| /products/api                |  4,800      | 0.6%  | 1.8%       | 3.8      |
| /about                       |  3,200      | 0.5%  | 1.8%       | 7.2      |

Title + meta rewrites on these 5 pages alone could recover an estimated 200-400 clicks/month.

(Pages that also appear under "AI Overview compression" below carry `AIO?` in an extra column and are excluded from the rewrite estimate.)

### AI Overview compression (sub-dim 17 — CTR fell at a steady position on AI-Overview-prone queries)

Render only when the `ai_overview_compression` finding exists.

AI-Overview-prone queries (question-form or 6+ words): CTR 3.1% → 1.7% at pos 4.2 → 4.0. Other queries: CTR 2.4% → 2.3%. The drop is concentrated where Google often shows an AI Overview.

| URL                       | AIO-prone share | CTR change | Position change | In Generative AI report? |
|---------------------------|-----------------|------------|-----------------|--------------------------|
| /blog/how-to-pick-widgets | 82%             | −41%       | +0.3            | yes                      |
| /guides/widget-vs-gadget  | 74%             | −28%       | −0.6            | no export                |

**Expected, not a title defect.** Pew's independent panel found users clicked a traditional result on 8% of visits with an AI summary vs 15% without. Judge these pages on clicks and conversions, not CTR; do not rewrite their titles for CTR. "In Generative AI report?" is `yes` / `no` (export present, page absent — weaker evidence) / `no export`.

### Position-band query opportunities (positions 5-20 with ≥100 imps — top 5 from Q1 queries digest)

| Query                        | Impressions | Clicks | CTR  | Position |
|------------------------------|-------------|--------|------|----------|
| best widgets                 | 4,200       | 88     | 2.1% | 8.3      |
| how to configure widgets     | 2,100       | 31     | 1.5% | 11.4     |
| widget pricing               | 1,800       | 22     | 1.2% | 14.8     |
| widget alternatives          | 1,200       | 18     | 1.5% | 9.7      |
| open source widget tool      |   650       | 12     | 1.8% | 12.1     |

Moving any of these from position 8-14 to position 3-5 typically 3-5x's clicks. Identify which page ranks for each query via GSC > Performance > Pages tab filtered by query.

### Traffic orphans (sitemap URLs with 0 impressions in window)

23 URLs in sitemap.xml received 0 impressions across GSC's data window. Sample: /archive/2019/jan, /author/legacy-contributor, /tag/deprecated-feature, … Audit: improve content + internal links, remove from sitemap if they shouldn't rank, or accept as legitimate low-traffic pages.

### Ranking-update windows (Google Search Status Dashboard overlay)

Render when any finding or due watchpoint has a non-empty `update_overlap`. When the overlay was unavailable, render one line instead: `Ranking-update overlay unavailable (<reason>) — time-windowed findings below were not checked against Google updates.`

| Finding / watchpoint                 | Data window             | Overlapping update (kind, dates)              | Effect |
|--------------------------------------|-------------------------|-----------------------------------------------|--------|
| content_decay (6 pages)              | 2026-08-14 → 2026-11-05 | November 2026 core update (core, 11-10 → ongoing) | certainty −0.15; "may be the update" |
| deindex_regression (7 quality-class) | 2026-10-30 → 2026-11-20 | November 2026 core update (core, 11-10 → ongoing) | advice notes possible reassessment |
| watchpoint /pricing (CTR)            | 2026-10-22 → 2026-11-20 | November 2026 core update (core, 11-10 → ongoing) | verdict → inconclusive |

A Google core or spam update can move rankings and clicks with no change on the site. Let a rollout finish and wait at least a week before comparing; until then, treat these findings as "possibly the update", not as site regressions or failed fixes. (Dates above are illustrative.)

### Bing AI citations (sub-dim 18 — from Bing Webmaster Tools AI Performance exports)

Render when the `bing_ai_citations` finding exists (with or without GSC).

Bing AI citations, <period>: **<total>** (Copilot and Bing AI summaries; no clicks; Bing keeps about 3 months).

| Cited page          | Citations | Money page? |
|---------------------|-----------|-------------|
| /blog/widget-guide  | 212       | no          |
| /pricing            | 31        | yes         |

Top grounding queries: "best widget for small teams" (44), "widget vs gadget" (29), … Branded share: 12%.
Money pages with no citations: /enterprise, /integrations. Same-run cross-links: /enterprise — `geo_raw_html_gap`.

Info only — a single export is a snapshot; compare totals run over run. Counts are Bing's surfaces only, not ChatGPT, Claude or Perplexity.

### Code-already-fixed annotations

3 of 18 GSC findings flagged `code_changed_since_gsc_window: true` (recent commits touched the affected paths within 35 days). Confidence lowered to 0.4 for these. They may resolve in the next GSC update cycle (2-4 weeks). Manually request indexing via GSC for the highest-traffic ones to accelerate.
```

If `gsc_mode: disabled`, this entire section is omitted. The skill produces score, findings, and ranking purely from heuristic signals.

---

## Section 4 — Score History (only when `docs/seo-history.md` exists)

```
## Score History

| Date       | Score | Δ    | Top-3 priorities |
|------------|-------|------|------------------|
| 2026-05-14 | 72    | +8   | [gsc] CTR opp on /pricing (12.4K imps); No Article JSON-LD on blog; [gsc] 1,146 crawled-not-indexed |
| 2026-04-30 | 64    | +12  | sitemap.xml; OG tags; canonicals |
| 2026-04-15 | 52    | -    | starting score |

**Still outstanding from last run:** Article JSON-LD (still missing); meta descriptions (was 18 missing, now 12 — improving).
```

Show last 5 entries. If history has >5 entries, link to the file.

**`[gsc]` prefix** on a top-3 priority string indicates the priority came from a GSC finding (see `rubric.md` "History row format"). Lets readers see why a row's priorities shifted between runs — e.g., user enabled or disabled the GSC API between two runs. Heuristic priorities have no prefix.

---

## Section 5 — Suggested Next Actions

```
## Suggested Next Actions

**Skill chains:**
- Run `/bx:seo --fix` first — 7 findings are allowlist-eligible mechanical scaffolds.
- Run `/bx:seo --url https://example.com` to add live HTML diff and probe sitemap URLs (currently skipped because URLs are relative).
- Run `/bx:clean --tests` if you see orphan-page warnings — some may correspond to deleted feature pages.
- After fixes land, re-run `/bx:seo` to capture the new score in history.

**Top strategic improvements (copy-paste into a fresh /bx:plan session):**

\```bash
/bx:plan "Add visible author bylines linking to author pages with credentials on the 8 blog posts flagged by /bx:seo (eeat). Use only facts from .seo-data/site-profile.yaml 'authors' — leave TODO where a credential is unknown. Goal: stronger E-E-A-T signals for Google and AI search citations."
\```

\```bash
/bx:plan "Write meta descriptions for 12 pages currently missing them. Pages list: src/app/about/page.tsx, src/app/pricing/page.tsx, ... [from /bx:seo findings]. Each description should be 150-160 chars, summarize the page, and use action-oriented language. Goal: recover ~3 points on On-Page SEO dimension."
\```
```

If `--plan` flag is set, this section is replaced by the full phased brief (see `plan-mode-seo.md`).
If `--fix` flag is set, this section is replaced by the per-finding gate flow (see `fix-allowlist.md`).

---

## Section 6 — Footer Disclosure

```
---

Best-practices brief fetched: 2026-05-14T14:32:00Z
Sources fetched (5):
- https://developers.google.com/search/docs/fundamentals/seo-starter-guide
- https://web.dev/learn/seo
- https://schema.org/Article
- https://llmstxt.org/
- (WebSearch for "AI search citation patterns 2026" — 3 highest-signal results consumed)

Brief divergences from embedded heuristics: 2 (see findings tagged `brief_divergence`)

Detected stack: Next.js 14 app-router, TypeScript, next-i18next
i18n: yes (en/fr/de — hreflang scan applied)
Sitemap URL probe: 47 URLs probed; 2 failures (1 × 404, 1 × redirect chain >1 hop)
Probe cap: 100 URLs (47 in this sitemap; no cap hit)

Git history scan: 35d, 23 SEO-relevant commits across 14 files. Shallow: no.

GSC API: Q1+Q2+Q3 succeeded; URL Inspection 194/200 (6 skipped — 5 unknown to Google, 1 transient 5xx).
Page-type map: 84 URLs classified (54 article / 18 product / 12 other).
URL impressions map: 312 URLs with traffic data.
API call failures: 0.

Files scanned: 84
Files skipped (per .gitignore + vendored dirs): 312

subtotal_check: 22 + 18 + 14 + 9 + 8 = 71 ⚠ (headline shows 72 — recheck consolidation) | gsc_findings: 18 (info-only, 0 score impact)
```

The `subtotal_check` line MUST show the arithmetic. If subtotals match the headline, render `... = 72 ✓`. If not, render the ⚠ with no auto-correction — the user sees the inconsistency directly rather than trusting a possibly-wrong headline silently. When GSC mode is enabled, append `| gsc_findings: <count> (info-only, 0 score impact)` to the same line.

Other footer notes:
- If `--url` was used: include `Live URL fetched: https://example.com (HTML excerpt 4.2k chars passed to seo-technical, seo-content)`.
- If probe was skipped: include `URL probe skipped: <reason>. Re-run with --url <base> for live URL health check.`
- If hreflang sub-dim was redistributed (no i18n): include `hreflang not applicable — points redistributed.`
- If best-practices fetch failed: include `⚠ best-practices fetch failed — used embedded heuristics only. Findings may not reflect current SEO/GEO guidance.`

**GSC-mode footer additions** (when `gsc_mode: enabled`):
- `Git history scan: 35d, <N> SEO-relevant commits across <M> files. Shallow: <true | false>.` — when shallow: `Git history scan: skipped (shallow clone).`
- `GSC API: Q1+Q2+Q3 <succeeded|N/3 failed>; URL Inspection <N>/<budget> (<skip count + reasons if any>).`
- `GSC API cache: <N>/<M> hits (split TTL: 24h on sa-*, 7d on ui-*<; fresh-call details>). Use --no-cache to force refresh.` — see `gsc-cache.md` "Footer line" for full format examples (full-hit, partial-hit, full-miss/bypass variants).
- `Page-type map: <N> URLs classified (<distribution>).`
- `URL impressions map: <N> URLs with traffic data.`
- `API call failures: <N> (<endpoint, http_status, error_status per line>).` — only when any API call failed.
- `Ranking-update overlay: <N> Google updates on record (source: <status-dashboard | cache, age Nd>); <M> findings and <W> watchpoints overlap.` — or `Ranking-update overlay unavailable: <reason>.`
- `AIO segmentation: AIO-prone CTR <prev>% → <now>%, other <prev>% → <now>%; <P> pages in ai_overview_compression, <R> content_decay ctr_loss URLs routed there.`

**2.20.0 footer lines** (any mode; each omitted when its step did not run and printed with its skip reason when it was skipped). The exact strings are owned by SKILL.md:
- `AI-crawler probe: …` (Step 3.5) — bots × pages, verdict counts, CDN/WAF suspects, policy conflicts, `utm_source` kept/stripped, IndexNow key state.
- `Page audit: …` (Step 3.4) — now also `<D> rendered-only directives; <G> raw-HTML gaps`, or `render-compare skipped (<reason>)`.
- `Bing exports: <N> files parsed, <total> citations over <period>.` — or `Bing exports: none (drop Bing Webmaster Tools AI Performance CSVs into .seo-data/bing/exports/ to track AI citations).` only when `site_profile.bing_verified: yes`.

**GSC-mode subtotal-check addendum:** append `| gsc_findings: <count> (info-only, 0 score impact)` to the subtotal_check line so reviewers can confirm GSC ran without affecting the score.

**When `gsc_mode: disabled`:** omit all GSC-mode footer additions. If the one-time setup banner fired this run, the banner itself appears BEFORE Section 1 (not in the footer).
