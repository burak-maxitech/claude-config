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

Each subagent reports per-finding `score_impact` (points lost). Findings are grouped by sub-dimension and the per-sub-dim sum is **clamped at the sub-dim's max points** before contributing to the dimension total. This keeps the Section 1 breakdown internally consistent — a sub-dim's reported deduction never exceeds its allocation, even when many findings land in the same bucket (e.g., 8+ `<img>` tags missing dimensions don't show a `-4.5` against a 4-point `image_perf` sub-dim).

```
sub_dim_deduction = min(sum(score_impact for findings in this sub_dim), sub_dim_max)
dimension_total = adjusted_dimension_max - sum(sub_dim_deductions)
```

Floor `dimension_total` at 0. The total report score is:

```
total = sum(dimension_total for each dimension)
```

Always 0-100.

**Clamp enforcement lives in the orchestrator's Step 6.1** (`SKILL.md`) so the rubric is the single source of truth and subagents don't need to track sub-dim caps locally. Sub-dim caps are the **base** values from the tables above and are *not* rescaled by weight adjustments — weight adjustments only move the dimension max, never the sub-dim caps.

## GSC findings — info-only

When `.seo-data/gsc/` contains Google Search Console CSV exports, the `seo-gsc-insights` subagent (4th parallel subagent) emits **info-only findings**: they appear in the report and rank alongside heuristic findings for headline top-3, but **never deduct from the /100 score**. The score stays purely heuristic so `docs/seo-history.md` remains apples-to-apples comparable across runs with or without CSVs present.

### Score-impact invariant

GSC findings carry `score_impact: 0`. **The orchestrator enforces this** in Step 6 — mirroring the sub-dim clamp single-point-of-enforcement pattern above — by zeroing any non-zero `score_impact` emitted on a finding whose `source == "gsc"`. The subagent may emit non-zero by mistake; the orchestrator overrides.

```
for finding in findings:
    if finding.source == "gsc":
        finding.score_impact = 0   # always, regardless of emitted value
```

This is **the single point of enforcement**. Subagent files don't need to track the invariant locally.

### gsc_insights dimension + sub-dim enum

GSC findings use their own `dimension: "gsc_insights"` with **14 sub-dimensions** for structural organization. No score allocation — these are routing labels, not score buckets:

| Sub-dim | Source | Notes |
|---|---|---|
| `indexing_coverage` | inspection-set non-index rate (info-only footer) | Site-wide rate not computable from per-URL inspection — info only |
| `crawled_not_indexed` | URL Inspection — `coverageState` matches | Content quality / E-E-A-T cluster |
| `discovered_not_indexed` | URL Inspection — `coverageState` matches | Crawl-budget / internal-linking cluster |
| `not_found_404` | URL Inspection — `coverageState` matches | Sitemap-vs-actual 404 cluster (dedupes with sitemap probe — see below) |
| `redirect_hygiene` | URL Inspection — `coverageState` matches | Sitemap entries pointing to redirected URLs. **Severity tiered medium/<50/high** (S34 burakarik6 dogfood — 838 affected URLs called for `high` severity that the original fixed-`medium` under-rated). Locale-prefix-cluster detection in recommendation. |
| `canonical_conflict` | URL Inspection — `coverageState` matches (with `googleCanonical` + `userCanonical` evidence) | Declared canonical disagrees with Google's chosen canonical |
| `blocked_access` | URL Inspection — `coverageState` matches | Usually intentional; low-severity info |
| `soft_404` | URL Inspection — `coverageState` matches | 200-but-empty pages |
| `server_errors` | URL Inspection — `coverageState` matches | High-severity availability signal |
| `ctr_opportunity` | Q2 pages digest | High-impressions, below-median CTR — dual trigger: position-band (5-20) OR high-volume override (imp ≥ 10k AND ctr < 0.5%). S31 dogfood fix. |
| `position_band_opportunity` | Q1 queries digest | Position 5-20 queries with ≥100 impressions |
| `traffic_orphan` | Q3 `url_impressions_map` + sitemap | Sitemap URLs with 0 impressions in the data window |
| `brand_query_anomaly` | Q1 queries digest ∩ Schema/CLAUDE.md brand-name | Brand queries (Person.name / Organization.name / CLAUDE.md first proper noun) ranking >pos 3 OR CTR <10% → entity-recognition deficit. Cross-links to Schema `Person.@id` split + `Person.sameAs` Wikidata findings. **S31 dogfood codification of emergent capability.** |
| `deindex_regression` | Snapshot diff (`.seo-data/gsc/snapshots/*.json`) — **orchestrator-emitted in SKILL.md Step 1.6.13** | URLs that flipped from `Submitted and indexed` → any non-indexed state since the previous run. The early-warning loop catching Google's "New reason preventing your pages from being indexed" / "Validation failed" emails before they hit the user's inbox. **S34 burakarik6 dogfood codification** — 838-URL `Page with redirect` regression was invisible to the impressions-only sampling pre-S34. Severity escalates to `critical` on Server error (5xx) transitions OR ≥20 URLs OR ≥10% of inspected URLs. Carries `path_clusters` + `git_correlation` evidence to bridge the regression to its likely-causal commit. NOT produced by the seo-gsc-insights subagent — emitted directly by the orchestrator after snapshot diff. |

### Per-finding output shape — GSC additions

GSC findings extend the canonical 10-field per-finding shape (defined in each scan-*.md) with 8 additional fields:

| Field | Type | Notes |
|---|---|---|
| `source` | `"gsc" \| "heuristic"` | **Required on every finding.** `"gsc"` triggers orchestrator-side score_impact:0 enforcement. Heuristic findings keep `"heuristic"` and have all GSC fields null. |
| `impressions` | `int \| null` | From Q1 queries digest / Q2 pages digest |
| `clicks` | `int \| null` | From Q1 queries digest / Q2 pages digest |
| `ctr` | `float \| null` | Click-through rate, 0.0-1.0 |
| `avg_position` | `float \| null` | Average position in SERP |
| `affected_urls` | `[str]` | Sample of URLs in the cluster (cap 10 inline; full list in subagent output addendum) |
| `code_changed_since_gsc_window` | `bool \| null` | Set from Step 1.5 git-history match; `null` when git history shallow |
| `recent_commits` | `[str]` | Short commit messages matched in window, max 3 |
| `routing_rename_match` | `bool \| null` | Optional, only emitted on `not_found_404` cluster findings when the cluster's URL pattern matches a rename in the git-history window. `null` for findings where the field doesn't apply. |

### Traffic-weighted ranking (Step 6)

The orchestrator's existing ranking formula gains a `traffic_weight` multiplier when GSC data is present, and uses a parallel `effective_impact` definition so GSC findings (with `score_impact: 0`) can still rank into the top-3:

```
effective_impact (heuristic) = score_impact
effective_impact (gsc)       = log10(impressions + 1)        # 0–~5 range

traffic_weight (URL in pages.csv)  = max(1.0, log10(page_impressions + 1))
traffic_weight (URL not in pages)  = 1.0                     # heuristic-only fallback

rank_score = effective_impact × certainty × traffic_weight / effort_weight
```

- No GSC CSVs present: `effective_impact == score_impact`, `traffic_weight == 1.0` everywhere — formula reduces to the existing `score_impact × certainty / effort_weight`. Behavior unchanged.
- With GSC: heuristic findings on high-traffic pages float up; GSC findings rank by their own impression-based effective_impact.

Magnitude calibration may be tuned after dogfood — adjust `effective_impact (gsc)` exponent or `traffic_weight` cap if heuristic findings consistently swamp GSC findings or vice versa.

### URL dedup with sitemap probe

When the orchestrator's sitemap probe (Step 3.2) and a GSC indexing finding both reference the same URL — typically `url_health` (probe-emitted, non-zero score_impact) and `not_found_404` or `redirect_hygiene` (GSC-emitted, score_impact:0) — **Step 6 dedupes by URL**. Keep one merged finding citing both sources:

- Sub-dim attribution stays with the probe finding (`technical_seo.url_health`) — that's the source of the score deduction.
- Merged record gains `gsc_corroborated: true` and `gsc_recent_commits: [...]` from the GSC finding.
- Report renders one row, not two.

URL is the join key. Case-insensitive, trailing-slash-normalized.

### History row format — [gsc] prefix

When a top-3 priority string in `docs/seo-history.md` comes from a GSC finding, prefix the string with `[gsc]` so readers see at-a-glance why a row's priorities shifted between runs (e.g., user added or removed CSVs):

```
| 2026-05-14 | 72 | [gsc] CTR opportunity on /pricing (12.4K imps); No llms.txt; [gsc] 1,146 crawled-not-indexed pages |
```

The `[gsc]` prefix is appended at history-write time in Step 7, after top-3 ranking is finalized.

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

When sitemap URL probe didn't run (no sitemap, dynamic sitemap.ts handler with no static output, relative URLs without `--url`), the `url_health` sub-dimension is 0/0 — no points deducted, but the maximum is also 0 for this sub-dim. To keep the dimension total at 25, the missing 8 points redistribute proportionally across other Technical SEO sub-dims that ran:

| Sub-dim | Probe ran | Probe skipped |
|---|---|---|
| robots_sitemap | 4 | 6 |
| canonicals | 4 | 6 |
| mobile | 3 | 5 |
| hreflang | 3 | 4 |
| redirects | 3 | 4 |
| url_health | 8 | 0 |

### Rendering the redistribution (S31 dogfood fix)

The S31 dogfood showed `url_health: 0/0 (probe skipped)` in the report — correct, but **opaque about where the 8 points went**. Users saw a "good" `url_health: 0/0` and didn't realize the other Technical SEO sub-dims now had elevated caps absorbing the redistribution.

**Reporting requirement (consumed by `report-template.md` Section 1 — Score breakdown):** When probe is skipped, the Sub-dim breakdown column for Technical SEO MUST render the redistribution explicitly. Two acceptable forms:

**Form A (compact)** — append a redistribution note after the deductions line:

```
| Technical SEO | 16 | 25 | canonicals: -5.25; hreflang: -2; robots_sitemap: -1.5; redirects: -0.5; url_health: 0/0 (probe skipped, 8pts redistributed: canonicals +2, robots_sitemap +2, mobile +2, hreflang +1, redirects +1) |
```

**Form B (explicit)** — add a dedicated row above the dimension showing the active caps:

```
| Technical SEO (probe skipped — caps redistributed) | — | — | canonicals→6, robots_sitemap→6, mobile→5, hreflang→4, redirects→4, url_health→0 |
| Technical SEO | 16 | 25 | canonicals: -5.25 (cap 6); robots_sitemap: -1.5 (cap 6); hreflang: -2 (cap 4); ... |
```

Form A is preferred (compact, single row per dimension). Form B is for `--verbose` reporting if added later.

**Footer note (in addition to per-dim breakdown):**

```
URL probe skipped: <reason — e.g., "dynamic sitemap.ts handler with no static output; re-run with --url <base> for live URL health check.">. 8 url_health points redistributed across other Technical SEO sub-dims (per rubric.md "Probe-skipped case").
```

Same pattern applies if the hreflang sub-dim is redistributed for non-i18n projects (existing rubric rule). When BOTH conditions hold (no i18n AND probe skipped), the two redistributions stack — 8 url_health pts + 3 hreflang pts = 11 pts redistribute. The probe-ran-with-i18n table above is the baseline; when both adjustments fire, recompute caps by applying both rules in sequence (hreflang to 0 first, then redistribute url_health's 8 pts across the remaining 4 sub-dims proportionally to their probe-ran-without-i18n weights).

Footer notes "URL probe skipped — Technical SEO sub-dim weights redistributed." User can re-run with `--url <base>` to get URL health scored.
