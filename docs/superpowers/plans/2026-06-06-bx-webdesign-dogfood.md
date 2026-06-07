# /bx:webdesign — First-Run Dogfood Checklist

**Date:** 2026-06-06
**Pre-condition:** Stitch MCP + stitch-skills must be installed before running. Work through the setup
checklist (Step A) first if they are not yet present.

---

## 0. Pre-flight: dependencies and setup

- [ ] Stitch MCP installed and registered: `npx @_davideast/stitch-mcp init` + `claude mcp add ... stitch ...`
- [ ] stitch-skills plugin installed: `npx plugins add google-labs-code/stitch-skills --scope project --target claude-code`
- [ ] `/bx:webdesign` no longer shows the setup banner on invocation (both dependency checks pass)
- [ ] Confirm the actual MCP tool-name prefix: run `/bx:webdesign` and check which tools appear as `mcp__<server-name>__*`. If the registered server name differs from `stitch`, the `allowed-tools` in `bx/skills/webdesign/SKILL.md` (line 6: `mcp__stitch__*`) and the detection check in SKILL.md Step A must be updated to match the real prefix.

---

## 1. Step 0 — Stack detection

- [ ] **Non-web repo:** run `/bx:webdesign` in a repo with no web signals (e.g. a Python CLI). Confirm it prints `Not a web project — /bx:webdesign only refactors web projects. Exiting.` and stops with no state written.
- [ ] **Greenfield repo:** run in a repo with `package.json` + a build config but no page/component/route files. Confirm it prints `Greenfield/new projects aren't supported in /bx:webdesign v1 (refactor only). Exiting.` and stops with no state written.
- [ ] **Web project:** run in a real Next.js (or other framework) project. Confirm the one-line detected-stack summary prints correctly: `Detected: <framework> · styling: <styling_system> · app_runnable: <true|false>`.
- [ ] Confirm `styling_system` matches what the project actually uses (check `tailwind.config.js` presence, etc.).
- [ ] Confirm `app_runnable` is set correctly (true only if `node_modules/` is present, a build/serve cmd was found, and no unresolved `.env.example`).

---

## 2. Phase 1 — Extract & Stage

- [ ] Phase 1 creates and checks out the `webdesign/<YYYY-MM-DD>` branch (date matches today). No commits yet on main/other branches.
- [ ] `.webdesign/` directory is created with `briefs/`, `before/`, and `after/` subdirectories.
- [ ] `.webdesign/` block is appended to the project's `.gitignore` between sentinel markers (`# /bx:webdesign managed`). Second run is idempotent (block not duplicated).
- [ ] `state.json` exists at `.webdesign/state.json` with correct initial shape: `branch`, `styling_system`, `build_cmd`, `serve_cmd`, `app_runnable`, `pages[]`.
- [ ] One brief per discovered route is written to `.webdesign/briefs/<page>.md`; each brief has a non-empty "Functionality to PRESERVE" section sourced from real handlers/API calls (not placeholder text).
- [ ] The page inventory table is printed before proceeding; the skill pauses and waits for user confirmation.
- [ ] **If `app_runnable: true`:** before/ screenshots are captured for each route into `.webdesign/before/<page>.png` via Playwright. Confirm screenshot files exist and show the current design.
- [ ] **If `app_runnable: false`:** the warning prints and screenshots are skipped cleanly (no error).
- [ ] Stitch is seeded: `stitch::code-to-design` is invoked (or the source-only fallback path via `stitch::extract-design-md` + `stitch::manage-design-system` when `app_runnable: false`).
- [ ] `stitch_project_id` is persisted to `state.json` (app_runnable: true path). Absent on source-only fallback.
- [ ] The Stitch project URL is recorded in `SITE.md` at the project root.

### 2a. Vibe-setting — Claude-led interview path (a)

- [ ] Claude asks all 5 questions in one turn (vibe, audience, inspiration, color, mode).
- [ ] Claude maps answers to design-system knobs using the vibe table and shows a proposed-knobs confirmation table.
- [ ] User confirms → `stitch::manage-design-system` is invoked, `design_system_id` is persisted to `state.json`.

### 2b. Vibe-setting — Stitch canvas path (b)

- [ ] Claude prints the Stitch project URL and waits for "continue".
- [ ] On "continue", Claude invokes `stitch::manage-design-system` → `list_design_systems`, identifies the configured design system, and persists `design_system_id` to `state.json`.

- [ ] Phase 1 closes: `phase: direction_set` written to `state.json`. Phase 1 summary block printed.

---

## 3. Phase 2 — Design & Review

- [ ] Phase 2 resumes correctly from `phase: direction_set` without re-running Phase 1 steps (no branch re-creation, no `.gitignore` re-append, no Stitch re-seeding).
- [ ] Quota pre-flight prints the screen estimate (`Σ states per page`) and waits for `yes / no / edit briefs first` before calling `generate_screen_from_text`.
- [ ] Generation proceeds sequentially per page/state pair (not parallelised). Progress notes print after each page.
- [ ] `pages[].states.<name>.screen_id` and `pages[].states.<name>.status = generated` are written to `state.json` after each successful generation.
- [ ] Page-level `pages[].status = generated` is set only after all of a page's states are attempted.
- [ ] A failed generation marks that state `status: failed` and continues; the run does not abort.
- [ ] Review card prints at the end: Stitch project URL + bulleted list of generated pages/states. `phase: review_pending` written to `state.json`. Skill stops.
- [ ] Re-running `/bx:webdesign` shows the approval prompt. Requesting changes routes through `edit_screens` and re-prints the review card; `phase` stays `review_pending` until approval.
- [ ] **Approving designs:** confirm that NO intermediate `phase: approved` is ever written. The transition goes directly from `review_pending` → `tokens_injected` (via Phase 3 Step 2). Verify `state.json` after approval to confirm.

