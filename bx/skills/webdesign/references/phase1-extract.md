# Phase 1 — Extract & Stage

**Goal:** detect the stack, branch, enumerate routes, draft page briefs, capture baseline screenshots, seed Stitch with the current design, then record the new design direction. On completion, `state.json` carries `branch`, `stitch_project_id` (if set), `design_system_id`, and `phase: direction_set`.

There are **three phases only**: Phase 1 (this file), Phase 2 (Design & Review), Phase 3 (Inject & Verify). Never reference a Phase 4 or Phase 5.

---

## Step 1 — Detect & Gate + Work Branch

### 1.1 — Run `web-stack-detection.md`

Read `references/web-stack-detection.md` and execute all four passes in a single parallel turn.

- **Pass 1** gates on web-project signals. On fail, stop cleanly.
- **Pass 3** gates on EXISTING vs. GREENFIELD. On greenfield detection, stop cleanly.
- **Pass 4** resolves `app_runnable`, `build_cmd`, `serve_cmd`.
- Write `styling_system`, `build_cmd`, `serve_cmd`, `app_runnable` to `.webdesign/state.json`.

Print the one-line detected-stack summary produced by `web-stack-detection.md`:

```
Detected: <framework> · styling: <styling_system> · app_runnable: <true|false>
```

### 1.2 — Create or resume the work branch

Check `.webdesign/state.json` for an existing `branch` key:

- **First run (no `branch` key):** create a new branch using today's date from the environment:
  ```
  git checkout -b webdesign/<YYYY-MM-DD>
  ```
  Write `{ "branch": "webdesign/<YYYY-MM-DD>" }` to `.webdesign/state.json`.

- **Resumed run (`branch` key present):** check out the recorded branch:
  ```
  git checkout <state.json["branch"]>
  ```

### 1.3 — Create `.webdesign/` and manage `.gitignore` (idempotent)

Immediately after the branch is created or resumed, ensure `.webdesign/` exists:

```bash
mkdir -p .webdesign/briefs .webdesign/before .webdesign/after
```

Then check the **target repo's** `.gitignore` for the sentinel start marker `# /bx:webdesign managed`. If absent, append the following sentinel-marked block (create `.gitignore` if the file does not exist):

```
# /bx:webdesign managed — do not edit between markers
.webdesign/
# /end /bx:webdesign managed
```

This covers `.webdesign/state.json`, `.webdesign/.setup-shown`, `.webdesign/briefs/`, `.webdesign/before/`, and all other working state — so the transient design artefacts are never committed alongside the refactored code.

**Print** `Added .webdesign/ to .gitignore (sentinel-marked block).` on first append. Silent on subsequent runs (sentinel already present).

---

## Step 2 — Enumerate Routes → Draft Briefs

### 2.1 — Stack-aware route enumeration

Enumerate the project's page routes using the same stack-specific pathspec overlays that `/bx:seo` uses (see `bx/skills/seo/SKILL.md` Step 1.5.2 for the full table). Apply the overlay matching the framework detected in Step 1.1. For each discovered route file, extract:

- The URL path (inferred from file position, e.g. `app/about/page.tsx` → `/about`)
- The source file path
- Any co-located layout files that wrap this route

### 2.2 — Draft a brief per page

For each enumerated route, draft `.webdesign/briefs/<page>.md` following the template in `references/brief-format.md`:

- Set `page:` to a slug (lowercase, hyphenated URL segment, e.g. `home`, `about`, `blog-post`)
- Set `route:` to the URL path
- Set `file:` to the source file path
- **Read the source file** before writing the brief; populate "Functionality to PRESERVE" from actual handlers, API calls, form submissions, and interactive states found in the source. Do not invent placeholder items.
- Populate "Key components" from imported components visible in the file.
- Leave "UX notes / new-design intent" with a one-line placeholder — the user will refine it.

Write briefs in parallel (one `Write` call per page, all in a single turn when feasible).

### 2.3 — Present inventory for user review

After writing all briefs, print a formatted inventory table:

```
## Page inventory (N pages)

| Page | Route | Source |
|------|-------|--------|
| home | / | src/app/page.tsx |
| about | /about | src/app/about/page.tsx |
| ...  | ...   | ... |

Briefs written to .webdesign/briefs/. Review and refine each brief — especially
"Functionality to PRESERVE" — before proceeding to Step 3.
```

