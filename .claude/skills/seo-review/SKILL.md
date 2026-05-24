---
name: seo-review
description: Audits a web project for SEO and Generative Engine Optimization (GEO). Fetches current best practices every run, probes sitemap URL health, and optionally ingests Google Search Console data via API. Score `/100` headline + top-3 priorities, tracked in `docs/seo-history.md`.
when_to_use: When user mentions SEO audit, GEO audit, Generative Engine Optimization, AI search optimization, llms.txt, structured data / JSON-LD, sitemap health, Google Search Console, GSC, search performance, AI citability, or "make this site rank better". Web projects only — rejects non-web repos silently. Distinct from generic code-review skills (no SEO awareness) and from `/architecture-review` (code structure, not SEO).
disable-model-invocation: true
allowed-tools: Read, Write, Grep, Glob, Edit, WebSearch, WebFetch, Bash(git:*), Bash(find:*), Bash(wc:*), Bash(grep:*), Bash(sed:*), Bash(cat:*), Bash(head:*), Bash(gcloud:*), Bash(curl:*), Task
effort: high
argument-hint: "[path] [--plan] [--fix] [--url <deployed-url>] [--no-cache]"
---

# SEO Review — Repo-Wide SEO + Generative Engine Optimization Audit

Audit a web project for SEO and Generative Engine Optimization (GEO — optimizing for AI search like ChatGPT, Perplexity, Claude, Google AI Overviews) health. The field evolves fast, so this skill **fetches current best practices fresh on every run** rather than relying on bundled static guidance.

This skill is web-projects-only. Step 0 detects web-project state and exits silently on non-web repos — there's nothing to do.

Distinct from existing review skills:

- **`/code-review`** / **`/review-deep`** — diff/commit scope, no SEO awareness
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

**Otherwise, print the detected stack in one line.** The line includes the GSC-mode summary computed in Step 1.6 (one of two outcomes: API enabled, or heuristic-only). Examples:

> Detected: Next.js 14 app-router project, TypeScript, with sitemap.xml at /public/sitemap.xml and i18n via next-i18next. Mode: heuristic + GSC (Search Console API — 95 URLs inspected, 3 perf queries). Use `--url <base>` for live HTML diff and sitemap URL probe.

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
- `Read references/gsc-ingestion.md` (always needed when API is configured — covers API ingestion contract + 13 sub-dim catalog)
- `Read .seo-data/gsc/config.yaml` (optimistic; if file doesn't exist the tool errors silently — interpret as `api_configured = false`)
- `Read references/gsc-api-queries.md` (optimistic; only used when API activates — reading early avoids an extra Read in Turn 2)
- `Read references/gsc-api-schema.md` (optimistic; reference for API response parsing)
- `Read references/gsc-cache.md` (optimistic; cache wrapper template + TTL policy used by Turn 2 dispatch)
- `Bash: mkdir -p .seo-data/gsc/cache 2>/dev/null; find .seo-data/gsc/cache -type f -mtime +7 -delete 2>/dev/null; ls .seo-data/gsc/cache 2>/dev/null | wc -l` (cache dir setup + 7-day prune + count of remaining entries — produces `<N>` for the footer cache stats line. `mkdir` here is load-bearing — the Turn 2 wrapper assumes the dir exists and does NOT recreate it per call. See `references/gsc-cache.md` "Eviction policy".)
- `Bash: gcloud --version 2>&1` (gcloud SDK install detection)
- `Bash: TOKEN=$(gcloud auth application-default print-access-token 2>&1); ADC_DIR=$(gcloud info --format="value(config.paths.global_config_dir)" 2>/dev/null); QUOTA_PROJECT=$(grep -oE '"quota_project_id"[[:space:]]*:[[:space:]]*"[^"]+"' "$ADC_DIR/application_default_credentials.json" 2>/dev/null | head -1 | sed -E 's/.*"([^"]+)"$/\1/'); echo "TOKEN_LEN:${#TOKEN}"; echo "QUOTA_PROJECT:$QUOTA_PROJECT"; curl -s -w "\nHTTP_STATUS:%{http_code}\n" -H "Authorization: Bearer $TOKEN" -H "x-goog-user-project: $QUOTA_PROJECT" "https://www.googleapis.com/webmasters/v3/sites"` (combined ADC + quota-project + API auth probe in one Bash invocation; orchestrator parses `TOKEN_LEN:`, `QUOTA_PROJECT:`, and `HTTP_STATUS:` to determine ADC + quota project + API reachability. The `x-goog-user-project` header is required on every Search Console API call to bill quota to the user-controlled project; ADC stores the value in `application_default_credentials.json` after `gcloud auth application-default set-quota-project <id>`. Without it, all calls return 403 SERVICE_DISABLED. **Extraction uses `grep -oE` + `sed -E` instead of `jq`** — `jq` isn't on PATH in many bash environments (notably claude-code's Bash on Windows + minimal Linux containers); grep + sed are always available.)

Only the **post-tool aggregation** (parsing git log, parsing config.yaml, resolving API or heuristic mode, parsing sites.list response) runs sequentially.

