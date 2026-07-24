# Phase 3 — Safe Inject & Verify

**Goal:** fetch the approved Stitch screens, merge the new design tokens into the project theme, then restyle each page in place — preserving all logic, content, and assets — and verify each page before committing it. On completion, `state.json` carries `phase = done`.

There are **three phases only**: Phase 1 (Extract & Stage), Phase 2 (Design & Review), Phase 3 (this file). Never reference a Phase 4 or Phase 5.

**All Phase-3 commits land on the `webdesign/<date>` branch** (recorded in `state.json["branch"]`, created by Phase 1).

**Inputs from `state.json` (written by Phases 1–2):**
- `branch` — the `webdesign/<date>` work branch; check it out before any writes.
- `styling_system` — one of `tailwind | css-vars | plain-css | css-in-js | css-modules | vanilla-extract | unknown`. Drives token-merge strategy in Step 2.
- `build_cmd` — command to verify a build (may be `null`).
- `app_runnable` — `true | false`. Controls whether Playwright verification is available.
- `pages[]` — one entry per page (canonical shape: SKILL.md Step B); keys Phase 3 reads/writes are listed under **Keys Phase 3 reads / writes** below.

---

## Keys Phase 3 reads / writes in `state.json`

Full canonical shape: **SKILL.md Step B**. Phase 3 touches only these keys:

| Key | Direction | Notes |
|-----|-----------|-------|
| `status` (page-level) | read + write | loop gate (skip `verified`); written: `injected` → `verified` / `failed` / `manual` |
| `states.<name>.screen_id` | read | passed to `get_screen` in Step 1 |
| `route`, `file`, `slug` | read | navigation, injection target, commit message |
| `failure_reason` | write | recorded on `failed` |
| `phase` | write | `tokens_injected` → `injecting_pages` → `done` |
| `tokens_applied` | write | set `true` after token commit |
| `serve_cmd`, `app_runnable` | read | dev-server startup (Step 3 pre-step) |
| `port` | read + write | dev-server startup (Step 3 pre-step); rewritten if the server logs a different port at startup |
| `build_cmd` | read | token-merge build verification (Step 2) |

---

## Step 1 — Fetch Approved Screens

**Check out the work branch first:**

```bash
git -C <project-root> checkout <state.json["branch"]>
```

Signed URLs returned by `get_screen` are short-lived — issue ALL `get_screen` calls in a **single parallel MCP turn**, then immediately issue ALL `curl` downloads in a **single parallel Bash turn**. Do not interleave them page-by-page.

> **Single-page entry (`/bx:webdesign page <name>`):** scope Round 1 + Round 2 to just that page's state(s). The re-fetch is **required** even if a prior run downloaded the HTML — the earlier signed URLs have expired and the `.webdesign/tmp/stitch-<page>-<state>.html` file may have been cleaned, so the Step 3 restyle loop cannot assume it is still on disk.

**Round 1 — one parallel MCP turn, all pages × all states:**

For every page in `pages[]` and every state under `pages[].states`, call `get_screen` in parallel:
```
get_screen(screen_id = pages[page].states[state].screen_id)
```

**Skip any state whose `screen_id` is `null`** (its Phase-2 generation failed) — print `⚠ <page>/<state>: no screen generated in Phase 2 — skipped.` instead of calling `get_screen` with a null ID. If **every** state of a page is null, set that page's `status = "failed"` with `failure_reason: "screen generation failed in Phase 2"` and exclude it from the Step 3 loop — one failed generation must not brick the run for the healthy pages (the page stays retryable via `/bx:webdesign page <name>` after its screens are regenerated).
Each response contains:
- `htmlCode.downloadUrl` — a **signed URL** (short-lived; fetch immediately with `curl`, not WebFetch)
- `screenshot.downloadUrl` — a signed URL for the rendered PNG
- `data-stitch-id` attributes on elements (preserve as comments in Step 3b)

**Round 2 — one parallel Bash turn, all downloads:**

