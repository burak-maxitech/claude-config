---
name: seo-review
description: Repo-wide SEO and Generative Engine Optimization audit for web projects. Rejects non-web repos. Fetches current best practices every run (SEO/GEO field evolves rapidly). Probes sitemap URLs for 4xx/5xx/redirect-chain/slow-response health. Optionally ingests Google Search Console data via Bulk Data Export to BigQuery (Performance — queries + pages + per-URL impressions) and/or CSV exports from .seo-data/gsc/ (Page Indexing — all 9 reasons, and Performance fallback when BQ not configured). 4-state matrix governs the mix (BQ + indexing / BQ-only / CSV-only / heuristic-only). Plus 35-day git-history overlap to flag "may already be fixed" against the GSC reporting lag. Three or four parallel Sonnet subagents (seo-technical / seo-content / geo-generative, plus seo-gsc-insights when any GSC data is present). Score stays /100 (purely heuristic) so docs/seo-history.md is comparable across runs regardless of GSC mode. Use when user mentions SEO audit, GEO audit, Generative Engine Optimization, AI search optimization, llms.txt, structured data, sitemap health, Google Search Console, GSC, BigQuery, Bulk Data Export, search performance, or "make this site rank better."
disable-model-invocation: true
allowed-tools: Read, Write, Grep, Glob, Edit, WebSearch, WebFetch, Bash(git:*), Bash(find:*), Bash(wc:*), Bash(jq:*), Bash(cat:*), Bash(head:*), Bash(bq:*), Bash(gcloud:*), Task
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

Steps 1.5 (git scan) and 1.6 (GSC ingestion via the 4-state matrix) have **independent tool calls** that should fire in a **single parallel turn** — not back-to-back sequentially. In one tool-use block, batch:

**Turn 1 — Detection + optimistic Reads:**
- `git rev-parse --is-shallow-repository` (Step 1.5.1)
- `git log --since="35 days ago" --name-status ...` (Step 1.5.3)
- `Glob .seo-data/gsc/**/*.csv` (Step 1.6.1 CSV inventory)
- `Glob .seo-data/gsc/config.yaml` (Step 1.6.1 BQ config presence)
- `Glob .seo-data/gsc/README.md` (Step 1.6.4 idempotency)
- `Read .gitignore` (Step 1.6.4 idempotency)
- `Read references/gsc-setup-readme-template.md` (fire optimistically; discard if README already exists)
- `Read references/gsc-ingestion.md` (always needed when any GSC mode is active — covers BQ subsection + CSV parsing rules + 12 sub-dim catalog)
- `Read .seo-data/gsc/config.yaml` (optimistic; if file doesn't exist, the tool errors silently — interpret as `bq_configured = false`)
- `Read references/bigquery-queries.md` (optimistic; only used when BQ activates — but reading early lets Turn 2 fire bq queries without an extra Read)
- `Bash: bq --version 2>&1` (BigQuery CLI install detection; non-zero exit treated as not-installed)
- `Bash: gcloud auth application-default print-access-token 2>&1` (ADC detection; empty/error output treated as not-authenticated)

Only the **post-tool aggregation** (parsing git log, parsing config.yaml flat keys, resolving the 4-state mode, parsing CSVs or BQ JSON) runs sequentially.

**Turn 2 — Data ingestion** (conditional on Turn 1's mode resolution):
- **If BQ active**: 5 parallel `Bash: bq query ...` calls (Q1-Q5 from `bigquery-queries.md`)
- **If CSV path active**: parallel `Read` on each canonical CSV path the Turn 1 Glob confirmed exists (up to 13 — 2 Performance + 11 indexing)
- **Hybrid (BQ active for Performance, indexing CSVs present)**: 5 BQ queries + 11 indexing CSV Reads — all in the same parallel turn

Without explicit batching, the orchestrator would run ~15+ sequential tool turns for Steps 1.5+1.6. With batching: 2 turns total.

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

## Step 1.6 — GSC Ingestion (4-state matrix dispatcher)

GSC data can arrive via two paths: **BigQuery Bulk Data Export** (Performance only — Google's product limit) and **CSV exports** (the only path for the 9-reason Page Indexing report, and a fallback for Performance when BQ not configured). This step resolves which paths are active and dispatches to the right ingestion logic.

Three reference files cover the implementation:
- `references/gsc-ingestion.md` — canonical digest shapes, CSV parsing rules, BigQuery-→-digest translation contract, 12 sub-dim finding catalog, freshness policy, `.gitignore` auto-append rules
- `references/bigquery-queries.md` — 5 parametrized SQL templates (Q1-Q5)
- `references/bigquery-config-template.md` — flat-YAML config schema + setup walkthrough

### The 4-state matrix

| BQ configured? | Indexing CSVs present? | Performance CSVs present? | Mode label | User-facing warning |
|---|---|---|---|---|
| ✓ | ✓ | (ignored) | **Full GSC** | none |
| ✓ | ✗ | (ignored) | Performance-only | Footer note: `indexing signal missing — drop the 11 indexing CSVs in .seo-data/gsc/indexing/ for cluster detection` |
| ✗ | ✓ | ✓ | CSV-only (v2 path) | Footer note: `Performance limited to ~1,000 rows — enable BigQuery Bulk Data Export for full coverage. See .seo-data/gsc/README.md.` |
| ✗ | ✓ | ✗ | Indexing-only | Footer note: `Performance signal missing — enable BigQuery OR drop performance/queries.csv + pages.csv` |
| ✗ | ✗ | ✓ | Performance-CSV-only | Footer note: `indexing missing + Performance limited — see .seo-data/gsc/README.md` |
| ✗ | ✗ | ✗ | **Heuristic-only** | Section 1 banner: `⚠ No GSC data — code-only review. Recommendations cannot be traffic-prioritized.` |

When BQ is configured AND a Q1-Q5 query fails at runtime: NO silent CSV fallback (per locked decision 10). Print the `bq` error in the footer, skip the Performance signal, and the matrix reads as if Performance source is missing. See `gsc-ingestion.md` "BQ-configured-and-failing — NO silent CSV fallback" for the rationale.

### 1.6.1 — Detection (Turn 1, joins Step 1.5's parallel batch)

All GSC-related tool calls listed in the "Parallel-batch note" above (CSV Glob, config.yaml Glob + optimistic Read, README + .gitignore + template Reads, bigquery-queries.md + gsc-ingestion.md reference Reads, `bq --version`, `gcloud auth application-default print-access-token`) fire in Turn 1 alongside Step 1.5. After the batch returns, parse the results into:

| Variable | Source | True/false condition |
|---|---|---|
| `perf_csvs_present` | Glob `.seo-data/gsc/performance/*.csv` | ≥1 of `queries.csv` or `pages.csv` |
| `indexing_csvs_present` | Glob `.seo-data/gsc/indexing/*.csv` | ≥1 indexing CSV |
| `config_yaml_present` | Read `.seo-data/gsc/config.yaml` | Read succeeded (non-error result) |
| `bq_cli_installed` | `bq --version` exit + stdout | stdout contains a version string (regex `\d+\.\d+`) |
| `adc_authenticated` | `gcloud auth application-default print-access-token` | stdout non-empty AND no `ERROR:` line |

### 1.6.2 — Parse config.yaml and resolve `bq_configured`

When `config_yaml_present`, parse the file's content (already Read in Turn 1) via line-by-line walk:

1. Reject nested keys: any line matching `^\s+[a-z_]+:` (leading whitespace before key) → emit `Config error: nested keys not supported in .seo-data/gsc/config.yaml — use flat top-level keys only.` and set `bq_configured = false`. Skip rest of parse.
2. Extract flat keys: lines matching `^([a-z_]+):\s*(.*)$` (no leading whitespace). Build `config: {key: value, ...}`.
3. Validate required keys: `project_id`, `dataset_id`, `location` must all be present and non-empty after trimming. If any missing → `bq_configured = false`, log per-key reason in footer (`Config warning: required key '<X>' missing or empty`).
4. Warn on unknown keys (not in `{project_id, dataset_id, location, site_url, lookback_days}`): log `Config warning: unknown key '<X>' — ignored.`
5. Default `lookback_days = 90` when omitted. Validate range [7, 365] when present.

If all checks pass: `bq_configured = true`.

### 1.6.3 — Resolve 4-state mode

```
bq_active            = bq_configured AND bq_cli_installed AND adc_authenticated
perf_source          = "bigquery" if bq_active else ("csv" if perf_csvs_present else "none")
indexing_source      = "csv" if indexing_csvs_present else "none"
gsc_mode             = "enabled" if (perf_source != "none" OR indexing_source != "none") else "disabled"
```

**Mode-label string** (used by Step 0 detected-line + Step 7 footer):

| `(perf_source, indexing_source)` | `mode_label` |
|---|---|
| `("bigquery", "csv")` | `Full GSC (BigQuery + indexing CSVs)` |
| `("bigquery", "none")` | `BigQuery Performance only (indexing missing)` |
| `("csv", "csv")` | `CSV-only (v2 path)` |
| `("csv", "none")` | `CSV Performance only (indexing missing)` |
| `("none", "csv")` | `Indexing-only (Performance missing)` |
| `("none", "none")` | `heuristic-only` |

Stash `gsc_warning_text` per the matrix table above. Empty string when no warning.

### 1.6.4 — Heuristic-only fast-path (gsc_mode == "disabled")

When `gsc_mode == "disabled"`:

1. Check sentinel `.seo-data/.gsc-banner-shown`. If **absent**: emit the unified setup banner (see `gsc-ingestion.md` "Setup banner — unified BQ + CSV"). Touch the sentinel (`Write` empty file).
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

Notice the block also covers `config.yaml` (under `.seo-data/gsc/`) — BQ config contains `project_id` which is non-secret but project-identifying, so the default of "don't commit" is right. If `.gitignore` doesn't exist, create it with the sentinel block. Print `Added .seo-data/gsc/ to .gitignore (sentinel-marked block).` on first append; silent thereafter.

### 1.6.6 — Data ingestion (Turn 2, parallel batch)

Per the matrix's `(perf_source, indexing_source)` resolution, fire a single parallel batch:

**When `perf_source == "bigquery"`** — fire **5 parallel `Bash: bq query` calls** using the templates from `references/bigquery-queries.md` (already Read in Turn 1). Substitute placeholders per the parsed `config`:

```
bq query \
  --use_legacy_sql=false \
  --maximum_bytes_billed=1000000000 \
  --format=json \
  --location=<config.location> \
  '<SQL with <<PROJECT>>, <<DATASET>>, <<LOOKBACK_DAYS>> substituted>'
```

Run Q1 (queries digest), Q2 (pages digest), Q3 (url_impressions_map), Q4 (orphan candidates — can be elided since Q3's keys serve), Q5 (freshness probe).

**When `perf_source == "csv"`** — fire parallel `Read` on `.seo-data/gsc/performance/queries.csv` and `pages.csv` (whichever the Glob confirmed exist).

**When `indexing_source == "csv"`** — fire parallel `Read` on each canonical indexing CSV path the Glob confirmed exists (up to 11 files).

All of the above fire in the **same parallel turn** — one tool-use block containing the mix of bq queries + CSV Reads dictated by the active sources. Worst case (Full GSC mode): 5 BQ + 11 indexing CSV Reads = 16 parallel tool calls in 1 turn.

### 1.6.7 — Parse outputs into byte-identical digests

After Turn 2 returns, walk results per `references/gsc-ingestion.md`:

**BigQuery JSON outputs** — translate per `gsc-ingestion.md` "BigQuery ingestion (primary path for Performance) → Digest shape — byte-identical to CSV path":
- Cast every INT64 / FLOAT64 field (returned as quoted JSON string) to JS Number on ingest
- Map BQ field names → digest field names (e.g., `avg_position` → `position`)
- Top-50 ordering already enforced server-side via `LIMIT 50` in Q1/Q2
- Build `url_impressions_map` from Q3's uncapped output

**CSV outputs** — parse per `gsc-ingestion.md` "Parsing rules" (BOM strip, header validation, quoted-comma handling, CTR `%`-strip and `/100`, position float-parse).

**Failure modes** (all log to footer, never block):
- BQ query fails → `bq_query_failed: true`, footer captures stderr verbatim, that signal skipped (no CSV fallback)
- BQ schema drift (column not found error) → footer note pointing to `bigquery-schema.md` for re-validation
- Unknown CSV path → `unknown CSV ignored: <path>`
- Missing required CSV header → `CSV skipped: <path> — expected <X>, detected <Y>`
- Malformed CSV rows → `malformed_rows: <count>` per file

Track `total_count` per cluster source (BQ Q1/Q2 truncate at 50 server-side; indexing CSVs may have unbounded source rows).

### 1.6.8 — Build cross-subagent maps

After all parsing complete (single source produces both):

- **page_type_map**: `{url → page_type}` over the union of URLs from Q2 / `performance/pages.csv` digest (whichever was active — top-50 only, NOT Q3's uncapped map) + any indexing CSV digests + sitemap URLs (Step 3.2). Classification per `gsc-ingestion.md` "page_type_map building".
- **url_impressions_map**: `{url → impressions}` — from Q3's uncapped output when BQ active, or from `performance/pages.csv` digest when CSV active. Passed to all subagents in Step 6 ranking (`rubric.md` "Traffic-weighted ranking").

### 1.6.9 — Freshness check (source-dependent)

**BigQuery path:** consume Q5's `latest_data_date`. Compute `days_old = today - latest_data_date`. Thresholds from `gsc-ingestion.md` "Freshness policy (BQ-specific)".

**CSV path:** per-file `mtime` → `days_old`. Same `<30 / 30-90 / >90` thresholds.

Never block on freshness. Note the GSC pipeline normally lags real-time by ~2 days — `days_old: 2` is fresh.

### 1.6.10 — Compute mode summary fragment (consumed by Step 0)

Build the GSC-mode fragment for Step 0's detected-stack line per `mode_label` from 1.6.3:

| `mode_label` | Step 0 fragment example |
|---|---|
| Full GSC | `Mode: heuristic + GSC (BigQuery: 47 days data, 2,445 URL rows; 7/11 indexing CSVs; freshness OK)` |
| BigQuery Performance only | `Mode: heuristic + GSC (BigQuery Performance only — drop indexing CSVs for cluster detection)` |
| CSV-only (v2) | `Mode: heuristic + GSC (CSVs only — 13 files; freshness OK; enable BigQuery for full Performance coverage)` |
| Indexing-only | `Mode: heuristic + GSC (indexing CSVs only — enable BigQuery OR drop performance/*.csv)` |
| CSV Performance only | `Mode: heuristic + GSC (Performance CSVs only — indexing missing)` |
| heuristic-only | `Mode: heuristic (no GSC data — see one-time setup banner above)` |

### 1.6.11 — Pass to all dispatched subagents (Step 5 shared context)

The orchestrator's Step 5 shared-context block (passed to all subagents) gains a GSC section:

```
GSC Mode: <mode_label from 1.6.3>
Performance source: <bigquery | csv | none>
Indexing source: <csv | none>

When perf_source or indexing_source != "none":
- Sources detected:
    - BigQuery: project=<x> dataset=<y> location=<z> lookback_days=<N>, latest_data_date=<YYYY-MM-DD> (Q5)
    - CSVs: <list of canonical paths present>
- Digests (byte-identical shape regardless of source — see gsc-ingestion.md):
  - queries digest: <top-50 records {query, impressions, clicks, ctr, position}>
  - pages digest: <top-50 records {url, impressions, clicks, ctr, position}>
  - indexing/summary digest: <full table, ≤11 rows>  ← CSV-sourced when indexing present
  - indexing/<reason> digests: <top-50 by last_crawled desc>, total_count=<N>  ← CSV-sourced
- page_type_map: {<url>: <page_type>, ...}
- url_impressions_map: {<url>: <impressions>, ...}   ← used for traffic_weight lookups
- Freshness summary: [{source, days_old}, ...]
- Malformed rows: {<file>: <count>} (omit when all zero)
- BQ query failures: [...] (omit when none)
- Unknown CSVs ignored: [<paths>] (omit when empty)

When both perf_source AND indexing_source == "none":
- gsc_mode: disabled
- Reason: "no .seo-data/gsc/" | "no BQ config + no CSVs"
```

**Primary consumer:** `seo-gsc-insights` subagent (dispatched as 4th parallel Task in Step 5 when `gsc_mode: enabled`). Other 3 subagents use `url_impressions_map` for traffic_weight when ranking their own findings; the rest is informational.

Subagents do NOT need to know which source produced the digest — the contract from `gsc-ingestion.md` guarantees byte-identical shape across paths.

### 1.6.12 — Footer addition

Append to Step 5's footer (after the Step 1.5.7 git-history line):

```
GSC mode: <mode_label from 1.6.3>. Performance source: <bigquery | csv | none>. Indexing source: <csv | none>.
<gsc_warning_text from matrix, if non-empty>
<freshness summary, single line>
<BQ query failures verbatim, if any — one line per failed query>
```

In heuristic-only mode, render only the first line: `GSC mode: heuristic-only. Performance source: none. Indexing source: none.` — the Section 1 banner carries the user-facing call to action; the footer line is a machine-readable audit record.

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
