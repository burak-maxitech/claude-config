# `/bx:webdesign` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. When authoring the markdown skill files, also consult **superpowers:writing-skills** for skill-quality conventions (frontmatter, description/when_to_use, reference-file structure).

**Goal:** Build `/bx:webdesign` — a resumable, web-only, refactor-mode Claude Code skill that totally re-skins an existing web project via Google Stitch (driven through the Stitch MCP + Google's `stitch-skills`), while preserving all functionality.

**Architecture:** A thin orchestrator skill under `bx/skills/webdesign/` (one `SKILL.md` + 8 `references/*.md`). `SKILL.md` detects setup → reads `.webdesign/state.json` → auto-routes a phase state machine (Setup → Phase 1 Extract → Phase 2 Design&Review → Phase 3 Inject&Verify). It **delegates** Stitch-side work (extraction, design-system, generation) to Google's official skills via the Skill tool, and **owns** web/styling detection, preserve-aware briefs, safe code injection, verification, and resumable state. The skill's *files* live in this repo; the skill *operates* on a separate target web project (where it creates `.webdesign/`, a `webdesign/<date>` branch, and per-page commits).

**Tech Stack:** Markdown skill files (YAML frontmatter + prose). Runtime tools the skill uses: Stitch MCP (`stitch*` tools), Playwright MCP (`mcp__plugin_playwright_playwright__*`), Google `stitch-skills` (invoked via Skill tool), Bash (`npm`/`npx`/`git`/`curl`). No build step for the skill itself; "tests" are structural validation + a gated end-to-end dogfood.

**Reference spec:** `docs/superpowers/specs/2026-06-06-bx-webdesign-design.md` (11 locked decisions). Read it before starting.

**Authoring conventions (match the repo):** Study `bx/skills/seo/SKILL.md` (web-only detection, `disable-model-invocation: true`, multi-step orchestration, setup-banner pattern, `effort: high`) and `bx/skills/plan/SKILL.md` (interview + mode detection) before writing. Match their voice, heading style, and reference-file split.

**Important environment note:** The skill files are edited in this repo (`bx/skills/webdesign/`), but the *installed* plugin is served from the plugin cache. After the files exist, the skill becomes invocable only after a `/plugin update bx` (or a fresh `cc` launch). All "dogfood" steps assume that refresh has happened and the Stitch MCP + `stitch-skills` are installed in the target project.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `bx/skills/webdesign/SKILL.md` | Orchestrator: setup-check → state-route → phase dispatch; defines args (`status`, `page <name>`), the phase state machine, and `state.json` read/write contract. |
| `bx/skills/webdesign/references/stitch-formats.md` | **Foundational.** Canonical Stitch artifacts: per-screen prompt format, DESIGN.md schema, `update_design_system` knob enums, MCP tool surface, vibe→knob mapping table, dynamic-state guidance, iteration discipline, runtime fresh-fetch instructions. Every other reference cites this. |
| `bx/skills/webdesign/references/setup-stitch-mcp.md` | Dependency detection (Stitch MCP + `stitch-skills`) + the guided setup banner (exact commands) + sentinel idempotency. |
| `bx/skills/webdesign/references/web-stack-detection.md` | Web-project gate, styling-system detection, refactor/greenfield gate, app-runnability probe (`build_cmd`/`serve_cmd`/`app_runnable`). |
| `bx/skills/webdesign/references/brief-format.md` | Per-page brief schema (purpose · functionality-to-PRESERVE · components · UX · per-state list) + the "brief PRESERVE list = verification contract" rule. |
| `bx/skills/webdesign/references/phase1-extract.md` | Phase 1 steps: route enumeration, briefs, before-screenshots, work-branch, `code-to-design` seed, flexible vibe-setting (decision 9). |
| `bx/skills/webdesign/references/phase2-design-review.md` | Phase 2: quota pre-flight, `generate-design` per brief (per-state for dynamic), mandatory visual-review checkpoint card. |
| `bx/skills/webdesign/references/phase3-inject.md` | Phase 3: tokens-first global commit, per-page safe-restyle loop (preserve logic+content+assets, restyle within existing breakpoints, verify, failure rollback, safety valve). |
| `bx/skills/webdesign/references/verification.md` | Build/test detection, Playwright behavior check (assertions = brief PRESERVE list), before/after capture, graceful build-only degradation. |
| `README.md` (modify) | Add `/bx:webdesign` to the skills list/table (9 → 10 skills). |
| `workflow.md` (modify) | Add a short `/bx:webdesign` usage note. |

> CLAUDE.md skill-count / status updates are intentionally **deferred to `/bx:save`** at session end — do not hand-edit them here.

Build order: scaffold + foundational formats first (Tasks 1–2), then the leaf reference files (Tasks 3–9), then wire the orchestrator (Task 10), then integrate + validate (Tasks 11–12).

---

## Task 1: Scaffold the skill + SKILL.md frontmatter & skeleton

**Files:**
- Create: `bx/skills/webdesign/SKILL.md`

- [ ] **Step 1: Create `SKILL.md` with frontmatter + top matter only**

Write exactly this frontmatter and intro (the orchestrator body is filled in Task 10):

```markdown
---
name: webdesign
description: "Totally re-skins an existing web project's visual design via Google Stitch (driven through the Stitch MCP + Google's stitch-skills), while preserving all functionality. Extracts the current design, applies a new design language, and safely injects it page-by-page with verification."
when_to_use: When the user wants to redesign, re-skin, restyle, or totally change the UI/UX / look-and-feel / design language of an existing web project using Google Stitch. Web projects only (rejects non-web repos). Refactor of an existing project only in v1 — greenfield/new projects exit with a 'not yet supported' note. Distinct from /bx:arch (code structure) and /bx:seo (search). NOT for fixing bugs or behavior.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Glob, Grep, Skill, Task, WebFetch, Bash(git:*), Bash(npm:*), Bash(npx:*), Bash(curl:*), Bash(find:*), Bash(ls:*), Bash(node:*), mcp__plugin_playwright_playwright__browser_navigate, mcp__plugin_playwright_playwright__browser_take_screenshot, mcp__plugin_playwright_playwright__browser_snapshot, mcp__plugin_playwright_playwright__browser_click, mcp__plugin_playwright_playwright__browser_fill_form, mcp__plugin_playwright_playwright__browser_console_messages, mcp__plugin_playwright_playwright__browser_wait_for, mcp__plugin_playwright_playwright__browser_close
effort: high
argument-hint: "[status | page <name>] [--force-setup]"
---

# /bx:webdesign — Stitch-driven Web Design Refactor

Totally re-skin an existing **web** project's visual design language using **Google Stitch**, without breaking any functionality. This skill is a thin orchestrator: it **delegates** the Stitch-side work (design extraction, design system, screen generation) to Google's official `stitch-skills` (via the Stitch MCP), and **owns** the parts Google's kit lacks — web-project detection, preserve-aware page briefs, **safe injection into existing code**, and **verification**.

**Web projects only.** Rejects non-web repos. **Refactor only in v1** — greenfield/new projects get a clean "not yet supported" exit.

**Companion skills:** `/bx:seo` (web audit) · `/bx:plan` (feature planning) · `/bx:save` (end-of-session save).

> ⚠️ Stitch produces **static visuals, no logic.** This skill therefore *restyles existing pages in place* — it never replaces working components, and never delegates behavior to Stitch.

---

<!-- ORCHESTRATOR BODY ADDED IN TASK 10 -->
```

- [ ] **Step 2: Verify frontmatter is valid YAML and required keys are present**

Run (PowerShell):
```powershell
$f = "bx/skills/webdesign/SKILL.md"
$lines = Get-Content $f
($lines[0] -eq '---') ; ($lines | Select-String -SimpleMatch '---').LineNumber[1]   # second --- closes frontmatter
$lines | Select-String -Pattern '^(name|description|when_to_use|disable-model-invocation|allowed-tools|effort|argument-hint):'
```
Expected: first line is `---`; a closing `---` exists; all seven frontmatter keys print. `name:` value is exactly `webdesign`.

- [ ] **Step 3: Confirm it matches repo conventions**

Run: `Read bx/skills/seo/SKILL.md` (frontmatter only) and confirm `webdesign`'s frontmatter uses the same key style (`disable-model-invocation: true`, `effort: high`, quoted `description`). Fix any divergence.

- [ ] **Step 4: Commit**

```bash
git -C . add bx/skills/webdesign/SKILL.md
git -C . commit -m "feat(webdesign): scaffold skill + frontmatter"
```

---

## Task 2: `references/stitch-formats.md` (foundational — canonical Stitch artifacts)

**Files:**
- Create: `bx/skills/webdesign/references/stitch-formats.md`

This file is the single source of truth for Stitch's exact formats; later references link to it instead of duplicating. Embed the content below **verbatim** (it is researched from Google's official `stitch-skills` repo + docs).

