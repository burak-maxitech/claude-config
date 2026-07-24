# Web-Stack Detection Reference

Used by `/bx:webdesign` at the start of Phase 1 (and cheaply re-validated on resume).

Run all four passes in a **single parallel turn** where possible — the `Read`, `Glob`, and `Bash` calls within each pass are independent and should fire together, not sequentially.

---

## Pass 1 — Web-Project Gate

Reject non-web repos immediately. A repo is "web" if **any** of the following signals are present:

### Frontend frameworks
Check `package.json` dependencies + devDependencies:
- **Next.js** (`next`), **Nuxt** (`nuxt`), **Astro** (`astro`), **Remix** (`@remix-run/*`), **Gatsby** (`gatsby`)
- **React** + a routing/SSR signal (`react-router`, `react-router-dom`), **Vue** (`vue`), **Svelte/SvelteKit** (`svelte`, `@sveltejs/kit`), **Angular** (`@angular/core`), **Solid** (`solid-js`)

### Static HTML / generators
- `index.html` at repo root or in `public/` / `static/` / `dist/`
- `_config.yml` (Jekyll)
- `config.toml` + `content/` (Hugo)
- `eleventy.config.{js,cjs}` (11ty)

### Server-rendered backends
- `pyproject.toml` / `requirements*.txt` with Django (`django`), Flask (`flask`), FastAPI (`fastapi`), Starlette (`starlette`) **AND** a `templates/` or `static/` directory
- `Gemfile` with Rails (`rails`) **AND** `app/views/`
- `composer.json` with Symfony (`symfony/*`), Laravel (`laravel/framework`) **AND** `resources/views/` or `templates/`
- `pom.xml` / `build.gradle` with Spring Boot Web (`spring-boot-starter-web`) **AND** `templates/` or `static/`
- `.NET` (`*.csproj` with `Microsoft.AspNetCore`)

> **Signal source:** this list is kept in sync with `/bx:seo` Step 0 — update both if the signal set changes.

**If none match**, print exactly:

```
Not a web project — /bx:webdesign only refactors web projects. Exiting.
```

and stop the skill cleanly (no further passes).

---

## Pass 2 — Styling-System Detection

Determines where design tokens land in Phase 3 injection. Detect in **priority order** (first match wins):

| Priority | System | Detection signals | `styling_system` value |
|----------|--------|-------------------|------------------------|
| 1 | Tailwind CSS | `tailwind.config.{js,ts,cjs,mjs}` exists (definitive, v3-style) **OR** `tailwindcss` in `package.json` deps/devDeps **OR** an `@import "tailwindcss"` (v4) or `@tailwind` (v3) directive in `*.css` files under `src/` and repo root (use `Grep "@import \"tailwindcss\"|@tailwind" glob:"*.css"` scoped to those directories, not a repo-wide scan) | `tailwind` |
| 2 | CSS-in-JS | `styled-components` or `@emotion/react` / `@emotion/styled` in `package.json` | `css-in-js` |
| 3 | CSS Modules | Any `*.module.css` file in the project | `css-modules` |
| 4 | vanilla-extract | `@vanilla-extract/css` in `package.json` **OR** `*.css.ts` files | `vanilla-extract` |
| 5 | CSS custom properties | A theme/tokens file (e.g. `tokens.css`, `variables.css`, `theme.css`) **OR** `:root { --…` declarations in any CSS file | `css-vars` |
| 6 | Plain CSS | Fallback — CSS files present but none of the above | `plain-css` |

> **Tailwind v4 note (load-bearing for Phase 3).** v4 projects typically have **no `tailwind.config.*` file** — the `tailwindcss` dependency plus an `@import "tailwindcss"` line in a CSS file are the definitive signals, and design tokens live in an `@theme { … }` block inside that CSS (e.g. `app/globals.css`), not in a JS/TS config. Still record `styling_system: tailwind`, but Phase 3's token-merge must target that `@theme` block, not a `tailwind.config.js/ts` that doesn't exist (see `phase3-inject.md` Step 2).

**If no CSS or styling files are found at all**, set `styling_system: unknown` and emit a warning:

```
Warning: styling system could not be determined — token-merge in Phase 3 will be best-effort.
```

**State written to `state.json`:**
```json
{ "styling_system": "<value>" }
```

---

## Pass 3 — Refactor vs Greenfield Gate

**Greenfield** = no renderable pages, routes, or components exist (only config files, docs, or an empty scaffold). This mirrors `/bx:plan`'s GREENFIELD detection.

**Detection logic:**
```
// Evaluate EXISTING signals FIRST — before concluding greenfield.
// Non-Node projects (Django, Rails, Hugo, Jekyll, etc.) may have no
// package.json but are still EXISTING if any renderable pages are present.

IF any EXISTING signal is present (see list below):
    -> EXISTING (proceed)
ELSE IF no source code files exist (only docs/config):
    -> GREENFIELD
ELSE IF package.json exists but no page/component/route files exist:
    -> GREENFIELD
ELSE:
    -> GREENFIELD   // no renderable pages AND no EXISTING signals
```

