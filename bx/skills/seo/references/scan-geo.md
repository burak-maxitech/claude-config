# Scan: Structured Data + Generative Engine Optimization

Loaded by the orchestrator and passed to the `geo-generative` subagent. The agent definition (`bx/agents/geo-generative.md` in the plugin — your own system prompt when dispatched as that agent) holds the canonical rules, tables and thresholds; this file is the step-by-step procedure. Where the two seem to differ, the agent definition wins.

## Inputs from the orchestrator

- `Detected stack` — framework + content patterns
- `Best-practices brief` — passed verbatim; **primary source of truth for current GEO facts** (the field evolves fast and embedded heuristics age quickly) — but it cannot revive a refused tactic without a first-party engine source
- `Scope file list` — source files in scope
- `Site profile` — `site_type`, `ai_policy`, `ymyl`, `money_pages`, `authors`, `cdn`, …
- `Page audit:` (Step 3.4) — raw-HTML records per live page, including `jsonld`, `jsonld_parse_errors`, `robots_meta`, `canonical`, `visible_dates`, `main_text_chars`, `schema_visible_checks` — or a skip-reason line
- `Render compare:` (Step 3.4, browser available only) — raw vs rendered per URL, `raw_html_gap` — or a skip-reason line
- `Bot probe:` (Step 3.5) — per-bot live fetch verdicts, `cdn_waf_suspect`, parsed live robots.txt (`content_signals`, `usage_groups`, `content_usage`, `per_bot_allowed`), `policy_conflicts` — or `unavailable` / a skip-reason line
- `Weight adjustments`

**Live first, source second.** A live record for a URL is the evidence; source files locate the fix. No live data → grep templates and content as before, at the lowered certainties in the agent definition, and write "source-only" in `evidence`.

## Read this twice

GEO is still SEO. What the evidence supports (as of 2026-11): crawl access at every layer, content in raw HTML, truthful structured data, extractable attributed facts. **When the brief contradicts or refines a heuristic in this file, prefer the brief** and mark divergence in `brief_divergence`. The refused-tactics list in the agent definition is the exception.

---

## Sub-scan 1: JSON-LD Coverage (`jsonld_coverage`, 10 points)

**Page-type detection heuristics:**

| Heuristic | Page type | Expected `@type` |
|---|---|---|
| Root `/` page | Homepage | `Organization` or `WebSite` |
| `pages/blog/*`, `content/blog/*`, `posts/*` | Blog post | `Article` or `BlogPosting` |
| `pages/products/*`, `app/products/*`, e-com signals (`addToCart`, `price`) | Product | `Product` |
| Path contains `recipe` or cooking-domain signals | Recipe | `Recipe` |
| Path contains `event` | Event | `Event` |
| Local business signals (NAP info, address fields) | Local | `LocalBusiness` |
| Path contains `author`, `team`, `about/<person>` | Person | `Person` |
| All multi-page sites | Inner pages | `BreadcrumbList` |

`site_profile.site_type` (Step 0.5) overrides detection when set — see the agent definition for the mapping.

