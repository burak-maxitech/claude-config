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
| Path contains `faq`, `frequently-asked` | FAQ | `FAQPage` |
| Path contains `how-to`, `tutorial`, `guide` | HowTo | `HowTo` |
| Path contains `recipe` or cooking-domain signals | Recipe | `Recipe` |
| Path contains `event` | Event | `Event` |
| Local business signals (NAP info, address fields) | Local | `LocalBusiness` |
| Path contains `author`, `team`, `about/<person>` | Person | `Person` |
| All multi-page sites | Inner pages | `BreadcrumbList` |

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
| `FAQPage` | `mainEntity` (non-empty array of `Question` with `acceptedAnswer.text` non-empty) |
| `Organization` | `name`, `url`, `logo` |
| `BreadcrumbList` | `itemListElement` array with `position`, `name`, `item` (URL) |
| `Recipe` | `name`, `recipeIngredient`, `recipeInstructions`, `author`, `datePublished` |
| `Event` | `name`, `startDate`, `location` |
| `Person` | `name` |

For each missing required field → `severity: medium`, `score_impact: 0.5-1`.

**Rich-result blockers** (these prevent rich snippets even when schema validates):
- `Article` missing `image` → no rich-result eligibility.
- `Product` with `offers` but no `priceCurrency`.
- `FAQPage` with placeholder answers (`answer text`, lorem ipsum, single-character answers).
- `aggregateRating` with `reviewCount: 0` or missing entirely on `Product`.

Each blocker → `severity: medium`, `score_impact: 0.5`.

---

## Sub-scan 3: llms.txt

**Presence check:**
- `Glob` for `llms.txt`, `public/llms.txt`, `static/llms.txt`, `app/llms.txt`.
- Missing on a content-rich site (heuristic: site has >10 content pages — blog posts, docs, articles) → `severity: medium`, `score_impact: 3`, `is_fix_eligible: true` (scaffold with TODO sections).

**Format compliance** (when present):

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

Check:
- First non-empty line starts with `# ` (project title) → if not, `severity: low`, `score_impact: 0.5`.
- Has a blockquote (`> `) description in the first 10 lines → if not, `severity: low`, `score_impact: 0.5`.
- Has at least 2 `## ` sections with markdown links → if not, `severity: low`, `score_impact: 1`.

When the brief contains updated llms.txt spec details, prefer the brief and mark `brief_divergence`.

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
- For content pages, count H2s phrased as questions (`How does X work?`, `What is Y?`).
- If zero question-format H2s on a content-rich page → `severity: low`, `score_impact: 0.25` nudge (these match AI query patterns).

**Descriptive subheadings:**
- Flag generic H2/H3 content: `Section 2`, `Overview`, `Details`, `Information`, `Content`.
- `severity: low`, `score_impact: 0.1` per occurrence.

---

## Sub-scan 6: AI-Bot Crawl Access

Parse `robots.txt`. For each AI bot user-agent listed in the brief OR these defaults, check Disallow rules:

**Default user-agent list to check** (brief may add):
- `GPTBot` (OpenAI training crawler)
- `ChatGPT-User` (OpenAI on-demand fetch)
- `OAI-SearchBot` (OpenAI search index)
- `ClaudeBot` / `anthropic-ai` (Anthropic)
- `Claude-User` / `Claude-SearchBot` (Anthropic on-demand)
- `PerplexityBot` (Perplexity)
- `Google-Extended` (Google AI/Gemini training opt-out)
- `Applebot-Extended` (Apple AI)
- `Bytespider` (TikTok)
- `CCBot` (Common Crawl)

For each bot with `Disallow: /` or `Disallow: <broad pattern>`:

1. Check CLAUDE.md, README, or `docs/` for a documented decision to block AI bots (string search for "AI", "GPT", "Claude", "LLM", "no AI", "opt out").
2. If documented decision exists → suppress finding entirely.
3. If no documented decision → `severity: low`, `certainty: 0.5`, `score_impact: 0.25` — surface a "did you mean to block these?" note. User may want AI citation traffic.

---

## Per-finding output shape

```json
{
  "dimension": "structured_data" | "generative_engine",
  "sub_dimension": "jsonld_coverage" | "schema_validation" | "rich_result" | "llms_txt" | "eeat" | "semantic_content" | "ai_bot_access",
  "location": "<path>:<line-range>",
  "title": "<one-line>",
  "severity": "low" | "medium" | "high",
  "certainty": 0.0-1.0,
  "effort_estimate": "trivial" | "small" | "medium" | "large",
  "score_impact": <float>,
  "is_fix_eligible": true | false,
  "recommended_action": "<prose>",
  "evidence": "<one or two lines>",
  "brief_divergence": "<text or null>"
}
```

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
- **Templated llms.txt** — some frameworks generate at build time; check config files before flagging missing.
- **Deliberate AI-bot blocking** — header comment in `robots.txt` mentioning policy → suppress.
- **SPA shells** — JSON-LD at the route level is weaker for SPA shells. Lower certainty.