**Wait for the user to confirm before continuing.** If the user wants to edit briefs, pause; proceed only when they say to continue.

---

## Step 3 — Capture `before/` Screenshots

**Condition: `app_runnable == true` (from `state.json`).**

### 3.1 — Serve the app

Start the dev server using `serve_cmd` from `state.json`. Wait for it to be ready (probe the local URL, up to 30 s).

### 3.2 — Screenshot each route

For each page in the inventory, invoke the Playwright MCP to navigate to the route and take a full-page screenshot:

```
mcp__plugin_playwright_playwright__browser_navigate → http://localhost:<port><route>
mcp__plugin_playwright_playwright__browser_take_screenshot → .webdesign/before/<page>.png
```

Use desktop viewport (1280 × 800 minimum). Screenshot sequentially (Playwright is stateful).

### 3.3 — Confirm or warn

After all screenshots: print `Captured N before/ screenshots in .webdesign/before/.`

**Condition: `app_runnable == false`.** Skip this step entirely. Print:

```
⚠ app_runnable: false — before/ screenshots skipped.
Reason: <whichever condition failed in web-stack-detection.md Pass 4>.
Phase 3 will also skip Playwright verification — degrade to build-only.
```

---

## Step 4 — Seed Stitch

### 4a — When `app_runnable == true`

1. Run the build:
   ```bash
   <build_cmd from state.json>
   ```
   If the build fails, print the error and skip to Step 4b's fallback path.

2. Invoke `stitch::code-to-design` via the Skill tool:
   ```
   Skill("stitch::code-to-design")
   ```
   Pass the project's **current** `DESIGN.md` as the baseline (read it if it exists; omit the argument if the file is absent — `stitch::code-to-design` will infer design tokens from the build output). Pass the DESIGN.md content per `stitch::code-to-design`'s own input convention (e.g. as the design-md content argument). If the exact argument signature is unknown, invoke the skill and follow its prompts rather than guessing a flag name.

3. From the Skill result, capture the `stitch_project_id` (the newly created Stitch project identifier).

4. Persist to `state.json`:
   ```json
   { "stitch_project_id": "<id>" }
   ```

5. Record in `SITE.md` (create if absent, append if present):
   ```markdown
   ## Stitch project
   - **Project ID:** <id>
   - **Seeded:** <YYYY-MM-DD> from Phase 1 (current design baseline)
   - **URL:** https://stitch.withgoogle.com/project/<id>
   ```

Print: `Stitch project seeded: <id>. URL: https://stitch.withgoogle.com/project/<id>`

### 4b — When `app_runnable == false` (fallback)

Build output is unavailable. Use the source-only seeding path:

1. Invoke `stitch::extract-design-md` on the source to produce or update `DESIGN.md`:
   ```
   Skill("stitch::extract-design-md")
   ```
2. Invoke `stitch::manage-design-system` to seed the design system from the extracted `DESIGN.md`:
   ```
   Skill("stitch::manage-design-system")
   ```
3. Print a limitation notice:
   ```
   ⚠ app_runnable: false — Stitch seeded from source files only (no static HTML).
   Design-system tokens are extracted heuristically; accuracy is lower than build-seeding.
   stitch_project_id is not set (no full project was created in this path).
   ```

`stitch_project_id` is **not** written to `state.json` in this fallback path — downstream steps treat its absence as "seeded from source, no project URL available."

---

## Step 5 — Capture the New Design Direction

**This step captures where the design is going, not where it currently is.** Step 4 supplied the structure and brand invariants (logo, an existing brand color) as a baseline to optionally carry forward. The new direction comes entirely from this step.

Present both paths and let the user choose:

```
## How would you like to set the new design direction?

**(a) Claude-led interview** — I'll ask you a few vibe questions (aesthetic, audience,
    inspiration references), map your answers to design-system knobs, show you the
    proposed settings, and apply them once you confirm.

**(b) Stitch web canvas** — Open the Stitch project URL and shape the design system
    yourself at https://stitch.withgoogle.com/project/<stitch_project_id>.
    Come back here when you're happy with it and type "continue" — I'll read
    the design system back and record it.

Which would you prefer — (a) or (b)?
```

*(If `stitch_project_id` is absent because `app_runnable == false`, omit the project URL from path (b) and note: "Stitch project URL unavailable (source-only seeding) — you can still create a new Stitch project at stitch.withgoogle.com and paste the project ID here.")*

