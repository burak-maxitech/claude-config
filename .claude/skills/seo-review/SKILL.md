---
name: seo-review
description: Repo-wide SEO and Generative Engine Optimization audit for web projects. Rejects non-web repos. Fetches current best practices every run (SEO/GEO field evolves rapidly). Probes sitemap URLs for 4xx/5xx/redirect-chain/slow-response health. Three parallel Sonnet subagents (seo-technical / seo-content / geo-generative). Produces a single score out of 100 + top-3 highest-impact opportunities, with delta from previous run when docs/seo-history.md exists. Use when user mentions SEO audit, GEO audit, Generative Engine Optimization, AI search optimization, llms.txt, structured data, sitemap health, or "make this site rank better."
disable-model-invocation: true
allowed-tools: Read, Write, Grep, Glob, Edit, WebSearch, WebFetch, Bash(git:*), Bash(find:*), Bash(wc:*), Bash(jq:*), Bash(cat:*), Bash(head:*), Task
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

**Otherwise, print the detected stack in one line.** The line includes the GSC-mode summary computed in Step 1.6 (e.g., `Mode: heuristic` when no CSVs present, `Mode: heuristic + GSC (N CSVs)` when CSVs detected). Examples:

> Detected: Next.js 14 app-router project, TypeScript, with sitemap.xml at /public/sitemap.xml and i18n via next-i18next. Mode: heuristic + GSC (7 CSVs present: queries, pages, 5/9 indexing reasons; freshness OK). Use `--url <base>` for live HTML diff and sitemap URL probe.

> Detected: Astro 4 project, TypeScript, no i18n. Mode: heuristic (drop GSC CSVs in `.seo-data/gsc/` for traffic-aware mode — see one-time setup banner above).

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

## Step 1.6 — GSC CSV Ingestion (orchestrator-only)

When the user has dropped Google Search Console CSV exports into `.seo-data/gsc/`, parse them into structured digests + maps for downstream subagent use. When absent, print a one-time setup banner and proceed heuristic-only.

Read `references/gsc-ingestion.md` for the canonical reference (folder layout, expected headers, parsing rules, finding-type catalog, freshness policy, `.gitignore` auto-append rules). The reference is comprehensive; this step describes the orchestrator's call graph.

This step is **independent of Step 1.5** (git-history scan) — both build shared context for Step 5 and may execute in any order or in parallel.

### 1.6.1 — Detection

1. `Glob` for `.seo-data/gsc/**/*.csv`.
2. If **zero matches**:
   - Check sentinel `.seo-data/.gsc-banner-shown`. If the sentinel file is **absent** → emit the setup banner (full text in `gsc-ingestion.md` "Setup banner"). Touch the sentinel file (`Write` an empty file).
   - Set `gsc_mode: disabled` in shared context. Skip to Step 2 (Mode Dispatch).
3. If **≥1 match**: proceed to 1.6.2.

### 1.6.2 — README + .gitignore (idempotent)

**README:** If `.seo-data/gsc/README.md` does NOT exist, read `references/gsc-setup-readme-template.md` and write its **template content block** (everything between the `## Template content (begin)` and `## Template content (end)` markers, inner-fenced block extracted) to `.seo-data/gsc/README.md`. If the README already exists, leave it alone — user may have edited it.

**.gitignore:** Read project-root `.gitignore` if it exists. Grep for the sentinel start marker `# /seo-review managed`. If absent, append:

```
# /seo-review managed — do not edit between markers
.seo-data/gsc/
.seo-data/.gsc-banner-shown
# /end /seo-review managed
```

If `.gitignore` doesn't exist, create it with the sentinel block as sole content. Print a one-line notice: `Added .seo-data/gsc/ to .gitignore (sentinel-marked block).` Subsequent runs are silent.

### 1.6.3 — Parse each canonical CSV

For each canonical path in `.seo-data/gsc/` (per the inventory in `gsc-ingestion.md` "Folder layout"):

1. `Read` the file.
2. Parse per `gsc-ingestion.md` "Parsing rules" — strip BOM, validate headers case-insensitively, walk rows respecting CSV quoting, normalize CTR/Position/dates.
3. Build digest per `gsc-ingestion.md` "Digest caps" (top-50 per CSV by the documented sort key).
4. Track `total_count` (full row count) separately from digest length — clusters use total_count in headlines.

Failure modes (all log to footer + continue, never block):
- Unknown CSV path → log `unknown CSV ignored: <path>`.
- Missing required header → log `CSV skipped: <path> — expected <X>, detected <Y>`.
- Malformed rows → tally `malformed_rows: <count>` per CSV.

### 1.6.4 — Build cross-subagent maps

After all CSVs parsed:

- **page_type_map**: `{url → page_type}` over the union of URLs from `performance/pages.csv` digest + any `indexing/*.csv` digests + sitemap URLs (from Step 3.2 probe results when available, else from sitemap parsing). Classification heuristics: `gsc-ingestion.md` "page_type_map building" (mirrors `scan-geo.md:25-37` patterns).
- **url_impressions_map**: `{url → impressions}` from `performance/pages.csv` rows. Used by ALL 4 subagents in Step 6 ranking — supplies `traffic_weight` when a finding's affected URL has GSC impression data (`rubric.md` "Traffic-weighted ranking").

### 1.6.5 — Freshness check

For each parsed CSV, compute `days_old = floor((now - file_mtime) / 1 day)`. Accumulate `freshness_summary: [{file, days_old}, ...]` for the footer. Per `gsc-ingestion.md` "Freshness policy":
- <30 days: no warning
- 30-90: footer warning "consider re-export"
- >90: stronger warning "data may be misleading"

Never block on freshness.

### 1.6.6 — Compute GSC mode summary (consumed by Step 0)

