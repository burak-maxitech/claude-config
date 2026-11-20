# Best-Practices Sources Catalog

Curated WebSearch queries + WebFetch URL targets for Step 1's fetch step. The orchestrator uses this file as the *source pool* for queries and the *list of curated fetch targets* — the fetched results themselves live in session memory, not in this file.

## Why this file exists

SEO and GEO best practices drift continuously. Embedding "current" guidance in a static reference file ages it instantly. Instead, this file holds the **map of where to look** — the queries to run and the URL targets to fetch. The orchestrator pulls fresh content from these sources on every run and synthesizes a brief.

If a source disappears or its URL structure changes, edit this file (not embedded heuristics in the scan-*.md files). Mark such edits with a date in the "last verified" note.

**Never hard-code a year in a query.** Write `<current year>`; the orchestrator substitutes the year of the brief's fetch date (SKILL Step 1).

**Source tiers.** First-party engine docs (Google, Bing, OpenAI, Anthropic, Perplexity) outrank peer-reviewed or preprint research, which outranks vendor studies, which outrank agency blogs and checklists. A lower tier never overrides a higher one in the brief, and no tier below first-party can revive a refused tactic (`bx/agents/geo-generative.md` "Refused tactics"). Vendor numbers enter the brief labelled as vendor numbers; lift percentages never enter it.

---

## Source category 1: Google Search Central + web.dev (authoritative)

**WebSearch queries:**

| Query | Why |
|---|---|
| `"Google Search Central" SEO best practices <current year> site:developers.google.com` | First-party Google guidance on crawling, indexing, structured data |
| `"Core Web Vitals" thresholds <current year> site:web.dev` | Current INP/LCP/CLS targets; CrUX soft-navigation changes (planned to fold into standard metrics from May 2027) |
| `"mobile-first indexing" Google Search Central` | Mobile UX as a ranking factor; latest guidance |
| `"Search Quality Rater Guidelines" PDF` | Periodically updated, drives quality signal weighting |

**Curated WebFetch URLs** (last verified 2026-11 unless noted — refresh if 404):

| URL | What it covers |
|---|---|
| `https://developers.google.com/search/docs/fundamentals/seo-starter-guide` | The official starter guide; entrypoint for crawling/indexing basics |
| `https://developers.google.com/search/docs/appearance/structured-data` | Structured data overview + supported types |
| `https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview` | Sitemap format + best practices |
| `https://web.dev/learn/seo` | web.dev SEO course (refreshed regularly) |
| `https://web.dev/articles/vitals` | Current Core Web Vitals definitions + thresholds |
| `https://developers.google.com/search/docs/essentials/spam-policies` | Spam policies — back-button hijacking ("Malicious practices"), keyword stuffing and the rest; drives `spam_policy` and `keyword_stuffing`. |
| `https://developers.google.com/search/docs/crawling-indexing/googlebot` | Googlebot crawls the first 2 MB of uncompressed HTML (other Google crawlers: 15 MB); drives `rendering`. |
| `https://developer.chrome.com/docs/crux/api` | CrUX API — field CWV source for Step 3.3 |
| `https://status.search.google.com/products/rGHU1u87FJnkP6W2GwMi/history` | Search Status Dashboard ranking-update history — human-readable source behind the helper's `update-windows` (core / spam rollouts) |

---

## Source category 2: Schema.org + JSON-LD

Structured data is fetched for **rich-result eligibility and truthfulness** — never as an AI-citation lever.

**WebSearch queries:**

| Query | Why |
|---|---|
| `"schema.org" Article required properties` | What Google needs for Article rich results |
| `"schema.org" Product required properties Merchant` | Product rich results + Merchant Center alignment; Organization-level return / shipping policies, `returnPolicyCountry` |
| `Google rich results retired OR deprecated <current year>` | Eligibility shifts (FAQ rich results ended 2026-05-07; HowTo, Practice problem, Dataset and others retired) — catch the next retirement |
| `"schema.org" BreadcrumbList implementation` | Most common rich-result win across site types |

**Curated WebFetch URLs:**

| URL | What it covers |
|---|---|
| `https://schema.org/Article` | Type definition + properties |
| `https://schema.org/Product` | Type definition |
| `https://schema.org/BreadcrumbList` | Type definition |
| `https://schema.org/Organization` | Type definition |
| `https://developers.google.com/search/docs/appearance/structured-data/search-gallery` | Google's supported rich-result gallery — eligibility per type changes |
| `https://developers.google.com/search/docs/appearance/structured-data/sd-policies` | General structured data guidelines — markup must match visible content; drives `schema_visible_mismatch` |