- [ ] **Step 1: Create the file with these exact sections**

````markdown
# Stitch canonical formats

> Bundled baseline. Stitch evolves fast — at the **start of Phase 1**, fetch the official prompting doc fresh and let it supersede anything here that diverges:
> `WebFetch https://stitch.withgoogle.com/docs/learn/prompting/ "Extract the current recommended prompt structure, frameworks, and any changes to design-system handling."`
> If the fetch fails, proceed with this baseline and note it in the run summary.

## Per-screen generation prompt format

Once a design system exists at the project level, **generation prompts contain layout/content/structure ONLY — never colors, fonts, roundness, or theme tokens.** This is the mechanism that prevents visual drift across pages. (Hex codes are acceptable only in *edit* prompts for precise tweaks.)

```
[One-line page purpose + vibe]

**PLATFORM:** Web, Desktop-first

**PAGE STRUCTURE:**
1. **Header:** <navigation + branding>
2. **Hero Section:** <headline, subtext, primary CTA>
3. **<Content Area>:** <component-by-component breakdown>
4. **Footer:** <links, legal>
```

For **edits** to an existing screen, be specific and single-purpose: location + change. One screen + one change per prompt; keep prompts under ~5000 chars; Stitch loses context across large edits; screenshot after each good step.

## DESIGN.md schema (portable design system)

YAML frontmatter (drives Stitch theme tokens via `create_design_system_from_design_md`) + semantic prose body.