Build the GSC-mode fragment for Step 0's detected-stack line:

- Disabled: `heuristic (drop GSC CSVs in .seo-data/gsc/ for traffic-aware mode — see one-time setup banner above)`
- Enabled: `heuristic + GSC (<N> CSVs present: <inventory summary>; freshness <OK | warning>)`

Where `<inventory summary>` lists categories present, e.g., `queries, pages, 5/9 indexing reasons`.

### 1.6.7 — Pass to all 4 subagents (Step 5 shared context)

The orchestrator's Step 5 shared-context block (the base block passed to all subagents) gains a GSC section:

```
GSC Mode: enabled | disabled

When enabled:
- CSVs detected: <list of canonical paths>
- Digests:
  - performance/queries.csv: <top-50 structured records>
  - performance/pages.csv: <top-50 structured records>
  - indexing/summary.csv: <full table, ≤11 rows>
  - indexing/<reason>.csv: <top-50 by last_crawled desc>, total_count=<N>
- page_type_map: {<url>: <page_type>, ...}
- url_impressions_map: {<url>: <impressions>, ...}   ← for traffic_weight lookups
- Freshness summary: [{file, days_old}, ...]
- Malformed rows: {<file>: <count>} (omit when all zero)
- Unknown CSVs ignored: [<paths>] (omit when empty)

When disabled:
- gsc_mode: disabled
- Reason: "no .seo-data/gsc/" | "no canonical CSVs found"
```

**Primary consumer:** `seo-gsc-insights` subagent (added in Phase 4 — Step 5 will be updated to 4 parallel Task dispatches at that point). Until Phase 4 ships, the GSC block is built but unused — the 3 existing subagents may consume `url_impressions_map` for traffic_weight ranking starting in Phase 3.

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

Launch all 3 Task subagents in a **single turn** (3 Task calls in one message). Mirror `/test-review` Step 4.

For each subagent, read its corresponding reference file (`references/scan-technical.md`, `references/scan-content.md`, `references/scan-geo.md`) and pass the contents in the task prompt along with shared context.

### Shared context — base block passed to all 3 subagents:

```
Detected stack: <from Step 0>
i18n detected: true | false (with config file path if true)
Best-practices brief (fetched <date>):
<verbatim 50-line brief from Step 1>

Weight adjustments (validated in Step 1: |each| ≤ 5, sum = 0):
{"structured_data": -2, "generative_engine": +3, "performance": -1, ...}

Scope file list: <paths>

Findings format: structured JSON-like blocks per the scan-*.md reference.
Each finding includes dimension, sub_dimension, location, title, severity, certainty,
effort_estimate, score_impact, is_fix_eligible, recommended_action, evidence.
Return raw findings only — do NOT format a final report.
```

### Per-subagent additions (do NOT include these in agents that don't consume them):

- **`seo-technical` only** — also pass the **Sitemap URL probe results** (full record list) AND the **Rendered HTML excerpt** if `--url` was provided.
- **`seo-content` only** — also pass the **Rendered HTML excerpt** if `--url` was provided. Do NOT pass probe results (it doesn't use them).
- **`geo-generative`** — base block only. No probe results (doesn't use them); no rendered HTML (JSON-LD lives in source most reliably). Keeps geo-generative's prompt smallest of the three.

### Agent 1: seo-technical
Read `references/scan-technical.md`, dispatch `seo-technical` with the file + shared context. Owns Technical SEO (25) + Performance signals (10) = 35 points. Consumes sitemap probe results.

### Agent 2: seo-content
Read `references/scan-content.md`, dispatch `seo-content` with the file + shared context. Owns On-Page SEO (25 points). Uses rendered HTML if provided.

### Agent 3: geo-generative
Read `references/scan-geo.md`, dispatch `geo-generative` with the file + shared context. Owns Structured Data (20) + Generative Engine (20) = 40 points. Source-only (no rendered HTML).

---

## Step 6 — Consolidate + Score

After all 3 subagents return:

1. **Aggregate + clamp sub-dimension deductions.** Each subagent returns a `sub_dimension_breakdown` map of deductions keyed by sub-dim name. For each sub-dim, **clamp at the sub-dim max** per `references/rubric.md`: `clamped[sub_dim] = min(raw[sub_dim], sub_dim_max)`. The dimension total is then `adjusted_dimension_max - sum(clamped sub_dim deductions)`, floored at 0. This is the single point of clamp enforcement — subagents may emit raw sums larger than a sub-dim cap (multiple findings in the same sub-dim), and the rubric is canonical here. If a subagent's emitted dimension_total disagrees with the recomputed one, prefer the recomputed value and flag the divergence in the footer.
2. **Apply weight adjustments** from Step 1's brief (max ±5 per dim, sum delta 0). E.g., if brief bumped Generative Engine +3, `adjusted_dimension_max` becomes 23 and the deduction-from-max is computed against the new max. Sub-dim caps used in step 1 are the **base** caps from `rubric.md` and are not rescaled by weight adjustments.
3. **Verify total = 100.** Print a `subtotal_check: <a>+<b>+<c>+<d>+<e>=<total>` line in the footer so any arithmetic drift is visible.
4. **Compute total score:** `total = sum(dimension_scores)`.
5. **Read `docs/seo-history.md`** if it exists. Find the most recent entry. Compute `delta = today_score - previous_score`.
6. **Rank improvement opportunities:** sort all findings by `score_impact × certainty / effort_weight` descending. Effort weights: trivial 1, small 2, medium 4, large 8. Take **top 3** for the headline.
7. **Drop low-confidence noise:** drop findings with `certainty < 0.5` AND `score_impact < 1` unless `is_fix_eligible: true` (fix-eligible findings get to surface even at lower confidence so the user can review the diff).

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