### 5a — Claude-led interview (path a)

Ask the following questions (present all at once, not one at a time):

1. **Vibe / aesthetic** — What's the overall feel you're going for? (e.g., elegant and refined, minimal and clean, bold and energetic, playful and warm, retro)
2. **Audience** — Who are the primary users, and what tone do they expect?
3. **Inspiration** — Any sites, brands, or visual references that capture the direction?
4. **Color** — Is there a primary/brand color you want to keep or seed the new palette from? (hex or name)
5. **Mode** — Light or dark?

Map the answers to knobs using the vibe→knob table in `references/stitch-formats.md`:

- `colorMode` (LIGHT/DARK) — from the mode answer
- `customColor` — from the brand color answer
- `colorVariant` — from the vibe table
- `roundness` — from the vibe table
- `headlineFont` / `bodyFont` — from the vibe table

**Show the proposed knobs to the user before applying:**

```
## Proposed design-system settings

| Knob | Value | Rationale |
|------|-------|-----------|
| colorMode | LIGHT | User stated "light" |
| customColor | #2D6BE4 | Brand blue kept from current design |
| colorVariant | TONAL | "professional, trustworthy" vibe |
| roundness | ROUND_EIGHT | Clean, not overly soft |
| headlineFont | PLUS_JAKARTA_SANS | Contemporary, professional |
| bodyFont | INTER | Neutral, highly legible |

Confirm to apply, or tell me what to change.
```

Wait for user confirmation. On confirm, apply via `stitch::manage-design-system` (prefer `create_design_system_from_design_md` if a full DESIGN.md is available; use `update_design_system` for knob-only application):

```
Skill("stitch::manage-design-system")
```

Record the resulting `design_system_id` in `state.json` (key: `design_system_id`).

### 5b — Stitch web canvas (path b)

Print the Stitch project URL (or instructions to create one) and wait for the user to return.

When the user resumes, invoke `stitch::manage-design-system` via the Skill tool to read back the current state via `list_design_systems`:

```
Skill("stitch::manage-design-system")  # calls list_design_systems internally
```

Identify the design system the user configured (by project, or ask the user to confirm the design-system name/ID). Record the `design_system_id` in `state.json`.

---

## Step 6 — Close Phase 1

1. Write `{ "phase": "direction_set" }` to `state.json` (merge with existing keys, do not overwrite the whole file).

2. Print the Phase 1 summary:

```
## Phase 1 complete — Extract & Stage

**Branch:** webdesign/<YYYY-MM-DD>
**Pages enumerated:** N (briefs in .webdesign/briefs/)
**Before screenshots:** <N captured | skipped (app_runnable: false)>
**Stitch project:** <id and URL | seeded from source only>
**Design direction:** <one-line summary of chosen knobs or "set via Stitch canvas">
**state.json:** branch, stitch_project_id (if set), design_system_id, phase=direction_set

**Next:** Phase 2 — Design & Review
Run /bx:webdesign again (or continue in this session) to start generating screens.
```

---

## State Keys Written in Phase 1

| Key | Type | Written in | Consumed by |
|-----|------|-----------|-------------|
| `branch` | string | Step 1.2 | all subsequent phases (branch checkout on resume) |
| `styling_system` | string | Step 1.1 | Phase 3 token injection |
| `build_cmd` | string \| null | Step 1.1 | Step 4, Phase 3 build |
| `serve_cmd` | string \| null | Step 1.1 | Step 3, Phase 3 Playwright |
| `app_runnable` | boolean | Step 1.1 | Step 3, Step 4, Phase 3 |
| `stitch_project_id` | string | Step 4a only (app_runnable: true) — absent on source-only fallback path | Phase 2 screen generation, Step 5b |
| `design_system_id` | string | Step 5a or 5b | Phase 2 screen generation |
| `phase` | string (`direction_set`) | Step 6 | resume logic in skill entry |

## Artefact Paths Written in Phase 1

| Artefact | Path |
|----------|------|
| State file | `.webdesign/state.json` |
| Per-page briefs | `.webdesign/briefs/<page>.md` |
| Before screenshots | `.webdesign/before/<page>.png` |
| Stitch project record | `SITE.md` |
| gitignore block | `.gitignore` (sentinel-marked) |
| DESIGN.md | created/updated by stitch::extract-design-md in Step 4b (source-only fallback path) |