**Turn 2 — Data ingestion** (only fires when API is active; skipped in heuristic-only mode):
- **Turn 2a — Performance**: 3 parallel `Bash: curl ...` calls for Q1+Q2+Q3 from `gsc-api-queries.md`
- **Turn 2b — Indexing**: up to 100 parallel `Bash: curl ...` calls for URL Inspection (URL selection from Q3 output + sitemap-probe failures + git-changed paths). Turn 2b runs after Turn 2a since URL selection depends on Q3's `url_impressions_map`.

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
- `references/gsc-ingestion.md` — digest shapes, 12 sub-dim finding catalog, `coverageState` → 9-reason lookup, setup banner, `.gitignore` auto-append rules
- `references/gsc-api-schema.md` — Search Console API endpoint inventory, auth/scope, quota model, `coverageState`/`pageFetchState` enums
- `references/gsc-api-queries.md` — 3 parametrized `curl` templates (Q1/Q2/Q3) + URL Inspection per-URL template + URL selection algorithm + lookup table
- `references/gsc-cache.md` — 24h TTL response cache for `searchanalytics.query` + `urlInspection.index.inspect`. Cache wrapper bash template (atomic write, skip-cache-on-non-200, stat portability). `--no-cache` bypass behavior. 7-day eviction policy. Footer line format.

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

**.gitignore**: from the Turn 1 `Read .gitignore` result, Grep for sentinel start marker `# /seo-review managed`. If absent, append:

```
# /seo-review managed — do not edit between markers
.seo-data/gsc/
.seo-data/.gsc-banner-shown
# /end /seo-review managed
```

The block covers `config.yaml` (which contains `site_url` — non-secret but property-identifying). If `.gitignore` doesn't exist, create it with the sentinel block. Print `Added .seo-data/gsc/ to .gitignore (sentinel-marked block).` on first append; silent thereafter.

### 1.6.6 — Data ingestion (Turn 2)

Only fires when `api_active == true`. Skipped in heuristic-only mode.

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

**Turn 2b — URL Inspection (N parallel cache-or-curl calls, N ≤ 100)** — fires after Turn 2a since URL selection uses Q3's output. Compute the URL inspection budget per `gsc-api-queries.md` "URL Inspection — selection algorithm" (top 80 by impressions from Q3 + 20 git-changed paths from Step 1.5 resolved via `page_type_map`, dedup, hard cap 100). Each URL gets its own cache slot (`ui-<sha1(site_url|inspection_url)>.json`) — partial cache hits across the batch are expected (e.g., 80 cached + 20 fresh after a rerun). Fresh-path curl inside the wrapper:

```
curl -s -w '%{http_code}' -o "$TMP" -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-goog-user-project: $QUOTA_PROJECT" \
  -H "Content-Type: application/json" \
  -d '{"inspectionUrl":"<URL>","siteUrl":"<config.site_url RAW>"}' \
  "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
```

Note: `siteUrl` in this request is a **body field** (raw, no URL encoding) — distinct from Search Analytics where it's a path param.

**Per-call cache stats capture.** For each call (Q1/Q2/Q3 + each URL Inspection), record `cache_status: hit | miss` and `age_seconds` (when hit) from the wrapper's first-line output. Aggregate into `{cache_hits: N, cache_misses: M, miss_call_tags: [...]}` for the Step 1.6.12 footer line. Quota tracking adjusts: cache hits don't count against the 2,000/day URL Inspection quota — only `cache_misses` consume quota.

Step 1.6 total: 3 turns max (Turn 1 detection + Turn 2a Performance + Turn 2b Inspection). Heuristic-only mode finishes after Turn 1. Full-cache-hit run (all 103 calls served from cache) consumes zero API quota and shaves several seconds off wall time.

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
| `enabled` | `Mode: heuristic + GSC (Search Console API — 95 URLs inspected, 3 perf queries)` |
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

---

## Ingestion conventions (cross-cutting, applies to Step 1.6 + Step 3.2)

Three rules the orchestrator must follow when ingesting external data. Surfaced from S30 dogfood (the first end-to-end run): the model improvised in three ways that the original spec under-specified.

### Disk-write boundary

`.seo-data/gsc/` is reserved for **user configuration + skill-auto-generated content only**:

- `config.yaml` (user-authored)
- `README.md` (skill-auto-written on first detection)
- `cache/` (skill-auto-managed; **TTL'd API response cache** — see `references/gsc-cache.md`)
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

#### Helper script (don't inline Python heredocs)

**S31 dogfood lesson.** Across one run the orchestrator wrote 5+ different inline Python invocations (Q1 parse, Q2 parse, Q3 parse, CTR opportunities, cluster aggregation), each with different bash quoting/escaping strategies. One heredoc failed with `unexpected EOF` (single quotes inside `<<'PY'` block). The fallback was to write `_parse_clusters.py` into `.seo-data/gsc/cache/` — **violating the disk-write boundary** (cache dir is response-JSON-only).

**Rule:** GSC JSON parsing MUST go through the shipped helper at `${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py`. Invoke with subcommand args:

```bash
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python "${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py" q1 .seo-data/gsc/cache/sa-q1-<hash>.json
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python "${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py" q2 .seo-data/gsc/cache/sa-q2-<hash>.json
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python "${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py" q3 .seo-data/gsc/cache/sa-q3-<hash>.json
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python "${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py" ctr .seo-data/gsc/cache/sa-q2-<hash>.json
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python "${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py" clusters .seo-data/gsc/cache
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python "${CLAUDE_SKILL_DIR}/references/gsc-parse-helper.py" brand .seo-data/gsc/cache/sa-q1-<hash>.json "Burak Arık"
```

`${CLAUDE_SKILL_DIR}` is a Claude Code string substitution that resolves automatically to the skill's own directory (cross-platform, CWD-independent). No orchestrator-side path resolution needed — works whether the user runs `/seo-review` from the repo root or any sub-directory of the target project.

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
| `--no-cache` | Bypass the 24h GSC API response cache. Forces fresh `searchanalytics.query` + `urlInspection.index.inspect` calls. Fresh responses are still written to cache for next run. Use when iterating on a fix and you need Google's current view, or when you suspect cached data is wrong. See `references/gsc-cache.md` for TTL policy + manual cache management. |

`--plan` and `--fix` are mutually exclusive. If both supplied: "Pick one — `--plan` emits a brief, `--fix` applies edits."

`--no-cache` is compatible with all other flags. No-op when `gsc_mode: disabled` (nothing to cache).

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
Read `references/gsc-ingestion.md` (the same reference used by the orchestrator in Step 1.6 — the "Finding-type catalog" section is the agent's spec) and dispatch `seo-gsc-insights` with the reference content + shared context + sitemap URL list. Owns `gsc_insights` dimension with 13 sub-dims and **0 score allocation** (informational only). All findings emit `source: "gsc"` and `score_impact: 0`.

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

**Same-commit dedup (S31 dogfood fix).** Before appending, check whether a previous run on the same `last_commit_sha` already wrote an entry. The skill's score has known methodology variance (the same codebase scored 60 → 48 → 40 → 55 across 4 runs on a single day in the S31 dogfood — last commit was docs-only). Writing 4 rows with different scores misleads the delta column and accumulates noise.

Detection + handling:

1. **Capture `current_commit_sha`** at run start via `git -C <repo> rev-parse HEAD` (orchestrator runs this in Step 0 or 1.5 batch).
2. **Embed the sha as an HTML comment** on every appended row so future runs can match: `| YYYY-MM-DD | <score> | <priorities> | <!-- commit:abc1234 -->`
3. **Read the last row of `docs/seo-history.md`** (just the tail, not full file) and grep for `<!-- commit:<sha7>` matching `current_commit_sha[:7]`.
4. **If matched** (previous run was on the same commit):
   - **Skip the append entirely.** Do NOT overwrite the existing row — preserving the first run's data is more honest than picking a "winner" between methodology-variant scores.
   - Report to the user instead:
     > "⚠ Score history not appended — last commit (`abc1234`) already has an entry in `docs/seo-history.md` from <date>. The skill's score has known methodology variance across runs on identical codebases; preserving the first run's data is more honest than appending variant scores. Make a code change before the next `/seo-review` run to log new progress, or run `/seo-review --plan` / `--fix` to act on the existing audit."
   - Also drop the delta clause from the headline (rendered at Step 7 first line): show `**SEO/GEO score: 55/100** — Top 3 opportunities: ...` without the `(Δ +X)` part, since "delta vs same-commit run" is misleading.
5. **If NOT matched** (new code since last entry, OR no previous entries at all) → proceed with normal append.

**Methodology-variance disclaimer in headline.** When same-commit dedup triggers AND the user explicitly forces a re-run anyway (re-running `/seo-review` is allowed for second opinions), the report's Section 0 headline gains a one-line disclaimer:

> `**SEO/GEO score: 55/100** — Top 3 opportunities: ... | ⚠ same-commit re-run (previous score: 40); score variance is methodology-driven, not codebase change.`

In default mode (first run on this commit), after the dedup check passes, render or create `docs/seo-history.md`:

If file doesn't exist, create with header:
```markdown
# SEO/GEO Score History

> Auto-managed by `/seo-review`. Append-only, never delete entries. Each row captures the score + top-3 priorities so progress is visible across runs.
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
| Per-commit / diff quality (quick / thorough) | `/code-review` / `/review-deep` |
| Dead code, unused deps | `/code-cleanup` |
| Repo-wide architecture audit | `/architecture-review` |
| Repo-wide test suite audit | `/test-review` |
| **Repo-wide SEO + GEO audit (web only)** | **`/seo-review` (this)** |
| Plan a SEO/GEO improvement effort | `/seo-review --plan` |
| Apply safe SEO scaffolds | `/seo-review --fix` |
| Live HTML diff + sitemap URL probe | `/seo-review --url <base>` |
| Not sure where to start | `/code-health-advice` |