```markdown
---
name: <Design System Name>
colors:            # Material-3-style semantic tokens (hex). Full set includes:
  surface: '#...'  # surface, surface-dim/bright, surface-container[-low|-high|-highest],
  on-surface: '#...'  # on-surface, on-surface-variant, outline, outline-variant,
  primary: '#...'  # primary, on-primary, primary-container, on-primary-container, inverse-primary,
  secondary: '#...'  # secondary + on/container variants, tertiary + variants,
  error: '#...'    # error + on/container, plus *-fixed / *-fixed-dim / on-*-fixed[-variant],
  background: '#...'  # background, on-background, surface-variant
typography:        # named styles, each: fontFamily / fontSize / fontWeight / lineHeight / letterSpacing
  display-lg: { fontFamily: Inter, fontSize: 48px, fontWeight: '800', lineHeight: 56px, letterSpacing: -0.02em }
  headline-md: { ... }
  body-base: { ... }
  label-caps: { ... }
rounded:           # radii scale
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:           # 4px baseline
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
---

## Brand & Style
<personality, design philosophy>
## Colors
<semantic color roles>
## Typography
<font choices + why>
## Layout & Spacing
<grid model, baseline rhythm, touch targets>
## Elevation & Depth
<shadow/glass hierarchy>
## Shapes
<corner/shape language>
```

## `update_design_system` theme knobs (enums)

- `colorMode`: `LIGHT` | `DARK` (REQUIRED)
- `headlineFont` / `bodyFont` / `labelFont`: one of `INTER, ROBOTO, OPEN_SANS, LATO, MONTSERRAT, NOTO_SANS, NOTO_SERIF, PLUS_JAKARTA_SANS, BE_VIETNAM_PRO` (headline+body REQUIRED; label optional → defaults to body)
- `roundness`: `ROUND_FOUR` | `ROUND_EIGHT` | `ROUND_TWELVE` | `ROUND_FULL` (REQUIRED)
- `customColor`: primary/seed brand color, hex (REQUIRED)
- `colorVariant`: `FIDELITY` | `TONAL` | `VIBRANT` | `EXPRESSIVE` | `CONTENT` | `MONOCHROME` | `FRUIT_SALAD` | `RAINBOW` (optional)
- `overridePrimaryColor` / `overrideSecondaryColor` / `overrideTertiaryColor` / `overrideNeutralColor`: hex (optional)
- `designMd`: full DESIGN.md markdown string (optional)
- Omit the legacy `font` field (causes "invalid argument").

> Prefer `create_design_system_from_design_md` (auto-populates all tokens from DESIGN.md frontmatter) over hand-setting knobs. Use `update_design_system` only for targeted knob overrides.

## Vibe → design-system-knob mapping (starter table — tune per project)

Used by Phase-1 decision-9 path (a) to translate the user's vibe words into knobs.

| Vibe words | colorVariant | roundness | headline/body font feel |
|---|---|---|---|
| elegant, refined, luxury | EXPRESSIVE or TONAL | ROUND_TWELVE | serif headline (NOTO_SERIF) + INTER body |
| minimal, simple, clean | MONOCHROME or CONTENT | ROUND_EIGHT | INTER / PLUS_JAKARTA_SANS |
| professional, trustworthy, corporate | FIDELITY or TONAL | ROUND_EIGHT | INTER / ROBOTO |
| playful, fun, friendly | VIBRANT or RAINBOW | ROUND_FULL | BE_VIETNAM_PRO / PLUS_JAKARTA_SANS |
| warm, inviting, artisanal | EXPRESSIVE | ROUND_TWELVE | LATO / MONTSERRAT |
| bold, energetic, high-performance | VIBRANT | ROUND_FOUR | MONTSERRAT / INTER (heavy weights) |
| retro, vintage | FRUIT_SALAD or EXPRESSIVE | ROUND_FOUR | NOTO_SERIF / LATO |

`colorMode` (LIGHT/DARK) and `customColor` (seed hex) come from the user's stated direction or a preserved brand color. This table is a starting point — always show the chosen knobs to the user before applying.

## Stitch MCP tool surface (called via Google's stitch-skills)

- Projects: `list_projects`, `create_project`, `get_project`
- Design system: `list_design_systems`, `create_design_system_from_design_md`, `update_design_system`, `apply_design_system`
- Screens: `generate_screen_from_text`, `generate_screen_from_image`, `edit_screens`, `get_screen`
- `get_screen` returns: `htmlCode.downloadUrl` (a **signed URL — fetch with `curl`**), `screenshot.downloadUrl`, `deviceType` (usually `DESKTOP`, 2560px base), and `data-stitch-id` attributes on elements (preserve as comments for future re-sync). The generated HTML `<head>` carries a localized `tailwind.config` that must be merged with the project theme.

## Google stitch-skills delegated to (invoke via the Skill tool)

| Need | Skill |
|---|---|
| Existing code → seeded Stitch project | `stitch::code-to-design` (chains the three below) |
| Standalone HTML from build output | `stitch::extract-static-html` |
| Source → DESIGN.md | `stitch::extract-design-md` |
| Upload + create design system | `stitch::manage-design-system` |
| Generate / edit screens | `stitch::generate-design` |

> `stitch::react-components` is **NOT** used in the refactor path (it generates *new* components rather than restyling existing ones).

## Dynamic / JS-heavy pages

Stitch makes **static screens, no logic.** For a dynamic page, generate **one screen per UI state** (empty · loading · error · loaded · modal-open · …) and record the **explicit interactions** ("when user clicks Filter → dropdown panel slides in") in the brief. Those interactions document what Phase 3 must **preserve in code** — they are never delegated to Stitch.
````