---

## 4. Phase 3 — Inject & Verify

### 4a. Tokens-first step

- [ ] Phase 3 checks out the `webdesign/<date>` branch before any writes.
- [ ] Stitch tokens are merged into the project's theme layer (correct strategy for the detected `styling_system`).
- [ ] Build runs after token merge and must pass before the token commit lands.
- [ ] Token commit message is `tokens: apply new design system`.
- [ ] `tokens_applied: true` and `phase: tokens_injected` written to `state.json` ONLY after the commit succeeds.
- [ ] If the token build fails: error surfaced, `phase` left as `review_pending`, no commit, clean re-entry on next run.

### 4b. Per-page loop

- [ ] `phase: injecting_pages` written to `state.json` at the start of the loop (before the first page iteration).
- [ ] For each page: the working tree is asserted clean (`git status --porcelain` empty) before starting. A non-empty tree causes the skill to STOP with a warning.
- [ ] **Core restyle check:** restyled page preserves all event handlers, lifecycle hooks, API calls, route links, and state variables from the original source. No Stitch placeholder text or stock images remain.
- [ ] **Responsive preservation:** if the original source has `sm:` / `md:` / `lg:` Tailwind prefixes (or equivalent media-queries), the restyled output retains them.
- [ ] `data-stitch-id` values are preserved as inline comments (`{/* data-stitch-id: <id> */}`) in the restyled markup, not as live DOM attributes.
- [ ] No new npm packages are imported in the restyled file.
- [ ] `pages[].status: injected` written after the restyle write, before verification.

### 4c. Verification

- [ ] Verification runs in order: typecheck → build → tests → Playwright (if `app_runnable: true`).
- [ ] **Green path:** `git add -A` + `git commit -m "webdesign: restyle <page>"` commits ALL changed files (not just `pages[].file`). `SITE.md` updated. `pages[].status: verified` written.
- [ ] After green commit, the working tree is clean (assert: next page's dirty-tree check passes).
- [ ] **Failure path — induce a build error:** break the project build (e.g. introduce a syntax error in the restyled file). Confirm:
  - Verification fails at the build step.
  - `git restore . && git clean -fd` rolls back ALL changes (not just the page file).
  - Tree is clean after rollback (`git status --porcelain` empty).
  - `pages[].status: failed` and `pages[].failure_reason` written to `state.json`.
  - The loop continues to the next page without aborting.

### 4d. Multi-file restyle

- [ ] Restyle a page that touches a shared component (e.g. a `Header` component imported by multiple pages). Confirm:
  - The commit uses `git add -A`, capturing ALL modified files (page file + shared component).
  - If the restyle fails, `git restore . && git clean -fd` rolls back ALL modified files (including the shared component).

---

## 5. Overrides and edge cases

- [ ] **`/bx:webdesign status`** before any run: prints `No /bx:webdesign run started in this project yet.` and stops.
- [ ] **`/bx:webdesign status`** mid-run: prints current phase + table of all pages with `status` and per-state `screen_id` / `status`. Takes no action.
- [ ] **`/bx:webdesign page <name>`** before tokens are applied (or before Phase 2 generates the page): prints the guard message (`Cannot inject <name> yet — ...`) and stops.
- [ ] **`/bx:webdesign page <name>`** after Phase 3 tokens applied + page generated: re-runs only the Phase-3 per-page loop for that page. Useful for retrying a `failed` page.
- [ ] **`/bx:webdesign --force-setup`** when both dependencies are present: prints `Stitch MCP + stitch-skills both detected — setup complete.` and stops.
- [ ] **`/bx:webdesign --force-setup`** when a dependency is missing: re-prints the setup banner (respecting the specificity rule — only the missing step(s)).

---

## 6. Responsive and mobile behavior

- [ ] Open a restyled page in the browser at a mobile viewport (e.g. 375px). Confirm the layout is responsive: no elements overflow, no mobile breakpoints are missing, navigation collapses correctly (if it did before the restyle).
- [ ] Compare the restyled mobile view against the `before/` screenshot to confirm mobile behavior was preserved, not regressed.

---

## 7. Notes / known caveats to record during dogfood

- If the Stitch MCP server name differs from `stitch`, update `allowed-tools: mcp__stitch__*` in `SKILL.md` and the detection pattern in Step A.
- `hugo` and `bundle exec jekyll` are framework-default `serve_cmd`/`build_cmd` values stored in `state.json` and executed via `Bash(<serve_cmd>)`. These are NOT covered by the current `allowed-tools` (`Bash(git:*)`, `Bash(npm:*)`, `Bash(npx:*)`, `Bash(curl:*)`, `Bash(mkdir:*)`). If running against a Hugo or Jekyll project, add `Bash(hugo:*)` and `Bash(bundle:*)` to allowed-tools. (See structural validation report 2026-06-06 for details.)
