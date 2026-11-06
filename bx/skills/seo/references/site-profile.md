# Site Profile — What the Skill Must Ask the User

Loaded by the orchestrator in **Step 0.5**. Defines `.seo-data/site-profile.yaml`, the interview that fills it, and how each answer changes the audit.

## Why this exists

The Search Console API exposes only four resources: Search Analytics, Sitemaps, Sites, URL Inspection ([API reference index](https://developers.google.com/webmaster-tools/v1/api_reference_index), verified 2026-11-06). Everything else that decides whether an audit is *right* is invisible to the skill:

- **Not in any GSC API** (Search Console UI only): manual actions, security issues, the Core Web Vitals report, the Page Indexing report at scale, the Links report, the **Generative AI performance report** (AI Overviews / AI Mode impressions — [blog 2026-06-03](https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports)), the **Search generative AI opt-out setting** ([control doc](https://developers.google.com/search/docs/crawling-indexing/control-what-you-share)), the **branded-queries filter** ([blog](https://developers.google.com/search/blog/2025/11/search-console-branded-filter)), Insights, annotations.
- **Not in GSC at all**: business goals and money pages, brand terms, intended markets, competitors, site type, YMYL status, authorship facts, the AI-crawler *intent* (blocking training while allowing AI search is a valid choice — robots.txt alone can't tell a mistake from a policy), recent migrations.

Without these, the skill ranks by impressions instead of business value, judges robots.txt without knowing intent, and cannot explain a traffic drop caused by a manual action. So it **asks**.

## File: `.seo-data/site-profile.yaml`

Flat keys (same parser rules as `config.yaml`: no nesting; lists are comma-separated strings). **Never contains secrets** — API keys live in environment variables (see `crux_api_key` below). It sits outside the gitignored `.seo-data/gsc/` folder on purpose: it is business context the team should share and review. If the user answers "keep it private" in the interview, append `.seo-data/site-profile.yaml` inside the existing `# /bx:seo managed` `.gitignore` block.

```yaml
# /bx:seo site profile — edit freely; the skill re-asks only for missing or stale keys.
profile_version: 1
reviewed: 2026-11-06            # date the durable keys were last confirmed
site_type: saas                 # local | ecommerce | publisher | saas | portfolio | docs | other:<text>
primary_goal: leads             # leads | sales | ad_revenue | signups | brand | other:<text>
money_pages: /pricing, /contact, /signup
brand_terms: acme, acme app, akme
markets: US:en, DE:de           # country:language pairs; "global:en" allowed
ymyl: no                        # no | health | finance | legal | safety | news
ai_policy: search_yes_training_no   # all_yes | search_yes_training_no | all_no | undecided
target_topics: invoicing software, freelancer taxes
competitors: example.com, other.com
authors: Jane Doe (CPA, 12y tax practice); John Roe (founder)
migration_12mo: none            # none | domain:<old→new, date> | urls:<date> | platform:<date>
private: no                     # yes → gitignored
# --- volatile (Search Console UI facts, re-checked every 28 days) ---
status_checked: 2026-11-06
manual_actions: none            # none | yes:<type> | unknown
security_issues: none           # none | yes:<type> | unknown
gsc_ai_features: on             # on | off | unknown  (Settings → Search generative AI)
```

`crux_api_key` is **never** stored. The orchestrator checks `printenv CRUX_API_KEY >/dev/null && echo set` (reports set/unset only; never echoes the value).

### Staleness

| Tier | Keys | Re-ask when |
|---|---|---|
| Durable | everything above `status_checked` | key missing, OR `reviewed` > 180 days old (then one confirmation question, not the full interview) |
| Volatile | `manual_actions`, `security_issues`, `gsc_ai_features` | `status_checked` > 28 days old, OR GSC mode enabled and this run will compare against a snapshot (a drop needs these facts to be explained) |

## Interview (Step 0.5)

Use **AskUserQuestion** — max 4 questions per call, 2–4 options each; the tool always adds "Other" for free text, so every free-text key is an "Other"-friendly question with the most likely answers as options. **Pre-fill options from the repo** (Step 0 already ran): detected routes for `money_pages`, `<title>`/package name for `brand_terms`, i18n locales for `markets`, schema/route signals for `site_type`. Mark the inferred option `(detected)`.

Ask only what is missing or stale. A first run is at most three calls:

**Call 1 — shapes the whole audit (always first when missing):**
1. `site_type` — "What kind of site is this?" options: the detected type (detected), and 3 alternatives from the enum.
2. `primary_goal` — "What should search traffic do for the business?" options: leads / sales / signups / ad revenue.
3. `ai_policy` — "Which AI systems may use your content?" options: *Allow AI search citations, block training (Recommended for most businesses)* / *Allow everything* / *Block all AI* / *Not decided — show me the trade-off*. Description of each option names the crawler groups (see "AI crawler groups" below).
4. `ymyl` — "Does the site give advice on health, money, legal or safety matters?" options: No / Health / Finance / Legal-or-safety.

**Call 2 — what to rank and for whom:**
1. `money_pages` — "Which pages make money or capture leads?" options: up to 3 detected route sets (e.g. `/pricing, /contact`), multiSelect true.
2. `brand_terms` — "What brand names and misspellings do people search?" options: the detected name, the name + product name. (Used to split brand vs non-brand queries — the GSC branded filter is UI-only.)
3. `markets` — "Which countries and languages are you targeting?" options: detected locales, "Global, English only".
4. `migration_12mo` — "Any domain move, URL restructure or platform change in the last 12 months?" options: None / URL restructure / Domain move / Platform/CMS change.

**Call 3 — Search Console UI facts the API cannot read** (only when the site has a GSC property or `gsc_mode` may be enabled; otherwise ask only the CrUX question):
1. `manual_actions` + `security_issues` — "In Search Console, do Security & Manual actions show anything?" options: Both clear / Manual action present / Security issue present / I can't check now.
2. `gsc_ai_features` — "In Search Console Settings, is 'Search generative AI' on for this property?" options: On (default) / Off / Don't know.
3. Exports — "Can you drop Search Console exports into `.seo-data/gsc/exports/`? They unlock data the API lacks." options (multiSelect): *Generative AI report → Pages (CSV)* / *Core Web Vitals report* / *Links report (top linked pages + top linking sites)* / *Not now*.
4. CrUX — "Real-user Core Web Vitals need a free CrUX API key in the `CRUX_API_KEY` environment variable. Set it up?" options: *Already set* / *Skip field data* / *Show me how* (→ print: create key at console.cloud.google.com → APIs → enable "Chrome UX Report API" → Credentials → API key; then set the env var and re-run). Skip this question when the env var is already set.

**Optional Call 4** — only on the first interview, and only after asking "Add competitors, topics and authors now? (improves content findings)" with Yes / Later:
`target_topics`, `competitors`, `authors`, `private`.

After the interview, write the file (create `.seo-data/` if needed), print `Saved site profile → .seo-data/site-profile.yaml (edit any time; re-asked only when missing or stale).`, and continue.

### When not to ask

- `--no-ask` in `$ARGUMENTS`, or the session is non-interactive (AskUserQuestion unavailable or denied) → use the profile as-is, fill missing keys with `unknown`, and add the footer line `Site profile: <N> keys unknown — run /bx:seo --profile to answer them.` Never block the audit on the interview.
- `--profile` → run the full interview (all calls, pre-filled with current values as `(current)` options), write the file, then continue the audit.
- `--plan` / `--fix` → ask nothing; they act on a prior audit.

## How each answer changes the audit

Every subagent receives the profile in the shared context (SKILL.md Step 5) as a `Site profile:` block. `unknown` values mean "use the default behaviour", never "assume yes".

| Key | Effect |
|---|---|
| `site_type` | Selects expected structured data: `local` → LocalBusiness + Google Business Profile reminder; `ecommerce` → Product/Offer/MerchantReturnPolicy + Merchant Center reminder; `publisher` → Article + Preferred Sources + Discover image checks; `saas`/`docs` → SoftwareApplication/Organization. Also picks the stack-agnostic WebSearch query in Step 1. |
| `primary_goal` + `money_pages` | Step 6.6 ranking: findings on a money page get `×1.5` priority; GSC CTR/position findings on money pages sort first. A money page that is not indexed, `noindex`, or missing from the sitemap is **high** severity. |
| `brand_terms` | `seo-gsc-insights` splits Q1 queries into brand / non-brand by case-insensitive substring match and reports both shares. CTR opportunities are judged on non-brand queries only (brand CTR is not an SEO lever). |
| `markets` | hreflang scan judges against intended markets (missing locale = finding; extra locale = info). GSC country rows outside `markets` are not flagged as low-CTR opportunities. |
| `ymyl` | `eeat` findings rise one severity level; missing author credentials / reviewer / sources on YMYL pages become **medium**. |
| `ai_policy` | `ai_bot_access` is judged against intent (see table below), not against an "allow everything" default. |
| `migration_12mo` | Step 1.6.13 regression findings and 404 clusters are annotated "expected after the <date> migration" when they match; domain moves add a Change of Address check (must now cover all subdomain variants, per [Search Central updates, 2026-06-17](https://developers.google.com/search/updates)). |
| `manual_actions` / `security_issues` = yes | Section 0 headline gets a ⚠ prefix; the top priority is forced to "Resolve the <type> in Search Console before any on-page work" — on-page fixes cannot recover traffic suppressed by a manual action. |
| `gsc_ai_features` = off | Any AI-visibility recommendation is prefixed "Search generative AI is off for this property — AI Overviews/AI Mode won't show it regardless". |
| exports present | Step 1.6.15 parses them (see SKILL.md). |
| `CRUX_API_KEY` set | Step 3.3 fetches real-user Core Web Vitals. |
| `competitors` / `target_topics` | `seo-content` checks whether target topics have a dedicated, indexable page; topics with no page → info finding. Competitors are named in `--plan` briefs only; the skill never fetches competitor sites. |
| `authors` | `eeat` checks that the named authors' bylines/credentials actually appear on their content. The skill never invents credentials. |

### AI crawler groups (for `ai_policy`)

Vendor-documented as of 2026-11 — [OpenAI bots](https://developers.openai.com/api/docs/bots), [Anthropic crawlers](https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler), [Perplexity bots](https://docs.perplexity.ai/guides/bots), [Google common crawlers](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers).

| Group | Tokens | `all_yes` | `search_yes_training_no` | `all_no` |
|---|---|---|---|---|
| Training | `GPTBot`, `ClaudeBot`, `Google-Extended`, `Applebot-Extended`, `CCBot`, `Bytespider` | allow | **block** | block |
| AI search indexing | `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot` | allow | **allow** | block |
| User-triggered fetch | `ChatGPT-User`, `Claude-User`, `Perplexity-User` | allow | allow | block (note: user-triggered fetchers may not honor robots.txt) |

Notes the scanner must carry into findings: `Google-Extended` does **not** affect Google Search inclusion or ranking (it does affect Gemini grounding); Googlebot itself must never be blocked to "opt out of AI Overviews" — that removes the site from Search. The AI Overviews opt-out is `nosnippet`/`max-snippet` or the Search Console setting.

`undecided` → report the current robots.txt state per group as info, with one sentence per group on the trade-off; no score deduction.
