# Design: `/bx:webdesign` — Stitch-driven web design refactor with safe injection

**Date:** 2026-06-06
**Status:** Approved (design), pending implementation plan
**Author:** Session with Claude

---

## Problem

There is no skill that **changes a web project's visual design language** (its UI/UX), as opposed to its code structure (`/bx:arch`), SEO (`/bx:seo`), or correctness (`/bx:review`). The user wants to take an existing web project and **totally re-skin it** — new colors, typography, spacing, layout, component styling — using **Google Stitch** as the design engine, **without breaking any functionality**.

The naive approach (let Stitch generate pages, copy its HTML over the existing files) destroys the app: Stitch emits **static mockup markup with no logic**, so a raw file replacement wipes every handler, API call, route, and piece of state. The hard, valuable problem is landing a new *visual* design onto *existing* pages while **preserving all behavior**.

Two facts make this tractable in 2026:

1. **Google ships an official Stitch MCP server** (`@_davideast/stitch-mcp`) plus an official **`google-labs-code/stitch-skills`** plugin (Claude-Code-compatible Agent Skills: `code-to-design`, `extract-design-md`, `generate-design`, `manage-design-system`, `react-components`, …). These do the Stitch-side heavy lifting through the MCP.
2. **None of Google's skills preserve existing app logic** — `react-components` generates *new* components from screens; it does not restyle an existing page in place. That gap is exactly the differentiated value `/bx:webdesign` provides.

So `/bx:webdesign` is a **thin orchestrator** over Google's engine that adds the layer Google's kit lacks: web-project detection, preserve-aware page briefs, **safe injection into existing code**, and **verification**.

---

## Decisions (locked with user)

