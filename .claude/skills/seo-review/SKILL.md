---
name: seo-review
description: Repo-wide SEO and Generative Engine Optimization audit for web projects. Rejects non-web repos. Fetches current best practices every run (SEO/GEO field evolves rapidly). Probes sitemap URLs for 4xx/5xx/redirect-chain/slow-response health. Optionally ingests Google Search Console data via Bulk Data Export to BigQuery (Performance — queries + pages + per-URL impressions) and/or CSV exports from .seo-data/gsc/ (Page Indexing — all 9 reasons, and Performance fallback when BQ not configured). 4-state matrix governs the mix (BQ + indexing / BQ-only / CSV-only / heuristic-only). Plus 35-day git-history overlap to flag "may already be fixed" against the GSC reporting lag. Three or four parallel Sonnet subagents (seo-technical / seo-content / geo-generative, plus seo-gsc-insights when any GSC data is present). Score stays /100 (purely heuristic) so docs/seo-history.md is comparable across runs regardless of GSC mode. Use when user mentions SEO audit, GEO audit, Generative Engine Optimization, AI search optimization, llms.txt, structured data, sitemap health, Google Search Console, GSC, BigQuery, Bulk Data Export, search performance, or "make this site rank better."
disable-model-invocation: true
allowed-tools: Read, Write, Grep, Glob, Edit, WebSearch, WebFetch, Bash(git:*), Bash(find:*), Bash(wc:*), Bash(jq:*), Bash(cat:*), Bash(head:*), Bash(bq:*), Bash(gcloud:*), Bash(curl:*), Task
effort: high
argument-hint: "[path] [--plan] [--fix] [--url <deployed-url>]"
---

# SEO Review — Repo-Wide SEO + Generative Engine Optimization Audit

Audit a web project for SEO and Generative Engine Optimization (GEO — optimizing for AI search like ChatGPT, Perplexity, Claude, Google AI Overviews) health. The field evolves fast, so this skill **fetches current best practices fresh on every run** rather than relying on bundled static guidance.

This skill is web-projects-only. Step 0 detects web-project state and exits silently on non-web repos — there's nothing to do.

Distinct from existing review skills:

- **`/code-review`** — diff/commit scope, no SEO awareness
- **`/architecture-review`** — code structure, not SEO
- **`/test-review`** — test suite health, not SEO
- **`/code-health-advice`** — routing advisor; routes to `/seo-review` when web project detected
- **`/seo-review` (this)** — repo-wide SEO + GEO audit with live sitemap URL health check

---

## Step 0 — Detect Web Project + Stack

**Run all detection probes in a single parallel turn** — the `Read` + `Glob` calls for the config files below are independent and should fire together, not sequentially.

Reject non-web repos silently. A repo is "web" if **any** of these signals are present:

**Frontend frameworks** (check `package.json` dependencies + devDependencies):
- Next.js (`next`), Nuxt (`nuxt`), Astro (`astro`), Remix (`@remix-run/*`), Gatsby (`gatsby`)
- React + a routing/SSR signal (`react-router`, `react-router-dom`), Vue (`vue`), Svelte/SvelteKit (`svelte`, `@sveltejs/kit`), Angular (`@angular/core`), Solid (`solid-js`)

**Static HTML / generators:**
- `index.html` at repo root or in `public/` / `static/` / `dist/`
- `_config.yml` (Jekyll), `config.toml` + `content/` (Hugo), `eleventy.config.{js,cjs}` (11ty)

**Server-rendered backends:**
- `pyproject.toml` / `requirements*.txt` with Django (`django`), Flask (`flask`), FastAPI (`fastapi`), Starlette (`starlette`) **AND** a `templates/` directory or `static/` directory
- `Gemfile` with Rails (`rails`) **AND** `app/views/`
- `composer.json` with Symfony (`symfony/*`), Laravel (`laravel/framework`) **AND** `resources/views/` or `templates/`
- `pom.xml` / `build.gradle` with Spring Boot Web (`spring-boot-starter-web`) **AND** `templates/` or `static/`
- `.NET` (`*.csproj` with `Microsoft.AspNetCore`)

If none match: output

> Not a web project (no frontend framework, static HTML, or server-rendered templates detected). /seo-review only audits web projects. Exiting.

and stop the skill cleanly.

**Otherwise, print the detected stack in one line.** The line includes the GSC-mode summary computed in Step 1.6 (varies across the 4-state matrix outcomes — see Step 1.6.10 for exact phrasing per mode). Examples:

> Detected: Next.js 14 app-router project, TypeScript, with sitemap.xml at /public/sitemap.xml and i18n via next-i18next. Mode: heuristic + GSC (BigQuery: 47 days data, 2,445 URL rows; 7/11 indexing CSVs; freshness OK). Use `--url <base>` for live HTML diff and sitemap URL probe.

> Detected: Astro 4 project, TypeScript, no i18n. Mode: heuristic + GSC (CSVs only — 13 files; freshness OK; enable BigQuery for full Performance coverage).

> Detected: Hugo static site, no i18n. Mode: heuristic (no GSC data — see one-time setup banner above).

**Detect i18n** for the hreflang scan: `next-i18next`, `nuxt-i18n`, `react-i18next`, `vue-i18n`, `@formatjs/intl`, `i18next`, `next-international` deps, or multi-locale folder structure (`pages/en/`, `pages/fr/`, etc.).

---

## Step 1 — Fetch Current Best Practices

**New pattern not in other skills.** SEO/GEO best practices drift fast (Google adjusts SERP rendering, AI providers shift citation algorithms). Fetch fresh, in-session.

Run in a **single parallel turn** (multiple WebSearch + WebFetch tool calls together):

**WebSearch queries (4-6, parallel):**
- `"SEO best practices 2026 Google Search Central updates"`
- `"generative engine optimization llms.txt content patterns 2026"`
- `"schema.org rich results JSON-LD changes 2026"`
- `"Core Web Vitals thresholds 2026"`
- `"AI search citation patterns ChatGPT Perplexity Claude 2026"`
- One stack-specific query if applicable, e.g. `"Next.js app router SEO metadata 2026"` or `"Astro SEO best practices 2026"`