Immediately after Round 1 (before signed URLs expire), issue all `curl` commands in a single parallel Bash turn:
```bash
mkdir -p .webdesign/tmp .webdesign/after
curl -sL "<htmlCode.downloadUrl>" -o .webdesign/tmp/stitch-<page>-<state>.html
curl -sL "<screenshot.downloadUrl>" -o .webdesign/after/<page>-<state>.png
# (one pair per page/state, all in the same parallel turn)
```

Print a one-line confirmation after all downloads complete:
```
Fetched: <N> screens → .webdesign/after/ and .webdesign/tmp/
```

---

## Step 2 — Tokens-First (one global commit)

**Merge the Stitch design-system tokens into the project theme layer before touching any page.**

The Stitch HTML `<head>` carries a localized `tailwind.config`; `DESIGN.md` (written by Phase 1 Step 4b, or by `stitch-design:extract-design-md`) carries the canonical token set. Use whichever is available; prefer the `<head>` config for `tailwind` projects.

Merge strategy by `styling_system`:

| `styling_system` | What to merge | Where to apply |
|---|---|---|
| `tailwind` | Extract the token values from any fetched Stitch `<head>` `tailwind.config` block + the DESIGN.md token set (colors, fonts, radius, spacing). **Detect the Tailwind version first:** if a `tailwind.config.{js,ts,cjs,mjs}` exists (v3), merge tokens under `theme.extend`. If there is **no config file** (v4), merge them into the `@theme { … }` block of the main CSS entry (the file that has `@import "tailwindcss"`, e.g. `app/globals.css`) as `--color-*` / `--font-*` / `--radius-*` / `--spacing-*` custom properties. Either way, do not overwrite custom project extensions — merge at the token-key level. | v3: `tailwind.config.js/ts` · **v4: the `@theme {}` block in the `@import "tailwindcss"` CSS file** |
| `css-vars` | Write the DESIGN.md color/typography/spacing tokens as CSS custom properties in the `--` namespace into the `:root {}` block of the project's theme stylesheet (create a dedicated `tokens.css` / `design-tokens.css` if no single `:root` file exists). | theme / `:root` stylesheet |
| `plain-css` | Same as `css-vars` — write as `--token-name: value` properties under `:root {}`. | theme / `:root` stylesheet |
| `css-in-js` | Update the project's theme object with the new token values. **Detection:** locate the theme object by grepping for `ThemeProvider` (e.g. `Grep -r "ThemeProvider" src/`); the object passed to it at its definition site is the merge target. Match the existing key-naming convention (camelCase vs kebab) in that file. | theme object / token file |
| `css-modules` | Write tokens as CSS custom properties in a shared `variables.module.css` or equivalent root-level module. | shared variables module |
| `vanilla-extract` | Update the `contract` or `vars` file (e.g. `vars.css.ts`) with the new token values following the existing `createGlobalTheme` / `createTheme` structure. | `vars.css.ts` or equivalent |
| `unknown` | Apply tokens as CSS custom properties under `:root {}` in the closest available global stylesheet, and warn: `⚠ styling_system: unknown — tokens applied as CSS custom properties in <file>. Manual verification required.` | best-effort global stylesheet |

After writing the tokens:

1. Run `build_cmd` (if non-null):
   ```bash
   <build_cmd from state.json>
   ```
   If the build fails: print the build error, **do not commit**, leave `phase` as-is (do NOT advance to `tokens_injected`), and stop Phase 3. Surface the build error to the user and instruct them to fix the token merge (or revert it) and re-run `/bx:webdesign` — which cleanly re-enters Step 2.

