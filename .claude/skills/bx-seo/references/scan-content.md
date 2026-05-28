# Scan: On-Page SEO Content

Loaded by the orchestrator and passed to the `seo-content` subagent.

## Inputs from the orchestrator

- `Detected stack` — framework + content patterns
- `Best-practices brief` — passed verbatim
- `Scope file list` — page-template / layout / content source files
- `Rendered HTML excerpt` (only if `--url` provided)
- `Weight adjustments`

## Approach

For each page-template or content source file, scan against the sub-dimensions below.

---

## Sub-scan 1: Titles

`Grep` pattern (HTML/JSX-style): `<title[^>]*>([^<]*)</title>`
`Grep` pattern (metadata API — Next.js app-router): `title:\s*["']([^"']+)["']` in `metadata = {...}` or `generateMetadata` returns.

For each extracted title:
- **Length**: <30 chars → `severity: low`, `score_impact: 0.25`; >70 chars → `severity: low`, `score_impact: 0.25` (truncated in SERP).
- **Optimal range**: 50-60 chars — no penalty.
- **Empty / placeholder titles** (`{{title}}`, `<title></title>`) — if it looks like an unfilled template variable AND the page is indexable, `severity: high`, `score_impact: 1.5`.
- **Duplicates**: build a map of all titles across the scope. Any title used on 3+ pages → finding for each duplicate cluster, `severity: medium`, `score_impact: 1`.

**Pages entirely missing `<title>`** in source AND in metadata API → `severity: high`, `score_impact: 2`. Caveat: SPA-shell template projects may legitimately have empty source titles (set client-side); lower certainty for those.

---

## Sub-scan 2: Meta Descriptions

`Grep` patterns:
- `<meta\s+name=["']description["']\s+content=["']([^"']*)["']`
- Next.js metadata API: `description:\s*["']([^"']+)["']`

For each extracted description:
- **Length**: <70 chars or >170 chars → `severity: low`, `score_impact: 0.25`.
- **Optimal**: 150-160 chars.
- **Boilerplate detection** (heuristic): descriptions starting with `This page is about`, `Welcome to`, `Learn more about` without further specificity → `severity: low`, `score_impact: 0.25` informational nudge.
- **Duplicates**: same map approach as titles. 3+ pages with identical description → `severity: medium`, `score_impact: 1`.

**Missing meta description entirely** → `severity: high`, `score_impact: 1.5`, `is_fix_eligible: true` (insert `<meta name="description" content=""> <!-- TODO: write description -->` placeholder).

---

## Sub-scan 3: Headings (H1 uniqueness + hierarchy)

For each page-template / content source:

1. Extract all heading tags `<h[1-6]>...</h[1-6]>` in order.
2. **H1 count check**: count occurrences. Should be exactly 1.
   - 0 H1s on an indexable page → `severity: high`, `score_impact: 1`.
   - 2+ H1s → `severity: medium`, `score_impact: 0.75`.
3. **Hierarchy check**: walk the sequence. Any jump of >1 level (H1 → H3, H2 → H4) → `severity: low`, `score_impact: 0.25`.
4. **H1 content quality**: empty H1, single-word generic H1 (`Home`, `Page`, `Welcome`), or H1 identical to `<title>` verbatim → `severity: low`, `score_impact: 0.25`.

Detection caveat for markdown/MDX content: `#`/`##` heading levels also count. Treat `#` as H1, `##` as H2, etc.

---

## Sub-scan 4: Image Alt Text

`Grep` pattern: `<img\b[^>]*>` (HTML/JSX `<img>` tags). Also scan `<Image>` framework components.

For each match:

1. Extract the `alt` attribute (or its absence).
2. **Missing `alt` attribute entirely** → `severity: high`, `score_impact: 0.75`. Always a finding.
3. **`alt=""`** (empty alt):
   - **Decorative-image guards** (do NOT flag if any apply):
     - Image inside a `<button>` or has `aria-hidden="true"`.
     - Image in a `<picture>` element with `aria-hidden` or explicit decorative role.
     - Common framework patterns: `<Image>` inside a logo component with explicit `decorative` prop.
   - If no guards apply AND the image looks content-bearing → `severity: medium`, `score_impact: 0.5`.
4. **Filename-as-alt** (`alt="hero-banner.jpg"`, `alt="DSC_1234.png"`): `severity: low`, `score_impact: 0.25`.
5. **Generic-word alt** (`alt="image"`, `alt="photo"`, `alt="picture"`): `severity: low`, `score_impact: 0.25`.