**Retired Google rich results** — `FAQPage` (gone from Search 2026-05-07, docs removed 2026-06-15), `HowTo`, sitelinks search box, `ClaimReview`, Course info, Estimated salary, Learning video, Special announcement, Vehicle listing, Book actions, Practice problem, Dataset: never flag as missing, never treat existing markup as an error (at most one info line), never recommend adding them for a rich result. Source: [search gallery](https://developers.google.com/search/docs/appearance/structured-data/search-gallery), [Search Central updates](https://developers.google.com/search/updates).

For each page-type/expected-schema pair:

1. Map `Page audit:` URLs to page types (path patterns above + `money_pages`). Read each record's `jsonld[].type`.
2. Parse `<script type="application/ld+json">` blocks / JSON-LD helpers in the page template.
3. **Missing in live HTML and source** → `severity: medium` (high for Article on a blog or Product on e-com), `certainty: 0.8`, `score_impact: 1-2`, `is_fix_eligible: true` (scaffold with required fields + TODO placeholders).
4. **Missing in source, present live** (CMS/plugin-injected) → no finding.
5. **No live record for the page type** → source-only at `certainty: 0.6` (0.4 for SPA shells and headless-CMS stacks).

Schema is scored for rich-result eligibility — never phrase a coverage finding as "needed for AI citation".

---

## Sub-scan 2: Schema Validation, Rich-Result Eligibility, Truthfulness (`schema_validation`, 10 points)

**Validity:**
- `Page audit:` `jsonld_parse_errors > 0` → `severity: high`, `certainty: 0.9`, `score_impact: 1.5`, URLs listed. Source-only parse failure → same, `certainty: 0.7`.

**Required fields per type** (from schema.org; brief may add or remove). Live `jsonld[].fields` answers `name`, `headline`, `author`, `datePublished`, `dateModified`, `price`, `priceCurrency`, `address`, `telephone`; read the rest from source.

| Type | Required fields |
|---|---|
| `Article` / `BlogPosting` | `headline`, `datePublished`, `author` (with `name`), `image` |
| `Product` | `name`, `image`, `offers` (with `price` and `priceCurrency`) |
| `Organization` | `name`, `url`, `logo` |
| `BreadcrumbList` | `itemListElement` array with `position`, `name`, `item` (URL) |
| `Recipe` | `name`, `recipeIngredient`, `recipeInstructions`, `author`, `datePublished` |
| `Event` | `name`, `startDate`, `location` |
| `Person` | `name` |

For each missing required field → `severity: medium`, `score_impact: 0.5-1`.

**Rich-result blockers** — emit under `sub_dimension: "schema_validation"` (no separate `rich_result` sub_dim):
- `Article` missing `image`.
- `Product` with `offers` but no `priceCurrency`.
- `aggregateRating` with `reviewCount: 0`.
- `site_type: ecommerce`: `MerchantReturnPolicy` without `returnPolicyCountry`; no return/shipping policy on offers or at `Organization` level → `severity: low`, `score_impact: 0.5`.

Each blocker → `severity: medium`, `score_impact: 0.5` unless stated.

**`schema_visible_mismatch`** (needs `Page audit:`; does not run source-only):
1. Collect `schema_visible_checks` rows with `in_visible_text: false`.
2. For each row, grep the page's source for the value in another format (thousands separators, decimals, phone punctuation, street abbreviations). Found → drop.
3. Group by `(type, field)`; one finding per group, up to 10 URLs.
4. Severity/certainty/impact per the agent definition's table: price/address/telephone medium (high on a money page), 0.7, 1; author low, 0.6, 0.5; datePublished low, 0.6, 0.25 (replaces the E-E-A-T visible-date finding for that URL); name/headline low, 0.4, 0.25.
5. `Render compare:` `raw_html_gap.main_content: true` for the URL → certainty 0.4 and note the value may be visible only after JavaScript.

Recommended action: make markup and visible text agree; whichever side is wrong is the owner's call (`is_fix_eligible: false`).

---

## Sub-scan 3: llms.txt (`llms_txt`, info only — never scored)

Google says Search does not use llms.txt ([AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)), and no major AI engine documents reading it. Every finding here has `score_impact: 0`.

**Presence check:**
- `Glob` for `llms.txt`, `public/llms.txt`, `static/llms.txt`, `app/llms.txt`. Record `llms_txt_present` in the addendum. **Missing is not a finding.**

**Format compliance** (when present — one combined `severity: low`, `score_impact: 0` finding at most):

```
# <Project Title>

> <one-line description>

## <Section name (e.g., "Getting Started")>

- [<Page title>](<URL>): <one-line description>
```

Check: first non-empty line starts with `# `; a `> ` description in the first 10 lines; at least 2 `## ` sections with markdown links.

Do not re-introduce scoring unless a first-party engine doc says it consumes the file.

---

## Sub-scan 3b: AI-feature eligibility (`ai_eligibility`, 3 points)

Pages are eligible for Google AI Overviews / AI Mode only when indexed and snippet-eligible ([AI features](https://developers.google.com/search/docs/appearance/ai-features)). Check `Page audit:` `robots_meta` first (`certainty: 0.9`), then templates, layouts and header config (`next.config.*`, `vercel.json`, `netlify.toml`, `_headers`, middleware; `certainty: 0.6`):
- `nosnippet` / `max-snippet:0` (or tiny values) in robots meta or `X-Robots-Tag` on indexable pages → `severity: medium` (high on a `money_pages` entry), `score_impact: 1-2`; info only when `ai_policy: all_no`.
- `data-nosnippet` around main content → `severity: low`, `score_impact: 0.5`.
- Robots meta rendered in `<body>` (Google honors it there, [robots meta doc](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag)) → `severity: high`, `score_impact: 1.5`.
- Rendered-only `noindex` / canonical changes belong to `seo-technical` (`rendered_only_directive`) — skip.

---

## Sub-scan 4: E-E-A-T Signals (`eeat`, 8 points)

Heuristic and often needing human judgment. Certainty 0.5-0.7 unless a live record settles it.

**Author bios linked from articles:**
- For each `Article`-type page, look for a byline (`by <name>`, `author: <name>`, `<address>` with a name), verify it links to a profile page (`/author/<name>`, `/team/<name>`) that exists and has a bio.
- Missing author bio link on Article → `severity: low`, `score_impact: 0.5`.

**Visible dates:**
- Live: `visible_dates` empty on an Article URL → `severity: low`, `certainty: 0.8`, `score_impact: 0.5` — unless `schema_visible_mismatch` already reported that URL's date.
- Source-only: grep `<time datetime=`, `Published:`, `Posted on`, `Updated:` → same finding at `certainty: 0.5`.
- Source template renders a date but the live `visible_dates` is empty → `geo_raw_html_gap` (`eeat`, 0.5) instead.
- Never suggest changing a date without a real content update.

**Sourced claims in long-form content** (replaces the old ≥1-link-per-500-words ratio):
- Articles > 800 words that state figures or factual claims with no link, footnote or attribution anywhere → `severity: low`, `certainty: 0.6`, `score_impact: 0.5`.

**YMYL fact-check line** (`ymyl` ≠ `no` only): no reviewer / "fact-checked by" / editorial-process line on an article → `severity: low`, `certainty: 0.4`, `score_impact: 0.25`, phrased as "reported" guidance.

**About / Contact pages:**
- Verify `/about` and `/contact` exist, with named humans and contact methods.
- Missing About → `severity: low`, `score_impact: 0.5`. Missing Contact → `severity: low`, `score_impact: 0.5`.

---

## Sub-scan 5: Extractable Facts (`semantic_content`, 5 points)

The id stays `semantic_content`; since 2.20.0 it scores extractable, attributed facts per the evidence grades in [arXiv 2607.14035](https://arxiv.org/html/2607.14035v1). Every finding is framed **"plausible, not proven"**, with no lift percentage, and recommends **additive** edits only.

1. **Select pages**: long-form content ≥ 800 words (source Markdown/MDX/templates/CMS exports in the repo), plus commercial (`money_pages`, pricing, product) and time-sensitive pages ("best", "vs", news, events, a year in the title).
2. **Count per page** the signals in the agent definition's table: sourced statistics, unsourced statistics, attributed quotes, definitions, comparison tables, explicit prices/dates.
3. **Emit:**
   - Zero sourced statistics, attributed quotes and comparison tables on a ≥ 800-word page → `severity: low`, `certainty: 0.5`, `score_impact: 0.5` (1 above 2,000 words). Name what to add.
   - ≥ 3 unsourced statistics on a page → `severity: low`, `certainty: 0.6`, `score_impact: 0.25`.
   - Three or more items compared on the same attributes in prose → `severity: low`, `score_impact: 0.25`, suggest a table.
   - A term-named heading whose section never defines it → `severity: low`, `score_impact: 0.1`.
   - Generic H2/H3 (`Section 2`, `Overview`, `Details`, `Information`, `Content`) → `severity: low`, `score_impact: 0.1` each.
   - Question-format headings: at most one site-level nudge, `score_impact` ≤ 0.1; never a quota, never an "AI requirement".
4. **`keyword_stuffing`** (negative) on content pages ≥ 300 words, target phrase = the 2–4-word phrase shared by `<title>` and H1 (else a matching `target_topics` entry):
   - exact-phrase density (occurrences × phrase words ÷ total words) > 3% with ≥ 8 occurrences, or
   - the exact phrase in ≥ 4 H2/H3 headings and more than half of them, or
   - the exact phrase ≥ 3 times inside any 50-word window.
   Any → `severity: medium` (low when only one condition holds within 0.5 pp of the density threshold), `certainty: 0.6`, `score_impact: 0.5`, counts in `evidence`.

Cap the sub-dim at 5.

---

## Sub-scan 6: AI-Bot Access — Declared (`ai_bot_access_declared`, 2 points; 4 when the bot probe did not run)

1. **Read robots**: `Bot probe:` `robots` (live file — includes CDN-managed lines) else repo `robots.txt` / `robots.ts`. If both exist and differ, judge the live one and note the difference.
2. **Classify user-agents** into training, AI search indexing, user-triggered and ads groups (lists in the agent definition and `references/site-profile.md` "AI crawler groups" — training includes `Meta-ExternalAgent`; ads is `OAI-AdsBot`, info only). The brief may add tokens.
3. **Judge against `ai_policy`**:
   - Stated policy + mismatch → `medium`, `certainty: 0.9`, `score_impact: 1-2`.
   - Policy `unknown` / `undecided` → "did you mean to block these?" (`low`, `certainty: 0.5`, `score_impact: 0.25`), suppressed when a documented decision exists (CLAUDE.md, README, `docs/`, robots.txt comment).
   - A vendor's search bot blocked while its training bot is allowed → `low`, `certainty: 0.7`.
   - `Googlebot` blocked as an "AI opt-out" → `high` (removes the site from Search).
   - Legacy tokens (`anthropic-ai`, `Claude-Web`) → info, name the current token.
4. **Parse preference signals** (presence → addendum `preference_signals`; absence is never a finding):
   - `Content-Signal:` lines (`search`, `ai-input`, `ai-train`), scoped to their user-agent group.
   - `User-agent: __usage_ai-training` groups (Google's planned aipref form, early 2027).
   - `Content-Usage:` lines (aipref attach draft).
5. **`ai_policy_conflict`** — from `Bot probe:` `policy_conflicts` plus your own parse, per the agent definition's table: signal vs per-bot rules (low, 0.7, 0.5); signal vs stated `ai_policy` (medium, 0.8, 1); live-only CDN lines (low, 0.6, 0 — info).
6. Never describe a preference signal as blocking or enforcing anything.

---

## Sub-scan 7: AI-Bot Access — Delivered (`ai_bot_access_delivered`, 2 points; needs `Bot probe:`)

Skip entirely (0/0, points to Sub-scan 6) when `Bot probe:` is absent, skipped or `unavailable`.

1. **`cdn_waf_block`**: for each bot in `cdn_waf_suspect` whose `robots.per_bot_allowed` is not `disallow`, apply the agent definition's group × policy table (search group under an allowing policy → high, 1.5; user-triggered → medium, 1; training under `all_yes` → low, 0.5; policy-consistent blocks → info, 0; ads → info).
2. **Certainty**: 0.5; 0.6 only when control and bot fetched the same URL and the bot's fetch has `challenge: true` with a named `challenge_marker`. Never higher, never "confirmed". Title: "Suspected CDN/WAF block of <bot>".
3. **Recommended action**: verify in the CDN dashboard (`site_profile.cdn` names it: Cloudflare Security → Events / AI Crawl Control; Vercel Firewall; Fastly/Akamai/Imperva bot manager) that the blocked requests came from the vendor's published IP ranges, then allow the verified bot. List that vendor's IP files: OpenAI `searchbot.json`, `gptbot.json`, `chatgpt-user.json`, `adsbot.json` (all under `https://openai.com/`); Anthropic `https://claude.com/crawling/bots.json`; Perplexity `https://www.perplexity.ai/perplexitybot.json`, `https://www.perplexity.ai/perplexity-user.json`; Google `common-crawlers.json`.
4. `differs` (bot < 50% of control bytes) → low, 0.4, 0.25. `unreachable` with control ok → low, 0.4, 0.25. Control unreachable or challenged too → no finding, addendum note.
5. Robots-only tokens (`Google-Extended`, `Applebot-Extended`) never produce a delivered finding.

---

## Sub-scan 8: Raw-HTML gap (`geo_raw_html_gap`)

Non-Google AI crawlers do not run JavaScript ([Vercel/MERJ](https://vercel.com/blog/the-rise-of-the-ai-crawler)). Using `Render compare:` and `Page audit:`:
- `raw_html_gap.jsonld: true` → medium, 0.8, `score_impact: 0`, `cross_ref: "technical_seo.rendering"`, sub-dim `ai_bot_access_delivered`.
- `raw_html_gap.main_content: true` → high on money pages / homepage, else medium; 0.8; `score_impact: 0`; same `cross_ref`.
- Source renders a date or byline but live `visible_dates` / raw text lacks it → `eeat`, low, 0.6, 0.5.
- No `Render compare:`, live `jsonld` empty, source emits JSON-LD from a client component → medium, 0.5, `score_impact: 0`, same `cross_ref`.

The zero-score rows tell the user what AI crawlers miss; `seo-technical` already deducts the points.

---

## Per-finding output shape

See the `geo-generative` agent definition for the canonical JSON shape (including `finding_id` and `cross_ref`). Do not duplicate.

---

## Output addendum

Use the agent definition's addendum verbatim (adds `live_pages_audited`, `preference_signals`, `bot_probe`, `cdn_waf_suspects`, `ai_policy_conflicts`, `schema_visible_mismatches`, `sub_dimension_breakdown`).

---

## Hard rules

- **Never fabricate content.** Fix-mode inserts JSON-LD scaffolds with TODO placeholders for values.
- **Brief is primary source of truth** for current facts; it cannot revive a refused tactic (agent definition, "Refused tactics") without a first-party engine source. Note `brief_divergence`.
- **AI-bot blocking findings default to `certainty: 0.5`** unless judged against a stated `ai_policy`; `cdn_waf_block` never exceeds 0.6.
- **No lift percentages**, ever.
- **Skip vendored / generated dirs.**
- **Cap output at 30 findings.**

## False-positive guards

- **CMS-driven JSON-LD** — a live record carrying the JSON-LD settles it; without one, lower certainty.
- **Templated llms.txt** — some frameworks generate at build time; check config files before reporting presence.
- **Deliberate AI-bot blocking** — header comment in `robots.txt` mentioning policy → suppress the `unknown`-policy note.
- **SPA shells** — JSON-LD at the route level is weaker for SPA shells. Lower certainty.
- **Site-wide bot protection** — a challenge served to the control too is not an AI-bot block.