- [ ] **Step 2: Verify required sections exist**

Run: `Grep -n "^## " bx/skills/webdesign/references/stitch-formats.md`
Expected: headings include `Per-screen generation prompt format`, `DESIGN.md schema (portable design system)`, `update_design_system theme knobs (enums)`, `Vibe → design-system-knob mapping`, `Stitch MCP tool surface`, `Google stitch-skills delegated to`, `Dynamic / JS-heavy pages`.

- [ ] **Step 3: Commit**

```bash
git -C . add bx/skills/webdesign/references/stitch-formats.md
git -C . commit -m "feat(webdesign): canonical Stitch formats reference"
```

---

## Task 3: `references/setup-stitch-mcp.md` (dependency detection + guided onboarding)

**Files:**
- Create: `bx/skills/webdesign/references/setup-stitch-mcp.md`

- [ ] **Step 1: Create the file**

It must specify, in prose + code blocks:

1. **Detection** (run at the top of every invocation):
   - Stitch MCP present? → check whether any `stitch*` tool is available in the current tool set (the orchestrator knows its available tools). If absent → MCP not configured.
   - `stitch-skills` installed? → attempt to confirm the `stitch::code-to-design` skill is listed among available skills. If absent → plugin not installed.
2. **The setup banner** — printed verbatim when either is missing, then **exit cleanly** (do not proceed). Include exactly:
   ````markdown
   ## ⚙️ One-time setup needed for /bx:webdesign

   This skill drives Google Stitch through its MCP + Google's official skills. Set up once:

   1. Install + auth the Stitch MCP (interactive wizard: gcloud, Google login, GCP project, enable Stitch API):
      ```
      npx @_davideast/stitch-mcp init
      claude mcp add -e GOOGLE_CLOUD_PROJECT=<your-gcp-project> -s user stitch -- npx -y @_davideast/stitch-mcp proxy
      ```
   2. Install Google's Stitch skills:
      ```
      npx plugins add google-labs-code/stitch-skills --scope project --target claude-code
      ```

   Prerequisites: a GCP project with **billing enabled** and the **Stitch API enabled**, and Owner/Editor on it.
   Re-run `/bx:webdesign` once both are done.
   ````
