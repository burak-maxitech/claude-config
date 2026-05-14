# Report Template — /seo-review

Render the final report exactly in this order. Every section appears even if empty so the output structure is predictable across runs.

## Section 0 — Single Headline

Render this **first**, before everything else. Format depends on whether `docs/seo-history.md` exists:

**With history (delta visible):**

```
## /seo-review — <project name>

**SEO/GEO score: 72/100 (Δ +8 since 2026-04-30)** — Top 3 opportunities: missing meta descriptions (12 pages); no llms.txt; broken /products/v1 (404).
```

**Without history (first run):**

```
## /seo-review — <project name>

**SEO/GEO score: 72/100** — Top 3 opportunities: missing meta descriptions (12 pages); no llms.txt; broken /products/v1 (404).
```

**Top-3 opportunities** are computed in Step 6 by `score_impact × certainty / effort_weight` desc.

Special cases:
- Total score 90+: render line as `**SEO/GEO score: 92/100** — Top 3 opportunities: <list, but framed as polish>` so the user knows the site is already in good shape.
- Total score 0-30: prepend a warning line: `⚠ **SEO/GEO score: 22/100 — significant gaps.** Top 3 opportunities: ...`.

---

## Section 1 — Context

```
## Context

**Detected stack:** Next.js 14 app-router, TypeScript, next-i18next (en/fr/de)
**Sitemap:** public/sitemap.xml (47 URLs, probed)
**Best practices fetched:** 2026-05-14 from 5 sources (see footer for URLs)
**Coverage mode:** static + sitemap URL probe (use `--url <base>` for live HTML diff)

### Score breakdown by dimension

| Dimension | Score | Max | Sub-dim breakdown |
|---|---|---|---|
| Technical SEO | 22 | 25 | url_health: -1.5; canonicals: -1; mobile: -0.5 |
| On-Page SEO | 18 | 25 | meta_descriptions: -3; alt_text: -2; internal_linking: -2 |
| Structured Data | 14 | 20 | jsonld_coverage: -4; schema_validation: -2 |
| Generative Engine | 9 | 20 | llms_txt: -6; eeat: -3; semantic_content: -2 |
| Performance | 8 | 10 | image_perf: -1; response_time: -1 |
| **Total** | **72** | **100** | |
```

If the brief proposed weight adjustments, add a line: `Weight adjustments applied: Generative Engine +3 / Performance -2 / Structured Data -1 (from fetched brief).`

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

---

## Section 3 — Score History (only when `docs/seo-history.md` exists)

```
## Score History

| Date       | Score | Δ    | Top-3 priorities |
|------------|-------|------|------------------|
| 2026-05-14 | 72    | +8   | meta descriptions; llms.txt; broken URL |
| 2026-04-30 | 64    | +12  | sitemap.xml; OG tags; canonicals |
| 2026-04-15 | 52    | -    | starting score |

**Still outstanding from last run:** llms.txt (still missing); meta descriptions (was 18 missing, now 12 — improving).
```

Show last 5 entries. If history has >5 entries, link to the file.

---

## Section 4 — Suggested Next Actions

```
## Suggested Next Actions

**Skill chains:**
- Run `/seo-review --fix` first — 7 findings are allowlist-eligible mechanical scaffolds.
- Run `/seo-review --url https://example.com` to add live HTML diff and probe sitemap URLs (currently skipped because URLs are relative).
- Run `/code-cleanup --tests` if you see orphan-page warnings — some may correspond to deleted feature pages.
- After fixes land, re-run `/seo-review` to capture the new score in history.

**Top strategic improvements (copy-paste into a fresh /plan-feature session):**

\```bash
/plan-feature "Add llms.txt to public/ following the convention at https://llmstxt.org. Include sections for /docs, /api, /guides with markdown links to top pages. Description + section structure should match the site's purpose. Goal: improve citability in AI search (ChatGPT, Perplexity, Claude)."
\```

\```bash
/plan-feature "Write meta descriptions for 12 pages currently missing them. Pages list: src/app/about/page.tsx, src/app/pricing/page.tsx, ... [from /seo-review findings]. Each description should be 150-160 chars, summarize the page, and use action-oriented language. Goal: recover ~3 points on On-Page SEO dimension."
\```
```

If `--plan` flag is set, this section is replaced by the full phased brief (see `plan-mode-seo.md`).
If `--fix` flag is set, this section is replaced by the per-finding gate flow (see `fix-allowlist.md`).

---

## Section 5 — Footer Disclosure

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

Files scanned: 84
Files skipped (per .gitignore + vendored dirs): 312

subtotal_check: 22 + 18 + 14 + 9 + 8 = 71 ⚠ (headline shows 72 — recheck consolidation)
```

The `subtotal_check` line MUST show the arithmetic. If subtotals match the headline, render `... = 72 ✓`. If not, render the ⚠ with no auto-correction — the user sees the inconsistency directly rather than trusting a possibly-wrong headline silently.

Other footer notes:
- If `--url` was used: include `Live URL fetched: https://example.com (HTML excerpt 4.2k chars passed to seo-technical, seo-content)`.
- If probe was skipped: include `URL probe skipped: <reason>. Re-run with --url <base> for live URL health check.`
- If hreflang sub-dim was redistributed (no i18n): include `hreflang not applicable — points redistributed.`
- If best-practices fetch failed: include `⚠ best-practices fetch failed — used embedded heuristics only. Findings may not reflect current SEO/GEO guidance.`
