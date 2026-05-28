---
name: seo
description: Audits a web project for SEO and Generative Engine Optimization (GEO). Fetches current best practices every run, probes sitemap URL health, and optionally ingests Google Search Console data via API. Score `/100` headline + top-3 priorities, tracked in `docs/seo-history.md`.
when_to_use: When user mentions SEO audit, GEO audit, Generative Engine Optimization, AI search optimization, llms.txt, structured data / JSON-LD, sitemap health, Google Search Console, GSC, search performance, AI citability, or "make this site rank better". Web projects only — rejects non-web repos silently. Distinct from generic code-review skills (no SEO awareness) and from `/bx:arch` (code structure, not SEO).
disable-model-invocation: true
allowed-tools: Read, Write, Grep, Glob, Edit, WebSearch, WebFetch, Bash(git:*), Bash(find:*), Bash(wc:*), Bash(grep:*), Bash(sed:*), Bash(cat:*), Bash(head:*), Bash(gcloud:*), Bash(curl:*), Task
effort: high
argument-hint: "[path] [--plan] [--fix] [--url <deployed-url>] [--no-cache]"
---

# SEO Review — Repo-Wide SEO + Generative Engine Optimization Audit

Audit a web project for SEO and Generative Engine Optimization (GEO — optimizing for AI search like ChatGPT, Perplexity, Claude, Google AI Overviews) health. The field evolves fast, so this skill **fetches current best practices fresh on every run** rather than relying on bundled static guidance.

This skill is web-projects-only. Step 0 detects web-project state and exits silently on non-web repos — there's nothing to do.

Distinct from existing review skills:

- **`/code-review`** / **`/bx:review`** — diff/commit scope, no SEO awareness
- **`/bx:arch`** — code structure, not SEO
- **`/bx:tests`** — test suite health, not SEO
- **`/bx:health`** — routing advisor; routes to `/bx:seo` when web project detected
- **`/bx:seo` (this)** — repo-wide SEO + GEO audit with live sitemap URL health check

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

> Not a web project (no frontend framework, static HTML, or server-rendered templates detected). /bx:seo only audits web projects. Exiting.

and stop the skill cleanly.

**Otherwise, print the detected stack in one line.** The line includes the GSC-mode summary computed in Step 1.6 (one of two outcomes: API enabled, or heuristic-only). Examples:

> Detected: Next.js 14 app-router project, TypeScript, with sitemap.xml at /public/sitemap.xml and i18n via next-i18next. Mode: heuristic + GSC (Search Console API — 194 URLs inspected, 3 perf queries). Use `--url <base>` for live HTML diff and sitemap URL probe.

> Detected: Hugo static site, no i18n. Mode: heuristic (no GSC data — see one-time setup banner above to enable GSC API).

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

Steps 1.5 (git scan) and 1.6 (GSC API ingestion when configured, else heuristic-only) have **independent tool calls** that should fire in a **single parallel turn** — not back-to-back sequentially. In one tool-use block, batch:

