# --fix Mode Allowlist (seo-review)

`/seo-review --fix` is deliberately the narrowest possible: **only mechanical, content-free, safe-by-construction additions** are eligible. Every other improvement routes to `--plan`.

## Why the allowlist is strict

Two hard rules drive the design:

1. **Never fabricate content.** Titles, meta descriptions, alt text, JSON-LD values — these require knowing what the page is about. The skill doesn't know. So `--fix` inserts placeholders + TODO comments, never fabricated copy. The user fills the values.
2. **Never break a working page.** Fixes that touch existing markup (rewriting headings, restructuring HTML) are out — they require human judgment about layout, accessibility, and content intent. `--fix` only adds missing things; it doesn't change present things.

If you find yourself wanting to auto-fix something not on this list, route it to `--plan` instead.

---

## Eligible patterns

### 1. Missing `<meta name="viewport">`

**Detection:** page-shell / layout file has no viewport meta.

**Fix:** insert in `<head>`:
```html
<meta name="viewport" content="width=device-width, initial-scale=1">
```

**Per-finding gate:** show the head block + the proposed insert. User approves y/n/skip/abort.

---

### 2. Missing `<link rel="canonical">` self-referencing

**Detection:** indexable page has no canonical, AND the page's expected public URL is deterministically derivable from filename (e.g., `pages/about.tsx` → `/about` in Next.js pages-router; `app/about/page.tsx` → `/about` in app-router).

**Fix:** insert self-referencing canonical:
```html
<link rel="canonical" href="/about">
```
For frameworks where canonical URLs need to be absolute, insert with a TODO placeholder for the base URL:
```html
<!-- TODO: replace BASE_URL with your domain -->
<link rel="canonical" href="BASE_URL/about">
```

Skip if the URL pattern can't be deterministically derived from the filename.

---

### 3. Missing `robots.txt`

**Detection:** no `robots.txt` found in repo root, `public/`, `static/`.

**Fix:** generate a permissive default at `public/robots.txt` (or repo root for non-framework projects):
```
User-agent: *
Allow: /

Sitemap: /sitemap.xml
```

If sitemap.xml also doesn't exist, omit the `Sitemap:` line and add a TODO comment:
```
# TODO: add Sitemap: /sitemap.xml once sitemap.xml is created
User-agent: *
Allow: /
```

---

### 4. Missing `sitemap.xml` stub

**Detection:** no `sitemap.xml` found anywhere.

**Fix:** generate empty `urlset` stub at `public/sitemap.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- TODO: populate with site URLs. Each <url> needs <loc>, optional <lastmod>, optional <priority>. -->
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
</urlset>
```

For frameworks with automatic sitemap generation (Next.js `app/sitemap.ts`, Nuxt `@nuxtjs/sitemap`, Astro `@astrojs/sitemap`), skip the static file and instead generate a TODO-marked framework-specific stub:

Next.js example (`app/sitemap.ts`):
```ts
import type { MetadataRoute } from 'next'

// TODO: replace with actual URLs from your routing tree
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: 'https://example.com', lastModified: new Date(), priority: 1.0 },
  ]
}
```

---

### 5. Missing OpenGraph + Twitter Card scaffolds

**Detection:** page-shell / layout has no `<meta property="og:*">` or `<meta name="twitter:*">` tags.

**Fix:** insert template in `<head>` with TODO placeholders:
```html
<!-- TODO: fill in OG values -->
<meta property="og:title" content="">
<meta property="og:description" content="">
<meta property="og:image" content="">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:url" content="">
<meta property="og:type" content="website">

<!-- TODO: fill in Twitter Card values -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="">
<meta name="twitter:description" content="">
<meta name="twitter:image" content="">
```

For frameworks with metadata API (Next.js), use the API instead of meta tags. Example:
```ts
export const metadata = {
  // TODO: fill in OG and Twitter values
  openGraph: {
    title: '',
    description: '',
    images: [{ url: '', width: 1200, height: 630 }],
    url: '',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: '',
    description: '',
    images: [''],
  },
}
```

**Never** fabricate values — always TODO-marked placeholders.

---

### 6. Missing `<meta name="description">`

**Detection:** indexable page has no meta description.

**Fix:** insert placeholder:
```html
<!-- TODO: write a 150-160 char description that summarizes this page -->
<meta name="description" content="">
```

Never auto-write the description content.

---

### 7. Missing `alt=""` on decorative images (high-confidence only)

**Detection:** `<img>` without `alt` attribute AND any of these decorative signals:
- Image is inside `<button>` element
- Image has `aria-hidden="true"` (consistency fix)
- Image is in a `<picture>` element with explicit decorative role
- Image is part of a logo component with explicit decorative prop

**Fix:** insert `alt=""` (empty alt = decorative declaration):
```html
<img src="..." alt="">
```

**Never insert descriptive alt text.** Descriptive alts for content images require understanding the image — route to `--plan`.