**Fix-eligibility**: only `alt=""` decorative scaffolds for images with strong decorative signals (in `<button>`, `aria-hidden`). Never auto-write descriptive alt text — that requires understanding the image content.

---

## Sub-scan 5: OpenGraph + Twitter Cards

`Grep` patterns:
- `<meta\s+property=["']og:(title|description|image|url|type)["']`
- `<meta\s+name=["']twitter:(card|title|description|image)["']`
- Next.js metadata API `openGraph: {...}`, `twitter: {...}`

For each page-shell / layout:

**Required OG tags** (all must be present):
- `og:title`, `og:description`, `og:image`, `og:url`, `og:type`

**Required Twitter Cards:**
- `twitter:card` (`summary_large_image` is the modern default), `twitter:title`, `twitter:description`, `twitter:image`

**Missing entirely** on a content-facing page → `severity: medium`, `score_impact: 1`, `is_fix_eligible: true` (insert templates with TODO placeholders for the values).

**Missing `og:image:width` and `og:image:height`** when `og:image` is declared → `severity: low`, `score_impact: 0.25` (improves social card rendering).

**Twitter Card type mismatch** — `twitter:card="summary"` when an `og:image` is large and high-quality (suggests `summary_large_image` would be better) → informational, low severity.

---

## Sub-scan 6: Internal Linking

**Orphan page detection:**

1. List all page files (`Glob` for `pages/**/*.{tsx,jsx,vue,svelte,md,mdx,html}` or framework equivalent).
2. For each page, derive its public URL path (e.g., `pages/blog/foo.tsx` → `/blog/foo`).
3. For each public path, `Grep` the entire scope for `href=["']<path>["']` (or `[link]: <path>` markdown).
4. Zero matches → orphan. Surface `severity: medium`, `score_impact: 0.5` per orphan (cap at 5 surfaced; if more orphans found, the rest go into the count footer).

**Broken internal links:**
- `Grep` for `href=["']/[^"']*["']` patterns across pages.
- For each captured href, check if a matching page file exists in the routing tree.
- Missed match → `severity: medium`, `score_impact: 0.5`.

**Anchor text quality:**
- `Grep` for `<a [^>]*>([^<]+)</a>` patterns.
- Flag generic anchor text: `click here`, `read more`, `learn more`, `here`, `this link` — `severity: low`, `score_impact: 0.1` per occurrence (cap impact at 0.5 total across the scan).

---

## Sub-scan 7: Content Depth Signals

For each indexable page (skip 404, login, search):

1. Use `wc -l` or word-count via a Grep heuristic on the content source.
2. If word count <300 → `severity: low`, `score_impact: 0.1`, `is_fix_eligible: false`.

This sub-dimension caps at 1 point total. It's primarily an informational signal — many short pages exist legitimately (landing pages, hub pages).

---

## Sub-scan 8: Live Source-vs-Rendered Diff (only when `--url` provided)

If rendered HTML is in shared context:
- Compare source title/meta/headings to rendered. Drift suggests runtime override that may or may not be intentional. Surface findings only when:
  - Source has empty/placeholder content AND rendered has real content → suppress (CMS-driven, working as designed).
  - Source has different content from rendered → `severity: low`, `score_impact: 0.5`, informational.

---

## Output addendum

```
on_page_seo_score: <int 0-25>
sub_dimension_breakdown: {
  "titles": <points deducted>,
  "meta_descriptions": <points deducted>,
  ...
}
duplicate_titles: <int>
duplicate_descriptions: <int>
orphan_pages: <int>
files_scanned: <int>
```

---

## Hard rules

- **Never fabricate content.** Fix-mode inserts placeholders + TODO comments only.
- **Honor the fetched best-practices brief** when it diverges from heuristics above.
- **Skip vendored / generated dirs.**
- **Cap output at 30 findings**, ordered by `score_impact × certainty` desc.

## False-positive guards

- **404/error/login pages** — exempt from titles, metas, OG checks.
- **Admin / utility routes** (`/admin`, `/dashboard`) — exempt from OG/Twitter Cards.
- **CMS-driven runtime content** — check for template-variable patterns (`{{ ... }}`, `${...}`, `<%= %>`) in source; if found, lower certainty for missing-content findings. If `--url` rendered HTML has the content, suppress.
- **SPA shells** — empty source titles are common; lower certainty.
