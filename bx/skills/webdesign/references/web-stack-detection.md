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

> **Signal source:** mirrors `/bx:seo` Step 0 exactly — the authoritative signal list lives there.

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
| 1 | Tailwind CSS | `tailwind.config.{js,ts,cjs,mjs}` exists **OR** `@tailwind` directives in any CSS file | `tailwind` |
| 2 | CSS-in-JS | `styled-components` or `@emotion/react` / `@emotion/styled` in `package.json` | `css-in-js` |
| 3 | CSS Modules | Any `*.module.css` file in the project | `css-modules` |
| 4 | vanilla-extract | `@vanilla-extract/css` in `package.json` **OR** `*.css.ts` files | `vanilla-extract` |
| 5 | CSS custom properties | A theme/tokens file (e.g. `tokens.css`, `variables.css`, `theme.css`) **OR** `:root { --…` declarations in any CSS file | `css-vars` |
| 6 | Plain CSS | Fallback — CSS files present but none of the above | `plain-css` |

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
IF no source code files exist (only docs/config):
    -> GREENFIELD
ELSE IF package.json exists but no page/component/route files exist:
    -> GREENFIELD
ELSE:
    -> EXISTING (proceed)
```

Signals that confirm an EXISTING project (at least one must be present):
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

Set `app_runnable: true` only if **both**:
1. At least one of `build_cmd` or `serve_cmd` resolved (non-null), AND
2. A quick non-blocking check suggests it can run:
   - `node_modules/` exists (for Node projects) **OR** dependencies are otherwise installed
   - No obviously fatal configuration missing (e.g. required env vars documented as mandatory in README)

Otherwise set `app_runnable: false`.

**Do NOT actually run the build or dev server** during this probe — this is a static check only.

### State written to `state.json`
```json
{
  "build_cmd": "npm run build",
  "serve_cmd": "npm run dev",
  "app_runnable": true
}
```

Set to `null` (not omitted) when a value cannot be resolved, so downstream steps can distinguish "not detected" from "not checked."

### Degradation rule

**Three later steps depend on `app_runnable`:**
1. Before/after screenshots (Phase 1 + Phase 5) — requires Playwright + a live dev server
2. Playwright interaction checks (Phase 5 verification) — requires a live dev server
3. `extract-static-html` (Phase 2 page-content extraction) — requires a build output

When `app_runnable: false`:
- The skill **degrades to build-only verification** — it still injects styles and applies Stitch tokens, but skips all Playwright steps and screenshot comparisons.
- Print a warning at the end of Step 0 and again at the start of Phase 5.
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
| `build_cmd` | string \| null | Pass 4 | Phase 5 build verification |
| `serve_cmd` | string \| null | Pass 4 | Phase 1 screenshots, Phase 5 Playwright |
| `app_runnable` | boolean | Pass 4 | Phase 1 screenshots, Phase 2 extract-static-html, Phase 5 Playwright |