1. **Stitch interaction:** **MCP-driven** (not manual copy-paste). `/bx:webdesign` drives Stitch through the Stitch MCP + Google's `stitch-skills`.
2. **Engine coupling:** **Reuse Google's `stitch-skills`** (thin orchestrator) — do *not* re-implement extraction/generation.
3. **Dependency model:** **Model A — separate install, detect & guide.** The user installs the Stitch MCP **and** the `stitch-skills` plugin via a one-time guided onboarding (`/bx:seo`-style). `/bx:webdesign` calls Google's skills via the Skill tool. The user's environment is openly aware of both. The **Stitch MCP setup is user-level in every model** (it is the user's Google credentials + GCP project + billing + Stitch API) and cannot be hidden or bundled — the skill can only detect and onboard it.
4. **Scope:** **Refactor-only v1.** Greenfield/new projects get a clean "not yet supported, coming in v2" exit. Mode detection mirrors `/bx:plan`'s GREENFIELD-vs-EXISTING split.
5. **Rollout model:** **Tokens-first, then page-by-page.** One global design-system/token commit, then a resumable per-page loop where each page is its own reviewable, verifiable, committable diff. (Rejected: big-bang all-at-once; per-page-independent tokens — both risk drift or unreviewable diffs.)
6. **Phase-1 prep:** **Claude drafts from the codebase, user refines.** Auto-enumerate routes/pages/components → draft a preserve-aware brief per page. (Rejected: light scaffold / per-page interview.)
7. **Verification:** **build/typecheck/test + Playwright behavior check + before/after screenshots**, per page, before commit. Pixel-identical regression is explicitly *not* the bar (visuals are supposed to change) — the bar is **functionality preserved**.
8. **Name:** **`bx:webdesign`** (not `design` — too broad, collides with "design doc"/system-design sense and sits ambiguously next to `bx:arch`/`bx:plan`; not `redesign` — under-covers future greenfield). Single lowercase token, fits convention, pairs conceptually with `bx:seo` (both web-only).

---

## Research foundation (authoritative formats)

All grounded in Google's official sources; the skill bundles these as a baseline reference **and** fetches the official prompting doc fresh at runtime (like `/bx:seo`) since Stitch evolves fast (major update 2026-03-18: 4 modes, Voice Canvas, portable design-system format).

**Sources:** [google-labs-code/stitch-skills](https://github.com/google-labs-code/stitch-skills) · [official prompting docs](https://stitch.withgoogle.com/docs/learn/prompting/) · [Google AI Dev forum prompt guide](https://discuss.ai.google.dev/t/stitch-prompt-guide/83844) · [stitch-mcp (davideast)](https://github.com/davideast/stitch-mcp) · [Stitch MCP setup guide](https://www.sotaaz.com/post/stitch-mcp-guide-en)

### Stitch prompt format (per-screen)
```
[One-line page purpose + vibe]

**PLATFORM:** Web, Desktop-first

**PAGE STRUCTURE:**
1. **Header:** <navigation + branding>
2. **Hero Section:** <headline, subtext, primary CTA>
3. **<Content Area>:** <component breakdown>
4. **Footer:** <links, legal>
```
**Critical multi-page consistency rule:** once a design system exists at the project level, **per-screen generation prompts contain layout/content/structure ONLY — never colors, fonts, roundness, or theme tokens.** This is the mechanism that prevents visual drift across pages. (Hex codes are acceptable only in *edit* prompts for precise tweaks.)

### DESIGN.md schema (the portable design system)
YAML frontmatter + semantic prose body:
- **frontmatter:** `name`, `colors:` (Material-3-style semantic token set — surface/on-surface/primary/secondary/tertiary/error + container/fixed/inverse variants), `typography:` (named styles → fontFamily/fontSize/fontWeight/lineHeight/letterSpacing), `rounded:` (radii scale), `spacing:` (4px baseline scale).
- **body:** Brand & Style · Colors · Typography · Layout & Spacing · Elevation & Depth · Shapes (semantic prose).
- `create_design_system_from_design_md` auto-populates Stitch's theme tokens directly from this frontmatter.

### Stitch MCP tool surface (consumed via Google's skills)
`list_projects`/`create_project`/`get_project` · `create_design_system_from_design_md`/`update_design_system`/`apply_design_system` · `generate_screen_from_text`/`generate_screen_from_image`/`edit_screens` · `get_screen` (returns a signed `htmlCode.downloadUrl` that must be fetched with `curl`, a `screenshot.downloadUrl`, and `data-stitch-id` attributes for re-sync). Generated HTML `<head>` carries a localized `tailwind.config` that must be merged with the project theme.

### Dynamic / JS-heavy pages (user requirement)
Stitch produces **static screens, no logic.** A dynamic page's brief therefore enumerates **each UI state as its own screen variant** (empty · loading · error · loaded · modal-open · …) and records the **explicit interactions** ("when user clicks Filter → dropdown panel slides in"). Those interactions document what Phase 3 must **preserve in code** — they are never delegated to Stitch.

### Iteration discipline (all sources agree)
One screen + one change per prompt; keep prompts under ~5000 chars; Stitch loses context across large edits; screenshot after each good step.

---

## Architecture

### Skill file structure
```
bx/skills/webdesign/
├── SKILL.md                       # orchestrator: setup-check → state-route → phase dispatch
└── references/
    ├── setup-stitch-mcp.md        # MCP + stitch-skills install/onboarding (detect-and-guide banner)
    ├── web-stack-detection.md     # web-project + styling-system + refactor/greenfield gate
    ├── phase1-extract.md          # route enumeration, preserve-briefs, code-to-design handoff
    ├── brief-format.md            # per-page brief schema incl. dynamic-state handling
    ├── phase2-design-review.md    # generate via Google skills + the visual-review checkpoint
    ├── phase3-inject.md           # tokens-first + per-page safe-restyle algorithm (the core)
    ├── verification.md            # build/test + Playwright behavior + before/after capture
    └── stitch-formats.md          # bundled DESIGN.md schema + prompt format + runtime fresh-fetch
```
Auto-discovered from `bx/skills/` — no `plugin.json` / `marketplace.json` edits. Frontmatter: `name: webdesign`, `disable-model-invocation: true`, `effort: high`. `allowed-tools` includes the `stitch*` MCP tools, the Playwright MCP tools (`mcp__plugin_playwright_playwright__*`), `Task`, `Skill`, Read/Write/Edit/Glob/Grep, and `Bash(npm:*)`/`Bash(npx:*)`/`Bash(git:*)`/`Bash(curl:*)`.

### Setup & dependency detection (one-time, `/bx:seo`-style)
On invocation, detect: (a) is the **Stitch MCP** configured (are `stitch*` tools available)? (b) is **`google-labs-code/stitch-skills`** installed? If either is missing, emit a setup banner with the exact commands —
```
npx @_davideast/stitch-mcp init           # wizard: gcloud, Google login, GCP project, enable Stitch API
claude mcp add -e GOOGLE_CLOUD_PROJECT=<id> -s user stitch -- npx -y @_davideast/stitch-mcp proxy
npx plugins add google-labs-code/stitch-skills --scope project --target claude-code
```
— note the GCP-project/billing/Stitch-API prerequisites, then exit cleanly. A sentinel (`.webdesign/.setup-shown`) suppresses repeat banners.

### State model — `.webdesign/` working folder (gitignored)
Named `.webdesign/` (not `.design/`) to avoid colliding with Google skills' own `.stitch/` scratch directory. Sentinel-marked into `.gitignore` like `/bx:seo` does.
```
.webdesign/
├── state.json        # {phase, mode, styling_system, stitch_project_id, design_direction,
│                     #  tokens_applied, pages:[{route, file, states[], status}]}
├── SITE.md           # "constitution" (Google's stitch-loop pattern): identity, visual language,
│                     #  live sitemap + per-page status, stitch_project_id  ← long-term memory
├── briefs/<page>.md  # auto-drafted preserve-aware briefs (user refines)
├── before/<page>.png # Playwright baselines (verification + Stitch image refs)
└── after/<page>.png
```
`/bx:webdesign` reads `state.json` and **auto-routes** to the correct phase (Approach A: single auto-detecting command). Two escape hatches: `/bx:webdesign status` (print progress, take no action) and `/bx:webdesign page <name>` (re-run/force one page).

### Phase 1 — Extract & Stage *(Claude)*
1. **Step 0 — detect & gate.** Reuse `/bx:seo`'s web-project detection. Additionally detect the **styling system** (Tailwind / CSS-modules / styled-components / vanilla-extract / CSS-vars / theme file) — this determines where tokens land in Phase 3. Detect **refactor vs greenfield**; greenfield → print "not supported in v1" and exit. Print the detected stack.
2. **Enumerate routes** (stack-aware, reusing `/bx:seo`'s pathspec table) → draft a **preserve-aware brief per page** (purpose · **functionality to PRESERVE** · key components · UX notes · per-state list for dynamic pages).
3. **Capture `before/` screenshots** via Playwright (verification baseline + reusable as Stitch image references).
4. **Seed Stitch** — build the project, then delegate to Google's **`code-to-design`** (which chains `extract-static-html` → `extract-design-md` → `manage-design-system`): creates a Stitch project carrying the project's **current** DESIGN.md as a baseline. Persist `stitch_project_id` into `state.json` + `SITE.md`.
5. **Capture the new design direction** — a short interview (target vibe in words + optional inspiration URLs/screenshots as Stitch image refs). Reshape DESIGN.md toward it and call `update_design_system`. Stitch now holds the **new** design language.

### Phase 2 — Design & Review *(Claude via Google skills + user)*
- Per brief, delegate to Google's **`generate-design`** (`generate_screen_from_text`, **layout/content only**, design system applied at project level so no color/font drift).
- **Dynamic/JS-heavy pages:** generate **one screen per UI state**; record explicit interactions in the brief for Phase-3 preservation.
- **Mandatory human visual checkpoint:** emit a review card (Stitch project URL + what to review + how to tweak via voice / direct edits / "Claude, `edit_screens` to …"). The user approves when satisfied. The skill resumes cleanly on the next invocation via `state.json`. (This is where the user's "handback / clear human instructions + clean resume" requirement lives in the MCP world — file-moving is unnecessary since the MCP transfers assets, but the human review-and-resume step remains explicit.)

### Phase 3 — Safe Inject & Verify *(Claude — the differentiated core)*
1. **`get_screen`** per approved screen → `curl` the signed `htmlCode.downloadUrl` + `screenshot.downloadUrl`.
2. **Tokens-first (one global commit):** merge the Stitch design-system tokens (including the localized `tailwind.config` from the generated HTML `<head>`) into the project's theme layer (location determined by the Step-0 styling system) → verify build → commit.
3. **Per-page loop (resumable):** read the existing page + the Stitch HTML/screenshot side-by-side; **restyle the existing page's markup/classes to match the new design while preserving every handler, API call, route, and piece of state**; keep `data-stitch-id` as comments for future re-sync; **verify** (build/typecheck/test + Playwright behavior check + `after/` screenshot vs `before/`); commit; update `SITE.md` live sitemap. Report "N of M pages done."
4. **Safety valve:** if a page's structure diverged too far to safely preserve logic, **flag it for manual handling** rather than risk clobbering behavior.

### What `/bx:webdesign` owns vs delegates
| Concern | Owner |
|---|---|
| Web-project + styling-system detection, refactor/greenfield gate | `bx:webdesign` |
| Route enumeration + preserve-aware briefs | `bx:webdesign` |
| Extract current design → seed Stitch | Google `code-to-design` |
| Design-system create/update | Google `manage-design-system` |
| Screen generation/edit | Google `generate-design` |
| **Safe injection into existing code (preserve logic)** | `bx:webdesign` |
| **Verification (build/test + Playwright + before/after)** | `bx:webdesign` |
| State / resumability / SITE.md | `bx:webdesign` |
Google's `react-components` is **not** used in the refactor path (it replaces rather than restyles); reserved as a possible v2 input for net-new screens.

---

## Out of scope (v1)

- **Greenfield / new projects** — clean "not yet supported" exit; v2.
- **Wholesale component replacement** — the skill restyles in place; it never swaps out working components.
- **Delegating behavior to Stitch** — Stitch only ever produces static visuals.
- **Auto-injecting unreviewed designs** — the human visual checkpoint is mandatory.
- **Re-implementing Google's extraction/generation** — reused via the plugin (Model A).
- **Non-web repos** — rejected silently in Step 0 (like `/bx:seo`).

## Risks / open questions (resolve in plan or note as accepted)

- **Stitch is experimental + evolving** — mitigated by a bundled baseline (`stitch-formats.md`) + runtime fresh-fetch of the official prompting doc, and by pinning the expected `stitch-skills` skill names.
- **Generation quota** (~350 screens/month standard tier) — surface remaining budget; dynamic pages multiply screen count (one per state).
- **Build-output dependency** — `extract-static-html` needs a built app; the skill must run/locate the build (or dev server) in Phase 1.
- **Styling-system coverage** — token-merge logic must handle Tailwind / CSS-modules / styled-components / CSS-vars; start with the project's detected system, flag unsupported ones.
- **Playwright behavior checks** are heuristic (load page, assert key elements/flows) — they reduce but don't eliminate the need for the human review checkpoint.

## Success criteria

- A user with the Stitch MCP + `stitch-skills` installed can run `/bx:webdesign` on an existing web project and, across resumable sessions, land a **completely new visual design** with **every page's functionality intact** (build/test/Playwright green per page).
- Step 0 correctly detects web-project + styling system, and exits cleanly on greenfield and non-web repos.
- Per-page commits each preserve handlers/API/state; no page is committed with failing verification.
- Multi-page output shows **no visual drift** (single project-level design system; layout-only per-page prompts).
- Dynamic pages are handled as per-state screens with interactions preserved in code.
- Missing dependencies produce a clear guided-setup banner, never a silent failure.
- The skill is resumable: re-running `/bx:webdesign` always continues from the correct phase; `status` and `page <name>` work as specified.
