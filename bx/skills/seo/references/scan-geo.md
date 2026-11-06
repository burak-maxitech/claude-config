# Scan: Structured Data + Generative Engine Optimization

Loaded by the orchestrator and passed to the `geo-generative` subagent.

## Inputs from the orchestrator

- `Detected stack` — framework + content patterns
- `Best-practices brief` — passed verbatim; **this is your primary source of truth for GEO** (the field evolves fast and embedded heuristics age quickly)
- `Scope file list` — source files in scope (rendered HTML is NOT used for this scan; JSON-LD lives in source)
- `Weight adjustments`

## Read this twice

GEO is a rapidly evolving field. The fetched best-practices brief contains current guidance from authoritative sources (OpenAI, Anthropic, Perplexity, Google AI). **When the brief contradicts or refines a heuristic in this file, prefer the brief** and mark divergence in your finding's `brief_divergence` field so the user can review it.

The heuristics below are a stable starting baseline. They describe *categories* of signal, not the absolute current best practice.

---

## Sub-scan 1: JSON-LD Coverage

For each page type detected, check for a `<script type="application/ld+json">` block with the expected `@type`.

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

**Retired Google rich results** — `FAQPage` (gone from Search 2026-05-07, docs removed 2026-06-15), `HowTo`, sitelinks search box, `ClaimReview`, Course info, Estimated salary, Learning video, Special announcement, Vehicle listing, Book actions, Practice problem: never flag as missing, never treat existing markup as an error (at most one info line). Source: [search gallery](https://developers.google.com/search/docs/appearance/structured-data/search-gallery), [Search Central updates](https://developers.google.com/search/updates).

For each page-type/expected-schema pair:

1. Parse `<script type="application/ld+json">` blocks in the page-template.
2. Match the `@type` field against the expected.
3. **Missing expected schema** → `severity: medium` (high if a high-traffic page type like Product or Article), `score_impact: 1-2`, `is_fix_eligible: true` (scaffold with required fields + TODO placeholders).

---

## Sub-scan 2: Schema Validation + Rich-Result Eligibility

For each found JSON-LD block:

**Validity:**
- Parse as JSON. Invalid JSON → `severity: high`, `score_impact: 1.5`.

**Required fields per type** (from schema.org; brief may add or remove):

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

**Rich-result blockers** (these prevent rich snippets even when schema validates) — emit under `sub_dimension: "schema_validation"` (the rubric combines rich-result eligibility with schema validation into a single 10-point bucket; do not use a separate `rich_result` sub_dim):
- `Article` missing `image` → no rich-result eligibility.
- `Product` with `offers` but no `priceCurrency`.
- `aggregateRating` with `reviewCount: 0` or missing entirely on `Product`.

Each blocker → `severity: medium`, `score_impact: 0.5`.

---

## Sub-scan 3: llms.txt (info only — never scored)

Google says Search does not use llms.txt ([AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), 2026-05/06), and no major AI engine documents reading it. Every finding here has `score_impact: 0`.

**Presence check:**
- `Glob` for `llms.txt`, `public/llms.txt`, `static/llms.txt`, `app/llms.txt`. Record `llms_txt_present` in the addendum. **Missing is not a finding.**

**Format compliance** (when present — one combined `severity: low`, `score_impact: 0` finding at most):

The llms.txt convention is:
```
# <Project Title>

> <one-line description>

## <Section name (e.g., "Getting Started")>

- [<Page title>](<URL>): <one-line description>
- [<Page title>](<URL>): <one-line description>

## <Another section>

- [<Page title>](<URL>): <one-line description>
```

Check: first non-empty line starts with `# `; a `> ` description in the first 10 lines; at least 2 `## ` sections with markdown links.

When the brief contains updated llms.txt spec details, prefer the brief and mark `brief_divergence`. Do not re-introduce scoring unless a first-party engine doc says it consumes the file.

---

## Sub-scan 3b: AI-feature eligibility (`ai_eligibility`, 3 points)

Pages are eligible for Google AI Overviews / AI Mode only when indexed and snippet-eligible ([AI features](https://developers.google.com/search/docs/appearance/ai-features)). Grep templates, layouts and header config (`next.config.*`, `vercel.json`, `netlify.toml`, `_headers`, middleware):
- `nosnippet` / `max-snippet:0` (or tiny values) in robots meta or `X-Robots-Tag` on indexable pages → `severity: medium` (high on a `money_pages` entry), `score_impact: 1-2`; info only when `ai_policy: all_no`.
- `data-nosnippet` around main content → `severity: low`, `score_impact: 0.5`.
- Robots meta rendered in `<body>` (Google honors it there, [robots meta doc](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag)) → `severity: high`, `score_impact: 1.5`.

Never recommend content "chunking", "AI schema", or per-query-variation pages — unnecessary per Google's AI guide, and the last risks the scaled content abuse policy.

---

## Sub-scan 4: E-E-A-T Signals (Experience, Expertise, Authoritativeness, Trustworthiness)

These signals are heuristic and often require human judgment. Lower certainty (0.5-0.7) for findings here.

**Author bios linked from articles:**
- For each `Article`-type page, look for an author byline pattern (`by <name>`, `author: <name>`, `<address>` element with name).
- If byline exists, verify it's a link (`<a href="...">`).
- If the link target is an author profile page (`/author/<name>`, `/team/<name>`), check that page exists and has a bio.
- Missing author bio link on Article → `severity: low`, `score_impact: 0.5`.

**Visible dates:**
- Verify `datePublished` (and `dateModified` if recently modified) are visible in rendered content, not just in JSON-LD.
- `Grep` for patterns like `<time datetime=`, `Published:`, `Posted on`, `Updated:`.
- Missing visible date on Article → `severity: low`, `score_impact: 0.5`.

**Citations in long-form content:**
- For articles >800 words, look for external links (`<a href="https://...">` to non-self domains).
- Heuristic: at least 1 external citation per ~500 words of long-form content.
- Below threshold → `severity: low`, `score_impact: 0.5`.

**About / Contact pages:**
- Verify `/about` and `/contact` pages exist.
- Check for named humans (founder names, team-member names, named contact methods).
- Missing About → `severity: low`, `score_impact: 0.5`.
- Missing Contact → `severity: low`, `score_impact: 0.5`.

---

## Sub-scan 5: Semantic Content Patterns (AI-Citability)

Cite specific structural signals that increase AI-citation likelihood:

**Topic sentences:**
- For each major section (under H2), check that the first paragraph's first sentence leads with the section's topic.
- Heuristic: extract first sentence of section's first paragraph; check if it contains keywords from the H2.
- Sections without clear topic sentences → `severity: low`, `score_impact: 0.1-0.25`.

**List / table structure:**
- For long content pages (>500 words), check ratio of structured content (lists, tables) to paragraph content.
- If the page contains factual content (definitions, comparisons, instructions) presented as dense paragraphs without lists → `severity: low`, `score_impact: 0.25` informational.

**Question-format headings:**
- Optional nudge only: zero question-format H2s on a content-rich page → `severity: low`, `score_impact: 0.1`. Google's AI guide says no special formatting is needed; never present this as an AI requirement.

**Descriptive subheadings:**
- Flag generic H2/H3 content: `Section 2`, `Overview`, `Details`, `Information`, `Content`.
- `severity: low`, `score_impact: 0.1` per occurrence.

---

## Sub-scan 6: AI-Bot Crawl Access

Parse `robots.txt` (4 points). Classify user-agents into **training**, **AI search indexing** and **user-triggered** groups, and judge them against `site_profile.ai_policy`. The group lists, the policy table and the severity rules are defined once in the `geo-generative` agent definition ("AI-bot crawl access") and in `references/site-profile.md` ("AI crawler groups"). Apply those; the brief may add new user-agents to a group.

Summary of the rules:
- Stated policy + mismatch → `medium`, `certainty: 0.9`. The user told us their intent.
- Policy `unknown` → the old "did you mean to block these?" note (`low`, `certainty: 0.5`, `score_impact: 0.25`), suppressed when a documented decision exists (CLAUDE.md, README, `docs/`, or a robots.txt comment).
- `Googlebot` blocked as an "AI opt-out" → `high` (removes the site from Search).
- Legacy tokens (`anthropic-ai`, `Claude-Web`) → info, name the current token.
- AIPREF `Content-Usage` lines → info presence only.

---

## Per-finding output shape

See the `geo-generative` agent definition (`bx/agents/geo-generative.md` in the plugin — your own system prompt when dispatched as that agent) for the canonical JSON shape. Same shape applies here; do not duplicate.

---

## Output addendum

```
structured_data_score: <int 0-20>
generative_engine_score: <int 0-20>
jsonld_blocks_found: <int>
jsonld_blocks_valid: <int>
llms_txt_present: true | false
ai_bots_blocked: [<list of user-agents found in Disallow rules>]
brief_divergences: <int>
files_scanned: <int>
sub_dimension_breakdown: { ... }
```

---

## Hard rules

- **Never fabricate content.** Fix-mode inserts JSON-LD scaffolds with TODO placeholders for values.
- **Brief is primary source of truth.** Always note `brief_divergence` when heuristic diverges.
- **AI-bot blocking findings default to `certainty: 0.5`** — many sites block deliberately.
- **Skip vendored / generated dirs.**
- **Cap output at 30 findings.**

## False-positive guards

- **CMS-driven JSON-LD** — if framework injects at runtime, source may be empty. Lower certainty.
- **Templated llms.txt** — some frameworks generate at build time; check config files before reporting presence.
- **Deliberate AI-bot blocking** — header comment in `robots.txt` mentioning policy → suppress.
- **SPA shells** — JSON-LD at the route level is weaker for SPA shells. Lower certainty.