---

## Source category 3: Generative Engine Optimization (rapidly evolving)

**WebSearch queries:**

| Query | Why |
|---|---|
| `"llms.txt" Google OR OpenAI OR Anthropic consumes <current year>` | Watch for a first-party engine *adopting* llms.txt — the only thing that would justify scoring it again (unscored since 2.16.0) |
| `"generative engine optimization" benchmark OR replication arXiv <current year>` | Controlled GEO studies (C-SEO Bench, SAGEO Arena successors) — evidence grades, not vendor correlations |
| `"AI Overviews" Google ranking factors <current year>` | Google AI search — what gets cited in summaries (secondary — lose to first-party docs on conflict) |
| `Perplexity citation behavior content patterns` | Perplexity is one of the most-studied AI search engines |
| `"ChatGPT search" content optimization <current year>` | OpenAI's search/citation behavior |
| `"E-E-A-T" Generative AI signals <current year>` | How experience/expertise/authoritativeness/trust translate to AI features; Google's generative-AI content guidance |
| `Anthropic Claude search citation` | Claude's web search + citation behavior (when active) |
| `"Bing Webmaster Tools" "AI Performance" OR IndexNow <current year>` | Bing's citation-level AI reporting and IndexNow guidance |

**Curated WebFetch URLs — first-party AI-search guidance:**

| URL | What it covers |
|---|---|
| `https://developers.google.com/search/docs/fundamentals/ai-optimization-guide` | **Primary.** Google's own AI-search optimization guide (2026-05-15): llms.txt unused by Search, no chunking / AI schema needed, scaled per-query pages are a policy risk. |
| `https://developers.google.com/search/docs/appearance/ai-features` | **Primary.** "AI features and your website": no additional requirements for AI Overviews / AI Mode beyond indexed + snippet-eligible; no AI text files or special markup; allow crawling in robots.txt *and at the CDN or hosting layer*; structured data must match visible text; keep Merchant Center and Business Profile current. Drives `ai_eligibility`, `ai_bot_access_delivered`, `schema_visible_mismatch`. |
| `https://developers.google.com/search/updates` | Dated changelog of every Search Central doc change — fetch every run to catch retirements and new guidance. |
| `https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers` | Google-Extended scope (Gemini grounding, not Search ranking); planned `user-agent: __usage_ai-training` aipref support (early 2027); `common-crawlers.json` IP ranges. |

**Curated WebFetch URLs — AI crawler tables (the crawler-table refresh sources):**

These vendor pages are the source of truth for the crawler groups in `references/site-profile.md` "AI crawler groups", the agent's group lists, and the helper's `AI_BOTS` table. Each run, diff the tokens, purposes, robots.txt behaviour and IP-file URLs on these pages against those three places; report any new, renamed or retired token in the brief under "Crawler table changes" so the maintainer can update all three together.

| URL | What it covers |
|---|---|
| `https://developers.openai.com/api/docs/bots` | OpenAI: GPTBot (training), OAI-SearchBot (ChatGPT search), ChatGPT-User (user-triggered; robots.txt "may not apply"), OAI-AdsBot (ad landing pages). Recommends allowing IP ranges as well as tokens. IP files: `https://openai.com/gptbot.json`, `https://openai.com/searchbot.json`, `https://openai.com/chatgpt-user.json`, `https://openai.com/adsbot.json`. |
| `https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler` | Anthropic: ClaudeBot (training), Claude-SearchBot (search; blocking "may reduce your site's visibility"), Claude-User (user-triggered; honors robots.txt). Warns that IP blocking can stop it reading robots.txt; honors an aipref-based no-training signal. |
| `https://claude.com/crawling/bots.json` | Anthropic's published crawler IP ranges (one file) — what users check WAF logs against for `cdn_waf_block`. |
| `https://docs.perplexity.ai/guides/bots` | Perplexity: PerplexityBot (search index, not training; honors robots.txt), Perplexity-User (user-triggered; "generally ignores" robots.txt). IP files: `https://www.perplexity.ai/perplexitybot.json`, `https://www.perplexity.ai/perplexity-user.json`. |
| `https://support.apple.com/en-us/119829` | Applebot / Applebot-Extended (training opt-out; robots-only token). |

**Curated WebFetch URLs — preference standards (declarations, not enforcement):**

