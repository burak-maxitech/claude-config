# Scoring Rubric

The `/seo-review` total score is out of 100, computed from 5 dimensions with **fixed base weights** and **±5 per-dimension tuning** applied from the orchestrator's fetched best-practices brief.

## Dimensions + base weights

| Dimension | Base weight | Tuning range | Owner subagent |
|---|---|---|---|
| Technical SEO | 25 | ±5 | `seo-technical` |
| On-Page SEO | 25 | ±5 | `seo-content` |
| Structured Data | 20 | ±5 | `geo-generative` |
| Generative Engine readiness | 20 | ±5 | `geo-generative` |
| Performance signals | 10 | ±5 | `seo-technical` |
| **Total** | **100** | sum delta = 0 | |

## Weight-tuning rules

The orchestrator's Step 1 fetch produces a "Weight adjustments suggested" block in the brief. Apply with these constraints:

1. **Per-dim cap: ±5.** A dimension can't move by more than 5 points in either direction in a single run.
2. **Sum delta must equal 0.** If Generative Engine bumps +3, some other dimension(s) must total -3.
3. **Total stays at 100.** Always.
4. **Score breakdown shows both base and adjusted.** Report renders `Generative Engine: 14/23 (base 20, +3 this run)` style.

If the brief proposes adjustments that violate these rules (e.g., requests +7 on one dim), the orchestrator caps to ±5 and notes the cap in the footer.

If the brief doesn't propose adjustments, use base weights as-is.

## Sub-dimension breakdowns

Each dimension has a sub-dimension breakdown that the subagent reports in its output. The breakdown shows where points were deducted. The orchestrator surfaces this in Section 1 of the report.

### Technical SEO — 25 points base

| Sub-dimension | Max points | Notes |
|---|---|---|
| `robots_sitemap` | 4 | robots.txt presence + correctness + sitemap.xml presence |
| `canonicals` | 4 | `<link rel="canonical">` presence + correctness |
| `mobile` | 3 | viewport meta correctness |
| `hreflang` | 3 | only counted if i18n detected; otherwise redistributes proportionally to other sub-dims |
| `redirects` | 3 | framework config redirect chains + 301/302 correctness |
| **`url_health`** | **8** | sitemap URL probe — 4xx/5xx/redirect chains. **Hard cap.** |

### On-Page SEO — 25 points base

| Sub-dimension | Max points |
|---|---|
| `titles` | 5 |
| `meta_descriptions` | 4 |
| `headings` (H1 uniqueness + hierarchy) | 4 |
| `alt_text` | 4 |
| `og_twitter` (OpenGraph + Twitter Cards) | 4 |
| `internal_linking` (orphans + broken + anchor quality) | 3 |
| `content_depth` (thin content nudge) | 1 |

### Structured Data — 20 points base

| Sub-dimension | Max points |
|---|---|
| `jsonld_coverage` (Organization on root, Article on blog, Product on e-com, BreadcrumbList everywhere) | 10 |
| `schema_validation` + `rich_result` (required fields, common rich-result blockers) | 10 |

### Generative Engine readiness — 20 points base

| Sub-dimension | Max points |
|---|---|
| `llms_txt` (presence + format) | 6 |
| `eeat` (E-E-A-T signals — author bios, dates, citations, About/Contact) | 6 |
| `semantic_content` (topic sentences, list/table structure, question-headings) | 5 |
| `ai_bot_access` (robots.txt rules for GPTBot/ClaudeBot/PerplexityBot/etc.) | 3 |

### Performance signals — 10 points base

| Sub-dimension | Max points |
|---|---|
| `image_perf` (width/height, lazy loading) | 4 |
| `font_script_perf` (preload, async/defer, inline base64) | 3 |
| `response_time` (sitemap URL probe response times) | 3 |

---

## Scoring computation

Each subagent reports per-finding `score_impact` (points lost). The subagent's dimension total is:

```
dimension_total = adjusted_dimension_max - sum(score_impact)
```

Floor at 0. The total report score is:

```
total = sum(dimension_total for each dimension)
```

Always 0-100.

## Subtotal-check footer

The orchestrator's Step 6 prints in the footer:

```
subtotal_check: 22 + 21 + 14 + 9 + 8 = 74 ✓
```

If subtotals don't sum to the headline total, the line shows the discrepancy with a ⚠ marker — visible to the user rather than the headline silently lying.

## Special case: hreflang not applicable

When i18n is not detected, the `hreflang` sub-dimension (3 points) is redistributed proportionally to the other Technical SEO sub-dimensions:

| Sub-dim | Without i18n | With i18n |
|---|---|---|
| robots_sitemap | 5 | 4 |
| canonicals | 5 | 4 |
| mobile | 4 | 3 |
| hreflang | 0 | 3 |
| redirects | 3 | 3 |
| url_health | 8 | 8 |

Technical SEO total stays at 25 either way. Report notes "hreflang not applicable — points redistributed" in the footer.

## Probe-skipped case

When sitemap URL probe didn't run (no sitemap, relative URLs without --url), the `url_health` sub-dimension is 0/0 — no points deducted, but the maximum is also 0 for this dim. To keep the total at 100, the missing 8 points redistribute proportionally across other Technical SEO sub-dims that ran:

| Sub-dim | Probe ran | Probe skipped |
|---|---|---|
| robots_sitemap | 4 | 6 |
| canonicals | 4 | 6 |
| mobile | 3 | 5 |
| hreflang | 3 | 4 |
| redirects | 3 | 4 |
| url_health | 8 | 0 |

Footer notes "URL probe skipped — Technical SEO sub-dim weights redistributed." User can re-run with `--url <base>` to get URL health scored.