3. **Idempotency** — write a sentinel `.webdesign/.setup-shown` after first banner so repeat runs in the same project don't re-spam (but still detect + exit if deps remain missing). `--force-setup` re-prints regardless.
4. State which of the two is missing specifically (don't show both commands if only one is absent).

- [ ] **Step 2: Verify the exact commands are present**

Run: `Grep -n "stitch-mcp init|claude mcp add|stitch-skills" bx/skills/webdesign/references/setup-stitch-mcp.md`
Expected: all three command fragments appear.

- [ ] **Step 3: Commit**

```bash
git -C . add bx/skills/webdesign/references/setup-stitch-mcp.md
git -C . commit -m "feat(webdesign): Stitch MCP + stitch-skills setup detection & banner"
```

---

## Task 4: `references/web-stack-detection.md` (web gate, styling system, runnability)

**Files:**
- Create: `bx/skills/webdesign/references/web-stack-detection.md`

- [ ] **Step 1: Create the file**

It must specify four detection passes, runnable in one parallel turn where possible:

1. **Web-project gate** — reuse `/bx:seo` Step 0 signals (read `bx/skills/seo/SKILL.md` "Step 0 — Detect Web Project + Stack" and mirror the framework/static/server-rendered signal list). Non-web → print `Not a web project — /bx:webdesign only refactors web projects. Exiting.` and stop.
2. **Styling-system detection** — determine where tokens will land in Phase 3. Detect (in priority order): Tailwind (`tailwind.config.{js,ts,cjs,mjs}` / `@tailwind` directives) → `tailwind`; CSS-in-JS (`styled-components`, `@emotion`) → `css-in-js`; CSS Modules (`*.module.css`) → `css-modules`; vanilla-extract (`@vanilla-extract`) → `vanilla-extract`; a theme/tokens file or `:root{--…}` CSS variables → `css-vars`; else `plain-css`. Record `styling_system`. Unknown → set `styling_system: unknown` and warn that token-merge will be best-effort.
3. **Refactor vs greenfield gate** — greenfield if there are no renderable pages/routes/components (only config/docs), mirroring `/bx:plan`'s GREENFIELD detection. Greenfield → print `Greenfield/new projects aren't supported in /bx:webdesign v1 (refactor only). Exiting.` and stop.
4. **App-runnability probe** — from `package.json` scripts (and framework defaults), resolve `build_cmd` (e.g. `npm run build`) and `serve_cmd` (e.g. `npm run dev`/`preview`/`start`). Set `app_runnable: true` only if a build or serve command exists and a quick non-blocking check suggests it can run; else `false`. Record `build_cmd`, `serve_cmd`, `app_runnable` in `state.json`. Note explicitly: **three later steps depend on `app_runnable`** (before/after screenshots, Playwright checks, `extract-static-html`); when false, the skill degrades to **build-only verification** and skips Playwright/screenshots with a warning — never hard-fails.

Output: a one-line detected-stack summary (stack · styling_system · app_runnable) printed by Step 0.

- [ ] **Step 2: Verify the four passes + the degradation rule are documented**

Run: `Grep -n "styling_system|app_runnable|greenfield|Non-web|build-only" bx/skills/webdesign/references/web-stack-detection.md`
Expected: all five tokens appear.

- [ ] **Step 3: Commit**

```bash
git -C . add bx/skills/webdesign/references/web-stack-detection.md
git -C . commit -m "feat(webdesign): web/styling/runnability detection reference"
```

---

## Task 5: `references/brief-format.md` (per-page brief schema)

**Files:**
- Create: `bx/skills/webdesign/references/brief-format.md`

- [ ] **Step 1: Create the file with this exact brief template + rules**

````markdown
# Per-page brief format

Claude auto-drafts one brief per page from the codebase; the user refines it before generation. The brief is BOTH the Stitch-generation input AND the Phase-3 verification contract.

## Template (`.webdesign/briefs/<page>.md`)

```markdown
---
page: <slug>
route: <url-path>
file: <source/file/path>
device: desktop   # v1 restyles within existing breakpoints; Stitch generates desktop
states: [default] # add empty/loading/error/loaded/modal-open for dynamic pages
---

## Purpose
<what this page is for, who uses it, the user intent>

## Functionality to PRESERVE   ← this list IS the verification contract
- <handler / API call / route / state / form / interaction that MUST keep working>
- <e.g. "submit button POSTs /api/contact and shows success toast">
- <e.g. "filter dropdown updates the results list client-side">

## Key components
- <component → what it does>

## UX notes / new-design intent
- <layout hierarchy, emphasis, what the redesign should improve>

## States (dynamic pages only)
- default: <description>
- empty: <description>
- loading: <description>
- error: <description>
- modal-open: <description>
```

## Rules
1. **Functionality to PRESERVE** is the most important section — it drives both what Phase 3 must keep and the exact Playwright assertions in verification (see `verification.md`). Be concrete and behavioral.
2. For **dynamic/JS-heavy pages**, enumerate each meaningful UI state in `states:` — each becomes a separate Stitch screen (see `stitch-formats.md` "Dynamic / JS-heavy pages").
3. Briefs describe **structure + content + behavior** — never colors/fonts (those live in the project-level design system).
4. Keep real content/copy intent in the brief; the redesign reuses the page's real content, not Stitch placeholders.
````

- [ ] **Step 2: Verify**

Run: `Grep -n "Functionality to PRESERVE|verification contract|states \[|device: desktop" bx/skills/webdesign/references/brief-format.md`
Expected: the PRESERVE heading, the "verification contract" phrase, the `states:` field, and the device line all appear.

- [ ] **Step 3: Commit**

```bash
git -C . add bx/skills/webdesign/references/brief-format.md
git -C . commit -m "feat(webdesign): per-page brief format reference"
```

---

## Task 6: `references/phase1-extract.md` (Phase 1 procedure)

**Files:**
- Create: `bx/skills/webdesign/references/phase1-extract.md`

- [ ] **Step 1: Create the file documenting Phase 1 as ordered steps**

Encode exactly the spec's Phase 1, each step concrete:

1. **Step 0 detect & gate + work branch** — run `web-stack-detection.md`; on pass, create/resume the `webdesign/<date>` branch (`git checkout -b webdesign/<YYYY-MM-DD>` first run; record `branch` in `state.json`; resumed runs `git checkout` the recorded branch). Use today's date from the environment.
2. **Enumerate routes → draft briefs** — stack-aware route enumeration (reuse `/bx:seo`'s pathspec table from `bx/skills/seo/SKILL.md` Step 1.5.2). For each page, draft `.webdesign/briefs/<page>.md` per `brief-format.md`, reading the source to populate "Functionality to PRESERVE". Present the inventory; the user refines.
3. **Capture `before/` screenshots** — only if `app_runnable`: serve the app (`serve_cmd`) and use the Playwright MCP to screenshot each route to `.webdesign/before/<page>.png`. If not runnable, skip + warn.
4. **Seed Stitch** — if `app_runnable`, run `build_cmd`, then invoke `stitch::code-to-design` (Skill tool) to create a Stitch project carrying the project's **current** DESIGN.md as baseline. Persist `stitch_project_id` to `state.json` + `SITE.md`. (If not runnable, fall back to invoking `stitch::extract-design-md` on source + `stitch::manage-design-system` to seed the design system without static HTML, and note the limitation.)
5. **Capture the NEW design direction (flexible — decision 9)** — present the two paths and let the user pick:
   - **(a) Claude-led interview:** ask the vibe questions (elegant/simple/retro/audience/inspiration refs), map answers to knobs via the `stitch-formats.md` vibe→knob table, **show the chosen knobs for confirmation**, then apply via `stitch::manage-design-system` (`create_design_system_from_design_md` or `update_design_system`).
   - **(b) Stitch web canvas:** instruct the user to shape the design system at the printed Stitch project URL, then on resume read it back via `list_design_systems` and use that design-system ID.
   - State clearly: the new *direction* comes from this step; step 4's extraction only supplies structure + brand invariants (logo, a brand color) to optionally keep.
6. Set `phase` to `direction_set` and print the Phase-1 summary + next action.

- [ ] **Step 2: Verify**

Run: `Grep -n "webdesign/|code-to-design|list_design_systems|before/|stitch_project_id" bx/skills/webdesign/references/phase1-extract.md`
Expected: branch pattern, the `code-to-design` delegate, the read-back tool, screenshot path, and project-id persistence all appear.

- [ ] **Step 3: Commit**

```bash
git -C . add bx/skills/webdesign/references/phase1-extract.md
git -C . commit -m "feat(webdesign): Phase 1 extract & stage procedure"
```

---

## Task 7: `references/phase2-design-review.md` (Phase 2 procedure)

**Files:**
- Create: `bx/skills/webdesign/references/phase2-design-review.md`

- [ ] **Step 1: Create the file documenting Phase 2 as ordered steps**

1. **Quota pre-flight** — compute `estimated_screens = Σ(len(states) per page)` across all briefs; show it alongside the ~350/month free-tier budget and **ask the user to confirm before generating** (skip on explicit override). Warn that dynamic pages multiply the count.
2. **Generate per brief** — for each page (and each state), invoke `stitch::generate-design` (`generate_screen_from_text`) with a prompt built from the brief in the **layout/content-only** format from `stitch-formats.md` (no colors/fonts — the project design system handles those). Pass the design-system ID. Set `pages[].status = generated`. Record screen IDs.
3. **Mandatory visual-review checkpoint** — print a review card:
   ```
   ## 🎨 Review your new designs in Stitch
   Open: <stitch project URL>
   Review: <list of generated pages/states>
   Tweak: use Voice Canvas / direct edits in the canvas, OR tell me "edit <page> to <change>" and I'll call edit_screens.
   When you're happy, re-run /bx:webdesign to inject the approved designs.
   ```
   Set `phase = review_pending` and **stop** (resumable). On resume with `phase = review_pending`, ask "approved?" — if yes, advance to Phase 3; if changes requested, route through `edit_screens` and re-present.

- [ ] **Step 2: Verify**

Run: `Grep -n "estimated_screens|generate_screen_from_text|review_pending|edit_screens" bx/skills/webdesign/references/phase2-design-review.md`
Expected: all four appear.

- [ ] **Step 3: Commit**

```bash
git -C . add bx/skills/webdesign/references/phase2-design-review.md
git -C . commit -m "feat(webdesign): Phase 2 design & review procedure"
```

---

## Task 8: `references/phase3-inject.md` (Phase 3 — the safe-injection core)

**Files:**
- Create: `bx/skills/webdesign/references/phase3-inject.md`

- [ ] **Step 1: Create the file documenting Phase 3 as ordered steps**

State up front: **all Phase-3 commits land on the `webdesign/<date>` branch** (decision 11).

1. **Fetch approved screens** — for each approved screen, `get_screen` → `curl` the signed `htmlCode.downloadUrl` to a temp file + `screenshot.downloadUrl` to `.webdesign/after/<page>-<state>.png`. (Signed URLs require `curl`, not WebFetch.)
2. **Tokens-first (one global commit)** — merge the Stitch design-system tokens into the project theme layer at the location dictated by `styling_system`:
   - `tailwind`: merge the generated `<head>` `tailwind.config` + DESIGN.md tokens into the project `tailwind.config`.
   - `css-vars`/`plain-css`: write the tokens as CSS custom properties in the theme/`:root` stylesheet.
   - `css-in-js`/`css-modules`/`vanilla-extract`: update the theme object/token file.
   - `unknown`: best-effort + warn.
   Then run `build_cmd` to verify; commit `tokens: apply new design system`. Set `tokens_applied = true`, `phase = tokens_injected`.
3. **Per-page loop (resumable)** — for each page with `status != verified`:
   a. Read the existing page source + the Stitch HTML + `after/` screenshot side-by-side.
   b. **Restyle the existing page's markup/classes to match the new design while preserving every handler, API call, route, and piece of state.** Preservation also covers **the page's real content/copy and existing images/assets** — discard Stitch's placeholder text + stock images; adopt only its visual structure/styling. Apply the new visual language **within the page's existing responsive breakpoints** (decision 10). Keep `data-stitch-id` values as comments for future re-sync.
   c. **Verify** per `verification.md`: build/typecheck/test + a Playwright behavior check whose assertions are the brief's *Functionality to PRESERVE* list + `after/` vs `before/` capture (build-only when `app_runnable` is false). Set `status = injected` then, on green, `verified`.
   d. **On green:** commit `webdesign: restyle <page>`; update `SITE.md` live sitemap.
   e. **On failure:** `git restore` the page's uncommitted changes (clean tree), set `status = failed`, surface the reason, and **continue to the next page** (retry later via `/bx:webdesign page <name>`).
   f. **Safety valve:** if the existing structure diverged too far to preserve logic safely, set `status = manual` and skip rather than risk clobbering behavior.
4. When all pages are `verified`/`manual`/`failed`, set `phase = done` and print a final report: `N verified, K manual, J failed` + the branch name + suggested next step (review the branch, run tests, merge).

- [ ] **Step 2: Verify**

Run: `Grep -n "Tokens-first|git restore|status = failed|within the page's existing responsive|data-stitch-id|placeholder" bx/skills/webdesign/references/phase3-inject.md`
Expected: all six appear.

- [ ] **Step 3: Commit**

```bash
git -C . add bx/skills/webdesign/references/phase3-inject.md
git -C . commit -m "feat(webdesign): Phase 3 safe-injection core procedure"
```

---

## Task 9: `references/verification.md` (verification procedure)

**Files:**
- Create: `bx/skills/webdesign/references/verification.md`

- [ ] **Step 1: Create the file**

Document the per-page verification used by Phase 3:

1. **Static checks** — run, in order, whichever exist (detect from `package.json` scripts): typecheck (`tsc --noEmit` / `npm run typecheck`), build (`build_cmd`), tests (`npm test` / detected runner). Any failure → verification fails.
2. **Playwright behavior check (only if `app_runnable`)** — serve the app, navigate to the page's route, and assert each item in the brief's **Functionality to PRESERVE** list resolves: required elements render, key flows work (e.g. submit a form and assert the success signal; click a control and assert the expected DOM change), no uncaught console errors. Map each PRESERVE bullet to a concrete assertion.
3. **Before/after capture (only if `app_runnable`)** — screenshot the restyled page to `.webdesign/after/<page>.png`; surface `before/` + `after/` paths for the human's visual confirmation (NOT a pixel-diff pass/fail — visuals are meant to change).
4. **Graceful degradation** — when `app_runnable` is false, run only the static checks ("build-only verification") and clearly note in the page's commit/report that runtime behavior was not auto-verified.
5. **Result contract** — verification returns green only if all applicable checks pass; Phase 3 commits only on green.

- [ ] **Step 2: Verify**

Run: `Grep -n "Functionality to PRESERVE|build-only|app_runnable|console errors" bx/skills/webdesign/references/verification.md`
Expected: all four appear.

- [ ] **Step 3: Commit**

```bash
git -C . add bx/skills/webdesign/references/verification.md
git -C . commit -m "feat(webdesign): verification procedure reference"
```

---

## Task 10: Wire the SKILL.md orchestrator body

**Files:**
- Modify: `bx/skills/webdesign/SKILL.md` (replace the `<!-- ORCHESTRATOR BODY ADDED IN TASK 10 -->` marker)

- [ ] **Step 1: Replace the marker with the orchestrator body**

The body must implement, in this order, referencing the files built above:

````markdown
## How to run

`/bx:webdesign` is a single auto-detecting command. It reads `.webdesign/state.json` and continues from wherever you left off. Two overrides:
- `/bx:webdesign status` — print progress (phase + per-page status) and take no action.
- `/bx:webdesign page <name>` — re-run/force a single page (e.g. after a failure).

## Step A — Setup check
Read `references/setup-stitch-mcp.md`. Detect the Stitch MCP + `stitch-skills`. If either is missing, print the setup banner and **stop**.

## Step B — Load or initialize state
Read `.webdesign/state.json` if present. The phase state machine:
`setup → extracted → direction_set → generating → review_pending → tokens_injected → injecting_pages → done`.
Per-page `status`: `pending → generated → injected → verified`, terminal `failed` / `manual`.
`state.json` shape:
```json
{ "phase": "...", "mode": "refactor", "styling_system": "...", "branch": "webdesign/YYYY-MM-DD",
  "stitch_project_id": "...", "design_direction": "...", "build_cmd": "...", "serve_cmd": "...",
  "app_runnable": true, "tokens_applied": false,
  "pages": [ { "route": "/", "file": "...", "states": ["default"], "status": "pending" } ] }
```
If `status` arg → print and stop. If `page <name>` arg → jump straight to the Phase-3 per-page loop for that page.

## Step C — Route by phase
- no state / `setup` → **Phase 1** (`references/phase1-extract.md`).
- `direction_set` → **Phase 2** (`references/phase2-design-review.md`).
- `review_pending` → ask "approved?"; on yes → **Phase 3** (`references/phase3-inject.md`); on changes → `edit_screens` then re-present.
- `tokens_injected` / `injecting_pages` → resume the **Phase 3** per-page loop.
- `done` → print the final report; offer to re-run a page or finish.

Always run web/styling/runnability detection (`references/web-stack-detection.md`) before Phase 1, and re-validate cheaply on resume (styling_system/app_runnable may have changed).

## Guardrails
- Web + refactor only; exit cleanly otherwise.
- Never raw-replace a page; never delegate behavior to Stitch; never auto-inject unreviewed designs.
- All commits on the `webdesign/<date>` branch.
- On any Stitch/MCP error, surface it and stop — never silently continue.
````

- [ ] **Step 2: Verify the orchestrator references every phase file and the state machine**

Run: `Grep -n "setup-stitch-mcp|phase1-extract|phase2-design-review|phase3-inject|web-stack-detection|state machine|status|page <name>" bx/skills/webdesign/SKILL.md`
Expected: all reference filenames + the args + state-machine line appear.

- [ ] **Step 3: Confirm all referenced files exist**

Run: `Glob bx/skills/webdesign/references/*.md`
Expected: exactly the 8 reference files (`stitch-formats`, `setup-stitch-mcp`, `web-stack-detection`, `brief-format`, `phase1-extract`, `phase2-design-review`, `phase3-inject`, `verification`). No reference is named in SKILL.md without a matching file.

- [ ] **Step 4: Commit**

```bash
git -C . add bx/skills/webdesign/SKILL.md
git -C . commit -m "feat(webdesign): wire orchestrator body + state routing"
```

---

## Task 11: Integrate into the toolkit docs

**Files:**
- Modify: `README.md`
- Modify: `workflow.md`

- [ ] **Step 1: Add `/bx:webdesign` to the README skills list**

Read `README.md`, find the skills list/table (currently 9 skills), and add a row/entry for `/bx:webdesign` matching the existing format. Use a one-line description: "Re-skin an existing web project's visual design via Google Stitch (MCP), preserving functionality (refactor; web-only)." If the README states a skill count ("9 skills"), bump it to 10.

- [ ] **Step 2: Add a usage note to `workflow.md`**

Read `workflow.md`, find where web-only skills (`/bx:seo`) are described, and add a short `/bx:webdesign` note covering: when to use it, the one-time Stitch MCP + `stitch-skills` setup, and that it works in resumable phases on a dedicated branch.

- [ ] **Step 3: Verify both updated**

Run: `Grep -rn "bx:webdesign" README.md workflow.md`
Expected: at least one hit in each file.

- [ ] **Step 4: Commit**

```bash
git -C . add README.md workflow.md
git -C . commit -m "docs(webdesign): add /bx:webdesign to README + workflow"
```

---

## Task 12: Structural validation + dogfood checklist

**Files:**
- (no new files — validation + a checklist artifact)

- [ ] **Step 1: Validate all frontmatter + cross-references**

Run (PowerShell):
```powershell
# Frontmatter present on SKILL.md
(Get-Content bx/skills/webdesign/SKILL.md)[0]   # expect ---
# Every references/*.md is a non-empty markdown file
Get-ChildItem bx/skills/webdesign/references/*.md | ForEach-Object { "$($_.Name): $((Get-Content $_).Count) lines" }
# No dangling reference: every 'references/<x>.md' named in SKILL.md exists
```
Expected: SKILL.md starts with `---`; all 8 reference files exist and are non-trivial (>15 lines each); every `references/*.md` named in SKILL.md resolves to a real file.

- [ ] **Step 2: Confirm the skill loads after a plugin refresh**

Run: `/plugin update bx` (or relaunch via `cc`), then in a new session confirm `/bx:webdesign` appears in the skills list and `/bx:webdesign status` (in a repo with no `.webdesign/`) prints a sensible "not started / Phase 1 will begin" message without crashing. Note: full behavior needs the Stitch MCP + `stitch-skills` installed.

- [ ] **Step 3: Write the dogfood checklist into the spec's parent dir for the first real run**

Create `docs/superpowers/plans/2026-06-06-bx-webdesign-dogfood.md` with a checklist for the first end-to-end run against a real project (e.g. burakarik.com) once the MCP is set up:
- [ ] Stitch MCP + `stitch-skills` installed; `/bx:webdesign` no longer shows the setup banner.
- [ ] Step 0 correctly detects stack + `styling_system` + `app_runnable`; non-web/greenfield exits verified separately.
- [ ] Phase 1 creates `webdesign/<date>` branch, drafts briefs, captures `before/`, seeds the Stitch project.
- [ ] Vibe-setting both paths work (Claude interview maps knobs; canvas read-back via `list_design_systems`).
- [ ] Phase 2 quota pre-flight shows an estimate; generation produces screens; review card prints; resume after approval works.
- [ ] Phase 3 tokens-first commit builds green; one page restyles with logic+content+assets preserved; verification green; commit on branch.
- [ ] Induce a failure (e.g. break a build) → page reverts via `git restore`, marks `failed`, loop continues.
- [ ] `status` and `page <name>` overrides behave as specified.
- [ ] Mobile/responsive behavior of a restyled page still works.

- [ ] **Step 4: Commit**

```bash
git -C . add docs/superpowers/plans/2026-06-06-bx-webdesign-dogfood.md
git -C . commit -m "test(webdesign): structural validation notes + first-run dogfood checklist"
```

---

## Self-Review (run after implementation, before merge)

- **Spec coverage:** every spec section maps to a task — Decisions 1–3 (MCP + reuse + Model A) → Tasks 1/3/6-8; Decision 4 (refactor-only) → Task 4; Decision 5 (tokens-first/page-by-page) → Task 8; Decision 6 (briefs) → Tasks 5/6; Decision 7 (verification) → Task 9; Decision 8 (name) → Task 1; Decision 9 (flexible vibe) → Task 6; Decision 10 (responsive) → Task 8; Decision 11 (branch) → Tasks 6/8. Research formats → Task 2. Setup → Task 3. State machine → Task 10.
- **Placeholder scan:** no "TBD/TODO/handle edge cases" — every reference task lists its exact required sections + verification grep.
- **Name consistency:** `webdesign` (skill), `.webdesign/` (state dir), `webdesign/<date>` (branch), `stitch::*` (delegated Google skills), `stitch_project_id`/`app_runnable`/`styling_system` (state keys) used identically across Tasks 2–12.

## Notes for the implementer
- This is a **markdown skill**, not code — "complete content" means complete frontmatter + section structure + the embedded canonical formats (Task 2) verbatim; the explanatory prose you write should match `bx/skills/seo` voice. Use **superpowers:writing-skills**.
- Don't touch `CLAUDE.md` status/skill-count — that's `/bx:save`'s job at session end.
- The skill's files live here; it *runs* in other repos. Don't create `.webdesign/`, branches, or `.gitignore` sentinels in this repo — those are runtime behaviors documented in the skill.
