# Phase 1 — Extract & Stage

**Goal:** detect the stack, branch, enumerate routes, draft page briefs, capture baseline screenshots, seed Stitch with the current design, then record the new design direction. On completion, `state.json` carries `branch`, `stitch_project_id` (if set), `design_system_id`, and `phase: direction_set`.

There are **three phases only**: Phase 1 (this file), Phase 2 (Design & Review), Phase 3 (Inject & Verify). Never reference a Phase 4 or Phase 5.

---

## Step 1 — Detect & Gate + Work Branch

### 1.1 — Run `web-stack-detection.md`

Read and execute `references/web-stack-detection.md` (all four passes, single parallel turn). On Pass 1 or Pass 3 failure, stop per that file's exit messages. On success, print its one-line summary:

```
Detected: <framework> · styling: <styling_system> · app_runnable: <true|false>
```

> **Do NOT fetch the Stitch prompting doc here.** The live-doc fetch (`https://stitch.withgoogle.com/docs/learn/prompting/`) now happens at **Phase 2 Step 2.1**, immediately before generation prompts are built — the only place its output is consumed. Fetching it in Phase 1 invites the deferral-then-drop that happened on the first dogfood (the fetch was pushed to Phase 2 and then silently skipped). Keep this inventory turn lean.

### 1.2 — Create or resume the work branch

Check `.webdesign/state.json` for an existing `branch` key:

- **First run (no `branch` key):** create a new branch using today's date from the environment:
  ```
  git -C <project-root> checkout -b webdesign/<YYYY-MM-DD>
  ```
  If the branch already exists (a prior run created it but `state.json` didn't survive), check it out instead of failing. Write `{ "branch": "webdesign/<YYYY-MM-DD>" }` to `.webdesign/state.json`.

- **Resumed run (`branch` key present):** check out the recorded branch:
  ```
  git -C <project-root> checkout <state.json["branch"]>
  ```

### 1.3 — Create `.webdesign/` and manage `.gitignore` (idempotent)

Immediately after the branch is created or resumed, ensure `.webdesign/` exists:

```bash
mkdir -p .webdesign/briefs .webdesign/before .webdesign/after
```

Then check the **target repo's** `.gitignore` for the sentinel start marker `# /bx:webdesign managed`:

- **Marker absent:** append the sentinel-marked block (create `.gitignore` if the file does not exist), then print `Added .webdesign/ + .stitch/ + .playwright-mcp/ to .gitignore (sentinel-marked block).`

  ```
  # /bx:webdesign managed — do not edit between markers
  .webdesign/
  .stitch/
  .playwright-mcp/
  # /end /bx:webdesign managed
  ```

- **Marker already present:** do **not** append a second block — but **verify the existing block lists all three of `.webdesign/`, `.stitch/`, and `.playwright-mcp/`**. Add any missing line **inside** the existing markers (a pre-fix block from an older run may lack `.stitch/` or `.playwright-mcp/`) and print `Added <lines> to existing .gitignore block.`. If all three are present, stay silent. (Don't rely on a separate "migration note" — this check is part of the present-marker branch, so it always runs.)

`.playwright-mcp/` is where the Playwright MCP writes screenshots — in **both** Phase 1 before-shots and Phase 3 per-page verification. Left untracked, it would trip Phase 3's clean-tree assertion on the *second* page iteration (the first verification creates it). Gitignoring it up front is what keeps that guard honest.

This covers `.webdesign/state.json`, `.webdesign/.setup-shown`, `.webdesign/SITE.md`, `.webdesign/briefs/`, `.webdesign/before/`, `.playwright-mcp/`, and all other working state — so the transient design artefacts are never committed alongside the refactored code.

Then **commit the `.gitignore` change immediately** (it is a tracked-file modification, and everything is on the throwaway `webdesign/<date>` branch):

```bash
git -C <project-root> add .gitignore
git -C <project-root> commit -m "webdesign: gitignore managed working dirs"
```

Leaving `.gitignore` modified-but-uncommitted is itself a clean-tree trap: Phase 3 Step 3 asserts `git status --porcelain` is empty at the start of every page, and an uncommitted (or resume-time marker-updated) `.gitignore` would halt the run. Commit it here so the tree is clean going into Phase 2/3. (If the marker block was already present and unchanged, there is nothing to commit — skip silently.)

**The general invariant (load-bearing for Phase 3):** every artifact the skill *or Google's `stitch-skills`* create **or modify** at the repo root must be either **gitignored** (working state) or **committed** (a real change) — otherwise it false-trips Phase 3's per-page "working tree must be clean" assertion and risks deletion by `git clean -fd` on a page failure. The artifacts that exist today: Google's `.stitch/` scratch dir and the Playwright MCP's `.playwright-mcp/` output dir (both gitignored via the block above); a root-level `DESIGN.md` (staged into the Phase 3 token commit); and **the `.gitignore` edit itself** (committed in the step above — the one tracked-file modification the skill makes). Any new root artifact a future `stitch-skills` release emits, or any new file the Playwright verification writes, must be handled the same way.

---

## Step 2 — Enumerate Routes → Draft Briefs

### 2.1 — Stack-aware route enumeration

Enumerate the project's page routes using the same stack-specific pathspec overlays that `/bx:seo` uses — the full table is in the **sibling seo skill's SKILL.md, Step 1.5.2**. Read it at `../seo/SKILL.md` resolved against **this skill's base directory** (the path Claude Code announces when the skill loads), NOT against the target project's CWD — a repo-rooted `bx/skills/seo/SKILL.md` path exists in neither the installed plugin layout nor the project being restyled. Apply the overlay matching the framework detected in Step 1.1. For each discovered route file, extract:

- The URL path (inferred from file position, e.g. `app/about/page.tsx` → `/about`)
- The source file path
- Any co-located layout files that wrap this route

### 2.2 — Draft a brief per page

Use two sequential batched turns:

1. **Read turn (parallel):** issue a single parallel Read turn to read ALL route source files at once.
2. **Write turn (parallel):** draft ALL briefs from the in-context sources and issue a single parallel Write turn to write them all at once.

For each brief (following the template in `references/brief-format.md`):

- Set `page:` to a slug (lowercase, hyphenated URL segment, e.g. `home`, `about`, `blog-post`)
- Set `route:` to the URL path
- Set `file:` to the source file path
- Populate "Functionality to PRESERVE" from actual handlers, API calls, form submissions, and interactive states found in the source. Do not invent placeholder items.
- Populate "Key components" from imported components visible in the file.
- Leave "UX notes / new-design intent" with a one-line placeholder — the user will refine it.

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

### 2.4 — Initialize `pages[]` in `state.json`

After all briefs are written (and before moving to Step 3), write the `pages[]` array and remaining Phase-1 scaffolding keys to `state.json`. Merge — do not overwrite the whole file.

For each brief:
- Read the brief's YAML frontmatter to get `page:` (→ `slug`), `route:`, `file:`, and `states:` (a list of state names; default `["default"]` if the key is absent).
- Emit one `pages[]` entry with these fields:

```json
{
  "slug": "<page: frontmatter value>",
  "route": "<route: frontmatter value>",
  "file": "<file: frontmatter value>",
  "status": "pending",
  "states": {
    "<state_name>": { "screen_id": null, "status": "pending" }
  }
}
```

`states` must be the **object-keyed shape** (keyed by state name, not a flat array). One key per name in the brief's `states:` list.

Also merge these two scalar keys if not already present (seed them once when `state.json` is first created in Step 1.2, or add them here if they were missed):

```json
{ "mode": "refactor", "tokens_applied": false }
```

After writing, `state.json` will contain `mode`, `tokens_applied`, and a fully-initialized `pages[]` array ready for Phase 2.

---

## Step 3 — Capture `before/` Screenshots

**Condition: `app_runnable == true` (from `state.json`).**

### 3.1 — Serve the app

Start the dev server in the **background** using `serve_cmd` from `state.json` — **keep the background task/shell handle so you can stop it in Step 3.3** — then wait for it to be ready by polling the local URL (same idiom as `references/verification.md` Step 2a):

```bash
curl -sf --retry 30 --retry-delay 1 --retry-connrefused "http://localhost:<port>/" >/dev/null
```

If the server logs a different port at startup than `state.json["port"]`, prefer the logged port and update `state.json["port"]`.

### 3.2 — Screenshot each route

For each page in the inventory, invoke the Playwright MCP to navigate to the route and take a full-page screenshot:

```
mcp__plugin_playwright_playwright__browser_navigate → http://localhost:<port><route>
mcp__plugin_playwright_playwright__browser_take_screenshot → <page>.png
```

Use desktop viewport (1280 × 800 minimum). Screenshot sequentially (Playwright is stateful).

> **The Playwright MCP writes to its own `.playwright-mcp/` dir, not the path you name.** The `filename` argument is resolved relative to the MCP's output directory (`.playwright-mcp/`), so the shots land there, not in `.webdesign/before/`. After capturing all routes, move them: `.playwright-mcp/<page>.png` → `.webdesign/before/<page>.png`. `.playwright-mcp/` is gitignored by Step 1.3, so it never dirties the tree.

### 3.3 — Confirm, stop the server, or warn

After all screenshots: **stop the background dev server** — use the `KillShell` tool with the background-shell ID returned when the server was started in Step 3.1. Do not improvise `kill`/`taskkill` shell commands (unpermitted, and process-name kills can hit unrelated processes). The server is not needed for Step 4's build or the rest of Phase 1, and leaving it running leaks a background process for the session. Then print `Captured N before/ screenshots in .webdesign/before/.`

> **Windows caveat — `KillShell` can orphan the dev-server child.** On Windows, `KillShell` terminates the `npm run dev` wrapper but the actual framework child (e.g. `next dev`) often survives and keeps holding the port. So **any later step that (re)starts a dev server must tolerate "port already in use"**: poll the port first (`curl -sf http://localhost:<port>/`), and if something already responds, reuse it instead of trying to spawn a second server (which will exit with "port in use"). This applies to Step 4's snapshot server and to Phase 3's per-loop server startup. Never `taskkill` the survivor — reuse it, or let it be reclaimed when the CLI session ends.

**Condition: `app_runnable == false`.** Skip this step entirely. Print:

```
⚠ app_runnable: false — before/ screenshots skipped.
Reason: <whichever condition failed in web-stack-detection.md Pass 4>.
Phase 3 will also skip Playwright verification — degrade to build-only.
```

---

## Step 4 — Seed Stitch

> **What Step 4 actually involves.** `code-to-design` is **not** a single turnkey call — it *chains* several `stitch-design:*` sub-skills, and on a real run it fans out into: create a project, snapshot the current design to HTML, write a baseline `DESIGN.md`, upload both, and create a design system. Several of those sub-steps carry their own prerequisites and mandatory confirmation checkpoints (below). Read each sub-skill before invoking it, and narrate every Stitch write.
>
> **The current-design HTML baseline is reference-only — not load-bearing.** It becomes a reference screen in the canvas; **Phase 2 generates from your briefs + the new direction, not from the old HTML.** So if the HTML-snapshot path is expensive (see the puppeteer note), you may seed from `DESIGN.md` alone without losing anything Phase 2 needs — offer the user that choice rather than forcing a heavy install.

### 4a — When `app_runnable == true`

1. **Run the build** (produces the artefacts the seeding chain reads):
   ```bash
   <build_cmd from state.json>
   ```
   If the build fails, print the error and skip to Step 4b's fallback path.

   > **SSR frameworks don't emit static HTML.** Next.js app-router / Nuxt / Remix / SvelteKit `build` produce a server bundle (`.next/`, etc.), not an `index.html`. For these, `extract-static-html` snapshots the **running dev server** instead — reuse the Step 3 server per the port-in-use caveat, and see the headless-browser note in sub-step 3.

2. **Create the Stitch project FIRST — `code-to-design` uploads *into* an existing project; it does not create one.** Its prerequisite is a `projectId`. Call `create_project` directly, then persist the ID *before* any further Stitch write so an interruption can't orphan the work:
   ```
   mcp__stitch__create_project(name = "<repo-name> — webdesign <YYYY-MM-DD>")
   ```
   Persist immediately to `state.json` (`{ "stitch_project_id": "<id>" }`) and to `.webdesign/SITE.md` (schema in sub-step 5).

3. **Seed the baseline into that project** via `stitch-design:code-to-design`, passing the `stitch_project_id` from sub-step 2 and the current `DESIGN.md` if one exists (omit if absent — the chain extracts tokens from the build/snapshot). Follow the sub-skill's prompts rather than guessing an argument signature:
   ```
   Skill("stitch-design:code-to-design")
   ```
   Two things it will surface and you must handle:
   - **Headless-browser strategy (SSR only).** `extract-static-html` requires either `puppeteer` (Google's default — an `npm install puppeteer` that downloads a bundled Chromium) or the already-connected Playwright MCP. Present this as a choice framed by the "baseline is reference-only" note above — puppeteer is a heavy install for a non-load-bearing artefact. If installing, prefer `npm install puppeteer --no-save` so `package.json` stays clean (node_modules is gitignored). The snapshot script may `import puppeteer` from **its own** directory, so it can't see a `--no-save` puppeteer in the project's `node_modules` — copy the (self-contained) script into a gitignored project dir (e.g. `.stitch/`) so the import resolves.
   - **Large uploads go through a Python helper, not MCP tools.** The design-system + HTML uploads use `upload_to_stitch.py` (the MCP tool-arg limit can't carry a multi-MB inlined HTML file). It needs a Python interpreter — **use `python`, not `python3`, on Windows** (`python3` is a broken Store stub there). Pass the API key from `.env`/env via a shell variable so it never prints to the transcript. Both upload sub-skills carry a mandatory "confirm before upload" checkpoint — honor them.

4. **Capture the baseline `design_system_id`** the chain creates and persist it (`{ "design_system_id": "<id>" }`). Step 5 *updates* this same asset with the new direction — it is created here, not replaced there.

5. Record in `.webdesign/SITE.md` (create if absent, append if present):
   ```markdown
   ## Stitch project
   - **Project ID:** <id>
   - **Seeded:** <YYYY-MM-DD> from Phase 1 (current design baseline)
   - **URL:** https://stitch.withgoogle.com/project/<id>
   ```

   > `SITE.md` lives **inside** `.webdesign/` (gitignored working memory), not at the repo root. A root-level `SITE.md` would be an untracked file that trips Phase 3's clean-tree guard and gets swept into the per-page restyle commit by `git add -A`.

Print: `Stitch project seeded: <id>. URL: https://stitch.withgoogle.com/project/<id>`

### 4b — When `app_runnable == false` (fallback)

Build output is unavailable. Use the source-only seeding path:

1. Invoke `stitch-design:extract-design-md` on the source to produce or update `DESIGN.md`:
   ```
   Skill("stitch-design:extract-design-md")
   ```
2. Invoke `stitch-design:manage-design-system` to seed the design system from the extracted `DESIGN.md`:
   ```
   Skill("stitch-design:manage-design-system")
   ```

3. **Establish a Stitch project and persist its ID.** Phase 2 cannot generate screens without a `stitch_project_id`, so this path must still produce one — it just can't seed it from a build:

   - **If step 1/2 (or a `create_project` call) returned a project ID**, persist it: write `{ "stitch_project_id": "<id>" }` to `state.json` and record it in `.webdesign/SITE.md`.
   - **If no project was created** (the source-only path only produced a design system), prompt the user and capture the ID they supply:
     ```
     The app isn't runnable, so I couldn't auto-create a full Stitch project from a build.
     To continue, open the Stitch web canvas (https://stitch.withgoogle.com), create a
     project seeded from the DESIGN.md I just wrote, and paste its project ID here.
     ```
     Write the pasted ID to `state.json["stitch_project_id"]` and to `.webdesign/SITE.md`. (If the user declines, Phase 1 still closes at `phase: direction_set`; Phase 2 will re-offer this capture before it can generate — see `phase2-design-review.md` Step 2 guard.)

4. Print a limitation notice:
   ```
   ⚠ app_runnable: false — Stitch seeded from source files only (no static HTML).
   Design-system tokens are extracted heuristically; accuracy is lower than build-seeding.
   ```

Unlike the build path, `stitch_project_id` here comes from a captured/returned ID rather than from `code-to-design`. If the user declines to supply one now, it stays unset until the Phase 2 guard captures it.

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

*(If `stitch_project_id` is absent because `app_runnable == false` and the user didn't supply one in Step 4b, omit the project URL from path (b) and note: "Stitch project URL unavailable (source-only seeding) — you can still create a new Stitch project at stitch.withgoogle.com and paste the project ID here." **When the user pastes a project ID, write it to `state.json["stitch_project_id"]` and `.webdesign/SITE.md` immediately** — otherwise Phase 2 will dead-end on its null-project guard.)*

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

Wait for user confirmation. On confirm, apply via `stitch-design:manage-design-system` (prefer `create_design_system_from_design_md` if a full DESIGN.md is available; use `update_design_system` for knob-only application):

```
Skill("stitch-design:manage-design-system")
```

Record the resulting `design_system_id` in `state.json` (key: `design_system_id`).

### 5b — Stitch web canvas (path b)

Print the Stitch project URL (or instructions to create one) and wait for the user to return.

When the user resumes, invoke `stitch-design:manage-design-system` via the Skill tool to read back the current state via `list_design_systems`:

```
Skill("stitch-design:manage-design-system")  # calls list_design_systems internally
```

Identify the design system the user configured (by project, or ask the user to confirm the design-system name/ID). Record the `design_system_id` in `state.json`.

---

## Step 6 — Close Phase 1

1. Write `{ "phase": "direction_set", "design_direction": "<one-line summary of the chosen knobs (path a) or the canvas direction (path b)>" }` to `state.json` (merge with existing keys, do not overwrite the whole file). `design_direction` is the human-readable record of the new aesthetic (e.g. `"minimal/clean, TONAL blue #2D6BE4, INTER, ROUND_EIGHT, light"`); it is surfaced in the Phase 1 summary and on `status`.

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
| `mode` | string (`refactor`) | Step 1.2 (seeded on first create) or Step 2.4 | Phase 2/3 guard logic |
| `tokens_applied` | boolean (`false`) | Step 1.2 (seeded on first create) or Step 2.4 | Phase 3 token-inject guard; `page <name>` pre-check |
| `styling_system` | string | Step 1.1 | Phase 3 token injection |
| `build_cmd` | string \| null | Step 1.1 | Step 4, Phase 3 build |
| `serve_cmd` | string \| null | Step 1.1 | Step 3, Phase 3 Playwright |
| `app_runnable` | boolean | Step 1.1 | Step 3, Step 4, Phase 3 |
| `port` | integer | Step 1.1 (via web-stack-detection.md Pass 4) | Step 3 screenshots (`http://localhost:<port>`), Phase 3 Playwright |
| `pages[]` | array of page objects | Step 2.4 (after briefs are written) | Phase 2 screen generation, Phase 3 per-page loop, `status` arg |
| `pages[].slug` | string | Step 2.4 | Phase 2/3 page lookup |
| `pages[].route` | string | Step 2.4 | Phase 1 screenshots, Phase 3 Playwright navigation |
| `pages[].file` | string | Step 2.4 | Phase 3 injection target |
| `pages[].status` | string (`pending`) | Step 2.4 | Phase 3 per-page loop gate; `status` display |
| `pages[].states` | object keyed by state name | Step 2.4 (object shape, not array) | Phase 2 fills `screen_id`; Phase 3 `get_screen` |
| `stitch_project_id` | string | Step 4a (build path) — or Step 4b/5b (source-only path, via a returned or user-supplied ID) | Phase 2 screen generation, Step 5b |
| `design_system_id` | string | Step 4a (baseline, created by the code-to-design chain) — updated in Step 5a/5b with the new direction | Phase 2 screen generation |
| `design_direction` | string | Step 6 | Phase 1 summary; `status` display |
| `phase` | string (`direction_set`) | Step 6 | resume logic in skill entry |

## Artefact Paths Written in Phase 1

| Artefact | Path |
|----------|------|
| State file | `.webdesign/state.json` |
| Per-page briefs | `.webdesign/briefs/<page>.md` |
| Before screenshots | `.webdesign/before/<page>.png` |
| Stitch project record | `.webdesign/SITE.md` (gitignored) |
| gitignore block | `.gitignore` (sentinel-marked) |
| DESIGN.md | created/updated by stitch-design:extract-design-md in Step 4b (source-only fallback path) |