| URL | What it covers |
|---|---|
| `https://datatracker.ietf.org/wg/aipref/about/` | IETF aipref working group — current vocab and attach drafts (`train-ai`, `ai-use`, `search`; `Content-Usage`). Drafts say they do "NOT REFLECT CONSENSUS"; check the revision number each run. |
| `https://blog.cloudflare.com/content-signals-policy` | Cloudflare `Content-Signal:` (`search`, `ai-input`, `ai-train`); managed robots.txt default `search=yes, ai-train=no`. Expresses reserved rights; blocks nothing. |
| `https://llmstxt.org/` | llms.txt spec (info only — format check when the file exists) |

**Curated WebFetch URLs — evidence base (research tier):**

| URL | What it covers |
|---|---|
| `https://arxiv.org/html/2607.14035v1` | Critical GEO survey (July 2026): re-reads the original "up to 40%" GEO result as a within-context word-share gain; C-SEO Bench (3 of 54 combinations significant) and SAGEO Arena (body-only rewrites cut final citation about 6%); evidence grades — extractable attributed facts moderate–strong, recency/prices moderate, structure moderate and stage-dependent, authoritative tone weak, keyword stuffing null or negative; AI-visibility measurement needs repeated sampling. Drives `semantic_content` (extractable facts), `keyword_stuffing`, the `--plan` additive-edit guard and the refused-tactics list. Check for a newer version (`v2`, …) each run. |
| `https://vercel.com/blog/the-rise-of-the-ai-crawler` | Vercel/MERJ (December 2024, vendor measurement): OAI-SearchBot, ChatGPT-User, GPTBot, ClaudeBot, Meta-ExternalAgent and Bytespider fetch JS without executing it. Drives `geo_raw_html_gap`. Replace when a newer primary measurement appears. |
| `https://www.perplexity.ai/hub/blog` | Perplexity's blog — crawler + citation behavior announcements |

**Note:** GEO sources are unstable. For this category the curated first-party and research URLs above are the fixed fetch set; WebSearch finds what changed since. Agency GEO checklists are not curated fetch targets — many still promote llms.txt, FAQPage markup and question-heading quotas, which the skill refuses. If a WebSearch result is such a checklist, the brief may cite a code-detectable pattern from it only when a first-party doc or the research tier backs the same pattern.

---

## Source category 4: Third-party authority blogs (synthesis)

**WebSearch queries:**

| Query | Why |
|---|---|
| `site:moz.com SEO updates <current year>` | Moz industry coverage |
| `site:ahrefs.com SEO research <current year>` | Ahrefs research / studies (vendor tier — label numbers as vendor) |
| `site:searchenginejournal.com <current year>` | SEJ news + analysis |
| `"Search Engine Land" algorithm update <current year>` | SEL coverage of Google algorithm shifts |

**Curated WebFetch URLs:** none. Third-party blogs change URLs frequently; relying on WebSearch each run is safer.

---

## How the orchestrator uses this catalog

SKILL.md Step 1 is authoritative for the run; this file supplies its pool.

1. **WebSearch: 4–6 queries per run** (SKILL Step 1's default list, plus the stack-specific and site-type queries). The category tables above are the pool to rotate from or substitute in when a default query returns thin results — not a list to run in full.
2. **WebFetch, in the same parallel turn:** the curated URLs most relevant to this run — always `https://developers.google.com/search/updates` and the Google AI features page; the AI-crawler table pages whenever the profile's `ai_policy` is set or a bot probe will run; schema.org type pages for the page types detected.
3. Optionally, a second WebFetch round on the 1–2 highest-signal WebSearch results when the curated URLs returned thin content.
4. Synthesize into the ~50-line best-practices brief and pass it to the subagents.

**Failure handling:** if WebSearch / WebFetch return nothing useful (network failure, rate limit, etc.), the orchestrator falls back to embedded heuristics in the scan-*.md files and notes the fallback in the report footer.

---

## Maintaining this file

This file is the *only* place to update when source URLs move or new authoritative sources emerge. **Do not embed time-sensitive guidance in scan-*.md files** — those describe stable detection patterns. Time-sensitive guidance lives in the fetched brief.

Edit cadence: when a source returns 404 or low-quality results, edit this file with the new URL and update the "last verified" note. When the crawler-table diff (category 3) reports a change, update `site-profile.md`, `bx/agents/geo-generative.md` and the helper's `AI_BOTS` table in the same commit.