**Turn 1 — Detection + optimistic Reads:**
- `git rev-parse --is-shallow-repository` (Step 1.5.1)
- `git log --since="35 days ago" --name-status ...` (Step 1.5.3)
- `Glob .seo-data/gsc/config.yaml` (Step 1.6.1 config presence)
- `Glob .seo-data/gsc/README.md` (Step 1.6.5 idempotency)
- `Read .gitignore` (Step 1.6.5 idempotency)
- `Read references/gsc-setup-readme-template.md` (fire optimistically; discard if README already exists)
- `Read references/gsc-ingestion.md` (always needed when API is configured — covers API ingestion contract + 14 sub-dim catalog including sub-dim 14 `deindex_regression`)
- `Read .seo-data/gsc/config.yaml` (optimistic; if file doesn't exist the tool errors silently — interpret as `api_configured = false`)
- `Read references/gsc-api-queries.md` (optimistic; only used when API activates — reading early avoids an extra Read in Turn 2)
- `Read references/gsc-api-schema.md` (optimistic; reference for API response parsing)
- `Read references/gsc-cache.md` (optimistic; cache wrapper template + TTL policy used by Turn 2 dispatch)
- `Bash: mkdir -p .seo-data/gsc/cache .seo-data/gsc/snapshots 2>/dev/null; find .seo-data/gsc/cache -type f -name 'sa-*' -mtime +7 -delete 2>/dev/null; find .seo-data/gsc/cache -type f -name 'ui-*' -mtime +14 -delete 2>/dev/null; find .seo-data/gsc/cache -type f ! -name 'sa-*' ! -name 'ui-*' -mtime +7 -delete 2>/dev/null; find .seo-data/gsc/snapshots -type f -mtime +30 -delete 2>/dev/null; ls .seo-data/gsc/cache 2>/dev/null | wc -l; ls .seo-data/gsc/snapshots 2>/dev/null | wc -l` (cache + snapshot dir setup + **two-tier cache prune** (sa-* at 7d, ui-* at 14d — matches the per-prefix TTL with slack; see `references/gsc-cache.md` "Eviction policy") + janitorial prune for orphaned `.tmp.$$` files + snapshot 30-day prune + counts of remaining entries — produces `<N>` for the footer cache stats line and `<M>` for the snapshot count. `mkdir` here is load-bearing — the Turn 2 wrapper assumes both dirs exist and does NOT recreate them per call. See `references/gsc-cache.md` "TTL policy" for the per-prefix split rationale (24h for sa-*, 7d for ui-* — codified after S34 burakarik6 dogfood scored 0/197 cache hits) and `references/gsc-ingestion.md` "Hard rules" for the 30-day snapshot retention rationale.)
- `Glob **/sitemap.xml` + `Glob **/sitemap_index.xml` (sitemap location detection — both probed in parallel so Turn 1 can begin Read'ing the right file in Turn 1.5 if found. Search paths: repo root, `public/`, `static/`, `dist/`, `out/`, `_site/`. Used by Step 1.6.6 Turn 2b URL Inspection sitemap-orphan slice AND by Step 3.2 URL probe — both consume the same parsed URL list, so a single parse is sufficient. If neither Glob finds anything, the sitemap-orphan slice in Turn 2b is skipped silently and Step 3.2 footer-notes "no sitemap.xml — URL probe skipped".)
- `Read .seo-data/gsc/known-bad-urls.txt` (optimistic — the file is user-authored and may not exist; Read errors silently on missing file → `user_supplied_urls` stays empty. When present, parsed in Step 1.6.6's Pre-Turn-2 step into the URL Inspection user-supplied slice — see `references/gsc-api-queries.md` "URL Inspection — selection algorithm" 4-slice mix.)
- `Bash: ls .seo-data/gsc/snapshots 2>/dev/null | sort | tail -1` (find most recent prior snapshot — used by Step 1.6.13.2 regression diff. Empty stdout means "first run for this property", in which case Step 1.6.13 emits no findings and footer-notes the activation.)
- `Read .seo-data/gsc/finding-history.json` (optimistic — file is skill-auto-managed under Group D finding-lifecycle infra; absent on first run. When present, the orchestrator parses `{<hash>: {run_count, first_seen_date, ...}}` and passes the map to Step 7 report rendering so findings with `run_count >= 3` get an escalation hint appended to their `recommended_action`. See Step 6.8 for the write-back step.)
- `Read .seo-data/gsc/watchpoints.json` (optimistic — same as above. When present, the orchestrator invokes `gsc-parse-helper.py watchpoint-check` AFTER Q2 cache lands in Turn 2a (since the check needs the current Q2 pages digest for metric comparison) — see **Step 1.6.14** below for the invocation block. Stash the helper output for Step 7 banner rendering.)
- `Bash: gcloud --version 2>&1` (gcloud SDK install detection)
- `Bash: TOKEN=$(gcloud auth application-default print-access-token 2>&1); ADC_DIR=$(gcloud info --format="value(config.paths.global_config_dir)" 2>/dev/null); QUOTA_PROJECT=$(grep -oE '"quota_project_id"[[:space:]]*:[[:space:]]*"[^"]+"' "$ADC_DIR/application_default_credentials.json" 2>/dev/null | head -1 | sed -E 's/.*"([^"]+)"$/\1/'); echo "TOKEN_LEN:${#TOKEN}"; echo "QUOTA_PROJECT:$QUOTA_PROJECT"; curl -s -w "\nHTTP_STATUS:%{http_code}\n" -H "Authorization: Bearer $TOKEN" -H "x-goog-user-project: $QUOTA_PROJECT" "https://www.googleapis.com/webmasters/v3/sites"` (combined ADC + quota-project + API auth probe in one Bash invocation; orchestrator parses `TOKEN_LEN:`, `QUOTA_PROJECT:`, and `HTTP_STATUS:` to determine ADC + quota project + API reachability. The `x-goog-user-project` header is required on every Search Console API call to bill quota to the user-controlled project; ADC stores the value in `application_default_credentials.json` after `gcloud auth application-default set-quota-project <id>`. Without it, all calls return 403 SERVICE_DISABLED. **Extraction uses `grep -oE` + `sed -E` instead of `jq`** — `jq` isn't on PATH in many bash environments (notably claude-code's Bash on Windows + minimal Linux containers); grep + sed are always available.)

Only the **post-tool aggregation** (parsing git log, parsing config.yaml, resolving API or heuristic mode, parsing sites.list response) runs sequentially.

**Turn 2 — Data ingestion** (only fires when API is active; skipped in heuristic-only mode):
- **Turn 2a — Performance**: 3 parallel `Bash: curl ...` calls for Q1+Q2+Q3 from `gsc-api-queries.md`
- **Turn 2b — Indexing**: up to 200 parallel `Bash: curl ...` calls for URL Inspection. URL selection algorithm (per `gsc-api-queries.md`): top 80 by impressions from Q3's `url_impressions_map` + 20 git-changed paths from Step 1.5 + 100 sitemap-orphan URLs (sitemap entries NOT in `url_impressions_map`, sorted document order; deterministic for snapshot regression diff). Dedup precedence: impressions > git > sitemap. Turn 2b runs after Turn 2a since URL selection depends on Q3's `url_impressions_map`.

Without explicit batching, the orchestrator would run ~15+ sequential tool turns for Steps 1.5+1.6. With batching: 3 turns total (Turn 1 detection + Turn 2a Performance + Turn 2b Inspection).

In heuristic-only mode, Step 1.6 finishes after Turn 1 (no data to ingest).

---

## Step 1.5 — SEO-Relevant Change Scan (last 35 days)

Scan git history for SEO-relevant code changes in the last 35 days — roughly the typical Google recrawl + position-stabilization cycle. Produces a ~30-line digest of recent commits + renames + touched files. Used by `seo-gsc-insights` to annotate findings with `code_changed_since_gsc_window`, and by `--plan` Phase 1 to detect routing-rename + 404-cluster co-occurrence (bulk-redirect signal).

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

## Step 1.6 — GSC API Ingestion (binary dispatcher)

GSC data is ingested via the **Search Console API**: `searchanalytics.query` for Performance signal, `urlInspection.index.inspect` per-URL for Indexing signal. Configuration is a single key (`site_url`) in `.seo-data/gsc/config.yaml`. When not configured or unreachable, the skill runs heuristic-only.

Four reference files cover the implementation:
- `references/gsc-ingestion.md` — digest shapes, **14 sub-dim** finding catalog (incl. sub-dim 14 `deindex_regression` for snapshot-diff early warning), `coverageState` → 9-reason lookup, setup banner, `.gitignore` auto-append rules
- `references/gsc-api-schema.md` — Search Console API endpoint inventory, auth/scope, quota model, `coverageState`/`pageFetchState` enums
- `references/gsc-api-queries.md` — 3 parametrized `curl` templates (Q1/Q2/Q3) + URL Inspection per-URL template + URL selection algorithm + lookup table
- `references/gsc-cache.md` — split-TTL response cache for `searchanalytics.query` (24h on `sa-*`) and `urlInspection.index.inspect` (7d on `ui-*` — coverageState is weeks-stable). Cache wrapper bash template (atomic write, skip-cache-on-non-200, stat portability) for Turn 2a Search Analytics; Turn 2b URL Inspection cache is helper-resident in `gsc-parse-helper.py inspect-batch`. `--no-cache` bypass behavior. Two-tier eviction policy (sa-* at 7d, ui-* at 14d). Footer line format.

### Mode resolution (binary)

| Mode | Condition | User-facing |
|---|---|---|
| **API enabled** | `config.yaml.site_url` set + `gcloud` installed + ADC authenticated + sites.list probe returns 200 with `site_url` in `siteEntry` | Step 0 line shows API mode. Findings include `[gsc]`-prefixed traffic-weighted priorities. |
| **Heuristic-only** | any of: config.yaml missing / `site_url` empty / gcloud not installed / ADC not authenticated / probe fails | Step 0 line shows heuristic mode. Section 1 banner if it's a first encounter. |

When API is configured but a runtime call fails: **NO silent CSV fallback** — print the error to footer, skip that signal, never block. Indexing and Performance signals fail independently (e.g., URL Inspection quota exhaustion doesn't disable Search Analytics).

### 1.6.1 — Detection (Turn 1, joins Step 1.5's parallel batch)

All GSC-related tool calls listed in the "Parallel-batch note" above fire in Turn 1 alongside Step 1.5. After the batch returns, parse the results into:

| Variable | Source | True/false condition |
|---|---|---|
| `config_yaml_present` | Read `.seo-data/gsc/config.yaml` | Read succeeded (non-error result) |
| `gcloud_cli_installed` | `gcloud --version` exit + stdout | stdout contains version string (regex `\d+\.\d+\.\d+`) |
| `adc_authenticated` | combined probe `TOKEN_LEN:` line | `TOKEN_LEN` is a positive integer (token returned, non-empty) |
| `adc_quota_project` | combined probe `QUOTA_PROJECT:` line | the string after `QUOTA_PROJECT:` (empty when `set-quota-project` was never run); cached in shared context for Turn 2 reuse |
| `api_probe_succeeded` | combined probe `HTTP_STATUS:` line + body | `HTTP_STATUS:200` present AND body parses as JSON containing `siteEntry` array |
| `api_probe_response` | same | full JSON body — used in 1.6.3 to check `site_url` membership |

### 1.6.2 — Parse config.yaml and resolve `api_configured`

When `config_yaml_present`, parse the file's content (already Read in Turn 1) via line-by-line walk:

1. Reject nested keys: any line matching `^\s+[a-z_]+:` (leading whitespace before key) → emit `Config error: nested keys not supported in .seo-data/gsc/config.yaml — use flat top-level keys only.` and set `api_configured = false`. Skip rest of parse.
2. Extract flat keys: lines matching `^([a-z_]+):\s*(.*)$`. Build `config: {key: value, ...}`.
3. Warn on unknown keys (not in `{site_url, lookback_days}`): log `Config warning: unknown key '<X>' — ignored.`
4. Default `lookback_days = 90` when omitted. Validate range [7, 365] when present.
5. `api_configured = config.site_url is present AND non-empty after trimming`

### 1.6.3 — Resolve `api_active` and mode

```
api_active = api_configured
           AND gcloud_cli_installed
           AND adc_authenticated
           AND adc_quota_project is non-empty
           AND api_probe_succeeded
           AND <config.site_url appears in api_probe_response.siteEntry[*].siteUrl>
           AND <matched entry's permissionLevel != "siteUnverifiedUser">

gsc_mode = "enabled" if api_active else "disabled"
```

**Probe failure handling** — when `api_configured == true` but `api_active == false`:
- Surface the exact error in footer (parse `error.code` + `error.status` per gsc-api-schema.md):
  - `gcloud_cli_installed == false` → `gcloud SDK not installed. Install: https://cloud.google.com/sdk/docs/install. Then run "gcloud auth application-default login --scopes=https://www.googleapis.com/auth/webmasters.readonly,https://www.googleapis.com/auth/cloud-platform" + "gcloud auth application-default set-quota-project <your-gcp-project>"`
  - `adc_authenticated == false` → `ADC not authenticated. Run "gcloud auth application-default login --scopes=https://www.googleapis.com/auth/webmasters.readonly,https://www.googleapis.com/auth/cloud-platform"`
  - `adc_quota_project` empty → `ADC quota project not set. Run "gcloud auth application-default set-quota-project <your-gcp-project>" — required for Google Cloud APIs to bill quota. Also ensure "gcloud services enable searchconsole.googleapis.com --project=<your-gcp-project>" has been run on that project.`
  - HTTP 401 → `Search Console API auth failed: 401 UNAUTHENTICATED. Re-run "gcloud auth application-default login" with the --scopes flag above (scope likely insufficient).`
  - HTTP 403 + error body mentions "SERVICE_DISABLED" or "quota project" → `Search Console API not enabled on quota project '<adc_quota_project>'. Run "gcloud services enable searchconsole.googleapis.com --project=<adc_quota_project>".`
  - HTTP 403 (other) → `Search Console API access denied: 403 PERMISSION_DENIED. The configured site_url '<X>' isn't accessible by your Google account. Verify property ownership in GSC > Settings.`
  - HTTP 200 but `site_url` not in `siteEntry` → `site_url '<X>' not in your verified GSC properties. Check the exact format at https://search.google.com/search-console > Settings.`
- Fall through to heuristic-only mode for this run.

### 1.6.4 — Heuristic-only fast-path (gsc_mode == "disabled")

When `gsc_mode == "disabled"`:

1. Check sentinel `.seo-data/.gsc-banner-shown`. If **absent**: emit the setup banner (see `gsc-ingestion.md` "Setup banner — Search Console API"). Touch the sentinel.
2. Set `gsc_mode_summary = "heuristic-only"` for Step 0's detected line.
3. Stash `section_1_banner = "⚠ No GSC data — code-only review. Recommendations cannot be traffic-prioritized. See .seo-data/gsc/README.md to enable GSC API audit."` for Section 1 rendering.
4. Skip to Step 2 (Mode Dispatch). No data ingestion needed.

### 1.6.5 — README + .gitignore (idempotent — runs whenever config.yaml exists)

If `.seo-data/gsc/config.yaml` exists (`api_configured == true` OR partial config detected):

**README**: if `.seo-data/gsc/README.md` is absent (from Turn 1 Glob), write the template's content block from `references/gsc-setup-readme-template.md` (extract between `## Template content (begin)` and `## Template content (end)` markers, inner-fenced block). If README exists, discard the optimistic template Read.

**.gitignore**: from the Turn 1 `Read .gitignore` result, Grep for sentinel start marker `# /bx:seo managed`. If absent, append:

```
# /bx:seo managed — do not edit between markers
.seo-data/gsc/
.seo-data/.gsc-banner-shown
# /end /bx:seo managed
```

The block covers `config.yaml` (which contains `site_url` — non-secret but property-identifying). If `.gitignore` doesn't exist, create it with the sentinel block. Print `Added .seo-data/gsc/ to .gitignore (sentinel-marked block).` on first append; silent thereafter.

### 1.6.6 — Data ingestion (Turn 2)

Only fires when `api_active == true`. Skipped in heuristic-only mode.

**Pre-Turn-2 sitemap parse.** Before dispatching Turn 2a/2b, parse the sitemap XML located in Turn 1's `Glob` results. If `Glob **/sitemap.xml` returned a path, issue a single `Read <path>` call (sequential, between Turn 1 aggregation and Turn 2 dispatch — adds one tool turn, cheap). If `Glob **/sitemap_index.xml` returned a path AND `sitemap.xml` did not, Read the index file and follow `<sitemap><loc>` entries to fetch child sitemaps (cap at 5 child sitemaps to avoid runaway). Parse `<url><loc>` entries in document order, build:

- `sitemap_url_list`: ordered list of `<loc>` URLs (preserving document order — required for the deterministic sitemap-orphan slice in Turn 2b URL selection)
- `sitemap_url_set`: a set for O(1) lookup when computing the orphan slice (`url in sitemap_url_set AND url NOT in url_impressions_map`)

Both data structures live in shared context across the rest of Step 1.6 and are also passed to Step 3.2 (URL probe consumes the same parsed list — no re-parse needed).

If no sitemap.xml or sitemap_index.xml was located: both structures stay empty. Turn 2b URL selection skips the sitemap-orphan slice and footer-notes the absence. Step 3.2 URL probe also notes the absent sitemap.

**Pre-Turn-2 known-bad-urls parse.** If Turn 1's optimistic `Read .seo-data/gsc/known-bad-urls.txt` returned content (file exists, non-empty after stripping), parse it line-by-line:

- Split on newlines
- Trim leading/trailing whitespace per line
- Skip lines that are blank OR start with `#` (comment lines)
- Validate each remaining line looks like a URL (`http://` or `https://` prefix — silently drop lines that don't, with a footer note `Skipped N lines from known-bad-urls.txt that didn't look like URLs`)
- Deduplicate (preserve first-occurrence order)
- Take first 100 entries (cap — raised from 50 after the S34 burakarik6 dogfood surfaced ~100-URL paste sizes from GSC validation-failed emails; 100 fits the shared 100-slot bucket cleanly, letting a user with a hot deindex incident paste up to 100 URLs and consume the entire user/orphan bucket without splitting across runs)

**If file content exceeds the 100-entry cap**, emit a top-level banner in the report's Suggested Next Actions section (NOT just a footer note): `⚠ known-bad-urls.txt has <N> URLs; only the first 100 were inspected this run. To process the remaining <N-100>, either re-run /bx:seo after removing the inspected URLs from the file, OR wait a day and re-run (URL Inspection daily quota is 2,000/property — 100/run leaves 1,900 headroom for other usage).` The banner makes the partial coverage explicitly visible — buried in the footer it's easy for the user to miss.

Result: `user_supplied_urls` list, in shared context. Used by Turn 2b URL selection as the 4th URL Inspection slice — see `references/gsc-api-queries.md` "URL Inspection — selection algorithm" 4-slice mix. If the file is absent or all lines are blank/comments, `user_supplied_urls` stays empty; sitemap-orphan claims the full 100-slot bucket in Turn 2b.

**Token + quota-project cache**: Turn 1's probe already produced both. Reuse from shared context across all curl invocations — no new gcloud calls needed in Turn 2:

```
TOKEN  = <from Turn 1 TOKEN_LEN-paired stdout (the token string itself, not the length)>
QUOTA_PROJECT = <from Turn 1 QUOTA_PROJECT: line, validated non-empty in Step 1.6.3>
```

If the Turn 2 dispatch needs to re-fetch (e.g., token approaching 1-hour TTL on long-running flows): re-run the same `gcloud auth application-default print-access-token` + `grep`/`sed` extraction chain from Step 1.6.1. In practice a single run completes in seconds — one Turn 1 fetch is reused.

**Every Turn 2 curl call MUST include both headers:** `Authorization: Bearer $TOKEN` AND `x-goog-user-project: $QUOTA_PROJECT`. Omitting the quota-project header returns 403 SERVICE_DISABLED even when auth is otherwise valid.

**Cache-aware dispatch.** Each curl call wraps in the cache pattern from `references/gsc-cache.md` "Cache wrapper" — 24h TTL, atomic write, skip-cache-on-non-200. The wrapper checks `.seo-data/gsc/cache/<prefix>-<hash>.json` and returns the cached body on hit (printing `CACHE_STATUS:HIT age=<N>s` as first line), else issues a fresh curl and writes the response atomically on HTTP 200 (printing `CACHE_STATUS:MISS http=<code>`). The orchestrator parses the first line for footer stats and treats the rest of stdout as the JSON body. **Cache bypass:** when `$ARGUMENTS` includes `--no-cache`, set `NO_CACHE=1` in the per-call environment before invocation — the wrapper skips the lookup but still writes fresh responses to cache.

**Turn 2a — Performance (3 parallel cache-or-curl calls)** for Q1 (queries digest) + Q2 (pages digest) + Q3 (`url_impressions_map`), using templates from `references/gsc-api-queries.md`. Per-call substitutions: `<<LOOKBACK_DAYS>>`, URL-encoded `site_url` (`:` → `%3A`, `/` → `%2F` per `gsc-api-schema.md`), and the per-Q cache filename prefix (`sa-q1`/`sa-q2`/`sa-q3`). Each call uses the `references/gsc-cache.md` "Cache wrapper" bash block — fully shown there, NOT inlined here. The fresh-path curl inside the wrapper is:

```
curl -s -w '%{http_code}' -o "$TMP" -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-goog-user-project: $QUOTA_PROJECT" \
  -H "Content-Type: application/json" \
  -d '<JSON_BODY>' \
  "https://www.googleapis.com/webmasters/v3/sites/<SITE_URL_ENCODED>/searchAnalytics/query"
```

**Turn 2b — URL Inspection (single helper invocation, internally parallel)** — fires after Turn 2a since URL selection uses Q3's output. Compute the URL inspection budget per `gsc-api-queries.md` "URL Inspection — selection algorithm" (top 80 by impressions from Q3 + 20 git-changed paths from Step 1.5 resolved via `page_type_map` + shared 100-slot bucket of user-supplied URLs from `.seo-data/gsc/known-bad-urls.txt` (up to 100) + sitemap-orphan URLs from the parsed sitemap.xml that don't appear in `url_impressions_map` (sorted document order, filling whatever the user-supplied slice doesn't claim); dedup precedence impressions > git > user-supplied > sitemap-orphan; hard cap 200).

**Canonical dispatch path: single Bash invocation of `gsc-parse-helper.py inspect-batch`.** The helper handles parallel HTTP via `ThreadPoolExecutor` (20 workers — empirically balanced against the API's per-property rate limit), per-URL cache check (7d TTL on `ui-*.json` files since `coverageState` is weeks-stable — see `gsc-cache.md` "TTL policy" for the split-TTL rationale), atomic write via `.tmp` + `os.replace`, and never-cache-non-200. Per-URL cache files match `gsc-cache.md`'s key strategy exactly (`ui-<sha1(site_url|inspection_url)>.json`) — so partial cache hits across runs interoperate cleanly.

```bash
# 1. Write the resolved URL list to system temp — NEVER under .seo-data/gsc/
#    (disk-write boundary; see "Helper script" subsection below).
TMPFILE_URLS=$(mktemp -t gsc-inspect-urls-XXXXXX.txt)
printf '%s\n' "${URL_LIST[@]}" > "$TMPFILE_URLS"

# 2. Dispatch — single Bash call, helper parallelizes internally.
GCLOUD_TOKEN="$TOKEN" \
GCLOUD_QUOTA_PROJECT="$QUOTA_PROJECT" \
NO_CACHE="${NO_CACHE:-0}" \
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
python "${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py" inspect-batch \
  .seo-data/gsc/cache \
  "$CONFIG_SITE_URL" \
  "$TMPFILE_URLS"

rm -f "$TMPFILE_URLS"
```

**Helper output** (machine-parseable, parsed by the orchestrator for footer + Step 1.6.7 cluster aggregation):

```
total_attempted:194
cache_hits:152
cache_misses:42
http_errors:0
--- cluster_counts ---
  submitted_indexed: 104
  not_found_404: 48
  discovered_not_indexed: 17
  ...
--- errors ---           # only when http_errors > 0
  <url>|http=429|<error body excerpt>
  ...
```

The full per-URL cluster classification (with `pageFetchState` joint key per `gsc-api-queries.md` lookup table) happens in Step 1.6.7 via the existing `clusters` subcommand walking `ui-*.json` cache files. The helper's `cluster_counts` preview is `coverageState`-only — sufficient for the footer summary but NOT a replacement for the full classification pass.

**Why a helper subcommand and not N parallel Bash curl calls.** S31 cont.² + S34 dogfoods both surfaced the same failure mode: orchestrators wrote ad-hoc Python scripts (`_parse_clusters.py`, `_inspect_batch.py`) into `.seo-data/gsc/` to bundle the dispatch (perceived as "more efficient than 200 parallel bash invocations" — true, but disk-write-boundary-violating). Shipping the dispatch as a canonical helper subcommand closes the spec-shaped hole that improvisation kept filling. See "Helper script" subsection below for the broader rule.

**Note:** `siteUrl` in the URL Inspection request body is a **raw field** (no URL encoding) — distinct from Search Analytics where it's a path param. The helper handles this internally; orchestrator just passes `$CONFIG_SITE_URL` as the second argument.

**Per-call cache stats capture (Turn 2a Search Analytics only).** For each Q1/Q2/Q3 call, record `cache_status: hit | miss` and `age_seconds` (when hit) from the cache wrapper's first-line output. Aggregate into `{cache_hits, cache_misses, miss_call_tags: [<q-tag>...]}` for the Step 1.6.12 footer line.

**Aggregate cache stats capture (Turn 2b URL Inspection).** The `inspect-batch` helper emits batch-aggregate stats only — no per-URL CACHE_STATUS markers — because per-URL cache decisions happen inside the helper's `ThreadPoolExecutor` workers and aren't surfaced individually (a deliberate trade-off when the helper replaced the prior N-parallel-Bash-curl dispatch — see SKILL.md Step 1.6.6 Turn 2b for the rationale). Parse `cache_hits:N / cache_misses:M / http_errors:E / total_attempted:T` from the helper's stdout and feed those four scalars into the same Step 1.6.12 footer line. `miss_call_tags` is **N/A for URL Inspection** — the footer renders the aggregate count without per-URL tags for this signal (a `miss_call_tags` line for URL Inspection would have to list potentially hundreds of URLs and isn't useful at that scale). _code-review finding #13._

Quota tracking (both tiers): cache hits don't count against the 2,000/day URL Inspection quota — only `cache_misses` consume quota.

Step 1.6 total: 3 turns max (Turn 1 detection + Turn 2a Performance + Turn 2b Inspection). Heuristic-only mode finishes after Turn 1. Full-cache-hit run (all 203 calls served from cache) consumes zero API quota and shaves several seconds off wall time.

### 1.6.7 — Parse outputs into digests

After Turn 2 returns, walk results per `references/gsc-ingestion.md` "API ingestion → Digest shape":

**Search Analytics output (Q1+Q2+Q3)**:
- API returns numeric fields as **native JSON numbers** (no cast needed).
- Map API row fields → digest field names: `keys[0]` → `query` (Q1) or `url` (Q2/Q3); `impressions` / `clicks` / `ctr` / `position` passthrough.
- Apply client-side filters: Q1 keeps `impressions >= 100 AND position BETWEEN 5.0 AND 20.0`; Q2 keeps `impressions >= 10`. Sort by impressions desc, take top 50.
- Q3's full result becomes `url_impressions_map`. **Silent truncation at rowLimit=25000** for sites with >25k URLs (documented in `gsc-api-schema.md`).
- **Cap-hit capture**: for each of Q1/Q2/Q3, record `rows_received` (len of `rows` array) and `rowLimit_requested` (what the call sent). Stash as `{q1: {received, limit}, q2: {...}, q3: {...}}` for Step 1.6.12 footer rendering. Cap-hit = `received == limit`, surfaces as a truncation warning. False-positive case (sample size genuinely equals limit) is accepted — the warning is "likely truncated", actionable as a follow-up pagination probe, not a hard error.

**URL Inspection output**:
- Walk each `inspectionResult.indexStatusResult`, apply the `coverageState` + `pageFetchState` joint lookup table from `gsc-api-queries.md` to assign each URL to a sub-dim 2-9 cluster (or "no finding" / "Other" bucket).
- Carry per-URL diagnostic fields (`lastCrawlTime`, `googleCanonical`, `userCanonical`, `crawledAs`, `indexingState`, `robotsTxtState`) into `evidence` for cluster findings.

**Failure modes** (all log to footer, never block):
- API call returns 4xx/5xx → parse `error.code` + `error.status` per `gsc-api-schema.md`; that signal skipped
- URL Inspection batch returns 429 mid-batch → graceful degrade: stop sending, surface count succeeded vs skipped in footer
- API schema drift (unmapped `coverageState`) → "Other" bucket, footer note

Track `total_count` per cluster source. API path: `total_count` = inspected-URL-count (not site-wide). Sub-dim 1 (`indexing_coverage` site-wide aggregate) is NOT emitted in API-only mode — surface as info-only footer instead.

### 1.6.8 — Build cross-subagent maps

After all parsing complete:

- **page_type_map**: `{url → page_type}` over the union of URLs from:
  - Top-50 URLs from Q2 Pages digest (NOT Q3's uncapped map)
  - Inspected URLs from URL Inspection batch
  - Sitemap URLs (Step 3.2)
  Classification per `gsc-ingestion.md` "page_type_map sources".
- **url_impressions_map**: `{url → impressions}` from Q3's output. Passed to all subagents for `traffic_weight` lookups in Step 6 ranking.

### 1.6.9 — Freshness annotation (API path is real-time)

Set `freshness_summary` to a static footer line:

```
GSC API path: real-time view of GSC's pipeline (typically ~2-day lag from real-world events).
```

No per-source freshness check needed — the API returns the live state of GSC.

### 1.6.10 — Compute mode summary fragment (consumed by Step 0)

| `gsc_mode` | Step 0 fragment example |
|---|---|
| `enabled` | `Mode: heuristic + GSC (Search Console API — 194 URLs inspected, 3 perf queries)` |
| `disabled` | `Mode: heuristic (no GSC data — see one-time setup banner above)` |

### 1.6.11 — Pass to all dispatched subagents (Step 5 shared context)

The orchestrator's Step 5 shared-context block (passed to all subagents) gains a GSC section:

```
GSC Mode: <enabled | disabled>

When gsc_mode == "enabled":
- Source: Search Console API (site_url=<x>, lookback_days=<N>)
- Performance: queries digest <top-50 records>; pages digest <top-50 records>
- Indexing: <up to 9 sub-dim clusters from URL Inspection>, each with total_count + affected_urls + per-URL evidence
- page_type_map: {<url>: <page_type>, ...}
- url_impressions_map: {<url>: <impressions>, ...}   ← used for traffic_weight lookups
- URL Inspection: inspected=<N>/<budget>, with diagnostic breakdown
- API call failures: [{endpoint, http_status, error_status}, ...] (omit when none)

When gsc_mode == "disabled":
- gsc_mode: disabled
- (no further fields — subagents have no action to take on the specific blocker; the audit reason lives in Step 1.6.12 footer instead)
```

**Primary consumer:** `seo-gsc-insights` subagent (dispatched as 4th parallel Task in Step 5 when `gsc_mode: enabled`). Other 3 subagents use `url_impressions_map` for traffic_weight when ranking their own findings.

### 1.6.12 — Footer addition

Append to Step 5's footer (after the Step 1.5.7 git-history line):

```
GSC mode: <enabled | disabled>. <source detail when enabled>
<freshness line — "real-time view of GSC's ~2-day-lagged pipeline" when enabled; absent when disabled>
<URL Inspection status when api active — "Inspected N/M URLs; quota remaining ~Y/2000 today">
<GSC API cache when api active — see "Cache stats line" below>
<Search Analytics rows when api active — "Search Analytics rows: Q1 <N1>/<L1>, Q2 <N2>/<L2>, Q3 <N3>/<L3> (rowLimit cap). ✓ no truncation" OR "⚠ Q<X> hit rowLimit cap — likely truncated; consider raising rowLimit or paginating with startRow for fuller coverage. Q3 cap-hit affects url_impressions_map completeness → URLs outside top-25k get traffic_weight=1.0 fallback in Step 6.6 ranking">
<API call failures, if any — one line per failed call with HTTP status + error_status>
```

**Cache stats line — canonical example** (full variant set in `references/gsc-cache.md` "Footer line" — full-hit / partial-hit / full-miss / bypass forms):

```
GSC API cache: 83/103 hits (24h TTL; 20 fresh calls — typically new URLs from this run's git scan). Use --no-cache to force refresh.
```

**Search Analytics row line — examples:**

Healthy (no truncation):
```
Search Analytics rows: Q1 1304/25000, Q2 1304/25000, Q3 1304/25000 (rowLimit cap). ✓ no truncation.
```

Suspicious (orchestrator improvised to API default of 1000, OR site has exactly 1000 unique queries):
```
Search Analytics rows: Q1 1000/1000, Q2 1000/1000, Q3 1304/25000 (rowLimit cap). ⚠ Q1+Q2 hit rowLimit cap — likely truncated. If site has ≤1000 unique queries/pages this is genuine; otherwise raise rowLimit in the request body or paginate with startRow.
```

Truncated url_impressions_map (large site):
```
Search Analytics rows: Q1 18400/25000, Q2 25000/25000, Q3 25000/25000 (rowLimit cap). ⚠ Q2+Q3 hit rowLimit cap — likely truncated. Q3 truncation affects url_impressions_map completeness → URLs outside top-25k by impressions get traffic_weight=1.0 fallback in Step 6.6 ranking (rankings still work but lose some traffic-prioritization signal). Pagination via startRow not yet implemented; revisit when a dogfood surfaces this on a real site.
```

In heuristic-only mode, render only: `GSC mode: disabled. Reason: <blocker from 1.6.3>.` — the Section 1 banner carries the user-facing call to action; the footer line is a machine-readable audit record. No cache stats line in heuristic-only mode (nothing to cache).

Quota tracking is approximate (the API doesn't expose a precise counter — back-of-envelope: `2000/day per property minus cache_misses this run`). Cache hits do NOT consume quota and should not be counted toward the daily total.

### 1.6.13 — Snapshot write + regression diff (sub-dim 14 emission)

Only fires when `api_active == true` AND Turn 2b URL Inspection produced ≥1 result. The early-warning loop that catches deindex events before Google emails the user. See `references/gsc-ingestion.md` sub-dim 14 (`deindex_regression`) for the finding shape and transition table.

#### 1.6.13.1 — Write current run's snapshot

After Turn 2b parsing completes (Step 1.6.7's URL Inspection output walk), the orchestrator has the cache directory full of `ui-<hash>.json` files for this run. Write a snapshot via the helper:

```bash
RUN_TIMESTAMP=$(date -u +%Y-%m-%dT%H%M%S)
COMMIT_SHA7=$(git rev-parse --short HEAD 2>/dev/null || echo "no-git")
SNAPSHOT_PATH=".seo-data/gsc/snapshots/${RUN_TIMESTAMP}-${COMMIT_SHA7}.json"

PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python "${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py" \
  snapshot-write \
  .seo-data/gsc/cache \
  "$RUN_TIMESTAMP" \
  "$COMMIT_SHA7" \
  "$CONFIG_SITE_URL" \
  "$SNAPSHOT_PATH"
```

The helper walks all `ui-*.json` in the cache dir, extracts `{inspectionUrl: coverageState}` pairs, wraps with metadata (`run_timestamp`, `commit_sha`, `site_url`, `lookback_days`), and writes atomically. Schema documented in `references/gsc-parse-helper.py` `snapshot-write` subcommand.

Failure handling: if the helper exits non-zero (e.g., empty cache dir, write permission failure), footer-note `Snapshot write failed: <reason>. Regression detection skipped this run; subsequent runs will compare against the prior snapshot.` and continue. Never block.

#### 1.6.13.2 — Find previous snapshot

Turn 1's batch already produced the most-recent prior snapshot filename (via `ls .seo-data/gsc/snapshots | sort | tail -1`). After Step 1.6.13.1 wrote the new snapshot, the orchestrator now picks the **second-most-recent** entry to use as the prior snapshot for diffing. From shared context:

```
PREV_SNAPSHOT_FILE = <output of: ls .seo-data/gsc/snapshots | sort | tail -2 | head -1>
```

When `PREV_SNAPSHOT_FILE` is empty (this is the first snapshot ever written for the property): set `regression_mode = "first_run"`, skip Step 1.6.13.3, emit footer line `Index Coverage snapshots: first run for this property. Regression detection activates on next /bx:seo run.` and proceed to Step 2.

When `PREV_SNAPSHOT_FILE` equals current snapshot's filename (orchestrator just wrote a new snapshot AND it's the only file): same first-run handling — Turn 1's `ls | sort | tail -1` ran BEFORE the new snapshot was written, so a second-most-recent file genuinely doesn't exist.

#### 1.6.13.3 — Run regression diff

```bash
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python "${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py" \
  regression \
  "$SNAPSHOT_PATH" \
  ".seo-data/gsc/snapshots/$PREV_SNAPSHOT_FILE"
```

The helper emits machine-parseable output:

```
transitions_total:<N>
critical_transitions:<count of Submitted-indexed → 5xx>
high_transitions:<count of other negative transitions>
recoveries:<count of any → Submitted-indexed>
no_change_count:<count of URLs unchanged>
previous_run_date:<YYYY-MM-DD>
previous_commit:<sha7>
current_commit:<sha7>
--- transitions ---
<url>|<prev_state>|<current_state>|<transition_class>
...
--- path_clusters ---
<prefix>|<count>
...
--- count_deltas ---
<coverage_state>|<previous_count>|<current_count>|<delta>
...
```

#### 1.6.13.4 — Emit sub-dim 14 finding (when transitions detected)

When `transitions_total > 0`, the orchestrator constructs a sub-dim 14 finding per `references/gsc-ingestion.md` sub-dim 14 entry (severity, certainty, evidence schema, recommended_action tiers). Cross-link to related findings in this run's pool:

- When `Page with redirect` transitions present → cross-link to sub-dim 5 (`redirect_hygiene`) finding (the locale-prefix-cluster diagnosis is in sub-dim 5)
- When `Not found (404)` transitions present → cross-link to sub-dim 4 (`not_found_404`) finding
- When `Server error (5xx)` transitions present → cross-link to sub-dim 9 (`server_errors`) finding

Path-cluster evidence: when `path_clusters` output has ≥1 entry, include in evidence + run git-correlation against Step 1.5's digest (for each cluster prefix, scan touched-files list for paths matching the prefix when resolved via `page_type_map`; attach matching commits as `git_correlation` evidence, max 3 commits per cluster).

The finding is added directly to the findings pool used by Step 6 ranking. Source: `"gsc"`. `score_impact: 0` (Step 6.0a enforcement applies as for all GSC findings).

#### 1.6.13.5 — Inflection-point footer lines (independent of finding emission)

When prior snapshot exists, render footer lines for the top-3 reason-category count deltas. Walk `count_deltas` from helper output, take top 3 by absolute delta:

```
Page-with-redirect count: 838 (delta +47 since previous run on 2026-05-13 [commit 5a441d1]). ⚠ Climbing fast — consider running /bx:seo with --plan to triage.
Crawled-not-indexed count: 142 (delta -8 since previous run). Improving.
Not-found-404 count: 23 (delta 0 since previous run). Stable.
```

Warning threshold (⚠): absolute delta ≥ 20 URLs OR relative delta ≥ 10% of prior count. Below threshold: render without warning.

Recovery footer line (when `recoveries > 0`):

```
Index Coverage recoveries: <N> URLs returned to "Submitted and indexed" since previous run. ✓
```

Snapshot stats footer line (always rendered when prior snapshot exists):

```
Index Coverage snapshots: 1 written (.seo-data/gsc/snapshots/<filename>); 7 retained (30-day rotation); compared against <previous filename>.
```

#### 1.6.13.6 — Same-commit dedup interaction

If the same-commit dedup rule in Step 7 (history append) skips writing a new `docs/seo-history.md` row because the previous run was on the same commit, the snapshot is **still written** (Step 1.6.13.1 doesn't dedup by commit — every run writes its own snapshot). Regression diff in Step 1.6.13.3 compares against the prior snapshot regardless of commit. This is correct: the snapshot is a coverage-state observation at a point in time, not a score audit. Same-commit reruns can still show drift if GSC's pipeline crawled new state between the two runs.

### 1.6.14 — Watchpoint check (Group D — phase-applied recheck banners)

Fires when `api_active == true` AND `.seo-data/gsc/watchpoints.json` is non-empty (parsed in Turn 1's optimistic Read). Must run AFTER Turn 2a so Q2 pages digest is available for metric comparison.

```bash
RUN_DATE=$(date -u +%Y-%m-%d)
# Q2 cache filename: deterministically derived from the Q2 cache key inputs
# (see references/gsc-cache.md "Cache key strategy → Search Analytics").
# DO NOT use `ls sa-q2-*.json | head -1` — multiple sa-q2 files accumulate
# (cache key includes endDate, shifts daily; sa-* eviction at 7d) and `ls`
# sorts by sha1 filename, picking a random old file rather than today's.
# _code-review finding #1._
LOOKBACK_DAYS="${LOOKBACK_DAYS:-90}"
END_DATE=$(date -u +%Y-%m-%d)
START_DATE=$(date -u -d "${LOOKBACK_DAYS} days ago" +%Y-%m-%d 2>/dev/null || \
             python -c "import datetime; print((datetime.date.today() - datetime.timedelta(days=${LOOKBACK_DAYS})).isoformat())")
Q2_KEY="${CONFIG_SITE_URL}|${END_DATE}|${START_DATE}|page|25000|web"
Q2_HASH=$(printf '%s' "$Q2_KEY" | sha1sum | cut -d' ' -f1)
Q2_CACHE_FILE=".seo-data/gsc/cache/sa-q2-${Q2_HASH}.json"

PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python "${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py" \
  watchpoint-check \
  .seo-data/gsc/watchpoints.json \
  "$Q2_CACHE_FILE" \
  "$RUN_DATE"
```

(The `date -u -d "N days ago"` form is GNU-find specific; the `python -c` fallback covers BSD/macOS where `-d` semantics differ. `sha1sum` is portable; on macOS use `shasum` if `sha1sum` is unavailable: `printf '%s' "$Q2_KEY" | shasum | cut -d' ' -f1`.)

The helper:
- Auto-evicts watchpoints older than 90 days (writes the trimmed file back).
- For each remaining watchpoint past its `expected_recheck_date`, compares baseline metric (impressions/ctr/position from the apply-time finding) against current Q2 data for the same URL.
- Emits machine-parseable `due` records with `status ∈ {improved, unchanged, regressed, no_data}` (see helper docstring).

**Orchestrator behavior**:
- Parse `watchpoints_active`, `watchpoints_due`, `watchpoints_evicted` for the footer line.
- Stash `due` records for Step 7 banner rendering (one banner per `due` watchpoint in Suggested Next Actions — see Step 7 "Watchpoint banner format").
- When `watchpoints_due == 0`, no banners; footer-line still emits the active count.

**No-prior-watchpoints case**: file absent or empty `watchpoints` array. Helper emits `watchpoints_active:0 / watchpoints_due:0 / watchpoints_evicted:0` and exits cleanly. Orchestrator skips Step 7 banner rendering for watchpoints.

**Footer line** (always rendered when api_active):

```
Watchpoints: 3 active (1 due this run, evaluated against Q2 pages digest); 0 evicted (90-day rotation).
```

---

## Ingestion conventions (cross-cutting, applies to Step 1.6 + Step 3.2)

Three rules the orchestrator must follow when ingesting external data. Surfaced from S30 dogfood (the first end-to-end run): the model improvised in three ways that the original spec under-specified.

### Disk-write boundary

`.seo-data/gsc/` is reserved for **user configuration + skill-auto-generated content only**:

- `config.yaml` (user-authored)
- `known-bad-urls.txt` (user-authored — optional; one URL per line, `#` comments allowed; up to 100 inspected per run as the 4th URL Inspection slice — see `references/gsc-api-queries.md` "URL Inspection — selection algorithm". Use this to paste specific problem URLs from GSC's "Not found (404)" / "Page with redirect" / "Validation failed" coverage exports that aren't in current sitemap/impressions/git. **Critical caveat:** sitemap-orphan slice only catches deindexed URLs that are STILL in your sitemap. If your codebase actively rotates deindexed URLs out of `sitemap.xml` (the right thing to do!), sitemap-orphan misses them — those need to be pasted into `known-bad-urls.txt` explicitly. The "404-only, redirects dropped" guidance from S34 cont. assumed in-sitemap redirects; revise per workflow.)
- `README.md` (skill-auto-written on first detection)
- `cache/` (skill-auto-managed; **TTL'd API response cache** — see `references/gsc-cache.md`)
- `snapshots/` (skill-auto-managed; **30-day coverage-state history** for sub-dim 14 regression detection — see `references/gsc-ingestion.md` sub-dim 14 + SKILL.md Step 1.6.13)
- `finding-history.json` (skill-auto-managed; **per-finding run_count tracker** for Group D stale-finding escalation — written by `gsc-parse-helper.py history-update` after Step 6 score consolidation. When a finding's `run_count >= 3` and the underlying location/sub_dim hasn't changed, the orchestrator appends an escalation hint to `recommended_action` urging external action or severity reassessment. See Step 6.8 for the integration. Auto-evicted entries: none — the file grows slowly (~1 entry per persistent finding) and stable findings ARE the signal worth keeping.)
- `watchpoints.json` (skill-auto-managed; **phase-applied watchpoints** auto-emitted when a finding has `code_changed_since_gsc_window=true` — see `gsc-parse-helper.py watchpoint-emit`. At Step 1.6 Turn 1, watchpoints past their `expected_recheck_date` (applied + 21 days, typical GSC pipeline lag) are checked via `watchpoint-check`; status delta surfaces as a top-level banner in Suggested Next Actions. Auto-evicted after 90 days to prevent unbounded growth.)
- `.gsc-banner-shown` (sentinel — sits in `.seo-data/` not `.seo-data/gsc/`)

The `cache/` subdirectory is the only sanctioned location for persisted API responses. The orchestrator owns its lifecycle (creates on Turn 1, writes via atomic mv in Turn 2, prunes entries >7d at the start of each run). Cache content is reproducible from the API on demand — safe to delete manually.

**Never write raw API responses, parsed JSON, intermediate inspection results, or any other ephemeral data anywhere else under `.seo-data/gsc/`.** When the orchestrator needs short-lived parsing scratch space (e.g., decoding a 200KB JSON body that doesn't belong in cache), write to **system temp** instead:

```
TMPFILE=$(mktemp -t gsc-q1-XXXXXX.json)
curl ... > "$TMPFILE"
# parse...
rm -f "$TMPFILE"
```

`mktemp` resolves to `/tmp/` or `$TMPDIR` on Unix and `%TEMP%` on Windows (via MSYS/git-bash). The temp file is discarded after parsing. The `.seo-data/gsc/` folder stays minimal so users can read it as their config-only space.

### JSON parser fallback chain

The skill doesn't require any specific parser to be installed. Preferred order:

1. **`jq`** — best ergonomics for filters, BUT not on PATH in claude-code's Bash on Windows + many Linux containers
2. **`python`** — invoke via the shipped helper script (see "Helper script" below), NOT via inline heredocs. **Windows note:** prefer `python` over `python3` — on Windows, `python3` frequently resolves to the Microsoft Store install stub which exits non-zero with "Python was not found" output
3. **`python3`** — fallback after `python`
4. **Bash core (`grep -oE` + `sed -E`)** — portable for shallow JSON (top-level string fields), regex extraction only

Detection pattern:

```
PY=$(command -v python 2>/dev/null || command -v python3 2>/dev/null || true)
JQ=$(command -v jq 2>/dev/null || true)
[ -n "$JQ" ] && JSON_PARSER="jq" \
  || { [ -n "$PY" ] && JSON_PARSER="$PY" \
  || { echo "ERR: install jq or python for GSC JSON parsing"; exit 1; }; }
```

Surface the chosen parser in the footer's debug line when ingesting GSC data.

#### UTF-8 enforcement on every Python invocation

**Critical (S31 dogfood fix).** Python 3 on Windows defaults `open()` to charmap encoding, which crashes on UTF-8 content like Turkish characters or the GSC prompt-injection garbage queries (`"do not update memories..."`). The dogfood's Q1 parse died with `UnicodeDecodeError` and cancelled parallel Q2/Q3 calls.

**Two enforcement layers (use both — belt-and-suspenders):**

1. **Env vars on every Python invocation** — preserve across `python -c`, heredocs (if used), and helper scripts. Even when the script declares `encoding='utf-8'` explicitly, stdin/stdout pipes still inherit the charmap default without these:

```bash
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python <script_or_args>
```

2. **Explicit `encoding='utf-8'` on every `open()` inside Python code.** The shipped helper script (`gsc-parse-helper.py`) does this; if you write any other Python that reads cache JSON, mirror the pattern. Never rely on the platform default.

Same class of bug as the S30 `jq`-missing fix — the spec under-specified a platform-dependent default. Codified after S31 caught it.

#### Helper script (don't inline Python heredocs, don't write orchestrator scripts into `.seo-data/gsc/`)

**S31 cont.² dogfood lesson.** Across one run the orchestrator wrote 5+ different inline Python invocations (Q1 parse, Q2 parse, Q3 parse, CTR opportunities, cluster aggregation), each with different bash quoting/escaping strategies. One heredoc failed with `unexpected EOF` (single quotes inside `<<'PY'` block). The fallback was to write `_parse_clusters.py` into `.seo-data/gsc/cache/` — **violating the disk-write boundary** (cache dir is response-JSON-only).

**S34 burakarik6 dogfood lesson (worse instance).** Orchestrator wrote a 396-line `_inspect_batch.py` into `.seo-data/gsc/` to bundle URL Inspection's parallel-curl dispatch + cache-write + snapshot-write into one script (motivated by the perception that 180+ parallel Bash curl calls would be "more efficient than 180 parallel bash calls"). Same root cause: spec under-specified an in-orchestrator implementation, model improvised disk-write. Boundary violation was larger this time (396 lines vs prior ~50).

**Rule (broader than just JSON parsing):** The orchestrator must NEVER write Python, JavaScript, shell, or any other script into `.seo-data/gsc/` for ANY purpose. This includes (non-exhaustive): JSON parsers, parallel-dispatch helpers, snapshot writers, cache eviction helpers, brand-name extractors, one-off analysis scripts. Applies regardless of script size, purpose, or whether it's auto-deleted after use. `.seo-data/gsc/` is the user's config-only workspace; we never leak skill-internal implementation there.

**Canonical paths for orchestrator logic:**

| Need | Canonical path | NOT this |
|---|---|---|
| GSC JSON parsing (Q1/Q2/Q3, clusters, CTR, brand, snapshot, regression) | `${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py` subcommands (see invocation block below) | Inline Python heredocs, `_parse_*.py` scripts in `.seo-data/gsc/` |
| URL Inspection dispatch (Turn 2b) | N parallel `Bash: curl ...` calls in one tool-use block, each wrapped in the `gsc-cache.md` cache pattern | `_inspect_batch.py` or similar orchestrator-written dispatch script |
| Ephemeral scratch parsing (>200KB JSON that doesn't belong in cache) | `mktemp`-style system temp (`mktemp -t gsc-XXXXXX.json`) | Any file under `.seo-data/gsc/` |

**If the helper script doesn't have a subcommand you need (e.g., URL Inspection batch dispatch isn't there as of 2026-05-26):** treat that as a skill-improvement signal, not a license to inline. Surface in the report footer (`gsc-parse-helper.py missing subcommand <X> — used <fallback approach>; file follow-up to extend the helper`) and proceed with the closest approximation that respects the boundary (typically: parallel Bash curl calls). Future helper extension is preferable to repeated boundary violations.

**Helper invocation:** GSC JSON parsing MUST go through the shipped helper at `${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py`. Invoke with subcommand args:

```bash
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python "${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py" q1 .seo-data/gsc/cache/sa-q1-<hash>.json
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python "${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py" q2 .seo-data/gsc/cache/sa-q2-<hash>.json
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python "${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py" q3 .seo-data/gsc/cache/sa-q3-<hash>.json
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python "${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py" ctr .seo-data/gsc/cache/sa-q2-<hash>.json
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python "${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py" clusters .seo-data/gsc/cache
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python "${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py" brand .seo-data/gsc/cache/sa-q1-<hash>.json "Burak Arık"
```

`${CLAUDE_SKILL_DIR}` is a Claude Code string substitution that resolves automatically to the skill's own directory (cross-platform, CWD-independent). No orchestrator-side path resolution needed — works whether the user runs `/bx:seo` from the repo root or any sub-directory of the target project.

If the helper script itself is missing (skill install integrity issue): emit a footer error `gsc-parse-helper.py not found at <path> — GSC parsing aborted, falling back to heuristic-only mode` and continue without GSC findings.

### Budget utilization expectation

When the spec defines a budget (URL Inspection cap = 100, sitemap probe cap = 100), the orchestrator **MUST attempt to fill the budget** when candidates are available. The cap is the ceiling, not the target.

**Common failure mode (S30 dogfood):** orchestrator used 40 URLs for URL Inspection and 13 URLs for sitemap probe despite having 1,304 URLs in the impressions map and 2,895 URLs in the sitemap. The under-utilization wasted ~60% of the diagnostic value of the run.

Rules:
- **Take the literal top-N** by the spec's sort key (impressions desc for URL Inspection, document order or `<priority>` desc for sitemap probe). Apply no additional minimum thresholds, "quality" filters, or "key URLs only" subjective trims.
- If the candidate pool is smaller than the budget (e.g., only 30 URLs have any impressions), take all available and surface the actual count.
- If genuine constraints reduce the budget (quota near-exhaustion, candidate pool actually smaller), surface the REASON in the budget log line.
- "Conservative because the model is uncertain" is NOT a valid reason to under-shoot. Take the full budget; the per-URL findings carry their own certainty.

Footer must include actual / budget counts:
```
URL Inspection: 97/100 attempted (top 80 by impressions + 17 git-resolved; dedup removed 3); 96/97 succeeded; quota remaining ~1904/2000.
Sitemap URL probe: 100/100 attempted (top 100 by document order from 2,895 total sitemap entries); 98/100 succeeded (2 timeouts).
```

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
| `--no-cache` | Bypass the GSC API response cache (24h TTL for sa-* / 7d TTL for ui-*). Forces fresh `searchanalytics.query` + `urlInspection.index.inspect` calls. Fresh responses are still written to cache for next run. Use when iterating on a fix and you need Google's current view, or when you suspect cached data is wrong. See `references/gsc-cache.md` for TTL policy + manual cache management. |
| `--force-dispatch` | Always run the 3 codebase-scanning subagents even when Step 4.5's gating logic would skip them. Use when validating a refactor, taking a second-opinion run, or after updating subagent reference files. Default is "skip when zero non-doc commits since prior snapshot" — see Step 4.5. |

`--plan` and `--fix` are mutually exclusive. If both supplied: "Pick one — `--plan` emits a brief, `--fix` applies edits."

`--no-cache` is compatible with all other flags. No-op when `gsc_mode: disabled` (nothing to cache).

`--force-dispatch` is compatible with all other flags. No-op when Step 4.5 gating would have run full dispatch anyway (the flag is harmless but the footer notes when it was a no-op so the user remembers).

---

## Step 3 — Live HTTP Work (Orchestrator-Only)

**Subagents never make network calls.** All HTTP work happens here.

### 3.1 Single deployed URL (if `--url <base>` provided)

`WebFetch` the URL with a prompt like "Return the full rendered HTML and document the final URL after any redirects." Capture the rendered HTML excerpt. Pass to `seo-technical` and `seo-content` (skip `geo-generative` — JSON-LD lives in source most reliably).

### 3.2 Sitemap URL Health Probe

Runs **always when sitemap.xml exists locally** AND (sitemap URLs are absolute OR `--url <base>` provides a domain to synthesize bases from).

1. **Locate sitemap.xml locally** — **reuse Step 1.6.6's pre-parsed `sitemap_url_list` when GSC mode is enabled** (the parse already happened in Step 1.6 for the sitemap-orphan URL Inspection slice). When GSC mode is disabled OR Step 1.6 didn't run, fall back to the standalone parse here: try in order: repo root, `public/sitemap.xml`, `static/sitemap.xml`, `dist/sitemap.xml`, `out/sitemap.xml`, `_site/sitemap.xml`. Also check for `sitemap_index.xml` — if found, parse it and follow `<sitemap><loc>` entries to find child sitemaps (cap at 5 child sitemaps to avoid runaway).
2. **Parse with Read tool** (not network) — extract `<url><loc>` entries. **Skip when `sitemap_url_list` is already populated from Step 1.6.6** — single-parse contract.
3. **URL list resolution:**
   - If URLs are absolute (start with `http://` / `https://`) → use them as-is.
   - If URLs are relative AND `--url <base>` provided → synthesize: `<base>` + relative path.
   - If URLs are relative AND no `--url` provided → **skip the probe**, add a footer note: "URL probe skipped — sitemap.xml has relative URLs; re-run with `--url <base>` for live URL health check."
4. **Cap at top 100 URLs** by document order (or by `<priority>` descending if present). The cap is the ceiling, not the target — **take the literal top 100** (or all available if fewer). Do not under-sample to a "representative subset" or skip URLs based on perceived non-importance. See "Ingestion conventions → Budget utilization" for the contract.
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

If a path argument was given, scope subagents to that path (only page-template / layout / content files under it). Else apply the standard tier from repo size (read `bx:arch/references/scale-strategy.md` for the formula). For SEO, default cap is files containing HTML-emitting code: page components, layout files, MDX/markdown content, templates.

---

## Step 4.5 — Codebase-Scan Subagent Skip Rule

**Codified after the S34 burakarik6 dogfood** caught the orchestrator improvising a "skip the 3 codebase subagents because nothing changed since last run" decision. The decision was correct (zero non-doc commits since Session 71, two days prior), but the report carried Session 71's per-dim deductions forward as if freshly computed — leaving no audit trail. This section makes the rule explicit + adds the audit-trail requirements that were the actual gap.

### 4.5.1 — Gating conditions (ALL must hold; any failure → full dispatch)

1. **GSC mode is enabled** AND a prior snapshot exists at `.seo-data/gsc/snapshots/*` (computed in Step 1.6.13.2). Without a prior snapshot, there's no baseline to inherit per-dim deductions from — full dispatch required.
2. **Zero code commits in window** affecting the Step 4 scope. Compute via:

```bash
# <PRIOR_SHA> is the commit_sha embedded in the most-recent prior snapshot filename
# (parsed in Step 1.6.13.2).
CODE_COMMITS=$(git log "${PRIOR_SHA}..HEAD" --pretty=format:"%H" -- \
  $(printf '%s ' "${SCOPE_PATHS[@]}") \
  ':(exclude)docs/*' ':(exclude)*.md' ':(exclude)CLAUDE.md' ':(exclude)README.md' \
  ':(exclude)*.txt' 2>/dev/null | wc -l)
```

The `:(exclude)` pathspecs strip pure-doc / pure-config commits that don't affect any subagent's source-scan output. If `CODE_COMMITS == 0`, gating condition 2 holds.

3. **`--force-dispatch` flag NOT in `$ARGUMENTS`.** The flag is the user's escape hatch — "I want a fresh codebase scan even though the gating logic says inherit." Useful for: validating a refactor didn't regress something subtle, sanity-checking after a long absence, second-opinion runs.
4. **`--plan` and `--fix` flags NOT in `$ARGUMENTS`.** Plan + fix modes need the freshest per-finding data possible — they're action-oriented, not audit-oriented. Always full dispatch.

When ALL 4 conditions hold → set `dispatch_mode = "skip_codebase_subagents"` and proceed to Step 4.5.2. Otherwise → set `dispatch_mode = "full"` and skip directly to Step 5.

### 4.5.2 — What runs vs what's inherited (when `dispatch_mode == "skip_codebase_subagents"`)

| Component | Status this run | Source |
|---|---|---|
| Subagent 1 (`seo-technical`) | **SKIPPED** | Per-dim deductions inherited from prior snapshot's run |
| Subagent 2 (`seo-content`) | **SKIPPED** | Per-dim deductions inherited from prior snapshot's run |
| Subagent 3 (`geo-generative`) | **SKIPPED** | Per-dim deductions inherited from prior snapshot's run |
| Subagent 4 (`seo-gsc-insights`) | **RUNS** | GSC data is fresh every run — never inherit |
| Sub-dim 14 (`deindex_regression`) | **RUNS** | Orchestrator-emitted (Step 1.6.13) — always |
| Sitemap URL probe (Step 3.2) | **RUNS** | Cheap and freshness-sensitive |
| URL Inspection (Step 1.6.6) | **RUNS** | Cache-protected; covered by Step 1.6.6 anyway |
| Best-practices brief (Step 1) | **RUNS** | Spec drift is independent of code changes |

**Inheritance source: `docs/seo-history.md`.** Read the row matching `<PRIOR_SHA>` (via the embedded `<!-- commit:abc1234 -->` comment) — it carries the score + top-3 priorities. Those two pieces drive the inherited render. Per-dimension deductions are NOT line-by-line preserved across runs; the inherited report shows totals plus the inheritance markers (see 4.5.3) without re-quoting prior breakdown text. To see prior breakdowns verbatim, the user either consults the saved prior report or re-runs with `--force-dispatch`.

**Design trade-off (explicit).** We could persist per-dim breakdown JSON alongside each snapshot to enable line-by-line inheritance, but that adds new disk-write surface, a new helper subcommand, and a new failure mode (breakdown-file-missing). For the current dogfood pressure (same-commit-with-doc-changes reruns), score + top-3 priorities is enough: the score is comparable, the priorities don't change without code changes. If a future dogfood shows a need for verbatim per-dim breakdown preservation across runs, escalate to a `breakdown-write` helper subcommand then.

### 4.5.3 — Audit-trail requirements (critical — closes the S34 gap)

When inheritance is used, the report's Section 2 score table per-dimension rows MUST be visibly marked. Acceptable forms:

```
| Technical SEO | 21 | 25 | (inherited from 76cdef9 [2026-05-24]) <breakdown line> |
| On-Page SEO   | 16 | 25 | (inherited from 76cdef9 [2026-05-24]) <breakdown line> |
| ...           |    |    |                                                        |
```

Each inherited row's per-dim breakdown text begins with `(inherited from <sha7> [<date>])` followed by the breakdown — no exceptions, even when the breakdown text is identical to the prior run.

**Findings list:** every finding inherited from the prior run carries `source_status: "inherited"`. Findings from `seo-gsc-insights` (Step 5) carry `source_status: "fresh"`. The report doesn't visually distinguish them in the table, but the JSON dump (when emitted) includes the field so downstream tooling can tell.

**Footer line** (always when `dispatch_mode == "skip_codebase_subagents"`):

```
Subagent dispatch: skipped (zero code commits affecting scope since 76cdef9 [2026-05-24, 3 days ago]). Per-dim breakdowns + heuristic findings inherited from that run; GSC + sub-dim 14 + URL probe refreshed this run. Run /bx:seo --force-dispatch to re-scan the codebase.
```

**`docs/seo-history.md` row:** append `[inherited]` suffix to the priorities column so the history is auditable:

```
| 2026-05-27 | 65 | [inherited] [gsc] smartphone CTR catastrophe; [gsc] sister-article CTR opps; [gsc] 48 NEW 404s from known-bad-urls.txt | <!-- commit:76cdef9 inherited_from:5a441d1 -->
```

The `inherited_from:<prior_sha>` HTML comment makes the inheritance chain machine-parseable for future audits. Same-commit dedup (Step 7) still applies — if `HEAD == <PRIOR_SHA>`, no row is appended (the prior row is the canonical record).

### 4.5.4 — Full-dispatch escape hatch

`--force-dispatch` always runs the 3 codebase subagents regardless of gating. Use cases:
- Validating a refactor didn't regress something subtle
- Sanity check after a long absence (>2 weeks since last run on the property)
- Second-opinion run when methodology variance is suspected
- After updating subagent reference files in `references/scan-*.md` (the gating measures source commits, not skill-config commits)

When `--force-dispatch` is passed, the footer reads:

```
Subagent dispatch: full (--force-dispatch override; gating would have permitted skip — zero code commits since <PRIOR_SHA>).
```

This makes the override visible so the user remembers why their run took longer.

---

## Step 5 — Parallel Subagent Dispatch

Launch subagents in a **single turn**. The dispatch count depends on `dispatch_mode` from Step 4.5:

| `dispatch_mode` | `gsc_mode` | Subagents dispatched | Count |
|---|---|---|---|
| `full` | `disabled` | seo-technical + seo-content + geo-generative | 3 |
| `full` | `enabled` | seo-technical + seo-content + geo-generative + seo-gsc-insights | 4 |
| `skip_codebase_subagents` | `enabled` | seo-gsc-insights only | 1 |
| `skip_codebase_subagents` | `disabled` | (never reached — Step 4.5 gating requires `gsc_mode: enabled`) | — |

Mirror `/bx:tests` Step 4 for the parallel-Task dispatch pattern. When `dispatch_mode == "skip_codebase_subagents"`, fire only the single `seo-gsc-insights` Task call — there's nothing to parallelize with.

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

# GSC + git context

GSC Mode: enabled | disabled
[When enabled: full GSC block per Step 1.6.11 spec — source, digests, page_type_map, url_impressions_map, inspection budget. When disabled: just `gsc_mode: disabled` — no further fields; orchestrator-side reason audit lives in footer, subagents don't need it.]

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
- **`seo-gsc-insights`** (only when `gsc_mode: enabled`) — base block only (GSC + git digests are already in the base block). Sitemap URL list from Step 3.2 is passed separately so the agent can compute `traffic_orphan` findings (sitemap URLs not appearing in the Q3 `url_impressions_map`).

### Agent 1: seo-technical
Read `references/scan-technical.md`, dispatch `seo-technical` with the file + shared context. Owns Technical SEO (25) + Performance signals (10) = 35 points. Consumes sitemap probe results.

### Agent 2: seo-content
Read `references/scan-content.md`, dispatch `seo-content` with the file + shared context. Owns On-Page SEO (25 points). Uses rendered HTML if provided.

### Agent 3: geo-generative
Read `references/scan-geo.md`, dispatch `geo-generative` with the file + shared context. Owns Structured Data (20) + Generative Engine (20) = 40 points. Source-only (no rendered HTML).

### Agent 4: seo-gsc-insights (only when `gsc_mode: enabled`)
Read `references/gsc-ingestion.md` (the same reference used by the orchestrator in Step 1.6 — the "Finding-type catalog" section is the agent's spec) and dispatch `seo-gsc-insights` with the reference content + shared context + sitemap URL list. Owns `gsc_insights` dimension with **14 sub-dims** and **0 score allocation** (informational only). All findings emit `source: "gsc"` and `score_impact: 0`. **Note:** the subagent only emits sub-dims 1-13 from API output; sub-dim 14 (`deindex_regression`) is orchestrator-emitted in Step 1.6.13 from snapshot diff and added directly to the findings pool — the subagent never sees regression transitions in its input.

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

### 6.8 — Finding lifecycle update (Group D)

Fires only when `gsc_mode == "enabled"` (heuristic-only mode doesn't run the GSC infra these files live alongside). Updates `finding-history.json` (run-counter increments + stale-finding escalation source) and emits watchpoints for phase-applied findings.

**Step 6.8.1 — Write findings to JSONL temp**. After Step 6.7's filter drops noise, serialize the surviving findings to a newline-delimited JSON tempfile (NOT under `.seo-data/gsc/` — disk-write boundary):

```bash
FINDINGS_JSONL=$(mktemp -t gsc-findings-XXXXXX.jsonl)
# Orchestrator writes one finding per line:
# {"sub_dim":"wikidata_sameAs","location":"Wikidata Q139820111","title":"...",
#  "url":"...","source":"heuristic","impressions":...,"ctr":...,"position":...,
#  "code_changed_since_gsc_window":false}
```

The orchestrator builds the JSONL via direct Bash redirection from the in-memory findings list — no inline Python. If the orchestrator's findings list is held in a structured form that doesn't trivially serialize to JSONL via Bash, fall back to: write each finding's minimal fields (`sub_dim`, `location`, `title`, optional `url`+`source`+`impressions`+`ctr`+`position`+`code_changed_since_gsc_window`) one per line.

**Step 6.8.2 — Update finding-history** (must check exit status before proceeding to 6.8.3 — _code-review finding #10_):

```bash
RUN_DATE=$(date -u +%Y-%m-%d)
COMMIT_SHA7=$(git rev-parse --short HEAD 2>/dev/null || echo "no-git")

if ! PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python "${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py" \
    history-update \
    "$FINDINGS_JSONL" \
    .seo-data/gsc/finding-history.json \
    "$COMMIT_SHA7" \
    "$RUN_DATE"; then
  echo "WARN: history-update failed; skipping 6.8.3 watchpoint-emit to avoid inconsistent state."
  rm -f "$FINDINGS_JSONL"
  # Skip 6.8.3 + 6.8.4 — return to Step 7 with no escalation hints + no new watchpoints.
fi
```

If history-update succeeds, the helper has already printed its results to stdout BEFORE attempting the write (per the helper's print-before-write contract — _code-review finding #9_), so partial-failure observability is preserved: even if the write step fails, the orchestrator has the per-finding run_counts and can render escalation hints in Step 7 from stdout.

Helper output includes per-finding `<hash>|<run_count>|<sub_dim>|<location>|<first_seen_date>[ ESCALATE]` lines. The orchestrator builds a `{finding_hash: {run_count, first_seen, escalate}}` map for Step 7 rendering. Findings tagged ` ESCALATE` (run_count ≥ 3) get an appended escalation hint in their `recommended_action`:

```
[Stale-finding escalation] This finding has appeared in 3+ consecutive runs without resolution. Three options: (a) schedule the external action this finding requires (most stale findings are external — Wikidata edits, GSC manual removals, third-party platform changes); (b) downgrade severity to acknowledge the user-side blocker (e.g., "deprioritized — waiting on upstream"); (c) if the finding is no longer relevant, document the rationale in CLAUDE.md so future runs don't re-surface it.
```

**Step 6.8.3 — Emit watchpoints for phase-applied findings** (only runs if 6.8.2 succeeded):

```bash
if ! PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python "${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py" \
    watchpoint-emit \
    "$FINDINGS_JSONL" \
    .seo-data/gsc/watchpoints.json \
    "$COMMIT_SHA7" \
    "$RUN_DATE"; then
  echo "WARN: watchpoint-emit failed; existing watchpoints.json is unchanged."
  # Proceed to 6.8.4 cleanup regardless — failure here just means no new watchpoints.
fi
```

The helper auto-emits a watchpoint for each finding with `code_changed_since_gsc_window=true` — these are exactly the findings that Step 1.5 already identified as "may already be fixed; re-check next cycle." The watchpoint captures the baseline metric so Step 1.6.14 (next run's watchpoint-check) can compare current vs baseline. Dedup by finding hash prevents duplicate watchpoints on the same finding.

**Step 6.8.4 — Cleanup**:

```bash
rm -f "$FINDINGS_JSONL"
```

Footer line additions (rendered in Step 7 footer alongside cache + snapshot stats):

```
Finding history: 47 tracked total; 12 fresh this run; 5 escalated (run_count ≥ 3).
Watchpoints emitted this run: 2 (auto-watch on findings with code_changed_since_gsc_window=true).
```

When `gsc_mode == "disabled"`, all of Step 6.8 is skipped — finding-history + watchpoints both live under `.seo-data/gsc/` infra. In heuristic-only mode there's no `code_changed_since_gsc_window` signal to drive watchpoint emission anyway.

---

## Step 7 — Output

Read `references/report-template.md` for exact formatting. The shape:

**Section 0 — Single headline** (first line of report):

> **SEO/GEO score: 72/100 (Δ +8 since 2026-04-30)** — Top 3 opportunities: missing meta descriptions (12 pages); no llms.txt; broken /products/v1 (404).

If no `docs/seo-history.md` exists yet, drop the delta clause: `**SEO/GEO score: 72/100** — Top 3 opportunities: ...`.

**Sections 1-5** per `references/report-template.md`.

### Append to docs/seo-history.md

**Only in default review-only mode.** Skip the history append entirely when `--plan` or `--fix` is in `$ARGUMENTS` — those are follow-ups to a recent audit, not new audits; writing duplicate score rows pollutes the history with no information gain.

**Same-commit dedup (S31 dogfood fix).** Before appending, check whether a previous run on the same `last_commit_sha` already wrote an entry. The skill's score has known methodology variance (the same codebase scored 60 → 48 → 40 → 55 across 4 runs on a single day in the S31 dogfood — last commit was docs-only). Writing 4 rows with different scores misleads the delta column and accumulates noise.

Detection + handling:

1. **Capture `current_commit_sha`** at run start via `git -C <repo> rev-parse HEAD` (orchestrator runs this in Step 0 or 1.5 batch).
2. **Embed the sha as an HTML comment** on every appended row so future runs can match: `| YYYY-MM-DD | <score> | <priorities> | <!-- commit:abc1234 -->`
3. **Read the last row of `docs/seo-history.md`** (just the tail, not full file) and grep for `<!-- commit:<sha7>` matching `current_commit_sha[:7]`.
4. **If matched** (previous run was on the same commit):
   - **Skip the append entirely.** Do NOT overwrite the existing row — preserving the first run's data is more honest than picking a "winner" between methodology-variant scores.
   - Report to the user instead:
     > "⚠ Score history not appended — last commit (`abc1234`) already has an entry in `docs/seo-history.md` from <date>. The skill's score has known methodology variance across runs on identical codebases; preserving the first run's data is more honest than appending variant scores. Make a code change before the next `/bx:seo` run to log new progress, or run `/bx:seo --plan` / `--fix` to act on the existing audit."
   - Also drop the delta clause from the headline (rendered at Step 7 first line): show `**SEO/GEO score: 55/100** — Top 3 opportunities: ...` without the `(Δ +X)` part, since "delta vs same-commit run" is misleading.
5. **If NOT matched** (new code since last entry, OR no previous entries at all) → proceed with normal append.

**Methodology-variance disclaimer in headline.** When same-commit dedup triggers AND the user explicitly forces a re-run anyway (re-running `/bx:seo` is allowed for second opinions), the report's Section 0 headline gains a one-line disclaimer:

> `**SEO/GEO score: 55/100** — Top 3 opportunities: ... | ⚠ same-commit re-run (previous score: 40); score variance is methodology-driven, not codebase change.`

In default mode (first run on this commit), after the dedup check passes, render or create `docs/seo-history.md`:

If file doesn't exist, create with header:
```markdown
# SEO/GEO Score History

> Auto-managed by `/bx:seo`. Append-only, never delete entries. Each row captures the score + top-3 priorities so progress is visible across runs.
> **Same-commit dedup:** only one entry per `last_commit_sha`. Re-runs on the same commit are silently skipped — score has known methodology variance that would misrepresent as code-driven delta.

| Date | Score | Top-3 priorities |
|------|-------|------------------|
```

Append row (with embedded commit sha):
```
| 2026-05-14 | 72 | Missing meta descriptions (12 pages); No llms.txt; Broken URL /products/v1 (404) | <!-- commit:abc1234 -->
```

The `<!-- commit:abc1234 -->` HTML comment is invisible in the rendered Markdown table but parseable by the next run's dedup check.

**Rules for the history file:**
- Create if missing — never assume it exists.
- Append-only — never delete or rewrite past entries.
- Each row always has all 3 columns. If fewer than 3 priorities surfaced, use "-" placeholders.
- Date is `YYYY-MM-DD`.
- This file is in-repo and git-tracked deliberately — the user can see history across machines / commits / team members.
- One row per `last_commit_sha`. Same-commit re-runs are silently skipped per the dedup rule above.

### Watchpoint banner format (Group D)

When Step 1.6.14's `watchpoint-check` produced `due` records, render one banner per due watchpoint at the **top of the "Suggested Next Actions" section** (above the skill-chain suggestions). Banner format depends on `status`:

**status: improved** (CTR / position moved favorably ≥10%)

```
📈 Watchpoint hit — improved. Phase applied 2026-05-24 (commit 76cdef9) targeted /en/article/smartphone-vs-mirrorless-2026 CTR.
   Baseline: ctr=0.28% / pos=4.65 / 58k imp.   Current: ctr=1.10% / pos=4.20 / 62k imp.
   Status: improved (CTR +293%). Consider removing the watchpoint by re-running /bx:seo --force-dispatch after pushing further fixes, or accept and move on.
```

**status: regressed** (CTR / position moved unfavorably ≥10%)

```
📉 Watchpoint hit — REGRESSED. Phase applied 2026-05-24 (commit 76cdef9) targeted /en/article/smartphone-vs-mirrorless-2026 CTR.
   Baseline: ctr=0.28% / pos=4.65 / 58k imp.   Current: ctr=0.22% / pos=5.10 / 60k imp.
   Status: regressed (CTR -21%). The applied change may have backfired — review commit 76cdef9's diff against this URL's current rendered title/meta.
```

**status: unchanged** (within ±10% of baseline)

```
📊 Watchpoint hit — no movement yet. Phase applied 2026-05-24 (commit 76cdef9) targeted /en/article/smartphone-vs-mirrorless-2026 CTR.
   Baseline: ctr=0.28% / pos=4.65 / 58k imp.   Current: ctr=0.30% / pos=4.55 / 59k imp.
   Status: unchanged (within ±10% of baseline). GSC pipeline lag is typically 2-3 weeks — re-check on the next run after 2026-06-15 if movement matters.
```

**status: no_data** (URL not in Q2 pages digest this run — usually impressions dropped below Q2's threshold)

```
🔍 Watchpoint hit — no current data. Phase applied 2026-05-24 (commit 76cdef9) targeted /en/article/smartphone-vs-mirrorless-2026 CTR.
   Baseline: ctr=0.28% / pos=4.65 / 58k imp.   Current: URL not in Q2 pages digest (impressions likely below 10/lookback floor).
   Status: no_data. URL may be deindexed, lost ranking entirely, or below Q2's impressions threshold — check sub-dim 14 (deindex_regression) if any.
```

Banners are info-only — they don't affect the score (consistent with the `score_impact:0` invariant on all GSC-side signals).

### Mode-specific tail

- `--plan` → read `references/plan-mode-seo.md` and emit 6-phase brief.
- `--fix` → walk findings where `is_fix_eligible: true` per `references/fix-allowlist.md`; per-finding diff preview gate; end with `/rewind` reminder.

---

## Step 8 — Closing

If default mode, end with:

> Run `/bx:seo --plan` to convert top findings into a phased rewrite brief, or `/bx:seo --fix` for safe-allowlist mechanical fixes (placeholders + TODO markers, never fabricated copy). Run `/bx:seo --url https://your-domain.com` to add live HTML diff and sitemap URL probe.

---

## Quick Reference

| Want... | Use... |
|---------|--------|
| Per-commit / diff quality (quick / thorough) | `/code-review` / `/bx:review` |
| Dead code, unused deps | `/bx:clean` |
| Repo-wide architecture audit | `/bx:arch` |
| Repo-wide test suite audit | `/bx:tests` |
| **Repo-wide SEO + GEO audit (web only)** | **`/bx:seo` (this)** |
| Plan a SEO/GEO improvement effort | `/bx:seo --plan` |
| Apply safe SEO scaffolds | `/bx:seo --fix` |
| Live HTML diff + sitemap URL probe | `/bx:seo --url <base>` |
| Not sure where to start | `/bx:health` |