2. Stage and commit. Stage the token file(s) first, then a **root-level** `DESIGN.md` **only if one exists** — it is the portable design system and belongs with the token commit. A `.stitch/`-internal `DESIGN.md` is already gitignored; leave it.

   ```bash
   git -C <project-root> add <token file(s)>
   git -C <project-root> add DESIGN.md   # run this line ONLY if a root-level DESIGN.md exists
   git -C <project-root> commit -m "tokens: apply new design system"
   ```

   > **Do not pass `DESIGN.md` to `git add` unconditionally.** When no root-level `DESIGN.md` exists (the common Tailwind case), `git add … DESIGN.md` fails with `fatal: pathspec 'DESIGN.md' did not match any files`, stages **nothing** (not even the token files), and the commit then fails — dead-ending Phase 3. Check for the file first (Glob/Read), and only run the second `add` line when it's present.

   Staging `DESIGN.md` here is also what keeps Phase 3's per-page clean-tree assertion (Step 3) true. The general rule is in **Phase 1 Step 1.3**: every root artifact the skill or Google's skills produce must be either gitignored (working state) or staged into the right commit (design artifacts), or it false-trips that assertion and risks `git clean -fd`. Don't add a separate clean-tree check here — Step 3 already asserts it per iteration.

3. Write to `state.json` **only after the token commit succeeds**:
   ```json
   { "tokens_applied": true, "phase": "tokens_injected" }
   ```

---

## Step 3 — Per-Page Restyle Loop (resumable)

**Before starting the loop:**

1. Write to `state.json`:
   ```json
   { "phase": "injecting_pages" }
   ```
   This ensures a mid-loop interruption resumes into the page loop correctly. `phase` stays `injecting_pages` until Step 4 sets it to `done`.