---

### 8. Missing `width` / `height` on `<img>` (when derivable from adjacent context)

**Detection:** `<img>` without `width` and `height`, AND a sibling component / Next.js `<Image>` / Astro `<Image>` references the same `src` with declared dimensions.

**Fix:** copy dimensions from the adjacent context:
```html
<img src="hero.jpg" width="1200" height="600" alt="...">
```

If no adjacent context provides dimensions, skip — route to `--plan` (user needs to look up the image dimensions).

---

### 9. Missing `loading="lazy"` on below-fold `<img>` (heuristic detection)

**Detection:** `<img>` without `loading` attribute AND the image appears after the first 200 lines of source / after a `<main>` element open / after specific layout markers suggesting below-the-fold position.

**Fix:** add `loading="lazy"`:
```html
<img src="..." loading="lazy" alt="...">
```

Skip framework-managed components (`next/image`, `Astro <Image>`, `nuxt-img`) — they handle this automatically.

---

### 10. Missing schema.org JSON-LD scaffolds

**Detection:** page-type detected (Article on blog post, Product on product page, etc.) AND no JSON-LD block of the expected `@type`.

**Fix:** insert scaffold in `<head>` (or via framework metadata API) with all required fields as TODO-marked placeholders. Example for Article:

```html
<!-- TODO: fill in Article values -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "",
  "datePublished": "",
  "dateModified": "",
  "author": {
    "@type": "Person",
    "name": ""
  },
  "image": ""
}
</script>
```

Example for Product:
```html
<!-- TODO: fill in Product values -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "",
  "image": "",
  "offers": {
    "@type": "Offer",
    "price": "",
    "priceCurrency": ""
  }
}
</script>
```

**Never** populate from page content. Heuristic-derived values are wrong often enough to be a net negative.

---

### 11. Missing `llms.txt`

**Detection:** content-rich site (heuristic: site has >10 content pages) AND no `llms.txt` found.

**Fix:** generate scaffold at `public/llms.txt`:
```
# <TODO: site title>

> <TODO: one-sentence site description>

## <TODO: section name, e.g. "Documentation">

- [<TODO: page title>](<TODO: URL>): <TODO: one-line description>

## <TODO: another section name>

- [<TODO: page title>](<TODO: URL>): <TODO: one-line description>
```

The TODO markers preserve format compliance while making it obvious the user must fill in real content.

---

## Per-finding gate flow

For each fix-eligible finding (in rank order):

```
─────────────────────────────────────────────────────
[Finding 3 of 8] Missing OG/Twitter Card scaffold
src/app/layout.tsx

Current state:
  <head>
    <meta charset="utf-8">
    <title>Site</title>
  </head>

Proposed change (diff):
  --- a/src/app/layout.tsx
  +++ b/src/app/layout.tsx
  @@ -12,4 +12,18 @@
     <head>
       <meta charset="utf-8">
       <title>Site</title>
  +    <!-- TODO: fill in OG values -->
  +    <meta property="og:title" content="">
  +    ...
     </head>

Score impact recovered if applied: +1.0 (On-Page SEO)
This fix adds placeholders only — you will need to fill in the values.

Apply? [y / n / skip / abort]
```

User responses:
- `y` — apply via `Edit`, advance.
- `n` — record "rejected (do not re-show this run)", advance.
- `skip` — record "skipped (revisit later)", advance.
- `abort` — stop the whole `--fix` pass. Already-applied edits stay; use `/rewind`.

## After all findings processed

Print a summary:

```
--fix pass complete.

Applied: 5 scaffolds across 4 files
Rejected: 1
Skipped: 2
Auto-routed to --plan: 23

Score recovery if all applied: estimated +6 points

⚠️  Every applied fix contains TODO placeholders. Run `grep -rn "TODO:" <touched-files>` to find them. Fill in values before this work delivers real SEO value.

Per-edit undo: press Esc Esc twice or run /rewind.
Whole-pass undo: if you did this on a branch, `git checkout main && git branch -D <fix-branch>` discards all changes.
```

## Hard rules

- **Never fabricate content.** Every fix inserts placeholders + TODO comments. Always.
- **Never modify existing content.** Only add missing things.
- **Per-finding diff preview gate** — no batch-apply.
- **Single-file per fix** — don't apply cross-file changes from one finding.
- **`certainty >= 0.7` required** — re-check at fix time, in case the consolidator's certainty was off.

## What this mode does NOT do

- Run tests after edits
- Fabricate copy (titles, descriptions, alt text, JSON-LD values, OG values, llms.txt content)
- Rewrite existing markup
- Modify content files (markdown bodies, blog posts) — only page-shell / layout / config files
- Add internal links (judgment-heavy)
- Adjust heading hierarchy (judgment-heavy)
- Update `robots.txt` AI-bot rules (deliberate policy decision)
- Run coverage / lighthouse / external audits

All of the above belong to `--plan`, not `--fix`.
