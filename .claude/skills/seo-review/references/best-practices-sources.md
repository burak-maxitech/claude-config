# Best-Practices Sources Catalog

Curated WebSearch queries + WebFetch URL targets for Step 1's fetch step. The orchestrator uses this file as the *query list source of truth* — the fetched results themselves live in session memory, not in this file.

## Why this file exists

SEO and GEO best practices drift continuously. Embedding "current" guidance in a static reference file ages it instantly. Instead, this file holds the **map of where to look** — the queries to run and the URL targets to fetch. The orchestrator pulls fresh content from these sources on every run and synthesizes a brief.

If a source disappears or its URL structure changes, edit this file (not embedded heuristics in the scan-*.md files). Mark such edits with a date in the "last verified" column.

---

## Source category 1: Google Search Central + web.dev (authoritative)

**WebSearch queries:**

| Query | Why |
|---|---|
| `"Google Search Central" SEO best practices 2026 site:developers.google.com` | First-party Google guidance on crawling, indexing, structured data |
| `"Core Web Vitals" thresholds 2026 site:web.dev` | Current INP/LCP/CLS targets — these get tuned yearly |
| `"mobile-first indexing" Google Search Central` | Mobile UX as a ranking factor; latest guidance |
| `"Search Quality Rater Guidelines" PDF` | Periodically updated, drives quality signal weighting |

**Curated WebFetch URLs** (last verified 2026-05 — refresh if 404):

| URL | What it covers | Priority |
|---|---|---|
| `https://developers.google.com/search/docs/fundamentals/ai-optimization-guide` | **Google's first-party AI Search optimization guide** (published 2026-05). Directly addresses AEO/GEO. Explicitly says: AEO/GEO is SEO (same foundations apply, no special tactics); `llms.txt` is **not needed** ("no need to create new machine readable files, AI text files, markup, or Markdown"); structured data is **not required** for generative AI search ("no special schema.org markup"); content chunking + AI-specific rewrites are **unnecessary**; debunks pursuing inauthentic mentions. Reframes RAG + query fan-out as making traditional SEO directly relevant. **Authoritative counterweight to third-party GEO speculation.** | **priority** — always fetch every run |
| `https://developers.google.com/search/docs/fundamentals/seo-starter-guide` | The official starter guide; entrypoint for crawling/indexing basics | |
| `https://developers.google.com/search/docs/appearance/structured-data` | Structured data overview + supported types | |
| `https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview` | Sitemap format + best practices | |
| `https://web.dev/learn/seo` | web.dev SEO course (refreshed regularly) | |
| `https://web.dev/articles/vitals` | Current Core Web Vitals definitions + thresholds | |

---

## Source category 2: Schema.org + JSON-LD

**WebSearch queries:**

| Query | Why |
|---|---|
| `"schema.org" Article required properties` | What Google needs for Article rich results |
| `"schema.org" Product required properties Merchant` | Product rich results + Merchant Center alignment |
| `"schema.org" FAQPage HowTo deprecation status 2026` | These types have had eligibility shifts; check current state |
| `"schema.org" BreadcrumbList implementation` | Most common rich-result win across site types |

**Curated WebFetch URLs:**

| URL | What it covers |
|---|---|
| `https://schema.org/Article` | Type definition + properties |
| `https://schema.org/Product` | Type definition |
| `https://schema.org/FAQPage` | Type definition |
| `https://schema.org/BreadcrumbList` | Type definition |
| `https://schema.org/Organization` | Type definition |
| `https://developers.google.com/search/docs/appearance/structured-data/search-gallery` | Google's supported rich-result gallery — eligibility per type changes |

---

## Source category 3: Generative Engine Optimization (rapidly evolving)

**WebSearch queries:**