2. **Start the dev server once (if `app_runnable == true`).** **First poll the port** — `curl -sf http://localhost:<port>/` — and if something already responds (e.g. an orphaned `next dev` child from an earlier step or session that a Windows `KillShell` didn't reap; see Phase 1 Step 3.3), **reuse it** rather than spawning a second server (a second start just exits with "port in use"). Otherwise, using `state.json["serve_cmd"]`, start the dev server in the background and wait for it to be ready (poll up to 30 s). Note the port it reports at startup; if it differs from `state.json["port"]`, update `state.json["port"]`. Keep the server running for the entire loop; stop it after Step 4 (or on early exit) with the `KillShell` tool using the background-shell ID from startup — do not improvise `kill`/`taskkill` shell commands. Do not restart it per-page. Verification (`references/verification.md`) assumes the server is already running.

   If `app_runnable == false`, skip this sub-step.

3. **Pre-read all page briefs.** Issue a single parallel Read turn to load every `.webdesign/briefs/<page>.md` into context before the loop starts. Hold the "Functionality to PRESERVE" list for each page in context so per-iteration reads are unnecessary.

Iterate over `pages[]` in order. **Skip any page whose page-level `status` is already `verified`.** (Resume: if the skill is re-run after a partial Phase 3, pages already verified are not re-touched.)

For each page with `status != verified`:

**At the start of each loop iteration, assert the working tree is clean:**
```bash
git -C <project-root> status --porcelain
```
If the output is non-empty, **STOP** and warn the user:
```
⚠ Unexpected dirty working tree before starting <page>. Phase 3 cannot continue safely.
  Resolve or commit the outstanding changes, then re-run /bx:webdesign.
  (Common cause: a root-level DESIGN.md / SITE.md, Google's .stitch/ scratch dir, or the
   Playwright MCP's .playwright-mcp/ output that isn't committed or gitignored — see
   Phase 1 Step 1.3 and Step 2 above.)
```
Do not proceed to 3a until the tree is confirmed clean. This holds because Phase 3 commits after every successful page (so the tree is clean between pages) **and** because Phase 1 Step 1.3's general invariant ensures every skill/Google artifact is gitignored or staged. If something slipped through, this guard catches it.

**Resume rule — `injected` status:** if a page's `status == injected` (the restyle write completed but verification was interrupted), **skip Steps 3a and 3b** and go straight to Step 3c (verify only). Do not re-restyle an already-restyled file.

### 3a — Read sources side-by-side

Load into context in a single parallel turn:

- The **existing page source** (the file at `pages[].file`)
- The **Stitch HTML** (`.webdesign/tmp/stitch-<page>-<default-state>.html`, or all states if the page has multiple)
- The `.webdesign/after/<page>-<state>.png` screenshot(s) (visual reference)

The page's brief "Functionality to PRESERVE" list was pre-read before the loop (Step 3 pre-step 3) — use the in-context copy; no re-read needed.

### 3b — Restyle in place (the core invariant)

**Restyle the existing page's markup and classes to match the new design while preserving every handler, API call, route, and piece of state.**

Preservation rules — these are absolute; violating any one is grounds for setting `status = manual`:

1. **Logic preservation:** every event handler, lifecycle hook, `useEffect`, `onClick`, `onSubmit`, form action, API call, route link, and state variable must remain in the output. Do not rename, remove, or stub them.
2. **Content and asset preservation:** the page's **real copy and existing images/assets** are kept as-is. Discard Stitch's placeholder text (e.g. "Lorem ipsum", "Your heading here", stock image URLs) and stock images entirely — adopt only the new visual structure and styling from the Stitch output. Real `<img src>` paths, `alt` text, and text content come from the existing source.
3. **Responsive preservation:** apply the new visual language **within the page's existing responsive breakpoints**. Do NOT introduce a desktop-only layout that removes or collapses mobile breakpoints. If the existing source has `sm:`, `md:`, `lg:` Tailwind prefixes (or equivalent media queries), the restyled output must have them too.
4. **`data-stitch-id` comments:** for each element in the Stitch HTML that carries a `data-stitch-id` attribute, add the value as an inline comment in the restyled markup (e.g. `{/* data-stitch-id: hero-cta-btn */}`) so future re-sync can locate the corresponding Stitch element. Do not add the attribute itself to the live DOM.
5. **No new dependencies:** do not add npm packages or import new third-party libraries. Use only what the project already has.

The restyle process:

1. For each section of the existing page, find the matching section in the Stitch HTML.
2. Adopt the Stitch section's class list, spacing, typography scale, and color token references.
3. Keep the existing section's markup structure (tags, nesting, conditionals) and all JS/TS expressions.
4. Where the Stitch HTML uses placeholder text, restore the real content from the existing source.
5. Where the Stitch HTML uses a stock image, restore the existing `<img>` or background-image reference.

After writing the restyled file, set page-level `status = injected` in `state.json`.

### 3c — Verify

Execute verification per `references/verification.md` (authoritative). The verification contract is the page brief's **"Functionality to PRESERVE"** list (from `.webdesign/briefs/<page>.md`).

Verification substeps (summary — see `references/verification.md` for full rules):

1. **Static checks — build/typecheck/test** (per `references/verification.md` — typecheck runs first; `verification.md` is authoritative on ordering). If any check fails, this page fails — go to Step 3e.
2. **Playwright behavior check (`app_runnable == true` only):** navigate to the page's route and assert each item in the "Functionality to PRESERVE" list (e.g. submit fires the API call, filter updates results). Capture `.webdesign/after/<page>-post-inject.png` for before/after comparison.
3. **Build-only (`app_runnable == false`):** skip Playwright and screenshot capture; green static checks are the verification gate.

If all checks pass: go to Step 3d. If any check fails: go to Step 3e.

### 3d — On green: commit and continue

1. Commit ALL files changed by the restyle (page file + any co-changed components, CSS modules, or new files — restyles are multi-file; `git add <pages[].file>` alone makes an incomplete commit that fails on fresh checkout):
   ```bash
   git -C <project-root> add -A
   git -C <project-root> commit -m "webdesign: restyle <page>"
   ```
   When `app_runnable == false`, append the degradation note from `references/verification.md` Step 4 as a second `-m` body paragraph (runtime behavior was not auto-verified).

2. Update `.webdesign/SITE.md` — add or update the live-sitemap entry for this page with its new route/status (create it if absent). It lives inside the gitignored `.webdesign/` dir, so it is **not** part of this page's restyle commit (and `git add -A` will not pick it up).

3. Set page-level `status = verified` in `state.json`.

4. Continue to the next page.

### 3e — On failure: rollback and continue

1. Clean ALL uncommitted changes since the last commit (a restyle may have touched shared components, CSS modules, or created new files; restoring only `pages[].file` leaks dirty files into the next page's iteration):
   ```bash
   git -C <project-root> restore .
   git -C <project-root> clean -fd
   ```

`git clean -fd` (no `-x`) removes only untracked files that are **not** gitignored — so it leaves `.webdesign/`, `.stitch/`, and the project's gitignored build output (`.next/`, `dist/`, `node_modules/`) untouched, and only ever deletes files born *during* this iteration's restyle. This is safe **because** the start-of-iteration clean-tree assertion already guaranteed the tree held nothing untracked before the restyle began: anything `clean -fd` now removes was created by the restyle itself. (Corollary: if the project does **not** gitignore its build output, that output is untracked and the start-of-iteration assertion will have halted the run *before* any `clean -fd` ran — never silently deleting it.)

After rollback, assert the tree is clean (`git status --porcelain` is empty) before continuing to the next page.

2. Set page-level `status = failed` in `state.json`. Record the failure reason in `state.json` under `pages[].failure_reason`.

3. **Continue to the next page.** Do not abort the run. Failed pages can be retried later via `/bx:webdesign page <name>`.

### 3f — Safety valve: set `status = manual` and skip

If the existing page structure has diverged too far from the Stitch screen to safely restyle without risking loss of logic (e.g. the existing markup is a deeply nested runtime-rendered tree that cannot be mapped section-by-section, or the page renders exclusively via third-party components with no reachable class props), **do not attempt the restyle.**

Set page-level `status = manual` in `state.json` and skip to the next page. Surface the reason:

```
⚠ <page>: status = manual — structure diverged too far to restyle safely without risking
  loss of logic. Manual restyle required. See .webdesign/briefs/<page>.md for the contract.
```

---

## Step 4 — Close Phase 3 and Print Final Report

When all pages have been processed (every page is `verified`, `manual`, or `failed`):

1. Write to `state.json`:
   ```json
   { "phase": "done" }
   ```

2. Print the final report:

```
## Phase 3 complete — Safe Inject & Verify

**Branch:** <state.json["branch"]>

| Status   | Count | Pages |
|----------|-------|-------|
| verified |   N   | <comma-separated page slugs> |
| manual   |   K   | <slugs> |
| failed   |   J   | <slugs> |

**Token commit:** <if tokens_applied was set THIS run: "tokens: apply new design system" | if tokens_applied was already true on entry: "design system already applied (prior session)">
**Page commits:** webdesign: restyle <page> × N

**Next steps:**
1. Review the `<branch>` branch — inspect `manual` and `failed` pages if any.
2. For failed pages, retry with: /bx:webdesign page <name>
3. For manual pages, restyle by hand following .webdesign/briefs/<page>.md.
4. Run your full test suite against the branch.
5. When satisfied, merge `<branch>` into your main branch.
```

---

## Summary: State Writes + Artefacts

### State keys written in Phase 3

| Key | Type | Written in | Value set |
|-----|------|-----------|-----------|
| `tokens_applied` | boolean | Step 2 | `true` after token commit |
| `phase` | string | Step 2 / Step 3 (loop start) / Step 4 | `tokens_injected` → `injecting_pages` → `done` |
| `pages[].status` | string | Step 1 (all states null) / 3b / 3d / 3e / 3f | `injected` → `verified` / `failed` / `manual` |
| `pages[].failure_reason` | string | Step 1 / 3e | error description on failure |

### Artefact paths written in Phase 3

| Artefact | Path |
|----------|------|
| Fetched Stitch HTML (temp) | `.webdesign/tmp/stitch-<page>-<state>.html` |
| After screenshots (approved design) | `.webdesign/after/<page>-<state>.png` |
| After screenshots (post-inject capture) | `.webdesign/after/<page>-post-inject.png` |
| State file (updated) | `.webdesign/state.json` |
| Live sitemap record | `.webdesign/SITE.md` (gitignored) |
| Token commit | one commit on `webdesign/<date>` branch |
| Per-page commits | one `webdesign: restyle <page>` commit per verified page |