EXISTING signals (check ALL of these before concluding GREENFIELD):
- `pages/`, `app/`, `src/pages/`, `src/app/`, `src/views/`, `src/routes/`, `src/components/` containing `.jsx`, `.tsx`, `.vue`, `.svelte`, or `.html` files
- A `templates/` directory containing `.html` files
- An `index.html` with non-trivial body content (more than a placeholder)

**If GREENFIELD is detected**, print exactly:

```
Greenfield/new projects aren't supported in /bx:webdesign v1 (refactor only). Exiting.
```

and stop the skill cleanly (no further passes).

---

## Pass 4 — App-Runnability Probe

Determines whether Playwright/screenshots/`extract-static-html` can run. Resolves `build_cmd` and `serve_cmd` from `package.json` scripts + framework defaults.

### Script resolution (check `package.json` `scripts` in this order)

**`serve_cmd` candidates** (first match wins):
1. `dev` → `npm run dev`
2. `start` → `npm run start`
3. `preview` → `npm run preview`
4. Framework default if no script: Astro `npx astro dev`, Hugo `hugo server`, Jekyll `bundle exec jekyll serve`

**`build_cmd` candidates** (first match wins):
1. `build` → `npm run build`
2. `export` → `npm run export`
3. Framework default if no script: Astro `npx astro build`, Hugo `hugo`, Jekyll `bundle exec jekyll build`

### Runnability check

Set `app_runnable: true` only if **all** of the following hold:
1. At least one of `build_cmd` or `serve_cmd` resolved (non-null), AND
2. `node_modules/` exists (for Node projects) **OR** dependencies are otherwise installed, AND
3. A `.env.example` or `.env.sample` file does **not** exist without a corresponding `.env` or `.env.local` — if an env-example file is present but no filled-in counterpart exists, the app likely needs env config that isn't supplied → set `app_runnable: false`.

Otherwise set `app_runnable: false`.

**Do NOT actually run the build or dev server** during this probe — this is a static check only.

### Port resolution

After resolving `serve_cmd`, also resolve the dev-server `port` and record it in `state.json`. This value is used by Phase 1 screenshots and Phase 3 Playwright verification (`http://localhost:<port><route>`).

**Resolution order (first match wins):**

1. Check the dev/serve script's value in `package.json` for an explicit `--port <N>` flag (e.g. `"dev": "next dev --port 4000"` → `4000`).
2. Otherwise use the framework default:
   | Framework | Default port |
   |-----------|-------------|
   | Next.js | 3000 |
   | Nuxt | 3000 |
   | Remix | 3000 |
   | Gatsby | 8000 |
   | Vite | 5173 |
   | SvelteKit | 5173 |
   | Astro | 4321 |
   | Hugo | 1313 |
   | Jekyll | 4000 |
   | (fallback) | 3000 |

> If the dev server logs a different port at startup during Phase 1 (Step 3.1), prefer the logged port over the value resolved here. Update `state.json["port"]` if it differs.

### State written to `state.json`
```json
{
  "build_cmd": "npm run build",
  "serve_cmd": "npm run dev",
  "app_runnable": true,
  "port": 3000
}
```

Set `build_cmd`/`serve_cmd` to `null` (not omitted) when a value cannot be resolved, so downstream steps can distinguish "not detected" from "not checked." `port` is always set to an integer (never null — falls back to `3000`).

### Degradation rule

**Three later steps depend on `app_runnable`:**
1. Before/after screenshots (Phase 1 + Phase 3) — requires Playwright + a live dev server
2. Playwright interaction checks (Phase 3 verification) — requires a live dev server
3. `extract-static-html` (Phase 1 page-content extraction) — requires a build output

When `app_runnable: false`:
- The skill **degrades to build-only verification** — it still injects styles and applies Stitch tokens, but skips all Playwright steps and screenshot comparisons.
- Print a warning with the detected-stack summary line (end of this file's passes) and again at the start of Phase 3.
- **Never hard-fail** on `app_runnable: false` — degrade gracefully.

---

## Output — Detected-Stack Summary Line

After all four passes complete, print a **one-line summary** before proceeding to Phase 1:

```
Detected: <framework> · styling: <styling_system> · app_runnable: <true|false>
```

Examples:
```
Detected: Next.js (app-router) · styling: tailwind · app_runnable: true
Detected: Hugo static site · styling: css-vars · app_runnable: false
Detected: React + react-router · styling: css-in-js · app_runnable: true
```

---

## Summary of `state.json` Keys Written by This Reference

| Key | Type | Set by Pass | Consumed by |
|-----|------|-------------|-------------|
| `styling_system` | string | Pass 2 | Phase 3 token injection |
| `build_cmd` | string \| null | Pass 4 | Phase 3 build verification |
| `serve_cmd` | string \| null | Pass 4 | Phase 1 screenshots, Phase 3 Playwright |
| `app_runnable` | boolean | Pass 4 | Phase 1 screenshots/extract-static-html, Phase 3 Playwright |
| `port` | integer | Pass 4 | Phase 1 `browser_navigate` (`http://localhost:<port><route>`), Phase 3 Playwright verification |