| Query | Why |
|---|---|
| `"llms.txt" specification format 2026` | The convention is young; spec details settle over time |
| `"generative engine optimization" citation patterns 2026` | What gets AI engines to cite |
| `"AI Overviews" Google ranking factors 2026` | Google AI search — what gets cited in summaries |
| `Perplexity citation behavior content patterns` | Perplexity is one of the most-studied AI search engines |
| `"ChatGPT search" content optimization 2026` | OpenAI's search/citation behavior |
| `"E-E-A-T" Generative AI signals 2026` | How experience/expertise/authoritativeness/trust translate to AI citation |
| `Anthropic Claude search citation` | Claude's web search + citation behavior (when active) |

**Curated WebFetch URLs:**

| URL | What it covers |
|---|---|
| `https://llmstxt.org/` | The llms.txt spec home page |
| `https://platform.openai.com/docs/bots` | OpenAI's bot user-agents (GPTBot, OAI-SearchBot, ChatGPT-User) |
| `https://docs.anthropic.com/en/docs/agents-and-tools/computer-use` *(if relevant)* | Anthropic crawler docs when available |
| `https://www.perplexity.ai/hub/blog` | Perplexity's blog — discusses crawler + citation behavior |

**Note:** GEO sources are unstable. WebSearch is usually more useful than fixed WebFetch URLs here. The orchestrator should prefer WebSearch for this category, then WebFetch only the highest-signal results.

**Authoritative cross-reference:** Google's AI Optimization Guide (Category 1, priority URL) is the **first-party** source on Google's stance toward AEO/GEO and explicitly debunks several third-party patterns (separate llms.txt files, AI-specific content rewrites, special schema.org markup for AI). When the brief synthesis encounters conflicting guidance, the Google guide wins on Google-search-specific topics; third-party blogs win on cross-engine citation behavior (Perplexity, ChatGPT, Claude — Google's guide doesn't cover those).

---

## Source category 4: Third-party authority blogs (synthesis)

**WebSearch queries:**

| Query | Why |
|---|---|
| `site:moz.com SEO updates 2026` | Moz industry coverage |
| `site:ahrefs.com SEO research 2026` | Ahrefs research / studies |
| `site:searchenginejournal.com 2026` | SEJ news + analysis |
| `"Search Engine Land" algorithm update 2026` | SEL coverage of Google algorithm shifts |

**Curated WebFetch URLs:** none. Third-party blogs change URLs frequently; relying on WebSearch each run is safer.

---

## How the orchestrator uses this catalog

Step 1 of `SKILL.md` instructs:

1. Run all queries from categories 1-4 in parallel (single turn) via `WebSearch`.
2. **Always fetch URLs marked `priority`** regardless of WebSearch results (Google AI Optimization Guide etc.) — these are first-party authoritative sources whose presence in the brief is non-negotiable.
3. From WebSearch results, pick the top 1-2 most authoritative URLs per category and `WebFetch` them in parallel (alongside priority URLs in the same turn).
4. Synthesize into the ~50-line best-practices brief. **When priority-source guidance conflicts with third-party/blog guidance on Google-search-specific topics, the priority source wins** — surface the divergence in the brief with `(per Google AI Optimization Guide)` annotation so subagents can prefer it.
5. Pass the brief to all 3 subagents (4 when GSC API enabled).

**Optimization:** if `Step 0` detected a specific framework (Next.js, Astro, Rails, etc.), add one framework-specific WebSearch query (`"<framework> SEO best practices 2026"`) to the batch.

**Failure handling:** if WebSearch / WebFetch return nothing useful (network failure, rate limit, etc.), the orchestrator falls back to embedded heuristics in the scan-*.md files and notes the fallback in the report footer. **Priority-URL fetch failure** is logged separately in the footer (e.g., "Google AI Optimization Guide fetch failed — falling back to embedded heuristics for AI-search topics; result may diverge from Google's current first-party guidance").

---

## Maintaining this file

This file is the *only* place to update when source URLs move or new authoritative sources emerge. **Do not embed time-sensitive guidance in scan-*.md files** — those describe stable detection patterns. Time-sensitive guidance lives in the fetched brief.

Edit cadence: when the user notices a source returning 404 or low-quality results, edit this file with the new URL. Optional: add a `last_verified: <YYYY-MM>` column to the tables and update on each verification.