**WebFetch (run in the SAME parallel turn as the WebSearch queries — the curated URLs in `references/best-practices-sources.md` are stable and don't need WebSearch results to fire):**
- Authoritative pages: Google Search Central docs, web.dev/learn/seo, schema.org type definitions for likely page types
- llms.txt spec page
- Recent Anthropic/OpenAI/Perplexity guidance on citation behavior

A second round of WebFetch on highest-signal WebSearch results is optional and only worth a follow-up turn when the curated URLs returned thin content.

**Summarize into a structured in-session "best-practices brief" (~50 lines max):**

```
## Best-Practices Brief (fetched <YYYY-MM-DD>)

### Google / web.dev
- <bullet 1 with URL>
- <bullet 2 with URL>

### Schema.org / Rich Results
- <bullet>

### Generative Engine Optimization
- <bullet>
- <bullet>

### Stack-specific (<framework>)
- <bullet>

### Weight adjustments suggested
- Generative Engine readiness: +3 (this week's guidance emphasizes AI citation)
- Performance signals: -2 (corresponding decrement)
- Sum delta: 0
```

The brief gets passed **verbatim** to all 3 subagents as shared context. Subagents prefer the brief over their embedded heuristics when the brief diverges.

**Weight-adjustment validation gate.** Before passing weight adjustments to subagents, validate: each |delta| ≤ 5, sum of deltas = 0. If the brief proposes deltas that violate either rule, cap individual deltas to ±5 and rebalance by scaling the opposing deltas proportionally so the sum remains 0. Note any capping in the report footer.

If WebSearch/WebFetch fail or return nothing useful (rare, but possible on flaky network), fall back to a one-line note "best-practices fetch failed — proceeding with embedded heuristics only" and continue. Mark the report footer accordingly.

---

## Parallel-batch note for Steps 1.5 + 1.6

Steps 1.5 (git scan) and 1.6 (GSC ingestion — Search Console API canonical / BigQuery alternative / CSV fallback / heuristic-only) have **independent tool calls** that should fire in a **single parallel turn** — not back-to-back sequentially. In one tool-use block, batch:

**Turn 1 — Detection + optimistic Reads:**
- `git rev-parse --is-shallow-repository` (Step 1.5.1)
- `git log --since="35 days ago" --name-status ...` (Step 1.5.3)
- `Glob .seo-data/gsc/**/*.csv` (Step 1.6.1 CSV inventory)
- `Glob .seo-data/gsc/config.yaml` (Step 1.6.1 config presence)
- `Glob .seo-data/gsc/README.md` (Step 1.6.5 idempotency)
- `Read .gitignore` (Step 1.6.5 idempotency)
- `Read references/gsc-setup-readme-template.md` (fire optimistically; discard if README already exists)
- `Read references/gsc-ingestion.md` (always needed when any GSC mode is active — covers API subsection + BQ subsection + CSV parsing rules + 12 sub-dim catalog)
- `Read .seo-data/gsc/config.yaml` (optimistic; if file doesn't exist, the tool errors silently — interpret as `api_configured = false` AND `bq_configured = false`)
- `Read references/gsc-api-queries.md` (optimistic; only used when API activates — but reading early avoids an extra Read in Turn 2)
- `Read references/gsc-api-schema.md` (optimistic; reference for API response parsing)
- `Read references/bigquery-queries.md` (optimistic; only used when BQ activates)
- `Bash: gcloud --version 2>&1` (gcloud SDK install detection — shared signal for both API and BQ paths)
- `Bash: bq --version 2>&1` (bq CLI install detection — BQ path specific; ships with gcloud SDK but verify independently)
- `Bash: gcloud auth application-default print-access-token 2>&1` (ADC detection; empty/error output treated as not-authenticated)
- `Bash: TOKEN=$(gcloud auth application-default print-access-token 2>&1); curl -s -w "\nHTTP_STATUS:%{http_code}\n" -H "Authorization: Bearer $TOKEN" "https://www.googleapis.com/webmasters/v3/sites"` (combined API auth probe — fetches token AND calls sites.list in one Bash invocation; orchestrator parses HTTP_STATUS to determine if API is reachable; if ADC fails, the probe fails with 401 — both signals captured in one tool call)

Only the **post-tool aggregation** (parsing git log, parsing config.yaml flat keys, resolving the API/BQ/CSV mode, parsing sites.list response, parsing CSVs / BQ JSON / API JSON) runs sequentially.

**Turn 2 — Data ingestion** (conditional on Turn 1's mode resolution; sub-turns 2a + 2b for API path):
- **If API active for Performance**: Turn 2a fires **3 parallel `Bash: curl ...` calls** (Q1+Q2+Q3 from `gsc-api-queries.md`)
- **If API active for Indexing**: Turn 2b fires **up to 100 parallel `Bash: curl ...` calls** (URL Inspection batch — URL selection from Q3 output + sitemap-probe failures + git-changed paths)
- **If BQ active (Performance only)**: 5 parallel `Bash: bq query ...` calls (Q1-Q5 from `bigquery-queries.md`)
- **If CSV path active**: parallel `Read` on each canonical CSV path the Turn 1 Glob confirmed exists (up to 13 — 2 Performance + 11 indexing)
- **Hybrid combinations**: mix per matrix outcome (e.g., API for Performance + CSV for Indexing when API can't inspect; BQ for Performance + CSV for Indexing per v3 default)

Without explicit batching, the orchestrator would run ~20+ sequential tool turns for Steps 1.5+1.6. With batching: 3 turns total (Turn 1 detection + Turn 2a Performance + Turn 2b Inspection batch).

---

## Step 1.5 — SEO-Relevant Change Scan (last 35 days)

Scan git history for SEO-relevant code changes in the last 35 days — roughly the typical Google recrawl + position-stabilization cycle. Produces a ~30-line digest of recent commits + renames + touched files. Used by `seo-gsc-insights` (Phase 4) to annotate findings with `code_changed_since_gsc_window`, and by `--plan` Phase 1 to detect routing-rename + 404-cluster co-occurrence (bulk-redirect signal).

**Critical context:** GSC's reports reflect Google's view of the site at crawl time, which can lag the actual codebase by 4-5 weeks. Without this scan, the skill would confidently recommend "add meta description to /pricing" while the user's commit history shows they added it 18 days ago. The annotation lets the recommendation become "may already be fixed — wait for next GSC cycle or request indexing manually."

### 1.5.1 — Detect git history depth

Run `git rev-parse --is-shallow-repository`. If the answer is `true`, set `git_history_shallow: true` in shared context, log to footer `"git history shallow — change-awareness annotations skipped"`, and skip to Step 1.6.

### 1.5.2 — Build SEO-relevant pathspec set

Combine **universal patterns** (always applied) with **stack-specific patterns** derived from Step 0 framework detection.

**Universal patterns** (every project):
- `**/robots.txt`, `**/sitemap.{xml,ts,js,tsx,jsx,mjs}`, `**/llms.txt`
- `vercel.json`, `netlify.toml`, `_redirects`
- `**/metadata.{ts,js,tsx,jsx}`
- `**/[Hh]ead*.{tsx,jsx,ts,js,vue,svelte,astro}`
- `**/[Ll]ayout*.{tsx,jsx,ts,js,vue,svelte,astro}`

**Stack-specific overlays** (apply when Step 0 detected the framework):

| Stack | Pathspecs |
|---|---|
| Next.js app-router | `app/**/page.{tsx,jsx,ts,js}`, `app/**/layout.{tsx,jsx,ts,js}`, `app/sitemap.{ts,js}`, `app/robots.{ts,js}`, `next.config.{js,ts,mjs}` |
| Next.js pages-router | `pages/**/*.{tsx,jsx,ts,js,md,mdx}`, `next.config.{js,ts,mjs}` |
| Nuxt | `pages/**/*.vue`, `layouts/**/*.vue`, `nuxt.config.{js,ts}` |
| Astro | `src/pages/**/*.{astro,mdx,md,html}`, `src/layouts/**/*.astro`, `astro.config.{mjs,ts,js}` |
| Remix | `app/routes/**/*.{tsx,jsx,ts,js,md,mdx}`, `app/root.{tsx,jsx,ts,js}` |
| SvelteKit | `src/routes/**/+page*.svelte`, `src/routes/**/+layout*.svelte`, `svelte.config.{js,ts}` |
| Vue/Vite | `src/pages/**/*.vue`, `vite.config.{js,ts}` |
| Gatsby | `src/pages/**/*.{js,jsx,ts,tsx}`, `gatsby-config.{js,ts}`, `gatsby-node.{js,ts}` |
| Jekyll | `_layouts/**/*.html`, `_includes/**/*.html`, `_config.yml`, `**/*.md` |
| Hugo | `layouts/**/*.html`, `content/**/*.md`, `config.toml`, `hugo.{toml,yaml,yml}` |
| 11ty | `**/*.{njk,liquid,hbs}`, `**/*.11ty.js`, `eleventy.config.{js,cjs}`, `.eleventy.js` |
| Rails | `app/views/**/*.{erb,haml,slim}`, `config/routes.rb` |
| Django | `**/templates/**/*.html`, `**/urls.py` |
| Flask/FastAPI | `**/templates/**/*.{html,jinja,jinja2}`, `**/routes.py`, `**/main.py` |
| Laravel | `resources/views/**/*.blade.php`, `routes/web.php` |
| Spring Boot | `**/templates/**/*.html`, `**/*Controller.java`, `**/*Controller.kt` |
| .NET | `**/Views/**/*.cshtml`, `**/Pages/**/*.cshtml`, `**/Program.cs`, `**/Startup.cs` |
| Static HTML | `**/*.html` |

If Step 0 detected an unrecognized stack OR no specific framework (e.g., raw static HTML in `public/`), use universal patterns only.

### 1.5.3 — Run git scan

Execute a **single** git log call:

```
git log --since="35 days ago" --name-status --pretty=format:"<<<COMMIT>>>%n%H|%ci|%s" -- <pathspec1> <pathspec2> ...
```

The `<<<COMMIT>>>` separator makes parsing unambiguous. Output structure per commit:

```
<<<COMMIT>>>
abc1234567|2026-04-22 12:34:56 -0700|fix: add meta description to /pricing
M	src/app/pricing/page.tsx
M	app/metadata.ts

<<<COMMIT>>>
ghi7894561|2026-04-10 14:22:11 -0700|chore: restructure blog routing
R100	src/content/posts/foo.md	src/app/blog/foo/page.tsx
R100	src/content/posts/bar.md	src/app/blog/bar/page.tsx
M	next.config.js
M	public/sitemap.xml
```

Cap the output to the first **200 commits** by splitting on `<<<COMMIT>>>` and slicing.

### 1.5.4 — Parse + aggregate

Walk the commit blocks. For each:

1. First line after `<<<COMMIT>>>` is `<hash>|<iso-date>|<subject>` — parse.
2. Subsequent lines are `<status>\t<path>[\t<new-path>]`:
   - `M`, `A`, `D` → modified/added/deleted, single path
   - `R<percent>`, `C<percent>` → rename/copy with old + new paths (rename score is the percent match)

Aggregate:

- `file_commits: {path → [(hash, date, subject), ...]}` — for the touched-files list
- `renames: [(old_path, new_path, hash, date, subject), ...]` — for rename detection (high signal for 404 generation)

### 1.5.5 — Output: SEO-Relevant Changes Digest

Build a structured digest (~30 lines max). Truncate per category if needed; cluster aggressive renames:

```
## Recent SEO-Relevant Changes (last 35 days, N commits across M files)

### Touched files (top 10 by commit count)
- src/app/pricing/page.tsx: 3 commits, latest 2026-04-22 ("add meta description")
- public/sitemap.xml: 2 commits, latest 2026-04-15 ("regen sitemap after route rename")
- next.config.js: 2 commits, latest 2026-04-10 ("restructure blog routing")
[…]

### Renames detected (high signal for 404 generation)
- src/content/posts/* → src/app/blog/* on 2026-04-10 (12 files, commit ghi7894, "restructure blog routing")
[…]

### Routing config changes
- next.config.js (3 commits, latest 2026-04-10): redirect rules touched
[…]
```

Cluster renames: when ≥3 renames share a prefix pattern (e.g., all `src/content/posts/foo.md → src/app/blog/foo/page.tsx`-style mappings), report as a single cluster `src/content/posts/* → src/app/blog/*` with file count, not per-file.

If the scan returned zero commits in window, render `## Recent SEO-Relevant Changes (last 35 days)\n\nNo SEO-relevant changes in the window.` — short, single block.

### 1.5.6 — Pass to all dispatched subagents (Step 5 shared context)

Append to the Step 5 base shared-context block (after the GSC section from 1.6):

```
Git history scan: 35d window, <N> commits across <M> files. Shallow: false.

Digest:
<the 30-line digest from 1.5.5>

(Renames + touched files map also passed as a structured object for 
seo-gsc-insights cross-reference logic.)
```

Subagents use this in two ways:
- **`seo-gsc-insights`** — primary consumer. For each GSC finding, scan the digest for matching paths (e.g., if a `not_found_404` finding affects `/blog/2023/foo`, look for a rename touching `src/content/posts/2023/` or similar). Set `code_changed_since_gsc_window: true` when matched; lower certainty to 0.4; rewrite recommendation to acknowledge the recent change.
- **Other 3 subagents** — informational. May note "this finding is on a recently-touched file" but don't change scoring.

### 1.5.7 — Footer addition

Append to Step 5's footer:

```
Git history scan: 35d, <N> SEO-relevant commits across <M> files. Shallow: <true | false>.
```

When shallow: `Git history scan: skipped (shallow clone — change-awareness annotations off).`

---

## Step 1.6 — GSC Ingestion (precedence-driven dispatcher)

GSC data can arrive via three paths, with precedence: **Search Console API** (canonical for both Performance and Indexing — v3.x) > **BigQuery Bulk Data Export** (alternative power-user path for Performance only — v3) > **CSV exports** (universal fallback — v2). This step detects which paths are reachable and dispatches accordingly.

Five reference files cover the implementation:
- `references/gsc-ingestion.md` — canonical digest shapes, CSV parsing rules, API + BigQuery digest contracts, 12 sub-dim finding catalog, freshness policy, `.gitignore` auto-append rules
- `references/gsc-api-schema.md` — Search Console API endpoint inventory, auth/scope, quota model, `coverageState`/`pageFetchState` enums
- `references/gsc-api-queries.md` — 3 parametrized `curl` templates (Q1/Q2/Q3) + URL Inspection per-URL template + URL selection algorithm + coverageState→9-reason lookup table
- `references/bigquery-queries.md` — 5 parametrized SQL templates (Q1-Q5)
- `references/bigquery-config-template.md` — flat-YAML config schema + setup walkthrough

### Precedence ladder

| Signal | First choice | Fallback | Final fallback |
|---|---|---|---|
| **Performance** | Search Console API (`searchanalytics.query`) | BigQuery (`bq query searchdata_url_impression`) | CSV (`performance/queries.csv` + `pages.csv`) |
| **Indexing** | Search Console API (`urlInspection.index.inspect` per-URL) | (no BQ option — Google's product limit) | CSV (the 11 indexing reason CSVs) |

Each signal independently picks the highest-priority available source. The orchestrator does NOT mix sources within a single signal — once API is active for Performance, BQ + CSV Performance are not consulted (and vice versa).

### User-facing mode labels (4-label collapse per Plan-agent S1)

The raw `(perf_source, indexing_source)` pair has 4 × 3 = 12 combinations, but only 4 user-facing labels:

| Mode label | Condition | User-facing warning |
|---|---|---|
| **Full GSC (API)** | `perf_source == "api" AND indexing_source == "api"` | none — best state |
| **Full GSC (hybrid)** | Both signals present but mixed sources (e.g., API perf + CSV indexing; BQ perf + CSV indexing; CSV+CSV) | Footer note: `Performance: <source>; Indexing: <source>. <upgrade hint if applicable>` |
| **Partial GSC** | Exactly one signal present (API/BQ/CSV) and one missing | Footer note: `Performance signal: <source/none>; Indexing signal: <source/none>. <upgrade hint>` |
| **Heuristic-only** | Both signals absent (no API + no BQ + no CSVs) | Section 1 banner: `⚠ No GSC data — code-only review. Recommendations cannot be traffic-prioritized.` |

The machine-readable `(perf_source, indexing_source)` pair is preserved separately for the footer audit (Step 1.6.12) — values: `api`, `bq`, `csv`, `none`.

### Failure-handling invariants (locked decision 10)

When API or BQ is configured AND a runtime call fails:
- **NO silent fallback** to a lower-precedence path for the SAME signal
- Print the exact API/bq error to footer
- Skip that signal (treat as missing for matrix purposes)
- The opposite-signal path proceeds independently

Example: API configured + Performance call returns 401 → Performance signal missing for this run → footer logs the error → indexing CSVs (if present) still produce findings. To restore BQ Performance behavior, user removes `site_url` from config.yaml (which deactivates API and lets BQ take over per precedence).

### 1.6.1 — Detection (Turn 1, joins Step 1.5's parallel batch)

All GSC-related tool calls listed in the "Parallel-batch note" above fire in Turn 1 alongside Step 1.5. After the batch returns, parse the results into:

| Variable | Source | True/false condition |
|---|---|---|
| `perf_csvs_present` | Glob `.seo-data/gsc/performance/*.csv` | ≥1 of `queries.csv` or `pages.csv` |
| `indexing_csvs_present` | Glob `.seo-data/gsc/indexing/*.csv` | ≥1 indexing CSV |
| `config_yaml_present` | Read `.seo-data/gsc/config.yaml` | Read succeeded (non-error result) |
| `gcloud_cli_installed` | `gcloud --version` exit + stdout | stdout contains version string (regex `\d+\.\d+\.\d+`) |
| `bq_cli_installed` | `bq --version` exit + stdout | stdout contains a version string |
| `adc_authenticated` | `gcloud auth application-default print-access-token` | stdout non-empty AND no `ERROR:` line |
| `api_probe_succeeded` | combined `gcloud + curl sites.list` output | `HTTP_STATUS:200` line present AND response body parses as JSON containing `siteEntry` array |
| `api_probe_response` | same | full JSON body — used in 1.6.3 to check `site_url` membership |

### 1.6.2 — Parse config.yaml and resolve `api_configured` + `bq_configured`

When `config_yaml_present`, parse the file's content (already Read in Turn 1) via line-by-line walk:

1. Reject nested keys: any line matching `^\s+[a-z_]+:` (leading whitespace before key) → emit `Config error: nested keys not supported in .seo-data/gsc/config.yaml — use flat top-level keys only.` and set BOTH `api_configured = false` AND `bq_configured = false`. Skip rest of parse.
2. Extract flat keys: lines matching `^([a-z_]+):\s*(.*)$` (no leading whitespace). Build `config: {key: value, ...}`.
3. Warn on unknown keys (not in `{project_id, dataset_id, location, site_url, lookback_days}`): log `Config warning: unknown key '<X>' — ignored.`
4. Default `lookback_days = 90` when omitted. Validate range [7, 365] when present.

**Path-aware validation** (Plan-agent locked decision 12):

```
api_configured = config.site_url is present AND non-empty after trimming
```

```
bq_configured = config.project_id is present AND non-empty
              AND config.dataset_id is present AND non-empty
              AND config.location is present AND non-empty
```

Both checks are independent — one can pass while the other fails:
- `site_url` only → API-only intent (most common new-user setup)
- `project_id` + `dataset_id` + `location` only → BQ-only intent (v3 power-user)
- All four keys → both paths possible (precedence picks API)
- Partial BQ keys (some present, others missing) → log `Config warning: BQ keys partially present — all of project_id, dataset_id, location must be set together. BQ path disabled this run.` and set `bq_configured = false`. API path unaffected if `site_url` is set.

### 1.6.3 — Resolve precedence and 4-label mode

```
api_active = api_configured
           AND gcloud_cli_installed
           AND adc_authenticated
           AND api_probe_succeeded
           AND <config.site_url appears in api_probe_response.siteEntry[*].siteUrl>
           AND <matched entry's permissionLevel != "siteUnverifiedUser">

bq_active  = bq_configured
           AND gcloud_cli_installed
           AND bq_cli_installed
           AND adc_authenticated

perf_source     = "api" if api_active else
                  "bq"  if bq_active  else
                  "csv" if perf_csvs_present else
                  "none"

indexing_source = "api" if api_active else
                  "csv" if indexing_csvs_present else
                  "none"

gsc_mode        = "enabled" if (perf_source != "none" OR indexing_source != "none")
                  else "disabled"
```

**User-facing mode_label** (Plan-agent S1 — collapse to 4):

```
if perf_source == "api" AND indexing_source == "api":
    mode_label = "Full GSC (API)"
elif perf_source != "none" AND indexing_source != "none":
    mode_label = "Full GSC (hybrid)"
elif perf_source != "none" OR indexing_source != "none":
    mode_label = "Partial GSC"
else:
    mode_label = "Heuristic-only"
```

The `(perf_source, indexing_source)` pair is preserved for the footer audit. Example footer values: `(api, api)`, `(api, csv)`, `(bq, csv)`, `(none, csv)`, `(none, none)`, etc.

**`gsc_warning_text`** is set per the table in the 1.6 intro:
- Full GSC (API) → empty
- Full GSC (hybrid) → `Performance: <source>; Indexing: <source>. <upgrade hint if downgradable>`
- Partial GSC → `Performance: <source/none>; Indexing: <source/none>. <upgrade hint>`
- Heuristic-only → (handled by Section 1 banner in 1.6.4, not footer)

**Probe failure handling**: when `api_configured == true` but `api_probe_succeeded == false` (HTTP 401/403/404/etc.):
- Set `api_active = false`
- Surface the exact error in footer (parse `error.status` per gsc-api-schema.md):
  - 401 → `Search Console API auth failed: 401 UNAUTHENTICATED. Run "gcloud auth application-default login --scopes=https://www.googleapis.com/auth/webmasters.readonly,https://www.googleapis.com/auth/cloud-platform" to refresh credentials with the right scope.`
  - 403 → `Search Console API access denied: 403 PERMISSION_DENIED. The configured site_url '<X>' is not accessible by your Google account. Verify property ownership in GSC > Settings.`
  - sites.list returns 200 but `site_url` not in `siteEntry`: `site_url '<X>' not found in your verified GSC properties. Check the value or verify the property.`
- Per precedence, control passes to BQ if `bq_active`, else CSV if `perf_csvs_present`, else heuristic for Performance signal
- Indexing signal flows independently: API failure for Performance ALSO disables API for Indexing (they're entangled — same auth) → indexing falls through to CSV path if present

### 1.6.4 — Heuristic-only fast-path (gsc_mode == "disabled")

When `gsc_mode == "disabled"` (no API + no BQ + no CSVs):

1. Check sentinel `.seo-data/.gsc-banner-shown`. If **absent**: emit the unified setup banner (see `gsc-ingestion.md` "Setup banner — Path 1 (API) / Path 1b (BQ) / Path 2 (CSV)"). Touch the sentinel (`Write` empty file).
2. Set `gsc_mode_summary = "heuristic-only"` for Step 0's detected line.
3. Stash `section_1_banner = "⚠ No GSC data — code-only review. Recommendations cannot be traffic-prioritized. See .seo-data/gsc/README.md to enable GSC-aware audit."` for Section 1 rendering.
4. Skip to Step 2 (Mode Dispatch). No data ingestion needed.

### 1.6.5 — README + .gitignore (idempotent — runs whenever .seo-data/gsc/ exists)

If `.seo-data/gsc/` exists (any CSV OR config.yaml detected):

**README**: if `.seo-data/gsc/README.md` is absent (from Turn 1 Glob), write the template's content block from `references/gsc-setup-readme-template.md` (extract between `## Template content (begin)` and `## Template content (end)` markers, inner-fenced block). If README exists, discard the optimistic template Read.

**.gitignore**: from the Turn 1 `Read .gitignore` result, Grep for sentinel start marker `# /seo-review managed`. If absent, append:

```
# /seo-review managed — do not edit between markers
.seo-data/gsc/
.seo-data/.gsc-banner-shown
# /end /seo-review managed
```

Notice the block also covers `config.yaml` (under `.seo-data/gsc/`) — config contains `project_id` and `site_url` which are non-secret but property-identifying, so the default of "don't commit" is right. If `.gitignore` doesn't exist, create it with the sentinel block. Print `Added .seo-data/gsc/ to .gitignore (sentinel-marked block).` on first append; silent thereafter.

### 1.6.6 — Data ingestion (Turn 2, parallel batch)

Per the precedence resolution from 1.6.3, fire data-ingestion calls. The Turn 2 structure depends on which sources are active.

#### Token acquisition (when API or BQ active)

When `api_active OR bq_active`, fetch the ADC token **once** at the start of Turn 2 (Plan-agent S2 — cache for run):

```
TOKEN=$(gcloud auth application-default print-access-token)
```

Reuse the token across all subsequent `curl` and `bq` invocations in this run.

#### Turn 2a — Performance signal (one branch fires)

**When `perf_source == "api"`** — fire **3 parallel `Bash: curl` calls** for Q1 (queries digest) + Q2 (pages digest) + Q3 (`url_impressions_map`), using templates from `references/gsc-api-queries.md` (already Read in Turn 1). Substitute `<<LOOKBACK_DAYS>>` and the URL-encoded `site_url` (`:` → `%3A`, `/` → `%2F` per `gsc-api-schema.md`):

```
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '<JSON_BODY with substituted startDate/endDate/dimensions/rowLimit>' \
  "https://www.googleapis.com/webmasters/v3/sites/<SITE_URL_ENCODED>/searchAnalytics/query"
```

Q4 (orphan candidates) and Q5 (freshness probe) are NOT fired — per Plan-agent S4, Q4 reuses Q3's keys for orphan computation, and the API has no freshness equivalent.

**When `perf_source == "bigquery"`** — fire **5 parallel `Bash: bq query` calls** using the templates from `references/bigquery-queries.md`:

```
bq query \
  --use_legacy_sql=false \
  --maximum_bytes_billed=1000000000 \
  --format=json \
  --location=<config.location> \
  '<SQL with <<PROJECT>>, <<DATASET>>, <<LOOKBACK_DAYS>> substituted>'
```

Run Q1-Q5 from `bigquery-queries.md`.

**When `perf_source == "csv"`** — fire parallel `Read` on `.seo-data/gsc/performance/queries.csv` and `pages.csv` (whichever the Glob confirmed exist).

**When `perf_source == "none"`** — no Performance data ingestion this turn.

#### Turn 2b — Indexing signal (one branch fires after Turn 2a)

Turn 2b depends on Turn 2a's output when API is active (URL selection algorithm uses Q3's `url_impressions_map`). When indexing source isn't API, Turn 2b can run in parallel with Turn 2a.

**When `indexing_source == "api"`** — first compute the URL Inspection budget per `gsc-api-queries.md` "URL Inspection — selection algorithm" (50 by impressions from Q3 output + 30 sitemap-probe-failures from Step 3.2 + 20 git-changed paths from Step 1.5 resolved via `page_type_map`, dedup, hard cap 100). Then fire **N parallel `Bash: curl` calls** (N ≤ 100):

```
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"inspectionUrl":"<URL>","siteUrl":"<config.site_url RAW>"}' \
  "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
```

Note: `siteUrl` in this request is a **body field** (raw, no URL encoding) — distinct from Search Analytics where it's a path param.

**When `indexing_source == "csv"`** — fire parallel `Read` on each canonical indexing CSV path the Glob confirmed exists (up to 11 files).

**When `indexing_source == "none"`** — no Indexing data ingestion this turn.

#### Parallel turn counts

Worst case (Full GSC API mode): Turn 2a = 3 curl calls; Turn 2b = up to 100 parallel curl calls. Total Step 1.6 = 3 turns (detection + 2a + 2b).

Other modes have fewer turns:
- API perf + CSV indexing: 3 curl (Turn 2a) + 11 Read (Turn 2b can run parallel with 2a since URLs don't feed CSVs)
- BQ perf + CSV indexing (v3 default): 5 bq query (Turn 2a) + 11 CSV Read in same parallel batch = 16 tool calls 1 turn
- CSV-only (v2 path): up to 13 CSV Reads in 1 parallel turn

### 1.6.7 — Parse outputs into byte-identical digests

After Turn 2 returns, walk results per `references/gsc-ingestion.md`. The digest shape is byte-identical regardless of source (API / BQ / CSV).

**Search Console API JSON outputs (Q1+Q2+Q3 + URL Inspection)** — translate per `gsc-ingestion.md` "API ingestion → Digest shape":
- API returns numeric fields as **native JSON numbers** (NOT quoted strings like BQ). No `Number()` cast needed — passthrough.
- Map API row fields → digest field names: `keys[0]` → `query` (Q1) or `url` (Q2/Q3); `impressions` / `clicks` / `ctr` / `position` passthrough.
- Apply **client-side filters** (the API doesn't support position-range filtering): Q1 filters `impressions >= 100 AND position BETWEEN 5.0 AND 20.0`; Q2 filters `impressions >= 10`. Then sort by impressions desc and take top 50.
- Q3's full result (`page` dimension, uncapped client-side) becomes `url_impressions_map`. **Silent truncation at rowLimit=25000** for sites with >25k URLs (Plan-agent B1 — documented).
- URL Inspection responses: walk each `inspectionResult.indexStatusResult`, apply the `coverageState` + `pageFetchState` joint lookup table from `gsc-api-queries.md` to assign each URL to a sub-dim cluster (or "no finding" / "Other" bucket). Carry per-URL diagnostic fields (`lastCrawlTime`, `googleCanonical`, `userCanonical`, `crawledAs`, `indexingState`, `robotsTxtState`) into `evidence` for cluster findings.

**BigQuery JSON outputs** — translate per `gsc-ingestion.md` "BigQuery ingestion → Digest shape":
- Cast every INT64 / FLOAT64 field (returned as quoted JSON string) to JS Number on ingest
- Map BQ field names → digest field names (e.g., `avg_position` → `position`)
- Top-50 ordering already enforced server-side via `LIMIT 50` in Q1/Q2
- Build `url_impressions_map` from Q3's uncapped output

**CSV outputs** — parse per `gsc-ingestion.md` "Parsing rules" (BOM strip, header validation, quoted-comma handling, CTR `%`-strip and `/100`, position float-parse).

**Failure modes** (all log to footer, never block):
- API call returns 4xx/5xx → parse `error.code` + `error.status` per `gsc-api-schema.md`; that signal skipped (no silent fallback to BQ/CSV for same signal)
- API URL Inspection batch returns 429 mid-batch → graceful degrade per Plan-agent decision 10 — stop sending, surface count succeeded vs skipped in footer
- BQ query fails → `bq_query_failed: true`, footer captures stderr verbatim, that signal skipped (no CSV fallback)
- BQ schema drift (column not found error) → footer note pointing to `bigquery-schema.md` for re-validation
- Unknown CSV path → `unknown CSV ignored: <path>`
- Missing required CSV header → `CSV skipped: <path> — expected <X>, detected <Y>`
- Malformed CSV rows → `malformed_rows: <count>` per file

Track `total_count` per cluster source. API path: `total_count` = inspected-URL-count (not site-wide). BQ Q1/Q2 truncate at 50 server-side. Indexing CSVs may have unbounded source rows.

### 1.6.8 — Build cross-subagent maps

After all parsing complete:

- **page_type_map**: `{url → page_type}` over the union of URLs from:
  - Top-50 URLs from the active Pages digest (Q2 — API or BQ or `performance/pages.csv` — top-50 only, NOT Q3's uncapped map)
  - Inspected URLs from URL Inspection batch (when `indexing_source == "api"`) OR URLs from indexing CSV digests (when `indexing_source == "csv"`)
  - Sitemap URLs (Step 3.2)
  Classification per `gsc-ingestion.md` "page_type_map building".
- **url_impressions_map**: `{url → impressions}` — from Q3's uncapped output when API or BQ active, or from `performance/pages.csv` digest when CSV active. Passed to all subagents in Step 6 ranking (`rubric.md` "Traffic-weighted ranking").

### 1.6.9 — Freshness check (source-dependent)

**Search Console API path:** no `data_date` equivalent — the API returns the live view of GSC's pipeline. Set `freshness_summary` to static footer line:

```
GSC API path: real-time view of GSC's pipeline (typically ~2-day lag from real-world events).
```

**BigQuery path:** consume Q5's `latest_data_date`. Compute `days_old = today - latest_data_date`. Thresholds from `gsc-ingestion.md` "Freshness policy (BQ-specific)".

**CSV path:** per-file `mtime` → `days_old`. Same `<30 / 30-90 / >90` thresholds.

Never block on freshness.

### 1.6.10 — Compute mode summary fragment (consumed by Step 0)

Build the GSC-mode fragment for Step 0's detected-stack line per `mode_label` from 1.6.3 (4 user-facing labels per Plan-agent S1):

| `mode_label` | Step 0 fragment example |
|---|---|
| **Full GSC (API)** | `Mode: heuristic + GSC (Search Console API — 95 URLs inspected, 3 perf queries; ~2-day API lag)` |
| **Full GSC (hybrid)** | `Mode: heuristic + GSC (hybrid — Performance: <source>, Indexing: <source>)` <br/>e.g. `(hybrid — Performance: BigQuery; Indexing: 7 indexing CSVs)` |
| **Partial GSC** | `Mode: heuristic + GSC (partial — Performance: <source/none>, Indexing: <source/none>; missing signal degrades top-3 recommendations)` |
| **Heuristic-only** | `Mode: heuristic (no GSC data — see one-time setup banner above)` |

The Step 0 line is informational. Detailed source breakdown lives in the footer (Step 1.6.12) for machine-readable audit.

### 1.6.11 — Pass to all dispatched subagents (Step 5 shared context)

The orchestrator's Step 5 shared-context block (passed to all subagents) gains a GSC section:

```
GSC Mode: <mode_label from 1.6.3>
Performance source: <api | bigquery | csv | none>
Indexing source: <api | csv | none>

When perf_source or indexing_source != "none":
- Sources detected:
    - Search Console API: site_url=<x> lookback_days=<N>, perf calls succeeded=<3/3>, urls inspected=<N>/<budget>
    - BigQuery: project=<x> dataset=<y> location=<z> lookback_days=<N>, latest_data_date=<YYYY-MM-DD> (Q5)
    - CSVs: <list of canonical paths present>
- Digests (byte-identical shape regardless of source — see gsc-ingestion.md):
  - queries digest: <top-50 records {query, impressions, clicks, ctr, position}>
  - pages digest: <top-50 records {url, impressions, clicks, ctr, position}>
  - indexing clusters: <up to 9 sub-dim clusters from URL Inspection OR CSV>, each with total_count + affected_urls + per-URL evidence
  - indexing/summary digest: <full table, ≤11 rows> ← only present when indexing CSV/summary.csv was parsed (API path has no site-wide aggregate)
- page_type_map: {<url>: <page_type>, ...}
- url_impressions_map: {<url>: <impressions>, ...}   ← used for traffic_weight lookups
- Freshness summary: [{source, days_old | "real-time"}, ...]
- Malformed rows: {<file>: <count>} (omit when all zero)
- API call failures: [{endpoint, http_status, error_status}, ...] (omit when none)
- BQ query failures: [...] (omit when none)
- Unknown CSVs ignored: [<paths>] (omit when empty)

When both perf_source AND indexing_source == "none":
- gsc_mode: disabled
- Reason: "no .seo-data/gsc/" | "no API/BQ config + no CSVs"
```

**Primary consumer:** `seo-gsc-insights` subagent (dispatched as 4th parallel Task in Step 5 when `gsc_mode: enabled`). Other 3 subagents use `url_impressions_map` for traffic_weight when ranking their own findings; the rest is informational.

Subagents do NOT need to know which source produced the digest — the byte-identical contract from `gsc-ingestion.md` guarantees identical finding emission across API / BQ / CSV paths.

### 1.6.12 — Footer addition

Append to Step 5's footer (after the Step 1.5.7 git-history line):

```
GSC mode: <mode_label from 1.6.3>. (perf: <api|bq|csv|none>, indexing: <api|csv|none>).
<gsc_warning_text from 1.6.3, if non-empty>
<freshness summary, single line — "real-time" for API, days_old for BQ/CSV>
<URL Inspection status, if api active for indexing — "Inspected N/M URLs; X% indexed; quota remaining ~Y/2000 today">
<API call failures, if any — one line per failed call with HTTP status + error_status>
<BQ query failures, if any — one line per failed query>
```

In heuristic-only mode, render only the first line: `GSC mode: heuristic-only. (perf: none, indexing: none).` — the Section 1 banner carries the user-facing call to action; the footer line is a machine-readable audit record.

Quota tracking is approximate for API path (the API doesn't expose a precise counter — back-of-envelope: `2000/day per property minus inspections this run`).

---

## Step 2 — Mode Dispatch

Interpret `$ARGUMENTS`:

| Argument | Effect |
|----------|--------|
| (none) | Default review-only: produce report and stop |
| path (e.g. `src/pages/`) | Scope to that path |
| `--plan` | After report, emit phased rewrite brief (read `references/plan-mode-seo.md`) |
| `--fix` | After report, apply strict-allowlist mechanical fixes with per-finding diff preview (read `references/fix-allowlist.md`) |
| `--url <deployed-url>` | Live HTML fetch for SSR/SSG checks AND synthesizes sitemap URL probe bases when sitemap URLs are relative |

`--plan` and `--fix` are mutually exclusive. If both supplied: "Pick one — `--plan` emits a brief, `--fix` applies edits."

---

## Step 3 — Live HTTP Work (Orchestrator-Only)

**Subagents never make network calls.** All HTTP work happens here.

### 3.1 Single deployed URL (if `--url <base>` provided)

`WebFetch` the URL with a prompt like "Return the full rendered HTML and document the final URL after any redirects." Capture the rendered HTML excerpt. Pass to `seo-technical` and `seo-content` (skip `geo-generative` — JSON-LD lives in source most reliably).

### 3.2 Sitemap URL Health Probe

Runs **always when sitemap.xml exists locally** AND (sitemap URLs are absolute OR `--url <base>` provides a domain to synthesize bases from).

1. **Locate sitemap.xml locally** — try in order: repo root, `public/sitemap.xml`, `static/sitemap.xml`, `dist/sitemap.xml`, `out/sitemap.xml`, `_site/sitemap.xml`. Also check for `sitemap_index.xml` — if found, parse it and follow `<sitemap><loc>` entries to find child sitemaps (cap at 5 child sitemaps to avoid runaway).
2. **Parse with Read tool** (not network) — extract `<url><loc>` entries.
3. **URL list resolution:**
   - If URLs are absolute (start with `http://` / `https://`) → use them as-is.
   - If URLs are relative AND `--url <base>` provided → synthesize: `<base>` + relative path.
   - If URLs are relative AND no `--url` provided → **skip the probe**, add a footer note: "URL probe skipped — sitemap.xml has relative URLs; re-run with `--url <base>` for live URL health check."
4. **Cap at top 100 URLs** by document order, or by `<priority>` descending if present.
5. **Probe each URL in a single parallel turn** — multiple `WebFetch` calls in one tool-use block with a minimal prompt:
   > "Report the HTTP status code, final URL after any redirects, redirect chain hop count, and response time in seconds. Do not return page content."
6. **Collect results** into structured records: `{url, status, redirect_hops, response_seconds}`. Classify response time into buckets: `fast` (<1s), `medium` (1-3s), `slow` (>3s).
7. **Pass results to `seo-technical`** as shared context.

**Score-impact rules** (enforced by `seo-technical` per its hard rules):

| Status / signal | Severity | Score impact per URL |
|---|---|---|
| 404 | high | 1-3 (scales with count) |
| 410 | medium | 1-2 |
| 403 | high | 1-3 |
| 5xx | high | 2-3 |
| redirect chain >1 hop | medium | 0.5-1 |
| response_bucket: slow | low | 0.25 (Performance dim) |
| WebFetch error (network failure) | low | 0 — record but don't penalize |

**Total URL-health deduction is capped at 8 points** (out of Technical SEO's 25). A fully broken sitemap doesn't zero out Technical SEO.

---

## Step 4 — Scope Selection

If a path argument was given, scope subagents to that path (only page-template / layout / content files under it). Else apply the standard tier from repo size (read `architecture-review/references/scale-strategy.md` for the formula). For SEO, default cap is files containing HTML-emitting code: page components, layout files, MDX/markdown content, templates.

---

## Step 5 — Parallel Subagent Dispatch

Launch all subagents in a **single turn** (3 Task calls when `gsc_mode: disabled`; 4 Task calls when `gsc_mode: enabled` — add the `seo-gsc-insights` dispatch in the same message as the other 3). Mirror `/test-review` Step 4.

For each subagent, read its corresponding reference file (`references/scan-technical.md`, `references/scan-content.md`, `references/scan-geo.md`, and `references/gsc-ingestion.md` for the 4th when enabled) and pass the contents in the task prompt along with shared context.

### Shared context — base block passed to all subagents:

```
Detected stack: <from Step 0>
i18n detected: true | false (with config file path if true)
Best-practices brief (fetched <date>):
<verbatim 50-line brief from Step 1>

Weight adjustments (validated in Step 1: |each| ≤ 5, sum = 0):
{"structured_data": -2, "generative_engine": +3, "performance": -1, ...}

Scope file list: <paths>

# GSC + git context (always present; values vary by mode)

GSC Mode: enabled | disabled
[When enabled, full GSC block from Step 1.6.7 — CSVs detected, digests, page_type_map, url_impressions_map, freshness summary, malformed rows]
[When disabled, just: gsc_mode: disabled, Reason: ...]

Git history scan: 35d window, <N> commits across <M> files. Shallow: <true|false>.
[Recent SEO-Relevant Changes digest from Step 1.5.5, ~30 lines]

# Output expectations

Findings format: structured JSON-like blocks per the scan-*.md reference.
Each finding includes dimension, sub_dimension, location, title, severity, certainty,
effort_estimate, score_impact, is_fix_eligible, recommended_action, evidence.
GSC findings (from seo-gsc-insights) additionally include the 8 GSC-specific fields
per rubric.md "Per-finding output shape — GSC additions" (source, impressions, etc.).
Return raw findings only — do NOT format a final report.
```

### Per-subagent additions (do NOT include these in agents that don't consume them):

- **`seo-technical` only** — also pass the **Sitemap URL probe results** (full record list) AND the **Rendered HTML excerpt** if `--url` was provided.
- **`seo-content` only** — also pass the **Rendered HTML excerpt** if `--url` was provided. Do NOT pass probe results (it doesn't use them).
- **`geo-generative`** — base block only. No probe results (doesn't use them); no rendered HTML (JSON-LD lives in source most reliably). Keeps geo-generative's prompt smallest of the three.
- **`seo-gsc-insights`** (only when `gsc_mode: enabled`) — base block only (GSC + git digests are already in the base block). Sitemap URL list from Step 3.2 is passed separately so the agent can compute `traffic_orphan` findings (sitemap URLs not appearing in `performance/pages.csv`).

### Agent 1: seo-technical
Read `references/scan-technical.md`, dispatch `seo-technical` with the file + shared context. Owns Technical SEO (25) + Performance signals (10) = 35 points. Consumes sitemap probe results.

### Agent 2: seo-content
Read `references/scan-content.md`, dispatch `seo-content` with the file + shared context. Owns On-Page SEO (25 points). Uses rendered HTML if provided.

### Agent 3: geo-generative
Read `references/scan-geo.md`, dispatch `geo-generative` with the file + shared context. Owns Structured Data (20) + Generative Engine (20) = 40 points. Source-only (no rendered HTML).

### Agent 4: seo-gsc-insights (only when `gsc_mode: enabled`)
Read `references/gsc-ingestion.md` (the same reference used by the orchestrator in Step 1.6 — the "Finding-type catalog" section is the agent's spec) and dispatch `seo-gsc-insights` with the reference content + shared context + sitemap URL list. Owns `gsc_insights` dimension with 12 sub-dims and **0 score allocation** (informational by Phase 0 contract). All findings emit `source: "gsc"` and `score_impact: 0`.

When `gsc_mode: disabled`, do not dispatch the 4th agent — only dispatch 3.

---

## Step 6 — Consolidate + Score

After all subagents return (3 by default, 4 when GSC mode enabled):

### 6.0 — GSC consolidation passes (only when `gsc_mode: enabled`)

When a 4th `seo-gsc-insights` subagent was dispatched, run these three passes **before** the existing aggregation. Each is a no-op under `gsc_mode: disabled` (no source-tagged findings to act on), so the order of operations stays the same regardless of mode.

**a) Score-impact enforcement.** For every finding with `source == "gsc"`, force `score_impact = 0`. Single point of enforcement per `references/rubric.md` "Score-impact invariant" — the subagent may emit non-zero by mistake; orchestrator overrides. Heuristic findings (`source == "heuristic"`) are untouched.

**b) URL dedup pass.** Build a normalized-URL index of probe `url_health` findings: `{normalize(url) → probe_finding}` where `normalize` lowercases + strips trailing slash. Then walk GSC `not_found_404` and `redirect_hygiene` findings; lookup each by `normalize(its_url)`. On match:
- Drop the GSC finding from the findings list.
- Add to the probe finding's record: `gsc_corroborated: true`, plus carry `gsc_recent_commits: [...]` from the GSC finding's `recent_commits` field when present.
- Sub-dim attribution stays with the probe finding — `technical_seo.url_health` is the source of the non-zero score_impact, so dedup never loses score signal.

**c) gsc_findings count.** Aggregate `gsc_findings_count = count of findings where source == "gsc"` (post-dedup). Stash for the footer's subtotal-check addendum.

### 6.1 — Aggregate + clamp sub-dimension deductions

Each subagent returns a `sub_dimension_breakdown` map of deductions keyed by sub-dim name. For each sub-dim, **clamp at the sub-dim max** per `references/rubric.md`: `clamped[sub_dim] = min(raw[sub_dim], sub_dim_max)`. The dimension total is then `adjusted_dimension_max - sum(clamped sub_dim deductions)`, floored at 0. Single point of clamp enforcement — subagents may emit raw sums larger than a sub-dim cap (multiple findings in the same sub-dim), and the rubric is canonical here. If a subagent's emitted dimension_total disagrees with the recomputed one, prefer the recomputed value and flag the divergence in the footer.

**Skip the `gsc_insights` dimension** in this pass — it has no score allocation (Phase 0 contract). Its sub-dim breakdown is structural-only and reported in the new Section 3 (`references/report-template.md`).

### 6.2 — Apply weight adjustments

From Step 1's brief (max ±5 per dim, sum delta 0). E.g., if brief bumped Generative Engine +3, `adjusted_dimension_max` becomes 23 and the deduction-from-max is computed against the new max. Sub-dim caps used in 6.1 are the **base** caps from `rubric.md` and are not rescaled by weight adjustments. Weight adjustments never touch `gsc_insights` (no score).

### 6.3 — Verify total = 100

Print a `subtotal_check: <a>+<b>+<c>+<d>+<e>=<total>` line in the footer so any arithmetic drift is visible. When GSC mode is enabled, append `| gsc_findings: <count> (info-only, 0 score impact)` to the same line — visible audit that GSC findings ran without contributing to the score.

### 6.4 — Compute total score

`total = sum(dimension_scores)` across the 5 scoring dimensions (Technical SEO, On-Page, Structured Data, Generative Engine, Performance). `gsc_insights` is excluded by construction.

### 6.5 — Read `docs/seo-history.md`

If it exists, find the most recent entry. Compute `delta = today_score - previous_score`. (History row format with `[gsc]` prefix on GSC-sourced priorities — see 6.6 and the rubric.)

### 6.6 — Rank improvement opportunities

The ranking formula expands when GSC mode is enabled. Reference: `rubric.md` "Traffic-weighted ranking".

**Effort weights** (unchanged): trivial 1, small 2, medium 4, large 8.

```
effective_impact (heuristic) = score_impact
effective_impact (gsc)       = log10(impressions + 1)

traffic_weight (URL in url_impressions_map) = max(1.0, log10(url_impressions + 1))
traffic_weight (URL not in map / no GSC)     = 1.0

rank_score = effective_impact × certainty × traffic_weight / effort_weight
```

**URL resolution for traffic_weight:**
- If the finding's `location` IS a URL → look it up directly in `url_impressions_map` from Step 1.6.
- If `location` is a source file path (e.g., `src/app/layout.tsx:14`) → derive the page URL from the filename via the same page-path heuristics used by `page_type_map` (Step 1.6), then look up.
- No match → `traffic_weight = 1.0`.

**Heuristic-only behavior preserved:** when `gsc_mode: disabled`, `effective_impact == score_impact`, `traffic_weight == 1.0` everywhere, formula collapses to the legacy `score_impact × certainty / effort_weight`. Score history stays comparable across runs.

**Top-3 for headline:** sort all findings (heuristic + GSC, post-dedup) by `rank_score` descending. Take top 3. GSC findings can land in headline because their `rank_score` is non-zero (via the `log10(impressions+1)` effective_impact path).

**[gsc] prefix on history row:** when a top-3 priority string for `docs/seo-history.md` comes from a GSC finding (`source == "gsc"`), prepend `[gsc]` to that priority's short string at history-write time (Step 7 docs/seo-history.md append).

### 6.7 — Drop low-confidence noise

Drop findings with `certainty < 0.5` AND `score_impact < 1` unless `is_fix_eligible: true` (fix-eligible findings surface even at lower confidence so the user can review the diff). **The drop rule applies only to `source == "heuristic"` findings.** GSC findings (`source == "gsc"`) are always retained — including those with `code_changed_since_gsc_window: true` whose certainty was lowered to 0.4 by the agent, since "may already be fixed; re-check next cycle" is exactly the annotation worth surfacing. The filter targets noisy heuristic guesses, not GSC ground-truth signal.

---

## Step 7 — Output

Read `references/report-template.md` for exact formatting. The shape:

**Section 0 — Single headline** (first line of report):

> **SEO/GEO score: 72/100 (Δ +8 since 2026-04-30)** — Top 3 opportunities: missing meta descriptions (12 pages); no llms.txt; broken /products/v1 (404).

If no `docs/seo-history.md` exists yet, drop the delta clause: `**SEO/GEO score: 72/100** — Top 3 opportunities: ...`.

**Sections 1-5** per `references/report-template.md`.

### Append to docs/seo-history.md

**Only in default review-only mode.** Skip the history append entirely when `--plan` or `--fix` is in `$ARGUMENTS` — those are follow-ups to a recent audit, not new audits; writing duplicate score rows pollutes the history with no information gain.

In default mode, after rendering the report, append (or create) `docs/seo-history.md`:

If file doesn't exist, create with header:
```markdown
# SEO/GEO Score History

> Auto-managed by `/seo-review`. Append-only, never delete entries. Each row captures the score + top-3 priorities so progress is visible across runs.

| Date | Score | Top-3 priorities |
|------|-------|------------------|
```

Append row:
```
| 2026-05-14 | 72 | Missing meta descriptions (12 pages); No llms.txt; Broken URL /products/v1 (404) |
```

**Rules for the history file:**
- Create if missing — never assume it exists.
- Append-only — never delete or rewrite past entries.
- Each row always has all 3 columns. If fewer than 3 priorities surfaced, use "-" placeholders.
- Date is `YYYY-MM-DD`.
- This file is in-repo and git-tracked deliberately — the user can see history across machines / commits / team members.

### Mode-specific tail

- `--plan` → read `references/plan-mode-seo.md` and emit 6-phase brief.
- `--fix` → walk findings where `is_fix_eligible: true` per `references/fix-allowlist.md`; per-finding diff preview gate; end with `/rewind` reminder.

---

## Step 8 — Closing

If default mode, end with:

> Run `/seo-review --plan` to convert top findings into a phased rewrite brief, or `/seo-review --fix` for safe-allowlist mechanical fixes (placeholders + TODO markers, never fabricated copy). Run `/seo-review --url https://your-domain.com` to add live HTML diff and sitemap URL probe.

---

## Quick Reference

| Want... | Use... |
|---------|--------|
| Per-commit / diff quality | `/code-review` |
| Dead code, unused deps | `/code-cleanup` |
| Repo-wide architecture audit | `/architecture-review` |
| Repo-wide test suite audit | `/test-review` |
| **Repo-wide SEO + GEO audit (web only)** | **`/seo-review` (this)** |
| Plan a SEO/GEO improvement effort | `/seo-review --plan` |
| Apply safe SEO scaffolds | `/seo-review --fix` |
| Live HTML diff + sitemap URL probe | `/seo-review --url <base>` |
| Not sure where to start | `/code-health-advice` |
